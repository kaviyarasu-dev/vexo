from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any


class CalendarDayItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: str  # YYYY-MM-DD
    day_of_month: int
    day_of_week: int  # 0=Monday, ..., 6=Sunday
    net_pnl: float
    gross_pnl: float
    total_charges: float
    trades_count: int
    win_count: int
    loss_count: int
    status: str  # 'WIN' | 'LOSS' | 'EVEN' | 'NO_TRADES'


class CalendarWeekSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    week_number: int
    net_pnl: float
    trades_count: int
    win_count: int
    loss_count: int


class CalendarMonthlyKPIs(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    monthly_net_pnl: float
    trading_days: int
    win_days: int
    loss_days: int
    win_day_pct: float
    max_win_streak: int
    max_loss_streak: int
    avg_win_day_pnl: float
    avg_loss_day_pnl: float
    profit_factor: float


class CalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = True
    year: int
    month: int
    kpis: CalendarMonthlyKPIs
    days: List[CalendarDayItem]
    weeks: List[CalendarWeekSummary]


class DiagnosticBucket(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    label: str
    trades_count: int
    win_rate: float
    net_pnl: float
    avg_r: float
    profit_factor: float


class DiagnosticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool = True
    time_of_day: List[DiagnosticBucket]
    direction: List[DiagnosticBucket]
    duration: List[DiagnosticBucket]
    instruments: List[DiagnosticBucket]
