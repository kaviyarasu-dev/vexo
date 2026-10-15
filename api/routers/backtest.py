from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import math
import pandas as pd
from db.connection import get_db
from services.backtest_service import BacktestService, compute_indicators
from core.interfaces import BacktestConfig
from api.models.portfolio_backtest_models import (
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
    PortfolioMetrics,
    DailyEquityPoint,
    AssetContribution,
    PortfolioUniverseItem,
)
from services.portfolio_universe_service import PortfolioUniverseService
from services.backtest.portfolio_engine import PortfolioEngine
from services.backtest.allocation import create_allocator
from api.models.optimization_models import (
    OptimizationRequest,
    OptimizationResponse,
    HeatmapCellDto,
    StabilityDto,
    WalkForwardDto,
    PresetsResponse,
    StrategyOptimizationPreset,
)
from services.backtest.optimization_preset_registry import get_optimization_presets
from services.backtest.optimization_engine import (
    OptimizationEngine,
    ParamSpec,
    generate_param_ticks,
    MAX_GRID_COMBINATIONS,
)

router = APIRouter(prefix="/api/v1/backtest", tags=["Backtest"])

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
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
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


@router.get("/portfolio/universes")
async def get_portfolio_universes_endpoint():
    """Returns available predefined universes with constituent counts."""
    universes = PortfolioUniverseService.get_available_universes()
    return {"success": True, "universes": universes}


@router.post("/portfolio/run", response_model=PortfolioBacktestResponse)
async def run_portfolio_backtest_endpoint(req: PortfolioBacktestRequest, db=Depends(get_db)):
    """Executes a multi-asset quantitative strategy simulation across a stock universe."""
    try:
        # Validate date range
        if req.start_date > req.end_date:
            raise HTTPException(status_code=400, detail="start_date must be less than or equal to end_date")

        # Resolve universe symbols
        if req.universe_type.upper() == "CUSTOM":
            if not req.symbols:
                raise HTTPException(status_code=400, detail="Custom universe requires at least one symbol in 'symbols'")
            symbols = req.symbols
        else:
            symbols = PortfolioUniverseService.get_constituents(req.universe_name or "NIFTY_50")

        if not symbols:
            raise HTTPException(status_code=400, detail="Resolved universe has 0 constituents")

        # Load candle data using DuckDB non-blocking read cursor
        candles_dict = PortfolioUniverseService.load_universe_candles(
            symbols=symbols,
            start_date=req.start_date,
            end_date=req.end_date,
            db=db,
        )

        if not candles_dict:
            raise HTTPException(
                status_code=400,
                detail=f"No verified real historical data available in DuckDB for any symbols in universe '{req.universe_name or 'CUSTOM'}' between {req.start_date} and {req.end_date}. Please sync or download data first."
            )

        # Precompute indicators and signals for each symbol
        prepared_universe: Dict[str, Any] = {}
        for sym, df in candles_dict.items():
            if df is not None and not df.empty:
                prepared_df = compute_indicators(df, req.strategy, req.parameters or {})
                # Ensure atr column exists if needed for InverseATR
                if "atr" not in prepared_df.columns:
                    high = prepared_df["high"]
                    low = prepared_df["low"]
                    close = prepared_df["close"]
                    hl = high - low
                    hc = (high - close.shift(1)).abs()
                    lc = (low - close.shift(1)).abs()
                    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
                    prepared_df["atr"] = tr.rolling(window=14, min_periods=1).mean().fillna(1.0)
                if "roc" not in prepared_df.columns:
                    prepared_df["roc"] = (prepared_df["close"].pct_change(10) * 100.0).fillna(0.0)
                prepared_universe[sym] = prepared_df

        if not prepared_universe:
            raise HTTPException(
                status_code=400,
                detail=f"Zero symbols in universe '{req.universe_name or 'CUSTOM'}' have sufficient real candles (minimum 15 required) between {req.start_date} and {req.end_date}."
            )

        # Load benchmark candles
        benchmark_df = PortfolioUniverseService.load_benchmark_candles(
            start_date=req.start_date,
            end_date=req.end_date,
            db=db,
        )

        # Build position sizing allocator
        allocator = create_allocator(
            req.sizing_model,
            weight_pct=req.sizing_val if req.sizing_model == "EQUAL_WEIGHT" else None,
            risk_pct=req.sizing_val if req.sizing_model == "INVERSE_ATR" else 1.0,
            fixed_amount=req.sizing_val if req.sizing_model == "FIXED_AMOUNT" else 100000.0,
        )

        # Initialize and run PortfolioEngine
        engine = PortfolioEngine(
            universe_data=prepared_universe,
            initial_capital=req.initial_capital,
            max_open_positions=req.max_open_positions,
            allocator=allocator,
            ranking_metric=req.ranking_metric,
            slippage_bps=req.slippage_bps,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            benchmark_data=benchmark_df,
        )

        raw_results = engine.run()
        backtest_id = str(uuid.uuid4())

        def _clean_val(v):
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    return 0.0
                return round(v, 4)
            elif isinstance(v, dict):
                return {k: _clean_val(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [_clean_val(item) for item in v]
            return v

        clean_results = _clean_val(raw_results)
        RESULTS_STORE[backtest_id] = clean_results

        tested_keys = list(prepared_universe.keys())
        skipped = [s for s in symbols if s not in prepared_universe]

        # Construct response
        response = PortfolioBacktestResponse(
            backtest_id=backtest_id,
            status="COMPLETED",
            strategy=req.strategy,
            universe_name=req.universe_name if req.universe_type != "CUSTOM" else "CUSTOM",
            symbols_tested=tested_keys,
            skipped_symbols=skipped,
            metrics=PortfolioMetrics(
                initial_capital=clean_results["initial_capital"],
                final_equity=clean_results["final_equity"],
                net_profit=clean_results["net_profit"],
                return_pct=clean_results["return_pct"],
                cagr=clean_results["cagr"],
                sharpe_ratio=clean_results["sharpe_ratio"],
                sortino_ratio=clean_results["sortino_ratio"],
                max_drawdown=clean_results["max_drawdown"],
                win_rate=clean_results["win_rate"],
                profit_factor=clean_results["profit_factor"],
                total_trades=clean_results["total_trades"],
                winning_trades=clean_results["winning_trades"],
                losing_trades=clean_results["losing_trades"],
                total_statutory_costs=clean_results["total_statutory_costs"],
                avg_exposure_ratio=clean_results["avg_exposure_ratio"],
                benchmark_cagr=clean_results["benchmark_cagr"],
                benchmark_return_pct=clean_results["benchmark_return_pct"],
            ),
            equity_curve=[DailyEquityPoint(**pt) for pt in clean_results["equity_curve"]],
            benchmark_curve=clean_results["benchmark_curve"],
            asset_contributions=[AssetContribution(**c) for c in clean_results["asset_contributions"]],
            monthly_returns=clean_results["monthly_returns"],
            trades=clean_results["trades"],
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimize/presets", response_model=PresetsResponse)
async def get_optimization_presets_endpoint():
    """Retrieve curated strategy parameter ranges for 2D Grid Optimization."""
    presets = get_optimization_presets()
    return PresetsResponse(success=True, presets=presets)


@router.post("/optimize", response_model=OptimizationResponse)
async def run_parameter_optimization_endpoint(req: OptimizationRequest, db=Depends(get_db)):
    """
    Run 2D Parameter Grid Optimization, 3x3 Plateau Stability Index evaluation,
    and Walk-Forward In-Sample vs Out-of-Sample validation.
    """
    try:
        # 1. Pre-validate grid combination count
        p1_ticks = generate_param_ticks(req.param1.min_val, req.param1.max_val, req.param1.step)
        p2_ticks = generate_param_ticks(req.param2.min_val, req.param2.max_val, req.param2.step)
        combinations = len(p1_ticks) * len(p2_ticks)
        if combinations > MAX_GRID_COMBINATIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Optimization grid has {combinations} combinations, which exceeds the institutional cap of {MAX_GRID_COMBINATIONS}. Please increase the parameter step size."
            )

        # 2. Load Candle Data using DuckDB non-blocking read cursor with fallback
        df = BacktestService.load_candles(db, req.symbol, req.start_date, req.end_date)
        if df is None or len(df) < 20:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient candle data available for symbol '{req.symbol}' between {req.start_date} and {req.end_date}."
            )

        # 3. Setup OptimizationEngine
        engine = OptimizationEngine()
        param1_spec = ParamSpec(
            name=req.param1.name,
            min_val=req.param1.min_val,
            max_val=req.param1.max_val,
            step=req.param1.step
        )
        param2_spec = ParamSpec(
            name=req.param2.name,
            min_val=req.param2.min_val,
            max_val=req.param2.max_val,
            step=req.param2.step
        )

        base_config = {
            "initial_capital": req.initial_capital,
            "slippage_bps": req.slippage_bps,
            "trade_type": req.trade_type,
            "stop_loss_pct": req.stop_loss_pct,
            "take_profit_pct": req.take_profit_pct,
        }

        # 4. Run Walk-Forward Optimization
        results = engine.optimize_with_walk_forward(
            df=df,
            strategy_name=req.strategy,
            param1=param1_spec,
            param2=param2_spec,
            walk_forward_split_pct=req.walk_forward_split_pct,
            target_metric=req.target_metric,
            base_params=req.base_params,
            base_config=base_config
        )

        # 5. Sanitize numeric values (NaN, Inf) and construct response DTOs
        def _clean_num(val, default=0.0):
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    return default
                return float(val)
            return val

        matrix_dtos = [
            HeatmapCellDto(
                param1_val=_clean_num(c.param1_val),
                param2_val=_clean_num(c.param2_val),
                sharpe_ratio=_clean_num(c.sharpe_ratio),
                net_pnl=_clean_num(c.net_pnl),
                net_pnl_pct=_clean_num(c.net_pnl_pct),
                max_drawdown_pct=_clean_num(c.max_drawdown_pct),
                win_rate=_clean_num(c.win_rate),
                total_trades=int(c.total_trades),
                profit_factor=_clean_num(c.profit_factor),
            )
            for c in results["matrix"]
        ]

        stability = results["stability"]
        stability_dto = StabilityDto(
            optimal_param1=_clean_num(stability.optimal_param1),
            optimal_param2=_clean_num(stability.optimal_param2),
            optimal_metric_val=_clean_num(stability.optimal_metric_val),
            stability_score=_clean_num(stability.stability_score),
            classification=stability.classification,
            neighbor_avg_val=_clean_num(stability.neighbor_avg_val),
            cliff_drop_pct=_clean_num(stability.cliff_drop_pct),
            neighbors=stability.neighbors,
        )

        wf = results["walk_forward"]
        wf_dto = WalkForwardDto(
            in_sample_net_pnl=_clean_num(wf.in_sample_net_pnl),
            in_sample_sharpe=_clean_num(wf.in_sample_sharpe),
            out_of_sample_net_pnl=_clean_num(wf.out_of_sample_net_pnl),
            out_of_sample_sharpe=_clean_num(wf.out_of_sample_sharpe),
            walk_forward_efficiency=_clean_num(wf.walk_forward_efficiency),
            split_date=wf.split_date,
            is_split_pct=wf.is_split_pct,
        )

        return OptimizationResponse(
            success=True,
            strategy=results["strategy"],
            symbol=req.symbol,
            param1_name=results["param1_name"],
            param2_name=results["param2_name"],
            param1_ticks=results["param1_ticks"],
            param2_ticks=results["param2_ticks"],
            total_combinations=results["total_combinations"],
            execution_time_ms=results["execution_time_ms"],
            best_params=results["best_params"],
            stability=stability_dto,
            walk_forward=wf_dto,
            matrix=matrix_dtos
        )

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


