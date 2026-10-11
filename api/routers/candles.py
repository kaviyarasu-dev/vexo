from fastapi import APIRouter, Query, Request
from typing import Optional
from datetime import datetime
import base64
import pytz

from api.models.envelope import ApiResponse
from api.models.candle_models import CandleQueryResponse, CandleDto
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo

router = APIRouter()

def encode_cursor(timestamp_iso: str) -> str:
    return base64.b64encode(timestamp_iso.encode('utf-8')).decode('utf-8')

def decode_cursor(cursor: str) -> str:
    return base64.b64decode(cursor.encode('utf-8')).decode('utf-8')

@router.get("/api/v1/candles", response_model=ApiResponse[CandleQueryResponse])
def get_candles(
    request: Request,
    symbol: str = Query(...),
    timeframe: str = Query("5m"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    adjusted: bool = Query(True),
    indicators: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    cursor: Optional[str] = Query(None)
):
    correlation_id = getattr(request.state, "correlation_id", "req-candles-001")
    
    # decode cursor if present
    decoded_cursor = decode_cursor(cursor) if cursor else None
    
    repo = DuckDBCandleRepo()
    
    from services.resampling_service import ResamplingService
    from db.connection import get_db
    
    start_dt = from_date or datetime(2000, 1, 1)
    end_dt = to_date or datetime(2100, 1, 1)
    
    # Check if we should use cursor
    if decoded_cursor:
        end_dt = datetime.fromisoformat(decoded_cursor.replace('Z', '+00:00'))

    # If datetime objects are naive, localize them to UTC before passing to resample
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=pytz.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=pytz.utc)

    service = ResamplingService(get_db())
    
    # Resample returns a Pandas DataFrame
    df = service.resample(
        symbol=symbol, 
        target_timeframe=timeframe, 
        start=start_dt, 
        end=end_dt, 
        adjusted=adjusted
    )
    
    dtos = []
    if not df.empty:
        # Take the last `limit` rows (backward lazy-loading)
        chunk = df.tail(limit)
        
        for _, row in chunk.iterrows():
            dtos.append(CandleDto(
                time=int(row['timestamp'].timestamp()),
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=int(row['volume'])
            ))
            
    next_cursor = None
    if len(dtos) == limit:
        # The earliest timestamp in this chunk
        earliest_dt = chunk.iloc[0]['timestamp']
        # Convert to string format compatible with isoformat
        iso_str = earliest_dt.isoformat().replace('+00:00', 'Z')
        next_cursor = encode_cursor(iso_str)
            
    response_data = CandleQueryResponse(
        symbol=symbol,
        timeframe=timeframe,
        adjusted=adjusted,
        count=len(dtos),
        next_cursor=next_cursor,
        candles=dtos
    )
    
    return ApiResponse.success_response(data=response_data, correlation_id=correlation_id)
