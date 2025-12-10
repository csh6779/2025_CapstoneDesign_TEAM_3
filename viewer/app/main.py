"""
ATI Lab 2025 - Neuroglancer Unified Viewer
JSON-based Authentication (MySQL 제거, 기존 API 형식 유지)
/viewer/app/main.py
"""

import os
import sys
from pathlib import Path
import time
import jwt
import json
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from passlib.context import CryptContext

# Python path 설정
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, HTTPException, Form, Query, Depends, Request, BackgroundTasks, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# 로깅 설정
from shared_logging import (
    get_logger,
    set_current_user,
    clear_current_user
)

logger = get_logger("viewer", "/logs")

print("🔥🔥🔥 JSON-based Authentication - 기존 API 형식 유지 🔥🔥🔥")

# ==========================================
# 1. FastAPI 앱 인스턴스 생성
# ==========================================
app = FastAPI(
    title="ATI Lab 2025 Viewer",
    description="Neuroglancer Viewer Backend with JSON-based Auth",
    version="3.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. 설정 및 경로
# ==========================================
CONVERTER_UPLOADS = os.getenv("CONVERTER_UPLOADS_DIR", "/mnt/converter_uploads")
F_UPLOADS = os.getenv("F_UPLOADS_DIR", "/mnt/f_uploads")
TMP_UPLOADS = os.getenv("TMP_UPLOADS_DIR", "/mnt/tmp_uploads")
FRONTEND_DIR = "/frontend"
LOG_DIR = "/logs"
DATA_DIR = "/viewer/data"

# 데이터 디렉터리 생성
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
USERS_FILE = Path(DATA_DIR) / "users.json"
BOOKMARKS_FILE = Path(DATA_DIR) / "bookmarks.json"

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

RAW_UPLOAD_DIRS = {}

# 업로드 디렉터리 설정
if os.path.exists(CONVERTER_UPLOADS):
    RAW_UPLOAD_DIRS["converter"] = CONVERTER_UPLOADS
if os.path.exists(F_UPLOADS):
    RAW_UPLOAD_DIRS["f_drive"] = F_UPLOADS

# tmp 폴더 생성 및 추가
if not os.path.exists(TMP_UPLOADS):
    try:
        os.makedirs(TMP_UPLOADS, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create tmp dir: {e}")
RAW_UPLOAD_DIRS["tmp"] = TMP_UPLOADS

logger.info("=" * 80)
logger.info("🔬 ATI Lab 2025 - Neuroglancer Viewer v3.0.0")
logger.info("=" * 80)
logger.info(f"   Converter: {CONVERTER_UPLOADS}")
logger.info(f"   F Drive:   {F_UPLOADS}")
logger.info(f"   Tmp Drive: {TMP_UPLOADS}")
logger.info(f"✅ Available locations: {list(RAW_UPLOAD_DIRS.keys())}")
logger.info("=" * 80)

# ==========================================
# 3. JSON 파일 관리 함수
# ==========================================

def load_users() -> Dict:
    """사용자 데이터 로드"""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users: Dict):
    """사용자 데이터 저장"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def load_bookmarks() -> Dict:
    """북마크 데이터 로드"""
    if not BOOKMARKS_FILE.exists():
        return {}
    try:
        with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_bookmarks(bookmarks: Dict):
    """북마크 데이터 저장"""
    with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bookmarks, f, indent=2, ensure_ascii=False)

# ==========================================
# 4. 인증 관련 함수
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해시"""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """JWT 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """현재 사용자 가져오기 (토큰 기반)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        login_id = payload.get("LoginId") or payload.get("sub")
        if login_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        users = load_users()
        if login_id not in users:
            raise HTTPException(status_code=401, detail="User not found")
        
        return users[login_id]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==========================================
# 5. 로깅 미들웨어
# ==========================================
# 5. 로깅 미들웨어
class AuthAndLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        login_id_str = None
        auth_header = request.headers.get("Authorization")
        path = request.url.path

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                login_id_str = payload.get("LoginId") or payload.get("sub")
            except:
                pass

        if not login_id_str and path.startswith("/u/"):
            try:
                parts = path.split("/")
                if len(parts) > 2:
                    login_id_str = parts[2]
            except:
                pass

        if not login_id_str:
            login_id_str = request.query_params.get("LoginId")

        # ✅ 사용자 컨텍스트 설정
        if login_id_str:
            set_current_user(login_id_str)

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        if request.method == "GET" and not path.startswith(("/api/health", "/favicon.ico", "/manifest.json", "/static")):
            log_payload = {
                "action": "view_image", "path": path, "method": request.method,
                "status": response.status_code, "duration": round(process_time, 4)
            }
            if response.status_code >= 500:
                logger.error(log_payload)
            elif response.status_code >= 400:
                logger.warning(log_payload)
            else:
                logger.info(log_payload)

        # ✅ 사용자 컨텍스트 클리어
        clear_current_user()
        return response

app.add_middleware(AuthAndLoggingMiddleware)

# ==========================================
# 6. Pydantic 모델
# ==========================================

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    LoginId: str
    UserName: str
    Password: str

class TokenResponse(BaseModel):
    AccessToken: str  # 기존 프론트엔드 형식 유지
    LoginId: str
    UserName: str
    Role: str

class UserResponse(BaseModel):
    LoginId: str
    UserName: str
    Role: str

class BookmarkCreate(BaseModel):
    volume_name: str
    location: str
    note: Optional[str] = None

# ==========================================
# 7. 볼륨 스캔 함수
# ==========================================

def scan_raw_uploads(location: str, calculate_size: bool = False) -> List[Dict]:
    """특정 위치의 precomputed 데이터셋 스캔"""
    if location not in RAW_UPLOAD_DIRS:
        return []

    base_path = Path(RAW_UPLOAD_DIRS[location])
    if not base_path.exists():
        logger.warning(f"Location path does not exist: {location} -> {base_path}")
        return []

    datasets = []
    try:
        for item in base_path.iterdir():
            if not item.is_dir():
                continue

            info_file = item / "info"
            if not info_file.exists():
                continue

            try:
                with open(info_file, 'r') as f:
                    info_data = json.load(f)

                size_info = {}
                if calculate_size:
                    try:
                        total_size = sum(
                            f.stat().st_size
                            for f in item.rglob('*')
                            if f.is_file()
                        )
                        size_info = {
                            'size_mb': round(total_size / (1024 * 1024), 2),
                            'size_gb': round(total_size / (1024 * 1024 * 1024), 2)
                        }
                    except:
                        size_info = {'size_mb': 0, 'size_gb': 0}

                dataset = {
                    'name': item.name,
                    'location': location,
                    'path': str(item),
                    'type': info_data.get('type', 'image'),
                    'data_type': info_data.get('data_type', 'uint8'),
                    'num_channels': info_data.get('num_channels', 1),
                    'dimensions': info_data['scales'][0]['size'] if 'scales' in info_data else None,
                    'resolution': info_data['scales'][0]['resolution'] if 'scales' in info_data else None,
                    'chunk_sizes': info_data['scales'][0]['chunk_sizes'][0] if 'scales' in info_data else None,
                    'has_info': True,
                    'created_at': datetime.fromtimestamp(item.stat().st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                    **size_info
                }
                datasets.append(dataset)
            except Exception as e:
                logger.error(f"Error reading info from {item.name}: {e}")
                continue

        logger.info(f"Scanned {location}: found {len(datasets)} precomputed datasets")
        return sorted(datasets, key=lambda x: x['modified_at'], reverse=True)
    except Exception as e:
        logger.error(f"Error scanning {location}: {e}")
        return []

def get_all_datasets() -> Dict[str, List[Dict]]:
    """모든 위치의 데이터셋 조회"""
    result = {}
    for location in RAW_UPLOAD_DIRS.keys():
        result[location] = scan_raw_uploads(location)
    return result

# ==========================================
# 8. API 엔드포인트
# ==========================================

@app.get("/")
def index():
    """메인 페이지"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "running", "version": "3.0.0", "available_locations": list(RAW_UPLOAD_DIRS.keys())}

@app.get("/api/health")
def health_check():
    """헬스 체크"""
    return {"status": "healthy", "locations": list(RAW_UPLOAD_DIRS.keys())}

# ==========================================
# 인증 API (기존 형식 유지)
# ==========================================

@app.post("/api/v1/auth/token", response_model=TokenResponse)
def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """로그인 - Form 데이터로 받기"""
    users = load_users()
    
    if username not in users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = users[username]
    
    if not verify_password(password, user["PasswordHash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"LoginId": username, "sub": username})
    
    logger.info(f"✅ User logged in: {username}")
    
    return TokenResponse(
        AccessToken=access_token,  # 기존 프론트엔드 형식
        LoginId=user["LoginId"],
        UserName=user["UserName"],
        Role=user["Role"]
    )

@app.post("/api/v1/auth/signup")
def signup(request: SignupRequest):
    """회원가입"""
    users = load_users()
    
    # 중복 확인
    if request.LoginId in users:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # 새 사용자 생성
    new_user = {
        "LoginId": request.LoginId,
        "UserName": request.UserName,
        "PasswordHash": get_password_hash(request.Password),
        "Role": "user",
        "CreatedAt": datetime.now().isoformat(),
        "UpdatedAt": datetime.now().isoformat()
    }
    
    users[request.LoginId] = new_user
    save_users(users)
    
    logger.info(f"✅ New user registered: {request.LoginId}")
    
    return {
        "message": "User created successfully",
        "LoginId": request.LoginId,
        "UserName": request.UserName
    }

@app.get("/api/v1/users/me", response_model=UserResponse)
@app.get("/api/v1/auth/me", response_model=UserResponse)
def get_me(current_user: Dict = Depends(get_current_user_from_token)):
    """현재 사용자 정보"""
    return UserResponse(
        LoginId=current_user["LoginId"],
        UserName=current_user["UserName"],
        Role=current_user["Role"]
    )

# ==========================================
# 볼륨 API (기존 형식 유지)
# ==========================================

@app.get("/api/volumes")
def list_volumes(
    LoginId: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user_from_token)
):
    """볼륨 목록 조회"""
    datasets = get_all_datasets()
    volumes_list = []
    
    for loc, items in datasets.items():
        for ds in items:
            volumes_list.append({
                "name": ds["name"],
                "location": loc,
                "dimensions": ds.get("dimensions"),
                "chunk_size": [64, 64, 64],
                "size_gb": round(ds.get("size_mb", 0) / 1024, 2),
            })
    
    logger.info(f"📦 User {current_user['LoginId']} requested volumes: {len(volumes_list)} found")
    
    return {"volumes": volumes_list, "count": len(volumes_list)}

@app.get("/api/admin/volumes")
def list_admin_volumes(current_user: Dict = Depends(get_current_user_from_token)):
    """관리자용 볼륨 목록"""
    if current_user["Role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    logger.info("Admin volume list requested by admin")
    volume_list = []
    
    for loc_name, loc_path in RAW_UPLOAD_DIRS.items():
        p = Path(loc_path)
        if not p.exists():
            logger.warning(f"⚠️ Path not found: {loc_path}")
            continue
        
        try:
            for item in p.iterdir():
                if item.is_dir() and not item.name.startswith(".") and item.name != "temp":
                    volume_list.append({
                        "name": item.name,
                        "location": loc_name
                    })
        except Exception as e:
            logger.error(f"Error scanning {loc_path}: {e}")
    
    logger.info(f"🔍 Found volumes: {len(volume_list)} items")
    return volume_list

@app.delete("/api/admin/volumes/{volume_name}")
def delete_volume(
    volume_name: str,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """볼륨 삭제"""
    if current_user["Role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    target_path = None
    found_location = ""
    
    for loc_name, loc_path in RAW_UPLOAD_DIRS.items():
        candidate_path = Path(loc_path) / volume_name
        if candidate_path.exists() and candidate_path.is_dir():
            target_path = candidate_path
            found_location = loc_name
            break
    
    if not target_path:
        raise HTTPException(status_code=404, detail=f"Volume '{volume_name}' not found")
    
    try:
        background_tasks.add_task(shutil.rmtree, target_path)
        logger.info(f"🗑️ Admin deleted volume: {volume_name} from {found_location}")
        return {"message": f"Started deletion of '{volume_name}' from {found_location}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/raw-uploads")
def list_raw_uploads(
    calculate_size: bool = Query(False, description="폴더 크기 계산 여부"),
    current_user: Dict = Depends(get_current_user_from_token)
):
    """변환된 precomputed 데이터셋 목록 조회"""
    logger.info(f"User {current_user['LoginId']} listing precomputed datasets")
    
    uploads = {}
    for location in RAW_UPLOAD_DIRS.keys():
        uploads[location] = scan_raw_uploads(location, calculate_size=calculate_size)
    
    total = sum(len(files) for files in uploads.values())
    
    return {
        "uploads": uploads,
        "total": total,
        "locations": list(RAW_UPLOAD_DIRS.keys())
    }

# ==========================================
# 북마크 API
# ==========================================

@app.get("/api/v1/bookmarks")
def list_bookmarks(current_user: Dict = Depends(get_current_user_from_token)):
    """북마크 목록"""
    bookmarks = load_bookmarks()
    user_bookmarks = bookmarks.get(current_user["LoginId"], [])
    return {"bookmarks": user_bookmarks}

@app.post("/api/v1/bookmarks")
def create_bookmark(
    bookmark: BookmarkCreate,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """북마크 생성"""
    bookmarks = load_bookmarks()
    
    if current_user["LoginId"] not in bookmarks:
        bookmarks[current_user["LoginId"]] = []
    
    new_bookmark = {
        "id": len(bookmarks[current_user["LoginId"]]) + 1,
        "volume_name": bookmark.volume_name,
        "location": bookmark.location,
        "note": bookmark.note,
        "created_at": datetime.now().isoformat()
    }
    
    bookmarks[current_user["LoginId"]].append(new_bookmark)
    save_bookmarks(bookmarks)
    
    logger.info(f"📌 User {current_user['LoginId']} created bookmark: {bookmark.volume_name}")
    return new_bookmark

@app.delete("/api/v1/bookmarks/{bookmark_id}")
def delete_bookmark(
    bookmark_id: int,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """북마크 삭제"""
    bookmarks = load_bookmarks()
    
    if current_user["LoginId"] not in bookmarks:
        raise HTTPException(status_code=404, detail="No bookmarks found")
    
    user_bookmarks = bookmarks[current_user["LoginId"]]
    bookmarks[current_user["LoginId"]] = [b for b in user_bookmarks if b["id"] != bookmark_id]
    save_bookmarks(bookmarks)
    
    logger.info(f"🗑️ User {current_user['LoginId']} deleted bookmark: {bookmark_id}")
    return {"message": "Bookmark deleted"}

# ==========================================
# 메모리 및 로그 API
# ==========================================

@app.get("/api/v1/memory-status")
def get_memory_status():
    """메모리 상태 조회 - 프론트엔드 호환 형식"""
    import psutil
    
    process = psutil.Process()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 프론트엔드가 기대하는 형식으로 반환
    return {
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free,
            "process_mb": process.memory_info().rss / (1024 * 1024),
            "system_percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        },
        "cache": {
            "cache_size_mb": 0,  # JSON 기반에서는 캠시 없음
            "hit_rate": 0.0
        },
        "config": {
            "cache_max_size_mb": 0
        }
    }

@app.post("/api/v1/memory-clean")
def clean_memory(current_user: Dict = Depends(get_current_user_from_token)):
    """메모리 정리 - 관리자 전용"""
    if current_user["Role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    import gc
    gc.collect()
    
    return {
        "freed_mb": 0,  # 실제로는 측정하기 어려움
        "message": "Memory cleanup completed"
    }

# ==========================================
# 업로드 API
# ==========================================

from fastapi import File, UploadFile
import aiofiles
from precomputed_writer import convert_image_file_to_precomputed

@app.post("/api/v1/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    파일 업로드 및 Precomputed 형식으로 변환
    업로드된 파일은 TMP_UPLOADS 디렉토리에 변환되어 저장됩니다.
    """
    if current_user["Role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # 파일 확장자 확인
    allowed_extensions = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # 임시 저장 경로
    upload_dir = Path(TMP_UPLOADS)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일명 중복 방지 (타임스탬프 추가)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = Path(file.filename).stem
    safe_filename = f"{timestamp}_{original_name}{file_ext}"
    temp_file_path = upload_dir / safe_filename
    
    # 변환된 precomputed 볼륨 저장 경로
    volume_name = f"{timestamp}_{original_name}"
    volume_path = upload_dir / volume_name
    
    try:
        # 1. 원본 파일 저장
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"📤 File uploaded by {current_user['LoginId']}: {safe_filename} ({file_size_mb:.2f} MB)")
        
        # 2. Precomputed 형식으로 변환
        logger.info(f"🔄 Converting {safe_filename} to precomputed format...")
        
        chunk_count = convert_image_file_to_precomputed(
            input_path=str(temp_file_path),
            output_path=str(volume_path),
            chunk_size=512,
            encoding="raw"
        )
        
        logger.info(f"✅ Conversion completed: {volume_name} ({chunk_count} chunks created)")
        
        # 3. 원본 파일 삭제 (선택적)
        try:
            temp_file_path.unlink()
            logger.info(f"🗑️ Temporary file removed: {safe_filename}")
        except:
            pass
        
        return {
            "message": f"File uploaded and converted successfully: {volume_name}",
            "volume_name": volume_name,
            "original_filename": file.filename,
            "size_mb": round(file_size_mb, 2),
            "chunks_created": chunk_count,
            "location": "tmp",
            "neuroglancer_url": f"http://localhost:8080/?json_url=http://localhost:9000/precomp/{volume_name}/info"
        }
        
    except Exception as e:
        logger.error(f"🚨 Upload/Conversion failed: {e}")
        # 실패 시 임시 파일 정리
        try:
            if temp_file_path.exists():
                temp_file_path.unlink()
            if volume_path.exists():
                shutil.rmtree(volume_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Upload/Conversion failed: {str(e)}")

@app.get("/api/logs/files")
def list_log_files():
    """로그 파일 목록"""
    log_base = Path(LOG_DIR)
    if not log_base.exists():
        return {"logs": {}}
    
    logs = {}
    try:
        for year_dir in sorted(log_base.iterdir(), reverse=True):
            if year_dir.is_dir():
                logs[year_dir.name] = {}
                for month_dir in sorted(year_dir.iterdir(), reverse=True):
                    if month_dir.is_dir():
                        logs[year_dir.name][month_dir.name] = sorted(
                            [f.stem for f in month_dir.glob("*.txt")], 
                            reverse=True
                        )
    except Exception as e:
        logger.error(f"Error listing log files: {e}")
    
    return {"logs": logs}

@app.get("/api/v1/image-logs/me")
def get_my_image_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    현재 사용자의 이미지 처리 로그 조회
    로그 파일에서 해당 사용자의 로그만 필터링하여 반환
    """
    log_base = Path(LOG_DIR)
    if not log_base.exists():
        return {"logs": [], "total": 0}
    
    login_id = current_user["LoginId"]
    logs = []
    
    try:
        # 날짜 범위 파싱
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            except:
                pass
        
        # 로그 파일 읽기
        for year_dir in sorted(log_base.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue
            
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue
                
                for log_file in sorted(month_dir.glob("*.txt"), reverse=True):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                
                                try:
                                    log_entry = json.loads(line)
                                    
                                    # 사용자 필터링 - 여러 필드 확인
                                    log_user = (
                                        log_entry.get("user") or 
                                        log_entry.get("user_id") or 
                                        log_entry.get("LoginId") or 
                                        log_entry.get("login_id")
                                    )
                                    
                                    if log_user != login_id:
                                        continue
                                    
                                    # 날짜 필터링
                                    if start_dt or end_dt:
                                        timestamp_str = log_entry.get("timestamp")
                                        if timestamp_str:
                                            try:
                                                log_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                                if start_dt and log_dt < start_dt:
                                                    continue
                                                if end_dt and log_dt > end_dt:
                                                    continue
                                            except:
                                                pass
                                    
                                    # 레벨 필터링
                                    if level and log_entry.get("level") != level:
                                        continue
                                    
                                    logs.append(log_entry)
                                    
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.error(f"Error reading log file {log_file}: {e}")
                        continue
        
        # 페이지네이션
        total = len(logs)
        logs = logs[skip:skip + limit]
        
        return {
            "logs": logs,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error fetching image logs: {e}")
        return {"logs": [], "total": 0}

# ==========================================
# Neuroglancer API
# ==========================================

NEUROGLANCER_URL = os.getenv("NEUROGLANCER_URL", "http://localhost:8080")

@app.get("/api/neuroglancer/info")
async def get_neuroglancer_info():
    """Neuroglancer 서버 정보 제공"""
    return {
        "url": NEUROGLANCER_URL,
        "local_url": "http://localhost:8080",
        "status": "running",
        "available_locations": list(RAW_UPLOAD_DIRS.keys())
    }

@app.get("/api/neuroglancer/state")
async def create_neuroglancer_state(
    volume_name: str,
    location: str,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """Neuroglancer 상태 URL 생성"""
    if location not in RAW_UPLOAD_DIRS:
        raise HTTPException(status_code=400, detail=f"Invalid location: {location}")

    volume_path = Path(RAW_UPLOAD_DIRS[location]) / volume_name
    if not volume_path.exists():
        raise HTTPException(status_code=404, detail=f"Volume not found: {volume_name}")

    info_file = volume_path / "info"
    if not info_file.exists():
        raise HTTPException(status_code=404, detail="Info file not found")

    with open(info_file, 'r') as f:
        info_data = json.load(f)

    state = {
        "layers": [
            {
                "type": "image",
                "source": f"precomputed://http://localhost:9000/precomp/{volume_name}",
                "name": volume_name,
                "shader": """
void main() {
  emitRGB(vec3(toNormalized(getDataValue(0))));
}
"""
            }
        ],
        "navigation": {
            "pose": {
                "position": {
                    "voxelSize": info_data['scales'][0]['resolution'],
                    "voxelCoordinates": [
                        info_data['scales'][0]['size'][0] // 2,
                        info_data['scales'][0]['size'][1] // 2,
                        info_data['scales'][0]['size'][2] // 2
                    ]
                }
            },
            "zoomFactor": 8
        },
        "layout": "xy-3d"
    }

    from urllib.parse import quote
    state_json = json.dumps(state)
    encoded_state = quote(state_json)

    neuroglancer_url = f"{NEUROGLANCER_URL}/#!{encoded_state}"

    logger.info({
        "action": "create_neuroglancer_state",
        "user": current_user["LoginId"],
        "volume": volume_name,
        "location": location
    })

    return {
        "url": neuroglancer_url,
        "state": state,
        "volume_info": {
            "name": volume_name,
            "location": location,
            "dimensions": info_data['scales'][0]['size'],
            "resolution": info_data['scales'][0]['resolution']
        }
    }

@app.get("/precomp/{volume_name}/{file_path:path}")
async def get_precomputed_file(volume_name: str, file_path: str):
    """Neuroglancer precomputed 파일 서빙"""
    target_path = None
    
    for loc_name, loc_path in RAW_UPLOAD_DIRS.items():
        candidate_dir = Path(loc_path) / volume_name
        if candidate_dir.exists() and candidate_dir.is_dir():
            target_path = candidate_dir
            break
    
    if not target_path:
        logger.warning(f"❌ Volume not found for request: {volume_name}")
        raise HTTPException(status_code=404, detail=f"Volume '{volume_name}' not found")
    
    full_file_path = target_path / file_path
    
    if full_file_path.exists() and full_file_path.is_file():
        return FileResponse(full_file_path)
    
    logger.warning(f"❌ File not found: {full_file_path}")
    raise HTTPException(status_code=404, detail="File not found")

# ==========================================
# Static files
# ==========================================

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

for location, path in RAW_UPLOAD_DIRS.items():
    if os.path.exists(path):
        app.mount(f"/precomputed/{location}", StaticFiles(directory=path), name=f"precomputed_{location}")
        logger.info(f"📁 Mounted: /precomputed/{location} -> {path}")

# ==========================================
# 시작 이벤트
# ==========================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Application Starting...")
    
    # 기본 관리자 계정 생성
    users = load_users()
    if "admin" not in users:
        users["admin"] = {
            "LoginId": "admin",
            "UserName": "Administrator",
            "PasswordHash": get_password_hash("admin1234"),
            "Role": "admin",
            "CreatedAt": datetime.now().isoformat(),
            "UpdatedAt": datetime.now().isoformat()
        }
        save_users(users)
        logger.info("✅ Default admin account created: admin / admin1234")
    
    # 북마크 파일 초기화
    if not BOOKMARKS_FILE.exists():
        save_bookmarks({})
        logger.info("✅ Bookmarks file initialized")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)