"""
Integration tests for Options Strategy Net Greeks and Payoff Simulation API.
Tests POST /api/v1/options/strategy/greeks and POST /api/v1/options/strategy/payoff.
Validates multi-leg strategy evaluation, lot-size scaling, breakevens, and curve schemas.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Sets up an isolated DuckDB instance for integration test execution."""
    db_path = str(tmp_path / "test_options_payoff_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_api_strategy_greeks_bull_call():
    """Verifies Strategy Net Greeks aggregation via POST /strategy/greeks."""
    payload = {
        "symbol": "NIFTY",
        "spot": 25050.0,
        "t_days": 4.0,
        "r": 0.065,
        "legs": [
            {"strike": 25000.0, "option_type": "CE", "position": "LONG", "premium": 140.0, "quantity": 1, "iv": 0.14},
            {"strike": 25200.0, "option_type": "CE", "position": "SHORT", "premium": 55.0, "quantity": 1, "iv": 0.135}
        ]
    }

    response = client.post("/api/v1/options/strategy/greeks", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    data = res["data"]
    assert data["symbol"] == "NIFTY"
    assert data["lot_size"] == 25
    assert data["net_delta"] > 0
    assert data["delta_inr"] > 0
    assert data["net_premium"] == -85.0
    assert data["total_cost_inr"] == -2125.0


def test_api_strategy_greeks_iron_condor():
    """Verifies 4-leg Iron Condor credit strategy on BANKNIFTY."""
    payload = {
        "symbol": "BANKNIFTY",
        "spot": 51200.0,
        "t_days": 4.0,
        "r": 0.065,
        "legs": [
            {"strike": 50800.0, "option_type": "PE", "position": "SHORT", "premium": 110.0, "quantity": 1, "iv": 0.16},
            {"strike": 50400.0, "option_type": "PE", "position": "LONG", "premium": 40.0, "quantity": 1, "iv": 0.17},
            {"strike": 51600.0, "option_type": "CE", "position": "SHORT", "premium": 105.0, "quantity": 1, "iv": 0.15},
            {"strike": 52000.0, "option_type": "CE", "position": "LONG", "premium": 35.0, "quantity": 1, "iv": 0.155}
        ]
    }

    response = client.post("/api/v1/options/strategy/greeks", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    data = res["data"]
    assert data["lot_size"] == 15
    assert data["net_premium"] == 140.0
    assert data["total_cost_inr"] == 2100.0
    assert data["theta_inr"] > 0  # Net credit strategy earns time decay


def test_api_simulate_payoff_bull_call():
    """Verifies dual curve payoff simulation via POST /strategy/payoff."""
    payload = {
        "symbol": "NIFTY",
        "spot": 25000.0,
        "t_days_remaining": 4.0,
        "target_days": 2.0,
        "iv_shock_pct": 0.0,
        "r": 0.065,
        "legs": [
            {"strike": 25000.0, "option_type": "CE", "position": "LONG", "premium": 100.0, "quantity": 1, "iv": 0.14},
            {"strike": 25200.0, "option_type": "CE", "position": "SHORT", "premium": 30.0, "quantity": 1, "iv": 0.135}
        ]
    }

    response = client.post("/api/v1/options/strategy/payoff", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    data = res["data"]
    assert data["symbol"] == "NIFTY"
    assert data["lot_size"] == 25
    assert data["net_debit_credit_inr"] == -1750.0

    # Max Profit: 3250, Max Loss: -1750
    assert abs(data["max_profit"] - 3250.0) < 10.0
    assert abs(data["max_loss"] - (-1750.0)) < 10.0
    assert len(data["breakevens"]) == 1
    assert abs(data["breakevens"][0] - 25070.0) < 5.0

    # Curve checks
    exp_curve = data["expiration_curve"]
    target_curve = data["target_date_curve"]
    assert len(exp_curve) == 45
    assert len(target_curve) == 45

    for pt in exp_curve:
        assert "spot" in pt
        assert "pnl" in pt


def test_api_simulate_payoff_straddle_equity():
    """Verifies payoff simulation for Long Straddle on equity underlying (RELIANCE)."""
    payload = {
        "symbol": "RELIANCE",
        "spot": 2865.0,
        "t_days_remaining": 5.0,
        "target_days": 2.5,
        "iv_shock_pct": 10.0,
        "r": 0.065,
        "legs": [
            {"strike": 2860.0, "option_type": "CE", "position": "LONG", "premium": 42.0, "quantity": 1, "iv": 0.18},
            {"strike": 2860.0, "option_type": "PE", "position": "LONG", "premium": 39.0, "quantity": 1, "iv": 0.18}
        ]
    }

    response = client.post("/api/v1/options/strategy/payoff", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    data = res["data"]
    assert data["symbol"] == "RELIANCE"
    assert data["lot_size"] == 250  # Reliance lot size

    # Long straddle has 2 breakeven points (upper and lower)
    assert len(data["breakevens"]) == 2
    assert data["breakevens"][0] < 2860.0 < data["breakevens"][1]
