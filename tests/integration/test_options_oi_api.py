"""
Integration tests for Options Open Interest and F&O Underlyings API.
Tests GET /api/v1/options/underlyings and GET /api/v1/options/open-interest endpoints.
Validates HTTP 200 OK, response envelope, schemas, PCR, sentiment, and strike data.
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
    db_path = str(tmp_path / "test_options_oi_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_api_get_fo_underlyings():
    """Verifies retrieval of full catalog of F&O indices and equities."""
    response = client.get("/api/v1/options/underlyings")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert "indices" in data
    assert "equities" in data
    assert "total_count" in data

    indices = data["indices"]
    equities = data["equities"]
    assert len(indices) == 4
    assert len(equities) >= 180
    assert data["total_count"] == len(indices) + len(equities)

    # Check NIFTY index structure
    nifty = next((idx for idx in indices if idx["symbol"] == "NIFTY"), None)
    assert nifty is not None
    assert nifty["display_name"] == "NIFTY 50"
    assert nifty["category"] == "INDEX"
    assert nifty["lot_size"] == 25
    assert nifty["spot_price"] > 0
    assert nifty["strike_step"] == 50.0

    # Check key equities
    equity_symbols = {eq["symbol"] for eq in equities}
    assert "RELIANCE" in equity_symbols
    assert "SBIN" in equity_symbols
    assert "TCS" in equity_symbols
    assert "INFY" in equity_symbols


def test_api_get_open_interest_nifty():
    """Verifies strike-by-strike Open Interest and sentiment report for NIFTY."""
    response = client.get("/api/v1/options/open-interest?symbol=NIFTY")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert data["symbol"] == "NIFTY"
    assert data["spot"] > 0
    assert "expiry_date" in data
    assert data["total_call_oi"] > 0
    assert data["total_put_oi"] > 0
    assert data["pcr_oi"] > 0
    assert data["sentiment"] in ("BULLISH", "BEARISH", "NEUTRAL")

    # Major walls
    assert data["major_resistance_strike"] > 0
    assert data["major_support_strike"] > 0
    assert data["max_pain_strike"] > 0
    assert data["active_call_battleground"] > 0
    assert data["active_put_battleground"] > 0

    strikes = data["strikes_data"]
    assert len(strikes) >= 20

    # Verify symmetric strike data fields
    for s in strikes:
        assert "strike" in s
        assert "call_oi" in s
        assert "put_oi" in s
        assert "call_oi_change" in s
        assert "put_oi_change" in s
        assert "call_ltp" in s
        assert "put_ltp" in s
        assert "call_iv" in s
        assert "put_iv" in s


def test_api_get_open_interest_banknifty():
    """Verifies open interest analysis for BANKNIFTY index."""
    response = client.get("/api/v1/options/open-interest?symbol=BANKNIFTY")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert data["symbol"] == "BANKNIFTY"
    assert data["spot"] > 40000
    assert len(data["strikes_data"]) >= 20


def test_api_get_open_interest_equity():
    """Verifies open interest analysis for an individual equity underlying."""
    response = client.get("/api/v1/options/open-interest?symbol=RELIANCE")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    data = payload["data"]
    assert data["symbol"] == "RELIANCE"
    assert data["spot"] > 500
    assert data["total_call_oi"] > 0
    assert data["total_put_oi"] > 0
    assert len(data["strikes_data"]) >= 20
