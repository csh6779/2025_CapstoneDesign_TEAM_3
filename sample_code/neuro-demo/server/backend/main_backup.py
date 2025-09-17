import os
import shutil
from pathlib import Path
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from PIL import Image
from cloudvolume import CloudVolume

app = FastAPI(title="Neuroglancer PNG Demo")

DATA_ROOT = os.environ.get("DATA_DIR", "/app/data/precomputed")
UPLOAD_DIR = "/app/uploads"
CHUNK_SIZE = 512

# CORS 미들웨어 추가
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

# precomputed 디렉터리를 /precomp/ 경로로 그대로 노출
app.mount("/precomp", StaticFiles(directory=DATA_ROOT), name="precomp")

# static (프론트엔드)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    # index.html 제공
    return FileResponse("static/index.html")

@app.get("/api/info")
def api_info():
    # info 파일 읽어서 그대로 반환
    info_path = os.path.join(DATA_ROOT, "info")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=f.read())
    return JSONResponse(content={"error": "info not found"}, status_code=404)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 및 자동 청크 변환"""
    try:
        # 파일 확장자 검사
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. PNG, JPG, TIFF만 지원합니다.")
        
        # 업로드된 파일 저장
        upload_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 이미지를 numpy 배열로 변환
        img = Image.open(upload_path)
        img_array = np.array(img)
        
        # 이미지 차원 확인 및 처리
        if len(img_array.shape) == 2:  # 그레이스케일
            img_array = np.expand_dims(img_array, axis=-1)
            num_channels = 1
        elif len(img_array.shape) == 3:  # 컬러
            num_channels = img_array.shape[2]
            # 4채널(RGBA)인 경우 3채널(RGB)로 변환
            if num_channels == 4:
                # RGBA를 RGB로 변환 (알파 채널 제거)
                img_array = img_array[:, :, :3]
                num_channels = 3
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 이미지 차원입니다.")
        
        # CloudVolume 생성 및 청크 변환
        volume_name = Path(file.filename).stem
        volume_path = os.path.join(DATA_ROOT, volume_name)
        
        # CloudVolume 설정 - 단일 해상도(level 0)로 생성
        info = CloudVolume.create_new_info(
            num_channels=min(num_channels, 3),  # 최대 3채널로 제한
            layer_type="image",
            data_type="uint8",  # 명시적으로 uint8로 설정
            encoding="png",
            resolution=[1, 1, 1],
            voxel_offset=[0, 0, 0],
            chunk_size=[CHUNK_SIZE, CHUNK_SIZE, 1],
            volume_size=[img_array.shape[1], img_array.shape[0], 1],  # width, height, depth
        )
        
        # 단일 해상도로 설정 (level 0)
        info['scales'] = [info['scales'][0]]  # 첫 번째 스케일만 유지
        info['scales'][0]['key'] = '0'  # level key를 '0'으로 설정
        
        # CloudVolume 생성
        vol = CloudVolume(f"precomputed://file://{volume_path}", info=info, compress=False, progress=False)
        vol.commit_info()
        
        # 이미지 데이터를 청크로 변환하여 저장
        # CloudVolume은 (x, y, z, c) 순서를 기대하므로 transpose 필요
        if num_channels == 1:
            # 그레이스케일: (H, W) -> (H, W, 1) -> (W, H, 1, 1)
            data = np.expand_dims(img_array, axis=-1)
            data = np.transpose(data, (1, 0, 2, 3))
        else:
            # 컬러: (H, W, C) -> (W, H, 1, C)
            data = np.expand_dims(img_array, axis=2)
            data = np.transpose(data, (1, 0, 2, 3))
        
        # 전체 이미지를 한 번에 쓰기 (CloudVolume이 자동으로 청크로 분할)
        vol[:, :, 0:1] = data
        
        # 업로드된 임시 파일 삭제
        os.remove(upload_path)
        
        return JSONResponse(content={
            "message": "파일이 성공적으로 업로드되고 청크로 변환되었습니다.",
            "volume_name": volume_name,
            "volume_path": f"/precomp/{volume_name}",
            "dimensions": [img_array.shape[1], img_array.shape[0], 1, num_channels],
            "chunk_size": CHUNK_SIZE
        })
        
    except Exception as e:
        # 에러 발생 시 임시 파일 정리
        if 'upload_path' in locals() and os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}")

@app.get("/api/volumes")
def list_volumes():
    """사용 가능한 볼륨 목록 반환"""
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
    """특정 볼륨의 상세 정보 반환"""
    try:
        volume_path = os.path.join(DATA_ROOT, volume_name)
        info_path = os.path.join(volume_path, "info")
        
        if not os.path.exists(info_path):
            raise HTTPException(status_code=404, detail="볼륨을 찾을 수 없습니다.")
        
        with open(info_path, "r", encoding="utf-8") as f:
            import json
            info = json.load(f)
            
        return JSONResponse(content={
            "volume_name": volume_name,
            "info": info,
            "volume_path": f"/precomp/{volume_name}"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"볼륨 정보 조회 중 오류가 발생했습니다: {str(e)}")

@app.delete("/api/volumes/{volume_name}")
def delete_volume(volume_name: str):
    """볼륨 삭제"""
    try:
        volume_path = os.path.join(DATA_ROOT, volume_name)
        if not os.path.exists(volume_path):
            raise HTTPException(status_code=404, detail="볼륨을 찾을 수 없습니다.")
        
        shutil.rmtree(volume_path)
        return JSONResponse(content={"message": f"볼륨 '{volume_name}'이 삭제되었습니다."})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"볼륨 삭제 중 오류가 발생했습니다: {str(e)}")
