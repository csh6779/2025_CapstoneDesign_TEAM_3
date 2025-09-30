@echo off
REM UTF-8 인코딩 설정
chcp 65001 >nul 2>&1

echo DZI 로컬 변환기 실행
echo ========================

REM 로그 폴더 생성
if not exist "logs" mkdir logs

echo.
echo 사용 가능한 명령어:
echo   python batch_dzi_converter.py --help                    # 도움말
echo   python batch_dzi_converter.py --dry-run                # 파일 목록만 확인
echo   python batch_dzi_converter.py                          # 기본 설정으로 변환 (모든 파일)
echo   python batch_dzi_converter.py --file "wafer"           # 특정 파일만 변환
echo   python batch_dzi_converter.py --file "wafer.bmp"       # 특정 파일만 변환 (확장자 포함)
echo   python batch_dzi_converter.py --workers 4              # 4개 작업자로 변환
echo   python batch_dzi_converter.py --tile-size 256          # 256x256 타일로 변환
echo.

REM Python 경로 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo 오류: Python이 설치되지 않았거나 PATH에 없습니다.
    echo Python을 설치하고 PATH에 추가한 후 다시 시도하세요.
    pause
    exit /b 1
)

REM 기본 변환 실행
echo 기본 설정으로 모든 이미지를 DZI로 변환합니다...
python batch_dzi_converter.py

if errorlevel 1 (
    echo.
    echo 변환 중 오류가 발생했습니다. 로그를 확인하세요.
) else (
    echo.
    echo 변환 완료! 로그를 확인하세요: logs/dzi_conversion.log
)

pause
