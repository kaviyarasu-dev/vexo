"""
Integration Tests for Backtest Studio Dual-Mode Switcher, Portfolio Analytics & Asset Contribution Breakdown UI.
Verifies Plan 03-001 deliverables:
- Static script serving: static/js/portfolio_backtest_ui.js
- HTML integration in static/index.html
- Dual-Mode Switcher, Universe Chips & Configurator DOM contract in static/js/backtest_ui.js
- Visual styling for switcher, chips, and contribution bars in static/css/theme.css
- End-to-end Portfolio API contract & data verification (Lightweight Charts curves, Asset Contributions, Trades)
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
    db_path = str(tmp_path / "test_portfolio_studio_ui.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_static_portfolio_backtest_ui_served():
    """Verify that portfolio_backtest_ui.js is served with 200 OK and exposes the required controller interface."""
    resp = client.get("/static/js/portfolio_backtest_ui.js")
    assert resp.status_code == 200
    js_text = resp.text

    # Controller Class Definition
    assert "class PortfolioBacktestController" in js_text

    # Core Methods
    assert "init()" in js_text or "init(" in js_text
    assert "bindModeSwitcher()" in js_text
    assert "switchMode(" in js_text
    assert "loadUniverses()" in js_text
    assert "renderUniverseChips()" in js_text
    assert "runPortfolioBacktest()" in js_text
    assert "renderPortfolioCharts(" in js_text
    assert "renderAssetContributionTable(" in js_text
    assert "renderPortfolioHeatmap(" in js_text
    assert "renderPortfolioTradeLedger(" in js_text
    assert "exportPortfolioTradesCSV()" in js_text
    assert "resizeCharts()" in js_text

    # Global exposures
    assert "window.PortfolioBacktestController = PortfolioBacktestController" in js_text
    assert "BacktestUI.prototype.switchMode" in js_text


def test_index_html_includes_portfolio_script():
    """Verify that static/index.html includes the portfolio_backtest_ui.js script tag."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    assert 'src="/static/js/portfolio_backtest_ui.js' in content

    # Verify root endpoint serves this HTML
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "portfolio_backtest_ui.js" in root_resp.text


def test_backtest_ui_dom_contract():
    """Verify that static/js/backtest_ui.js includes the required Dual-Mode Switcher and Portfolio DOM structures."""
    ui_path = Path("static/js/backtest_ui.js")
    assert ui_path.exists()
    content = ui_path.read_text(encoding="utf-8")

    # 1. Dual-Mode Switcher
    assert 'id="studio-mode-switcher"' in content
    assert 'id="btn-mode-single"' in content
    assert 'id="btn-mode-portfolio"' in content
    assert 'data-mode="single"' in content
    assert 'data-mode="portfolio"' in content

    # 2. Configurator Cards
    assert 'id="card-single-asset"' in content
    assert 'id="card-single-risk"' in content
    assert 'id="card-portfolio-universe"' in content
    assert 'id="card-portfolio-allocation"' in content

    # 3. Portfolio Inputs
    assert 'id="portfolio-universe-chips"' in content
    assert 'id="portfolio-custom-symbols-box"' in content
    assert 'id="portfolio-max-positions"' in content
    assert 'id="portfolio-sizing-model"' in content
    assert 'id="portfolio-ranking-metric"' in content
    assert 'id="portfolio-stop-loss"' in content
    assert 'id="portfolio-take-profit"' in content

    # 4. Results Section & Subtabs
    assert 'id="section-portfolio-view"' in content
    assert 'id="portfolio-alert-banner"' in content
    assert 'id="portfolio-headline-net-pnl"' in content
    assert 'id="portfolio-subtabs"' in content
    assert 'id="portfolio-subtab-overview"' in content
    assert 'id="portfolio-subtab-contributions"' in content
    assert 'id="portfolio-subtab-heatmap"' in content
    assert 'id="portfolio-subtab-trades"' in content

    # 5. Charts & Tables
    assert 'id="portfolio-equity-chart"' in content
    assert 'id="portfolio-drawdown-chart"' in content
    assert 'id="table-asset-contributions"' in content
    assert 'id="portfolio-monthly-heatmap-container"' in content
    assert 'id="portfolio-trades-data-table"' in content


def test_theme_css_portfolio_styles():
    """Verify that static/css/theme.css includes modern visual styles for portfolio backtesting."""
    resp = client.get("/static/css/theme.css")
    assert resp.status_code == 200
    css = resp.text

    # Switcher & Buttons
    assert ".studio-mode-switcher" in css
    assert ".mode-toggle-btn" in css
    assert ".mode-toggle-btn.active" in css

    # Universe Chips
    assert ".universe-chips-group" in css
    assert ".universe-chip" in css
    assert ".universe-chip.active" in css
    assert ".badge-count-pill" in css

    # Sizing & Custom Symbols
    assert ".custom-symbol-tag" in css
    assert ".portfolio-metrics-grid" in css
    assert ".bullet-portfolio-equity" in css

    # Asset Contribution Table & Visual Bars
    assert ".asset-contribution-table" in css
    assert ".contribution-bar-wrap" in css
    assert ".contribution-bar" in css
    assert ".contribution-bar.bar-gain" in css
    assert ".contribution-bar.bar-loss" in css

    # Alert Box
    assert ".portfolio-alert-box" in css
    assert ".btn-alert-retry" in css


def test_portfolio_universes_api_integration():
    """Verify GET /api/v1/backtest/portfolio/universes returns valid predefined universes for UI chips."""
    resp = client.get("/api/v1/backtest/portfolio/universes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    universes = data["universes"]
    assert len(universes) >= 3

    ids = [u["id"] for u in universes]
    assert "NIFTY_50" in ids
    assert "NIFTY_NEXT_50" in ids
    assert "NIFTY_MIDCAP_150" in ids

    nifty50 = next(u for u in universes if u["id"] == "NIFTY_50")
    assert nifty50["name"] == "NIFTY 50"
    assert nifty50["count"] >= 40


def test_portfolio_backtest_run_api_contract():
    """Verify POST /api/v1/backtest/portfolio/run provides full payload for charts, KPI cards, and contribution table."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "PREDEFINED",
        "universe_name": "NIFTY_50",
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 1000000.0,
        "max_open_positions": 5,
        "sizing_model": "EQUAL_WEIGHT",
        "sizing_val": 20.0,
        "ranking_metric": "AUTO",
        "slippage_bps": 5.0,
        "parameters": {
            "short_window": 10,
            "long_window": 30
        }
    }

    resp = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Backtest meta
    assert data["status"] == "COMPLETED"
    assert data["strategy"] == "SMA_CROSS"
    assert data["universe_name"] == "NIFTY_50"
    assert len(data["symbols_tested"]) > 0

    # Metrics
    metrics = data["metrics"]
    assert "cagr" in metrics
    assert "net_profit" in metrics
    assert "final_equity" in metrics
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "win_rate" in metrics
    assert "profit_factor" in metrics
    assert "total_trades" in metrics
    assert "total_statutory_costs" in metrics
    assert "avg_exposure_ratio" in metrics

    # Equity & Benchmark Curves for Lightweight Charts
    equity_curve = data["equity_curve"]
    assert len(equity_curve) > 0
    first_pt = equity_curve[0]
    assert "timestamp" in first_pt
    assert "equity" in first_pt
    assert "cash" in first_pt
    assert "invested" in first_pt
    assert "exposure_ratio" in first_pt

    benchmark_curve = data["benchmark_curve"]
    assert len(benchmark_curve) > 0
    assert "timestamp" in benchmark_curve[0]
    assert "value" in benchmark_curve[0]

    # Asset Contribution Breakdown Table Contract
    asset_contributions = data["asset_contributions"]
    assert isinstance(asset_contributions, list)
    assert len(asset_contributions) > 0
    sample_c = asset_contributions[0]
    assert "symbol" in sample_c
    assert "trade_count" in sample_c
    assert "win_rate" in sample_c
    assert "net_pnl" in sample_c
    assert "alpha_contribution_pct" in sample_c

    # Monthly Returns Heatmap
    assert isinstance(data["monthly_returns"], dict)

    # Trades Ledger
    assert isinstance(data["trades"], list)


def test_portfolio_custom_basket_run():
    """Verify portfolio backtest execution using custom symbol basket."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "CUSTOM",
        "symbols": ["NSE:RELIANCE-EQ", "NSE:TCS-EQ"],
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30",
        "initial_capital": 500000.0,
        "max_open_positions": 2,
        "sizing_model": "FIXED_AMOUNT",
        "sizing_val": 200000.0,
        "ranking_metric": "AUTO",
        "slippage_bps": 5.0,
        "parameters": {
            "short_window": 10,
            "long_window": 30
        }
    }

    resp = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["universe_name"] == "CUSTOM"
    assert set(data["symbols_tested"]) == {"NSE:RELIANCE-EQ", "NSE:TCS-EQ"}


def test_portfolio_custom_basket_validation_error():
    """Verify 400 Bad Request when custom universe has no valid symbols."""
    payload = {
        "strategy": "SMA_CROSS",
        "universe_type": "CUSTOM",
        "symbols": [],
        "timeframe": "1D",
        "start_date": "2023-01-01",
        "end_date": "2023-06-30"
    }

    resp = client.post("/api/v1/backtest/portfolio/run", json=payload)
    assert resp.status_code == 400
