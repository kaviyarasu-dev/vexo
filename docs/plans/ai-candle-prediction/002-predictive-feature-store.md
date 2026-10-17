# Plan 002: Predictive Quantitative Feature Store & Stationarity Engine

## Goal
Implement a high-performance, stationary feature extraction pipeline for machine learning candle forecasting:
1. Pin and install required numerical dependencies (`lightgbm`, `scikit-learn`, `scipy`, `statsmodels`).
2. Implement Fractional Differentiation ($d \approx 0.35$) preserving price memory while achieving statistical stationarity (ADF test $p < 0.01$).
3. Implement vectorized feature extraction: Garman-Klass Volatility, Normalized VWAP Z-score distance, Signed Volume Delta proxy, and Range Ratios.
4. Verify anti-lookahead bias compliance ($t$ features consume data strictly $\le t$).

## Read first
- `trading-app/services/indicator_service.py`
- `trading-app/services/resampling_service.py`
- `trading-app/requirements.txt`

## Steps

### Step 1: Pin and install required machine learning libraries
- Add `lightgbm>=4.3.0`, `scikit-learn>=1.4.0`, `scipy>=1.12.0`, `statsmodels>=0.14.0` to `requirements.txt`.
- Install packages into `.venv` using `pip install -r requirements.txt`.
- Verify importability in Python.

### Step 2: Implement stationarity engine with fractional differentiation
- Create `services/ai/stationarity.py`.
- Implement `compute_weights(d, size, threshold)`: computes expanding window memory weights $\omega_k = -\omega_{k-1}\frac{d - k + 1}{k}$ with $\omega_0 = 1$.
- Implement `fractional_differentiation(series, d)`: computes stationary differentiated series.
- Implement `check_stationarity(series)`: runs Augmented Dickey-Fuller test via `statsmodels.tsa.stattools.adfuller` and asserts $p < 0.01$.

### Step 3: Implement vectorized quantitative feature extractor
- Create `services/ai/feature_extractor.py`.
- Implement `extract_features(df_ohlcv)` consuming standard OHLCV DataFrames:
  - Garman-Klass Volatility: $\sigma_{GK}^2 = 0.5(\ln(H/L))^2 - (2\ln 2 - 1)(\ln(C/O))^2$.
  - Normalized VWAP Z-score: $Z_{VWAP} = (C_t - VWAP_t) / \sigma_{rolling}$.
  - Signed Volume Delta: $V_{delta} = V_t \cdot \frac{C_t - L_t - (H_t - C_t)}{H_t - L_t}$.
  - Intraday Range Ratio: $(H_t - L_t) / \text{ATR}_{14}(t)$.
  - Fractionally Differentiated Close price.
- Return clean Pandas DataFrame with NaN values purged.

### Step 4: Write and verify unit test suite for feature store
- Create `tests/unit/test_ai_features.py`.
- Test 1: Verify output feature shapes and types.
- Test 2: Verify stationarity ($p < 0.01$ on sample price series).
- Test 3: Anti-lookahead leakage verification: ensure feature values at index $t$ are mathematically invariant to appending future rows $t+1 \dots t+N$.

## Do not touch
- `trading-app/services/backtest/engine.py`
- `trading-app/db/connection.py`
- `trading-app/core/security.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/unit/test_ai_features.py
```
All feature and stationarity tests must pass with exit code 0.

## If blocked
Write exact error trace, failing assertions, and attempted fixes to `docs/plans/ai-candle-prediction/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming zero lookahead leakage and verified stationarity across all engineered features.
