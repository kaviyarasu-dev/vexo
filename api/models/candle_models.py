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
    next_cursor: Optional[str] = None
    candles: List[CandleDto]
    is_live: Optional[bool] = False
    auth_status: Optional[str] = "OK"
    message: Optional[str] = None

class LiveQuoteDto(BaseModel):
    ltp: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    prev_close: Optional[float] = None
    ch: Optional[float] = None
    chp: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[int] = None

class LiveCandleResponse(BaseModel):
    symbol: str
    timeframe: str
    candle: Optional[CandleDto] = None
    quote: Optional[LiveQuoteDto] = None
    is_live: bool = True
    auth_status: str = "OK"
    message: Optional[str] = None

