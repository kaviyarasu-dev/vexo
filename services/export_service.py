import os
import uuid
import duckdb
import pandas as pd
from datetime import datetime
from fastapi import HTTPException
import logging

from core.interfaces import IDataExporter
from core.security import attach_export_metadata_to_file
from db.connection import get_db, DuckDBConnectionManager

logger = logging.getLogger(__name__)

class ExportService(IDataExporter):
    def __init__(self, db: DuckDBConnectionManager | None = None):
        self.db = db or get_db()
        self.export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "exports"))
        os.makedirs(self.export_dir, exist_ok=True)

    def export(self, symbol: str, timeframe: str, start: datetime, end: datetime, format: str, adjusted: bool = True) -> str:
        cursor = self.db.get_read_cursor()
        try:
            format = format.lower()
            if format not in ["parquet", "csv", "excel"]:
                raise ValueError(f"Unsupported format: {format}")

            if timeframe not in ["1D", "1m"]:
                from services.resampling_service import ResamplingService
                import pytz
                start_dt = start if getattr(start, "tzinfo", None) else start.replace(tzinfo=pytz.utc)
                end_dt = end if getattr(end, "tzinfo", None) else end.replace(tzinfo=pytz.utc)
                resample_service = ResamplingService(self.db)
                df = resample_service.resample(symbol=symbol, target_timeframe=timeframe, start=start_dt, end=end_dt, adjusted=adjusted)
                
                if format == "excel" and len(df) > 1048575:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "code": "EXCEL_ROW_LIMIT_EXCEEDED",
                            "message": f"Export contains {len(df)} rows exceeding Excel's 1,048,575 limit. Please export as Parquet or CSV, or narrow your date range.",
                            "details": {"row_count": len(df), "limit": 1048575, "recommended_format": "parquet"}
                        }
                    )

                file_id = uuid.uuid4().hex
                ext = "xlsx" if format == "excel" else format
                filepath = os.path.join(self.export_dir, f"tmp_{file_id}.{ext}")

                if format == "parquet":
                    df.to_parquet(filepath, index=False)
                elif format == "csv":
                    df.to_csv(filepath, index=False)
                elif format == "excel":
                    df.to_excel(filepath, index=False, engine='openpyxl')

                attach_export_metadata_to_file(filepath, format)
                return filepath

            table_prefix = "candles_1d" if timeframe == "1D" else "candles_1m"
            table_suffix = "adjusted" if adjusted else "raw"
            table_name = f"{table_prefix}_{table_suffix}"
            time_col = "date" if timeframe == "1D" else "timestamp"
            
            # Excel Row Limit Guard
            if format == "excel":
                count_query = f"SELECT count(*) FROM {table_name} WHERE symbol = ? AND {time_col} >= ? AND {time_col} <= ?"
                count_row = cursor.execute(count_query, [symbol, start, end]).fetchone()
                count = count_row[0] if count_row else 0
                if count > 1048575:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "code": "EXCEL_ROW_LIMIT_EXCEEDED",
                            "message": f"Export contains {count} rows exceeding Excel's 1,048,575 limit. Please export as Parquet or CSV, or narrow your date range.",
                            "details": {"row_count": count, "limit": 1048575, "recommended_format": "parquet"}
                        }
                    )

            file_id = uuid.uuid4().hex
            ext = "xlsx" if format == "excel" else format
            filepath = os.path.join(self.export_dir, f"tmp_{file_id}.{ext}")
            
            query = f"SELECT * FROM {table_name} WHERE symbol = ? AND {time_col} >= ? AND {time_col} <= ? ORDER BY {time_col} ASC"
            
            if format == "parquet":
                sql = f"COPY ({query}) TO '{filepath}' (FORMAT PARQUET)"
                cursor.execute(sql, [symbol, start, end])
            elif format == "csv":
                sql = f"COPY ({query}) TO '{filepath}' (FORMAT CSV, HEADER TRUE)"
                cursor.execute(sql, [symbol, start, end])
            elif format == "excel":
                df = cursor.execute(query, [symbol, start, end]).df()
                # Use pandas to save Excel
                df.to_excel(filepath, index=False, engine='openpyxl')
                
            # Attach mandatory Fyers personal non-commercial license and SEBI disclaimers
            attach_export_metadata_to_file(filepath, format)
            
            return filepath
        finally:
            cursor.close()
