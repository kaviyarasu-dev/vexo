# Requirements Document: Interactive Chart Drawing Tools Suite

## 1. Overview & Business Value
Quantitative and technical traders on Indian markets (NSE/BSE) rely extensively on visual chart markings to identify support/resistance levels, trend channels, Fibonacci retracements, and risk-to-reward ratios before placing orders. Currently, the charting workspace in the NSE Quant Platform offers Lightweight Charts with indicators and candlestick markers, but lacks an interactive drawing toolbar.

This feature introduces a TradingView-standard Interactive Drawing Tools Suite directly inside the charting canvas, with a sleek left vertical floating toolbar, reactive coordinate conversion, magnet snap, interactive drag handles, and dual persistence (instant LocalStorage caching + permanent DuckDB backend storage).

---

## 2. User Stories & Functional Requirements

### User Story 1: Left Vertical Floating Toolbar
- **As a** trader,
- **I want** a dedicated vertical floating toolbar on the left edge of the chart,
- **So that** I can easily toggle drawing tools, magnet mode, and clear drawings without obscuring the chart.
- **Acceptance Criteria**:
  - Toolbar contains icons for: Cursor/Select, Trendline, Horizontal Ray, Fibonacci Retracement, Long/Short Position Box, Magnet Mode Toggle, and Clear/Trash.
  - Active tool is highlighted with an institutional cyan/indigo glow.
  - Keyboard shortcut `Esc` resets active tool back to Cursor/Select mode.

### User Story 2: 5-Tool Core Institutional Suite
- **As a** technical quant,
- **I want** five core technical drawing tools:
  1. **Trendline**: Click two anchor points to draw a straight line. Displays delta price (₹), percentage change (%), and bar count / angle.
  2. **Horizontal Ray**: Click an anchor point to project an infinite horizontal support/resistance ray to the right edge with a price tag pill on the price axis.
  3. **Fibonacci Retracement**: Click high and low pivots to project institutional Fibonacci ratio levels (`0.0%`, `23.6%`, `38.2%`, `50.0%`, `61.8%`, `78.6%`, `100.0%`) with translucent shaded bands and price labels.
  4. **Long/Short Position Risk-Reward Box**: Click entry to project a 3-part box: Entry line, Green Target zone with target price and % gain, and Red Stop-Loss zone with stop price and % loss. Displays exact computed Risk-to-Reward ratio (e.g., `1:2.50`) and risk in ₹.
  5. **Magnet Snap Mode**: When enabled, drawing clicks snap automatically to the nearest candle High, Low, Open, or Close price within a 15-pixel radius.

### User Story 3: Interactive Editing & Selection
- **As a** trader,
- **I want** to select and modify drawings after they have been placed,
- **So that** I can adjust levels as price evolves.
- **Acceptance Criteria**:
  - Clicking any drawing highlights it and displays circular drag handles at its anchor vertices.
  - Dragging a vertex repositions that anchor point in real-time.
  - Dragging the body of the drawing translates the entire shape.
  - Selecting a drawing displays a mini floating action toolbar allowing color changes, stroke width adjustments, and deletion.
  - Pressing `Delete` or `Backspace` deletes the selected drawing.

### User Story 4: Dual Persistence (LocalStorage + DuckDB REST API)
- **As a** trader,
- **I want** drawings to be saved automatically per symbol,
- **So that** when I switch between stocks (e.g. `NSE:RELIANCE-EQ` to `NSE:TCS-EQ`) and return, my drawings are preserved.
- **Acceptance Criteria**:
  - Drawings are cached in `localStorage` under `drawings_{symbol}` for immediate 0ms load.
  - Drawings are synced to DuckDB table `chart_drawings` via REST API `/api/v1/chart/drawings/{symbol}`.
  - Switching symbols automatically saves current drawings and loads the destination symbol's drawings.
  - "Clear All" prompts confirmation and removes drawings for the current symbol from both LocalStorage and DuckDB.

---

## 3. Technical Constraints & Architecture

1. **Lightweight Charts Coordinate Mapping**:
   - The drawing engine renders on an absolute SVG/HTML5 Canvas layer overlaid exactly over `#chart-container`.
   - Anchors are stored in logical domain coordinates: `{ time: number | string, price: number }`.
   - Screen pixel coordinates `(x, y)` are computed using:
     - `x = chart.timeScale().timeToCoordinate(time)`
     - `y = candleSeries.priceToCoordinate(price)`
   - Subscribed to `chart.timeScale().subscribeVisibleTimeRangeChange()` and `chart.timeScale().subscribeVisibleLogicalRangeChange()` to re-render at 60 FPS during chart panning and zooming.

2. **DuckDB Concurrency & Database Table**:
   - Table `chart_drawings` in DuckDB:
     - `drawing_id VARCHAR PRIMARY KEY`
     - `symbol VARCHAR NOT NULL`
     - `tool_type VARCHAR NOT NULL` (TRENDLINE, HORIZONTAL_RAY, FIBONACCI, POSITION_RR)
     - `points JSON NOT NULL`
     - `style JSON NOT NULL`
     - `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
     - `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
   - Read queries use independent cursor `db.get_read_cursor()`.
   - Write mutations use `db.execute_write_batch()`.

---

## 4. Test Strategy
- **Unit Tests**:
  - Service tests for `ChartDrawingService` CRUD operations in DuckDB.
  - Coordinate projection mathematics and Fibonacci ratio computations.
  - Risk-to-Reward ratio calculations.
- **Integration Tests**:
  - REST API tests for `/api/v1/chart/drawings/{symbol}` endpoints.
  - Static asset serving for `chart_drawings.js` and `chart_drawings.css`.
  - DOM contract tests verifying presence and layout of drawing toolbar and overlay canvas.
