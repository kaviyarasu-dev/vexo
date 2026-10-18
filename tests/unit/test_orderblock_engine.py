import pytest
import pandas as pd
from datetime import datetime, timedelta
import pytz

from services.orderblock.zone_engine import OrderBlockZoneEngine, OrderBlockZone, Candle5m
from services.orderblock.liquidity_engine import OrderBlockLiquidityEngine, LevelsLadder, LiquidityPool

IST = pytz.timezone("Asia/Kolkata")


def create_candles_sequence(candle_data):
    """Helper to generate a list of Candle5m dataclasses."""
    base_time = datetime(2026, 10, 16, 9, 15, tzinfo=IST)
    candles = []
    for i, (o, h, l, c, v) in enumerate(candle_data):
        t = base_time + timedelta(minutes=5 * i)
        candles.append(Candle5m(
            timestamp=t,
            open=float(o),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=int(v)
        ))
    return candles


def test_bullish_orderblock_detection():
    """Detects last down-candle before an impulsive upward break above a swing high."""
    engine = OrderBlockZoneEngine()
    
    # Sequence:
    # 0: Initial high at 105.0
    # 1: Slight pullback
    # 2: Down-candle (Bearish block candidate): Open 103, High 103.5, Low 101.0, Close 101.5
    # 3: Strong Bullish Impulse breaking previous swing high 105.0: Open 101.5, High 107.0, Low 101.5, Close 106.8
    # 4: Continuation
    data = [
        (100.0, 105.0, 99.5, 104.0, 5000),   # Swing High = 105.0
        (104.0, 104.5, 102.5, 103.0, 3000),  # Pullback
        (103.0, 103.5, 101.0, 101.5, 4000),  # Last down-candle (Bearish: close < open)
        (101.5, 107.0, 101.5, 106.8, 15000), # Impulse breakout above 105.0
        (106.8, 108.0, 106.0, 107.5, 6000),  # Continuation
    ]
    candles = create_candles_sequence(data)
    zones = engine.detect_zones("NSE:RELIANCE-EQ", candles)
    
    bullish_zones = [z for z in zones if z.block_type == "BULLISH"]
    assert len(bullish_zones) >= 1
    primary = bullish_zones[0]
    assert primary.top_price == 103.5
    assert primary.bottom_price == 101.0
    assert not primary.is_mitigated
    assert primary.invalidation_price == 101.0


def test_bearish_orderblock_detection():
    """Detects last up-candle before an impulsive downward drop below a swing low."""
    engine = OrderBlockZoneEngine()
    
    # Sequence:
    # 0: Initial swing low at 95.0
    # 1: Slight rally
    # 2: Up-candle (Bullish block candidate): Open 96.0, High 98.5, Low 95.8, Close 98.2
    # 3: Strong Bearish Impulse breaking previous swing low 95.0: Open 98.2, High 98.4, Low 92.5, Close 93.0
    # 4: Continuation
    data = [
        (98.0, 99.0, 95.0, 96.0, 5000),   # Swing Low = 95.0
        (96.0, 97.0, 95.5, 96.5, 3000),   # Consolidation
        (96.0, 98.5, 95.8, 98.2, 4500),   # Last up-candle (Bullish: close > open)
        (98.2, 98.4, 92.5, 93.0, 16000),  # Impulse breakdown below 95.0
        (93.0, 93.5, 91.0, 91.5, 7000),   # Continuation
    ]
    candles = create_candles_sequence(data)
    zones = engine.detect_zones("NSE:TCS-EQ", candles)
    
    bearish_zones = [z for z in zones if z.block_type == "BEARISH"]
    assert len(bearish_zones) >= 1
    primary = bearish_zones[0]
    assert primary.top_price == 98.5
    assert primary.bottom_price == 95.8
    assert not primary.is_mitigated
    assert primary.invalidation_price == 98.5


def test_zone_mitigation_on_close_beyond_invalidation():
    """Zone is marked mitigated when a subsequent candle closes through the invalidation price."""
    engine = OrderBlockZoneEngine()
    
    # Bullish order block created at candle 2, invalidated at candle 5
    data = [
        (100.0, 105.0, 99.5, 104.0, 5000),   # Swing High = 105.0
        (104.0, 104.5, 102.5, 103.0, 3000),
        (103.0, 103.5, 101.0, 101.5, 4000),  # Down-candle: Low = 101.0 (invalidation)
        (101.5, 107.0, 101.5, 106.8, 15000), # Impulse Breakout
        (106.8, 107.0, 102.0, 103.0, 5000),  # Retest into zone (touches 102.0, close 103.0 > 101.0) -> Valid
        (103.0, 103.2, 99.8, 100.2, 8000),   # Closes at 100.2 (< 101.0 invalidation) -> Mitigated!
    ]
    candles = create_candles_sequence(data)
    zones = engine.detect_zones("NSE:RELIANCE-EQ", candles)
    
    bullish_zones = [z for z in zones if z.block_type == "BULLISH"]
    assert len(bullish_zones) >= 1
    zone = bullish_zones[0]
    assert zone.is_mitigated
    assert zone.mitigation_timestamp == candles[5].timestamp


def test_levels_ladder_and_rr_calculation():
    """Levels ladder computes Z, S1-S4, R1-R4 and authentic Risk-to-Reward ratio."""
    liquidity_engine = OrderBlockLiquidityEngine()
    
    # Active Bullish Zone: Top 103.5 (Z), Bottom 101.0 (S1). Risk = 103.5 - 101.0 = 2.5
    zone = OrderBlockZone(
        symbol="NSE:INFY-EQ",
        block_type="BULLISH",
        start_time=datetime(2026, 10, 16, 9, 25, tzinfo=IST),
        top_price=103.5,
        bottom_price=101.0,
        invalidation_price=101.0,
        is_mitigated=False
    )
    
    # Swing high / day high target at 108.5 -> Reward = 108.5 - 103.5 = 5.0
    ladder = liquidity_engine.compute_levels(
        zone=zone,
        day_high=108.5,
        day_low=99.0,
        current_price=104.0
    )
    
    assert ladder.z_price == 103.5
    assert ladder.invalidation_price == 101.0
    assert ladder.risk == pytest.approx(2.5, rel=1e-3)
    assert ladder.r1 == pytest.approx(106.0, rel=1e-3)  # Z + 1.0 * risk
    assert ladder.r2 == pytest.approx(108.5, rel=1e-3)  # Day high target
    assert ladder.risk_reward_ratio == pytest.approx(2.0, rel=1e-3)  # 5.0 / 2.5 = 2.0


def test_liquidity_sweep_pools_detection():
    """Identifies equal highs and equal lows resting liquidity pools within 0.1% tolerance."""
    liquidity_engine = OrderBlockLiquidityEngine()
    
    # Two candle highs: 1500.0 and 1501.2 -> difference = 1.2 / 1500 = 0.08% <= 0.1%
    # Two candle lows: 1450.0 and 1450.8 -> difference = 0.8 / 1450 = 0.055% <= 0.1%
    data = [
        (1480.0, 1500.0, 1475.0, 1490.0, 5000),
        (1490.0, 1495.0, 1450.0, 1460.0, 4000),
        (1460.0, 1501.2, 1455.0, 1492.0, 6000), # Equal High with candle 0
        (1492.0, 1496.0, 1450.8, 1470.0, 3500), # Equal Low with candle 1
    ]
    candles = create_candles_sequence(data)
    pools = liquidity_engine.detect_liquidity_pools("NSE:HDFCBANK-EQ", candles, tolerance_pct=0.001)
    
    eq_highs = [p for p in pools if p.pool_type == "EQUAL_HIGHS"]
    eq_lows = [p for p in pools if p.pool_type == "EQUAL_LOWS"]
    
    assert len(eq_highs) >= 1
    assert eq_highs[0].price_level == pytest.approx(1500.6, abs=0.5)
    assert eq_highs[0].touches == 2
    
    assert len(eq_lows) >= 1
    assert eq_lows[0].price_level == pytest.approx(1450.4, abs=0.5)
    assert eq_lows[0].touches == 2
