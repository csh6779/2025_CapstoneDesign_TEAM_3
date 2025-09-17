#!/usr/bin/env python3
"""
배치 DZI 변환기
original/ 폴더의 이미지 파일들을 DZI 형식으로 변환하여 dzi/ 폴더에 저장
로컬에서 직접 실행 가능
"""

import os
import sys
from pathlib import Path
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 현재 스크립트 위치를 기준으로 경로 설정
script_dir = Path(__file__).parent.resolve()
project_root = script_dir.parent

# 로컬 실행을 위한 경로 설정
if (project_root / "server" / "util_zarr.py").exists():
    # 프로젝트 내부에서 실행
    sys.path.insert(0, str(project_root / "server"))
    from util_zarr import create_dzi_from_image
elif (script_dir / "util_zarr.py").exists():
    # utility 폴더에 util_zarr.py가 있는 경우
    sys.path.insert(0, str(script_dir))
    from util_zarr import create_dzi_from_image
else:
    # 로컬 환경에서 실행 (util_zarr.py가 같은 폴더에 있는 경우)
    try:
        from util_zarr import create_dzi_from_image
    except ImportError:
        print("❌ 오류: util_zarr.py를 찾을 수 없습니다.")
        print("   다음 중 하나를 확인하세요:")
        print("   1. utility/ 폴더에 util_zarr.py 파일이 있는지 확인")
        print("   2. server/ 폴더에 util_zarr.py 파일이 있는지 확인")
        print("   3. PYTHONPATH에 util_zarr.py 경로를 추가")
        print(f"   현재 스크립트 위치: {script_dir}")
        print(f"   프로젝트 루트: {project_root}")
        sys.exit(1)

# 로깅 설정
log_dir = script_dir / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'dzi_conversion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_image_files(original_dir: Path, target_file: str = None):
    """original 폴더에서 지원되는 이미지 파일들을 찾습니다."""
    supported_extensions = {'.tif', '.tiff', '.png', '.bmp', '.jpg', '.jpeg'}
    image_files = []
    
    if target_file:
        # 특정 파일명으로 검색
        target_path = original_dir / target_file
        if target_path.exists():
            # 확장자가 지원되는 형식인지 확인
            if target_path.suffix.lower() in supported_extensions:
                return [target_path]
            else:
                logger.warning(f"지원되지 않는 파일 형식: {target_path.suffix}")
                return []
        else:
            # 확장자가 없는 경우 지원되는 확장자로 검색
            for ext in supported_extensions:
                test_path = original_dir / f"{target_file}{ext}"
                if test_path.exists():
                    return [test_path]
                test_path = original_dir / f"{target_file}{ext.upper()}"
                if test_path.exists():
                    return [test_path]
            
            logger.warning(f"파일을 찾을 수 없습니다: {target_file}")
            return []
    
    # 모든 이미지 파일 검색
    for ext in supported_extensions:
        image_files.extend(original_dir.glob(f"*{ext}"))
        image_files.extend(original_dir.glob(f"*{ext.upper()}"))
    
    return sorted(image_files)

def convert_single_image(input_path: Path, output_dir: Path, tile_size: int = 512, overlap: int = 0):
    """단일 이미지를 DZI로 변환합니다."""
    try:
        start_time = time.time()
        logger.info(f"변환 시작: {input_path.name}")
        
        # 출력 디렉토리 생성
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # DZI 변환 실행
        result = create_dzi_from_image(
            input_path=input_path,
            output_dir=output_dir / input_path.stem,
            tile_size=tile_size,
            overlap=overlap,
            format="jpg"
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"변환 완료: {input_path.name} -> {elapsed_time:.1f}초")
        logger.info(f"  크기: {result['width']}x{result['height']}, 레벨: {result['max_level']}")
        
        return {
            'input': str(input_path),
            'output': result['dzi_path'],
            'success': True,
            'elapsed_time': elapsed_time,
            'metadata': result
        }
        
    except Exception as e:
        logger.error(f"변환 실패: {input_path.name} - {str(e)}")
        return {
            'input': str(input_path),
            'output': None,
            'success': False,
            'error': str(e)
        }

def batch_convert_images(original_dir: Path, dzi_dir: Path, max_workers: int = 2, tile_size: int = 512, overlap: int = 0, target_file: str = None):
    """여러 이미지를 배치로 DZI로 변환합니다."""
    image_files = get_image_files(original_dir, target_file)
    
    if not image_files:
        if target_file:
            logger.warning(f"변환할 파일을 찾을 수 없습니다: {target_file}")
        else:
            logger.warning(f"변환할 이미지 파일을 찾을 수 없습니다: {original_dir}")
        return []
    
    if target_file:
        logger.info(f"파일 '{target_file}'을(를) DZI로 변환합니다:")
    else:
        logger.info(f"총 {len(image_files)}개 이미지 파일을 찾았습니다:")
    
    for img_file in image_files:
        file_size_mb = img_file.stat().st_size / (1024 * 1024)
        logger.info(f"  - {img_file.name} ({file_size_mb:.1f}MB)")
    
    # 출력 디렉토리 생성
    dzi_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # 병렬 처리로 변환
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 변환 작업 제출
        future_to_file = {
            executor.submit(
                convert_single_image, 
                img_file, 
                dzi_dir, 
                tile_size, 
                overlap
            ): img_file for img_file in image_files
        }
        
        # 완료된 작업 처리
        for future in as_completed(future_to_file):
            img_file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"작업 실행 중 오류: {img_file.name} - {str(e)}")
                results.append({
                    'input': str(img_file),
                    'output': None,
                    'success': False,
                    'error': f"작업 실행 오류: {str(e)}"
                })
    
    return results

def print_summary(results):
    """변환 결과 요약을 출력합니다."""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print("\n" + "="*60)
    print("DZI 변환 결과 요약")
    print("="*60)
    
    if successful:
        total_time = sum(r.get('elapsed_time', 0) for r in successful)
        print(f"✅ 성공: {len(successful)}개")
        print(f"⏱️  총 소요 시간: {total_time:.1f}초")
        print(f"📊 평균 처리 시간: {total_time/len(successful):.1f}초/파일")
        
        print("\n성공한 파일들:")
        for result in successful:
            file_size_mb = Path(result['input']).stat().st_size / (1024 * 1024)
            print(f"  ✓ {Path(result['input']).name} ({file_size_mb:.1f}MB) -> {result['elapsed_time']:.1f}초")
    
    if failed:
        print(f"\n❌ 실패: {len(failed)}개")
        for result in failed:
            print(f"  ✗ {Path(result['input']).name}: {result['error']}")
    
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="배치 DZI 변환기")
    parser.add_argument(
        "--original-dir", 
        type=Path, 
        default=script_dir.parent / "data" / "uploads" / "original",
        help="원본 이미지 폴더 경로 (기본값: ../data/uploads/original)"
    )
    parser.add_argument(
        "--dzi-dir", 
        type=Path, 
        default=script_dir.parent / "data" / "dzi",
        help="DZI 출력 폴더 경로 (기본값: ../data/dzi)"
    )
    parser.add_argument(
        "--file", 
        type=str,
        help="변환할 특정 파일명 (확장자 제외 가능, 예: 'wafer' 또는 'wafer.bmp')"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=2,
        help="동시 처리할 작업 수 (기본값: 2)"
    )
    parser.add_argument(
        "--tile-size", 
        type=int, 
        default=512,
        help="타일 크기 (기본값: 512)"
    )
    parser.add_argument(
        "--overlap", 
        type=int, 
        default=0,
        help="타일 오버랩 (기본값: 0)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="실제 변환 없이 파일 목록만 출력"
    )
    
    args = parser.parse_args()
    
    # 경로 정규화
    original_dir = args.original_dir.resolve()
    dzi_dir = args.dzi_dir.resolve()
    
    # 경로 확인
    if not original_dir.exists():
        logger.error(f"원본 폴더를 찾을 수 없습니다: {original_dir}")
        logger.error(f"현재 스크립트 위치: {script_dir}")
        logger.error(f"프로젝트 루트: {project_root}")
        sys.exit(1)
    
    logger.info(f"원본 폴더: {original_dir}")
    logger.info(f"DZI 출력 폴더: {dzi_dir}")
    if args.file:
        logger.info(f"대상 파일: {args.file}")
    logger.info(f"동시 작업 수: {args.workers}")
    logger.info(f"타일 크기: {args.tile_size}")
    logger.info(f"타일 오버랩: {args.overlap}")
    
    if args.dry_run:
        logger.info("DRY RUN 모드 - 실제 변환은 수행하지 않습니다")
        image_files = get_image_files(original_dir, args.file)
        if args.file:
            print(f"\n파일 '{args.file}' 검색 결과:")
        else:
            print(f"\n변환할 이미지 파일들 ({len(image_files)}개):")
        for img_file in image_files:
            file_size_mb = img_file.stat().st_size / (1024 * 1024)
            print(f"  - {img_file.name} ({file_size_mb:.1f}MB)")
        return
    
    # 배치 변환 실행
    start_time = time.time()
    results = batch_convert_images(
        original_dir=original_dir,
        dzi_dir=dzi_dir,
        max_workers=args.workers,
        tile_size=args.tile_size,
        overlap=args.overlap,
        target_file=args.file
    )
    total_time = time.time() - start_time
    
    # 결과 출력
    print_summary(results)
    logger.info(f"전체 작업 완료: {total_time:.1f}초")

if __name__ == "__main__":
    main()
