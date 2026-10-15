"""
Integration Tests for Journal Analytics UI: Monthly Green/Red Wall Calendar, Diagnostics Dashboard & Tabbed Workspace.
Verifies Plan 03-001 deliverables:
- Static script serving: static/js/journal_analytics.js
- HTML DOM contract in static/index.html (Subtab bar, Calendar Grid, 6 Monthly KPIs, Diagnostics Cards, Import Modal)
- Theme CSS styling for wall calendar grid, win/loss day cells, weekly bars, diagnostics meters, and import modal
- API contract integration for GET /api/v1/journal/calendar, GET /api/v1/journal/diagnostics, and POST /api/v1/journal/import
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
    """Isolated database fixture to prevent DuckDB writer lock contention."""
    db_path = str(tmp_path / "test_journal_analytics_ui.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_static_journal_analytics_js_served():
    """Verify that journal_analytics.js is served with 200 OK and exposes the required controller interface."""
    resp = client.get("/static/js/journal_analytics.js")
    assert resp.status_code == 200
    js_text = resp.text

    # Controller Class Definition
    assert "class JournalAnalyticsController" in js_text

    # Core Methods
    assert "init()" in js_text or "init(" in js_text
    assert "switchSubtab(" in js_text
    assert "loadCalendarMonth(" in js_text
    assert "renderCalendar()" in js_text
    assert "renderMonthlyKPIs(" in js_text
    assert "loadDiagnostics()" in js_text
    assert "renderDiagnostics()" in js_text
    assert "filterTradesByDate(" in js_text
    assert "clearDateFilter()" in js_text
    assert "bindImportModal()" in js_text
    assert "detectBrokerFormat(" in js_text
    assert "executeImport()" in js_text

    # Global window exposure
    assert "window.JournalAnalyticsController = JournalAnalyticsController" in js_text


def test_index_html_includes_journal_analytics_script():
    """Verify that static/index.html includes the journal_analytics.js script tag."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    assert 'src="/static/js/journal_analytics.js"' in content

    # Verify root endpoint serves this HTML
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "journal_analytics.js" in root_resp.text


def test_index_html_journal_tabbed_workspace_dom_contract():
    """Verify that static/index.html includes all DOM components required by Plan 03-001."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    # 1. Subtabs Navigation Bar
    assert 'id="journal-subtabs-nav"' in content
    assert 'id="btn-journal-tab-calendar"' in content
    assert 'id="btn-journal-tab-diagnostics"' in content
    assert 'id="btn-journal-tab-trades"' in content
    assert 'id="btn-journal-tab-mistakes"' in content

    # 2. Subpanel 1: Monthly Wall Calendar
    assert 'id="journal-calendar-panel"' in content
    assert 'id="btn-calendar-prev"' in content
    assert 'id="btn-calendar-next"' in content
    assert 'id="btn-calendar-today"' in content
    assert 'id="calendar-month-title"' in content
    assert 'id="calendar-kpis-grid"' in content
    assert 'id="cal-kpi-net-pnl"' in content
    assert 'id="cal-kpi-win-loss-days"' in content
    assert 'id="cal-kpi-win-day-pct"' in content
    assert 'id="cal-kpi-win-streak"' in content
    assert 'id="cal-kpi-loss-streak"' in content
    assert 'id="cal-kpi-avg-win-loss"' in content
    assert 'id="journal-calendar-grid"' in content

    # 3. Subpanel 2: Quantitative Diagnostics Panel
    assert 'id="journal-diagnostics-panel"' in content
    assert 'id="diag-tod-container"' in content
    assert 'id="diag-direction-container"' in content
    assert 'id="diag-duration-container"' in content
    assert 'id="diag-instrument-container"' in content

    # 4. Subpanel 3: Detailed Trade Log with Date Filter Indicator
    assert 'id="journal-trades-panel"' in content
    assert 'id="journal-date-filter-indicator"' in content
    assert 'id="journal-date-filter-text"' in content
    assert 'id="btn-clear-date-filter"' in content
    assert 'id="journal-trades-table"' in content
    assert 'id="equity-curve-chart"' in content

    # 5. Subpanel 4: Psychological Mistake Cloud
    assert 'id="journal-mistakes-panel"' in content
    assert 'id="mistake-cloud"' in content
    assert 'id="journal-mistake-cost-badge"' in content

    # 6. Multi-Broker Import Modal
    assert 'id="import-tradebook-modal"' in content
    assert 'id="tradebook-dropzone"' in content
    assert 'id="tradebook-modal-file-input"' in content
    assert 'id="import-detected-broker-badge"' in content
    assert 'id="btn-modal-do-import"' in content
    assert 'id="btn-modal-cancel-import"' in content


def test_theme_css_journal_analytics_styles():
    """Verify that static/css/theme.css defines styles for calendar grid, day cells, and diagnostics meters."""
    css_path = Path("static/css/theme.css")
    assert css_path.exists()
    css_text = css_path.read_text(encoding="utf-8")

    # Subtab & Panels
    assert ".journal-subtab" in css_text
    assert ".journal-subpanel" in css_text

    # Calendar Grid & Cells
    assert ".journal-calendar-grid" in css_text
    assert ".calendar-header-cell" in css_text
    assert ".calendar-day-cell" in css_text
    assert ".calendar-day-cell.cell-win" in css_text or ".cell-win" in css_text
    assert ".calendar-day-cell.cell-loss" in css_text or ".cell-loss" in css_text
    assert ".calendar-day-cell.cell-selected" in css_text or ".cell-selected" in css_text
    assert ".calendar-week-cell" in css_text

    # Diagnostics Grid & Progress Bars
    assert ".diagnostics-grid" in css_text
    assert ".diagnostic-card" in css_text
    assert ".diag-bar-track" in css_text
    assert ".diag-bar-fill" in css_text

    # Import Modal & Dropzone
    assert ".file-dropzone" in css_text
    assert ".detected-broker-badge" in css_text
    assert ".broker-preset-btn" in css_text


def test_api_calendar_and_diagnostics_integration():
    """Verify that backend calendar and diagnostics APIs respond properly to frontend requests."""
    # Seed data
    seed_res = client.post("/api/v1/journal/sample-data")
    assert seed_res.status_code == 200

    # 1. Calendar endpoint
    cal_res = client.get("/api/v1/journal/calendar?year=2026&month=10")
    assert cal_res.status_code == 200
    cal_data = cal_res.json()
    assert cal_data["year"] == 2026
    assert cal_data["month"] == 10
    assert "days" in cal_data
    assert "weeks" in cal_data or "weekly_summaries" in cal_data
    assert "kpis" in cal_data or "monthly_kpis" in cal_data

    # 2. Diagnostics endpoint
    diag_res = client.get("/api/v1/journal/diagnostics")
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert "time_of_day" in diag_data
    assert "direction" in diag_data
    assert "duration" in diag_data or "holding_duration" in diag_data
    assert "instruments" in diag_data or "instrument" in diag_data

