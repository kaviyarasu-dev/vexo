from fastapi import APIRouter, Query, Request
from typing import Optional
from datetime import datetime
import base64
import pytz

from api.models.envelope import ApiResponse
from api.models.candle_models import CandleQueryResponse, CandleDto, LiveCandleResponse
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
    cursor: Optional[str] = Query(None),
    refresh_live: bool = Query(True),
):
    correlation_id = getattr(request.state, "correlation_id", "req-candles-001")
    
    # decode cursor if present
    decoded_cursor = decode_cursor(cursor) if cursor else None
    
    from services.resampling_service import ResamplingService
    from services.live_market_data_service import LiveMarketDataService
    from db.connection import get_db

    db = get_db()
    is_live = False
    auth_status = "OK"
    live_msg = None

    # On initial request (not cursor-paginating older history), ensure data is freshly synced from Fyers
    if refresh_live and not decoded_cursor and not to_date:
        try:
            live_service = LiveMarketDataService(db=db)
            sync_res = live_service.ensure_symbol_freshness(symbol, timeframe)
            is_live = sync_res.get("is_live", False)
            auth_status = sync_res.get("status", "OK")
            live_msg = sync_res.get("message")
        except Exception as exc:
            auth_status = "ERROR"
            live_msg = str(exc)
    
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

    service = ResamplingService(db)
    
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
        
        import pandas as pd
        for _, row in chunk.iterrows():
            c_close = float(row['close']) if pd.notna(row['close']) else 0.0
            c_open = float(row['open']) if pd.notna(row['open']) else c_close
            c_high = float(row['high']) if pd.notna(row['high']) else max(c_open, c_close)
            c_low = float(row['low']) if pd.notna(row['low']) else min(c_open, c_close)
            c_vol = int(row['volume']) if pd.notna(row['volume']) else 0

            dtos.append(CandleDto(
                time=int(row['timestamp'].timestamp()),
                open=c_open,
                high=c_high,
                low=c_low,
                close=c_close,
                volume=c_vol
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
        candles=dtos,
        is_live=is_live,
        auth_status=auth_status,
        message=live_msg,
    )
    
    return ApiResponse.success_response(data=response_data, correlation_id=correlation_id)


@router.get("/api/v1/candles/live", response_model=ApiResponse[LiveCandleResponse])
def get_live_candle(
    request: Request,
    symbol: str = Query(...),
    timeframe: str = Query("5m"),
):
    correlation_id = getattr(request.state, "correlation_id", "req-candles-live-001")
    from db.connection import get_db
    from services.live_market_data_service import LiveMarketDataService

    live_service = LiveMarketDataService(db=get_db())
    live_res = live_service.get_live_candle(symbol, timeframe)
    return ApiResponse.success_response(data=live_res, correlation_id=correlation_id)

