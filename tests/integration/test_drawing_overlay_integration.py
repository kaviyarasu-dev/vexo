import re
from pathlib import Path
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_static_assets_serving():
    """Verify that chart_drawings.js and chart_drawings.css are served with 200 OK."""
    # 1. JS Script
    js_resp = client.get("/static/js/chart_drawings.js")
    assert js_resp.status_code == 200
    js_text = js_resp.text
    assert "class ChartDrawingManager" in js_text
    assert "getMagnetPoint" in js_text
    assert "setTool" in js_text
    assert "toggleMagnet" in js_text
    assert "clearAll" in js_text
    assert "renderDrawingObject" in js_text
    assert "window.ChartDrawingManager" in js_text

    # 2. CSS Stylesheet
    css_resp = client.get("/static/css/chart_drawings.css")
    assert css_resp.status_code == 200
    css_text = css_resp.text
    assert ".chart-drawing-toolbar" in css_text
    assert "position: static;" in css_text
    assert "width: 44px;" in css_text
    assert ".toolbar-top-group" in css_text
    assert ".toolbar-bottom-group" in css_text
    assert ".chart-drawings-svg" in css_text
    assert ".drawing-tool-btn" in css_text
    assert ".magnet-snap-indicator" in css_text


def test_index_html_drawing_components():
    """Verify that static/index.html includes required CSS, JS, toolbar, and SVG overlay elements."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    # CSS link in head
    assert 'href="/static/css/chart_drawings.css' in content

    # JS script tag
    assert 'src="/static/js/chart_drawings.js' in content

    # Stage and panes wrapper
    assert 'class="chart-stage"' in content
    assert 'class="chart-panes-wrapper"' in content

    # Toolbar container and SVG overlay
    assert 'id="chart-drawing-toolbar"' in content
    assert 'class="toolbar-top-group"' in content
    assert 'class="toolbar-bottom-group"' in content
    assert 'id="chart-drawings-svg"' in content

    # All 7 toolbar buttons
    assert 'data-tool="cursor"' in content
    assert 'data-tool="trendline"' in content
    assert 'data-tool="horizontal_ray"' in content
    assert 'data-tool="fibonacci"' in content
    assert 'data-tool="position_rr"' in content
    assert 'id="btn-toggle-magnet"' in content
    assert 'id="btn-clear-drawings"' in content


def test_root_html_endpoint():
    """Verify that the FastAPI root endpoint renders the drawing overlay and toolbar."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "chart-drawing-toolbar" in resp.text
    assert "chart-drawings-svg" in resp.text


def test_chart_js_integration_hooks():
    """Verify that static/js/chart.js has lifecycle hooks for chartDrawingManager."""
    chart_js_path = Path("static/js/chart.js")
    assert chart_js_path.exists()
    content = chart_js_path.read_text(encoding="utf-8")

    assert "window.chartDrawingManager.requestRender" in content
    assert "window.chartDrawingManager.handleResize" in content
    assert "window.chartDrawingManager.onSymbolOrCandlesChanged" in content
