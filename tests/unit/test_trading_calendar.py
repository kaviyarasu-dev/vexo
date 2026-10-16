import datetime
import pytest
from db.connection import get_db, DuckDBConnectionManager
from db.migrations import init_db
from services.trading_calendar import TradingCalendar

@pytest.fixture
def test_db():
    db = get_db(":memory:", reset=True)
    init_db(manager=db)
    
    # Insert Republic Day 2024 (Friday) as holiday
    db.execute_write(
        "INSERT INTO market_holidays (holiday_date, description, is_special_session) VALUES (?, ?, ?)",
        ['2024-01-26', 'Republic Day', False]
    )
    # Insert a special session
    db.execute_write(
        "INSERT INTO market_holidays (holiday_date, description, is_special_session) VALUES (?, ?, ?)",
        ['2024-11-01', 'Muhurat Trading', True]
    )
    yield db
    db.close()

def test_trading_calendar(test_db):
    calendar = TradingCalendar(db_path=":memory:")
    
    # Republic day (Friday) -> False
    assert not calendar.is_trading_day("2024-01-26")
    
    # Regular Monday -> True
    assert calendar.is_trading_day("2024-01-22")
    
    # Weekend (Saturday) -> False
    assert not calendar.is_trading_day("2024-01-27")
    
    # Weekend (Sunday) -> False
    assert not calendar.is_trading_day("2024-01-28")
    
    # Special session -> True
    assert calendar.is_trading_day("2024-11-01")

def test_get_previous_trading_day(test_db):
    calendar = TradingCalendar(db_path=":memory:")
    
    # If today is Monday 2024-01-29, previous is Thursday 2024-01-25 (since 26 is holiday, 27-28 weekend)
    d = datetime.date(2024, 1, 29)
    prev = calendar.get_previous_trading_day(d)
    assert prev == datetime.date(2024, 1, 25)
