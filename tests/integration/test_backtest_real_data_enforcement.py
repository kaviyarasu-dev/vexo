"""
Integration Tests for Real Market Data Backtesting Enforcement.
Validates:
1. Backtest executes on authentic DuckDB candles for valid symbols (e.g. NSE:RELIANCE-EQ).
2. Zero synthetic data fallback: requesting a non-existent stock with no DB data strictly fails with HTTP 400.
3. Portfolio backtest skips missing symbols and reports them in skipped_symbols rather than inventing fake data.
"""

import urllib.request
import json
import pytest


def _post_json(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, {"detail": body}


def test_real_data_backtest_success_for_existing_symbol():
    """Verifies that backtest runs successfully using real DuckDB candles."""
    payload = {
        "strategy": "SMA_CROSS",
        "symbol": "NSE:RELIANCE-EQ",
        "timeframe": "1D",
        "start_date": "2022-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 1000000.0,
        "trade_type": "DELIVERY",
        "parameters": {
            "short_window": 20,
            "long_window": 50
        }
    }
    status, data = _post_json("http://127.0.0.1:8000/api/v1/backtest/run", payload)
    assert status == 200
    assert data["success"] is True
    res = data["data"]
    assert res["data_version_hash"] is not None
    assert isinstance(res["trades"], list)
    assert isinstance(res["equity_curve"], list)
    assert len(res["equity_curve"]) > 50


def test_zero_synthetic_data_rejection_for_missing_symbol():
    """Verifies that requesting an unknown symbol without DB data strictly throws HTTP 400 (no fake GBM candles)."""
    payload = {
        "strategy": "SMA_CROSS",
        "symbol": "NSE:NONEXISTENT_FAKE_STOCK-EQ",
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_capital": 1000000.0,
        "parameters": {
            "short_window": 10,
            "long_window": 30
        }
    }
    status, err_body = _post_json("http://127.0.0.1:8000/api/v1/backtest/run", payload)
    assert status == 400
    msg = err_body.get("error", {}).get("message") or err_body.get("message") or err_body.get("detail", "")
    assert "No verified real historical data available in DuckDB" in msg or "Insufficient real historical data" in msg


def test_portfolio_backtest_skips_missing_stocks_no_synthetic_data():
    """Verifies that portfolio backtest skips stocks without DB data and records them in skipped_symbols."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:RELIANCE-EQ", "NSE:FAKE_NONEXISTENT_STOCK-EQ"],
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 1000000.0,
        "max_open_positions": 5,
        "sizing_model": "EQUAL_WEIGHT",
        "sizing_val": 20.0,
        "ranking_metric": "AUTO",
        "parameters": {
            "short_window": 10,
            "long_window": 30
        }
    }
    status, data = _post_json("http://127.0.0.1:8000/api/v1/backtest/portfolio/run", payload)
    assert status == 200
    assert data["status"] == "COMPLETED"
    assert "NSE:RELIANCE-EQ" in data["symbols_tested"]
    assert "NSE:FAKE_NONEXISTENT_STOCK-EQ" not in data["symbols_tested"]
    assert "NSE:FAKE_NONEXISTENT_STOCK-EQ" in data["skipped_symbols"]
