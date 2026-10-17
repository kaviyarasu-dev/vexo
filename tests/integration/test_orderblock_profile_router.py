"""Integration tests for OrderBlock Profile and augmented Boards endpoints.
Verifies GET /api/v1/orderblock/profile and GET /api/v1/orderblock/boards.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from services.orderblock.tick_recorder import get_tick_recorder


@pytest.fixture
def client():
    return TestClient(app)


def test_get_orderblock_profile_live_memory(client):
    recorder = get_tick_recorder()
    symbol = "NSE:RELIANCE-EQ"

    # Seed live tick data into recorder
    recorder.handle_tick(symbol, 2800.0, 50000, 2800.0, 2840.0)
    recorder.handle_tick(symbol, 2820.0, 60000, 2800.0, 2840.0)

    response = client.get(f"/api/v1/orderblock/profile?symbol={symbol}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["symbol"] == symbol
    assert data["day_low"] == 2800.0
    assert data["day_high"] == 2840.0
    assert data["current_price"] == 2820.0
    assert len(data["buckets"]) == 40
    assert data["poc_volume"] == 10000


def test_get_orderblock_boards_augmented_profile(client):
    response = client.get("/api/v1/orderblock/boards")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert "bullish_boards" in data
    assert "bearish_boards" in data

    # Every contender item should have profile_summary
    for item in data.get("bullish_boards", []):
        assert "profile_summary" in item
        summary = item["profile_summary"]
        if summary:
            assert "mini_buckets" in summary
            assert len(summary["mini_buckets"]) == 40

    for item in data.get("bearish_boards", []):
        assert "profile_summary" in item
        summary = item["profile_summary"]
        if summary:
            assert "mini_buckets" in summary
            assert len(summary["mini_buckets"]) == 40
