import pytest
import os
from db.connection import get_db
from db.migrations import init_db
from services.journal_service import JournalService

@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test_journal.db")
    db = get_db(db_path)
    init_db(db_path, manager=db)
    yield db
    db.close()

def test_tradebook_import(test_db):
    service = JournalService(test_db)
    
    csv_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_fyers_tradebook.csv")
    with open(csv_path, "r") as f:
        content = f.read()
        
    count = service.import_tradebook_csv(content)
    assert count == 2
    
    trades = service.list_trades()
    assert len(trades) == 2
    
    # 1 Long Trade
    t1 = next(t for t in trades if t.symbol == "NSE:RELIANCE-EQ")
    assert t1.direction == "LONG"
    assert t1.pnl_net == 10000.0 # 100 qty * 100 gain
    
    # 1 Short Trade
    t2 = next(t for t in trades if t.symbol == "NSE:TCS-EQ")
    assert t2.direction == "SHORT"
    assert t2.pnl_net == 5000.0 # 50 qty * 100 gain

def test_malformed_csv(test_db):
    service = JournalService(test_db)
    with pytest.raises(ValueError, match="CSV missing required columns"):
        service.import_tradebook_csv("symb,date,pr\nRELIANCE,2023-10-10,2500")
