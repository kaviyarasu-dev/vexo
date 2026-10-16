"""
Integration Tests for Strategy Parameter Optimization REST API Endpoints.
Tests GET /api/v1/backtest/optimize/presets and POST /api/v1/backtest/optimize.
Validates curated strategy presets, grid execution, 400 combination cap, 
3x3 stability scoring, walk-forward validation, and Pydantic error handling.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_optimization_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


# ============================================================================
# 1. Presets Endpoint Tests
# ============================================================================

def test_get_optimization_presets():
    """Verifies retrieval of curated parameter presets for all 5 quant strategies."""
    response = client.get("/api/v1/backtest/optimize/presets")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    presets = data["presets"]
    assert len(presets) == 5

    strategies = [p["strategy"] for p in presets]
    assert "SMA_CROSS" in strategies
    assert "RSI_REVERSION" in strategies
    assert "BOLLINGER_BANDS" in strategies
    assert "SUPERTREND" in strategies
    assert "MACD" in strategies

    # Check SMA_CROSS preset structure
    sma = next(p for p in presets if p["strategy"] == "SMA_CROSS")
    assert "short_window" == sma["param1"]["name"]
    assert sma["param1"]["min_val"] == 5.0
    assert sma["param1"]["max_val"] == 30.0
    assert sma["param1"]["step"] == 5.0
    assert "long_window" == sma["param2"]["name"]
    assert sma["param2"]["min_val"] == 30.0
    assert sma["param2"]["max_val"] == 100.0
    assert sma["param2"]["step"] == 10.0


# ============================================================================
# 2. Optimization Endpoint Valid Execution Tests
# ============================================================================

def test_run_parameter_optimization_sma_cross():
    """Executes a 3x3 grid optimization for SMA Crossover with walk-forward validation."""
    payload = {
        "strategy": "SMA_CROSS",
        "symbol": "NSE:RELIANCE-EQ",
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 1000000.0,
        "slippage_bps": 5.0,
        "trade_type": "DELIVERY",
        "param1": {
            "name": "short_window",
            "min_val": 10.0,
            "max_val": 20.0,
            "step": 5.0
        },
        "param2": {
            "name": "long_window",
            "min_val": 30.0,
            "max_val": 40.0,
            "step": 5.0
        },
        "walk_forward_split_pct": 70.0,
        "target_metric": "sharpe_ratio"
    }

    response = client.post("/api/v1/backtest/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["strategy"] == "SMA_CROSS"
    assert data["symbol"] == "NSE:RELIANCE-EQ"
    assert data["param1_name"] == "short_window"
    assert data["param2_name"] == "long_window"
    assert data["param1_ticks"] == [10.0, 15.0, 20.0]
    assert data["param2_ticks"] == [30.0, 35.0, 40.0]
    assert data["total_combinations"] == 9
    assert data["execution_time_ms"] > 0

    # Best params
    assert "short_window" in data["best_params"]
    assert "long_window" in data["best_params"]

    # Stability report
    stability = data["stability"]
    assert stability["classification"] in ("ROBUST_PLATEAU", "MODERATE_SENSITIVITY", "FRAGILE_CLIFF")
    assert 0.0 <= stability["stability_score"] <= 1.0
    assert isinstance(stability["cliff_drop_pct"], (int, float))

    # Walk-forward report
    wf = data["walk_forward"]
    assert wf["is_split_pct"] == 70.0
    assert isinstance(wf["walk_forward_efficiency"], (int, float))
    assert wf["split_date"] != ""

    # Heatmap matrix
    matrix = data["matrix"]
    assert len(matrix) == 9
    for cell in matrix:
        assert "param1_val" in cell
        assert "param2_val" in cell
        assert "sharpe_ratio" in cell
        assert "net_pnl" in cell
        assert "net_pnl_pct" in cell
        assert "max_drawdown_pct" in cell
        assert "win_rate" in cell
        assert "total_trades" in cell
        assert "profit_factor" in cell


def test_run_parameter_optimization_rsi_reversion():
    """Executes a 2x2 grid optimization for RSI Reversal."""
    payload = {
        "strategy": "RSI_REVERSION",
        "symbol": "NSE:TCS-EQ",
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 500000.0,
        "slippage_bps": 5.0,
        "trade_type": "DELIVERY",
        "param1": {
            "name": "rsi_period",
            "min_val": 10.0,
            "max_val": 14.0,
            "step": 4.0
        },
        "param2": {
            "name": "oversold",
            "min_val": 25.0,
            "max_val": 30.0,
            "step": 5.0
        },
        "walk_forward_split_pct": 60.0,
        "target_metric": "net_pnl"
    }

    response = client.post("/api/v1/backtest/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["strategy"] == "RSI_REVERSION"
    assert data["total_combinations"] == 4
    assert len(data["matrix"]) == 4


# ============================================================================
# 3. Maximum Combination Cap Rejection Tests (> 400)
# ============================================================================

def test_optimization_cap_rejection_over_400():
    """Verifies HTTP 400 when parameter space generates > 400 combinations."""
    # 25 * 25 = 625 combinations (> 400)
    payload = {
        "strategy": "SMA_CROSS",
        "symbol": "NSE:INFY-EQ",
        "param1": {
            "name": "short_window",
            "min_val": 1.0,
            "max_val": 25.0,
            "step": 1.0
        },
        "param2": {
            "name": "long_window",
            "min_val": 50.0,
            "max_val": 74.0,
            "step": 1.0
        }
    }

    response = client.post("/api/v1/backtest/optimize", json=payload)
    assert response.status_code == 400
    res_json = response.json()
    msg = res_json.get("error", {}).get("message") or res_json.get("detail", "")
    assert "exceeds the institutional cap of 400" in msg


# ============================================================================
# 4. Pydantic Payload Validation Error Tests
# ============================================================================

def test_optimization_invalid_step_validation():
    """Verifies HTTP 422 when step is non-positive."""
    payload = {
        "strategy": "SMA_CROSS",
        "symbol": "NSE:INFY-EQ",
        "param1": {
            "name": "short_window",
            "min_val": 10.0,
            "max_val": 20.0,
            "step": 0.0  # Invalid step <= 0
        },
        "param2": {
            "name": "long_window",
            "min_val": 30.0,
            "max_val": 40.0,
            "step": 5.0
        }
    }

    response = client.post("/api/v1/backtest/optimize", json=payload)
    assert response.status_code == 422


def test_optimization_invalid_split_percentage():
    """Verifies HTTP 422 when walk_forward_split_pct is outside [10, 90]."""
    payload = {
        "strategy": "SMA_CROSS",
        "symbol": "NSE:INFY-EQ",
        "walk_forward_split_pct": 98.0,  # Invalid (> 90.0)
        "param1": {
            "name": "short_window",
            "min_val": 10.0,
            "max_val": 20.0,
            "step": 5.0
        },
        "param2": {
            "name": "long_window",
            "min_val": 30.0,
            "max_val": 40.0,
            "step": 5.0
        }
    }

    response = client.post("/api/v1/backtest/optimize", json=payload)
    assert response.status_code == 422
