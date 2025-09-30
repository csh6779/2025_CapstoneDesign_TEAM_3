import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tifffile as tiff

# ================= 설정 =================
# 목표 해상도 (8bit Gray: 용량 = W * H 바이트)
W, H = 65536, 65536     # 65536^2 = 4,294,967,296 bytes ≈ 4.00 GiB
# H = 66000             # (선택) BigTIFF 강제 유도: ≈ 4.03 GiB

# 타일 크기 (메모리/성능 밸런스, NG/OSD 변환도 고려)
TILE = 512

# 바둑판(타일 단위) 밝기
LIGHT, DARK = 200, 55

# 타일 경계선(그리드) 표시 (None이면 미표시)
GRID_VAL = 128
GRID_THICK = 2  # 픽셀

# 라벨(타일마다 1개, 타일 중앙)
FONT_PATH = None  # 예: r"C:\Windows\Fonts\malgun.ttf" (한글 라벨 선명)
FONT_BASE = 24    # 폰트 최소 크기
LABEL_FG_LIGHT = 255  # 밝은 글자(흰색)
LABEL_FG_DARK  = 0    # 어두운 글자(검정)
LABEL_BG_LIGHT = 30   # 어두운 배경 박스
LABEL_BG_DARK  = 200  # 밝은 배경 박스
LABEL_PAD = 10
LABEL_STROKE = 2

# 출력 파일명
OUTFILE = "checker_coords_gray8_4GiB.tif"
# =======================================


def human_bytes(n):
    units = ["B","KB","MB","GB","TB"]
    i = 0
    x = float(n)
    while x >= 1024 and i < len(units)-1:
        x /= 1024; i += 1
    return f"{x:.2f} {units[i]}"


def make_font(tile_pixels, font_path):
    # 타일 크기에 비례한 폰트(타일의 약 1/6)
    size = max(FONT_BASE, tile_pixels // 6)
    try:
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def draw_center_label_L(pil_img, text, font, fg, bg, pad=8, stroke=2):
    """그레이스케일(L) 이미지 중앙에 배경 박스 + 외곽선 + 텍스트."""
    draw = ImageDraw.Draw(pil_img)
    try:
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        tw, th = draw.textsize(text, font=font)  # 구버전 Pillow 호환
    W, H = pil_img.size
    x = (W - tw) // 2
    y = (H - th) // 2

    # 배경 박스
    box = (max(0, x - pad), max(0, y - pad),
           min(W, x + tw + pad), min(H, y + th + pad))
    draw.rectangle(box, fill=bg)

    # 텍스트 + 외곽선
    try:
        draw.text((x, y), text, fill=fg, font=font,
                  stroke_width=stroke, stroke_fill=(0 if fg > 127 else 255))
    except TypeError:
        # stroke 미지원 Pillow 대체: 주변 4방 오프셋으로 의사 외곽선
        edge = (0 if fg > 127 else 255)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            draw.text((x+dx, y+dy), text, fill=edge, font=font)
        draw.text((x, y), text, fill=fg, font=font)


def main():
    outpath = os.path.abspath(OUTFILE)
    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)

    est = W * H  # 8bit Gray
    print(f"[INFO] Size: {W} x {H}  ≈ {human_bytes(est)}")
    print(f"[INFO] Output: {outpath}")
    print("[INFO] Creating BigTIFF via memmap...")

    # tifffile.memmap: 큰 파일이면 자동 BigTIFF.
    # (최신 버전은 bigtiff=True 인자를 지원. 안전하게 쓰고 싶다면 아래 주석 해제)
    # arr = tiff.memmap(outpath, shape=(H, W), dtype=np.uint8, bigtiff=True)
    arr = tiff.memmap(outpath, shape=(H, W), dtype=np.uint8)

    tiles_y = math.ceil(H / TILE)
    tiles_x = math.ceil(W / TILE)

    # 폰트(타일 크기 스케일)
    font = make_font(TILE, FONT_PATH)

    for ty in range(tiles_y):
        y0 = ty * TILE
        y1 = min(H, y0 + TILE)
        th = y1 - y0

        for tx in range(tiles_x):
            x0 = tx * TILE
            x1 = min(W, x0 + TILE)
            tw = x1 - x0

            # 바둑판(타일 단위로 LIGHT/DARK 선택)
            base = LIGHT if ((tx + ty) % 2 == 0) else DARK
            tile = np.full((th, tw), base, dtype=np.uint8)

            # 타일 경계선(옵션)
            if GRID_VAL is not None:
                g = GRID_VAL
                t = min(GRID_THICK, th)
                s = min(GRID_THICK, tw)
                tile[:t, :], tile[-t:, :] = g, g
                tile[:, :s], tile[:, -s:] = g, g

            # 좌표 라벨 (타일 좌상단 (x0,y0))
            label = f"({x0:,}, {y0:,})"
            pil = Image.fromarray(tile, mode="L")
            if base == DARK:
                # 어두운 타일 → 밝은 배경 + 검은 글자
                draw_center_label_L(pil, label, font,
                                    fg=LABEL_FG_DARK, bg=LABEL_BG_DARK,
                                    pad=LABEL_PAD, stroke=LABEL_STROKE)
            else:
                # 밝은 타일 → 어두운 배경 + 흰 글자
                draw_center_label_L(pil, label, font,
                                    fg=LABEL_FG_LIGHT, bg=LABEL_BG_LIGHT,
                                    pad=LABEL_PAD, stroke=LABEL_STROKE)

            arr[y0:y1, x0:x1] = np.asarray(pil, dtype=np.uint8)

        print(f"[PROGRESS] row {ty+1}/{tiles_y} written")

    # flush
    del arr
    print(f"[OK] Saved: {outpath}")
    print("[TIP] 라벨은 충분히 줌인(1:1 근처)해야 선명하게 보입니다.")
    print("[TIP] OSD(DZI)나 Neuroglancer 변환 시 PNG 인코딩을 권장(텍스트 보존).")


if __name__ == "__main__":
    main()