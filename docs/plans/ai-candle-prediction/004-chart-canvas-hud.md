# Plan 004: Frontend TradingView Canvas Corridor & Real-Time Predictive HUD

## Goal
Integrate visual prediction elements onto the frontend user interface:
1. Render a forward-projected shaded range probability corridor on the TradingView Lightweight Charts canvas.
2. Mount a real-time Predictive HUD badge in the chart header displaying directional probability, expected High/Low corridor, and regime tag.
3. Handle graceful fallback for assets with sparse data ($< 200$ bars) by rendering classical ATR corridors.

## Read first
- `trading-app/static/js/chart.js`
- `trading-app/static/js/volume_profile_overlay.js`
- `trading-app/static/index.html`
- `trading-app/static/css/theme.css`

## Steps

### Step 1: Implement chart predictor canvas overlay
- Create `static/js/chart_predictor_overlay.js`.
- Follow the HTML5 Canvas pattern from `volume_profile_overlay.js`.
- Render forward-projected boundaries ahead of the latest visible candle:
  - Upper line: dashed gold line at predicted $Q_{0.90}$ High.
  - Lower line: dashed cyan line at predicted $Q_{0.10}$ Low.
  - Median line: solid line at predicted $Q_{0.50}$ Close.
  - Semi-transparent gradient fill between upper and lower boundaries.
- Bind viewport coordinate conversions to `chart.timeScale().coordinateToLogical()` and handle `window.devicePixelRatio`.

### Step 2: Mount Predictive HUD badge in chart header
- In `static/index.html`, add `#predictive-hud` container inside the active chart header controls.
- Add responsive styling in `static/css/theme.css`:
  - Bullish conviction badge ($>60\%$): emerald green text with glowing green border.
  - Bearish conviction badge ($>60\%$): crimson red text with glowing red border.
  - Neutral / Choppy badge: amber border with warning indicator.
  - Tooltip explaining quantile envelope and conformal coverage guarantee ($80\%$).

### Step 3: Wire prediction lifecycle and graceful fallback in chart.js
- In `static/js/chart.js`, trigger prediction fetch on symbol load, timeframe change, or forming candle completion:
  `fetch('/api/v1/predict/candle?symbol=' + symbol + '&timeframe=' + timeframe)`
- Pass prediction payload to `PredictorOverlay.update(data)`.
- Implement graceful fallback: if API returns insufficient data or symbol has $< 200$ candles, display `Status: Insufficient Data (< 200 bars)` in HUD and render ATR(14) volatility envelope.

### Step 4: Verify JavaScript syntax and frontend integration bindings
- Create `tests/unit/test_frontend_prediction_bindings.py` asserting that script tags and HUD elements exist in `static/index.html`.
- Run syntax verification with Node.js on `static/js/chart_predictor_overlay.js`.
- Verify absence of unhandled exceptions or NaN canvas coordinate errors.

## Do not touch
- `trading-app/core/security.py`
- `trading-app/services/backtest/engine.py`

## Acceptance
Run:
```bash
node -c static/js/chart_predictor_overlay.js
.\.venv\Scripts\pytest.exe tests/unit/test_frontend_prediction_bindings.py
```
Syntax check and integration tests must pass with exit code 0.

## If blocked
Write exact error trace, failing assertions, and attempted fixes to `docs/plans/ai-candle-prediction/BLOCKED.md` and stop.

## Report back
Provide syntax verification and test output confirming clean overlay mounting and graceful fallback handling.
