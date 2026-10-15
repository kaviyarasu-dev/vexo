# Plan 03-001: Interactive Tools Implementation: Trendline, H-Ray, Fibonacci & Long/Short R:R Box

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "01-database-and-api/001-database-and-api.md"
    - "02-toolbar-and-overlay/001-toolbar-and-overlay.md"
  reads:
    - "static/js/chart_drawings.js"
    - "static/css/chart_drawings.css"
    - "static/js/chart.js"
  produces:
    - "static/js/chart_drawings.js"
    - "static/css/chart_drawings.css"
    - "tests/integration/test_chart_drawing_tools_suite.py"
  exposes:
    - "ChartDrawingManager.tools.Trendline"
    - "ChartDrawingManager.tools.HorizontalRay"
    - "ChartDrawingManager.tools.Fibonacci"
    - "ChartDrawingManager.tools.PositionRR"
  must_not_modify:
    - "core/interfaces.py"
    - "db/connection.py"
  test_plan:
    - "pytest tests/integration/test_chart_drawing_tools_suite.py -v"
  definition_of_done:
    - "Trendline renders with delta price, percentage move and angle indicator"
    - "Horizontal Ray renders infinite right line with interactive price tag pill"
    - "Fibonacci Retracement projects institutional levels (0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%) with shaded bands"
    - "Long/Short Position Box calculates Target, Stop Loss, Risk-to-Reward ratio (e.g. 1:2.5) and risk in ₹"
    - "Selecting any drawing renders circular drag handles allowing vertex adjustment and shape dragging"
    - "Floating micro-toolbar permits instant color, width adjustment, and deletion"
  failure_modes_and_recovery:
    - "Zero division in Risk-Reward calculation -> guard with min threshold (stopLoss != entryPrice)"
    - "Drag handle offscreen -> clamp handles within visible chart viewport"
  handoff:
    - "Completes the Interactive Chart Drawing Tools Suite feature"
```

---

## 1. Goal & Scope / User Jobs Served
Implement the interactive mathematical state machines and rendering logic for the four core technical drawing tools: Trendline, Horizontal Ray, Fibonacci Retracement, and Long/Short Position Risk-Reward Box. Provide full interactive selection, vertex drag handles, drag-to-move translation, and a floating micro-toolbar for rapid styling.

---

## 2. Architecture & SOLID Principles Application
- **Single Responsibility Principle (SRP):**
  - Each tool is modeled as an independent class (`TrendlineTool`, `HorizontalRayTool`, `FibonacciTool`, `PositionRRTool`) inheriting from `BaseDrawingTool`.
  - Base class manages selection state, drag handle hit-testing, and coordinate normalization.
- **Open/Closed Principle (OCP):**
  - New drawing tools can be plugged in by defining `createPoint(point)`, `render(ctx, isSelected)`, and `getHandles()`.

---

## 3. Mathematical Specifications of Drawing Tools

### 3.1 Trendline
Given anchor points $A(t_1, p_1)$ and $B(t_2, p_2)$ mapped to pixel coordinates $(x_1, y_1)$ and $(x_2, y_2)$:
- $\Delta\text{Price} = p_2 - p_1$
- $\% \text{Change} = \frac{p_2 - p_1}{p_1} \times 100$
- $\text{Angle} = \text{atan2}(-(y_2 - y_1), x_2 - x_1) \times \frac{180}{\pi}$
- Render line segment with middle label pill displaying: `+₹12.50 (+1.45%) 14 bars`.

### 3.2 Horizontal Ray
Given anchor point $A(t_1, p_1)$ mapped to $(x_1, y_1)$ and canvas width $W$:
- Line extends horizontally from $x_1$ to $W$ at fixed $y = y_1$.
- Price tag pill rendered on the right edge displaying `₹p_1.toFixed(2)` with dark background badge.

### 3.3 Fibonacci Retracement
Given swing high and swing low pivots $(t_1, p_{\text{start}})$ and $(t_2, p_{\text{end}})$:
$$\Delta P = p_{\text{end}} - p_{\text{start}}$$
Standard Institutional Ratios:
- $0.0\%: p_{\text{start}}$
- $23.6\%: p_{\text{start}} + 0.236 \times \Delta P$
- $38.2\%: p_{\text{start}} + 0.382 \times \Delta P$
- $50.0\%: p_{\text{start}} + 0.500 \times \Delta P$
- $61.8\%: p_{\text{start}} + 0.618 \times \Delta P$ (Golden Ratio)
- $78.6\%: p_{\text{start}} + 0.786 \times \Delta P$
- $100.0\%: p_{\text{end}}$

Render horizontal lines across the time span $x_1 \to x_2$ with translucent colored fill bands between key zones (e.g., $38.2\% - 61.8\%$ golden pocket shaded in subtle green/gold).

### 3.4 Long / Short Risk-Reward Projection Tool
Given:
- Entry Price $P_E$
- Target Price $P_T$
- Stop Loss Price $P_S$
- Default Account Capital $C = 1,00,000$, Max Risk $\text{Pct} = 2.0\%$ ($\text{Risk Amount} = ₹2,000$)

Computations:
- $\text{Risk per share} = |P_E - P_S|$
- $\text{Reward per share} = |P_T - P_E|$
- $\text{Risk-to-Reward Ratio} = \frac{\text{Reward per share}}{\text{Risk per share}}$
- $\text{Position Size} = \lfloor \frac{\text{Risk Amount}}{\text{Risk per share}} \rfloor$
- $\text{Total Projected Profit} = \text{Position Size} \times \text{Reward per share}$

Visual Rendering:
- Central blue entry line.
- Translucent green box above entry line extending to Target Price, displaying:
  `Target: ₹P_T (+X.X%) | Profit: ₹ProjProfit | R:R 1:R_val`.
- Translucent red box below entry line extending to Stop Loss Price, displaying:
  `Stop: ₹P_S (-Y.Y%) | Risk: ₹RiskAmount`.

---

## 4. Selection, Drag Handles & Micro-Toolbar

1. **Vertex Handles**:
   - Small circular dots (radius = 5px, white fill, blue border) rendered at each anchor point when a drawing is selected.
   - Mouse down on a handle enters `DRAGGING_HANDLE` mode, updating that single vertex coordinate.
   - Mouse down inside the drawing body enters `DRAGGING_OBJECT` mode, applying $(\Delta x, \Delta y)$ to all points.
2. **Floating Micro-Toolbar**:
   - Appears centered above the selected drawing.
   - Contains:
     - Color Picker dropdown (Indigo, Cyan, Green, Amber, Red, Purple).
     - Line Width selector (`1px`, `2px`, `3px`).
     - Line Style toggle (Solid, Dashed).
     - Delete button.
3. **Keyboard Controls**:
   - `Delete` / `Backspace`: Deletes selected drawing.
   - `Escape`: Deselects active drawing and resets tool to Cursor mode.

---

## 5. Implementation Steps
1. In `static/js/chart_drawings.js`:
   - Implement `TrendlineTool`, `HorizontalRayTool`, `FibonacciTool`, `PositionRRTool`.
   - Implement selection collision detection and vertex handle dragging.
   - Implement the floating micro-toolbar DOM and event listeners.
   - Implement keyboard listener (`Delete`, `Backspace`, `Escape`).
2. In `static/css/chart_drawings.css`:
   - Add styles for drag handles, labels, shaded zones, and floating micro-toolbar.
3. Hook `ChartDrawingManager` into `chart.js` symbol changing workflow to auto-load drawings on symbol switch.
4. Author comprehensive integration test `tests/integration/test_chart_drawing_tools_suite.py`.

---

## 6. Verification & Acceptance Criteria
- Run `pytest tests/integration/test_chart_drawing_tools_suite.py -v`.
- Verify Trendline, Horizontal Ray, Fibonacci, and Position R:R Box render and calculate metrics correctly.
- Verify vertex handle manipulation and micro-toolbar styling.
- Verify dual persistence correctly preserves drawings across symbol changes.
