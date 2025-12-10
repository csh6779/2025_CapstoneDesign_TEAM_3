@echo off
REM Downloader 중지 스크립트
echo ========================================
echo Bidirectional Transfer Service Stop
echo ========================================

cd /d "%~dp0"

docker-compose down

echo.
echo ========================================
echo Service Down
echo ========================================

pause
