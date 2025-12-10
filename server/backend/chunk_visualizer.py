"""
청크 분리 로직 시각화 도구
"""

def visualize_chunking(width, height, chunk_size=512):
    """
    주어진 이미지 크기와 청크 크기에 대해 생성될 타일을 시각화
    """
    print(f"\n{'='*60}")
    print(f"이미지 크기: {width}×{height}")
    print(f"청크 크기: {chunk_size}×{chunk_size}")
    print(f"{'='*60}\n")
    
    tiles = []
    tile_count = 0
    
    for y0 in range(0, height, chunk_size):
        y1 = min(height, y0 + chunk_size)
        for x0 in range(0, width, chunk_size):
            x1 = min(width, x0 + chunk_size)
            
            tile_width = x1 - x0
            tile_height = y1 - y0
            filename = f"{x0}-{x1}_{y0}-{y1}_0-1"
            
            tile_count += 1
            tiles.append({
                'number': tile_count,
                'filename': filename,
                'x_range': (x0, x1),
                'y_range': (y0, y1),
                'size': (tile_width, tile_height),
                'pixels': tile_width * tile_height
            })
    
    # 타일 정보 출력
    print(f"생성될 타일 개수: {tile_count}개\n")
    
    for tile in tiles:
        print(f"타일 #{tile['number']}: {tile['filename']}")
        print(f"  - X 범위: {tile['x_range'][0]} ~ {tile['x_range'][1]}")
        print(f"  - Y 범위: {tile['y_range'][0]} ~ {tile['y_range'][1]}")
        print(f"  - 크기: {tile['size'][0]} x {tile['size'][1]} 픽셀")
        print(f"  - 총 픽셀: {tile['pixels']:,}개")
        print()
    
    # 통계
    total_pixels = sum(t['pixels'] for t in tiles)
    print(f"{'='*60}")
    print(f"통계:")
    print(f"  - 전체 픽셀: {width * height:,}개")
    print(f"  - 타일 픽셀 합: {total_pixels:,}개")
    print(f"  - 일치 여부: {'일치' if total_pixels == width * height else '불일치'}")
    
    # 그리드 패턴 출력
    print(f"\n그리드 패턴:")
    x_chunks = (width + chunk_size - 1) // chunk_size
    y_chunks = (height + chunk_size - 1) // chunk_size
    
    for y_idx in range(y_chunks):
        row = ""
        for x_idx in range(x_chunks):
            y0 = y_idx * chunk_size
            y1 = min(height, y0 + chunk_size)
            x0 = x_idx * chunk_size
            x1 = min(width, x0 + chunk_size)
            
            tile_w = x1 - x0
            tile_h = y1 - y0
            
            if tile_w == chunk_size and tile_h == chunk_size:
                row += "[F] "  # Full size
            else:
                row += "[P] "  # Partial
        print(f"  {row}")
    
    print(f"  ([F] = {chunk_size}x{chunk_size}, [P] = partial/edge)")
    print(f"{'='*60}\n")
    
    return tiles


if __name__ == "__main__":
    print("\n" + "="*60)
    print("청크 분리 로직 시뮬레이터")
    print("="*60)
    
    # 테스트 케이스들
    test_cases = [
        (512, 512, 512),   # 정확히 맞는 경우
        (512, 513, 512),   # 세로로 1픽셀 초과
        (513, 512, 512),   # 가로로 1픽셀 초과
        (513, 513, 512),   # 양쪽 다 1픽셀 초과
        (1024, 1024, 512), # 정확히 2x2
        (1000, 1000, 512), # 애매한 크기
    ]
    
    for width, height, chunk_size in test_cases:
        visualize_chunking(width, height, chunk_size)
        print("\n" + "-"*60 + "\n")
