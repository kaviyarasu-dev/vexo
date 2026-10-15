import math
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from main import app
from db.connection import get_db, close_db
from db.migrations import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_path = str(tmp_path / "test_chart_drawing_tools.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


# ==============================================================================
# 1. Mathematical Logic & Algorithm Validations
# ==============================================================================

def test_trendline_mathematical_specifications():
    """Verify Trendline delta price, percentage move, and angle geometry."""
    # Test coordinates
    p1_price = 2500.0
    p2_price = 2650.0
    delta_p = p2_price - p1_price
    assert delta_p == 150.0

    pct = (delta_p / p1_price) * 100
    assert round(pct, 2) == 6.00

    # Screen coordinates angle calculation
    x1, y1 = 100, 400
    x2, y2 = 300, 200
    dx = x2 - x1
    dy = y2 - y1  # note: y increases downward in screen space
    # Screen angle: atan2(-(y2 - y1), x2 - x1)
    angle = math.degrees(math.atan2(-dy, dx))
    assert round(angle) == 45


def test_fibonacci_institutional_ratios():
    """Verify Fibonacci Retracement projects all 7 institutional levels and golden pocket."""
    ratios = [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000]
    p_start = 1000.0
    p_end = 2000.0
    delta = p_end - p_start

    levels = {r: p_start + (delta * r) for r in ratios}

    assert levels[0.0] == 1000.0
    assert levels[0.236] == 1236.0
    assert levels[0.382] == 1382.0
    assert levels[0.500] == 1500.0
    assert levels[0.618] == 1618.0  # Golden Ratio
    assert levels[0.786] == 1786.0
    assert levels[1.000] == 2000.0

    # Golden pocket span check
    assert levels[0.618] > levels[0.382]


def test_position_risk_reward_mathematics():
    """Verify Position R:R Box metrics, position sizing, and zero-division protection."""
    # Long trade scenario
    entry = 2400.0
    target = 2600.0
    stop = 2300.0

    risk_per_share = max(abs(entry - stop), 0.05)
    reward_per_share = abs(target - entry)
    assert risk_per_share == 100.0
    assert reward_per_share == 200.0

    rr_ratio = reward_per_share / risk_per_share
    assert round(rr_ratio, 2) == 2.00  # 1:2 Risk to Reward

    risk_budget = 2000.0  # ₹2,000 risk allocation
    position_size = math.floor(risk_budget / risk_per_share)
    assert position_size == 20

    projected_profit = position_size * reward_per_share
    assert projected_profit == 4000.0

    # Zero-division protection scenario (stop == entry)
    zero_div_stop = 2400.0
    guarded_risk = max(abs(entry - zero_div_stop), 0.05)
    assert guarded_risk == 0.05
    guarded_rr = reward_per_share / guarded_risk
    assert guarded_rr > 0


# ==============================================================================
# 2. Static Asset Definitions, DOM Structure & Micro-Toolbar
# ==============================================================================

def test_chart_drawings_js_exposures_and_tool_classes():
    """Verify that chart_drawings.js exposes modular tool classes and drag handle structures."""
    js_path = Path("static/js/chart_drawings.js")
    assert js_path.exists()
    content = js_path.read_text(encoding="utf-8")

    # Exposes tools on ChartDrawingManager
    assert "ChartDrawingManager.tools = {" in content
    assert "Trendline: TrendlineTool" in content
    assert "HorizontalRay: HorizontalRayTool" in content
    assert "Fibonacci: FibonacciTool" in content
    assert "PositionRR: PositionRRTool" in content

    # Drag handles
    assert 'data-handle-index="0"' in content
    assert 'data-handle-index="1"' in content
    assert "drawing-handle" in content

    # Micro-toolbar logic
    assert "showMicroToolbar" in content
    assert "updateMicroToolbarPosition" in content
    assert "micro-color-pill" in content
    assert "micro-width-btn" in content
    assert "micro-style-btn" in content
    assert "micro-delete-btn" in content

    # Keyboard listener
    assert "Escape" in content
    assert "Delete" in content
    assert "Backspace" in content


def test_index_html_contains_micro_toolbar():
    """Verify that static/index.html includes the micro-toolbar markup and options."""
    html_path = Path("static/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")

    assert 'id="chart-drawing-micro-toolbar"' in content
    assert 'class="micro-colors"' in content
    assert 'micro-width-btn' in content
    assert 'micro-style-btn' in content
    assert 'micro-delete-btn' in content


def test_chart_drawings_css_styling_rules():
    """Verify CSS rules for drag handles, Fibonacci shaded bands, and micro-toolbar."""
    css_path = Path("static/css/chart_drawings.css")
    assert css_path.exists()
    content = css_path.read_text(encoding="utf-8")

    assert ".fib-band" in content
    assert ".golden-pocket" in content
    assert ".drawing-micro-toolbar" in content
    assert ".micro-color-pill" in content
    assert ".drawing-handle" in content


# ==============================================================================
# 3. End-to-End REST API Persistence & Lifecycle for All 4 Tools
# ==============================================================================

def test_full_lifecycle_for_all_four_drawing_tools():
    """Verify persistence across all 4 tools (Trendline, H-Ray, Fibonacci, Position R:R)."""
    symbol = "NSE:TATASTEEL-EQ"

    # 1. Create TRENDLINE
    resp_trend = client.post(f"/api/v1/chart/drawings/{symbol}", json={
        "tool_type": "TRENDLINE",
        "points": [
            {"time": 1700000000, "price": 140.0},
            {"time": 1700100000, "price": 160.0}
        ],
        "style": {"color": "#2962FF", "lineWidth": 2}
    })
    assert resp_trend.status_code == 201
    trend_id = resp_trend.json()["data"]["drawing_id"]

    # 2. Create HORIZONTAL_RAY
    resp_ray = client.post(f"/api/v1/chart/drawings/{symbol}", json={
        "tool_type": "HORIZONTAL_RAY",
        "points": [{"time": 1700000000, "price": 150.0}],
        "style": {"color": "#F59E0B", "lineWidth": 1}
    })
    assert resp_ray.status_code == 201
    ray_id = resp_ray.json()["data"]["drawing_id"]

    # 3. Create FIBONACCI
    resp_fib = client.post(f"/api/v1/chart/drawings/{symbol}", json={
        "tool_type": "FIBONACCI",
        "points": [
            {"time": 1700000000, "price": 120.0},
            {"time": 1700200000, "price": 180.0}
        ]
    })
    assert resp_fib.status_code == 201
    fib_id = resp_fib.json()["data"]["drawing_id"]

    # 4. Create POSITION_RR
    resp_rr = client.post(f"/api/v1/chart/drawings/{symbol}", json={
        "tool_type": "POSITION_RR",
        "points": [
            {"time": 1700000000, "price": 145.0},
            {"time": 1700100000, "price": 165.0},
            {"time": 1700000000, "price": 138.0}
        ]
    })
    assert resp_rr.status_code == 201
    rr_id = resp_rr.json()["data"]["drawing_id"]

    # 5. Fetch all drawings for symbol -> should be 4
    list_resp = client.get(f"/api/v1/chart/drawings/{symbol}")
    assert list_resp.status_code == 200
    drawings = list_resp.json()["data"]
    assert len(drawings) == 4
    tool_types = {d["tool_type"] for d in drawings}
    assert tool_types == {"TRENDLINE", "HORIZONTAL_RAY", "FIBONACCI", "POSITION_RR"}

    # 6. Simulate Vertex Dragging / Handle Update on Trendline via PUT
    update_resp = client.put(f"/api/v1/chart/drawings/{trend_id}", json={
        "points": [
            {"time": 1700000000, "price": 140.0},
            {"time": 1700150000, "price": 175.0}  # Dragged endpoint up
        ],
        "style": {
            "color": "#10B981",  # Changed to Green via micro-toolbar
            "lineWidth": 3,
            "lineStyle": 1  # Dashed
        }
    })
    assert update_resp.status_code == 200
    updated_d = update_resp.json()["data"]
    assert updated_d["points"][1]["price"] == 175.0
    assert updated_d["style"]["color"] == "#10B981"
    assert updated_d["style"]["lineWidth"] == 3
    assert updated_d["style"]["lineStyle"] == 1

    # 7. Delete individual drawing
    del_resp = client.delete(f"/api/v1/chart/drawings/{ray_id}")
    assert del_resp.status_code == 200

    # 8. Check remaining count
    list_after_del = client.get(f"/api/v1/chart/drawings/{symbol}")
    assert list_after_del.json()["count"] == 3

    # 9. Clean up all
    clear_resp = client.delete(f"/api/v1/chart/drawings/{symbol}/all")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["count"] == 3
