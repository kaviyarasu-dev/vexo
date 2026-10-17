/**
 * OrderBlock Quick-View Sheet Modal Drawer
 * Displays instant 10-second inspection metrics (Z-level, S1/R1 invalidation, targets, R:R, 4-point alignment)
 * without switching or reloading the active main chart.
 */

(function () {
    class OrderBlockSheet {
        constructor() {
            this.container = null;
            this.isOpen = false;
            this.currentSymbol = null;

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }

        init() {
            this.container = document.getElementById('orderblock-quick-sheet');
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'orderblock-quick-sheet';
                this.container.className = 'orderblock-quick-sheet hidden';
                this.container.innerHTML = `
                    <div id="orderblock-sheet-backdrop" class="orderblock-sheet-backdrop"></div>
                    <div class="orderblock-sheet-drawer">
                        <div class="orderblock-sheet-header">
                            <div class="sheet-title-group">
                                <h3 id="sheet-symbol-name" class="sheet-symbol font-mono">--</h3>
                                <span id="sheet-symbol-sector" class="sheet-sector-badge">--</span>
                            </div>
                            <button id="btn-close-orderblock-sheet" class="sheet-close-btn" title="Close (Esc)">✕</button>
                        </div>
                        <div class="orderblock-sheet-body">
                            <div class="sheet-metric-row">
                                <div class="sheet-metric-card">
                                    <div class="sheet-metric-label">Last Price</div>
                                    <div id="sheet-price" class="sheet-metric-val font-mono">₹--</div>
                                </div>
                                <div class="sheet-metric-card">
                                    <div class="sheet-metric-label">Day Move</div>
                                    <div id="sheet-day-move" class="sheet-metric-val font-mono">--%</div>
                                </div>
                                <div class="sheet-metric-card">
                                    <div class="sheet-metric-label">Strength Score</div>
                                    <div id="sheet-strength" class="sheet-metric-val font-mono text-accent">--</div>
                                </div>
                            </div>
                            <div class="sheet-levels-section">
                                <h4 class="sheet-section-title">Institutional Levels (5m)</h4>
                                <div class="sheet-levels-grid">
                                    <div class="level-box">
                                        <span class="level-label">Reference Zone (Z)</span>
                                        <span id="sheet-level-z" class="level-val font-mono text-cyan">₹--</span>
                                    </div>
                                    <div class="level-box">
                                        <span class="level-label">Invalidation (Stop)</span>
                                        <span id="sheet-level-inval" class="level-val font-mono text-red">₹--</span>
                                    </div>
                                    <div class="level-box">
                                        <span class="level-label">Primary Target (T2)</span>
                                        <span id="sheet-level-target" class="level-val font-mono text-gold">₹--</span>
                                    </div>
                                    <div class="level-box">
                                        <span class="level-label">Risk-to-Reward (R:R)</span>
                                        <span id="sheet-level-rr" class="level-val font-mono text-accent">--x</span>
                                    </div>
                                </div>
                            </div>
                            <div class="sheet-alignment-section">
                                <h4 class="sheet-section-title">4-Point Institutional Alignment</h4>
                                <div id="sheet-alignment-badge" class="alignment-badge-large font-mono">--/4 Evaluating...</div>
                            </div>
                        </div>
                        <div class="orderblock-sheet-footer">
                            <button id="btn-sheet-switch-chart" class="btn-primary w-full">📈 Open Full Chart</button>
                        </div>
                    </div>
                `;
                document.body.appendChild(this.container);
            }

            // Bind close triggers
            const closeBtn = document.getElementById('btn-close-orderblock-sheet');
            const backdrop = document.getElementById('orderblock-sheet-backdrop');
            if (closeBtn) closeBtn.addEventListener('click', () => this.closeSheet());
            if (backdrop) backdrop.addEventListener('click', () => this.closeSheet());

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.closeSheet();
                }
            });

            // Bind switch chart button
            const switchBtn = document.getElementById('btn-sheet-switch-chart');
            if (switchBtn) {
                switchBtn.addEventListener('click', () => {
                    if (this.currentSymbol && typeof window.switchChartSymbol === 'function') {
                        window.switchChartSymbol(this.currentSymbol);
                        this.closeSheet();
                    } else if (this.currentSymbol && typeof window.fetchChartData === 'function') {
                        window.currentActiveSymbol = this.currentSymbol;
                        window.fetchChartData(this.currentSymbol, window.currentSymbolTimeframe || '5m');
                        this.closeSheet();
                    }
                });
            }
        }

        async openSheet(symbol, summaryData = {}) {
            this.currentSymbol = symbol;
            if (!this.container) this.init();

            // Populate initial summary if available
            document.getElementById('sheet-symbol-name').textContent = symbol;
            document.getElementById('sheet-symbol-sector').textContent = summaryData.sector || 'Equities';
            document.getElementById('sheet-price').textContent = summaryData.price ? `₹${summaryData.price}` : '₹--';
            document.getElementById('sheet-day-move').textContent = summaryData.day_move_pct ? `${summaryData.day_move_pct > 0 ? '+' : ''}${summaryData.day_move_pct}%` : '--%';
            document.getElementById('sheet-strength').textContent = summaryData.score ? `${summaryData.score.toFixed(2)}` : '--';

            // Show drawer
            this.container.classList.remove('hidden');
            this.container.classList.add('active');
            this.isOpen = true;

            // Fetch live zones and levels
            try {
                const res = await fetch(`/api/v1/orderblock/zones?symbol=${encodeURIComponent(symbol)}`);
                if (!res.ok) return;
                const payload = await res.json();
                if (payload.success && payload.data) {
                    const data = payload.data;
                    const ladder = data.ladder;
                    if (ladder) {
                        document.getElementById('sheet-level-z').textContent = `₹${ladder.z_price}`;
                        document.getElementById('sheet-level-inval').textContent = `₹${ladder.invalidation_price}`;
                        document.getElementById('sheet-level-target').textContent = `₹${ladder.r2 || ladder.s2}`;
                        document.getElementById('sheet-level-rr').textContent = `${ladder.risk_reward_ratio}x`;
                    }
                    // Evaluate 4-point alignment synchronized with orderBlockDashboard
                    let align = null;
                    if (window.orderBlockDashboard && typeof window.orderBlockDashboard.computeAlignment === 'function') {
                        const pt = (window.orderBlockDashboard.points && window.orderBlockDashboard.points.find(p => p.symbol === symbol)) || summaryData;
                        align = window.orderBlockDashboard.computeAlignment(pt);
                    }
                    const score = align ? align.score : ((summaryData.is_contender ? 1 : 0) + (summaryData.is_pick ? 1 : 0) + (ladder && ladder.risk_reward_ratio >= 1.5 ? 1 : 0) + 1);
                    const label = align ? align.badge : (score === 4 ? '4/4 Full Edge' : (score === 3 ? '3/4 Half Size' : '≤2/4 Pass'));
                    const color = align ? align.color : (score === 4 ? 'green' : (score === 3 ? 'yellow' : 'dim'));
                    const badgeElem = document.getElementById('sheet-alignment-badge');
                    if (badgeElem) {
                        badgeElem.textContent = label;
                        badgeElem.className = `alignment-badge-large font-mono ${color === 'green' ? 'edge-full' : (color === 'yellow' ? 'edge-half' : 'edge-pass')}`;
                    }
                }
            } catch (err) {
                console.warn('[OrderBlockSheet] Error loading sheet details:', err);
            }
        }

        closeSheet() {
            if (!this.container) return;
            this.container.classList.remove('active');
            this.container.classList.add('hidden');
            this.isOpen = false;
        }
    }

    window.OrderBlockSheet = OrderBlockSheet;
    window.orderBlockSheet = new OrderBlockSheet();
    window.openOrderBlockSheet = (symbol, summary) => window.orderBlockSheet.openSheet(symbol, summary);
})();
