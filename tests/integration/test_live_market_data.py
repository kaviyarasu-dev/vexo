"""Integration tests for LiveMarketDataService and live chart data synchronization.
Adheres to GEMINI.md single-writer DuckDB rules and IST timezone alignment.
"""

from datetime import datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient

from core.exceptions import AuthenticationExpiredError, FyersAPIError
from db.connection import get_db, close_db
from db.migrations import init_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from main import app
from services.live_market_data_service import LiveMarketDataService


class MockMarketDataProvider:
    def __init__(self, candles=None, quotes=None, should_fail_auth=False):
        self.candles = candles or []
        self.quotes = quotes or {}
        self.should_fail_auth = should_fail_auth
        self.calls = []

    def fetch_candles(self, symbol, resolution, range_from, range_to, cont_flag="0", priority_lane=1):
        self.calls.append({
            "symbol": symbol,
            "resolution": resolution,
            "range_from": range_from,
            "range_to": range_to,
        })
        if self.should_fail_auth:
            raise AuthenticationExpiredError("Fyers token expired and automated refresh failed.")
        return self.candles

    def fetch_quotes(self, symbols):
        if self.should_fail_auth:
            raise AuthenticationExpiredError("Fyers token expired.")
        return self.quotes

    def fetch_option_chain(self, symbol, strikes=20):
        return {}


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_live_market_data.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_jit_sync_on_empty_db(setup_test_db):
    """When DB has 0 candles for a symbol, JIT sync downloads initial historical window."""
    db = setup_test_db
    now = datetime.now(timezone.utc).replace(microsecond=0)
    mock_candles = [
        {
            "symbol": "NSE:INFY-EQ",
            "timestamp": now - timedelta(minutes=i),
            "open": 1500.0 + i,
            "high": 1505.0 + i,
            "low": 1498.0 + i,
            "close": 1502.0 + i,
            "volume": 1000 * (i + 1),
        }
        for i in range(10)
    ]

    mock_provider = MockMarketDataProvider(candles=mock_candles)
    candle_repo = DuckDBCandleRepo(db)
    service = LiveMarketDataService(
        db=db,
        market_data_provider=mock_provider,
        candle_repo=candle_repo,
    )

    result = service.ensure_symbol_freshness("NSE:INFY-EQ", "5m")
    assert result["status"] == "OK"
    assert result["is_live"] is True
    assert result["inserted"] == 10

    # Verify candles are in DuckDB
    cursor = db.get_read_cursor()
    try:
        count = cursor.execute("SELECT COUNT(*) FROM candles_1m_raw WHERE symbol = 'NSE:INFY-EQ'").fetchone()[0]
        assert count == 10
    finally:
        cursor.close()


def test_jit_sync_auth_expired_graceful(setup_test_db):
    """When Fyers auth is expired, ensure_symbol_freshness returns AUTH_REQUIRED without failing."""
    db = setup_test_db
    mock_provider = MockMarketDataProvider(should_fail_auth=True)
    service = LiveMarketDataService(
        db=db,
        market_data_provider=mock_provider,
        candle_repo=DuckDBCandleRepo(db),
    )

    result = service.ensure_symbol_freshness("NSE:INFY-EQ", "1m")
    assert result["status"] == "AUTH_REQUIRED"
    assert result["is_live"] is False
    assert result["inserted"] == 0


def test_get_live_candle_with_quote(setup_test_db):
    """Verify get_live_candle returns active candle with merged LTP quote."""
    db = setup_test_db
    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_ts = int(now.timestamp())

    mock_candles = [
        {
            "symbol": "NSE:TCS-EQ",
            "timestamp": now,
            "open": 3500.0,
            "high": 3510.0,
            "low": 3495.0,
            "close": 3505.0,
            "volume": 2500,
        }
    ]

    mock_quotes = {
        "s": "ok",
        "d": [
            {
                "n": "NSE:TCS-EQ",
                "v": {
                    "lp": 3525.0,
                    "open_price": 3500.0,
                    "high_price": 3530.0,
                    "low_price": 3490.0,
                    "prev_close_price": 3480.0,
                    "ch": 45.0,
                    "chp": 1.29,
                    "volume": 120000,
                    "tt": now_ts,
                }
            }
        ]
    }

    mock_provider = MockMarketDataProvider(candles=mock_candles, quotes=mock_quotes)
    service = LiveMarketDataService(
        db=db,
        market_data_provider=mock_provider,
        candle_repo=DuckDBCandleRepo(db),
    )

    resp = service.get_live_candle("NSE:TCS-EQ", "1m")
    assert resp.is_live is True
    assert resp.auth_status == "OK"
    assert resp.quote is not None
    assert resp.quote.ltp == 3525.0
    assert resp.candle is not None
    assert resp.candle.close == 3525.0
    assert resp.candle.high >= 3525.0


def test_candles_api_endpoints(setup_test_db):
    """Verify FastAPI GET /api/v1/candles and /api/v1/candles/live contracts."""
    db = setup_test_db
    # Insert 1 test candle during NSE market hours (10:00 AM IST)
    ist_market_time = datetime(2026, 10, 14, 10, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    candle_time = ist_market_time.astimezone(timezone.utc).replace(tzinfo=None)
    candle_repo = DuckDBCandleRepo(db)
    candle_repo.batch_insert_1m([{
        "symbol": "NSE:RELIANCE-EQ",
        "timestamp": candle_time,
        "open": 2500.0,
        "high": 2510.0,
        "low": 2490.0,
        "close": 2505.0,
        "volume": 1000
    }])


    client = TestClient(app)

    # 1. Historical candles query with refresh_live=false
    resp = client.get("/api/v1/candles?symbol=NSE:RELIANCE-EQ&timeframe=1m&limit=5&refresh_live=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "candles" in data["data"]
    assert len(data["data"]["candles"]) >= 1
    assert data["data"]["candles"][-1]["close"] == 2505.0
    assert "is_live" in data["data"]
    assert "auth_status" in data["data"]


    # 2. Live candle query
    live_resp = client.get("/api/v1/candles/live?symbol=NSE:RELIANCE-EQ&timeframe=1m")
    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert live_data["success"] is True
    assert "symbol" in live_data["data"]
    assert "timeframe" in live_data["data"]
    assert "auth_status" in live_data["data"]


def test_multi_chunk_catchup_across_historical_gap(setup_test_db):
    """When a stock has not been opened for 120+ days, catch-up splits requests into Fyers-compliant chunks."""
    db = setup_test_db
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    old_date = (now_ist.date() - timedelta(days=120))
    old_time = datetime.combine(old_date, datetime.min.time(), tzinfo=timezone.utc)

    candle_repo = DuckDBCandleRepo(db)
    # Seed 1 old candle
    candle_repo.batch_insert_1m([{
        "symbol": "NSE:RELIANCE-EQ",
        "timestamp": old_time,
        "open": 2000.0,
        "high": 2010.0,
        "low": 1990.0,
        "close": 2005.0,
        "volume": 50000,
    }])

    # Mock provider that captures chunk calls and returns new candles
    class MultiChunkMockProvider:
        def __init__(self):
            self.chunk_calls = []

        def fetch_candles(self, symbol, resolution, range_from, range_to, cont_flag="0", priority_lane=1):
            self.chunk_calls.append({"range_from": range_from, "range_to": range_to})
            d = datetime.strptime(range_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return [{
                "symbol": symbol,
                "timestamp": d,
                "open": 2100.0,
                "high": 2110.0,
                "low": 2090.0,
                "close": 2105.0,
                "volume": 10000,
            }]

        def fetch_quotes(self, symbols):
            return {}

        def fetch_option_chain(self, symbol, strikes=20):
            return {}

    mock_provider = MultiChunkMockProvider()
    service = LiveMarketDataService(
        db=db,
        market_data_provider=mock_provider,
        candle_repo=candle_repo,
    )

    result = service.ensure_symbol_freshness("NSE:RELIANCE-EQ", "1m")
    assert result["status"] == "OK"
    assert result["is_live"] is True
    # 120 days gap must have been broken into at least 2 chunks (each <= 100 days)
    assert len(mock_provider.chunk_calls) >= 2
    assert result["inserted"] >= 1


def test_strict_broker_zero_fake_data_when_auth_expired(setup_test_db):
    """When Fyers auth is expired, zero fake, dummy, or fallback candles are returned."""
    db = setup_test_db
    mock_provider = MockMarketDataProvider(should_fail_auth=True)
    service = LiveMarketDataService(
        db=db,
        market_data_provider=mock_provider,
        candle_repo=DuckDBCandleRepo(db),
    )

    resp = service.get_live_candle("NSE:RELIANCE-EQ", "1m")
    assert resp.is_live is False
    assert resp.auth_status == "AUTH_REQUIRED"
    assert resp.candle is None
    assert resp.quote is None


def test_auth_status_and_contracts():
    """Verify index.html and theme.css contain the required popup, outdated banner, and empty state elements."""
    from pathlib import Path
    html_text = Path("static/index.html").read_text(encoding="utf-8")
    css_text = Path("static/css/theme.css").read_text(encoding="utf-8")

    # Auth Modal popup elements
    assert 'id="auth-modal"' in html_text
    assert 'id="auth-modal-status-badge"' in html_text
    assert 'id="input-manual-token"' in html_text
    assert 'id="btn-save-manual-token"' in html_text
    assert 'id="btn-login-browser"' in html_text

    # Outdated data warning banner and empty state
    assert 'id="chart-outdated-banner"' in html_text
    assert 'id="chart-auth-empty-state"' in html_text
    assert 'id="btn-banner-login"' in html_text
    assert 'id="btn-empty-login"' in html_text

    # CSS rules
    assert ".chart-outdated-banner" in css_text
    assert ".chart-auth-empty-state" in css_text
    assert ".auth-status-pill" in css_text


def test_auth_token_and_code_exchange_endpoints(monkeypatch):
    """Verify auth endpoints handle redirect URLs, auth codes, and callbacks."""
    from main import app
    client = TestClient(app)

    # 1. Test short input rejection
    resp = client.post("/api/v1/auth/token", json={"token": "too_short"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_INPUT"

    # 2. Test URL with auth_code extraction and simulated exchange
    exchange_called = []
    def mock_exchange(self, code, pin=None):
        exchange_called.append(code)
        from core.interfaces import AuthToken
        now = datetime.now(timezone.utc)
        return AuthToken(access_token="mock_access", refresh_token=None, access_token_expires_at=now, refresh_token_expires_at=None)

    def mock_validate(self):
        return True

    from services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "exchange_code_for_token", mock_exchange)
    monkeypatch.setattr(AuthService, "validate_session", mock_validate)

    # Paste full URL containing auth_code
    url_payload = "https://127.0.0.1:5000/?s=ok&code=200&auth_code=test_jwt_auth_code_from_redirect_url_123456789"
    resp = client.post("/api/v1/auth/token", json={"token": url_payload})
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["data"]["auth_status"] == "CONNECTED"
    assert "test_jwt_auth_code_from_redirect_url_123456789" in exchange_called

    # 3. Test OAuth callback endpoint
    cb_resp = client.get("/api/v1/auth/callback?auth_code=test_jwt_code_callback_123456789", follow_redirects=False)
    assert cb_resp.status_code == 302
    assert cb_resp.headers["location"] == "/?auth=success"

