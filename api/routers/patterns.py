from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
import pytz

from api.models.envelope import ApiResponse
from services.pattern_recognition_service import PatternRecognitionService
from services.resampling_service import ResamplingService
from db.connection import get_db

router = APIRouter()
_scanner = PatternRecognitionService()


class PatternScanRequest(BaseModel):
    symbol: Optional[str] = None
    timeframe: Optional[str] = "5m"
    candles: Optional[List[Dict[str, Any]]] = None
    patterns: Optional[List[str]] = None


@router.post("/api/v1/studies/patterns", response_model=ApiResponse[Dict[str, Any]])
def scan_patterns(
    request: Request,
    payload: PatternScanRequest
):
    correlation_id = getattr(request.state, "correlation_id", "req-pattern-scan")

    # If client passed raw candles directly (e.g. from current chart viewport)
    if payload.candles and len(payload.candles) >= 3:
        df = pd.DataFrame(payload.candles)
        # Ensure timestamp column or time column exists
        if 'time' in df.columns and 'timestamp' not in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
    elif payload.symbol:
        # Query and resample from DuckDB
        start_dt = datetime(2000, 1, 1, tzinfo=pytz.utc)
        end_dt = datetime(2100, 1, 1, tzinfo=pytz.utc)
        service = ResamplingService(get_db())
        df = service.resample(
            symbol=payload.symbol,
            target_timeframe=payload.timeframe or "5m",
            start=start_dt,
            end=end_dt,
            adjusted=True
        )
    else:
        df = pd.DataFrame()

    if df.empty or len(df) < 3:
        return ApiResponse.success_response(
            data={"signals": [], "markers": [], "count": 0},
            correlation_id=correlation_id
        )

    signals = _scanner.scan_all(df, enabled_patterns=payload.patterns)
    markers = _scanner.to_chart_markers(signals)

    return ApiResponse.success_response(
        data={
            "signals": [
                {
                    "time": s.time,
                    "pattern_id": s.pattern_id,
                    "pattern_name": s.pattern_name,
                    "sentiment": s.sentiment,
                    "badge_text": s.badge_text,
                    "price": s.price,
                    "description": s.description,
                    "confirmation_rule": s.confirmation_rule,
                    "historical_accuracy_pct": s.historical_accuracy_pct
                }
                for s in signals
            ],
            "markers": markers,
            "count": len(signals)
        },
        correlation_id=correlation_id
    )
