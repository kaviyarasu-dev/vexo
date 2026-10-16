from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from db.connection import get_db, DuckDBConnectionManager
from services.paper_trading_service import PaperTradingService
from api.models.paper_trading_models import (
    OrderRequest,
    OrderResponse,
    PositionResponse,
    AccountResponse,
    ClosePositionRequest,
    UpdateRiskRequest,
    DeployStrategyRequest,
    AutoStrategyResponse,
    TradeHistoryItem,
)

router = APIRouter(prefix="/api/v1/paper-trading", tags=["Paper Trading"])


def get_paper_service(db: DuckDBConnectionManager = Depends(get_db)) -> PaperTradingService:
    return PaperTradingService(db)


@router.get("/account", response_model=Dict[str, Any])
def get_account_summary(service: PaperTradingService = Depends(get_paper_service)):
    """Returns the paper trading account balance, margin utilization, and total portfolio valuation."""
    try:
        acc = service.get_account_summary()
        return {
            "success": True,
            "data": acc.model_dump(),
            "message": "Account summary retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account/reset", response_model=Dict[str, Any])
def reset_account(
    initial_capital: float = Query(default=1000000.0, description="Virtual capital to reset to"),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Resets virtual account balance to initial capital and clears positions, orders, and trades."""
    try:
        acc = service.reset_account(initial_capital)
        return {
            "success": True,
            "data": acc.model_dump(),
            "message": f"Account reset to ₹{initial_capital:,.2f} successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=Dict[str, Any])
def list_positions(service: PaperTradingService = Depends(get_paper_service)):
    """Returns all open positions with live mark-to-market valuations and unrealized P&L."""
    try:
        positions = service.get_positions_with_mtm()
        return {
            "success": True,
            "data": [p.model_dump() for p in positions],
            "count": len(positions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders", response_model=Dict[str, Any])
def place_order(req: OrderRequest, service: PaperTradingService = Depends(get_paper_service)):
    """Places a simulated virtual order applying Indian statutory taxes and 5 bps slippage."""
    try:
        res = service.place_order(
            symbol=req.symbol,
            side=req.side,
            quantity=req.quantity,
            order_type=req.order_type,
            trade_type=req.trade_type,
            price=req.price,
            stop_loss=req.stop_loss,
            take_profit=req.take_profit,
            trailing_sl_pct=req.trailing_sl_pct
        )
        return {
            "success": True,
            "data": res.model_dump(),
            "message": f"Order {res.order_id} filled at ₹{res.fill_price:,.2f}"
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/positions/{symbol}/close", response_model=Dict[str, Any])
@router.delete("/positions/{symbol}/close", response_model=Dict[str, Any])
def close_position(
    symbol: str,
    exit_price: Optional[float] = Query(default=None, description="Exit price for square off"),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Squares off an active position completely at current market price."""
    try:
        res = service.close_position(symbol=symbol, exit_price=exit_price)
        return {
            "success": True,
            "data": res.model_dump(),
            "message": f"Position for {symbol} squared off successfully at ₹{res.fill_price:,.2f}"
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/positions/{symbol}/risk", response_model=Dict[str, Any])
def update_position_risk(
    symbol: str,
    req: UpdateRiskRequest,
    service: PaperTradingService = Depends(get_paper_service)
):
    """Updates stop loss, take profit, or trailing SL % for an active position."""
    try:
        updated = service.update_position_risk(
            symbol=symbol,
            stop_loss=req.stop_loss,
            take_profit=req.take_profit,
            trailing_sl_pct=req.trailing_sl_pct
        )
        return {
            "success": updated,
            "message": f"Risk levels updated for {symbol}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=Dict[str, Any])
def list_orders(
    limit: int = Query(default=50, ge=1, le=500),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Returns recent order history."""
    try:
        orders = service.get_orders(limit=limit)
        return {
            "success": True,
            "data": orders,
            "count": len(orders)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=Dict[str, Any])
def list_trade_history(
    limit: int = Query(default=50, ge=1, le=500),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Returns execution fills ledger with detailed statutory tax and fee deductions."""
    try:
        trades = service.get_history(limit=limit)
        return {
            "success": True,
            "data": [t.model_dump() for t in trades],
            "count": len(trades)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy-strategy", response_model=Dict[str, Any])
def deploy_strategy(
    req: DeployStrategyRequest,
    service: PaperTradingService = Depends(get_paper_service)
):
    """Deploys a backtested algorithmic strategy for simulated forward testing."""
    try:
        res = service.register_auto_strategy(
            strategy_name=req.strategy_name,
            symbol=req.symbol,
            timeframe=req.timeframe,
            parameters=req.parameters,
            trade_type=req.trade_type,
            allocated_capital=req.allocated_capital
        )
        return {
            "success": True,
            "data": res.model_dump(),
            "message": f"Strategy {req.strategy_name} deployed for {req.symbol}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-strategies", response_model=Dict[str, Any])
def list_auto_strategies(
    status: Optional[str] = Query(default=None),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Returns deployed automated strategies with optional status filter."""
    try:
        strategies = service.list_auto_strategies(status=status)
        return {
            "success": True,
            "data": [s.model_dump() for s in strategies],
            "count": len(strategies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-strategies/{strategy_id}/stop", response_model=Dict[str, Any])
def stop_auto_strategy(
    strategy_id: str,
    service: PaperTradingService = Depends(get_paper_service)
):
    """Stops an active automated strategy, switching status to STOPPED."""
    try:
        service.stop_auto_strategy(strategy_id)
        return {
            "success": True,
            "message": f"Strategy {strategy_id} stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/auto-strategies/{strategy_id}", response_model=Dict[str, Any])
def delete_auto_strategy(
    strategy_id: str,
    stop_only: bool = Query(default=False),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Stops or permanently removes an automated strategy."""
    try:
        if stop_only:
            service.stop_auto_strategy(strategy_id)
            msg = f"Strategy {strategy_id} stopped"
        else:
            service.delete_auto_strategy(strategy_id)
            msg = f"Strategy {strategy_id} removed from forward testing"
        return {
            "success": True,
            "message": msg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-strategies/evaluate", response_model=Dict[str, Any])
def evaluate_auto_strategies(
    symbol: Optional[str] = Query(default=None),
    service: PaperTradingService = Depends(get_paper_service)
):
    """Evaluates active automated strategies against market candles and triggers orders on signal triggers."""
    try:
        cursor = service.db.get_read_cursor()
        try:
            if symbol:
                rows = cursor.execute("""
                    SELECT date, open, high, low, close, volume, symbol
                    FROM candles_1d_adjusted
                    WHERE symbol = ?
                    ORDER BY date ASC
                """, [symbol.strip().upper()]).fetchall()
            else:
                rows = cursor.execute("""
                    SELECT date, open, high, low, close, volume, symbol
                    FROM candles_1d_adjusted
                    ORDER BY date ASC
                """).fetchall()
        finally:
            cursor.close()

        import pandas as pd
        if rows:
            df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "symbol"])
        else:
            df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"])

        executions = service.evaluate_auto_strategies_on_candle(df, symbol=symbol)
        return {
            "success": True,
            "executions": executions,
            "count": len(executions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
