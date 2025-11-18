# app/Services/main.py

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.api.v1.endpoints import user as user_router_v1
from app.api.v1.endpoints import Auth, neuroglancer, memory, logs
from app.utils.json_logger import json_logger
import os
import time

# 데이터베이스 자동 초기화
from app.database.init_db import init_database

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Neuroglancer 대용량 뷰어 시스템",
    version="2.0.0",
    description="이미지 업로드 및 Neuroglancer 뷰어 통합 시스템"
)

# CORS 설정
from fastapi.middleware.cors import CORSMiddleware

origins = [
    # ... 기존 항목 ...
    "http://localhost:8080",      # 👈 로컬 Neuroglancer 포트 추가
    "http://127.0.0.1:8080"       # 👈 127.0.0.1도 함께 추가하는 것이 좋습니다.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
BUILD_DIR = STATIC_DIR / "build"

# 데이터 디렉터리 설정
DATA_ROOT = os.environ.get("DATA_DIR", str(BASE_DIR / "uploads"))
os.makedirs(DATA_ROOT, exist_ok=True)

# 정적 파일 마운트 (React 빌드 결과물)
if (BUILD_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BUILD_DIR / "static")), name="static")
    json_logger.log(
        username="system",
        log_level="INFO",
        message=f"React 빌드 결과물 마운트됨: {BUILD_DIR / 'static'}",
        logger_name="server.mount",
        service="fastapi"
    )
else:
    json_logger.log(
        username="system",
        log_level="WARNING",
        message=f"React 빌드 결과물이 없습니다: {BUILD_DIR}",
        logger_name="server.mount",
        service="fastapi"
    )

# uploads 디렉터리 마운트
if os.path.exists(DATA_ROOT):
    app.mount("/uploads", StaticFiles(directory=DATA_ROOT), name="uploads")
    json_logger.log(
        username="system",
        log_level="INFO",
        message=f"uploads 디렉터리 마운트됨: {DATA_ROOT}",
        logger_name="server.mount",
        service="fastapi",
        additional_info={"structure": "/uploads/{username}/{volume_name}"}
    )

# 라우터 등록
app.include_router(user_router_v1.router, prefix="/v1")
app.include_router(Auth.router, prefix="/v1")
app.include_router(neuroglancer.router, prefix="/api", tags=["Neuroglancer"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(logs.router, prefix="/api/v1", tags=["Logs"])

# 볼륨 직접 접근을 위한 동적 라우팅
from fastapi import HTTPException as FastAPIHTTPException
from starlette.responses import FileResponse as StarletteFileResponse, JSONResponse


@app.get("/uploads/{username}/{volume_name}/info")
async def get_volume_info(username: str, volume_name: str):
    """사용자별 볼륨 info 파일 접근"""
    json_logger.log(
        username="system",
        log_level="INFO",
        message=f"Volume info 요청: {username}/{volume_name}",
        logger_name="volume.info",
        service="neuroglancer",
        additional_info={"username": username, "volume_name": volume_name}
    )

    user_path = os.path.join(DATA_ROOT, username)
    volume_path = os.path.join(user_path, volume_name)
    info_path = os.path.join(volume_path, "info")

    if os.path.exists(info_path):
        json_logger.log(
            username=username,
            log_level="INFO",
            message="Volume info 제공 성공",
            logger_name="volume.info",
            service="neuroglancer",
            additional_info={"volume_name": volume_name, "info_path": info_path}
        )
        return StarletteFileResponse(info_path, media_type="application/json")

    # Info 파일이 없는 경우
    json_logger.log(
        username=username,
        log_level="ERROR",
        message="Volume info 파일 없음",
        logger_name="volume.info",
        service="neuroglancer",
        additional_info={"volume_name": volume_name, "info_path": info_path}
    )

    # 사용 가능한 볼륨 목록 수집
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
    """사용자별 볼륨 청크 파일 접근"""
    user_path = os.path.join(DATA_ROOT, username)
    volume_path = os.path.join(user_path, volume_name)
    chunk_path = os.path.join(volume_path, scale_key, chunk_file)

    if os.path.exists(chunk_path):
        # DEBUG 레벨로 로깅 (청크 요청이 매우 많기 때문)
        json_logger.log(
            username=username,
            log_level="DEBUG",
            message="Chunk 제공 성공",
            logger_name="volume.chunk",
            service="neuroglancer",
            additional_info={
                "volume_name": volume_name,
                "scale_key": scale_key,
                "chunk_file": chunk_file
            }
        )
        return StarletteFileResponse(chunk_path)

    # 청크 파일이 없는 경우
    json_logger.log(
        username=username,
        log_level="ERROR",
        message="Chunk 파일 없음",
        logger_name="volume.chunk",
        service="neuroglancer",
        additional_info={
            "volume_name": volume_name,
            "scale_key": scale_key,
            "chunk_file": chunk_file,
            "chunk_path": chunk_path
        }
    )

    raise FastAPIHTTPException(
        status_code=404,
        detail=f"Chunk file not found: {username}/{volume_name}/{scale_key}/{chunk_file}"
    )


@app.get("/api/volumes/list")
async def list_all_volumes():
    """모든 사용자의 볼륨 목록 조회 (디버깅용)"""
    json_logger.log(
        username="system",
        log_level="INFO",
        message="전체 볼륨 목록 조회",
        logger_name="volume.list",
        service="api"
    )

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
    client_ip = request.client.host if request.client else "unknown"

    # 요청 처리
    response = await call_next(request)

    # 응답 로깅
    duration_ms = (time.time() - start_time) * 1000

    # 로그 API 자체는 제외 (무한 루프 방지)
    if not request.url.path.startswith("/api/v1/logs"):
        # 로그 레벨 결정
        if response.status_code >= 500:
            log_level = "ERROR"
        elif response.status_code >= 400:
            log_level = "WARNING"
        else:
            log_level = "INFO"

        json_logger.log(
            username="system",
            log_level=log_level,
            message=f"{request.method} {request.url.path} - {response.status_code}",
            logger_name="http.middleware",
            service="fastapi",
            additional_info={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2)
            }
        )

    return response


# React Router 지원
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """React Router를 지원하기 위해 모든 경로에서 index.html을 반환"""
    # API 경로는 제외
    if full_path.startswith("api/") or full_path.startswith("v1/") or full_path.startswith("uploads/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")

    # React 빌드 결과물의 index.html 제공
    index_path = BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    # 빌드 결과물이 없으면 안내 메시지
    return {
        "message": "React 빌드 결과물이 없습니다.",
        "instruction": "'cd static && npm install && npm run build'를 실행하세요.",
        "build_dir": str(BUILD_DIR)
    }


# 서버 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    # 데이터베이스 초기화
    init_database()

    # 서버 시작 로깅
    json_logger.log(
        username="system",
        log_level="INFO",
        message="서버 시작",
        logger_name="server.startup",
        service="fastapi",
        additional_info={
            "data_root": DATA_ROOT,
            "static_dir": str(STATIC_DIR),
            "build_dir": str(BUILD_DIR),
            "server_url": "http://localhost:8000",
            "version": "2.0.0"
        }
    )

    # 콘솔 출력
    print("=" * 60)
    print("🚀 Neuroglancer 대용량 뷰어 시스템 시작")
    print(f"📍 데이터 루트: {DATA_ROOT}")
    print(f"📁 정적 파일: {STATIC_DIR}")
    print(f"⚙️ React 빌드: {BUILD_DIR}")
    if (BUILD_DIR / "index.html").exists():
        print("   ✅ 빌드 결과물 발견")
    else:
        print("   ⚠️ 빌드 필요: 'cd static && npm run build'")
    print(f"📝 로그: logs/YYYY/MM/DD.txt")
    print(f"🌐 서버: http://localhost:8000")
    print(f"📚 API 문서: http://localhost:8000/docs")
    print(f"👥 사용자별 폴더: /uploads/{{username}}/{{volume}}")
    print(f"🔍 볼륨 목록: http://localhost:8000/api/volumes/list")
    print(f"📊 로그 API: http://localhost:8000/api/v1/logs/dates")
    print("=" * 60)


# 서버 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    json_logger.log(
        username="system",
        log_level="INFO",
        message="서버 종료",
        logger_name="server.shutdown",
        service="fastapi"
    )

    print("\n" + "=" * 60)
    print("🛑 서버 종료")
    print("=" * 60)


# 직접 실행 시
if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("🚀 FastAPI 개발 서버 시작...")
    print(f"📍 서버: http://localhost:8000")
    print(f"📁 데이터: {DATA_ROOT}")
    print(f"⚙️ React: {BUILD_DIR}")
    if (BUILD_DIR / "index.html").exists():
        print("   ✅ 빌드 완료")
    else:
        print("   ⚠️ 빌드 필요")
    print(f"👥 구조: /uploads/{{username}}/{{volume}}")
    print(f"📚 문서: http://localhost:8000/docs")
    print(f"📊 로그: logs/YYYY/MM/DD.txt")
    print("\n서버 중지: Ctrl+C")
    print("=" * 60 + "\n")

    uvicorn.run(
        "app.Services.main:app",
        host="localhost",
        port=8000,
        reload=True
    )