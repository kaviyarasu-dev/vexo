/**
 * ============================================================================
 * Real-Time Positions & Orders Terminal Dock (Plan 03-001)
 * Trader Command Center for Monitoring Open Positions, Orders, Fills & Taxes
 * ============================================================================
 */

class PaperTerminalDock {
    constructor() {
        this.activeTab = 'positions';
        
        // LocalStorage persistence for dock state (default: closed/collapsed unless explicitly 'open')
        let savedState = null;
        try {
            savedState = localStorage.getItem('trading_app_paper_dock_state');
        } catch (e) {}
        this.isCollapsed = (savedState !== 'open');

        this.positions = [];
        this.orders = [];
        this.history = [];
        this.strategies = [];
        this.accountSummary = null;
        this.pollingTimer = null;
        this.isRefreshing = false;

        this.init();
    }

    init() {
        this.ensureDockDOM();
        const dock = document.getElementById('paper-trading-dock');
        if (dock) {
            dock.classList.toggle('collapsed', this.isCollapsed);
        }
        this.bindEvents();
        this.refreshAll();
        this.startPolling();
    }

    // --------------------------------------------------------------------------
    // 1. DOM Creation & Mount
    // --------------------------------------------------------------------------
    ensureDockDOM() {
        const workspace = document.querySelector('.chart-workspace');
        if (!workspace) return;

        let dock = document.getElementById('paper-trading-dock');
        if (!dock) {
            dock = document.createElement('div');
            dock.id = 'paper-trading-dock';
            dock.className = 'paper-trading-dock';
            dock.innerHTML = `
                <!-- Dock Header Bar -->
                <div class="paper-dock-header">
                    <div class="dock-header-left">
                        <span class="dock-title-icon">💼</span>
                        <span class="dock-title">Paper Trading Terminal</span>
                        <div class="dock-tabs">
                            <button type="button" class="dock-tab active" data-dock-tab="positions">
                                Positions <span id="dock-positions-count" class="badge-pill font-mono">0</span>
                            </button>
                            <button type="button" class="dock-tab" data-dock-tab="orders">
                                Orders <span id="dock-orders-count" class="badge-pill font-mono">0</span>
                            </button>
                            <button type="button" class="dock-tab" data-dock-tab="history">
                                Fills History <span id="dock-history-count" class="badge-pill font-mono">0</span>
                            </button>
                            <button type="button" class="dock-tab" data-dock-tab="strategies">
                                Auto Strategies <span id="dock-strat-count" class="badge-pill font-mono">0</span>
                            </button>
                        </div>
                    </div>
                    <div class="dock-header-right">
                        <div class="account-metric-pill" title="Virtual Free Cash available for placing new trades">
                            <span class="metric-lbl">Virtual Cash:</span>
                            <span class="metric-val font-mono" id="dock-cash-val">₹10,00,000.00</span>
                        </div>
                        <div class="account-metric-pill" title="Mark-to-Market Unrealized P&L across all active positions">
                            <span class="metric-lbl">Unrealized P&L:</span>
                            <span class="metric-val font-mono" id="dock-pnl-val">₹0.00</span>
                        </div>
                        <div class="account-metric-pill" title="Realized P&L from closed positions minus statutory taxes">
                            <span class="metric-lbl">Realized P&L:</span>
                            <span class="metric-val font-mono" id="dock-realized-val">₹0.00</span>
                        </div>
                        <button type="button" class="btn-dock-action" id="btn-dock-reset-account" title="Reset Account Balance to ₹10,00,000">
                            🔄 Reset
                        </button>
                        <button type="button" class="btn-dock-toggle" id="btn-dock-toggle-view" title="Collapse / Expand Terminal">
                            ▼
                        </button>
                    </div>
                </div>

                <!-- Dock Content Body -->
                <div class="paper-dock-body" id="paper-dock-body">
                    <!-- Tab 1: Positions -->
                    <div class="dock-panel active" id="dock-panel-positions">
                        <table class="paper-table" id="table-paper-positions">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Type</th>
                                    <th>Side</th>
                                    <th class="text-right">Qty</th>
                                    <th class="text-right">Avg Price (₹)</th>
                                    <th class="text-right">LTP (₹)</th>
                                    <th class="text-right">Unrealized P&L (₹)</th>
                                    <th class="text-right">P&L (%)</th>
                                    <th class="text-center">Stop Loss</th>
                                    <th class="text-center">Target (TP)</th>
                                    <th class="text-center">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-paper-positions"></tbody>
                        </table>
                    </div>

                    <!-- Tab 2: Orders -->
                    <div class="dock-panel hidden" id="dock-panel-orders">
                        <table class="paper-table" id="table-paper-orders">
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Order ID</th>
                                    <th>Symbol</th>
                                    <th>Side</th>
                                    <th>Type</th>
                                    <th>Product</th>
                                    <th class="text-right">Qty</th>
                                    <th class="text-right">Price (₹)</th>
                                    <th class="text-center">Status</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-paper-orders"></tbody>
                        </table>
                    </div>

                    <!-- Tab 3: Fills History -->
                    <div class="dock-panel hidden" id="dock-panel-history">
                        <table class="paper-table" id="table-paper-history">
                            <thead>
                                <tr>
                                    <th>Execution Time</th>
                                    <th>Trade ID</th>
                                    <th>Symbol</th>
                                    <th>Side</th>
                                    <th class="text-right">Qty</th>
                                    <th class="text-right">Fill Price (₹)</th>
                                    <th class="text-right">Brokerage (₹)</th>
                                    <th class="text-right">STT (₹)</th>
                                    <th class="text-right">Total Taxes (₹)</th>
                                    <th class="text-right">Realized Net P&L (₹)</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-paper-history"></tbody>
                        </table>
                    </div>

                    <!-- Tab 4: Auto Strategies -->
                    <div class="dock-panel hidden" id="dock-panel-strategies">
                        <table class="paper-table" id="table-paper-strategies">
                            <thead>
                                <tr>
                                    <th>Strategy Name</th>
                                    <th>Symbol</th>
                                    <th>Timeframe</th>
                                    <th>Product</th>
                                    <th class="text-right">Allocated Capital (₹)</th>
                                    <th class="text-center">Status</th>
                                    <th class="text-center">Action</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-paper-strategies"></tbody>
                        </table>
                    </div>
                </div>
            `;
            workspace.appendChild(dock);
        }

        // Ensure Risk Edit Modal DOM
        let riskModal = document.getElementById('modal-edit-risk');
        if (!riskModal) {
            riskModal = document.createElement('div');
            riskModal.id = 'modal-edit-risk';
            riskModal.className = 'risk-modal-overlay';
            riskModal.innerHTML = `
                <div class="risk-modal">
                    <div class="risk-modal-header">
                        <span class="risk-modal-title" id="risk-modal-sym">Edit Risk Parameters</span>
                        <button type="button" class="risk-modal-close" id="btn-close-risk-modal">&times;</button>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div class="ticket-field-group">
                            <label class="ticket-field-label">Stop Loss Price (₹)</label>
                            <div class="ticket-input-wrap">
                                <span class="ticket-currency-prefix">₹</span>
                                <input type="number" id="risk-input-sl" class="ticket-input font-mono" step="0.05" placeholder="Optional" />
                            </div>
                        </div>
                        <div class="ticket-field-group">
                            <label class="ticket-field-label">Take Profit Target (₹)</label>
                            <div class="ticket-input-wrap">
                                <span class="ticket-currency-prefix">₹</span>
                                <input type="number" id="risk-input-tp" class="ticket-input font-mono" step="0.05" placeholder="Optional" />
                            </div>
                        </div>
                        <div class="ticket-field-group">
                            <label class="ticket-field-label">Trailing Stop Loss %</label>
                            <div class="ticket-input-wrap">
                                <input type="number" id="risk-input-trail" class="ticket-input font-mono" step="0.1" min="0.1" max="20" placeholder="e.g. 1.5" />
                                <span style="color: #64748B; font-size: 12px;">%</span>
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px;">
                        <button type="button" class="ticket-cancel-btn" id="btn-cancel-risk">Cancel</button>
                        <button type="button" class="ticket-submit-btn buy-mode" id="btn-save-risk">Update Risk</button>
                    </div>
                </div>
            `;
            document.body.appendChild(riskModal);
        }
    }

    // --------------------------------------------------------------------------
    // 2. Event Binding
    // --------------------------------------------------------------------------
    bindEvents() {
        // Tab switching
        document.querySelectorAll('.dock-tab').forEach(tabBtn => {
            tabBtn.addEventListener('click', (e) => {
                const targetTab = e.currentTarget.dataset.dockTab;
                this.switchTab(targetTab);
            });
        });

        // Collapse / Expand toggle
        const btnToggle = document.getElementById('btn-dock-toggle-view');
        if (btnToggle) {
            btnToggle.addEventListener('click', () => {
                this.toggleCollapse();
            });
        }

        // Reset account
        const btnReset = document.getElementById('btn-dock-reset-account');
        if (btnReset) {
            btnReset.addEventListener('click', () => {
                this.promptResetAccount();
            });
        }

        // Risk modal controls
        const btnCloseRisk = document.getElementById('btn-close-risk-modal');
        const btnCancelRisk = document.getElementById('btn-cancel-risk');
        const btnSaveRisk = document.getElementById('btn-save-risk');
        const riskOverlay = document.getElementById('modal-edit-risk');

        if (btnCloseRisk) btnCloseRisk.addEventListener('click', () => this.closeRiskModal());
        if (btnCancelRisk) btnCancelRisk.addEventListener('click', () => this.closeRiskModal());
        if (riskOverlay) {
            riskOverlay.addEventListener('click', (e) => {
                if (e.target === riskOverlay) this.closeRiskModal();
            });
        }

        if (btnSaveRisk) {
            btnSaveRisk.addEventListener('click', () => {
                this.saveRiskParameters();
            });
        }
    }

    toggleCollapse() {
        const dock = document.getElementById('paper-trading-dock');
        if (!dock) return;
        this.isCollapsed = !this.isCollapsed;
        dock.classList.toggle('collapsed', this.isCollapsed);
        try {
            localStorage.setItem('trading_app_paper_dock_state', this.isCollapsed ? 'closed' : 'open');
        } catch (e) {}
        if (window.handleResize) {
            window.handleResize();
            requestAnimationFrame(window.handleResize);
        }
    }

    switchTab(tabName) {
        this.activeTab = tabName;

        // Update active tab buttons
        document.querySelectorAll('.dock-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.dockTab === tabName);
        });

        // Toggle subpanels
        const panels = {
            positions: document.getElementById('dock-panel-positions'),
            orders: document.getElementById('dock-panel-orders'),
            history: document.getElementById('dock-panel-history'),
            strategies: document.getElementById('dock-panel-strategies')
        };

        Object.keys(panels).forEach(key => {
            const p = panels[key];
            if (p) {
                if (key === tabName) {
                    p.classList.remove('hidden');
                    p.classList.add('active');
                } else {
                    p.classList.add('hidden');
                    p.classList.remove('active');
                }
            }
        });
    }

    // --------------------------------------------------------------------------
    // 3. Periodic Polling & Data Retrieval
    // --------------------------------------------------------------------------
    startPolling() {
        if (this.pollingTimer) clearInterval(this.pollingTimer);
        this.pollingTimer = setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.refreshAll();
            }
        }, 2500);
    }

    async refreshAll() {
        if (this.isRefreshing) return;
        this.isRefreshing = true;

        try {
            const [accRes, posRes, ordRes, histRes, stratRes] = await Promise.all([
                fetch('/api/v1/paper-trading/account'),
                fetch('/api/v1/paper-trading/positions'),
                fetch('/api/v1/paper-trading/orders?limit=30'),
                fetch('/api/v1/paper-trading/history?limit=30'),
                fetch('/api/v1/paper-trading/auto-strategies')
            ]);

            if (accRes.ok) {
                const d = await accRes.json();
                if (d.success && d.data) {
                    this.accountSummary = d.data;
                    this.renderAccountMetrics(d.data);
                }
            }

            if (posRes.ok) {
                const d = await posRes.json();
                if (d.success && Array.isArray(d.data)) {
                    this.positions = d.data;
                    this.renderPositionsTable(d.data);
                    const countEl = document.getElementById('dock-positions-count');
                    if (countEl) countEl.textContent = d.data.length;
                }
            }

            if (ordRes.ok) {
                const d = await ordRes.json();
                if (d.success && Array.isArray(d.data)) {
                    this.orders = d.data;
                    this.renderOrdersTable(d.data);
                    const countEl = document.getElementById('dock-orders-count');
                    if (countEl) countEl.textContent = d.data.length;
                }
            }

            if (histRes.ok) {
                const d = await histRes.json();
                if (d.success && Array.isArray(d.data)) {
                    this.history = d.data;
                    this.renderHistoryTable(d.data);
                    const countEl = document.getElementById('dock-history-count');
                    if (countEl) countEl.textContent = d.data.length;
                }
            }

            if (stratRes.ok) {
                const d = await stratRes.json();
                if (d.success && Array.isArray(d.data)) {
                    this.strategies = d.data;
                    this.renderStrategiesTable(d.data);
                    const countEl = document.getElementById('dock-strat-count');
                    if (countEl) countEl.textContent = d.data.length;
                }
            }
        } catch (e) {
            console.warn('[PaperTerminalDock] Polling error:', e);
        } finally {
            this.isRefreshing = false;
        }
    }

    refreshPositions() {
        return this.refreshAll();
    }

    // --------------------------------------------------------------------------
    // 4. Render Table Views
    // --------------------------------------------------------------------------
    renderAccountMetrics(acc) {
        const cashEl = document.getElementById('dock-cash-val');
        const pnlEl = document.getElementById('dock-pnl-val');
        const realizedEl = document.getElementById('dock-realized-val');

        if (cashEl) {
            cashEl.textContent = `₹${acc.balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }

        if (pnlEl) {
            const unPnl = acc.total_unrealized_pnl || 0.0;
            const sign = unPnl >= 0 ? '+' : '';
            pnlEl.textContent = `${sign}₹${unPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            pnlEl.className = `metric-val font-mono ${unPnl >= 0 ? 'positive' : 'negative'}`;
        }

        if (realizedEl) {
            const relPnl = acc.realized_pnl || 0.0;
            const sign = relPnl >= 0 ? '+' : '';
            realizedEl.textContent = `${sign}₹${relPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            realizedEl.className = `metric-val font-mono ${relPnl >= 0 ? 'positive' : 'negative'}`;
        }
    }

    renderPositionsTable(positions) {
        const tbody = document.getElementById('tbody-paper-positions');
        if (!tbody) return;

        if (!positions || positions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="dock-empty-state">
                        <div class="dock-empty-icon">💼</div>
                        No active open positions. Execute a trade using the Quick Trade bar above.
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        positions.forEach(p => {
            const isLong = (p.side === 'LONG');
            const sideClass = isLong ? 'long' : 'short';
            const pnlClass = p.unrealized_pnl >= 0 ? 'positive' : 'negative';
            const sign = p.unrealized_pnl >= 0 ? '+' : '';

            const slText = p.stop_loss ? `₹${p.stop_loss.toFixed(2)}` : '--';
            const tpText = p.take_profit ? `₹${p.take_profit.toFixed(2)}` : '--';

            html += `
                <tr data-symbol="${p.symbol}">
                    <td><strong>${p.symbol}</strong></td>
                    <td><span class="pos-type-pill">${p.trade_type}</span></td>
                    <td><span class="pos-side-pill ${sideClass}">${p.side}</span></td>
                    <td class="text-right font-mono">${p.quantity}</td>
                    <td class="text-right font-mono">₹${p.average_price.toFixed(2)}</td>
                    <td class="text-right font-mono">₹${p.current_price.toFixed(2)}</td>
                    <td class="text-right font-mono ${pnlClass}">${sign}₹${p.unrealized_pnl.toFixed(2)}</td>
                    <td class="text-right font-mono ${pnlClass}">${sign}${p.unrealized_pnl_pct.toFixed(2)}%</td>
                    <td class="text-center font-mono">${slText}</td>
                    <td class="text-center font-mono">${tpText}</td>
                    <td class="text-center">
                        <button type="button" class="btn-table-action btn-edit-risk" onclick="window.paperTerminalDock.openRiskEditModal('${p.symbol}')" title="Adjust Stop Loss / Target">
                            Risk
                        </button>
                        <button type="button" class="btn-table-action btn-square-off" onclick="window.paperTerminalDock.closePosition('${p.symbol}')" title="Square off position at current market price">
                            Square Off
                        </button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    renderOrdersTable(orders) {
        const tbody = document.getElementById('tbody-paper-orders');
        if (!tbody) return;

        if (!orders || orders.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="dock-empty-state">
                        <div class="dock-empty-icon">📋</div>
                        No orders recorded yet.
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        orders.forEach(o => {
            const timeStr = o.created_at ? o.created_at.replace('T', ' ').substring(0, 19) : '--';
            const sideClass = o.side === 'BUY' ? 'long' : 'short';
            const priceText = o.price ? `₹${o.price.toFixed(2)}` : '--';

            html += `
                <tr>
                    <td class="font-mono">${timeStr}</td>
                    <td class="font-mono" style="color: #64748B;">${o.order_id.substring(0, 8)}...</td>
                    <td><strong>${o.symbol}</strong></td>
                    <td><span class="pos-side-pill ${sideClass}">${o.side}</span></td>
                    <td>${o.order_type}</td>
                    <td><span class="pos-type-pill">${o.trade_type}</span></td>
                    <td class="text-right font-mono">${o.quantity}</td>
                    <td class="text-right font-mono">${priceText}</td>
                    <td class="text-center"><span class="status-pill filled">${o.status}</span></td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    renderHistoryTable(trades) {
        const tbody = document.getElementById('tbody-paper-history');
        if (!tbody) return;

        if (!trades || trades.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="dock-empty-state">
                        <div class="dock-empty-icon">📜</div>
                        No closed trade fills ledger yet.
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        trades.forEach(t => {
            const timeStr = t.executed_at ? t.executed_at.replace('T', ' ').substring(0, 19) : '--';
            const sideClass = t.side === 'BUY' ? 'long' : 'short';
            const pnlClass = t.net_pnl >= 0 ? 'positive' : 'negative';
            const pnlSign = t.net_pnl >= 0 ? '+' : '';

            html += `
                <tr>
                    <td class="font-mono">${timeStr}</td>
                    <td class="font-mono" style="color: #64748B;">${t.trade_id.substring(0, 8)}...</td>
                    <td><strong>${t.symbol}</strong></td>
                    <td><span class="pos-side-pill ${sideClass}">${t.side}</span></td>
                    <td class="text-right font-mono">${t.quantity}</td>
                    <td class="text-right font-mono">₹${t.fill_price.toFixed(2)}</td>
                    <td class="text-right font-mono">₹${t.brokerage.toFixed(2)}</td>
                    <td class="text-right font-mono">₹${t.stt.toFixed(2)}</td>
                    <td class="text-right font-mono">₹${t.total_charges.toFixed(2)}</td>
                    <td class="text-right font-mono ${pnlClass}">
                        ${t.side === 'SELL' ? `${pnlSign}₹${t.net_pnl.toFixed(2)}` : '--'}
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    renderStrategiesTable(strats) {
        const tbody = document.getElementById('tbody-paper-strategies');
        if (!tbody) return;

        if (!strats || strats.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="dock-empty-state">
                        <div class="dock-empty-icon">🤖</div>
                        No quantitative strategies deployed for forward-testing yet.
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        strats.forEach(s => {
            html += `
                <tr>
                    <td><strong>${s.strategy_name}</strong></td>
                    <td>${s.symbol}</td>
                    <td><span class="pos-type-pill">${s.timeframe}</span></td>
                    <td><span class="pos-type-pill">${s.trade_type}</span></td>
                    <td class="text-right font-mono">₹${s.allocated_capital.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td class="text-center"><span class="status-pill active">${s.status}</span></td>
                    <td class="text-center">
                        <button type="button" class="btn-table-action btn-square-off" onclick="window.paperTerminalDock.deleteStrategy('${s.strategy_id}')" title="Stop and remove strategy">
                            Stop
                        </button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    // --------------------------------------------------------------------------
    // 5. Actions: Square Off, Risk Edit, Reset Account
    // --------------------------------------------------------------------------
    async closePosition(symbol) {
        if (!confirm(`Are you sure you want to square off your position in ${symbol}?`)) return;

        try {
            const res = await fetch(`/api/v1/paper-trading/positions/${encodeURIComponent(symbol)}/close`, {
                method: 'DELETE'
            });

            const data = await res.json();
            if (res.ok && data.success) {
                if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.showToast === 'function') {
                    window.chartPaperTradeManager.showToast(
                        'Position Squared Off',
                        `Closed position for ${symbol} at ₹${data.data.fill_price.toFixed(2)}`,
                        'success'
                    );
                }
                // Notify chart manager to clear lines
                if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.renderPositionLines === 'function') {
                    window.chartPaperTradeManager.renderPositionLines(null);
                }
                await this.refreshAll();
            } else {
                alert(`Square Off Failed: ${data.detail || 'Could not close position'}`);
            }
        } catch (e) {
            alert(`Error: ${e.message}`);
        }
    }

    openRiskEditModal(symbol) {
        const pos = this.positions.find(p => p.symbol === symbol);
        if (!pos) return;

        this.currentEditingSymbol = symbol;
        const symEl = document.getElementById('risk-modal-sym');
        const slInp = document.getElementById('risk-input-sl');
        const tpInp = document.getElementById('risk-input-tp');
        const trailInp = document.getElementById('risk-input-trail');
        const overlay = document.getElementById('modal-edit-risk');

        if (symEl) symEl.textContent = `Edit Risk: ${symbol}`;
        if (slInp) slInp.value = pos.stop_loss ? pos.stop_loss.toFixed(2) : '';
        if (tpInp) tpInp.value = pos.take_profit ? pos.take_profit.toFixed(2) : '';
        if (trailInp) trailInp.value = pos.trailing_sl_pct ? pos.trailing_sl_pct.toFixed(1) : '';

        if (overlay) overlay.classList.add('open');
    }

    closeRiskModal() {
        const overlay = document.getElementById('modal-edit-risk');
        if (overlay) overlay.classList.remove('open');
        this.currentEditingSymbol = null;
    }

    async saveRiskParameters() {
        if (!this.currentEditingSymbol) return;
        const symbol = this.currentEditingSymbol;

        const slInp = document.getElementById('risk-input-sl');
        const tpInp = document.getElementById('risk-input-tp');
        const trailInp = document.getElementById('risk-input-trail');

        const stopLoss = (slInp && slInp.value) ? parseFloat(slInp.value) : null;
        const takeProfit = (tpInp && tpInp.value) ? parseFloat(tpInp.value) : null;
        const trailingPct = (trailInp && trailInp.value) ? parseFloat(trailInp.value) : null;

        try {
            const res = await fetch(`/api/v1/paper-trading/positions/${encodeURIComponent(symbol)}/risk`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stop_loss: stopLoss,
                    take_profit: takeProfit,
                    trailing_sl_pct: trailingPct
                })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.closeRiskModal();
                if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.showToast === 'function') {
                    window.chartPaperTradeManager.showToast('Risk Updated', `Updated levels for ${symbol}`, 'success');
                    window.chartPaperTradeManager.refreshPositionsAndAccount();
                }
                await this.refreshAll();
            } else {
                alert(`Update Failed: ${data.detail || 'Could not update risk parameters'}`);
            }
        } catch (e) {
            alert(`Network error: ${e.message}`);
        }
    }

    async promptResetAccount() {
        if (!confirm('Are you sure you want to reset your paper trading account to ₹10,00,000? All active positions, orders, and trade history will be wiped.')) return;

        try {
            const res = await fetch('/api/v1/paper-trading/account/reset?initial_capital=1000000.0', {
                method: 'POST'
            });

            const data = await res.json();
            if (res.ok && data.success) {
                if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.showToast === 'function') {
                    window.chartPaperTradeManager.showToast('Account Reset', 'Virtual balance restored to ₹10,00,000.00', 'success');
                    window.chartPaperTradeManager.renderPositionLines(null);
                    window.chartPaperTradeManager.refreshPositionsAndAccount();
                }
                await this.refreshAll();
            } else {
                alert(`Reset Failed: ${data.detail || 'Could not reset account'}`);
            }
        } catch (e) {
            alert(`Error: ${e.message}`);
        }
    }

    async deleteStrategy(strategyId) {
        if (!confirm('Stop and remove this automated strategy?')) return;

        try {
            const res = await fetch(`/api/v1/paper-trading/auto-strategies/${strategyId}`, {
                method: 'DELETE'
            });

            const data = await res.json();
            if (res.ok && data.success) {
                if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.showToast === 'function') {
                    window.chartPaperTradeManager.showToast('Strategy Removed', 'Automated strategy has been stopped', 'success');
                }
                await this.refreshAll();
            }
        } catch (e) {
            alert(`Error: ${e.message}`);
        }
    }
}

// Global Instantiation on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.paperTerminalDock = new PaperTerminalDock();
});
