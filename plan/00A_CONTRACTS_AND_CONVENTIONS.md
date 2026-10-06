# 00A: Canonical Contracts, Schemas & System Conventions

**Document Status**: ARCHITECTURAL SOURCE OF TRUTH (LOCKED GATE)  
**Applicability**: Mandatory across all implementation phases (00 through 19, 99).  
**Enforcement**: Every plan file, interface, table, config key, and endpoint MUST cite the exact identifiers registered here. No ad-hoc variations or aliases are permitted.

---

## 1. Canonical Interface Registry

Every service and repository in the system implements exactly ONE canonical interface defined under `core/interfaces.py`.

| Canonical Interface | Purpose / Domain | Key Conceptual Method Signatures | Retired / Prohibited Variants |
|---|---|---|---|
| `IAuthService` | Authentication, OAuth code exchange, token lifecycle | `get_auth_url() -> str`<br>`exchange_code_for_token(code: str) -> AuthToken`<br>`get_valid_token() -> str`<br>`validate_session() -> bool`<br>`refresh_token_if_needed() -> bool` | `FyersAuthManager`, `TokenValidator` |
| `IMarketDataProvider` | Upstream broker HTTP/WebSocket network client | `fetch_candles(symbol: str, resolution: str, range_from: str, range_to: str, cont_flag: str = "0") -> list[dict]`<br>`fetch_quotes(symbols: list[str]) -> dict`<br>`fetch_option_chain(symbol: str, strikes: int = 20) -> dict` | `MarketDataProvider`, `IMarketData`, `FyersDataClient` |
| `ISymbolRepository` | Symbol master storage & search | `upsert_symbols(symbols: list[SymbolEntity]) -> int`<br>`search_symbols(query: str, category: str \| None, limit: int = 20) -> list[SymbolEntity]`<br>`get_by_symbol(symbol: str) -> SymbolEntity \| None`<br>`list_active_symbols(tier: int \| None = None) -> list[SymbolEntity]` | `ISymbolService`, `SymbolMasterRepository` |
| `ICandleReader` | Time-series candle reading & queries | `get_raw_candles(symbol: str, timeframe: str, start: datetime, end: datetime, limit: int = 1000, cursor: str \| None = None) -> list[Candle]`<br>`get_adjusted_candles(symbol: str, timeframe: str, start: datetime, end: datetime, limit: int = 1000) -> list[Candle]`<br>`get_latest_candle(symbol: str, timeframe: str) -> Candle \| None` | `CandleRepository`, `IHistoricalReader` |
| `ICandleWriter` | Ingestion batch insertion & deduplication | `batch_insert_1m(candles: list[dict] \| pa.Table) -> int`<br>`batch_insert_1d(candles: list[dict] \| pa.Table) -> int`<br>`stage_and_merge_1m(staging_table: str) -> int` | `CandleWriter`, `IBatchWriter` |
| `ICheckpointRepository` | Download state machine & resumption tracking | `get_checkpoint(symbol: str, timeframe: str) -> Checkpoint \| None`<br>`update_checkpoint(checkpoint: Checkpoint) -> None`<br>`list_pending_symbols(timeframe: str, tier: int \| None = None) -> list[str]` | `CheckpointManager`, `IDownloadState` |
| `ICorporateActionRepository` | Splits, bonuses, dividends, and adjustment factors | `upsert_actions(actions: list[CorporateAction]) -> int`<br>`get_factors(symbol: str) -> list[AdjustmentFactor]`<br>`recompute_adjustment_factors(symbol: str) -> None` | `CorporateActionManager` |
| `IResamplingService` | In-database & vectorized session-aligned resampling | `resample(symbol: str, target_timeframe: str, start: datetime, end: datetime, adjusted: bool = True) -> pd.DataFrame` | `IResampler`, `TimeframeResampler` |
| `IIndicator` | Pluggable technical & quantitative indicator math | `name() -> str`<br>`required_columns() -> list[str]`<br>`compute(df: pd.DataFrame) -> pd.DataFrame` | `IIndicatorCalculator`, `QuantIndicatorEngine` |
| `IDataExporter` | Export generation (Parquet, CSV, Excel) | `export(symbol: str, timeframe: str, start: datetime, end: datetime, format: str, adjusted: bool = True) -> str` (returns temp file path) | `DataExporter`, `ExportFactory` |
| `ICandleService` | High-level market data orchestration for API | `get_candles(request: CandleQueryRequest) -> CandleQueryResponse`<br>`get_stream_info(symbol: str) -> StreamMetadata` | `CandleService`, `MarketDataService` |
| `IScreenerService` | Multi-factor quantitative screening engine | `run_screener(filter_params: ScreenerFilter) -> list[ScreenerResult]`<br>`save_preset(name: str, filter_params: ScreenerFilter) -> str` | `ScreenerEngine`, `IScanner` |
| `IAlertService` | Rule evaluation, deduplication, and notification | `evaluate_rules(latest_candles: dict[str, Candle]) -> list[AlertTrigger]`<br>`dispatch_alert(alert: AlertTrigger) -> bool` | `AlertManager`, `IAlertEngine` |
| `IBacktestEngine` | Historical event-driven/vectorized simulation | `run_backtest(config: BacktestConfig) -> BacktestResult`<br>`run_walk_forward(config: WalkForwardConfig) -> WalkForwardResult` | `Backtester`, `IStrategyEngine` |
| `IJournalService` | Trade logging, tagging, analytics, and paper trading | `record_trade(trade: JournalEntry) -> str`<br>`get_performance_metrics() -> JournalMetrics`<br>`simulate_paper_order(order: PaperOrder) -> PaperFill` | `JournalRepository`, `ITradeJournal` |

---

## 2. Canonical Timeframe List & Session Alignment Rules

### 2.1. Supported Timeframes
The platform supports exactly these canonical timeframe strings:
- **Base (Downloaded)**: `1m`, `1D`.
- **Derived (Resampled from `1m`)**: `3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1W`.

### 2.2. Indian Session Alignment & UTC Conversion Math
- Standard Indian Equity Session: **09:15:00 to 15:30:00 IST** (Duration: 375 minutes).
- Indian Standard Time (IST) is **UTC+05:30**.
- **Conversion Formula**:
  $$\text{UTC Time} = \text{IST Time} - 05\text{ hours } 30\text{ minutes}$$
- Market Open `09:15:00 IST` = **`03:45:00 UTC`** ($09:15 - 05:30 = 03:45$).
- Market Close `15:30:00 IST` = **`10:00:00 UTC`** ($15:30 - 05:30 = 10:00$).
- Muhurat Special Session (typical): `18:15:00 to 19:15:00 IST` = `12:45:00 to 13:45:00 UTC`.

### 2.3. Intraday Session Bucketing Rules
DuckDB `time_bucket` MUST use the explicit origin `TIMESTAMP '2000-01-01 03:45:00'` to anchor grids to `09:15:00 IST`:
- **`5m`**: 75 full bars/day (`09:15-09:20`, ..., `15:25-15:30`).
- **`15m`**: 25 full bars/day (`09:15-09:30`, ..., `15:15-15:30`).
- **`30m`**: 12 full bars (`09:15-09:45`, ..., `14:45-15:15`) + 1 session stub bar of 15 minutes (`15:15-15:30`).
- **`1h`**: 6 full bars (`09:15-10:15`, `10:15-11:15`, `11:15-12:15`, `12:15-13:15`, `13:15-14:15`, `14:15-15:15`) + 1 session stub bar of 15 minutes (`15:15-15:30`). Total: 7 bars/day.
- **`2h`**: 3 bars (`09:15-11:15`, `11:15-13:15`, `13:15-15:15`) + 1 session stub of 15 minutes (`15:15-15:30`). Total: 4 bars/day.
- **`4h`**: 1 full 4h bar (`09:15-13:15`) + 1 session stub of 2h 15m (`13:15-15:30`). Total: 2 bars/day.
- **`1D`**: 1 bar spanning the full trading session (`09:15:00 to 15:30:00 IST`). Stored with `DATE` representation.
- **`1W`**: Monday through Friday calendar week, anchored to the Monday session.

### 2.4. Zero-Volume Bar Policy
If an illiquid instrument has no trades in a 1-minute interval:
- **Storage Layer**: NO fake/synthetic candle is ever stored in `candles_1m_raw`.
- **Resampling Layer**: If an entire higher timeframe bucket has zero trades, the resampler produces a row with `open = close = prev_close`, `high = max(open, close)`, `low = min(open, close)`, `volume = 0`, and flags `is_zero_volume = TRUE`.

---

## 3. Canonical Time Conventions
- **Internal Storage**: UTC `TIMESTAMP` for intraday (`candles_1m_raw`); `DATE` (`YYYY-MM-DD`) for daily (`candles_1d_raw`).
- **Boundary Semantics**: Candle timestamps represent the **START** of the candle interval (e.g. `03:45:00 UTC` represents `09:15:00` to `09:15:59.999 IST`).
- **API Response Output**: ISO-8601 string (`"2024-01-10T09:15:00+05:30"`) or Unix Epoch Seconds (`1704858300`), normalized to IST for frontend display.

---

## 4. Canonical Database Schema Registry

Database: `data/market_data.duckdb` (Single embedded DuckDB instance).  
Current Schema Version: `1.0.0` (Tracked in `schema_version` table).

```sql
-- Migration tracking table (Owner: Phase 02)
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR NOT NULL
);

-- Master Instruments Table (Owner: Phase 03)
CREATE TABLE IF NOT EXISTS symbols (
    symbol VARCHAR PRIMARY KEY,           -- Canonical: 'NSE:RELIANCE-EQ'
    name VARCHAR NOT NULL,                 -- 'Reliance Industries Limited'
    isin VARCHAR,                          -- 'INE002A01018'
    exchange VARCHAR DEFAULT 'NSE',
    segment VARCHAR DEFAULT 'EQUITY',
    series VARCHAR DEFAULT 'EQ',
    lot_size INTEGER DEFAULT 1,
    tick_size DOUBLE DEFAULT 0.05,
    category VARCHAR,                      -- 'NIFTY50', 'NIFTYNEXT50', 'NIFTYMIDCAP150', 'NIFTYSMALLCAP250', 'OTHERS'
    tier INTEGER NOT NULL DEFAULT 4,       -- 1 (Top 100), 2 (Mid 150), 3 (Small 250), 4 (Tail)
    priority_rank INTEGER DEFAULT 9999,
    listing_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw Intraday 1-Minute Candles (Owner: Phase 02 / 04)
CREATE TABLE IF NOT EXISTS candles_1m_raw (
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,          -- UTC bar start time
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL
);

-- Raw Daily EOD Candles (Owner: Phase 02 / 04)
CREATE TABLE IF NOT EXISTS candles_1d_raw (
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,                    -- Trading session date
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL
);

-- Official Corporate Actions Feed (Owner: Phase 15)
CREATE TABLE IF NOT EXISTS corporate_actions (
    id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    action_type VARCHAR NOT NULL,          -- 'SPLIT', 'BONUS', 'DIVIDEND', 'RIGHTS'
    ex_date DATE NOT NULL,
    record_date DATE,
    ratio_from DOUBLE,                     -- e.g. 10 for a 10:1 split
    ratio_to DOUBLE,                       -- e.g. 1 for a 10:1 split
    dividend_amount DOUBLE,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Calculated Adjustment Factors (Owner: Phase 15)
CREATE TABLE IF NOT EXISTS adjustment_factors (
    symbol VARCHAR NOT NULL,
    ex_date DATE NOT NULL,
    factor_price DOUBLE NOT NULL,          -- Multiplier applied to historical price (< 1.0 for splits)
    factor_volume DOUBLE NOT NULL,         -- Multiplier applied to historical volume (> 1.0 for splits)
    PRIMARY KEY (symbol, ex_date)
);

-- Resumable Download Checkpoints (Owner: Phase 02 / 04)
CREATE TABLE IF NOT EXISTS download_checkpoints (
    symbol VARCHAR NOT NULL,
    timeframe VARCHAR NOT NULL,            -- '1m' or '1D'
    earliest_ts TIMESTAMP,                 -- Earliest timestamp ingested (precise timestamp)
    latest_ts TIMESTAMP,                   -- Latest timestamp ingested (precise timestamp)
    total_candles INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'PENDING',      -- 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    consecutive_empty_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message VARCHAR,
    PRIMARY KEY (symbol, timeframe)
);

-- Market Trading Calendar & Holidays (Owner: Phase 02 / 06)
CREATE TABLE IF NOT EXISTS market_holidays (
    holiday_date DATE PRIMARY KEY,
    description VARCHAR NOT NULL,
    is_special_session BOOLEAN DEFAULT FALSE,
    trading_start TIME DEFAULT '09:15:00',
    trading_end TIME DEFAULT '15:30:00'
);

-- EOD Options Chain Snapshots (Owner: Phase 16)
CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    snapshot_date DATE NOT NULL,
    underlying_symbol VARCHAR NOT NULL,
    expiry_date DATE NOT NULL,
    strike_price DOUBLE NOT NULL,
    option_type VARCHAR NOT NULL,          -- 'CE' or 'PE'
    ltp DOUBLE,
    oi BIGINT,
    volume BIGINT,
    iv DOUBLE,
    delta DOUBLE,
    gamma DOUBLE,
    theta DOUBLE,
    vega DOUBLE,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (snapshot_date, underlying_symbol, expiry_date, strike_price, option_type)
);

-- Screener Presets & Saved Scans (Owner: Phase 12)
CREATE TABLE IF NOT EXISTS screener_presets (
    preset_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    filter_criteria JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring Watchlists (Owner: Phase 13)
CREATE TABLE IF NOT EXISTS watchlists (
    watchlist_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    symbols JSON NOT NULL,                 -- Array of symbol strings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Active Alerts Registry (Owner: Phase 13)
CREATE TABLE IF NOT EXISTS alert_rules (
    alert_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    rule_type VARCHAR NOT NULL,            -- 'PRICE_CROSS', 'RSI_THRESHOLD', 'VWAP_CROSS', 'VOLUME_SPIKE'
    condition_params JSON NOT NULL,
    channel VARCHAR NOT NULL DEFAULT 'IN_APP', -- 'IN_APP', 'EMAIL', 'TELEGRAM'
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trade Journal & Paper Trading Log (Owner: Phase 17)
CREATE TABLE IF NOT EXISTS journal_entries (
    trade_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    trade_type VARCHAR NOT NULL,           -- 'PAPER' or 'MANUAL'
    direction VARCHAR NOT NULL,            -- 'LONG' or 'SHORT'
    entry_time TIMESTAMP NOT NULL,
    entry_price DOUBLE NOT NULL,
    exit_time TIMESTAMP,
    exit_price DOUBLE,
    quantity INTEGER NOT NULL,
    stop_loss DOUBLE,
    take_profit DOUBLE,
    pnl_gross DOUBLE,
    total_charges DOUBLE,
    pnl_net DOUBLE,
    r_multiple DOUBLE,
    mistake_tags JSON,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Operational Execution Logs (Owner: Phase 02 / 06)
CREATE TABLE IF NOT EXISTS job_logs (
    job_id VARCHAR PRIMARY KEY,
    job_type VARCHAR NOT NULL,             -- 'HISTORICAL_INITIAL', 'DAILY_INCREMENTAL', 'OPTION_SNAPSHOT', 'MAINTENANCE'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    symbols_processed INTEGER DEFAULT 0,
    symbols_failed INTEGER DEFAULT 0,
    total_candles_ingested BIGINT DEFAULT 0,
    status VARCHAR NOT NULL,               -- 'RUNNING', 'COMPLETED', 'FAILED', 'FAILED_AUTH'
    details VARCHAR
);
```

### 4.1. Corporate Action Dynamic Views
```sql
-- Adjusted 1D view combining raw candles with cumulative adjustment factors
CREATE OR REPLACE VIEW candles_1d_adjusted AS
SELECT 
    c.symbol,
    c.date,
    c.open * COALESCE(af.factor_price, 1.0) AS open,
    c.high * COALESCE(af.factor_price, 1.0) AS high,
    c.low * COALESCE(af.factor_price, 1.0) AS low,
    c.close * COALESCE(af.factor_price, 1.0) AS close,
    CAST(c.volume * COALESCE(af.factor_volume, 1.0) AS BIGINT) AS volume
FROM candles_1d_raw c
LEFT JOIN adjustment_factors af 
    ON c.symbol = af.symbol AND c.date <= af.ex_date;

-- Adjusted 1m view
CREATE OR REPLACE VIEW candles_1m_adjusted AS
SELECT 
    c.symbol,
    c.timestamp,
    c.open * COALESCE(af.factor_price, 1.0) AS open,
    c.high * COALESCE(af.factor_price, 1.0) AS high,
    c.low * COALESCE(af.factor_price, 1.0) AS low,
    c.close * COALESCE(af.factor_price, 1.0) AS close,
    CAST(c.volume * COALESCE(af.factor_volume, 1.0) AS BIGINT) AS volume
FROM candles_1m_raw c
LEFT JOIN adjustment_factors af 
    ON c.symbol = af.symbol AND CAST(c.timestamp AS DATE) <= af.ex_date;
```

---

## 5. Canonical API Contract Registry

All HTTP endpoints adhere to this standard response envelope:
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

Error Envelope on HTTP 4xx/5xx:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "EXCEL_ROW_LIMIT_EXCEEDED",
    "message": "Export contains 1,250,000 rows exceeding Excel's 1,048,576 limit.",
    "details": { "row_count": 1250000, "recommended_format": "parquet" }
  },
  "meta": {
    "correlation_id": "req-9b8c-4a3e",
    "timestamp": "2026-10-05T17:35:00.123Z"
  }
}
```

### 5.1. Registered Endpoints Table
| Method | Path | Key Query / Body Parameters | Response Data Shape |
|---|---|---|---|
| `GET` | `/api/v1/health` | None | `{"status": "healthy", "duckdb_connected": true, "auth_valid": true}` |
| `GET` | `/api/v1/auth/status` | None | `{"is_authenticated": true, "token_expires_at": "...", "days_remaining_refresh": 12}` |
| `POST` | `/api/v1/auth/refresh` | None | `{"refreshed": true, "new_expiry": "..."}` |
| `GET` | `/api/v1/symbols/search` | `query` (str), `category` (str), `limit` (int = 20) | `list[SymbolSummary]` |
| `GET` | `/api/v1/symbols/{symbol}/metadata` | Path: `symbol` | `SymbolDetail` (ISIN, tiers, earliest/latest timestamps) |
| `GET` | `/api/v1/candles` | `symbol` (str), `timeframe` (str), `from_date` (ts), `to_date` (ts), `adjusted` (bool=true), `indicators` (str), `limit` (int=1000), `cursor` (str) | `{"candles": list[Candle], "next_cursor": str \| null}` |
| `GET` | `/api/v1/export` | `symbol`, `timeframe`, `from_date`, `to_date`, `format` (`parquet`\|`csv`\|`excel`), `adjusted` | File stream (`application/octet-stream` or spreadsheet) |
| `GET` | `/api/v1/screener/run` | Filter params (JSON query) | `list[ScreenerMatch]` |
| `POST` | `/api/v1/backtest/run` | Body: `BacktestConfig` | `BacktestMetricsSummary` + trade list |
| `GET` | `/api/v1/options/chain` | `symbol` (str), `expiry` (str) | `OptionChainResponse` (calls & puts) |
| `GET` | `/api/v1/alerts` | None | `list[AlertRule]` |
| `POST` | `/api/v1/alerts` | Body: `CreateAlertRequest` | `{"alert_id": "..."}` |
| `GET` | `/api/v1/journal/entries` | `start_date`, `end_date`, `limit` | `list[JournalEntry]` |
| `GET` | `/api/v1/system/downloader/status`| None | `DownloaderStatus` |
| `GET` | `/api/v1/system/downloader/stream`| None (SSE endpoint) | SSE stream emitting live download speed, ETA, current ticker |
| `POST`| `/api/v1/system/downloader/control`| `{"action": "start" \| "pause" \| "resume"}` | `{"status": "accepted"}` |

---

## 6. Canonical Configuration Key Registry

All environment configurations are declared in `config/settings.py` using Pydantic Settings.

| Config Key | Data Type | Default Value | Validation / Description |
|---|---|---|---|
| `FYERS_APP_ID` | `str` | Required | Format: `{ALPHANUM}-{TYPE}` (e.g. `2Q10WHDO67-100`). Validates hyphen. |
| `FYERS_SECRET_KEY` | `SecretStr` | Required | Secret key from Fyers developer portal. Never logged. |
| `FYERS_REDIRECT_URI` | `str` | `https://127.0.0.1:5000/` | Registered OAuth redirect URI. |
| `AUTH_CREDENTIAL_STORAGE` | `str` | `KEYRING` | `KEYRING` (OS Keyring) or `ENCRYPTED_FILE` (`data/.vault.enc`). |
| `DUCKDB_PATH` | `str` | `data/market_data.duckdb` | Path to single-file DuckDB database. |
| `EXPORT_DIR` | `str` | `data/exports` | Directory for temporary export files. |
| `LOG_LEVEL` | `str` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `RATE_GOVERNOR_BURST_PER_SEC` | `int` | `10` | Hard cap: 10 requests / second. |
| `RATE_GOVERNOR_TARGET_PER_MIN` | `int` | `180` | Safety target under Fyers 200/min cap. |
| `RATE_GOVERNOR_DAILY_CAP` | `int` | `90000` | Safety target under Fyers 100,000/day cap. |
| `DEFAULT_1M_HISTORY_YEARS` | `int` | `5` | Historical intraday target backfill depth. |
| `DEFAULT_1D_HISTORY_YEARS` | `int` | `15` | Historical daily target backfill depth. |
| `CORS_ORIGINS` | `list[str]` | `["http://localhost:8000", "http://127.0.0.1:8000"]` | Allowed CORS origins. |
| `UVICORN_WORKERS` | `int` | `1` | Strictly 1. Multi-worker uvicorn violates DuckDB single-process rule. |

---

## 7. Global RateGovernor Specification

To prevent account suspension (caused by exceeding 200 req/min more than 3 times/day), ALL network calls to Fyers must pass through ONE shared singleton `RateGovernor`.

```
                        [ Priority Queue: RateGovernor ]
                                       │
     ┌─────────────────────────────────┼────────────────────────────────┐
     │ Lane 1 (High Priority)          │ Lane 2 (Medium Priority)       │ Lane 3 (Low Priority)
     │ Interactive UI Calls            │ EOD Incremental Sync & Alerts  │ Historical Multi-Year Backfill
     │ (Chart requests, Options chain) │ (Triggered post-market)        │ (Background multi-day batch)
     └─────────────────────────────────┴────────────────────────────────┴────────────────────────┘
                                       │
                         [ Dual-Token Bucket Engine ]
                         - Bucket A: Burst (Capacity: 10 tokens, refill 10/sec)
                         - Bucket B: Minute Window (Max 180 tokens/min)
                         - Daily Counter: Soft-stops at 90,000 req/day
                                       │
                         [ Outgoing HTTP / Fyers SDK ]
```

### 7.1. Enforcement Rules
1. **Zero External Calls**: No service may instantiate an HTTP client or call `fyers_apiv3` directly. All calls must invoke `RateGovernor.execute(priority_lane, request_func)`.
2. **Lane Starvation Prevention**: Lane 1 requests preempt Lane 3. If a backfill is running and a user requests a chart, the backfill pauses until the interactive request completes.
3. **429 Handling**: If an unexpected HTTP 429 occurs:
   - Immediately throttle target to 120 req/min for 5 minutes.
   - Sleep 2.0s + exponential jitter ($2^n \times \text{rand}(0.2, 0.5)$).

---

## 8. Process & Concurrency Architecture

- **Single Operating System Process**: The entire application (FastAPI server, background downloader, daily scheduler, alert evaluator) runs inside **ONE Python process**.
- **DuckDB Concurrency Rules**:
  - `write_connection`: Exactly ONE persistent write connection exists, held by `DuckDBConnectionManager`. All write operations are placed onto an in-memory queue (`asyncio.Queue` or `Queue.Queue`) and executed sequentially.
  - `read_connection`: Read endpoints call `conn.cursor()` to obtain lightweight read cursors. Readers do NOT acquire the write lock, allowing simultaneous chart reads during background writes.
  - Blocking DB calls must be dispatched via `asyncio.to_thread()` or `concurrent.futures` to prevent stalling the FastAPI async event loop.
  - Server launcher (`main.py` / uvicorn) strictly sets `workers=1`. Running `uvicorn main:app --workers 4` is forbidden as it creates separate processes competing for DuckDB file locks.

---

## 9. Universe Definitions & Hierarchy Arithmetic

The universe is derived strictly from official NSE index constituent files:

$$\begin{aligned}
\text{Tier 1 (Nifty 100)} &= \text{Nifty 50 (50)} + \text{Nifty Next 50 (50)} = \mathbf{100\text{ stocks}} \\
\text{Tier 2 (Midcap 150)} &= \text{Nifty Midcap 150} = \mathbf{150\text{ stocks}} \\
\text{Tier 3 (Smallcap 250)} &= \text{Nifty Smallcap 250} = \mathbf{250\text{ stocks}} \\
\text{Total Tiers 1 to 3} &= 100 + 150 + 250 = \mathbf{500\text{ stocks (Exact Nifty 500)}} \\
\text{Tier 4 (Remaining NSE Equities)} &= \text{All active NSE EQ stocks not in Nifty 500} \approx \mathbf{1,500\text{ to } 1,700\text{ stocks}}
\end{aligned}$$

- **Rule**:
  - Initial 1m backfill scope is **Tier 1, Tier 2, and Tier 3** (Nifty 500).
  - 1D backfill scope is **All Active Equities (Tiers 1 through 4)**.

---

## 10. Enterprise Non-Functional Requirements (NFR) Checklist

Every implementation phase must satisfy this NFR checklist:
1. **Type Safety & Linting**: 100% typed Python (`mypy --strict` compatible, `ruff` linted).
2. **Layered Pytest Architecture**:
   - `tests/unit/`: Pure algorithmic logic (resampling math, indicator formulas, chunking calculation). Fast, zero I/O.
   - `tests/integration/`: In-memory DuckDB repositories and service wiring.
   - `tests/fixtures/`: Golden recorded API payloads (`tests/fixtures/fyers_response_*.json`). **Live API calls in automated test suites are strictly prohibited.**
3. **Structured Observability**: Logs formatted as JSON with `correlation_id`, `symbol`, `timestamp`, `phase`, and automatic secret redaction (API keys, tokens, PIN).
4. **Idempotence**: Every job, sync, and migration must be safely re-runnable without creating duplicate records or corrupted checkpoints.
5. **Graceful Shutdown**: On `SIGINT`/`SIGTERM`, downloader finishes the in-flight chunk, commits the checkpoint, and flushes the DuckDB WAL before exiting.
6. **Hardware Performance Target**:
   - Baseline hardware: 4 CPU cores, 8 GB RAM, standard NVMe SSD.
   - Resampling query latency: $\le 25\text{ ms}$ for 1 month of 5m data.
   - Ingestion throughput: $\ge 25,000$ candles inserted per second during DuckDB batch commit.
