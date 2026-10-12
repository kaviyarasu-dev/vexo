import os
import re
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_index_html_has_study_modal_markup():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Trigger button in toolbar
    assert 'id="btn-open-studies"' in html
    assert 'class="tv-studies-btn"' in html
    assert 'fx</span> Indicators' in html

    # Modal container and components
    assert 'id="study-modal-backdrop"' in html
    assert 'id="study-modal"' in html
    assert 'id="study-search-input"' in html
    assert 'id="study-pills-bar"' in html
    assert 'id="study-create-new-btn"' in html
    assert 'id="study-create-modal"' in html
    assert 'id="create-study-form"' in html
    assert 'id="study-items-list"' in html
    assert 'id="study-detail-bar"' in html

    # CSS & Script includes
    assert '/static/css/study_dialog.css' in html
    assert '/static/js/study_dialog.js' in html


def test_study_dialog_css_exists_and_styled():
    with open("static/css/study_dialog.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert ".tv-study-modal-backdrop" in css
    assert ".tv-study-modal" in css
    assert ".tv-studies-btn" in css
    assert ".tv-study-pill-btn" in css
    assert ".tv-study-sidebar" in css
    assert ".tv-study-create-btn" in css
    assert ".tv-study-delete-btn" in css
    assert ".custom-badge" in css
    assert ".tv-study-create-dialog" in css


def test_study_dialog_js_syntax_and_exports():
    with open("static/js/study_dialog.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "window.openStudyDialog = openStudyDialog" in js
    assert "window.closeStudyDialog = closeStudyDialog" in js
    assert "window.openCreateStudyModal = openCreateStudyModal" in js
    assert "window.confirmAndDeleteStudy = confirmAndDeleteStudy" in js
    assert "fetchCatalog" in js
    assert "filterStudies" in js


def test_study_catalog_api_full_profiles():
    res = client.get("/api/v1/studies/catalog?sub_category=profiles")
    assert res.status_code == 200
    data = res.json()["data"]
    
    expected_names = [
        "Time price opportunity",
        "Session time price opportunity",
        "Auto anchored volume profile",
        "Fixed range volume profile",
        "Periodic volume profile",
        "Session volume profile",
        "Session volume profile HD",
        "Visible range volume profile",
    ]
    catalog_names = [p["name"] for p in data]
    for expected in expected_names:
        assert expected in catalog_names, f"Expected '{expected}' in catalog"


def test_study_catalog_api_search_filter():
    res = client.get("/api/v1/studies/catalog?query=rsi")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 2
    assert any("rsi" in d["id"] for d in data)


def test_study_catalog_api_custom_endpoints():
    payload = {
        "id": "custom_test_strat_123",
        "name": "Custom RSI Breakout Strategy",
        "section": "personal",
        "category": "technicals",
        "sub_category": "strategies",
        "description": "Integration test custom strategy",
        "author": "Trader",
        "overlay": False,
        "default_inputs": {"period": 14, "overbought": 80},
        "tags": ["custom", "rsi"],
        "is_custom": True,
        "base_type": "strat_rsi_reversal"
    }
    # Create
    post_res = client.post("/api/v1/studies/custom", json=payload)
    assert post_res.status_code == 200
    created = post_res.json()["data"]
    assert created["id"] == "custom_test_strat_123"
    assert created["is_custom"] is True
    assert created["base_type"] == "strat_rsi_reversal"

    # Query catalog
    cat_res = client.get("/api/v1/studies/catalog?sub_category=strategies")
    assert cat_res.status_code == 200
    cat_data = cat_res.json()["data"]
    assert any(s["id"] == "custom_test_strat_123" for s in cat_data)

    # Delete
    del_res = client.delete("/api/v1/studies/custom/custom_test_strat_123")
    assert del_res.status_code == 200
    assert del_res.json()["data"] is True


def test_create_modal_scrolling_and_alignment_structure():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # The create modal must be outside study-modal-backdrop so it is not clipped by overflow:hidden
    backdrop_close_idx = html.find('id="study-modal-backdrop"')
    assert backdrop_close_idx != -1
    # Check that </section> and </div> closing study-modal-backdrop occur before study-create-modal
    create_modal_idx = html.find('id="study-create-modal"')
    assert create_modal_idx != -1

    # Check structure: fixed header, scrollable body, fixed footer
    assert 'class="tv-study-create-header"' in html
    assert 'class="tv-study-create-body"' in html
    assert 'class="tv-study-create-actions"' in html
    assert 'id="create-modal-badge"' in html
    assert 'id="create-modal-title"' in html
    assert 'id="create-study-category"' in html
    assert 'id="create-study-base"' in html
    assert 'id="create-param-period-row"' in html
    assert 'id="create-param-secondary-row"' in html
    assert 'id="create-param-style-row"' in html
    assert 'class="tv-color-picker-box"' in html
    assert 'class="tv-radio-group"' in html
    assert 'id="create-study-auto-apply"' in html


def test_selectbox_hover_style_reset():
    with open("static/css/theme.css", "r", encoding="utf-8") as f:
        theme_css = f.read()

    with open("static/css/study_dialog.css", "r", encoding="utf-8") as f:
        dialog_css = f.read()

    # Verify no cyan hover arrow distortion in theme.css
    assert "stroke='%2338bdf8'" not in theme_css

    # Verify select hover reset exists
    assert "select:hover" in theme_css
    assert ".tv-study-create-form .tv-input-select:hover" in dialog_css

    # Verify scrollable body and fixed container styles
    assert ".tv-study-create-body" in dialog_css
    assert "overflow-y: auto" in dialog_css
    assert "max-height: calc(100vh - 48px)" in dialog_css


