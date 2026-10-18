# NSE Quant Platform — AI Predictive Roadmap, Forensic Audit & Pending Engineering Master Plan

**Document Version:** 1.0.0-PROD  
**Author:** Principal Financial AI Engineer & Senior Quantitative Researcher  
**Classification:** Local-First Institutional Quantitative Research & Financial Machine Learning  
**Target Repository:** `d:\trading-app`  
**Market Universe:** National Stock Exchange of India (NSE Equities & Equity F&O)  

---

## Table of Contents
1. [Executive Summary & System Philosophy](#1-executive-summary--system-philosophy)
2. [Current Architecture & Master Inventory of Implemented Features](#2-current-architecture--master-inventory-of-implemented-features)
3. [Deep Forensic Audit: Codebase Defects & Mathematical Flaws](#3-deep-forensic-audit-codebase-defects--mathematical-flaws)
4. [The Quantitative Science of "Candle Prediction": Retail Fallacies vs. Institutional Reality](#4-the-quantitative-science-of-candle-prediction-retail-fallacies-vs-institutional-reality)
5. [Master Blueprint: Proposed AI Predictive Feature Suite](#5-master-blueprint-proposed-ai-predictive-feature-suite)
6. [Mathematical Formulations & Feature Engineering Specifications](#6-mathematical-formulations--feature-engineering-specifications)
7. [Comprehensive Pending Items & Technical Debt Catalog](#7-comprehensive-pending-items--technical-debt-catalog)
8. [Five-Phase Execution Roadmap & Verification Milestones](#8-five-phase-execution-roadmap--verification-milestones)
9. [Bilingual Tamil Operations Summary (தமிழ் சுருக்கம்)](#9-bilingual-tamil-operations-summary)
10. [Statutory SEBI Regulatory Compliance Notice](#10-statutory-sebi-regulatory-compliance-notice)

---

## 1. Executive Summary & System Philosophy

The **NSE Quant Platform** is engineered from first principles as an institutional-grade, local-first quantitative research and analytical workstation specifically tailored for the National Stock Exchange of India (NSE). 

Operating with a high-performance **DuckDB OLAP engine**, an asynchronous **FastAPI backend (single-writer model)**, and **TradingView Lightweight Charts (v4.2.1)** with custom HTML5 Canvas overlays, the platform provides zero-latency analytical capabilities on over 15 years of daily data and 5 years of 1-minute intraday tick aggregates across 2,581 NSE equities.

### Strategic Objective of this Master Plan
This document establishes an authoritative, source-backed forensic audit of the existing codebase, resolves critical calculation flaws (such as double-slippage deduction and Cartesian product view joins), establishes the mathematical rigor required to predict candlestick dynamics, and details the pending technical backlog required to transition the platform into an AI-augmented quantitative trading environment.

---

## 2. Current Architecture & Master Inventory of Implemented Features

The platform currently comprises 17 canonical DuckDB tables, 2 split-adjusted dynamic SQL views, 18 REST router suites, and 30 modular frontend visualizers.

```
+-----------------------------------------------------------------------------------------------+
|                                      FRONTEND WORKSTATION                                     |
|    TradingView Lightweight Charts (v4.2.1) | HTML5 Canvas Overlays | Vanilla JavaScript (ES6) |
+-----------------------------------------------------------------------------------------------+
                                               |  HTTP / SSE / REST (Port 8000)
                                               v
+-----------------------------------------------------------------------------------------------+
|                                    FASTAPI CORE CONTROLLER                                    |
|   Workers=1 (DuckDB Writer Safety) | RedactingFormatter Logging | Correlation ID Tracking    |
|   Statutory 403 Order Execution Gate | RateGovernor Multi-Lane Token Bucket (180 req/min)     |
+-----------------------------------------------------------------------------------------------+
         |                              |                                |
         v                              v                                v
+--------------------+        +--------------------+           +--------------------+
| API ROUTERS (18)   |        | SERVICES LAYER     |           | SECURITY & VAULT   |
| - /candles         |        | - Resampling       |           | - OS Keyring API   |
| - /symbols         |        | - Greeks (BSM)     |           | - AES-256 .vault   |
| - /screener        |        | - Backtesting      |           | - 24h Access Token |
| - /options         |        | - Ingestion (JIT)  |           | - 15d Refresh Token|
| - /backtest        |        | - Downloader       |           +--------------------+
| - /journal         |        | - Paper Trading    |
| - /alerts          |        | - Patterns & VP    |
+--------------------+        +--------------------+
         |                              |
         +--------------------+         |
                              v         v
+-----------------------------------------------------------------------------------------------+
|                                    DUCKDB OLAP DATA ENGINE                                    |
| - Storage File: data/db/nse_quant.duckdb                                                      |
| - Concurrency: Single Writer Process, Lockless Independent Readers (conn.cursor())           |
| - Tables (17): symbols, candles_1m_raw, candles_1d_raw, corporate_actions, adjustment_factors,|
|   download_checkpoints, market_holidays, job_logs, journal_entries, paper_account,             |
|   paper_positions, paper_orders, paper_trades, paper_auto_strategies, chart_drawings,         |
|   option_chain_snapshots, schema_version                                                      |
| - Dynamic Views: candles_1d_adjusted, candles_1m_adjusted                                     |
+-----------------------------------------------------------------------------------------------+
```

### 2.1 Implemented Subsystems Matrix
- **Interactive Multi-Timeframe Charting:** Dynamic vectorized resampling (`1m`, `3m`, `5m`, `15m`, `1h`, `1D`, `1W`), cursor-based infinite history lazy loading, and multi-indicator overlays (VWAP, EMA, SMA, Bollinger Bands, Supertrend, RSI, MACD, ATR).
- **Chart Drawing Annotations:** Trendlines, Horizontal Rays, Fibonacci Retracements, Supply/Demand Zones, Measure Tools, persistently stored in DuckDB `chart_drawings`.
- **In-Database High-Speed Screener:** Sub-50ms execution on `candles_1d_adjusted` for Volume Spikes (Z-Score $> 2.0$), 52-Week High proximity, RSI oversold/overbought thresholds, and index basket filtering (NIFTY 50, NIFTY NEXT 50, NIFTY 500).
- **Options Analytics & Greeks Matrix:** Interactive Option Chain with Open Interest (OI) depth bars, closed-form Black-Scholes Greeks ($\Delta, \Gamma, \Theta, \mathcal{V}$), Put-Call Ratio (PCR Total & $\Delta$OI), Max Pain calculation, and multi-leg P&L payoff simulation.
- **Quantitative Backtesting Lab:** Single-symbol and multi-stock portfolio simulator with statutory Indian transaction taxes (STT, GST, Exchange turnover, SEBI turnover, Stamp Duty), parameter grid search optimizer, and 1,000-run Monte Carlo bootstrap robustness validation.
- **Paper Trading Environment:** Realistic virtual broker with ₹10,00,000 capital, market/limit/stop-loss order simulation, on-chart trade execution dock, and automated strategy deployment bridge.
- **Trade Journal & Behavioral Analytics:** 1-click Fyers `tradebook.csv` import, P&L calendar heatmap, R-multiple statistical distributions, and emotional mistake tagging (`FOMO`, `Revenge`, `Chasing`) with rupee loss attribution.
- **Real-Time Alert Engine:** Rule-based threshold alerts with NSE Quiet Hours (09:15–15:30 IST) auto-suppression and cooldown deduplication.
- **Dual Persona UX:** Seamless switching between Simple Mode (plain-language financial labels and 3-part pedagogical context micro-cards: Definition, Analogy, Risk) and Pro Mode.

---

## 3. Deep Forensic Audit: Codebase Defects & Mathematical Flaws

A meticulous audit of the active source files revealed four foundational defects requiring immediate remediation:

| Subsystem / Component | Exact Code Location | Verified Flaw / Code Snippet | Mathematical & Financial Impact | Required Quantitative Fix |
| :--- | :--- | :--- | :--- | :--- |
| **Backtest Engine Execution** | [`services/backtest/engine.py:L59-L64`](file:///d:/trading-app/services/backtest/engine.py#L59-L64)<br>[`services/backtest/cost_model.py:L40-L51`](file:///d:/trading-app/services/backtest/cost_model.py#L40-L51) | **Double-Slippage Deduction:**<br>In `engine.py`, execution prices are penalized by slippage:<br>`fill_price = open_price * (1 + slippage_factor)`.<br>Then in `cost_model.py`, slippage is computed as turnover cash and added to `total_taxes_and_fees`:<br>`slippage = turnover * (self.slippage_bps / 10000.0)`<br>`total = ... + slippage`.<br>This cash fee is deducted again via `self.cash -= (trade_val + total_fee)`. | Every backtested trade is penalized **twice** for slippage (once in execution price, and once in cash balance fees). Strategy returns, Sharpe ratios, and profit factors are artificially depressed. | Remove `slippage` from `CostResult.total_taxes_and_fees` in [`cost_model.py`](file:///d:/trading-app/services/backtest/cost_model.py). Slippage is an execution price variance, not a cash statutory fee. |
| **Corporate Actions Views** | [`db/migrations.py:L260-L261`](file:///d:/trading-app/db/migrations.py#L260-L261)<br>[`db/migrations.py:L274-L275`](file:///d:/trading-app/db/migrations.py#L274-L275) | **Cartesian Join Duplication:**<br>`LEFT JOIN adjustment_factors af ON c.symbol = af.symbol AND c.date <= af.ex_date;`<br>When a stock undergoes multiple corporate actions ($D_1 < D_2 < D_3$), any historical candle dated before $D_1$ satisfies `c.date <= af.ex_date` for all $k$ rows in `adjustment_factors`. | DuckDB returns $k$ duplicated rows for every single date prior to corporate actions. Backtests, charting queries, and screener scans operate on corrupted, multiplied data with incorrect individual factors instead of the cumulative product $\prod_{i} r_i$. | Re-architect the adjustment factor pipeline to store precomputed cumulative factors $A_t$ with non-overlapping date validity intervals $[D_i, D_{i+1})$, guaranteeing a strictly unique $1:1$ join. |
| **Black-Scholes Options Greeks** | [`services/options/greeks_engine.py:L37-L58`](file:///d:/trading-app/services/options/greeks_engine.py#L37-L58) | **Time Scale Inconsistency & Zero Dividend:**<br>Annualized expiration is computed as $T = t_{\text{days}} / 365.0$ (calendar days), but daily Theta decay is converted via `theta = theta / 250.0` (trading days). Furthermore, continuous dividend yield $q$ is omitted ($q = 0$). | Produces a **~46% scale distortion** in calculated daily Theta. Omitting dividend yield introduces systematic mispricing on high-dividend NSE underlyings (e.g., ITC, COALINDIA, VEDL), inflating Call Greeks and underpricing Put Greeks. | Standardize time scale convention: use trading days ($T = t / 250.0$) or calendar days ($T = t / 365.0$) consistently throughout. Add continuous dividend yield $q$ into the generalized Black-Scholes-Merton model equations. |
| **Candlestick Pattern Engine** | [`services/pattern_recognition_service.py:L29-L95`](file:///d:/trading-app/services/pattern_recognition_service.py#L29-L95) | **Static Hardcoded Accuracy:**<br>The pattern metadata dictionary specifies static accuracy numbers (e.g. `"accuracy": 63.8` for Bullish Engulfing, `67.5` for Morning Star) regardless of stock, timeframe, or market regime. | Users are misled by artificial statistical confidence. In reality, a Hammer pattern on Nifty 5-minute data possesses a completely different empirical win rate than on a small-cap daily chart. | Replace static numbers with **Dynamic Empirical Bayesian Accuracy**: dynamically calculate win rates ($P(\text{Target Hit} \mid \text{Pattern}, \text{Symbol}, \text{Timeframe}, \text{Regime})$) directly from historical DuckDB records. |

---

## 4. The Quantitative Science of "Candle Prediction": Retail Fallacies vs. Institutional Reality

A common aspiration among retail traders is using Artificial Intelligence to "predict whether the next candle will be green or red" or "predict the exact close price". In quantitative finance, market microstructure, and statistical arbitrage, this approach is fundamentally flawed.

| Dimension | Retail "AI Indicator" Fallacy | Institutional Quantitative Reality | Why the Retail Approach Fails | Mathematical Formulation |
| :--- | :--- | :--- | :--- | :--- |
| **Target Variable ($Y_{t+1}$)** | Predict exact next close $\hat{P}_{t+1}$ or binary candle color (Green/Red). | Predict the **Quantile Distribution of the Next Candle Range** ($Q_{0.10}(L_{t+1}), Q_{0.90}(H_{t+1})$) and **Directional Return Probability**. | Financial prices are non-stationary martingales with low signal-to-noise ratio ($\text{SNR} < 0.05$). Point prediction models minimize mean squared error by simply outputting the current price ($\hat{P}_{t+1} \approx P_t$), creating a useless lagging indicator. | **Quantile Pinball Loss:**<br>$\mathcal{L}_q(y, \hat{y}) = \max\left(q(y - \hat{y}), (1-q)(\hat{y} - y)\right)$<br>Calibrates prediction intervals with formal coverage guarantees. |
| **Input Features ($\mathbf{X}_t$)** | Raw OHLCV prices, lagging simple moving averages (SMA 20/50), standard RSI. | **Stationary Engineered Signals:**<br>Log returns, Fractional Differentiation ($d \approx 0.35$), Garman-Klass Volatility, Signed Volume Delta, VWAP Z-scores. | Raw prices have infinite memory and non-constant variance; ML algorithms overfit to specific price levels rather than universal market dynamics. | **Fractional Differentiation:**<br>$(1 - B)^d = \sum_{k=0}^{\infty} (-1)^k \binom{d}{k} B^k$<br>Eliminates unit roots (ADF test $p < 0.01$) while retaining $90\%+$ correlation with original price series. |
| **Model Architecture** | Overparameterized deep neural networks (Vanilla LSTM, Bi-LSTM, CNN-1D) trained on raw price sequences. | **LightGBM Quantile Gradient Boosted Decision Trees** + **Gaussian Hidden Markov Models (HMM)**. | Tabular financial data lacks the spatial/sequential inductive bias required by deep networks; LSTMs overfit noise, require GPU runtimes, and add unacceptable latency ($>300$ms). | Decision trees natively partition heterogeneous, non-linear tabular features with **sub-10ms CPU inference latency**. |
| **Market Regimes** | Assumes identical market physics across all trading sessions. | Dynamic **Regime-Conditioned Models**: State 0 (Low-Vol Bullish Trend), State 1 (High-Vol Trend), State 2 (Mean-Reverting Choppy). | Trend-following patterns that generate alpha in trending regimes consistently fail in high-volatility choppy markets. | **3-State Gaussian HMM:**<br>$P(S_{t+1} = j \mid S_t = i) = A_{ij}$<br>Filters trading signals based on active latent regime state $S_t$. |
| **Validation Methodology** | Standard Train/Test split or standard $K$-Fold cross validation. | **Purged & Embargoed Combinatorial Walk-Forward CV** + **Deflated Sharpe Ratio (DSR)**. | Standard cross-validation causes massive data leakage due to serial correlation and overlapping event labels. | **Deflated Sharpe Ratio:**<br>$\text{DSR} = \Phi\left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\text{SR}} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{\text{SR}}^2}} \right)$<br>Controls for selection bias under multiple testing. |

---

## 5. Master Blueprint: Proposed AI Predictive Feature Suite

To genuinely assist traders in forecasting candlestick behavior, the platform will implement a five-component quantitative AI suite:

| Feature Name | How it Forecasts "The Next Candle" | Underlying Quantitative Models | Feature Inputs (Engineered from DuckDB) | UI Integration & Visualizer | Performance Specs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Conformal Next-Candle Range Corridor** | Projects the statistically calibrated **High, Low, and Close envelope** for the upcoming bar before it completes. | **LightGBM Quantile Gradient Boosting** ($q = 0.10, 0.50, 0.90$) with Split Conformal Calibration. | Garman-Klass Volatility, Normalized ATR, Parkinson Volatility, Fractional Difference of Close, Candle Wick Ratios, Volume Z-Score. | Shaded forward-projected probability ribbon on TradingView Lightweight Charts + dashed expected High/Low boundary lines. | Inference time: $< 8\text{ms}$ on CPU.<br>Coverage: Guaranteed $80\%$ empirical prediction interval. |
| **2. Directional Conviction Probability Engine** | Computes the exact calibrated probability ($0\%$ to $100\%$) that the next candle will close bullish ($C_{t+1} > O_{t+1}$). | **Calibrated LightGBM Classifier** (isotonic regression calibration) + Binary Cross-Entropy Loss. | Relative Volume (RVOL), VWAP Z-score distance, Signed Volume Delta, Multi-Timeframe Trend Confluence (5m vs 15m vs 1h). | Predictive HUD Badge on Chart Header: `Direction: Bullish (68.4% Confidence)` with dynamic green/red glow. | Log-loss: $< 0.65$.<br>Calibrated Brier score: $< 0.21$. |
| **3. Latent Market Regime Detector (HMM)** | Identifies whether the current candle is forming in a **Trend** or **Choppy Range**, preventing fakeout predictions. | **3-State Gaussian Hidden Markov Model (HMM)** with Expectation-Maximization (Baum-Welch). | Rolling 20-bar Log Returns, Realized Variance, Parkinson High-Low Volatility, Traded Volume Intensity. | Real-time Regime Tag on Chart HUD: `Regime: Bullish Trend (State 0)` or `Regime: Mean Reversion / Choppy (State 2)`. | Online Viterbi path decoding in $< 2\text{ms}$. Updates on each bar completion. |
| **4. Volatility Expansion Squeeze Predictor** | Detects pre-breakout compression and forecasts whether the next candle will experience an **explosive range expansion**. | **GARCH(1,1) Conditional Volatility** + Bollinger/Keltner Bandwidth Squeeze Ratio. | Close-to-Close returns, Normalized Average True Range (NATR), High-Low ratio, Intraday Volume Clustering. | On-chart volatility dots: Gold/Cyan dots indicating imminent volatility expansion breakout. | Early warning signal triggered 1–2 bars prior to explosive multi-sigma expansion. |
| **5. Dynamic Bayesian Candlestick Edge Evaluator** | Replaces hardcoded pattern win-rates with live empirical edge calculated for the active stock and regime. | **Bayesian Updating with Beta Prior:**<br>$\text{Beta}(\alpha_0 + k, \beta_0 + n - k)$. | Historical occurrences of the detected pattern in DuckDB filtered by symbol, timeframe, and HMM regime. | Tooltip on pattern marker: displays empirical win-rate, sample size ($n=342$), and expected value (EV) in rupees. | Dynamic calculation executed directly in DuckDB OLAP engine in $< 15\text{ms}$. |

---

## 6. Mathematical Formulations & Feature Engineering Specifications

### 6.1 Conformal Quantile Range Prediction
To predict the next candle's boundaries, two quantile models are trained for the upper bound ($H_{t+1}$) and lower bound ($L_{t+1}$):
$$\hat{H}_{t+1}^{(0.90)} = \arg\min_{\hat{y}} \mathbb{E}\left[ \mathcal{L}_{0.90}(H_{t+1}, \hat{y}) \mid \mathbf{X}_t \right]$$
$$\hat{L}_{t+1}^{(0.10)} = \arg\min_{\hat{y}} \mathbb{E}\left[ \mathcal{L}_{0.10}(L_{t+1}, \hat{y}) \mid \mathbf{X}_t \right]$$
where the pinball loss $\mathcal{L}_q$ is defined as:
$$\mathcal{L}_q(y, \hat{y}) = (y - \hat{y}) \cdot \left( q - \mathbb{I}(y < \hat{y}) \right)$$

### 6.2 Microstructure Feature Vectors ($\mathbf{X}_t$)
The predictive models consume strictly stationary, scale-invariant engineered features:

1. **Garman-Klass Volatility (incorporating Open, High, Low, Close):**
   $$\sigma_{GK}^2 = \frac{1}{2}\left(\ln \frac{H_t}{L_t}\right)^2 - (2\ln 2 - 1)\left(\ln \frac{C_t}{O_t}\right)^2$$
2. **Normalized Distance to Session VWAP:**
   $$Z_{VWAP} = \frac{C_t - VWAP_t}{\sigma_{rolling}}$$
3. **Signed Volume Delta Proxy:**
   $$V_{delta} = V_t \cdot \frac{C_t - L_t - (H_t - C_t)}{H_t - L_t}$$
4. **Fractionally Differentiated Price ($d \approx 0.35$):**
   $$\tilde{P}_t = \sum_{k=0}^{K} \omega_k P_{t-k}, \quad \text{where } \omega_k = -\omega_{k-1} \frac{d - k + 1}{k}, \quad \omega_0 = 1$$
5. **Intraday Bar Range vs. Normalized ATR:**
   $$\text{Range Ratio}_t = \frac{H_t - L_t}{\text{ATR}_{14}(t)}$$

---

## 7. Comprehensive Pending Items & Technical Debt Catalog

Beyond the AI roadmap, this catalog audits all pending tasks, background jobs, and unfinished workflows from `PENDING_PROMPTS.md` and codebase inspection:

| Category | Pending Component / Task | Source / Origin | Status / Gap Identified | Required Remediation |
| :--- | :--- | :--- | :--- | :--- |
| **Engine Fix** | Double-Slippage Bug | Codebase Audit | Active in `services/backtest/engine.py` & `cost_model.py`. | Remove slippage cash calculation from `CostResult.total_taxes_and_fees`. |
| **Engine Fix** | Cartesian View Duplication | Codebase Audit | Active in `db/migrations.py` lines 260-261. | Re-architect `adjustment_factors` to store contiguous date ranges $[D_i, D_{i+1})$. |
| **Engine Fix** | BSM Theta Scaling Mismatch | Codebase Audit | Active in `services/options/greeks_engine.py` lines 37, 58. | Unify annualized time convention to trading days ($250$) or calendar days ($365$). |
| **Engine Fix** | Hardcoded Pattern Win Rates | Codebase Audit | Active in `services/pattern_recognition_service.py`. | Implement in-database Bayesian empirical win-rate calculations. |
| **Automation** | APScheduler Daily Sync Cron | Phase 06 (`PENDING_PROMPTS.md`) | `services/scheduler_service.py` exists but requires verification with active DuckDB lock handling. | Verify cron `'45 15 * * 1-5'` (`Asia/Kolkata`) with pre-flight auth probe at 15:40 IST. |
| **External Data** | Daily UDiFF Bhavcopy Fetcher | Phase 15 (`PENDING_PROMPTS.md`) | `scripts/fetch_bhavcopy_udiff.py` exists; requires automated daily ingestion hook into DuckDB. | Wire UDiFF Bhavcopy script to execute automatically after market close (16:00 IST). |
| **External Data** | Delivery % & FII/DII Fetcher | Phase 15 (`PENDING_PROMPTS.md`) | `scripts/fetch_delivery_data.py` exists; requires integration into Stock Screener filter parameters. | Add Delivery % and Institutional net flows as filterable columns in Screener UI. |
| **Alerts** | Telegram & Email Dispatchers | Phase 13 (`PENDING_PROMPTS.md`) | `services/notifiers/telegram_notifier.py` and `email_notifier.py` created but need webhook/SMTP settings in UI. | Add Alert Notification Settings modal in UI for Telegram Bot Token and SMTP credentials. |
| **Maintenance** | Anomaly Auditor & DB Drill | Phase 10 (`PENDING_PROMPTS.md`) | `scripts/audit_anomalies.py` and `backup_restore_drill.py` created; need scheduled cron trigger. | Register weekly DB backup and corporate action anomaly scan with scheduler. |
| **Benchmarking** | Phase 09 Hard Gate Benchmark | Phase 09 (`PENDING_PROMPTS.md`) | `scripts/run_m1_benchmark.py` created; requires full 5-gate benchmark report generation. | Execute `run_m1_benchmark.py` and verify all 5 gates pass against `NSE:RELIANCE-EQ`. |

---

## 8. Five-Phase Execution Roadmap & Verification Milestones

Aligned with the user interview decision (**Foundation First $\rightarrow$ Probabilistic Next-Candle Prediction Engine**), execution proceeds across five structured phases:

```
+-----------------------------------------------------------------------------------------------+
| PHASE 1: Core Engine & Mathematical Bug Remediation                                           |
| - Fix double-slippage in backtest engine and cost model                                       |
| - Fix corporate actions view Cartesian product duplication in DuckDB                          |
| - Standardize BSM Greeks time-scaling (365 vs 250) and add dividend yield                     |
+-----------------------------------------------------------------------------------------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------------+
| PHASE 2: Quantitative Feature Engineering & Stationarity Pipeline                            |
| - Build services/ai/feature_extractor.py (Garman-Klass, VWAP Z-score, Volume Delta)          |
| - Implement Fractional Differentiation (d ≈ 0.35) for stationarity preservation               |
| - Create in-memory DuckDB feature extraction pipeline for zero-latency training               |
+-----------------------------------------------------------------------------------------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------------+
| PHASE 3: LightGBM Quantile Range & Directional Prediction Models                              |
| - Train & calibrate Quantile Regressors for Q_0.10, Q_0.50, Q_0.90 High/Low envelopes         |
| - Train Calibrated Directional Conviction Classifier (P(Bullish Candle))                      |
| - Expose REST endpoints: GET /api/v1/predict/candle and GET /api/v1/predict/regime            |
+-----------------------------------------------------------------------------------------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------------+
| PHASE 4: Frontend TradingView Canvas Corridor & Predictive HUD                               |
| - Render shaded forward-projected probability envelope on Lightweight Charts canvas           |
| - Add Predictive HUD overlay in chart header (Bullish/Bearish conviction %, expected range)    |
| - Implement real-time websocket/forming candle update synchronization                         |
+-----------------------------------------------------------------------------------------------+
                                               |
                                               v
+-----------------------------------------------------------------------------------------------+
| PHASE 5: Dynamic Pattern Edge & Overfitting Guard (DSR)                                       |
| - Replace static pattern accuracy with dynamic Bayesian in-database empirical win-rates       |
| - Implement Deflated Sharpe Ratio (DSR) in Backtest Lab to eliminate data mining bias        |
| - Execute full test suite and Phase 09 benchmark verification                                |
+-----------------------------------------------------------------------------------------------+
```

### Detailed Phase Deliverables Table

| Phase | Milestone Name | Target Files Touched / Created | Acceptance & Testing Criteria |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **Core Calculation & View Fixes** | - `services/backtest/cost_model.py`<br>- `services/backtest/engine.py`<br>- `db/migrations.py`<br>- `services/options/greeks_engine.py` | - `pytest tests/test_backtest.py` passes with single slippage deduction.<br>- Multi-split stocks (e.g., INFY, RELIANCE) return strictly $1:1$ rows from `candles_1d_adjusted`.<br>- BSM Theta values match analytical benchmark options calculator outputs. |
| **Phase 2** | **Predictive Feature Store** | - `services/ai/feature_extractor.py`<br>- `services/ai/stationarity.py`<br>- `tests/test_ai_features.py` | - Vectorized extraction completes in $< 20\text{ms}$ on 5,000 candles.<br>- All features pass Augmented Dickey-Fuller (ADF) stationarity test ($p < 0.01$).<br>- Strict anti-lookahead verification: bar $t$ features use strictly data $\le t$. |
| **Phase 3** | **LightGBM Quantile Inference** | - `services/ai/candle_predictor.py`<br>- `services/ai/regime_classifier.py`<br>- `api/routers/predictions.py`<br>- `main.py` | - Prediction latency $< 10\text{ms}$ per request on single CPU core.<br>- Empirical test coverage of $80\% \pm 2\%$ for the $Q_{0.10} - Q_{0.90}$ prediction envelope.<br>- Calibrated Brier score $< 0.21$ for directional classifier. |
| **Phase 4** | **Chart Canvas Visualization** | - `static/js/chart_predictor_overlay.js`<br>- `static/js/chart.js`<br>- `static/index.html`<br>- `static/css/theme.css` | - Predictive corridor plots smoothly ahead of the active forming candle on Lightweight Charts.<br>- Synchronized with chart panning, mouse wheel zoom, and window resize.<br>- Predictive HUD renders conviction gauge and regime badge cleanly in both Simple and Pro modes. |
| **Phase 5** | **Dynamic Edge & DSR Validation** | - `services/pattern_recognition_service.py`<br>- `services/backtest/robustness.py`<br>- `static/js/backtest_ui.js`<br>- `scripts/run_m1_benchmark.py` | - Pattern markers display live Bayesian historical win rates and sample sizes.<br>- Backtest Lab calculates Deflated Sharpe Ratio with asymptotic $p$-value.<br>- Full automated test suite passes with zero regressions. |

---

## 9. Bilingual Tamil Operations Summary (தமிழ் சுருக்கம்)

### 1. முக்கிய கணித மற்றும் சிஸ்டம் பிழைகள் திருத்தம் (Core Fixes)
- **Double-Slippage திருத்தம்:** தற்போதைய பேக்டெஸ்ட் என்ஜினில் slippage இரண்டு முறை கழிக்கப்படுகிறது (விலையிலும், கட்டணத்திலும்). இதை சரிசெய்து ஒரு முறை மட்டுமே கணக்கிடப்படும்.
- **Cartesian Join திருத்தம்:** பல முறை Stock Split / Bonus கண்ட பங்குகளில் (INFY, Reliance போன்றவை) DuckDB View-ல் ஒரே நாள் டேட்டா பல முறை டூப்ளிகேட் ஆகிறது. இதை மாற்றி துல்லியமான cumulative factor கொண்டு சரிசெய்யப்படும்.
- **Options Theta திருத்தம்:** Black-Scholes கணக்கீட்டில் 365 நாட்கள் மற்றும் 250 நாட்கள் கலந்து பயன்படுத்தப்பட்ட குழப்பம் நீக்கப்பட்டு சீரமைக்கப்படும்.

### 2. கேண்டில் கணிக்கும் AI தொழில்நுட்பம் (Candle Prediction Science)
- பங்குச்சந்தையில் அடுத்த கேண்டில் பச்சை அல்லது சிகப்பு என சாதாரணமாக கணிக்க முடியாது.
- மாறாக, **LightGBM Quantile Regression** மூலம் அடுத்த கேண்டிலின் **அதிகபட்ச விலை (High) மற்றும் குறைந்தபட்ச விலை (Low) எல்லைகள் (Range Corridor)** 80% துல்லியத்துடன் சார்ட்டிலேயே ஷேடிங் செய்யப்பட்டு காட்டப்படும்.
- **Directional Probability:** அடுத்த கேண்டில் ஏறுவதற்கான வாய்ப்பு எத்தனை சதவீதம் (எ.கா. `Bullish: 68%`) என்பதை Volume Delta மற்றும் VWAP மூலம் கணக்கிட்டு Chart HUD-ல் காட்டப்படும்.
- **Market Regime (HMM):** சந்தை தற்போது ட்ரெண்டில் உள்ளதா அல்லது சைட்வேஸ் (Choppy) சந்தையா என்பதை AI கண்டறிந்து எச்சரிக்கும்.

---

## 10. Statutory SEBI Regulatory Compliance Notice

> [!IMPORTANT]
> **STATUTORY REGULATORY DISCLAIMER (SEBI COMPLIANCE)**
> 
> The **NSE Quant Platform** is an independent, local-first analytical workstation designed strictly for educational, personal quantitative research, and algorithmic backtesting purposes.
> 
> 1. **No Investment Advice:** The platform does not provide investment advisory services, trading tips, or financial recommendations as defined under the SEBI (Investment Advisers) Regulations, 2013.
> 2. **No Automated Live Execution:** Live broker order routing is permanently disabled (`HTTP 403 Forbidden`). All trade execution features operate strictly within simulated paper trading environments.
> 3. **Market Risks:** Trading in securities markets, particularly futures and options (F&O), involves substantial financial risk. Quantitative models and AI predictive envelopes represent probabilistic forecasts and cannot guarantee future market returns.

---
*End of Master AI Predictive Roadmap & Technical Audit.*
