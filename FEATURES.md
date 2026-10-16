# NSE Quant Platform — Complete Feature Catalog & Operational Guide

This document provides an exhaustive, production-grade master catalog of all features, analytical engines, mathematical models, UI tools, REST API endpoints, and CLI utilities available in the **NSE Quant Platform**. 

Each feature is documented with its technical specifications, exact UI location/shortcut, underlying architecture, and step-by-step instructions in both **English and Tamil (தமிழ் விளக்கம்)**.

---

## Table of Contents
1. [Architectural Overview & System Philosophy](#1-architectural-overview--system-philosophy)
2. [Master Web UI Features Catalog](#2-master-web-ui-features-catalog)
   - [2.1 Interactive Charting & Technical Visualizer](#21-interactive-charting--technical-visualizer)
   - [2.2 Smart Symbol Search & Universe Navigation](#22-smart-symbol-search--universe-navigation)
   - [2.3 High-Performance In-Database Stock Screener](#23-high-performance-in-database-stock-screener)
   - [2.4 Options Trading, Greeks & Analytics Suite](#24-options-trading-greeks--analytics-suite)
   - [2.5 Quantitative Backtesting Lab, Portfolio Studio & Optimizer](#25-quantitative-backtesting-lab-portfolio-studio--optimizer)
   - [2.6 Paper Trading Simulation & Strategy Dock](#26-paper-trading-simulation--strategy-dock)
   - [2.7 Trade Journal & Behavioral Analytics](#27-trade-journal--behavioral-analytics)
   - [2.8 Real-Time Alert Engine & Monitoring](#28-real-time-alert-engine--monitoring)
   - [2.9 Dual Persona UX (Simple vs. Pro Mode)](#29-dual-persona-ux-simple-vs-pro-mode)
   - [2.10 Ingestion Telemetry & Session Management](#210-ingestion-telemetry--session-management)
3. [CLI Tools & Background Automation Catalog](#3-cli-tools--background-automation-catalog)
4. [Complete REST API Endpoint Directory (`/api/v1/...`)](#4-complete-rest-api-endpoint-directory)
5. [DuckDB Database Schema & Views Architecture](#5-duckdb-database-schema--views-architecture)
6. [Keyboard Shortcuts & Quick Navigation Reference](#6-keyboard-shortcuts--quick-navigation-reference)
7. [Recommended Daily Trading & Research Workflow](#7-recommended-daily-trading--research-workflow)
8. [Statutory Regulatory Compliance Notice](#8-statutory-regulatory-compliance-notice)

---

## 1. Architectural Overview & System Philosophy

The **NSE Quant Platform** is engineered from first principles as an institutional-grade, local-first quantitative research and analytical workstation specifically built for the National Stock Exchange of India (NSE).

```
+---------------------------------------------------------------------------------------+
|                                    WEB CLIENT (SPA)                                   |
|   TradingView Lightweight Charts (v4.1.3) | HTML5 Canvas Overlays | Vanilla JS (ES6+)  |
+---------------------------------------------------------------------------------------+
                                           |  HTTP / REST / SSE (Port 8000)
                                           v
+---------------------------------------------------------------------------------------+
|                                 FASTAPI APPLICATION CORE                              |
|   Correlation ID Tracking | Order Safety Gate (403) | Token Bucket Rate Governor     |
+---------------------------------------------------------------------------------------+
        |                                   |                                   |
        v                                   v                                   v
+-----------------------+       +-----------------------+       +-----------------------+
|   ROUTER LAYER        |       |   SERVICES LAYER      |       |   SECURITY & VAULT    |
| - /candles            |       | - Resampling Service  |       | - OS Keyring Storage  |
| - /symbols            |       | - Greeks & Payoff     |       | - AES-256 .vault.enc  |
| - /screener           |       | - Backtest & Monte C. |       | - 24h Access / 15d RT |
| - /options            |       | - JIT Market Sync     |       | - 48h Warning Timer   |
| - /backtest           |       | - Downloader Engine   |       +-----------------------+
| - /paper-trading      |       | - Journal & Analytics |
| - /journal            |       +-----------------------+
+-----------------------+                   |
        |                                   v
        +---------------------> +-------------------------------------------------------+
                                |               DUCKDB OLAP DATA ENGINE                 |
                                | - Single Writer Process (uvicorn workers=1)           |
                                | - Lockless Reader Cursors (conn.cursor())             |
                                | - Append-Only Raw Tables (candles_1m_raw, 1d)         |
                                | - Split-Adjusted Dynamic SQL Views                    |
                                +-------------------------------------------------------+
```

### Key Engineering Principles
- **In-Database Dynamic Resampling:** Raw 1-minute historical bars are aggregated on the fly into 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1D, and 1W bars directly inside DuckDB using vectorized SQL, eliminating the need to store duplicate timeframe tables.
- **Strict Concurrency Protection:** DuckDB employs a strict single-writer lock. The FastAPI server operates with `workers=1`, and all read-heavy routes instantiate independent cursors (`conn.cursor()`) to ensure zero lock contention between background ingestion and real-time UI charting.
- **Zero-Secret Security Architecture:** API secrets and tokens are never stored in plain text or `.env` files. They are managed through OS Keyring or AES-256 encrypted local vaults (`.vault.enc`).
- **Indian Market Alignment:** All timestamps, resampling rules, and market holiday schedules are synchronized strictly with Indian Standard Time (`Asia/Kolkata`, IST, UTC+05:30) and the official NSE trading calendar (09:15 to 15:30 IST).
- **Realistic Execution Modeling:** Backtest simulations apply strict $t$ Close to $t+1$ Open execution to eliminate lookahead bias, combined with statutory Indian transaction taxes (STT, GST, SEBI turnover fees, Stamp Duty, and exchange turnover charges).

---

## 2. Master Web UI Features Catalog

Launch the application by running `.\start_server.bat` in PowerShell and opening **`http://localhost:8000`** in any modern web browser.

### 2.1 Interactive Charting & Technical Visualizer

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Interactive Candlestick Chart** | Center Canvas (`#chart-container`) | **English:**<br>1. Open `http://localhost:8000`.<br>2. **Pan**: Left-click and drag the chart canvas left or right.<br>3. **Zoom**: Scroll your mouse wheel up (zoom in) or down (zoom out).<br>4. **Inspect**: Hover your mouse over any candle to view Date, Time, OHLC, and Volume in the legend.<br>5. **Reset View**: Double-click anywhere on the canvas to auto-fit price action.<br><br>**தமிழ்:**<br>1. சார்ட்டை கிளிக் செய்து இடது/வலதுபுறம் drag செய்து past/future candles பார்க்கலாம்.<br>2. Mouse wheel scroll செய்து Zoom In/Zoom Out செய்யலாம்.<br>3. ஏதேனும் ஒரு candle மீது கர்சரை வைத்தால் அதன் Open, High, Low, Close மற்றும் Volume தெரியும்.<br>4. சார்ட்டில் Double-click செய்தால் திரைக்கு தகுந்தவாறு தானாக பொருந்தும் (auto-fit). | High-performance TradingView Lightweight Charts (v4.1.3). Renders split-adjusted candles with synchronized volume subpane, crosshair coordinate tracker, and automatic time scale formatting. | Simple & Pro |
| **Multi-Timeframe Engine** | Pro Toolbar (`.tf-btn`) | **English:**<br>1. Ensure **Pro Mode** is active.<br>2. Click any timeframe pill: `1m`, `3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1D`, `1W`.<br>3. Chart updates dynamically within milliseconds.<br><br>**தமிழ்:**<br>1. Pro Mode-ல் Toolbar-ல் உள்ள `1m`, `5m`, `15m`, `1h`, `1D` போன்ற பொத்தான்களை கிளிக் செய்யவும்.<br>2. DuckDB-யில் 1-minute டேட்டாவில் இருந்து நேரலையாக resample செய்யப்பட்டு மில்லி விநாடிகளில் சார்ட் மாறும். | Dynamic in-database SQL aggregation. Aggregates from base 1-minute candles (`candles_1m_adjusted`) using IST trading session windows (09:15 to 15:30 IST). | Pro Mode |
| **Infinite Scroll (Backward Lazy-Load)** | Chart Viewport (Pan Left) | **English:**<br>1. Drag the chart canvas towards the right (moving backward in time).<br>2. Approaching the left edge triggers an automatic background fetch.<br>3. Earlier historical bars prepended seamlessly without UI flicker.<br><br>**தமிழ்:**<br>1. சார்ட்டை வலதுபுறமாக இழுத்தால் பழைய வருடங்களின் டேட்டா தானாக பின்னணியில் லோட் ஆகும்.<br>2. 5 முதல் 15 வருடங்களுக்கான டேட்டாவை தொடர்ச்சியாக பார்க்கலாம். | Cursor-based pagination (`/api/v1/candles?before_timestamp=...`). Fetches and prepends chunks without reloading the page or losing current zoom level. | Simple & Pro |
| **Technical Indicator Suite** | Pro Toolbar (`Studies` / Dropdown) | **English:**<br>1. Click **`Studies`** in the toolbar.<br>2. Select overlays: **VWAP**, **EMA (9, 21, 50, 200)**, **SMA (20, 50, 200)**, **Bollinger Bands (20, 2)**, or **Supertrend (10, 3)**.<br>3. Select sub-panes: **RSI (14)**, **MACD (12, 26, 9)**, or **ATR (14)**.<br>4. Toggle button again to remove indicator.<br><br>**தமிழ்:**<br>1. Toolbar-ல் **Studies** கிளிக் செய்து VWAP, EMA, SMA, Bollinger Bands, Supertrend போன்ற கோடுகளை சேர்க்கலாம்.<br>2. RSI, MACD, ATR ஆகியவற்றை கீழ்பகுதியில் தனி sub-pane-ல் பார்க்கலாம்.<br>3. மீண்டும் கிளிக் செய்தால் அந்த indicator மறைந்துவிடும். | Vectorized mathematics computed client-side or server-side. Multi-color line series, Bollinger envelope bands, MACD histogram with zero-line coloring, and RSI overbought (70)/oversold (30) threshold bands. | Pro Mode |
| **Candlestick Pattern Recognition** | Pro Toolbar (`#btn-toggle-patterns`) | **English:**<br>1. Click the **Patterns** button in the toolbar.<br>2. Platform scans visible candles and plots visual marker arrows.<br>3. Hover over any marker to see pattern name, sentiment, and confirmation criteria.<br><br>**தமிழ்:**<br>1. Toolbar-ல் **Patterns** பட்டனை கிளிக் செய்யவும்.<br>2. சார்ட்டில் உள்ள கேண்டில்களில் Bullish/Bearish Engulfing, Hammer, Shooting Star, Doji போன்ற வடிவங்கள் தானாக அடையாளம் காணப்பட்டு குறியீடுகள் தோன்றும்.<br>3. குறியீட்டின் மீது கர்சரை வைத்தால் அதன் முழு விவரம் தெரியும். | Detects 12 major classical candlestick formations: Bullish/Bearish Engulfing, Hammer, Inverted Hammer, Shooting Star, Hanging Man, Morning/Evening Star, Doji variants (Dragonfly, Gravestone), and Three White Soldiers/Black Crows. | Pro Mode |
| **Volume Profile Canvas Overlay** | Pro Toolbar (`#btn-toggle-vp`) | **English:**<br>1. Click the **Volume Profile** button (`#btn-toggle-vp`).<br>2. An HTML5 canvas overlay draws horizontal volume distribution bars along the price axis.<br>3. Inspect the **Point of Control (POC)** (bright red line) and **Value Area (VAH & VAL)** (70% volume range).<br><br>**தமிழ்:**<br>1. Toolbar-ல் **Volume Profile** பட்டனை கிளிக் செய்யவும்.<br>2. சார்ட்டின் வலதுபுறத்தில் எந்தெந்த விலைகளில் அதிக வர்த்தகம் நடந்துள்ளது என்பதை காட்டும் Volume Profile தோன்றும்.<br>3. அதிக வர்த்தகம் நடந்த மைய விலை Point of Control (POC) சிவப்பு கோடாகவும், 70% வர்த்தக எல்லைகள் (VAH & VAL) நீல நிறத்திலும் தெரியும். | Custom HTML5 Canvas rendering. Calculates traded volume per price tick, identifies POC (highest volume price), and computes Value Area High/Low at 70% threshold. Synchronized with chart zoom/pan. | Pro Mode |
| **Interactive Chart Drawing Tools** | Left Drawing Palette (`#drawing-toolbar`) | **English:**<br>1. Select a tool from the left toolbar: **Trendline**, **Horizontal Ray**, **Fibonacci Retracement**, **Supply/Demand Zones (Box)**, **Text Note**, or **Measure Tool**.<br>2. Click on the chart canvas to place anchors.<br>3. Edit color, line width, or delete via the active selection widget.<br>4. Drawings automatically persist across sessions.<br><br>**தமிழ்:**<br>1. இடதுபுற டூல்பாரில் உள்ள Trendline, Horizontal Line, Fibonacci, Rectangle Box அல்லது Measure டூலை தேர்வு செய்யவும்.<br>2. சார்ட்டில் கிளிக் செய்து வரையவும்.<br>3. இதன் நிறம், தடிமன் மாற்றலாம். வரைந்த கோடுகள் DuckDB-யில் தானாக சேமிக்கப்படும். | Canvas-based geometric overlay. Supports Fibonacci ratios (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0), price/time delta measuring, and persistent DuckDB storage (`chart_drawings` table). | Pro Mode |
| **On-Chart Options Intelligence HUD** | Pro Toolbar (`Options Overlay`) | **English:**<br>1. When viewing an F&O underlying (e.g. `NSE:NIFTY50-INDEX`), enable **Options Overlay**.<br>2. Chart renders a horizontal dashed gold line at the **Max Pain Strike**.<br>3. Floating HUD displays live **PCR (Put-Call Ratio)** and nearest Support/Resistance walls.<br><br>**தமிழ்:**<br>1. F&O பங்குகளை பார்க்கும்போது Options Overlay ஆன் செய்யவும்.<br>2. சார்ட்டில் தற்போதைய **Max Pain** விலை கோடு தெரியும்.<br>3. மேல் பகுதியில் Put-Call Ratio (PCR) மற்றும் Support/Resistance அளவுகள் மிதக்கும் அட்டையாக (HUD) தோன்றும். | Integrates option chain analytics directly onto the equity chart canvas. Updates Max Pain and strike open interest distribution in real time. | Pro Mode |
| **On-Chart Paper Trade Dock** | Top Right Canvas Dock (`#chart-paper-dock`) | **English:**<br>1. Click **Trade** on the chart header.<br>2. Set order side (Buy/Sell), Quantity, Target %, and Stop-Loss %.<br>3. Click **Execute Paper Trade**.<br>4. Live unrealized P&L and SL/TP target lines appear on the chart with 1-click **Square Off**.<br><br>**தமிழ்:**<br>1. சார்ட்டின் மேல் உள்ள **Trade** பட்டனை கிளிக் செய்யவும்.<br>2. Buy/Sell, அளவு (Quantity), Target மற்றும் Stop-Loss சதவீதத்தை உள்ளிடவும்.<br>3. **Execute** கிளிக் செய்தால் சார்ட்டிலேயே SL/TP கோடுகள் தோன்றும் மற்றும் நேரலை லாப/நஷ்டம் (P&L) தெரியும். 1-click மூலம் நிலையை மூடலாம் (Square Off). | Direct execution widget connected to the paper trading engine. Visualizes entry price, Stop-Loss price, and Take-Profit price directly on the active candlestick series. | Simple & Pro |
| **Strategy Tester Chart Dock** | Bottom Canvas Dock (`#strategy-tester-dock`) | **English:**<br>1. Click **Strategy Tester** at the bottom of the chart.<br>2. Pick a strategy (e.g. `EMA Cross 9/21`) and click **Quick Test**.<br>3. Historical buy (green arrow) and sell (red arrow) markers render on candles.<br>4. Bottom dock displays Net Profit, Win Rate %, Profit Factor, and Max Drawdown.<br><br>**தமிழ்:**<br>1. சார்ட்டின் கீழ்பகுதியில் உள்ள **Strategy Tester**-ஐ திறக்கவும்.<br>2. உத்தியை (எ.கா. EMA Cross) தேர்வு செய்து **Quick Test** கிளிக் செய்யவும்.<br>3. கடந்த காலத்தில் வாங்கிய மற்றும் விற்ற இடங்கள் பச்சை மற்றும் சிவப்பு அம்புக்குறிகளாக சார்ட்டில் தெரியும். லாப/நஷ்ட புள்ளிவிவரங்கள் கீழ்ப்பகுதியில் தோன்றும். | Instant single-symbol backtest execution. Overlays historical trade markers onto Lightweight Charts and renders performance statistics with deep-dive link to Backtest Lab. | Pro Mode |

---

### 2.2 Smart Symbol Search & Universe Navigation

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Smart Symbol Search (2,581 Stocks)** | Top Navigation / **`Ctrl + K`** | **English:**<br>1. Press **`Ctrl + K`** or click the search box in the header.<br>2. Type ticker or company name (e.g. `RELIANCE`, `TCS`, `INFY`, `HDFCBANK`).<br>3. Use arrow keys $\uparrow / \downarrow$ to navigate and press **`Enter`**.<br>4. Chart immediately switches and synchronizes data.<br><br>**தமிழ்:**<br>1. கீபோர்டில் **`Ctrl + K`** அழுத்தவும் அல்லது Search பாக்ஸை கிளிக் செய்யவும்.<br>2. நீங்கள் பார்க்க விரும்பும் ஸ்டாக் பெயரை டைப் செய்யவும்.<br>3. லிஸ்ட்டில் வரும் பங்கை தேர்ந்தெடுத்து **Enter** அழுத்தினால் உடனே சார்ட் லோட் ஆகும். | Searches across 2,581 active NSE equities. Features sub-millisecond substring indexing, index constituent tags (`NIFTY 50`, `NIFTY NEXT 50`, `MIDCAP`), and popular recommendations. | Simple & Pro |
| **Dynamic Popular Stocks Drawer** | Symbol Modal (Empty State) | **English:**<br>1. Press **`Ctrl + K`** with an empty input field.<br>2. Recommended high-turnover stocks appear automatically.<br>3. Click any symbol chip for 1-click loading.<br><br>**தமிழ்:**<br>1. **`Ctrl + K`** திறந்தவுடன் அதிக வர்த்தகமாகும் முன்னணி பங்குகள் (Reliance, HDFC Bank, TCS போன்றவை) பரிந்துரைகளாக தோன்றும்.<br>2. அதில் ஏதேனும் ஒன்றை கிளிக் செய்து உடனே திறக்கலாம். | Dynamic recommendations derived from market cap, daily turnover, and F&O liquidity via `/api/v1/symbols/popular`. | Simple & Pro |

---

### 2.3 High-Performance In-Database Stock Screener

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Pre-Built Quick Screener Filters** | Screener Dashboard (`#screener-view`) | **English:**<br>1. Navigate to the **Screener** tab.<br>2. Click a quick template:<br>   - **Volume Spike**: Identifies stocks with volume Z-Score $> 2.0$.<br>   - **52-Week High**: Stocks trading within 2% of their 52-week peak.<br>   - **RSI Oversold**: Stocks with daily RSI $\le 30$.<br>3. Table updates in $<50$ms.<br>4. Click any row to load the symbol into the interactive chart.<br><br>**தமிழ்:**<br>1. Screener பகுதிக்குச் செல்லவும்.<br>2. மேலே உள்ள **Volume Spike** (திடீர் வால்யூம் உயர்வு), **52-Week High** (உச்ச விலை அருகில்), அல்லது **RSI Oversold** (விலை குறைவு) பட்டன்களை கிளிக் செய்யவும்.<br>3. 50 மில்லி விநாடிகளுக்குள் முடிவுகள் அட்டவணையில் தோன்றும். ஏதேனும் ஒரு பங்கை கிளிக் செய்தால் அதன் சார்ட் திறக்கும். | High-speed analytical queries executed directly on DuckDB `candles_1d_adjusted`. Employs window functions to compute Z-scores, rolling 52-week highs/lows, and RSI without loading raw data into memory. | Pro Mode |
| **Custom Multi-Parameter Filter Builder** | Screener Dashboard (`#custom-filter-panel`) | **English:**<br>1. Expand the **Custom Filters** accordion in the Screener.<br>2. Configure criteria: RSI range (Min/Max), Volume Z-Score threshold, % distance to 52W High/Low, % distance to 20-day SMA, 1-Day % Change, and Min Turnover (₹ Cr).<br>3. Click **Run Scan**.<br>4. Save criteria as a personal template for future scans.<br><br>**தமிழ்:**<br>1. Screener-ல் **Custom Filters** பகுதியை திறக்கவும்.<br>2. RSI அளவு, Volume Z-Score, 52W High-க்கு உள்ள தூரம் %, 20-SMA தூரம் % ஆகியவற்றை உங்கள் விருப்பப்படி மாற்றியமைக்கவும்.<br>3. **Run Scan** கொடுத்தால் அந்த நிபந்தனைகளுக்கு பொருந்தும் பங்குகள் மட்டும் வடிகட்டப்பட்டு காட்டப்படும். எதிர்கால பயன்பாட்டிற்கு இதை Template-ஆக சேமிக்கலாம். | Dynamic multi-predicate SQL generator. Combines momentum, volatility, volume anomaly, and moving average distance filters into an optimized single-pass query. | Pro Mode |
| **Universe Basket Filtering** | Screener Universe Dropdown | **English:**<br>1. In the Screener header, open the **Universe** selector.<br>2. Select: **All Stocks (2,581)**, **NIFTY 50**, **NIFTY NEXT 50**, or **NIFTY 500**.<br>3. Scan executes strictly against the selected universe.<br><br>**தமிழ்:**<br>1. Screener-ல் உள்ள **Universe** மெனுவை திறக்கவும்.<br>2. Nifty 50, Nifty Next 50, Nifty 500 அல்லது All Stocks ஆகியவற்றில் ஒன்றை தேர்வு செய்யவும்.<br>3. தேர்வு செய்த குறியீட்டு பங்குகளுக்குள் மட்டும் ஸ்கேனிங் நடைபெறும். | Integrates dynamic constituent lists fetched from `/api/v1/backtest/portfolio/universes`. Filters queries by official NSE index constituent membership. | Pro Mode |
| **1-Click Live Data Synchronization** | Screener Header (`#btn-sync-screener`) | **English:**<br>1. Click **Sync Live Data** in the Screener toolbar.<br>2. Platform contacts Fyers quotes API and updates today's forming candle for all universe symbols.<br>3. Table refreshes with latest intraday metrics.<br><br>**தமிழ்:**<br>1. Screener-ல் உள்ள **Sync Live Data** பட்டனை கிளிக் செய்யவும்.<br>2. இன்றைய நேரலை விலை மற்றும் வால்யூம் உடனடியாக அப்டேட் செய்யப்பட்டு புதிய முடிவுகள் காட்டப்படும். | Triggers JIT rate-governed quote sync across symbols. Updates temporary in-memory forming bar to ensure real-time intraday screener accuracy. | Pro Mode |
| **Screener CSV Export** | Screener Header (`#btn-export-screener`) | **English:**<br>1. After running a scan, click **Export CSV**.<br>2. Browser automatically downloads a `.csv` file containing filtered stocks, LTP, Volume, RSI, Z-Score, and change %.<br><br>**தமிழ்:**<br>1. ஸ்கேன் செய்த பிறகு **Export CSV** பட்டனை கிளிக் செய்யவும்.<br>2. அனைத்து விவரங்களும் அடங்கிய `.csv` ஃபைல் உங்கள் கணினியில் சேமிக்கப்படும். | Exports active screen results with column headers and formatted metrics for spreadsheet or quant modeling workflows. | Pro Mode |

---

### 2.4 Options Trading, Greeks & Analytics Suite

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Interactive Strike Matrix (Option Chain)** | Options Dashboard (`#options-view`) | **English:**<br>1. Navigate to the **Options** tab.<br>2. Select an underlying: `NIFTY 50`, `BANK NIFTY`, `FIN NIFTY`, `MIDCP NIFTY`, or 180+ F&O stocks.<br>3. Choose an expiration date from the expiry dropdown.<br>4. Inspect the side-by-side matrix: Calls (left) vs. Puts (right) with Strike Price, LTP, Net Change, OI, $\Delta$OI, and IV.<br>5. The **At-The-Money (ATM)** strike is highlighted with a distinct indicator badge.<br><br>**தமிழ்:**<br>1. Options பகுதிக்குச் சென்று NIFTY 50 அல்லது BANK NIFTY தேர்ந்தெடுக்கவும்.<br>2. Expiry தேதியை தேர்ந்தெடுக்கவும்.<br>3. இடதுபுறம் Calls, வலதுபுறம் Puts, நடுவில் Strike Price கொண்ட Option Chain அட்டவணை தோன்றும். இதில் LTP, Open Interest (OI), Change in OI மற்றும் IV விவரங்கள் இருக்கும்.<br>4. சந்தை விலைக்கு மிக அருகில் உள்ள At-The-Money (ATM) ஸ்ட்ரைக் தனி நிறத்தில் காட்டப்படும். | Full strike matrix with visual OI depth bars embedded in table cells. Features automatic lot size mapping, volume tracking, and strike price distance sorting. | Pro Mode |
| **Real-Time Black-Scholes Greeks Engine** | Option Chain Matrix Columns | **English:**<br>1. In Option Chain, view the Greeks columns for every Call and Put strike:<br>   - **Delta ($\Delta$)**: Price sensitivity per ₹1 move in underlying.<br>   - **Gamma ($\Gamma$)**: Rate of change of Delta per ₹1 move.<br>   - **Theta ($\Theta$)**: Daily time decay in ₹ per share.<br>   - **Vega ($\mathcal{V}$)**: Sensitivity per 1% change in Implied Volatility.<br><br>**தமிழ்:**<br>1. Option Chain-ல் ஒவ்வொரு ஸ்ட்ரைக்கிற்கும் Delta, Gamma, Theta, Vega ஆகிய Greeks மதிப்புகளை பார்க்கலாம்.<br>2. பங்கு ₹1 ஏறினால் ஆப்ஷன் எவ்வளவு ஏறும் (Delta) மற்றும் தினமும் காலாவதி நெருங்கும்போது எவ்வளவு மதிப்பு குறையும் (Theta) என்பதை துல்லியமாக கணிக்கலாம். | Closed-form Black-Scholes-Merton (BSM) analytical pricing model. Uses the official Reserve Bank of India (RBI) 91-day Treasury Bill rate ($6.5\%$) as the risk-free rate ($r$) and exact days to expiry ($T-t$). | Pro Mode |
| **Open Interest & Market Sentiment Analytics** | Options Header HUD (`#oi-analytics-hud`) | **English:**<br>1. View the summary cards above the Option Chain:<br>   - **PCR (Total OI)**: Overall Put-Call Ratio ($\Sigma PE_{OI} / \Sigma CE_{OI}$).<br>   - **PCR ($\Delta$OI)**: Intraday momentum Put-Call Ratio ($\Sigma \Delta PE_{OI} / \Sigma \Delta CE_{OI}$).<br>   - **Call Resistance Wall**: Strike with largest Call Open Interest.<br>   - **Put Support Wall**: Strike with largest Put Open Interest.<br>   - **Battleground Strike**: Strike with highest combined Call + Put volume.<br>   - **Market Sentiment Badge**: Algorithmic classification (**Bullish**, **Bearish**, or **Neutral**).<br><br>**தமிழ்:**<br>1. Option Chain-க்கு மேல் உள்ள Analytics அட்டையை பார்க்கவும்.<br>2. Put-Call Ratio (PCR) மதிப்பு 1.0-க்கு மேல் இருந்தால் Bullish, 0.7-க்கு கீழ் இருந்தால் Bearish என காட்டும்.<br>3. சந்தையின் முக்கிய Resistance மற்றும் Support ஸ்ட்ரைக்குகள் தானாக கணக்கிடப்பட்டு காட்டப்படும். | High-level market sentiment synthesis. Computes volume-weighted and open-interest-weighted put-call ratios to determine institutional positioning. | Pro Mode |
| **Max Pain Benchmark Calculator** | Options Analytics Sub-Tab (`#max-pain-panel`) | **English:**<br>1. Click the **Max Pain** tab in Options.<br>2. Review the interactive bar chart showing cumulative seller payout across all strikes.<br>3. Locate the **Max Pain Strike** where option writers have the least monetary liability.<br><br>**தமிழ்:**<br>1. Options-ல் **Max Pain** பகுதியை திறக்கவும்.<br>2. Expiry அன்று பெரிய ஆப்ஷன் விற்பனையாளர்களுக்கு (Option Sellers) குறைந்தபட்ச நஷ்டம் ஏற்படும் விலை எது என Max Pain வரைபடம் காட்டும்.<br>3. பெரும்பாலான சந்தை காலாவதிகள் இந்த விலையை நோக்கியே முடியும் என்பது Max Pain தத்துவம். | Computes cumulative payout across all options: $\sum CE_{OI} \times \max(0, S - K) + \sum PE_{OI} \times \max(0, K - S)$. Identifies the global minimum payout point. | Pro Mode |
| **Multi-Leg Payoff Simulator** | Options Strategy Builder (`#payoff-simulator`) | **English:**<br>1. Navigate to the **Payoff Simulator**.<br>2. Choose a pre-built preset (**Long Call**, **Long Put**, **Bull Call Spread**, **Bear Put Spread**, **Straddle**, **Iron Condor**) or click **Add Custom Leg**.<br>3. Configure Leg Action (Buy/Sell), Option Type (CE/PE), Strike, Lots, and Entry Premium.<br>4. Inspect the interactive P&L Payoff Curve plotting net profit/loss across target spot prices.<br>5. Check **Breakeven Points**, **Max Profit**, **Max Loss**, and **Risk/Reward Ratio**.<br><br>**தமிழ்:**<br>1. **Payoff Simulator** பகுதிக்கு செல்லவும்.<br>2. Bull Call Spread, Iron Condor போன்ற ரெடிமேட் உத்திகளை தேர்ந்தெடுக்கலாம் அல்லது புதிய Legs சேர்க்கலாம்.<br>3. Buy/Sell, Strike, Lot அளவு ஆகியவற்றை மாற்றும்போது உங்கள் லாப/நஷ்ட வரைபடம் (P&L Chart) உடனுக்குடன் மாறும்.<br>4. இந்த உத்தியில் அதிகபட்ச லாபம் எவ்வளவு, அதிகபட்ச நஷ்டம் எவ்வளவு மற்றும் Breakeven விலை என்ன என்பதை முன்கூட்டியே தெளிவாக அறியலாம். | Multi-leg expiration payoff calculation combined with pre-expiry Black-Scholes simulation curve ($T-t$). Computes exact breakeven strikes, asymmetric risk/reward boundaries, and net debit/credit outlays. | Pro Mode |

---

### 2.5 Quantitative Backtesting Lab, Portfolio Studio & Optimizer

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **No-Code Single-Stock Backtest Wizard** | Backtest Panel (`#backtest-view`) | **English:**<br>1. Navigate to the **Backtest** tab.<br>2. **Step 1: Strategy**: Select strategy (e.g. `SMA Crossover`, `EMA Crossover`, `RSI Mean Reversion`, `Bollinger Bands`, `Supertrend`, `MACD`).<br>3. **Step 2: Configuration**: Choose Symbol, Timeframe (`1D`, `1h`, `15m`, `5m`), and Date Range.<br>4. **Step 3: Capital & Execution**: Set Initial Capital (e.g. ₹1,00,000), Position Sizing, and Slippage.<br>5. Click **Run Backtest**.<br>6. View Cumulative Equity Curve, Drawdown Underwater Chart, and full Trade Log.<br><br>**தமிழ்:**<br>1. **Backtest** பகுதிக்குச் செல்லவும்.<br>2. உங்களுக்கு தேவையான உத்தியை (Strategy) தேர்வு செய்து, பங்கு, Timeframe மற்றும் தேதியை உள்ளிடவும்.<br>3. முதலீட்டுத் தொகையை கொடுத்து **Run Backtest** கிளிக் செய்யவும்.<br>4. கடந்த காலத்தில் இந்த உத்தி எவ்வளவு லாபம் தந்தது, எத்தனை டிரேடுகள் வெற்றி பெற்றன என்ற முழு முடிவுகளையும் வரைபடத்துடன் பார்க்கலாம். | Vectorized and event-driven backtesting engine. Enforces strict $t$ Close to $t+1$ Open execution to eliminate lookahead bias. Models statutory Indian charges (STT, GST, Exchange charges, SEBI fees, Stamp Duty, and brokerage). | Pro Mode |
| **Comprehensive Quant Performance KPIs** | Backtest Results Dashboard | **English:**<br>1. After running a backtest, review the top metrics row:<br>   - **Net P&L (₹ & %)**: Total cumulative monetary return.<br>   - **CAGR (%)**: Compound Annual Growth Rate.<br>   - **Win Rate (%)**: Percentage of profitable trades.<br>   - **Profit Factor**: Gross Profit divided by Gross Loss.<br>   - **Sharpe Ratio**: Risk-adjusted excess return over risk-free rate.<br>   - **Sortino Ratio**: Downside risk-adjusted return.<br>   - **Max Drawdown (% & Duration)**: Peak-to-trough equity decline.<br>   - **Expectancy & Avg R-Multiple**: Mathematical expectation per trade.<br><br>**தமிழ்:**<br>1. பேக்டெஸ்ட் முடிந்ததும் அதன் முக்கிய அளவீடுகளை பார்க்கவும்:<br>   - **Win Rate (%)**: எத்தனை சதவீத டிரேடுகள் வெற்றி பெற்றன.<br>   - **Profit Factor**: மொத்த லாபம் / மொத்த நஷ்டம் விகிதம்.<br>   - **Sharpe & Sortino Ratio**: ரிஸ்க்கிற்கு தகுந்த லாப விகிதம்.<br>   - **Max Drawdown**: அதிகபட்சமாக கணக்கு எவ்வளவு சரிவை சந்தித்தது.<br>2. ஒவ்வொரு டிரேடும் எப்போது வாங்கப்பட்டது, விற்கப்பட்டது என்ற விரிவான பட்டியல் கிடைக்கும். | Institutional quantitative analytics. Computes daily equity returns, volatility, risk-adjusted ratios, and provides exportable trade-by-trade audit logs. | Pro Mode |
| **Multi-Stock Portfolio Backtesting Studio** | Backtest Tab (`#portfolio-studio`) | **English:**<br>1. In Backtest tab, switch to the **Portfolio Studio** sub-tab.<br>2. Pick a Universe: **NIFTY 50**, **NIFTY NEXT 50**, or **NIFTY 500**.<br>3. Select Strategy and set Portfolio Capital (e.g. ₹10,00,000).<br>4. Choose Position Sizing: **Equal Weight**, **Fixed Capital**, or **Inverse Volatility (ATR-based)**.<br>5. Set Max Concurrent Positions (e.g. 10) and Rebalance Frequency.<br>6. Click **Run Portfolio Backtest**.<br>7. Inspect aggregate portfolio equity curve plotted alongside the **NIFTY 50 Benchmark**.<br><br>**தமிழ்:**<br>1. Backtest-ல் **Portfolio Studio** பகுதிக்கு செல்லவும்.<br>2. Nifty 50 அல்லது Nifty 500 பங்குகளை கூடை (Basket)-யாக தேர்வு செய்யவும்.<br>3. முதலீடு ₹10,00,000 என கொடுத்து, ஒரே நேரத்தில் எத்தனை பங்குகளுக்கு மேல் வாங்கக்கூடாது என்பதை முடிவு செய்யவும்.<br>4. **Run Portfolio Backtest** கொடுத்தால், மொத்த போர்ட்ஃபோலியோ எப்படி செயல்பட்டது மற்றும் Nifty 50 குறியீட்டை விட அதிக லாபம் தந்ததா என்ற ஒப்பீட்டு வரைபடம் தோன்றும். | Simulates multi-asset portfolio strategies with dynamic cash allocation, position constraints, risk parity sizing, and benchmark alpha/beta comparisons. | Pro Mode |
| **Parameter Grid Search Optimizer** | Backtest Tab (`#optimizer-panel`) | **English:**<br>1. In Backtest tab, open the **Optimizer** sub-tab.<br>2. Pick a strategy preset (e.g. `EMA Cross Optimizer`).<br>3. Define parameter bounds: Fast EMA (range: 5 to 20, step: 1), Slow EMA (range: 20 to 100, step: 5).<br>4. Click **Run Optimization**.<br>5. Review the interactive **2D Heatmap** showing Sharpe Ratio and Net Profit across parameter combinations.<br>6. Click any cell to load the optimal parameters into your strategy.<br><br>**தமிழ்:**<br>1. Backtest-ல் **Optimizer** பகுதிக்கு செல்லவும்.<br>2. ஒரு உத்தியில் எந்த எண்கள் சிறந்த லாபம் தரும் (எ.கா. EMA 9/21 சிறந்ததா அல்லது 13/48 சிறந்ததா) என கண்டுபிடிக்க parameter வரம்புகளை கொடுக்கவும்.<br>3. **Run Optimization** கொடுத்தால் வண்ணமயமான 2D Heatmap வரைபடம் தோன்றும்.<br>4. அதிக லாபம் மற்றும் குறைந்த நஷ்டம் தரும் சிறந்த எண்களை எளிதில் கண்டறியலாம். | Multi-threaded grid search exploring multidimensional parameter spaces. Visualizes parameter sensitivity heatmaps to detect robust parameter islands and avoid curve fitting. | Pro Mode |
| **Monte Carlo Robustness Engine** | Backtest Results (`#monte-carlo-section`) | **English:**<br>1. In Backtest Results, scroll to the **Monte Carlo Analysis** section.<br>2. Platform reshuffles historical trade sequences 1,000 times.<br>3. Review the **Confidence Envelopes**: 5th percentile (worst case), 50th percentile (median), and 95th percentile (best case).<br>4. Inspect the **Drawdown Probability Distribution** and **Risk of Ruin** ($>30\%$ or $>50\%$ capital loss probability).<br><br>**தமிழ்:**<br>1. பேக்டெஸ்ட் முடிவுகளுக்கு கீழ் உள்ள **Monte Carlo** பகுதிக்கு செல்லவும்.<br>2. கணினி உங்கள் டிரேடுகளை 1,000 முறை மாற்றி அமைத்து (Reshuffle) சோதனை செய்யும்.<br>3. உங்கள் உத்தியின் உண்மைத்தன்மை, அதிகபட்ச சரிவுக்கான வாய்ப்பு மற்றும் முதலீடு அழியக்கூடிய அபாயம் (Risk of Ruin) உள்ளதா என்பதை அறிவியல் பூர்வமாக அறியலாம். | 1,000-run bootstrap resampling simulation. Analyzes sequence risk, validates statistical edge against randomness, and calculates empirical ruin probabilities. | Pro Mode |

---

### 2.6 Paper Trading Simulation & Strategy Dock

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Virtual Brokerage Account & Wallet** | Paper Trading Tab (`#paper-trading-view`) | **English:**<br>1. Navigate to the **Paper Trading** tab.<br>2. View initial starting capital of **₹10,00,000** virtual cash.<br>3. Monitor Available Margin, Utilized Margin, Realized P&L, and Unrealized P&L.<br>4. Click **Reset Account** anytime to restore default ₹10,00,000 balance.<br><br>**தமிழ்:**<br>1. **Paper Trading** பகுதிக்குச் செல்லவும்.<br>2. உங்களுக்கு தொடக்க நிதியாக **₹10,00,000** விர்ச்சுவல் பணம் இருக்கும்.<br>3. உங்கள் கையிருப்பு பணம், பயன்படுத்திய பணம், மற்றும் மொத்த லாப/நஷ்டத்தை பார்க்கலாம்.<br>4. எப்போது வேண்டுமானாலும் **Reset Account** கொடுத்து கணக்கை மீண்டும் ₹10 லட்சத்திற்கு மீட்டமைக்கலாம். | Realistic paper trading engine. Tracks account balance, margin utilization, cash flow, and persists all states in DuckDB tables (`paper_account`, `paper_positions`, `paper_orders`). | Simple & Pro |
| **Order Placement Terminal** | Paper Trading Order Ticket (`#order-ticket`) | **English:**<br>1. In Paper Trading terminal, enter Symbol (e.g. `NSE:RELIANCE-EQ`).<br>2. Select Order Side: **BUY** or **SELL**.<br>3. Select Order Type: **MARKET**, **LIMIT**, **STOP-LOSS (SL-M)**, or **STOP-LOSS LIMIT (SL-L)**.<br>4. Specify Quantity, Limit Price, Trigger Price, and optional Target/Stop-loss brackets.<br>5. Click **Submit Order**.<br><br>**தமிழ்:**<br>1. பங்கை தேர்ந்தெடுத்து **BUY** அல்லது **SELL** கிளிக் செய்யவும்.<br>2. ஆர்டர் வகை: **Market** (உடனடி விலை), **Limit** (குறிப்பிட்ட விலை), அல்லது **Stop-Loss** தேர்வு செய்யவும்.<br>3. பங்கின் எண்ணிக்கை மற்றும் Target/Stop-Loss விலையை உள்ளிட்டு **Submit Order** அழுத்தவும். | Supports standard order execution types. Simulates slippage and Indian statutory transaction fees to reflect live execution accuracy. | Simple & Pro |
| **Real-Time Position Management & Square-Off** | Paper Trading Positions Table | **English:**<br>1. View open positions in the **Positions** table.<br>2. Monitor real-time Mark-to-Market (MTM) P&L updating with live market quotes.<br>3. Click **Edit Risk** to modify Target or Stop-Loss levels.<br>4. Click **Square Off** to close any position instantly, or **Close All** to exit entire portfolio.<br><br>**தமிழ்:**<br>1. தற்போதைய நிலைகளை (Open Positions) அட்டவணையில் பார்க்கலாம்.<br>2. நேரலை விலைக்கு ஏற்ப உங்கள் லாப/நஷ்டம் (MTM) வினாடிக்கு வினாடி மாறும்.<br>3. Target அல்லது Stop-Loss அளவுகளை மாற்றியமைக்கலாம்.<br>4. **Square Off** பட்டனை கிளிக் செய்து உடனடியாக அந்த நிலையை விற்று வெளியேறலாம். | Dynamic mark-to-market valuation against live forming quotes. Automatic bracket order trigger checking and full order audit logging. | Simple & Pro |
| **Strategy Auto-Deployment Engine** | Backtest / Paper Trading Bridge | **English:**<br>1. After validating a strategy in the Backtest Lab, click **Deploy to Paper Trading**.<br>2. Strategy is registered in the paper execution engine (`paper_auto_strategies`).<br>3. Engine evaluates signals on bar completions and submits paper orders automatically.<br>4. Monitor or terminate active strategies from the Paper Trading dashboard.<br><br>**தமிழ்:**<br>1. பேக்டெஸ்ட்டில் ஒரு உத்தி சிறப்பாக செயல்பட்டால், **Deploy to Paper Trading** கிளிக் செய்யவும்.<br>2. அந்த உத்தி விர்ச்சுவல் கணக்கில் தானாக இணைக்கப்பட்டு, மார்க்கெட் சிக்னல் வரும்போது ஆர்டர்களை தானாகவே செயல்படுத்தும்.<br>3. Dashboard-ல் இதன் செயல்பாட்டை கண்காணிக்கலாம் அல்லது நிறுத்தலாம். | Bridges quantitative research directly to forward simulation. Automated signal generation, execution, and strategy lifecycle management. | Pro Mode |

---

### 2.7 Trade Journal & Behavioral Analytics

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Trade Journal Dashboard** | Journal Tab (`#journal-view`) | **English:**<br>1. Navigate to the **Trade Journal** tab.<br>2. View performance overview: **Net P&L (₹)**, **Win Rate %**, **Profit Factor**, **Expectancy**, and **Avg R-Multiple**.<br>3. Inspect the cumulative **Account Equity Curve** tracking balance growth over time.<br><br>**தமிழ்:**<br>1. **Trade Journal** பகுதிக்குச் செல்லவும்.<br>2. உங்கள் மொத்த வர்த்தகத்தின் Net P&L, Win Rate (வெற்றி சதவீதம்), Profit Factor மற்றும் சராசரி R-Multiple அளவீடுகளை பார்க்கலாம்.<br>3. உங்கள் முதலீடு காலப்போக்கில் எப்படி வளர்ந்துள்ளது என்பதை Equity Curve வரைபடம் காட்டும். | Self-directed trading ledger. Automatically computes statistical trade metrics, fee deductions, and equity progression from logged executions. | All Users |
| **1-Click Fyers Tradebook CSV Importer** | Journal Header (`#tradebook-upload`) | **English:**<br>1. Download your official `tradebook.csv` from Fyers Web/Mobile.<br>2. In Trade Journal, click **Choose File** under "Import Fyers Tradebook".<br>3. Select the file and click **Import**.<br>4. All trades, execution timestamps, quantities, prices, and STT are parsed and reconciled instantly.<br><br>**தமிழ்:**<br>1. Fyers-ல் இருந்து `tradebook.csv` டவுன்லோட் செய்யவும்.<br>2. Trade Journal-ல் **Choose File** கிளிக் செய்து அந்த ஃபைலை அப்லோட் செய்யவும்.<br>3. தானாகவே அனைத்து டிரேடுகளும் கணக்கிடப்பட்டு, தரகு மற்றும் வரிகள் கழிக்கப்பட்டு ஜர்னலில் சேர்ந்துவிடும். | Automated broker CSV parser. Features cryptographic trade deduplication, statutory fee reconciliation, and automated round-trip trade matching. | All Users |
| **Interactive P&L Calendar Heatmap** | Journal Sub-Panel (`#journal-calendar`) | **English:**<br>1. Scroll to the **P&L Calendar** in the Journal.<br>2. Calendar displays a monthly grid with green (profitable) and red (loss) trading days.<br>3. Hover over any day to see net profit/loss, trade count, and win rate for that date.<br><br>**தமிழ்:**<br>1. Journal-ல் உள்ள **P&L Calendar** பகுதியை பார்க்கவும்.<br>2. காலண்டரில் நீங்கள் லாபம் ஈட்டிய நாட்கள் பச்சை நிறத்திலும், நஷ்டமடைந்த நாட்கள் சிவப்பு நிறத்திலும் தெரியும்.<br>3. ஏதேனும் ஒரு தேதியின் மீது மவுஸை வைத்தால் அன்றைய லாபத் தொகை மற்றும் செய்த டிரேடுகளின் எண்ணிக்கை தோன்றும். | Visual trading calendar heatmap. Summarizes daily net P&L, volume of executions, and weekly consistency metrics. | All Users |
| **Behavioral Mistake Tagging & Loss Attribution** | Journal Trade List (`#mistake-tag-cloud`) | **English:**<br>1. In the trade history table, click any losing trade.<br>2. Assign emotional mistake tags: `FOMO`, `Revenge Trading`, `Chasing`, `Moved Stoploss`, `Exited Early`, `Over-Leveraged`, or `Broken Plan`.<br>3. Review the **Mistake Tag Cloud** above the table.<br>4. Inspect the exact rupee cost lost per bad habit (e.g. `FOMO: -₹42,500`).<br><br>**தமிழ்:**<br>1. நஷ்டமடைந்த டிரேடில் என்ன தவறு செய்தீர்கள் (FOMO, Revenge Trading, அவசரம், Stop-loss மாற்றியது) என Tag செய்யவும்.<br>2. **Mistake Tag Cloud**-ல் எந்த தவறான பழக்கத்தால் நீங்கள் எவ்வளவு பணம் இழந்தீர்கள் என்பது தெளிவாக கணக்கிடப்பட்டு காட்டப்படும்.<br>3. உளவியல் ரீதியான தவறுகளை திருத்திக் கொள்ள இது பெரிதும் உதவும். | Behavioral finance analytics. Quantifies and attributes financial losses to specific psychological biases, helping traders cultivate discipline. | All Users |

---

### 2.8 Real-Time Alert Engine & Monitoring

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Price & Indicator Threshold Alerts** | Top Navigation Alert Bell (`🔔`) | **English:**<br>1. Click the `🔔` icon in the top header to open the Alerts drawer.<br>2. Click **Create Alert**.<br>3. Set Target Symbol, Condition (`Price Crosses Above`, `Price Crosses Below`, `RSI Crosses 30`, `EMA 9 Crosses 21`), and Threshold Value.<br>4. Click **Save Alert**.<br>5. Notifications appear via toast and sound when triggered.<br><br>**தமிழ்:**<br>1. மேலே உள்ள `🔔` பெல் ஐகானை கிளிக் செய்து Alerts drawer-ஐ திறக்கவும்.<br>2. **Create Alert** கிளிக் செய்து, பங்கு, நிபந்தனை (விலை அல்லது RSI அளவு) ஆகியவற்றை உள்ளிட்டு சேமிக்கவும்.<br>3. சந்தையில் அந்த விலை வந்தவுடன் திரையில் அறிவிப்பு (Toast Notification) வரும். | Rule-based event monitoring engine. Evaluates prices on live quote ticks and bar completions. Features alert deduplication and cooldown windows. | All Users |
| **NSE Market Quiet Hours Enforcement** | Alerts Background Engine | **English:**<br>1. Alert engine checks current IST time against the NSE trading schedule (09:15 to 15:30 IST).<br>2. Alerts outside market hours or on official NSE holidays are automatically suppressed.<br>3. Status displays in the alert drawer as `Market Closed (Quiet Hours Active)`.<br><br>**தமிழ்:**<br>1. சந்தை நேரத்திற்கு வெளியே (மாலை 03:30 முதல் காலை 09:15 வரை) மற்றும் விடுமுறை நாட்களில் அலர்ட்டுகள் தானாகவே நிறுத்தி வைக்கப்படும் (Quiet Hours).<br>2. இதனால் தேவையற்ற தொந்தரவுகள் தவிர்க்கப்படும். | Automated quiet hours compliance aligned with the dynamic NSE holiday calendar and daily trading hours. | All Users |

---

### 2.9 Dual Persona UX (Simple vs. Pro Mode)

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Persona Mode Switcher** | Top Navigation Center | **English:**<br>1. Click **Simple** for a distraction-free, beginner-friendly view.<br>2. Click **Pro** to unlock multi-timeframes, indicators, drawing tools, options matrices, and advanced backtesting.<br>3. Selection is saved automatically in browser `localStorage`.<br><br>**தமிழ்:**<br>1. எளிய இடைமுகத்திற்கு **Simple** பட்டனை கிளிக் செய்யவும்.<br>2. அனைத்து தொழில்நுட்ப வரைபடங்கள், டூல்கள் மற்றும் backtesting வேண்டும் என்றால் **Pro** பட்டனை கிளிக் செய்யவும்.<br>3. உங்கள் தேர்வு பிரவுசரில் தானாக நினைவில் வைக்கப்படும். | Dynamically toggles interface density, toolbar visibilities, and complexity levels across all views. | All Users |
| **Plain-Language Financial Translations** | Simple Mode Elements | **English:**<br>1. Switch to **Simple Mode**.<br>2. Complex quant terms transform into clear English (e.g. "VWAP" becomes "Average Traded Price", "OHLCV" becomes "Daily Price & Volume", "Drawdown" becomes "Peak Account Dip").<br><br>**தமிழ்:**<br>1. Simple Mode-ல் கடினமான பங்குச்சந்தை வார்த்தைகள் எளிய மொழியில் தானாக மாற்றப்படும். | Replaces intimidating technical jargon with plain-language equivalents via `/api/v1/system/ux_translations`. | Simple Mode |
| **3-Part Educational Context Micro-Cards** | Hover over dotted terms (`?`) | **English:**<br>1. In Simple Mode, hover over any term with a dotted underline or `?` icon.<br>2. An educational card appears showing:<br>   - **1. Plain Definition**: Clear, jargon-free explanation.<br>   - **2. Real-World Analogy**: Relatable everyday metaphor.<br>   - **3. Key Risk Warning**: Important risk reminder.<br><br>**தமிழ்:**<br>1. Simple Mode-ல் ஏதேனும் ஒரு சொல்லின் அருகில் உள்ள `?` மீது மவுஸை வைத்தால் விளக்க அட்டை தோன்றும்.<br>2. அதன் விளக்கம், எளிய உதாரணம் மற்றும் சந்தை அபாயங்கள் (Risks) தெளிவாக காட்டப்படும். | 3-part pedagogical micro-cards designed to teach retail traders sound trading concepts safely and intuitively. | Simple Mode |

---

### 2.10 Ingestion Telemetry & Session Management

| Feature | UI Location / Shortcut | Step-by-Step Instructions & தமிழ் விளக்கம் | Capabilities & Technical Specs | User Persona |
| :--- | :--- | :--- | :--- | :--- |
| **Downloader Live Telemetry Drawer** | Top Right Header (`Downloads`) | **English:**<br>1. Click the **Downloads** button in the header.<br>2. Slide-out drawer displays live historical ingestion speed (req/min & candles/sec).<br>3. Monitor the **Daily API Quota Meter** (out of 90,000 requests) and active symbol.<br>4. Click **Pause**, **Resume**, or **Cancel** to manage active background batch jobs.<br><br>**தமிழ்:**<br>1. Header-ல் உள்ள **Downloads** பட்டனை கிளிக் செய்யவும்.<br>2. டேட்டா டவுன்லோட் ஆகும் வேகம், Fyers-ன் 90,000 API வரம்பில் மீதமுள்ள அளவு மற்றும் எந்த பங்கு டவுன்லோட் ஆகிறது என்பதை பார்க்கலாம்.<br>3. தேவைப்பட்டால் Pause அல்லது Resume செய்யலாம். | Real-time Server-Sent Events (SSE) telemetry (`/api/v1/system/downloader/stream`). Displays active download lane, throughput, checkpoint states, and quota utilization. | Pro Mode |
| **Authentication Session Badge & Quick Refresh** | Top Right Header (`#auth-badge`) | **English:**<br>1. View the live session badge: `🔑 Token: --h --m`.<br>2. Turns amber when $<48$ hours remain on the 15-day refresh token.<br>3. Click badge to open Auth Modal.<br>4. Click **Quick Refresh** for instant renewal or **Login via Browser** for a fresh Fyers OAuth session.<br><br>**தமிழ்:**<br>1. Header-ல் டோக்கன் இன்னும் எத்தனை மணி நேரம் செல்லும் என்ற கவுண்டவுன் இருக்கும்.<br>2. டோக்கன் காலாவதியாக 48 மணி நேரத்திற்குள் இருந்தால் மஞ்சள் நிறத்தில் எச்சரிக்கும்.<br>3. அதை கிளிக் செய்து **Quick Refresh** கொடுத்தால் பிரவுசர் லாகின் இல்லாமலேயே டோக்கன் புதுப்பிக்கப்படும். | Proactive authentication monitor. Tracks 24-hour access token and 15-day refresh token expiration countdowns with 1-click token rotation. | All Users |
| **Multi-Format Data Exporter** | Pro Toolbar (`#btn-export`) | **English:**<br>1. Click **Export Data** in the toolbar.<br>2. Select format: **Parquet** (recommended, compressed, typed), **CSV**, or **Excel**.<br>3. Review estimated row count.<br>4. Click **Download File**.<br><br>**தமிழ்:**<br>1. Toolbar-ல் **Export Data** கிளிக் செய்யவும்.<br>2. Parquet, CSV அல்லது Excel-ல் ஒன்றை தேர்வு செய்யவும்.<br>3. **Download** கிளிக் செய்தால் உங்கள் கணினியில் தரவு சேமிக்கப்படும். | Exports split-adjusted historical OHLCV data directly from DuckDB views to local disk. | Pro Mode |
| **Excel 1-Million Row Safety Guard** | Export Modal | **English:**<br>1. In Export Modal, select **Excel**.<br>2. If dataset exceeds 1,048,575 rows, Excel is automatically disabled with an amber warning badge.<br>3. User is prompted to select **Parquet** or **CSV** instead to prevent silent data corruption.<br><br>**தமிழ்:**<br>1. எக்செல் ஃபைலில் 10,48,575 வரிசைகளுக்கு மேல் இருந்தால் ஃபைல் பழுதாகாமல் தடுக்க எக்செல் ஆப்ஷன் முடக்கப்படும்.<br>2. தரவு முழுமையாக கிடைக்க Parquet அல்லது CSV தேர்வு செய்யுமாறு வழிகாட்டும். | Prevents silent data truncation and corrupted `.xlsx` spreadsheets caused by Microsoft Excel's hard row limit. | Pro Mode |

---

## 3. CLI Tools & Background Automation Catalog

The platform provides dedicated command-line utilities and batch scripts for data backfills, database inspection, and server operations:

| Utility / Script | Command Line Execution | Step-by-Step Instructions & தமிழ் விளக்கம் | Functionality & Technical Specs |
| :--- | :--- | :--- | :--- |
| **1-Click Web Server Launcher** | `.\start_server.bat` | **English:** Double-click or run in PowerShell to start the FastAPI server on port 8000.<br>**தமிழ்:** PowerShell-ல் `.\start_server.bat` என இயக்கினால் வெப் சர்வர் `http://localhost:8000`-ல் தொடங்கும். | Validates Python environment, initializes DuckDB tables, and launches Uvicorn server with single-writer lock configuration. |
| **1-Click Clean Stop Utility** | `.\stop_server.bat` | **English:** Run to stop the web server and clear any remaining DuckDB lock files.<br>**தமிழ்:** டவுன்லோட் செய்வதற்கு முன் சர்வரை சுத்தமாக நிறுத்த `.\stop_server.bat` இயக்கவும். | Gracefully terminates port 8000 processes and removes any orphan `.pid` or lock files to prevent DuckDB locking conflicts. |
| **Interactive Download Wizard** | `.\download_all.bat` | **English:**<br>1. Run `.\stop_server.bat` if the server is active.<br>2. Run `.\download_all.bat`.<br>3. Enter `1` for Nifty 50, `2` for Nifty 500, or `3` for All 2,581 Stocks.<br><br>**தமிழ்:**<br>1. `.\download_all.bat` இயக்கவும்.<br>2. `1` அழுத்தினால் Nifty 50, `2` அழுத்தினால் Nifty 500 பங்குகள் 1D மற்றும் 1m டேட்டா தானாக பதிவிறக்கம் ஆகும். | Interactive CLI menu downloading 15-year 1D and 5-year 1m candles. Uses checkpoint resumption, error -300 recovery, and automatic rate-governor throttling. |
| **Full Historical Backfill CLI** | `.\.venv\Scripts\python.exe scripts/run_historical_download.py --all` | **English:** Run in PowerShell when server is stopped to backfill all 2,581 NSE equities.<br>**தமிழ்:** அனைத்து 2,581 பங்குகளுக்கும் முழு டேட்டாவையும் ஒரே கமாண்டில் பதிவிறக்கம் செய்ய இதை இயக்கவும். | Automated backfill engine. Manages multi-year chunking, checkpoint recovery in DuckDB `download_checkpoints`, and respects the 180 req/min rolling limit. |
| **Targeted Symbol Download** | `.\.venv\Scripts\python.exe scripts/run_historical_download.py --symbols NSE:RELIANCE-EQ,NSE:TCS-EQ --timeframe both` | **English:** Ingests 1D and 1m history for specific comma-separated symbols.<br>**தமிழ்:** உங்களுக்கு தேவையான குறிப்பிட்ட பங்குகளை மட்டும் பதிவிறக்கம் செய்ய கமா கொடுத்து இயக்கவும். | Pulls historical candles for specified tickers directly into `candles_1m_raw` and `candles_1d_raw`. |
| **Database Inspector Utility** | `.\.venv\Scripts\python.exe scripts/inspect_db.py` | **English:** Run anytime (online or offline) to inspect table counts and database size.<br>**தமிழ்:** டேட்டாபேஸில் எத்தனை வரிசைகள் மற்றும் அட்டவணைகள் உள்ளன என்பதை பார்க்க இதை இயக்கவும். | Prints comprehensive summary of all 17 DuckDB tables, total candle records, views, and `.duckdb` file size on disk. Supports `--table` and `--query` flags. |
| **Fyers OAuth Login CLI** | `.\.venv\Scripts\python.exe -m scripts.auth_cli --login` | **English:** Terminal-based OAuth login helper.<br>**தமிழ்:** புதிய Fyers டோக்கன் பெற இதை இயக்கினால் பிரவுசர் திறந்து லாகின் செய்ய உதவும். | Generates Fyers authorization URL, captures authorization code and 4-digit PIN, exchanges tokens, and encrypts credentials into OS Keyring. |
| **Token Status & Refresh CLI** | `.\.venv\Scripts\python.exe -m scripts.auth_cli --status` | **English:** Checks active token lifespan and remaining refresh window.<br>**தமிழ்:** தற்போதைய டோக்கன் செல்லுபடியாகும் காலத்தை பார்க்க இதை இயக்கவும். | Displays hours remaining on the 24-hour access token and days remaining on the 15-day refresh token. Supports `--refresh` flag. |
| **Zero-Secret Security Scanner** | `.\.venv\Scripts\python.exe scripts/audit_security.py` | **English:** Scans codebase for exposed API keys, tokens, or uncommitted secrets.<br>**தமிழ்:** கோப்புகளில் ஏதேனும் ரகசிய சாவிகள் (API keys) உள்ளதா என பாதுகாப்பை சரிபார்க்க உதவும். | Audits source files, git diffs, and configuration files to ensure strict zero-secret compliance before commits. |

---

## 4. Complete REST API Endpoint Directory

All endpoints are hosted under `http://localhost:8000/api/v1` and return standardized JSON envelopes (`ApiResponse[T]`):

```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed successfully",
  "correlation_id": "req-a1b2c3d4",
  "execution_time_ms": 12.4
}
```

### 4.1 System & Health (`/api/v1/...`)
- `GET /api/v1/health`: Server health check, DuckDB connection status, and token lifecycle status.
- `GET /ready`: Kubernetes/Docker readiness probe checking database availability.
- `GET /api/v1/system/downloader/stream`: Server-Sent Events (SSE) telemetry stream for background downloads.
- `POST /api/v1/system/downloader/control`: Controls active downloader job (`pause`, `resume`, `cancel`).
- `GET /api/v1/system/ux_translations`: Plain-language translation dictionary for Simple Mode.
- `GET /api/v1/system/db/stats`: Live database statistics, table row counts, and file size.

### 4.2 Authentication (`/api/v1/auth/...`)
- `GET /api/v1/auth/status`: Current session status, token expiration countdowns, and refresh window.
- `POST /api/v1/auth/refresh`: 1-click rotation renewing the 24-hour access token via refresh token.
- `POST /api/v1/auth/token`: Exchanges OAuth authorization code for new access/refresh tokens.
- `GET /api/v1/auth/login`: Generates Fyers OAuth authorization URL.
- `GET /api/v1/auth/callback`: OAuth callback handler capturing authorization code.

### 4.3 Symbols & Market Quotes (`/api/v1/symbols/...`)
- `GET /api/v1/symbols/search?q={query}`: Substring search across all 2,581 NSE equities.
- `GET /api/v1/symbols/popular`: High-turnover recommended symbols and index constituents.

### 4.4 Candles & Data Ingestion (`/api/v1/candles/...`)
- `GET /api/v1/candles`: Historical candles query. Supports `symbol`, `timeframe`, `from_date`, `to_date`, `limit`, and `before_timestamp` for lazy loading.
- `GET /api/v1/candles/live?symbol={symbol}`: JIT sync endpoint returning today's forming candle and real-time tick.

### 4.5 Technical Studies & Candlestick Patterns (`/api/v1/studies/...`)
- `GET /api/v1/studies/catalog`: Complete catalog of available indicators, overlays, and subpanes.
- `GET /api/v1/studies/{study_id}`: Technical indicator definition and mathematical parameters.
- `POST /api/v1/studies/patterns`: Detects 12 classical candlestick patterns across given candle arrays.
- `GET /api/v1/studies/session-volume-profile`: Computes Volume Profile (POC, VAH, VAL) for visible session.
- `GET /api/v1/studies/tpo-profile`: Computes Time-Price Opportunity (TPO) Market Profile structure.

### 4.6 Chart Drawing Annotations (`/api/v1/chart/drawings/...`)
- `GET /api/v1/chart/drawings/{symbol}`: Retrieves all saved drawings (trendlines, fibonacci, zones) for a symbol.
- `POST /api/v1/chart/drawings/{symbol}`: Saves a new drawing annotation to DuckDB.
- `PUT /api/v1/chart/drawings/{drawing_id}`: Updates coordinates, anchors, or styles of an existing drawing.
- `DELETE /api/v1/chart/drawings/{symbol}/all`: Clears all drawings for a specific symbol.
- `DELETE /api/v1/chart/drawings/{drawing_id}`: Deletes an individual drawing by ID.

### 4.7 Stock Screener Engine (`/api/v1/screener/...`)
- `GET /api/v1/screener/templates`: Returns predefined and custom saved screener filter templates.
- `POST /api/v1/screener/templates`: Creates and saves a new custom screener template.
- `DELETE /api/v1/screener/templates/{template_id}`: Deletes a saved screener template.
- `GET /api/v1/screener/status`: Returns last sync timestamp and database freshness status.
- `POST /api/v1/screener/sync-live`: Triggers on-demand rate-governed quote sync across screened universe.
- `POST /api/v1/screener/run`: Executes multi-parameter screening query against DuckDB views.

### 4.8 Options Suite & Analytics (`/api/v1/options/...`)
- `GET /api/v1/options/chain?symbol={symbol}&expiry={expiry}`: Full strike matrix with Calls, Puts, LTP, OI, and IV.
- `GET /api/v1/options/underlyings`: Master list of 4 indices and 180+ equity F&O underlyings with official lot sizes.
- `GET /api/v1/options/greeks?symbol={symbol}&expiry={expiry}`: Real-time Black-Scholes Greeks ($\Delta, \Gamma, \Theta, \mathcal{V}$).
- `GET /api/v1/options/maxpain?symbol={symbol}&expiry={expiry}`: Expiration strike with minimum seller payout.
- `GET /api/v1/options/open-interest?symbol={symbol}&expiry={expiry}`: PCR (Total OI & $\Delta$OI), Support/Resistance walls, and sentiment badge.
- `GET /api/v1/options/payoff`: Generates P&L payoff curves for standard single-leg or spread presets.
- `POST /api/v1/options/strategy/greeks`: Calculates aggregate net Greeks for multi-leg option combinations.
- `POST /api/v1/options/strategy/payoff`: Simulates expiration and pre-expiry ($T-t$) P&L payoff curves for custom spreads.

### 4.9 Quantitative Backtesting & Optimization (`/api/v1/backtest/...`)
- `POST /api/v1/backtest/run`: Runs single-symbol backtest with statutory Indian tax modeling and slippage.
- `GET /api/v1/backtest/results/{backtest_id}`: Fetches detailed backtest metrics, trade logs, and equity series.
- `POST /api/v1/backtest/scan-universe`: Executes a strategy scan across an entire index universe.
- `GET /api/v1/backtest/portfolio/universes`: Available universe baskets (`NIFTY 50`, `NIFTY NEXT 50`, `NIFTY 500`) with live constituent counts.
- `POST /api/v1/backtest/portfolio/run`: Executes multi-stock portfolio simulation with rebalancing and position sizing.
- `GET /api/v1/backtest/optimize/presets`: Predefined parameter optimization templates.
- `POST /api/v1/backtest/optimize`: Executes parameter grid search and generates 2D sensitivity heatmaps.

### 4.10 Paper Trading Simulation (`/api/v1/paper-trading/...`)
- `GET /api/v1/paper-trading/account`: Account balance, margins, realized P&L, and unrealized P&L.
- `POST /api/v1/paper-trading/account/reset`: Resets paper trading balance back to default ₹10,00,000.
- `GET /api/v1/paper-trading/positions`: Active open positions with live Mark-to-Market P&L.
- `POST /api/v1/paper-trading/orders`: Submits new paper order (`MARKET`, `LIMIT`, `SL-M`, `SL-L`).
- `POST /api/v1/paper-trading/positions/{symbol}/close`: Squares off open position for a symbol.
- `PUT /api/v1/paper-trading/positions/{symbol}/risk`: Updates Target or Stop-Loss bracket levels.
- `GET /api/v1/paper-trading/orders`: Order history ledger and pending limit orders.
- `GET /api/v1/paper-trading/history`: Closed trade execution history and realized P&L.
- `POST /api/v1/paper-trading/deploy-strategy`: Registers backtested strategy for automated paper execution.
- `GET /api/v1/paper-trading/auto-strategies`: List of active deployed auto-trading strategies.
- `POST /api/v1/paper-trading/auto-strategies/{id}/stop`: Halts an active deployed strategy.
- `DELETE /api/v1/paper-trading/auto-strategies/{id}`: Deletes a deployed strategy.
- `POST /api/v1/paper-trading/auto-strategies/evaluate`: Evaluates market signals for active auto-strategies.

### 4.11 Trade Journal & Behavioral Analytics (`/api/v1/journal/...`)
- `GET /api/v1/journal/trades`: Retrieves logged trade records, mistake tags, and notes.
- `POST /api/v1/journal/trade`: Manually creates or edits a trade entry.
- `DELETE /api/v1/journal/trades/{trade_id}`: Deletes an individual trade record.
- `POST /api/v1/journal/import`: Uploads and parses official Fyers `tradebook.csv`.
- `GET /api/v1/journal/metrics`: Summary KPIs: Win Rate, Profit Factor, Expectancy, and Average R-Multiple.
- `POST /api/v1/journal/sample-data`: Generates realistic sample trades for demonstration.
- `DELETE /api/v1/journal/clear`: Clears all journal entries.

### 4.12 Real-Time Alerts (`/api/v1/alerts/...`)
- `GET /api/v1/alerts/status`: Alert engine health, active rules count, and Quiet Hours status.
- `GET /api/v1/alerts`: List of configured alert rules.
- `POST /api/v1/alerts`: Creates a new price or indicator threshold alert rule.
- `DELETE /api/v1/alerts/{alert_id}`: Deletes an alert rule.

### 4.13 Data Exporter (`/api/v1/export`)
- `GET /api/v1/export`: Streams clean, split-adjusted OHLCV datasets in `parquet`, `csv`, or `excel` format. Features the 1,048,575 row safety limit on Excel exports.

### 4.14 Statutory Regulatory Order Gate (`HTTP 403 Forbidden`)
- `ALL /api/v1/orders/*`: Permanently disabled broker live execution gateway. All live order routing attempts return `403 Forbidden` with a statutory notice affirming that the platform is strictly a research and backtesting tool.

---

## 5. DuckDB Database Schema & Views Architecture

The DuckDB database file is located at `data/db/nse_quant.duckdb`. It consists of 17 dedicated tables and 2 dynamic SQL views:

### 5.1 Tables Master Directory

```
+---------------------------------------------------------------------------------------------+
|                                    DUCKDB TABLES CATALOG                                    |
+--------------------------+------------------------------------------------------------------+
| Table Name               | Description & Stored Fields                                      |
+--------------------------+------------------------------------------------------------------+
| symbols                  | Master directory of 2,581 NSE equities (ticker, name, industry) |
| candles_1m_raw           | Append-only 1-minute unadjusted OHLCV historical bars            |
| candles_1d_raw           | Append-only 1-day unadjusted OHLCV historical bars               |
| corporate_actions        | Splits, bonuses, and face value history                          |
| adjustment_factors       | Multiplicative split adjustment factors (A_t = prod r_i)         |
| download_checkpoints     | State machine tracking completed multi-year historical chunks    |
| market_holidays          | Dynamic NSE market holiday dates and session exclusions          |
| job_logs                 | System operational logs, ingestion speeds, and error traces      |
| journal_entries          | Manual and imported broker trades, STT, and mistake tags         |
| paper_account            | Virtual trading balance, margin utilization, and cash reserves   |
| paper_positions          | Open paper trading positions and mark-to-market prices           |
| paper_orders             | Paper order tickets (Market, Limit, Stop-Loss)                   |
| paper_trades             | Paper trade execution fills and commission records               |
| paper_auto_strategies    | Deployed backtested strategies running in paper simulation       |
| chart_drawings           | Persisted technical drawings (trendlines, fibonacci, zones)      |
| option_chain_snapshots   | Historical snapshots of option chains and Greeks matrices        |
| schema_version           | Migration tracking table verifying schema integrity              |
+--------------------------+------------------------------------------------------------------+
```

### 5.2 Dynamic Split-Adjusted SQL Views
- **`candles_1d_adjusted`**: Dynamically multiplies raw 1D prices by cumulative adjustment factors:
  $$\text{Adjusted Price} = \text{Raw Price} \times A_t$$
  $$\text{Adjusted Volume} = \text{Raw Volume} / A_t$$
- **`candles_1m_adjusted`**: Dynamically multiplies raw 1m prices by cumulative adjustment factors for continuous intraday price action across historical stock splits.

---

## 6. Keyboard Shortcuts & Quick Navigation Reference

| Shortcut | Context | Action / Result |
| :--- | :--- | :--- |
| **`Ctrl + K`** | Universal | Opens Smart Symbol Search modal across 2,581 NSE equities. |
| **`Esc`** | Universal | Closes any open modal (Search, Auth, Export, Settings) or slide-out drawer. |
| **`Double-Click`** | Chart Canvas | Auto-fits price and time scales to the full screen viewport. |
| **`Mouse Scroll Wheel`** | Chart Canvas | Zooms in or out centered on cursor position. |
| **`Left-Click + Drag`** | Chart Canvas | Pans horizontally across historical bars or vertically along the price axis. |
| **`Alt + T`** | Pro Chart | Activates the Trendline drawing tool. |
| **`Alt + H`** | Pro Chart | Activates the Horizontal Ray drawing tool. |
| **`Alt + F`** | Pro Chart | Activates the Fibonacci Retracement tool. |
| **`Delete` / `Backspace`** | Selected Drawing | Deletes the currently selected chart drawing annotation. |

---

## 7. Recommended Daily Trading & Research Workflow

Follow this institutional routine (பரிந்துரைக்கப்படும் தினசரி முறை) to maximize the analytical power of the platform:

### 1. Pre-Market Preparation (08:30 – 09:15 IST)
1. **Launch Server:** Run `.\start_server.bat` in PowerShell and navigate to `http://localhost:8000`.
2. **Session Verification:** Check the header badge to ensure `🔑 Token: >10h` is active. If expiring, click **Quick Refresh**.
3. **Market Calendar Check:** Verify today is an active NSE trading day.
4. **Screener Scan:** Open **Screener**, select the **NIFTY 500** universe, and run the **52-Week High** and **Volume Spike** filters to identify leading stocks with momentum.

### 2. Live Market Operations (09:15 – 15:30 IST)
1. **Intraday Charting:** Open shortlisted symbols using `Ctrl + K`. Switch to `5m` or `15m` timeframes.
2. **Technical Confluence:** Overlay **VWAP**, **EMA (9, 21, 50)**, and enable **Candlestick Patterns** to spot institutional entry setups.
3. **F&O Surveillance:** For index trading (`NIFTY 50`, `BANK NIFTY`), open the **Options** tab to track the **Max Pain Strike**, **PCR OI**, and shifting Call/Put open interest walls.
4. **Paper Execution:** Test trade ideas in real-time using the **On-Chart Paper Trade Dock** with defined Target and Stop-Loss brackets.

### 3. Post-Market Journaling & Analysis (15:30 – 17:00 IST)
1. **Import Broker Trades:** Download `tradebook.csv` from Fyers and upload it to the **Trade Journal** in 1 click.
2. **Behavioral Tagging:** Review executed trades. Assign mistake tags (`FOMO`, `Chasing`, `Revenge`) to losing trades to track psychological discipline in the **Mistake Tag Cloud**.
3. **Performance Review:** Check today's P&L in the **P&L Calendar Heatmap** and review Win Rate % and Profit Factor.

### 4. Weekend Quant Research & Backtesting
1. **Strategy Development:** Open **Backtest Lab** to test rules on 15 years of split-adjusted data.
2. **Portfolio Testing:** Use the **Portfolio Studio** to evaluate multi-stock baskets with ATR risk parity sizing against the Nifty 50 benchmark.
3. **Robustness Validation:** Run the **Optimizer** to locate parameter stability zones and test with 1,000 **Monte Carlo** runs to verify edge stability and risk of ruin.

---

## 8. Statutory Regulatory Compliance Notice

> [!IMPORTANT]
> **STATUTORY SEBI REGULATORY DISCLAIMER**
> 
> The **NSE Quant Platform** is an independent, local-first analytical workstation designed strictly for educational, personal research, and algorithmic backtesting purposes.
> 
> 1. **No Investment Advice:** The platform does not provide investment advisory services, trading tips, or financial recommendations as defined under the SEBI (Investment Advisers) Regulations, 2013.
> 2. **No Automated Live Execution:** Live broker order routing is intentionally disabled (`HTTP 403 Forbidden`). All trade execution features operate strictly in simulated paper trading environments.
> 3. **Market Risks:** Trading in securities markets, particularly futures and options (F&O), involves substantial financial risk. Users are solely responsible for their own investment and trading decisions.
