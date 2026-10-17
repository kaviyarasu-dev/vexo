import pytest
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from main import app
from services.ai.candle_predictor import LightGBMCandlePredictor, CandlePredictionResult
from services.ai.regime_classifier import MarketRegimeClassifier, RegimeResult


@pytest.fixture
def synthetic_history():
    """Generates synthetic OHLCV sequence for model verification."""
    np.random.seed(123)
    n = 200
    dates = [datetime(2024, 1, 1) + timedelta(minutes=5 * i) for i in range(n)]
    p = 2500.0 * np.exp(np.cumsum(np.random.normal(0.0001, 0.005, n)))
    h = p * (1.0 + np.abs(np.random.normal(0, 0.002, n)))
    l = p * (1.0 - np.abs(np.random.normal(0, 0.002, n)))
    o = l + np.random.uniform(0.2, 0.8, n) * (h - l)
    c = l + np.random.uniform(0.2, 0.8, n) * (h - l)
    v = np.random.randint(2000, 30000, n).astype(float)
    return pd.DataFrame({"timestamp": dates, "open": o, "high": h, "low": l, "close": c, "volume": v})


def test_quantile_monotonicity_and_envelope(synthetic_history):
    """Verifies that the predictive envelope strictly guarantees Low(10) <= Close(50) <= High(90)."""
    predictor = LightGBMCandlePredictor()
    metrics = predictor.train(synthetic_history)
    
    assert metrics["coverage_80pct"] >= 0.60
    assert metrics["samples"] >= 50
    
    # Predict across 10 sequential steps
    for i in range(150, 160):
        window = synthetic_history.iloc[:i]
        res = predictor.predict_next(window, symbol="NSE:TEST-EQ", timeframe="5m")
        
        assert isinstance(res, CandlePredictionResult)
        # Strict monotonicity assertion
        assert res.low_10 <= res.close_50, f"Monotonicity violation: Low {res.low_10} > Close {res.close_50}"
        assert res.close_50 <= res.high_90, f"Monotonicity violation: Close {res.close_50} > High {res.high_90}"
        assert res.expected_range_pts >= 0.0
        assert 0.0 <= res.directional_prob <= 1.0


def test_cpu_inference_latency_benchmark(synthetic_history):
    """Verifies institutional performance benchmark: CPU inference latency must be < 10ms."""
    predictor = LightGBMCandlePredictor()
    predictor.train(synthetic_history)
    
    # Warm up
    predictor.predict_next(synthetic_history)
    
    latencies = []
    for _ in range(30):
        t0 = time.perf_counter()
        _ = predictor.predict_next(synthetic_history)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        
    mean_latency = float(np.mean(latencies))
    p95_latency = float(np.percentile(latencies, 95))
    
    print(f"\nInference Latency Benchmark -> Mean: {mean_latency:.2f}ms, P95: {p95_latency:.2f}ms")
    assert mean_latency < 10.0, f"Inference too slow: {mean_latency:.2f}ms exceeds 10ms institutional ceiling"


def test_3_state_regime_classifier(synthetic_history):
    """Verifies 3-state Gaussian mixture regime detector."""
    classifier = MarketRegimeClassifier()
    classifier.fit(synthetic_history)
    
    regime = classifier.predict_regime(synthetic_history)
    assert isinstance(regime, RegimeResult)
    assert regime.state in (0, 1, 2)
    assert regime.label in ("BULLISH_TREND", "HIGH_VOL_TREND", "CHOPPY_SIDEWAYS")
    assert regime.volatility_level in ("LOW", "MODERATE", "ELEVATED")
    
    prob_sum = sum(regime.probabilities.values())
    assert pytest.approx(prob_sum, abs=0.01) == 1.0


def test_fastapi_prediction_endpoints():
    """Verifies FastAPI REST endpoints under /api/v1/predict with standard ApiResponse envelope."""
    client = TestClient(app)
    
    # 1. GET /api/v1/predict/candle
    res_candle = client.get("/api/v1/predict/candle?symbol=NSE:RELIANCE-EQ&timeframe=1D")
    assert res_candle.status_code == 200
    body = res_candle.json()
    assert body["success"] is True
    assert "data" in body
    data = body["data"]
    assert "high_90" in data
    assert "low_10" in data
    assert "close_50" in data
    assert "directional_prob" in data
    assert data["low_10"] <= data["close_50"] <= data["high_90"]
    assert body["meta"]["correlation_id"] is not None
    
    # 2. GET /api/v1/predict/regime
    res_regime = client.get("/api/v1/predict/regime?symbol=NSE:RELIANCE-EQ&timeframe=1D")
    assert res_regime.status_code == 200
    body_regime = res_regime.json()
    assert body_regime["success"] is True
    assert body_regime["data"]["state"] in (0, 1, 2)
    assert "probabilities" in body_regime["data"]
    
    # 3. POST /api/v1/predict/train-custom
    res_train = client.post("/api/v1/predict/train-custom?symbol=NSE:RELIANCE-EQ&timeframe=1D")
    assert res_train.status_code == 200
    body_train = res_train.json()
    assert body_train["success"] is True
    assert body_train["data"]["status"] == "FINE_TUNING_COMPLETE"
    assert "metrics" in body_train["data"]
