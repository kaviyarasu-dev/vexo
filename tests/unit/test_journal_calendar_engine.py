import pytest
import datetime
from db.connection import get_db, close_db
from db.migrations import init_db
from core.interfaces import JournalEntry
from services.journal_service import JournalService
from services.journal.calendar_service import JournalCalendarService
from services.journal.diagnostics_service import JournalDiagnosticsService


@pytest.fixture
def test_db(tmp_path):
    """Sets up an isolated DuckDB instance for unit testing."""
    db_path = str(tmp_path / "test_calendar_engine.db")
    db = get_db(db_path, reset=True)
    init_db(db_path, manager=db)
    yield db
    close_db()


def test_empty_calendar_returns_full_month_days(test_db):
    """Verifies that an empty journal returns all days of the month with NO_TRADES status."""
    cal_service = JournalCalendarService(test_db)
    res = cal_service.get_monthly_calendar(year=2026, month=10)

    assert res.success is True
    assert res.year == 2026
    assert res.month == 10
    assert len(res.days) == 31  # October has 31 days

    # Verify first and last day
    assert res.days[0].date == "2026-10-01"
    assert res.days[0].day_of_month == 1
    assert res.days[0].status == "NO_TRADES"
    assert res.days[0].net_pnl == 0.0

    assert res.days[30].date == "2026-10-31"
    assert res.days[30].day_of_month == 31
    assert res.days[30].status == "NO_TRADES"

    # KPIs on empty
    kpis = res.kpis
    assert kpis.monthly_net_pnl == 0.0
    assert kpis.trading_days == 0
    assert kpis.win_days == 0
    assert kpis.loss_days == 0
    assert kpis.win_day_pct == 0.0
    assert kpis.max_win_streak == 0
    assert kpis.max_loss_streak == 0


def test_calendar_aggregation_and_streaks(test_db):
    """Verifies daily aggregation, exit date attribution, and streak computations."""
    j_service = JournalService(test_db)
    cal_service = JournalCalendarService(test_db)

    # Day 1: 2026-10-05 (Win) - 2 winning trades
    j_service.record_trade(JournalEntry(
        trade_id="t1",
        symbol="NSE:RELIANCE-EQ",
        trade_type="EQUITY",
        direction="LONG",
        entry_time=datetime.datetime(2026, 10, 5, 9, 30),
        entry_price=2500.0,
        exit_time=datetime.datetime(2026, 10, 5, 10, 15),
        exit_price=2550.0,
        quantity=10,
        stop_loss=2480.0,
        take_profit=2560.0,
        pnl_gross=500.0,
        total_charges=25.0,
        pnl_net=475.0,
        r_multiple=2.5,
        mistake_tags=[],
        notes="Clean scalp"
    ))
    j_service.record_trade(JournalEntry(
        trade_id="t2",
        symbol="NSE:TCS-EQ",
        trade_type="EQUITY",
        direction="LONG",
        entry_time=datetime.datetime(2026, 10, 5, 13, 15),
        entry_price=3500.0,
        exit_time=datetime.datetime(2026, 10, 5, 14, 30),
        exit_price=3520.0,
        quantity=10,
        stop_loss=3480.0,
        take_profit=3540.0,
        pnl_gross=200.0,
        total_charges=20.0,
        pnl_net=180.0,
        r_multiple=1.0,
        mistake_tags=[],
        notes="Afternoon trend"
    ))

    # Day 2: 2026-10-06 (Win) - 1 winning trade (Continues win streak -> 2)
    j_service.record_trade(JournalEntry(
        trade_id="t3",
        symbol="NSE:INFY-EQ",
        trade_type="EQUITY",
        direction="LONG",
        entry_time=datetime.datetime(2026, 10, 6, 9, 45),
        entry_price=1500.0,
        exit_time=datetime.datetime(2026, 10, 6, 11, 0),
        exit_price=1530.0,
        quantity=20,
        stop_loss=1480.0,
        take_profit=1550.0,
        pnl_gross=600.0,
        total_charges=30.0,
        pnl_net=570.0,
        r_multiple=1.5,
        mistake_tags=[],
        notes="Morning breakout"
    ))

    # Day 3: 2026-10-07 (Loss) - 1 loss trade (Breaks win streak, starts loss streak -> 1)
    j_service.record_trade(JournalEntry(
        trade_id="t4",
        symbol="NSE:HDFCBANK-EQ",
        trade_type="EQUITY",
        direction="SHORT",
        entry_time=datetime.datetime(2026, 10, 7, 10, 45),
        entry_price=1600.0,
        exit_time=datetime.datetime(2026, 10, 7, 12, 15),
        exit_price=1620.0,
        quantity=25,
        stop_loss=1615.0,
        take_profit=1580.0,
        pnl_gross=-500.0,
        total_charges=25.0,
        pnl_net=-525.0,
        r_multiple=-1.33,
        mistake_tags=["Ignored Stop Loss"],
        notes="Short failed"
    ))

    # Day 4: 2026-10-08 (Loss) - 1 loss trade (Continues loss streak -> 2)
    j_service.record_trade(JournalEntry(
        trade_id="t5",
        symbol="NSE:SBIN-EQ",
        trade_type="EQUITY",
        direction="LONG",
        entry_time=datetime.datetime(2026, 10, 8, 14, 0),
        entry_price=800.0,
        exit_time=datetime.datetime(2026, 10, 8, 15, 15),
        exit_price=790.0,
        quantity=30,
        stop_loss=792.0,
        take_profit=815.0,
        pnl_gross=-300.0,
        total_charges=20.0,
        pnl_net=-320.0,
        r_multiple=-1.25,
        mistake_tags=[],
        notes="EOD cut"
    ))

    # Trade with entry in September and exit in October (Must be attributed to October 9th)
    j_service.record_trade(JournalEntry(
        trade_id="t6",
        symbol="NSE:ICICIBANK-EQ",
        trade_type="EQUITY",
        direction="LONG",
        entry_time=datetime.datetime(2026, 9, 28, 11, 0),
        entry_price=1200.0,
        exit_time=datetime.datetime(2026, 10, 9, 10, 0),
        exit_price=1240.0,
        quantity=15,
        stop_loss=1180.0,
        take_profit=1250.0,
        pnl_gross=600.0,
        total_charges=30.0,
        pnl_net=570.0,
        r_multiple=2.0,
        mistake_tags=[],
        notes="Multi-day swing realized on Oct 9"
    ))

    res = cal_service.get_monthly_calendar(year=2026, month=10)
    assert res.success is True

    # Check Day Oct 5 (Index 4: Oct 5th)
    day_5 = res.days[4]
    assert day_5.date == "2026-10-05"
    assert day_5.trades_count == 2
    assert day_5.win_count == 2
    assert day_5.loss_count == 0
    assert day_5.net_pnl == 655.0  # 475 + 180
    assert day_5.status == "WIN"

    # Check Day Oct 6
    day_6 = res.days[5]
    assert day_6.date == "2026-10-06"
    assert day_6.trades_count == 1
    assert day_6.net_pnl == 570.0
    assert day_6.status == "WIN"

    # Check Day Oct 7
    day_7 = res.days[6]
    assert day_7.date == "2026-10-07"
    assert day_7.trades_count == 1
    assert day_7.net_pnl == -525.0
    assert day_7.status == "LOSS"

    # Check Day Oct 8
    day_8 = res.days[7]
    assert day_8.date == "2026-10-08"
    assert day_8.trades_count == 1
    assert day_8.net_pnl == -320.0
    assert day_8.status == "LOSS"

    # Check Day Oct 9 (Swing trade exited Oct 9)
    day_9 = res.days[8]
    assert day_9.date == "2026-10-09"
    assert day_9.trades_count == 1
    assert day_9.net_pnl == 570.0
    assert day_9.status == "WIN"

    # Verify Monthly KPIs & Streaks
    kpis = res.kpis
    assert kpis.trading_days == 5
    assert kpis.win_days == 3  # Oct 5, Oct 6, Oct 9
    assert kpis.loss_days == 2  # Oct 7, Oct 8
    assert kpis.win_day_pct == 60.0
    assert kpis.max_win_streak == 2  # Oct 5, Oct 6
    assert kpis.max_loss_streak == 2  # Oct 7, Oct 8
    # Monthly Net = 655 + 570 - 525 - 320 + 570 = 950.0
    assert kpis.monthly_net_pnl == 950.0
    assert kpis.profit_factor > 1.0


def test_quantitative_diagnostics_service(test_db):
    """Verifies multi-dimensional breakdown across Time-of-Day, Direction, Duration, and Instruments."""
    j_service = JournalService(test_db)
    diag_service = JournalDiagnosticsService(test_db)

    # 1. Morning Intraday Long Equity (09:30)
    j_service.record_trade(JournalEntry(
        trade_id="d1",
        symbol="NSE:TCS-EQ",
        trade_type="EQUITY",
        direction="LONG",
        entry_time=datetime.datetime(2026, 10, 5, 9, 30),
        entry_price=3500.0,
        exit_time=datetime.datetime(2026, 10, 5, 10, 15),
        exit_price=3550.0,
        quantity=10,
        stop_loss=3480.0,
        take_profit=3560.0,
        pnl_gross=500.0,
        total_charges=25.0,
        pnl_net=475.0,
        r_multiple=2.5,
        mistake_tags=[],
        notes="Morning scalp"
    ))

    # 2. Midday Intraday Short Equity (11:15)
    j_service.record_trade(JournalEntry(
        trade_id="d2",
        symbol="NSE:INFY-EQ",
        trade_type="EQUITY",
        direction="SHORT",
        entry_time=datetime.datetime(2026, 10, 5, 11, 15),
        entry_price=1600.0,
        exit_time=datetime.datetime(2026, 10, 5, 12, 30),
        exit_price=1620.0,
        quantity=10,
        stop_loss=1615.0,
        take_profit=1580.0,
        pnl_gross=-200.0,
        total_charges=20.0,
        pnl_net=-220.0,
        r_multiple=-1.33,
        mistake_tags=[],
        notes="Midday loss"
    ))

    # 3. Afternoon Overnight Swing Long F&O (14:15)
    j_service.record_trade(JournalEntry(
        trade_id="d3",
        symbol="NSE:NIFTY50-INDEX",
        trade_type="F&O",
        direction="LONG",
        entry_time=datetime.datetime(2026, 10, 5, 14, 15),
        entry_price=25000.0,
        exit_time=datetime.datetime(2026, 10, 7, 10, 0),  # Held overnight -> Swing
        exit_price=25200.0,
        quantity=25,
        stop_loss=24900.0,
        take_profit=25300.0,
        pnl_gross=5000.0,
        total_charges=150.0,
        pnl_net=4850.0,
        r_multiple=2.0,
        mistake_tags=[],
        notes="Index swing"
    ))

    res = diag_service.get_quantitative_diagnostics()
    assert res.success is True

    # 1. Time-of-Day
    tod_map = {b.name: b for b in res.time_of_day}
    assert tod_map["morning"].trades_count == 1
    assert tod_map["morning"].win_rate == 100.0
    assert tod_map["morning"].net_pnl == 475.0

    assert tod_map["midday"].trades_count == 1
    assert tod_map["midday"].win_rate == 0.0
    assert tod_map["midday"].net_pnl == -220.0

    assert tod_map["afternoon"].trades_count == 1
    assert tod_map["afternoon"].win_rate == 100.0
    assert tod_map["afternoon"].net_pnl == 4850.0

    # 2. Direction
    dir_map = {b.name: b for b in res.direction}
    assert dir_map["long"].trades_count == 2
    assert dir_map["long"].win_rate == 100.0
    assert dir_map["long"].net_pnl == 475.0 + 4850.0

    assert dir_map["short"].trades_count == 1
    assert dir_map["short"].win_rate == 0.0
    assert dir_map["short"].net_pnl == -220.0

    # 3. Duration
    dur_map = {b.name: b for b in res.duration}
    assert dur_map["intraday"].trades_count == 2  # d1 and d2
    assert dur_map["swing"].trades_count == 1  # d3 (2 days hold)
    assert dur_map["swing"].net_pnl == 4850.0

    # 4. Instruments
    inst_map = {b.name: b for b in res.instruments}
    assert inst_map["equity"].trades_count == 2
    assert inst_map["fno"].trades_count == 1
    assert inst_map["fno"].net_pnl == 4850.0
