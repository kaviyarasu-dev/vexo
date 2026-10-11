# Phase 07: High-Performance FastAPI Backend & Streaming Quant Exporters

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#5-canonical-api-contract-registry"
    - "plan/VERIFICATION_REPORT.md#27-duckdb-time_bucket-origin"
  produces:
    - "api/server.py"
    - "api/v1/candles.py"
    - "api/v1/symbols.py"
    - "api/v1/export.py"
    - "api/v1/system.py"
    - "services/export_service.py"
  exposes:
    - "ICandleService"
    - "IDataExporter"
  must_not_modify:
    - "plan/*"
    - "db/migrations.py"
  test_plan:
    unit_tests: "tests/unit/test_api_models.py tests/unit/test_export_service.py"
    integration_tests: "tests/integration/test_fastapi_endpoints.py"
    contract_tests: "tests/contract/test_api_envelope.py"
    fixtures: "tests/fixtures/sample_candles.json"
    command: "pytest tests/integration/test_fastapi_endpoints.py tests/contract/test_api_envelope.py -v"
  definition_of_done:
    - item: 1
      command: "curl -s http://localhost:8000/api/v1/candles?symbol=NSE:RELIANCE-EQ&timeframe=5m&limit=10 | jq '.meta.correlation_id'"
      result: "Returns HTTP 200 with standard 00A response envelope and non-null correlation_id."
    - item: 2
      command: "curl -s \"http://localhost:8000/api/v1/export?symbol=NSE:RELIANCE-EQ&timeframe=1m&format=parquet\" -o test.parquet && python -c 'import pandas as pd; df = pd.read_parquet(\"test.parquet\"); assert len(df) > 0'"
      result: "Generates valid Parquet file streamed via temporary scratch file and verifiable by Pandas."
    - item: 3
      command: "curl -s \"http://localhost:8000/api/v1/export?symbol=NSE:RELIANCE-EQ&timeframe=1m&from_date=2015-01-01&to_date=2024-01-01&format=excel\" | jq '.error.code'"
      result: "Returns HTTP 400 with error code 'EXCEL_ROW_LIMIT_EXCEEDED' when row count exceeds 1,048,575."
  failure_modes_and_recovery:
    - failure: "Parquet temp file leak in data/exports/"
      detection: "File count in data/exports/ exceeds 50 files"
      recovery: "FastAPI BackgroundTasks deletes tmp_{uuid}.parquet immediately after FileResponse stream completes; cron cleanup deletes files older than 1 hour"
    - failure: "Slow cursor pagination queries on deep history"
      detection: "Endpoint latency exceeds 100ms for cursor-based paginated chunks"
      recovery: "Ensure queries use Zone-Map pushdown: WHERE timestamp < cursor ORDER BY timestamp DESC LIMIT N"
  handoff:
    - "FastAPI server and REST endpoints operational with standard 00A envelopes."
    - "Parquet, CSV, and Excel exporters verified."
    - "Ready for Phase 08 frontend charting and downloader dashboard."
```

---

## 1. Goal & Scope
Develop a production-grade, asynchronous FastAPI backend exposing clean REST, Server-Sent Events (SSE), and streaming data export APIs for quantitative researchers and frontend charts adhering to the 00A Canonical Registry.

This phase delivers:
- Fast symbol discovery and metadata endpoints with prefix search.
- Time-series candle endpoints supporting dynamic server-side resampling, indicator calculation, and cursor-based pagination (`limit`, `cursor`).
- Standardized response and error envelopes across all endpoints with correlation IDs.
- Multi-format data exporters (**Apache Parquet**, **CSV**, and **Excel .xlsx**) implementing `IDataExporter`.
- Parquet streaming architecture using temporary scratch files (`data/exports/tmp_{uuid}.parquet`) and FastAPI `FileResponse` with background task cleanup.
- Strict Excel ceiling: 1,048,575 data rows (+ 1 header row = 1,048,576 total rows) returning HTTP 400 `EXCEL_ROW_LIMIT_EXCEEDED` on breach.
- Export metadata: attaching data source (Fyers API), personal non-commercial license note, survivorship bias disclosure, and corporate action adjustment status.
- Real-time download progress telemetry via Server-Sent Events (SSE).

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - Route handlers parse HTTP parameters, validate Pydantic schemas, and map exceptions to HTTP status codes only.
  - `ExportService`: Solely responsible for serializing database cursors into Parquet, CSV, or Excel formats.
  - `CandleService`: Implements `ICandleService`, coordinating repository reads and resampling transformations.
- **Open/Closed Principle (OCP)**:
  - Exporters implement `IDataExporter`. Adding Apache Arrow IPC, Feather, or HDF5 requires creating a new exporter class without modifying route controllers.
- **Dependency Inversion Principle (DIP)**:
  - Route handlers inject interfaces (`ISymbolRepository`, `ICandleService`, `IDataExporter`) via FastAPI's `Depends()` framework.

---

## 3. Canonical API Contract Specifications

### 3.1. Standard Response & Error Envelopes
Every response conforms strictly to 00A Section 5:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "correlation_id": "req-9b8c-4a3e",
    "timestamp": "2026-10-05T17:35:00.123Z",
    "execution_time_ms": 14.2
  }
}
```

Error Envelope on HTTP 4xx / 5xx:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "EXCEL_ROW_LIMIT_EXCEEDED",
    "message": "Export contains 1,250,000 rows exceeding Excel's 1,048,575 limit. Please export as Parquet or CSV, or narrow your date range.",
    "details": { "row_count": 1250000, "limit": 1048575, "recommended_format": "parquet" }
  },
  "meta": {
    "correlation_id": "req-9b8c-4a3e",
    "timestamp": "2026-10-05T17:35:00.123Z"
  }
}
```

### 3.2. Endpoints Detail

#### `GET /api/v1/symbols/search`
- Query Params: `query` (str, min length 1), `category` (optional, e.g. `NIFTY50`), `limit` (default 20).
- Response: `list[SymbolSummary]` (symbol, name, lot_size, category, tier, priority_rank, is_active).

#### `GET /api/v1/symbols/{symbol}/metadata`
- Path Param: `symbol` (e.g. `NSE:RELIANCE-EQ`).
- Response: Detailed instrument metadata, earliest 1m timestamp, latest 1m timestamp, total 1m candles, total 1D candles.

#### `GET /api/v1/candles`
- Query Params:
  - `symbol` (str, required): e.g. `NSE:RELIANCE-EQ`.
  - `timeframe` (str, default `'5m'`): canonical string (`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `1D`, etc.).
  - `from_date` (datetime, ISO format).
  - `to_date` (datetime, ISO format).
  - `adjusted` (bool, default `true`): queries `candles_1m_adjusted` or `candles_1d_adjusted`.
  - `indicators` (comma-separated, optional): e.g. `vwap,rsi,macd,bb,atr`.
  - `limit` (int, default `1000`): max candles per chunk.
  - `cursor` (str, optional): ISO timestamp of earliest candle from previous chunk for backward lazy-loading.
- Response Shape:
  ```json
  {
    "symbol": "NSE:RELIANCE-EQ",
    "timeframe": "5m",
    "adjusted": true,
    "count": 75,
    "next_cursor": "2024-01-10T09:15:00Z",
    "candles": [
      {
        "time": 1704858300,
        "open": 2580.0,
        "high": 2585.5,
        "low": 2578.0,
        "close": 2584.2,
        "volume": 142500,
        "vwap": 2582.1,
        "rsi": 54.2
      }
    ]
  }
  ```

#### `GET /api/v1/export`
- Query Params: `symbol`, `timeframe`, `from_date`, `to_date`, `format` (`parquet` | `csv` | `excel`), `adjusted` (bool, default `true`).
- **Parquet Export Implementation**:
  - DuckDB `COPY (SELECT ...) TO 'data/exports/tmp_{uuid}.parquet' (FORMAT PARQUET)` writes file to disk.
  - Returns `FileResponse("data/exports/tmp_{uuid}.parquet", media_type="application/octet-stream", filename=f"{symbol}_{timeframe}.parquet", background=BackgroundTask(cleanup_file))`.
- **Excel Constraint**:
  - Computes row count: `SELECT count(*) FROM ...`.
  - If count $> 1,048,575$: immediately raises `HTTPException(status_code=400, detail=EXCEL_ROW_LIMIT_EXCEEDED)`.
- **Export Metadata**:
  - Parquet: embedded file key-value metadata (`source: Fyers API`, `adjusted: True`, `survivorship_bias_note: Active listed universe only`, `license: Personal Non-Commercial Use`).
  - CSV / Excel: header metadata comments.

#### `GET /api/v1/system/downloader/stream` (SSE Telemetry)
- Returns `text/event-stream` emitting live JSON updates every 500ms:
  - `current_symbol`: e.g. `'NSE:TCS-EQ'`.
  - `completed_count`: 120.
  - `total_count`: 500.
  - `speed_req_per_min`: 178.
  - `estimated_time_remaining_sec`: 1280.
  - `token_expires_in_sec`: 28400.

---

## 4. Implementation Steps
1. Create `api/v1/models/`:
   - `envelope.py` (Generic `ApiResponse[T]`, `ApiError`).
   - `candle_models.py` (Query parameters, candle DTOs).
   - `symbol_models.py`.
2. Implement `services/export_service.py` (`IDataExporter`):
   - Parquet generator writing to `data/exports/tmp_{uuid}.parquet`.
   - CSV streaming generator yielding row chunks.
   - Excel generator (`openpyxl` with 1,048,575 row ceiling guard).
3. Implement controllers under `api/v1/`: `candles.py`, `symbols.py`, `export.py`, `system.py`.
4. Assemble `api/server.py` with CORS middleware, exception handlers, and correlation ID middleware.

---

## 5. Verification & Acceptance Criteria
- OpenAPI documentation renders cleanly at `http://localhost:8000/docs`.
- Pagination verification: Querying `/api/v1/candles?limit=100` returns `count: 100` and a non-null `next_cursor`. Passing `cursor={next_cursor}` fetches the preceding 100 bars seamlessly.
- Parquet export of 1 year 1m RELIANCE data completes in $< 1.2\text{ s}$ and verifies cleanly via `pd.read_parquet()`.
- Excel guard: Exporting $> 1,048,575$ rows returns HTTP 400 in $< 50\text{ ms}$ with the exact `EXCEL_ROW_LIMIT_EXCEEDED` error envelope.
- SSE stream pushes updates continuously without connection drops while downloader is active.
