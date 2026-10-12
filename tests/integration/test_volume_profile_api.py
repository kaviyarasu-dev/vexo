import pytest
import pandas as pd
from fastapi.testclient import TestClient
from main import app
from db.connection import get_db, close_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    db = get_db(":memory:", reset=True)
    db.execute_write("""
        CREATE TABLE IF NOT EXISTS candles_1m_adjusted (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT
        )
    """)
    start = pd.Timestamp("2024-01-10 03:45:00", tz="UTC")
    timestamps = [start + pd.Timedelta(minutes=i) for i in range(75)]
    df = pd.DataFrame({
        "symbol": "NSE:RELIANCE-EQ",
        "timestamp": [t.tz_localize(None) for t in timestamps],
        "open": [2500.0 + (i % 10) for i in range(75)],
        "high": [2505.0 + (i % 10) for i in range(75)],
        "low": [2495.0 + (i % 10) for i in range(75)],
        "close": [2502.0 + (i % 10) for i in range(75)],
        "volume": [1000 + i * 10 for i in range(75)]
    })
    db.execute_write_df("INSERT INTO candles_1m_adjusted SELECT * FROM _temp_input_table", df)
    yield db
    close_db()


def test_session_volume_profile_endpoint():
    response = client.get("/api/v1/studies/session-volume-profile?symbol=NSE:RELIANCE-EQ&timeframe=5m")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert json_data["data"] is not None
    assert "symbol" in json_data["data"]
    assert "sessions" in json_data["data"]


def test_tpo_market_profile_endpoint():
    response = client.get("/api/v1/studies/tpo-profile?symbol=NSE:RELIANCE-EQ&tick_size=1.0")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert json_data["data"] is not None
    assert "poc_price" in json_data["data"]
    assert "vah_price" in json_data["data"]
    assert "val_price" in json_data["data"]
    assert "price_matrix" in json_data["data"]
    assert "brackets" in json_data["data"]


def test_volume_profile_overlay_script_exists():
    with open("static/js/volume_profile_overlay.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "class VolumeProfileOverlay" in js
    assert "window.volumeProfileOverlay" in js
    assert "drawVisibleRangeVP" in js
    assert "drawSessionVP" in js
    assert "drawTPOMarketProfile" in js
    assert "hexToRgba" in js


def test_index_html_has_volume_profile_script():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert '/static/js/volume_profile_overlay.js' in html
