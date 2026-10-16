# PowerShell Automated Setup Script for NSE Quant Platform
# Run in PowerShell: .\setup_windows.ps1

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "         NSE QUANT PLATFORM - WINDOWS AUTOMATED SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "  Please install Python 3.11+ from https://www.python.org/downloads/ and check 'Add python.exe to PATH'." -ForegroundColor Red
    exit 1
}

# 2. Check Git
Write-Host "`n[2/6] Checking Git installation..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    Write-Host "  Found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "  [WARNING] Git not detected in PATH. Please install Git for Windows from https://git-scm.com/." -ForegroundColor Yellow
}

# 3. Create Virtual Environment
Write-Host "`n[3/6] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  Created virtual environment at .\.venv" -ForegroundColor Green
} else {
    Write-Host "  Virtual environment .\.venv already exists." -ForegroundColor Green
}

# 4. Install Dependencies
Write-Host "`n[4/6] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Failed to install dependencies." -ForegroundColor Red
    exit 1
}
Write-Host "  Dependencies successfully installed." -ForegroundColor Green

# 5. Setup Directories and .env
Write-Host "`n[5/6] Creating data directories and configuration..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "data\exports" | Out-Null
New-Item -ItemType Directory -Force -Path "data\backups" | Out-Null

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "  Created .env configuration file from .env.example." -ForegroundColor Green
        Write-Host "  NOTE: Update .env with your FYERS_APP_ID before authenticating." -ForegroundColor Cyan
    }
} else {
    Write-Host "  Existing .env configuration detected." -ForegroundColor Green
}

# 6. Run Database Migrations
Write-Host "`n[6/6] Initializing DuckDB database schema..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -c "from db.connection import get_db; db = get_db(); db.initialize_schema(); print('Database initialized.')"
Write-Host "  Database schema verified." -ForegroundColor Green

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Authenticate with Fyers:   .\.venv\Scripts\python.exe -m scripts.auth_cli --login" -ForegroundColor White
Write-Host "  2. Sync NSE Symbols:          .\.venv\Scripts\python.exe -m scripts.sync_symbols" -ForegroundColor White
Write-Host "  3. Start the Web App:         .\start_server.bat  (or python main.py)" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
