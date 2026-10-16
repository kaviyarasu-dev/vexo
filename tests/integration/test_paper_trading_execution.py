import pytest
from db.connection import get_db
from db.migrations import init_db
from services.paper_trading_service import PaperTradingService

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test_paper.db")
    db = get_db(db_path)
    init_db(db_path, manager=db)
    yield db
    db.close()

def test_paper_trading_execution(test_db):
    service = PaperTradingService(test_db)
    
    # Initial balance should be 1000000
    cursor = test_db.get_read_cursor()
    bal = cursor.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()[0]
    cursor.close()
    assert bal == 1000000.0
    
    # Execute buy
    # Price = 2500. Slippage = 5bps -> 2501.25
    # Value = 250125.
    # Cost model will compute fees on 250125.
    # Brokerage = 20, STT = 250.13, Stamp = 37.52, Exchange = 7.43, SEBI = 0.25, GST = 4.98
    # Total ~ 320 (excluding slippage which is baked in)
    fill = service.execute_order("NSE:RELIANCE-EQ", 100, "BUY", "MARKET", 2500.0)
    
    assert fill.fill_price == 2501.25
    assert fill.total_charges > 300
    
    cursor = test_db.get_read_cursor()
    new_bal = cursor.execute("SELECT balance FROM paper_account WHERE account_id = 'DEFAULT'").fetchone()[0]
    pos = cursor.execute("SELECT quantity, average_price FROM paper_positions WHERE symbol = 'NSE:RELIANCE-EQ'").fetchone()
    cursor.close()
    
    assert new_bal < 1000000.0 - 250125.0
    assert pos is not None
    assert pos[0] == 100
    assert pos[1] == 2501.25

def test_paper_trading_sell_execution(test_db):
    service = PaperTradingService(test_db)
    
    # Add fake position
    service.execute_order("NSE:RELIANCE-EQ", 100, "BUY", "MARKET", 2500.0)
    
    fill = service.execute_order("NSE:RELIANCE-EQ", 100, "SELL", "MARKET", 2600.0)
    # Price 2600. Sell -> slippage down -> 2598.70
    assert fill.fill_price == 2600.0 * (1 - 0.0005)
    
    cursor = test_db.get_read_cursor()
    pos = cursor.execute("SELECT * FROM paper_positions WHERE symbol = 'NSE:RELIANCE-EQ'").fetchone()
    cursor.close()
    
    assert pos is None # Position closed
