import asyncio
import json
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from api.models.envelope import ApiResponse

router = APIRouter()

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


async def event_generator(request: Request):
    # Mock SSE stream for downloader telemetry
    completed = 0
    total = 500
    while True:
        if await request.is_disconnected():
            break

        completed += 1
        data = {
            "current_symbol": "NSE:TCS-EQ",
            "completed_count": completed,
            "total_count": total,
            "speed_req_per_min": 178,
            "estimated_time_remaining_sec": max(0, 1280 - completed),
            "token_expires_in_sec": 28400,
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.5)


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
    action = body.get("action", "pause")
    return ApiResponse.success_response(
        data={"action": action, "status": f"Downloader {action} acknowledged"},
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

