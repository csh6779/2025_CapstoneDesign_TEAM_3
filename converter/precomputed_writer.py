import os
import sys
import json
import time
import struct
import subprocess
import concurrent.futures
from pathlib import Path
import numpy as np

# Pyvips 필수 체크
try:
    import pyvips
    pyvips.cache_set_max(0)
    pyvips.cache_set_max_mem(0)
except ImportError:
    sys.exit("❌ pyvips 모듈이 필요합니다. (pip install pyvips)")

# ========================================================================
# [Disk Tuner] 디스크 타입 자동 감지 및 스레드 추천기
# ========================================================================
def get_optimal_workers(output_path):
    """
    저장 경로의 디스크 타입(SSD/HDD)을 감지하여 최적의 스레드 수를 반환합니다.
    """
    default_workers = min(os.cpu_count() + 4, 32) # 기본값 (SSD 기준)
    
    try:
        # 1. 드라이브 문자 추출 (예: "F:\Data" -> "F")
        drive_letter = os.path.splitdrive(os.path.abspath(output_path))[0].strip(':')
        if not drive_letter: return 8 # 경로가 이상하면 안전값 반환

        # 2. PowerShell 명령어로 디스크 타입 조회 (Windows 전용)
        # 명령: Get-Partition -DriveLetter X | Get-Disk | Select-Object MediaType
        cmd = f"powershell -Command \"Get-Partition -DriveLetter {drive_letter} | Get-Disk | Select-Object -ExpandProperty MediaType\""
        
        # 팝업창 없이 백그라운드에서 실행
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        media_type = result.stdout.strip().upper()

        print(f"   ⚙️ 디스크 감지: 드라이브 {drive_letter}: [{media_type}]")

        # 3. 타입에 따른 스레드 배정
        if 'SSD' in media_type:
            return default_workers  # SSD는 풀파워 (최대 32)
        elif 'HDD' in media_type:
            return 4  # HDD는 헤드 병목 방지를 위해 4개로 제한
        else:
            return 8  # USB나 알 수 없는 장치는 적당히 8개

    except Exception as e:
        print(f"   ⚠️ 디스크 감지 실패({e}). 기본값({default_workers})을 사용합니다.")
        return default_workers

# ========================================================================
# [Loader 1] FastBMPLoader (TB급 대응)
# ========================================================================
class FastBMPLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mmap = None
        self._parse_header()
        
        # 24비트나 8비트가 아니면 처리 불가 -> 에러 발생시켜서 Universal로 넘김
        if self.bpp not in [8, 24]:
            raise ValueError(f"지원하지 않는 비트 수({self.bpp}). UniversalLoader 사용 권장")

        self.mmap = np.memmap(self.file_path, dtype='uint8', mode='r')

    def _parse_header(self):
        with open(self.file_path, 'rb') as f:
            header = f.read(54)
            if header[:2] != b'BM': raise ValueError("BMP 형식이 아닙니다.")
            
            self.data_offset = struct.unpack('<I', header[10:14])[0]
            self.width = struct.unpack('<i', header[18:22])[0]
            self.height = struct.unpack('<i', header[22:26])[0]
            self.bpp = struct.unpack('<H', header[28:30])[0]
            compression = struct.unpack('<I', header[30:34])[0]

            if compression != 0: raise ValueError("압축된 BMP는 FastLoader 불가")

            self.is_bottom_up = self.height > 0
            self.height = abs(self.height)
            self.row_stride = ((self.width * self.bpp + 31) // 32) * 4
            self.channels = 3 if self.bpp == 24 else 1

    def get_crop(self, x, y, w, h):
        x_end = min(x + w, self.width)
        y_end = min(y + h, self.height)
        real_w, real_h = x_end - x, y_end - y
        if real_w <= 0 or real_h <= 0: return None

        if self.is_bottom_up:
            s_row, e_row = self.height - y_end, self.height - y
        else:
            s_row, e_row = y, y_end

        start = self.data_offset + s_row * self.row_stride
        end = self.data_offset + e_row * self.row_stride
        
        try:
            raw = self.mmap[start:end].reshape((real_h, self.row_stride))
            
            if self.bpp == 24:
                crop = raw[:, x*3 : (x+real_w)*3].reshape((real_h, real_w, 3))
                img = crop[..., ::-1] # BGR -> RGB
            elif self.bpp == 8:
                img = raw[:, x : x+real_w].reshape((real_h, real_w, 1))
            
            if self.is_bottom_up: img = np.flipud(img)
            return img.copy()
        except Exception:
            return None

    def close(self):
        if self.mmap is not None: del self.mmap

# ========================================================================
# [Loader 2] UniversalLoader (Pyvips)
# ========================================================================
class UniversalLoader:
    def __init__(self, file_path):
        self.img = pyvips.Image.new_from_file(file_path, access='random')
        self.width = self.img.width
        self.height = self.img.height
        self.channels = self.img.bands

    def get_crop(self, x, y, w, h):
        try:
            if x >= self.width or y >= self.height: return None
            real_w = min(w, self.width - x)
            real_h = min(h, self.height - y)
            
            crop_region = self.img.crop(x, y, real_w, real_h)
            np_img = crop_region.numpy()
            
            if np_img.ndim == 2: np_img = np_img[..., np.newaxis]
            if np_img.shape[2] == 4: np_img = np_img[..., :3]
            return np_img
        except Exception:
            return None

    def close(self):
        self.img = None

# ========================================================================
# [Worker] 타일 저장
# ========================================================================
def save_tile(loader, x, y, chunk, out_dir):
    try:
        data = loader.get_crop(x, y, chunk, chunk)
        if data is None:
            return 0

        # data: (H, W) or (H, W, C)
        if data.ndim == 2:
            data = data[..., np.newaxis]  # (H, W, 1)

        h, w, c = data.shape  # (y, x, channel)

        # ─────────────────────────────────────────────
        # 1) Neuroglancer 축 순서로 바꾸기: [x, y, z, channel]
        #    현재: (y, x, c) -> (x, y, 1, c)
        # ─────────────────────────────────────────────
        chunk_arr = np.transpose(data, (1, 0, 2))      # (W, H, C)
        chunk_arr = chunk_arr.reshape((w, h, 1, c))    # (X, Y, Z=1, C)

        # ─────────────────────────────────────────────
        # 2) Fortran order(열 우선)로 변환 후 저장
        # ─────────────────────────────────────────────
        chunk_arr = np.asfortranarray(chunk_arr)

        out_path = os.path.join(out_dir, f"{x}-{x+w}_{y}-{y+h}_0-1")

        with open(out_path, "wb") as f:
            f.write(chunk_arr.tobytes(order="F"))

        return 1

    except Exception as e:
        # 디버깅 도움 되도록 로그 찍어도 좋음
        # print(f"타일 저장 실패 ({x},{y}): {e}")
        return 0

# ========================================================================
# [Main] 메인 실행
# ========================================================================
def main():
    print("\n" + "★" * 50)
    print("★  [확인] 2025년 최신 수정 버전 코드가 실행 중입니다!  ★")
    print("★" * 50 + "\n")
    config_file = Path(__file__).parent / "output_directory.txt"
    out_root = "F:\\precomputed"
    chunk_size = 512

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if len(lines) >= 1: out_root = lines[0].strip('"')
                if len(lines) >= 2: 
                    try: val = int(lines[1]); 
                    except ValueError: pass
                    if val > 0: chunk_size = val
            print(f"📂 설정 로드: {out_root} (Chunk: {chunk_size})")
        except Exception: pass

    # 🔥 [자동 튜닝] 시작 전 디스크 타입 체크 🔥
    print("🔍 저장소 성능을 분석 중입니다...")
    optimal_workers = get_optimal_workers(out_root)
    print(f"✅ 최적 스레드 수 설정: {optimal_workers}개")

    while True:
        print("\n" + "="*50)
        path = input("📁 이미지 파일 경로 입력 (종료: Enter): ").strip().strip('"')
        if not path: break
        if not os.path.exists(path): 
            print("❌ 파일이 존재하지 않습니다."); continue

        ext = Path(path).suffix.lower()
        loader = None
        mode_str = ""
        
        # 1. 로더 자동 선택
        if ext == ".bmp":
            try:
                loader = FastBMPLoader(path)
                mode_str = "🚀 BMP Memmap Engine (TB-Ready)"
            except ValueError as e:
                print(f"⚠️ FastLoader 조건 불충족 -> Universal로 전환")
                loader = UniversalLoader(path)
                mode_str = "🐢 Universal Engine (Safety)"
        else:
            loader = UniversalLoader(path)
            mode_str = f"🐢 Universal Engine ({ext.upper()})"

        W, H = loader.width, loader.height
        
        # 2. 메타데이터 감지
        if isinstance(loader, UniversalLoader):
            channels = loader.channels 
            dtype_map = {'uchar': 'uint8', 'char': 'int8', 'ushort': 'uint16', 'short': 'int16'}
            ng_type = dtype_map.get(loader.img.format, 'uint8')
        else:
            channels = loader.channels
            ng_type = 'uint8'

        total_chunks = ((W + chunk_size - 1) // chunk_size) * ((H + chunk_size - 1) // chunk_size)
        
        print("-" * 50)
        print(f"   [작업 요약]")
        print(f"   ▶ 파일명 : {Path(path).name}")
        print(f"   ▶ 해상도 : {W:,} x {H:,}")
        print(f"   ▶ 타  입 : {ng_type} / {channels}ch")
        print(f"   ▶ 모  드 : {mode_str}")
        print(f"   ▶ 스레드 : {optimal_workers}개 (자동할당)")
        print("-" * 50)

        if input("🔥 시작할까요? [y/n]: ").lower().strip() != 'y':
            loader.close(); continue

        name = Path(path).stem
        scale_dir = Path(out_root) / name / "0"
        os.makedirs(scale_dir, exist_ok=True)

        info = {
            "type": "image", "data_type": ng_type, "num_channels": channels,
            "scales": [{"chunk_sizes": [[chunk_size, chunk_size, 1]], "encoding": "raw", 
                        "key": "0", "resolution": [1, 1, 1], "size": [W, H, 1], "voxel_offset": [0, 0, 0]}]
        }
        with open(scale_dir.parent / "info", "w") as f: json.dump(info, f)
        with open(scale_dir.parent / "provenance", "w") as f: json.dump({"source": name}, f)

        print(f"\n🚀 작업 시작 (스레드: {optimal_workers})...")
        start_time = time.time()
        processed = 0
        log_interval = max(1, total_chunks // 1000)

        # 🔥 자동 감지된 최적 스레드 수 적용
        with concurrent.futures.ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            futures = [executor.submit(save_tile, loader, x, y, chunk_size, str(scale_dir))
                       for y in range(0, H, chunk_size) for x in range(0, W, chunk_size)]
            
            for _ in concurrent.futures.as_completed(futures):
                processed += 1
                if processed % log_interval == 0 or processed == total_chunks:
                    elapsed = time.time() - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    eta = (total_chunks - processed) / speed if speed > 0 else 0
                    print(f"\r⚡ {processed:,}/{total_chunks:,} | {speed:.0f} tiles/s | ETA: {eta:.0f}s  ", end="")

        loader.close()
        print(f"\n✨ 완료! ({time.time() - start_time:.1f}초)")

if __name__ == "__main__":
    main()