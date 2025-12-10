"""
Bidirectional Downloader/Uploader
Docker 서버 <-> 로컬 (Converter, F Drive) 양방향 전송
Viewer와 경로 공유
"""
import os
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys
sys.path.insert(0, '/app')

# 로깅 설정 (shared_logging이 없을 경우 기본 logging 사용)
try:
    from shared_logging import get_logger
    logger = get_logger("downloader", "/logs")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("downloader")

app = FastAPI(title="Neuroglancer Bidirectional Transfer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= 디렉터리 설정 (Viewer와 통합) =============

# Docker 서버 내부 (Downloader only)
DOCKER_UPLOADS = os.getenv("DOCKER_UPLOADS_DIR", "/tmp/uploads")

# Viewer와 동일한 경로
# Viewer: /mnt/converter_uploads -> Downloader: /app/converter_uploads
CONVERTER_UPLOADS = os.getenv("CONVERTER_UPLOADS_DIR", "/app/converter_uploads")

# Viewer: /mnt/f_uploads -> Downloader: /app/f_uploads
F_UPLOADS = os.getenv("F_UPLOADS_DIR", "/app/f_uploads")

# 전송 기록 (data 디렉터리에 저장)
TRANSFER_LOG = "/app/data/transfer_history.json"

# 디렉터리 생성
for directory in [DOCKER_UPLOADS, CONVERTER_UPLOADS, F_UPLOADS]:
    os.makedirs(directory, exist_ok=True)

# transfer_history.json을 저장할 data 디렉터리 생성
os.makedirs("/app/data", exist_ok=True)

logger.info("=" * 80)
logger.info("Bidirectional Transfer Service")
logger.info("=" * 80)
logger.info("경로 매핑 (Viewer와 공유):")
logger.info(f"   Docker:    {DOCKER_UPLOADS}")
logger.info(f"   Converter: {CONVERTER_UPLOADS}")
logger.info(f"             (Viewer: /mnt/converter_uploads)")
logger.info(f"   F Drive:   {F_UPLOADS}")
logger.info(f"             (Viewer: /mnt/f_uploads)")
logger.info("=" * 80)


# ============= 위치 관리 =============

LOCATIONS = {
    "docker": DOCKER_UPLOADS,
    "converter": CONVERTER_UPLOADS,  # Viewer와 공유
    "f_drive": F_UPLOADS,            # Viewer와 공유
}


def get_location_path(location: str) -> Path:
    """위치 문자열을 경로로 변환"""
    if location not in LOCATIONS:
        raise ValueError(f"Invalid location: {location}. Available: {list(LOCATIONS.keys())}")
    return Path(LOCATIONS[location])


# ============= 전송 기록 관리 =============

def load_transfer_log() -> List[Dict]:
    """전송 기록 로드"""
    if os.path.exists(TRANSFER_LOG):
        try:
            with open(TRANSFER_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
                # JSON 파일이 리스트면 그대로 반환, 딕셔너리면 빈 리스트 반환
                if isinstance(data, list):
                    return data
                else:
                    logger.warning(f"Transfer log file has wrong format (expected list, got {type(data).__name__}). Resetting.")
                    return []
        except Exception as e:
            logger.error(f"Error loading transfer log: {e}")
            return []
    return []


def save_transfer_log(log: List[Dict]):
    """전송 기록 저장"""
    with open(TRANSFER_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def add_transfer_record(
    source_location: str,
    target_location: str,
    folder_name: str,
    status: str = "success",
    size_mb: float = 0,
    duration_seconds: float = 0
):
    """전송 기록 추가"""
    logs = load_transfer_log()
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "source_location": source_location,
        "target_location": target_location,
        "folder_name": folder_name,
        "status": status,
        "size_mb": size_mb,
        "duration_seconds": duration_seconds,
    })
    # 최대 100개 유지
    if len(logs) > 100:
        logs = logs[-100:]
    save_transfer_log(logs)
    logger.info(f"Transfer recorded: {source_location}/{folder_name} -> {target_location} [{status}]")


# ============= API Endpoints =============

@app.get("/", response_class=HTMLResponse)
def index():
    """메인 페이지 (index.html 서빙)"""
    # frontend 디렉터리에서 index.html 찾기
    html_path = Path("/frontend/index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    # fallback: 간단한 안내 페이지
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>Downloader</title></head>
    <body>
        <h1>Bidirectional Transfer Service</h1>
        <p>static/index.html 파일이 필요합니다.</p>
        <h2>API Endpoints:</h2>
        <ul>
            <li>GET /api/locations - 위치 목록</li>
            <li>GET /api/folders/{location} - 폴더 목록</li>
            <li>POST /api/transfer - 폴더 전송</li>
            <li>GET /api/transfer/history - 전송 기록</li>
        </ul>
    </body>
    </html>
    """)


@app.get("/api/status")
def get_status():
    """서비스 상태"""
    return {
        "service": "Neuroglancer Bidirectional Transfer",
        "version": "2.0.0",
        "available_locations": list(LOCATIONS.keys()),
        "shared_with_viewer": ["converter", "f_drive"],
    }


@app.get("/api/locations")
def list_locations():
    """사용 가능한 위치 목록"""
    result = {}
    for location, path in LOCATIONS.items():
        try:
            items = os.listdir(path) if os.path.exists(path) else []
            folders = [i for i in items if os.path.isdir(os.path.join(path, i))]
            result[location] = {
                "path": str(path),
                "accessible": os.path.exists(path),
                "folders_count": len(folders),
                "shared_with_viewer": location in ["converter", "f_drive"],
            }
        except Exception as e:
            result[location] = {
                "path": str(path),
                "accessible": False,
                "error": str(e),
            }

    return result


@app.get("/api/folders/{location}")
def list_folders(location: str):
    """특정 위치의 폴더 목록"""
    try:
        path = get_location_path(location)

        if not path.exists():
            return {
                "location": location,
                "folders": [],
                "total": 0,
                "error": f"Location not accessible: {path}"
            }

        folders = []
        for item in path.iterdir():
            if item.is_dir():
                # info 파일 확인 (Neuroglancer precomputed format)
                has_info = (item / "info").exists()

                # 폴더 크기 계산 - 빠른 응답을 위해 비활성화
                # 60GB+ 파일이 있으면 매우 느림!
                size_mb = 0  # 크기 계산 생략

                folders.append({
                    "name": item.name,
                    "location": location,
                    "has_info": has_info,
                    "size_mb": size_mb,
                    "modified_at": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                })

        logger.info(f"Listed {len(folders)} folders in {location}")
        return {
            "location": location,
            "folders": sorted(folders, key=lambda x: x["modified_at"], reverse=True),
            "total": len(folders),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing folders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transfer")
def transfer_folder(
    source_location: str = Query(..., description="원본 위치"),
    target_location: str = Query(..., description="대상 위치"),
    folder_name: str = Query(..., description="폴더 이름"),
    overwrite: bool = Query(False, description="덮어쓰기 여부"),
):
    """폴더 전송"""
    import time
    start_time = time.time()

    try:
        # 경로 검증
        source_path = get_location_path(source_location) / folder_name
        target_path = get_location_path(target_location) / folder_name

        if not source_path.exists():
            raise HTTPException(status_code=404, detail=f"Source folder not found: {folder_name}")

        if target_path.exists():
            if overwrite:
                logger.info(f"Removing existing target: {target_path}")
                shutil.rmtree(target_path)
            else:
                raise HTTPException(status_code=409, detail=f"Target folder already exists: {folder_name}")

        # 폴더 크기 계산
        try:
            size_bytes = sum(f.stat().st_size for f in source_path.rglob("*") if f.is_file())
            size_mb = round(size_bytes / (1024 * 1024), 2)
        except:
            size_mb = 0

        # 폴더 복사
        logger.info(f"Transferring: {source_location}/{folder_name} -> {target_location}/{folder_name}")
        shutil.copytree(source_path, target_path)

        duration = round(time.time() - start_time, 2)

        # 전송 기록
        add_transfer_record(
            source_location=source_location,
            target_location=target_location,
            folder_name=folder_name,
            status="success",
            size_mb=size_mb,
            duration_seconds=duration
        )

        logger.info(f"Transfer completed: {folder_name} ({size_mb} MB in {duration}s)")
        return {
            "message": "Transfer successful",
            "source": f"{source_location}/{folder_name}",
            "target": f"{target_location}/{folder_name}",
            "size_mb": size_mb,
            "duration_seconds": duration,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        logger.error(f"Transfer error: {e}", exc_info=True)

        # 실패 기록
        add_transfer_record(
            source_location=source_location,
            target_location=target_location,
            folder_name=folder_name,
            status=f"failed: {str(e)}",
            duration_seconds=duration
        )

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transfer/history")
def get_transfer_history(limit: int = Query(50, description="최대 개수")):
    """전송 기록 조회"""
    logs = load_transfer_log()
    return {
        "history": logs[-limit:] if limit > 0 else logs,
        "total": len(logs),
    }


@app.delete("/api/folders/{location}/{folder_name}")
def delete_folder(location: str, folder_name: str):
    """폴더 삭제"""
    try:
        path = get_location_path(location) / folder_name

        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Folder not found: {folder_name}")

        logger.info(f"Deleting: {location}/{folder_name}")
        shutil.rmtree(path)

        logger.info(f"Deleted: {folder_name}")
        return {
            "message": "Folder deleted",
            "location": location,
            "folder": folder_name,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============= Static Files =============

# frontend 디렉터리를 static으로 마운트
frontend_dir = Path("/frontend")
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# ============= Startup Event =============

@app.on_event("startup")
async def startup_event():
    """시작 시 실행"""
    logger.info("=" * 80)
    logger.info("Downloader Service Starting...")
    logger.info("=" * 80)

    logger.info("Checking directories:")
    for location, path in LOCATIONS.items():
        exists = os.path.exists(path)
        status = "OK" if exists else "NOT FOUND"
        shared = " (Viewer와 공유)" if location in ["converter", "f_drive"] else ""
        logger.info(f"[{status}] {location:15s}: {path}{shared}")

        if exists:
            try:
                items = [i for i in os.listdir(path) if os.path.isdir(os.path.join(path, i))]
                logger.info(f"       -> {len(items)} folders")
            except Exception as e:
                logger.error(f"       -> Error: {e}")
    
    # Frontend 디렉터리 확인
    frontend_exists = os.path.exists("/frontend/index.html")
    logger.info(f"[{'OK' if frontend_exists else 'NOT FOUND'}] frontend       : /frontend/index.html")

    logger.info("=" * 80)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Downloader server")
    uvicorn.run(app, host="0.0.0.0", port=8001)