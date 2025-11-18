import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tifffile as tiff

# ================= 설정 =================
W, H = 40960, 40960   # 40k x 40k → 약 5 GB
TILE = 512            # 그리기 단위
OUTFILE = "checker_coords_rgb8_4GiB_plus.tif"

LIGHT, DARK = 200, 55
GRID_RGB = (128,128,128)
GRID_THICK = 2

FONT_PATH = None
FONT_BASE = 24
FG_LIGHT = (255,255,255)
FG_DARK  = (0,0,0)
BG_LIGHT = (30,30,30)
BG_DARK  = (200,200,200)
LABEL_PAD = 10
LABEL_STROKE = 2
# =======================================

def human_bytes(n):
    units = ["B","KB","MB","GB","TB"]
    i=0; x=float(n)
    while x>=1024 and i<len(units)-1:
        x/=1024; i+=1
    return f"{x:.2f} {units[i]}"

def make_font(tile_pixels, font_path):
    size = max(FONT_BASE, tile_pixels // 6)
    try:
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()

def draw_center_label(pil_img, text, font, fg, bg, pad=8, stroke=2):
    draw = ImageDraw.Draw(pil_img)
    try:
        bbox = draw.textbbox((0,0), text, font=font, stroke_width=stroke)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        tw, th = draw.textsize(text, font=font)
    Wp, Hp = pil_img.size
    x = (Wp - tw)//2; y = (Hp - th)//2
    box = (max(0,x-pad), max(0,y-pad), min(Wp,x+tw+pad), min(Hp,y+th+pad))
    draw.rectangle(box, fill=bg)
    stroke_fill = (0,0,0) if (sum(fg)/3)>127 else (255,255,255)
    draw.text((x,y), text, fill=fg, font=font,
              stroke_width=stroke, stroke_fill=stroke_fill)

def main():
    outpath = os.path.abspath(OUTFILE)
    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)

    est = W*H*3
    print(f"[INFO] 예상 크기: {W} x {H} x 3 ≈ {human_bytes(est)}")
    print(f"[INFO] 출력 파일: {outpath}")

    arr = tiff.memmap(outpath, shape=(H, W, 3), dtype=np.uint8, bigtiff=True)

    tiles_y = math.ceil(H/TILE)
    tiles_x = math.ceil(W/TILE)
    font = make_font(TILE, FONT_PATH)

    for ty in range(tiles_y):
        y0 = ty*TILE; y1 = min(H, y0+TILE); th = y1-y0
        for tx in range(tiles_x):
            x0 = tx*TILE; x1 = min(W, x0+TILE); tw = x1-x0
            base = LIGHT if ((tx+ty)%2==0) else DARK
            tile_rgb = np.full((th,tw,3), base, dtype=np.uint8)
            if GRID_RGB is not None:
                t = min(GRID_THICK, th); s = min(GRID_THICK, tw)
                tile_rgb[:t,:,:]  = GRID_RGB
                tile_rgb[-t:,:,:] = GRID_RGB
                tile_rgb[:,:s,:]  = GRID_RGB
                tile_rgb[:,-s:,:] = GRID_RGB
            label = f"({x0:,}, {y0:,})"
            pil = Image.fromarray(tile_rgb)
            if base == DARK:
                draw_center_label(pil, label, font, fg=FG_DARK, bg=BG_DARK,
                                  pad=LABEL_PAD, stroke=LABEL_STROKE)
            else:
                draw_center_label(pil, label, font, fg=FG_LIGHT, bg=BG_LIGHT,
                                  pad=LABEL_PAD, stroke=LABEL_STROKE)
            arr[y0:y1, x0:x1, :] = np.asarray(pil, dtype=np.uint8)
        print(f"[PROGRESS] row {ty+1}/{tiles_y} 완료")

    del arr
    print(f"[OK] 저장 완료: {outpath}")

    # 검증
    with tiff.TiffFile(outpath) as tf:
        print(f"[CHECK] is_bigtiff={tf.is_bigtiff}, shape={tf.pages[0].shape}")

if __name__ == "__main__":
    main()
