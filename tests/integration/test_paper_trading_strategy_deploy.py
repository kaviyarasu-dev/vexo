import pytest
import pandas as pd
from fastapi.testclient import TestClient

from main import app
from db.connection import get_db, close_db
from db.migrations import init_db
from services.paper_trading_service import PaperTradingService

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_strategy_deploy.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_deploy_strategy_endpoint():
    """Verify deploying an RSI strategy registers row in paper_auto_strategies and appears in auto-strategies endpoint."""
    payload = {
        "strategy_name": "RSI_REVERSION",
        "symbol": "NSE:RELIANCE-EQ",
        "timeframe": "1D",
        "parameters": {
            "rsi_period": 14,
            "oversold": 30.0,
            "overbought": 70.0
        },
        "trade_type": "DELIVERY",
        "allocated_capital": 100000.0
    }

    # 1. POST deploy
    response = client.post("/api/v1/paper-trading/deploy-strategy", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["strategy_name"] == "RSI_REVERSION"
    assert data["symbol"] == "NSE:RELIANCE-EQ"
    assert data["timeframe"] == "1D"
    assert data["allocated_capital"] == 100000.0
    assert data["status"] == "ACTIVE"
    strat_id = data["strategy_id"]

    # 2. GET list
    list_resp = client.get("/api/v1/paper-trading/auto-strategies")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["success"] is True
    assert list_data["count"] == 1
    item = list_data["data"][0]
    assert item["strategy_id"] == strat_id
    assert item["strategy_name"] == "RSI_REVERSION"
    assert item["symbol"] == "NSE:RELIANCE-EQ"
    assert item["status"] == "ACTIVE"


def test_deploy_duplicate_symbol_updates_existing_allocation():
    """Verify deploying for same symbol updates existing allocation rather than failing duplicate key error."""
    # First deployment
    first_payload = {
        "strategy_name": "SMA_CROSS",
        "symbol": "NSE:INFY-EQ",
        "timeframe": "1D",
        "parameters": {"short_window": 10, "long_window": 30},
        "allocated_capital": 100000.0
    }
    r1 = client.post("/api/v1/paper-trading/deploy-strategy", json=first_payload)
    assert r1.status_code == 200
    id1 = r1.json()["data"]["strategy_id"]

    # Second deployment for same symbol with updated capital and parameters
    second_payload = {
        "strategy_name": "RSI_REVERSION",
        "symbol": "NSE:INFY-EQ",
        "timeframe": "1D",
        "parameters": {"rsi_period": 21, "oversold": 25.0, "overbought": 75.0},
        "allocated_capital": 250000.0
    }
    r2 = client.post("/api/v1/paper-trading/deploy-strategy", json=second_payload)
    assert r2.status_code == 200
    res2 = r2.json()["data"]
    assert res2["strategy_id"] == id1
    assert res2["strategy_name"] == "RSI_REVERSION"
    assert res2["allocated_capital"] == 250000.0

    # Ensure list has only 1 strategy
    list_resp = client.get("/api/v1/paper-trading/auto-strategies")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1
    assert list_resp.json()["data"][0]["allocated_capital"] == 250000.0


def test_stop_auto_strategy():
    """Verify stopping strategy changes status to STOPPED."""
    payload = {
        "strategy_name": "SUPERTREND",
        "symbol": "NSE:TCS-EQ",
        "timeframe": "1D",
        "parameters": {"period": 10, "multiplier": 3.0},
        "allocated_capital": 50000.0
    }
    r = client.post("/api/v1/paper-trading/deploy-strategy", json=payload)
    assert r.status_code == 200
    strat_id = r.json()["data"]["strategy_id"]

    # 1. Stop strategy via POST /stop
    stop_resp = client.post(f"/api/v1/paper-trading/auto-strategies/{strat_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["success"] is True

    # 2. Check list
    list_resp = client.get("/api/v1/paper-trading/auto-strategies")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1
    assert list_resp.json()["data"][0]["status"] == "STOPPED"

    # 3. Filter by ACTIVE
    active_resp = client.get("/api/v1/paper-trading/auto-strategies?status=ACTIVE")
    assert active_resp.status_code == 200
    assert active_resp.json()["count"] == 0

    # 4. Filter by STOPPED
    stopped_resp = client.get("/api/v1/paper-trading/auto-strategies?status=STOPPED")
    assert stopped_resp.status_code == 200
    assert stopped_resp.json()["count"] == 1


def test_evaluate_auto_strategies_buy_and_sell_execution(setup_test_db):
    """Verify candle evaluation executes simulated buy order on signal and square-off on sell signal."""
    service = PaperTradingService(setup_test_db)

    # Deploy SMA_CROSS strategy
    strat = service.register_auto_strategy(
        strategy_name="SMA_CROSS",
        symbol="NSE:RELIANCE-EQ",
        timeframe="1D",
        parameters={"short_window": 3, "long_window": 5},
        allocated_capital=100000.0
    )
    assert strat.status == "ACTIVE"

    # Synthetic candles where short SMA crosses above long SMA on the last bar
    # 5 candles: close prices = [100, 100, 100, 100, 120]
    # On bar 3 (idx 3): short(3)=100, long(5)=100
    # On bar 4 (idx 4): short(3)=(100+100+120)/3 = 106.67 > long(5)=(100+100+100+100+120)/5 = 104 -> signal_buy = True!
    dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"]
    buy_df = pd.DataFrame({
        "date": dates,
        "symbol": ["NSE:RELIANCE-EQ"] * 5,
        "open": [100.0, 100.0, 100.0, 100.0, 115.0],
        "high": [105.0, 105.0, 105.0, 105.0, 122.0],
        "low": [95.0, 95.0, 95.0, 95.0, 110.0],
        "close": [100.0, 100.0, 100.0, 100.0, 120.0],
        "volume": [1000, 1000, 1000, 1000, 5000]
    })

    # Evaluate candles -> triggers BUY
    executions = service.evaluate_auto_strategies_on_candle(buy_df, symbol="NSE:RELIANCE-EQ")
    assert len(executions) == 1
    assert executions[0]["action"] == "BUY"
    assert executions[0]["symbol"] == "NSE:RELIANCE-EQ"
    assert executions[0]["price"] == 120.0

    # Verify position is now OPEN
    pos = service.get_position("NSE:RELIANCE-EQ")
    assert pos is not None
    assert pos.quantity > 0
    assert pos.side == "LONG"

    # Subsequent candles where fast SMA crosses below slow SMA -> triggers SELL
    # Add bars dropping sharply to 70
    sell_df = pd.DataFrame({
        "date": dates + ["2026-01-06", "2026-01-07"],
        "symbol": ["NSE:RELIANCE-EQ"] * 7,
        "open": [100.0, 100.0, 100.0, 100.0, 115.0, 110.0, 80.0],
        "high": [105.0, 105.0, 105.0, 105.0, 122.0, 112.0, 82.0],
        "low": [95.0, 95.0, 95.0, 95.0, 110.0, 75.0, 68.0],
        "close": [100.0, 100.0, 100.0, 100.0, 120.0, 85.0, 70.0],
        "volume": [1000, 1000, 1000, 1000, 5000, 6000, 7000]
    })

    sell_execs = service.evaluate_auto_strategies_on_candle(sell_df, symbol="NSE:RELIANCE-EQ")
    assert len(sell_execs) == 1
    assert sell_execs[0]["action"] == "SELL"
    assert sell_execs[0]["price"] == 70.0

    # Position should now be CLOSED
    pos_after = service.get_position("NSE:RELIANCE-EQ")
    assert pos_after is None

    # Trade should be recorded in trade history
    history = service.get_history()
    assert len(history) >= 2  # Buy fill and Sell fill


def test_stopped_strategy_ceases_trade_executions(setup_test_db):
    """Verify stopping strategy halts automated signal evaluation and trade placements."""
    service = PaperTradingService(setup_test_db)

    strat = service.register_auto_strategy(
        strategy_name="SMA_CROSS",
        symbol="NSE:HDFCBANK-EQ",
        timeframe="1D",
        parameters={"short_window": 3, "long_window": 5},
        allocated_capital=50000.0
    )
    # Stop strategy
    service.stop_auto_strategy(strat.strategy_id)

    # Bullish candle crossover
    candle_df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
        "symbol": ["NSE:HDFCBANK-EQ"] * 5,
        "open": [100.0, 100.0, 100.0, 100.0, 115.0],
        "high": [105.0, 105.0, 105.0, 105.0, 122.0],
        "low": [95.0, 95.0, 95.0, 95.0, 110.0],
        "close": [100.0, 100.0, 100.0, 100.0, 120.0],
        "volume": [1000, 1000, 1000, 1000, 5000]
    })

    execs = service.evaluate_auto_strategies_on_candle(candle_df, symbol="NSE:HDFCBANK-EQ")
    assert len(execs) == 0  # No trades placed because strategy is STOPPED
    pos = service.get_position("NSE:HDFCBANK-EQ")
    assert pos is None


def test_evaluate_auto_strategies_api_endpoint():
    """Verify POST /api/v1/paper-trading/auto-strategies/evaluate returns valid JSON."""
    res = client.post("/api/v1/paper-trading/auto-strategies/evaluate")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "executions" in data
    assert "count" in data


def test_static_asset_backtest_deploy_and_ui():
    """Verify backtest_paper_deploy.js and BacktestUI deploy buttons are properly served."""
    r_deploy = client.get("/static/js/backtest_paper_deploy.js")
    assert r_deploy.status_code == 200
    assert "class BacktestPaperDeployHelper" in r_deploy.text
    assert "deployFromConfig" in r_deploy.text

    r_bt_ui = client.get("/static/js/backtest_ui.js")
    assert r_bt_ui.status_code == 200
    assert "btn-deploy-paper-strategy" in r_bt_ui.text
    assert "deployToPaperTrading" in r_bt_ui.text
