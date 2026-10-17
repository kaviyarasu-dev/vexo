"""Unit tests for OrderBlock In-Tile Volume Profile UI and Theme Styles.
Verifies DOM contract, CSS classes, Point of Control (POC) gold highlight (#F5AC00),
active price marker, and adaptive grid rules.
"""

from pathlib import Path
import pytest


def test_orderblock_dashboard_contract():
    """Verify orderblock_dashboard.js implements in-tile profile bars and price marker."""
    js_path = Path("static/js/orderblock_dashboard.js")
    assert js_path.exists(), "static/js/orderblock_dashboard.js must exist"
    
    content = js_path.read_text(encoding="utf-8")
    
    # Check for in-tile profile markup generation
    assert "tile-profile-wrap" in content, "Dashboard JS must create tile-profile-wrap container"
    assert "profile-bar" in content, "Dashboard JS must render profile-bar elements"
    assert "profile-price-marker" in content, "Dashboard JS must render profile-price-marker indicator"
    assert "poc" in content.lower(), "Dashboard JS must highlight Point of Control (POC)"
    assert "mini_buckets" in content, "Dashboard JS must inspect mini_buckets from profile_summary"


def test_theme_css_tile_profile_tokens():
    """Verify theme.css contains complete design system tokens for in-tile profile and grid."""
    css_path = Path("static/css/theme.css")
    assert css_path.exists(), "static/css/theme.css must exist"

    content = css_path.read_text(encoding="utf-8")

    # Check for core container and element classes
    assert ".tile-profile-wrap" in content, "theme.css must define .tile-profile-wrap"
    assert ".profile-bar" in content, "theme.css must define .profile-bar"
    assert ".profile-price-marker" in content, "theme.css must define .profile-price-marker"
    
    # Check for exact POC gold color token #F5AC00
    assert "#F5AC00" in content.upper() or "#f5ac00" in content.lower(), "theme.css must use POC gold highlight #F5AC00"
    
    # Check for adaptive grid styling
    assert "orderblock-tile" in content or "tile-board" in content, "theme.css must define orderblock tile grid"
