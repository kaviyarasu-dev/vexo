# Plan 02-001: Left Vertical Drawing Toolbar & Overlay Canvas Rendering Engine

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-database-and-api/001-database-and-api.md"
  reads:
    - "static/index.html"
    - "static/js/chart.js"
    - "api/routers/chart_drawings.py"
  produces:
    - "static/css/chart_drawings.css"
    - "static/js/chart_drawings.js"
    - "static/index.html"
    - "tests/integration/test_drawing_overlay_integration.py"
  exposes:
    - "window.ChartDrawingManager"
    - "window.ChartDrawingManager.setTool(toolName)"
    - "window.ChartDrawingManager.toggleMagnet()"
    - "window.ChartDrawingManager.clearAll()"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "powershell -Command \"Invoke-WebRequest -Uri http://localhost:8000/static/js/chart_drawings.js -UseBasicParsing | Select-Object -Property StatusCode\""
    - "pytest tests/integration/test_drawing_overlay_integration.py -v"
  definition_of_done:
    - "Left vertical glassmorphic drawing toolbar rendered alongside main chart container"
    - "Interactive SVG/Canvas drawing layer mounted over Lightweight Charts container"
    - "Pixel-to-Domain and Domain-to-Pixel coordinate projection synchronized with chart pan/zoom at 60 FPS"
    - "Magnet snap mode accurately identifies nearest candle vertex within 15px"
    - "Dual persistence seamlessly loads from LocalStorage and synchronizes with REST API"
  failure_modes_and_recovery:
    - "Chart resizing causes coordinate drift -> recompute all drawing pixel paths on handleResize and subscribeVisibleTimeRangeChange"
    - "Canvas intercepts chart zoom clicks -> pass through mouse wheel events when cursor is in select mode"
  handoff:
    - "Provides drawing overlay infrastructure for Plan 03-001 (Specific Tool State Machines)"
```

---

## 1. Goal & Scope / User Jobs Served
Establish the visual and mathematical frontend infrastructure for chart drawings: a TradingView-style left vertical floating toolbar, an interactive SVG drawing canvas overlaid on the chart viewport, a 60 FPS coordinate projection pipeline that keeps drawings locked to candles during zooming and panning, and a magnet snap engine for high-precision charting.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - `chart_drawings.css`: Toolbar positioning, active glow states, cursor types, and glassmorphic styling.
  - `chart_drawings.js`: Coordinates mapping, toolbar event delegation, canvas overlay rendering, magnet snapping, and dual storage synchronization.
- **Open/Closed Principle (OCP):**
  - Drawing tools implement a pluggable `ITool` interface (`onMouseDown`, `onMouseMove`, `onMouseUp`, `renderSvg`) so new drawing tools can be added without modifying the core canvas lifecycle.

---

## 3. UI/UX Specifications: Left Vertical Floating Toolbar

```html
<div class="chart-drawing-toolbar" id="chart-drawing-toolbar">
    <button type="button" class="drawing-tool-btn active" data-tool="cursor" title="Cursor / Select (Esc)">
        <span class="tool-icon">↖</span>
    </button>
    <div class="toolbar-divider"></div>
    <button type="button" class="drawing-tool-btn" data-tool="trendline" title="Trendline">
        <span class="tool-icon">╱</span>
    </button>
    <button type="button" class="drawing-tool-btn" data-tool="horizontal_ray" title="Horizontal Ray">
        <span class="tool-icon">─→</span>
    </button>
    <button type="button" class="drawing-tool-btn" data-tool="fibonacci" title="Fibonacci Retracement">
        <span class="tool-icon">≡</span>
    </button>
    <button type="button" class="drawing-tool-btn" data-tool="position_rr" title="Long/Short Risk-Reward Box">
        <span class="tool-icon">⚖</span>
    </button>
    <div class="toolbar-divider"></div>
    <button type="button" class="drawing-tool-btn" id="btn-toggle-magnet" data-tool="magnet" title="Magnet Mode (Snap to Candle OHLC)">
        <span class="tool-icon">🧲</span>
    </button>
    <button type="button" class="drawing-tool-btn btn-trash" id="btn-clear-drawings" title="Clear All Drawings">
        <span class="tool-icon">🗑</span>
    </button>
</div>
```

---

## 4. Coordinate Projection & Magnet Snap Mathematics

### 4.1 Domain Coordinates to Screen Pixels
Each drawing point is stored as:
$$\text{Point} = \{ t: \text{timestamp}, p: \text{price} \}$$

During render:
$$x = \text{chart.timeScale().timeToCoordinate}(t)$$
$$y = \text{candleSeries.priceToCoordinate}(p)$$

When the chart pans or zooms, the visible range changes. The engine subscribes to:
```javascript
chart.timeScale().subscribeVisibleTimeRangeChange(() => this.requestRender());
chart.timeScale().subscribeVisibleLogicalRangeChange(() => this.requestRender());
```

### 4.2 Magnet Snap Logic
When `magnetMode === true` and the user hovers or clicks at cursor $(x_m, y_m)$:
1. Find candle bar closest to $x_m$ using `chart.timeScale().coordinateToTime(x_m)`.
2. Inspect candle $O, H, L, C$ values.
3. Convert each to pixel Y: $y_O, y_H, y_L, y_C$.
4. Calculate Euclidean distance:
$$d = \min(|y_m - y_O|, |y_m - y_H|, |y_m - y_L|, |y_m - y_C|)$$
5. If $d \le 15\text{px}$, snap target coordinate to the closest price vertex.

---

## 5. Implementation Steps
1. Create `static/css/chart_drawings.css` with left floating glassmorphic toolbar and SVG canvas overlay styles.
2. Link `chart_drawings.css` and `chart_drawings.js` in `static/index.html`.
3. Create `static/js/chart_drawings.js`:
   - Initialize SVG overlay inside `#chart-container`.
   - Setup coordinate converters between Lightweight Charts and SVG canvas.
   - Implement Magnet Snap calculation.
   - Implement dual persistence: load from `localStorage`, fetch updates from `/api/v1/chart/drawings/{symbol}`, write through on change.
4. Create integration tests `tests/integration/test_drawing_overlay_integration.py`.

---

## 6. Verification & Acceptance Criteria
- Verify HTTP 200 on `Invoke-WebRequest -Uri http://localhost:8000/static/js/chart_drawings.js`.
- Verify `#chart-drawing-toolbar` renders on the left edge with all 7 buttons.
- Verify SVG drawing overlay covers chart container with pointer events handled properly.
- All integration tests pass.
