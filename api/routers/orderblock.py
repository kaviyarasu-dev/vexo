"""OrderBlock REST API Router.
Endpoints:
- GET /api/v1/orderblock/boards
- GET /api/v1/orderblock/zones
- GET /api/v1/orderblock/market-picture
- POST /api/v1/orderblock/snapshot
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging
import pytz
import pandas as pd
from fastapi import APIRouter, Depends, Query, Request

from db.connection import get_db, DuckDBConnectionManager
from api.models.envelope import ApiResponse, success_response, error_response
from services.orderblock.strength_engine import IntradayStrengthEngine, StockStrengthMetric
from services.orderblock.picks_engine import OrderBlockBoardsEngine, BoardsSnapshot
from services.orderblock.zone_engine import OrderBlockZoneEngine, Candle5m, OrderBlockZone
from services.orderblock.liquidity_engine import OrderBlockLiquidityEngine
from services.orderblock.profile_engine import VolumeProfileEngine, VolumeProfile
from services.orderblock.backfill_service import VolumeProfileBackfillService
from services.orderblock.tick_recorder import get_tick_recorder

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

router = APIRouter(prefix="/api/v1/orderblock", tags=["orderblock"])

# In-memory singleton state
_boards_engine = OrderBlockBoardsEngine()


def _get_engine_instances(db: DuckDBConnectionManager):
    """Instantiate OrderBlock calculation engines with db manager."""
    strength_eng = IntradayStrengthEngine(db_manager=db)
    zone_eng = OrderBlockZoneEngine(db_manager=db)
    liq_eng = OrderBlockLiquidityEngine()
    return strength_eng, zone_eng, liq_eng


def _fetch_universe_metrics(db: DuckDBConnectionManager, strength_eng: IntradayStrengthEngine) -> List[StockStrengthMetric]:
    """Fetch quote metrics across active universe and compute strength metrics."""
    cursor = db.get_read_cursor()
    try:
        processed_symbols = set()
        metrics: List[StockStrengthMetric] = []

        # 1. Fetch any intraday 1m candles for symbols that have today's 1m data
        try:
            intraday_rows = cursor.execute("""
                WITH latest_day AS (
                    SELECT MAX(CAST(timestamp AS DATE)) as max_d FROM candles_1m_raw
                )
                SELECT c.symbol, 
                       first(c.open) as day_open, 
                       max(c.high) as day_high, 
                       min(c.low) as day_low, 
                       arg_max(c.close, c.timestamp) as current_price
                FROM candles_1m_raw c, latest_day l
                WHERE CAST(c.timestamp AS DATE) = l.max_d
                GROUP BY c.symbol
            """).fetchall()

            if intraday_rows:
                for row in intraday_rows:
                    sym = row[0]
                    o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
                    m = strength_eng.evaluate_strength(
                        symbol=sym,
                        open_price=o,
                        high_price=h,
                        low_price=l,
                        current_price=c
                    )
                    metrics.append(m)
                    processed_symbols.add(sym)
        except Exception as exc:
            logger.warning(f"Error fetching intraday 1m candles: {exc}")

        # 2. For all other active symbols with daily candles, fetch their latest daily candle
        try:
            daily_rows = cursor.execute("""
                WITH ranked_raw AS (
                    SELECT symbol, open, high, low, close,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
                    FROM candles_1d_raw
                ),
                ranked_adj AS (
                    SELECT symbol, open, high, low, close,
                           ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
                    FROM candles_1d_adjusted
                )
                SELECT COALESCE(r.symbol, a.symbol) as symbol,
                       COALESCE(r.open, a.open) as open,
                       COALESCE(r.high, a.high) as high,
                       COALESCE(r.low, a.low) as low,
                       COALESCE(r.close, a.close) as close
                FROM symbols s
                LEFT JOIN ranked_raw r ON s.symbol = r.symbol AND r.rn = 1
                LEFT JOIN ranked_adj a ON s.symbol = a.symbol AND a.rn = 1
                WHERE s.is_active = TRUE AND (r.symbol IS NOT NULL OR a.symbol IS NOT NULL)
                ORDER BY s.tier ASC, s.symbol ASC
            """).fetchall()

            for row in daily_rows:
                sym = row[0]
                if sym not in processed_symbols:
                    o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
                    m = strength_eng.evaluate_strength(
                        symbol=sym,
                        open_price=o,
                        high_price=h,
                        low_price=l,
                        current_price=c
                    )
                    metrics.append(m)
                    processed_symbols.add(sym)
        except Exception as exc:
            logger.warning(f"Error fetching daily candles: {exc}")

        return metrics
    except Exception as e:
        logger.error(f"Error fetching universe metrics: {e}")
        return []
    finally:
        cursor.close()


@router.get("/boards")
async def get_orderblock_boards(request: Request):
    """Returns Top 20 Bullish and Bearish boards, algorithmic Picks, and Breadth ratio."""
    correlation_id = getattr(request.state, "correlation_id", "req-orderblock")
    db = get_db()
    strength_eng, _, _ = _get_engine_instances(db)

    metrics = _fetch_universe_metrics(db, strength_eng)
    snapshot = _boards_engine.update_boards(metrics, top_n=20)

    # Calculate Market Breadth
    advances = sum(1 for m in metrics if m.day_move_pct > 0)
    declines = sum(1 for m in metrics if m.day_move_pct < 0)
    unchanged = sum(1 for m in metrics if m.day_move_pct == 0)
    total = len(metrics)
    ratio = round((advances / max(1, advances + declines)) * 100.0, 1)

    # Calculate Leading Sectors
    sector_scores: Dict[str, List[float]] = {}
    for m in metrics:
        sec = m.sector or "General"
        sector_scores.setdefault(sec, []).append(m.score if m.side == "BULLISH" else -m.score)
    
    leading_sectors = [
        {"sector": sec, "avg_strength": round(sum(scores) / len(scores), 2)}
        for sec, scores in sector_scores.items()
    ]
    leading_sectors.sort(key=lambda s: s["avg_strength"], reverse=True)

    recorder = get_tick_recorder(db)

    def _augment_contender(item):
        d = item.__dict__.copy()
        mini = recorder.get_mini_profile(item.symbol)
        if mini is None:
            mini = {
                "poc_price": item.current_price,
                "poc_width_pct": 0.0,
                "current_bucket_idx": 20,
                "mini_buckets": [0.0] * 40
            }
        d["profile_summary"] = mini
        return d

    data = {
        "timestamp": snapshot.timestamp.isoformat(),
        "bullish_boards": [_augment_contender(item) for item in snapshot.bullish],
        "bearish_boards": [_augment_contender(item) for item in snapshot.bearish],
        "bullish_picks": [_augment_contender(item) for item in snapshot.bullish_picks],
        "bearish_picks": [_augment_contender(item) for item in snapshot.bearish_picks],
        "market_breadth": {
            "advances": advances,
            "declines": declines,
            "unchanged": unchanged,
            "total": total,
            "ratio": ratio
        },
        "leading_sectors": leading_sectors
    }
    return success_response(data=data, correlation_id=correlation_id)


@router.get("/profile")
async def get_orderblock_profile(request: Request, symbol: str = Query(..., description="Target equity symbol")):
    """Returns 40-bucket intraday volume profile with Point of Control (POC) and relative scaling."""
    correlation_id = getattr(request.state, "correlation_id", "req-orderblock")
    db = get_db()
    recorder = get_tick_recorder(db)
    profile = recorder.get_profile(symbol)

    if profile is None:
        # Fall back to DuckDB raw 1m candles late-start backfill
        now_ts = datetime.now(IST)
        today_str = now_ts.strftime("%Y-%m-%d")
        backfill_svc = VolumeProfileBackfillService()
        profile = backfill_svc.backfill_from_db_candles(symbol, today_str, manager=db)

    if profile is None:
        # Fall back to latest daily candle bounds for instant baseline display
        cursor = db.get_read_cursor()
        try:
            row = cursor.execute("""
                SELECT open, high, low, close
                FROM candles_1d_raw
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 1
            """, (symbol,)).fetchone()
            if row:
                d_open, d_high, d_low, d_close = float(row[0]), float(row[1]), float(row[2]), float(row[3])
                profile_eng = VolumeProfileEngine(num_buckets=40)
                profile = profile_eng.build_profile(
                    symbol=symbol,
                    trade_date=datetime.now(IST).strftime("%Y-%m-%d"),
                    day_low=d_low,
                    day_high=d_high,
                    current_price=d_close,
                    bucket_volumes={},
                )
        finally:
            cursor.close()

    if profile is None:
        return success_response(
            data={
                "symbol": symbol,
                "trade_date": datetime.now(IST).strftime("%Y-%m-%d"),
                "poc_price": 0.0,
                "poc_volume": 0,
                "current_price": 0.0,
                "day_low": 0.0,
                "day_high": 0.0,
                "buckets": [],
            },
            correlation_id=correlation_id,
        )

    return success_response(data=profile.to_dict(), correlation_id=correlation_id)


@router.get("/zones")
async def get_orderblock_zones(request: Request, symbol: str = Query(..., description="Target equity symbol")):
    """Returns 5-minute active and mitigated zones, level ladders (Z, S1-S4, R1-R4, R:R), and liquidity pools."""
    correlation_id = getattr(request.state, "correlation_id", "req-orderblock")
    db = get_db()
    _, zone_eng, liq_eng = _get_engine_instances(db)

    cursor = db.get_read_cursor()
    try:
        # Fetch recent 1m candles for 5m resampling (limit to last 2000 bars ~5 days for instant response)
        rows = cursor.execute("""
            SELECT timestamp, open, high, low, close, volume
            FROM (
                SELECT timestamp, open, high, low, close, volume
                FROM candles_1m_raw
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 2000
            )
            ORDER BY timestamp ASC
        """, (symbol,)).fetchall()

        candles_5m: List[Candle5m] = []
        if rows:
            # Resample 1m rows into 5m blocks
            df_1m = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df_1m["timestamp"] = pd.to_datetime(df_1m["timestamp"])
            df_5m = df_1m.resample("5min", on="timestamp").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum"
            }).dropna().reset_index()

            for _, r in df_5m.iterrows():
                candles_5m.append(Candle5m(
                    timestamp=r["timestamp"].to_pydatetime(),
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=int(r["volume"])
                ))

        zones = zone_eng.detect_zones(symbol, candles_5m) if candles_5m else []

        # Separate active unmitigated vs historical mitigated zones
        active_zones = [z for z in zones if not z.is_mitigated]
        historical_zones = [z for z in zones if z.is_mitigated]
        primary_active = active_zones[-1] if active_zones else (zones[-1] if zones else None)

        ladder_dict = None
        if primary_active and candles_5m:
            day_high = max(c.high for c in candles_5m)
            day_low = min(c.low for c in candles_5m)
            curr_p = candles_5m[-1].close
            ladder = liq_eng.compute_levels(primary_active, day_high, day_low, curr_p)
            ladder_dict = ladder.__dict__
        elif not primary_active:
            # Fall back to latest daily candle to construct a baseline institutional zone
            daily_candle = cursor.execute("""
                SELECT open, high, low, close
                FROM candles_1d_raw
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 1
            """, (symbol,)).fetchone()
            if daily_candle:
                d_open, d_high, d_low, d_close = float(daily_candle[0]), float(daily_candle[1]), float(daily_candle[2]), float(daily_candle[3])
                is_bull = d_close >= d_open
                dummy_zone = OrderBlockZone(
                    symbol=symbol,
                    block_type="BULLISH" if is_bull else "BEARISH",
                    start_time=datetime.now(IST),
                    top_price=round(max(d_open, d_close), 2),
                    bottom_price=round(min(d_open, d_close), 2),
                    invalidation_price=round(d_low if is_bull else d_high, 2),
                    end_time=None,
                    is_mitigated=False,
                    timeframe="5m"
                )
                ladder = liq_eng.compute_levels(dummy_zone, day_high=d_high, day_low=d_low, current_price=d_close)
                ladder_dict = ladder.__dict__
                primary_active = dummy_zone

        pools = liq_eng.detect_liquidity_pools(symbol, candles_5m) if candles_5m else []

        data = {
            "symbol": symbol,
            "active_zone": primary_active.__dict__ if primary_active else None,
            "historical_zones": [z.__dict__ for z in historical_zones],
            "ladder": ladder_dict,
            "liquidity_pools": [p.__dict__ for p in pools]
        }
        return success_response(data=data, correlation_id=correlation_id)
    except Exception as e:
        logger.error(f"Error computing zones for {symbol}: {e}")
        return success_response(data={
            "symbol": symbol,
            "active_zone": None,
            "historical_zones": [],
            "ladder": None,
            "liquidity_pools": []
        }, correlation_id=correlation_id)
    finally:
        cursor.close()


@router.get("/market-picture")
async def get_market_picture(request: Request):
    """Returns 2D scatter coordinates for Market X-Ray and Sector Flow panel."""
    correlation_id = getattr(request.state, "correlation_id", "req-orderblock")
    db = get_db()
    strength_eng, _, _ = _get_engine_instances(db)

    metrics = _fetch_universe_metrics(db, strength_eng)
    snapshot = _boards_engine.update_boards(metrics, top_n=20)

    contender_symbols = {item.symbol for item in snapshot.bullish}.union({item.symbol for item in snapshot.bearish})
    pick_symbols = {p.symbol for p in snapshot.bullish_picks if p.status == "PICKED"}.union(
        {p.symbol for p in snapshot.bearish_picks if p.status == "PICKED"}
    )

    points = []
    for m in metrics:
        points.append({
            "symbol": m.symbol,
            "sector": m.sector,
            "day_move_pct": m.day_move_pct,
            "strength_score": m.score,
            "side": m.side,
            "is_contender": m.symbol in contender_symbols,
            "is_pick": m.symbol in pick_symbols,
            "is_event_risk": m.is_event_risk,
            "current_price": m.current_price
        })

    advances = sum(1 for m in metrics if m.day_move_pct > 0)
    declines = sum(1 for m in metrics if m.day_move_pct < 0)

    # Sector flow
    sector_moves: Dict[str, List[float]] = {}
    for m in metrics:
        sec = m.sector or "General"
        sector_moves.setdefault(sec, []).append(m.day_move_pct)

    avg_sector_moves = [
        {"sector": sec, "move_pct": round(sum(moves) / len(moves), 2)}
        for sec, moves in sector_moves.items()
    ]
    avg_sector_moves.sort(key=lambda x: x["move_pct"], reverse=True)

    leading = avg_sector_moves[0]["sector"] if avg_sector_moves else "N/A"
    lagging = avg_sector_moves[-1]["sector"] if avg_sector_moves else "N/A"

    data = {
        "points": points,
        "breadth": {"advances": advances, "declines": declines, "total": len(metrics)},
        "leading_sector": leading,
        "lagging_sector": lagging,
        "sectors": avg_sector_moves
    }
    return success_response(data=data, correlation_id=correlation_id)


@router.post("/snapshot")
async def save_orderblock_snapshot(request: Request):
    """Persists current boards and picks rankings into DuckDB table orderblock_snapshots."""
    correlation_id = getattr(request.state, "correlation_id", "req-orderblock")
    db = get_db()
    strength_eng, _, _ = _get_engine_instances(db)

    metrics = _fetch_universe_metrics(db, strength_eng)
    snapshot = _boards_engine.update_boards(metrics, top_n=20)

    now_ts = datetime.now(IST)
    today_dt = now_ts.date()

    rows_to_insert = []
    for item in snapshot.bullish:
        is_p = any(p.symbol == item.symbol and p.status == "PICKED" for p in snapshot.bullish_picks)
        rows_to_insert.append((
            today_dt, item.symbol, item.score, item.rank, item.side, is_p, item.sector, now_ts
        ))

    for item in snapshot.bearish:
        is_p = any(p.symbol == item.symbol and p.status == "PICKED" for p in snapshot.bearish_picks)
        rows_to_insert.append((
            today_dt, item.symbol, item.score, item.rank, item.side, is_p, item.sector, now_ts
        ))

    if rows_to_insert:
        df_snap = pd.DataFrame(rows_to_insert, columns=[
            "snapshot_date", "symbol", "strength_score", "rank", "side", "is_pick", "sector", "captured_at"
        ])
        db.execute_write_df("""
            INSERT OR REPLACE INTO orderblock_snapshots 
            SELECT * FROM _temp_input_table
        """, df_snap)

    return success_response(data={"rows_persisted": len(rows_to_insert)}, correlation_id=correlation_id)
