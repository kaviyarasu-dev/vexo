@echo off
title NSE Quant Platform - Historical Data Downloader
cd /d "%~dp0"

echo ======================================================================
echo         NSE QUANT PLATFORM - HISTORICAL DATA DOWNLOAD LAUNCHER
echo ======================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Please run setup first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

:: Check if start_server.bat is currently running on port 8000
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %ERRORLEVEL% equ 0 goto :server_running
goto :server_ok

:server_running
echo [WARNING] The Web Server [start_server.bat] is currently running on port 8000!
echo DuckDB on Windows allows only ONE process to write to data\market_data.duckdb at a time.
echo.
echo INSTRUCTIONS TO DOWNLOAD:
echo   1. Go to your start_server.bat terminal window and press Ctrl+C to stop the server.
echo   2. Re-run '.\download_all.bat' to download your historical data.
echo   3. Once download completes or is paused with Ctrl+C, re-run '.\start_server.bat'.
echo.
echo ======================================================================
pause
exit /b 1

:server_ok

:: If command line arguments were passed directly, run immediately
if not "%~1"=="" (
    python scripts/run_historical_download.py %*
    exit /b %ERRORLEVEL%
)

:menu
echo Choose download universe for both 1D and 1m timeframes:
echo.
echo   [1] Fast Mode      : Nifty 50 (Tier 1 - 50 Top Equities)
echo   [2] Standard Mode  : Nifty 500 (Tiers 1, 2, 3 - 500 Equities) [Recommended]
echo   [3] Full Universe  : All Active Equities (Tiers 1, 2, 3, 4 - 2,500+ Stocks)
echo   [4] Custom Symbols : Enter ticker symbols manually
echo   [5] Exit
echo.
echo Note: Press Ctrl+C at any time to pause. Checkpoints resume automatically.
echo ======================================================================
set /p choice="Enter choice (1-5) [Default: 2]: "

if "%choice%"=="" set choice=2
if "%choice%"=="1" goto :fast
if "%choice%"=="2" goto :standard
if "%choice%"=="3" goto :full
if "%choice%"=="4" goto :custom
if "%choice%"=="5" goto :end

echo Invalid selection. Please choose 1 to 5.
echo.
goto :menu

:fast
echo.
echo [STARTING] Fast Mode: Nifty 50 (1D + 1m)...
python scripts/run_historical_download.py --timeframe both --tiers 1
goto :end

:standard
echo.
echo [STARTING] Standard Mode: Nifty 500 (1D + 1m)...
python scripts/run_historical_download.py --timeframe both --tiers 1,2,3
goto :end

:full
echo.
echo [STARTING] Full Universe: All 2,500+ NSE Equities (1D + 1m)...
python scripts/run_historical_download.py --all
goto :end

:custom
echo.
set /p custom_sym="Enter comma-separated symbols (e.g. NSE:TCS-EQ,NSE:INFY-EQ): "
if "%custom_sym%"=="" goto :menu
python scripts/run_historical_download.py --symbols %custom_sym% --timeframe both
goto :end

:end
echo.
echo ======================================================================
echo Download job finished or paused.
echo Run '.\.venv\Scripts\python.exe scripts/inspect_db.py' to inspect database stats.
echo ======================================================================
pause
