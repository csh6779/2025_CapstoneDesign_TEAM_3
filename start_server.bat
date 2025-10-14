@echo off
REM Windows용 서버 시작 스크립트

echo ================================================
echo   Neuroglancer 대용량 뷰어 시스템 시작
echo ================================================
echo.

REM 가상환경 활성화 확인
if not exist ".venv\Scripts\activate.bat" (
    echo [오류] 가상환경을 찾을 수 없습니다.
    echo 먼저 다음 명령어를 실행하세요:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM 가상환경 활성화
call .venv\Scripts\activate.bat

echo [1/3] 가상환경 활성화 완료
echo.

REM 필요한 디렉터리 생성
if not exist "uploads" mkdir uploads
if not exist "uploads\temp" mkdir uploads\temp
echo [2/3] 디렉터리 생성 완료
echo.

REM 서버 시작
echo [3/3] 서버 시작 중...
echo.
echo ================================================
echo   서버 주소: http://localhost:8000
echo   API 문서: http://localhost:8000/docs
echo   서버를 중지하려면 Ctrl+C를 누르세요
echo ================================================
echo.

python -m app.Services.main

pause
