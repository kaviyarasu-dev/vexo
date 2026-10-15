# Plan 01-001: DuckDB Schema, Drawing Persistence Service & REST API Router

```yaml
EXECUTION_CONTRACT:
  depends_on: []
  reads:
    - "db/connection.py"
    - "main.py"
  produces:
    - "api/models/drawing_models.py"
    - "services/chart_drawing_service.py"
    - "api/routers/chart_drawings.py"
    - "tests/unit/test_chart_drawing_service.py"
    - "tests/integration/test_chart_drawings_api.py"
  exposes:
    - "GET /api/v1/chart/drawings/{symbol}"
    - "POST /api/v1/chart/drawings/{symbol}"
    - "PUT /api/v1/chart/drawings/{drawing_id}"
    - "DELETE /api/v1/chart/drawings/{drawing_id}"
    - "DELETE /api/v1/chart/drawings/{symbol}/all"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/unit/test_chart_drawing_service.py tests/integration/test_chart_drawings_api.py -v"
  definition_of_done:
    - "DuckDB table chart_drawings is auto-created with single-writer batch write protection"
    - "ChartDrawingService provides CRUD operations with independent read cursors and write batches"
    - "FastAPI router exposes REST endpoints with strict Pydantic validation"
    - "Unit and integration tests pass with 100% test coverage for drawing persistence"
  failure_modes_and_recovery:
    - "DuckDB write lock contention -> wrap table writes in db.execute_write_batch()"
    - "Invalid JSON in points or style -> enforce strict Pydantic models before database write"
  handoff:
    - "Provides stable persistence backend for Plan 02-001 (Toolbar and Canvas Overlay)"
```

---

## 1. Goal & Scope / User Jobs Served
Provide a secure, performant database schema and REST API for storing and retrieving technical drawing objects (Trendlines, Horizontal Rays, Fibonacci Retracements, and Risk-Reward boxes) partitioned by stock symbol. Ensures that technical annotations drawn by traders persist across browser sessions and devices.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `drawing_models.py`: Defines request/response schemas and point/style structures.
  - `chart_drawing_service.py`: Encapsulates database transactions, serialization, and DuckDB interactions.
  - `chart_drawings.py`: Handles HTTP routing, path validation, and status code mapping.
- **Dependency Inversion Principle (DIP):**
  - Service receives `DuckDBConnectionManager` via dependency injection.
  - Router receives service via FastAPI `Depends()`.

---

## 3. Domain & Data Schema Specifications

### DuckDB Table: `chart_drawings`
```sql
CREATE TABLE IF NOT EXISTS chart_drawings (
    drawing_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    tool_type VARCHAR NOT NULL,
    points JSON NOT NULL,
    style JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chart_drawings_symbol ON chart_drawings(symbol);
```

### Supported `tool_type` Values:
- `TRENDLINE`: 2 points `[{ time, price }, { time, price }]`
- `HORIZONTAL_RAY`: 1 anchor point `[{ time, price }]`
- `FIBONACCI`: 2 pivot points `[{ time, price }, { time, price }]`
- `POSITION_RR`: 3 reference levels `[{ time, price: entryPrice }, { time, price: targetPrice }, { time, price: stopLossPrice }]`

---

## 4. Domain Contracts & Service Interfaces

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DrawingPoint(BaseModel):
    time: Any
    price: float

class DrawingStyle(BaseModel):
    color: str = "#2962FF"
    lineWidth: int = 2
    lineStyle: int = 0  # 0: Solid, 1: Dotted, 2: Dashed
    filled: bool = False
    fillColor: Optional[str] = None
    transparency: Optional[float] = 0.2

class CreateDrawingRequest(BaseModel):
    tool_type: str
    points: List[DrawingPoint]
    style: Optional[DrawingStyle] = None

class UpdateDrawingRequest(BaseModel):
    points: Optional[List[DrawingPoint]] = None
    style: Optional[DrawingStyle] = None

class DrawingResponse(BaseModel):
    drawing_id: str
    symbol: str
    tool_type: str
    points: List[DrawingPoint]
    style: DrawingStyle
    created_at: str
    updated_at: str
```

---

## 5. Implementation Steps
1. Create `api/models/drawing_models.py` with Pydantic schemas.
2. Create `services/chart_drawing_service.py`:
   - `_ensure_tables()`: Creates `chart_drawings` table.
   - `get_drawings(symbol)`: Queries drawings for symbol using `db.get_read_cursor()`.
   - `create_drawing(symbol, tool_type, points, style)`: Inserts new drawing via `execute_write_batch()`.
   - `update_drawing(drawing_id, points, style)`: Updates existing drawing.
   - `delete_drawing(drawing_id)`: Removes drawing by ID.
   - `clear_symbol_drawings(symbol)`: Wipes all drawings for symbol.
3. Create `api/routers/chart_drawings.py` and mount in `main.py`.
4. Create unit tests `tests/unit/test_chart_drawing_service.py` and integration tests `tests/integration/test_chart_drawings_api.py`.

---

## 6. Verification & Acceptance Criteria
- Run `pytest tests/unit/test_chart_drawing_service.py tests/integration/test_chart_drawings_api.py -v`.
- Verify creating, listing, updating, and deleting drawings succeeds with HTTP 200/201.
- Verify DuckDB single-writer concurrency constraints are strictly maintained.
