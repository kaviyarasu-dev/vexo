# Requirements Specification: Trade Journal Analytics

## 1. Feature Overview
The Trade Journal Analytics feature upgrades the existing Trade Journal (`#view-journal`) from a simple table and equity curve into an institutional-grade performance and behavioral analytics suite. It introduces:
1. **Interactive Monthly Green/Red P&L Wall Calendar**:
   - Day-by-day visual calendar grid mapping Realized P&L by trade exit date.
   - Distinct green (profitable day), red (loss day), and neutral (no trades) color coding with net ₹ amount and win/loss counts.
   - Weekly row totals (Net P&L, Total Trades).
   - Monthly KPI summary banner (Monthly Net P&L, Win Days / Loss Days, Win Day %, Max Win Streak, Max Loss Streak, Average Win Day vs Average Loss Day).
   - 1-click day cell filter: Clicking any date filters the trade ledger to that specific session.
2. **Quantitative Trade Diagnostics**:
   - **Time-of-Day Analysis**: Segmenting trades into Indian market sessions (09:15-10:30 Morning Opening Momentum, 10:30-13:00 Midday Range, 13:00-15:30 Afternoon Institutional Closing Flow).
   - **Direction Analysis**: Long vs. Short win rate, net P&L, expectancy, and profit factor.
   - **Duration / Holding Period Analysis**: Intraday (same-day entry & exit) vs. Swing / Positional (holding overnight > 1 day).
   - **Instrument Breakdown**: Equity Cash vs. F&O (Futures & Options).
3. **Multi-Broker Tradebook Importers**:
   - Intelligent auto-detection of broker CSV file format by header inspection.
   - Native parsers for:
     - FYERS Tradebook CSV
     - Zerodha Console Tradebook CSV
     - Groww Trade History CSV
   - Robust FIFO matching engine reconstructing executed round-trip trades, deducting charges, and calculating R-multiples.
4. **Tabbed Workspace Architecture**:
   - Seamless subtabs: `📅 P&L Wall Calendar`, `📊 Quantitative Diagnostics`, `📜 Detailed Trade Log`, `🧠 Behavioral Mistake Cloud`.

---

## 2. Detailed Technical Requirements

### 2.1 Backend / Analytical Engine
- **Calendar Aggregation Service**:
  - Filter trades by target `year` and `month`.
  - Group trades by `CAST(exit_time AS DATE)`. If `exit_time` is null, trade is open and excluded from realized calendar P&L.
  - Calculate daily metrics: `date`, `net_pnl`, `gross_pnl`, `total_charges`, `trades_count`, `win_count`, `loss_count`, `profit_factor`.
  - Calculate weekly row summaries (Monday through Friday/Sunday).
  - Calculate month-level metrics:
    - Total monthly net P&L.
    - Win day count & Loss day count.
    - Win day percentage (`win_days / total_trading_days`).
    - Consecutive winning days streak (`max_win_streak`).
    - Consecutive losing days streak (`max_loss_streak`).
    - Average Win Day P&L vs. Average Loss Day P&L ratio.
- **Quantitative Diagnostics Service**:
  - Time-of-Day Bucketing (IST):
    - `morning`: 09:15:00 to 10:29:59 IST
    - `midday`: 10:30:00 to 12:59:59 IST
    - `afternoon`: 13:00:00 to 15:30:00 IST
    - `other`: Outside regular market hours
  - Direction Metrics: `LONG` vs `SHORT` (count, win_rate, total_pnl, avg_r, profit_factor).
  - Duration Metrics: `intraday` (entry date == exit date) vs `swing` (exit date > entry date).
  - Instrument Metrics: `EQUITY` vs `F&O`.
- **Multi-Broker CSV Importer Engine**:
  - `detect_broker_format(csv_text: str) -> str`:
    - Checks for Zerodha Console signature columns: `isin`, `exchange`, `order_execution_time`, `trade_type` / `trade_date`.
    - Checks for Groww signature columns: `stock name`, `type`, `execution date & time` or `order status`.
    - Checks for FYERS signature columns: `symbol`, `trade_date`, `side`, `price`, `quantity`.
    - Throws `ValueError` with clear message if unknown.
  - Resilient FIFO fill matching pairing Buy & Sell fills across symbols.
  - Calculates Indian equity charges per broker rules or standard statutory cost model.
  - Generates unique deterministic or UUID trade IDs.

### 2.2 REST API Endpoints
1. `GET /api/v1/journal/calendar?year=YYYY&month=MM`
   - Response: `{ success: true, year: int, month: int, kpis: { net_pnl, win_days, loss_days, win_rate_days, max_win_streak, max_loss_streak, avg_win_day, avg_loss_day }, days: [...], weeks: [...] }`
2. `GET /api/v1/journal/diagnostics`
   - Response: `{ success: true, time_of_day: [...], direction: [...], duration: [...], instruments: [...] }`
3. `POST /api/v1/journal/import`
   - Form-data: `file: UploadFile`, `broker: Optional[str] = 'AUTO'`
   - Response: `{ success: true, broker_detected: str, imported_trades: int, matched_positions: int }`

### 2.3 Frontend & UI Experience
- Subtab navigation:
  - `btn-journal-tab-calendar` (Active by default)
  - `btn-journal-tab-diagnostics`
  - `btn-journal-tab-trades`
  - `btn-journal-tab-mistakes`
- Monthly Wall Calendar:
  - Header with `◄ Prev`, `Next ►`, Month Title (`October 2026`), and 6 KPI badge cards.
  - 7 Column Grid (Mon, Tue, Wed, Thu, Fri, Sat, Sun) + Weekly Total column.
  - Date cell elements:
    - Date number (e.g. `12`)
    - Day Net P&L (₹) in green (`text-emerald`) or red (`text-rose`).
    - Win / Loss badge (e.g. `2W 1L`).
    - Hover tooltip detailing trade breakdown.
    - Click-to-filter interaction linking directly to `#journal-trades-table`.
- Quantitative Diagnostics Dashboard:
  - 4 visual card modules with proportional horizontal performance bars and KPI metrics.
- Enhanced Import Modal:
  - Displays auto-detected broker badge with green confirmation checkmark.
