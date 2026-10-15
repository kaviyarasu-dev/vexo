# Plan 01-001: Options Open Interest (ΔOI) Calculation Engine, Support/Resistance & REST Router

```yaml
EXECUTION_CONTRACT:
  depends_on: []
  reads:
    - "services/options/greeks_engine.py"
    - "api/routers/options.py"
    - "core/interfaces.py"
    - "db/connection.py"
  produces:
    - "services/options/oi_engine.py"
    - "api/models/options_models.py"
    - "tests/unit/test_options_oi_engine.py"
    - "tests/integration/test_options_oi_api.py"
  exposes:
    - "services.options.oi_engine.OpenInterestEngine"
    - "services.options.oi_engine.FOUniverseRegistry"
    - "GET /api/v1/options/open-interest"
    - "GET /api/v1/options/underlyings"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/unit/test_options_oi_engine.py tests/integration/test_options_oi_api.py -v"
  definition_of_done:
    - "OpenInterestEngine calculates strike-by-strike Call OI, Put OI, Call ΔOI, and Put ΔOI accurately"
    - "Total Put/Call Ratio (PCR_OI) and Change Put/Call Ratio (PCR_ΔOI) computed with market sentiment classification (Bullish, Bearish, Neutral)"
    - "Major Call Resistance Wall, Major Put Support Wall, and Active Battleground strikes identified from strike open interest distributions"
    - "FOUniverseRegistry provides all 180+ NSE F&O equities and indices with standardized lot sizes, spot prices, and strike intervals"
    - "GET /api/v1/options/open-interest returns full Open Interest and ΔOI analytics with sub-50ms latency"
    - "GET /api/v1/options/underlyings returns complete F&O universe with lot sizes and spot prices"
    - "100% assertions pass across unit and integration test suites"
  failure_modes_and_recovery:
    - "Broker live option chain offline or unauthenticated -> generate realistic synthetic ΔOI and volume distributions preserving mathematical put-call parity"
    - "Strike count mismatch between calls and puts -> zero-fill missing strikes ensuring symmetric dual-bar alignment"
  handoff:
    - "Supplies Open Interest, ΔOI, PCR, and F&O underlying metadata required by Plan 02-001 and Plan 03-001"
```

---

## 1. Goal & Scope / User Jobs Served
Empower quantitative derivatives traders with deep visibility into institutional market maker positioning. In Indian index and equity derivatives, open interest concentration and intraday changes ($\Delta\text{OI}$) represent where major writing desks have built defensive walls or are actively covering. This engine computes strike-by-strike open interest distributions, net daily changes, Put/Call Ratios, and structural resistance/support levels, exposed via high-performance REST endpoints.

---

## 2. Architecture & SOLID Principles

```
                  ┌───────────────────────────────┐
                  │    FastAPI Options Router     │
                  │     (api/routers/options)     │
                  └──────────────┬────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
  ┌─────────────────────────────┐  ┌─────────────────────────────┐
  │     OpenInterestEngine      │  │     FOUniverseRegistry      │
  │ (services/options/oi_engine)│  │ (services/options/oi_engine)│
  └──────────────┬──────────────┘  └──────────────┬──────────────┘
                 │                                │
                 ▼                                ▼
  ┌─────────────────────────────┐  ┌─────────────────────────────┐
  │ DuckDB Read Replica & Spot  │  │   Standardized F&O Lots     │
  │  (candles_1d_adjusted)      │  │  (NIFTY: 25, SBIN: 750...)  │
  └─────────────────────────────┘  └─────────────────────────────┘
```

- **Single Responsibility (SRP):** `OpenInterestEngine` handles solely open interest calculations, PCR, and support/resistance detection. `FOUniverseRegistry` manages F&O lot sizes and symbol metadata.
- **Open/Closed (OCP):** Engine operates seamlessly across live broker feeds (`FyersMarketDataProvider`) and offline mathematical models without modifying core calculation rules.
- **Dependency Inversion (DIP):** Database access relies on read-only cursors (`db.get_read_cursor()`), preventing writer lock contention.

---

## 3. Mathematical & Domain Specifications

### 3.1 Put/Call Ratio (PCR)
$$\text{PCR}_{\text{OI}} = \frac{\sum_{i=1}^{N} \text{Put OI}_i}{\sum_{i=1}^{N} \text{Call OI}_i}$$

$$\text{PCR}_{\Delta\text{OI}} = \frac{\sum_{i=1}^{N} \max(0, \Delta\text{Put OI}_i)}{\sum_{i=1}^{N} \max(0, \Delta\text{Call OI}_i) + \epsilon}$$

- **Sentiment Tagging:**
  - $\text{PCR}_{\text{OI}} \ge 1.25$: `"BULLISH"` (Put writing dominance / strong floor)
  - $0.85 < \text{PCR}_{\text{OI}} < 1.25$: `"NEUTRAL"` (Balanced market)
  - $\text{PCR}_{\text{OI}} \le 0.85$: `"BEARISH"` (Call writing dominance / heavy ceiling)

### 3.2 Major Resistance and Support Walls
- **Major Call Resistance:**
  $$K_{\text{resistance}} = \arg\max_{K} (\text{Call OI}(K))$$
- **Major Put Support:**
  $$K_{\text{support}} = \arg\max_{K} (\text{Put OI}(K))$$
- **Max Pain Strike:**
  $$K_{\text{maxpain}} = \arg\min_{K} \sum_{j} \left( \text{Call OI}_j \times \max(0, K - K_j) + \text{Put OI}_j \times \max(0, K_j - K) \right)$$

---

## 4. Domain Contracts & Service Interfaces

### 4.1 Pydantic Schemas (`api/models/options_models.py`)
```python
class StrikeOIData(BaseModel):
    strike: float
    call_oi: int
    call_oi_change: int
    put_oi: int
    put_oi_change: int
    call_volume: int
    put_volume: int
    call_ltp: float
    put_ltp: float
    call_iv: float
    put_iv: float

class OpenInterestAnalysisResponse(BaseModel):
    symbol: str
    spot: float
    expiry_date: str
    total_call_oi: int
    total_put_oi: int
    total_call_oi_change: int
    total_put_oi_change: int
    pcr_oi: float
    pcr_oi_change: float
    sentiment: str  # BULLISH | BEARISH | NEUTRAL
    major_resistance_strike: float
    major_support_strike: float
    max_pain_strike: float
    active_call_battleground: float
    active_put_battleground: float
    strikes_data: List[StrikeOIData]

class FOUnderlyingItem(BaseModel):
    symbol: str
    display_name: str
    category: str  # INDEX | EQUITY
    lot_size: int
    spot_price: float
    strike_step: float
```

---

## 5. Implementation Steps
1. Create `api/models/options_models.py` defining clean Pydantic request/response models.
2. Create `services/options/oi_engine.py`:
   - Implement `FOUniverseRegistry` with comprehensive lot size registry (NIFTY=25, BANKNIFTY=15, FINNIFTY=25, MIDCPNIFTY=50, RELIANCE=250, TCS=175, INFY=400, HDFCBANK=550, SBIN=750, TATAMOTORS=1425, etc.) and DuckDB spot price integration.
   - Implement `OpenInterestEngine.analyze_open_interest(symbol, expiry)` with strike alignment, PCR, resistance/support walls, and synthetic $\Delta\text{OI}$ fallback.
3. Update `api/routers/options.py`:
   - Mount `GET /api/v1/options/open-interest`.
   - Mount `GET /api/v1/options/underlyings`.
4. Author unit tests `tests/unit/test_options_oi_engine.py`:
   - Test PCR calculation, resistance/support detection, symmetric strike data alignment.
5. Author integration tests `tests/integration/test_options_oi_api.py`:
   - Test `GET /api/v1/options/open-interest` and `GET /api/v1/options/underlyings` with HTTP 200 OK and schema validation.

---

## 6. Verification & Acceptance Criteria
- `pytest tests/unit/test_options_oi_engine.py tests/integration/test_options_oi_api.py -v` passes 100%.
- Both endpoints return valid responses in $< 50$ms.
- All existing 287 repository tests continue to pass with zero regressions.
