"""Contract tests for IMarketDataProvider and FyersMarketDataProvider.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from core.interfaces import IAuthService, IMarketDataProvider
from core.rate_governor import RateGovernor
from services.fyers_client import FyersMarketDataProvider


@pytest.fixture
def mock_auth():
    auth = MagicMock(spec=IAuthService)
    auth.get_valid_token.return_value = "mock_access_token_12345"
    auth.refresh_token_if_needed.return_value = True
    return auth


@pytest.fixture
def fast_rate_governor():
    return RateGovernor(
        target_per_min=180,
        burst_per_sec=10,
        daily_cap=10000,
        time_provider=lambda: 1000.0,
        sleep_provider=lambda s: None,
    )


def test_fyers_provider_implements_imarketdataprovider(mock_auth, fast_rate_governor):
    """Verify FyersMarketDataProvider strictly satisfies IMarketDataProvider contract."""
    client = FyersMarketDataProvider(
        auth_service=mock_auth,
        rate_governor=fast_rate_governor,
        transport=lambda url, h, p: {"s": "ok", "candles": []},
    )
    assert isinstance(client, IMarketDataProvider)

    # Check method signatures
    sig_fetch = inspect.signature(client.fetch_candles)
    assert "symbol" in sig_fetch.parameters
    assert "resolution" in sig_fetch.parameters
    assert "range_from" in sig_fetch.parameters
    assert "range_to" in sig_fetch.parameters
    assert "cont_flag" in sig_fetch.parameters

    sig_quotes = inspect.signature(client.fetch_quotes)
    assert "symbols" in sig_quotes.parameters

    sig_chain = inspect.signature(client.fetch_option_chain)
    assert "symbol" in sig_chain.parameters
    assert "strikes" in sig_chain.parameters


def test_fetch_candles_parses_golden_fixture(mock_auth, fast_rate_governor):
    """Verify candle parsing against golden fixture fyers_response_1m_reliance.json."""
    fixture_path = Path("tests/fixtures/fyers_response_1m_reliance.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        golden_payload = json.load(f)

    def mock_transport(url, headers, params):
        return golden_payload

    client = FyersMarketDataProvider(
        auth_service=mock_auth,
        rate_governor=fast_rate_governor,
        transport=mock_transport,
    )

    candles = client.fetch_candles(
        symbol="NSE:RELIANCE-EQ",
        resolution="1m",
        range_from="2024-01-01",
        range_to="2024-01-02",
    )

    assert len(candles) == 10
    first = candles[0]
    assert first["symbol"] == "NSE:RELIANCE-EQ"
    assert first["open"] == 2580.0
    assert first["high"] == 2585.5
    assert first["low"] == 2578.0
    assert first["close"] == 2582.0
    assert first["volume"] == 15420
    assert "timestamp" in first


def test_fetch_candles_no_data_returns_empty_list(mock_auth, fast_rate_governor):
    """Verify 'no_data' envelope returns an empty list without raising."""
    client = FyersMarketDataProvider(
        auth_service=mock_auth,
        rate_governor=fast_rate_governor,
        transport=lambda u, h, p: {"s": "no_data", "candles": []},
    )

    candles = client.fetch_candles(
        symbol="NSE:RELIANCE-EQ",
        resolution="1m",
        range_from="2020-01-01",
        range_to="2020-04-10",
    )
    assert candles == []


def test_transient_error_300_retries(mock_auth, fast_rate_governor, monkeypatch):
    """Verify error -300 triggers retry with backoff and does not abort immediately."""
    monkeypatch.setattr("time.sleep", lambda s: None)

    attempt_count = 0

    def mock_transport(url, headers, params):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            return {"s": "error", "code": -300, "message": "Internal Server Error"}
        return {
            "s": "ok",
            "candles": [[1704080700, 100, 105, 95, 102, 1000]],
        }

    client = FyersMarketDataProvider(
        auth_service=mock_auth,
        rate_governor=fast_rate_governor,
        transport=mock_transport,
    )

    candles = client.fetch_candles(
        symbol="NSE:TCS-EQ",
        resolution="1m",
        range_from="2024-01-01",
        range_to="2024-01-10",
    )

    assert attempt_count == 3
    assert len(candles) == 1
