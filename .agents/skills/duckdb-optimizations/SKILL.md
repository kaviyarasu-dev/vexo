---
name: duckdb-optimizations
description: Guidelines for working with DuckDB as the primary database, especially single-writer constraints.
---

# DuckDB Optimizations & Rules

## The Single-Writer Constraint
DuckDB allows multiple concurrent readers but ONLY ONE WRITER process at a time.
- **Uvicorn Configuration:** You MUST run Uvicorn with `--workers 1`.
- **Connections:** 
  - Create a single global connection pool/manager for writes.
  - For reads, you can clone connections or use cursors (`conn.cursor()`) to prevent locking the main connection.

## Data Ingestion
- Use Appender (`conn.appender()`) for high-throughput inserts instead of individual `INSERT INTO` statements.
- Store OHLCV and raw financial data as Append-Only. Do not UPDATE historical tick data.

## Parquet Integration
- DuckDB excels at reading Parquet. For backups or historical dumps, always export to Parquet.
- Querying directly from Parquet files is allowed for data older than 1 year to save memory.
