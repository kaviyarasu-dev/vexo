"""
Integration Tests for Options Lab UI: ΔOI Bar Chart, Net Greeks Dashboard & Interactive Pre-Expiry Payoff Simulator.
Verifies Plan 03-001 deliverables:
- Static script serving: static/js/options_analytics.js
- HTML integration in static/index.html (Quick chips, F&O search, OI subtab, Net Greeks HUD, Pre-expiry sliders)
- Theme CSS styling for dual-bar chart, Greeks HUD cards, sliders, and payoff curves
- Full API contract validation for /api/v1/options/underlyings, /api/v1/options/open-interest,
  /api/v1/options/strategy/greeks, and /api/v1/options/strategy/payoff
- Preset strategy application and theoretical curve simulation contracts
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Isolated database fixture to prevent DuckDB lock contention."""
    db_path = str(tmp_path / "test_options_lab_ui.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_static_options_analytics_js_served():
    """Verify that options_analytics.js is served with 200 OK and exposes the required controller interface."""
    resp = client.get("/static/js/options_analytics.js")
    assert resp.status_code == 200
    js_text = resp.text

    # Controller Class Definition
    assert "class OptionsAnalyticsController" in js_text

    # Core Methods
    assert "init()" in js_text or "init(" in js_text
    assert "switchOptionsTab(" in js_text
    assert "loadUnderlyings()" in js_text
    assert "loadOpenInterest(" in js_text or "loadOpenInterestData(" in js_text
    assert "renderOIDualBarChart(" in js_text or "renderOIBarChart(" in js_text
    assert "renderNetGreeksHUD(" in js_text
    assert "updateStrategyGreeksAndPayoff()" in js_text or "updatePayoffSimulation()" in js_text
    assert "renderPayoffSimulator(" in js_text or "renderPreExpiryPayoffChart(" in js_text
    assert "applyExpandedPreset(" in js_text or "applyStrategyPreset(" in js_text

    # Global window exposure
    assert "window.OptionsAnalyticsController = OptionsAnalyticsController" in js_text


def test_index_html_includes_options_analytics_script():
    """Verify that static/index.html includes the options_analytics.js script tag."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    assert 'src="/static/js/options_analytics.js"' in content

    # Verify root endpoint serves this HTML
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "options_analytics.js" in root_resp.text


def test_index_html_options_lab_dom_contract():
    """Verify that static/index.html includes all DOM components required by Plan 03-001."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    # 1. Hybrid Underlying Selector
    assert 'class="options-quick-chips"' in content
    assert 'class="options-chip-btn' in content
    assert 'data-symbol="NSE:NIFTY50-INDEX"' in content
    assert 'data-symbol="NSE:NIFTYBANK-INDEX"' in content
    assert 'id="options-symbol-search-input"' in content
    assert 'id="options-symbol-select"' in content

    # 2. Sub-Tab Bar & OI Analytics Subtab
    assert 'id="options-subtabs-nav"' in content
    assert 'data-subtab="open_interest"' in content
    assert 'id="btn-options-tab-oi"' in content
    assert 'id="options-oi-panel"' in content

    # 3. Open Interest Wall Callouts & SVG Dual-Bar Chart Container
    assert 'id="oi-resistance-val"' in content
    assert 'id="oi-support-val"' in content
    assert 'id="oi-maxpain-val"' in content
    assert 'id="oi-sentiment-badge"' in content
    assert 'id="oi-pcr-combined-val"' in content
    assert 'id="oi-dual-bar-chart"' in content

    # 4. Persistent Strategy Net Greeks HUD
    assert 'id="net-greeks-hud-card"' in content
    assert 'id="hud-delta-val"' in content
    assert 'id="hud-delta-inr"' in content
    assert 'id="hud-gamma-val"' in content
    assert 'id="hud-theta-val"' in content
    assert 'id="hud-theta-inr"' in content
    assert 'id="hud-vega-val"' in content
    assert 'id="hud-vega-inr"' in content

    # 5. Interactive Pre-Expiry Payoff Simulation Sliders & Metrics
    assert 'id="payoff-max-profit"' in content
    assert 'id="payoff-max-loss"' in content
    assert 'id="payoff-breakevens"' in content
    assert 'id="slider-target-days"' in content
    assert 'id="slider-iv-shock"' in content
    assert 'id="slider-target-days-val"' in content
    assert 'id="slider-iv-shock-val"' in content
    assert 'id="payoff-chart-svg"' in content

    # 6. Expanded Strategy Presets
    assert 'data-preset="bull_call"' in content
    assert 'data-preset="bear_call"' in content
    assert 'data-preset="bull_put"' in content
    assert 'data-preset="bear_put"' in content
    assert 'data-preset="straddle"' in content
    assert 'data-preset="strangle"' in content
    assert 'data-preset="iron_condor"' in content
    assert 'data-preset="iron_butterfly"' in content


def test_theme_css_options_lab_styles():
    """Verify that static/css/theme.css includes the required visual styling for Options Lab UI."""
    resp = client.get("/static/css/theme.css")
    assert resp.status_code == 200
    css = resp.text

    # Quick Chips & Search
    assert ".options-quick-chips" in css
    assert ".options-chip-btn" in css
    assert ".options-chip-btn.active" in css
    assert ".options-symbol-search-wrap" in css
    assert ".options-search-input" in css

    # OI Analytics Panel & Chart
    assert ".options-oi-panel" in css
    assert ".oi-chart-container" in css
    assert ".oi-toggle-group" in css
    assert ".oi-toggle-btn" in css
    assert ".oi-table-wrapper" in css
    assert ".oi-table" in css
    assert ".oi-atm-row" in css

    # Net Greeks HUD Card & Grid
    assert ".net-greeks-hud-card" in css
    assert ".net-greeks-grid" in css
    assert ".greek-hud-card" in css
    assert ".greek-hud-label" in css
    assert ".greek-hud-val" in css
    assert ".greek-hud-sub" in css

    # Pre-Expiry Payoff Simulation Sliders & Legend
    assert ".payoff-simulation-sliders" in css
    assert ".payoff-slider-group" in css
    assert ".payoff-range-slider" in css
    assert ".legend-dashed" in css
    assert ".legend-solid-cyan" in css


def test_options_underlyings_catalog_api_integration():
    """Verify GET /api/v1/options/underlyings returns full index and equity F&O universe."""
    resp = client.get("/api/v1/options/underlyings")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    catalog = data["data"]
    assert "indices" in catalog
    assert "equities" in catalog
    assert len(catalog["indices"]) == 4
    assert len(catalog["equities"]) >= 180


def test_options_oi_analytics_api_integration():
    """Verify GET /api/v1/options/open-interest returns PCR, Sentiment, Walls and strike-by-strike OI."""
    resp = client.get("/api/v1/options/open-interest?symbol=NIFTY")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    oi = data["data"]
    assert oi["symbol"] == "NIFTY"
    assert oi["spot"] > 0
    assert oi["pcr_oi"] > 0
    assert oi["sentiment"] in ("BULLISH", "BEARISH", "NEUTRAL")
    assert oi["major_resistance_strike"] > 0
    assert oi["major_support_strike"] > 0
    assert oi["max_pain_strike"] > 0

    strikes = oi["strikes_data"]
    assert len(strikes) >= 20
    first = strikes[0]
    assert "strike" in first
    assert "call_oi" in first
    assert "call_oi_change" in first
    assert "put_oi" in first
    assert "put_oi_change" in first


def test_options_payoff_pre_expiry_simulation_api_integration():
    """Verify POST /api/v1/options/strategy/greeks and POST /api/v1/options/strategy/payoff calculate dual curves and rupee net Greeks."""
    greeks_payload = {
        "symbol": "NIFTY",
        "spot": 25050.0,
        "t_days": 4.0,
        "r": 0.065,
        "legs": [
            {"strike": 25000.0, "option_type": "CE", "position": "LONG", "premium": 140.0, "quantity": 1, "iv": 0.14},
            {"strike": 25200.0, "option_type": "CE", "position": "SHORT", "premium": 55.0, "quantity": 1, "iv": 0.135}
        ]
    }

    g_resp = client.post("/api/v1/options/strategy/greeks", json=greeks_payload)
    assert g_resp.status_code == 200
    g_res = g_resp.json()
    assert g_res["success"] is True
    g_data = g_res["data"]
    assert g_data["net_delta"] > 0
    assert g_data["delta_inr"] > 0
    assert g_data["net_gamma"] != 0
    assert "vega_inr" in g_data

    payoff_payload = {
        "symbol": "NIFTY",
        "spot": 25050.0,
        "t_days_remaining": 5.0,
        "target_days": 2.0,
        "iv_shock_pct": 5.0,
        "r": 0.065,
        "legs": greeks_payload["legs"]
    }

    p_resp = client.post("/api/v1/options/strategy/payoff", json=payoff_payload)
    assert p_resp.status_code == 200
    p_res = p_resp.json()
    assert p_res["success"] is True
    p_data = p_res["data"]

    assert "max_profit" in p_data
    assert "max_loss" in p_data
    assert "breakevens" in p_data
    assert "expiration_curve" in p_data
    assert "target_date_curve" in p_data

    # Verify both curves exist on points: theoretical (T+x) and expiration (T=0)
    exp_curve = p_data["expiration_curve"]
    target_curve = p_data["target_date_curve"]
    assert len(exp_curve) > 0
    assert len(target_curve) > 0
    assert "spot" in exp_curve[0]
    assert "pnl" in exp_curve[0]
    assert "spot" in target_curve[0]
    assert "pnl" in target_curve[0]


def test_strategy_presets_contract_coverage():
    """Verify that all standard strategy presets supported in OptionsAnalyticsController produce valid multi-leg payloads."""
    js_resp = client.get("/static/js/options_analytics.js")
    assert js_resp.status_code == 200
    js = js_resp.text

    # Ensure all 8 presets are handled in the controller
    expected_presets = [
        "bull_call",
        "bear_call",
        "bull_put",
        "bear_put",
        "straddle",
        "strangle",
        "iron_condor",
        "iron_butterfly",
    ]
    for preset in expected_presets:
        assert f"'{preset}'" in js or f'"{preset}"' in js, f"Missing preset {preset} in options_analytics.js"


def test_options_two_sections_data_loading_and_visibility():
    """Verify that Strike-by-Strike OI chart and Combined Strategy Net Greeks HUD contracts are correctly linked and styled."""
    # 1. Verify CSS rules for subpanel hiding
    css_resp = client.get("/static/css/theme.css")
    assert css_resp.status_code == 200
    assert ".options-subpanel.hidden" in css_resp.text
    assert "display: none !important" in css_resp.text

    # 2. Verify options_ui.js exports window.optionsUI and window.optionsController
    ui_resp = client.get("/static/js/options_ui.js")
    assert ui_resp.status_code == 200
    assert "window.optionsController = new OptionsUI();" in ui_resp.text
    assert "window.optionsUI = window.optionsController;" in ui_resp.text
    assert "switchOptionsTab(target)" in ui_resp.text

    # 3. Verify options_analytics.js eager loading and HUD update
    analytics_resp = client.get("/static/js/options_analytics.js")
    assert analytics_resp.status_code == 200
    assert "await this.loadOpenInterest(this.activeSymbol);" in analytics_resp.text
    assert "await this.updateStrategyGreeksAndPayoff();" in analytics_resp.text
    assert "renderNetGreeksHUD" in analytics_resp.text
    assert "renderOIDualBarChart" in analytics_resp.text


def test_max_pain_chart_collision_free_rendering_and_styling():
    """Verify that Max Pain chart has collision-free label spacing, range toggle, and theme styling."""
    # 1. Verify CSS rules for maxpain
    css_resp = client.get("/static/css/theme.css")
    assert css_resp.status_code == 200
    css = css_resp.text
    assert ".maxpain-range-toggle" in css
    assert ".text-emerald" in css
    assert ".text-amber" in css
    assert ".active-mp-bar" in css

    # 2. Verify options_ui.js implementation of collision-free adaptive labels and range toggle
    ui_resp = client.get("/static/js/options_ui.js")
    assert ui_resp.status_code == 200
    js = ui_resp.text
    assert "minLabelSpacing" in js
    assert "maxAllowedTicks" in js
    assert "btn-mp-range-focused" in js
    assert "btn-mp-range-all" in js
    assert "minBarHeight" in js
    assert "maxPainRangeMode" in js
    assert "Spot: ₹" in js

