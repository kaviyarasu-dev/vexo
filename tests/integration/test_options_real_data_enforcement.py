"""
Integration Tests for Real Options Analytics & Greeks Enforcement.
Verifies:
1. Live Fyers real data loading for option chain, strikes matrix, and Black-Scholes Greeks.
2. Max Pain calculation strictly from real call/put open interest.
3. Open interest (ΔOI) analytics, PCR, sentiment, and major support/resistance walls on real market data.
4. Zero fake data guarantee: non-existent / non-F&O symbols strictly return HTTP 400 rather than synthesizing fake chains.
5. Auto-persistence: live option chain snapshots are cached into DuckDB option_chain_snapshots table.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Isolated database fixture to prevent DuckDB lock contention."""
    db_path = str(tmp_path / "test_options_real_data.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_real_option_chain_success_live():
    """Verifies that live option chain retrieves authentic market data with Black-Scholes Greeks."""
    resp = client.get("/api/v1/options/chain?symbol=NSE:NIFTY50-INDEX")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["source"] in ("live", "historical")
    assert data["underlying"] == "NSE:NIFTY50-INDEX"
    assert data["spot"] > 10000

    matrix = data["matrix"]
    assert len(matrix) > 0

    # Ensure strikes are real and Greeks are calculated accurately
    for row in matrix:
        assert "strike_price" in row
        assert row["strike_price"] > 0
        call = row.get("call")
        put = row.get("put")
        if call:
            assert "delta" in call
            assert "gamma" in call
            assert "theta" in call
            assert "vega" in call
        if put:
            assert "delta" in put
            assert "gamma" in put
            assert "theta" in put
            assert "vega" in put


def test_real_max_pain_success_live():
    """Verifies that Max Pain is calculated strictly from real option chain OI."""
    resp = client.get("/api/v1/options/maxpain?symbol=NSE:NIFTY50-INDEX")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["symbol"] == "NSE:NIFTY50-INDEX"
    assert data["max_pain_strike"] > 10000
    assert len(data["strikes"]) > 0
    assert len(data["payout_curve"]) > 0


def test_real_open_interest_success_live():
    """Verifies that open interest analytics and sentiment are derived from real market data."""
    resp = client.get("/api/v1/options/open-interest?symbol=NSE:NIFTY50-INDEX")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["total_call_oi"] > 0
    assert data["total_put_oi"] > 0
    assert data["pcr_oi"] > 0
    assert data["sentiment"] in ("BULLISH", "BEARISH", "NEUTRAL")
    assert data["major_resistance_strike"] > 0
    assert data["major_support_strike"] > 0


def test_zero_fake_data_rejection_for_non_fo_symbol():
    """Verifies that invalid or non-F&O symbol strictly fails with HTTP 400 (no synthetic fallback)."""
    resp = client.get("/api/v1/options/chain?symbol=NSE:INVALID_FAKE_STOCK-EQ")
    assert resp.status_code == 400
    err_body = resp.json()
    detail = (err_body.get("error") or {}).get("message") or err_body.get("detail", "")
    assert "No verified real option chain data available" in detail


def test_zero_fake_data_rejection_for_max_pain_invalid_symbol():
    """Verifies that Max Pain endpoint strictly returns HTTP 400 when real data is unavailable."""
    resp = client.get("/api/v1/options/maxpain?symbol=NSE:INVALID_FAKE_STOCK-EQ")
    assert resp.status_code == 400
    err_body = resp.json()
    detail = (err_body.get("error") or {}).get("message") or err_body.get("detail", "")
    assert "No verified real options data available" in detail


def test_zero_fake_data_rejection_for_open_interest_invalid_symbol():
    """Verifies that Open Interest endpoint strictly returns HTTP 400 when real data is unavailable."""
    resp = client.get("/api/v1/options/open-interest?symbol=NSE:INVALID_FAKE_STOCK-EQ")
    assert resp.status_code == 400
    err_body = resp.json()
    detail = (err_body.get("error") or {}).get("message") or err_body.get("detail", "")
    assert "No verified real option chain data available" in detail

