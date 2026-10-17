# Technical Design Specification: AI Candle Prediction & Quantitative Engine Upgrade

**Document ID:** `2026-10-17-ai-candle-prediction-design`  
**Feature Slug:** `ai-candle-prediction`  
**Author:** Principal Financial AI Engineer & Senior Quantitative Researcher  
**Target Architecture:** FastAPI, DuckDB, TradingView Lightweight Charts (v4.2.1), LightGBM  
**Status:** Spec Approved / Ready for Plan Split  

---

## 1. Overview & Business Value

This specification defines the institutional upgrade of the **NSE Quant Platform** (`d:\trading-app`). It resolves three foundational calculation bugs in the active codebase (Double-Slippage in the backtest engine, Cartesian product join in dynamic corporate actions views, and time-scale distortion in Black-Scholes Greeks), and implements a high-performance **Probabilistic Next-Candle Prediction Suite** powered by **LightGBM Quantile Gradient Boosting**.

Rather than attempting naive point prediction of non-stationary prices, this system delivers:
1. **Conformal Quantile Range Corridor ($Q_{0.10}, Q_{0.50}, Q_{0.90}$):** Forward-projected directly onto the TradingView chart canvas with $80\%$ empirical coverage guarantees.
2. **Calibrated Directional Conviction Probability ($P(\text{Bullish Bar})$):** Real-time probability estimation conditioned on stationary microstructural features (Volume Delta, VWAP Z-score, Fractional Differentiation).
3. **Latent Market Regime Classifier (3-State Gaussian HMM):** Identifies whether the active candle is forming in a Trend or Choppy Mean-Reverting regime.
4. **Dynamic Bayesian Pattern Edge Evaluator:** Computes empirical in-database win-rates replacing static hardcoded dictionary metrics.
5. **Deflated Sharpe Ratio (DSR):** Guards against strategy overfitting in the Backtest Lab by adjusting for selection bias under multiple testing.

---

## 2. Architecture & Subsystem Division

The implementation is partitioned into **five standalone, sequential parts** following the File Splitting Rule for Large (L) features:

```
+---------------------------------------------------------------------------------------------------+
| PART 1: Core Engine & Mathematical Bug Remediation                                                |
| Target Files: services/backtest/engine.py, cost_model.py, db/migrations.py, greeks_engine.py      |
| Verify: pytest tests/test_core_engine_fixes.py                                                     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| PART 2: Predictive Quantitative Feature Store & Stationarity Engine                               |
| Target Files: services/ai/feature_extractor.py, stationarity.py, requirements.txt                 |
| Verify: pytest tests/test_ai_features.py                                                          |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| PART 3: LightGBM Quantile Range & Directional Inference Engine                                    |
| Target Files: services/ai/candle_predictor.py, regime_classifier.py, api/routers/predictions.py   |
| Verify: pytest tests/test_ai_models.py                                                            |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| PART 4: Frontend TradingView Canvas Corridor & Real-Time Predictive HUD                           |
| Target Files: static/js/chart_predictor_overlay.js, chart.js, static/index.html, theme.css       |
| Verify: node -c static/js/chart_predictor_overlay.js                                              |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| PART 5: Dynamic Bayesian Pattern Edge & Deflated Sharpe Ratio (DSR)                               |
| Target Files: services/pattern_recognition_service.py, services/backtest/robustness.py           |
| Verify: pytest tests/test_pattern_recognition.py tests/test_dsr.py                                |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Specifications per Part

### Part 1: Core Engine & Mathematical Bug Remediation
1. **Double-Slippage Fix:**
   - In [`services/backtest/cost_model.py`](file:///d:/trading-app/services/backtest/cost_model.py), remove `slippage` from `CostResult.total_taxes_and_fees`.
   - Maintain `fill_price = open_price * (1 \pm \text{slippage_factor})` in [`services/backtest/engine.py`](file:///d:/trading-app/services/backtest/engine.py). Slippage is modeled strictly as price execution impact, not a double cash fee deduction.
2. **Corporate Actions View Cartesian Join Fix:**
   - In [`db/migrations.py`](file:///d:/trading-app/db/migrations.py), redesign `candles_1d_adjusted` and `candles_1m_adjusted` dynamic views.
   - Re-architect `adjustment_factors` to precompute the cumulative multiplicative factor $A_t = \prod_{i} r_i$ with non-overlapping effective dates $[D_i, D_{i+1})$.
   - Verify that multi-split equities (e.g., Infosys with 4 historical splits/bonuses) return strictly $1:1$ candle rows matching `candles_1d_raw`.
3. **Options Greeks Time Scale Unification:**
   - In [`services/options/greeks_engine.py`](file:///d:/trading-app/services/options/greeks_engine.py), standardize time to trading days convention ($T = t / 250.0$) across both $d_1, d_2$ and daily Theta decay (`theta = theta / 250.0`).
   - Add continuous dividend yield $q$ parameter (default $q=0.0$, dynamically populated for NSE dividend payers).

### Part 2: Predictive Quantitative Feature Store & Stationarity Engine
1. **Vectorized Feature Extractor (`services/ai/feature_extractor.py`):**
   - **Garman-Klass Volatility:** $\sigma_{GK}^2 = 0.5(\ln(H/L))^2 - (2\ln 2 - 1)(\ln(C/O))^2$
   - **Normalized VWAP Z-score:** $Z_{VWAP} = (C_t - VWAP_t) / \sigma_{rolling}$
   - **Signed Volume Delta Proxy:** $V_{delta} = V_t \cdot \frac{C_t - L_t - (H_t - C_t)}{H_t - L_t}$
   - **Range Ratio:** $(H_t - L_t) / \text{ATR}_{14}(t)$
2. **Stationarity Engine (`services/ai/stationarity.py`):**
   - Implements Fractional Differentiation via expanding memory window:
     $$(1 - B)^d = \sum_{k=0}^{K} (-1)^k \binom{d}{k} B^k, \quad d \approx 0.35$$
   - Enforces Augmented Dickey-Fuller (ADF) test verification ($p < 0.01$).
   - Strict anti-lookahead guarantee: feature generation at index $t$ uses strictly data $\le t$.

### Part 3: LightGBM Quantile Range & Directional Inference Engine
1. **Quantile Regressors (`services/ai/candle_predictor.py`):**
   - Trains three LightGBM regressors with pinball loss for $Q_{0.10}$ (Lower Bound), $Q_{0.50}$ (Expected Median), and $Q_{0.90}$ (Upper Bound) of the next candle range.
   - Enforces monotonicity constraint: $\hat{L}_{t+1}^{(0.10)} \le \hat{P}_{t+1}^{(0.50)} \le \hat{H}_{t+1}^{(0.90)}$.
2. **Directional Conviction Classifier:**
   - LightGBM binary classifier with isotonic calibration outputting $P(\text{Bullish Bar}) \in [0.0, 1.0]$.
3. **Latent Market Regime Classifier (`services/ai/regime_classifier.py`):**
   - 3-State Gaussian Hidden Markov Model (HMM) classifying:
     - State 0: Low-Vol Bullish Trend
     - State 1: High-Vol Trend / Breakout
     - State 2: Mean-Reverting Choppy
4. **REST Prediction Router (`api/routers/predictions.py`):**
   - `GET /api/v1/predict/candle?symbol={symbol}&timeframe={timeframe}`
   - `GET /api/v1/predict/regime?symbol={symbol}`
   - `POST /api/v1/predict/train-custom?symbol={symbol}` (On-demand training in $< 3$s)
   - Adheres to canonical `ApiResponse[T]` envelope with correlation IDs.

### Part 4: Frontend TradingView Canvas Corridor & Real-Time Predictive HUD
1. **Interactive Canvas Overlay (`static/js/chart_predictor_overlay.js`):**
   - Extends the custom HTML5 Canvas rendering pattern established by Volume Profile.
   - Renders forward-projected shaded range corridor:
     - Upper boundary: dashed gold line at $\hat{H}_{t+1}^{(0.90)}$.
     - Lower boundary: dashed teal line at $\hat{L}_{t+1}^{(0.10)}$.
     - Center target: solid line at $\hat{P}_{t+1}^{(0.50)}$.
     - Semi-transparent fill between upper and lower quantiles.
   - Automatically synchronizes with TradingView Lightweight Charts pan and zoom.
2. **Predictive HUD (`static/index.html` + `static/js/chart.js`):**
   - Mounted in top chart header dock.
   - Displays: `Direction: Bullish (68.4%) | Expected Range: ₹2,510 - ₹2,545 | Regime: Bullish Trend (State 0)`.
   - Dynamic color glow: emerald green for bullish $> 60\%$, crimson red for bearish $> 60\%$, amber for choppy regime.
   - Graceful fallback: for symbols with $< 200$ historical bars, shows `Status: Insufficient Data (< 200 bars)` with classical ATR bounds.

### Part 5: Dynamic Bayesian Pattern Edge & Deflated Sharpe Ratio (DSR)
1. **Empirical Bayesian Win Rates (`services/pattern_recognition_service.py`):**
   - Replaces hardcoded dictionary numbers with live DuckDB query:
     $$P(\text{Win} \mid \text{Pattern}) = \frac{\alpha_0 + \text{Wins}}{\alpha_0 + \beta_0 + \text{Total Occurrences}}$$
   - Marker tooltip displays: `Bullish Engulfing | Win Rate: 64.2% (n=312) | EV: +₹1.42/share | Regime: Trending`.
2. **Deflated Sharpe Ratio (`services/backtest/robustness.py`):**
   - Implements Marcos López de Prado's DSR formulation adjusting for skewness ($\hat{\gamma}_3$), kurtosis ($\hat{\gamma}_4$), and number of optimization trials ($N$).
   - Backtest Lab results dashboard displays Amber Overfitting Alert badge if $p$-value exceeds $0.05$.

---

## 4. Verification & Testing Matrix

| Subsystem Part | Test Command | Acceptance Gate |
| :--- | :--- | :--- |
| **Part 1** | `pytest tests/test_core_engine_fixes.py` | - Zero double-slippage deduction in closed trades.<br>- Cartesian join test passes on INFY corporate action dates with exact $1:1$ row count.<br>- BSM Theta matches analytical benchmark outputs. |
| **Part 2** | `pytest tests/test_ai_features.py` | - All generated feature series pass Augmented Dickey-Fuller stationarity test ($p < 0.01$).<br>- Lookahead bias test fixture confirms zero future-bar leakage. |
| **Part 3** | `pytest tests/test_ai_models.py` | - Quantile monotonicity check: $Q_{0.10} \le Q_{0.50} \le Q_{0.90}$ across $100\%$ of test samples.<br>- CPU inference latency $< 10\text{ms}$ per request.<br>- Calibrated Brier score $< 0.21$. |
| **Part 4** | `node -c static/js/chart_predictor_overlay.js` | - Clean JavaScript syntax compilation with zero runtime exceptions.<br>- Canvas projection aligns with time scale coordinates on viewport resize. |
| **Part 5** | `pytest tests/test_pattern_recognition.py tests/test_dsr.py` | - Dynamic win-rate query executes in $< 15\text{ms}$ in DuckDB.<br>- DSR formula rejects overfitted synthetic return series with $p > 0.05$. |

---

## 5. SEBI Regulatory & Safety Safeguards
- Live broker order execution remains permanently gated with `HTTP 403 Forbidden` (`core.security.OrderExecutionGateMiddleware`).
- All predictive signals, corridors, and probability metrics are designated strictly for simulated paper trading, backtesting, and educational quantitative research.
