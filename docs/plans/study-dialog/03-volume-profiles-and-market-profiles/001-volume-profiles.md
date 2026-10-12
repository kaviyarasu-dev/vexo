# Plan 03-001: Volume Profile & Market Profile (TPO) Quantitative Suite

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - 01-modal-shell-and-catalog/001-modal-ui-and-catalog.md
    - 02-indicators-and-oscillators/001-subpanes-and-indicators.md
  reads:
    - static/js/chart.js
    - services/indicators/vwap.py
    - db/repositories/duckdb_candle_repo.py
  produces:
    - static/js/volume_profile_overlay.js
    - services/indicators/volume_profile.py
    - api/routers/volume_profile.py
  exposes:
    - window.renderVolumeProfile(candles, config)
    - GET /api/v1/studies/session-volume-profile
  must_not_modify:
    - plan/_work/
    - data/market_data.duckdb
  test_plan:
    - python -m pytest tests/unit/test_volume_profile.py
    - node -e "/* Canvas rendering test for price binning and Value Area 70% threshold */"
  definition_of_done:
    - "Selecting 'Visible range volume profile' (VRVP) renders a high-performance horizontal volume histogram on the right price scale of the main chart"
    - "VRVP dynamically recalculates at 60fps upon chart zoom or pan using visible candles"
    - "Point of Control (POC) is distinctly rendered as a prominent red horizontal ray"
    - "Value Area High (VAH) and Value Area Low (VAL) enclose the 70% volume distribution"
    - "Selecting 'Session volume profile' (SVP) displays per-day volume clusters with session-specific POC and Value Area"
    - "Selecting 'Time price opportunity' (TPO) displays 30-min market profile letter brackets (A-M) and Initial Balance (IB)"
  failure_modes_and_recovery:
    - "Low bar count (<10 candles in viewport): Suppress profile rendering gracefully with a 'Zoom out for profile' indicator"
    - "Heavy chart panning: Debounce calculation to 16ms (requestAnimationFrame) to prevent main thread blocking"
  handoff:
    - "Exposes Volume Profile Canvas layer for pattern and options overlays in plan 04-001"
```

## 1. Goal & Scope / User Jobs Served
Replicate TradingView's premier volume and market profile suite. Institutional and volume-spread traders can visualize auction market theory: where buyers and sellers committed maximum capital, identifying High Volume Nodes (HVN), Low Volume Nodes (LVN), Point of Control (POC), and the 70% Value Area (VAH/VAL) across both the visible viewport (VRVP) and individual daily sessions (SVP).

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `volume_profile_overlay.js`: Renders the transparent HTML5 canvas overlay pinned to Lightweight Charts price coordinates.
  - `volume_profile.py`: Vectorized numpy/pandas price binning and 70% value area summation algorithm.
- **Open-Closed Principle (OCP)**:
  - Extensible calculation engine supporting multiple binning modes (Number of Rows vs Tick Size) and anchoring modes (Visible Range, Session, Fixed Range).

## 3. Mathematical & Core Logic Specifications
1. **Price Bin Discretization**:
   $$\text{Price Range} = \text{High}_{\text{max}} - \text{Low}_{\text{min}}, \quad \text{Bin Size} = \frac{\text{Price Range}}{N_{\text{rows}}} \quad (\text{Default } N_{\text{rows}} = 70)$$
2. **Volume Allocation per Candle**:
   For each candle $i$, the traded volume $V_i$ is distributed across bins overlapping $[L_i, H_i]$:
   - Up-Volume: Assigned to green histogram bar if $\text{Close}_i \ge \text{Open}_i$.
   - Down-Volume: Assigned to red/orange histogram bar if $\text{Close}_i < \text{Open}_i$.
3. **Point of Control (POC)**:
   $$\text{POC Price} = \text{Price}(\max(\text{Total Volume}_{\text{bin}}))$$
4. **Value Area Calculation (70% Rule)**:
   Starting from the POC bin, iteratively expand upward and downward taking the larger adjacent volume sum until cumulative volume reaches:
   $$\sum V_{\text{VA}} \ge 0.70 \times \sum_{\text{all bins}} V$$
   - Top boundary of selected bins = **Value Area High (VAH)**.
   - Bottom boundary of selected bins = **Value Area Low (VAL)**.
5. **Time Price Opportunity (TPO / Market Profile)**:
   - Trading day partitioned into 30-minute brackets: `A` (09:15-09:45), `B` (09:45-10:15) through `M` (15:15-15:30 IST).
   - Initial Balance (IB) defined as the price range of brackets `A` and `B` (first hour).

## 4. Domain Contracts & Service Interfaces
```python
# services/indicators/volume_profile.py
from dataclasses import dataclass
from typing import List

@dataclass
class VolumeProfileBin:
    price_level: float
    total_volume: float
    up_volume: float
    down_volume: float
    is_poc: bool
    is_in_value_area: bool

@dataclass
class VolumeProfileResult:
    poc_price: float
    vah_price: float
    val_price: float
    total_volume: float
    bins: List[VolumeProfileBin]

class VolumeProfileEngine:
    def compute_profile(self, df: pd.DataFrame, num_rows: int = 70, value_area_pct: float = 0.70) -> VolumeProfileResult:
        ...
```

## 5. Implementation Steps
1. Create `services/indicators/volume_profile.py` implementing fast numpy price binning, POC determination, and 70% value area traversal.
2. Create `api/routers/volume_profile.py` with `GET /api/v1/studies/session-volume-profile` for querying historical session profiles from DuckDB.
3. Create `static/js/volume_profile_overlay.js`:
   - Inject transparent `<canvas id="volume-profile-canvas">` synchronized with the main chart viewport.
   - Subscribe to chart `timeScale().subscribeVisibleLogicalRangeChange` and price range events.
   - Draw horizontal volume bars aligned with chart price levels, drawing red POC line and yellow VAH/VAL dashed rays.
4. Support TPO / Market Profile rendering mode with letter brackets (A-M) and Initial Balance lines.
5. Connect with `study_dialog.js` under the `Profiles` tab.

## 6. Verification & Acceptance Criteria
- Activating "Visible range volume profile" immediately renders the volume histogram on the right side of the candle chart.
- Panning the chart left/right recalculates the profile instantly with smooth 60fps rendering.
- POC corresponds accurately to the price level with the highest traded volume.
- VAH and VAL bound exactly 70% of total visible volume.
- Hovering over a profile bar displays price, total volume, and delta (buy vs sell volume).
