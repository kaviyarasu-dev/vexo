from fastapi import APIRouter, Query, Request
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pytz

from api.models.envelope import ApiResponse
from services.indicators.volume_profile import VolumeProfileEngine
from services.resampling_service import ResamplingService
from db.connection import get_db

router = APIRouter()
_engine = VolumeProfileEngine()


@router.get("/api/v1/studies/session-volume-profile", response_model=ApiResponse[Dict[str, Any]])
def get_session_volume_profile(
    request: Request,
    symbol: str = Query(...),
    timeframe: str = Query("5m"),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    rows: int = Query(50, ge=10, le=200),
    value_area_pct: float = Query(0.70, ge=0.50, le=0.95)
):
    correlation_id = getattr(request.state, "correlation_id", "req-svp-profile")
    
    start_dt = from_date or datetime(2000, 1, 1, tzinfo=pytz.utc)
    end_dt = to_date or datetime(2100, 1, 1, tzinfo=pytz.utc)

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=pytz.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=pytz.utc)

    service = ResamplingService(get_db())
    df = service.resample(
        symbol=symbol,
        target_timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        adjusted=True
    )

    if df.empty:
        return ApiResponse.success_response(
            data={"symbol": symbol, "timeframe": timeframe, "sessions": {}},
            correlation_id=correlation_id
        )

    engine = VolumeProfileEngine(default_rows=rows, default_value_area_pct=value_area_pct)
    sessions = engine.compute_session_profiles(df, num_rows=rows, value_area_pct=value_area_pct)

    return ApiResponse.success_response(
        data={
            "symbol": symbol,
            "timeframe": timeframe,
            "sessions": sessions
        },
        correlation_id=correlation_id
    )


@router.get("/api/v1/studies/tpo-profile", response_model=ApiResponse[Optional[Dict[str, Any]]])
def get_tpo_market_profile(
    request: Request,
    symbol: str = Query(...),
    session_date: Optional[str] = Query(None),
    tick_size: float = Query(0.5, ge=0.05, le=10.0)
):
    correlation_id = getattr(request.state, "correlation_id", "req-tpo-profile")

    start_dt = datetime(2000, 1, 1, tzinfo=pytz.utc)
    end_dt = datetime(2100, 1, 1, tzinfo=pytz.utc)

    service = ResamplingService(get_db())
    df = service.resample(
        symbol=symbol,
        target_timeframe="5m",
        start=start_dt,
        end=end_dt,
        adjusted=True
    )

    if df.empty:
        return ApiResponse.success_response(data=None, correlation_id=correlation_id)

    engine = VolumeProfileEngine()
    tpo_result = engine.compute_tpo(df, tick_size=tick_size, session_date=session_date)

    return ApiResponse.success_response(
        data=tpo_result.to_dict() if tpo_result else None,
        correlation_id=correlation_id
    )
