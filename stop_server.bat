@echo off
title NSE Quant Platform - Stop Server
cd /d "%~dp0"

echo ======================================================================
echo           NSE QUANT PLATFORM - STOP SERVER UTILITY
echo ======================================================================
echo.

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo [INFO] Found server running on port 8000 with PID: %%a
    echo [INFO] Terminating process %%a...
    taskkill /F /PID %%a >nul 2>&1
    set FOUND=1
)

:: Also clean up duckdb lock file if orphaned
if exist "data\market_data.duckdb.pid" (
    del /f /q "data\market_data.duckdb.pid" >nul 2>&1
)

if "%FOUND%"=="1" (
    echo.
    echo [SUCCESS] Server process stopped cleanly. DuckDB lock released!
) else (
    echo [INFO] No server process was running on port 8000.
)

echo.
echo ======================================================================
pause
