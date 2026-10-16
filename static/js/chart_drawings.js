/**
 * Interactive Chart Drawing Tools Suite
 * TradingView Institutional Standard - Left Floating Toolbar, Coordinate Projection,
 * Magnet OHLC Snap, Interactive Tools (Trendline, H-Ray, Fibonacci, Position R:R) & Micro-Toolbar
 */

// ==============================================================================
// 1. Core Tool Mathematical State Machines & Renderers
// ==============================================================================

class TrendlineTool {
    static get toolType() { return 'TRENDLINE'; }
    static get minPoints() { return 2; }

    static calculate(points, manager) {
        if (!points || points.length < 2) return null;
        const p1 = points[0];
        const p2 = points[1];
        const deltaPrice = p2.price - p1.price;
        const pct = p1.price ? ((deltaPrice / p1.price) * 100) : 0;

        // Angle in degrees in screen space
        const x1 = manager.timeToX(p1.time);
        const y1 = manager.priceToY(p1.price);
        const x2 = manager.timeToX(p2.time);
        const y2 = manager.priceToY(p2.price);
        let angle = 0;
        if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {
            angle = Math.round(Math.atan2(-(y2 - y1), (x2 - x1)) * (180 / Math.PI));
        }

        // Count bars if window.allLoadedCandles is available
        let barCount = 0;
        if (window.allLoadedCandles && Array.isArray(window.allLoadedCandles)) {
            const minT = Math.min(p1.time, p2.time);
            const maxT = Math.max(p1.time, p2.time);
            barCount = window.allLoadedCandles.filter(c => c.time >= minT && c.time <= maxT).length;
        }

        return { deltaPrice, pct, angle, barCount, x1, y1, x2, y2 };
    }

    static render(drawing, manager, isSelected = false, isPreview = false) {
        const points = drawing.points || [];
        if (points.length < 2) return '';
        const calc = this.calculate(points, manager);
        if (!calc || calc.x1 === null || calc.y1 === null || calc.x2 === null || calc.y2 === null) return '';

        const style = drawing.style || {};
        const strokeColor = style.color || '#2962FF';
        const strokeWidth = style.lineWidth || 2;
        const isDashed = isPreview || style.lineStyle === 1;
        const strokeDash = isDashed ? 'stroke-dasharray="4,4"' : '';
        const selectClass = isSelected ? 'selected' : '';

        const sign = calc.deltaPrice >= 0 ? '+' : '';
        const midX = (calc.x1 + calc.x2) / 2;
        const midY = (calc.y1 + calc.y2) / 2;

        let handlesHtml = '';
        if (isSelected && !isPreview) {
            handlesHtml = `
                <circle cx="${calc.x1}" cy="${calc.y1}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="0" />
                <circle cx="${calc.x2}" cy="${calc.y2}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="1" />
            `;
        }

        const barText = calc.barCount > 0 ? ` · ${calc.barCount} bars` : '';
        const labelText = `${sign}₹${calc.deltaPrice.toFixed(2)} (${sign}${calc.pct.toFixed(2)}%)${barText} · ${calc.angle}°`;
        const labelWidth = Math.max(120, labelText.length * 6.5 + 16);

        return `
            <g class="drawing-group ${selectClass}" data-drawing-id="${drawing.drawing_id || ''}">
                <line x1="${calc.x1}" y1="${calc.y1}" x2="${calc.x2}" y2="${calc.y2}" 
                      stroke="${strokeColor}" stroke-width="${strokeWidth}" ${strokeDash} 
                      class="drawing-element" data-drawing-id="${drawing.drawing_id || ''}" />
                <rect x="${midX - labelWidth / 2}" y="${midY - 18}" width="${labelWidth}" height="18" rx="4" 
                      fill="rgba(15, 20, 31, 0.88)" stroke="${strokeColor}" stroke-width="1" />
                <text x="${midX}" y="${midY - 5}" font-size="10" font-family="monospace" fill="#FFFFFF" text-anchor="middle">
                    ${labelText}
                </text>
                ${handlesHtml}
            </g>
        `;
    }
}

class HorizontalRayTool {
    static get toolType() { return 'HORIZONTAL_RAY'; }
    static get minPoints() { return 1; }

    static calculate(points, manager) {
        if (!points || points.length < 1) return null;
        const p1 = points[0];
        const x1 = manager.timeToX(p1.time);
        const y1 = manager.priceToY(p1.price);
        const width = (manager.container && manager.container.clientWidth) ? manager.container.clientWidth : 1200;
        return { p1, x1, y1, width };
    }

    static render(drawing, manager, isSelected = false, isPreview = false) {
        const points = drawing.points || [];
        if (points.length < 1) return '';
        const calc = this.calculate(points, manager);
        if (!calc || calc.x1 === null || calc.y1 === null) return '';

        const style = drawing.style || {};
        const strokeColor = style.color || '#2962FF';
        const strokeWidth = style.lineWidth || 2;
        const isDashed = isPreview || style.lineStyle === 1;
        const strokeDash = isDashed ? 'stroke-dasharray="4,4"' : '';
        const selectClass = isSelected ? 'selected' : '';

        let handlesHtml = '';
        if (isSelected && !isPreview) {
            handlesHtml = `<circle cx="${calc.x1}" cy="${calc.y1}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="0" />`;
        }

        const tagWidth = 78;
        const tagX = calc.width - tagWidth - 8;

        return `
            <g class="drawing-group ${selectClass}" data-drawing-id="${drawing.drawing_id || ''}">
                <line x1="${calc.x1}" y1="${calc.y1}" x2="${calc.width}" y2="${calc.y1}" 
                      stroke="${strokeColor}" stroke-width="${strokeWidth}" ${strokeDash} 
                      class="drawing-element" data-drawing-id="${drawing.drawing_id || ''}" />
                <rect x="${tagX}" y="${calc.y1 - 10}" width="${tagWidth}" height="20" rx="3" 
                      fill="#1E293B" stroke="${strokeColor}" stroke-width="1" />
                <text x="${tagX + tagWidth / 2}" y="${calc.y1 + 4}" font-size="10" font-family="monospace" fill="#F8FAFC" text-anchor="middle">
                    ₹${calc.p1.price.toFixed(2)}
                </text>
                ${handlesHtml}
            </g>
        `;
    }
}

class FibonacciTool {
    static get toolType() { return 'FIBONACCI'; }
    static get minPoints() { return 2; }

    static get RATIOS() {
        return [
            { r: 0.0, label: '0.0%', color: '#94A3B8' },
            { r: 0.236, label: '23.6%', color: '#F43F5E' },
            { r: 0.382, label: '38.2%', color: '#F59E0B' },
            { r: 0.500, label: '50.0%', color: '#10B981' },
            { r: 0.618, label: '61.8%', color: '#3B82F6' }, // Golden Ratio
            { r: 0.786, label: '78.6%', color: '#8B5CF6' },
            { r: 1.000, label: '100.0%', color: '#94A3B8' }
        ];
    }

    static calculate(points, manager) {
        if (!points || points.length < 2) return null;
        const p1 = points[0];
        const p2 = points[1];
        const deltaP = p2.price - p1.price;

        const x1 = manager.timeToX(p1.time);
        const y1 = manager.priceToY(p1.price);
        const x2 = manager.timeToX(p2.time);
        const y2 = manager.priceToY(p2.price);

        const startX = (x1 !== null && x2 !== null) ? Math.min(x1, x2) : null;
        const endX = (x1 !== null && x2 !== null) ? Math.max(x1, x2, (startX || 0) + 160) : null;

        const levels = this.RATIOS.map(item => {
            const levelPrice = p1.price + (deltaP * item.r);
            const y = manager.priceToY(levelPrice);
            return {
                ratio: item.r,
                label: item.label,
                color: item.color,
                price: levelPrice,
                y: y
            };
        });

        return { p1, p2, deltaP, x1, y1, x2, y2, startX, endX, levels };
    }

    static render(drawing, manager, isSelected = false, isPreview = false) {
        const points = drawing.points || [];
        if (points.length < 2) return '';
        const calc = this.calculate(points, manager);
        if (!calc || calc.startX === null || calc.endX === null || calc.y1 === null || calc.y2 === null) return '';

        const selectClass = isSelected ? 'selected' : '';

        // Translucent shaded bands between key Fibonacci zones:
        // 1. 23.6% - 38.2% (Warm Amber Tint)
        // 2. 38.2% - 61.8% (Golden Pocket Blue Tint)
        // 3. 61.8% - 78.6% (Purple Tint)
        let bandsHtml = '';
        const y236 = calc.levels[1].y;
        const y382 = calc.levels[2].y;
        const y618 = calc.levels[4].y;
        const y786 = calc.levels[5].y;

        if (y236 !== null && y382 !== null) {
            const topY = Math.min(y236, y382);
            const h = Math.abs(y236 - y382);
            bandsHtml += `<rect x="${calc.startX}" y="${topY}" width="${calc.endX - calc.startX}" height="${h}" fill="rgba(245, 158, 11, 0.08)" class="fib-band" />`;
        }
        if (y382 !== null && y618 !== null) {
            const topY = Math.min(y382, y618);
            const h = Math.abs(y382 - y618);
            bandsHtml += `<rect x="${calc.startX}" y="${topY}" width="${calc.endX - calc.startX}" height="${h}" fill="rgba(59, 130, 246, 0.12)" class="fib-band golden-pocket" />`;
        }
        if (y618 !== null && y786 !== null) {
            const topY = Math.min(y618, y786);
            const h = Math.abs(y618 - y786);
            bandsHtml += `<rect x="${calc.startX}" y="${topY}" width="${calc.endX - calc.startX}" height="${h}" fill="rgba(139, 92, 246, 0.08)" class="fib-band" />`;
        }

        let linesHtml = '';
        calc.levels.forEach(lvl => {
            if (lvl.y !== null) {
                linesHtml += `
                    <line x1="${calc.startX}" y1="${lvl.y}" x2="${calc.endX}" y2="${lvl.y}" 
                          stroke="${lvl.color}" stroke-width="1.2" stroke-dasharray="3,3" 
                          class="drawing-element" data-drawing-id="${drawing.drawing_id || ''}" />
                    <text x="${calc.startX + 6}" y="${lvl.y - 4}" font-size="9" font-family="monospace" fill="${lvl.color}">
                        ${lvl.label} (₹${lvl.price.toFixed(2)})
                    </text>
                `;
            }
        });

        let handlesHtml = '';
        if (isSelected && !isPreview) {
            handlesHtml = `
                <circle cx="${calc.x1}" cy="${calc.y1}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="0" />
                <circle cx="${calc.x2}" cy="${calc.y2}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="1" />
            `;
        }

        return `
            <g class="drawing-group ${selectClass}" data-drawing-id="${drawing.drawing_id || ''}">
                ${bandsHtml}
                ${linesHtml}
                ${handlesHtml}
            </g>
        `;
    }
}

class PositionRRTool {
    static get toolType() { return 'POSITION_RR'; }
    static get minPoints() { return 1; }

    static calculate(points, manager, style = {}) {
        if (!points || points.length < 1) return null;
        const entryPrice = points[0].price;
        const targetPrice = points.length > 1 ? points[1].price : (style.targetPrice || entryPrice * 1.03);
        const stopPrice = points.length > 2 ? points[2].price : (style.stopPrice || (entryPrice * 0.985));

        const x1 = manager.timeToX(points[0].time);
        const yEntry = manager.priceToY(entryPrice);
        const yTarget = manager.priceToY(targetPrice);
        const yStop = manager.priceToY(stopPrice);

        const x2 = points.length > 1 ? manager.timeToX(points[1].time) : null;
        const boxWidth = (x1 !== null && x2 !== null && Math.abs(x2 - x1) > 40) ? Math.abs(x2 - x1) : 180;
        const leftX = (x1 !== null && x2 !== null && x2 < x1) ? x2 : (x1 || 0);

        // Account & Risk Computations
        const capital = 100000; // ₹1,00,000 capital
        const riskAmount = 2000; // 2% max risk = ₹2,000
        const riskPerShare = Math.max(Math.abs(entryPrice - stopPrice), 0.05);
        const rewardPerShare = Math.abs(targetPrice - entryPrice);
        const rrRatio = (rewardPerShare / riskPerShare).toFixed(2);
        const positionSize = Math.max(1, Math.floor(riskAmount / riskPerShare));
        const projectedProfit = (positionSize * rewardPerShare).toFixed(2);
        const targetPct = entryPrice ? (((targetPrice - entryPrice) / entryPrice) * 100).toFixed(2) : '0.00';
        const stopPct = entryPrice ? (((stopPrice - entryPrice) / entryPrice) * 100).toFixed(2) : '0.00';

        return {
            entryPrice, targetPrice, stopPrice,
            x1, yEntry, yTarget, yStop, leftX, boxWidth,
            riskAmount, riskPerShare, rewardPerShare, rrRatio,
            positionSize, projectedProfit, targetPct, stopPct
        };
    }

    static render(drawing, manager, isSelected = false, isPreview = false) {
        const points = drawing.points || [];
        if (points.length < 1) return '';
        const calc = this.calculate(points, manager, drawing.style);
        if (!calc || calc.yEntry === null || calc.yTarget === null || calc.yStop === null || calc.x1 === null) return '';

        const selectClass = isSelected ? 'selected' : '';
        const targetTopY = Math.min(calc.yEntry, calc.yTarget);
        const targetH = Math.abs(calc.yEntry - calc.yTarget);
        const stopTopY = Math.min(calc.yEntry, calc.yStop);
        const stopH = Math.abs(calc.yEntry - calc.yStop);

        let handlesHtml = '';
        if (isSelected && !isPreview) {
            handlesHtml = `
                <circle cx="${calc.leftX}" cy="${calc.yEntry}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="0" title="Entry Handle" />
                <circle cx="${calc.leftX + calc.boxWidth}" cy="${calc.yTarget}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="1" title="Target Handle" />
                <circle cx="${calc.leftX}" cy="${calc.yStop}" r="5" class="drawing-handle" data-drawing-id="${drawing.drawing_id}" data-handle-index="2" title="Stop Loss Handle" />
            `;
        }

        return `
            <g class="drawing-group ${selectClass}" data-drawing-id="${drawing.drawing_id || ''}">
                <!-- Target Rectangle (Green) -->
                <rect x="${calc.leftX}" y="${targetTopY}" width="${calc.boxWidth}" height="${targetH}" 
                      fill="rgba(8, 153, 129, 0.22)" stroke="#089981" stroke-width="1" class="drawing-element" data-drawing-id="${drawing.drawing_id || ''}" />
                
                <!-- Stop Loss Rectangle (Red) -->
                <rect x="${calc.leftX}" y="${stopTopY}" width="${calc.boxWidth}" height="${stopH}" 
                      fill="rgba(242, 54, 69, 0.22)" stroke="#F23645" stroke-width="1" class="drawing-element" data-drawing-id="${drawing.drawing_id || ''}" />
                
                <!-- Central Blue Entry Line -->
                <line x1="${calc.leftX}" y1="${calc.yEntry}" x2="${calc.leftX + calc.boxWidth}" y2="${calc.yEntry}" 
                      stroke="#3B82F6" stroke-width="2" class="drawing-element" data-drawing-id="${drawing.drawing_id || ''}" />

                <!-- Text Badges -->
                <text x="${calc.leftX + 8}" y="${calc.yEntry - 5}" font-size="10" font-family="monospace" fill="#FFFFFF" font-weight="bold">
                    Entry: ₹${calc.entryPrice.toFixed(2)} | Qty: ${calc.positionSize}
                </text>
                <text x="${calc.leftX + 8}" y="${calc.yTarget + (calc.yTarget < calc.yEntry ? 14 : -5)}" font-size="10" font-family="monospace" fill="#089981" font-weight="bold">
                    Target: ₹${calc.targetPrice.toFixed(2)} (+${calc.targetPct}%) | Profit: ₹${calc.projectedProfit} | R:R 1:${calc.rrRatio}
                </text>
                <text x="${calc.leftX + 8}" y="${calc.yStop + (calc.yStop > calc.yEntry ? -5 : 14)}" font-size="10" font-family="monospace" fill="#F23645" font-weight="bold">
                    Stop: ₹${calc.stopPrice.toFixed(2)} (${calc.stopPct}%) | Risk: ₹${calc.riskAmount.toFixed(2)}
                </text>

                ${handlesHtml}
            </g>
        `;
    }
}

// ==============================================================================
// 2. ChartDrawingManager Engine
// ==============================================================================

class ChartDrawingManager {
    constructor() {
        this.activeTool = 'cursor';
        this.magnetMode = false;
        this.drawings = [];
        this.selectedDrawingId = null;
        this.inProgressDrawing = null;
        this.magnetSnapPoint = null;
        this.currentSymbol = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';

        this.container = null;
        this.svg = null;
        this.toolbar = null;
        this.microToolbar = null;
        this.renderPending = false;
        this.draggingState = null;

        this.init();
    }

    init() {
        this.container = document.getElementById('chart-container');
        if (!this.container) return;

        this.ensureToolbar();
        this.ensureSvgOverlay();
        this.ensureMicroToolbar();
        this.bindEvents();
        this.attachChartSubscriptions();
        this.loadDrawingsForSymbol(this.currentSymbol);
    }

    attachChartSubscriptions() {
        if (window.mainChart && window.mainChart.timeScale()) {
            try {
                window.mainChart.timeScale().subscribeVisibleLogicalRangeChange(() => this.requestRender());
                window.mainChart.timeScale().subscribeVisibleTimeRangeChange(() => this.requestRender());
            } catch (e) {}
        }
    }

    // --------------------------------------------------------------------------
    // DOM Hierarchy Setup
    // --------------------------------------------------------------------------
    ensureToolbar() {
        let tb = document.getElementById('chart-drawing-toolbar');
        if (!tb) {
            tb = document.createElement('aside');
            tb.id = 'chart-drawing-toolbar';
            tb.className = 'chart-drawing-toolbar';
            tb.setAttribute('aria-label', 'Chart Drawing Tools');
            tb.innerHTML = `
                <div class="toolbar-top-group">
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
                </div>
                <div class="toolbar-bottom-group">
                    <button type="button" class="drawing-tool-btn btn-trash" id="btn-clear-drawings" title="Clear All Drawings">
                        <span class="tool-icon">🗑</span>
                    </button>
                </div>
            `;

            const stage = (this.container && this.container.closest('.chart-stage')) ||
                          (this.container && this.container.closest('.chart-workspace')) ||
                          (this.container && this.container.parentElement) ||
                          this.container;
            if (stage && stage.firstChild) {
                stage.insertBefore(tb, stage.firstChild);
            } else if (stage) {
                stage.appendChild(tb);
            }
        }
        this.toolbar = tb;
    }

    ensureSvgOverlay() {
        let svgEl = document.getElementById('chart-drawings-svg');
        if (!svgEl) {
            svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svgEl.id = 'chart-drawings-svg';
            svgEl.setAttribute('class', 'chart-drawings-svg');
            svgEl.setAttribute('width', '100%');
            svgEl.setAttribute('height', '100%');
            this.container.appendChild(svgEl);
        }
        this.svg = svgEl;
    }

    ensureMicroToolbar() {
        let mt = document.getElementById('chart-drawing-micro-toolbar');
        if (!mt) {
            mt = document.createElement('div');
            mt.id = 'chart-drawing-micro-toolbar';
            mt.className = 'drawing-micro-toolbar';
            mt.innerHTML = `
                <div class="micro-colors">
                    <span class="micro-color-pill" data-color="#2962FF" style="background: #2962FF;" title="Blue"></span>
                    <span class="micro-color-pill" data-color="#10B981" style="background: #10B981;" title="Green"></span>
                    <span class="micro-color-pill" data-color="#F59E0B" style="background: #F59E0B;" title="Amber"></span>
                    <span class="micro-color-pill" data-color="#F43F5E" style="background: #F43F5E;" title="Red"></span>
                    <span class="micro-color-pill" data-color="#8B5CF6" style="background: #8B5CF6;" title="Purple"></span>
                    <span class="micro-color-pill" data-color="#06B6D4" style="background: #06B6D4;" title="Cyan"></span>
                </div>
                <div class="micro-divider"></div>
                <button type="button" class="micro-btn micro-width-btn" title="Cycle Line Width">2px</button>
                <button type="button" class="micro-btn micro-style-btn" title="Toggle Line Style (Solid/Dash)">—</button>
                <div class="micro-divider"></div>
                <button type="button" class="micro-btn micro-delete-btn" title="Delete Drawing (Del)">🗑</button>
            `;

            const parent = (this.container && this.container.closest('.chart-panes-wrapper')) ||
                           (this.container && this.container.closest('.chart-workspace')) ||
                           this.container;
            if (parent) parent.appendChild(mt);
        }
        this.microToolbar = mt;
    }

    // --------------------------------------------------------------------------
    // Event Binding
    // --------------------------------------------------------------------------
    bindEvents() {
        // Toolbar tool click delegation
        if (this.toolbar) {
            this.toolbar.addEventListener('click', (e) => {
                const btn = e.target.closest('.drawing-tool-btn');
                if (!btn) return;

                const tool = btn.dataset.tool;
                if (tool === 'magnet') {
                    this.toggleMagnet();
                } else if (btn.id === 'btn-clear-drawings') {
                    this.clearAll();
                } else if (tool) {
                    this.setTool(tool);
                }
            });
        }

        // Micro-toolbar delegation
        if (this.microToolbar) {
            this.microToolbar.addEventListener('click', (e) => {
                const drawing = this.drawings.find(d => d.drawing_id === this.selectedDrawingId);
                if (!drawing) return;

                const colorPill = e.target.closest('.micro-color-pill');
                if (colorPill && colorPill.dataset.color) {
                    drawing.style = drawing.style || {};
                    drawing.style.color = colorPill.dataset.color;
                    this.updateDrawing(drawing);
                    this.requestRender();
                    return;
                }

                const widthBtn = e.target.closest('.micro-width-btn');
                if (widthBtn) {
                    drawing.style = drawing.style || {};
                    const curW = drawing.style.lineWidth || 2;
                    const nextW = curW >= 3 ? 1 : curW + 1;
                    drawing.style.lineWidth = nextW;
                    widthBtn.textContent = `${nextW}px`;
                    this.updateDrawing(drawing);
                    this.requestRender();
                    return;
                }

                const styleBtn = e.target.closest('.micro-style-btn');
                if (styleBtn) {
                    drawing.style = drawing.style || {};
                    drawing.style.lineStyle = drawing.style.lineStyle === 1 ? 0 : 1;
                    styleBtn.textContent = drawing.style.lineStyle === 1 ? '- -' : '—';
                    this.updateDrawing(drawing);
                    this.requestRender();
                    return;
                }

                const delBtn = e.target.closest('.micro-delete-btn');
                if (delBtn) {
                    this.deleteDrawing(this.selectedDrawingId);
                }
            });
        }

        // SVG Canvas Mouse Events
        if (this.svg) {
            this.svg.addEventListener('mousedown', (e) => this.onMouseDown(e));
            this.svg.addEventListener('mousemove', (e) => this.onMouseMove(e));
            this.svg.addEventListener('mouseup', (e) => this.onMouseUp(e));
            this.svg.addEventListener('mouseleave', () => this.onMouseLeave());
        }

        // Global Keyboard shortcuts (Escape & Delete)
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.setTool('cursor');
                this.inProgressDrawing = null;
                this.selectedDrawingId = null;
                this.hideMicroToolbar();
                this.requestRender();
            } else if (e.key === 'Delete' || e.key === 'Backspace') {
                if (this.selectedDrawingId && !this.isInputFieldFocused()) {
                    this.deleteDrawing(this.selectedDrawingId);
                }
            }
        });
    }

    isInputFieldFocused() {
        const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        return tag === 'input' || tag === 'textarea' || tag === 'select';
    }

    // --------------------------------------------------------------------------
    // Tool Selection & State Management
    // --------------------------------------------------------------------------
    setTool(toolName) {
        this.activeTool = toolName;
        this.inProgressDrawing = null;

        if (this.toolbar) {
            this.toolbar.querySelectorAll('.drawing-tool-btn').forEach(btn => {
                if (btn.dataset.tool && btn.dataset.tool !== 'magnet' && btn.id !== 'btn-clear-drawings') {
                    btn.classList.toggle('active', btn.dataset.tool === toolName);
                }
            });
        }

        if (this.svg) {
            if (toolName !== 'cursor') {
                this.svg.classList.add('drawing-active');
                this.selectedDrawingId = null;
                this.hideMicroToolbar();
            } else {
                this.svg.classList.remove('drawing-active');
            }
        }
        this.requestRender();
    }

    toggleMagnet() {
        this.magnetMode = !this.magnetMode;
        const btn = document.getElementById('btn-toggle-magnet');
        if (btn) btn.classList.toggle('active', this.magnetMode);
        this.requestRender();
    }

    // --------------------------------------------------------------------------
    // Coordinate Projection Helpers
    // --------------------------------------------------------------------------
    timeToX(time) {
        if (!window.mainChart || !window.mainChart.timeScale()) return null;
        try {
            return window.mainChart.timeScale().timeToCoordinate(time);
        } catch (e) {
            return null;
        }
    }

    xToTime(x) {
        if (!window.mainChart || !window.mainChart.timeScale()) return null;
        try {
            return window.mainChart.timeScale().coordinateToTime(x);
        } catch (e) {
            return null;
        }
    }

    priceToY(price) {
        if (!window.candleSeries || typeof window.candleSeries.priceToCoordinate !== 'function') return null;
        try {
            return window.candleSeries.priceToCoordinate(price);
        } catch (e) {
            return null;
        }
    }

    yToPrice(y) {
        if (!window.candleSeries || typeof window.candleSeries.coordinateToPrice !== 'function') return null;
        try {
            return window.candleSeries.coordinateToPrice(y);
        } catch (e) {
            return null;
        }
    }

    // --------------------------------------------------------------------------
    // Magnet Snap Logic
    // --------------------------------------------------------------------------
    getMagnetPoint(mouseX, mouseY) {
        if (!this.magnetMode || !window.allLoadedCandles || window.allLoadedCandles.length === 0) {
            return null;
        }

        const time = this.xToTime(mouseX);
        if (!time) return null;

        let nearestCandle = null;
        let minTimeDiff = Infinity;

        for (const c of window.allLoadedCandles) {
            const diff = Math.abs(c.time - time);
            if (diff < minTimeDiff) {
                minTimeDiff = diff;
                nearestCandle = c;
            }
        }

        if (!nearestCandle) return null;

        const candleX = this.timeToX(nearestCandle.time);
        if (candleX === null) return null;

        const vertices = [
            { price: nearestCandle.high, y: this.priceToY(nearestCandle.high) },
            { price: nearestCandle.low, y: this.priceToY(nearestCandle.low) },
            { price: nearestCandle.close, y: this.priceToY(nearestCandle.close) },
            { price: nearestCandle.open, y: this.priceToY(nearestCandle.open) }
        ].filter(v => v.y !== null);

        let closestVertex = null;
        let minDist = 15; // 15px snap radius threshold

        for (const v of vertices) {
            const dist = Math.abs(mouseY - v.y);
            if (dist < minDist) {
                minDist = dist;
                closestVertex = v;
            }
        }

        if (closestVertex) {
            return {
                time: nearestCandle.time,
                price: closestVertex.price,
                x: candleX,
                y: closestVertex.y
            };
        }

        return null;
    }

    // --------------------------------------------------------------------------
    // Mouse Interaction Handlers
    // --------------------------------------------------------------------------
    onMouseDown(e) {
        const rect = this.svg.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // --- Mode 1: Cursor (Selection, Handle Dragging & Shape Translation) ---
        if (this.activeTool === 'cursor') {
            const handleEl = e.target.closest('.drawing-handle');
            if (handleEl && handleEl.dataset.drawingId) {
                const drawingId = handleEl.dataset.drawingId;
                const handleIdx = parseInt(handleEl.dataset.handleIndex, 10);
                const drawing = this.drawings.find(d => d.drawing_id === drawingId);

                if (drawing) {
                    this.selectedDrawingId = drawingId;
                    this.draggingState = {
                        type: 'handle',
                        drawingId: drawingId,
                        handleIndex: handleIdx
                    };
                    this.showMicroToolbar(drawing);
                    this.requestRender();
                    return;
                }
            }

            const groupEl = e.target.closest('.drawing-group, .drawing-element');
            if (groupEl && groupEl.dataset.drawingId) {
                const drawingId = groupEl.dataset.drawingId;
                const drawing = this.drawings.find(d => d.drawing_id === drawingId);

                if (drawing) {
                    this.selectedDrawingId = drawingId;
                    this.draggingState = {
                        type: 'object',
                        drawingId: drawingId,
                        startX: mouseX,
                        startY: mouseY,
                        startPoints: JSON.parse(JSON.stringify(drawing.points))
                    };
                    this.showMicroToolbar(drawing);
                    this.requestRender();
                    return;
                }
            }

            // Clicked background -> deselect
            if (this.selectedDrawingId) {
                this.selectedDrawingId = null;
                this.hideMicroToolbar();
                this.requestRender();
            }
            return;
        }

        // --- Mode 2: Active Drawing Tool ---
        const magnet = this.getMagnetPoint(mouseX, mouseY);
        let ptTime = magnet ? magnet.time : this.xToTime(mouseX);
        let ptPrice = magnet ? magnet.price : this.yToPrice(mouseY);

        if (!ptTime || ptPrice === null) return;

        const newPoint = { time: ptTime, price: Number(ptPrice.toFixed(2)) };

        if (!this.inProgressDrawing) {
            // Anchor 1
            this.inProgressDrawing = {
                tool_type: this.activeTool.toUpperCase(),
                points: [newPoint],
                style: {
                    color: '#2962FF',
                    lineWidth: 2,
                    lineStyle: 0
                }
            };

            // Single-click tools like Horizontal Ray complete immediately
            if (this.activeTool === 'horizontal_ray') {
                this.finalizeDrawing(this.inProgressDrawing);
                this.inProgressDrawing = null;
                this.setTool('cursor');
            }
        } else {
            // Anchor 2
            this.inProgressDrawing.points.push(newPoint);
            this.finalizeDrawing(this.inProgressDrawing);
            this.inProgressDrawing = null;
            this.setTool('cursor');
        }

        this.requestRender();
    }

    onMouseMove(e) {
        const rect = this.svg.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Magnet indicator
        this.magnetSnapPoint = this.getMagnetPoint(mouseX, mouseY);

        // Handle dragging state in Cursor mode
        if (this.draggingState) {
            const drawing = this.drawings.find(d => d.drawing_id === this.draggingState.drawingId);
            if (!drawing) return;

            if (this.draggingState.type === 'handle') {
                const ptTime = this.magnetSnapPoint ? this.magnetSnapPoint.time : this.xToTime(mouseX);
                const ptPrice = this.magnetSnapPoint ? this.magnetSnapPoint.price : this.yToPrice(mouseY);

                if (ptTime && ptPrice !== null) {
                    const handleIdx = this.draggingState.handleIndex;
                    if (drawing.tool_type === 'POSITION_RR' && handleIdx === 2) {
                        if (drawing.points.length > 2) {
                            drawing.points[2] = { time: ptTime, price: Number(ptPrice.toFixed(2)) };
                        } else if (drawing.points.length === 2) {
                            drawing.points.push({ time: ptTime, price: Number(ptPrice.toFixed(2)) });
                        } else {
                            drawing.style = drawing.style || {};
                            drawing.style.stopPrice = Number(ptPrice.toFixed(2));
                        }
                    } else {
                        drawing.points[handleIdx] = { time: ptTime, price: Number(ptPrice.toFixed(2)) };
                    }
                    this.updateMicroToolbarPosition(drawing);
                    this.requestRender();
                }
            } else if (this.draggingState.type === 'object') {
                const deltaX = mouseX - this.draggingState.startX;
                const deltaY = mouseY - this.draggingState.startY;

                for (let i = 0; i < this.draggingState.startPoints.length; i++) {
                    const orig = this.draggingState.startPoints[i];
                    const curX = this.timeToX(orig.time) + deltaX;
                    const curY = this.priceToY(orig.price) + deltaY;

                    const newTime = this.xToTime(curX);
                    const newPrice = this.yToPrice(curY);

                    if (newTime && newPrice !== null) {
                        drawing.points[i] = { time: newTime, price: Number(newPrice.toFixed(2)) };
                    }
                }
                this.updateMicroToolbarPosition(drawing);
                this.requestRender();
            }
            return;
        }

        // Rubber-band preview for in-progress drawing creation
        if (this.inProgressDrawing && this.inProgressDrawing.points.length > 0) {
            const ptTime = this.magnetSnapPoint ? this.magnetSnapPoint.time : this.xToTime(mouseX);
            const ptPrice = this.magnetSnapPoint ? this.magnetSnapPoint.price : this.yToPrice(mouseY);

            if (ptTime && ptPrice !== null) {
                this.inProgressPreviewPoint = { time: ptTime, price: Number(ptPrice.toFixed(2)) };
            }
        }

        this.requestRender();
    }

    onMouseUp(e) {
        if (this.draggingState) {
            const drawing = this.drawings.find(d => d.drawing_id === this.draggingState.drawingId);
            if (drawing) {
                this.updateDrawing(drawing);
            }
            this.draggingState = null;
            this.requestRender();
        }
    }

    onMouseLeave() {
        this.magnetSnapPoint = null;
        if (this.draggingState) {
            const drawing = this.drawings.find(d => d.drawing_id === this.draggingState.drawingId);
            if (drawing) {
                this.updateDrawing(drawing);
            }
            this.draggingState = null;
        }
        this.requestRender();
    }

    // --------------------------------------------------------------------------
    // Floating Micro-Toolbar Management
    // --------------------------------------------------------------------------
    showMicroToolbar(drawing) {
        if (!this.microToolbar || !drawing) return;
        this.microToolbar.style.display = 'flex';
        this.updateMicroToolbarPosition(drawing);

        // Sync button states
        const widthBtn = this.microToolbar.querySelector('.micro-width-btn');
        if (widthBtn) {
            widthBtn.textContent = `${drawing.style && drawing.style.lineWidth ? drawing.style.lineWidth : 2}px`;
        }
        const styleBtn = this.microToolbar.querySelector('.micro-style-btn');
        if (styleBtn) {
            styleBtn.textContent = (drawing.style && drawing.style.lineStyle === 1) ? '- -' : '—';
        }
    }

    hideMicroToolbar() {
        if (this.microToolbar) {
            this.microToolbar.style.display = 'none';
        }
    }

    updateMicroToolbarPosition(drawing) {
        if (!this.microToolbar || !drawing || !this.container) return;

        const points = drawing.points || [];
        if (points.length === 0) return;

        let avgX = 0;
        let minY = Infinity;
        let validPoints = 0;

        for (const pt of points) {
            const px = this.timeToX(pt.time);
            const py = this.priceToY(pt.price);
            if (px !== null && py !== null) {
                avgX += px;
                minY = Math.min(minY, py);
                validPoints++;
            }
        }

        if (validPoints === 0 || minY === Infinity) return;
        avgX = avgX / validPoints;

        // Clamp within container
        const contW = this.container.clientWidth;
        const contH = this.container.clientHeight;

        avgX = Math.max(80, Math.min(contW - 80, avgX));
        minY = Math.max(30, Math.min(contH - 20, minY));

        this.microToolbar.style.left = `${avgX}px`;
        this.microToolbar.style.top = `${minY}px`;
    }

    // --------------------------------------------------------------------------
    // Dual Persistence (LocalStorage + DuckDB REST API)
    // --------------------------------------------------------------------------
    async loadDrawingsForSymbol(symbol) {
        this.currentSymbol = symbol || this.currentSymbol;
        const cacheKey = `drawings_${this.currentSymbol}`;

        // 1. Instant local load
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
            try {
                this.drawings = JSON.parse(cached);
                this.requestRender();
            } catch (e) {
                this.drawings = [];
            }
        }

        // 2. Background sync with backend
        try {
            const res = await fetch(`/api/v1/chart/drawings/${encodeURIComponent(this.currentSymbol)}`);
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.data)) {
                    this.drawings = data.data;
                    localStorage.setItem(cacheKey, JSON.stringify(this.drawings));
                    this.requestRender();
                }
            }
        } catch (e) {
            console.warn('Could not sync drawings with backend:', e);
        }
    }

    async finalizeDrawing(drawingObj) {
        drawingObj.drawing_id = 'draw_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
        drawingObj.symbol = this.currentSymbol;

        this.drawings.push(drawingObj);
        const cacheKey = `drawings_${this.currentSymbol}`;
        localStorage.setItem(cacheKey, JSON.stringify(this.drawings));

        try {
            const res = await fetch(`/api/v1/chart/drawings/${encodeURIComponent(this.currentSymbol)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tool_type: drawingObj.tool_type,
                    points: drawingObj.points,
                    style: drawingObj.style
                })
            });
            if (res.ok) {
                const saved = await res.json();
                if (saved.success && saved.data && saved.data.drawing_id) {
                    drawingObj.drawing_id = saved.data.drawing_id;
                    localStorage.setItem(cacheKey, JSON.stringify(this.drawings));
                }
            }
        } catch (e) {
            console.warn('Failed to save drawing to backend:', e);
        }

        this.requestRender();
    }

    async updateDrawing(drawing) {
        const cacheKey = `drawings_${this.currentSymbol}`;
        localStorage.setItem(cacheKey, JSON.stringify(this.drawings));

        try {
            await fetch(`/api/v1/chart/drawings/${encodeURIComponent(drawing.drawing_id)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    points: drawing.points,
                    style: drawing.style
                })
            });
        } catch (e) {
            console.warn('Failed to update drawing on backend:', e);
        }
    }

    async deleteDrawing(drawingId) {
        this.drawings = this.drawings.filter(d => d.drawing_id !== drawingId);
        if (this.selectedDrawingId === drawingId) {
            this.selectedDrawingId = null;
            this.hideMicroToolbar();
        }

        const cacheKey = `drawings_${this.currentSymbol}`;
        localStorage.setItem(cacheKey, JSON.stringify(this.drawings));

        try {
            await fetch(`/api/v1/chart/drawings/${encodeURIComponent(drawingId)}`, {
                method: 'DELETE'
            });
        } catch (e) {
            console.warn('Failed to delete drawing from backend:', e);
        }

        this.requestRender();
    }

    async clearAll() {
        if (!confirm(`Clear all drawing annotations for ${this.currentSymbol}?`)) return;

        this.drawings = [];
        this.selectedDrawingId = null;
        this.inProgressDrawing = null;
        this.hideMicroToolbar();

        const cacheKey = `drawings_${this.currentSymbol}`;
        localStorage.removeItem(cacheKey);

        try {
            await fetch(`/api/v1/chart/drawings/${encodeURIComponent(this.currentSymbol)}/all`, {
                method: 'DELETE'
            });
        } catch (e) {
            console.warn('Failed to clear drawings on backend:', e);
        }

        this.requestRender();
    }

    // --------------------------------------------------------------------------
    // Lifecycle Hooks
    // --------------------------------------------------------------------------
    onSymbolOrCandlesChanged(symbol) {
        if (symbol && symbol !== this.currentSymbol) {
            this.currentSymbol = symbol;
            this.hideMicroToolbar();
            this.loadDrawingsForSymbol(symbol);
        } else {
            this.requestRender();
        }
    }

    handleResize() {
        if (this.selectedDrawingId) {
            const d = this.drawings.find(x => x.drawing_id === this.selectedDrawingId);
            if (d) this.updateMicroToolbarPosition(d);
        }
        this.requestRender();
    }

    requestRender() {
        if (this.renderPending) return;
        this.renderPending = true;
        requestAnimationFrame(() => {
            this.render();
            this.renderPending = false;
        });
    }

    // --------------------------------------------------------------------------
    // SVG Rendering Pipeline
    // --------------------------------------------------------------------------
    render() {
        if (!this.svg) return;

        let svgHtml = '';

        // 1. Render finalized drawings
        for (const d of this.drawings) {
            svgHtml += this.renderDrawingObject(d, d.drawing_id === this.selectedDrawingId);
        }

        // 2. Render in-progress preview
        if (this.inProgressDrawing && this.inProgressPreviewPoint) {
            const previewObj = {
                ...this.inProgressDrawing,
                points: [...this.inProgressDrawing.points, this.inProgressPreviewPoint]
            };
            svgHtml += this.renderDrawingObject(previewObj, false, true);
        }

        // 3. Render magnet snap indicator
        if (this.magnetSnapPoint) {
            svgHtml += `
                <circle cx="${this.magnetSnapPoint.x}" cy="${this.magnetSnapPoint.y}" class="magnet-snap-indicator" />
            `;
        }

        this.svg.innerHTML = svgHtml;
    }

    renderDrawingObject(d, isSelected = false, isPreview = false) {
        const type = (d.tool_type || '').toUpperCase();
        if (type === 'TRENDLINE') return TrendlineTool.render(d, this, isSelected, isPreview);
        if (type === 'HORIZONTAL_RAY') return HorizontalRayTool.render(d, this, isSelected, isPreview);
        if (type === 'FIBONACCI') return FibonacciTool.render(d, this, isSelected, isPreview);
        if (type === 'POSITION_RR') return PositionRRTool.render(d, this, isSelected, isPreview);
        return '';
    }
}

// Register modular tools onto ChartDrawingManager
ChartDrawingManager.tools = {
    Trendline: TrendlineTool,
    HorizontalRay: HorizontalRayTool,
    Fibonacci: FibonacciTool,
    PositionRR: PositionRRTool
};

// Global exports & static delegates
window.ChartDrawingManager = ChartDrawingManager;

ChartDrawingManager.setTool = function(toolName) {
    if (window.chartDrawingManager) return window.chartDrawingManager.setTool(toolName);
};

ChartDrawingManager.toggleMagnet = function() {
    if (window.chartDrawingManager) return window.chartDrawingManager.toggleMagnet();
};

ChartDrawingManager.clearAll = function() {
    if (window.chartDrawingManager) return window.chartDrawingManager.clearAll();
};

document.addEventListener('DOMContentLoaded', () => {
    window.chartDrawingManager = new ChartDrawingManager();
});
