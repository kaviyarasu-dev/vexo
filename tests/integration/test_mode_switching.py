import pytest
from pathlib import Path

def test_ux_mode_controller_exists():
    """Verify ux_mode_controller.js is generated for Simple/Pro switching."""
    js_path = Path("static/js/ux_mode_controller.js")
    assert js_path.exists()
    
def test_onboarding_tour_exists():
    """Verify onboarding_tour.js is generated."""
    js_path = Path("static/js/onboarding_tour.js")
    assert js_path.exists()

def test_modes_css_exists():
    css_path = Path("static/css/modes.css")
    assert css_path.exists()

def test_translation_registry_exists():
    js_path = Path("static/js/translation_registry.js")
    assert js_path.exists()
