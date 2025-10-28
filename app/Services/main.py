# app/Services/main.py

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api.v1.endpoints import user as user_router_v1
from app.api.v1.endpoints import Auth, neuroglancer, memory, logs
from app.utils.file_logger import FileLogger
import os
import time

# 데이터베이스 자동 초기화 (Base.metadata.create_all 대체)
from app.database.init_db import init_database

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Neuroglancer 대용량 뷰어 시스템",
    version="2.0.0",
    description="이미지 업로드 및 Neuroglancer 뷰어 통합 시스템"
)

# CORS 설정 추가
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"

# 데이터 디렉터리 설정 (사용자별 폴더 구조)
DATA_ROOT = os.environ.get("DATA_DIR", str(BASE_DIR / "uploads"))
os.makedirs(DATA_ROOT, exist_ok=True)

# 로거 초기화
logger = FileLogger(
    log_dir=str(BASE_DIR / "logs"),
    log_prefix="app",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    enable_daily_rotation=True,
    enable_console=True
)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# uploads 디렉터리를 루트로 마운트 (사용자별 폴더 구조)
if os.path.exists(DATA_ROOT):
    app.mount("/uploads", StaticFiles(directory=DATA_ROOT), name="uploads")
    logger.info(f"uploads 디렉터리 마운트됨: {DATA_ROOT}")
    logger.info("사용자별 폴더 구조: /uploads/{username}/{volume_name}")

# 라우터 등록
# v1 사용자 관리 API
app.include_router(user_router_v1.router, prefix="/v1")

# v1 인증 API
app.include_router(Auth.router, prefix="/v1")

# Neuroglancer API
app.include_router(
    neuroglancer.router,
    prefix="/api",
    tags=["Neuroglancer"]
)

# 메모리 관리 API
app.include_router(
    memory.router,
    prefix="/api",
    tags=["Memory"]
)

# 로그 관리 API
app.include_router(
    logs.router,
    prefix="/api",
    tags=["Logs"]
)

# 볼륨 직접 접근을 위한 동적 라우팅
from fastapi import HTTPException as FastAPIHTTPException
from starlette.responses import FileResponse as StarletteFileResponse, JSONResponse


@app.get("/uploads/{username}/{volume_name}/info")
async def get_volume_info(username: str, volume_name: str):
    """
    사용자별 볼륨 info 파일 접근
    경로: /uploads/{username}/{volume_name}/info
    """
    logger.info(f"📂 Volume info 요청: {username}/{volume_name}")

    user_path = os.path.join(DATA_ROOT, username)
    volume_path = os.path.join(user_path, volume_name)
    info_path = os.path.join(volume_path, "info")

    logger.info(f"  🔍 Info 경로: {info_path}")

    if os.path.exists(info_path):
        logger.info(f"  ✅ Info 파일 발견")
        return StarletteFileResponse(
            info_path,
            media_type="application/json"
        )

    logger.error(f"  ❌ Info 파일 없음")

    # 디버깅 정보 제공
    available_volumes = []
    if os.path.exists(DATA_ROOT):
        for user in os.listdir(DATA_ROOT):
            user_dir = os.path.join(DATA_ROOT, user)
            if os.path.isdir(user_dir):
                for vol in os.listdir(user_dir):
                    vol_dir = os.path.join(user_dir, vol)
                    if os.path.isdir(vol_dir):
                        available_volumes.append(f"{user}/{vol}")

    return JSONResponse(
        status_code=404,
        content={
            "error": "Volume info not found",
            "requested": f"{username}/{volume_name}",
            "info_path": info_path,
            "available_volumes": available_volumes
        }
    )


@app.get("/uploads/{username}/{volume_name}/{scale_key}/{chunk_file}")
async def get_volume_chunk(username: str, volume_name: str, scale_key: str, chunk_file: str):
    """
    사용자별 볼륨 청크 파일 접근
    경로: /uploads/{username}/{volume_name}/{scale_key}/{chunk_file}
    """
    logger.info(f"📦 Chunk 요청: {username}/{volume_name}/{scale_key}/{chunk_file}")

    user_path = os.path.join(DATA_ROOT, username)
    volume_path = os.path.join(user_path, volume_name)
    chunk_path = os.path.join(volume_path, scale_key, chunk_file)

    if os.path.exists(chunk_path):
        logger.info(f"  ✅ Chunk 발견: {chunk_path}")
        return StarletteFileResponse(chunk_path)

    logger.error(f"  ❌ Chunk 없음: {chunk_path}")
    raise FastAPIHTTPException(
        status_code=404,
        detail=f"Chunk file not found: {username}/{volume_name}/{scale_key}/{chunk_file}"
    )


# 디버깅용: 사용 가능한 모든 볼륨 목록 조회
@app.get("/api/volumes/list")
async def list_all_volumes():
    """
    모든 사용자의 볼륨 목록 조회 (디버깅용)
    """
    volumes = {}

    if os.path.exists(DATA_ROOT):
        for username in os.listdir(DATA_ROOT):
            user_path = os.path.join(DATA_ROOT, username)
            if os.path.isdir(user_path):
                user_volumes = []
                for volume_name in os.listdir(user_path):
                    volume_path = os.path.join(user_path, volume_name)
                    if os.path.isdir(volume_path):
                        info_path = os.path.join(volume_path, "info")
                        has_info = os.path.exists(info_path)

                        # 스케일 디렉터리 확인
                        scales = []
                        for item in os.listdir(volume_path):
                            item_path = os.path.join(volume_path, item)
                            if os.path.isdir(item_path) and item != "temp":
                                scales.append(item)

                        user_volumes.append({
                            "name": volume_name,
                            "path": f"/uploads/{username}/{volume_name}",
                            "has_info": has_info,
                            "scales": scales,
                            "neuroglancer_url": f"precomputed://http://localhost:8000/uploads/{username}/{volume_name}"
                        })

                if user_volumes:
                    volumes[username] = user_volumes

    return {
        "data_root": DATA_ROOT,
        "total_users": len(volumes),
        "volumes": volumes
    }


# 미들웨어: 요청/응답 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청/응답을 로깅"""
    start_time = time.time()

    # 요청 로깅
    client_ip = request.client.host if request.client else "unknown"
    logger.log_request(request.method, request.url.path, client_ip)

    # 요청 처리
    response = await call_next(request)

    # 응답 로깅
    duration_ms = (time.time() - start_time) * 1000
    logger.log_response(request.method, request.url.path, response.status_code, duration_ms)

    return response


# 루트 경로에서 index.html 제공
@app.get("/")
def read_root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Welcome to Neuroglancer 대용량 뷰어 시스템"}


# 서버 시작 이벤트
@app.on_event("startup")
async def startup_event():
    # 데이터베이스 초기화 (테이블 생성 및 마이그레이션)
    init_database()

    logger.log_header("Neuroglancer 대용량 뷰어 시스템 시작")
    logger.info(f"데이터 루트: {DATA_ROOT}")
    logger.info(f"정적 파일: {STATIC_DIR}")
    logger.info(f"로그 디렉터리: {BASE_DIR / 'logs'}")
    logger.info(f"서버 주소: http://localhost:8000")
    logger.info(f"API 문서: http://localhost:8000/docs")
    logger.info(f"📁 사용자별 폴더 구조: /uploads/{{username}}/{{volume_name}}")
    logger.log_separator()

    print("=" * 60)
    print("🚀 Neuroglancer 대용량 뷰어 시스템 시작")
    print(f"📍 데이터 루트: {DATA_ROOT}")
    print(f"📁 정적 파일: {STATIC_DIR}")
    print(f"📝 로그 디렉터리: {BASE_DIR / 'logs'}")
    print(f"🌐 서버 주소: http://localhost:8000")
    print(f"📚 API 문서: http://localhost:8000/docs")
    print(f"👥 사용자별 폴더: /uploads/{{username}}/{{volume}}")
    print(f"🔍 볼륨 목록: http://localhost:8000/api/volumes/list")
    print("=" * 60)


# 서버 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    logger.log_header("서버 종료")
    logger.info("정상 종료")
    logger.log_separator()

    print("\n" + "=" * 60)
    print("🛑 서버 종료 중...")
    print("=" * 60)


# 직접 실행 시 uvicorn 서버 시작
if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("🚀 FastAPI 개발 서버 시작...")
    print(f"📍 서버 주소: http://localhost:8000")
    print(f"📁 데이터 디렉터리: {DATA_ROOT}")
    print(f"👥 사용자별 폴더 구조: /uploads/{{username}}/{{volume}}")
    print(f"📚 API 문서: http://localhost:8000/docs")
    print(f"🔍 볼륨 목록: http://localhost:8000/api/volumes/list")
    print("\n서버 중지하려면 Ctrl+C를 누르세요.")
    print("=" * 60 + "\n")

    uvicorn.run(
        "app.Services.main:app",
        host="localhost",
        port=8000,
        reload=True
    )