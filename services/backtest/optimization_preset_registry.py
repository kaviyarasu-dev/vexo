"""
optimization_preset_registry.py
Curated strategy parameter ranges and presets for institutional 2D Grid Optimization.
"""

from typing import List, Dict, Optional
from api.models.optimization_models import ParamRangeSpec, StrategyOptimizationPreset


PRESETS_REGISTRY: List[StrategyOptimizationPreset] = [
    StrategyOptimizationPreset(
        strategy="SMA_CROSS",
        label="SMA Crossover (Fast & Slow Windows)",
        param1=ParamRangeSpec(
            name="short_window",
            min_val=5.0,
            max_val=30.0,
            step=5.0
        ),
        param2=ParamRangeSpec(
            name="long_window",
            min_val=30.0,
            max_val=100.0,
            step=10.0
        )
    ),
    StrategyOptimizationPreset(
        strategy="RSI_REVERSION",
        label="RSI Mean Reversion (Period & Oversold)",
        param1=ParamRangeSpec(
            name="rsi_period",
            min_val=7.0,
            max_val=21.0,
            step=2.0
        ),
        param2=ParamRangeSpec(
            name="oversold",
            min_val=20.0,
            max_val=40.0,
            step=5.0
        )
    ),
    StrategyOptimizationPreset(
        strategy="BOLLINGER_BANDS",
        label="Bollinger Bands Reversal (Period & Std Dev)",
        param1=ParamRangeSpec(
            name="period",
            min_val=10.0,
            max_val=30.0,
            step=5.0
        ),
        param2=ParamRangeSpec(
            name="std_dev",
            min_val=1.5,
            max_val=3.0,
            step=0.25
        )
    ),
    StrategyOptimizationPreset(
        strategy="SUPERTREND",
        label="Supertrend Volatility Breakout (Period & Multiplier)",
        param1=ParamRangeSpec(
            name="period",
            min_val=7.0,
            max_val=14.0,
            step=1.0
        ),
        param2=ParamRangeSpec(
            name="multiplier",
            min_val=1.5,
            max_val=4.0,
            step=0.5
        )
    ),
    StrategyOptimizationPreset(
        strategy="MACD",
        label="MACD Momentum Trend (Fast & Slow EMA)",
        param1=ParamRangeSpec(
            name="fast_period",
            min_val=8.0,
            max_val=16.0,
            step=2.0
        ),
        param2=ParamRangeSpec(
            name="slow_period",
            min_val=20.0,
            max_val=34.0,
            step=2.0
        )
    )
]


def get_optimization_presets() -> List[StrategyOptimizationPreset]:
    """Retrieve all curated strategy parameter presets."""
    return list(PRESETS_REGISTRY)


def get_preset_for_strategy(strategy_name: str) -> Optional[StrategyOptimizationPreset]:
    """Retrieve preset by strategy name with case-insensitive matching."""
    s_upper = strategy_name.upper()
    for preset in PRESETS_REGISTRY:
        if preset.strategy.upper() == s_upper:
            return preset
        # Alias matches
        if s_upper in ("SMA", "SMA CROSSOVER") and preset.strategy == "SMA_CROSS":
            return preset
        if s_upper in ("RSI", "RSI REVERSAL") and preset.strategy == "RSI_REVERSION":
            return preset
        if s_upper in ("BB", "BOLLINGER") and preset.strategy == "BOLLINGER_BANDS":
            return preset
        if s_upper in ("SUPER_TREND",) and preset.strategy == "SUPERTREND":
            return preset
        if s_upper in ("MACD_MOMENTUM",) and preset.strategy == "MACD":
            return preset
    return None
