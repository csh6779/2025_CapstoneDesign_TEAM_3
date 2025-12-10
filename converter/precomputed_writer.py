import os
import sys
import json
import time
import struct
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
# [Loader 1] 초고속 BMP 로더 (NumPy Memory Map)
# ========================================================================
class FastBMPLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mmap = None
        self._parse_header()
        self.mmap = np.memmap(self.file_path, dtype='uint8', mode='r')

    def _parse_header(self):
        with open(self.file_path, 'rb') as f:
            header = f.read(26)
            if header[:2] != b'BM': raise ValueError("Invalid BMP")
            self.data_offset = struct.unpack('<I', header[10:14])[0]
            self.width = struct.unpack('<i', header[18:22])[0]
            self.height = struct.unpack('<i', header[22:26])[0]
            self.is_bottom_up = self.height > 0
            self.height = abs(self.height)
            self.row_stride = ((self.width * 3 * 8 + 31) // 32) * 4

    def get_crop(self, x, y, w, h):
        x_end, y_end = min(x + w, self.width), min(y + h, self.height)
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
            crop = raw[:, x*3 : (x+real_w)*3].reshape((real_h, real_w, 3))
            img = crop[..., ::-1]
            if self.is_bottom_up: img = np.flipud(img)
            return img.copy()
        except Exception:
            return None

    def close(self):
        if self.mmap is not None: del self.mmap

# ========================================================================
# [Loader 2] 만능 로더 (JPG, PNG, TIF용 - Pyvips)
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
# [Worker] 타일 저장 작업
# ========================================================================
def save_tile(loader, x, y, chunk, out_dir):
    try:
        data = loader.get_crop(x, y, chunk, chunk)
        if data is None: return 0

        h, w = data.shape[:2]
        out_path = os.path.join(out_dir, f"{x}-{x+w}_{y}-{y+h}_0-1")

        if not data.flags['C_CONTIGUOUS']:
            data = np.ascontiguousarray(data)
            
        with open(out_path, "wb") as f:
            f.write(data.tobytes())
        return 1
    except Exception:
        return 0

# ========================================================================
# [Main] 실행 로직
# ========================================================================
def main():
    # 1. 설정 파일 로드 (시작 시 한 번만 수행)
    config_file = Path(__file__).parent / "output_directory.txt"
    out_root = "F:\\precomputed"
    chunk_size = 512

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if len(lines) >= 1: out_root = lines[0].strip('"')
                if len(lines) >= 2: 
                    try:
                        val = int(lines[1])
                        if val > 0: chunk_size = val
                    except ValueError: pass
            print(f"📂 설정 로드: {out_root} (Chunk: {chunk_size})")
        except Exception as e:
            print(f"⚠️ 설정 오류: {e}")

    # ===== 메인 루프 (N 선택 시 여기로 돌아옴) =====
    while True:
        print("\n" + "="*50)
        path = input("📁 이미지 파일 경로 입력 (종료: Enter): ").strip().strip('"')
        if not path: break
        
        if not os.path.exists(path): 
            print("❌ 파일이 존재하지 않습니다."); continue

        ext = Path(path).suffix.lower()
        
        # 2. 로더 초기화
        try:
            if ext == ".bmp":
                loader = FastBMPLoader(path)
                mode_str = "🚀 BMP Ultra-Fast (Memmap)"
            else:
                loader = UniversalLoader(path)
                mode_str = f"🐢 Universal ({ext.upper()})"
        except Exception as e:
            print(f"❌ 로드 실패: {e}"); continue

        W, H = loader.width, loader.height
        total_chunks = ((W + chunk_size - 1) // chunk_size) * ((H + chunk_size - 1) // chunk_size)
        
        # 3. 🔍 작업 요약 및 최종 확인
        print("-" * 50)
        print(f"   [작업 요약]")
        print(f"   ▶ 파일명 : {Path(path).name}")
        print(f"   ▶ 해상도 : {W:,} x {H:,}")
        print(f"   ▶ 모  드 : {mode_str}")
        print(f"   ▶ 청  크 : {chunk_size}px (총 {total_chunks:,}개)")
        print(f"   ▶ 저  장 : {out_root}")
        print("-" * 50)

        confirm = input("🔥 변환을 시작할까요? [y/n]: ").lower().strip()
        
        if confirm != 'y':
            print("🚫 취소되었습니다. 다시 처음으로 돌아갑니다.")
            loader.close() # 자원 해제 후 재시작
            continue

        # 4. 변환 시작
        workers = min(os.cpu_count() + 4, 32)
        name = Path(path).stem
        scale_dir = Path(out_root) / name / "0"
        os.makedirs(scale_dir, exist_ok=True)

        info = {
            "type": "image", "data_type": "uint8", "num_channels": 3,
            "scales": [{
                "chunk_sizes": [[chunk_size, chunk_size, 1]],
                "encoding": "raw", "key": "0", "resolution": [1, 1, 1],
                "size": [W, H, 1], "voxel_offset": [0, 0, 0]
            }]
        }
        with open(scale_dir.parent / "info", "w") as f: json.dump(info, f)
        with open(scale_dir.parent / "provenance", "w") as f: json.dump({"source": name}, f)

        print(f"\n🚀 작업을 시작합니다! (스레드: {workers})")
        start_time = time.time()
        processed = 0
        log_interval = max(1, total_chunks // 100) # 1% 단위

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(save_tile, loader, x, y, chunk_size, str(scale_dir))
                for y in range(0, H, chunk_size)
                for x in range(0, W, chunk_size)
            ]
            
            for _ in concurrent.futures.as_completed(futures):
                processed += 1
                if processed % log_interval == 0 or processed == total_chunks:
                    elapsed = time.time() - start_time
                    pct = (processed / total_chunks) * 100
                    speed = processed / elapsed if elapsed > 0 else 0
                    eta = (total_chunks - processed) / speed if speed > 0 else 0
                    
                    print(f"\r⚡ 진행률: {pct:.1f}% ({processed:,}/{total_chunks:,}) | "
                          f"속도: {speed:.0f} tiles/s | 남은시간: {eta:.0f}초   ", end="")

        loader.close()
        print(f"\n✨ 변환 완료! 총 {time.time() - start_time:.1f}초 소요.")
        print("="*50 + "\n")

if __name__ == "__main__":
    main()