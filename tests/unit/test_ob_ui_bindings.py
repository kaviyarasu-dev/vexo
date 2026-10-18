"""Unit tests for OrderBlock UI bindings, Canvas overlay contracts, and Quick-View sheet.
Tests:
- Syntax and contract verification for static/js/chart_orderblock_overlay.js
- Syntax and contract verification for static/js/orderblock_sheet.js
- DOM element contract in static/index.html
- High-DPI scaling, color palette tokens, and 5-minute timeframe gate
"""

import os
import subprocess
import pytest


def test_overlay_js_file_syntax():
    """Verify chart_orderblock_overlay.js exists and passes node syntax check."""
    path = "static/js/chart_orderblock_overlay.js"
    assert os.path.exists(path), f"{path} must exist"
    res = subprocess.run(["node", "-c", path], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error in {path}: {res.stderr}"


def test_sheet_js_file_syntax():
    """Verify orderblock_sheet.js exists and passes node syntax check."""
    path = "static/js/orderblock_sheet.js"
    assert os.path.exists(path), f"{path} must exist"
    res = subprocess.run(["node", "-c", path], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error in {path}: {res.stderr}"


def test_overlay_palette_and_timeframe_gate():
    """Verify chart_orderblock_overlay.js contains required SMC design tokens and 5m timeframe gate."""
    path = "static/js/chart_orderblock_overlay.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Color tokens per spec
    assert "rgba(34, 197, 94" in content, "Must include green bullish zone styling"
    assert "rgba(239, 68, 68" in content, "Must include red bearish zone styling"
    assert "rgba(148, 163, 184" in content, "Must include gray mitigated zone styling"

    # Timeframe gate
    assert "5m" in content, "Overlay must gate rendering to 5m timeframe"
    assert "devicePixelRatio" in content, "Must handle high-DPI retina display scaling"


def test_quick_sheet_dom_and_event_handling():
    """Verify orderblock_sheet.js contains container binding, close handlers, and switch chart callback."""
    path = "static/js/orderblock_sheet.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "orderblock-quick-sheet" in content, "Must reference #orderblock-quick-sheet container"
    assert "Escape" in content or "keydown" in content, "Must handle Escape key to dismiss drawer"
    assert "openSheet" in content or "open" in content, "Must expose sheet opening function"


def test_chart_js_hooks():
    """Verify chart.js has hooks for orderBlockOverlay and switchChartSymbol."""
    path = "static/js/chart.js"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "orderBlockOverlay" in content, "chart.js must notify orderBlockOverlay"
    assert "switchChartSymbol" in content, "chart.js must export switchChartSymbol"


def test_alignment_popover_and_drawer_bindings():
    """Verify index.html and orderblock_dashboard.js contracts for alignment popover and drawer click."""
    html_path = "static/index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="chart-alignment-badge"' in html, "index.html must have #chart-alignment-badge"
    assert 'id="chart-alignment-popover"' in html, "index.html must have #chart-alignment-popover card"
    assert 'id="popover-checklist"' in html, "index.html must have #popover-checklist"
    assert 'id="popover-advice-banner"' in html, "index.html must have #popover-advice-banner"

    js_path = "static/js/orderblock_dashboard.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "bindAlignmentPopoverAndDrawer" in js, "dashboard must bind hover popover and click drawer"
    assert "renderAlignmentPopover" in js, "dashboard must render popover card"
    assert "openOrderBlockSheet" in js, "badge click must invoke openOrderBlockSheet"
    assert "details" in js, "computeAlignment must provide details"
