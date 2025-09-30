#!/bin/bash

echo "DZI 로컬 변환기 실행"
echo "========================"

# 로그 폴더 생성
mkdir -p logs

echo ""
echo "사용 가능한 명령어:"
echo "  python batch_dzi_converter.py --help                    # 도움말"
echo "  python batch_dzi_converter.py --dry-run                # 파일 목록만 확인"
echo "  python batch_dzi_converter.py                          # 기본 설정으로 변환"
echo "  python batch_dzi_converter.py --workers 4              # 4개 작업자로 변환"
echo "  python batch_dzi_converter.py --tile-size 256          # 256x256 타일로 변환"
echo ""

# 기본 변환 실행
echo "기본 설정으로 모든 이미지를 DZI로 변환합니다..."
python batch_dzi_converter.py

echo ""
echo "변환 완료! 로그를 확인하세요: logs/dzi_conversion.log"
