"""
Pydantic Models for Options & Open Interest Analytics.
Defines schemas for Strike-by-Strike OI, Net Greeks, Payoff, and F&O Underlyings.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class StrikeOIData(BaseModel):
    """Open Interest and intraday shift breakdown for an individual strike price."""
    strike: float
    call_oi: int = Field(..., description="Call Open Interest in contracts")
    call_oi_change: int = Field(0, description="Intraday shift in Call Open Interest")
    put_oi: int = Field(..., description="Put Open Interest in contracts")
    put_oi_change: int = Field(0, description="Intraday shift in Put Open Interest")
    call_volume: int = Field(0, description="Cumulative Call volume")
    put_volume: int = Field(0, description="Cumulative Put volume")
    call_ltp: float = Field(0.0, description="Call Last Traded Price")
    put_ltp: float = Field(0.0, description="Put Last Traded Price")
    call_iv: float = Field(0.0, description="Call Implied Volatility percentage")
    put_iv: float = Field(0.0, description="Put Implied Volatility percentage")


class OpenInterestAnalysisResponse(BaseModel):
    """Institutional Open Interest and PCR sentiment report for an underlying."""
    symbol: str
    spot: float
    expiry_date: str
    total_call_oi: int
    total_put_oi: int
    total_call_oi_change: int
    total_put_oi_change: int
    pcr_oi: float
    pcr_oi_change: float
    sentiment: str  # BULLISH | BEARISH | NEUTRAL
    major_resistance_strike: float
    major_support_strike: float
    max_pain_strike: float
    active_call_battleground: float
    active_put_battleground: float
    strikes_data: List[StrikeOIData]


class FOUnderlyingItem(BaseModel):
    """Metadata and standardized lot configuration for an NSE F&O underlying."""
    symbol: str
    display_name: str
    category: str  # INDEX | EQUITY
    lot_size: int
    spot_price: float
    strike_step: float


class FOUnderlyingListResponse(BaseModel):
    """Registry response containing all supported NSE F&O underlying assets."""
    indices: List[FOUnderlyingItem]
    equities: List[FOUnderlyingItem]
    total_count: int


class OptionLeg(BaseModel):
    """Individual option position leg in a multi-leg options strategy."""
    strike: float
    option_type: str = Field(..., description="Option type: CE or PE")
    position: str = Field(..., description="Position side: LONG or SHORT")
    premium: float = Field(..., description="Option trade premium in rupees/points")
    quantity: int = Field(1, ge=1, description="Quantity multiplier / lot count")
    iv: Optional[float] = Field(None, description="Implied volatility (percentage e.g. 15.0 or decimal 0.15)")


class StrategyGreeksRequest(BaseModel):
    """Request payload for multi-leg strategy Net Greeks aggregation."""
    symbol: str
    spot: float
    t_days: float = Field(..., gt=0, description="Calendar days to expiration")
    r: float = Field(0.065, description="Risk-free interest rate (default 6.5% for RBI MIBOR)")
    legs: List[OptionLeg]


class StrategyGreeksResponse(BaseModel):
    """Aggregated Net Greeks and lot-size adjusted INR rupee risks."""
    symbol: str
    lot_size: int
    net_delta: float
    net_gamma: float
    net_theta: float
    net_vega: float
    delta_inr: float
    theta_inr: float
    vega_inr: float
    net_premium: float
    total_cost_inr: float


class PayoffPoint(BaseModel):
    """Coordinate on a payoff P&L curve."""
    spot: float
    pnl: float


class PayoffSimulationRequest(BaseModel):
    """Request payload for pre-expiration theoretical and expiry payoff simulation."""
    symbol: str
    spot: float
    t_days_remaining: float = Field(..., gt=0, description="Total days remaining until contract expiry")
    target_days: float = Field(..., gt=0, description="Evaluation target days remaining (T+x)")
    iv_shock_pct: float = Field(0.0, description="Implied volatility shift percentage (e.g. +10.0 or -15.0)")
    r: float = Field(0.065, description="Risk-free interest rate")
    legs: List[OptionLeg]


class PayoffSimulationResponse(BaseModel):
    """Complete payoff simulation response containing curves, metrics, and breakevens."""
    symbol: str
    lot_size: int
    spot: float
    max_profit: float
    max_loss: float
    risk_reward_ratio: Optional[float] = None
    breakevens: List[float]
    net_debit_credit_inr: float
    expiration_curve: List[PayoffPoint]
    target_date_curve: List[PayoffPoint]
