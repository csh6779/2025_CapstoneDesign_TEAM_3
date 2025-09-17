from pathlib import Path
import argparse
import tifffile as tiff
import zarr

parser = argparse.ArgumentParser()
parser.add_argument("input_tif", type=Path)
parser.add_argument("output_zarr", type=Path)
args = parser.parse_args()

arr = tiff.imread(str(args.input_tif))  # 단순 버전(메모리 사용 큼)
store = zarr.DirectoryStore(str(args.output_zarr))
root = zarr.group(store=store, overwrite=True)
# 채널 마지막 가정: 2D/3D 모두 허용
root.create_dataset('0', data=arr, chunks=(512, 512, arr.shape[2]) if arr.ndim==3 else (512, 512), overwrite=True)
# 최소 multiscales 메타 (선택)
root.attrs['multiscales'] = [{
    'version': '0.1',
    'datasets': [{'path': '0'}],
}]
print("Wrote:", args.output_zarr)