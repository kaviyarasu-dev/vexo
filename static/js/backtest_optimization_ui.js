/**
 * backtest_optimization_ui.js
 * Strategy Parameter Optimization 2D Heatmap Grid, 3x3 Plateau Stability Index HUD,
 * and Walk-Forward Validation Controller.
 */

class BacktestOptimizationController {
    constructor(backtestUI) {
        this.ui = backtestUI;
        this.presets = [];
        this.currentPreset = null;
        this.lastOptimizationResult = null;
        this.activeMetric = 'sharpe_ratio';
        this.selectedCell = null;
        this.isLoading = false;

        this.init();
    }

    /**
     * Initializes listeners, loads presets, and hooks into Backtest Studio.
     */
    async init() {
        this.bindSubtabs();
        this.bindStrategySelector();
        this.bindPresetChips();
        this.bindRangeInputs();
        this.bindSplitSlider();
        this.bindMetricSwitcher();
        this.bindRunButton();
        this.bindApplyButton();
        await this.loadPresets();
    }

    /**
     * Binds subtab switching between Single-Stock, Portfolio, and 2D Optimization.
     */
    bindSubtabs() {
        const btnOptimize = document.getElementById('btn-backtest-tab-optimize');
        if (btnOptimize) {
            btnOptimize.addEventListener('click', () => {
                this.activateOptimizeTab();
            });
        }
    }

    /**
     * Activates the 2D Parameter Optimization Studio view.
     */
    activateOptimizeTab() {
        if (this.ui && this.ui.activeMode !== 'optimize' && typeof this.ui.switchMode === 'function') {
            this.ui.switchMode('optimize');
        }

        // Synchronize inputs from Single-Stock Backtest Studio if available
        if (this.ui) {
            const sym = this.ui.currentSymbol || (this.ui.config && this.ui.config.symbol);
            if (sym) {
                const symInput = document.getElementById('opt-symbol-input');
                if (symInput) symInput.value = sym;
            }

            const strat = this.ui.activeStrategy;
            if (strat) {
                this.syncStrategy(strat);
            }
        }
    }

    /**
     * Deactivates the Optimization Studio view when navigating away.
     */
    deactivateOptimizeTab(targetMode = 'single') {
        if (this.ui && typeof this.ui.switchMode === 'function') {
            this.ui.switchMode(targetMode || 'single');
        }
    }

    /**
     * Fetches curated presets from the backend API.
     */
    async loadPresets() {
        try {
            const response = await fetch('/api/v1/backtest/optimize/presets');
            if (!response.ok) return;
            const data = await response.json();
            if (data && data.success && Array.isArray(data.presets)) {
                this.presets = data.presets;
                const strat = (this.ui && this.ui.activeStrategy) || 'SMA_CROSS';
                this.syncStrategy(strat);
            }
        } catch (e) {
            console.warn('[OptimizationStudio] Presets load failed:', e);
        }
    }

    /**
     * Binds strategy dropdown changes.
     */
    bindStrategySelector() {
        const select = document.getElementById('opt-strategy-select');
        if (!select) return;
        select.addEventListener('change', (e) => {
            this.syncStrategy(e.target.value);
        });
    }

    /**
     * Binds preset quick-select chip clicks.
     */
    bindPresetChips() {
        const container = document.querySelector('.opt-presets-bar');
        if (!container) return;
        container.querySelectorAll('.opt-preset-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                const presetStrategy = e.currentTarget.dataset.strategyPreset;
                if (presetStrategy) {
                    this.syncStrategy(presetStrategy);
                }
            });
        });
    }

    /**
     * Synchronizes UI inputs with preset ranges for selected strategy.
     */
    syncStrategy(stratKey) {
        const select = document.getElementById('opt-strategy-select');
        if (select && select.value !== stratKey) {
            select.value = stratKey;
        }

        // Update active chip
        document.querySelectorAll('.opt-preset-chip').forEach(c => {
            c.classList.toggle('active', c.dataset.strategyPreset === stratKey);
        });

        // Find preset
        const preset = this.presets.find(p => p.strategy === stratKey);
        if (!preset) return;
        this.currentPreset = preset;

        // Update badge
        const badge = document.getElementById('opt-active-strategy-badge');
        if (badge) badge.textContent = `Strategy: ${preset.label}`;

        // Param 1
        const p1Name = document.getElementById('opt-param1-name');
        const p1Min = document.getElementById('opt-param1-min');
        const p1Max = document.getElementById('opt-param1-max');
        const p1Step = document.getElementById('opt-param1-step');
        if (p1Name) p1Name.textContent = preset.param1.name;
        if (p1Min) p1Min.value = preset.param1.min_val;
        if (p1Max) p1Max.value = preset.param1.max_val;
        if (p1Step) p1Step.value = preset.param1.step;

        // Param 2
        const p2Name = document.getElementById('opt-param2-name');
        const p2Min = document.getElementById('opt-param2-min');
        const p2Max = document.getElementById('opt-param2-max');
        const p2Step = document.getElementById('opt-param2-step');
        if (p2Name) p2Name.textContent = preset.param2.name;
        if (p2Min) p2Min.value = preset.param2.min_val;
        if (p2Max) p2Max.value = preset.param2.max_val;
        if (p2Step) p2Step.value = preset.param2.step;

        this.updateCombinationCount();
    }

    /**
     * Binds input change events to update the combination counter.
     */
    bindRangeInputs() {
        const inputIds = [
            'opt-param1-min', 'opt-param1-max', 'opt-param1-step',
            'opt-param2-min', 'opt-param2-max', 'opt-param2-step'
        ];
        inputIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => this.updateCombinationCount());
            }
        });
    }

    /**
     * Calculates and displays total Cartesian combinations.
     */
    updateCombinationCount() {
        const p1Min = parseFloat(document.getElementById('opt-param1-min')?.value || 0);
        const p1Max = parseFloat(document.getElementById('opt-param1-max')?.value || 0);
        const p1Step = parseFloat(document.getElementById('opt-param1-step')?.value || 1);

        const p2Min = parseFloat(document.getElementById('opt-param2-min')?.value || 0);
        const p2Max = parseFloat(document.getElementById('opt-param2-max')?.value || 0);
        const p2Step = parseFloat(document.getElementById('opt-param2-step')?.value || 1);

        let t1 = 0;
        let t2 = 0;
        if (p1Step > 0 && p1Max >= p1Min) {
            t1 = Math.floor((p1Max - p1Min) / p1Step + 1e-9) + 1;
        }
        if (p2Step > 0 && p2Max >= p2Min) {
            t2 = Math.floor((p2Max - p2Min) / p2Step + 1e-9) + 1;
        }

        const total = t1 * t2;
        const countEl = document.getElementById('opt-comb-count');
        const badge = document.getElementById('opt-combinations-badge');
        const runBtn = document.getElementById('btn-run-optimization');
        const banner = document.getElementById('opt-alert-banner');
        const bannerMsg = document.getElementById('opt-alert-msg');

        if (countEl) countEl.textContent = total;

        if (total > 400) {
            if (badge) badge.classList.add('badge-error');
            if (runBtn) runBtn.disabled = true;
            if (banner) {
                banner.classList.remove('hidden');
                if (bannerMsg) {
                    bannerMsg.textContent = `Grid size of ${total} combinations exceeds the institutional limit of 400. Please increase parameter step size.`;
                }
            }
        } else if (total <= 0) {
            if (runBtn) runBtn.disabled = true;
        } else {
            if (badge) badge.classList.remove('badge-error');
            if (runBtn) runBtn.disabled = false;
            if (banner && bannerMsg && bannerMsg.textContent.includes('institutional limit')) {
                banner.classList.add('hidden');
            }
        }
    }

    /**
     * Binds Walk-Forward In-Sample split percentage slider.
     */
    bindSplitSlider() {
        const slider = document.getElementById('opt-split-slider');
        const valText = document.getElementById('opt-split-val');
        if (!slider || !valText) return;

        slider.addEventListener('input', (e) => {
            const isPct = parseInt(e.target.value, 10);
            const oosPct = 100 - isPct;
            valText.textContent = `${isPct}% IS / ${oosPct}% OOS`;
        });
    }

    /**
     * Binds Metric Switcher buttons (Sharpe, Net P&L, Max DD, Win Rate).
     */
    bindMetricSwitcher() {
        const switcher = document.getElementById('opt-metric-switcher');
        if (!switcher) return;

        switcher.querySelectorAll('.opt-metric-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const metric = e.currentTarget.dataset.metric;
                if (!metric) return;
                this.activeMetric = metric;

                switcher.querySelectorAll('.opt-metric-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');

                this.renderHeatmap();
            });
        });
    }

    /**
     * Binds the Run 2D Grid Optimization action button.
     */
    bindRunButton() {
        const btn = document.getElementById('btn-run-optimization');
        if (!btn) return;
        btn.addEventListener('click', () => {
            this.runOptimization();
        });
    }

    /**
     * Executes the parameter optimization grid search against the backend API.
     */
    async runOptimization() {
        if (this.isLoading) return;

        const strat = document.getElementById('opt-strategy-select')?.value || 'SMA_CROSS';
        const symbol = document.getElementById('opt-symbol-input')?.value || 'NSE:RELIANCE-EQ';
        const timeframe = document.getElementById('opt-timeframe-select')?.value || '1D';
        const startDate = document.getElementById('opt-start-date')?.value || '2020-01-01';
        const endDate = document.getElementById('opt-end-date')?.value || '2023-12-31';
        const targetMetric = document.getElementById('opt-target-metric')?.value || 'sharpe_ratio';
        const splitPct = parseFloat(document.getElementById('opt-split-slider')?.value || 70.0);

        const p1Name = document.getElementById('opt-param1-name')?.textContent || 'short_window';
        const p1Min = parseFloat(document.getElementById('opt-param1-min')?.value || 5);
        const p1Max = parseFloat(document.getElementById('opt-param1-max')?.value || 30);
        const p1Step = parseFloat(document.getElementById('opt-param1-step')?.value || 5);

        const p2Name = document.getElementById('opt-param2-name')?.textContent || 'long_window';
        const p2Min = parseFloat(document.getElementById('opt-param2-min')?.value || 30);
        const p2Max = parseFloat(document.getElementById('opt-param2-max')?.value || 100);
        const p2Step = parseFloat(document.getElementById('opt-param2-step')?.value || 10);

        const payload = {
            strategy: strat,
            symbol: symbol,
            timeframe: timeframe,
            start_date: startDate,
            end_date: endDate,
            initial_capital: 1000000.0,
            slippage_bps: 5.0,
            trade_type: "DELIVERY",
            param1: {
                name: p1Name,
                min_val: p1Min,
                max_val: p1Max,
                step: p1Step
            },
            param2: {
                name: p2Name,
                min_val: p2Min,
                max_val: p2Max,
                step: p2Step
            },
            walk_forward_split_pct: splitPct,
            target_metric: targetMetric
        };

        const btn = document.getElementById('btn-run-optimization');
        const spinner = document.getElementById('opt-btn-spinner');
        const banner = document.getElementById('opt-alert-banner');
        const bannerMsg = document.getElementById('opt-alert-msg');

        this.isLoading = true;
        if (btn) btn.disabled = true;
        if (spinner) spinner.classList.remove('hidden');
        if (banner) banner.classList.add('hidden');

        try {
            const resp = await fetch('/api/v1/backtest/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();

            if (!resp.ok || !data.success) {
                const errorMsg = (data.error && data.error.message) || data.detail || 'Optimization failed.';
                if (banner && bannerMsg) {
                    banner.classList.remove('hidden');
                    bannerMsg.textContent = errorMsg;
                }
                return;
            }

            this.lastOptimizationResult = data;

            // Render all UI components
            this.renderHeatmap();
            this.renderStabilityHUD();
            this.renderWalkForwardHUD();

            const timeBadge = document.getElementById('opt-execution-time');
            if (timeBadge) {
                timeBadge.textContent = `Execution: ${data.execution_time_ms} ms (${data.total_combinations} cells)`;
            }

        } catch (err) {
            console.error('[OptimizationStudio] Error:', err);
            if (banner && bannerMsg) {
                banner.classList.remove('hidden');
                bannerMsg.textContent = err.message || 'Network error running optimization.';
            }
        } finally {
            this.isLoading = false;
            if (btn) btn.disabled = false;
            if (spinner) spinner.classList.add('hidden');
        }
    }

    /**
     * Interpolates color based on metric value between min and max.
     */
    interpolateColor(val, minVal, maxVal, metric) {
        if (minVal === maxVal) return '#10b981';

        // Normalized score 0.0 to 1.0
        let norm;
        if (metric === 'max_drawdown_pct') {
            // For drawdown, lower absolute value is better (greener)
            norm = 1.0 - Math.min(1.0, Math.max(0.0, (val - minVal) / (maxVal - minVal)));
        } else {
            norm = Math.min(1.0, Math.max(0.0, (val - minVal) / (maxVal - minVal)));
        }

        // Color interpolation: Red (#f43f5e) -> Slate (#334155) -> Green (#10b981)
        if (norm < 0.5) {
            const t = norm * 2.0; // 0 to 1
            const r = Math.round(244 * (1 - t) + 51 * t);
            const g = Math.round(63 * (1 - t) + 65 * t);
            const b = Math.round(94 * (1 - t) + 85 * t);
            return `rgb(${r}, ${g}, ${b})`;
        } else {
            const t = (norm - 0.5) * 2.0; // 0 to 1
            const r = Math.round(51 * (1 - t) + 16 * t);
            const g = Math.round(65 * (1 - t) + 185 * t);
            const b = Math.round(85 * (1 - t) + 129 * t);
            return `rgb(${r}, ${g}, ${b})`;
        }
    }

    /**
     * Dynamically renders the 2D Heatmap SVG matrix.
     */
    renderHeatmap() {
        const svg = document.getElementById('opt-heatmap-svg');
        if (!svg) return;

        if (!this.lastOptimizationResult || !Array.isArray(this.lastOptimizationResult.matrix)) {
            svg.innerHTML = `
                <text x="370" y="200" text-anchor="middle" fill="#64748b" font-size="14" font-family="Inter, sans-serif">
                    Configure parameter ranges above and click "Run 2D Grid Optimization" to generate heatmap.
                </text>
            `;
            return;
        }

        const data = this.lastOptimizationResult;
        const p1Ticks = data.param1_ticks;
        const p2Ticks = data.param2_ticks;
        const cells = data.matrix;
        const optimalP1 = data.stability.optimal_param1;
        const optimalP2 = data.stability.optimal_param2;

        const cellMap = {};
        let minVal = Infinity;
        let maxVal = -Infinity;

        cells.forEach(c => {
            const key = `${c.param1_val}_${c.param2_val}`;
            cellMap[key] = c;
            const v = c[this.activeMetric];
            if (v !== undefined && v !== null && !isNaN(v)) {
                if (v < minVal) minVal = v;
                if (v > maxVal) maxVal = v;
            }
        });

        if (minVal === Infinity) minVal = 0.0;
        if (maxVal === -Infinity) maxVal = 1.0;

        // Update Legend labels
        const legMin = document.getElementById('opt-legend-min');
        const legMid = document.getElementById('opt-legend-mid');
        const legMax = document.getElementById('opt-legend-max');
        if (legMin) legMin.textContent = `Min: ${minVal.toFixed(2)}`;
        if (legMid) legMid.textContent = `Mid: ${((minVal + maxVal) / 2).toFixed(2)}`;
        if (legMax) legMax.textContent = `Max: ${maxVal.toFixed(2)}`;

        // SVG Layout Dimensions
        const width = 740;
        const height = 380;
        const marginLeft = 65;
        const marginBottom = 50;
        const marginTop = 30;
        const marginRight = 30;

        const gridW = width - marginLeft - marginRight;
        const gridH = height - marginTop - marginBottom;

        const cellW = gridW / p1Ticks.length;
        const cellH = gridH / p2Ticks.length;

        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.innerHTML = '';

        // Axis Titles
        const axisGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        axisGroup.setAttribute('class', 'opt-axis-labels');

        // X-Axis Title (Param 1)
        const xTitle = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        xTitle.setAttribute('x', marginLeft + gridW / 2);
        xTitle.setAttribute('y', height - 10);
        xTitle.setAttribute('text-anchor', 'middle');
        xTitle.setAttribute('fill', '#94a3b8');
        xTitle.setAttribute('font-size', '12');
        xTitle.setAttribute('font-weight', '600');
        xTitle.textContent = `${data.param1_name} (Parameter 1)`;
        axisGroup.appendChild(xTitle);

        // Y-Axis Title (Param 2)
        const yTitle = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yTitle.setAttribute('transform', `translate(16, ${marginTop + gridH / 2}) rotate(-90)`);
        yTitle.setAttribute('text-anchor', 'middle');
        yTitle.setAttribute('fill', '#94a3b8');
        yTitle.setAttribute('font-size', '12');
        yTitle.setAttribute('font-weight', '600');
        yTitle.textContent = `${data.param2_name} (Parameter 2)`;
        axisGroup.appendChild(yTitle);

        svg.appendChild(axisGroup);

        // X-Axis Ticks
        const xTicksGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        p1Ticks.forEach((p1, idx) => {
            const x = marginLeft + (idx + 0.5) * cellW;
            const y = height - marginBottom + 16;
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', y);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', '#64748b');
            text.setAttribute('font-size', '11');
            text.setAttribute('font-family', 'monospace');
            text.textContent = p1;
            xTicksGroup.appendChild(text);
        });
        svg.appendChild(xTicksGroup);

        // Y-Axis Ticks
        const yTicksGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        p2Ticks.forEach((p2, idx) => {
            // Y is rendered from bottom to top
            const y = marginTop + (p2Ticks.length - 1 - idx + 0.5) * cellH + 4;
            const x = marginLeft - 10;
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', y);
            text.setAttribute('text-anchor', 'end');
            text.setAttribute('fill', '#64748b');
            text.setAttribute('font-size', '11');
            text.setAttribute('font-family', 'monospace');
            text.textContent = p2;
            yTicksGroup.appendChild(text);
        });
        svg.appendChild(yTicksGroup);

        // Grid Cells Group
        const cellsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        cellsGroup.setAttribute('class', 'opt-cells-group');

        const tooltip = document.getElementById('opt-heatmap-tooltip');

        p2Ticks.forEach((p2, yIdx) => {
            p1Ticks.forEach((p1, xIdx) => {
                const key = `${p1}_${p2}`;
                const cell = cellMap[key];
                if (!cell) return;

                const metricVal = cell[this.activeMetric] || 0.0;
                const fillColor = this.interpolateColor(metricVal, minVal, maxVal, this.activeMetric);

                const x = marginLeft + xIdx * cellW;
                // Render from bottom up
                const y = marginTop + (p2Ticks.length - 1 - yIdx) * cellH;

                const isOptimal = (p1 === optimalP1 && p2 === optimalP2);

                const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                rect.setAttribute('x', x + 1);
                rect.setAttribute('y', y + 1);
                rect.setAttribute('width', Math.max(1, cellW - 2));
                rect.setAttribute('height', Math.max(1, cellH - 2));
                rect.setAttribute('fill', fillColor);
                rect.setAttribute('rx', '3');
                rect.setAttribute('class', `heatmap-cell ${isOptimal ? 'optimal-cell' : ''}`);
                rect.dataset.p1 = p1;
                rect.dataset.p2 = p2;
                rect.dataset.sharpe = cell.sharpe_ratio;
                rect.dataset.pnl = cell.net_pnl;
                rect.dataset.winrate = cell.win_rate;
                rect.dataset.maxdd = cell.max_drawdown_pct;
                rect.dataset.trades = cell.total_trades;

                if (isOptimal) {
                    rect.setAttribute('stroke', '#38bdf8');
                    rect.setAttribute('stroke-width', '2.5');
                }

                // Tooltip Interaction
                rect.addEventListener('mouseenter', (e) => {
                    if (!tooltip) return;
                    tooltip.classList.remove('hidden');
                    tooltip.innerHTML = `
                        <div class="tooltip-header">
                            <strong>${data.param1_name}: ${cell.param1_val}</strong> | 
                            <strong>${data.param2_name}: ${cell.param2_val}</strong>
                            ${isOptimal ? '<span class="badge-tag badge-trend ml-1">Optimal</span>' : ''}
                        </div>
                        <div class="tooltip-body mt-1">
                            <div>Sharpe Ratio: <strong class="text-white">${cell.sharpe_ratio}</strong></div>
                            <div>Net P&L: <strong class="${cell.net_pnl >= 0 ? 'text-green' : 'text-red'}">₹${cell.net_pnl.toLocaleString('en-IN')} (${cell.net_pnl_pct}%)</strong></div>
                            <div>Max Drawdown: <strong class="text-muted">${cell.max_drawdown_pct}%</strong></div>
                            <div>Win Rate: <strong class="text-white">${(cell.win_rate * 100).toFixed(1)}%</strong> (${cell.total_trades} trades)</div>
                            <div>Profit Factor: <strong class="text-accent">${cell.profit_factor}</strong></div>
                        </div>
                    `;
                });

                rect.addEventListener('mousemove', (e) => {
                    if (!tooltip) return;
                    const container = document.getElementById('opt-heatmap-container');
                    const cRect = container ? container.getBoundingClientRect() : { left: 0, top: 0 };
                    tooltip.style.left = `${e.clientX - cRect.left + 15}px`;
                    tooltip.style.top = `${e.clientY - cRect.top + 15}px`;
                });

                rect.addEventListener('mouseleave', () => {
                    if (tooltip) tooltip.classList.add('hidden');
                });

                // Click Selection
                rect.addEventListener('click', () => {
                    cellsGroup.querySelectorAll('.heatmap-cell').forEach(r => r.classList.remove('selected-cell'));
                    rect.classList.add('selected-cell');
                    this.selectedCell = cell;
                });

                cellsGroup.appendChild(rect);

                // Small cell text for small grids
                if (p1Ticks.length <= 8 && p2Ticks.length <= 8 && cellW >= 40) {
                    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    text.setAttribute('x', x + cellW / 2);
                    text.setAttribute('y', y + cellH / 2 + 4);
                    text.setAttribute('text-anchor', 'middle');
                    text.setAttribute('fill', '#ffffff');
                    text.setAttribute('font-size', '10');
                    text.setAttribute('font-family', 'monospace');
                    text.setAttribute('pointer-events', 'none');
                    text.textContent = (this.activeMetric === 'net_pnl') 
                        ? (cell.net_pnl >= 1000 ? `₹${(cell.net_pnl/1000).toFixed(0)}k` : `₹${cell.net_pnl.toFixed(0)}`)
                        : metricVal.toFixed(2);
                    cellsGroup.appendChild(text);
                }
            });
        });

        svg.appendChild(cellsGroup);
    }

    /**
     * Renders the 3x3 Plateau Stability Index HUD card.
     */
    renderStabilityHUD() {
        if (!this.lastOptimizationResult || !this.lastOptimizationResult.stability) return;

        const stability = this.lastOptimizationResult.stability;
        const p1Name = this.lastOptimizationResult.param1_name;
        const p2Name = this.lastOptimizationResult.param2_name;

        const badge = document.getElementById('opt-stability-badge');
        const score = document.getElementById('opt-stability-score');
        const cliff = document.getElementById('opt-cliff-drop');
        const optSummary = document.getElementById('opt-optimal-params-summary');
        const desc = document.getElementById('opt-stability-desc');

        if (score) score.textContent = `${(stability.stability_score * 100).toFixed(1)}%`;
        if (cliff) cliff.textContent = `-${stability.cliff_drop_pct}% in 3x3 neighborhood`;
        if (optSummary) {
            optSummary.textContent = `${p1Name}: ${stability.optimal_param1} | ${p2Name}: ${stability.optimal_param2}`;
        }

        if (badge) {
            badge.className = 'badge-pill';
            if (stability.classification === 'ROBUST_PLATEAU') {
                badge.classList.add('badge-robust');
                badge.textContent = 'ROBUST PLATEAU';
                if (desc) desc.textContent = 'Adjacent 3x3 neighborhood configurations retain high profitability, confirming parameter robustness against market regime shifts.';
            } else if (stability.classification === 'MODERATE_SENSITIVITY') {
                badge.classList.add('badge-moderate');
                badge.textContent = 'MODERATE SENSITIVITY';
                if (desc) desc.textContent = 'Performance drops moderately around optimal settings. Strategy exhibits acceptable parameter tolerance with mild sensitivity.';
            } else {
                badge.classList.add('badge-cliff');
                badge.textContent = '⚠️ FRAGILE OVERFITTING CLIFF';
                if (desc) desc.textContent = 'CRITICAL OVERFITTING WARNING: Neighboring settings plummet abruptly. High likelihood of historical curve-fitting and out-of-sample failure.';
            }
        }
    }

    /**
     * Renders the Walk-Forward Validation Table and WFE HUD.
     */
    renderWalkForwardHUD() {
        if (!this.lastOptimizationResult || !this.lastOptimizationResult.walk_forward) return;

        const wf = this.lastOptimizationResult.walk_forward;

        const wfeBadge = document.getElementById('opt-wfe-badge');
        if (wfeBadge) {
            wfeBadge.className = 'badge-pill';
            wfeBadge.textContent = `WFE: ${wf.walk_forward_efficiency.toFixed(2)}`;
            if (wf.walk_forward_efficiency >= 0.50) {
                wfeBadge.classList.add('badge-robust');
            } else {
                wfeBadge.classList.add('badge-cliff');
            }
        }

        const isDate = document.getElementById('opt-is-split-date');
        const isPnl = document.getElementById('opt-is-net-pnl');
        const isSharpe = document.getElementById('opt-is-sharpe');

        const oosDate = document.getElementById('opt-oos-split-date');
        const oosPnl = document.getElementById('opt-oos-net-pnl');
        const oosSharpe = document.getElementById('opt-oos-sharpe');

        if (isDate) isDate.textContent = `Prior to ${wf.split_date} (${wf.is_split_pct}%)`;
        if (isPnl) {
            isPnl.textContent = `${wf.in_sample_net_pnl >= 0 ? '+' : ''}₹${wf.in_sample_net_pnl.toLocaleString('en-IN')}`;
            isPnl.className = `text-right font-mono ${wf.in_sample_net_pnl >= 0 ? 'text-green' : 'text-red'}`;
        }
        if (isSharpe) isSharpe.textContent = wf.in_sample_sharpe.toFixed(2);

        if (oosDate) oosDate.textContent = `After ${wf.split_date} (${(100 - wf.is_split_pct).toFixed(0)}%)`;
        if (oosPnl) {
            oosPnl.textContent = `${wf.out_of_sample_net_pnl >= 0 ? '+' : ''}₹${wf.out_of_sample_net_pnl.toLocaleString('en-IN')}`;
            oosPnl.className = `text-right font-mono ${wf.out_of_sample_net_pnl >= 0 ? 'text-green' : 'text-red'}`;
        }
        if (oosSharpe) oosSharpe.textContent = wf.out_of_sample_sharpe.toFixed(2);
    }

    /**
     * Binds the "Apply Optimal Parameters to Backtest" 1-click deploy button.
     */
    bindApplyButton() {
        const btn = document.getElementById('btn-apply-optimal-params');
        if (!btn) return;
        btn.addEventListener('click', () => {
            this.applyOptimalParameters();
        });
    }

    /**
     * Applies the discovered best parameters to the Single-Stock Backtest Studio.
     */
    applyOptimalParameters() {
        if (!this.lastOptimizationResult || !this.lastOptimizationResult.best_params) {
            alert('No optimization run available yet. Please run 2D Grid Optimization first.');
            return;
        }

        const bestParams = this.lastOptimizationResult.best_params;

        // 1. Update BacktestUI internal config if available
        if (this.ui) {
            if (!this.ui.config) this.ui.config = {};
            if (!this.ui.config.parameters) this.ui.config.parameters = {};
            Object.assign(this.ui.config.parameters, bestParams);

            if (typeof this.ui.updateDynamicParams === 'function') {
                this.ui.updateDynamicParams();
            }
        }

        // 2. Directly update DOM input elements if present
        for (const [key, val] of Object.entries(bestParams)) {
            const dashed = key.replace(/_/g, '-');
            const input = document.getElementById(`param-${dashed}`);
            if (input) input.value = val;
        }

        // 3. Switch back to Single-Asset Studio tab
        const btnSingle = document.getElementById('btn-mode-single');
        if (btnSingle) {
            btnSingle.click();
        }

        // 4. Update status chip
        const statusText = document.getElementById('studio-status-text');
        if (statusText) {
            statusText.textContent = 'Optimal parameters applied! Ready to verify.';
        }
    }
}

// Attach globally
window.BacktestOptimizationController = BacktestOptimizationController;

// Auto-hook into backtestUI if already initialized
if (window.backtestUI && !window.backtestUI.optimizationController) {
    window.backtestUI.optimizationController = new BacktestOptimizationController(window.backtestUI);
}
