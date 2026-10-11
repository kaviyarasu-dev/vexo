import logging
from typing import Any, Dict

from db.connection import DuckDBConnectionManager

logger = logging.getLogger(__name__)

class DataIntegrityAuditor:
    def __init__(self, db: DuckDBConnectionManager):
        self.db = db

    def run_audit(self) -> Dict[str, Any]:
        """Scans database for anomalies like large price jumps without corporate actions."""
        logger.info("Running Data Integrity Audit")
        
        query = """
        WITH shifts AS (
            SELECT 
                symbol, 
                date, 
                close,
                LAG(close) OVER (PARTITION BY symbol ORDER BY date) as prev_close,
                ABS(close - LAG(close) OVER (PARTITION BY symbol ORDER BY date)) / NULLIF(LAG(close) OVER (PARTITION BY symbol ORDER BY date), 0) as price_shift
            FROM candles_1d_raw
        )
        SELECT s.symbol, s.date, s.close, s.prev_close, s.price_shift
        FROM shifts s
        LEFT JOIN corporate_actions ca 
          ON s.symbol = ca.symbol AND s.date = ca.ex_date
        WHERE s.price_shift > 0.25 AND ca.id IS NULL
        """
        
        cursor = self.db.get_read_cursor()
        try:
            anomalies_raw = cursor.execute(query).fetchall()
            anomalies = []
            for row in anomalies_raw:
                anomalies.append({
                    "symbol": row[0],
                    "date": row[1].isoformat() if hasattr(row[1], 'isoformat') else str(row[1]),
                    "close": row[2],
                    "prev_close": row[3],
                    "price_shift": row[4]
                })
            
            return {
                "anomalies_detected": len(anomalies) > 0,
                "anomalies_count": len(anomalies),
                "anomalies": anomalies
            }
        finally:
            cursor.close()
