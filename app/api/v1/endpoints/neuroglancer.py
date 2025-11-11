# app/api/v1/endpoints/neuroglancer.py
"""
Neuroglancer 관련 API 엔드포인트
- 이미지 업로드 및 청크 변환
- 볼륨 관리
- 메모리 상태 조회
- 대용량 TIFF 파일을 위한 스트리밍 처리
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
import gc

from app.api.v1.deps.Auth import get_current_user
from app.utils.json_logger import json_logger  # ✅ 변경: ncsa_logger → json_logger

# Pillow의 decompression bomb 보호 해제 (대용량 이미지 처리)
Image.MAX_IMAGE_PIXELS = None

router = APIRouter()

# 디렉터리 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
UPLOADS_BASE = os.environ.get("DATA_DIR", str(BASE_DIR / "uploads"))
CHUNK_SIZE = 512

# 기본 uploads 디렉터리 생성
os.makedirs(UPLOADS_BASE, exist_ok=True)

print(f"[Neuroglancer] Uploads 기본 경로: {UPLOADS_BASE}")


def get_user_data_root(username: str) -> str:
    """사용자별 데이터 루트 디렉터리 경로 반환"""
    user_root = os.path.join(UPLOADS_BASE, username)
    os.makedirs(user_root, exist_ok=True)
    return user_root


def get_user_temp_dir(username: str) -> str:
    """사용자별 임시 디렉터리 경로 반환"""
    temp_dir = os.path.join(UPLOADS_BASE, username, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


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


def process_chunk_from_image(img: Image.Image, chunk_x: int, chunk_y: int,
                             chunk_size: int, volume_path: str, scale_key: str = "0") -> str:
    """
    이미지에서 청크 영역만 추출하여 raw 형식으로 저장 (메모리 효율적)

    Args:
        img: PIL Image 객체 (전체를 메모리에 로드하지 않음)
        chunk_x: 청크 X 인덱스
        chunk_y: 청크 Y 인덱스
        chunk_size: 청크 크기
        volume_path: 볼륨 저장 경로
        scale_key: 스케일 키 (기본값: "0")

    Returns:
        저장된 청크 파일 경로
    """
    # 청크 좌표 계산
    x_start = chunk_x * chunk_size
    y_start = chunk_y * chunk_size
    x_end = min(x_start + chunk_size, img.width)
    y_end = min(y_start + chunk_size, img.height)

    # 해당 영역만 크롭 (메모리 효율적)
    chunk_img = img.crop((x_start, y_start, x_end, y_end))

    # numpy 배열로 변환
    chunk_data = np.array(chunk_img)

    # RGB를 그레이스케일로 변환 (필요한 경우)
    if len(chunk_data.shape) == 3 and chunk_data.shape[2] == 3:
        # RGB -> Grayscale
        chunk_data = np.mean(chunk_data, axis=2).astype(np.uint8)
    elif len(chunk_data.shape) == 3 and chunk_data.shape[2] == 4:
        # RGBA -> Grayscale (alpha 채널 무시)
        chunk_data = np.mean(chunk_data[:, :, :3], axis=2).astype(np.uint8)

    # 청크 크기가 부족한 경우 패딩
    actual_height, actual_width = chunk_data.shape[:2] if len(chunk_data.shape) == 2 else (
    chunk_data.shape[0], chunk_data.shape[1])

    if actual_height < chunk_size or actual_width < chunk_size:
        if len(chunk_data.shape) == 2:
            padded = np.zeros((chunk_size, chunk_size), dtype=np.uint8)
            padded[:actual_height, :actual_width] = chunk_data
        else:
            padded = np.zeros((chunk_size, chunk_size, chunk_data.shape[2]), dtype=np.uint8)
            padded[:actual_height, :actual_width] = chunk_data
        chunk_data = padded

    # 3D 배열로 변환 (Z축 추가)
    if len(chunk_data.shape) == 2:
        chunk_data = chunk_data[:, :, np.newaxis]
    else:
        chunk_data = chunk_data[:, :, :, np.newaxis]

    # Neuroglancer가 기대하는 청크 파일명 형식: x_start-x_end_y_start-y_end_z_start-z_end
    # 실제 끝 좌표를 사용 (x_end, y_end는 실제 이미지 크기로 제한됨)
    chunk_filename = f"{x_start}-{x_end}_{y_start}-{y_end}_0-1"

    # 스케일별 디렉터리 생성
    scale_dir = os.path.join(volume_path, scale_key)
    os.makedirs(scale_dir, exist_ok=True)

    # 청크 파일 경로
    chunk_path = os.path.join(scale_dir, chunk_filename)

    # Raw 바이너리 형식으로 저장 (확장자 없음)
    with open(chunk_path, 'wb') as f:
        # Neuroglancer raw 형식: C-order (channel-last)
        chunk_bytes = chunk_data.tobytes(order='C')
        f.write(chunk_bytes)

    # 메모리 정리
    del chunk_data, chunk_img

    return chunk_path


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
    - 대용량 TIFF 파일을 위한 스트리밍 처리
    """

    username = current_user.UserName
    print(f"[Upload] 파일 업로드 요청: {file.filename} by {username}")

    # 파일 형식 검증
    if not validate_image_file(file.filename):
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=username,
            activity_type="UPLOAD_FAILED",
            details={"filename": file.filename, "reason": "invalid_format"}
        )
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 파일 형식입니다. PNG, JPG, TIFF만 지원합니다."
        )

    # 사용자별 디렉터리 설정
    user_data_root = get_user_data_root(username)
    user_temp_dir = get_user_temp_dir(username)

    print(f"[Upload] 사용자 데이터 경로: {user_data_root}")
    print(f"[Upload] 임시 파일 경로: {user_temp_dir}")

    # 임시 파일 저장
    upload_path = os.path.join(user_temp_dir, file.filename)

    try:
        # 파일 저장
        content = await file.read()
        file_size = len(content)

        with open(upload_path, "wb") as buffer:
            buffer.write(content)
        print(f"[Upload] 파일 저장 완료: {file_size} bytes ({file_size / (1024 ** 3):.2f} GB)")

        # 메모리 정리
        del content
        gc.collect()

        # 볼륨 설정 (사용자별 디렉터리)
        volume_name = Path(file.filename).stem
        volume_path = os.path.join(user_data_root, volume_name)

        print(f"[Upload] 볼륨 이름: {volume_name}")
        print(f"[Upload] 볼륨 경로: {volume_path}")

        # Precomputed 형식으로 변환
        print("[Upload] Precomputed 형식으로 변환 시작 (스트리밍 모드)...")

        # 이미지 열기 (메모리에 전체를 로드하지 않음)
        img = Image.open(upload_path)
        width, height = img.size
        num_channels = 1  # 그레이스케일로 변환

        print(f"[Upload] 이미지 크기: {width}x{height} ({width * height / (1024 ** 2):.2f} MP)")

        # 볼륨 디렉터리 생성
        os.makedirs(volume_path, exist_ok=True)

        # 청크 수 계산
        chunks_x = (width + CHUNK_SIZE - 1) // CHUNK_SIZE
        chunks_y = (height + CHUNK_SIZE - 1) // CHUNK_SIZE
        total_chunks = chunks_x * chunks_y

        print(f"[Upload] 청크 수: {chunks_x}x{chunks_y} = {total_chunks}개")
        print(f"[Upload] 예상 메모리 사용: 청크당 ~{(CHUNK_SIZE * CHUNK_SIZE) / (1024 ** 2):.2f} MB")

        # ✅ 청크 데이터 저장 (스트리밍 방식 - 메모리 효율적)
        print("[Upload] 청크 데이터 저장 시작 (스트리밍)...")
        saved_chunks = 0

        for cy in range(chunks_y):
            for cx in range(chunks_x):
                chunk_path = process_chunk_from_image(
                    img, cx, cy, CHUNK_SIZE, volume_path, scale_key="0"
                )
                saved_chunks += 1

                # 진행 상황 로그 (100개마다 또는 마지막)
                if saved_chunks % 100 == 0 or saved_chunks == total_chunks:
                    progress = (saved_chunks / total_chunks) * 100
                    print(f"[Upload] 청크 저장 진행: {saved_chunks}/{total_chunks} ({progress:.1f}%)")

                # 주기적으로 가비지 컬렉션 (메모리 정리)
                if saved_chunks % 500 == 0:
                    gc.collect()

        # 이미지 닫기
        img.close()
        del img
        gc.collect()

        print(f"[Upload] 총 {saved_chunks}개 청크 저장 완료!")

        # info 파일 생성
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

        print("[Upload] info 파일 저장 완료")
        print("[Upload] 데이터 저장 완료")

        # 백그라운드에서 임시 파일 정리
        background_tasks.add_task(cleanup_temp_file, upload_path)

        # 업로드 성공 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=username,
            activity_type="VOLUME_UPLOAD",
            details={
                "volume_name": volume_name,
                "file_size": file_size,
                "dimensions": f"{width}x{height}",
                "chunks": total_chunks
            }
        )

        # 사용자 활동 로깅
        json_logger.log_activity(
            username=username,
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
        json_logger.log_activity(
            username=username,
            activity="CHUNK_SPLIT",
            status="SUCCESS",
            details={
                "volume": volume_name,
                "chunk_size": CHUNK_SIZE,
                "total_chunks": total_chunks,
                "chunks_x": chunks_x,
                "chunks_y": chunks_y,
                "saved_chunks": saved_chunks
            }
        )

        return JSONResponse(content={
            "message": "파일이 성공적으로 업로드되고 변환되었습니다.",
            "volume_name": volume_name,
            "username": username,
            "volume_path": f"/uploads/{username}/{volume_name}",
            "neuroglancer_url": f"precomputed://http://localhost:8000/uploads/{username}/{volume_name}",
            "dimensions": [width, height, 1],
            "num_channels": num_channels,
            "chunk_size": CHUNK_SIZE,
            "total_chunks": total_chunks,
            "saved_chunks": saved_chunks
        })

    except Exception as e:
        # 에러 발생 시 임시 파일 정리
        if os.path.exists(upload_path):
            background_tasks.add_task(cleanup_temp_file, upload_path)

        print(f"[Upload ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

        # 메모리 정리
        gc.collect()

        # 업로드 실패 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=username,
            activity_type="UPLOAD_ERROR",
            details={
                "filename": file.filename,
                "error": str(e)
            }
        )

        json_logger.log_activity(
            username=username,
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
    - 현재 사용자의 볼륨만 표시
    """
    try:
        username = current_user.UserName
        user_data_root = get_user_data_root(username)

        volumes = []
        if os.path.exists(user_data_root):
            for item in os.listdir(user_data_root):
                # temp 디렉터리 제외
                if item == "temp" or item.startswith("temp_"):
                    continue

                volume_path = os.path.join(user_data_root, item)
                if os.path.isdir(volume_path):
                    info_path = os.path.join(volume_path, "info")
                    if os.path.exists(info_path):
                        # info 파일에서 상세 정보 읽기
                        with open(info_path, 'r') as f:
                            info = json.load(f)

                        volumes.append({
                            "name": item,
                            "username": username,
                            "path": f"/uploads/{username}/{item}",
                            "info_url": f"/uploads/{username}/{item}/info",
                            "neuroglancer_url": f"precomputed://http://localhost:8000/uploads/{username}/{item}",
                            "dimensions": info['scales'][0]['size'] if 'scales' in info else None,
                            "chunk_size": info['scales'][0]['chunk_sizes'][0] if 'scales' in info else None
                        })

        # 볼륨 목록 조회 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=username,
            activity_type="LIST_VOLUMES",
            details={"volume_count": len(volumes)}
        )

        return JSONResponse(content={"volumes": volumes, "count": len(volumes)})

    except Exception as e:
        await json_logger.log_request(
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
    - 현재 사용자의 볼륨만 접근 가능
    """
    try:
        username = current_user.UserName
        user_data_root = get_user_data_root(username)
        volume_path = os.path.join(user_data_root, volume_name)
        info_path = os.path.join(volume_path, "info")

        if not os.path.exists(info_path):
            await json_logger.log_request(
                request=request,
                response=response,
                auth_user=username,
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
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=username,
            activity_type="VIEW_VOLUME_INFO",
            details={"volume_name": volume_name}
        )

        # 이미지 열기 활동 로깅
        json_logger.log_activity(
            username=username,
            activity="IMAGE_VIEW",
            status="SUCCESS",
            details={
                "volume": volume_name,
                "dimensions": info['scales'][0]['size'] if 'scales' in info else None
            }
        )

        return JSONResponse(content={
            "volume_name": volume_name,
            "username": username,
            "info": info,
            "volume_path": f"/uploads/{username}/{volume_name}",
            "neuroglancer_url": f"precomputed://http://localhost:8000/uploads/{username}/{volume_name}"
        })

    except HTTPException:
        raise
    except Exception as e:
        await json_logger.log_request(
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
    - 현재 사용자의 볼륨만 삭제 가능
    """
    try:
        username = current_user.UserName
        user_data_root = get_user_data_root(username)
        volume_path = os.path.join(user_data_root, volume_name)

        if not os.path.exists(volume_path):
            await json_logger.log_request(
                request=request,
                response=response,
                auth_user=username,
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
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=username,
            activity_type="VOLUME_DELETE",
            details={"volume_name": volume_name}
        )

        json_logger.log_activity(
            username=username,
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
        await json_logger.log_request(
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
    username = current_user.UserName
    user_data_root = get_user_data_root(username)
    user_temp_dir = get_user_temp_dir(username)

    # 테스트 요청 로깅
    await json_logger.log_request(
        request=request,
        response=response,
        auth_user=username,
        activity_type="TEST_UPLOAD_CONFIG",
        details={"action": "check_setup"}
    )

    return JSONResponse(content={
        "username": username,
        "uploads_base": UPLOADS_BASE,
        "user_data_root": user_data_root,
        "user_temp_dir": user_temp_dir,
        "uploads_base_exists": os.path.exists(UPLOADS_BASE),
        "user_data_root_exists": os.path.exists(user_data_root),
        "user_temp_dir_exists": os.path.exists(user_temp_dir),
        "chunk_size": CHUNK_SIZE
    })