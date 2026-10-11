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
            with open("data/screener_templates.json", "r") as f:
                return json.load(f).get("templates", [])
        except Exception as e:
            logger.warning(f"Could not load screener templates: {e}")
            return []

    def _save_templates(self):
        try:
            with open("data/screener_templates.json", "w") as f:
                json.dump({"templates": self.templates}, f, indent=2)
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

    def run_screener(self, filter_params: Optional[ScreenerFilter] = None, template: str = None, universe: str = None, as_of_date: str = None) -> list[ScreenerResult]:
        if template:
            tmpl = self.get_template(template)
            rules = tmpl["conditions"] if tmpl else []
            tmpl_univ = tmpl.get("universe") if tmpl else None
            effective_univ = universe or tmpl_univ or "ALL"
            if not filter_params:
                filter_params = ScreenerFilter(
                    universe=effective_univ,
                    as_of_date=as_of_date,
                    technical_rules=rules
                )
            else:
                filter_params.technical_rules = rules
                if as_of_date: filter_params.as_of_date = as_of_date
                if effective_univ: filter_params.universe = effective_univ
                
        if not filter_params:
            filter_params = ScreenerFilter(universe=universe or "ALL", as_of_date=as_of_date, technical_rules=[])
            
        target_date = filter_params.as_of_date
        
        with self.db.get_read_cursor() as conn:
            if not target_date:
                res = conn.execute("SELECT MAX(date) FROM candles_1d_adjusted").fetchone()
                target_date = res[0].strftime("%Y-%m-%d") if res and res[0] else datetime.now().strftime("%Y-%m-%d")

            # Parse Universe
            if filter_params.universe == "NIFTY50":
                cat_filter = "s.category = 'NIFTY50'"
            elif filter_params.universe == "NIFTY500":
                cat_filter = "s.tier <= 3"
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
                    avg(loss) OVER w_14 AS avg_loss_14
                FROM gains_losses
                WINDOW 
                    w_250 AS (PARTITION BY symbol ORDER BY date ROWS BETWEEN 250 PRECEDING AND CURRENT ROW),
                    w_20 AS (PARTITION BY symbol ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                    w_14 AS (PARTITION BY symbol ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW)
            ),
            projected AS (
                SELECT 
                    m.symbol,
                    s.name,
                    s.category,
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
                    s.tier,
                    m.turnover AS turnover_today,
                    m.turnover / 10000000.0 AS turnover_cr,
                    (m.close - m.sma_20) / NULLIF(m.sma_20, 0) * 100 AS dist_from_sma_20_pct,
                    (m.close - m.prev_close) / NULLIF(m.prev_close, 0) * 100 AS change_pct_1d
                FROM daily_metrics m
                JOIN symbols s ON m.symbol = s.symbol
                WHERE m.date = '{target_date}' AND {cat_filter}
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
                results = []
                for row in res:
                    results.append(ScreenerResult(
                        symbol=row[0],
                        name=row[1],
                        category=row[2],
                        close=float(row[3]) if row[3] else 0.0,
                        turnover_cr=float(row[4])/10000000 if row[4] else 0.0,
                        matched_rules=matched_rules_names,
                        as_of_date=row[9].strftime("%Y-%m-%d")
                    ))
                return results
            except Exception as e:
                logger.error(f"Screener query failed: {e}")
                return []
