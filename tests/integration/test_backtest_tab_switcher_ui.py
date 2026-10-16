"""
Integration Tests for Backtest Studio 3-Tab Switcher & Section Visibility.
Validates:
1. CSS display rules: .hidden and explicit section .hidden rules exist with display: none !important.
2. BacktestUI unified switchMode(mode) implementation across 'single', 'portfolio', and 'optimize'.
3. Event binding on all 3 subtab buttons (#btn-mode-single, #btn-mode-portfolio, #btn-backtest-tab-optimize).
4. Single-instance lifecycle in app.js and backtest_ui.js via window.backtestInitialized.
"""

import pytest
from pathlib import Path


def test_css_hidden_rules_contract():
    """Verify that theme.css defines .hidden utility and explicit section rules."""
    css_path = Path("static/css/theme.css")
    assert css_path.exists(), "theme.css must exist"
    css = css_path.read_text(encoding="utf-8")

    # Global utility
    assert ".hidden {" in css
    assert "display: none !important;" in css

    # Specific section overrides
    assert ".studio-portfolio-view-section.hidden" in css
    assert ".studio-optimize-view-section.hidden" in css
    assert ".studio-universe-section.hidden" in css
    assert ".studio-current-view-section.hidden" in css
    assert ".config-card.hidden" in css
    assert "#section-portfolio-view.hidden" in css
    assert "#backtest-optimize-panel.hidden" in css


def test_backtest_ui_unified_switch_mode_implementation():
    """Verify that BacktestUI defines a unified switchMode supporting all 3 modes."""
    js_path = Path("static/js/backtest_ui.js")
    assert js_path.exists(), "backtest_ui.js must exist"
    js = js_path.read_text(encoding="utf-8")

    # Method signature and activeMode assignment
    assert "switchMode(mode) {" in js
    assert "this.activeMode = mode;" in js

    # Subtab button active toggling
    assert "btn.classList.toggle('active', btnMode === mode);" in js

    # Card and section visibility toggling across single, portfolio, and optimize
    assert "cardSingleAsset.classList.toggle('hidden', mode === 'portfolio');" in js
    assert "cardPortfolioUniverse.classList.toggle('hidden', mode !== 'portfolio');" in js
    assert "cardPortfolioAllocation.classList.toggle('hidden', mode !== 'portfolio');" in js

    assert "secCurrentMatches.classList.toggle('hidden', mode !== 'single');" in js
    assert "secPastMatches.classList.toggle('hidden', mode !== 'single');" in js
    assert "secCurrentView.classList.toggle('hidden', mode !== 'single');" in js
    assert "secPortfolioView.classList.toggle('hidden', mode !== 'portfolio');" in js
    assert "panelOptimize.classList.toggle('hidden', mode !== 'optimize');" in js

    # Initial mode activation in init()
    assert "this.switchMode('single');" in js


def test_subtabs_event_binding_contract():
    """Verify that subtab buttons have click events wired to switchMode."""
    js_path = Path("static/js/backtest_ui.js")
    js = js_path.read_text(encoding="utf-8")

    # Selector and event loop in bindEvents
    assert "studio-mode-switcher" in js
    assert "this.switchMode(mode);" in js


def test_portfolio_controller_delegation():
    """Verify that PortfolioBacktestController delegates mode switching to parent BacktestUI."""
    port_js_path = Path("static/js/portfolio_backtest_ui.js")
    assert port_js_path.exists()
    port_js = port_js_path.read_text(encoding="utf-8")

    # Must delegate to this.ui.switchMode
    assert "this.ui.switchMode(mode)" in port_js
    # Guarded prototype definition
    assert "BacktestUI.prototype.switchMode" in port_js


def test_optimization_controller_delegation():
    """Verify that BacktestOptimizationController coordinates through parent BacktestUI."""
    opt_js_path = Path("static/js/backtest_optimization_ui.js")
    assert opt_js_path.exists()
    opt_js = opt_js_path.read_text(encoding="utf-8")

    # activateOptimizeTab delegates to switchMode('optimize')
    assert "this.ui.switchMode('optimize')" in opt_js
    assert "this.ui.switchMode" in opt_js

    # Must NOT bind btn-mode-portfolio to deactivateOptimizeTab (which caused reverting to single)
    assert "btnPortfolio.addEventListener" not in opt_js
    assert "btnSingle.addEventListener" not in opt_js


def test_app_lifecycle_single_instance_guard():
    """Verify that app.js and backtest_ui.js prevent double instantiation and enforce active mode."""
    app_js_path = Path("static/js/app.js")
    assert app_js_path.exists()
    app_js = app_js_path.read_text(encoding="utf-8")

    bt_js_path = Path("static/js/backtest_ui.js")
    assert bt_js_path.exists()
    bt_js = bt_js_path.read_text(encoding="utf-8")

    # Both must check/set window.backtestInitialized
    assert "window.backtestInitialized = true;" in bt_js
    assert "if (!window.backtestInitialized && typeof BacktestUI === 'function')" in app_js
    assert "window.backtestUI.switchMode(mode);" in app_js
