# ⚡ NSE Quant Platform

> **Institutional-Grade, Local-First Quantitative Trading & Equity Research Workstation for the National Stock Exchange of India (NSE).**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-FFF000.svg)](https://duckdb.org)
[![TradingView Charts](https://img.shields.io/badge/TradingView-Lightweight_Charts_v4-black.svg)](https://tradingview.github.io/lightweight-charts/)
[![SEBI Compliant](https://img.shields.io/badge/SEBI-Research_Only_(No_Algo_Orders)-orange.svg)]()

---

## 🗺️ System Architecture (Visual Flow)

```mermaid
graph TD
    A["📡 Fyers API v3<br/>(Historical Candles & Live Ticks)"] -->|OAuth 2.0 / REST / WS| B["⚡ FastAPI Core (Port 8000)<br/>(Rate Governor & Security Vault)"]
    
    subgraph Core Engines
        B --> C["⏱️ Resampling Engine<br/>(1m → 3m, 5m, 15m, 1h, 1D)"]
        B --> D["🏛️ OrderBlock Engine<br/>(Tick Absorption & Institutional Footprint)"]
        B --> E["📈 Options & Greeks Lab<br/>(Black-Scholes IV, Delta, Gamma, Payoff)"]
        B --> F["🧪 Quant Backtest & Paper Trading<br/>(Monte Carlo & Indian Cost Model)"]
    end
    
    C & D & E & F <-->|Vectorized SQL| G[("💾 DuckDB Storage<br/>(data/market_data.duckdb)<br/>Single-Writer Lock")]
    
    B -->|REST APIs & SSE| H["🖥️ Web Client (SPA)<br/>TradingView Lightweight Charts • Screener • Modal Views"]
```

---

## 🚀 Quick Start (In 3 Steps)

| Step | Goal | Command / Action |
|:---:|---|---|
| **1** | **Automated Setup** | `powershell -ExecutionPolicy Bypass -File setup_windows.ps1` |
| **2** | **Fyers Login** | `.venv\Scripts\python.exe scripts/auth_cli.py login` |
| **3** | **Start Platform** | Double-click `start_server.bat` *(Opens `http://localhost:8000`)* |

---

## 💎 Core Features Matrix

| Feature | Mode | Visual Preview & Description |
|---|:---:|---|
| **📈 Interactive Charting** | Pro / Simple | **TradingView Lightweight Charts** with dynamic 1m–1D resampling, volume profiles, and multi-indicator technical overlays (RSI, EMA, MACD). |
| **🏛️ OrderBlock Suite** | Institutional | **Real-Time Absorption Footprint**: Identifies large institutional liquidity pools, conviction scores (0–100), and detailed stock profile modals. |
| **🔍 In-Database Screener** | SQL-Powered | **Sub-Second Scanning**: Filters 2,000+ NSE stocks by volume surge, momentum, breakout patterns, and user-defined custom predicates. |
| **⚡ Options & Greeks Lab** | Derivatives | **Black-Scholes Mathematical Engine**: Live Greeks (Δ, Γ, Θ, ν), multi-leg strategy payoff diagrams, and strike-by-strike Open Interest (OI) analysis. |
| **🧪 Backtesting Studio** | Quantitative | **Strategy Lab**: Parameter optimization grids, walk-forward simulations, and risk metrics (Sharpe, Sortino, Max Drawdown). |
| **📝 Paper Trading Dock** | Zero-Risk | **Realistic Simulation**: Live virtual order fills incorporating Indian STT, exchange charges, GST, SEBI turnover fees, and execution slippage. |
| **📓 Trade Journal** | Analytics | **Behavioral Insights**: Interactive calendar heatmap, win/loss tradebook CSV imports, risk-reward R-multiple tracking, and emotional bias audits. |

---

## ⚙️ Technology Stack

```
┌────────────────────────────────────────────────────────────────────────┐
│ FRONTEND      Vanilla JS (ES6+) • HTML5 Canvas • Lightweight Charts    │
├────────────────────────────────────────────────────────────────────────┤
│ BACKEND       Python 3.11+ • FastAPI • Uvicorn (Strictly workers=1)    │
├────────────────────────────────────────────────────────────────────────┤
│ DATABASE      DuckDB (In-Process Vectorized OLAP) • Zero external DB   │
├────────────────────────────────────────────────────────────────────────┤
│ BROKER API    Fyers API v3 (Official NSE Equity & Derivatives Data)    │
├────────────────────────────────────────────────────────────────────────┤
│ SECURITY      OS Keyring • AES-256 Encrypted Vault (.vault.enc)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Directory Structure

```text
trading-app/
├── api/             # FastAPI route controllers (/candles, /orderblock, /screener, /options, ...)
├── config/          # Central configuration, constants & Indian market trading hours
├── core/            # Canonical contracts, abstract interfaces & domain exceptions
├── db/              # DuckDB connection manager, schema migrations & table models
├── services/        # Analytical business logic (Resampling, OrderBlock, Greeks, Backtest)
├── static/          # Modern Web UI (index.html, theme.css, JS modules & chart visualizers)
├── scripts/         # Automated CLI utilities (auth_cli.py, sync_symbols.py, run_daily_sync.py)
├── data/            # DuckDB database file, encrypted vault, caches & symbol master
├── tests/           # Regression test suite (Unit, Integration & Contract tests)
├── main.py          # Application entry point & FastAPI factory
├── start_server.bat # One-click server launcher
└── stop_server.bat  # Graceful server shutdown utility
```

---

## ⌨️ Common Operations & Shortcuts

| Task | Command / Shortcut |
|---|---|
| **Start Server** | `start_server.bat` |
| **Stop Server** | `stop_server.bat` |
| **Download Market Data** | `download_all.bat` |
| **Run Unit Tests** | `.venv\Scripts\pytest tests/unit` |
| **Check Server Health** | `curl http://localhost:8000/api/v1/health` |
| **Fast Symbol Search** | Press `/` anywhere in Web UI |
| **Dismiss Modals / Popups** | Press `Esc` or click `✕` |

---

## 🛡️ Safety & Regulatory Compliance

* 🔐 **Zero Secrets in Codebase**: API credentials never touch git; stored exclusively in Windows Credential Manager (OS Keyring) or encrypted vault (`data/.vault.enc`).
* 📜 **SEBI Research Compliance**: Strictly an educational & analytical workstation. Every chart and export embeds statutory **"Not Investment Advice"** disclosures.
* 🚫 **Safety Circuit Breaker**: Automated order execution routing is permanently disabled (`HTTP 403 Forbidden`).

---

## 📚 Further Reading & References

* 📖 [Full Features Catalog & Operational Manual](FEATURES.md)
* 🛠️ [Detailed Windows Setup & Configuration Guide](HOW_TO_RUN.md)
* 🧭 [Master Architecture & Phase Execution Runbook](AGENT_RUNBOOK.md)
