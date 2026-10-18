from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class SymbolSummary(BaseModel):
    symbol: str
    name: str
    lot_size: int = 1
    category: Optional[str] = None
    tier: int = 4
    priority_rank: int = 9999
    is_active: bool = True

class SymbolDetail(SymbolSummary):
    isin: Optional[str] = None
    exchange: Optional[str] = None
    segment: Optional[str] = None
    series: Optional[str] = None
    tick_size: float
    listing_date: Optional[date] = None
    updated_at: Optional[datetime] = None
    # Additional metadata can be added here
