COPY _arrow_stage_1m FROM 'artifacts/duckdb_export/_arrow_stage__m.parquet' (FORMAT 'parquet', COMPRESSION 'ZSTD');
COPY _dedup_1m FROM 'artifacts/duckdb_export/_dedup__m.parquet' (FORMAT 'parquet', COMPRESSION 'ZSTD');
COPY _staging_1m_batch FROM 'artifacts/duckdb_export/_staging__m_batch.parquet' (FORMAT 'parquet', COMPRESSION 'ZSTD');
COPY candles_1m_raw FROM 'artifacts/duckdb_export/candles__m_raw.parquet' (FORMAT 'parquet', COMPRESSION 'ZSTD');
