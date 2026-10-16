import pytest
from fastapi.testclient import TestClient

from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_paper_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_get_account_initial_state():
    response = client.get("/api/v1/paper-trading/account")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["account_id"] == "DEFAULT"
    assert data["balance"] == 1000000.0
    assert data["available_balance"] == 1000000.0
    assert data["margin_utilized"] == 0.0
    assert data["realized_pnl"] == 0.0
    assert data["net_portfolio_value"] == 1000000.0


def test_place_order_and_get_positions():
    # 1. Place Buy Order
    order_payload = {
        "symbol": "NSE:RELIANCE-EQ",
        "side": "BUY",
        "quantity": 50,
        "order_type": "MARKET",
        "trade_type": "DELIVERY",
        "price": 2500.0,
        "stop_loss": 2400.0,
        "take_profit": 2700.0
    }
    order_resp = client.post("/api/v1/paper-trading/orders", json=order_payload)
    assert order_resp.status_code == 200
    ord_data = order_resp.json()
    assert ord_data["success"] is True
    assert ord_data["data"]["symbol"] == "NSE:RELIANCE-EQ"
    assert ord_data["data"]["status"] == "FILLED"
    assert ord_data["data"]["fill_price"] == 2501.25  # 5 bps slippage

    # 2. Get Open Positions
    pos_resp = client.get("/api/v1/paper-trading/positions")
    assert pos_resp.status_code == 200
    pos_data = pos_resp.json()
    assert pos_data["success"] is True
    assert pos_data["count"] == 1
    pos = pos_data["data"][0]
    assert pos["symbol"] == "NSE:RELIANCE-EQ"
    assert pos["quantity"] == 50
    assert pos["average_price"] == 2501.25
    assert pos["side"] == "LONG"
    assert pos["trade_type"] == "DELIVERY"
    assert pos["stop_loss"] == 2400.0
    assert pos["take_profit"] == 2700.0


def test_place_order_validation_errors():
    # Invalid side
    res = client.post("/api/v1/paper-trading/orders", json={
        "symbol": "NSE:INFY-EQ",
        "side": "HOLD",
        "quantity": 10
    })
    assert res.status_code == 422  # Pydantic validation error

    # Invalid negative quantity
    res = client.post("/api/v1/paper-trading/orders", json={
        "symbol": "NSE:INFY-EQ",
        "side": "BUY",
        "quantity": -5
    })
    assert res.status_code == 422


def test_update_position_risk():
    # Open position
    client.post("/api/v1/paper-trading/orders", json={
        "symbol": "NSE:TCS-EQ",
        "side": "BUY",
        "quantity": 20,
        "price": 3500.0
    })

    # Update risk
    risk_payload = {
        "stop_loss": 3400.0,
        "take_profit": 3800.0,
        "trailing_sl_pct": 2.0
    }
    risk_resp = client.put("/api/v1/paper-trading/positions/NSE:TCS-EQ/risk", json=risk_payload)
    assert risk_resp.status_code == 200
    assert risk_resp.json()["success"] is True

    # Verify positions reflects updated risk
    pos_resp = client.get("/api/v1/paper-trading/positions")
    pos = pos_resp.json()["data"][0]
    assert pos["stop_loss"] == 3400.0
    assert pos["take_profit"] == 3800.0
    assert pos["trailing_sl_pct"] == 2.0


def test_close_position_endpoint():
    # Open position
    client.post("/api/v1/paper-trading/orders", json={
        "symbol": "NSE:SBIN-EQ",
        "side": "BUY",
        "quantity": 100,
        "price": 600.0
    })

    # Close position
    close_resp = client.delete("/api/v1/paper-trading/positions/NSE:SBIN-EQ/close?exit_price=620.0")
    assert close_resp.status_code == 200
    close_data = close_resp.json()
    assert close_data["success"] is True
    assert close_data["data"]["side"] == "SELL"
    assert close_data["data"]["quantity"] == 100

    # Verify position is gone
    pos_resp = client.get("/api/v1/paper-trading/positions")
    assert pos_resp.json()["count"] == 0

    # Closing nonexistent position should return 404
    nonexistent = client.delete("/api/v1/paper-trading/positions/NSE:NONEXISTENT/close")
    assert nonexistent.status_code == 404


def test_orders_and_trade_history_endpoints():
    # Execute a trade round-trip
    client.post("/api/v1/paper-trading/orders", json={
        "symbol": "NSE:RELIANCE-EQ",
        "side": "BUY",
        "quantity": 25,
        "price": 2500.0
    })
    client.delete("/api/v1/paper-trading/positions/NSE:RELIANCE-EQ/close?exit_price=2550.0")

    # Test GET /orders
    orders_resp = client.get("/api/v1/paper-trading/orders?limit=10")
    assert orders_resp.status_code == 200
    orders_data = orders_resp.json()
    assert orders_data["success"] is True
    assert orders_data["count"] == 2

    # Test GET /history
    history_resp = client.get("/api/v1/paper-trading/history?limit=10")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert history_data["success"] is True
    assert history_data["count"] == 2
    sell_trade = history_data["data"][0]  # Most recent is SELL
    assert sell_trade["side"] == "SELL"
    assert sell_trade["gross_pnl"] > 0.0
    assert sell_trade["total_charges"] > 0.0


def test_auto_strategy_endpoints():
    # Deploy strategy
    strat_payload = {
        "strategy_name": "MeanReversion_RSI",
        "symbol": "NSE:INFY-EQ",
        "timeframe": "5m",
        "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70},
        "trade_type": "INTRADAY",
        "allocated_capital": 200000.0
    }
    deploy_resp = client.post("/api/v1/paper-trading/deploy-strategy", json=strat_payload)
    assert deploy_resp.status_code == 200
    deploy_data = deploy_resp.json()
    assert deploy_data["success"] is True
    strategy_id = deploy_data["data"]["strategy_id"]

    # List strategies
    list_resp = client.get("/api/v1/paper-trading/auto-strategies")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["count"] == 1
    assert list_data["data"][0]["strategy_id"] == strategy_id
    assert list_data["data"][0]["strategy_name"] == "MeanReversion_RSI"

    # Delete strategy
    del_resp = client.delete(f"/api/v1/paper-trading/auto-strategies/{strategy_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify list is empty
    list_after = client.get("/api/v1/paper-trading/auto-strategies")
    assert list_after.json()["count"] == 0


def test_reset_account_endpoint():
    # Execute a trade
    client.post("/api/v1/paper-trading/orders", json={
        "symbol": "NSE:RELIANCE-EQ",
        "side": "BUY",
        "quantity": 10,
        "price": 2500.0
    })

    # Reset account
    reset_resp = client.post("/api/v1/paper-trading/account/reset?initial_capital=1500000.0")
    assert reset_resp.status_code == 200
    reset_data = reset_resp.json()
    assert reset_data["success"] is True
    assert reset_data["data"]["balance"] == 1500000.0
    assert reset_data["data"]["realized_pnl"] == 0.0

    # Verify positions and orders cleared
    pos_resp = client.get("/api/v1/paper-trading/positions")
    assert pos_resp.json()["count"] == 0
    ord_resp = client.get("/api/v1/paper-trading/orders")
    assert ord_resp.json()["count"] == 0
