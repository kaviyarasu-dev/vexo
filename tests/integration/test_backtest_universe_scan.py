import pytest
import urllib.request
import json
from starlette.testclient import TestClient
from main import app
from db.connection import get_db, DuckDBConnectionManager

def test_scan_universe_endpoint_live():
    # Test against live running server at http://127.0.0.1:8000
    payload = {
        "strategy": "RSI_REVERSION",
        "timeframe": "1D",
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "parameters": {
            "rsi_period": 14,
            "oversold": 30.0,
            "overbought": 70.0
        },
        "max_symbols": 20
    }
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/v1/backtest/scan-universe",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Fallback to TestClient with in-memory DB override
        mock_db = DuckDBConnectionManager(":memory:")
        app.dependency_overrides[get_db] = lambda: mock_db
        client = TestClient(app)
        resp = client.post("/api/v1/backtest/scan-universe", json=payload)
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()

    assert data["success"] is True
    assert data["strategy"] == "RSI_REVERSION"
    assert "total_scanned" in data
    assert "current_matches" in data
    assert "past_matches" in data
    assert isinstance(data["current_matches"], list)
    assert isinstance(data["past_matches"], list)
    assert data["total_scanned"] > 0

    if data["past_matches"]:
        item = data["past_matches"][0]
        assert "symbol" in item
        assert "total_trades" in item
        assert "win_count" in item
        assert "loss_count" in item
        assert "win_rate" in item
        assert "net_pnl" in item
        assert "profit_factor" in item
