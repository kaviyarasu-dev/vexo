# Task Brief: Patch 07_FASTAPI_BACKEND_AND_QUANT_APIS.md

**Target File**: `plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md` (ONLY this file may be modified)  
**Allowed Read Set**:
- `plan/00A_CONTRACTS_AND_CONVENTIONS.md`
- `plan/07_FASTAPI_BACKEND_AND_QUANT_APIS.md`
- `plan/VERIFICATION_REPORT.md`

**Objective**:
Upgrade `07_FASTAPI_BACKEND_AND_QUANT_APIS.md` to enterprise quant architecture standards:
1. Add mandatory EXECUTION CONTRACT block at top.
2. Update `/api/v1/candles` query parameters: add `limit` (default 1000) and `cursor` (ISO timestamp) for pagination (required by Phase 08 frontend lazy-loading).
3. Enforce 00A standard response envelope (`success`, `data`, `error`, `meta` with correlation ID).
4. Correct Parquet export architecture: DuckDB `COPY TO PARQUET` writes to local disk; service generates `data/exports/tmp_{uuid}.parquet` and streams via `FileResponse` with background task file cleanup.
5. Excel ceiling: strictly 1,048,575 data rows (+ 1 header = 1,048,576 rows). HTTP 400 `EXCEL_ROW_LIMIT_EXCEEDED` on breach.
6. Export metadata: attach header metadata detailing data source (Fyers API), personal non-commercial license note, survivorship bias disclosure, and corporate action adjustment status (`adjusted` vs `raw`).
7. Align canonical interfaces: `IDataExporter`, `ICandleService`, `ISymbolRepository`.
8. Keep file under 400 lines.

**Acceptance Self-Test**:
- Begins with EXECUTION CONTRACT.
- Pagination parameters (`limit`, `cursor`) included on candle endpoints.
- Temp file pattern for Parquet export detailed.
- Excel 1,048,575 data row limit and HTTP 400 error envelope documented.
