import datetime
import logging
from typing import Optional

from db.connection import get_db
from core.rate_governor import RateGovernor
from services.fyers_client import FyersMarketDataProvider
from services.options.greeks_engine import BlackScholesGreeks

logger = logging.getLogger(__name__)

class OptionChainCollector:
    """Collects EOD option chain snapshots and persists them to DuckDB."""
    
    def __init__(
        self,
        governor: Optional[RateGovernor] = None,
        fyers: Optional[FyersMarketDataProvider] = None
    ):
        self.governor = governor or RateGovernor()
        self.fyers = fyers or FyersMarketDataProvider()
        self.db = get_db()
        self.greeks = BlackScholesGreeks()

    async def collect_snapshot(self, symbol: str = "NSE:NIFTY50-INDEX"):
        """Collects option chain snapshot and computes Greeks."""
        logger.info(f"Collecting option chain snapshot for {symbol}")
        
        try:
            # We must use RateGovernor Lane 2 (Medium) as per spec
            response = await self.governor.execute(
                priority_lane=2,
                request_func=lambda: self.fyers.client.optionchain({"symbol": symbol, "strikecount": 50})
            )
        except Exception as e:
            logger.error(f"Failed to fetch option chain for {symbol}: {e}")
            return
            
        if not response or "data" not in response:
            logger.error(f"Invalid Fyers option chain response: {response}")
            return
            
        data = response["data"]
        # In Fyers v3 optionchain response, it usually has "optionsChain" array
        chain = data.get("optionsChain", [])
        
        today = datetime.date.today()
        now = datetime.datetime.now()
        
        # Calculate time to expiry and greeks
        # Note: Fyers optionsChain has `strike_price`, `option_type` (CE/PE), `ltp`, `oi`, `volume`, `expiry`
        records = []
        for opt in chain:
            strike = float(opt.get("strike_price", 0))
            opt_type = opt.get("option_type", "CE")
            ltp = float(opt.get("ltp", 0.0))
            oi = int(opt.get("oi", 0))
            volume = int(opt.get("volume", 0))
            
            # Simplified expiry parsing (Fyers gives timestamp or string)
            # Assuming expiry_date is provided or we take a default
            expiry_date = opt.get("expiry_date", "")
            if not expiry_date:
                # Fallback to 7 days from now if missing
                expiry = today + datetime.timedelta(days=7)
            else:
                try:
                    expiry = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
                except ValueError:
                    expiry = today + datetime.timedelta(days=7)
            
            # Simple t_days calculation (calendar days)
            t_days = max(1, (expiry - today).days)
            
            # For greeks, we need underlying spot price. We assume the response provides it or we estimate
            # Fyers usually gives underlying LTP or we might need to fetch it.
            # For simplicity, we get spot from the option response or fallback to ATM strike
            spot = float(data.get("underlying_ltp", strike)) # fallback
            
            iv = float(opt.get("implied_volatility", 0.20)) # Fyers gives IV sometimes, else fallback
            if iv <= 0: iv = 0.20
            
            # config setting for risk free rate
            from config.settings import get_settings
            r = get_settings().RBI_RISK_FREE_RATE
            
            # Calculate Greeks
            greeks_res = self.greeks.calculate(
                spot=spot,
                strike=strike,
                t_days=t_days,
                iv=iv,
                r=r,
                option_type=opt_type
            )
            
            records.append((
                today,
                symbol,
                expiry,
                strike,
                opt_type,
                ltp,
                oi,
                volume,
                iv,
                greeks_res.delta,
                greeks_res.gamma,
                greeks_res.theta,
                greeks_res.vega,
                now
            ))
            
        if not records:
            logger.warning(f"No valid options found in chain for {symbol}")
            return
            
        # Insert into duckdb using execute_write
        try:
            self.db.execute_write(
                """
                INSERT OR REPLACE INTO option_chain_snapshots 
                (snapshot_date, underlying_symbol, expiry_date, strike_price, option_type, 
                ltp, oi, volume, iv, delta, gamma, theta, vega, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
                many=True
            )
            logger.info(f"Persisted {len(records)} option chain records for {symbol}")
        except Exception as e:
            logger.error(f"DB insert failed for option chain snapshot: {e}")
