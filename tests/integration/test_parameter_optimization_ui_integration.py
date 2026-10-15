"""
Integration Tests for Strategy Parameter Optimization Studio UI.
Validates subtab navigation, 2D Heatmap SVG canvas, Metric Switcher, 
3x3 Plateau Stability HUD, Walk-Forward Table, and 1-Click Deploy DOM contracts.
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
    db_path = str(tmp_path / "test_optimization_ui.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


# ============================================================================
# 1. Static Asset Serving & Index.html Script Integration
# ============================================================================

def test_static_asset_serving():
    """Verify that static/index.html and backtest_optimization_ui.js are properly served."""
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "backtest_optimization_ui.js" in root_resp.text

    script_resp = client.get("/static/js/backtest_optimization_ui.js")
    assert script_resp.status_code == 200
    assert "BacktestOptimizationController" in script_resp.text
    assert "renderHeatmap" in script_resp.text
    assert "renderStabilityHUD" in script_resp.text
    assert "renderWalkForwardHUD" in script_resp.text


# ============================================================================
# 2. Backtest Studio Subtab Navigation DOM Contract
# ============================================================================

def test_backtest_subtabs_navigation_contract():
    """Verify that Backtest Studio includes dedicated #btn-backtest-tab-optimize navigation."""
    ui_path = Path("static/js/backtest_ui.js")
    assert ui_path.exists()
    content = ui_path.read_text(encoding="utf-8")

    # Subtab bar container
    assert 'id="backtest-subtabs-nav"' in content
    assert 'class="subtabs-bar"' in content

    # Subtab buttons
    assert 'id="btn-backtest-tab-optimize"' in content
    assert 'data-subtab="optimize"' in content
    assert 'data-mode="optimize"' in content
    assert 'Parameter Optimization' in content

    # Retains backward compatibility for single and portfolio mode buttons
    assert 'id="btn-mode-single"' in content
    assert 'id="btn-mode-portfolio"' in content
    assert 'id="studio-mode-switcher"' in content


# ============================================================================
# 3. Optimization Studio Workspace Panel DOM Contract
# ============================================================================

def test_optimization_workspace_panel_contract():
    """Verify that #backtest-optimize-panel contains all required inputs, cards, and buttons."""
    ui_path = Path("static/js/backtest_ui.js")
    content = ui_path.read_text(encoding="utf-8")

    # Main panel
    assert 'id="backtest-optimize-panel"' in content
    assert 'class="studio-optimize-view-section hidden"' in content

    # Strategy selector & Preset chips
    assert 'id="opt-strategy-select"' in content
    assert 'id="opt-symbol-input"' in content
    assert 'data-strategy-preset="SMA_CROSS"' in content
    assert 'data-strategy-preset="RSI_REVERSION"' in content
    assert 'data-strategy-preset="BOLLINGER_BANDS"' in content
    assert 'data-strategy-preset="SUPERTREND"' in content
    assert 'data-strategy-preset="MACD"' in content

    # 2D Parameter Range Inputs
    assert 'id="opt-param1-name"' in content
    assert 'id="opt-param1-min"' in content
    assert 'id="opt-param1-max"' in content
    assert 'id="opt-param1-step"' in content

    assert 'id="opt-param2-name"' in content
    assert 'id="opt-param2-min"' in content
    assert 'id="opt-param2-max"' in content
    assert 'id="opt-param2-step"' in content

    # Combinations Counter & Split Slider
    assert 'id="opt-combinations-badge"' in content
    assert 'id="opt-comb-count"' in content
    assert 'id="opt-split-slider"' in content
    assert 'id="opt-split-val"' in content
    assert 'id="btn-run-optimization"' in content


# ============================================================================
# 4. 2D Heatmap Grid, Metric Switcher & Tooltip Contract
# ============================================================================

def test_heatmap_svg_and_metric_switcher_contract():
    """Verify that 2D Heatmap SVG canvas, metric switcher, and tooltip are declared."""
    ui_path = Path("static/js/backtest_ui.js")
    content = ui_path.read_text(encoding="utf-8")

    # Metric Switcher Buttons
    assert 'id="opt-metric-switcher"' in content
    assert 'id="btn-metric-sharpe"' in content
    assert 'data-metric="sharpe_ratio"' in content
    assert 'id="btn-metric-pnl"' in content
    assert 'data-metric="net_pnl"' in content
    assert 'id="btn-metric-drawdown"' in content
    assert 'data-metric="max_drawdown_pct"' in content
    assert 'id="btn-metric-winrate"' in content
    assert 'data-metric="win_rate"' in content

    # Heatmap Canvas & Tooltip
    assert 'id="opt-heatmap-svg"' in content
    assert 'id="opt-heatmap-tooltip"' in content
    assert 'id="opt-heatmap-container"' in content
    assert 'id="opt-execution-time"' in content
    assert 'id="opt-legend-min"' in content
    assert 'id="opt-legend-max"' in content


# ============================================================================
# 5. Stability HUD, Walk-Forward Table & 1-Click Deploy Contract
# ============================================================================

def test_stability_hud_and_walk_forward_contract():
    """Verify Stability HUD Card, Walk-Forward Table, and 1-Click Apply Button."""
    ui_path = Path("static/js/backtest_ui.js")
    content = ui_path.read_text(encoding="utf-8")

    # Stability HUD
    assert 'id="opt-stability-hud"' in content
    assert 'id="opt-stability-badge"' in content
    assert 'id="opt-stability-score"' in content
    assert 'id="opt-cliff-drop"' in content
    assert 'id="opt-optimal-params-summary"' in content

    # Walk-Forward HUD & Table
    assert 'id="opt-walk-forward-card"' in content
    assert 'id="opt-walk-forward-table"' in content
    assert 'id="opt-wfe-badge"' in content
    assert 'id="opt-is-split-date"' in content
    assert 'id="opt-is-net-pnl"' in content
    assert 'id="opt-oos-split-date"' in content
    assert 'id="opt-oos-net-pnl"' in content

    # 1-Click Deploy Button
    assert 'id="btn-apply-optimal-params"' in content
    assert 'Apply Optimal Parameters to Backtest' in content


# ============================================================================
# 6. Theme CSS Style Definitions Contract
# ============================================================================

def test_theme_css_optimization_styles_contract():
    """Verify that static/css/theme.css defines styles for heatmap, badges, and controls."""
    css_path = Path("static/css/theme.css")
    assert css_path.exists()
    content = css_path.read_text(encoding="utf-8")

    assert ".studio-optimize-view-section" in content
    assert ".opt-control-card" in content
    assert ".opt-preset-chip" in content
    assert ".opt-heatmap-card" in content
    assert ".opt-metric-btn" in content
    assert ".opt-heatmap-svg" in content
    assert ".heatmap-cell" in content
    assert ".opt-heatmap-tooltip" in content
    assert ".badge-robust" in content
    assert ".badge-moderate" in content
    assert ".badge-cliff" in content
    assert ".btn-apply-optimal" in content


# ============================================================================
# 7. JavaScript Controller Logic Contract
# ============================================================================

def test_javascript_controller_methods_contract():
    """Verify that backtest_optimization_ui.js exposes all required methods."""
    js_path = Path("static/js/backtest_optimization_ui.js")
    assert js_path.exists()
    content = js_path.read_text(encoding="utf-8")

    assert "class BacktestOptimizationController" in content
    assert "activateOptimizeTab" in content
    assert "deactivateOptimizeTab" in content
    assert "loadPresets" in content
    assert "syncStrategy" in content
    assert "updateCombinationCount" in content
    assert "runOptimization" in content
    assert "interpolateColor" in content
    assert "renderHeatmap" in content
    assert "renderStabilityHUD" in content
    assert "renderWalkForwardHUD" in content
    assert "applyOptimalParameters" in content
    assert "window.BacktestOptimizationController = BacktestOptimizationController" in content
