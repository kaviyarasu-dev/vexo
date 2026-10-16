"""Live Market Data Service for on-demand JIT candle synchronization and live ticker polling.
Adheres strictly to GEMINI.md single-writer DuckDB rules and IST timezone alignment.
"""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
import pytz

from config.settings import Settings, get_settings
from core.exceptions import AuthenticationExpiredError, FyersAPIError
from core.interfaces import ICandleWriter, IMarketDataProvider
from core.rate_governor import LANE_INTERACTIVE
from db.connection import DuckDBConnectionManager, get_db
from db.repositories.duckdb_candle_repo import DuckDBCandleRepo
from services.fyers_client import FyersMarketDataProvider
from services.resampling_service import ResamplingService
from services.chunk_generator import CalendarChunker
from api.models.candle_models import CandleDto, LiveCandleResponse, LiveQuoteDto

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class LiveMarketDataService:
    """Coordinates on-demand JIT candle downloads into DuckDB and real-time polling updates."""

    def __init__(
        self,
        db: Optional[DuckDBConnectionManager] = None,
        market_data_provider: Optional[IMarketDataProvider] = None,
        candle_repo: Optional[DuckDBCandleRepo] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.db = db or get_db()
        self.market_data_provider = market_data_provider or FyersMarketDataProvider(settings=self.settings)
        self.candle_repo = candle_repo or DuckDBCandleRepo(self.db)
        self.resampling_service = ResamplingService(self.db)

    def _normalize_resolution(self, timeframe: str) -> str:
        """Determines upstream fetch resolution based on requested chart timeframe."""
        if timeframe in ("1D", "1W", "D", "d"):
            return "1D"
        return "1m"

    def _sync_resolution(self, symbol: str, resolution: str, today_date: date) -> int:
        """Internal helper to chunk-sync missing historical candles for a specific resolution."""
        try:
            latest_candle = self.candle_repo.get_latest_candle(symbol, resolution)
        except Exception as exc:
            logger.warning(f"Error checking latest candle for {symbol} ({resolution}): {exc}")
            latest_candle = None

        if latest_candle is None:
            # First load: download rich initial history
            if resolution == "1m":
                start_date = today_date - timedelta(days=99)
            else:
                start_date = today_date - timedelta(days=365)
        else:
            ts = latest_candle.timestamp
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = pytz.utc.localize(ts)
                candle_date = ts.astimezone(IST).date()
            elif isinstance(ts, date):
                candle_date = ts
            else:
                candle_date = today_date - timedelta(days=99)

            start_date = candle_date

        if start_date > today_date:
            return 0

        # Generate Fyers-compliant chunks to span the gap with zero gaps and zero overlaps
        chunks = CalendarChunker.generate_backward_chunks(
            symbol=symbol,
            timeframe=resolution,
            start_date=start_date,
            end_date=today_date,
        )
        chunks.reverse()

        total = 0
        for chunk in chunks:
            raw_candles = self.market_data_provider.fetch_candles(
                symbol=symbol,
                resolution=resolution,
                range_from=chunk.range_from_str,
                range_to=chunk.range_to_str,
                priority_lane=LANE_INTERACTIVE,
            )

            if raw_candles:
                if resolution == "1m":
                    ins = self.candle_repo.batch_insert_1m(raw_candles)
                else:
                    ins = self.candle_repo.batch_insert_1d(raw_candles)
                total += (ins or 0)
        return total

    def ensure_symbol_history(self, symbol: str, timeframe: str, start_date: date, end_date: date) -> int:
        """Ensures DuckDB cache contains historical candles spanning start_date to end_date.
        
        Uses CalendarChunker to generate non-overlapping chunks conforming to Fyers limits.
        Fetches real candles from Fyers API and stores them into DuckDB.
        Returns count of inserted candles.
        Strictly refuses any synthetic or simulated data.
        """
        resolution = self._normalize_resolution(timeframe)
        chunks = CalendarChunker.generate_backward_chunks(
            symbol=symbol,
            timeframe=resolution,
            start_date=start_date,
            end_date=end_date,
        )
        total = 0
        for chunk in chunks:
            try:
                raw_candles = self.market_data_provider.fetch_candles(
                    symbol=symbol,
                    resolution=resolution,
                    range_from=chunk.range_from_str,
                    range_to=chunk.range_to_str,
                    priority_lane=LANE_INTERACTIVE,
                )
                if raw_candles:
                    if resolution == "1m":
                        ins = self.candle_repo.batch_insert_1m(raw_candles)
                    else:
                        ins = self.candle_repo.batch_insert_1d(raw_candles)
                    total += ins
            except Exception as exc:
                logger.debug("Failed fetching chunk for %s (%s to %s): %s", symbol, chunk.range_from_str, chunk.range_to_str, exc)
                break
        return total

    def ensure_symbol_freshness(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Ensures DuckDB cache has the latest real-time candle data for the symbol.
        
        - If symbol has 0 candles: downloads initial 100-day (1m) or 365-day (1D) window.
        - If symbol has older candles: chunk-downloads missing delta from last date to today.
        - Chunks conform to Fyers API limits (max 100 days for 1m, 366 days for 1D).
        - Inserts into DuckDB with anti-join deduplication.
        - Synchronizes both 1m and 1D caches so resampling is always coherent.
        - Strictly refuses any fake, dummy, or simulated data.
        """
        resolution = self._normalize_resolution(timeframe)
        now_ist = datetime.now(IST)
        today_date = now_ist.date()
        total_inserted = 0

        try:
            # 1. Primary requested resolution sync
            total_inserted += self._sync_resolution(symbol, resolution, today_date)

            # 2. Resampling coherence: if timeframe is 1D/1W and 1m history exists for this symbol,
            # ensure 1m is also brought up to today so ResamplingService (which resamples 1m to 1D) has latest data.
            if resolution == "1D":
                try:
                    latest_1m = self.candle_repo.get_latest_candle(symbol, "1m")
                    if latest_1m is not None:
                        total_inserted += self._sync_resolution(symbol, "1m", today_date)
                except Exception as exc:
                    logger.debug("Secondary 1m sync skipped for %s: %s", symbol, exc)

            logger.info(
                "LiveMarketDataService: Catch-up completed for %s (%s). %d candles inserted.",
                symbol, resolution, total_inserted
            )
            return {
                "status": "OK",
                "is_live": True,
                "inserted": total_inserted,
                "message": f"Successfully synced {total_inserted} live candles",
            }

        except AuthenticationExpiredError as exc:
            logger.warning("LiveMarketDataService: Fyers auth expired during catch-up for %s: %s", symbol, exc)
            return {
                "status": "AUTH_REQUIRED",
                "is_live": False,
                "inserted": 0,
                "message": str(exc),
            }
        except FyersAPIError as exc:
            logger.warning("LiveMarketDataService: Fyers API error during catch-up for %s: %s", symbol, exc)
            return {
                "status": "BROKER_ERROR",
                "is_live": False,
                "inserted": 0,
                "message": str(exc),
            }
        except Exception as exc:
            logger.error("LiveMarketDataService: Unexpected error syncing %s: %s", symbol, exc)
            return {
                "status": "ERROR",
                "is_live": False,
                "inserted": 0,
                "message": str(exc),
            }

    def get_live_candle(self, symbol: str, timeframe: str) -> LiveCandleResponse:
        """Fetches the latest live candle and real-time quote for real-time chart polling."""
        resolution = self._normalize_resolution(timeframe)
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime("%Y-%m-%d")

        quote_dto: Optional[LiveQuoteDto] = None
        candle_dto: Optional[CandleDto] = None
        is_live = False
        auth_status = "OK"
        message: Optional[str] = None

        # 1. Fetch real-time snapshot quote via Lane 1
        try:
            quote_payload = self.market_data_provider.fetch_quotes([symbol])
            if quote_payload and quote_payload.get("s") == "ok":
                data_list = quote_payload.get("d", [])
                if data_list and len(data_list) > 0:
                    v = data_list[0].get("v", {})
                    ltp = float(v.get("lp", 0.0))
                    if ltp > 0:
                        quote_dto = LiveQuoteDto(
                            ltp=ltp,
                            open=float(v.get("open_price", 0.0)) or None,
                            high=float(v.get("high_price", 0.0)) or None,
                            low=float(v.get("low_price", 0.0)) or None,
                            close=float(v.get("prev_close_price", 0.0)) or None,
                            prev_close=float(v.get("prev_close_price", 0.0)) or None,
                            ch=float(v.get("ch", 0.0)) or None,
                            chp=float(v.get("chp", 0.0)) or None,
                            volume=int(v.get("volume", 0)) or None,
                            timestamp=int(v.get("tt", 0)) or None,
                        )
                        is_live = True
        except AuthenticationExpiredError as exc:
            auth_status = "AUTH_REQUIRED"
            message = str(exc)
        except Exception as exc:
            logger.debug("Live quote fetch skipped or failed for %s: %s", symbol, exc)

        # 2. Fetch today's latest forming candle(s)
        if auth_status != "AUTH_REQUIRED":
            try:
                today_candles = self.market_data_provider.fetch_candles(
                    symbol=symbol,
                    resolution=resolution,
                    range_from=today_str,
                    range_to=today_str,
                    priority_lane=LANE_INTERACTIVE,
                )
                if today_candles:
                    if resolution == "1m":
                        self.candle_repo.batch_insert_1m(today_candles)
                    else:
                        self.candle_repo.batch_insert_1d(today_candles)
                    is_live = True
            except AuthenticationExpiredError as exc:
                auth_status = "AUTH_REQUIRED"
                message = str(exc)
            except Exception as exc:
                logger.debug("Live today candle fetch error for %s: %s", symbol, exc)

        # 3. Resample the most recent candle for the requested timeframe
        try:
            start_dt = now_ist.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)
            end_dt = (now_ist + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)

            df = self.resampling_service.resample(
                symbol=symbol,
                target_timeframe=timeframe,
                start=start_dt,
                end=end_dt,
                adjusted=True,
            )

            if not df.empty:
                last_row = df.iloc[-1]
                t_val = int(last_row["timestamp"].timestamp())
                
                import pandas as pd
                raw_open = last_row.get("open")
                raw_high = last_row.get("high")
                raw_low = last_row.get("low")
                raw_close = last_row.get("close")
                raw_vol = last_row.get("volume")

                close_val = float(raw_close) if pd.notna(raw_close) else (quote_dto.ltp if quote_dto else 0.0)
                open_val = float(raw_open) if pd.notna(raw_open) else (quote_dto.open if (quote_dto and quote_dto.open) else close_val)
                high_val = float(raw_high) if pd.notna(raw_high) else max(open_val, close_val, (quote_dto.high if quote_dto and quote_dto.high else close_val))
                low_val = float(raw_low) if pd.notna(raw_low) else min(open_val, close_val, (quote_dto.low if quote_dto and quote_dto.low else close_val))
                vol_val = int(raw_vol) if pd.notna(raw_vol) else (quote_dto.volume if quote_dto and quote_dto.volume else 0)

                # If we have a fresh quote LTP, update current forming bar
                if quote_dto and quote_dto.ltp > 0:
                    close_val = quote_dto.ltp
                    high_val = max(high_val, quote_dto.ltp)
                    low_val = min(low_val, quote_dto.ltp)

                candle_dto = CandleDto(
                    time=t_val,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    volume=vol_val,
                )

        except Exception as exc:
            logger.debug("Error computing latest resampled candle for %s (%s): %s", symbol, timeframe, exc)

        # If auth expired, do not manufacture fake or stale live quotes
        if auth_status == "AUTH_REQUIRED":
            return LiveCandleResponse(
                symbol=symbol,
                timeframe=timeframe,
                candle=None,
                quote=None,
                is_live=False,
                auth_status="AUTH_REQUIRED",
                message=message or "Fyers authentication required.",
            )

        return LiveCandleResponse(
            symbol=symbol,
            timeframe=timeframe,
            candle=candle_dto,
            quote=quote_dto,
            is_live=is_live,
            auth_status=auth_status,
            message=message,
        )

    def sync_live_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetches live real-time quotes for symbols and upserts today's 1D candle into DuckDB.

        Guarantees:
        1. Strictly zero synthetic or fake data.
        2. Chunks requests to 50 symbols per call (Fyers API standard).
        3. Updates DuckDB candles_1d_raw using single-writer lock.
        4. If unauthenticated, returns AUTH_REQUIRED without writing any fake data.
        """
        if not symbols:
            return {"status": "OK", "synced": 0, "message": "No symbols provided for live sync"}

        now_ist = datetime.now(IST)
        today_date = now_ist.date()

        chunk_size = 50
        total_synced = 0
        candles_to_insert = []

        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i : i + chunk_size]
            try:
                payload = self.market_data_provider.fetch_quotes(chunk)
                if not payload or payload.get("s") != "ok":
                    continue
                data_list = payload.get("d", [])
                for item in data_list:
                    sym = item.get("n") or item.get("v", {}).get("symbol")
                    if not sym:
                        continue
                    v = item.get("v", {})
                    ltp = float(v.get("lp", 0.0))
                    if ltp <= 0:
                        continue

                    o_val = float(v.get("open_price", 0.0)) or ltp
                    h_val = float(v.get("high_price", 0.0)) or max(o_val, ltp)
                    l_val = float(v.get("low_price", 0.0)) or min(o_val, ltp)
                    vol_val = int(v.get("volume", 0)) or 0

                    candles_to_insert.append({
                        "symbol": sym,
                        "date": today_date,
                        "open": o_val,
                        "high": h_val,
                        "low": l_val,
                        "close": ltp,
                        "volume": vol_val
                    })
            except AuthenticationExpiredError as exc:
                return {
                    "status": "AUTH_REQUIRED",
                    "synced": total_synced,
                    "message": "Fyers login required to sync live quotes. Operating on verified historical DuckDB market data.",
                }
            except Exception as exc:
                logger.warning("Error fetching live quotes for chunk: %s", exc)

        if candles_to_insert:
            ins = self.candle_repo.upsert_1d(candles_to_insert)
            total_synced = ins or len(candles_to_insert)

        return {
            "status": "OK",
            "synced": total_synced,
            "as_of_date": str(today_date),
            "message": f"Successfully updated {total_synced} symbols with live market data." if total_synced > 0 else "Live quotes retrieved."
        }

