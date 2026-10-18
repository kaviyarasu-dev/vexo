"""Unit and integration test suite for frontend AI prediction corridor and HUD bindings."""

import os
import re
import pytest


def read_file_utf8(path: str) -> str:
    """Helper to safely read file with UTF-8 encoding across operating systems."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_html_predictive_hud_and_scripts():
    """Verifies that static/index.html mounts the predictive HUD and loads overlay scripts."""
    html_path = os.path.join("static", "index.html")
    assert os.path.exists(html_path), "static/index.html must exist"
    
    html = read_file_utf8(html_path)
    
    # HUD container and elements
    assert 'id="predictive-hud"' in html, "Missing #predictive-hud container in index.html"
    assert 'id="hud-regime-label"' in html, "Missing #hud-regime-label in index.html"
    assert 'id="hud-dir-badge"' in html, "Missing #hud-dir-badge in index.html"
    assert 'id="hud-range-corridor"' in html, "Missing #hud-range-corridor in index.html"
    
    # Script tag for chart predictor overlay
    assert 'chart_predictor_overlay.js' in html, "Missing chart_predictor_overlay.js script tag in index.html"


def test_css_predictive_hud_styling():
    """Verifies that static/css/theme.css defines required responsive states for Predictive HUD."""
    css_path = os.path.join("static", "css", "theme.css")
    assert os.path.exists(css_path), "static/css/theme.css must exist"
    
    css = read_file_utf8(css_path)
    
    assert '.predictive-hud' in css, "Missing .predictive-hud base class in theme.css"
    assert '.predictive-hud.bullish' in css, "Missing .predictive-hud.bullish styling in theme.css"
    assert '.predictive-hud.bearish' in css, "Missing .predictive-hud.bearish styling in theme.css"
    assert '.predictive-hud.neutral' in css or '.predictive-hud.choppy' in css, "Missing neutral/choppy styling in theme.css"
    assert '.predictive-hud.insufficient' in css, "Missing insufficient data styling in theme.css"
    
    # Color standards check
    assert '#089981' in css, "Missing institutional emerald green (#089981)"
    assert '#F23645' in css, "Missing institutional crimson red (#F23645)"
    assert '#F5AC00' in css, "Missing institutional gold/amber (#F5AC00)"


def test_js_chart_predictor_overlay_structure():
    """Verifies static/js/chart_predictor_overlay.js contains required canvas architecture and corridor methods."""
    js_path = os.path.join("static", "js", "chart_predictor_overlay.js")
    assert os.path.exists(js_path), "static/js/chart_predictor_overlay.js must exist"
    
    code = read_file_utf8(js_path)
    
    # Core class and canvas ID
    assert 'class ChartPredictorOverlay' in code, "Missing ChartPredictorOverlay class"
    assert 'chart-predictor-canvas' in code, "Missing chart-predictor-canvas ID"
    
    # Device pixel ratio scaling
    assert 'devicePixelRatio' in code, "Missing window.devicePixelRatio scaling"
    
    # Multi-quantile boundaries & corridor rendering
    assert 'renderCorridor' in code, "Missing renderCorridor method"
    assert 'setLineDash' in code, "Missing dashed line styling for quantile boundaries"
    assert 'createLinearGradient' in code, "Missing gradient fill for corridor"
    
    # Quantile tags
    assert 'Q90' in code, "Missing Q90 tag"
    assert 'Q50' in code, "Missing Q50 tag"
    assert 'Q10' in code, "Missing Q10 tag"
    
    # Global instance exports
    assert 'window.chartPredictorOverlay' in code, "Missing window.chartPredictorOverlay export"


def test_js_chart_wiring_and_graceful_fallback():
    """Verifies static/js/chart.js wires prediction fetch lifecycle and graceful ATR fallback."""
    chart_js_path = os.path.join("static", "js", "chart.js")
    assert os.path.exists(chart_js_path), "static/js/chart.js must exist"
    
    code = read_file_utf8(chart_js_path)
    
    # Prediction fetch lifecycle function
    assert 'fetchPredictionForCurrentChart' in code, "Missing fetchPredictionForCurrentChart in chart.js"
    assert '/api/v1/predict/candle' in code, "Missing /api/v1/predict/candle API call in chart.js"
    
    # Graceful fallback assertion
    assert 'Insufficient Data' in code, "Missing Insufficient Data handling in chart.js"
    assert '200' in code, "Missing 200 bars threshold check in chart.js"
    assert 'updateFallback' in code, "Missing updateFallback invocation in chart.js"
