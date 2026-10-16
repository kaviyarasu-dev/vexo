"""
Integration tests for Trade Journal Calendar & Quantitative Diagnostics REST APIs.
Tests GET /api/v1/journal/calendar and GET /api/v1/journal/diagnostics endpoints.
Validates HTTP 200 OK, response envelope, schemas, daily attribution, streaks, and diagnostics.
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
    db_path = str(tmp_path / "test_journal_calendar_api.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_api_get_calendar_default():
    """Verifies retrieval of current month's calendar with default parameters."""
    response = client.get("/api/v1/journal/calendar")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert "year" in payload
    assert "month" in payload
    assert "days" in payload
    assert "weeks" in payload
    assert "kpis" in payload

    kpis = payload["kpis"]
    assert "monthly_net_pnl" in kpis
    assert "trading_days" in kpis
    assert "win_days" in kpis
    assert "loss_days" in kpis
    assert "win_day_pct" in kpis
    assert "max_win_streak" in kpis
    assert "max_loss_streak" in kpis


def test_api_get_calendar_specific_month():
    """Verifies retrieval of calendar for a specific year and month."""
    response = client.get("/api/v1/journal/calendar?year=2026&month=10")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert payload["year"] == 2026
    assert payload["month"] == 10
    assert len(payload["days"]) == 31

    first_day = payload["days"][0]
    assert first_day["date"] == "2026-10-01"
    assert first_day["day_of_month"] == 1
    assert "status" in first_day
    assert "net_pnl" in first_day


def test_api_get_quantitative_diagnostics():
    """Verifies retrieval of multi-dimensional quantitative diagnostics."""
    response = client.get("/api/v1/journal/diagnostics")
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert "time_of_day" in payload
    assert "direction" in payload
    assert "duration" in payload
    assert "instruments" in payload

    # Verify time-of-day bucket schema
    tod = payload["time_of_day"]
    assert len(tod) == 4
    names = {b["name"] for b in tod}
    assert "morning" in names
    assert "midday" in names
    assert "afternoon" in names
    assert "off_hours" in names

    for b in tod:
        assert "trades_count" in b
        assert "win_rate" in b
        assert "net_pnl" in b
        assert "avg_r" in b
        assert "profit_factor" in b


def test_api_calendar_and_diagnostics_with_seeded_data():
    """Verifies calendar KPIs and diagnostics after loading realistic sample data."""
    # Seed sample trades
    seed_resp = client.post("/api/v1/journal/sample-data")
    assert seed_resp.status_code == 200
    assert seed_resp.json()["status"] == "success"

    # Query calendar
    cal_resp = client.get("/api/v1/journal/calendar")
    assert cal_resp.status_code == 200
    cal_data = cal_resp.json()
    kpis = cal_data["kpis"]
    assert kpis["trading_days"] > 0
    assert kpis["monthly_net_pnl"] != 0.0

    # Query diagnostics
    diag_resp = client.get("/api/v1/journal/diagnostics")
    assert diag_resp.status_code == 200
    diag_data = diag_resp.json()

    # Direction breakdown
    dir_map = {b["name"]: b for b in diag_data["direction"]}
    assert dir_map["long"]["trades_count"] > 0
    assert "short" in dir_map

    # Instruments has equity and F&O
    inst_map = {b["name"]: b for b in diag_data["instruments"]}
    assert inst_map["equity"]["trades_count"] > 0
    assert inst_map["fno"]["trades_count"] > 0


def test_download_sample_csv_endpoint():
    """Verifies that GET /api/v1/journal/sample-csv serves the institutional sample tradebook CSV."""
    resp = client.get("/api/v1/journal/sample-csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert 'filename="sample_tradebook.csv"' in resp.headers["content-disposition"]
    text = resp.text
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert len(lines) >= 100
    header = lines[0]
    assert "symbol" in header
    assert "trade_date" in header
    assert "trade_type" in header
    assert "order_execution_time" in header
    assert "RELIANCE" in text
    assert "MARUTI" in text
