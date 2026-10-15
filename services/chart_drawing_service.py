import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from db.connection import DuckDBConnectionManager
from api.models.drawing_models import (
    DrawingPoint,
    DrawingStyle,
    DrawingResponse,
)

logger = logging.getLogger(__name__)


class ChartDrawingService:
    """Service for managing interactive technical chart drawing annotations per symbol."""

    def __init__(self, db: DuckDBConnectionManager):
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        """Idempotently ensures chart_drawings table exists."""
        def _create(conn):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chart_drawings (
                    drawing_id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    tool_type VARCHAR NOT NULL,
                    points JSON NOT NULL,
                    style JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        self.db.execute_write_batch(_create)

    def get_drawings(self, symbol: str) -> List[DrawingResponse]:
        """Retrieves all drawings associated with a specific stock symbol."""
        clean_symbol = symbol.strip().upper()
        cursor = self.db.get_read_cursor()
        try:
            rows = cursor.execute("""
                SELECT drawing_id, symbol, tool_type, points, style, created_at, updated_at
                FROM chart_drawings
                WHERE symbol = ?
                ORDER BY created_at ASC
            """, [clean_symbol]).fetchall()
        finally:
            cursor.close()

        results = []
        for r in rows:
            try:
                raw_points = json.loads(r[3]) if isinstance(r[3], str) else (r[3] or [])
                raw_style = json.loads(r[4]) if isinstance(r[4], str) else (r[4] or {})
            except Exception as e:
                logger.warning(f"Failed to parse JSON for drawing {r[0]}: {e}")
                raw_points = []
                raw_style = {}

            points = [DrawingPoint(**p) if isinstance(p, dict) else p for p in raw_points]
            style = DrawingStyle(**raw_style) if isinstance(raw_style, dict) else DrawingStyle()

            results.append(DrawingResponse(
                drawing_id=r[0],
                symbol=r[1],
                tool_type=r[2],
                points=points,
                style=style,
                created_at=str(r[5]),
                updated_at=str(r[6])
            ))
        return results

    def get_drawing_by_id(self, drawing_id: str) -> Optional[DrawingResponse]:
        """Retrieves a single drawing by its unique identifier."""
        cursor = self.db.get_read_cursor()
        try:
            r = cursor.execute("""
                SELECT drawing_id, symbol, tool_type, points, style, created_at, updated_at
                FROM chart_drawings
                WHERE drawing_id = ?
            """, [drawing_id]).fetchone()
        finally:
            cursor.close()

        if not r:
            return None

        raw_points = json.loads(r[3]) if isinstance(r[3], str) else (r[3] or [])
        raw_style = json.loads(r[4]) if isinstance(r[4], str) else (r[4] or {})
        points = [DrawingPoint(**p) if isinstance(p, dict) else p for p in raw_points]
        style = DrawingStyle(**raw_style) if isinstance(raw_style, dict) else DrawingStyle()

        return DrawingResponse(
            drawing_id=r[0],
            symbol=r[1],
            tool_type=r[2],
            points=points,
            style=style,
            created_at=str(r[5]),
            updated_at=str(r[6])
        )

    def create_drawing(
        self,
        symbol: str,
        tool_type: str,
        points: List[DrawingPoint],
        style: Optional[DrawingStyle] = None
    ) -> DrawingResponse:
        """Creates and stores a new chart drawing annotation."""
        clean_symbol = symbol.strip().upper()
        drawing_id = str(uuid.uuid4())
        style_obj = style or DrawingStyle()
        now = datetime.now()

        points_json = json.dumps([p.model_dump() for p in points])
        style_json = json.dumps(style_obj.model_dump())

        def _insert(conn):
            conn.execute("""
                INSERT INTO chart_drawings (drawing_id, symbol, tool_type, points, style, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, [drawing_id, clean_symbol, tool_type.upper(), points_json, style_json])

        self.db.execute_write_batch(_insert)

        return DrawingResponse(
            drawing_id=drawing_id,
            symbol=clean_symbol,
            tool_type=tool_type.upper(),
            points=points,
            style=style_obj,
            created_at=now.isoformat(),
            updated_at=now.isoformat()
        )

    def update_drawing(
        self,
        drawing_id: str,
        points: Optional[List[DrawingPoint]] = None,
        style: Optional[DrawingStyle] = None
    ) -> Optional[DrawingResponse]:
        """Updates vertices or style parameters of an existing drawing."""
        existing = self.get_drawing_by_id(drawing_id)
        if not existing:
            return None

        updated_points = points if points is not None else existing.points
        updated_style = style if style is not None else existing.style

        points_json = json.dumps([p.model_dump() for p in updated_points])
        style_json = json.dumps(updated_style.model_dump())

        def _update(conn):
            conn.execute("""
                UPDATE chart_drawings
                SET points = ?, style = ?, updated_at = CURRENT_TIMESTAMP
                WHERE drawing_id = ?
            """, [points_json, style_json, drawing_id])

        self.db.execute_write_batch(_update)
        return self.get_drawing_by_id(drawing_id)

    def delete_drawing(self, drawing_id: str) -> bool:
        """Deletes a drawing annotation by its unique ID."""
        existing = self.get_drawing_by_id(drawing_id)
        if not existing:
            return False

        def _delete(conn):
            conn.execute("DELETE FROM chart_drawings WHERE drawing_id = ?", [drawing_id])

        self.db.execute_write_batch(_delete)
        return True

    def clear_symbol_drawings(self, symbol: str) -> int:
        """Removes all drawings associated with a symbol."""
        clean_symbol = symbol.strip().upper()
        drawings = self.get_drawings(clean_symbol)
        count = len(drawings)

        if count > 0:
            def _delete_all(conn):
                conn.execute("DELETE FROM chart_drawings WHERE symbol = ?", [clean_symbol])

            self.db.execute_write_batch(_delete_all)
        return count
