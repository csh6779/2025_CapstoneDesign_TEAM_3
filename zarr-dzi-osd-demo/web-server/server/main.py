# /templates/main.py
# 사용자가 업로드한 대용량 이미지를 서버에 저장
# .zarr 형식과 DZI 형식으로 변환
# 클라이언트가 요청하는 타일 단위 이미지 조각을 HTTP로 제공

from __future__ import annotations
from pathlib import Path
import io
import os
import re
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from util_zarr import read_tile_from_zarr, open_zarr_array, lmax, ingest_to_zarr, create_dzi_from_image

BASE = Path(__file__).parent
DATA = Path("/app/data")  # Docker 컨테이너 내부 경로
ZARR_DIR = DATA / "zarr"
DZI_DIR = DATA / "dzi"
UPLOADS_DIR = DATA / "uploads" / "original"
CACHE_DIR = Path("/app/cache")  # Docker 컨테이너 내부 경로
for d in (ZARR_DIR, DZI_DIR, UPLOADS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OSD + Zarr + FastAPI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(BASE / "templates")), name="static")
# DZI 정적 제공 (사전 생성된 파일)
if DZI_DIR.exists():
    app.mount("/dzi-static", StaticFiles(directory=str(DZI_DIR)), name="dzi-static")

jinja_env = Environment(
    loader=FileSystemLoader(str(BASE / "templates")),
    autoescape=select_autoescape(['html'])
)


@app.get("/", response_class=HTMLResponse)
async def index():
    tmpl = jinja_env.get_template("index.html")
    return tmpl.render()


# ------------------- 업로드 API -------------------
ALLOWED_EXT = {'.tif', '.tiff', '.png', '.bmp', '.jpg', '.jpeg'} 


def _safe_id(name: str) -> str:
    name = os.path.splitext(name)[0]  # (파일명, 확장자)
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", name) # (정규식, 치환값, 대상문자열) --> 경로에 안전하게 쓸 수 있는 ID를 만듬


@app.post("/upload")
async def upload_image(  # 비동기 함수 
    file: UploadFile = File(...),
    image_id: str | None = Form(None),
    ingest: bool = Form(True), 
    create_dzi: bool = Form(True),  # DZI 생성 옵션 추가
):
    ext = os.path.splitext(file.filename)[1].lower() # [1] 확장자만 가져옴, 소문자화
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, detail=f"Unsupported extension: {ext}") # FastAPI 전용 예외. 확장자 허용 목록에 없으면 HTTP 상태코드(415), 업로드 거부 응답
    if not image_id:  # 이미지 ID , None 또는 빈 문자열이면 실행
        image_id = _safe_id(file.filename)   # 클라이언트가 ID를 안 줬으면, 파일명에서 추출
    image_id = _safe_id(image_id)

    dest = UPLOADS_DIR / f"{image_id}{ext}"   # pathlib.Path의 / 연산자 오버로딩 (연산자의 의미를 재정의)
    with open(dest, 'wb') as f:  # wb = write + bianry -> 글자x, 이미지, 동영상, 압축파일 저장
        shutil.copyfileobj(file.file, f, length=16 * 1024 * 1024) # 지정 버퍼 크기로 파일 복사

    # 파일 크기 확인 (2GB = 2 *1024 * 1024 * 1024 bytes)
    file_size = dest.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    
    result = {
        "image_id": image_id,
        "saved": str(dest.relative_to(DATA)),
        "file_size_mb": round(file_size_mb, 2),
    }

    if ingest: # 원본 이미지를 .zarr 형식으로 변환 ,ingest = 외부 데이터를 시스템 내부 형식으로 변환 후 저장
        zarr_out = ZARR_DIR / f"{image_id}.zarr"
        try:   # try/except = 예외처리
            meta = ingest_to_zarr(dest, zarr_out)  # ** = 딕셔너리 언패킹, meta 딕셔너리 내용을 복붙 후 합쳐 넣기
            result["zarr"] = {"path": str(zarr_out.relative_to(DATA)), **meta} # 성공시 메타데이터 기록
        except Exception as e:
            raise HTTPException(400, detail=f"Zarr ingest failed: {e}") # 에러 400 코드 응답
        
        # DZI 생성 (Zarr 성공 후) - 2GB 이상이면 건너뛰기
        if create_dzi and file_size < 2 *1024 * 1024 * 1024: # 크기가 2GB 미만일 시 DZI 생성
            try: 
                dzi_out = DZI_DIR / image_id
                dzi_meta = create_dzi_from_image(dest, dzi_out)
                result["dzi"] = {
                    "path": str(dzi_out.relative_to(DATA)),
                    **dzi_meta
                }
            except Exception as e:
                # DZI 생성 실패는 경고로 처리 (Zarr은 성공했으므로)
                result["dzi_warning"] = f"DZI creation failed: {e}"
        elif create_dzi and file_size >=  2 * 1024 * 1024 * 1024:  # elif는 분기, 분기 = 조건에 따라 실행 흐름이 달라짐
            result["dzi_skipped"] = f"DZI creation skipped: file size ({file_size_mb:.1f}MB) exceeds 2GB limit"

    return JSONResponse(result)  #딕셔너리를 JSON으로 변환 (업로드 / 변환 과정 요약)


# ------------------- Zarr 기반 커스텀 타일 API -------------------
@app.get("/zarr/{image_id}/meta")
async def zarr_meta(image_id: str):
    store_dir = ZARR_DIR / f"{image_id}.zarr"
    if not store_dir.exists():
        raise HTTPException(404, detail="Zarr store not found")
    arr, W, H, C = open_zarr_array(store_dir)
    LMAX = lmax(W, H)
    return {
        "width": W,
        "height": H,
        "channels": C,
        "tileSize": 512,
        "tileOverlap": 1,  # 1픽셀 오버랩으로 타일 간 경계 부드럽게
        "minLevel": 0,
        "maxLevel": LMAX,
    }


@app.get("/zarr/{image_id}/tile/{level}/{x}/{y}.jpg")  #경로에 변수들 바인딩 (level, x, y)
async def zarr_tile(image_id: str, level: int, x: int, y: int):
    store_dir = ZARR_DIR / f"{image_id}.zarr"
    if not store_dir.exists():   # zarr 저장소 확인
        raise HTTPException(404, detail="Zarr store not found")

    # 파일 캐시 경로
    tile_path = CACHE_DIR / image_id / str(level)
    tile_path.mkdir(parents=True, exist_ok=True) # 상위 폴더까지 생성 , 있어도 예외 x
    tile_file = tile_path / f"{x}_{y}.jpg"
    if tile_file.exists(): 
        return FileResponse(str(tile_file), media_type="image/jpeg")  # 캐시된 타일 반환

    try:
        im = read_tile_from_zarr(store_dir, level, x, y, tile_size=512)  # .zarr 저장소에서 특정 좌표의 타일을 읽음
    except Exception as e:
        raise HTTPException(400, detail=str(e))

    buf = io.BytesIO()
    im.convert('RGB').save(buf, format='JPEG', quality=85)   #BytesIO에 JPEG로 저장
    data = buf.getvalue()   

    # 캐시에 저장
    with open(tile_file, 'wb') as f:
        f.write(data)

    return Response(content=data, media_type="image/jpeg")


# ------------------- DZI 동적/정적 제공 -------------------
@app.get("/dzi/{image_id}.dzi")
async def dzi_descriptor(image_id: str):
    # 정적 파일 우선
    static_dzi = DZI_DIR / f"{image_id}.dzi"  
    if static_dzi.exists():
        return FileResponse(str(static_dzi), media_type="application/xml")  # 서버에 변환된 정적 DZI 타일이 미리 있다면 그대로 반환

    # 정적이 없으면 Zarr 메타로 가짜 DZI XML 생성 (OSD 호환)
    store_dir = ZARR_DIR / f"{image_id}.zarr"
    if not store_dir.exists():
        raise HTTPException(404, detail="Not found: DZI or Zarr")

    arr, W, H, _ = open_zarr_array(store_dir)
    #DZI XML 문자열 직접 만듦
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>   
<Image TileSize="512" Overlap="1" Format="jpg" xmlns="http://schemas.microsoft.com/deepzoom/2008">
  <Size Width="{W}" Height="{H}"/>
</Image>'''
    return Response(content=xml, media_type="application/xml")


@app.get("/dzi/{image_id}_files/{level}/{col}_{row}.jpg")
async def dzi_tile(image_id: str, level: int, col: int, row: int):
    # 정적 타일이 있으면 제공
    static_tile = DZI_DIR / f"{image_id}_files" / str(level) / f"{col}_{row}.jpg"
    if static_tile.exists():
        return FileResponse(str(static_tile), media_type="image/jpeg")

    # 없으면 Zarr에서 동적 생성 (DZI 좌표와 동일 로직)
    store_dir = ZARR_DIR / f"{image_id}.zarr"
    if not store_dir.exists():
        raise HTTPException(404, detail="Not found: DZI tile or Zarr store")

    # DZI는 level이 0..LMAX 기준
    try:   # 타일 추출
        im = read_tile_from_zarr(store_dir, level, col, row, tile_size=512)   #read_title_from_zarr 호출 시 좌표계(level,col,row) 사용
    except Exception as e:
        raise HTTPException(400, detail=str(e))

    buf = io.BytesIO()
    im.convert('RGB').save(buf, format='JPEG', quality=85) # .save(...) JPEG 압축 후 버퍼에 저장 
    return Response(content=buf.getvalue(), media_type="image/jpeg")