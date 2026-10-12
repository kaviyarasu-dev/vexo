# Requirements Document: TradingView Indicators, Strategies, Profiles & Patterns Modal

## 1. Executive Summary & Objective
Implement a TradingView-identical **"Indicators, metrics, and strategies"** modal dialog integrated with the interactive Lightweight Charts workspace in the NSE Quant Platform.
The modal provides centralized discovery, search, configuration, and one-click application of:
1. **Technicals -> Indicators**: Moving Averages (SMA, EMA, WMA), VWAP, Bollinger Bands, RSI, MACD, ATR, Supertrend, Stochastic Oscillator.
2. **Technicals -> Strategies**: Backtestable algorithmic strategies with trade markers, entry/exit rules, and one-click backtest execution dock.
3. **Technicals -> Profiles**: Volume Profiles (Visible Range VRVP, Session Volume Profile SVP, Fixed Range FRVP, Auto Anchored AAVP) and Market Profile / Time Price Opportunity (TPO).
4. **Technicals -> Patterns**: Candlestick patterns (Engulfing, Doji, Hammer, Morning/Evening Star, Shooting Star) and Chart patterns (Head & Shoulders, Double Top/Bottom, Triangles).
5. **Technicals -> Options**: Option analytics (Greeks profile, IV Skew/Rank, Max Pain, PCR, Open Interest distribution, Payoff curves).
6. **Built-in -> Fundamentals**: Key fundamental metrics (P/E, EPS, Market Cap, Debt/Equity, ROE).
7. **Personal & Community**: Custom saved indicators/scripts, user-created templates, and institutional quant presets.

---

## 2. TradingView Modal UX/UI Specifications (from Reference Image)
- **Header**:
  - Modal Title: `Indicators, metrics, and strategies`
  - Global Search Input: Real-time fuzzy filtering across name, description, author, and tags.
  - Close Button: `✕` (Supports Escape key & outside-click dismissal).
- **Left Sidebar Navigation**:
  - `PERSONAL`:
    - My scripts (Custom multi-indicator templates and saved setups)
    - Purchased / Favorites (Pinned/starred indicators for 1-click access)
  - `BUILT-IN`:
    - Technicals (Active view with 5 sub-category pills)
    - Fundamentals (Financial valuation and accounting metrics)
  - `COMMUNITY`:
    - Editors' picks (Platform-curated institutional models)
    - Top (Most frequently used indicators by retail traders)
    - Trending (Momentum, breakout, and high-volatility setups)
    - Marketplace / Presets (Pre-packaged multi-indicator templates)
- **Sub-Category Navigation (Pills inside Technicals)**:
  - `Indicators`
  - `Strategies`
  - `Profiles` (As highlighted in the reference image)
  - `Patterns`
  - `Options`
- **Main List / Table Content**:
  - Column header: `SCRIPT NAME`
  - Star / Favorite icon toggle per row.
  - Interactive item selection highlighting the row.
  - Info button/tooltip explaining the mathematical logic and usage.
  - "Apply to Chart" / "Add" action button.
  - Active indicators drawer / management list (hide/show eye icon, settings gear, remove `✕`).

---

## 3. Detailed Category & Script Catalog Specifications

### Category 3.1: Technicals -> Indicators
1. **Simple Moving Average (SMA)**: Rolling arithmetic mean of closing prices over $N$ periods ($N=20, 50, 200$). Plotted as an overlay line on the candlestick pane.
2. **Exponential Moving Average (EMA)**: Exponentially weighted moving average giving higher weight to recent prices: $\text{EMA}_t = P_t \cdot \alpha + \text{EMA}_{t-1} \cdot (1 - \alpha)$, where $\alpha = \frac{2}{N+1}$.
3. **Volume Weighted Average Price (VWAP)**: Intraday benchmark resetting daily at 09:15 IST: $\text{VWAP} = \frac{\sum (P_{\text{typical}} \cdot V)}{\sum V}$, where $P_{\text{typical}} = \frac{H + L + C}{3}$.
4. **Bollinger Bands (BB)**: Center SMA (period 20) with Upper and Lower bands placed $K$ standard deviations away ($K=2.0$). Includes shaded volatility channel.
5. **Relative Strength Index (RSI)**: Momentum oscillator bounded between 0 and 100 calculated via Wilder's smoothing. Rendered in a dedicated sub-pane with 70/30 overbought/oversold levels.
6. **Moving Average Convergence Divergence (MACD)**: Fast EMA (12) minus Slow EMA (26), 9-day Signal line, and histogram bars rendered in a dedicated sub-pane.
7. **Average True Range (ATR)**: Volatility measure of market price range. Rendered in a sub-pane.
8. **Supertrend**: Trend-following indicator based on ATR and factor multiplier ($N=10$, Multiplier=3.0), plotted as green/red trailing stop line on candlestick pane.
9. **Stochastic Oscillator**: Compares a particular closing price to a range of prices over $N$ periods (%K and %D lines in sub-pane).

### Category 3.2: Technicals -> Strategies
1. **SMA Crossover Strategy**: Buys when fast SMA crosses above slow SMA; exits or shorts when fast crosses below slow.
2. **RSI Reversal Strategy**: Buys when RSI crosses below 30 and recovers; sells when RSI crosses above 70 and falls back.
3. **Bollinger Bands Mean Reversion Strategy**: Buys on touch of lower band with bullish rejection; exits on center band or upper band.
4. **Supertrend Trend Following Strategy**: Enters long on green supertrend flip; exits on red supertrend flip.
5. **MACD Momentum Strategy**: Enters on MACD histogram zero-line crossing; exits on MACD signal line crossover.
*Action*: Plots Buy/Sell execution marker arrows on the chart and opens a collapsible "Strategy Tester" summary dock at the bottom showing Net Profit, Win Rate, Profit Factor, Max Drawdown, and "Deep Dive in Backtest Lab" button.

### Category 3.3: Technicals -> Profiles (Volume Profile & Market Profile)
1. **Visible Range Volume Profile (VRVP)**: Dynamically scans currently visible chart bars in the viewport, bins volume into price increments, calculates Point of Control (POC - peak volume price), Value Area High (VAH), and Value Area Low (VAL) covering 70% of traded volume. Renders as horizontal volume histogram on right edge of chart.
2. **Session Volume Profile (SVP)**: Computes volume distribution separately for each trading day (09:15 - 15:30 IST), rendering per-session volume profiles with individual daily POC, VAH, and VAL.
3. **Fixed Range Volume Profile (FRVP)**: User selects custom start and end time boundaries to calculate volume distribution for a specific accumulation/distribution zone.
4. **Auto Anchored Volume Profile (AAVP)**: Automatically anchors volume profile to the highest volume bar, lowest low, or highest high of the visible lookback window.
5. **Time Price Opportunity (TPO / Market Profile)**: 30-minute letter brackets (A to M for NSE market hours) mapping price versus time, identifying Initial Balance (IB: first hour), Value Area, and Single Print buying/selling tails.

### Category 3.4: Technicals -> Patterns (Candlestick & Chart Patterns)
1. **Bullish & Bearish Engulfing**: Detects candle body completely engulfing preceding candle body with opposite sentiment. Places `BE` badge on candle.
2. **Hammer & Inverted Hammer**: Detects long lower/upper shadow ($\ge 2\times$ body) and small body near opposite extreme. Places `H` / `IH` badge on candle.
3. **Doji & Dragonfly / Gravestone Doji**: Detects candles where Open $\approx$ Close with significant wicks. Places `D` badge on candle.
4. **Morning Star & Evening Star**: 3-candle reversal pattern detecting exhaustion candle followed by decisive opposite trend confirmation.
5. **Double Top & Double Bottom**: Identifies twin swing highs or lows within $\pm 0.5\%$ price tolerance confirming M or W reversal patterns.
6. **Head and Shoulders**: Identifies left shoulder, higher head, and right shoulder with neckline support level.

### Category 3.5: Technicals -> Options
1. **Max Pain Level**: Plots the option strike where option writers experience minimum cumulative payout as a horizontal benchmark line on the stock chart.
2. **Put-Call Ratio (PCR)**: Computes Total Put OI / Total Call OI; rendered as an oscillator sub-pane below chart.
3. **Strike Open Interest Profile**: Renders Call OI (red) vs Put OI (green) horizontal bar chart at respective strike price levels alongside the stock price.
4. **Implied Volatility (IV) Rank & Percentile**: Displays active IV context badge on legend HUD.

### Category 3.6: Built-in -> Fundamentals
1. **Valuation Multiples**: P/E, P/B, Market Capitalization.
2. **Profitability & Quality**: EPS (TTM), Return on Equity (ROE), Return on Capital Employed (ROCE).
3. **Solvency & Balance Sheet**: Debt to Equity, Free Cash Flow.
*Display*: Renders a floating HUD fundamental scorecard widget on chart.

### Category 3.7: Personal & Community
1. **My Scripts / Presets**: Saved multi-indicator bundles (e.g. "Triple EMA + VWAP + RSI").
2. **Favorites**: Starred indicators stored in `localStorage` for instant 1-click loading.
3. **Editors' Picks**: Institutional quant setups ("Intraday Breakout", "Swing Momentum", "Options Buyer/Seller Suite").

---

## 4. Architectural Implementation Blueprint
- **Frontend Layer**:
  - Modal Dialog Component: `static/js/study_dialog.js` + `static/css/study_dialog.css`.
  - Chart Series & Sub-Pane Manager: `static/js/chart_studies.js` handling dynamic sub-panes for RSI/MACD, markers for patterns/strategies, and Canvas overlays for Volume Profile.
  - Top Toolbar Entry Point: `fx Indicators` button in `#pro-toolbar`.
- **Backend API Layer**:
  - `GET /api/v1/studies/catalog`: JSON catalog of all indicators, strategies, profiles, patterns, options, and fundamentals with metadata, inputs, and formulas.
  - `GET /api/v1/studies/volume-profile`: Computes server-side SVP / DuckDB 1-minute volume binning.
  - `GET /api/v1/studies/patterns`: High-performance pattern scanner returning timestamped pattern markers.
  - `GET /api/v1/studies/options-context`: Returns Max Pain, PCR, and strike OI distribution.
- **Data & Storage Layer**:
  - DuckDB queries for candles, volume, and OI aggregation.
  - JSON repository for user presets (`data/user_study_presets.json`).
