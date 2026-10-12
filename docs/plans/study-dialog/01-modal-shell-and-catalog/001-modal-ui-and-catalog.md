# Plan 01-001: TradingView Study Modal Shell & Script Catalog System

```yaml
EXECUTION_CONTRACT:
  depends_on: []
  reads:
    - static/index.html
    - static/css/theme.css
    - static/js/chart.js
    - api/routers/candles.py
  produces:
    - static/js/study_dialog.js
    - static/css/study_dialog.css
    - api/routers/studies.py
    - services/study_catalog_service.py
  exposes:
    - window.openStudyDialog()
    - window.closeStudyDialog()
    - GET /api/v1/studies/catalog
  must_not_modify:
    - plan/_work/
    - .env
    - data/market_data.duckdb
  test_plan:
    - python -m pytest tests/unit/test_study_catalog.py
    - node -e "/* DOM smoke test verifying modal open, search, and category switching */"
  definition_of_done:
    - "Toolbar includes 'fx Indicators' button that triggers the TradingView study dialog"
    - "Dialog strictly replicates the reference TradingView UI: Left sidebar (Personal, Built-in, Community) and Sub-pills (Indicators, Strategies, Profiles, Patterns, Options)"
    - "Real-time fuzzy search filters through all script names and tags"
    - "Starring any script adds it to Favorites / Personal scripts in localStorage"
    - "Esc key and backdrop click dismiss the modal"
  failure_modes_and_recovery:
    - "Network failure fetching catalog: Fallback immediately to embedded client-side cached catalog"
    - "Z-index overlap with chart or symbol search: Modal z-index anchored at 1100 with backdrop at 1099"
  handoff:
    - "Exposes window.studyCatalog and window.activeStudiesManager for plan 02-001"
```

## 1. Goal & Scope / User Jobs Served
Provide a TradingView-identical discovery and search interface ("Indicators, metrics, and strategies") accessible from the main chart toolbar (`fx Indicators`). Traders can quickly find any indicator, profile, strategy, or pattern, preview its formula and parameters, star favorites, and apply it directly to the active chart.

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `study_dialog.js`: Manages modal state, DOM event listeners, search filtering, and tab transitions.
  - `study_catalog_service.py`: Centralized registry of all technical studies, their required inputs, output series types, and educational descriptions.
- **Open-Closed Principle (OCP)**:
  - New indicators or profiles can be added to the catalog JSON/dictionary without modifying the rendering logic or modal UI.
- **Dependency Inversion Principle (DIP)**:
  - Frontend talks to `IStudyCatalogService` contract via standard REST API `/api/v1/studies/catalog`, gracefully falling back to a bundled client-side JSON catalog when offline.

## 3. Domain & Core Logic Specifications
- **Modal Geometry & Layout**:
  - Modal Dimensions: `min(960px, 92vw)` width, `min(680px, 86vh)` height.
  - Sidebar: Width `240px`, glassmorphic dark theme (`#131722` / `#1E222D` with subtle borders `#2A2E39`).
  - Search Input: Top bar search with instant debounce (100ms), matching against `name`, `acronym`, `category`, and `tags`.
  - Categories & Pills:
    - PERSONAL: `My scripts`, `Purchased / Favorites`
    - BUILT-IN: `Technicals` (with pills: `Indicators`, `Strategies`, `Profiles`, `Patterns`, `Options`), `Fundamentals`
    - COMMUNITY: `Editors' picks`, `Top`, `Trending`, `Marketplace`
- **Favorites & Persistence**:
  - Store starred item IDs in `localStorage.getItem('nse_quant_starred_studies')`.
  - Starred items render with yellow filled star `★` and appear inside `Favorites`.

## 4. Domain Contracts & Service Interfaces
```python
# services/study_catalog_service.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class StudyItem(BaseModel):
    id: str
    name: str
    category: str # "indicators", "strategies", "profiles", "patterns", "options", "fundamentals"
    sub_category: Optional[str] = None
    section: str # "builtin", "personal", "community"
    description: str
    overlay: bool # True = on main candle pane; False = sub-pane oscillator
    default_inputs: Dict[str, Any]
    tags: List[str]

class IStudyCatalogService:
    def get_catalog(self) -> List[StudyItem]:
        ...
    def search_studies(self, query: str) -> List[StudyItem]:
        ...
```

## 5. Implementation Steps
1. Create `services/study_catalog_service.py` with the complete registry of built-in studies matching TradingView's catalog.
2. Create `api/routers/studies.py` exposing `GET /api/v1/studies/catalog` and register in `main.py`.
3. Add `#study-modal` markup in `static/index.html` and the `fx Indicators` button in `#pro-toolbar`.
4. Create `static/css/study_dialog.css` with exact TradingView styling tokens.
5. Create `static/js/study_dialog.js` handling open/close, category switching, search filtering, and favorite starring.
6. Register the modal in `static/js/app.js` universal modal manager for outside-click and Esc key dismissals.

## 6. Verification & Acceptance Criteria
- Clicking `fx Indicators` opens the modal with 0 DOM errors.
- Switching between `Indicators`, `Strategies`, `Profiles`, `Patterns`, and `Options` correctly re-filters the script list.
- Searching "Volume" filters to Volume, VRVP, SVP, FRVP, and VWAP.
- Pressing `Escape` or clicking outside closes the modal smoothly.
