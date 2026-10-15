# Requirements Specification: Portfolio / Multi-Stock Basket Backtesting Engine & Studio UI

- **Feature Slug**: `portfolio-basket-backtest`
- **Parent Initiative**: Institutional Quantitative Trader Roadmap (Priority Tier P1)
- **Status**: APPROVED & ALIGNED VIA /GRILL-ME

---

## 1. Executive Summary & Problem Statement
Currently, the Quant Backtest Studio only simulates individual equities one at a time (`config.symbol`). In institutional quantitative trading and realistic retail portfolio management, capital is allocated across a multi-asset universe (e.g. NIFTY 50 or custom watchlists) with cash allocation constraints, max open positions, and capital reallocation upon exit. Single-stock tests ignore cash drag, concurrent position contention, and cross-asset diversification.

This feature introduces a production-ready **Portfolio / Multi-Stock Basket Backtesting Engine** that executes strategies across synchronized chronological bars for multi-asset baskets, managing a shared portfolio cash pool, position sizing models (Equal Weight, Inverse ATR, Fixed ₹), signal ranking policies, and generating true portfolio-level Sharpe, Sortino, Max Drawdown, and CAGR alongside Nifty 50 benchmark comparison.

---

## 2. User Stories & Use Cases

### US-1: Predefined & Custom Basket Selection
As a quant trader, I want to select predefined universes (NIFTY 50, NIFTY NEXT 50, NIFTY MIDCAP 150) or build a custom multi-stock basket so that I can evaluate strategy performance across diversified market segments.

### US-2: Institutional Position Sizing & Max Concurrent Slots
As a risk manager, I want to define maximum concurrent open positions (e.g., max 5 or 10 stocks) and choose between Equal Weight (1/N or % capital), Volatility-Adjusted (Inverse ATR), or Fixed Amount per position so that capital is allocated realistically without margin breaches.

### US-3: Signal Contention & Ranking Policy
As an algorithmic trader, when 8 stocks trigger BUY signals simultaneously on the same bar but only 3 open slots remain, I want the portfolio engine to prioritize candidates based on signal strength (e.g., Lowest RSI for mean-reversion, Highest ROC for trend-following, or Highest Volume Expansion) so that the best opportunities are funded.

### US-4: Portfolio Equity Curve & Benchmark Alpha
As an investment analyst, I want to view the consolidated Portfolio Equity Curve plotted alongside the NIFTY 50 Benchmark Buy & Hold curve, accompanied by portfolio-level metrics (CAGR, Sharpe, Sortino, Max Drawdown, Exposure/Cash Drag %).

### US-5: Asset Contribution & Combined Trades Ledger
As a portfolio manager, I want to inspect which individual stocks generated the alpha vs. which dragged down returns (Win Rate, Net P&L ₹, Trades Count per symbol) and browse a consolidated chronologically sorted round-trip trade ledger with Indian statutory costs deducted.

---

## 3. Scope & Boundaries

### In Scope:
1. `PortfolioEngine` and `PortfolioBroker` running multi-asset bar synchronization.
2. Sizing models:
   - `EQUAL_WEIGHT`: `(cash / remaining_slots)` or `initial_capital * (weight_pct / 100)`.
   - `INVERSE_ATR`: Sizing inversely proportional to 14-period ATR volatility.
   - `FIXED_AMOUNT`: Strict fixed rupee allocation per slot (e.g. ₹1,00,000).
3. Signal Contention Resolver: Ranking candidates by indicator value / momentum on trigger date.
4. Statutory realism: `IndianEquityCostModel` applied to every buy and sell leg across all basket assets.
5. Endpoints:
   - `POST /api/v1/backtest/portfolio/run`: Executes portfolio basket simulation.
   - `GET /api/v1/backtest/portfolio/universes`: Retrieves available predefined universes and constituents.
6. Frontend Backtest Studio:
   - Dual Mode Switcher: `Single Asset` $\longleftrightarrow$ `Portfolio Basket`.
   - Universe selector dropdown with chip tags.
   - Portfolio Sizing controls (Max Positions, Sizing Model, Ranking Metric).
   - Portfolio Results: Consolidated Equity Curve vs. Nifty 50 Benchmark, Asset Contribution Table, Monthly Returns Matrix, Combined Trade Ledger.

### Out of Scope (Future Phases):
- Dynamic intraday tick-level order book depth simulation (EOD and resampled 5m/15m/1h/1D supported).
- Live broker auto-routing (SEBI compliance requires simulated paper execution).

---

## 4. Technical & Architectural Constraints
- **DuckDB Read Concurrency**: Fetching historical candle data for 50 stocks must execute using `db.get_read_cursor()` in batch or vectorized parallel queries without locking the writer process.
- **Strict IST Alignment**: All dates and resampling must respect Indian Standard Time (UTC+5:30).
- **Zero Lookahead Bias**: Orders must fill on next bar's OPEN price with slippage.
- **Fast Execution**: Full 50-stock EOD 4-year backtest must execute in $< 2.5$ seconds using pandas/numpy vectorized indicator computation.
