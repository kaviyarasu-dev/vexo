"""
optimization_models.py
Pydantic Request and Response Schemas for Strategy Parameter Optimization, 
3x3 Plateau Stability Index, and Walk-Forward Validation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ParamRangeSpec(BaseModel):
    name: str = Field(..., description="Parameter variable name (e.g. short_window, rsi_period)")
    min_val: float = Field(..., description="Minimum parameter value")
    max_val: float = Field(..., description="Maximum parameter value")
    step: float = Field(..., gt=0.0, description="Step increment (strictly positive)")


class OptimizationRequest(BaseModel):
    strategy: str = Field(..., description="Quant strategy identifier (e.g. SMA_CROSS, RSI_REVERSION)")
    symbol: str = Field(..., description="Trading symbol (e.g. NSE:RELIANCE-EQ)")
    timeframe: str = Field(default="1D", description="Candle timeframe (1D, 1h, 15m)")
    start_date: str = Field(default="2020-01-01", description="Start date (YYYY-MM-DD)")
    end_date: str = Field(default="2023-12-31", description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(default=1000000.0, ge=1000.0, description="Starting capital in INR")
    slippage_bps: float = Field(default=5.0, ge=0.0, description="Slippage in basis points")
    trade_type: str = Field(default="DELIVERY", description="Trade type (DELIVERY or INTRADAY)")
    stop_loss_pct: Optional[float] = Field(default=None, ge=0.0, description="Stop loss percentage per trade")
    take_profit_pct: Optional[float] = Field(default=None, ge=0.0, description="Take profit percentage per trade")
    param1: ParamRangeSpec = Field(..., description="First parameter search range")
    param2: ParamRangeSpec = Field(..., description="Second parameter search range")
    walk_forward_split_pct: float = Field(default=70.0, ge=10.0, le=90.0, description="In-sample partition percentage (10-90%)")
    target_metric: str = Field(default="sharpe_ratio", description="Target metric: sharpe_ratio, net_pnl, max_drawdown_pct, win_rate")
    base_params: Dict[str, Any] = Field(default_factory=dict, description="Fixed baseline parameters for other strategy settings")


class HeatmapCellDto(BaseModel):
    param1_val: float
    param2_val: float
    sharpe_ratio: float
    net_pnl: float
    net_pnl_pct: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profit_factor: float


class StabilityDto(BaseModel):
    optimal_param1: float
    optimal_param2: float
    optimal_metric_val: float
    stability_score: float
    classification: str  # 'ROBUST_PLATEAU' | 'MODERATE_SENSITIVITY' | 'FRAGILE_CLIFF'
    neighbor_avg_val: float
    cliff_drop_pct: float
    neighbors: List[Dict[str, Any]] = Field(default_factory=list)


class WalkForwardDto(BaseModel):
    in_sample_net_pnl: float
    in_sample_sharpe: float
    out_of_sample_net_pnl: float
    out_of_sample_sharpe: float
    walk_forward_efficiency: float
    split_date: str
    is_split_pct: float


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = True
    strategy: str
    symbol: str
    param1_name: str
    param2_name: str
    param1_ticks: List[float]
    param2_ticks: List[float]
    total_combinations: int
    execution_time_ms: float
    best_params: Dict[str, Any]
    stability: StabilityDto
    walk_forward: WalkForwardDto
    matrix: List[HeatmapCellDto]


class StrategyOptimizationPreset(BaseModel):
    strategy: str
    label: str
    param1: ParamRangeSpec
    param2: ParamRangeSpec


class PresetsResponse(BaseModel):
    success: bool = True
    presets: List[StrategyOptimizationPreset]
