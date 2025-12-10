"""
Bidirectional Downloader/Uploader with Logging
Docker 서버 ↔ 로컬 (F:/uploads, ./converter/uploads) 양방향 전송
"""
import os
import sys
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict
import zipfile
import io
from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 로깅 모듈 import
sys.path.insert(0, '/app')
try:
    from shared_logging import get_logger
    logger = get_logger("downloader", "/logs")
    logger.info("Shared logging initialized for Downloader")
except ImportError as e:

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("downloader")
    logger.info(f"Using fallback logger: {e}")

app = FastAPI(title="Neuroglancer Bidirectional Transfer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= 디렉터리 설정 =============
DOCKER_UPLOADS = "/tmp/uploads"
F_DRIVE_UPLOADS = "/app/f_uploads"
PROJECT_UPLOADS = "/app/project_uploads"
TRANSFER_LOG = "/app/transfer_history.json"
LOG_DIR = "/logs"

# 디렉터리 생성
for directory in [DOCKER_UPLOADS, F_DRIVE_UPLOADS, PROJECT_UPLOADS]:
    os.makedirs(directory, exist_ok=True)

logger.info("=" * 60)
logger.info("🔄 Bidirectional Transfer Service Starting")
logger.info("=" * 60)
logger.info(f"Docker uploads: {DOCKER_UPLOADS}")
logger.info(f"F Drive uploads: {F_DRIVE_UPLOADS}")
logger.info(f"Project uploads: {PROJECT_UPLOADS}")
logger.info(f"Log directory: {LOG_DIR}")
logger.info("=" * 60)


# ============= Models =============

class TransferRequest(BaseModel):
    source_location: str
    target_location: str
    item_name: str
    overwrite: bool = False


class TransferHistory:
    """전송 기록 관리"""
    
    def __init__(self, log_file: str = TRANSFER_LOG):
        self.log_file = log_file
        self.history = self._load()
        logger.info(f"TransferHistory initialized with {len(self.history)} records")
    
    def _load(self) -> List[Dict]:
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load transfer history: {e}", exc_info=True)
                return []
        return []
    
    def _save(self):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            logger.debug(f"Transfer history saved: {len(self.history)} records")
        except Exception as e:
            logger.error(f"Failed to save transfer history: {e}", exc_info=True)
    
    def add(self, record: Dict):
        record['timestamp'] = datetime.now().isoformat()
        self.history.append(record)
        self._save()
        logger.info(f"Transfer record added", **record)
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        return list(reversed(self.history[-limit:]))


transfer_history = TransferHistory()


# ============= Helper Functions =============

def get_location_path(location: str) -> Path:
    """위치 문자열을 실제 경로로 변환"""
    locations = {
        'docker': Path(DOCKER_UPLOADS),
        'f_drive': Path(F_DRIVE_UPLOADS),
        'project': Path(PROJECT_UPLOADS)
    }
    
    if location not in locations:
        raise ValueError(f"Invalid location: {location}")
    
    return locations[location]


def scan_directory(location: str) -> List[Dict]:
    """디렉터리 스캔하여 파일/폴더 목록 반환"""
    try:
        base_path = get_location_path(location)

        logger.info(f"🔍 Scanning {location} -> {base_path}")

        if not base_path.exists():
            logger.warning(f"⚠️ Location path does not exist: {location} -> {base_path}")
            return []

        items = []

        logger.info(f"📂 Reading directory: {base_path}")

        for item in base_path.iterdir():
            try:
                is_dir = item.is_dir()

                # 파일만 크기 계산, 디렉터리는 "-" 표시
                if is_dir:
                    size_mb = "-"  # 디렉터리는 크기 표시 안 함
                else:
                    size_bytes = item.stat().st_size
                    size_mb = round(size_bytes / (1024 * 1024), 2)

                items.append({
                    'name': item.name,
                    'type': 'directory' if is_dir else 'file',
                    'size_mb': size_mb,
                    'extension': item.suffix.lower() if not is_dir else None,
                    'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })

                logger.debug(f"  ✅ {item.name} ({size_mb} MB)")

            except Exception as e:
                logger.error(f"❌ Error scanning {item.name}: {e}", location=location, exc_info=True)

        logger.info(f"✅ Scanned {location}: found {len(items)} items")
        return sorted(items, key=lambda x: (x['type'], x['name']))

    except Exception as e:
        logger.error(f"❌ Fatal error scanning {location}: {e}", exc_info=True)
        return []


def calculate_size(path: Path) -> int:
    """경로의 전체 크기 계산 (바이트)"""
    if path.is_file():
        return path.stat().st_size
    
    total = 0
    for item in path.rglob('*'):
        if item.is_file():
            total += item.stat().st_size
    return total


def transfer_item(source_loc: str, target_loc: str, item_name: str, overwrite: bool = False) -> Dict:
    """파일 또는 디렉터리 전송"""
    logger.info(f"Transfer started: {item_name}", 
               source=source_loc, 
               target=target_loc, 
               overwrite=overwrite)
    
    source_path = get_location_path(source_loc) / item_name
    target_path = get_location_path(target_loc) / item_name
    
    if not source_path.exists():
        logger.error(f"Source not found: {source_path}")
        raise FileNotFoundError(f"Source not found: {source_path}")
    
    if target_path.exists() and not overwrite:
        logger.error(f"Target already exists: {target_path}")
        raise FileExistsError(f"Target already exists: {target_path}")
    
    # 기존 파일 삭제
    if target_path.exists():
        logger.info(f"Removing existing target: {target_path}")
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
    
    start_time = datetime.now()
    
    try:
        # 복사 실행
        if source_path.is_dir():
            shutil.copytree(source_path, target_path)
        else:
            shutil.copy2(source_path, target_path)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        size_bytes = calculate_size(target_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        result = {
            'success': True,
            'item_name': item_name,
            'source_location': source_loc,
            'target_location': target_loc,
            'type': 'directory' if source_path.is_dir() else 'file',
            'size_mb': size_mb,
            'duration_seconds': round(duration, 2),
            'source_path': str(source_path),
            'target_path': str(target_path)
        }
        
        logger.info(f"Transfer completed: {item_name}", 
                   size_mb=size_mb, 
                   duration=duration)
        
        return result
        
    except Exception as e:
        logger.error(f"Transfer failed: {item_name}", 
                    source=source_loc,
                    target=target_loc,
                    exc_info=True)
        raise


# ============= Frontend 설정 =============
frontend_dir = "/frontend"
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    logger.info(f"Frontend mounted: {frontend_dir}")


# ============= API Endpoints =============

@app.get("/")
def index():
    """메인 페이지"""
    logger.debug("Index page accessed")
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {
        "service": "Bidirectional Transfer Service",
        "status": "running",
        "endpoints": {
            "list_files": "/api/files/{location}",
            "transfer": "/api/transfer",
            "download": "/api/download/{location}/{item_name}",
            "upload": "/api/upload/{location}",
            "history": "/api/history"
        }
    }


@app.get("/api/health")
def health_check():
    """헬스 체크"""
    health_info = {
        "status": "healthy",
        "locations": {
            "docker": {
                "path": DOCKER_UPLOADS,
                "accessible": os.path.exists(DOCKER_UPLOADS),
                "items": len(scan_directory('docker'))
            },
            "f_drive": {
                "path": F_DRIVE_UPLOADS,
                "accessible": os.path.exists(F_DRIVE_UPLOADS),
                "items": len(scan_directory('f_drive'))
            },
            "project": {
                "path": PROJECT_UPLOADS,
                "accessible": os.path.exists(PROJECT_UPLOADS),
                "items": len(scan_directory('project'))
            }
        }
    }
    logger.debug("Health check performed", **health_info)
    return health_info


@app.get("/api/files/{location}")
def list_files(location: str):
    """특정 위치의 파일 목록"""
    logger.info(f"Listing files for location: {location}")
    try:
        items = scan_directory(location)
        return {
            "location": location,
            "path": str(get_location_path(location)),
            "items": items,
            "total": len(items)
        }
    except ValueError as e:
        logger.error(f"Invalid location: {location}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/files")
def list_all_files():
    """모든 위치의 파일 목록"""
    logger.info("Listing all files")

    result = {}

    for location in ['docker', 'f_drive', 'project']:
        try:
            items = scan_directory(location)
            result[location] = items
            logger.info(f"Scanned {location}: found {len(items)} items")
        except Exception as e:
            logger.error(f"Failed to scan {location}: {e}", exc_info=True)
            result[location] = []

    return result


@app.post("/api/transfer")
def transfer(request: TransferRequest):
    """파일/디렉터리 전송 실행"""
    logger.info(f"Transfer requested: {request.item_name}",
               source=request.source_location,
               target=request.target_location)
    try:
        result = transfer_item(
            source_loc=request.source_location,
            target_loc=request.target_location,
            item_name=request.item_name,
            overwrite=request.overwrite
        )
        
        transfer_history.add(result)
        
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Transfer failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")


@app.get("/api/download/{location}/{item_name}")
async def download_item(location: str, item_name: str):
    """파일 또는 디렉터리를 ZIP으로 다운로드"""
    logger.info(f"Download requested: {location}/{item_name}")
    try:
        source_path = get_location_path(location) / item_name
        
        if not source_path.exists():
            logger.warning(f"Item not found for download: {source_path}")
            raise HTTPException(status_code=404, detail="Item not found")
        
        if source_path.is_file():
            logger.info(f"Downloading file: {item_name}")
            return FileResponse(source_path, filename=item_name, media_type='application/octet-stream')
        
        # 디렉터리인 경우 ZIP으로 압축
        logger.info(f"Creating ZIP for directory: {item_name}")
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_path)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        logger.info(f"ZIP created successfully: {item_name}")
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={item_name}.zip"}
        )
        
    except ValueError as e:
        logger.error(f"Invalid location: {location}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload/{location}")
async def upload_file(location: str, file: UploadFile = File(...)):
    """파일 업로드"""
    logger.info(f"Upload requested: {file.filename}", location=location)
    try:
        target_path = get_location_path(location) / file.filename
        
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        size_mb = round(target_path.stat().st_size / (1024 * 1024), 2)
        
        result = {
            'success': True,
            'filename': file.filename,
            'location': location,
            'size_mb': size_mb,
            'path': str(target_path)
        }
        
        transfer_history.add({
            **result,
            'source_location': 'upload',
            'target_location': location,
            'item_name': file.filename,
            'type': 'file'
        })
        
        logger.info(f"Upload completed: {file.filename}", size_mb=size_mb)
        return result
        
    except ValueError as e:
        logger.error(f"Invalid location: {location}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Upload failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.delete("/api/files/{location}/{item_name}")
def delete_item(location: str, item_name: str):
    """파일 또는 디렉터리 삭제"""
    logger.info(f"Delete requested: {location}/{item_name}")
    try:
        item_path = get_location_path(location) / item_name
        
        if not item_path.exists():
            logger.warning(f"Item not found for deletion: {item_path}")
            raise HTTPException(status_code=404, detail="Item not found")
        
        if item_path.is_dir():
            shutil.rmtree(item_path)
        else:
            item_path.unlink()
        
        logger.info(f"Deleted: {location}/{item_name}")
        return {
            "success": True,
            "message": f"Deleted: {item_name}",
            "location": location
        }
        
    except ValueError as e:
        logger.error(f"Invalid location: {location}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/history")
def get_history(limit: int = Query(20, ge=1, le=100)):
    """전송 기록 조회"""
    logger.debug(f"History requested: limit={limit}")
    return {
        "history": transfer_history.get_recent(limit),
        "total": len(transfer_history.history)
    }


@app.delete("/api/history")
def clear_history():
    """전송 기록 초기화"""
    logger.warning("Transfer history cleared")
    transfer_history.history = []
    transfer_history._save()
    return {"success": True, "message": "History cleared"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8001)
