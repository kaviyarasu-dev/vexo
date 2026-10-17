import pytest
import math
from datetime import date, datetime
import duckdb

from services.backtest.cost_model import IndianEquityCostModel
from services.options.greeks_engine import BlackScholesGreeks
from db.connection import DuckDBConnectionManager
from db.migrations import init_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo


def test_slippage_single_deduction():
    """Verify that cost_model does NOT add slippage into total_taxes_and_fees.
    
    Slippage is an execution price variance handled at fill time, not a statutory cash fee.
    """
    model = IndianEquityCostModel(slippage_bps=10.0)  # 10 bps
    
    # Buy 100,000, Sell 100,000
    res = model.compute_fees(buy_val=100000.0, sell_val=100000.0, trade_type="DELIVERY")
    
    # Turnover = 200,000. Slippage @ 10 bps = 200.0
    assert res.slippage == 200.0
    
    # Calculate expected taxes & statutory fees sum without slippage
    statutory_sum = round(
        res.brokerage + res.stt + res.exchange_charges + res.sebi_fee + res.gst + res.stamp_duty,
        2
    )
    
    # total_taxes_and_fees must equal statutory_sum, strictly excluding slippage
    assert res.total_taxes_and_fees == statutory_sum
    assert res.total_taxes_and_fees < statutory_sum + res.slippage


def test_corporate_actions_interval_join_no_cartesian_duplication(tmp_path):
    """Verify that candles_1d_adjusted and candles_1m_adjusted return strictly 1:1 rows.
    
    When a stock has multiple historical splits, intervals [prev_ex_date, ex_date)
    guarantee zero row duplication and correct cumulative factor application.
    """
    db_path = str(tmp_path / "test_split_dedup.duckdb")
    mgr = DuckDBConnectionManager(db_path)
    init_db(manager=mgr)
    
    conn = mgr.get_write_connection()
    
    # 1. Insert 3 historical daily candles for a stock
    conn.execute("""
        INSERT INTO candles_1d_raw (symbol, date, open, high, low, close, volume) VALUES
        ('NSE:INFY-EQ', '2019-06-01', 1000.0, 1020.0, 990.0, 1000.0, 10000),
        ('NSE:INFY-EQ', '2021-06-01', 500.0, 510.0, 490.0, 500.0, 20000),
        ('NSE:INFY-EQ', '2023-06-01', 250.0, 255.0, 245.0, 250.0, 40000);
    """)
    
    # 2. Insert 2 corporate actions (Splits)
    # Split 1 on 2020-01-01 (1:2) -> cumulative factor 0.25
    # Split 2 on 2022-01-01 (1:2) -> cumulative factor 0.50
    conn.execute("""
        INSERT INTO adjustment_factors (symbol, ex_date, factor_price, factor_volume) VALUES
        ('NSE:INFY-EQ', '2020-01-01', 0.25, 4.0),
        ('NSE:INFY-EQ', '2022-01-01', 0.50, 2.0);
    """)
    
    # Query adjusted view
    cursor = mgr.get_read_cursor()
    rows = cursor.execute("""
        SELECT date, open, close, volume 
        FROM candles_1d_adjusted 
        WHERE symbol = 'NSE:INFY-EQ' 
        ORDER BY date ASC
    """).fetchall()
    
    # CRITICAL: Strict 1:1 row count matching raw candles (3 rows, not 4 or 6)
    assert len(rows) == 3, f"Expected exactly 3 rows, got {len(rows)} (Cartesian duplication detected)"
    
    # 2019 candle adjusted by 0.25 (1000 * 0.25 = 250.0, volume 10000 * 4 = 40000)
    assert rows[0][0] == date(2019, 6, 1)
    assert rows[0][1] == pytest.approx(250.0)
    assert rows[0][2] == pytest.approx(250.0)
    assert rows[0][3] == 40000
    
    # 2021 candle adjusted by 0.50 (500 * 0.50 = 250.0, volume 20000 * 2 = 40000)
    assert rows[1][0] == date(2021, 6, 1)
    assert rows[1][1] == pytest.approx(250.0)
    assert rows[1][2] == pytest.approx(250.0)
    assert rows[1][3] == 40000
    
    # 2023 candle unadjusted (factor 1.0)
    assert rows[2][0] == date(2023, 6, 1)
    assert rows[2][1] == pytest.approx(250.0)
    assert rows[2][2] == pytest.approx(250.0)
    assert rows[2][3] == 40000
    
    mgr.close()


def test_greeks_time_scale_and_dividend_yield():
    """Verify BSM Greeks engine time scale standardization (250 trading days) and dividend yield."""
    engine = BlackScholesGreeks()
    
    spot = 2500.0
    strike = 2500.0
    t_days = 25.0
    iv = 0.20
    r = 0.065
    
    # 1. Zero dividend yield (q = 0.0)
    res_no_div = engine.calculate(
        spot=spot,
        strike=strike,
        t_days=t_days,
        iv=iv,
        r=r,
        option_type="CE",
        dividend_yield=0.0
    )
    
    # Time to expiry T = 25 / 250 = 0.10 years
    assert res_no_div.delta > 0.50  # Call ATM delta > 0.50 due to positive interest rate r
    assert res_no_div.gamma > 0.0
    assert res_no_div.theta < 0.0
    assert res_no_div.vega > 0.0
    
    # 2. Continuous dividend yield (q = 0.03, e.g. 3% yield)
    res_with_div = engine.calculate(
        spot=spot,
        strike=strike,
        t_days=t_days,
        iv=iv,
        r=r,
        option_type="CE",
        dividend_yield=0.03
    )
    
    # Dividend yield reduces Call Delta because holding the option foregoes dividends
    assert res_with_div.delta < res_no_div.delta
    
    # Put option with dividend yield
    put_no_div = engine.calculate(
        spot=spot,
        strike=strike,
        t_days=t_days,
        iv=iv,
        r=r,
        option_type="PE",
        dividend_yield=0.0
    )
    put_with_div = engine.calculate(
        spot=spot,
        strike=strike,
        t_days=t_days,
        iv=iv,
        r=r,
        option_type="PE",
        dividend_yield=0.03
    )
    
    # For puts, dividend increases put price and increases magnitude of negative Delta
    assert put_with_div.delta < put_no_div.delta  # e.g. -0.48 < -0.45
