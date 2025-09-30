import os
import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from PIL import Image
import tifffile as tiff
from cloudvolume import CloudVolume

# (선택) 매우 큰 PNG/JPG 허용
# Image.MAX_IMAGE_PIXELS = None

app = FastAPI(title="Neuroglancer PNG/TIFF Demo")

DATA_ROOT = os.environ.get("DATA_DIR", "/app/data/precomputed")
UPLOAD_DIR = "/app/uploads"
CHUNK_SIZE = 512

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉터리 생성
os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 정적 파일 마운트
app.mount("/precomp", StaticFiles(directory=DATA_ROOT), name="precomp")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("static/index.html")


# ================== 업로드/변환 ==================
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        ext = Path(file.filename).suffix.lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.tiff', '.tif'):
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. PNG, JPG, TIFF만 지원합니다.")

        upload_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        volume_name = Path(file.filename).stem
        volume_path = os.path.join(DATA_ROOT, volume_name)

        # ================= TIFF 처리 =================
        if ext in ('.tif', '.tiff'):
            mm = tiff.memmap(upload_path)  # (H,W) or (H,W,C)
            if mm.dtype != np.uint8:
                mm = mm.astype(np.uint8, copy=False)

            if mm.ndim == 2:
                H, W = mm.shape
                num_channels = 1
            elif mm.ndim == 3:
                H, W, C = mm.shape
                if C == 4:
                    C = 3
                num_channels = C
            else:
                raise HTTPException(status_code=400, detail=f"지원하지 않는 TIFF 차원: {mm.shape}")

            info = CloudVolume.create_new_info(
                num_channels=min(num_channels, 3),
                layer_type="image",
                data_type="uint8",
                encoding="png",  # PNG 청크 저장
                resolution=[1, 1, 1],
                voxel_offset=[0, 0, 0],
                chunk_size=[CHUNK_SIZE, CHUNK_SIZE, 1],
                volume_size=[W, H, 1],
            )
            info['scales'] = [info['scales'][0]]
            info['scales'][0]['key'] = '0'

            vol = CloudVolume(f"precomputed://file://{volume_path}", info=info,
                              compress=False, progress=False)
            vol.commit_info()

            # 블록 단위 변환
            for y0 in range(0, H, CHUNK_SIZE):
                y1 = min(H, y0 + CHUNK_SIZE)
                for x0 in range(0, W, CHUNK_SIZE):
                    x1 = min(W, x0 + CHUNK_SIZE)
                    block = np.asarray(mm[y0:y1, x0:x1])
                    if block.ndim == 2:
                        block = block[..., None]   # (th,tw) -> (th,tw,1)
                    elif block.shape[-1] == 4:
                        block = block[..., :3]     # RGBA -> RGB

                    blk = block[np.newaxis, :, :, :]     # (1,th,tw,C)
                    blk = np.transpose(blk, (2, 1, 0, 3))  # (tw,th,1,C)
                    vol[x0:x1, y0:y1, 0:1] = blk

            os.remove(upload_path)
            return JSONResponse(content={
                "message": "TIFF가 precomputed로 변환되었습니다.",
                "volume_name": volume_name,
                "volume_path": f"/precomp/{volume_name}",
                "dimensions": [W, H, 1, num_channels],
                "chunk_size": CHUNK_SIZE
            })

        # ================= PNG/JPG 처리 =================
        else:
            img = Image.open(upload_path)
            img_array = np.array(img)

            if img_array.ndim == 2:
                img_array = img_array[..., None]  # (H,W,1)
                num_channels = 1
            elif img_array.ndim == 3:
                num_channels = img_array.shape[2]
                if num_channels == 4:
                    img_array = img_array[:, :, :3]
                    num_channels = 3
            else:
                raise HTTPException(status_code=400, detail="지원하지 않는 이미지 차원입니다.")

            H, W = img_array.shape[0], img_array.shape[1]

            info = CloudVolume.create_new_info(
                num_channels=min(num_channels, 3),
                layer_type="image",
                data_type="uint8",
                encoding="png",
                resolution=[1, 1, 1],
                voxel_offset=[0, 0, 0],
                chunk_size=[CHUNK_SIZE, CHUNK_SIZE, 1],
                volume_size=[W, H, 1],
            )
            info['scales'] = [info['scales'][0]]
            info['scales'][0]['key'] = '0'

            vol = CloudVolume(f"precomputed://file://{volume_path}", info=info,
                              compress=False, progress=False)
            vol.commit_info()

            data = img_array[np.newaxis, :, :, :]      # (1,H,W,C)
            data = np.transpose(data, (2, 1, 0, 3))    # (W,H,1,C)
            vol[:, :, 0:1] = data

            os.remove(upload_path)
            return JSONResponse(content={
                "message": "파일이 성공적으로 업로드되고 청크로 변환되었습니다.",
                "volume_name": volume_name,
                "volume_path": f"/precomp/{volume_name}",
                "dimensions": [W, H, 1, num_channels],
                "chunk_size": CHUNK_SIZE
            })

    except Exception as e:
        if 'upload_path' in locals() and os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}")


# ================== 볼륨 관리 ==================
@app.get("/api/volumes")
def list_volumes():
    """DATA_ROOT 안의 볼륨 목록 조회"""
    volumes = []
    for item in os.listdir(DATA_ROOT):
        item_path = os.path.join(DATA_ROOT, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "info")):
            volumes.append({
                "name": item,
                "path": f"/precomp/{item}",
                "info_url": f"/precomp/{item}/info"
            })
    return JSONResponse(content={"volumes": volumes})


@app.get("/api/volumes/{volume_name}/info")
def get_volume_info(volume_name: str):
    """특정 볼륨 info.json 조회"""
    volume_path = os.path.join(DATA_ROOT, volume_name)
    info_path = os.path.join(volume_path, "info")
    if not os.path.exists(info_path):
        raise HTTPException(status_code=404, detail="볼륨을 찾을 수 없습니다.")
    import json
    with open(info_path, "r", encoding="utf-8") as f:
        info = json.load(f)
    return JSONResponse(content={
        "volume_name": volume_name,
        "info": info,
        "volume_path": f"/precomp/{volume_name}"
    })


@app.delete("/api/volumes/{volume_name}")
def delete_volume(volume_name: str):
    """특정 볼륨 삭제"""
    volume_path = os.path.join(DATA_ROOT, volume_name)
    if not os.path.exists(volume_path):
        raise HTTPException(status_code=404, detail="볼륨을 찾을 수 없습니다.")
    shutil.rmtree(volume_path)
    return JSONResponse(content={"message": f"볼륨 '{volume_name}'이 삭제되었습니다."})
