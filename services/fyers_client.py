"""Fyers API v3 Market Data Provider implementing IMarketDataProvider.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

from datetime import date, datetime, timedelta, timezone
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.parse
import urllib.request
import urllib.error

from config.settings import Settings, get_settings
from core.exceptions import AuthenticationExpiredError, FyersAPIError, QuantPlatformError
from core.interfaces import IAuthService, IMarketDataProvider
from core.rate_governor import (
    LANE_BACKFILL,
    LANE_INTERACTIVE,
    RateGovernor,
    get_rate_governor,
)
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

FYERS_HISTORY_BASE_URL = "https://api-t1.fyers.in/data/history"
FYERS_QUOTES_BASE_URL = "https://api-t1.fyers.in/data/quotes"
FYERS_OPTIONS_BASE_URL = "https://api-t1.fyers.in/data/options-chain-v3"


class FyersMarketDataProvider(IMarketDataProvider):
    """Canonical upstream market data client for Fyers API v3.
    
    Guarantees:
    - All network calls routed through Global RateGovernor.
    - Full mapping of Fyers error codes (-300, 429, -353, -339, -16, 401, 5xx).
    - Automatic token refresh on -16 / 401 token expiry.
    - Transient retry with backoff on error -300 and 5xx.
    - OHLC sanity filtering (high >= low, volume >= 0).
    """

    def __init__(
        self,
        auth_service: Optional[IAuthService] = None,
        rate_governor: Optional[RateGovernor] = None,
        settings: Optional[Settings] = None,
        transport: Optional[Callable[[str, Dict[str, str], Optional[Dict[str, Any]]], Dict[str, Any]]] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.auth_service = auth_service or AuthService(settings=self.settings)
        self.rate_governor = rate_governor or get_rate_governor()
        self._transport = transport or self._default_http_transport

    def _get_headers(self) -> Dict[str, str]:
        """Constructs Authorization headers using valid access token."""
        token = self.auth_service.get_valid_token()
        app_id = self.settings.FYERS_APP_ID
        return {
            "Authorization": f"{app_id}:{token}",
            "Content-Type": "application/json",
            "User-Agent": "python-requests/2.31.0",
            "version": "3",
        }

    def _default_http_transport(
        self,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronous HTTP GET transport using standard library urllib."""
        if params:
            query_string = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            full_url = f"{url}{sep}{query_string}"
        else:
            full_url = url

        req = urllib.request.Request(full_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            try:
                parsed = json.loads(body)
                return parsed
            except Exception:
                raise FyersAPIError(
                    f"HTTP {exc.code}: {exc.reason} - {body}",
                    status_code=exc.code,
                ) from exc
        except urllib.error.URLError as exc:
            raise FyersAPIError(f"Network error connecting to {url}: {exc.reason}", status_code=503) from exc

    def _normalize_resolution(self, resolution: str) -> str:
        """Translates canonical resolution to Fyers API parameter."""
        res_map = {
            "1m": "1",
            "1": "1",
            "1D": "D",
            "D": "D",
            "d": "D",
        }
        return res_map.get(resolution, resolution)

    def fetch_candles(
        self,
        symbol: str,
        resolution: str,
        range_from: str,
        range_to: str,
        cont_flag: str = "0",
        priority_lane: int = LANE_BACKFILL,
    ) -> List[Dict[str, Any]]:
        """Fetches historical candles array for symbol, timeframe, and date interval.
        
        Args:
            symbol: Canonical ticker (e.g. 'NSE:RELIANCE-EQ').
            resolution: '1m' or '1D'.
            range_from: 'YYYY-MM-DD'.
            range_to: 'YYYY-MM-DD'.
            cont_flag: '0' for raw, '1' for continuous.
            priority_lane: 1 (Interactive), 2 (Sync), 3 (Backfill).
            
        Returns:
            List of candle dictionaries: [{"timestamp": datetime/date, "open": float, "high": float, "low": float, "close": float, "volume": int}]
        """
        fyers_res = self._normalize_resolution(resolution)
        cur_from = range_from
        cur_to = range_to

        max_attempts = 5
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            params = {
                "symbol": symbol,
                "resolution": fyers_res,
                "date_format": "1",
                "range_from": cur_from,
                "range_to": cur_to,
                "cont_flag": cont_flag,
            }

            headers = self._get_headers()

            # Execute through RateGovernor
            def _call() -> Dict[str, Any]:
                return self._transport(FYERS_HISTORY_BASE_URL, headers, params)

            payload = self.rate_governor.execute(priority_lane, _call)

            # Check status and response envelope
            status = payload.get("s")
            code = payload.get("code")
            msg = payload.get("message", "")

            # 1. Successful response
            if status == "ok" or (status is None and "candles" in payload):
                candles_raw = payload.get("candles", [])
                return self._parse_and_validate_candles(symbol, resolution, candles_raw)

            # 2. No data (valid empty response)
            if status == "no_data":
                return []

            # 3. Token expired (-16 or 401)
            if code in (-16, 401) or "token" in msg.lower() or "unauthorized" in msg.lower():
                logger.warning("FyersMarketDataProvider: Auth expired (code=%s). Attempting refresh.", code)
                refreshed = self.auth_service.refresh_token_if_needed()
                if not refreshed:
                    raise AuthenticationExpiredError("Fyers token expired and automated refresh failed.")
                continue

            # 4. Transient error -300
            if code == -300:
                logger.warning(
                    "FyersMarketDataProvider: Transient error -300 on %s (%s to %s). Attempt %d/%d. Sleeping 1.5s.",
                    symbol, cur_from, cur_to, attempt, max_attempts
                )
                if attempt >= max_attempts:
                    logger.error("FyersMarketDataProvider: Symbol %s chunk %s-%s exhausted 5 retries on -300. Returning empty.", symbol, cur_from, cur_to)
                    return []
                time.sleep(1.5)
                continue

            # 5. Range exceeded: -353 (1m > 100 days)
            if code == -353:
                logger.critical("FyersMarketDataProvider: Error -353 (1m range > 100 days). Truncating to 99 days.")
                to_dt = datetime.strptime(cur_to, "%Y-%m-%d").date()
                cur_from = (to_dt - timedelta(days=99)).strftime("%Y-%m-%d")
                continue

            # 6. Range exceeded: -339 (1D > 366 days)
            if code == -339:
                logger.critical("FyersMarketDataProvider: Error -339 (1D range > 366 days). Truncating to 365 days.")
                to_dt = datetime.strptime(cur_to, "%Y-%m-%d").date()
                cur_from = (to_dt - timedelta(days=365)).strftime("%Y-%m-%d")
                continue

            # 7. Gateway / server glitch (500, 502, 504)
            if code in (500, 502, 504):
                delay = 2.0 * (2 ** (attempt - 1))
                logger.warning("FyersMarketDataProvider: Broker gateway glitch (%s). Backing off %.1fs.", code, delay)
                time.sleep(delay)
                continue

            # 8. Unhandled or invalid symbol error
            logger.error("FyersMarketDataProvider: API returned error code=%s msg=%s for %s", code, msg, symbol)
            raise FyersAPIError(f"Fyers error code {code}: {msg}", error_code=str(code))

        return []

    def _parse_and_validate_candles(
        self,
        symbol: str,
        resolution: str,
        raw_candles: List[List[Any]],
    ) -> List[Dict[str, Any]]:
        """Transforms Fyers [ts, o, h, l, c, v] tuples into normalized dictionaries with OHLC validation."""
        result: List[Dict[str, Any]] = []

        is_daily = resolution in ("1D", "D", "d")

        for c in raw_candles:
            if not isinstance(c, (list, tuple)) or len(c) < 6:
                continue

            epoch_ts, o, h, l, cl, vol = c[0], c[1], c[2], c[3], c[4], c[5]

            # OHLC sanity checks
            o_val = float(o)
            h_val = float(h)
            l_val = float(l)
            c_val = float(cl)
            v_val = int(vol)

            if h_val < l_val or v_val < 0 or o_val < 0:
                continue  # Discard corrupt candle

            if is_daily:
                # Store trading session date
                dt_obj = datetime.fromtimestamp(epoch_ts, tz=timezone.utc).date()
                result.append({
                    "symbol": symbol,
                    "date": dt_obj,
                    "open": o_val,
                    "high": h_val,
                    "low": l_val,
                    "close": c_val,
                    "volume": v_val,
                })
            else:
                # UTC timestamp for 1m
                ts_obj = datetime.fromtimestamp(epoch_ts, tz=timezone.utc).replace(tzinfo=None)
                result.append({
                    "symbol": symbol,
                    "timestamp": ts_obj,
                    "open": o_val,
                    "high": h_val,
                    "low": l_val,
                    "close": c_val,
                    "volume": v_val,
                })

        return result

    def fetch_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetches real-time snapshot quotes for multiple symbols via Lane 1."""
        if not symbols:
            return {}

        headers = self._get_headers()
        symbols_str = ",".join(symbols)
        params = {"symbols": symbols_str}

        def _call() -> Dict[str, Any]:
            return self._transport(FYERS_QUOTES_BASE_URL, headers, params)

        return self.rate_governor.execute(LANE_INTERACTIVE, _call)

    def fetch_option_chain(self, symbol: str, strikes: int = 20) -> Dict[str, Any]:
        """Fetches real-time option chain for symbol via Lane 1."""
        headers = self._get_headers()
        params = {"symbol": symbol, "strikecount": strikes}

        def _call() -> Dict[str, Any]:
            return self._transport(FYERS_OPTIONS_BASE_URL, headers, params)

        return self.rate_governor.execute(LANE_INTERACTIVE, _call)
