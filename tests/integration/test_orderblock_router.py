"""Integration tests for OrderBlock REST API Router and DuckDB Snapshots.
Tests:
- GET /api/v1/orderblock/boards
- GET /api/v1/orderblock/zones?symbol={symbol}
- GET /api/v1/orderblock/market-picture
- POST /api/v1/orderblock/snapshot
"""

import pytest
from datetime import datetime, date, timedelta
import pandas as pd
import pytz
from fastapi.testclient import TestClient

from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

IST = pytz.timezone("Asia/Kolkata")
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Sets up an isolated DuckDB instance populated with test market data."""
    db_path = str(tmp_path / "test_orderblock_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)

    # Insert test symbols
    symbols = [
        ("NSE:RELIANCE-EQ", "Reliance Industries", "NIFTY50", 1),
        ("NSE:TCS-EQ", "Tata Consultancy Services", "NIFTY50", 1),
        ("NSE:INFY-EQ", "Infosys", "NIFTY50", 1),
        ("NSE:WIPRO-EQ", "Wipro", "NIFTY50", 1),
        ("NSE:HDFCBANK-EQ", "HDFC Bank", "NIFTY50", 1),
        ("NSE:ICICIBANK-EQ", "ICICI Bank", "NIFTY50", 1),
    ]
    for sym, name, cat, tier in symbols:
        db.execute_write(
            "INSERT OR REPLACE INTO symbols (symbol, name, category, tier, is_active) VALUES (?, ?, ?, ?, TRUE)",
            (sym, name, cat, tier)
        )

    # Insert 50 daily candles per symbol for ADM calculation
    base_date = date(2026, 1, 1)
    daily_rows = []
    for sym, _, _, _ in symbols:
        for i in range(50):
            d = base_date + timedelta(days=i)
            # High 1050, Low 1000 -> Range 50.0
            daily_rows.append((sym, d, 1010.0, 1050.0, 1000.0, 1040.0, 100000))
            
    df_daily = pd.DataFrame(daily_rows, columns=["symbol", "date", "open", "high", "low", "close", "volume"])
    # Insert raw candles
    db.execute_write_df("INSERT INTO candles_1d_raw SELECT * FROM _temp_input_table", df_daily)

    # Insert 1-minute candles for 5m resampling
    start_time = datetime(2026, 10, 16, 9, 15, tzinfo=IST)
    minute_rows = []
    # Reliance: Bullish expansion
    for i in range(60):
        t = start_time + timedelta(minutes=i)
        p = 1000.0 + (i * 1.5)
        minute_rows.append(("NSE:RELIANCE-EQ", t.astimezone(pytz.UTC).replace(tzinfo=None), p, p + 2.0, p - 1.0, p + 1.0, 500))
        
    # TCS: Bearish decline
    for i in range(60):
        t = start_time + timedelta(minutes=i)
        p = 3000.0 - (i * 2.0)
        minute_rows.append(("NSE:TCS-EQ", t.astimezone(pytz.UTC).replace(tzinfo=None), p, p + 1.0, p - 2.0, p - 1.5, 500))

    df_min = pd.DataFrame(minute_rows, columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
    db.execute_write_df("INSERT INTO candles_1m_raw SELECT * FROM _temp_input_table", df_min)

    yield db
    close_db()


def test_get_orderblock_boards():
    """Validates GET /api/v1/orderblock/boards returns 20-board arrays, picks, and breadth."""
    response = client.get("/api/v1/orderblock/boards")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert "bullish_boards" in data
    assert "bearish_boards" in data
    assert "bullish_picks" in data
    assert "bearish_picks" in data
    assert "market_breadth" in data
    assert "leading_sectors" in data

    # Verify breadth schema
    breadth = data["market_breadth"]
    assert "advances" in breadth
    assert "declines" in breadth
    assert "ratio" in breadth


def test_get_orderblock_zones():
    """Validates GET /api/v1/orderblock/zones returns 5m zones, levels ladder, and liquidity pools."""
    response = client.get("/api/v1/orderblock/zones?symbol=NSE:RELIANCE-EQ")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert data["symbol"] == "NSE:RELIANCE-EQ"
    assert "active_zone" in data
    assert "historical_zones" in data
    assert "ladder" in data
    assert "liquidity_pools" in data


def test_get_orderblock_market_picture():
    """Validates GET /api/v1/orderblock/market-picture returns scatter coordinates and sector flow."""
    response = client.get("/api/v1/orderblock/market-picture")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert "points" in data
    assert "breadth" in data
    assert "leading_sector" in data
    assert "lagging_sector" in data
    assert isinstance(data["points"], list)


def test_post_orderblock_snapshot_persistence():
    """Validates POST /api/v1/orderblock/snapshot persists records into orderblock_snapshots."""
    response = client.post("/api/v1/orderblock/snapshot")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert "rows_persisted" in data
    assert data["rows_persisted"] >= 0

    # Query database to confirm table exists and holds records
    db = get_db()
    cursor = db.get_read_cursor()
    try:
        count = cursor.execute("SELECT count(*) FROM orderblock_snapshots").fetchone()[0]
        assert count == data["rows_persisted"]
    finally:
        cursor.close()
