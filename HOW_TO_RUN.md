# NSE Quant Platform — Complete Windows Setup & Execution Guide

This document is the **definitive, step-by-step guide** for installing, configuring, running, and maintaining the **NSE Quant Platform** on a fresh **local Windows machine** (Windows 10 / Windows 11).

---

## Table of Contents
1. [Platform Architecture & Prerequisites](#1-platform-architecture--prerequisites)
2. [External Applications & Accounts Needed](#2-external-applications--accounts-needed)
3. [One-Click Automated Setup (Quickest)](#3-one-click-automated-setup-quickest)
4. [Step-by-Step Manual Setup Walkthrough](#4-step-by-step-manual-setup-walkthrough)
5. [Fyers API Portal & OAuth Setup](#5-fyers-api-portal--oauth-setup)
6. [First-Time Authentication (Daily Token & 15-Day Refresh)](#6-first-time-authentication)
7. [Downloading Market Data (Symbols, Holidays & Candles)](#7-downloading-market-data)
8. [Running the Application Server](#8-running-the-application-server)
9. [Using the Platform (Features Overview)](#9-using-the-platform-features-overview)
10. [Running Security Audits & Test Suites](#10-running-security-audits--test-suites)
11. [Windows Troubleshooting & FAQ](#11-windows-troubleshooting--faq)

---

## 1. Platform Architecture & Prerequisites

The NSE Quant Platform is a self-directed quantitative equity research and backtesting platform built strictly for educational, analytical, and personal non-commercial research:
- **Backend**: Python 3.11+, FastAPI, Uvicorn (strictly `workers=1`).
- **Database Engine**: Embedded [DuckDB](https://duckdb.org/) (`data/market_data.duckdb`) with zero external database server required.
- **Frontend**: Single-Page Application (HTML5, Vanilla CSS, Vanilla JavaScript, TradingView Lightweight Charts).
- **Market Data Provider**: Fyers API v3 (REST endpoints for symbol master, historical 1-minute and 1-day candles, quotes, and option chains).
- **Security & Regulatory Model**:
  - Zero plaintext secrets in repository or code. Credentials stored in OS Keyring or AES-256 encrypted local vault (`data/.vault.enc`).
  - Strict compliance with SEBI Research Analyst regulations: All views, reports, and exports embed statutory **"Not Investment Advice"** notices.
  - **Architectural Hard Gate**: Automated order execution is strictly disabled; order-routing calls return **HTTP 403 Forbidden**.

---

## 2. External Applications & Accounts Needed

Before setting up the project, ensure you have installed the following external software:

### 2.1. Python 3.11 (or 3.12)
- **Download**: [Official Python Website](https://www.python.org/downloads/) (Download Python 3.11.x or 3.12.x for Windows 64-bit).
- **CRITICAL STEP DURING INSTALLATION**:
  > [!IMPORTANT]
  > On the first installer screen, you **MUST CHECK THE BOX**:  
  > `☑ Add python.exe to PATH`  
  > If you omit this, commands like `python` and `pip` will not work in PowerShell.
- **Verification**: Open PowerShell and run:
  ```powershell
  python --version
  ```
  *(Expected: `Python 3.11.x` or `Python 3.12.x`)*

### 2.2. Git for Windows
- **Download**: [git-scm.com/download/win](https://git-scm.com/download/win).
- **Installation**: Choose default options (Use Git from the command line, OpenSSH, etc.).
- **Verification**: In PowerShell:
  ```powershell
  git --version
  ```

### 2.3. Modern Web Browser
- Google Chrome, Microsoft Edge, Brave, or Mozilla Firefox with JavaScript enabled.

### 2.4. Fyers Trading Account & Developer Portal Credentials
To fetch real NSE market data, you need a free Fyers API App:
1. Open a Fyers trading account at [fyers.in](https://fyers.in/).
2. Log into the **Fyers API Dashboard**: [myapi.fyers.in](https://myapi.fyers.in/).
3. Click **"Create App"** (or **"New App"**):
   - **App Name**: `NSE Quant Platform`
   - **Redirect URI**: `https://127.0.0.1:5000/` *(Must match exactly, including https and trailing slash)*
   - **App Type**: `100` (Personal / Web) or `200`
   - **Permissions**: Read / Market Data / History
4. Note down your generated credentials:
   - **App ID / Client ID** (format: `{ALPHANUMERIC}-{APP_TYPE}`, e.g., `ABCD1234EF-100`)
   - **App Secret Key** (e.g., `jsvGf4pLiIz...`)
   - **4-Digit User PIN** (your trading login PIN)

### 2.5. (Optional but Recommended) Code Editor
- **VS Code**: [code.visualstudio.com](https://code.visualstudio.com/) with the Python extension.
- **Windows Terminal**: Available via the Microsoft Store for enhanced tabbed PowerShell sessions.

---

## 3. One-Click Automated Setup (Quickest)

If you prefer an automated setup, a PowerShell setup script and Windows batch launcher are provided in the repository root:

1. Open **PowerShell** and navigate to your project directory:
   ```powershell
   cd d:\trading-app
   ```
2. Enable script execution for your user account (if not already enabled):
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
   ```
3. Run the automated setup script:
   ```powershell
   .\setup_windows.ps1
   ```
   *This script automatically verifies Python, sets up `.venv`, upgrades pip, installs `requirements.txt`, creates required storage folders, and initializes the DuckDB database.*

---

## 4. Step-by-Step Manual Setup Walkthrough

If you prefer setting up manually or want full visibility into every step, follow this walkthrough:

### Step 4.1: Open PowerShell
Press `Win + X` and select **Terminal** or **Windows PowerShell**. Navigate to the project root:
```powershell
cd d:\trading-app
```

### Step 4.2: Create Python Virtual Environment (`.venv`)
Create an isolated virtual environment to prevent package conflicts with global Python:
```powershell
python -m venv .venv
```

### Step 4.3: Activate Virtual Environment
Activate the environment in PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(You will see `(.venv)` appear at the beginning of your command prompt)*

> [!NOTE]
> If PowerShell throws `File cannot be loaded because running scripts is disabled on this system`, run this once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
> ```
> Then re-run `.\.venv\Scripts\Activate.ps1`.

### Step 4.4: Upgrade Pip & Install Dependencies
Install all required libraries from [requirements.txt](file:///d:/trading-app/requirements.txt):
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4.5: Configure Environment Variables (`.env`)
Copy [.env.example](file:///d:/trading-app/.env.example) to `.env`:
```powershell
Copy-Item .env.example .env
```
Open `.env` in Notepad or your text editor:
```powershell
notepad .env
```
Update `FYERS_APP_ID` with your actual Fyers App ID:
```env
FYERS_APP_ID=YOUR_APP_ID-100
FYERS_REDIRECT_URI=https://127.0.0.1:5000/
AUTH_CREDENTIAL_STORAGE=KEYRING
DUCKDB_PATH=data/market_data.duckdb
EXPORT_DIR=data/exports
RATE_GOVERNOR_BURST_PER_SEC=10
RATE_GOVERNOR_TARGET_PER_MIN=180
RATE_GOVERNOR_DAILY_CAP=90000
DEFAULT_1M_HISTORY_YEARS=5
DEFAULT_1D_HISTORY_YEARS=15
LOG_LEVEL=INFO
UVICORN_WORKERS=1
```
Save and close the file.

> [!IMPORTANT]
> Do NOT store your secret key or 4-digit PIN in `.env`. The platform stores secrets securely in the Windows Credential Manager (OS Keyring) or the AES-256 encrypted local vault (`data/.vault.enc`).

### Step 4.6: Initialize Local Database & Folders
Ensure the required folders exist and initialize the DuckDB schema:
```powershell
New-Item -ItemType Directory -Force -Path "data\exports", "data\backups"
python -c "from db.connection import get_db; db = get_db(); db.initialize_schema(); print('DuckDB schema successfully initialized!')"
```

---

## 5. Fyers API Portal & OAuth Setup

Fyers API v3 uses OAuth 2.0 with a dual-token security architecture:
- **Access Token**: Valid daily until ~06:00 AM IST of the following morning.
- **Refresh Token**: Valid for 15 calendar days; automatically renews access tokens daily without requiring re-login.

### Confirm Your Fyers App Redirect URI
In [myapi.fyers.in](https://myapi.fyers.in/):
- App Redirect URI **must** be: `https://127.0.0.1:5000/`

---

## 6. First-Time Authentication

Authenticate with Fyers using the interactive CLI tool:

### Step 6.1: Run Authentication CLI
Make sure your virtual environment is active (`(.venv)` visible):
```powershell
python -m scripts.auth_cli --login
```

### Step 6.2: Complete Browser Login
1. The script will automatically open your default browser to the official Fyers authentication page.
2. Enter your registered mobile number, OTP, and trading PIN.
3. Upon successful login, your browser will redirect to a URL starting with:
   `https://127.0.0.1:5000/?s=ok&code=...&auth_code=...`
   *(It is completely normal if your browser displays "This site can't be reached" — this is simply the redirect callback)*.
4. Copy the entire `auth_code` parameter from your browser's address bar.
5. Paste the auth code back into the PowerShell terminal and press **Enter**.

### Step 6.3: Verify Authentication Status
Check your session validity and token expiration countdown:
```powershell
python -m scripts.auth_cli --status
```
**Expected Output:**
```
======================================================================
FYERS API v3 SESSION TELEMETRY
======================================================================
  Session Status:           ACTIVE / VALID
  Access Token Expiry:      ~06:00:00 AM IST Tomorrow
  Refresh Token Validity:   15 Days Remaining
  Storage Backend:          OS Keyring (Windows Credential Manager)
======================================================================
```

---

## 7. Downloading Market Data

Once authenticated, populate your local database with market data.

### Step 7.1: Synchronize NSE Universe & Trading Holidays
Download the active NSE symbol master, Nifty 50/100/200/500 constituent lists, and exchange holidays:
```powershell
python -m scripts.sync_symbols
```
*Time required: ~15 to 30 seconds.*

### Step 7.2: Fast Milestone 1 Verification (Reliance 5-Year Data)
To verify the historical downloader quickly without waiting for the full 500-stock universe:
```powershell
python -m scripts.run_m1_benchmark
```
*Downloads ~5 years of 1-minute candles for Reliance Industries (`NSE:RELIANCE-EQ`), resamples to multiple timeframes, and calculates indicators.*

### Step 7.3: Full Universe Historical Backfill (Optional / Overnight)
To perform a complete historical backfill of Nifty 500 stocks:
```powershell
python -m scripts.run_initial_backfill
```
*Adheres to the Fyers rate governor (Lane 1: 180 req/min, 10/s burst ceiling, 90,000 requests/day soft cap). The downloader tracks checkpoints in DuckDB and can be paused or resumed at any time without duplicate downloads.*

### Step 7.4: Daily Incremental Sync
To fetch today's newly closed candles after 15:40 IST on trading days:
```powershell
python -m scripts.run_daily_sync
```

---

## 8. Running the Application Server

You can start the web platform using either the one-click launcher or standard PowerShell command.

### Option A: One-Click Batch Launcher
Double-click [start_server.bat](file:///d:/trading-app/start_server.bat) in File Explorer, or run in PowerShell:
```powershell
.\start_server.bat
```

### Option B: PowerShell Command
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

> [!WARNING]
> **DuckDB Single-Writer Rule**: You **MUST ALWAYS** use `--workers 1`. DuckDB operates as an embedded database process; running with multiple Uvicorn workers will trigger lock collisions (`Resource temporarily unavailable`).

### Open the Application
Open your browser and navigate to:
```
http://localhost:8000
```
or
```
http://127.0.0.1:8000
```

---

## 9. Using the Platform (Features Overview)

Once the application is running, the web UI provides access to all institutional modules:

### 9.1. Dual UX Personas (Simple vs. Pro Mode)
- **Top Navigation Bar Toggle**: Switch between **Simple Mode** (clean summary cards, intuitive plain-English translations, beginner onboarding) and **Pro Mode** (full TradingView candlestick charts, technical overlays, order book data).
- **Interactive Beginner Glossary**: Hover over financial terms (e.g., RSI, VWAP, Sharpe Ratio, Survivorship Bias) to see definitions, real-world analogies, and statutory risk warnings.

### 9.2. High-Performance Screener Engine
- Navigate to the **Screener** tab.
- Filter Nifty 50, Nifty 100, or Nifty 500 stocks based on moving averages, RSI oversold/overbought criteria, or 52-week highs.
- Screener queries execute in `< 2.0s` via optimized DuckDB window functions.
- Every screener result includes mandatory SEBI educational disclosures.

### 9.3. Institutional Backtesting Engine
- Navigate to the **Backtest** tab.
- Configure strategy, timeframe, capital, and date ranges.
- **Statutory Indian Tax Deductions**: The backtester deducts STT, NSE transaction charges, SEBI turnover fees, GST, and stamp duty with realistic slippage.
- **Lookahead Prevention**: Bar $t$ close signals fill on bar $t+1$ open.
- Output includes equity curve, Sharpe/Sortino ratios, max drawdown, and Monte Carlo simulations.

### 9.4. Options Analytics & Greeks Engine
- Navigate to the **Options** tab.
- View live and end-of-day Option Chains with Black-Scholes Greeks ($\Delta$, $\Gamma$, $\Theta$, $\mathcal{V}$) computed using the RBI 91-day T-bill risk-free rate.
- Interactive payoff diagram calculator for Call/Put spreads and multi-leg strategies.

### 9.5. Trade Journal & Paper Trading Simulator
- Navigate to the **Journal** tab.
- Record manual trades or execute simulated paper trades without risking capital.
- Import external tradebook CSVs from Fyers.
- Analyze $R$-multiples, win rate, expectancy, and cost of psychological trading mistakes.

### 9.6. Regulatory Safe Exports
- Export any symbol's historical candles as **Parquet**, **CSV**, or **Excel**.
- Every export file automatically embeds the mandatory **Fyers Personal Non-Commercial License** metadata and SEBI disclosures.
- Excel exports enforce a guard against the 1,048,575 row boundary.

---

## 10. Running Security Audits & Test Suites

### 10.1. Regulatory Compliance & Security Audit
Run the institutional security auditor to verify that zero credentials, API keys, or PINs are leaked across the repository:
```powershell
python scripts/audit_security.py
```
**Expected Result:**
```
[1/4] Auditing .gitignore Configuration & Tracked Sensitive Files... [PASS]
[2/4] Scanning Source Code, Configurations, and Fixtures...          [PASS]
[3/4] Scanning Git Commit History Diffs...                          [PASS]
[4/4] Verifying Architectural Hard Gate: Zero Order Execution APIs...[PASS]
AUDIT SUCCESSFUL: Institutional compliance & security verification passed!
```

### 10.2. Running Automated Unit, Contract & Integration Tests
Execute test suites using Pytest:
```powershell
# Run compliance & log redaction test suite
pytest tests/unit/test_log_redaction.py tests/unit/test_export_sanitization.py tests/integration/test_security_audit.py tests/contract/test_compliance_notices.py -v

# Run beginner glossary & UX test suite
pytest tests/unit/test_glossary_integrity.py tests/contract/test_glossary_schema.py -v

# Run complete platform test suite
pytest tests/unit/ tests/contract/ -v
```

---

## 11. Windows Troubleshooting & FAQ

### Q1: "Execution of scripts is disabled on this system"
**Cause**: Windows PowerShell security policy blocks local script execution by default.  
**Fix**: Open PowerShell and run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

---

### Q2: `ModuleNotFoundError: No module named 'fastapi'` (or similar)
**Cause**: The terminal is using the global Python instead of the project virtual environment.  
**Fix**: Ensure your virtual environment is active (`(.venv)` in prompt), or explicitly invoke Python via:
```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

---

### Q3: `duckdb.IOException: Could not set lock on file: Resource temporarily unavailable`
**Cause**: Another Python process or background terminal is holding the single-writer lock on `data/market_data.duckdb`.  
**Fix**: Close any open instances of the downloader or server, or terminate lingering Python processes:
```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

### Q4: Port 8000 is already in use (`Errno 10048: Only one usage of each socket address is normally permitted`)
**Cause**: An existing Uvicorn server is already running on port 8000.  
**Fix**: Identify and terminate the process holding port 8000:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```
Or start on a different port:
```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --workers 1
```

---

### Q5: "15-day refresh window expired. Please re-authenticate."
**Cause**: Fyers API refresh tokens expire automatically every 15 calendar days per exchange 2FA security guidelines.  
**Fix**: Run the interactive login command to renew the 15-day token:
```powershell
python -m scripts.auth_cli --login
```

---

### Q6: Browser shows "This site can't be reached" after Fyers login
**Cause**: Fyers redirects to `https://127.0.0.1:5000/`. Because no web server is running on port 5000, your browser reports an unreachable page.  
**Fix**: **This is completely normal and expected.** Simply copy the URL from your browser's address bar (containing `&auth_code=...`) and paste it back into your PowerShell prompt where `auth_cli.py` is waiting.

---

### Q7: Can this application place automated live trades?
**Answer**: **No.** In strict adherence to SEBI's Retail Algorithmic Trading Framework (which mandates broker strategy certification, Algo ID tagging, static IP whitelisting, and a 10 OPS ceiling), automated order execution is **strictly out of scope**. The codebase contains zero order placement endpoints, and any order-routing request is blocked with **HTTP 403 Forbidden**. For live trading, users manually place trades through their official Fyers mobile/web terminal based on their independent analysis.

---

### Summary Checklist for Daily Operation
1. **Morning (08:45 IST)**: `python -m scripts.sync_symbols` (Updates symbol master & holiday calendar).
2. **Throughout the Day**: Run `.\start_server.bat` and open `http://localhost:8000` to analyze charts, scan setups, backtest strategies, and paper-trade.
3. **Evening (15:45 IST)**: `python -m scripts.run_daily_sync` (Pulls newly closed candles into DuckDB).
4. **Every 15 Days**: `python -m scripts.auth_cli --login` (Renews Fyers OAuth session).
