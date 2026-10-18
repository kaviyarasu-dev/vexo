"""Unit tests for OrderBlock Backtest Harness & Capital Protection Gate.
Verifies expectancy calculation, drawdown tracking, single-month concentration,
and strict enforcement of the 300-trade, +0.15R, 10R drawdown gate.
"""

from datetime import datetime, date
import pytest

from services.orderblock.backtest_harness import (
    BacktestTrade,
    BacktestResult,
    OrderBlockBacktestHarness,
)


def test_expectancy_and_drawdown_calculation():
    """Verify net R-multiple expectancy and peak-to-trough max drawdown calculations."""
    harness = OrderBlockBacktestHarness()
    
    # 5 trades: +2.0R, -1.0R, +1.5R, -1.0R, +3.0R (Net R = 4.5R / 5 = 0.90R)
    trades = [
        BacktestTrade("T1", "NSE:RELIANCE-EQ", "BULLISH", "2026-01-05", 2800.0, 2840.0, 2.0, 0.05, 1.95),
        BacktestTrade("T2", "NSE:TCS-EQ", "BEARISH", "2026-01-06", 3500.0, 3480.0, -1.0, 0.05, -1.05),
        BacktestTrade("T3", "NSE:INFY-EQ", "BULLISH", "2026-01-08", 1500.0, 1530.0, 1.5, 0.05, 1.45),
        BacktestTrade("T4", "NSE:SBIN-EQ", "BULLISH", "2026-01-10", 800.0, 792.0, -1.0, 0.05, -1.05),
        BacktestTrade("T5", "NSE:HDFCBANK-EQ", "BULLISH", "2026-01-12", 1500.0, 1560.0, 3.0, 0.05, 2.95),
    ]

    metrics = harness.calculate_gate_metrics(trades)
    
    assert metrics.total_trades == 5
    # Total net R: 1.95 - 1.05 + 1.45 - 1.05 + 2.95 = 4.25R -> Expectancy = 4.25 / 5 = 0.85R
    assert metrics.expectancy == pytest.approx(0.85, abs=0.01)
    assert metrics.win_rate == pytest.approx(60.0)
    assert metrics.max_drawdown <= 2.0


def test_gate_pass_criteria():
    """Verify that a simulation meeting all 4 institutional criteria passes the capital gate."""
    harness = OrderBlockBacktestHarness()
    
    # Generate 320 valid trades spread across 4 months with +0.22R expectancy and 3.5R max drawdown
    trades = []
    import random
    rng = random.Random(42)
    
    for i in range(320):
        month = (i // 80) + 1  # 4 months evenly spread (25% per month)
        date_str = f"2026-0{month}-{(i % 25) + 1:02d}"
        
        # 55% win rate with 1.8R win vs 1.0R loss
        is_win = rng.random() < 0.55
        gross_r = 1.8 if is_win else -1.0
        slippage_r = 0.05
        net_r = gross_r - slippage_r
        
        trades.append(
            BacktestTrade(
                f"TR-{i}",
                "NSE:RELIANCE-EQ",
                "BULLISH",
                date_str,
                2800.0,
                2836.0 if is_win else 2780.0,
                gross_r,
                slippage_r,
                net_r,
            )
        )

    result = harness.evaluate_gate(trades)
    assert result.passed is True
    assert result.total_trades >= 300
    assert result.expectancy >= 0.15
    assert result.max_drawdown <= 10.0
    assert result.max_month_profit_pct <= 40.0


def test_gate_rejection_low_expectancy():
    """Verify rejection when trade expectancy falls below +0.15R."""
    harness = OrderBlockBacktestHarness()
    # 350 trades with negative expectancy (-0.10R)
    trades = [
        BacktestTrade(f"TR-{i}", "NSE:TEST-EQ", "BULLISH", "2026-01-05", 100.0, 99.0, -0.05, 0.05, -0.10)
        for i in range(350)
    ]
    result = harness.evaluate_gate(trades)
    assert result.passed is False
    assert any("Expectancy" in r for r in result.rejection_reasons)


def test_gate_rejection_insufficient_sample():
    """Verify rejection when trade count is below 300 trades."""
    harness = OrderBlockBacktestHarness()
    trades = [
        BacktestTrade(f"TR-{i}", "NSE:TEST-EQ", "BULLISH", "2026-01-05", 100.0, 105.0, 2.0, 0.05, 1.95)
        for i in range(150)
    ]
    result = harness.evaluate_gate(trades)
    assert result.passed is False
    assert any("trades" in r.lower() for r in result.rejection_reasons)
