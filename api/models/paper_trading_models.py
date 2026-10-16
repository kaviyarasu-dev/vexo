from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    symbol: str
    side: str = Field(..., pattern="^(?i)(BUY|SELL)$", description="BUY or SELL")
    quantity: int = Field(..., gt=0, description="Order quantity")
    order_type: str = Field(default="MARKET", pattern="^(?i)(MARKET|LIMIT)$", description="MARKET or LIMIT")
    trade_type: str = Field(default="DELIVERY", pattern="^(?i)(DELIVERY|INTRADAY)$", description="DELIVERY or INTRADAY")
    price: Optional[float] = Field(default=None, description="Limit price if LIMIT order")
    stop_loss: Optional[float] = Field(default=None, description="Stop loss price level")
    take_profit: Optional[float] = Field(default=None, description="Take profit price level")
    trailing_sl_pct: Optional[float] = Field(default=None, description="Trailing stop loss %")


class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    side: str
    order_type: str
    trade_type: str
    quantity: int
    fill_price: float
    total_charges: float
    status: str
    executed_at: str


class PositionResponse(BaseModel):
    symbol: str
    side: str
    trade_type: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_sl_pct: Optional[float] = None
    updated_at: str


class AccountResponse(BaseModel):
    account_id: str
    balance: float
    initial_balance: float
    margin_utilized: float
    available_balance: float
    realized_pnl: float
    total_unrealized_pnl: float
    net_portfolio_value: float


class ClosePositionRequest(BaseModel):
    exit_price: Optional[float] = None


class UpdateRiskRequest(BaseModel):
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_sl_pct: Optional[float] = None


class DeployStrategyRequest(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str = "1D"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    trade_type: str = "DELIVERY"
    allocated_capital: float = 100000.0


class AutoStrategyResponse(BaseModel):
    strategy_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    parameters: Dict[str, Any]
    trade_type: str
    allocated_capital: float
    status: str
    created_at: str


class TradeHistoryItem(BaseModel):
    trade_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    fill_price: float
    brokerage: float
    stt: float
    total_charges: float
    gross_pnl: float
    net_pnl: float
    executed_at: str
