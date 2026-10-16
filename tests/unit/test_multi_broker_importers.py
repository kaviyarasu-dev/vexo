import pytest
import os
import datetime
from db.connection import get_db, close_db
from db.migrations import init_db
from services.journal.importer_engine import BrokerParserFactory, FIFOReconciler, TradeImporterEngine
from services.journal.parsers.base_parser import RawTradeFill
from services.journal.parsers.fyers_parser import FyersParser
from services.journal.parsers.zerodha_parser import ZerodhaParser
from services.journal.parsers.groww_parser import GrowwParser
from services.journal_service import JournalService


@pytest.fixture
def test_db(tmp_path):
    """Sets up an isolated DuckDB instance for unit testing."""
    db_path = str(tmp_path / "test_multi_broker_importers.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def load_fixture(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "fixtures", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_broker_auto_detection():
    """Verifies that BrokerParserFactory accurately auto-detects all three broker formats."""
    fyers_csv = load_fixture("sample_fyers_tradebook.csv")
    zerodha_csv = load_fixture("sample_zerodha_tradebook.csv")
    groww_csv = load_fixture("sample_groww_tradebook.csv")

    assert BrokerParserFactory.detect_broker(fyers_csv) == "FYERS"
    assert BrokerParserFactory.detect_broker(zerodha_csv) == "ZERODHA"
    assert BrokerParserFactory.detect_broker(groww_csv) == "GROWW"

    # Unknown format must raise descriptive error
    with pytest.raises(ValueError, match="Unable to identify broker tradebook format"):
        BrokerParserFactory.detect_broker("col_a,col_b,col_c\n1,2,3")


def test_zerodha_parser():
    """Verifies parsing of Zerodha Kite Console tradebook fills."""
    csv_text = load_fixture("sample_zerodha_tradebook.csv")
    parser = ZerodhaParser()
    fills = parser.parse_fills(csv_text)

    assert len(fills) == 4
    # First fill: INFY BUY 50 @ 1450.0
    f0 = fills[0]
    assert f0.symbol == "NSE:INFY-EQ"
    assert f0.side == "BUY"
    assert f0.quantity == 50
    assert f0.price == 1450.0
    assert f0.broker == "ZERODHA"

    # Second fill: INFY SELL 50 @ 1480.0
    f1 = fills[1]
    assert f1.symbol == "NSE:INFY-EQ"
    assert f1.side == "SELL"
    assert f1.quantity == 50
    assert f1.price == 1480.0

    # Third fill: HDFCBANK SELL 40 @ 1620.0 (Short entry)
    f2 = fills[2]
    assert f2.symbol == "NSE:HDFCBANK-EQ"
    assert f2.side == "SELL"
    assert f2.quantity == 40
    assert f2.price == 1620.0


def test_groww_parser():
    """Verifies parsing of Groww equity trade report fills."""
    csv_text = load_fixture("sample_groww_tradebook.csv")
    parser = GrowwParser()
    fills = parser.parse_fills(csv_text)

    assert len(fills) == 4
    # First fill: RELIANCE BUY 100 @ 2500.0
    f0 = fills[0]
    assert f0.symbol == "NSE:RELIANCE-EQ"
    assert f0.side == "BUY"
    assert f0.quantity == 100
    assert f0.price == 2500.0
    assert f0.broker == "GROWW"

    # Second fill: RELIANCE SELL 100 @ 2540.0
    f1 = fills[1]
    assert f1.symbol == "NSE:RELIANCE-EQ"
    assert f1.side == "SELL"
    assert f1.quantity == 100
    assert f1.price == 2540.0


def test_fifo_reconciler_partial_fills():
    """Verifies that FIFO reconciler pairs multi-fill partial orders accurately."""
    # Buy 100 @ 1000, then Sell 40 @ 1020, then Sell 60 @ 1030
    fills = [
        RawTradeFill(
            symbol="NSE:TCS-EQ",
            side="BUY",
            quantity=100,
            price=1000.0,
            timestamp=datetime.datetime(2026, 10, 5, 9, 30),
            broker="ZERODHA",
        ),
        RawTradeFill(
            symbol="NSE:TCS-EQ",
            side="SELL",
            quantity=40,
            price=1020.0,
            timestamp=datetime.datetime(2026, 10, 5, 10, 30),
            broker="ZERODHA",
        ),
        RawTradeFill(
            symbol="NSE:TCS-EQ",
            side="SELL",
            quantity=60,
            price=1030.0,
            timestamp=datetime.datetime(2026, 10, 5, 11, 30),
            broker="ZERODHA",
        ),
    ]

    trades = FIFOReconciler.reconcile(fills)
    assert len(trades) == 2

    # First closed trade: 40 qty from 1000 to 1020 (+20 pt gain * 40 = +800)
    t1 = trades[0]
    assert t1.symbol == "NSE:TCS-EQ"
    assert t1.direction == "LONG"
    assert t1.quantity == 40
    assert t1.entry_price == 1000.0
    assert t1.exit_price == 1020.0
    assert t1.pnl_gross == 800.0

    # Second closed trade: 60 qty from 1000 to 1030 (+30 pt gain * 60 = +1800)
    t2 = trades[1]
    assert t2.symbol == "NSE:TCS-EQ"
    assert t2.direction == "LONG"
    assert t2.quantity == 60
    assert t2.entry_price == 1000.0
    assert t2.exit_price == 1030.0
    assert t2.pnl_gross == 1800.0


def test_trade_importer_engine_end_to_end(test_db):
    """Verifies that TradeImporterEngine ingests Zerodha and Groww files directly into DuckDB."""
    importer = TradeImporterEngine(test_db)
    journal_svc = JournalService(test_db)

    # 1. Import Zerodha
    zerodha_csv = load_fixture("sample_zerodha_tradebook.csv")
    res_z = importer.import_tradebook_csv(zerodha_csv)
    assert res_z["status"] == "success"
    assert res_z["broker_detected"] == "ZERODHA"
    assert res_z["imported_trades"] == 2

    # 2. Import Groww
    groww_csv = load_fixture("sample_groww_tradebook.csv")
    res_g = importer.import_tradebook_csv(groww_csv)
    assert res_g["status"] == "success"
    assert res_g["broker_detected"] == "GROWW"
    assert res_g["imported_trades"] == 2

    # Verify total trades in DuckDB
    all_trades = journal_svc.list_trades()
    assert len(all_trades) == 4

    # Verify Zerodha trades present
    symbols = {t.symbol for t in all_trades}
    assert "NSE:INFY-EQ" in symbols
    assert "NSE:HDFCBANK-EQ" in symbols
    assert "NSE:RELIANCE-EQ" in symbols
    assert "NSE:SBIN-EQ" in symbols
