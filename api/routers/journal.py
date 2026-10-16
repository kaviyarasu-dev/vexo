import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Dict, Any, Optional
from core.interfaces import JournalEntry
from db.connection import get_db, DuckDBConnectionManager
from services.journal_service import JournalService
from services.journal.calendar_service import JournalCalendarService
from services.journal.diagnostics_service import JournalDiagnosticsService
from api.models.journal_models import CalendarResponse, DiagnosticsResponse

router = APIRouter(prefix="/api/v1/journal", tags=["Journal"])

def get_journal_service(db: DuckDBConnectionManager = Depends(get_db)) -> JournalService:
    return JournalService(db)

def get_calendar_service(db: DuckDBConnectionManager = Depends(get_db)) -> JournalCalendarService:
    return JournalCalendarService(db)

def get_diagnostics_service(db: DuckDBConnectionManager = Depends(get_db)) -> JournalDiagnosticsService:
    return JournalDiagnosticsService(db)

class CreateTradeRequest(BaseModel):
    symbol: str
    direction: str = "LONG"
    trade_type: str = "MANUAL"
    entry_price: float
    exit_price: Optional[float] = None
    quantity: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    mistake_tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

@router.get("/trades", response_model=List[Dict[str, Any]])
async def list_trades(
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    service: JournalService = Depends(get_journal_service)
):
    trades = service.list_trades(start_date=start_date, end_date=end_date)
    return [t.__dict__ for t in trades]

@router.post("/trade", response_model=Dict[str, Any])
async def create_trade(
    req: CreateTradeRequest,
    service: JournalService = Depends(get_journal_service)
):
    direction = req.direction.upper()
    if direction not in ("LONG", "SHORT"):
        raise HTTPException(status_code=400, detail="Direction must be LONG or SHORT")
    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    if req.entry_price <= 0:
        raise HTTPException(status_code=400, detail="Entry price must be greater than 0")

    entry_p = float(req.entry_price)
    exit_p = float(req.exit_price) if req.exit_price is not None else entry_p
    qty = int(req.quantity)

    # Calculate Gross and Net PnL
    gross = (exit_p - entry_p) * qty if direction == "LONG" else (entry_p - exit_p) * qty
    charges = round(min(150.0, max(20.0, (entry_p * qty) * 0.001)), 2)
    net = round(gross - charges, 2)

    # Stop Loss default if not provided
    sl = req.stop_loss
    if sl is None or sl <= 0:
        sl = round(entry_p * 0.98 if direction == "LONG" else entry_p * 1.02, 2)

    # Calculate R-Multiple
    try:
        r_mult = service.calculate_r_multiple(entry_p, exit_p, sl, direction)
    except Exception:
        risk = abs(entry_p - sl)
        gain = (exit_p - entry_p) if direction == "LONG" else (entry_p - exit_p)
        r_mult = round(gain / risk, 2) if risk > 0 else 0.0

    now = datetime.now()
    entry = JournalEntry(
        trade_id=str(uuid.uuid4()),
        symbol=req.symbol.strip().upper(),
        trade_type=req.trade_type,
        direction=direction,
        entry_time=now,
        entry_price=entry_p,
        exit_time=now if req.exit_price is not None else None,
        exit_price=exit_p if req.exit_price is not None else None,
        quantity=qty,
        stop_loss=sl,
        take_profit=req.take_profit,
        pnl_gross=gross,
        total_charges=charges,
        pnl_net=net,
        r_multiple=r_mult,
        mistake_tags=req.mistake_tags,
        notes=req.notes or ""
    )

    trade_id = service.record_trade(entry)
    return {
        "status": "success",
        "trade_id": trade_id,
        "pnl_net": net,
        "r_multiple": r_mult
    }

@router.delete("/trades/{trade_id}", response_model=Dict[str, Any])
async def delete_trade(
    trade_id: str,
    service: JournalService = Depends(get_journal_service)
):
    service.delete_trade(trade_id)
    return {"status": "deleted", "trade_id": trade_id}

@router.post("/sample-data", response_model=Dict[str, Any])
async def seed_sample_data(
    service: JournalService = Depends(get_journal_service)
):
    count = service.seed_sample_trades()
    return {"status": "success", "seeded_count": count}

@router.delete("/clear", response_model=Dict[str, Any])
async def clear_all_trades(
    service: JournalService = Depends(get_journal_service)
):
    service.clear_all_trades()
    return {"status": "success", "message": "All trades cleared"}

@router.get("/sample-csv")
def download_sample_csv():
    """Serves the institutional multi-broker sample tradebook CSV file for direct download."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    csv_path = Path("static/data/sample_tradebook.csv")
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Sample CSV not found")
    return FileResponse(
        path=str(csv_path),
        filename="sample_tradebook.csv",
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sample_tradebook.csv"'}
    )

@router.post("/import", response_model=Dict[str, Any])
async def import_trades(
    file: UploadFile = File(...),
    broker: str = "AUTO",
    service: JournalService = Depends(get_journal_service)
):
    content = await file.read()
    text = content.decode('utf-8')
    try:
        from services.journal.importer_engine import TradeImporterEngine
        engine = TradeImporterEngine(service.db)
        hint = broker if broker not in ("AUTO", "") else None
        res = engine.import_tradebook_csv(text, broker_hint=hint)
        return {
            "status": "success",
            "imported_trades": res["imported_trades"],
            "broker_detected": res["broker_detected"],
            "fills_parsed": res["fills_parsed"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=Dict[str, Any])
async def get_performance_summary(
    service: JournalService = Depends(get_journal_service)
):
    return service.get_performance_summary()

@router.get("/calendar", response_model=CalendarResponse)
async def get_monthly_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    service: JournalCalendarService = Depends(get_calendar_service)
):
    return service.get_monthly_calendar(year=year, month=month)

@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def get_quantitative_diagnostics(
    service: JournalDiagnosticsService = Depends(get_diagnostics_service)
):
    return service.get_quantitative_diagnostics()


