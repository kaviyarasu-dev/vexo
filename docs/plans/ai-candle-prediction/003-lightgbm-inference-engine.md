# Plan 003: LightGBM Quantile & Directional Inference Engine

## Goal
Implement the quantitative inference models and REST API layer:
1. Train and calibrate LightGBM Quantile Regressors ($Q_{0.10}, Q_{0.50}, Q_{0.90}$) predicting the next candle's High, Low, and Close envelope with monotonic ordering guarantees.
2. Implement Calibrated Directional Conviction Classifier estimating $P(\text{Bullish Bar}) \in [0.0, 1.0]$.
3. Implement 3-State Gaussian Hidden Markov Model (HMM) for latent market regime detection.
4. Expose standardized REST endpoints under `/api/v1/predict/...` in FastAPI with sub-10ms CPU inference latency.

## Read first
- `trading-app/api/models/envelope.py`
- `trading-app/main.py`
- `trading-app/db/connection.py`

## Steps

### Step 1: Implement LightGBM quantile range and directional predictor
- Create `services/ai/candle_predictor.py`.
- Define `CandlePredictionResult(high_90, close_50, low_10, directional_prob, regime_state, confidence)`.
- Implement `LightGBMCandlePredictor`:
  - `train(features_df)`: fits quantile regressors for $q=0.10$ (lower bound), $q=0.50$ (median), $q=0.90$ (upper bound).
  - Fits calibrated binary classifier for directional return $C_{t+1} > O_{t+1}$.
  - `predict_next(current_features)`: generates quantile envelopes.
  - Enforces monotonicity check: $\hat{L}_{t+1}^{(0.10)} \le \hat{P}_{t+1}^{(0.50)} \le \hat{H}_{t+1}^{(0.90)}$.
  - Implements model saving and loading (`data/models/`).

### Step 2: Implement 3-State Gaussian HMM market regime classifier
- Create `services/ai/regime_classifier.py`.
- Implement `MarketRegimeClassifier`:
  - Consumes rolling 20-bar log returns and Garman-Klass volatility.
  - Fits 3-State Gaussian HMM (or Gaussian Mixture Jump Model):
    - State 0: Low-Vol Bullish Trend
    - State 1: High-Vol Trend / Breakout
    - State 2: Mean-Reverting Choppy / Sideways
  - `predict_regime(features)`: returns current state identifier and state probability distribution.

### Step 3: Implement FastAPI prediction REST router
- Create `api/routers/predictions.py`.
- Endpoints:
  - `GET /api/v1/predict/candle?symbol={symbol}&timeframe={timeframe}`: returns next-candle quantile envelope and directional probability in standardized `ApiResponse` envelope.
  - `GET /api/v1/predict/regime?symbol={symbol}`: returns current regime state and label.
  - `POST /api/v1/predict/train-custom?symbol={symbol}`: triggers on-demand background training/fine-tuning in $< 3$ seconds.
- Adhere to single-writer DuckDB safety using `db.get_read_cursor()`.

### Step 4: Mount router in main.py and verify inference test suite
- In `main.py`, include `predictions.router` under `/api/v1/predict`.
- Create `tests/unit/test_ai_models.py`.
- Test 1: Verify quantile monotonicity ($Q_{0.10} \le Q_{0.50} \le Q_{0.90}$) on test samples.
- Test 2: Verify CPU inference latency is $< 10\text{ms}$.
- Test 3: Verify REST endpoints return HTTP 200 with valid `ApiResponse` payload.

## Do not touch
- `trading-app/core/security.py`
- `trading-app/services/backtest/engine.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/unit/test_ai_models.py
```
All model inference and API tests must pass with exit code 0.

## If blocked
Write exact error trace, failing assertions, and attempted fixes to `docs/plans/ai-candle-prediction/BLOCKED.md` and stop.

## Report back
Provide test execution output showing quantile envelope verification and sub-10ms CPU inference benchmark.
