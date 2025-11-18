@echo off
setlocal

REM 이 배치파일이 있는 폴더로 이동 (C:\Users\csh67\Desktop\2025_CapstoneDesign_TEAM_3-BackEnd-Siwon\)
cd /d %~dp0

echo ================================================
echo   Neuroglancer 대용량 뷰어 시스템 통합 시작
echo ================================================
echo.

REM 가상환경 확인
if not exist ".venv\Scripts\activate.bat" (
    echo [오류] Python 가상환경(.venv)을 찾을 수 없습니다.
    echo 먼저 다음 명령을 실행하세요:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    goto :end
)

REM 1. Python 백엔드 (FastAPI / uvicorn)
echo [1/3] Python 백엔드 서버 실행...
echo     => API: http://localhost:8000/api/v1/...
start "BACKEND" cmd /k ^
"cd /d %~dp0 && call .venv\Scripts\activate.bat && ^
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM 2. React 프론트엔드 개발 서버
echo [2/3] React 프론트 서버 실행...
echo     => REACT: http://localhost:3000 (기본 포트)
start "FRONTEND" cmd /k ^
"cd /d %~dp0 && npm start"

REM 3. Neuroglancer 정적 파일 서버
echo [3/3] Neuroglancer 서버 실행...
echo     => Neuroglancer UI: http://localhost:8080  <-- 포트 수정
start "NEUROGLANCER" cmd /k ^
"cd /d %~dp0\neuroglancer\dist\client && python -m http.server 8080"  <-- 8080으로 수정

echo.
echo ================================================
echo   세 개의 서버를 각각 새 창에서 실행했습니다.
echo   각 창에서 Ctrl+C 를 누르면 해당 서버가 종료됩니다.
echo ================================================
echo.

:end
pause
endlocal