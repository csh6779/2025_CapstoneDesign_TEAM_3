@echo off
REM Downloader 실행 스크립트
echo ========================================
echo Bidirectional Transfer Service START
echo ========================================

cd /d "%~dp0"

echo.
echo Docker Containers Build and START...
docker-compose up -d --build

echo.
echo ========================================
echo Service On!!
echo ========================================
echo.
echo WEB Interface Addr: http://localhost:8001
echo API: http://localhost:8001/docs
echo.
echo Log Check: docker-compose logs -f downloader
echo Stop: docker-compose down
echo ========================================

pause
