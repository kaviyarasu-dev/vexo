import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_index_html_contains_quick_trade_elements():
    """Validates that static/index.html includes paper trading stylesheets, scripts, and chart containers."""
    res = client.get("/static/index.html")
    assert res.status_code == 200
    html = res.text

    assert 'href="/static/css/paper_trade.css' in html
    assert 'src="/static/js/chart_paper_trade.js' in html
    assert 'id="chart-container"' in html


def test_chart_paper_trade_js_contract():
    """Validates that chart_paper_trade.js exports expected interfaces and handles DOM."""
    res = client.get("/static/js/chart_paper_trade.js")
    assert res.status_code == 200
    content = res.text

    # Core class
    assert "class ChartPaperTradeManager" in content

    # Methods required by Plan 02-001
    assert "placeQuickOrder" in content
    assert "renderPositionLines" in content
    assert "clearPriceLines" in content
    assert "updateLTP" in content
    assert "openOrderTicket" in content
    assert "closeOrderTicket" in content
    assert "onSymbolOrCandlesChanged" in content

    # Endpoints called
    assert "/api/v1/paper-trading/orders" in content
    assert "/api/v1/paper-trading/positions" in content
    assert "/api/v1/paper-trading/account" in content

    # Lightweight Charts price lines styling
    assert "#2962FF" in content  # Entry line color
    assert "#089981" in content  # Take profit color
    assert "#F23645" in content  # Stop loss color


def test_paper_trade_css_rules():
    """Validates that paper_trade.css includes required design system selectors."""
    res = client.get("/static/css/paper_trade.css")
    assert res.status_code == 200
    css = res.text

    assert ".chart-quick-trade-bar" in css
    assert "right: 80px;" in css  # Offset by 80px to clear the right-hand price scale numbers
    assert ".quick-buy-btn" in css
    assert ".quick-sell-btn" in css
    assert ".quick-qty-stepper" in css
    assert ".order-ticket-modal" in css
    assert ".paper-toast" in css
    assert ".paper-trading-dock" in css
    assert ".paper-dock-header" in css
    assert ".paper-table" in css
    assert ".btn-square-off" in css


def test_paper_terminal_dock_contract():
    """Validates that paper_terminal_dock.js exports expected class, methods, and DOM bindings."""
    res = client.get("/static/js/paper_terminal_dock.js")
    assert res.status_code == 200
    content = res.text

    assert "class PaperTerminalDock" in content
    assert "refreshAll" in content
    assert "refreshPositions" in content
    assert "closePosition" in content
    assert "promptResetAccount" in content
    assert "renderPositionsTable" in content
    assert "renderOrdersTable" in content
    assert "renderHistoryTable" in content
    assert "renderStrategiesTable" in content

    # Endpoints called
    assert "/api/v1/paper-trading/positions" in content
    assert "/api/v1/paper-trading/orders" in content
    assert "/api/v1/paper-trading/history" in content
    assert "/api/v1/paper-trading/auto-strategies" in content
    assert "/api/v1/paper-trading/account/reset" in content
