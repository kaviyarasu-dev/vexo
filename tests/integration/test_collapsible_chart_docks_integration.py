import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_index_html_collapsible_docks_dom_structure():
    """Verify index.html contains bottom-chart-dock and paper-trading-dock in correct hierarchy."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    # Bottom secondary chart dock contract
    assert 'id="bottom-chart-dock"' in content
    assert 'class="bottom-chart-dock collapsed"' in content
    assert 'id="bottom-chart-header"' in content
    assert 'id="btn-bottom-chart-toggle"' in content
    assert 'id="bottom-chart-body"' in content
    assert 'id="volume-pane"' in content
    assert 'id="chart-subpanes-container"' in content

    # Paper trading dock at bottom position (default: collapsed)
    assert 'class="paper-trading-dock collapsed"' in content
    assert 'id="paper-trading-dock"' in content
    assert 'id="btn-dock-toggle-view"' in content

    # Relative ordering: chart-stage (with main chart & bottom chart) appears BEFORE paper-trading-dock
    pos_main_chart = content.find('id="chart-container"')
    pos_bottom_dock = content.find('id="bottom-chart-dock"')
    pos_paper_dock = content.find('id="paper-trading-dock"')

    assert pos_main_chart != -1
    assert pos_bottom_dock != -1
    assert pos_paper_dock != -1

    # Hierarchy: main chart < bottom chart dock < paper trading dock
    assert pos_main_chart < pos_bottom_dock < pos_paper_dock


def test_theme_css_bottom_chart_dock_rules():
    """Verify theme.css contains styles for bottom-chart-dock and collapse states."""
    css_resp = client.get("/static/css/theme.css")
    assert css_resp.status_code == 200
    css_text = css_resp.text

    assert ".bottom-chart-dock" in css_text
    assert ".bottom-chart-header" in css_text
    assert ".bottom-chart-body" in css_text
    assert ".bottom-chart-dock.collapsed .bottom-chart-body" in css_text
    assert ".btn-bottom-chart-toggle" in css_text
    assert ".bottom-chart-dock.collapsed .btn-bottom-chart-toggle" in css_text


def test_chart_js_bottom_dock_controller_contract():
    """Verify chart.js has initBottomChartDock with localStorage persistence."""
    js_resp = client.get("/static/js/chart.js")
    assert js_resp.status_code == 200
    js_text = js_resp.text

    assert "initBottomChartDock" in js_text
    assert "trading_app_bottom_chart_state" in js_text
    assert "btn-bottom-chart-toggle" in js_text
    assert "bottom-chart-header" in js_text
    assert "bottom-chart-dock" in js_text


def test_paper_terminal_dock_localstorage_persistence_contract():
    """Verify paper_terminal_dock.js persists dock state in localStorage and defaults to closed."""
    dock_resp = client.get("/static/js/paper_terminal_dock.js")
    assert dock_resp.status_code == 200
    dock_text = dock_resp.text

    assert "trading_app_paper_dock_state" in dock_text
    assert "localStorage.getItem('trading_app_paper_dock_state')" in dock_text
    assert "localStorage.setItem('trading_app_paper_dock_state'" in dock_text
    assert "toggleCollapse" in dock_text
