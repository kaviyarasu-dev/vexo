import json
import logging
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel
from core.interfaces import IScreenerService, ScreenerFilter, ScreenerResult

logger = logging.getLogger(__name__)

class ScreenerService(IScreenerService):
    def __init__(self, db_conn_manager):
        self.db = db_conn_manager
        self.templates = self._load_templates()

    def _load_templates(self):
        try:
            with open("data/screener_templates.json", "r", encoding="utf-8") as f:
                return json.load(f).get("templates", [])
        except Exception as e:
            logger.warning(f"Could not load screener templates: {e}")
            return []

    def _save_templates(self):
        try:
            with open("data/screener_templates.json", "w", encoding="utf-8") as f:
                json.dump({"templates": self.templates}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save screener templates: {e}")

    def get_template(self, template_id: str) -> Optional[dict]:
        for t in self.templates:
            if t["id"].upper() == template_id.upper():
                return t
        return None

    def list_presets(self) -> list[dict[str, Any]]:
        return self.templates

    def create_custom_template(self, name: str, description: str, universe: str, conditions: list[dict[str, Any]]) -> dict:
        import time
        import re
        
        ALLOWED_FIELDS = {
            "volume_zscore_20", "dist_from_52w_high_pct", "dist_from_52w_low_pct",
            "dist_from_sma_20_pct", "change_pct_1d", "rsi_14", "tier",
            "close", "turnover", "turnover_today", "turnover_cr"
        }
        ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=", "!="}
        
        valid_conditions = []
        for c in conditions:
            f = str(c.get("field", "")).strip().lower()
            op = str(c.get("operator", "")).strip()
            try:
                v = float(c.get("value", 0))
            except (ValueError, TypeError):
                continue
            if f in ALLOWED_FIELDS and op in ALLOWED_OPERATORS:
                valid_conditions.append({"field": f, "operator": op, "value": v})

        clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower().strip())[:30]
        template_id = f"custom_{clean_slug}_{int(time.time())}"
        
        new_template = {
            "id": template_id,
            "name": name.strip(),
            "persona": "both",
            "is_custom": True,
            "universe": universe or "ALL",
            "description": description or f"Custom scan with {len(valid_conditions)} rules",
            "conditions": valid_conditions
        }
        self.templates.append(new_template)
        self._save_templates()
        return new_template

    def delete_custom_template(self, template_id: str) -> bool:
        target = None
        for t in self.templates:
            if t.get("id") == template_id:
                target = t
                break
        if not target or not target.get("is_custom"):
            return False
        self.templates = [t for t in self.templates if t.get("id") != template_id]
        self._save_templates()
        return True

    def save_preset(self, name: str, filter_params: ScreenerFilter) -> str:
        rules = filter_params.technical_rules or []
        created = self.create_custom_template(
            name=name,
            description="Saved preset",
            universe=filter_params.universe,
            conditions=rules
        )
        return created["id"]

    def get_latest_market_date(self) -> Optional[str]:
        """Returns the latest authentic market trading date available in candles_1d_adjusted."""
        try:
            with self.db.get_read_cursor() as conn:
                res = conn.execute("SELECT MAX(date) FROM candles_1d_adjusted").fetchone()
                if res and res[0]:
                    return res[0].strftime("%Y-%m-%d") if hasattr(res[0], "strftime") else str(res[0])
        except Exception as e:
            logger.warning(f"Could not determine latest market date: {e}")
        return None

    def sync_live_universe(self, universe: str = "ALL") -> dict:
        """Fetches authentic live quotes from Fyers API for the given universe and updates DuckDB."""
        from services.live_market_data_service import LiveMarketDataService
        
        univ = (universe or "ALL").upper().replace("_", "")
        with self.db.get_read_cursor() as conn:
            if univ == "NIFTY50":
                rows = conn.execute("SELECT symbol FROM symbols WHERE category = 'NIFTY50' ORDER BY symbol").fetchall()
            elif univ == "NIFTYNEXT50":
                rows = conn.execute("SELECT symbol FROM symbols WHERE category = 'NIFTYNEXT50' ORDER BY symbol").fetchall()
            elif univ == "NIFTY500":
                rows = conn.execute("SELECT symbol FROM symbols WHERE COALESCE(tier, 1) <= 3 ORDER BY symbol").fetchall()
            else:
                rows = conn.execute("SELECT symbol FROM symbols ORDER BY symbol").fetchall()
                
            symbols = [r[0] for r in rows if r and r[0]]
            if not symbols:
                c_rows = conn.execute("SELECT DISTINCT symbol FROM candles_1d_raw ORDER BY symbol").fetchall()
                symbols = [r[0] for r in c_rows if r and r[0]]

        live_service = LiveMarketDataService(db=self.db)
        return live_service.sync_live_quotes(symbols)

    def run_screener(self, filter_params: Optional[ScreenerFilter] = None, template: str = None, universe: str = None, as_of_date: str = None) -> list[ScreenerResult]:
        if template:
            tmpl = self.get_template(template)
            rules = tmpl["conditions"] if tmpl else []
            tmpl_univ = tmpl.get("universe") if tmpl else None
            caller_univ = universe or (filter_params.universe if filter_params and filter_params.universe else None)
            effective_univ = caller_univ or tmpl_univ or "ALL"
            if not filter_params:
                filter_params = ScreenerFilter(
                    universe=effective_univ,
                    as_of_date=as_of_date,
                    technical_rules=rules
                )
            else:
                filter_params.technical_rules = rules
                if as_of_date: filter_params.as_of_date = as_of_date
                filter_params.universe = effective_univ
                
        if not filter_params:
            filter_params = ScreenerFilter(universe=universe or "ALL", as_of_date=as_of_date, technical_rules=[])
            
        target_date = filter_params.as_of_date
        
        with self.db.get_read_cursor() as conn:
            if not target_date:
                target_date = self.get_latest_market_date()
                if not target_date:
                    raise ValueError(
                        "No verified real market candles found in database. "
                        "NSE Stock Screener operates strictly on actual market data."
                    )

            # Parse Universe
            univ = (filter_params.universe or "ALL").upper().replace("_", "")
            if univ == "NIFTY50":
                cat_filter = "s.category = 'NIFTY50'"
            elif univ == "NIFTYNEXT50":
                cat_filter = "s.category = 'NIFTYNEXT50'"
            elif univ == "NIFTY500":
                cat_filter = "COALESCE(s.tier, 1) <= 3"
            else:
                cat_filter = "1=1"
                
            query = f"""
            WITH base_candles AS (
                SELECT 
                    symbol,
                    date,
                    close,
                    volume,
                    close * volume AS turnover,
                    high,
                    low,
                    LAG(close) OVER (PARTITION BY symbol ORDER BY date) as prev_close
                FROM candles_1d_adjusted
                WHERE date <= '{target_date}'
            ),
            gains_losses AS (
                SELECT
                    *,
                    CASE WHEN close > prev_close THEN close - prev_close ELSE 0 END AS gain,
                    CASE WHEN close < prev_close THEN prev_close - close ELSE 0 END AS loss
                FROM base_candles
            ),
            daily_metrics AS (
                SELECT 
                    symbol,
                    date,
                    close,
                    prev_close,
                    volume,
                    turnover,
                    max(high) OVER w_250 AS high_52w,
                    min(low) OVER w_250 AS low_52w,
                    avg(close) OVER w_20 AS sma_20,
                    avg(volume) OVER w_20 AS vol_avg_20,
                    stddev(volume) OVER w_20 AS vol_std_20,
                    avg(gain) OVER w_14 AS avg_gain_14,
                    avg(loss) OVER w_14 AS avg_loss_14,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
                FROM gains_losses
                WINDOW 
                    w_250 AS (PARTITION BY symbol ORDER BY date ROWS BETWEEN 250 PRECEDING AND CURRENT ROW),
                    w_20 AS (PARTITION BY symbol ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                    w_14 AS (PARTITION BY symbol ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW)
            ),
            projected AS (
                SELECT 
                    m.symbol,
                    COALESCE(s.name, m.symbol) AS name,
                    COALESCE(s.category, 'EQ') AS category,
                    m.close,
                    m.turnover,
                    (m.high_52w - m.close) / NULLIF(m.high_52w, 0) * 100 AS dist_from_52w_high_pct,
                    (m.close - m.low_52w) / NULLIF(m.low_52w, 0) * 100 AS dist_from_52w_low_pct,
                    (m.volume - m.vol_avg_20) / NULLIF(m.vol_std_20, 0) AS volume_zscore_20,
                    CASE 
                        WHEN m.avg_loss_14 = 0 AND m.avg_gain_14 = 0 THEN 50.0
                        WHEN m.avg_loss_14 = 0 THEN 100.0
                        ELSE 100.0 - (100.0 / (1.0 + (m.avg_gain_14 / m.avg_loss_14)))
                    END AS rsi_14,
                    m.date,
                    COALESCE(s.tier, 1) AS tier,
                    m.turnover AS turnover_today,
                    m.turnover / 10000000.0 AS turnover_cr,
                    (m.close - m.sma_20) / NULLIF(m.sma_20, 0) * 100 AS dist_from_sma_20_pct,
                    (m.close - m.prev_close) / NULLIF(m.prev_close, 0) * 100 AS change_pct_1d
                FROM daily_metrics m
                LEFT JOIN symbols s ON m.symbol = s.symbol
                WHERE m.rn = 1 AND {cat_filter}
            )
            SELECT * FROM projected WHERE 1=1
            """
            
            rules = filter_params.technical_rules or []
            matched_rules_names = []
            
            ALLOWED_FIELDS = {
                "volume_zscore_20", "dist_from_52w_high_pct", "dist_from_52w_low_pct",
                "dist_from_sma_20_pct", "change_pct_1d", "rsi_14", "tier",
                "close", "turnover", "turnover_today", "turnover_cr"
            }
            ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=", "!="}

            for rule in rules:
                field = str(rule.get("field", "")).strip().lower()
                op = str(rule.get("operator", "")).strip()
                try:
                    val = float(rule.get("value", 0))
                except (ValueError, TypeError):
                    continue

                if field in ALLOWED_FIELDS and op in ALLOWED_OPERATORS:
                    query += f" AND {field} {op} {val}"
                    matched_rules_names.append(f"{field} {op} {val}")
                
            if filter_params.min_turnover_cr > 0:
                query += f" AND turnover >= {filter_params.min_turnover_cr * 10000000}"
                
            try:
                res = conn.execute(query).fetchall()
                logger.info("Screener scan executed for %s: found %d matches (rules: %s)", target_date, len(res), matched_rules_names)
                results = []
                for row in res:
                    results.append(ScreenerResult(
                        symbol=str(row[0]),
                        name=str(row[1]) if row[1] else str(row[0]),
                        category=str(row[2]) if row[2] else "EQ",
                        close=round(float(row[3]), 2) if row[3] is not None else 0.0,
                        turnover_cr=round(float(row[12]), 2) if row[12] is not None else (round(float(row[4])/10000000, 2) if row[4] else 0.0),
                        matched_rules=matched_rules_names,
                        as_of_date=row[9].strftime("%Y-%m-%d") if hasattr(row[9], "strftime") else str(row[9]),
                        dist_from_52w_high_pct=round(float(row[5]), 2) if row[5] is not None else None,
                        dist_from_52w_low_pct=round(float(row[6]), 2) if row[6] is not None else None,
                        volume_zscore_20=round(float(row[7]), 2) if row[7] is not None else None,
                        rsi_14=round(float(row[8]), 2) if row[8] is not None else None,
                        dist_from_sma_20_pct=round(float(row[13]), 2) if row[13] is not None else None,
                        change_pct_1d=round(float(row[14]), 2) if row[14] is not None else None
                    ))
                return results
            except Exception as e:
                logger.error(f"Screener query failed: {e}", exc_info=True)
                raise
