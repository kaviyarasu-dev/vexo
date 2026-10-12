import pytest
from db.connection import get_db
from db.migrations import init_db
from services.paper_trading_service import PaperTradingService
from services.backtest.cost_model import IndianEquityCostModel


@pytest.fixture
def unit_db(tmp_path):
    db_path = str(tmp_path / "test_paper_unit.db")
    db = get_db(db_path)
    init_db(db_path, manager=db)
    yield db
    db.close()


def test_tables_and_initial_account_state(unit_db):
    service = PaperTradingService(unit_db)
    
    cursor = unit_db.get_read_cursor()
    tables = [r[0] for r in cursor.execute("SHOW TABLES").fetchall()]
    assert "paper_account" in tables
    assert "paper_positions" in tables
    assert "paper_orders" in tables
    assert "paper_trades" in tables
    assert "paper_auto_strategies" in tables
    
    acc = cursor.execute("SELECT balance, initial_balance, realized_pnl FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()
    cursor.close()
    
    assert acc is not None
    assert acc[0] == 1000000.0
    assert acc[1] == 1000000.0
    assert acc[2] == 0.0


def test_place_order_buy_delivery_cost_and_slippage(unit_db):
    service = PaperTradingService(unit_db)
    
    # 5 bps slippage on 2500 -> 2501.25
    order = service.place_order(
        symbol="NSE:RELIANCE-EQ",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        trade_type="DELIVERY",
        price=2500.0,
        stop_loss=2400.0,
        take_profit=2700.0
    )
    
    assert order.status == "FILLED"
    assert order.fill_price == 2501.25
    assert order.total_charges > 300.0
    
    # Check DuckDB persistence
    cursor = unit_db.get_read_cursor()
    pos = cursor.execute("SELECT quantity, average_price, side, trade_type, stop_loss, take_profit FROM paper_positions WHERE symbol = 'NSE:RELIANCE-EQ'").fetchone()
    ord_row = cursor.execute("SELECT order_id, status, trade_type FROM paper_orders WHERE order_id = ?", [order.order_id]).fetchone()
    trade_row = cursor.execute("SELECT stt, brokerage, total_charges FROM paper_trades WHERE order_id = ?", [order.order_id]).fetchone()
    bal = cursor.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()[0]
    cursor.close()
    
    assert pos is not None
    assert pos[0] == 100
    assert pos[1] == 2501.25
    assert pos[2] == "LONG"
    assert pos[3] == "DELIVERY"
    assert pos[4] == 2400.0
    assert pos[5] == 2700.0
    
    assert ord_row is not None
    assert ord_row[1] == "FILLED"
    
    assert trade_row is not None
    assert trade_row[0] > 0.0  # STT charged on Indian equity delivery
    assert trade_row[2] > 0.0  # Total charges > 0
    
    # Balance should be deducted by (trade_val + total_charges)
    expected_bal = 1000000.0 - (2501.25 * 100 + trade_row[2])
    assert pytest.approx(bal, 0.01) == expected_bal


def test_place_order_buy_intraday_margin_leverage(unit_db):
    service = PaperTradingService(unit_db)
    
    order = service.place_order(
        symbol="NSE:TCS-EQ",
        side="BUY",
        quantity=50,
        order_type="MARKET",
        trade_type="INTRADAY",
        price=3500.0
    )
    
    # TCS @ 3500 -> 5 bps slippage = 3501.75
    # Trade value = 50 * 3501.75 = 175,087.50
    # Intraday 5x margin required = 175,087.50 / 5.0 = 35,017.50
    cursor = unit_db.get_read_cursor()
    bal = cursor.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()[0]
    trade_row = cursor.execute("SELECT total_charges FROM paper_trades WHERE order_id = ?", [order.order_id]).fetchone()
    cursor.close()
    
    expected_deduction = (3501.75 * 50 / 5.0) + trade_row[0]
    expected_bal = 1000000.0 - expected_deduction
    assert pytest.approx(bal, 0.01) == expected_bal


def test_place_order_insufficient_funds(unit_db):
    service = PaperTradingService(unit_db)
    
    with pytest.raises(ValueError, match="Insufficient virtual balance"):
        service.place_order(
            symbol="NSE:RELIANCE-EQ",
            side="BUY",
            quantity=10000,  # ₹2.5 crore value vs ₹10 lakh balance
            order_type="MARKET",
            trade_type="DELIVERY",
            price=2500.0
        )


def test_close_position_realizes_pnl(unit_db):
    service = PaperTradingService(unit_db)
    
    # 1. Buy 100 shares @ 2500 (Fill 2501.25)
    service.place_order("NSE:RELIANCE-EQ", "BUY", 100, price=2500.0, trade_type="DELIVERY")
    
    # 2. Close position at 2600 (Fill 2598.70)
    close_order = service.close_position("NSE:RELIANCE-EQ", exit_price=2600.0)
    assert close_order.side == "SELL"
    assert close_order.quantity == 100
    assert close_order.fill_price == 2598.70
    
    # Position should be closed
    cursor = unit_db.get_read_cursor()
    pos = cursor.execute("SELECT * FROM paper_positions WHERE symbol = 'NSE:RELIANCE-EQ'").fetchone()
    acc = cursor.execute("SELECT balance, realized_pnl FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()
    trades = cursor.execute("SELECT gross_pnl, net_pnl FROM paper_trades WHERE symbol = 'NSE:RELIANCE-EQ' AND side = 'SELL'").fetchone()
    cursor.close()
    
    assert pos is None
    gross_pnl = (2598.70 - 2501.25) * 100
    assert pytest.approx(trades[0], 0.01) == gross_pnl
    assert trades[1] < gross_pnl  # net_pnl deducted taxes
    assert pytest.approx(acc[1], 0.01) == trades[1]  # realized_pnl matches


def test_partial_position_close(unit_db):
    service = PaperTradingService(unit_db)
    
    # Buy 100 shares @ 2500
    service.place_order("NSE:RELIANCE-EQ", "BUY", 100, price=2500.0)
    
    # Sell 40 shares @ 2600
    service.place_order("NSE:RELIANCE-EQ", "SELL", 40, price=2600.0)
    
    cursor = unit_db.get_read_cursor()
    pos = cursor.execute("SELECT quantity, average_price FROM paper_positions WHERE symbol = 'NSE:RELIANCE-EQ'").fetchone()
    cursor.close()
    
    assert pos is not None
    assert pos[0] == 60
    assert pos[1] == 2501.25


def test_short_position_lifecycle(unit_db):
    service = PaperTradingService(unit_db)
    
    # 1. Short sell 50 shares @ 2000 (Fill 1999.00)
    short_order = service.place_order("NSE:INFY-EQ", "SELL", 50, price=2000.0, trade_type="INTRADAY")
    assert short_order.status == "FILLED"
    
    cursor = unit_db.get_read_cursor()
    pos = cursor.execute("SELECT quantity, average_price, side FROM paper_positions WHERE symbol = 'NSE:INFY-EQ'").fetchone()
    cursor.close()
    assert pos is not None
    assert pos[0] == 50
    assert pos[1] == 1999.00
    assert pos[2] == "SHORT"
    
    # 2. Buy back to cover @ 1900 (Fill 1900.95)
    cover_order = service.close_position("NSE:INFY-EQ", exit_price=1900.0)
    assert cover_order.side == "BUY"
    
    cursor = unit_db.get_read_cursor()
    pos_after = cursor.execute("SELECT * FROM paper_positions WHERE symbol = 'NSE:INFY-EQ'").fetchone()
    trades = cursor.execute("SELECT gross_pnl, net_pnl FROM paper_trades WHERE symbol = 'NSE:INFY-EQ' AND side = 'BUY'").fetchone()
    cursor.close()
    
    assert pos_after is None
    # Short profit = (entry - exit) * qty = (1999.00 - 1900.95) * 50 = ~4902.50
    assert trades[0] > 4800.0


def test_update_position_risk_parameters(unit_db):
    service = PaperTradingService(unit_db)
    service.place_order("NSE:RELIANCE-EQ", "BUY", 50, price=2500.0)
    
    updated = service.update_position_risk(
        symbol="NSE:RELIANCE-EQ",
        stop_loss=2420.0,
        take_profit=2750.0,
        trailing_sl_pct=1.5
    )
    assert updated is True
    
    cursor = unit_db.get_read_cursor()
    pos = cursor.execute("SELECT stop_loss, take_profit, trailing_sl_pct FROM paper_positions WHERE symbol = 'NSE:RELIANCE-EQ'").fetchone()
    cursor.close()
    
    assert pos[0] == 2420.0
    assert pos[1] == 2750.0
    assert pos[2] == 1.5


def test_get_positions_with_mtm(unit_db):
    service = PaperTradingService(unit_db)
    service.place_order("NSE:RELIANCE-EQ", "BUY", 100, price=2500.0)
    
    # MTM valuation with quote at 2650.0
    positions = service.get_positions_with_mtm({"NSE:RELIANCE-EQ": 2650.0})
    assert len(positions) == 1
    p = positions[0]
    assert p.symbol == "NSE:RELIANCE-EQ"
    assert p.quantity == 100
    assert p.average_price == 2501.25
    assert p.current_price == 2650.0
    expected_unrealized = (2650.0 - 2501.25) * 100
    assert pytest.approx(p.unrealized_pnl, 0.01) == expected_unrealized
    assert p.unrealized_pnl_pct > 5.0


def test_get_account_summary(unit_db):
    service = PaperTradingService(unit_db)
    summary = service.get_account_summary()
    assert summary.balance == 1000000.0
    assert summary.margin_utilized == 0.0
    assert summary.available_balance == 1000000.0
    assert summary.net_portfolio_value == 1000000.0
    assert summary.realized_pnl == 0.0


def test_reset_account(unit_db):
    service = PaperTradingService(unit_db)
    service.place_order("NSE:RELIANCE-EQ", "BUY", 50, price=2500.0)
    service.register_auto_strategy("EMA_Cross", "NSE:RELIANCE-EQ")
    
    # Account has positions and strategies
    assert len(service.get_positions_with_mtm()) == 1
    assert len(service.list_auto_strategies()) == 1
    
    # Reset
    res = service.reset_account(initial_capital=750000.0)
    assert res.balance == 750000.0
    assert res.net_portfolio_value == 750000.0
    assert res.realized_pnl == 0.0
    assert len(service.get_positions_with_mtm()) == 0
    assert len(service.list_auto_strategies()) == 0


def test_auto_strategy_registration_and_lifecycle(unit_db):
    service = PaperTradingService(unit_db)
    strat = service.register_auto_strategy(
        strategy_name="MACD_Bullish_Breakout",
        symbol="NSE:HDFCBANK-EQ",
        timeframe="15m",
        parameters={"fast": 12, "slow": 26, "signal": 9},
        trade_type="INTRADAY",
        allocated_capital=150000.0
    )
    
    assert strat.strategy_name == "MACD_Bullish_Breakout"
    assert strat.symbol == "NSE:HDFCBANK-EQ"
    assert strat.status == "ACTIVE"
    assert strat.parameters["fast"] == 12
    
    # List
    strategies = service.list_auto_strategies()
    assert len(strategies) == 1
    assert strategies[0].strategy_id == strat.strategy_id
    
    # Delete
    deleted = service.delete_auto_strategy(strat.strategy_id)
    assert deleted is True
    assert len(service.list_auto_strategies()) == 0
