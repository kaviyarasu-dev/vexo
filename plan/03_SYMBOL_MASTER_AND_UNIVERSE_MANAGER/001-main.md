# Phase 03: NSE Symbol Master Ingestion, Universe Sorter & Liquidity Ranking

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#9-universe-definitions--hierarchy-arithmetic"
    - "plan/VERIFICATION_REPORT.md#28-symbol-master-nse_cmcsv-symbology"
  produces:
    - "services/symbol_service.py"
    - "services/symbol_master_parser.py"
    - "scripts/fetch_nse_indices.py"
    - "scripts/sync_symbols.py"
    - "config/indices/manual_override_indices.json"
  exposes:
    - "ISymbolRepository"
  must_not_modify:
    - "plan/*"
    - "db/migrations.py"
  test_plan:
    unit_tests: "tests/unit/test_symbol_parser.py"
    integration_tests: "tests/integration/test_symbol_sync.py"
    contract_tests: "tests/contract/test_symbol_contract.py"
    fixtures: "tests/fixtures/sample_NSE_CM.csv"
    command: "pytest tests/unit/test_symbol_parser.py tests/contract/test_symbol_contract.py -v"
  definition_of_done:
    - item: 1
      command: "python scripts/sync_symbols.py"
      result: "Populates symbols table with active NSE EQ securities (~2,000 stocks) and seeds download_checkpoints."
    - item: 2
      command: "python -c 'from db.connection import get_db; conn = get_db().get_read_cursor(); t1 = conn.execute(\"SELECT count(*) FROM symbols WHERE tier = 1\").fetchone()[0]; t2 = conn.execute(\"SELECT count(*) FROM symbols WHERE tier = 2\").fetchone()[0]; t3 = conn.execute(\"SELECT count(*) FROM symbols WHERE tier = 3\").fetchone()[0]; assert t1 == 100 and t2 == 150 and t3 == 250'"
      result: "Tier counts match exact arithmetic: Tier 1 = 100, Tier 2 = 150, Tier 3 = 250 (Total Nifty 500 = 500)."
    - item: 3
      command: "python -c 'from db.repositories.duckdb_symbol_repo import DuckDBSymbolRepo; from db.connection import get_db; repo = DuckDBSymbolRepo(get_db()); res = repo.search_symbols(\"RELI\", None, 5); assert any(\"RELIANCE\" in s.name for s in res)'"
      result: "Symbol search returns RELIANCE with sub-5ms latency."
  failure_modes_and_recovery:
    - failure: "Fyers CDN or NSE indices URL unreachable (network failure or 403)"
      detection: "requests.exceptions.RequestException or HTTP 403 in sync_symbols.py"
      recovery: "Fall back automatically to local cached manual override file (config/indices/manual_override_indices.json) and log warning"
    - failure: "Non-equity instruments leak into symbols table"
      detection: "Series other than 'EQ' or segment != 'EQUITY' detected in symbols table"
      recovery: "Parser filter rule enforces strict whitelist: instrument_type == 0 and series == 'EQ'"
  handoff:
    - "Symbol master table populated and classified into Tiers 1-4."
    - "Checkpoints seeded for 1m and 1D ingestion."
    - "Ready for Phase 04 historical downloader engine."
```

---

## 1. Goal & Scope
Develop an automated Symbol Master & Universe Management Service for all NSE Equity securities adhering to the 00A Canonical Registry.

This phase delivers:
- Automated streaming download and parsing of the official Fyers NSE Symbol Master (`NSE_CM.csv`).
- Strict equity filtering isolating `-EQ` securities while excluding debt, bonds, SME, and derivative tokens.
- Mathematically consistent Universe Classification: Tier 1 (Nifty 100 = 100), Tier 2 (Midcap 150 = 150), Tier 3 (Smallcap 250 = 250), Tier 4 (Broad Market Tail). Total Tiers 1-3 = Exactly Nifty 500 (500 stocks).
- Automated constituent fetching from official NSE index CSVs, with local manual-override fallback files. **Zero hand-typed constituent data.**
- Default universe boundaries: Nifty 500 for intraday 1m backfill; all active equities for daily 1D backfill.
- High-speed prefix search and checkpoint initialization.

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `SymbolMasterParser`: Parses raw Fyers CSV columns into domain entities.
  - `UniverseClassifier`: Fetches official index CSVs and assigns tier/category tags.
  - `DuckDBSymbolRepo`: Handles database persistence and prefix search queries implementing `ISymbolRepository`.
- **Open/Closed Principle (OCP)**:
  - Custom user watchlists and thematic baskets implement the `IUniverseFilter` contract, allowing new groupings without modifying the master parser.
- **Dependency Inversion Principle (DIP)**:
  - Downstream services inject `ISymbolRepository`, never executing raw SQL queries or parsing CSV files directly.

---

## 3. Fyers Symbol Master Specification

### 3.1. Source & CDN Characteristics
- **URL**: `https://public.fyers.in/sym_details/NSE_CM.csv` (Public CDN, updated daily pre-market).
- **Structure**: Comma-delimited file **without a header row**.
- **Verified Column Mapping (0-indexed)**:
  - Index `0`: Fyers Security Token (e.g. `10100000002885`).
  - Index `1`: Instrument Full Name (e.g. `Reliance Industries Limited`).
  - Index `2`: Instrument Type (`0` = Equity Cash, `1` = Indices, `2` = Futures, etc.).
  - Index `3`: Lot Size (`1` for standard equities).
  - Index `4`: Tick Size (`0.05`).
  - Index `9`: Fyers Symbology String (e.g. `NSE:RELIANCE-EQ`).
  - Index `13`: Exchange Symbol Ticker (e.g. `RELIANCE`).
  - Index `14`: Series Code (`EQ`, `BE`, `BZ`, `GB`, `GS`, etc.).

### 3.2. Strict Equity Filtering Rules
- **Whitelist Criteria**:
  - Column 2 (Instrument Type) must be `0`.
  - Column 9 (Symbology) must begin with `NSE:` and end with `-EQ`.
  - Column 14 (Series) must be `EQ` (standard equity rolling settlement) or `BE` (book entry / trade-to-trade).
- **Blacklist Criteria**:
  - Exclude series: `GB` (Sovereign Gold Bonds), `GS` (Government Securities), `TB` (Treasury Bills), `N1`-`NZ` (Debentures), `P1` (Preference Shares).
  - Exclude derivatives (`F&O`, Options, Futures) and standalone index tokens.

---

## 4. Universe Classification & Tier Hierarchy Arithmetic

### 4.1. Mathematical Sizing & Consistency
The platform eliminates the legacy inconsistency where "Tier 3" was ambiguously defined. The hierarchy is derived with exact arithmetic from official NSE index constituent files:

$$\begin{aligned}
\text{Tier 1 (Nifty 100)} &= \text{Nifty 50 (50)} + \text{Nifty Next 50 (50)} = \mathbf{100\text{ stocks}} \\
\text{Tier 2 (Midcap 150)} &= \text{Nifty Midcap 150} = \mathbf{150\text{ stocks}} \\
\text{Tier 3 (Smallcap 250)} &= \text{Nifty Smallcap 250} = \mathbf{250\text{ stocks}} \\
\text{Total Tiers 1-3} &= 100 + 150 + 250 = \mathbf{500\text{ stocks (Exact Nifty 500)}} \\
\text{Tier 4 (Remaining NSE Equities)} &= \text{All active NSE EQ stocks not in Nifty 500} \approx \mathbf{1,500\text{ to } 1,700\text{ stocks}}
\end{aligned}$$

### 4.2. Ingestion Universe Scopes
- **1-Minute (`1m`) Intraday Scope**: Tiers 1, 2, and 3 (Nifty 500 = 500 stocks). Downloading intraday tick/1m data for illiquid penny stocks in Tier 4 is prevented by default to preserve rate limits.
- **Daily (`1D`) EOD Scope**: Tiers 1 through 4 (All active NSE EQ stocks, ~2,000+ stocks).

### 4.3. Automated Constituent Ingestion (No Hardcoded Lists)
Index constituents are fetched programmatically by `scripts/fetch_nse_indices.py` from official NSE endpoints:
- Nifty 50: `https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv`
- Nifty Next 50: `https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv`
- Nifty Midcap 150: `https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv`
- Nifty Smallcap 250: `https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap250list.csv`
- Nifty 500: `https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv`

**Fallback Policy**: If NSE archives are unreachable, the script loads `config/indices/manual_override_indices.json`.

---

## 5. Domain Models & Service Contracts

### 5.1. Domain Entity (`core/models.py`)
```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

@dataclass
class SymbolEntity:
    symbol: str               # "NSE:RELIANCE-EQ"
    name: str                 # "Reliance Industries Limited"
    isin: Optional[str]       # "INE002A01018"
    exchange: str = "NSE"
    segment: str = "EQUITY"
    series: str = "EQ"
    lot_size: int = 1
    tick_size: float = 0.05
    category: str = "OTHERS"  # "NIFTY50", "NIFTYNEXT50", "NIFTYMIDCAP150", etc.
    tier: int = 4             # 1, 2, 3, or 4
    priority_rank: int = 9999
    listing_date: Optional[date] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None
```

### 5.2. Repository Interface (`core/interfaces.py`)
```python
class ISymbolRepository(ABC):
    @abstractmethod
    def upsert_symbols(self, symbols: list[SymbolEntity]) -> int:
        """Upserts symbol records into DuckDB symbols table."""
        pass

    @abstractmethod
    def search_symbols(self, query: str, category: Optional[str] = None, limit: int = 20) -> list[SymbolEntity]:
        """Prefix search by ticker or name with sub-5ms latency."""
        pass

    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[SymbolEntity]:
        """Retrieves single symbol entity."""
        pass

    @abstractmethod
    def list_active_symbols(self, tier: Optional[int] = None) -> list[SymbolEntity]:
        """Returns active symbols filtered optionally by tier (1 to 4)."""
        pass
```

---

## 6. Implementation Steps
1. Create `scripts/fetch_nse_indices.py`:
   - Downloads official index CSVs with polite headers (User-Agent, timeout).
   - Generates local cache `data/indices_cache.json`.
   - Populates fallback `config/indices/manual_override_indices.json`.
2. Create `services/symbol_master_parser.py`:
   - Streams `https://public.fyers.in/sym_details/NSE_CM.csv`.
   - Filters rows where column index `2 == 0` and column `14 in ('EQ', 'BE')`.
   - Merges tier and category tags from index cache.
3. Implement `DuckDBSymbolRepo` in `db/repositories/duckdb_symbol_repo.py`:
   - Executes batch `INSERT OR REPLACE INTO symbols` using DuckDB connection manager.
   - Initialises corresponding records in `download_checkpoints` with `status = 'PENDING'`.
4. Create unified runner `scripts/sync_symbols.py`.

---

## 7. Verification & Acceptance Criteria
- Running `python scripts/sync_symbols.py` seeds `symbols` with ~2,000 active NSE equity stocks.
- Tier count check verifies exact arithmetic:
  - `SELECT count(*) FROM symbols WHERE tier = 1` = **100**.
  - `SELECT count(*) FROM symbols WHERE tier = 2` = **150**.
  - `SELECT count(*) FROM symbols WHERE tier = 3` = **250**.
  - Total Tiers 1-3 = **500** (Exact Nifty 500).
- `download_checkpoints` is seeded with corresponding records for resolutions `'1m'` and `'1D'`.
- Prefix search query `search_symbols("TCS")` returns `NSE:TCS-EQ` in $< 5\text{ ms}$.
- Zero debt, bond, or derivative instruments exist in `symbols`.
