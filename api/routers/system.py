import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from api.models.envelope import ApiResponse

router = APIRouter()

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


import threading
from typing import Optional
from services.downloader_service import HistoricalDownloader

_DOWNLOADER_INSTANCE: Optional[HistoricalDownloader] = None
_DOWNLOADER_LOCK = threading.Lock()


def get_downloader_instance() -> HistoricalDownloader:
    """Provides a singleton instance of HistoricalDownloader within the server process."""
    global _DOWNLOADER_INSTANCE
    with _DOWNLOADER_LOCK:
        if _DOWNLOADER_INSTANCE is None:
            _DOWNLOADER_INSTANCE = HistoricalDownloader()
        return _DOWNLOADER_INSTANCE


async def event_generator(request: Request):
    """Streams live downloader engine telemetry, RateGovernor quota usage, and DuckDB checkpoints."""
    from core.rate_governor import get_rate_governor
    from db.connection import get_db

    downloader = get_downloader_instance()
    governor = get_rate_governor()

    while True:
        if await request.is_disconnected():
            break

        status = downloader.get_status()
        is_running = status.get("is_running", False)
        is_paused = status.get("is_paused", False)

        total_symbols = 0
        completed_symbols = 0
        try:
            db = get_db()
            cursor = db.get_read_cursor()
            try:
                tot_row = cursor.execute("SELECT count(*) FROM symbols WHERE is_active = TRUE").fetchone()
                if tot_row and tot_row[0]:
                    total_symbols = int(tot_row[0])
                comp_row = cursor.execute(
                    "SELECT count(DISTINCT symbol) FROM download_checkpoints WHERE status = 'COMPLETED'"
                ).fetchone()
                if comp_row and comp_row[0]:
                    completed_symbols = int(comp_row[0])
            finally:
                cursor.close()
        except Exception:
            pass

        if is_running:
            state_label = "Paused" if is_paused else "Downloading"
        else:
            state_label = "Idle"

        progress_pct = round((completed_symbols / total_symbols * 100), 1) if total_symbols > 0 else 0

        # Current rolling minute speed or candles ingested speed
        speed_req_min = len(governor._minute_window) if hasattr(governor, "_minute_window") else 0
        speed_display = f"{speed_req_min}" if is_running else "--"

        # Quota used today from RateGovernor
        quota_used = f"{governor.daily_count:,}"

        # Current active batch symbol and timeframe
        curr_sym = status.get("current_symbol")
        curr_tf = status.get("current_timeframe")
        curr_batch = f"{curr_sym} ({curr_tf})" if (curr_sym and curr_tf) else (curr_sym or "None")

        data = {
            "status": state_label,
            "is_running": is_running,
            "is_paused": is_paused,
            "current_symbol": curr_batch,
            "progress_pct": progress_pct,
            "completed_count": completed_symbols,
            "total_count": total_symbols,
            "speed": speed_display,
            "speed_candles_per_sec": status.get("speed_candles_per_sec", 0.0),
            "quota_used": quota_used,
            "candles_ingested": status.get("total_candles_ingested", 0),
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(1.0)


@router.get("/api/v1/system/downloader/stream")
async def downloader_stream(request: Request):
    return StreamingResponse(event_generator(request), media_type="text/event-stream")


@router.post("/api/v1/system/downloader/control")
async def downloader_control(request: Request):
    correlation_id = getattr(request.state, "correlation_id", "req-downloader-ctrl")
    try:
        body = await request.json()
    except Exception:
        body = {}
    action = str(body.get("action", "pause")).lower()
    downloader = get_downloader_instance()

    if action == "pause":
        downloader.pause()
        status_msg = "Downloader paused"
    elif action == "resume":
        downloader.resume()
        status_msg = "Downloader resumed"
    elif action in ("cancel", "stop"):
        downloader.cancel()
        status_msg = "Downloader stopped"
    else:
        status_msg = f"Action {action} acknowledged"

    return ApiResponse.success_response(
        data={"action": action, "status": status_msg},
        correlation_id=correlation_id,
    )


@router.get("/api/v1/system/ux_translations")
async def get_ux_translations():
    trans_file = CONFIG_DIR / "ux_translations.json"
    if trans_file.exists():
        data = json.loads(trans_file.read_text(encoding="utf-8"))
        return JSONResponse(content=data)
    return JSONResponse(content={})


@router.get("/api/v1/system/db/stats")
async def get_db_stats(request: Request):
    correlation_id = getattr(request.state, "correlation_id", "req-db-stats")
    from db.connection import get_db
    from config.settings import get_settings

    settings = get_settings()
    db = get_db()
    db_file = Path(settings.DUCKDB_PATH)
    file_size_mb = round(db_file.stat().st_size / (1024 * 1024), 2) if db_file.exists() else 0.0

    tables_stats = {}
    cursor = db.get_read_cursor()
    try:
        tables = cursor.execute("SHOW TABLES").fetchall()
        for row in tables:
            t_name = row[0]
            try:
                cnt = cursor.execute(f"SELECT count(*) FROM {t_name}").fetchone()[0]
                tables_stats[t_name] = cnt
            except Exception:
                tables_stats[t_name] = 0
    finally:
        cursor.close()

    return ApiResponse.success_response(
        data={
            "db_path": str(db_file),
            "file_size_mb": file_size_mb,
            "tables": tables_stats,
        },
        correlation_id=correlation_id,
    )

