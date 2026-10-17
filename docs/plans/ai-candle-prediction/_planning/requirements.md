# Requirements & Architecture Specification: AI Candle Prediction & Quantitative Engine Upgrade

**Feature Slug:** `ai-candle-prediction`  
**Target Platform:** NSE Quant Platform (`d:\trading-app`)  
**Status:** In Progress (Phase: Interview)  

---

## Code findings

1. **Backtesting Double-Slippage Bug (`services/backtest/engine.py:L59-L64`, `services/backtest/cost_model.py:L40-L51`):**
   - In `engine.py`, execution fill prices are already adjusted for slippage: `fill_price = open_price * (1 + slippage_factor)` on BUY, and `open_price * (1 - slippage_factor)` on SELL.
   - Concurrently, `cost_model.py` computes `slippage = turnover * (self.slippage_bps / 10000.0)` and appends it to `total_taxes_and_fees`.
   - `engine.py` deducts `total_fee` from cash: `self.cash -= (trade_val + total_fee)`.
   - Result: Every single backtest trade is penalized twice for slippage, severely depressing net P&L and risk-adjusted metrics.
   - Fix: Remove slippage from `CostResult.total_taxes_and_fees` in `cost_model.py` so it is applied strictly through price execution variance.

2. **Corporate Actions Cartesian Join Duplication (`db/migrations.py:L260-L261`, `L274-L275`):**
   - The view definition executes:
     `LEFT JOIN adjustment_factors af ON c.symbol = af.symbol AND c.date <= af.ex_date;`
   - If a stock underwent $k$ splits/bonuses (e.g. INFY, RELIANCE), any date prior to the first action matches all $k$ records.
   - Result: Historical candle rows are duplicated $k$ times in `candles_1d_adjusted` and `candles_1m_adjusted`, multiplying data volume and using uncombined partial factors instead of the cumulative product $\prod_{i} r_i$.
   - Fix: Store precomputed cumulative adjustment factors $A_t$ with contiguous validity ranges $[D_i, D_{i+1})$, ensuring a strictly unique $1:1$ join.

3. **Options Greeks Time Scaling & Dividend Yield (`services/options/greeks_engine.py:L37`, `L58`):**
   - Annualized time uses calendar days: `T = t_days / 365.0`.
   - Daily Theta conversion divides by trading days: `theta = theta / 250.0`.
   - Continuous dividend yield $q$ is absent ($q = 0$), causing systematic pricing bias on high-dividend NSE stocks (e.g., ITC, COALINDIA, VEDL).
   - Fix: Unify time scale convention consistently to trading days ($250$) or calendar days ($365$), and add continuous dividend yield parameter $q$.

4. **Hardcoded Pattern Recognition Accuracy (`services/pattern_recognition_service.py:L29-L95`):**
   - Static percentages (`"accuracy": 63.8`, `62.4`, `67.5`) are hardcoded for 12 candlestick patterns across all symbols and timeframes.
   - Fix: Implement dynamic Bayesian empirical win rates ($P(\text{Target Hit} \mid \text{Pattern}, \text{Symbol}, \text{Timeframe}, \text{Regime})$) calculated directly against DuckDB historical records.

5. **Python ML Environment Dependencies (`.venv`):**
   - `lightgbm`, `scikit-learn`, `scipy`, `statsmodels`, `hmmlearn`, and `arch` are currently NOT installed in the virtual environment.
   - Fix: Explicitly specify lightweight dependencies (`lightgbm`, `scikit-learn`, `scipy`, `statsmodels`) in `requirements.txt` and install in `.venv`.

6. **Frontend Visualizer Infrastructure (`static/`):**
   - Uses TradingView Lightweight Charts v4.2.1.
   - Custom HTML5 Canvas overlays exist for Volume Profile (`static/js/volume_profile_overlay.js`) and Drawings (`static/js/chart_drawings.js`).
   - Adding a forward-projected prediction ribbon and header HUD follows the existing canvas overlay and dock patterns.

---

## Decisions

- **D1 (from User Interview):** Priority sequencing starts with Foundation First: fix core calculation bugs (Double-Slippage, Cartesian Join in Corporate Actions, and BSM Theta scaling), followed immediately by the Probabilistic Next-Candle Prediction Engine.
- **D2 (from User Interview):** Model architecture selected is **LightGBM Quantile Gradient Boosting** for sub-10ms CPU inference in FastAPI, eliminating heavy GPU dependencies.
- **D3 (from User Interview):** UI visualization selected is **Dual**: Forward-projected shaded probability corridor on the Lightweight Charts canvas + a real-time Predictive HUD badge in the chart header.
- **D7 (from User Interview):** Size confirmed as **L (Large)**. The feature will be partitioned into 5 standalone plan parts following the File Splitting Rule.
- **D8 (from User Interview):** Hybrid model storage & training lifecycle: pre-trained benchmark models for NIFTY50 and BANKNIFTY stored in `data/models/`, combined with an on-demand DuckDB background training endpoint capable of training any active symbol in $< 3$ seconds.
- **D9 (from User Interview):** Multi-timeframe prediction: dynamic synchronization with active chart view, predicting next-candle envelopes for Intraday `5m`, `15m`, and Daily `1D`.
- **D10 (from User Interview):** Graceful degraded fallback: for symbols with $< 200$ historical bars, HUD displays `Status: Insufficient Data (< 200 bars)` and renders classical ATR volatility corridors instead of throwing errors.
- **D11 (from User Interview):** Machine verification is structured as dedicated pytest suites per plan part (`tests/test_core_engine_fixes.py`, `tests/test_ai_features.py`, `tests/test_ai_models.py`, `tests/test_dsr.py`) plus syntax/import assertions for frontend JavaScript files.
- **D12 (from User Interview):** DSR overfitting reporting displays a prominent Amber Overfitting Alert banner in Backtest Lab with both raw Sharpe, Deflated Sharpe, and asymptotic $p$-value, prioritizing trader education and transparency.
- **D4 (Decided from Code):** DuckDB single-writer concurrency must be respected (`workers=1`). ML batch feature extraction will use lockless read cursors (`db.get_read_cursor()`) to ensure zero contention with UI charting.
- **D5 (Decided from Code):** All REST responses will adhere strictly to the standardized envelope `ApiResponse[T]` (`{status, data, message, correlation_id, execution_time_ms}`) via `api.models.envelope`.
- **D6 (Decided from Code):** SEBI statutory compliance dictates that live automated order execution remains permanently disabled (`HTTP 403 Forbidden`). All predictive signals remain analytical / paper trading only.

---

## Assumptions

- **A1:** Historical 1-minute and 1-day candles in DuckDB (`candles_1d_raw`, `candles_1m_raw`) have sufficient history for training (at least 2,000 bars per asset).
- **A2:** Default quantile levels for the next-candle envelope are $Q_{0.10}$ (lower bound), $Q_{0.50}$ (median expectation), and $Q_{0.90}$ (upper bound), providing an $80\%$ empirical prediction corridor.
- **A3:** Target asset coverage for initial pre-trained models focuses on NSE liquid benchmarks: `NSE:NIFTY50-INDEX`, `NSE:BANKNIFTY-INDEX`, and high-turnover equities (`NSE:RELIANCE-EQ`, `NSE:TCS-EQ`, `NSE:HDFCBANK-EQ`), with on-the-fly local fine-tuning for any searched symbol.

---

## Out of scope

- Direct tick-by-tick Level 3 order book matching (Fyers API provides OHLCV aggregates, not full L3 depth).
- Deep neural networks requiring dedicated CUDA/GPU infrastructure (e.g. PyTorch TFT/LSTMs).
- Live broker automated order routing (explicitly restricted by SEBI regulatory order gate).

---

## Open questions

- (None currently open prior to interview questions).

---

## N/A Areas (Skipped with Justification)

- **Users and Roles:** N/A: The platform is a local-first single-user workstation without multi-tenant authentication or role-based access control.
- **Admin Panel:** N/A: Administrative management is handled via local CLI tools and internal system routes (`/api/v1/system/...`).
- **Cloud Infrastructure & Deployments:** N/A: Architecture is local-first (`localhost:8000`), operating on local DuckDB storage.
