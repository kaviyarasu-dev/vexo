from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
from db.connection import get_db
from services.backtest_service import BacktestService
from core.interfaces import BacktestConfig
import uuid

router = APIRouter(prefix="/api/v1/backtest", tags=["Backtest"])

from typing import Dict, Any, Optional

class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str = "1D"
    start_date: str = "2020-01-01"
    end_date: str = "2023-12-31"
    initial_capital: float = 1000000.0
    trade_type: str = "DELIVERY"
    parameters: Dict[str, Any] = {}
    slippage_bps: float = 5.0
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    position_size_type: str = "PERCENT_CAPITAL"
    position_size_val: float = 100.0

# In-memory store for backtest results (for demo purposes)
# In production, this would be stored in DuckDB or Redis
RESULTS_STORE = {}

@router.post("/run")
async def run_backtest_endpoint(req: BacktestRequest, background_tasks: BackgroundTasks, db=Depends(get_db)):
    backtest_id = str(uuid.uuid4())
    
    try:
        service = BacktestService(db)
        config = BacktestConfig(
            strategy_name=req.strategy,
            symbol=req.symbol,
            timeframe=req.timeframe,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            trade_type=req.trade_type,
            parameters=req.parameters,
            slippage_bps=req.slippage_bps,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            position_size_type=req.position_size_type,
            position_size_val=req.position_size_val
        )
        
        raw_result = service.run_backtest(config)
        if hasattr(raw_result, "__dataclass_fields__"):
            from dataclasses import asdict
            result_dict = asdict(raw_result)
        elif isinstance(raw_result, dict):
            result_dict = raw_result
        else:
            result_dict = dict(raw_result)

        import math
        def _clean(val):
            if isinstance(val, float):
                if math.isnan(val) or math.isinf(val):
                    return 0.0
                return round(val, 4)
            elif isinstance(val, dict):
                return {k: _clean(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [_clean(v) for v in val]
            return val

        clean_result = _clean(result_dict)
        RESULTS_STORE[backtest_id] = clean_result

        return {
            "success": True,
            "backtest_id": backtest_id,
            "status": "COMPLETED",
            "result": clean_result,
            "data": clean_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{backtest_id}")
async def get_backtest_result(backtest_id: str):
    if backtest_id not in RESULTS_STORE:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    return RESULTS_STORE[backtest_id]


class StrategyScanRequest(BaseModel):
    strategy: str
    timeframe: str = "1D"
    start_date: str = "2020-01-01"
    end_date: str = "2023-12-31"
    initial_capital: float = 1000000.0
    parameters: Dict[str, Any] = {}
    slippage_bps: float = 5.0
    stop_loss_pct: Optional[float] = 3.0
    take_profit_pct: Optional[float] = 8.0
    position_size_type: str = "PERCENT_CAPITAL"
    position_size_val: float = 100.0
    symbols: Optional[list[str]] = None
    max_symbols: int = 100


@router.post("/scan-universe")
async def scan_universe_endpoint(req: StrategyScanRequest, db=Depends(get_db)):
    try:
        service = BacktestService(db)
        result = service.scan_universe(
            strategy_name=req.strategy,
            parameters=req.parameters,
            timeframe=req.timeframe,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            slippage_bps=req.slippage_bps,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            position_size_type=req.position_size_type,
            position_size_val=req.position_size_val,
            symbols=req.symbols,
            max_symbols=req.max_symbols
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

