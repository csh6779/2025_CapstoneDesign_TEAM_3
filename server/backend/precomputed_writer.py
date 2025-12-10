"""
CloudVolume 없이 직접 Precomputed 형식으로 저장하는 유틸리티
- IntervalTree 이슈 회피
- TIFF는 tifffile + zarr로 '부분 슬라이스' 스트리밍
- encoding: 'raw' 또는 'png' 선택 지원
- 파일명 규칙: {xStart}-{yStart}-{z}  (z=0 고정)
"""
import os
import json
import warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile
import tifffile as tiff
import zarr

# Pillow 폭탄가드 완전 해제 (PNG/JPG용)
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True
warnings.simplefilter('ignore', Image.DecompressionBombWarning)


# ---------- info/provenance ----------
def create_precomputed_info(width, height, num_channels, chunk_size, dtype_str, encoding):
    return {
        "type": "image",
        "data_type": dtype_str,                    # "uint8" / "uint16" / "float32" ...
        "num_channels": int(num_channels),         # 1 or 3
        "scales": [{
            "chunk_sizes": [[int(chunk_size), int(chunk_size), 1]],
            "encoding": encoding,                  # "raw" or "png"
            "key": "0",
            "resolution": [1, 1, 1],
            "size": [int(width), int(height), 1],  # [x, y, z]
            "voxel_offset": [0, 0, 0]
        }],
    }


def np_dtype_to_str(dtype_like):
    """
    np.dtype, dtype 문자열, 실제 numpy scalar dtype 모두 수용.
    neuroglancer 'data_type'과 정확히 일치하는 문자열로 변환.
    """
    dt = np.dtype(dtype_like)  # <- 핵심: 무엇이 오든 np.dtype로 정규화
    if dt == np.uint8:   return "uint8"
    if dt == np.uint16:  return "uint16"
    if dt == np.int16:   return "int16"
    if dt == np.uint32:  return "uint32"
    if dt == np.float32: return "float32"
    raise ValueError(f"지원하지 않는 dtype: {dt} (str: {str(dt)})")


# ---------- 저장 함수 ----------
def save_chunk_raw(tile_hwc_or_hw: np.ndarray, out_path: str):
    """
    tile: (H, W, C) 또는 (H, W) [uint8/uint16/float32 등]
    RAW 파일을 Neuroglancer가 기대하는 레이아웃으로 기록.
    안전한 축 순서: (C, Y, X)  → C-order로 직렬화하면 X가 가장 빠름.
    """
    tile = tile_hwc_or_hw
    if tile.ndim == 2:          # (H, W) → (H, W, 1)
        tile = tile[:, :, None]

    # (H, W, C) -> (C, Y, X)
    tile_cyx = np.transpose(tile, (2, 0, 1)).copy(order="C")
    with open(out_path, "wb") as f:
        f.write(tile_cyx.tobytes(order="C"))



def save_chunk_png(tile_whc, out_path):
    """
    tile_whc: (H, W, C) 또는 (H, W) -> PNG로 저장
    - 단일 채널 uint16은 'I;16'로 저장 가능
    - RGB 16bit는 Pillow가 직접 지원하지 않으므로 uint8로 다운샘플
    """
    if tile_whc.ndim == 2:
        arr = tile_whc
        if arr.dtype == np.uint16:
            # PIL이 'I;16'로 처리
            img = Image.fromarray(arr)
        else:
            img = Image.fromarray(arr.astype(np.uint8), mode='L')
        img.save(out_path, format='PNG', compress_level=0)
        return

    # (H,W,C)
    H, W, C = tile_whc.shape
    if C == 1:
        ch = tile_whc[:, :, 0]
        if ch.dtype == np.uint16:
            img = Image.fromarray(ch)  # 'I;16'
        else:
            img = Image.fromarray(ch.astype(np.uint8), mode='L')
        img.save(out_path, format='PNG', compress_level=0)
        return

    if C == 3:
        if tile_whc.dtype == np.uint16:
            # 경고: RGB 16-bit PNG는 Pillow 기본 지원이 애매함 → 8-bit 다운샘플
            down = (tile_whc >> 8).astype(np.uint8)
            img = Image.fromarray(down, mode='RGB')
        else:
            img = Image.fromarray(tile_whc.astype(np.uint8), mode='RGB')
        img.save(out_path, format='PNG', compress_level=0)
        return

    raise ValueError(f"지원하지 않는 채널 수: {C}")


# ---------- 공통 타일 루프 ----------
def write_precomputed_from_array(arr_hwc, volume_path, chunk_size=512, encoding="raw"):
    """
    arr_hwc: (H, W[, C])  (C가 없으면 1채널로 처리)
    encoding: "raw" 또는 "png"
    """
    # 차원/채널 정리
    if arr_hwc.ndim == 2:
        H, W = arr_hwc.shape
        C = 1
    elif arr_hwc.ndim == 3:
        H, W, C = arr_hwc.shape
        if C == 4:
            arr_hwc = arr_hwc[..., :3]
            C = 3
        elif C not in (1, 3):
            raise ValueError(f"지원하지 않는 채널 수: {C}")
    else:
        raise ValueError(f"지원하지 않는 차원: {arr_hwc.shape}")

    dtype_str = np_dtype_to_str(arr_hwc.dtype)

    # 디렉터리/메타 생성
    os.makedirs(volume_path, exist_ok=True)
    scale_dir = os.path.join(volume_path, "0")
    os.makedirs(scale_dir, exist_ok=True)

    info = create_precomputed_info(W, H, C, chunk_size, dtype_str, encoding)
    with open(os.path.join(volume_path, "info"), "w") as f:
        json.dump(info, f, indent=2)
    with open(os.path.join(volume_path, "provenance"), "w") as f:
        json.dump({"sources": []}, f, indent=2)

    # 타일 저장
    total = 0
    for y0 in range(0, H, chunk_size):
        y1 = min(H, y0 + chunk_size)
        for x0 in range(0, W, chunk_size):
            x1 = min(W, x0 + chunk_size)

            # 가장자리는 작아도 OK (패딩 불필요)
            tile = arr_hwc[y0:y1, x0:x1] if C != 1 else arr_hwc[y0:y1, x0:x1].squeeze()

            # 파일명 규칙: {xStart}-{yStart}-0
            fname = f"{x0}-{x1}_{y0}-{y1}_0-1"
            out_path = os.path.join(scale_dir, fname)

            if encoding == "raw":
                save_chunk_raw(tile, out_path)
            elif encoding == "png":
                save_chunk_png(tile, out_path)  # 확장자 없어도 NG는 문제 없음
            else:
                raise ValueError("encoding은 'raw' 또는 'png'만 지원")

            total += 1
    return total


# ---------- 파일 단위 변환 ----------
def convert_image_file_to_precomputed(input_path, output_path, chunk_size=512, encoding="raw"):
    """
    이미지 파일을 Precomputed 형식으로 변환.
    - TIFF: tifffile + zarr 스트리밍 (메모리 폭주 방지)
    - PNG/JPG: Pillow (폭탄가드 해제됨)
    - encoding: "raw" 또는 "png"
    """
    ext = Path(input_path).suffix.lower()

    # ---------- TIFF: 스트리밍 ----------
    if ext in (".tif", ".tiff"):
        with tiff.TiffFile(input_path) as tf:
            # zarr 뷰(부분 디코드) — 압축된 TIFF도 슬라이스 단위로 안전
            z = zarr.open(tf.aszarr())
            if z.ndim == 2:
                H, W = z.shape
                C = 1
            elif z.ndim == 3:
                H, W, C = z.shape
                # RGBA → RGB (뒤에서 :C 슬라이스로 통일)
                if C not in (1, 3, 4):
                    raise ValueError(f"지원하지 않는 TIFF 채널 수: {C}")
            else:
                raise ValueError(f"지원하지 않는 TIFF 차원: {z.shape}")

            # info/provenance 먼저 생성 (dtype은 zarr dtype 기반)
            dtype_str = np_dtype_to_str(z.dtype)
            os.makedirs(output_path, exist_ok=True)
            scale_dir = os.path.join(output_path, "0")
            os.makedirs(scale_dir, exist_ok=True)

            info = create_precomputed_info(W, H, min(C, 3), chunk_size, dtype_str, encoding)
            with open(os.path.join(output_path, "info"), "w") as f:
                json.dump(info, f, indent=2)
            with open(os.path.join(output_path, "provenance"), "w") as f:
                json.dump({"sources": [Path(input_path).name]}, f, indent=2)

            total = 0
            # 타일 루프: 필요 영역만 디코드
            for y0 in range(0, H, chunk_size):
                y1 = min(H, y0 + chunk_size)
                for x0 in range(0, W, chunk_size):
                    x1 = min(W, x0 + chunk_size)

                    # 부분 슬라이스
                    if C == 1:
                        tile = z[y0:y1, x0:x1]
                    else:
                        tile = z[y0:y1, x0:x1, : min(C, 3)]  # RGBA → RGB

                    tile_np = np.asarray(tile)

                    # 파일명 규칙: {xStart}-{yStart}-0
                    fname = f"{x0}-{x1}_{y0}-{y1}_0-1"
                    out_path = os.path.join(scale_dir, fname)

                    if encoding == "raw":
                        save_chunk_raw(tile_np, out_path)
                    else:
                        save_chunk_png(tile_np, out_path)

                    total += 1
            return total

    # ---------- PNG/JPG 등: Pillow ----------
    with Image.open(input_path) as img:
        arr = np.array(img)

    if arr.ndim == 2:
        pass
    elif arr.ndim == 3:
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]  # RGBA→RGB
        elif arr.shape[2] not in (1, 3):
            raise ValueError(f"지원하지 않는 채널 수: {arr.shape[2]}")
    else:
        raise ValueError(f"지원하지 않는 이미지 차원: {arr.shape}")

    # dtype은 있는 그대로 사용(예: uint8/uint16/float32)
    return write_precomputed_from_array(arr, output_path, chunk_size=chunk_size, encoding=encoding)


# ---------- RAW 파일 지원 ----------
def convert_raw_to_precomputed(
        raw_path: str,
        output_path: str,
        width: int,
        height: int,
        channels: int = 3,
        dtype_str: str = "uint8",
        chunk_size: int = 512,
        encoding: str = "raw"
):
    """
    RAW 이미지 파일(헤더 없는 순수 바이너리)을 Precomputed 형식으로 변환

    Args:
        raw_path: RAW 파일 경로
        output_path: 출력 디렉터리
        width: 이미지 너비
        height: 이미지 높이
        channels: 채널 수 (1=grayscale, 3=RGB)
        dtype_str: 데이터 타입 ("uint8", "uint16", "int16", "uint32", "float32")
        chunk_size: 청크 크기 (기본: 512)
        encoding: 출력 인코딩 ("raw" or "png")
    """
    # dtype 매핑
    dtype_map = {
        "uint8": np.uint8,
        "uint16": np.uint16,
        "int16": np.int16,
        "uint32": np.uint32,
        "float32": np.float32,
    }

    if dtype_str not in dtype_map:
        raise ValueError(
            f"지원하지 않는 dtype: {dtype_str}\n"
            f"지원되는 타입: {list(dtype_map.keys())}"
        )

    np_dtype = dtype_map[dtype_str]

    # 예상 파일 크기 계산
    total_pixels = width * height * channels
    bytes_per_element = np.dtype(np_dtype).itemsize
    expected_bytes = total_pixels * bytes_per_element

    # 파일 크기 검증
    actual_bytes = os.path.getsize(raw_path)

    if actual_bytes != expected_bytes:
        raise ValueError(
            f"❌ RAW 파일 크기 불일치!\n"
            f"  예상: {expected_bytes:,} bytes\n"
            f"    = {width} × {height} × {channels} × {bytes_per_element} bytes\n"
            f"  실제: {actual_bytes:,} bytes\n"
            f"  차이: {abs(actual_bytes - expected_bytes):,} bytes\n\n"
            f"올바른 파라미터를 지정했는지 확인하세요:\n"
            f"  - width, height가 정확한가요?\n"
            f"  - channels가 맞나요? (1=grayscale, 3=RGB)\n"
            f"  - dtype이 올바른가요? (현재: {dtype_str})"
        )

    print(f"✅ RAW 파일 크기 검증 완료: {actual_bytes:,} bytes")

    # RAW 데이터를 numpy 배열로 로드
    with open(raw_path, 'rb') as f:
        data = np.fromfile(f, dtype=np_dtype)

    # (H, W, C) 또는 (H, W) 형태로 reshape
    if channels == 1:
        arr = data.reshape((height, width))
    else:
        arr = data.reshape((height, width, channels))

    print(f"✅ RAW 파일 로드 완료:")
    print(f"  - 크기: {width}×{height}")
    print(f"  - 채널: {channels}")
    print(f"  - dtype: {dtype_str}")
    print(f"  - shape: {arr.shape}")
    print(f"  - 값 범위: [{arr.min()}, {arr.max()}]")

    # Precomputed 형식으로 변환
    return write_precomputed_from_array(
        arr,
        output_path,
        chunk_size=chunk_size,
        encoding=encoding
    )