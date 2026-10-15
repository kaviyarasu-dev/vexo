/**
 * ============================================================================
 * Chart Quick Execution Floating Bar & Visual Price Lines (Plan 02-001)
 * Lightweight Charts Overlays for Institutional Paper Trading
 * ============================================================================
 */

class ChartPaperTradeManager {
    constructor() {
        this.activeSymbol = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
        this.currentLTP = 2500.0;
        this.activePosition = null;
        this.activePriceLines = {
            entry: null,
            target: null,
            stopLoss: null
        };
        this.accountSummary = null;
        this.isSubmitting = false;

        // Ticket state
        this.ticketState = {
            side: 'BUY',
            tradeType: 'DELIVERY',
            orderType: 'MARKET',
            quantity: 50,
            limitPrice: 2500.0,
            enableSL: false,
            stopLoss: null,
            enableTP: false,
            takeProfit: null,
            enableTrailing: false,
            trailingPct: null
        };

        this.init();
    }

    init() {
        this.ensureQuickTradeBarDOM();
        this.ensureOrderTicketModalDOM();
        this.ensureToastContainer();
        this.bindEvents();
        this.refreshPositionsAndAccount();
    }

    // --------------------------------------------------------------------------
    // 1. DOM Creation & Mount
    // --------------------------------------------------------------------------
    ensureQuickTradeBarDOM() {
        const container = document.getElementById('chart-container');
        if (!container) return;

        let bar = document.getElementById('chart-quick-trade-bar');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'chart-quick-trade-bar';
            bar.className = 'chart-quick-trade-bar';
            bar.innerHTML = `
                <!-- Dynamic Active Position Badge -->
                <div class="quick-position-badge" id="quick-pos-badge" style="display: none;">
                    <span class="quick-pos-side long" id="quick-pos-side">LONG</span>
                    <span class="font-mono" id="quick-pos-qty">50</span>
                    <span class="quick-pos-pnl font-mono" id="quick-pos-pnl">₹0.00</span>
                    <button type="button" class="quick-pos-close-btn" id="btn-quick-close-pos" title="Close Position at Market">×</button>
                </div>

                <button type="button" class="quick-trade-btn quick-buy-btn" id="btn-quick-buy" title="1-Click Instant Market Buy">
                    <span class="btn-side-lbl">BUY</span>
                    <span class="btn-price-lbl font-mono" id="quick-buy-price">₹--</span>
                </button>
                <div class="quick-qty-stepper">
                    <button type="button" class="qty-step-btn" id="btn-qty-minus">-</button>
                    <input type="number" id="quick-trade-qty" class="qty-input font-mono" value="50" min="1" step="1">
                    <button type="button" class="qty-step-btn" id="btn-qty-plus">+</button>
                </div>
                <button type="button" class="quick-trade-btn quick-sell-btn" id="btn-quick-sell" title="1-Click Instant Market Sell">
                    <span class="btn-side-lbl">SELL</span>
                    <span class="btn-price-lbl font-mono" id="quick-sell-price">₹--</span>
                </button>
                <button type="button" class="quick-settings-btn" id="btn-quick-order-ticket" title="Advanced Order Ticket (SL, TP, Limit Orders)">
                    ⚙️
                </button>
            `;
            container.appendChild(bar);
        }
    }

    ensureOrderTicketModalDOM() {
        let overlay = document.getElementById('modal-order-ticket');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'modal-order-ticket';
            overlay.className = 'order-ticket-overlay';
            overlay.innerHTML = `
                <div class="order-ticket-modal">
                    <div class="order-ticket-header">
                        <div class="order-ticket-title-wrap">
                            <span class="order-ticket-symbol" id="ticket-symbol-display">NSE:RELIANCE-EQ</span>
                            <span class="order-ticket-ltp-badge font-mono" id="ticket-ltp-display">₹2,500.00</span>
                        </div>
                        <button type="button" class="order-ticket-close-btn" id="btn-close-ticket">&times;</button>
                    </div>

                    <div class="order-ticket-body">
                        <!-- Side Selector -->
                        <div class="ticket-segmented-control" id="ticket-side-control">
                            <button type="button" class="ticket-segment-btn active buy-active" data-side="BUY">BUY</button>
                            <button type="button" class="ticket-segment-btn" data-side="SELL">SELL</button>
                        </div>

                        <!-- Product & Order Type -->
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <div class="ticket-segmented-control" id="ticket-product-control">
                                <button type="button" class="ticket-segment-btn active default-active" data-product="DELIVERY">Delivery</button>
                                <button type="button" class="ticket-segment-btn" data-product="INTRADAY">Intraday 5x</button>
                            </div>
                            <div class="ticket-segmented-control" id="ticket-order-type-control">
                                <button type="button" class="ticket-segment-btn active default-active" data-order-type="MARKET">Market</button>
                                <button type="button" class="ticket-segment-btn" data-order-type="LIMIT">Limit</button>
                            </div>
                        </div>

                        <!-- Limit Price Field (conditionally shown) -->
                        <div class="ticket-field-group" id="ticket-limit-price-group" style="display: none;">
                            <label class="ticket-field-label">Limit Price (₹)</label>
                            <div class="ticket-input-wrap">
                                <span class="ticket-currency-prefix">₹</span>
                                <input type="number" id="ticket-limit-price" class="ticket-input font-mono" step="0.05" value="2500.00" />
                            </div>
                        </div>

                        <!-- Quantity Stepper & Quick Chips -->
                        <div class="ticket-field-group">
                            <label class="ticket-field-label">Quantity (Shares)</label>
                            <div class="ticket-input-wrap">
                                <input type="number" id="ticket-qty-input" class="ticket-input font-mono" value="50" min="1" step="1" />
                            </div>
                            <div class="ticket-chips-row">
                                <button type="button" class="ticket-chip" data-add-qty="10">+10</button>
                                <button type="button" class="ticket-chip" data-add-qty="25">+25</button>
                                <button type="button" class="ticket-chip" data-add-qty="50">+50</button>
                                <button type="button" class="ticket-chip" data-add-qty="100">+100</button>
                                <button type="button" class="ticket-chip" data-add-qty="500">+500</button>
                            </div>
                        </div>

                        <!-- Risk Management (Take Profit & Stop Loss) -->
                        <div class="ticket-risk-card">
                            <div class="ticket-risk-row">
                                <label class="ticket-checkbox-lbl">
                                    <input type="checkbox" id="ticket-enable-tp" />
                                    <span>Target (TP)</span>
                                </label>
                                <div class="ticket-input-wrap">
                                    <span class="ticket-currency-prefix">₹</span>
                                    <input type="number" id="ticket-tp-price" class="ticket-input font-mono" placeholder="Target Price" step="0.05" disabled />
                                </div>
                            </div>

                            <div class="ticket-risk-row">
                                <label class="ticket-checkbox-lbl">
                                    <input type="checkbox" id="ticket-enable-sl" />
                                    <span>Stop Loss</span>
                                </label>
                                <div class="ticket-input-wrap">
                                    <span class="ticket-currency-prefix">₹</span>
                                    <input type="number" id="ticket-sl-price" class="ticket-input font-mono" placeholder="Stop Price" step="0.05" disabled />
                                </div>
                            </div>

                            <div class="ticket-risk-row">
                                <label class="ticket-checkbox-lbl">
                                    <input type="checkbox" id="ticket-enable-trailing" />
                                    <span>Trailing SL %</span>
                                </label>
                                <div class="ticket-input-wrap">
                                    <input type="number" id="ticket-trailing-pct" class="ticket-input font-mono" placeholder="e.g. 1.5" step="0.1" min="0.1" max="20" disabled />
                                    <span style="color: #64748B; font-size: 12px; margin-left: 4px;">%</span>
                                </div>
                            </div>
                        </div>

                        <!-- Statutory Cost & Financial Breakdown -->
                        <div class="ticket-calc-card">
                            <div class="ticket-calc-row">
                                <span>Order Value:</span>
                                <span class="val font-mono" id="ticket-calc-value">₹1,25,000.00</span>
                            </div>
                            <div class="ticket-calc-row">
                                <span>Margin Required:</span>
                                <span class="val font-mono" id="ticket-calc-margin">₹1,25,000.00</span>
                            </div>
                            <div class="ticket-calc-row">
                                <span>Est. Taxes & Fees (STT, GST, Exch):</span>
                                <span class="val font-mono" id="ticket-calc-charges">~₹160.00</span>
                            </div>
                            <div class="ticket-calc-row highlight">
                                <span>Available Virtual Balance:</span>
                                <span class="val font-mono" id="ticket-calc-balance">₹10,00,000.00</span>
                            </div>
                        </div>
                    </div>

                    <div class="order-ticket-footer">
                        <button type="button" class="ticket-cancel-btn" id="btn-ticket-cancel">Cancel</button>
                        <button type="button" class="ticket-submit-btn buy-mode" id="btn-ticket-submit">Execute BUY Order</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
        }
    }

    ensureToastContainer() {
        let toastBox = document.getElementById('paper-toast-container');
        if (!toastBox) {
            toastBox = document.createElement('div');
            toastBox.id = 'paper-toast-container';
            toastBox.className = 'paper-toast-container';
            document.body.appendChild(toastBox);
        }
    }

    // --------------------------------------------------------------------------
    // 2. Event Binding
    // --------------------------------------------------------------------------
    bindEvents() {
        // Quick Buy / Sell
        const btnBuy = document.getElementById('btn-quick-buy');
        const btnSell = document.getElementById('btn-quick-sell');
        const btnMinus = document.getElementById('btn-qty-minus');
        const btnPlus = document.getElementById('btn-qty-plus');
        const qtyInput = document.getElementById('quick-trade-qty');
        const btnGear = document.getElementById('btn-quick-order-ticket');
        const btnClosePos = document.getElementById('btn-quick-close-pos');

        if (btnBuy) {
            btnBuy.addEventListener('click', (e) => {
                e.preventDefault();
                const qty = parseInt(qtyInput ? qtyInput.value : '50', 10) || 50;
                this.placeQuickOrder('BUY', qty);
            });
        }

        if (btnSell) {
            btnSell.addEventListener('click', (e) => {
                e.preventDefault();
                const qty = parseInt(qtyInput ? qtyInput.value : '50', 10) || 50;
                this.placeQuickOrder('SELL', qty);
            });
        }

        if (btnMinus && qtyInput) {
            btnMinus.addEventListener('click', () => {
                let v = parseInt(qtyInput.value, 10) || 50;
                if (v > 1) {
                    qtyInput.value = Math.max(1, v - 10);
                    this.updateTicketCalculations();
                }
            });
        }

        if (btnPlus && qtyInput) {
            btnPlus.addEventListener('click', () => {
                let v = parseInt(qtyInput.value, 10) || 50;
                qtyInput.value = v + 10;
                this.updateTicketCalculations();
            });
        }

        if (btnGear) {
            btnGear.addEventListener('click', () => {
                this.openOrderTicket(this.ticketState.side);
            });
        }

        if (btnClosePos) {
            btnClosePos.addEventListener('click', () => {
                this.closeActivePosition();
            });
        }

        // Modal Controls
        const modalOverlay = document.getElementById('modal-order-ticket');
        const btnCloseTicket = document.getElementById('btn-close-ticket');
        const btnCancelTicket = document.getElementById('btn-ticket-cancel');
        const btnSubmitTicket = document.getElementById('btn-ticket-submit');

        if (btnCloseTicket) btnCloseTicket.addEventListener('click', () => this.closeOrderTicket());
        if (btnCancelTicket) btnCancelTicket.addEventListener('click', () => this.closeOrderTicket());
        if (modalOverlay) {
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) this.closeOrderTicket();
            });
        }

        // Side buttons
        document.querySelectorAll('#ticket-side-control .ticket-segment-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const side = e.currentTarget.dataset.side;
                this.setTicketSide(side);
            });
        });

        // Product (Delivery / Intraday)
        document.querySelectorAll('#ticket-product-control .ticket-segment-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('#ticket-product-control .ticket-segment-btn').forEach(b => b.classList.remove('active', 'default-active'));
                e.currentTarget.classList.add('active', 'default-active');
                this.ticketState.tradeType = e.currentTarget.dataset.product;
                this.updateTicketCalculations();
            });
        });

        // Order Type (Market / Limit)
        document.querySelectorAll('#ticket-order-type-control .ticket-segment-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('#ticket-order-type-control .ticket-segment-btn').forEach(b => b.classList.remove('active', 'default-active'));
                e.currentTarget.classList.add('active', 'default-active');
                const oType = e.currentTarget.dataset.orderType;
                this.ticketState.orderType = oType;
                const limGroup = document.getElementById('ticket-limit-price-group');
                if (limGroup) {
                    limGroup.style.display = (oType === 'LIMIT') ? 'flex' : 'none';
                }
                this.updateTicketCalculations();
            });
        });

        // Quick Qty Chips
        document.querySelectorAll('.ticket-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                const add = parseInt(e.currentTarget.dataset.addQty, 10) || 0;
                const input = document.getElementById('ticket-qty-input');
                if (input) {
                    input.value = (parseInt(input.value, 10) || 0) + add;
                    this.updateTicketCalculations();
                }
            });
        });

        const ticketQtyInput = document.getElementById('ticket-qty-input');
        if (ticketQtyInput) {
            ticketQtyInput.addEventListener('input', () => this.updateTicketCalculations());
        }

        const ticketLimitPrice = document.getElementById('ticket-limit-price');
        if (ticketLimitPrice) {
            ticketLimitPrice.addEventListener('input', () => this.updateTicketCalculations());
        }

        // SL & TP Checkbox Toggles
        const chkTP = document.getElementById('ticket-enable-tp');
        const inpTP = document.getElementById('ticket-tp-price');
        if (chkTP && inpTP) {
            chkTP.addEventListener('change', (e) => {
                inpTP.disabled = !e.target.checked;
                if (e.target.checked && !inpTP.value) {
                    const offset = this.ticketState.side === 'BUY' ? 1.03 : 0.97;
                    inpTP.value = (this.currentLTP * offset).toFixed(2);
                }
            });
        }

        const chkSL = document.getElementById('ticket-enable-sl');
        const inpSL = document.getElementById('ticket-sl-price');
        if (chkSL && inpSL) {
            chkSL.addEventListener('change', (e) => {
                inpSL.disabled = !e.target.checked;
                if (e.target.checked && !inpSL.value) {
                    const offset = this.ticketState.side === 'BUY' ? 0.98 : 1.02;
                    inpSL.value = (this.currentLTP * offset).toFixed(2);
                }
            });
        }

        const chkTrail = document.getElementById('ticket-enable-trailing');
        const inpTrail = document.getElementById('ticket-trailing-pct');
        if (chkTrail && inpTrail) {
            chkTrail.addEventListener('change', (e) => {
                inpTrail.disabled = !e.target.checked;
                if (e.target.checked && !inpTrail.value) {
                    inpTrail.value = '1.5';
                }
            });
        }

        // Submit Ticket
        if (btnSubmitTicket) {
            btnSubmitTicket.addEventListener('click', () => {
                this.submitAdvancedOrderTicket();
            });
        }
    }

    // --------------------------------------------------------------------------
    // 3. LTP & Price Label Synchronization
    // --------------------------------------------------------------------------
    updateLTP(price) {
        if (!price || isNaN(price) || price <= 0) return;
        this.currentLTP = Number(price);

        const buyPriceEl = document.getElementById('quick-buy-price');
        const sellPriceEl = document.getElementById('quick-sell-price');
        const ticketLtpEl = document.getElementById('ticket-ltp-display');

        // Slippage visual cue: 5 bps (0.05%)
        const buySlippagePrice = this.currentLTP * 1.0005;
        const sellSlippagePrice = this.currentLTP * 0.9995;

        if (buyPriceEl) buyPriceEl.textContent = `₹${buySlippagePrice.toFixed(2)}`;
        if (sellPriceEl) sellPriceEl.textContent = `₹${sellSlippagePrice.toFixed(2)}`;
        if (ticketLtpEl) ticketLtpEl.textContent = `₹${this.currentLTP.toFixed(2)}`;

        // Update live active position badge MTM P&L
        this.updatePositionBadgeMTM();
    }

    updatePositionBadgeMTM() {
        if (!this.activePosition) return;
        const badge = document.getElementById('quick-pos-badge');
        const pnlEl = document.getElementById('quick-pos-pnl');
        if (!badge || !pnlEl) return;

        const avgPrice = this.activePosition.average_price;
        const qty = this.activePosition.quantity;
        const isLong = (this.activePosition.side === 'LONG');

        const diff = isLong ? (this.currentLTP - avgPrice) : (avgPrice - this.currentLTP);
        const pnl = diff * qty;
        const costBasis = avgPrice * qty;
        const pct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;

        const sign = pnl >= 0 ? '+' : '';
        pnlEl.textContent = `${sign}₹${pnl.toFixed(2)} (${sign}${pct.toFixed(2)}%)`;
        pnlEl.className = `quick-pos-pnl font-mono ${pnl >= 0 ? 'positive' : 'negative'}`;
    }

    onSymbolOrCandlesChanged() {
        this.activeSymbol = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
        
        // Extract latest candle close as LTP if available
        if (window.allLoadedCandles && window.allLoadedCandles.length > 0) {
            const latest = window.allLoadedCandles[window.allLoadedCandles.length - 1];
            if (latest && latest.close) {
                this.updateLTP(latest.close);
            }
        }

        // Update symbol display in ticket modal
        const symEl = document.getElementById('ticket-symbol-display');
        if (symEl) symEl.textContent = this.activeSymbol;

        // Refresh position lines & markers for the new symbol
        this.refreshPositionsAndAccount();
    }

    // --------------------------------------------------------------------------
    // 4. Position Lines & Execution Markers Overlays
    // --------------------------------------------------------------------------
    async refreshPositionsAndAccount() {
        try {
            const [posRes, accRes] = await Promise.all([
                fetch('/api/v1/paper-trading/positions'),
                fetch('/api/v1/paper-trading/account')
            ]);

            if (posRes.ok) {
                const posData = await posRes.json();
                if (posData.success && Array.isArray(posData.data)) {
                    const currentPos = posData.data.find(p => p.symbol === this.activeSymbol);
                    this.activePosition = currentPos || null;
                    this.renderPositionLines(this.activePosition);
                }
            }

            if (accRes.ok) {
                const accData = await accRes.json();
                if (accData.success && accData.data) {
                    this.accountSummary = accData.data;
                    this.updateTicketCalculations();
                }
            }

            if (window.paperTerminalDock && typeof window.paperTerminalDock.refreshAll === 'function') {
                window.paperTerminalDock.refreshAll();
            }
        } catch (e) {
            console.warn('[ChartPaperTradeManager] Error refreshing state:', e);
        }
    }

    renderPositionLines(position) {
        const series = window.candleSeries;
        if (!series || typeof series.createPriceLine !== 'function') return;

        // 1. Remove existing lines cleanly
        this.clearPriceLines();

        const badge = document.getElementById('quick-pos-badge');
        const sideEl = document.getElementById('quick-pos-side');
        const qtyEl = document.getElementById('quick-pos-qty');

        if (!position) {
            if (badge) badge.style.display = 'none';
            return;
        }

        // Show active position badge
        if (badge) badge.style.display = 'inline-flex';
        if (sideEl) {
            sideEl.textContent = position.side;
            sideEl.className = `quick-pos-side ${position.side.toLowerCase()}`;
        }
        if (qtyEl) {
            qtyEl.textContent = `${position.quantity} Qty`;
        }
        this.updatePositionBadgeMTM();

        const isLong = position.side === 'LONG';
        const avgPrice = position.average_price;
        const qty = position.quantity;

        // 2. Entry Price Line: Color #2962FF (Royal Blue), Solid 2px
        this.activePriceLines.entry = series.createPriceLine({
            price: avgPrice,
            color: '#2962FF',
            lineWidth: 2,
            lineStyle: (typeof LightweightCharts !== 'undefined' && LightweightCharts.LineStyle) ? LightweightCharts.LineStyle.Solid : 0,
            axisLabelVisible: true,
            title: `Entry: ₹${avgPrice.toFixed(2)} (${qty} Qty)`
        });

        // 3. Take-Profit (Target) Line: Color #089981 (Teal Green), Dashed 2px
        if (position.take_profit && position.take_profit > 0) {
            const tpGain = isLong ? (position.take_profit - avgPrice) * qty : (avgPrice - position.take_profit) * qty;
            const gainSign = tpGain >= 0 ? '+' : '';
            this.activePriceLines.target = series.createPriceLine({
                price: position.take_profit,
                color: '#089981',
                lineWidth: 2,
                lineStyle: (typeof LightweightCharts !== 'undefined' && LightweightCharts.LineStyle) ? LightweightCharts.LineStyle.Dashed : 2,
                axisLabelVisible: true,
                title: `Target: ₹${position.take_profit.toFixed(2)} (${gainSign}₹${tpGain.toFixed(2)})`
            });
        }

        // 4. Stop-Loss Line: Color #F23645 (Vibrant Red), Dashed 2px
        if (position.stop_loss && position.stop_loss > 0) {
            const slLoss = isLong ? (position.stop_loss - avgPrice) * qty : (avgPrice - position.stop_loss) * qty;
            this.activePriceLines.stopLoss = series.createPriceLine({
                price: position.stop_loss,
                color: '#F23645',
                lineWidth: 2,
                lineStyle: (typeof LightweightCharts !== 'undefined' && LightweightCharts.LineStyle) ? LightweightCharts.LineStyle.Dashed : 2,
                axisLabelVisible: true,
                title: `Stop Loss: ₹${position.stop_loss.toFixed(2)} (₹${slLoss.toFixed(2)})`
            });
        }
    }

    clearPriceLines() {
        const series = window.candleSeries;
        if (!series || typeof series.removePriceLine !== 'function') return;

        if (this.activePriceLines.entry) {
            try { series.removePriceLine(this.activePriceLines.entry); } catch (e) {}
            this.activePriceLines.entry = null;
        }
        if (this.activePriceLines.target) {
            try { series.removePriceLine(this.activePriceLines.target); } catch (e) {}
            this.activePriceLines.target = null;
        }
        if (this.activePriceLines.stopLoss) {
            try { series.removePriceLine(this.activePriceLines.stopLoss); } catch (e) {}
            this.activePriceLines.stopLoss = null;
        }
    }

    // --------------------------------------------------------------------------
    // 5. Order Placement (Quick & Advanced)
    // --------------------------------------------------------------------------
    async placeQuickOrder(side, quantity, tradeType = 'DELIVERY') {
        if (this.isSubmitting) return;
        this.isSubmitting = true;

        const payload = {
            symbol: this.activeSymbol,
            side: side.toUpperCase(),
            quantity: quantity,
            order_type: 'MARKET',
            trade_type: tradeType,
            price: this.currentLTP
        };

        try {
            const res = await fetch('/api/v1/paper-trading/orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.success) {
                const fill = data.data;
                this.showToast(
                    `${side} Order Executed!`,
                    `Filled ${quantity}x ${this.activeSymbol} at ₹${fill.fill_price.toFixed(2)} (Fees: ₹${fill.total_charges.toFixed(2)})`,
                    'success'
                );
                await this.refreshPositionsAndAccount();
            } else {
                const errorMsg = data.detail || data.message || 'Order rejected by trading engine.';
                this.showToast('Order Rejected', errorMsg, 'error');
            }
        } catch (e) {
            this.showToast('Network Error', e.message || 'Unable to connect to paper trading engine', 'error');
        } finally {
            this.isSubmitting = false;
        }
    }

    async closeActivePosition() {
        if (!this.activePosition || this.isSubmitting) return;
        this.isSubmitting = true;

        try {
            const res = await fetch(`/api/v1/paper-trading/positions/${encodeURIComponent(this.activeSymbol)}/close?exit_price=${this.currentLTP}`, {
                method: 'DELETE'
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.showToast(
                    'Position Squared Off',
                    `Closed ${this.activePosition.quantity}x ${this.activeSymbol} at ₹${data.data.fill_price.toFixed(2)}`,
                    'success'
                );
                this.activePosition = null;
                this.renderPositionLines(null);
                await this.refreshPositionsAndAccount();
            } else {
                this.showToast('Square Off Failed', data.detail || 'Could not close position', 'error');
            }
        } catch (e) {
            this.showToast('Network Error', e.message, 'error');
        } finally {
            this.isSubmitting = false;
        }
    }

    // --------------------------------------------------------------------------
    // 6. Advanced Order Ticket Dialog
    // --------------------------------------------------------------------------
    openOrderTicket(defaultSide = 'BUY') {
        const overlay = document.getElementById('modal-order-ticket');
        if (!overlay) return;

        this.setTicketSide(defaultSide);
        const qtyInp = document.getElementById('ticket-qty-input');
        const quickQty = document.getElementById('quick-trade-qty');
        if (qtyInp && quickQty) {
            qtyInp.value = quickQty.value || '50';
        }

        const limInp = document.getElementById('ticket-limit-price');
        if (limInp) limInp.value = this.currentLTP.toFixed(2);

        this.updateTicketCalculations();
        overlay.classList.add('open');
    }

    closeOrderTicket() {
        const overlay = document.getElementById('modal-order-ticket');
        if (overlay) overlay.classList.remove('open');
    }

    setTicketSide(side) {
        this.ticketState.side = side;
        const sideBtns = document.querySelectorAll('#ticket-side-control .ticket-segment-btn');
        const submitBtn = document.getElementById('btn-ticket-submit');

        sideBtns.forEach(btn => {
            btn.classList.remove('active', 'buy-active', 'sell-active');
            if (btn.dataset.side === side) {
                btn.classList.add('active', side === 'BUY' ? 'buy-active' : 'sell-active');
            }
        });

        if (submitBtn) {
            submitBtn.textContent = `Execute ${side} Order`;
            submitBtn.className = `ticket-submit-btn ${side === 'BUY' ? 'buy-mode' : 'sell-mode'}`;
        }

        this.updateTicketCalculations();
    }

    updateTicketCalculations() {
        const qtyInp = document.getElementById('ticket-qty-input');
        const qty = parseInt(qtyInp ? qtyInp.value : '50', 10) || 50;

        const isLimit = (this.ticketState.orderType === 'LIMIT');
        const limInp = document.getElementById('ticket-limit-price');
        const price = isLimit && limInp ? (parseFloat(limInp.value) || this.currentLTP) : this.currentLTP;

        const isIntraday = (this.ticketState.tradeType === 'INTRADAY');
        const orderVal = price * qty;
        const marginReq = isIntraday ? (orderVal / 5.0) : orderVal;

        // Estimated taxes: STT (0.1% delivery, 0.025% intraday sell), stamp duty (0.015%), brokerage ₹20, GST 18%
        const estTaxes = Math.max(25.0, (orderVal * (isIntraday ? 0.0003 : 0.0013)) + 23.6);

        const valEl = document.getElementById('ticket-calc-value');
        const marginEl = document.getElementById('ticket-calc-margin');
        const chargesEl = document.getElementById('ticket-calc-charges');
        const balEl = document.getElementById('ticket-calc-balance');

        if (valEl) valEl.textContent = `₹${orderVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (marginEl) marginEl.textContent = `₹${marginReq.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (chargesEl) chargesEl.textContent = `~₹${estTaxes.toFixed(2)}`;

        const availBal = this.accountSummary ? this.accountSummary.available_balance : 1000000.0;
        if (balEl) balEl.textContent = `₹${availBal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    async submitAdvancedOrderTicket() {
        if (this.isSubmitting) return;

        const qtyInp = document.getElementById('ticket-qty-input');
        const quantity = parseInt(qtyInp ? qtyInp.value : '50', 10) || 50;

        const isLimit = (this.ticketState.orderType === 'LIMIT');
        const limInp = document.getElementById('ticket-limit-price');
        const limitPrice = isLimit && limInp ? parseFloat(limInp.value) : null;

        const chkTP = document.getElementById('ticket-enable-tp');
        const inpTP = document.getElementById('ticket-tp-price');
        const takeProfit = (chkTP && chkTP.checked && inpTP && inpTP.value) ? parseFloat(inpTP.value) : null;

        const chkSL = document.getElementById('ticket-enable-sl');
        const inpSL = document.getElementById('ticket-sl-price');
        const stopLoss = (chkSL && chkSL.checked && inpSL && inpSL.value) ? parseFloat(inpSL.value) : null;

        const chkTrail = document.getElementById('ticket-enable-trailing');
        const inpTrail = document.getElementById('ticket-trailing-pct');
        const trailingPct = (chkTrail && chkTrail.checked && inpTrail && inpTrail.value) ? parseFloat(inpTrail.value) : null;

        const payload = {
            symbol: this.activeSymbol,
            side: this.ticketState.side,
            quantity: quantity,
            order_type: this.ticketState.orderType,
            trade_type: this.ticketState.tradeType,
            price: limitPrice || this.currentLTP,
            stop_loss: stopLoss,
            take_profit: takeProfit,
            trailing_sl_pct: trailingPct
        };

        this.isSubmitting = true;
        try {
            const res = await fetch('/api/v1/paper-trading/orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.success) {
                this.closeOrderTicket();
                this.showToast(
                    `${this.ticketState.side} Order Executed`,
                    `Filled ${quantity}x ${this.activeSymbol} at ₹${data.data.fill_price.toFixed(2)}`,
                    'success'
                );
                await this.refreshPositionsAndAccount();
            } else {
                this.showToast('Order Failed', data.detail || 'Could not place order', 'error');
            }
        } catch (e) {
            this.showToast('Network Error', e.message, 'error');
        } finally {
            this.isSubmitting = false;
        }
    }

    // --------------------------------------------------------------------------
    // 7. Toast Notification Utility
    // --------------------------------------------------------------------------
    showToast(title, message, type = 'success') {
        const container = document.getElementById('paper-toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `paper-toast ${type}`;
        const icon = type === 'success' ? '✅' : '❌';

        toast.innerHTML = `
            <span class="paper-toast-icon">${icon}</span>
            <div class="paper-toast-content">
                <div class="paper-toast-title">${title}</div>
                <div class="paper-toast-msg">${message}</div>
            </div>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
}

// Global Instantiation on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.chartPaperTradeManager = new ChartPaperTradeManager();
});
