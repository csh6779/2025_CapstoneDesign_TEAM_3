# util_zarr.py
# 실제 이미지 처리를 담당하는 유틸리티 모듈

from pathlib import Path
import tifffile as tiff
import zarr
from PIL import Image
import numpy as np
import math

def ingest_to_zarr(input_path: Path, output_path: Path):
    """이미지 파일을 Zarr 형식으로 변환 (TIFF, PNG, BMP, JPEG 지원)"""
    # 이 함수는 원본과 거의 동일하게 유지됩니다.
    # 참고: 이 방식은 가장 높은 해상도의 레벨 '0'만 생성합니다.
    # 더 나은 성능을 위해서는 zarr-pyramid 같은 라이브러리로
    # 미리 모든 레벨의 이미지를 생성해두는 것이 좋습니다.
    ext = input_path.suffix.lower()
    
    #TIFF 
    #초대용량 이미지 지원
    #멀티페이지, 다중채널 , 16/32bit 같은 고비트 심도 지원
    #tifffile = TIFF 전용 고성능 라이브러리
    if ext in {'.tif', '.tiff'}:  #확장자가 TIFF계열이면 tifffile 라이브러리로 읽기
        arr = tiff.imread(str(input_path))
    else:  #그 외 -> Pillow(Image.open)로 읽고 Numpy배열로 반환 / Pillow = py에서 쓰는 이미지 처리 라이브러리
        Image.MAX_IMAGE_PIXELS = None #Pillow의 너무 큰 이미지 방지 제한을 해제
        img = Image.open(input_path) 
        arr = np.array(img)
    
    root = zarr.open_group(str(output_path), mode='w')  # out_path 위치에 zarr 그룹 생성 , w = 쓰기모드
    
    # 데이터 차원에 따라 청크 크기 결정
    if arr.ndim == 3:
        # 데이터가 (높이, 너비, 채널) 순서라고 가정
        chunks = (512, 512, arr.shape[2])
    else:
        # 흑백 이미지
        chunks = (512, 512)

    # 최고 해상도 이미지를 '0' 경로에 저장
    root.create_dataset('0', data=arr, shape=arr.shape, chunks=chunks, overwrite=True)
    
    # OME-NGFF multiscales 메타데이터 추가 (OpenSeadragon 호환)
    # metadata =실제 데이터가 무엇인지 설명하는 부가정보
    # multiscales = 이미지 피라미드(해상도) 구조를 설명하는 표준키
    root.attrs['multiscales'] = [{  #root.attrs = zarr 그룹에 달 수 있는 attribute 저장소
        'version': '0.1',  #포멧 버전
        'datasets': [{'path': '0'}],
        'type': 'deepzoom' # OSD 호환성을 위해 타입 명시
    # 이 zarr은 deepzoom 방식이고 레벨 0, 데이터셋 하나만 있음
    }]
    
    return {
        "shape": arr.shape,
        "dtype": str(arr.dtype),
        "chunks": root['0'].chunks  #블록크기
    }

def open_zarr_array(store_dir: Path):
    """Zarr 배열 열기"""
    root = zarr.open_group(str(store_dir), mode='r')
    # 최고 해상도 데이터셋을 직접 참조
    arr = root['0'] # 레벨 [0] = 최고 해상도 데이터셋
    
    if arr.ndim == 3: #ndim = 차원 수
        H, W, C = arr.shape # 3차원 컬러 이미지 (H,W,C)
    else:
        H, W = arr.shape # 2차원 흑백 이미지 (H,W)
        C = 1
    
    return arr, W, H, C

def lmax(W: int, H: int) -> int:
    """
    OpenSeadragon/DeepZoom 호환 최대 레벨 계산.
    레벨 N은 2^(maxLevel-N) 배 축소된 이미지를 의미합니다.
    """
    return int(math.ceil(math.log2(max(W, H)))) # 이미지의 긴 변이 2의 몇 제곱인지 계산 후 MAX 레벨 지정

def read_tile_from_zarr(store_dir: Path, level: int, x: int, y: int, tile_size: int = 512):
    """
    Zarr에서 동적으로 다운샘플링하여 타일 읽기 (버그 수정 및 로직 강화)
    """
    arr, W, H, C = open_zarr_array(store_dir)
    max_level = lmax(W, H)
    
    # 1. 요청된 레벨에 대한 축척(scale) 계산
    # level이 max_level이면 scale=1 (원본), level이 0이면 최대 축소
    if level > max_level:
        level = max_level
    scale = 2 ** (max_level - level)

    # 2. 원본 이미지(level 'max_level') 좌표계에서 읽을 영역 계산
    # 요청된 타일(x,y)의 시작 위치를 원본 좌표로 변환
    read_start_x = x * tile_size * scale
    read_start_y = y * tile_size * scale
    
    # 읽어야 할 영역의 크기를 계산 (축척 고려)
    read_size = tile_size * scale
    
    # 원본 이미지 경계를 벗어나지 않도록 읽을 끝 좌표 조정
    read_end_x = min(read_start_x + read_size, W)
    read_end_y = min(read_start_y + read_size, H)

    # 실제 읽을 영역의 너비와 높이 (정수형으로 변환)
    read_width = int(read_end_x - read_start_x)
    read_height = int(read_end_y - read_start_y)

    # 요청된 타일이 이미지 영역을 완전히 벗어나는 경우, 빈 타일 반환
    if read_width <= 0 or read_height <= 0:
        # OSD 호환성을 위해 RGB 빈 타일 생성
        empty_tile = Image.new('RGB', (tile_size, tile_size), (0, 0, 0))
        return empty_tile

    # 3. Zarr 배열에서 고해상도 데이터 블록 추출
    tile_data_high_res = arr[read_start_y:read_end_y, read_start_x:read_end_x]

    # 4. 데이터 타입 정규화 (uint8로 변환) , unit8 형식 (0~255 정수)
    # 이미지 픽셀 데이터를 표준 형식으로 전처리
    if tile_data_high_res.dtype != np.uint8:
        if tile_data_high_res.dtype == np.uint16:  #16비트 값으로 줄임
            tile_data_high_res = (tile_data_high_res / 256).astype(np.uint8) # /256 해서 범위 축소 후 unit8로 캐스팅
        elif tile_data_high_res.dtype in (np.float32, np.float64):   #float 데이터는 보통 정규화 된 값
            tile_data_high_res = (tile_data_high_res * 255).clip(0, 255).astype(np.uint8) # x255 해서 0~255 범위로 반환
        else:
            tile_data_high_res = tile_data_high_res.astype(np.uint8) # 그 외 타입은 스케일링 없이 형 변환, 범위 밖 값이면 잘려서 들어감

    # 5. PIL Image로 변환 후 리사이즈(다운샘플링)
    # 채널 처리
    # mode = 'L' 흑백
    if tile_data_high_res.ndim == 3: 
        if C == 1: # (H, W, 1) 형태 , 마지막 차원(채널)이 흑백이미지
            mode = 'L'
            tile_data_high_res = tile_data_high_res.squeeze(axis=2) # squeeze(axis=2)로 채널 차원을 없앰 -> (H,W) 형태로 반환
        elif C >= 3: # RGB 또는 RGBA (3채널 이상)
            mode = 'RGB'
            tile_data_high_res = tile_data_high_res[:, :, :3] # 3채널로 강제
        else: # 그 외의 경우 (예: 2채널) -> 흑백 처리
            mode = 'L'
            tile_data_high_res = tile_data_high_res[:, :, 0]
    else: # 흑백
        mode = 'L'
        
    img = Image.fromarray(tile_data_high_res, mode=mode) #최종적으로 PIL이 이해할 수 있는 객체로 변환
    
    # 최종 타일 크기 계산 (경계 타일의 경우 tile_size보다 작음)
    # 여기서 ceil을 사용하여 0이 되는 것을 방지
    target_width = math.ceil(read_width / scale) #ceil = 소수점 올림 (최소 1픽셀은 남게 저장)
    target_height = math.ceil(read_height / scale)

    # 안티에일리어싱을 적용하여 리사이즈
    resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS) #Image.Resampling.LANCZOS : 고품질 다운샘플링
    
    # 6. 경계 타일 패딩 처리
    # 최종 타일이 512x512가 아니라면, 배경으로 채워진 512x512 이미지에 붙여넣기
    if resized_img.size != (tile_size, tile_size):
        # 최종적으로 RGB로 반환하는 것이 OSD에서 색상 문제 방지에 유리
        padded_img = Image.new('RGB', (tile_size, tile_size), (0, 0, 0))
        # 흑백 이미지인 경우 RGB로 변환하여 붙여넣기
        padded_img.paste(resized_img.convert('RGB'), (0, 0))
        return padded_img

    return resized_img.convert('RGB')


def create_dzi_from_image(input_path: Path, output_dir: Path, tile_size: int = 512, overlap: int = 0, format: str = "jpg"):
    """
    이미지 파일을 DZI 형식으로 미리 렌더링하여 저장 (버그 수정됨)
    """
    # 이미지 열기 및 RGB로 변환
    Image.MAX_IMAGE_PIXELS = None # 초대형 이미지 경고/차단 방지
    if input_path.suffix.lower() in {'.tif', '.tiff'}: #TIFF 처리 : PIL.Image로 래핑 ->RGB로 통일
        img_arr = tiff.imread(str(input_path))
        img = Image.fromarray(img_arr).convert('RGB')
    else:
        img = Image.open(input_path).convert('RGB')
    
    W, H = img.size
    max_level = lmax(W, H)  #deepzoom 촤대 레벨 
    
    # DZI 파일 이름 및 디렉토리 설정
    file_name = output_dir.stem
    dzi_files_dir = output_dir.parent / f"{file_name}_files"
    dzi_files_dir.mkdir(parents=True, exist_ok=True)
    
    # DZI XML 파일 생성
    # XML 필수 필드: TileSize, Overlap, Format, Size(Width/Height)
    # 뷰어가 이미지 피라미드를 이해하도록 메타데이터 제공
    dzi_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Image TileSize="{tile_size}" Overlap="{overlap}" Format="{format}" xmlns="http://schemas.microsoft.com/deepzoom/2008">
    <Size Width="{W}" Height="{H}"/>
</Image>'''
    
    with open(output_dir.parent / f"{file_name}.dzi", 'w') as f:
        f.write(dzi_xml)
    
    # 각 레벨별로 타일 생성
    for level in range(max_level + 1): 
        level_dir = dzi_files_dir / str(level)
        level_dir.mkdir(exist_ok=True)
        
        # 현재 레벨의 축척 및 크기 계산
        scale = 2 ** (max_level - level)
        
        # *** BUG FIX: int() 대신 math.ceil()을 사용하여 0이 되는 것을 방지 ***
        current_width = math.ceil(W / scale)
        current_height = math.ceil(H / scale)
        
        # 현재 레벨의 이미지 리사이즈
        if scale == 1:
            current_img = img
        else:
            current_img = img.resize((current_width, current_height), Image.Resampling.LANCZOS)
        
        # 레벨을 돌면서 각 레벨의 축소 비율을 계산, 현재 레벨 해상도의 이미지를 준비 
        
        # 타일 개수 계산
        #가로 세로 필요한 타일 계산
        cols = math.ceil(current_width / tile_size)
        rows = math.ceil(current_height / tile_size)
        
        # 각 타일 생성 및 저장
        for row in range(rows):
            for col in range(cols): #(row,col)마다 타일의 좌상단 픽셸 좌표 (x,y) 구함
                x = col * tile_size
                y = row * tile_size
                
                # 타일 크기 (경계 타일은 더 작을 수 있음)
                # 경계 타일 = 이미지의 가장자리에 걸쳐 있는 타일 , 고정크기 배수가 아닐 때 생기는 타일

                tile_w = min(tile_size, current_width - x)
                tile_h = min(tile_size, current_height - y)  # 남은 영역만큼 더 작을 수 있으므르  min으로 실제 크기 제한
                
                # 타일 추출
                tile = current_img.crop((x, y, x + tile_w, y + tile_h))
                
                # 최종 타일은 항상 tile_size x tile_size 여야 함 (필요시 패딩)
                #경계 타일이 작다면 검정 배경으로 정규화
                if tile.size != (tile_size, tile_size):
                    padded_tile = Image.new('RGB', (tile_size, tile_size), (0, 0, 0))
                    padded_tile.paste(tile, (0, 0))
                    tile_to_save = padded_tile
                else:
                    tile_to_save = tile
                
                # 파일로 저장
                tile_path = level_dir / f"{col}_{row}.{format}"
                tile_to_save.save(tile_path, quality=85)
   
        print(f"Level {level}: {cols}x{rows} tiles created at {level_dir}")   # 레벨별 가로 x 세로 타일 개수를 찍음
        
    return {
        "width": W,
        "height": H,
        "max_level": max_level,
        "tile_size": tile_size,
        "overlap": overlap,
        "dzi_path": str(output_dir.parent / f"{file_name}.dzi") # 호출자에게 DZI 경로 응답
    }

# 스크립트로 실행될 때의 동작 (테스트용)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert large images to Zarr or pre-rendered DZI tiles.")
    parser.add_argument("command", choices=['to-zarr', 'to-dzi'], help="The command to execute.")
    parser.add_argument("input_path", type=Path, help="Path to the input image file.")
    parser.add_argument("output_path", type=Path, help="Path to the output Zarr store or DZI file name.")
    
    args = parser.parse_args()
    
    if args.command == 'to-zarr':
        if not args.output_path.suffix == '.zarr':
            print("Error: Output for 'to-zarr' must end with .zarr")
        else:
            result = ingest_to_zarr(args.input_path, args.output_path)
            print("Wrote Zarr store:", args.output_path)
            print("Metadata:", result)
    elif args.command == 'to-dzi':
        result = create_dzi_from_image(args.input_path, args.output_path)
        print("\nWrote DZI files.")
        print("Metadata:", result)
