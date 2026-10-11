@echo off
title NSE Quant Platform - Web Server
cd /d "%~dp0"

echo ======================================================================
echo           NSE QUANT PLATFORM - LOCAL APPLICATION LAUNCHER
echo ======================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run the setup first:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip.exe install -r requirements.txt
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
    )
)

if not exist "data" mkdir data
if not exist "data\exports" mkdir data\exports

echo [1/2] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [2/2] Starting FastAPI backend on http://127.0.0.1:8000 (Workers: 1)...
echo.
echo ======================================================================
echo  Open your web browser and navigate to: http://localhost:8000
echo  Press Ctrl+C in this window to stop the server.
echo ======================================================================
echo.

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --reload

pause

