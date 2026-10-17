import pytest
import pandas as pd
from datetime import date, timedelta
from db.connection import get_db
from services.orderblock.strength_engine import IntradayStrengthEngine, StockStrengthMetric
from services.orderblock.picks_engine import OrderBlockBoardsEngine, PickCandidate


@pytest.fixture
def memory_db():
    """In-memory DuckDB initialized with required schema and 50-day test candles."""
    db = get_db(":memory:", reset=True)
    
    db.execute_write("""
        CREATE TABLE symbols (
            symbol VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            category VARCHAR,
            tier INTEGER NOT NULL DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    
    db.execute_write("""
        CREATE TABLE candles_1d_adjusted (
            symbol VARCHAR NOT NULL,
            date DATE NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume BIGINT NOT NULL
        );
    """)
    
    # Insert test symbols
    symbols = [
        ("NSE:RELIANCE-EQ", "Reliance Industries", "NIFTY50"),
        ("NSE:TCS-EQ", "Tata Consultancy Services", "NIFTY50"),
        ("NSE:INFY-EQ", "Infosys", "NIFTY50"),
        ("NSE:WIPRO-EQ", "Wipro", "NIFTY50"),
        ("NSE:HDFCBANK-EQ", "HDFC Bank", "NIFTY50"),
        ("NSE:ICICIBANK-EQ", "ICICI Bank", "NIFTY50"),
        ("NSE:SBIN-EQ", "State Bank of India", "NIFTY50"),
        ("NSE:TATAMOTORS-EQ", "Tata Motors", "NIFTY50"),
    ]
    for sym, name, cat in symbols:
        db.execute_write(
            "INSERT INTO symbols (symbol, name, category, tier, is_active) VALUES (?, ?, ?, 1, TRUE)",
            (sym, name, cat)
        )
        
    # Generate 50 daily candles per symbol with consistent daily range of 50.0 (High 1050, Low 1000)
    base_date = date(2026, 1, 1)
    rows = []
    for sym, _, _ in symbols:
        for i in range(50):
            d = base_date + timedelta(days=i)
            # High = 1050, Low = 1000 -> Daily Move = 50.0
            rows.append((sym, d, 1010.0, 1050.0, 1000.0, 1040.0, 100000))
            
    df = pd.DataFrame(rows, columns=["symbol", "date", "open", "high", "low", "close", "volume"])
    db.execute_write_df("INSERT INTO candles_1d_adjusted SELECT * FROM _temp_input_table", df)
    
    yield db
    db.close()


def test_adm_lookback_calculation(memory_db):
    """ADM should accurately compute the mean of High - Low over the 50-session window."""
    engine = IntradayStrengthEngine(db_manager=memory_db)
    adm = engine.compute_adm("NSE:RELIANCE-EQ", lookback=50)
    assert adm == pytest.approx(50.0, rel=1e-3)


def test_bullish_strength_scoring_valid_2x(memory_db):
    """Clean expansion away from open where delta_high > 2 * delta_low."""
    engine = IntradayStrengthEngine(db_manager=memory_db)
    
    # ADM = 50.0. Open = 1000.0. High = 1100.0 (delta_high = 100.0). Low = 980.0 (delta_low = 20.0).
    # delta_high (100) > 2 * delta_low (40) -> Bullish. Score = 100 / 50 = 2.0.
    metric = engine.evaluate_strength(
        symbol="NSE:RELIANCE-EQ",
        open_price=1000.0,
        high_price=1100.0,
        low_price=980.0,
        current_price=1095.0,
        adm=50.0
    )
    
    assert metric.side == "BULLISH"
    assert metric.score == pytest.approx(2.0, rel=1e-3)
    assert not metric.is_event_risk
    assert metric.delta_high == 100.0
    assert metric.delta_low == 20.0


def test_bearish_strength_scoring_valid_2x(memory_db):
    """Clean downward drop where delta_low > 2 * delta_high."""
    engine = IntradayStrengthEngine(db_manager=memory_db)
    
    # ADM = 50.0. Open = 1000.0. High = 1010.0 (delta_high = 10.0). Low = 960.0 (delta_low = 40.0, 4.0% drop).
    # delta_low (40) > 2 * delta_high (20) -> Bearish. Score = 40 / 50 = 0.8.
    metric = engine.evaluate_strength(
        symbol="NSE:TCS-EQ",
        open_price=1000.0,
        high_price=1010.0,
        low_price=960.0,
        current_price=965.0,
        adm=50.0
    )
    
    assert metric.side == "BEARISH"
    assert metric.score == pytest.approx(0.8, rel=1e-3)
    assert not metric.is_event_risk


def test_ineligible_scoring_fails_2x_boundary(memory_db):
    """Choppy, two-sided move where neither delta satisfies the 2x ratio."""
    engine = IntradayStrengthEngine(db_manager=memory_db)
    
    # Open = 1000.0. High = 1030.0 (delta_high = 30.0). Low = 980.0 (delta_low = 20.0).
    # delta_high (30) is NOT > 2 * delta_low (40).
    # delta_low (20) is NOT > 2 * delta_high (60).
    metric = engine.evaluate_strength(
        symbol="NSE:INFY-EQ",
        open_price=1000.0,
        high_price=1030.0,
        low_price=980.0,
        current_price=1010.0,
        adm=50.0
    )
    
    assert metric.side == "NEUTRAL"
    assert metric.score == 0.0
    assert not metric.is_event_risk


def test_event_risk_drop_percentage(memory_db):
    """Intraday drop > 5.0% from open triggers event-risk suppression."""
    engine = IntradayStrengthEngine(db_manager=memory_db)
    
    # Open = 1000.0. Current/Low = 940.0 (-6.0% drop).
    metric = engine.evaluate_strength(
        symbol="NSE:TATAMOTORS-EQ",
        open_price=1000.0,
        high_price=1005.0,
        low_price=940.0,
        current_price=940.0,
        adm=50.0
    )
    
    assert metric.is_event_risk
    assert metric.event_risk_reason == "Intraday drop > 5.0% (-6.00%)"


def test_event_risk_drop_multiple_adm(memory_db):
    """Intraday drop > 2.5x ADM triggers event-risk suppression."""
    engine = IntradayStrengthEngine(db_manager=memory_db)
    
    # ADM = 20.0. Open = 1000.0. Low = 945.0 (drop = 55.0 = 2.75x ADM, but 5.5% drop).
    # Let's test with drop = 60 on open 2000 (3% drop, but ADM = 20 so 60 > 2.5 * 20 = 50).
    metric = engine.evaluate_strength(
        symbol="NSE:HDFCBANK-EQ",
        open_price=2000.0,
        high_price=2005.0,
        low_price=1940.0,
        current_price=1942.0,
        adm=20.0
    )
    
    assert metric.is_event_risk
    assert "2.5x ADM" in metric.event_risk_reason


def test_boards_ranking_and_rank_delta(memory_db):
    """Boards rank descending by score and compute minute-over-minute delta."""
    boards_engine = OrderBlockBoardsEngine()
    
    # Minute 1 metrics
    m1 = [
        StockStrengthMetric("NSE:RELIANCE-EQ", "Energy", 2.5, "BULLISH", 1000, 1125, 990, 1120, False, ""),
        StockStrengthMetric("NSE:TCS-EQ", "IT", 2.1, "BULLISH", 3000, 3105, 2990, 3100, False, ""),
        StockStrengthMetric("NSE:INFY-EQ", "IT", 1.8, "BULLISH", 1500, 1545, 1495, 1540, False, ""),
    ]
    
    board_min1 = boards_engine.update_boards(m1)
    rel_min1 = next(item for item in board_min1.bullish if item.symbol == "NSE:RELIANCE-EQ")
    assert rel_min1.rank == 1
    assert rel_min1.rank_delta == 0
    assert rel_min1.is_new_top10
    
    # Minute 2: TCS overtakes Reliance
    m2 = [
        StockStrengthMetric("NSE:TCS-EQ", "IT", 3.0, "BULLISH", 3000, 3150, 2990, 3145, False, ""),
        StockStrengthMetric("NSE:RELIANCE-EQ", "Energy", 2.4, "BULLISH", 1000, 1120, 990, 1115, False, ""),
        StockStrengthMetric("NSE:INFY-EQ", "IT", 1.9, "BULLISH", 1500, 1548, 1495, 1542, False, ""),
    ]
    
    board_min2 = boards_engine.update_boards(m2)
    tcs_min2 = next(item for item in board_min2.bullish if item.symbol == "NSE:TCS-EQ")
    rel_min2 = next(item for item in board_min2.bullish if item.symbol == "NSE:RELIANCE-EQ")
    
    assert tcs_min2.rank == 1
    assert tcs_min2.rank_delta == 1  # Moved up from rank 2 to 1 (+1)
    assert rel_min2.rank == 2
    assert rel_min2.rank_delta == -1  # Moved down from rank 1 to 2 (-1)


def test_picks_shortlist_with_2_sector_cap(memory_db):
    """Picks select Top 3 per side enforcing maximum 2 stocks from any single sector."""
    boards_engine = OrderBlockBoardsEngine()
    
    # 4 Bullish IT stocks + 1 Energy stock + 1 Banking stock + 1 Event-risk stock
    metrics = [
        StockStrengthMetric("NSE:TCS-EQ", "IT", 3.5, "BULLISH", 3000, 3175, 2990, 3170, False, ""),
        StockStrengthMetric("NSE:INFY-EQ", "IT", 3.2, "BULLISH", 1500, 1580, 1495, 1575, False, ""),
        StockStrengthMetric("NSE:WIPRO-EQ", "IT", 3.0, "BULLISH", 450, 480, 448, 478, False, ""),  # 3rd IT stock (Sector Cap Exceeded)
        StockStrengthMetric("NSE:RELIANCE-EQ", "Energy", 2.8, "BULLISH", 1000, 1140, 990, 1135, False, ""), # Should be picked
        StockStrengthMetric("NSE:HDFCBANK-EQ", "Banking", 2.2, "BULLISH", 1600, 1640, 1595, 1638, False, ""),
        StockStrengthMetric("NSE:BADNEWS-EQ", "Auto", 4.0, "BULLISH", 100, 120, 80, 90, True, "Event Risk"), # Excluded
    ]
    
    picks = boards_engine.select_picks(metrics, side="BULLISH", max_picks=3, max_per_sector=2)
    
    picked_symbols = [p.symbol for p in picks if p.status == "PICKED"]
    assert len(picked_symbols) == 3
    assert "NSE:TCS-EQ" in picked_symbols  # 1st IT
    assert "NSE:INFY-EQ" in picked_symbols  # 2nd IT
    assert "NSE:RELIANCE-EQ" in picked_symbols  # Energy (skipped WIPRO due to sector cap)
    assert "NSE:WIPRO-EQ" not in picked_symbols
    
    # Verify audit reasons
    wipro_pick = next(p for p in picks if p.symbol == "NSE:WIPRO-EQ")
    assert wipro_pick.status == "NOT PICKED: Sector Cap Exceeded"
    
    bad_pick = next(p for p in picks if p.symbol == "NSE:BADNEWS-EQ")
    assert bad_pick.status == "NOT PICKED: Event Risk Excluded"
