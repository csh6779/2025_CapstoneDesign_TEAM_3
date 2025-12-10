@echo off
chcp 65001 >nul
echo ============================================================
echo Precomputed Converter START
echo ============================================================
echo.

cd /d %~dp0

REM
call .venv_312\Scripts\activate
REM -----------------------------------------

REM
python .\precomputed_writer.py
pause