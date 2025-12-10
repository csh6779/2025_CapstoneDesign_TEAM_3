"""
CloudVolume 없이 직접 Precomputed 형식으로 저장하는 유틸리티
"""
import os
import json
import warnings
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile
import tifffile as tiff
import zarr

# Pillow 폭탄가드 완전 해제
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True
warnings.simplefilter('ignore', Image.DecompressionBombWarning)


# ---------- info/provenance ----------
def create_precomputed_info(width, height, num_channels, chunk_size, dtype_str, encoding):
    return {
        "type": "image",
        "data_type": dtype_str,
        "num_channels": int(num_channels),
        "scales": [{
            "chunk_sizes": [[int(chunk_size), int(chunk_size), 1]],
            "encoding": encoding,
            "key": "0",
            "resolution": [1, 1, 1],
            "size": [int(width), int(height), 1],
            "voxel_offset": [0, 0, 0]
        }],
    }


def np_dtype_to_str(dtype_like):
    dt = np.dtype(dtype_like)
    if dt == np.uint8:   return "uint8"
    if dt == np.uint16:  return "uint16"
    if dt == np.int16:   return "int16"
    if dt == np.uint32:  return "uint32"
    if dt == np.float32: return "float32"
    raise ValueError(f"지원하지 않는 dtype: {dt} (str: {str(dt)})")


# ---------- 저장 함수 ----------
def save_chunk_raw(tile_hwc_or_hw: np.ndarray, out_path: str):
    tile = tile_hwc_or_hw
    if tile.ndim == 2:
        tile = tile[:, :, None]

    tile_cyx = np.transpose(tile, (2, 0, 1)).copy(order="C")
    with open(out_path, "wb") as f:
        f.write(tile_cyx.tobytes(order="C"))


def save_chunk_png(tile_whc, out_path):
    if tile_whc.ndim == 2:
        arr = tile_whc
        if arr.dtype == np.uint16:
            img = Image.fromarray(arr)
        else:
            img = Image.fromarray(arr.astype(np.uint8), mode='L')
        img.save(out_path, format='PNG', compress_level=0)
        return

    H, W, C = tile_whc.shape
    if C == 1:
        ch = tile_whc[:, :, 0]
        if ch.dtype == np.uint16:
            img = Image.fromarray(ch)
        else:
            img = Image.fromarray(ch.astype(np.uint8), mode='L')
        img.save(out_path, format='PNG', compress_level=0)
        return

    if C == 3:
        if tile_whc.dtype == np.uint16:
            down = (tile_whc >> 8).astype(np.uint8)
            img = Image.fromarray(down, mode='RGB')
        else:
            img = Image.fromarray(tile_whc.astype(np.uint8), mode='RGB')
        img.save(out_path, format='PNG', compress_level=0)
        return

    raise ValueError(f"지원하지 않는 채널 수: {C}")


# ---------- 공통 타일 루프 ----------
def write_precomputed_from_array(arr_hwc, volume_path, chunk_size=512, encoding="raw"):
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

    os.makedirs(volume_path, exist_ok=True)
    scale_dir = os.path.join(volume_path, "0")
    os.makedirs(scale_dir, exist_ok=True)

    info = create_precomputed_info(W, H, C, chunk_size, dtype_str, encoding)
    with open(os.path.join(volume_path, "info"), "w") as f:
        json.dump(info, f, indent=2)
    with open(os.path.join(volume_path, "provenance"), "w") as f:
        json.dump({"sources": []}, f, indent=2)

    for y0 in range(0, H, chunk_size):
        y1 = min(H, y0 + chunk_size)
        for x0 in range(0, W, chunk_size):
            x1 = min(W, x0 + chunk_size)

            tile = arr_hwc[y0:y1, x0:x1] if C != 1 else arr_hwc[y0:y1, x0:x1].squeeze()
            fname = f"{x0}-{x1}_{y0}-{y1}_0-1"
            out_path = os.path.join(scale_dir, fname)

            if encoding == "raw":
                save_chunk_raw(tile, out_path)
            elif encoding == "png":
                save_chunk_png(tile, out_path)
            else:
                raise ValueError("encoding은 'raw' 또는 'png'만 지원")
    return 0


# ---------- 파일 단위 변환 ----------
def convert_image_file_to_precomputed(input_path, output_path, chunk_size=512, encoding="raw", chunk_z=1):
    ext = Path(input_path).suffix.lower()

    # TIFF 처리
    if ext in (".tif", ".tiff"):
        with tiff.TiffFile(input_path) as tf:
            z = zarr.open(tf.aszarr())
            if z.ndim == 2:
                H, W = z.shape
                C = 1
            elif z.ndim == 3:
                H, W, C = z.shape
                if C not in (1, 3, 4):
                    raise ValueError(f"지원하지 않는 TIFF 채널 수: {C}")
            else:
                raise ValueError(f"지원하지 않는 TIFF 차원: {z.shape}")

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
            for y0 in range(0, H, chunk_size):
                y1 = min(H, y0 + chunk_size)
                for x0 in range(0, W, chunk_size):
                    x1 = min(W, x0 + chunk_size)

                    if C == 1:
                        tile = z[y0:y1, x0:x1]
                    else:
                        tile = z[y0:y1, x0:x1, : min(C, 3)]

                    tile_np = np.asarray(tile)
                    fname = f"{x0}-{x1}_{y0}-{y1}_0-1"
                    out_path = os.path.join(scale_dir, fname)

                    if encoding == "raw":
                        save_chunk_raw(tile_np, out_path)
                    else:
                        save_chunk_png(tile_np, out_path)
                    total += 1
            return total

    # 일반 이미지 (PNG, JPG) 처리
    with Image.open(input_path) as img:
        arr = np.array(img)

    return write_precomputed_from_array(arr, output_path, chunk_size=chunk_size, encoding=encoding)