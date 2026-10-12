import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_patterns_scan_api_endpoint():
    payload = {
        "candles": [
            {"time": 1700000000, "open": 100.0, "high": 101.0, "low": 89.0, "close": 90.0, "volume": 1000},
            {"time": 1700000300, "open": 89.0, "high": 103.0, "low": 88.0, "close": 102.0, "volume": 2000},
            {"time": 1700000600, "open": 102.0, "high": 105.0, "low": 101.0, "close": 104.0, "volume": 1200}
        ]
    }
    response = client.post("/api/v1/studies/patterns", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert "signals" in json_data["data"]
    assert "markers" in json_data["data"]
    assert json_data["data"]["count"] >= 1
    # Check marker fields
    marker = json_data["data"]["markers"][0]
    assert marker["text"] == "BE"
    assert marker["position"] == "belowBar"
    assert marker["shape"] == "arrowUp"
    assert "customData" in marker


def test_static_files_exist_and_exposed():
    with open("static/js/chart_patterns.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "class ChartPatternManager" in js
    assert "window.applyChartPattern" in js
    assert "findMarkerNear" in js
    assert "showTooltip" in js

    with open("static/js/strategy_tester_dock.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "class StrategyTesterDock" in js
    assert "window.applyChartStrategy" in js
    assert "strategy-tester-dock" in js
    assert "Deep Dive in Backtest Lab" in js

    with open("static/js/chart_options_overlay.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "class ChartOptionsOverlay" in js
    assert "window.applyChartOptionsStudy" in js
    assert "renderMaxPain" in js
    assert "renderPCR" in js
    assert "renderStrikeOI" in js


def test_index_html_has_all_study_scripts():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert "/static/js/chart_patterns.js" in html
    assert "/static/js/strategy_tester_dock.js" in html
    assert "/static/js/chart_options_overlay.js" in html
    assert "/static/js/volume_profile_overlay.js" in html
    assert "/static/js/chart_studies.js" in html
    assert "/static/js/study_dialog.js" in html


def test_personal_and_community_catalog_presets():
    res_pers = client.get("/api/v1/studies/catalog?section=personal")
    assert res_pers.status_code == 200
    pers_data = res_pers.json()["data"]
    pers_ids = [s["id"] for s in pers_data]
    assert "pers_scalper_pro" in pers_ids
    assert "pers_trend_rider" in pers_ids

    res_comm = client.get("/api/v1/studies/catalog?section=community")
    assert res_comm.status_code == 200
    comm_data = res_comm.json()["data"]
    comm_ids = [s["id"] for s in comm_data]
    assert "comm_intraday_momentum" in comm_ids
    assert "comm_swing_breakout" in comm_ids
    assert "comm_options_seller" in comm_ids

    with open("static/js/study_dialog.js", "r", encoding="utf-8") as f:
        js = f.read()
    assert "saveCurrentActiveSetup" in js
    assert "tv_user_saved_scripts" in js


def test_deep_dive_in_backtest_lab_integration():
    with open("static/js/strategy_tester_dock.js", "r", encoding="utf-8") as f:
        dock_js = f.read()
    assert "navigateToBacktest" in dock_js
    assert "btn-dock-deep-dive" in dock_js
    assert "window.switchAppView" in dock_js
    assert "setStrategyAndParams" in dock_js

    with open("static/js/backtest_ui.js", "r", encoding="utf-8") as f:
        backtest_js = f.read()
    assert "setStrategyAndParams" in backtest_js
    assert "updateDynamicParams" in backtest_js

    with open("static/js/app.js", "r", encoding="utf-8") as f:
        app_js = f.read()
    assert "window.switchAppView = switchAppView" in app_js
    assert "window.switchView = switchAppView" in app_js


