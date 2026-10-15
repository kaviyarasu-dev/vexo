# Feature Requirements: Strategy Parameter Optimization 2D Heatmap & Walk-Forward Validation

- **Feature Slug**: `strategy-parameter-optimization`
- **Feature Name**: Strategy Parameter Optimization 2D Heatmap & Walk-Forward Validation
- **Target Initiative**: Institutional Quantitative Trader Roadmap (Priority Tier P2)
- **Target Workspaces**: Backtest Studio (`#view-backtest`), Backend Engine (`services/backtest/`), REST API (`api/routers/backtest.py`)

---

## 1. Executive Summary & Quant Motivation
In quantitative algorithmic trading, a single backtest with arbitrarily chosen parameters (e.g., SMA 20/50 or RSI 14 with 30/70) provides zero information about parameter robustness, sensitivity, or overfitting. 
Retail traders frequently suffer from **curve-fitting traps**—finding an isolated parameter spike that generated abnormal historical returns purely due to noise, only to experience severe capital drawdown when traded live.

This feature introduces an institutional-grade **Strategy Parameter Optimization 2D Heatmap & Walk-Forward Validation Engine**:
1. **Cartesian Grid Search Runner**: Rapidly evaluates combinations of 2 strategy parameters (e.g. Fast Period $\times$ Slow Period, or RSI Period $\times$ Oversold Threshold) over pre-loaded historical DuckDB OHLCV data.
2. **2D Interactive Heatmap Matrix**: Renders a color-coded grid where cell colors represent Sharpe Ratio, Net Realized P&L (₹), Max Drawdown %, or Win Rate %.
3. **Plateau Stability Score & Cliff Detection**: Analyzes the 3x3 neighborhood around the optimal cell to identify whether the peak is a robust plateau or a dangerous, overfit cliff edge.
4. **Walk-Forward In-Sample vs. Out-of-Sample (OOS) Analysis**: Splits historical data into In-Sample (e.g. 70%) for optimization and Out-of-Sample (e.g. 30%) for unseen validation, computing Walk-Forward Efficiency ($WFE$).
5. **1-Click Optimal Parameter Deployment**: Allows traders to apply optimal parameters directly into single-stock or portfolio backtests with a single click.

---

## 2. Granular Requirements Specification

### 2.1 Grid Search Engine & Mathematical Logic (`services/backtest/optimization_engine.py`)
- **Data Ingestion**: Loads OHLCV candles once from DuckDB via `BacktestService.load_candles` or read cursor to eliminate repeated disk I/O.
- **Data Splitting (Walk-Forward Splitter)**:
  - Supports configurable percentage split (default 70% In-Sample / 30% Out-of-Sample) or explicit start/end dates.
  - Ensures strictly zero lookahead bias by splitting along continuous calendar timestamps.
- **Cartesian Parameter Product**:
  - Accepts Parameter 1 range: `name`, `min`, `max`, `step`.
  - Accepts Parameter 2 range: `name`, `min`, `max`, `step`.
  - Validates total combinations (capped at 400 iterations per grid, e.g. $20 \times 20$, to ensure execution stays under 2-3 seconds).
- **Execution Engine**:
  - Uses fast vectorized indicator re-computation and in-memory execution loop.
  - Runs with concurrent thread pool (`concurrent.futures.ThreadPoolExecutor`) across combinations.
- **Metrics Computation per Cell**:
  - `param1_val`, `param2_val`
  - `sharpe_ratio`: Annualized Sharpe ratio ($(\text{mean daily return} / \text{stdev daily return}) \times \sqrt{252}$).
  - `net_pnl`: Net Realized P&L in ₹ after Indian statutory levies and slippage.
  - `net_pnl_pct`: Percentage return on initial capital.
  - `max_drawdown_pct`: Peak-to-trough equity drawdown percentage.
  - `win_rate`: Percentage of profitable closed trades.
  - `total_trades`: Number of round-trip executions.
  - `profit_factor`: Gross Profits / Gross Losses.

### 2.2 Stability Index & Walk-Forward Mathematics
- **3x3 Plateau Stability Index ($PSI$)**:
  - For the optimal cell $(x^*, y^*)$, inspects the 8 immediate adjacent neighbor cells $(x^* \pm 1, y^* \pm 1)$.
  - Computes the average relative metric retention:
    $$PSI = \frac{1}{|N|} \sum_{(i,j) \in N} \max\left(0, \frac{M_{i,j}}{M_{x^*, y^*}}\right)$$
  - Classification:
    - $PSI \ge 0.75$: `ROBUST_PLATEAU` (Green Badge)
    - $0.50 \le PSI < 0.75$: `MODERATE_SENSITIVITY` (Amber Badge)
    - $PSI < 0.50$: `FRAGILE_CLIFF` (Red Overfitting Warning)
- **Walk-Forward Efficiency ($WFE$)**:
  $$WFE = \frac{\text{Annualized Return}_{\text{OOS}}}{\text{Annualized Return}_{\text{IS}}}$$
  - $WFE \ge 0.50$: Passed Walk-Forward Validation.
  - $WFE < 0.50$: Warning for Alpha Decay in unseen market conditions.

### 2.3 REST API Layer (`api/routers/backtest.py`)
- `POST /api/v1/backtest/optimize`:
  - Request: `strategy`, `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`, `slippage_bps`, `param1_spec`, `param2_spec`, `walk_forward_split_pct`.
  - Response:
    - `best_params`: Optimal parameter set.
    - `stability_score`: $PSI$ score, classification, and neighbor summary.
    - `walk_forward`: In-Sample metrics, Out-of-Sample metrics, and $WFE$.
    - `matrix`: 2D list of evaluation cells for heatmap rendering.
    - `param1_ticks`: X-axis tick values.
    - `param2_ticks`: Y-axis tick values.
- `GET /api/v1/backtest/optimize/presets`:
  - Returns recommended parameter search ranges for built-in strategies (`SMA_CROSS`, `RSI_REVERSION`, `BOLLINGER_BANDS`, `SUPERTREND`, `MACD`).

### 2.4 Frontend UX & 2D Heatmap (`static/js/backtest_optimization_ui.js`)
- Dedicated subtab `#btn-backtest-tab-optimize` in `#view-backtest` alongside Single-Stock and Portfolio Basket backtesting.
- Parameter range definition controls (dropdown for Param 1 and Param 2 with min/max/step inputs).
- Walk-Forward Split slider (50% to 90% IS) with real-time calendar date preview.
- Interactive 2D Heatmap SVG:
  - Metric switcher buttons: `Sharpe Ratio`, `Net P&L (₹)`, `Max Drawdown %`, `Win Rate %`.
  - High-fidelity gradient color scale (Emerald Green for high, Slate Neutral, Rose Red for low).
  - Hover tooltips showing exact cell parameters, trades, and returns.
  - Click on cell to select parameters.
- Stability & Walk-Forward HUD:
  - 3x3 Plateau Stability badge (`ROBUST_PLATEAU` / `FRAGILE_CLIFF`).
  - Side-by-side comparison card: In-Sample vs. Out-of-Sample KPI table ($WFE$ indicator).
- 1-Click Action:
  - `⚡ Apply Optimal Parameters to Backtest`: Injects the best discovered parameters directly into Backtest Studio and triggers single-stock backtest verification.

---

## 3. Plan Architecture Breakdown
- **Plan 01-001**: Grid Search Engine, Plateau Stability Index (3x3 Neighborhood) & Walk-Forward Splitter (`01-engine-and-stability/001-engine-and-stability.md`)
- **Plan 02-001**: FastAPI Optimization Router, Strategy Ranges & Pydantic Contracts (`02-api-and-presets/001-api-and-presets.md`)
- **Plan 03-001**: Optimization Studio UI: 2D Heatmap Grid, Metric Switcher & Walk-Forward HUD (`03-heatmap-ui-and-walkforward/001-heatmap-ui-and-walkforward.md`)
