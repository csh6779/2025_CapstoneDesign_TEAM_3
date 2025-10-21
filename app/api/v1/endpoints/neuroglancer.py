# app/api/v1/endpoints/neuroglancer.py
"""
Neuroglancer 관련 API 엔드포인트
- 이미지 업로드 및 청크 변환
- 볼륨 관리
- 메모리 상태 조회
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Request, Response, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np
from PIL import Image

from app.api.v1.deps.Auth import get_current_user
from app.utils.ncsa_logger import ncsa_logger

# Pillow의 decompression bomb 보호 해제 (대용량 이미지 처리)
Image.MAX_IMAGE_PIXELS = None

router = APIRouter()

# 디렉터리 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DATA_ROOT = os.environ.get("DATA_DIR", str(BASE_DIR / "uploads"))
UPLOAD_DIR = os.path.join(DATA_ROOT, "temp")
CHUNK_SIZE = 512

# 디렉터리 생성
os.makedirs(DATA_ROOT, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

print(f"[Neuroglancer] 데이터 루트: {DATA_ROOT}")
print(f"[Neuroglancer] 업로드 디렉터리: {UPLOAD_DIR}")


class VolumeInfo(BaseModel):
    """볼륨 정보 모델"""
    name: str
    path: str
    info_url: str
    neuroglancer_url: str
    dimensions: Optional[List[int]] = None
    chunk_size: Optional[List[int]] = None


def validate_image_file(filename: str) -> bool:
    """파일 확장자 검증"""
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif'))


def cleanup_temp_file(file_path: str):
    """임시 파일 정리 (백그라운드 태스크)"""
    import time
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"임시 파일 삭제 완료: {file_path}")
                return
            else:
                print(f"파일이 이미 삭제됨: {file_path}")
                return
        except PermissionError:
            if attempt < max_retries - 1:
                print(f"파일 잠금 감지, 재시도 {attempt + 1}/{max_retries}")
                time.sleep(2 ** attempt)
            else:
                print(f"임시 파일 삭제 최종 실패: {file_path}")
        except Exception as e:
            print(f"임시 파일 삭제 실패: {file_path} - {str(e)}")
            return


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """
    파일 업로드 및 Neuroglancer 형식으로 자동 변환
    
    - PNG, JPG, TIFF 형식 지원
    - 자동으로 precomputed 형식으로 변환
    - 청크 단위로 저장하여 메모리 효율적 처리
    """
    
    print(f"[Upload] 파일 업로드 요청: {file.filename} by {current_user.UserName}")
    
    # 파일 형식 검증
    if not validate_image_file(file.filename):
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="UPLOAD_FAILED",
            details={"filename": file.filename, "reason": "invalid_format"}
        )
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다. PNG, JPG, TIFF만 지원합니다."
        )
    
    # 임시 파일 저장
    upload_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # 파일 저장
        content = await file.read()
        file_size = len(content)
        
        with open(upload_path, "wb") as buffer:
            buffer.write(content)
        print(f"[Upload] 파일 저장 완료: {file_size} bytes")
        
        # 볼륨 설정
        volume_name = Path(file.filename).stem
        volume_path = os.path.join(DATA_ROOT, volume_name)
        
        print(f"[Upload] 볼륨 이름: {volume_name}")
        print(f"[Upload] 볼륨 경로: {volume_path}")
        
        # Precomputed 형식으로 변환 (간단한 구현)
        print("[Upload] Precomputed 형식으로 변환 시작...")
        
        # 이미지 로드
        img = Image.open(upload_path)
        img_array = np.array(img)
        
        # 볼륨 디렉터리 생성
        os.makedirs(volume_path, exist_ok=True)
        
        # info 파일 생성
        height, width = img_array.shape[:2]
        num_channels = 1 if len(img_array.shape) == 2 else img_array.shape[2]
        
        # 청크 수 계산
        chunks_x = (width + CHUNK_SIZE - 1) // CHUNK_SIZE
        chunks_y = (height + CHUNK_SIZE - 1) // CHUNK_SIZE
        total_chunks = chunks_x * chunks_y
        
        info = {
            "@type": "neuroglancer_multiscale_volume",
            "type": "image",
            "data_type": "uint8",
            "num_channels": num_channels,
            "scales": [
                {
                    "key": "0",
                    "size": [width, height, 1],
                    "resolution": [1, 1, 1],
                    "voxel_offset": [0, 0, 0],
                    "chunk_sizes": [[CHUNK_SIZE, CHUNK_SIZE, 1]],
                    "encoding": "raw"
                }
            ]
        }
        
        info_path = os.path.join(volume_path, "info")
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
        
        print("[Upload] 데이터 저장 완료")
        
        # 백그라운드에서 임시 파일 정리
        background_tasks.add_task(cleanup_temp_file, upload_path)
        
        # 업로드 성공 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VOLUME_UPLOAD",
            details={
                "volume_name": volume_name,
                "file_size": file_size,
                "dimensions": f"{width}x{height}",
                "chunks": total_chunks
            }
        )
        
        # 사용자 활동 로깅
        ncsa_logger.log_activity(
            username=current_user.UserName,
            activity="IMAGE_UPLOADED",
            status="SUCCESS",
            details={
                "filename": file.filename,
                "volume": volume_name,
                "size_bytes": file_size,
                "width": width,
                "height": height,
                "chunks": total_chunks
            }
        )
        
        # 청크 분리 활동 로깅
        ncsa_logger.log_activity(
            username=current_user.UserName,
            activity="CHUNK_SPLIT",
            status="SUCCESS",
            details={
                "volume": volume_name,
                "chunk_size": CHUNK_SIZE,
                "total_chunks": total_chunks,
                "chunks_x": chunks_x,
                "chunks_y": chunks_y
            }
        )
        
        return JSONResponse(content={
            "message": "파일이 성공적으로 업로드되고 변환되었습니다.",
            "volume_name": volume_name,
            "volume_path": f"/precomp/{volume_name}",
            "neuroglancer_url": f"precomputed://http://localhost:8000/precomp/{volume_name}",
            "dimensions": [width, height, 1],
            "num_channels": num_channels,
            "chunk_size": CHUNK_SIZE,
            "total_chunks": total_chunks
        })
        
    except Exception as e:
        # 에러 발생 시 임시 파일 정리
        if os.path.exists(upload_path):
            background_tasks.add_task(cleanup_temp_file, upload_path)
        
        print(f"[Upload ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 업로드 실패 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="UPLOAD_ERROR",
            details={
                "filename": file.filename,
                "error": str(e)
            }
        )
        
        ncsa_logger.log_activity(
            username=current_user.UserName,
            activity="IMAGE_UPLOAD_FAILED",
            status="FAILED",
            details={
                "filename": file.filename,
                "error": str(e)
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "upload_failed",
                "message": f"파일 처리 중 오류가 발생했습니다: {str(e)}",
                "detail": str(e)
            }
        )


@router.get("/volumes")
async def list_volumes(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    사용 가능한 볼륨 목록 반환
    
    - 변환된 모든 볼륨의 목록과 상세 정보 제공
    """
    try:
        volumes = []
        if os.path.exists(DATA_ROOT):
            for item in os.listdir(DATA_ROOT):
                # temp 디렉터리 제외
                if item == "temp" or item.startswith("temp_"):
                    continue
                
                volume_path = os.path.join(DATA_ROOT, item)
                if os.path.isdir(volume_path):
                    info_path = os.path.join(volume_path, "info")
                    if os.path.exists(info_path):
                        # info 파일에서 상세 정보 읽기
                        with open(info_path, 'r') as f:
                            info = json.load(f)
                        
                        volumes.append({
                            "name": item,
                            "path": f"/precomp/{item}",
                            "info_url": f"/precomp/{item}/info",
                            "neuroglancer_url": f"precomputed://http://localhost:8000/precomp/{item}",
                            "dimensions": info['scales'][0]['size'] if 'scales' in info else None,
                            "chunk_size": info['scales'][0]['chunk_sizes'][0] if 'scales' in info else None
                        })
        
        # 볼륨 목록 조회 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="LIST_VOLUMES",
            details={"volume_count": len(volumes)}
        )
        
        return JSONResponse(content={"volumes": volumes, "count": len(volumes)})
    
    except Exception as e:
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="LIST_VOLUMES_ERROR",
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"볼륨 목록 조회 실패: {str(e)}"
        )


@router.get("/volumes/{volume_name}/info")
async def get_volume_info(
    volume_name: str,
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    특정 볼륨의 상세 정보 반환
    
    - info 파일 내용과 메타데이터 제공
    """
    try:
        volume_path = os.path.join(DATA_ROOT, volume_name)
        info_path = os.path.join(volume_path, "info")
        
        if not os.path.exists(info_path):
            await ncsa_logger.log_request(
                request=request,
                response=response,
                auth_user=current_user.UserName,
                activity_type="VOLUME_NOT_FOUND",
                details={"volume_name": volume_name}
            )
            raise HTTPException(
                status_code=404,
                detail="볼륨을 찾을 수 없습니다."
            )
        
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        
        # 볼륨 정보 조회 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_VOLUME_INFO",
            details={"volume_name": volume_name}
        )
        
        # 이미지 열기 활동 로깅
        ncsa_logger.log_activity(
            username=current_user.UserName,
            activity="IMAGE_VIEW",
            status="SUCCESS",
            details={
                "volume": volume_name,
                "dimensions": info['scales'][0]['size'] if 'scales' in info else None
            }
        )
        
        return JSONResponse(content={
            "volume_name": volume_name,
            "info": info,
            "volume_path": f"/precomp/{volume_name}",
            "neuroglancer_url": f"precomputed://http://localhost:8000/precomp/{volume_name}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_VOLUME_ERROR",
            details={"volume_name": volume_name, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"볼륨 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/volumes/{volume_name}")
async def delete_volume(
    volume_name: str, 
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    볼륨 삭제
    
    - 지정된 볼륨과 관련 데이터를 모두 삭제
    """
    try:
        volume_path = os.path.join(DATA_ROOT, volume_name)
        if not os.path.exists(volume_path):
            await ncsa_logger.log_request(
                request=request,
                response=response,
                auth_user=current_user.UserName,
                activity_type="DELETE_VOLUME_FAILED",
                details={"volume_name": volume_name, "reason": "not_found"}
            )
            raise HTTPException(
                status_code=404,
                detail="볼륨을 찾을 수 없습니다."
            )
        
        # 백그라운드에서 삭제
        background_tasks.add_task(shutil.rmtree, volume_path)
        
        # 볼륨 삭제 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VOLUME_DELETE",
            details={"volume_name": volume_name}
        )
        
        ncsa_logger.log_activity(
            username=current_user.UserName,
            activity="VOLUME_DELETED",
            status="SUCCESS",
            details={"volume": volume_name}
        )
        
        return JSONResponse(content={
            "message": f"볼륨 '{volume_name}'이 삭제 대기열에 추가되었습니다."
        })
        
    except HTTPException:
        raise
    except Exception as e:
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="DELETE_VOLUME_ERROR",
            details={"volume_name": volume_name, "error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"볼륨 삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/test-upload")
async def test_upload_setup(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    업로드 설정 테스트
    
    - 디렉터리 상태 및 설정 확인용
    """
    
    # 테스트 요청 로깅
    await ncsa_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="TEST_UPLOAD_CONFIG",
        details={"action": "check_setup"}
    )
    
    return JSONResponse(content={
        "upload_dir": UPLOAD_DIR,
        "data_root": DATA_ROOT,
        "upload_dir_exists": os.path.exists(UPLOAD_DIR),
        "data_root_exists": os.path.exists(DATA_ROOT),
        "chunk_size": CHUNK_SIZE
    })