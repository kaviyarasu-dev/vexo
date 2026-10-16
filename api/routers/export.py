from fastapi import APIRouter, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from datetime import datetime
import os

from services.export_service import ExportService
from api.models.envelope import ApiResponse

router = APIRouter()

def cleanup_file(filepath: str):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        pass

@router.get("/api/v1/export")
def export_data(
    request: Request,
    background_tasks: BackgroundTasks,
    symbol: str = Query(...),
    timeframe: str = Query("1m"),
    from_date: datetime = Query(default_factory=lambda: datetime(2000, 1, 1)),
    to_date: datetime = Query(default_factory=lambda: datetime(2100, 1, 1)),
    format: str = Query("parquet"),
    adjusted: bool = Query(True)
):
    correlation_id = getattr(request.state, "correlation_id", "req-export-001")
    service = ExportService()
    
    # Exporter throws HTTPException(400) if Excel row limit exceeded
    filepath = service.export(
        symbol=symbol,
        timeframe=timeframe,
        start=from_date,
        end=to_date,
        format=format,
        adjusted=adjusted
    )
    
    filename = os.path.basename(filepath)
    # Background task to clean up the temporary file
    background_tasks.add_task(cleanup_file, filepath)
    
    media_type = "application/octet-stream"
    if format == "csv":
        media_type = "text/csv"
    elif format == "excel":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
    safe_symbol = symbol.replace(":", "_").replace("/", "_").replace("\\", "_")
    safe_filename = f"{safe_symbol}_{timeframe}.{format if format != 'excel' else 'xlsx'}"
        
    return FileResponse(
        filepath, 
        media_type=media_type, 
        filename=safe_filename
    )
