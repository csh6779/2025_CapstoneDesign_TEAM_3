# main.py - 간소화된 메인 애플리케이션
import os
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 메모리 관리 모듈 임포트
from memory_management import MemoryManager, MemoryConfig

# FastAPI 앱 초기화
app = FastAPI(title="Neuroglancer PNG Demo")

# 디렉터리 설정
DATA_ROOT = os.environ.get("DATA_DIR", "/app/data/precomputed")
UPLOAD_DIR = "/app/uploads"
os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
app.mount("/precomp", StaticFiles(directory=DATA_ROOT), name="precomp")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 메모리 관리자 초기화
memory_config = MemoryConfig(
    max_image_size_mb=500,
    chunk_size=512,
    cache_max_size_mb=200,
    memory_cleanup_threshold=0.8
)
memory_manager = MemoryManager(memory_config)


# =============================================================================
# API 엔드포인트
# =============================================================================

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("static/index.html")


@app.get("/api/memory-status")
def get_memory_status():
    """메모리 상태 조회"""
    return JSONResponse(content=memory_manager.get_overall_stats())


@app.post("/api/memory-cleanup")
def force_memory_cleanup():
    """강제 메모리 정리"""
    result = memory_manager.force_cleanup()
    return JSONResponse(content={
        "message": "메모리 정리 완료",
        **result
    })


@app.post("/api/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """파일 업로드 및 자동 청크 변환"""

    # 파일 형식 검증
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    # 임시 파일 저장
    upload_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 볼륨 경로 설정
        volume_name = Path(file.filename).stem
        volume_path = os.path.join(DATA_ROOT, volume_name)

        # 스트리밍 처리
        chunk_count = 0
        final_progress = 0
        errors = []

        async for result in memory_manager.processor.process_image_streaming(upload_path, volume_path):
            if result.success:
                chunk_count += 1
                final_progress = result.progress
            else:
                errors.append(result.error_message)

        # 백그라운드에서 임시 파일 정리
        background_tasks.add_task(cleanup_temp_file, upload_path)

        if errors:
            return JSONResponse(
                status_code=400,
                content={
                    "message": "처리 중 일부 오류 발생",
                    "errors": errors[:5],  # 최대 5개 오류만 표시
                    "chunks_processed": chunk_count
                }
            )

        return JSONResponse(content={
            "message": "파일이 성공적으로 처리되었습니다.",
            "volume_name": volume_name,
            "volume_path": f"/precomp/{volume_name}",
            "chunks_processed": chunk_count,
            "final_progress": final_progress,
            "memory_stats": memory_manager.get_overall_stats()
        })

    except Exception as e:
        # 오류 발생 시 정리
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=500, detail=f"처리 중 오류: {str(e)}")


async def cleanup_temp_file(file_path: str):
    """임시 파일 정리"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"임시 파일 정리 실패: {e}")


@app.get("/api/volumes")
def list_volumes():
    """볼륨 목록 조회"""
    volumes = []
    for item in os.listdir(DATA_ROOT):
        item_path = os.path.join(DATA_ROOT, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "info")):
            # 볼륨 크기 계산
            size_mb = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(item_path)
                for filename in filenames
            ) / (1024 * 1024)

            volumes.append({
                "name": item,
                "path": f"/precomp/{item}",
                "info_url": f"/precomp/{item}/info",
                "size_mb": round(size_mb, 2)
            })

    return JSONResponse(content={
        "volumes": volumes,
        "total_volumes": len(volumes),
        "memory_status": memory_manager.get_overall_stats()
    })


@app.delete("/api/volumes/{volume_name}")
def delete_volume(volume_name: str):
    """볼륨 삭제"""
    try:
        volume_path = os.path.join(DATA_ROOT, volume_name)
        if not os.path.exists(volume_path):
            raise HTTPException(status_code=404, detail="볼륨을 찾을 수 없습니다.")

        # 관련 캐시 정리
        memory_manager.cache.clear()

        shutil.rmtree(volume_path)

        # 메모리 정리
        cleanup_result = memory_manager.force_cleanup()

        return JSONResponse(content={
            "message": f"볼륨 '{volume_name}'이 삭제되었습니다.",
            "cleanup_result": cleanup_result
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"볼륨 삭제 중 오류: {str(e)}")


# =============================================================================
# 앱 생명주기 관리
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    print("메모리 최적화된 Neuroglancer 서버 시작")
    print(f"메모리 설정: {memory_config}")


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 정리"""
    memory_manager.shutdown()
    print("서버 종료 완료")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)