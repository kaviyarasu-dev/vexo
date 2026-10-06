# Verification Report: DuckDB Engine Behaviour

**Research Topic**: DuckDB (Concurrency, Primary Keys on 100M+ rows, time_bucket origin, Parquet export)  
**Date of Research**: 2026-10-05  
**Reviewer/Researcher**: Stage A Quant Architect Researcher  

---

## 1. Concurrency Model: Readers vs Single Writer
- **Status**: VERIFIED
- **Source**: DuckDB Official Documentation (`https://duckdb.org/docs/api/python/overview`)
- **Paraphrase**: DuckDB allows only one writer process to hold an active write lock on a persistent database file. Multiple threads within the SAME process can execute queries. While DuckDB supports multi-threaded readers, writing requires serialization.
- **Architectural Correction to Plan 00 / 02**:
  - The previous plans suggested readers acquire a mutex lock alongside writers. That would unnecessarily serialize read queries and stall UI charts during heavy ingestion!
  - **Verified Pattern**: The single application process maintains ONE dedicated write connection handle (`write_conn`) managed by an asynchronous/thread-safe queue worker. API readers obtain read-only cursor instances (`conn.cursor()`) which do NOT acquire the write mutex. This allows chart reads and screener queries to execute concurrently with background batch flushes.

---

## 2. Primary Keys & Indexing on 100M+ Rows
- **Status**: VERIFIED
- **Source**: DuckDB Architecture & Performance Guidelines (`https://duckdb.org/docs/internals/storage`)
- **Paraphrase**:
  - In DuckDB, a `PRIMARY KEY` or `UNIQUE` constraint creates an Adaptive Radix Tree (ART) index.
  - While ART indexes provide fast point lookups, maintaining an ART index on a 100M+ row table during bulk insertions incurs substantial memory overhead (gigabytes of RAM) and causes insertion throughput to degrade dramatically as the tree grows.
  - Furthermore, DuckDB achieves its highest analytical query performance not through ART indexes, but via **Zone Maps** (min/max metadata stored per 122,880-row columnar vector chunk) when the table is physically sorted by `(symbol, timestamp)`.
- **Architectural Decision & Gate**:
  - **Primary Design**: Use an unindexed append-only raw table or staging table approach.
    - Chunks are inserted into a temporary in-memory staging table: `INSERT INTO staging_candles SELECT ...;`
    - Staging is merged into the master table with anti-join deduplication:
      `INSERT INTO candles_1m SELECT s.* FROM staging_candles s WHERE NOT EXISTS (SELECT 1 FROM candles_1m c WHERE c.symbol = s.symbol AND c.timestamp = s.timestamp);`
  - **Phase 09 Gate Benchmark**: Benchmark synthetic ingestion at 1M, 10M, and 100M rows comparing:
    - (Option A) `PRIMARY KEY (symbol, timestamp)`
    - (Option B) Unindexed table with sorted insertion + staging anti-join deduplication.
    - Measure: Write throughput (rows/sec), peak RAM usage (MB), and range-read latency (ms). Apply the winner to the full universe scaling.

---

## 3. `time_bucket` with Session Origin
- **Status**: VERIFIED
- **Source**: DuckDB SQL Documentation (`https://duckdb.org/docs/sql/functions/timewindow`)
- **Paraphrase**: DuckDB's `time_bucket(bucket_width, timestamp, origin)` function accepts an explicit `origin` parameter of type `TIMESTAMP` to anchor the grid.
- **NSE Session Alignment Application**:
  - Indian Standard Time (IST) is UTC+05:30.
  - NSE market opens at `09:15:00 IST`, which corresponds to `03:45:00 UTC` ($09:15 - 05:30 = 03:45$).
  - When timestamps are stored in UTC:
    `time_bucket(INTERVAL '15 MINUTES', timestamp, TIMESTAMP '2000-01-01 03:45:00')`
  - This mathematically guarantees that 15-minute bars start exactly at `03:45 UTC` (`09:15 IST`), `04:00 UTC` (`09:30 IST`), ..., with zero drift.

---

## 4. `COPY TO ... (FORMAT PARQUET)` Streaming vs Temp File
- **Status**: VERIFIED
- **Source**: DuckDB Parquet Export Docs (`https://duckdb.org/docs/data/parquet/overview`)
- **Paraphrase**: `COPY (SELECT ...) TO 'path/file.parquet' (FORMAT PARQUET)` writes directly to an OS filesystem path. DuckDB does not support direct streaming of generated Parquet files over raw HTTP socket descriptors.
- **Architectural Requirement for Plan 07**:
  - The export service must generate the Parquet file into a temporary local scratch directory (`data/exports/tmp_{uuid}.parquet`).
  - FastAPI streams the file using `FileResponse` (with background cleanup callback to delete the temp file upon stream completion).
  - This avoids loading the entire Parquet byte array into Python memory while adhering to DuckDB's file-based writer contract.
