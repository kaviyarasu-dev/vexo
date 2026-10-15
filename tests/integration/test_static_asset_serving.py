import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_static_index_html_mount():
    """Frontend shell loads successfully from FastAPI static mount."""
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert 'id="chart-container"' in response.text
    # Ensure redundant header logo text is removed to conserve horizontal space
    assert '<div class="logo">NSE Quant App</div>' not in response.text
    assert 'id="search-trigger"' in response.text

def test_root_serves_spa():
    """Root URL serves HTML dashboard with Lightweight Charts script tags embedded."""
    response = client.get("/")
    assert response.status_code == 200
    assert "LightweightCharts" in response.text
    assert '<div class="logo">NSE Quant App</div>' not in response.text
    assert "chart_paper_trade.js" in response.text
    assert "paper_terminal_dock.js" in response.text
    assert "paper_trade.css" in response.text


def test_paper_trading_static_assets_serving():
    """Validates that chart_paper_trade.js, paper_terminal_dock.js and paper_trade.css are served with HTTP 200."""
    js_res = client.get("/static/js/chart_paper_trade.js")
    assert js_res.status_code == 200
    assert "class ChartPaperTradeManager" in js_res.text
    assert "placeQuickOrder" in js_res.text
    assert "renderPositionLines" in js_res.text

    dock_res = client.get("/static/js/paper_terminal_dock.js")
    assert dock_res.status_code == 200
    assert "class PaperTerminalDock" in dock_res.text
    assert "renderPositionsTable" in dock_res.text
    assert "promptResetAccount" in dock_res.text

    css_res = client.get("/static/css/paper_trade.css")
    assert css_res.status_code == 200
    assert ".chart-quick-trade-bar" in css_res.text
    assert ".order-ticket-modal" in css_res.text
    assert ".paper-trading-dock" in css_res.text
    assert ".paper-dock-header" in css_res.text
    assert ".btn-deploy-paper" in css_res.text

    deploy_res = client.get("/static/js/backtest_paper_deploy.js")
    assert deploy_res.status_code == 200
    assert "class BacktestPaperDeployHelper" in deploy_res.text
    assert "deployFromConfig" in deploy_res.text
