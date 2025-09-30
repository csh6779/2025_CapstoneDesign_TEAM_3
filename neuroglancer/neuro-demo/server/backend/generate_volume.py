import os
import numpy as np
from cloudvolume import CloudVolume, Storage

# 컨테이너 내부 데이터 루트
DATA_ROOT = os.environ.get("DATA_DIR", "/app/data/precomputed")

# 파일 시스템용 precomputed URL (로컬 파일)
#   예: file:///app/data/precomputed
PRECOMP_URL = f"precomputed://file://{DATA_ROOT}"

# 간단한 2D RGB uint8 이미지 1장 (Z=1) 생성
W, H, Z = 2048, 2048, 1
NUM_CHANNELS = 3
DTYPE = "uint8"

def ensure_volume():
    # info.json을 새로 생성 (존재 시 스킵)
    # PNG 인코딩, 512x512 타일, level key "0"
    info = CloudVolume.create_new_info(
        num_channels=NUM_CHANNELS,
        layer_type="image",
        data_type=DTYPE,
        encoding="png",
        resolution=[1, 1, 1],             # voxel 크기(임의)
        voxel_offset=[0, 0, 0],
        chunk_size=[512, 512, 1],
        volume_size=[W, H, Z],            # XYZ 순서
    )

    os.makedirs(DATA_ROOT, exist_ok=True)
    vol = CloudVolume(PRECOMP_URL, info=info, compress=False, progress=False)
    
    # exists() 메서드는 slices 형식을 기대함
    # 전체 볼륨 범위를 체크 (slices 형식: [x_start:x_end, y_start:y_end, z_start:z_end])
    slices = [slice(0, W), slice(0, H), slice(0, Z)]
    if not vol.exists(slices):
        vol.commit_info()  # info.json 쓰기
        vol.commit_provenance({"method": "generate_volume.py"})

    return vol

def write_data(vol):
    # RGB 그라디언트 예시
    # CloudVolume의 write 배열 shape: (x, y, z, c)
    x = np.linspace(0, 255, W, dtype=np.uint8)
    y = np.linspace(0, 255, H, dtype=np.uint8)
    xv, yv = np.meshgrid(x, y, indexing="xy")

    r = xv
    g = yv
    b = ((xv.astype(np.uint16) + yv.astype(np.uint16)) // 2).astype(np.uint8)

    arr = np.stack([r, g, b], axis=-1)      # (H, W, 3)
    arr = np.expand_dims(arr, axis=2)       # (H, W, 1, 3)
    arr = np.transpose(arr, (1, 0, 2, 3))   # (W, H, 1, 3) -> CloudVolume 순서와 맞추기

    # 전체 범위에 한번에 쓰기
    vol[:, :, 0:1] = arr

if __name__ == "__main__":
    vol = ensure_volume()

    # 이미 타일이 있으면 건너뛰기 (간단 체크)
    # /0 디렉터리에 PNG가 있으면 생성되어 있다고 판단
    level0 = os.path.join(DATA_ROOT, "0")
    already = os.path.exists(level0) and any(f.endswith(".png") for f in os.listdir(level0))
    if not already:
        write_data(vol)
        print("Precomputed PNG tiles generated.")
    else:
        print("Tiles already exist. Skipping generation.")
