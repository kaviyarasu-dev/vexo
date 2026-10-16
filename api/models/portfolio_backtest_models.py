"""
Pydantic Request and Response Schemas for Portfolio / Multi-Stock Basket Backtesting.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PortfolioBacktestRequest(BaseModel):
    strategy: str = Field(..., description="Strategy identifier, e.g. SMA_CROSS, RSI_REVERSION, SUPERTREND, MACD")
    universe_type: str = Field(default="PREDEFINED", description="PREDEFINED or CUSTOM")
    universe_name: Optional[str] = Field(default="NIFTY_50", description="Predefined universe name (NIFTY_50, NIFTY_NEXT_50, NIFTY_MIDCAP_150)")
    symbols: Optional[List[str]] = Field(default=None, description="Custom list of symbols if universe_type is CUSTOM")
    timeframe: str = Field(default="1D", description="Candle timeframe: 1D, 1h, 15m, 5m")
    start_date: str = Field(default="2020-01-01", description="Start date (YYYY-MM-DD)")
    end_date: str = Field(default="2023-12-31", description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(default=1000000.0, ge=10000.0, description="Starting capital in INR")
    max_open_positions: int = Field(default=10, ge=1, le=50, description="Max concurrent open positions (slots)")
    sizing_model: str = Field(default="EQUAL_WEIGHT", description="Position sizing model: EQUAL_WEIGHT, INVERSE_ATR, FIXED_AMOUNT")
    sizing_val: float = Field(default=10.0, ge=0.0, description="Sizing parameter value (% per slot or fixed INR)")
    ranking_metric: str = Field(default="AUTO", description="Signal contention ranking metric: AUTO, RSI_OVERSOLD, ROC_MOMENTUM, VOLUME_SURGE")
    slippage_bps: float = Field(default=5.0, ge=0.0, description="Slippage in basis points")
    stop_loss_pct: Optional[float] = Field(default=None, ge=0.0, description="Stop loss percentage per position")
    take_profit_pct: Optional[float] = Field(default=None, ge=0.0, description="Take profit percentage per position")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters dict")


class DailyEquityPoint(BaseModel):
    timestamp: str
    equity: float
    cash: float
    invested: float
    open_positions: int
    exposure_ratio: float


class AssetContribution(BaseModel):
    symbol: str
    trade_count: int
    win_rate: float
    net_pnl: float
    alpha_contribution_pct: float


class PortfolioMetrics(BaseModel):
    initial_capital: float
    final_equity: float
    net_profit: float
    return_pct: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_statutory_costs: float
    avg_exposure_ratio: float
    benchmark_cagr: float
    benchmark_return_pct: float


class PortfolioBacktestResponse(BaseModel):
    backtest_id: str
    status: str = "COMPLETED"
    strategy: str
    universe_name: str
    symbols_tested: List[str]
    skipped_symbols: List[str] = Field(default_factory=list)
    metrics: PortfolioMetrics
    equity_curve: List[DailyEquityPoint]
    benchmark_curve: List[Dict[str, Any]]
    asset_contributions: List[AssetContribution]
    monthly_returns: Dict[str, Dict[str, float]]
    trades: List[Dict[str, Any]]


class PortfolioUniverseItem(BaseModel):
    id: str
    name: str
    description: str
    count: int
    tier: int
