"""
Unit Tests for Strategy Parameter Optimization Engine, 
3x3 Plateau Stability Index (PSI) Analyzer & Walk-Forward Splitter.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from services.backtest.optimization_engine import (
    ParamSpec,
    OptimizationCell,
    StabilityResult,
    WalkForwardResult,
    generate_param_ticks,
    create_strategy_instance,
    WalkForwardSplitter,
    StabilityAnalyzer,
    OptimizationEngine,
    MAX_GRID_COMBINATIONS,
)


# ============================================================================
# Helpers & Fixtures
# ============================================================================

def generate_synthetic_ohlcv(bars: int = 200, trend: float = 0.5) -> pd.DataFrame:
    """Generate realistic synthetic OHLCV candle series with cyclical oscillations and trend."""
    start_dt = datetime(2023, 1, 1, 9, 15)
    timestamps = [start_dt + timedelta(days=i) for i in range(bars)]
    
    # Cyclical wave + linear trend
    t = np.linspace(0, 8 * np.pi, bars)
    price_base = 1000.0 + (trend * np.arange(bars)) + (40.0 * np.sin(t))
    
    opens = price_base + np.random.uniform(-2, 2, bars)
    highs = opens + np.random.uniform(5, 15, bars)
    lows = opens - np.random.uniform(5, 15, bars)
    closes = price_base + np.random.uniform(-3, 3, bars)
    volumes = np.random.randint(50000, 200000, bars)

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": opens.round(2),
        "high": highs.round(2),
        "low": lows.round(2),
        "close": closes.round(2),
        "volume": volumes
    })


# ============================================================================
# 1. Parameter Tick Generation Tests
# ============================================================================

def test_param_tick_generation_integers():
    ticks = generate_param_ticks(min_val=10, max_val=50, step=10)
    assert ticks == [10, 20, 30, 40, 50]
    assert all(isinstance(t, int) for t in ticks)


def test_param_tick_generation_floats():
    ticks = generate_param_ticks(min_val=1.5, max_val=3.0, step=0.5)
    assert len(ticks) == 4
    assert ticks == [1.5, 2.0, 2.5, 3.0]


def test_param_tick_generation_invalid_step():
    with pytest.raises(ValueError, match="Step must be strictly positive"):
        generate_param_ticks(min_val=10, max_val=50, step=0)

    with pytest.raises(ValueError, match="Step must be strictly positive"):
        generate_param_ticks(min_val=10, max_val=50, step=-5)


def test_param_tick_generation_min_greater_than_max():
    with pytest.raises(ValueError, match="min_val.*cannot be greater than max_val"):
        generate_param_ticks(min_val=50, max_val=10, step=5)


# ============================================================================
# 2. Maximum Grid Combinations Cap Tests
# ============================================================================

def test_max_grid_combinations_cap_enforced():
    engine = OptimizationEngine()
    df = generate_synthetic_ohlcv(50)

    # 25 * 25 = 625 combinations (> 400 cap)
    p1 = ParamSpec(name="short_window", min_val=1, max_val=25, step=1)
    p2 = ParamSpec(name="long_window", min_val=50, max_val=74, step=1)

    with pytest.raises(ValueError, match="exceeds the institutional cap of 400"):
        engine.run_grid(
            df=df,
            strategy_name="SMA_CROSS",
            param1=p1,
            param2=p2
        )


def test_grid_combinations_under_cap_allowed():
    engine = OptimizationEngine()
    df = generate_synthetic_ohlcv(60)

    # 4 * 4 = 16 combinations (<= 400 cap)
    p1 = ParamSpec(name="short_window", min_val=10, max_val=25, step=5)
    p2 = ParamSpec(name="long_window", min_val=40, max_val=55, step=5)

    cells, p1_ticks, p2_ticks = engine.run_grid(
        df=df,
        strategy_name="SMA_CROSS",
        param1=p1,
        param2=p2
    )

    assert len(cells) == 16
    assert p1_ticks == [10, 15, 20, 25]
    assert p2_ticks == [40, 45, 50, 55]


# ============================================================================
# 3. Walk-Forward Splitter Tests
# ============================================================================

def test_walk_forward_splitter_chronological_split():
    df = generate_synthetic_ohlcv(100)
    is_df, oos_df, split_date = WalkForwardSplitter.split(df, split_pct=70.0)

    assert len(is_df) == 70
    assert len(oos_df) == 30

    # Ensure zero lookahead leakage: Max timestamp in IS is strictly before Min timestamp in OOS
    assert is_df['timestamp'].max() < oos_df['timestamp'].min()
    assert str(split_date) in str(is_df['timestamp'].max())


def test_walk_forward_splitter_boundary_validation():
    df = generate_synthetic_ohlcv(50)

    with pytest.raises(ValueError, match="split_pct must be between"):
        WalkForwardSplitter.split(df, split_pct=5.0)

    with pytest.raises(ValueError, match="split_pct must be between"):
        WalkForwardSplitter.split(df, split_pct=95.0)

    with pytest.raises(ValueError, match="Cannot split empty DataFrame"):
        WalkForwardSplitter.split(pd.DataFrame(), split_pct=70.0)


def test_walk_forward_efficiency_calculation():
    # Normal positive case: IS = 10000, OOS = 6000 -> WFE = 0.60
    assert WalkForwardSplitter.calculate_wfe(10000.0, 6000.0) == 0.60

    # Strong performance: IS = 5000, OOS = 5000 -> WFE = 1.00
    assert WalkForwardSplitter.calculate_wfe(5000.0, 5000.0) == 1.00

    # Negative OOS: IS = 10000, OOS = -2000 -> WFE = -0.20
    assert WalkForwardSplitter.calculate_wfe(10000.0, -2000.0) == -0.20

    # Unprofitable IS: IS <= 0 -> 0.0
    assert WalkForwardSplitter.calculate_wfe(-1000.0, 5000.0) == 0.0
    assert WalkForwardSplitter.calculate_wfe(0.0, 5000.0) == 0.0


# ============================================================================
# 4. Plateau Stability Index (PSI) & 3x3 Neighborhood Tests
# ============================================================================

def test_stability_analyzer_robust_plateau():
    # Construct a 3x3 grid where center (1, 1) is optimal (Sharpe 2.0)
    # and all 8 neighbors retain ~1.9 Sharpe (Retention ~ 95%)
    p1_ticks = [10.0, 20.0, 30.0]
    p2_ticks = [40.0, 50.0, 60.0]

    cells = []
    for p2 in p2_ticks:
        for p1 in p1_ticks:
            val = 2.0 if (p1 == 20.0 and p2 == 50.0) else 1.9
            cells.append(
                OptimizationCell(
                    param1_val=p1,
                    param2_val=p2,
                    sharpe_ratio=val,
                    net_pnl=val * 10000,
                    net_pnl_pct=val * 2.0,
                    max_drawdown_pct=5.0,
                    win_rate=0.6,
                    total_trades=20,
                    profit_factor=2.1
                )
            )

    result = StabilityAnalyzer.evaluate(cells, p1_ticks, p2_ticks, target_metric="sharpe_ratio")

    assert result.optimal_param1 == 20.0
    assert result.optimal_param2 == 50.0
    assert result.optimal_metric_val == 2.0
    assert result.stability_score >= 0.75
    assert result.classification == "ROBUST_PLATEAU"
    assert result.cliff_drop_pct < 10.0
    assert len(result.neighbors) == 8


def test_stability_analyzer_fragile_cliff():
    # Construct a 3x3 grid where center (1, 1) is a sharp spike (Sharpe 3.0)
    # and surrounding neighbors plummet to 0.3 (Retention ~ 10%)
    p1_ticks = [10.0, 20.0, 30.0]
    p2_ticks = [40.0, 50.0, 60.0]

    cells = []
    for p2 in p2_ticks:
        for p1 in p1_ticks:
            val = 3.0 if (p1 == 20.0 and p2 == 50.0) else 0.3
            cells.append(
                OptimizationCell(
                    param1_val=p1,
                    param2_val=p2,
                    sharpe_ratio=val,
                    net_pnl=val * 10000,
                    net_pnl_pct=val * 2.0,
                    max_drawdown_pct=15.0,
                    win_rate=0.4,
                    total_trades=10,
                    profit_factor=1.1
                )
            )

    result = StabilityAnalyzer.evaluate(cells, p1_ticks, p2_ticks, target_metric="sharpe_ratio")

    assert result.optimal_param1 == 20.0
    assert result.optimal_param2 == 50.0
    assert result.stability_score < 0.50
    assert result.classification == "FRAGILE_CLIFF"
    assert result.cliff_drop_pct >= 80.0


def test_stability_analyzer_moderate_sensitivity():
    # Moderate neighborhood retention (~60%)
    p1_ticks = [10.0, 20.0, 30.0]
    p2_ticks = [40.0, 50.0, 60.0]

    cells = []
    for p2 in p2_ticks:
        for p1 in p1_ticks:
            val = 2.0 if (p1 == 20.0 and p2 == 50.0) else 1.2
            cells.append(
                OptimizationCell(
                    param1_val=p1,
                    param2_val=p2,
                    sharpe_ratio=val,
                    net_pnl=val * 10000,
                    net_pnl_pct=val * 2.0,
                    max_drawdown_pct=8.0,
                    win_rate=0.5,
                    total_trades=15,
                    profit_factor=1.5
                )
            )

    result = StabilityAnalyzer.evaluate(cells, p1_ticks, p2_ticks, target_metric="sharpe_ratio")

    assert 0.50 <= result.stability_score < 0.75
    assert result.classification == "MODERATE_SENSITIVITY"


def test_stability_analyzer_corner_cell_handling():
    # Optimal cell is at corner (0, 0), so it only has 3 valid neighbors in bounds
    p1_ticks = [10.0, 20.0, 30.0]
    p2_ticks = [40.0, 50.0, 60.0]

    cells = []
    for p2 in p2_ticks:
        for p1 in p1_ticks:
            val = 3.0 if (p1 == 10.0 and p2 == 40.0) else 2.5
            cells.append(
                OptimizationCell(
                    param1_val=p1,
                    param2_val=p2,
                    sharpe_ratio=val,
                    net_pnl=val * 10000,
                    net_pnl_pct=val * 2.0,
                    max_drawdown_pct=5.0,
                    win_rate=0.6,
                    total_trades=12,
                    profit_factor=2.0
                )
            )

    result = StabilityAnalyzer.evaluate(cells, p1_ticks, p2_ticks, target_metric="sharpe_ratio")

    assert result.optimal_param1 == 10.0
    assert result.optimal_param2 == 40.0
    # Corner cell has exactly 3 neighbors: (10,50), (20,40), (20,50)
    assert len(result.neighbors) == 3
    assert result.classification == "ROBUST_PLATEAU"


# ============================================================================
# 5. Optimization Engine Execution & Zero Trades Resilience Tests
# ============================================================================

def test_optimization_engine_cell_evaluation():
    engine = OptimizationEngine(max_workers=2)
    df = generate_synthetic_ohlcv(150, trend=1.0)

    cell = engine.evaluate_cell(
        df=df,
        strategy_name="SMA_CROSS",
        param1_name="short_window",
        param1_val=10,
        param2_name="long_window",
        param2_val=30,
        base_params={},
        base_config={"initial_capital": 500000.0, "slippage_bps": 5.0}
    )

    assert isinstance(cell, OptimizationCell)
    assert cell.param1_val == 10
    assert cell.param2_val == 30
    assert isinstance(cell.sharpe_ratio, float)
    assert isinstance(cell.win_rate, float)
    assert isinstance(cell.total_trades, int)


def test_optimization_engine_zero_trades_graceful_handling():
    # Flat data where no crossover occurs -> 0 trades
    dates = pd.date_range("2023-01-01", periods=50, freq="1D")
    flat_df = pd.DataFrame({
        "timestamp": dates,
        "open": [1000.0] * 50,
        "high": [1000.0] * 50,
        "low": [1000.0] * 50,
        "close": [1000.0] * 50,
        "volume": [10000] * 50
    })

    engine = OptimizationEngine(max_workers=2)
    cell = engine.evaluate_cell(
        df=flat_df,
        strategy_name="SMA_CROSS",
        param1_name="short_window",
        param1_val=10,
        param2_name="long_window",
        param2_val=30,
        base_params={},
        base_config={"initial_capital": 1000000.0}
    )

    # Must not throw ZeroDivisionError and should return zeroed stats
    assert cell.total_trades == 0
    assert cell.net_pnl == 0.0
    assert cell.win_rate == 0.0
    assert cell.profit_factor == 0.0
    assert cell.max_drawdown_pct == 0.0


# ============================================================================
# 6. End-to-End Walk-Forward Optimization Workflow Tests
# ============================================================================

def test_optimize_with_walk_forward_end_to_end():
    engine = OptimizationEngine(max_workers=4)
    df = generate_synthetic_ohlcv(200, trend=0.8)

    p1 = ParamSpec(name="short_window", min_val=10, max_val=20, step=5)
    p2 = ParamSpec(name="long_window", min_val=30, max_val=40, step=5)

    result = engine.optimize_with_walk_forward(
        df=df,
        strategy_name="SMA_CROSS",
        param1=p1,
        param2=p2,
        walk_forward_split_pct=70.0,
        target_metric="sharpe_ratio",
        base_params={},
        base_config={"initial_capital": 1000000.0, "slippage_bps": 5.0}
    )

    assert result["strategy"] == "SMA_CROSS"
    assert result["total_combinations"] == 9  # 3 * 3
    assert result["execution_time_ms"] > 0
    assert len(result["matrix"]) == 9

    # Check stability result
    stability = result["stability"]
    assert isinstance(stability, StabilityResult)
    assert stability.classification in ("ROBUST_PLATEAU", "MODERATE_SENSITIVITY", "FRAGILE_CLIFF")

    # Check walk forward result
    wf = result["walk_forward"]
    assert isinstance(wf, WalkForwardResult)
    assert wf.is_split_pct == 70.0
    assert isinstance(wf.walk_forward_efficiency, float)
    assert wf.split_date != ""


def test_create_strategy_instance():
    sma = create_strategy_instance("SMA_CROSS")
    assert sma.__class__.__name__ == "SMACrossStrategy"

    rsi = create_strategy_instance("RSI_REVERSION")
    assert rsi.__class__.__name__ == "RSIReversalStrategy"

    bb = create_strategy_instance("BOLLINGER_BANDS")
    assert bb.__class__.__name__ == "BollingerBandsStrategy"

    st = create_strategy_instance("SUPERTREND")
    assert st.__class__.__name__ == "SupertrendStrategy"

    macd = create_strategy_instance("MACD")
    assert macd.__class__.__name__ == "MACDStrategy"
