from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CandleDto(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    # indicators can be added dynamically or not enforced by pydantic

    class Config:
        extra = 'allow'

class CandleQueryResponse(BaseModel):
    symbol: str
    timeframe: str
    adjusted: bool
    count: int
    next_cursor: Optional[str]
    candles: List[CandleDto]
