import pytest
from fastapi.testclient import TestClient
from main import app
import re
import os

client = TestClient(app)


def test_static_files_served():
    """Verify that all core frontend scripts and stylesheets are served."""
    files = [
        "/static/js/chart.js",
        "/static/js/chart_studies.js",
        "/static/js/volume_profile_overlay.js",
        "/static/js/chart_patterns.js",
        "/static/js/study_dialog.js",
        "/static/css/study_dialog.css",
    ]
    for f in files:
        res = client.get(f)
        assert res.status_code == 200, f"Failed to fetch {f}"


def test_chart_js_global_exposure():
    """Verify chart.js attaches mainChart, candleSeries, and calculations to window."""
    res = client.get("/static/js/chart.js")
    assert res.status_code == 200
    code = res.text
    assert "window.mainChart = mainChart;" in code
    assert "window.candleSeries = candleSeries;" in code
    assert "window.volumeChart = volumeChart;" in code
    assert "window.volumeSeries = volumeSeries;" in code
    assert "window.calculateVWAP = calculateVWAP;" in code
    assert "window.calculateEMA = calculateEMA;" in code
    assert "window.volumeProfileOverlay.requestRedraw()" in code
    assert "window.chartPatternManager.rescan()" in code


def test_study_dialog_css_pointer_events():
    """Verify study tag buttons and controls have pointer-events: auto."""
    res = client.get("/static/css/study_dialog.css")
    assert res.status_code == 200
    css = res.text
    assert "pointer-events: auto !important;" in css
    assert ".study-tag-btn" in css
    assert ".chart-legend-study-tags" in css


def test_chart_studies_profile_support_and_events():
    """Verify chart_studies.js has profile definitions and stopPropagation on tag buttons."""
    res = client.get("/static/js/chart_studies.js")
    assert res.status_code == 200
    code = res.text
    assert "isProfile: true" in code
    assert "session_tpo" in code
    assert "tpo" in code
    assert "stopPropagation" in code
    assert "window.volumeProfileOverlay.enable" in code
    assert "window.volumeProfileOverlay.disable" in code


def test_volume_profile_overlay_modes():
    """Verify volume_profile_overlay.js handles session_tpo, tpo, and session_vp."""
    res = client.get("/static/js/volume_profile_overlay.js")
    assert res.status_code == 200
    code = res.text
    assert "session_tpo" in code
    assert "drawTPOMarketProfile(w, h, true)" in code
    assert "drawTPOMarketProfile(w, h, false)" in code
    assert "drawSessionVP(w, h)" in code
    assert "updateLegendTagVal" in code


def test_chart_patterns_tags_and_rescan():
    """Verify chart_patterns.js creates legend tags and attaches markers."""
    res = client.get("/static/js/chart_patterns.js")
    assert res.status_code == 200
    code = res.text
    assert "updateLegendTags" in code
    assert "window.candleSeries.setMarkers(allMarkers)" in code
    assert "legend-tag-patt-" in code


def test_study_dialog_pattern_id_parsing():
    """Verify study_dialog.js strips pat_ and patt_ prefixes."""
    res = client.get("/static/js/study_dialog.js")
    assert res.status_code == 200
    code = res.text
    assert "replace(/^patt?_/," in code


def test_pattern_recognition_endpoint_with_sample_candles():
    """Verify pattern scanning API correctly detects patterns with and without pat_ prefix."""
    # Create sample candles with a Bullish Engulfing pattern at the end
    candles = [
        {"time": 1700000000, "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000},
        {"time": 1700000060, "open": 101.0, "high": 101.5, "low": 98.0, "close": 98.5, "volume": 1500},  # Bearish
        {"time": 1700000120, "open": 98.0, "high": 103.0, "low": 97.5, "close": 102.5, "volume": 3000},  # Bullish Engulfing
    ]

    # Test with prefix 'pat_bullish_engulfing'
    res1 = client.post("/api/v1/studies/patterns", json={
        "candles": candles,
        "patterns": ["pat_bullish_engulfing"]
    })
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert len(data1["signals"]) >= 1
    assert data1["signals"][0]["pattern_id"] == "bullish_engulfing"
    assert len(data1["markers"]) >= 1
    assert data1["markers"][0]["text"] == "BE"

    # Test with clean 'bullish_engulfing'
    res2 = client.post("/api/v1/studies/patterns", json={
        "candles": candles,
        "patterns": ["bullish_engulfing"]
    })
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert len(data2["signals"]) >= 1
    assert data2["signals"][0]["pattern_id"] == "bullish_engulfing"
