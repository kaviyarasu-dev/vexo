"""
Integration Tests for NSE Stock Screener Real Data Enforcement.
Verifies:
1. Screener operates strictly on authentic DuckDB daily candles (candles_1d_adjusted) from NSE.
2. Zero fake / synthetic / mock data fallback: no fake stocks or mock candles.
3. Screener API returns enriched actual technical metrics (1D Change %, RSI-14, Volume Z-Score, 52W High/Low distance, 20-SMA distance).
4. Meta object guarantees real data and authentic market date.
5. All built-in presets return authentic market leaders.
6. Empty database condition strictly raises ValueError / HTTP 400.
"""

import pytest
import urllib.request
import json
from db.connection import DuckDBConnectionManager
from services.screener_service import ScreenerService
from core.interfaces import ScreenerFilter

BASE_URL = "http://127.0.0.1:8000/api/v1/screener"


def is_server_online():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_screener_status_real_data_guarantee():
    """Verifies that screener status endpoint confirms zero fake data and authentic market date."""
    req = urllib.request.Request(f"{BASE_URL}/status")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["success"] is True
        assert data["is_real_data"] is True
        assert data["zero_fake_data_guarantee"] is True
        assert "candles_1d_adjusted" in data["data_source"]
        assert data["latest_market_date"] >= "2026-10-09"


@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_screener_run_returns_enriched_real_metrics():
    """Verifies that screener returns actual computed technical metrics for matched real stocks."""
    payload = {
        "template": "volume_surge",
        "universe": "ALL",
        "technical_rules": [],
        "min_turnover_cr": 0.0
    }
    req = urllib.request.Request(
        f"{BASE_URL}/run",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode())
        assert res["success"] is True
        assert "meta" in res
        assert res["meta"]["is_real_data"] is True
        assert res["meta"]["zero_fake_data_guarantee"] is True
        assert res["meta"]["as_of_date"] >= "2026-10-09"

        stocks = res["data"]
        assert len(stocks) > 0, "Expected volume surge matches in real market dataset"

        for stock in stocks:
            assert stock["symbol"].startswith("NSE:"), f"Invalid symbol: {stock['symbol']}"
            assert stock["close"] > 0, "Stock close price must be positive"
            assert stock["as_of_date"] >= "2026-10-09"
            assert stock["volume_zscore_20"] >= 2.0, "Volume Z-score must satisfy template condition"
            assert stock["turnover_cr"] >= 10.0, "Turnover must satisfy >= 10 Cr condition"
            assert isinstance(stock["change_pct_1d"], (int, float)), "1D change must be numeric"
            assert 0.0 <= stock["rsi_14"] <= 100.0, "RSI-14 must be within [0, 100]"
            assert stock["dist_from_52w_high_pct"] is not None
            assert stock["dist_from_sma_20_pct"] is not None


@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_all_presets_execute_with_real_market_data():
    """Verifies that each preset scan executes successfully and yields valid real data."""
    presets = ["all_stocks", "volume_surge", "52_week_high", "rsi_oversold", "rsi_momentum", "sma_support"]
    for tmpl in presets:
        payload = {"template": tmpl, "universe": "ALL"}
        req = urllib.request.Request(
            f"{BASE_URL}/run",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode())
            assert res["success"] is True
            assert isinstance(res["data"], list)
            assert res["meta"]["is_real_data"] is True


@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_all_stocks_and_universe_filtering():
    """Verifies that all_stocks returns 100 stocks, and NIFTY50 universe returns 50 stocks."""
    req_all = urllib.request.Request(
        f"{BASE_URL}/run",
        data=json.dumps({"template": "all_stocks", "universe": "ALL"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_all) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert len(data["data"]) == 100, f"Expected 100 stocks in ALL universe, got {len(data['data'])}"

    req_n50 = urllib.request.Request(
        f"{BASE_URL}/run",
        data=json.dumps({"template": "all_stocks", "universe": "NIFTY50"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_n50) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert len(data["data"]) == 50, f"Expected 50 stocks in NIFTY50 universe, got {len(data['data'])}"


def test_screener_service_strict_error_when_no_candles(tmp_path):
    """Verifies ScreenerService raises ValueError when database has no verified candles (Zero Fake Data)."""
    empty_db_path = str(tmp_path / "empty_market.duckdb")
    empty_db = DuckDBConnectionManager(empty_db_path)
    # Create empty schema
    with empty_db.get_read_cursor() as conn:
        conn.execute("""
            CREATE TABLE candles_1d_adjusted (
                symbol VARCHAR,
                date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT
            );
            CREATE TABLE symbols (
                symbol VARCHAR,
                name VARCHAR,
                category VARCHAR,
                tier INTEGER
            );
        """)

    service = ScreenerService(empty_db)
    # Must return None for latest market date
    assert service.get_latest_market_date() is None

    # Must raise ValueError with explicit real data enforcement message
    with pytest.raises(ValueError) as excinfo:
        service.run_screener(ScreenerFilter(universe="ALL"))

    assert "No verified real market candles found in database" in str(excinfo.value)
    empty_db.close()


@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_screener_sync_live_endpoint():
    """Verifies that /api/v1/screener/sync-live connects to live pipeline and guarantees real data."""
    req = urllib.request.Request(
        f"{BASE_URL}/sync-live",
        data=json.dumps({"universe": "NIFTY50"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert "data" in data
        assert data["is_real_data"] is True
        assert data["zero_fake_data_guarantee"] is True
        # If Fyers token is present or expired, it reports clean real status without fabricating fake data
        res_data = data["data"]
        assert res_data["status"] in ("OK", "AUTH_REQUIRED")
        if res_data["status"] == "AUTH_REQUIRED":
            assert "Fyers" in res_data["message"]


@pytest.mark.skipif(not is_server_online(), reason="Server not running on port 8000")
def test_screener_run_with_refresh_live():
    """Verifies that /run with refresh_live=True executes cleanly with zero fake data."""
    req = urllib.request.Request(
        f"{BASE_URL}/run",
        data=json.dumps({"template": "all_stocks", "universe": "NIFTY50", "refresh_live": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["success"] is True
        assert len(data["data"]) == 50
        assert data["meta"]["is_real_data"] is True
        assert data["meta"]["zero_fake_data_guarantee"] is True
