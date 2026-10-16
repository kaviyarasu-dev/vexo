"""
Integration Tests for Portfolio Backtest REST Endpoints.
Tests GET /api/v1/backtest/portfolio/universes and POST /api/v1/backtest/portfolio/run.
Validates predefined & custom universes, sizing models, signal contention, error handling, and response schema.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_portfolio_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_get_portfolio_universes():
    """Verifies retrieval of predefined NSE index universes."""
    response = client.get("/api/v1/backtest/portfolio/universes")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    universes = data["universes"]
    assert len(universes) >= 3

    ids = [u["id"] for u in universes]
    assert "NIFTY_50" in ids
    assert "NIFTY_NEXT_50" in ids
    assert "NIFTY_MIDCAP_150" in ids

    nifty50 = next(u for u in universes if u["id"] == "NIFTY_50")
    assert nifty50["count"] >= 40
    assert nifty50["tier"] == 1


def test_run_portfolio_backtest_predefined_universe():
    """Executes a multi-asset backtest on predefined NIFTY 50 universe."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "PREDEFINED",
        "universe_name": "NIFTY_50",
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 1000000.0,
        "max_open_positions": 5,
        "sizing_model": "EQUAL_WEIGHT",
        "sizing_val": 20.0,
        "ranking_metric": "AUTO",
        "slippage_bps": 5.0,
        "parameters": {
            "short_window": 10,
            "long_window": 30,
        },
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert "backtest_id" in data
    assert data["strategy"] == "SMA_CROSS"
    assert len(data["symbols_tested"]) > 0

    # Validate KPI metrics
    metrics = data["metrics"]
    assert metrics["initial_capital"] == 1000000.0
    assert isinstance(metrics["cagr"], (int, float))
    assert isinstance(metrics["sharpe_ratio"], (int, float))
    assert isinstance(metrics["max_drawdown"], (int, float))
    assert isinstance(metrics["total_statutory_costs"], (int, float))

    # Validate curves and analytics
    assert len(data["equity_curve"]) > 0
    assert len(data["asset_contributions"]) > 0
    assert isinstance(data["monthly_returns"], dict)


def test_run_portfolio_backtest_custom_universe():
    """Executes a backtest on a user-defined custom stock basket."""
    payload = {
        "strategy": "RSI_REVERSION",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ"],
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-05-31",
        "initial_capital": 500000.0,
        "max_open_positions": 2,
        "sizing_model": "EQUAL_WEIGHT",
        "sizing_val": 50.0,
        "ranking_metric": "RSI_OVERSOLD",
        "stop_loss_pct": 3.0,
        "take_profit_pct": 6.0,
        "parameters": {
            "rsi_period": 14,
            "oversold": 35.0,
            "overbought": 65.0,
        },
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert len(data["symbols_tested"]) == 3
    assert set(data["symbols_tested"]) == {"NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ"}
    assert len(data["asset_contributions"]) == 3


def test_run_portfolio_backtest_inverse_atr_sizing():
    """Tests Volatility-Adjusted (Inverse ATR) sizing."""
    payload = {
        "strategy": "SUPERTREND",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ"],
        "start_date": "2023-01-01",
        "end_date": "2023-04-30",
        "initial_capital": 1000000.0,
        "max_open_positions": 2,
        "sizing_model": "INVERSE_ATR",
        "sizing_val": 1.5,  # 1.5% risk
        "parameters": {
            "period": 10,
            "multiplier": 3.0,
        },
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert len(data["equity_curve"]) > 0


def test_run_portfolio_backtest_fixed_amount_sizing():
    """Tests Fixed Amount per slot sizing."""
    payload = {
        "strategy": "MACD",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:LT-EQ", "NSE:ITC-EQ"],
        "start_date": "2023-01-01",
        "end_date": "2023-04-30",
        "initial_capital": 500000.0,
        "max_open_positions": 2,
        "sizing_model": "FIXED_AMOUNT",
        "sizing_val": 100000.0,  # ₹1L per slot
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
        },
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"


def test_run_portfolio_backtest_invalid_date_range():
    """Rejects requests where start_date is later than end_date."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:RELIANCE-EQ"],
        "start_date": "2023-12-31",
        "end_date": "2023-01-01",  # Invalid inverted range
        "initial_capital": 1000000.0,
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 400
    res = response.json()
    msg = res.get("error", {}).get("message") or res.get("detail", "")
    assert "start_date" in msg


def test_run_portfolio_backtest_empty_custom_symbols():
    """Rejects custom universe requests with empty symbols list."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "CUSTOM",
        "symbols": [],
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 1000000.0,
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 400


def test_run_portfolio_backtest_capital_too_low():
    """Rejects capital below ₹10,000 threshold."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:RELIANCE-EQ"],
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 5000.0,  # Less than min 10000.0
    }
    response = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert response.status_code == 422  # Pydantic validation error
