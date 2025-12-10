# main.py - [로컬/서버 선택 기능]
import os
import shutil
from pathlib import Path
import json
from urllib.parse import quote
from typing import List, Optional

from fastapi import Form, FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import numpy as np
from PIL import Image, ImageFile
import warnings

# Pillow의 안전장치 해제/완화 (대용량 이미지 허용)
Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter('ignore', Image.DecompressionBombWarning)
ImageFile.LOAD_TRUNCATED_IMAGES = True

# 로컬 모듈
from precomputed_writer import convert_image_file_to_precomputed, convert_raw_to_precomputed
from memory_management import MemoryManager, MemoryConfig
from output_path_manager import OutputPathManager

# FastAPI 앱 초기화
app = FastAPI(title="Neuroglancer Server - Custom Output Path")

# =============================================================================
# 디렉터리 설정 (yml 환경 변수에서 읽기)
# =============================================================================
DATA_ROOT = os.environ.get("DATA_DIR", "/app/data/precomputed")
UPLOAD_DIR = os.path.join(DATA_ROOT, "temp")
CHUNK_SIZE = 512

# [⭐️ 추가] yml에서 정의한 서버/로컬 저장 경로
SERVER_SAVE_PATH = os.environ.get("SERVER_SAVE_PATH", DATA_ROOT)
LOCAL_SAVE_PATH = os.environ.get("LOCAL_SAVE_PATH", os.path.join(DATA_ROOT, "local_storage"))

# 디렉터리 생성
os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SERVER_SAVE_PATH, exist_ok=True)  # 서버 경로 생성
os.makedirs(LOCAL_SAVE_PATH, exist_ok=True)  # 로컬 경로 생성 (컨테이너 내부)

print(f"데이터 루트 (서빙 기준): {DATA_ROOT}")
print(f"업로드 디렉터리: {UPLOAD_DIR}")
print(f"서버 저장 경로: {SERVER_SAVE_PATH}")
print(f"로컬 저장 경로: {LOCAL_SAVE_PATH} (-> C:\\precomputed)")
# =============================================================================

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://neuroglancer-demo.appspot.com",  # Neuroglancer 공식
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"  # 개발용 (프로덕션에서는 제거)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # 🔥 중요!
)

# 정적 파일 서빙
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# precomp 디렉터리 마운트 (DATA_ROOT)
# 이 마운트 하나로 /app/data/precomputed (서버)와
# /app/data/precomputed/local_storage (로컬) 모두 서빙 가능
if os.path.exists(DATA_ROOT):
    app.mount("/precomp", StaticFiles(directory=DATA_ROOT), name="precomp")


@app.get("/", response_class=FileResponse)
async def get_root_index_html():
    static_file_path = "/app/static/index.html"
    if not os.path.exists(static_file_path):
        raise HTTPException(status_code=404, detail="index.html 파일을 찾을 수 없습니다.")
    return FileResponse(static_file_path)


# OutputPathManager는 이제 사용하지 않으므로 초기화 코드 제거
# (또는 OutputPathManager 자체를 수정해야 하지만, 단순화를 위해 이 방식 사용)

# 메모리 관리자 초기화 (기존과 동일)
memory_config = MemoryConfig(
    max_image_size_mb=500,
    chunk_size=CHUNK_SIZE,
    cache_max_size_mb=200,
    memory_cleanup_threshold=0.8
)
memory_manager = MemoryManager(memory_config)


def validate_image_file(filename: str) -> bool:
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp'))


def cleanup_temp_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"임시 파일 삭제 실패: {e}")


def _base_url(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


def create_neuroglancer_url_with_auto_mode(
        base_url: str,
        volume_path: str,
        volume_name: str,
        image_width_nm: int = None,
        image_height_nm: int = None,
        target_scale_nm: int = 10
) -> str:
    """
    Neuroglancer URL 생성 - RGB 컬러 모드 + 10nm 줌 레벨
    """

    print(f"🔍 URL 디버깅:")
    print(f"  base_url: {base_url}")
    print(f"  volume_path: {volume_path}")
    print(f"  이미지 크기: {image_width_nm} x {image_height_nm} nm")


    cross_section_scale = 500  # 10nm 스케일용

    # 위치 계산
    if image_width_nm is not None and image_width_nm > 0:
        center_x = image_width_nm // 2
        center_y = (image_height_nm or image_width_nm) // 2
        position = [center_x, center_y, 0.5]

        print(f"  줌 레벨: {cross_section_scale} (고정)")
        print(f"  초기 위치: [{center_x}, {center_y}, 0.5]")
    else:
        position = [5000, 10000, 0.5]
        print(f"  기본 줌 레벨 및 위치 사용")

    # RGB shader
    rgb_shader = """
#uicontrol vec3 color color(default="white")
#uicontrol float brightness slider(min=-1, max=1, default=0)
#uicontrol float contrast slider(min=-3, max=3, default=0)
void main() {
  emitRGB(
    color * 
    vec3(
      toNormalized(getDataValue(0)),
      toNormalized(getDataValue(1)), 
      toNormalized(getDataValue(2))
    ) * 
    (1.0 + brightness) * 
    exp(contrast)
  );
}
    """.strip()

    # State 생성
    state = {
        "dimensions": {
            "x": [1e-9, "m"],
            "y": [1e-9, "m"],
            "z": [1e-9, "m"]
        },
        "layers": [{
            "type": "image",
            "source": f"precomputed://{base_url}{volume_path}",
            "name": volume_name,
            "shader": rgb_shader,
            "shaderControls": {
                "brightness": 0,
                "contrast": 0,
                "color": "#ffffff"
            },
            "visible": True
        }],
        "layout": "4panel",
        "crossSectionScale": cross_section_scale,  # 🔥 500 사용
        "projectionScale": 16384,
        "position": position,
        "navigation": {
            "pose": {
                "position": {
                    "voxelSize": [1, 1, 1]
                }
            },
            "zoomFactor": 8
        }
    }

    print(f"  crossSectionScale: {cross_section_scale}")
    print(f"  생성된 source: precomputed://{base_url}{volume_path}")

    import json
    from urllib.parse import quote

    state_json = json.dumps(state, separators=(',', ':'))
    encoded_state = quote(state_json)

    neuroglancer_url = f"https://neuroglancer-demo.appspot.com/#!{encoded_state}"

    return neuroglancer_url

# =============================================================================
# 이미지 업로드 및 변환 (저장 위치 선택)
# =============================================================================

@app.post("/api/upload")
async def upload_and_convert(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        save_location: str = Form("local"),  # 🔥 "local" or "server"
        volume_name: Optional[str] = Form(None),
        request: Request = None
):
    """
    이미지 파일 업로드 및 Precomputed 형식으로 변환

    Parameters:
    - file: 업로드할 이미지 파일
    - save_location: 저장 위치 ("local" 또는 "server")
    - volume_name: 볼륨 이름 (선택, 미지정 시 파일명 사용)
    """
    if not validate_image_file(file.filename):
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    safe_name = os.path.basename(file.filename)
    upload_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"📤 파일 저장 완료: {upload_path}")

        if not volume_name:
            volume_name = Path(safe_name).stem
        print(f"📦 볼륨 이름: {volume_name}")

        # 저장 위치 결정
        if save_location == "local":
            base_output_path = LOCAL_SAVE_PATH
            print(f"📂 저장 위치: 로컬 (C:\\precomputed)")
        else:
            base_output_path = SERVER_SAVE_PATH
            print(f"📂 저장 위치: 서버 (appdata)")

        final_output_path = os.path.join(base_output_path, volume_name)
        print(f"💾 최종 경로: {final_output_path}")

        os.makedirs(final_output_path, exist_ok=True)

        # 변환 시작
        print(f"🔄 Precomputed 형식으로 변환 시작...")
        chunk_count = convert_image_file_to_precomputed(
            upload_path,
            final_output_path,
            chunk_size=CHUNK_SIZE,
            encoding="raw"
        )
        print(f"✅ 변환 완료: {chunk_count}개 청크 생성")

        info_path = os.path.join(final_output_path, "info")
        with open(info_path, 'r', encoding="utf-8") as f:
            info = json.load(f)

        background_tasks.add_task(cleanup_temp_file, upload_path)

        # 🔥 이 2줄 추가!
        base = _base_url(request) if request else "http://localhost:8000"

        # 🔥 neuroglancer_path 계산 추가!
        try:
            rel_path = os.path.relpath(final_output_path, DATA_ROOT)
            neuroglancer_path = rel_path.replace("\\", "/")
        except ValueError:
            neuroglancer_path = volume_name

        # 🔥 이미지 크기 계산
        dimensions = info['scales'][0]['size']
        resolution = info['scales'][0].get('resolution', [1, 1, 1])
        width_nm = int(dimensions[0] * resolution[0])
        height_nm = int(dimensions[1] * resolution[1])

        # 🔥 여기서 딱 한 번만 URL 생성
        neuroglancer_url = create_neuroglancer_url_with_auto_mode(
            base_url=base,
            volume_path=f"/precomp/{neuroglancer_path}",
            volume_name=volume_name,
            image_width_nm=width_nm,
            image_height_nm=height_nm,
            target_scale_nm=10
        )

        return JSONResponse(content={
            "message": "이미지가 성공적으로 변환되었습니다.",
            "volume_name": volume_name,
            "output_path": final_output_path,
            "volume_path": f"/precomp/{neuroglancer_path}",
            "neuroglancer_url": neuroglancer_url,  # 🔥 변수 사용
            "dimensions": info['scales'][0]['size'],
            "num_channels": info['num_channels'],
            "chunk_size": CHUNK_SIZE,
            "total_chunks": chunk_count,
            "storage_info": {
                "save_location": save_location,
                "base_directory": base_output_path,
                "volume_directory": final_output_path,
            }
        })

    except Exception as e:
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except:
                pass
        import traceback
        error_msg = f"파일 처리 중 오류: {str(e)}"
        print(f"ERROR: {error_msg}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "upload_failed", "message": error_msg, "detail": str(e)}
        )

@app.post("/api/upload-raw")
async def upload_raw(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        width: int = Form(...),
        height: int = Form(...),
        channels: int = Form(3),
        dtype: str = Form("uint8"),
        save_location: str = Form("local"),
        volume_name: Optional[str] = Form(None),
        request: Request = None
):
    safe_name = os.path.basename(file.filename)
    upload_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"📥 파일 저장 완료: {upload_path}")

        if not volume_name:
            volume_name = Path(safe_name).stem

        # 저장 위치 결정
        if save_location == "local":
            base_output_path = LOCAL_SAVE_PATH
        else:
            base_output_path = SERVER_SAVE_PATH

        final_output_path = os.path.join(base_output_path, volume_name)
        print(f"💾 최종 경로: {final_output_path}")

        os.makedirs(final_output_path, exist_ok=True)

        print(f"🔄 Precomputed 형식으로 변환 시작...")
        chunk_count = convert_raw_to_precomputed(
            upload_path, final_output_path, width, height, channels, dtype, CHUNK_SIZE, "raw"
        )
        print(f"✅ 변환 완료: {chunk_count}개 청크 생성")

        background_tasks.add_task(cleanup_temp_file, upload_path)
        base = _base_url(request) if request else "http://localhost:8000"

        # Neuroglancer URL 생성
        try:
            rel_path = os.path.relpath(final_output_path, DATA_ROOT)
            neuroglancer_path = rel_path.replace("\\", "/")
        except ValueError:
            neuroglancer_path = volume_name

        return JSONResponse(content={
            "message": "RAW 파일이 성공적으로 변환되었습니다.",
            "volume_name": volume_name,
            "output_path": final_output_path,
            "volume_path": f"/precomp/{neuroglancer_path}",
            "neuroglancer_url": create_neuroglancer_url_with_auto_mode(
                base_url=base,
                volume_path=f"/precomp/{neuroglancer_path}",
                volume_name=volume_name
            ),
            "dimensions": [width, height, 1],
            "num_channels": channels,
            "chunk_size": CHUNK_SIZE,
            "total_chunks": chunk_count,
            "dtype": dtype,
            "storage_info": {
                "save_location": save_location,
                "base_directory": base_output_path,
                "volume_directory": final_output_path,
            }
        })
    except Exception as e:
        if os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except:
                pass
        import traceback
        error_msg = f"RAW 파일 처리 중 오류: {str(e)}"
        print(f"ERROR: {error_msg}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "raw_upload_failed", "message": error_msg, "detail": str(e)}
        )

@app.get("/api/volumes")
def list_volumes(request: Request):
    """변환된 볼륨 목록"""
    try:
        volumes = []
        for root, dirs, files in os.walk(DATA_ROOT):
            if "info" in files:
                # 'temp' 폴더 및 하위 폴더 제외
                if "temp" in root.split(os.path.sep):
                    continue

                volume_name = os.path.basename(root)
                volume_path = root

                # URL 계산
                rel_path = os.path.relpath(volume_path, DATA_ROOT)
                neuroglancer_path = rel_path.replace("\\", "/")

                with open(os.path.join(root, "info"), 'r', encoding="utf-8") as f:
                    info = json.load(f)

                volumes.append({
                    "name": volume_name,
                    "path": f"/precomp/{neuroglancer_path}",
                    "info_url": f"/precomp/{neuroglancer_path}/info",
                    "neuroglancer_url": create_neuroglancer_url_with_auto_mode(
                        base_url=_base_url(request),
                        volume_path=f"/precomp/{neuroglancer_path}",
                        volume_name=volume_name
                    ),
                    "dimensions": info['scales'][0]['size'] if 'scales' in info else None,
                    "chunk_size": info['scales'][0]['chunk_sizes'][0] if 'scales' in info else None,
                    "local_path": volume_path  # 컨테이너 내부 경로
                })
        return JSONResponse(content={"volumes": volumes, "count": len(volumes)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"볼륨 목록 조회 실패: {str(e)}")


@app.delete("/api/volumes/{volume_name}")
def delete_volume(volume_name: str, background_tasks: BackgroundTasks):
    try:
        volume_path_to_delete = None
        for root, dirs, files in os.walk(DATA_ROOT):
            if os.path.basename(root) == volume_name and "info" in files:
                volume_path_to_delete = root
                break

        if not volume_path_to_delete:
            raise HTTPException(status_code=404, detail="볼륨을 찾을 수 없습니다.")

        background_tasks.add_task(shutil.rmtree, volume_path_to_delete)
        background_tasks.add_task(memory_manager.force_cleanup)
        return JSONResponse(content={"message": f"볼륨 '{volume_name}'이 삭제 대기열에 추가되었습니다."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"볼륨 삭제 중 오류가 발생했습니다: {str(e)}")


@app.get("/api/memory-status")
def get_memory_status():
    if not memory_manager:
        raise HTTPException(status_code=500, detail="MemoryManager가 초기화되지 않았습니다.")
    try:
        return memory_manager.get_status_json()
    except Exception as e:
        print(f"!!! /api/memory-status API 오류: {e} !!!")
        return {
            "memory": {"process_mb": 0, "system_percent": 0},
            "cache": {"cache_size_mb": 0, "hit_rate": 0},
            "config": {"cache_max_size_mb": memory_config.cache_max_size_mb}
        }


@app.post("/api/memory-cleanup")
def cleanup_memory_api():
    if not memory_manager:
        raise HTTPException(status_code=500, detail="MemoryManager가 초기화되지 않았습니다.")
    freed_mb = memory_manager.force_cleanup()
    return JSONResponse(
        content={"message": "Memory cleanup successful", "freed_mb": freed_mb}
    )


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🚀 Neuroglancer 서버 시작 (로컬/서버 선택)")
    print(f"📍 데이터 루트 (서빙 기준): {DATA_ROOT}")
    print(f"📤 업로드 디렉터리: {UPLOAD_DIR}")
    print(f"💾 서버 저장 경로: {SERVER_SAVE_PATH}")
    print(f"💾 로컬 저장 경로: {LOCAL_SAVE_PATH}")
    print(f"🔧 청크 크기: {CHUNK_SIZE}x{CHUNK_SIZE}")
    print("=" * 60)
    yield
    print("\n서버 종료 중...")
    memory_manager.force_cleanup()
    print("메모리 정리 완료")


app.router.lifespan_context = lifespan


@app.get("/debug")
def debug_info():
    return JSONResponse(content={
        "data_root": DATA_ROOT,
        "upload_dir": UPLOAD_DIR,
        "server_save_path": SERVER_SAVE_PATH,
        "local_save_path": LOCAL_SAVE_PATH,
        "chunk_size": CHUNK_SIZE
    })

def run_server():
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 FastAPI 서버 시작...")
    print(f"📍 서버 주소: http://localhost:8000")
    print(f"📁 데이터 디렉터리: {DATA_ROOT}")
    print(f"📚 API 문서: http://localhost:8000/docs")
    print(f"🔍 디버그 정보: http://localhost:8000/debug")
    print("=" * 60 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")


if __name__ == "__main__":
    run_server()