import pytest
from db.connection import get_db, close_db
from db.migrations import init_db
from services.chart_drawing_service import ChartDrawingService
from api.models.drawing_models import DrawingPoint, DrawingStyle


@pytest.fixture
def test_service(tmp_path):
    db_path = str(tmp_path / "test_chart_drawings_unit.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    service = ChartDrawingService(db)
    yield service
    close_db()


def test_create_and_get_drawings(test_service):
    # 1. Create a Trendline
    points = [
        DrawingPoint(time="2026-01-01", price=2500.0),
        DrawingPoint(time="2026-01-10", price=2650.0)
    ]
    style = DrawingStyle(color="#00E676", lineWidth=3)
    created = test_service.create_drawing(
        symbol="NSE:RELIANCE-EQ",
        tool_type="TRENDLINE",
        points=points,
        style=style
    )

    assert created.drawing_id is not None
    assert created.symbol == "NSE:RELIANCE-EQ"
    assert created.tool_type == "TRENDLINE"
    assert len(created.points) == 2
    assert created.points[0].price == 2500.0
    assert created.points[1].price == 2650.0
    assert created.style.color == "#00E676"
    assert created.style.lineWidth == 3

    # 2. Get drawings for symbol
    drawings = test_service.get_drawings("NSE:RELIANCE-EQ")
    assert len(drawings) == 1
    assert drawings[0].drawing_id == created.drawing_id

    # 3. Get drawing by ID
    single = test_service.get_drawing_by_id(created.drawing_id)
    assert single is not None
    assert single.drawing_id == created.drawing_id


def test_update_drawing(test_service):
    points = [DrawingPoint(time="2026-01-01", price=1500.0)]
    created = test_service.create_drawing(
        symbol="NSE:INFY-EQ",
        tool_type="HORIZONTAL_RAY",
        points=points
    )

    # Update points and style
    new_points = [DrawingPoint(time="2026-01-01", price=1550.0)]
    new_style = DrawingStyle(color="#FF5252", lineWidth=1)
    updated = test_service.update_drawing(
        drawing_id=created.drawing_id,
        points=new_points,
        style=new_style
    )

    assert updated is not None
    assert updated.points[0].price == 1550.0
    assert updated.style.color == "#FF5252"
    assert updated.style.lineWidth == 1


def test_delete_and_clear_drawings(test_service):
    d1 = test_service.create_drawing(
        symbol="NSE:TCS-EQ",
        tool_type="HORIZONTAL_RAY",
        points=[DrawingPoint(time="2026-01-01", price=3800.0)]
    )
    d2 = test_service.create_drawing(
        symbol="NSE:TCS-EQ",
        tool_type="TRENDLINE",
        points=[
            DrawingPoint(time="2026-01-01", price=3700.0),
            DrawingPoint(time="2026-01-05", price=3900.0)
        ]
    )
    d3 = test_service.create_drawing(
        symbol="NSE:HDFCBANK-EQ",
        tool_type="HORIZONTAL_RAY",
        points=[DrawingPoint(time="2026-01-01", price=1600.0)]
    )

    # Delete single drawing
    deleted = test_service.delete_drawing(d1.drawing_id)
    assert deleted is True
    assert test_service.get_drawing_by_id(d1.drawing_id) is None

    # TCS has 1 left, HDFCBANK has 1
    assert len(test_service.get_drawings("NSE:TCS-EQ")) == 1
    assert len(test_service.get_drawings("NSE:HDFCBANK-EQ")) == 1

    # Clear all for TCS
    cleared_count = test_service.clear_symbol_drawings("NSE:TCS-EQ")
    assert cleared_count == 1
    assert len(test_service.get_drawings("NSE:TCS-EQ")) == 0
    # HDFCBANK untouched
    assert len(test_service.get_drawings("NSE:HDFCBANK-EQ")) == 1


def test_nonexistent_drawing_operations(test_service):
    assert test_service.get_drawing_by_id("non-existent-id") is None
    assert test_service.update_drawing("non-existent-id", points=[]) is None
    assert test_service.delete_drawing("non-existent-id") is False
    assert test_service.clear_symbol_drawings("NSE:NONEXISTENT-EQ") == 0
