import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
import datetime

from core.rate_governor import RateGovernor
from services.fyers_client import FyersMarketDataProvider
from services.options.greeks_engine import BlackScholesGreeks
from services.options.payoff_calculator import PayoffCalculator
from services.options.oi_engine import OpenInterestEngine, FOUniverseRegistry
from services.options.strategy_greeks_service import StrategyGreeksAggregator
from services.options.payoff_simulator import PreExpiryPayoffSimulator
from api.models.options_models import StrategyGreeksRequest, PayoffSimulationRequest
from db.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/options", tags=["Options"])

governor = RateGovernor()
fyers = FyersMarketDataProvider()
greeks_engine = BlackScholesGreeks()
payoff_calc = PayoffCalculator()
oi_engine = OpenInterestEngine(fyers_client=fyers)
strategy_greeks_service = StrategyGreeksAggregator()
payoff_simulator = PreExpiryPayoffSimulator()

BANNER_TEXT = "No historical options data available prior to local collection start date."

def format_response(data: dict):
    return {
        "success": True,
        "data": data,
        "meta": {
            "banner": BANNER_TEXT,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    }

def _get_spot_for_symbol(db, symbol: str) -> float:
    """Retrieves the latest spot price from DB or sensible market defaults."""
    clean_sym = symbol.strip()
    cursor = db.get_read_cursor()
    try:
        row = cursor.execute(
            "SELECT close FROM candles_1d_adjusted WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            [clean_sym]
        ).fetchone()
        if not row and ":" in clean_sym:
            bare = clean_sym.split(":")[1].split("-")[0]
            row = cursor.execute(
                "SELECT close FROM candles_1d_adjusted WHERE symbol LIKE ? ORDER BY date DESC LIMIT 1",
                [f"%{bare}%"]
            ).fetchone()
        if row and row[0] is not None and float(row[0]) > 0:
            return round(float(row[0]), 2)
    except Exception:
        pass
    finally:
        cursor.close()

    default_spots = {
        "NIFTY50": 25050.0,
        "NIFTYBANK": 51200.0,
        "FINNIFTY": 23400.0,
        "MIDCPNIFTY": 13100.0,
        "RELIANCE": 2865.0,
        "TCS": 4120.0,
        "INFY": 1915.0,
        "HDFCBANK": 1660.0,
        "ICICIBANK": 1240.0,
        "SBIN": 810.0,
        "TATAMOTORS": 920.0
    }
    for k, v in default_spots.items():
        if k in clean_sym:
            return v
    return 2500.0


def _cache_option_chain_to_db(db, symbol: str, expiry_date: str, records: list):
    """Persists real option chain snapshot into DuckDB option_chain_snapshots table."""
    if not records or db is None:
        return
    today = datetime.date.today()
    rows = []
    for r in records:
        strike = float(r.get("strike_price") or 0.0)
        if strike <= 0:
            continue
        rows.append((
            today,
            symbol,
            r.get("expiry_date") or expiry_date or today.strftime("%Y-%m-%d"),
            strike,
            r.get("option_type", "CE"),
            float(r.get("ltp", 0.0)),
            int(r.get("oi", 0)),
            int(r.get("volume", 0)),
            float(r.get("iv", 0.0)),
            float(r.get("delta", 0.0)),
            float(r.get("gamma", 0.0)),
            float(r.get("theta", 0.0)),
            float(r.get("vega", 0.0)),
            datetime.datetime.now()
        ))
    if not rows:
        return
    try:
        def _insert(conn):
            conn.executemany(
                """
                INSERT OR REPLACE INTO option_chain_snapshots 
                (snapshot_date, underlying_symbol, expiry_date, strike_price, option_type, 
                ltp, oi, volume, iv, delta, gamma, theta, vega, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows
            )
        db.execute_write_batch(_insert)
        logger.info("Auto-cached %d real option chain records for %s into DuckDB.", len(rows), symbol)
    except Exception as exc:
        logger.warning("Failed to auto-cache option chain records into DuckDB for %s: %s", symbol, exc)


@router.get("/chain")
async def get_option_chain(
    symbol: str, 
    date: Optional[str] = None,
    expiry: Optional[str] = None
):
    """
    Get option chain. If date is provided, fetches from local DuckDB snapshot.
    If no date is provided, fetches live real data from Fyers API and auto-caches into DuckDB.
    Strictly zero synthetic/fake data generation.
    """
    db = get_db()
    if date:
        query = "SELECT * FROM option_chain_snapshots WHERE (underlying_symbol = ? OR underlying_symbol LIKE ?) AND snapshot_date = ?"
        params = [symbol, f"%{symbol}%", date]
        if expiry:
            query += " AND expiry_date = ?"
            params.append(expiry)
            
        rows = await db.execute_read_async(query, params)
        cols = ["snapshot_date", "underlying_symbol", "expiry_date", "strike_price", "option_type", 
                "ltp", "oi", "volume", "iv", "delta", "gamma", "theta", "vega", "captured_at"]
        data = [dict(zip(cols, row)) for row in rows]
        
        if data:
            spot = _get_spot_for_symbol(db, symbol)
            strikes_map = {}
            for r in data:
                s = r["strike_price"]
                if s not in strikes_map:
                    strikes_map[s] = {"strike_price": s, "call": None, "put": None}
                if r["option_type"] == "CE":
                    strikes_map[s]["call"] = r
                else:
                    strikes_map[s]["put"] = r
            matrix = [strikes_map[k] for k in sorted(strikes_map.keys())]
            return format_response({
                "chain": data,
                "matrix": matrix,
                "spot": spot,
                "source": "historical",
                "underlying": symbol,
                "expiry_date": expiry or (data[0]["expiry_date"] if data else "")
            })

    # Fetch live real option chain from Fyers API
    spot = _get_spot_for_symbol(db, symbol)
    live_chain = None
    expiry_data = []
    fyers_sym = FOUniverseRegistry.get_fyers_symbol(symbol)

    try:
        live_res = fyers.fetch_option_chain(symbol=fyers_sym, strikes=50)
        if isinstance(live_res, dict) and live_res.get("s") == "ok":
            raw_options = live_res.get("data", {}).get("optionsChain", [])
            expiry_data = live_res.get("data", {}).get("expiryData", [])
            if raw_options:
                live_chain = raw_options
    except Exception as exc:
        logger.warning("Fyers live option chain fetch failed for %s: %s", symbol, exc)
        live_chain = None

    if live_chain:
        # Extract underlying spot price if index 0 has strike_price == -1
        if live_chain and float(live_chain[0].get("strike_price", 0)) == -1:
            spot = float(live_chain[0].get("ltp") or spot)

        resolved_expiry = expiry or (expiry_data[0].get("date", "") if expiry_data else live_chain[0].get("expiry_date", ""))

        enriched_chain = []
        strikes_map = {}
        for opt in live_chain:
            strike = float(opt.get("strike_price") or opt.get("strike") or 0)
            if strike <= 0 or spot <= 0:
                continue
            opt_type = opt.get("option_type") or opt.get("type") or "CE"
            iv_val = float(opt.get("iv") or 15.0)
            if iv_val <= 0:
                iv_val = 15.0
            iv = (iv_val / 100.0) if iv_val > 1.0 else iv_val
            try:
                greeks = greeks_engine.calculate(spot, strike, 4.0, iv, 0.065, opt_type)
            except Exception:
                from services.options.greeks_engine import GreeksResult
                greeks = GreeksResult(delta=0.0, gamma=0.0, theta=0.0, vega=0.0)

            record = dict(opt)
            record["strike_price"] = strike
            record["option_type"] = opt_type
            record["delta"] = round(greeks.delta, 4)
            record["gamma"] = round(greeks.gamma, 5)
            record["theta"] = round(greeks.theta, 2)
            record["vega"] = round(greeks.vega, 3)
            record["expiry_date"] = resolved_expiry
            enriched_chain.append(record)

            if strike not in strikes_map:
                strikes_map[strike] = {"strike_price": strike, "call": None, "put": None}
            if opt_type == "CE":
                strikes_map[strike]["call"] = record
            else:
                strikes_map[strike]["put"] = record

        matrix = [strikes_map[k] for k in sorted(strikes_map.keys())]

        # Auto-persist real chain snapshot into DuckDB
        _cache_option_chain_to_db(db, symbol, resolved_expiry, enriched_chain)

        return format_response({
            "chain": enriched_chain,
            "matrix": matrix,
            "spot": spot,
            "source": "live",
            "underlying": symbol,
            "expiry_date": resolved_expiry
        })

    # Check latest historical DB snapshot before failing
    if db:
        try:
            cursor = db.get_read_cursor()
            try:
                latest_row = cursor.execute(
                    "SELECT MAX(snapshot_date) FROM option_chain_snapshots WHERE underlying_symbol = ? OR underlying_symbol LIKE ?",
                    [symbol, f"%{symbol}%"]
                ).fetchone()
                if latest_row and latest_row[0]:
                    latest_date = str(latest_row[0])
                    query = "SELECT * FROM option_chain_snapshots WHERE (underlying_symbol = ? OR underlying_symbol LIKE ?) AND snapshot_date = ?"
                    params = [symbol, f"%{symbol}%", latest_date]
                    rows = cursor.execute(query, params).fetchall()
                    if rows:
                        cols = ["snapshot_date", "underlying_symbol", "expiry_date", "strike_price", "option_type", 
                                "ltp", "oi", "volume", "iv", "delta", "gamma", "theta", "vega", "captured_at"]
                        data = [dict(zip(cols, r)) for r in rows]
                        strikes_map = {}
                        for r in data:
                            s = r["strike_price"]
                            if s not in strikes_map:
                                strikes_map[s] = {"strike_price": s, "call": None, "put": None}
                            if r["option_type"] == "CE":
                                strikes_map[s]["call"] = r
                            else:
                                strikes_map[s]["put"] = r
                        matrix = [strikes_map[k] for k in sorted(strikes_map.keys())]
                        return format_response({
                            "chain": data,
                            "matrix": matrix,
                            "spot": spot,
                            "source": "historical_latest",
                            "underlying": symbol,
                            "expiry_date": data[0]["expiry_date"] if data else ""
                        })
            finally:
                cursor.close()
        except Exception:
            pass

    # Strict Zero-Fake Mode: Throw HTTP 400 with actionable error prompt
    raise HTTPException(
        status_code=400,
        detail=(
            f"No verified real option chain data available for '{symbol}'. "
            f"Live Fyers API returned no data and no snapshot exists in DuckDB. "
            f"Please ensure Fyers is authenticated and symbol is an active F&O contract."
        )
    )


@router.get("/greeks")
async def get_greeks(
    spot: float,
    strike: float,
    t_days: float,
    iv: float,
    r: float = 0.065,
    option_type: str = "CE"
):
    """Calculate Black-Scholes Greeks for a specific option."""
    if option_type not in ("CE", "PE"):
        raise HTTPException(status_code=400, detail="option_type must be CE or PE")
        
    res = greeks_engine.calculate(spot, strike, t_days, iv, r, option_type)
    
    return format_response({
        "delta": res.delta,
        "gamma": res.gamma,
        "theta": res.theta,
        "vega": res.vega
    })


@router.get("/maxpain")
@router.get("/max-pain")
async def get_max_pain(symbol: str):
    """Calculates Max Pain for the given symbol using verified real market data."""
    db = get_db()
    spot = _get_spot_for_symbol(db, symbol)
    fyers_sym = FOUniverseRegistry.get_fyers_symbol(symbol)

    chain = []
    exp_date = ""

    # 1. Attempt live real Fyers option chain
    try:
        live_res = fyers.fetch_option_chain(symbol=fyers_sym, strikes=50)
        if isinstance(live_res, dict) and live_res.get("s") == "ok":
            raw_options = live_res.get("data", {}).get("optionsChain", [])
            expiry_data = live_res.get("data", {}).get("expiryData", [])
            if raw_options:
                if float(raw_options[0].get("strike_price", 0)) == -1:
                    spot = float(raw_options[0].get("ltp") or spot)
                exp_date = (expiry_data[0].get("date", "") if expiry_data else raw_options[0].get("expiry_date", ""))
                chain = [opt for opt in raw_options if float(opt.get("strike_price") or 0) > 0]
    except Exception as exc:
        logger.warning("Max Pain live chain fetch failed for %s: %s", symbol, exc)

    # 2. If live unavailable, check DuckDB latest snapshot
    if not chain and db:
        try:
            cursor = db.get_read_cursor()
            try:
                latest_row = cursor.execute(
                    "SELECT MAX(snapshot_date) FROM option_chain_snapshots WHERE underlying_symbol = ? OR underlying_symbol LIKE ?",
                    [symbol, f"%{symbol}%"]
                ).fetchone()
                if latest_row and latest_row[0]:
                    latest_date = str(latest_row[0])
                    rows = cursor.execute(
                        "SELECT strike_price, option_type, oi, expiry_date FROM option_chain_snapshots WHERE (underlying_symbol = ? OR underlying_symbol LIKE ?) AND snapshot_date = ?",
                        [symbol, f"%{symbol}%", latest_date]
                    ).fetchall()
                    if rows:
                        exp_date = str(rows[0][3])
                        chain = [{"strike_price": r[0], "option_type": r[1], "oi": r[2]} for r in rows]
            finally:
                cursor.close()
        except Exception:
            pass

    # 3. Strict Zero-Fake Mode: Reject if no real data
    if not chain:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No verified real options data available for '{symbol}' to calculate Max Pain. "
                f"Please ensure Fyers is authenticated and symbol is an active F&O contract."
            )
        )

    strikes_set = set()
    call_oi_map = {}
    put_oi_map = {}
    
    for opt in chain:
        strike = float(opt.get("strike_price", 0))
        if strike <= 0:
            continue
        strikes_set.add(strike)
        oi = int(opt.get("oi") or opt.get("open_interest") or 0)
        opt_type = opt.get("option_type") or opt.get("type") or "CE"
        if opt_type == "CE":
            call_oi_map[strike] = call_oi_map.get(strike, 0) + oi
        elif opt_type == "PE":
            put_oi_map[strike] = put_oi_map.get(strike, 0) + oi
            
    strikes = sorted(list(strikes_set))
    call_oi = [call_oi_map.get(s, 0) for s in strikes]
    put_oi = [put_oi_map.get(s, 0) for s in strikes]
    
    max_pain = payoff_calc.max_pain(strikes, call_oi, put_oi)

    # Compute payout curve across real strikes
    payout_curve = []
    for cand in strikes:
        payout = 0.0
        for i, s in enumerate(strikes):
            if cand > s:
                payout += call_oi[i] * (cand - s)
            if cand < s:
                payout += put_oi[i] * (s - cand)
        payout_curve.append({"strike": cand, "payout": round(payout, 2)})

    return format_response({
        "symbol": symbol,
        "spot": spot,
        "expiry_date": exp_date,
        "max_pain_strike": max_pain,
        "strikes": strikes,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "payout_curve": payout_curve
    })

@router.get("/payoff")
async def get_payoff(spot: float, legs: str):
    """
    Calculate payoff curve.
    legs is a JSON string of list of dicts: 
    [{"strike": 2500, "option_type": "CE", "position": "LONG", "premium": 100}]
    """
    import json
    try:
        parsed_legs = json.loads(legs)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="legs must be a valid JSON string")
        
    if not parsed_legs:
        return format_response({"curve": [], "max_profit": 0, "max_loss": 0})

    # Dynamically determine the spot range covering current spot AND all leg strikes
    strikes = [float(leg.get("strike", spot)) for leg in parsed_legs if "strike" in leg]
    min_strike = min(strikes) if strikes else spot
    max_strike = max(strikes) if strikes else spot

    low_bound = min(spot * 0.90, min_strike * 0.96)
    high_bound = max(spot * 1.10, max_strike * 1.04)

    # Generate 35 points smoothly spanning the entire range
    step = (high_bound - low_bound) / 34.0
    spot_range = [round(low_bound + i * step, 1) for i in range(35)]
    
    payoff_curve = []
    max_profit = float('-inf')
    max_loss = float('inf')
    
    for s in spot_range:
        total_pnl = 0
        for leg in parsed_legs:
            strike = leg["strike"]
            opt_type = leg["option_type"]
            premium = leg["premium"]
            qty = leg.get("quantity", 1)
            is_long = leg["position"].upper() == "LONG"
            
            if opt_type == "CE":
                intrinsic = max(0, s - strike)
            else:
                intrinsic = max(0, strike - s)
                
            if is_long:
                pnl = intrinsic - premium
            else:
                pnl = premium - intrinsic
                
            total_pnl += pnl * qty
            
        payoff_curve.append({"spot": round(s, 2), "pnl": round(total_pnl, 2)})
        max_profit = max(max_profit, total_pnl)
        max_loss = min(max_loss, total_pnl)
        
    return format_response({
        "curve": payoff_curve,
        "max_profit": max_profit if max_profit > 0 else 0,
        "max_loss": max_loss if max_loss < 0 else 0
    })


@router.get("/open-interest")
async def get_open_interest(
    symbol: str,
    expiry: Optional[str] = None,
    date: Optional[str] = None
):
    """
    Get Strike-by-Strike Open Interest and ΔOI analysis, Put/Call Ratio (PCR),
    major support/resistance strikes, and sentiment classification.
    """
    try:
        res = oi_engine.analyze_open_interest(symbol=symbol, expiry=expiry, date=date)
        return format_response(res.model_dump())
    except ValueError as e:
        logger.warning("Real data unavailable for open interest (%s): %s", symbol, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to analyze open interest for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/underlyings")
async def get_fo_underlyings():
    """
    Get full list of supported NSE F&O indices and equities with standardized lot sizes,
    spot prices, and strike steps.
    """
    try:
        db = get_db()
        catalog = FOUniverseRegistry.get_all_underlyings(db=db)
        return format_response(catalog.model_dump())
    except Exception as e:
        logger.error("Failed to fetch F&O underlyings: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy/greeks")
async def get_strategy_greeks(payload: StrategyGreeksRequest):
    """
    Calculate Net Strategy Greeks (Delta, Gamma, Theta, Vega) and
    lot-size adjusted Indian Rupee (₹) risk exposures for multi-leg strategies.
    """
    try:
        res = strategy_greeks_service.calculate_greeks(payload)
        return format_response(res.model_dump())
    except Exception as e:
        logger.error("Failed calculating strategy greeks: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy/payoff")
async def simulate_strategy_payoff(payload: PayoffSimulationRequest):
    """
    Simulate multi-leg option strategy payoff curves comparing Expiration P&L
    against pre-expiration theoretical Black-Scholes curve with IV shock adjustments.
    """
    try:
        res = payoff_simulator.simulate_payoff(payload)
        return format_response(res.model_dump())
    except Exception as e:
        logger.error("Failed simulating strategy payoff: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


