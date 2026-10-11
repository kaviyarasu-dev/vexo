/**
 * options_ui.js
 * Advanced Options Chain, Real-time Black-Scholes Greeks, Max Pain & Strategy Payoff Simulator
 */

class OptionsUI {
    constructor() {
        this.activeSymbol = 'NSE:NIFTY50-INDEX';
        this.currentSpot = 25050;
        this.matrix = [];
        this.maxPainData = null;
        this.strategyLegs = [];
        this.hasCustomLegs = false;
        this.activeSubtab = 'matrix'; // 'matrix' or 'payoff'
        this.expandedStrikes = new Set();
        this.toastTimeout = null;

        this.lotSizes = {
            'NSE:NIFTY50-INDEX': 25,
            'NSE:NIFTYBANK-INDEX': 15,
            'NSE:FINNIFTY-INDEX': 25,
            'NSE:RELIANCE-EQ': 250,
            'NSE:TCS-EQ': 175,
            'NSE:INFY-EQ': 400,
            'NSE:HDFCBANK-EQ': 550
        };
    }

    init() {
        this.bindEvents();
        this.loadOptionsData(this.activeSymbol, true);
    }

    getLotSize(symbol) {
        return this.lotSizes[symbol] || 50;
    }

    bindEvents() {
        const select = document.getElementById('options-symbol-select');
        if (select) {
            select.addEventListener('change', (e) => {
                this.activeSymbol = e.target.value;
                this.expandedStrikes.clear();
                this.strategyLegs = [];
                this.hasCustomLegs = false;
                this.loadOptionsData(this.activeSymbol, true);
            });
        }

        const refreshBtn = document.getElementById('btn-options-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadOptionsData(this.activeSymbol, false);
            });
        }

        // Subtabs: Matrix vs Payoff
        document.querySelectorAll('.options-subtab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                document.querySelectorAll('.options-subtab').forEach(t => t.classList.remove('active'));
                e.currentTarget.classList.add('active');
                const target = e.currentTarget.dataset.subtab;
                this.activeSubtab = target;

                const matrixPanel = document.getElementById('options-matrix-panel');
                const payoffPanel = document.getElementById('options-payoff-panel');
                if (target === 'matrix') {
                    matrixPanel?.classList.remove('hidden');
                    payoffPanel?.classList.add('hidden');
                } else {
                    matrixPanel?.classList.add('hidden');
                    payoffPanel?.classList.remove('hidden');
                    this.renderPayoffSimulator();
                }
            });
        });

        // Add Leg Button in Simulator
        document.getElementById('btn-add-leg')?.addEventListener('click', () => {
            this.addStrategyLeg();
        });

        // Clear All Legs Button
        document.getElementById('btn-clear-legs')?.addEventListener('click', () => {
            this.clearAllLegs();
        });

        // Strategy Presets in Simulator
        document.querySelectorAll('.strategy-preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const preset = e.currentTarget.dataset.preset;
                this.hasCustomLegs = false;
                this.applyStrategyPreset(preset);
            });
        });
    }

    clearAllLegs() {
        this.strategyLegs = [];
        this.hasCustomLegs = true;
        this.renderLegsTable();
        this.updateStrategyLegsBadge();
        this.calculateAndDrawPayoff();
        this.showToast('Cleared all legs from Strategy Simulator.');
    }

    async loadOptionsData(symbol, isNewSymbol = false) {
        const statusEl = document.getElementById('options-loading-indicator');
        if (statusEl) statusEl.classList.remove('hidden');

        try {
            const [chainRes, maxPainRes] = await Promise.all([
                fetch(`/api/v1/options/chain?symbol=${encodeURIComponent(symbol)}`).then(r => r.json()),
                fetch(`/api/v1/options/maxpain?symbol=${encodeURIComponent(symbol)}`).then(r => r.json())
            ]);

            if (chainRes.success && chainRes.data) {
                this.matrix = chainRes.data.matrix || [];
                this.currentSpot = chainRes.data.spot || 25000;
                this.expiryDate = chainRes.data.expiry_date || '';
                this.renderDedicatedMetrics(chainRes.data, maxPainRes.data);
                this.renderStrikeMatrix();
            }

            if (maxPainRes.success && maxPainRes.data) {
                this.maxPainData = maxPainRes.data;
                this.renderMaxPainChart();
            }

            // Sync strategy legs to the current symbol's spot and strike step
            if (!this.hasCustomLegs) {
                if (isNewSymbol || this.strategyLegs.length === 0) {
                    this.applyStrategyPreset('bull_call');
                }
            } else {
                this.calculateAndDrawPayoff();
            }

            this.updateStrategyLegsBadge();
        } catch (e) {
            console.error("Failed to fetch options data:", e);
        } finally {
            if (statusEl) statusEl.classList.add('hidden');
        }
    }

    renderDedicatedMetrics(chainData, maxPainData) {
        // Tab 1 (Strike Matrix) Dedicated Metrics
        const spotEl = document.getElementById('options-spot-val');
        const pcrEl = document.getElementById('options-pcr-val');
        const atmIvEl = document.getElementById('options-atm-iv-val');
        const expiryEl = document.getElementById('options-expiry-val');

        if (spotEl) spotEl.textContent = `₹${Number(this.currentSpot).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        if (expiryEl) expiryEl.textContent = this.expiryDate || 'Weekly';

        // PCR Calculation & ATM IV
        let totalCallOI = 0;
        let totalPutOI = 0;
        let minDiff = Infinity;
        let atmStrike = 0;
        let atmIv = 0;

        this.matrix.forEach(row => {
            if (row.call && row.call.oi) totalCallOI += row.call.oi;
            if (row.put && row.put.oi) totalPutOI += row.put.oi;

            const diff = Math.abs(row.strike_price - this.currentSpot);
            if (diff < minDiff) {
                minDiff = diff;
                atmStrike = row.strike_price;
                atmIv = (row.call && row.call.iv) ? row.call.iv : ((row.put && row.put.iv) ? row.put.iv : 15.0);
            }
        });

        const pcr = totalCallOI > 0 ? (totalPutOI / totalCallOI).toFixed(2) : '1.00';
        if (pcrEl) {
            const sentiment = pcr > 1.2 ? '(Bullish)' : (pcr < 0.8 ? '(Bearish)' : '(Neutral)');
            pcrEl.textContent = `${pcr} ${sentiment}`;
        }

        if (atmIvEl) {
            atmIvEl.textContent = `₹${Number(atmStrike).toLocaleString()} (${atmIv.toFixed(1)}% IV)`;
        }

        // Tab 2 (Max Pain & Simulator) Dedicated Metrics
        const maxPainEl = document.getElementById('options-maxpain-val');
        if (maxPainEl && maxPainData) {
            maxPainEl.textContent = `₹${Number(maxPainData.max_pain_strike).toLocaleString('en-IN')}`;
        }
    }

    renderStrikeMatrix() {
        const tbody = document.querySelector('#options-matrix-table tbody');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (this.matrix.length === 0) {
            tbody.innerHTML = `<tr><td colspan="19" class="text-center p-4">No options data available for this symbol.</td></tr>`;
            return;
        }

        // Find ATM strike
        let minDiff = Infinity;
        let atmStrike = 0;
        this.matrix.forEach(r => {
            const diff = Math.abs(r.strike_price - this.currentSpot);
            if (diff < minDiff) {
                minDiff = diff;
                atmStrike = r.strike_price;
            }
        });

        const lotSize = this.getLotSize(this.activeSymbol);

        this.matrix.forEach(r => {
            const tr = document.createElement('tr');
            const isAtm = (r.strike_price === atmStrike);
            if (isAtm) tr.className = 'atm-row';

            const c = r.call || {};
            const p = r.put || {};

            const cItm = r.strike_price < this.currentSpot;
            const pItm = r.strike_price > this.currentSpot;
            const isExpanded = this.expandedStrikes.has(r.strike_price);

            tr.innerHTML = `
                <!-- CALLS -->
                <td class="text-center">
                    <button class="btn-leg-add call-add ${isExpanded ? 'expanded' : ''}" title="${isExpanded ? 'Collapse additional details' : 'Expand contract details & Greeks'}" data-strike="${r.strike_price}">${isExpanded ? '−' : '+'}</button>
                </td>
                <td class="font-mono text-right greeks-cell ${cItm ? 'itm-cell' : ''}">${(c.delta !== undefined) ? c.delta.toFixed(3) : '—'}</td>
                <td class="font-mono text-right greeks-cell ${cItm ? 'itm-cell' : ''}">${(c.gamma !== undefined) ? c.gamma.toFixed(4) : '—'}</td>
                <td class="font-mono text-right greeks-cell ${cItm ? 'itm-cell' : ''}">${(c.theta !== undefined) ? c.theta.toFixed(1) : '—'}</td>
                <td class="font-mono text-right greeks-cell ${cItm ? 'itm-cell' : ''}">${(c.vega !== undefined) ? c.vega.toFixed(2) : '—'}</td>
                <td class="font-mono text-right ${cItm ? 'itm-cell' : ''}">${c.iv ? c.iv.toFixed(1) + '%' : '—'}</td>
                <td class="font-mono text-right ${cItm ? 'itm-cell' : ''}">${c.oi ? c.oi.toLocaleString() : '0'}</td>
                <td class="font-mono text-right ${cItm ? 'itm-cell' : ''}">${c.volume ? c.volume.toLocaleString() : '0'}</td>
                <td class="font-mono text-right font-bold call-price ${cItm ? 'itm-cell' : ''}">₹${(c.ltp || 0).toFixed(2)}</td>

                <!-- STRIKE -->
                <td class="text-center font-mono strike-cell ${isAtm ? 'atm-badge' : ''}" style="cursor: pointer;" title="Click strike to view additional details">
                    <strong>${r.strike_price.toLocaleString()}</strong>
                    ${isAtm ? '<span class="atm-tag">ATM</span>' : ''}
                </td>

                <!-- PUTS -->
                <td class="font-mono text-right font-bold put-price ${pItm ? 'itm-cell' : ''}">₹${(p.ltp || 0).toFixed(2)}</td>
                <td class="font-mono text-right ${pItm ? 'itm-cell' : ''}">${p.volume ? p.volume.toLocaleString() : '0'}</td>
                <td class="font-mono text-right ${pItm ? 'itm-cell' : ''}">${p.oi ? p.oi.toLocaleString() : '0'}</td>
                <td class="font-mono text-right ${pItm ? 'itm-cell' : ''}">${p.iv ? p.iv.toFixed(1) + '%' : '—'}</td>
                <td class="font-mono text-right greeks-cell ${pItm ? 'itm-cell' : ''}">${(p.delta !== undefined) ? p.delta.toFixed(3) : '—'}</td>
                <td class="font-mono text-right greeks-cell ${pItm ? 'itm-cell' : ''}">${(p.gamma !== undefined) ? p.gamma.toFixed(4) : '—'}</td>
                <td class="font-mono text-right greeks-cell ${pItm ? 'itm-cell' : ''}">${(p.theta !== undefined) ? p.theta.toFixed(1) : '—'}</td>
                <td class="font-mono text-right greeks-cell ${pItm ? 'itm-cell' : ''}">${(p.vega !== undefined) ? p.vega.toFixed(2) : '—'}</td>
                <td class="text-center">
                    <button class="btn-leg-add put-add ${isExpanded ? 'expanded' : ''}" title="${isExpanded ? 'Collapse additional details' : 'Expand contract details & Greeks'}" data-strike="${r.strike_price}">${isExpanded ? '−' : '+'}</button>
                </td>
            `;

            // Toggle expansion on '+' button or strike click
            const toggleHandler = () => {
                if (this.expandedStrikes.has(r.strike_price)) {
                    this.expandedStrikes.delete(r.strike_price);
                } else {
                    this.expandedStrikes.add(r.strike_price);
                }
                this.renderStrikeMatrix();
            };

            tr.querySelectorAll('.btn-leg-add').forEach(btn => {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    toggleHandler();
                };
            });

            const strikeCell = tr.querySelector('.strike-cell');
            if (strikeCell) {
                strikeCell.onclick = toggleHandler;
            }

            tbody.appendChild(tr);

            // Render Accordion Additional Details Row if expanded
            if (isExpanded) {
                const detailsTr = document.createElement('tr');
                detailsTr.className = 'strike-details-row';

                // Financial computations
                const diffFromSpot = r.strike_price - this.currentSpot;
                const diffPct = (diffFromSpot / this.currentSpot) * 100;

                const cIntrinsic = Math.max(0, this.currentSpot - r.strike_price);
                const cExtrinsic = Math.max(0, (c.ltp || 0) - cIntrinsic);
                const cMoneynessText = isAtm ? 'ATM' : (cItm ? `ITM (+${Math.abs(diffFromSpot).toFixed(1)} pts)` : `OTM (-${Math.abs(diffFromSpot).toFixed(1)} pts)`);

                const pIntrinsic = Math.max(0, r.strike_price - this.currentSpot);
                const pExtrinsic = Math.max(0, (p.ltp || 0) - pIntrinsic);
                const pMoneynessText = isAtm ? 'ATM' : (pItm ? `ITM (+${Math.abs(diffFromSpot).toFixed(1)} pts)` : `OTM (-${Math.abs(diffFromSpot).toFixed(1)} pts)`);

                detailsTr.innerHTML = `
                    <td colspan="19">
                        <div class="strike-details-container">
                            <!-- CALL SIDE -->
                            <div class="details-side-card call-side">
                                <div class="side-header">
                                    <div>
                                        <span class="side-badge ce-badge">CALL (CE)</span>
                                        <strong>₹${r.strike_price.toLocaleString()} CE</strong>
                                        <span class="moneyness-badge ${isAtm ? 'badge-atm' : (cItm ? 'badge-itm' : 'badge-otm')}">${cMoneynessText}</span>
                                    </div>
                                    <div class="side-ltp font-mono">₹${(c.ltp || 0).toFixed(2)}</div>
                                </div>
                                <div class="side-metrics-grid">
                                    <div class="detail-metric">
                                        <span class="d-label">Intrinsic Value:</span>
                                        <span class="d-val font-mono">₹${cIntrinsic.toFixed(2)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Time Value:</span>
                                        <span class="d-val font-mono">₹${cExtrinsic.toFixed(2)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Bid / Ask:</span>
                                        <span class="d-val font-mono">₹${(c.bid || c.ltp || 0).toFixed(2)} / ₹${(c.ask || c.ltp || 0).toFixed(2)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Lot Size:</span>
                                        <span class="d-val font-mono">${lotSize} Qty</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Delta / Gamma:</span>
                                        <span class="d-val font-mono">${(c.delta || 0).toFixed(3)} / ${(c.gamma || 0).toFixed(4)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Theta / Vega:</span>
                                        <span class="d-val font-mono">-₹${Math.abs(c.theta || 0).toFixed(1)}/day / ₹${(c.vega || 0).toFixed(2)}</span>
                                    </div>
                                </div>
                                <div class="side-actions">
                                    <button type="button" class="btn-strategy-action btn-strategy-buy" data-strike="${r.strike_price}" data-type="CE" data-pos="LONG" data-ltp="${c.ltp || 0}">
                                        🟢 + Buy Call
                                    </button>
                                    <button type="button" class="btn-strategy-action btn-strategy-sell" data-strike="${r.strike_price}" data-type="CE" data-pos="SHORT" data-ltp="${c.ltp || 0}">
                                        🔴 - Sell Call
                                    </button>
                                </div>
                            </div>

                            <!-- CENTER DIVIDER -->
                            <div class="details-divider">
                                <div class="divider-strike font-mono">₹${r.strike_price.toLocaleString()}</div>
                                <div class="divider-diff ${diffFromSpot >= 0 ? 'text-green' : 'text-red'} font-mono">
                                    ${diffFromSpot >= 0 ? '+' : ''}${diffFromSpot.toFixed(1)} pts (${diffPct.toFixed(2)}%)
                                </div>
                            </div>

                            <!-- PUT SIDE -->
                            <div class="details-side-card put-side">
                                <div class="side-header">
                                    <div>
                                        <span class="side-badge pe-badge">PUT (PE)</span>
                                        <strong>₹${r.strike_price.toLocaleString()} PE</strong>
                                        <span class="moneyness-badge ${isAtm ? 'badge-atm' : (pItm ? 'badge-itm' : 'badge-otm')}">${pMoneynessText}</span>
                                    </div>
                                    <div class="side-ltp font-mono">₹${(p.ltp || 0).toFixed(2)}</div>
                                </div>
                                <div class="side-metrics-grid">
                                    <div class="detail-metric">
                                        <span class="d-label">Intrinsic Value:</span>
                                        <span class="d-val font-mono">₹${pIntrinsic.toFixed(2)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Time Value:</span>
                                        <span class="d-val font-mono">₹${pExtrinsic.toFixed(2)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Bid / Ask:</span>
                                        <span class="d-val font-mono">₹${(p.bid || p.ltp || 0).toFixed(2)} / ₹${(p.ask || p.ltp || 0).toFixed(2)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Lot Size:</span>
                                        <span class="d-val font-mono">${lotSize} Qty</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Delta / Gamma:</span>
                                        <span class="d-val font-mono">${(p.delta || 0).toFixed(3)} / ${(p.gamma || 0).toFixed(4)}</span>
                                    </div>
                                    <div class="detail-metric">
                                        <span class="d-label">Theta / Vega:</span>
                                        <span class="d-val font-mono">-₹${Math.abs(p.theta || 0).toFixed(1)}/day / ₹${(p.vega || 0).toFixed(2)}</span>
                                    </div>
                                </div>
                                <div class="side-actions">
                                    <button type="button" class="btn-strategy-action btn-strategy-buy" data-strike="${r.strike_price}" data-type="PE" data-pos="LONG" data-ltp="${p.ltp || 0}">
                                        🟢 + Buy Put
                                    </button>
                                    <button type="button" class="btn-strategy-action btn-strategy-sell" data-strike="${r.strike_price}" data-type="PE" data-pos="SHORT" data-ltp="${p.ltp || 0}">
                                        🔴 - Sell Put
                                    </button>
                                </div>
                            </div>
                        </div>
                    </td>
                `;

                // Wire Buy/Sell action buttons inside details card
                detailsTr.querySelectorAll('.btn-strategy-action').forEach(btn => {
                    btn.onclick = () => {
                        const strike = Number(btn.dataset.strike);
                        const optType = btn.dataset.type;
                        const position = btn.dataset.pos;
                        const ltp = Number(btn.dataset.ltp);
                        this.addLegToStrategy(strike, optType, position, ltp);
                    };
                });

                tbody.appendChild(detailsTr);
            }
        });
    }

    addLegToStrategy(strike, optType, position, premium) {
        // If user hasn't created custom legs yet, start fresh with user's selected leg
        if (!this.hasCustomLegs) {
            this.strategyLegs = [];
            this.hasCustomLegs = true;
        }

        this.strategyLegs.push({
            strike: strike,
            option_type: optType,
            position: position,
            premium: premium,
            quantity: 1,
            isNew: true
        });

        this.updateStrategyLegsBadge();
        this.calculateAndDrawPayoff();

        // Show friendly toast notification
        const actionLabel = position === 'LONG' ? 'BUY' : 'SELL';
        this.showToast(`Added <strong>₹${strike.toLocaleString()} ${optType}</strong> (${actionLabel} @ ₹${premium.toFixed(2)}) to Strategy Simulator.`);
    }

    updateStrategyLegsBadge() {
        const badge = document.getElementById('strategy-legs-badge');
        if (!badge) return;

        const count = this.strategyLegs.length;
        if (count > 0) {
            badge.textContent = `${count} ${count === 1 ? 'Leg' : 'Legs'}`;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    showToast(messageHtml) {
        const toast = document.getElementById('options-toast');
        if (!toast) return;

        if (this.toastTimeout) clearTimeout(this.toastTimeout);

        toast.innerHTML = `
            <span>${messageHtml}</span>
            <a class="toast-link" id="btn-toast-view-payoff">View in Simulator →</a>
        `;
        toast.classList.remove('hidden');

        const viewLink = document.getElementById('btn-toast-view-payoff');
        if (viewLink) {
            viewLink.onclick = () => {
                toast.classList.add('hidden');
                document.querySelector('.options-subtab[data-subtab="payoff"]')?.click();
                setTimeout(() => {
                    const viewContainer = document.querySelector('#view-options .view-container');
                    const card = document.getElementById('strategy-builder-card');
                    if (viewContainer && card) {
                        const targetTop = card.offsetTop - 15;
                        viewContainer.scrollTo({
                            top: Math.max(0, targetTop),
                            behavior: 'smooth'
                        });
                    }
                }, 60);
            };
        }

        this.toastTimeout = setTimeout(() => {
            toast.classList.add('hidden');
        }, 5000);
    }

    renderMaxPainChart() {
        const container = document.getElementById('maxpain-chart-container');
        if (!container || !this.maxPainData) return;

        const strikes = this.maxPainData.strikes || [];
        const payouts = this.maxPainData.payout_curve || [];
        const mpStrike = this.maxPainData.max_pain_strike;

        if (payouts.length === 0) return;

        // Find min and max payout for normalization
        let minPayout = Infinity;
        let maxPayout = -Infinity;
        payouts.forEach(p => {
            if (p.payout < minPayout) minPayout = p.payout;
            if (p.payout > maxPayout) maxPayout = p.payout;
        });

        const width = container.clientWidth || 800;
        const height = 180;
        const padding = { top: 20, right: 30, bottom: 35, left: 60 };

        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        // Build SVG
        let barsHtml = '';
        const barWidth = Math.max(6, Math.floor(chartW / payouts.length) - 4);

        payouts.forEach((pt, idx) => {
            const x = padding.left + idx * (chartW / payouts.length) + 2;
            const normHeight = maxPayout > minPayout ? ((pt.payout - minPayout) / (maxPayout - minPayout)) * chartH : 20;
            const y = padding.top + (chartH - normHeight);
            const isMp = (pt.strike === mpStrike);

            barsHtml += `
                <rect x="${x}" y="${y}" width="${barWidth}" height="${normHeight}" 
                      fill="${isMp ? '#089981' : '#2A2E39'}" rx="2" 
                      class="maxpain-bar ${isMp ? 'active-mp-bar' : ''}" 
                      title="Strike ₹${pt.strike} | Total Payout: ₹${Number(pt.payout).toLocaleString()}">
                </rect>
                ${(idx % 3 === 0 || isMp) ? `
                    <text x="${x + barWidth / 2}" y="${height - 10}" 
                          fill="${isMp ? '#089981' : '#787B86'}" font-size="10" 
                          text-anchor="middle" font-weight="${isMp ? 'bold' : 'normal'}">
                        ${pt.strike}
                    </text>
                ` : ''}
            `;
        });

        container.innerHTML = `
            <div class="maxpain-header">
                <div>
                    <strong>Option Expiration Max Pain: ₹${Number(mpStrike).toLocaleString()}</strong>
                    <span class="badge-accent">Minimum Seller Payout Strike</span>
                </div>
                <div class="text-muted text-sm">Underlying Spot: ₹${Number(this.currentSpot).toLocaleString()}</div>
            </div>
            <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: ${height}px; overflow: visible;">
                ${barsHtml}
            </svg>
        `;
    }

    renderPayoffSimulator() {
        this.renderLegsTable();
        this.calculateAndDrawPayoff();
    }

    renderLegsTable() {
        const tbody = document.querySelector('#strategy-legs-table tbody');
        if (!tbody) return;

        tbody.innerHTML = '';
        if (this.strategyLegs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center p-3 text-muted">No strategy legs configured. Click a preset or Add Leg from the Strike Matrix.</td></tr>`;
            return;
        }

        const step = this.currentSpot > 10000 ? 100 : (this.currentSpot > 2000 ? 50 : 20);

        this.strategyLegs.forEach((leg, idx) => {
            const tr = document.createElement('tr');
            tr.className = `strategy-leg-row ${leg.isNew ? 'new-leg-highlight' : ''}`;

            tr.innerHTML = `
                <td>
                    <select class="leg-input leg-pos" data-idx="${idx}">
                        <option value="LONG" ${leg.position === 'LONG' ? 'selected' : ''}>BUY (+)</option>
                        <option value="SHORT" ${leg.position === 'SHORT' ? 'selected' : ''}>SELL (-)</option>
                    </select>
                    ${leg.isNew ? '<span class="badge-just-added">Just Added</span>' : ''}
                </td>
                <td>
                    <select class="leg-input leg-type" data-idx="${idx}">
                        <option value="CE" ${leg.option_type === 'CE' ? 'selected' : ''}>CALL (CE)</option>
                        <option value="PE" ${leg.option_type === 'PE' ? 'selected' : ''}>PUT (PE)</option>
                    </select>
                </td>
                <td>
                    <input type="number" class="leg-input leg-strike" data-idx="${idx}" value="${leg.strike}" step="${step}" style="width: 100px;">
                </td>
                <td>
                    <input type="number" class="leg-input leg-premium" data-idx="${idx}" value="${leg.premium}" step="0.05" style="width: 85px;">
                </td>
                <td>
                    <input type="number" class="leg-input leg-qty" data-idx="${idx}" value="${leg.quantity || 1}" min="1" style="width: 60px;">
                </td>
                <td class="text-center">
                    <button class="btn-remove-leg" data-idx="${idx}" title="Remove Leg">✕</button>
                </td>
            `;

            // Bind change handlers
            tr.querySelectorAll('.leg-input').forEach(input => {
                input.onchange = (e) => {
                    const i = Number(e.target.dataset.idx);
                    if (e.target.classList.contains('leg-pos')) this.strategyLegs[i].position = e.target.value;
                    if (e.target.classList.contains('leg-type')) this.strategyLegs[i].option_type = e.target.value;
                    if (e.target.classList.contains('leg-strike')) this.strategyLegs[i].strike = Number(e.target.value);
                    if (e.target.classList.contains('leg-premium')) this.strategyLegs[i].premium = Number(e.target.value);
                    if (e.target.classList.contains('leg-qty')) this.strategyLegs[i].quantity = Number(e.target.value);
                    this.hasCustomLegs = true;
                    this.calculateAndDrawPayoff();
                };
            });

            tr.querySelector('.btn-remove-leg').onclick = () => {
                this.strategyLegs.splice(idx, 1);
                this.hasCustomLegs = true;
                this.renderLegsTable();
                this.updateStrategyLegsBadge();
                this.calculateAndDrawPayoff();
            };

            tbody.appendChild(tr);
        });

        // Clear isNew flag after rendering once so future re-renders don't keep it highlighted forever
        setTimeout(() => {
            this.strategyLegs.forEach(l => l.isNew = false);
        }, 3000);
    }

    addStrategyLeg() {
        const step = this.currentSpot > 10000 ? 100 : (this.currentSpot > 2000 ? 50 : 20);
        const atm = Math.round(this.currentSpot / step) * step;

        this.hasCustomLegs = true;
        this.strategyLegs.push({
            strike: atm,
            option_type: 'CE',
            position: 'LONG',
            premium: Math.round(this.currentSpot * 0.01),
            quantity: 1,
            isNew: true
        });

        this.renderLegsTable();
        this.updateStrategyLegsBadge();
        this.calculateAndDrawPayoff();
    }

    applyStrategyPreset(preset) {
        const spot = this.currentSpot;
        const step = spot > 10000 ? 100 : (spot > 2000 ? 50 : 20);
        const atm = Math.round(spot / step) * step;
        const estAtmPremium = Math.max(10, Math.round(spot * 0.008));
        const estOtmPremium = Math.max(5, Math.round(estAtmPremium * 0.4));

        if (preset === 'long_call') {
            this.strategyLegs = [
                { strike: atm, option_type: 'CE', position: 'LONG', premium: estAtmPremium, quantity: 1 }
            ];
        } else if (preset === 'long_put') {
            this.strategyLegs = [
                { strike: atm, option_type: 'PE', position: 'LONG', premium: estAtmPremium, quantity: 1 }
            ];
        } else if (preset === 'bull_call') {
            this.strategyLegs = [
                { strike: atm, option_type: 'CE', position: 'LONG', premium: estAtmPremium, quantity: 1 },
                { strike: atm + step * 2, option_type: 'CE', position: 'SHORT', premium: estOtmPremium, quantity: 1 }
            ];
        } else if (preset === 'bear_put') {
            this.strategyLegs = [
                { strike: atm, option_type: 'PE', position: 'LONG', premium: estAtmPremium, quantity: 1 },
                { strike: atm - step * 2, option_type: 'PE', position: 'SHORT', premium: estOtmPremium, quantity: 1 }
            ];
        } else if (preset === 'straddle') {
            this.strategyLegs = [
                { strike: atm, option_type: 'CE', position: 'LONG', premium: estAtmPremium, quantity: 1 },
                { strike: atm, option_type: 'PE', position: 'LONG', premium: estAtmPremium, quantity: 1 }
            ];
        } else if (preset === 'iron_condor') {
            this.strategyLegs = [
                { strike: atm + step, option_type: 'CE', position: 'SHORT', premium: Math.round(estAtmPremium * 0.6), quantity: 1 },
                { strike: atm + step * 3, option_type: 'CE', position: 'LONG', premium: Math.round(estAtmPremium * 0.25), quantity: 1 },
                { strike: atm - step, option_type: 'PE', position: 'SHORT', premium: Math.round(estAtmPremium * 0.6), quantity: 1 },
                { strike: atm - step * 3, option_type: 'PE', position: 'LONG', premium: Math.round(estAtmPremium * 0.25), quantity: 1 }
            ];
        }

        this.renderLegsTable();
        this.updateStrategyLegsBadge();
        this.calculateAndDrawPayoff();
    }

    async calculateAndDrawPayoff() {
        const container = document.getElementById('payoff-chart-svg');
        const maxProfitEl = document.getElementById('payoff-max-profit');
        const maxLossEl = document.getElementById('payoff-max-loss');
        const breakevenEl = document.getElementById('payoff-breakevens');
        const netPremEl = document.getElementById('options-net-premium-val');
        const simProfitEl = document.getElementById('options-sim-profit-val');
        const simLossEl = document.getElementById('options-sim-loss-val');

        if (!container || this.strategyLegs.length === 0) {
            if (container) container.innerHTML = '<div class="text-center p-8 text-muted">Configure legs above or add legs from the Strike Matrix to view payoff curve.</div>';
            if (netPremEl) {
                netPremEl.textContent = '₹0.00';
                netPremEl.className = 'metric-value font-mono';
            }
            if (simProfitEl) simProfitEl.textContent = '₹0';
            if (simLossEl) simLossEl.textContent = '₹0';
            if (breakevenEl) breakevenEl.textContent = '--';
            return;
        }

        // Compute Net Premium
        let netDebitCredit = 0;
        this.strategyLegs.forEach(leg => {
            const cost = leg.premium * (leg.quantity || 1);
            if (leg.position === 'LONG') {
                netDebitCredit -= cost; // Outflow (Debit)
            } else {
                netDebitCredit += cost; // Inflow (Credit)
            }
        });

        if (netPremEl) {
            if (netDebitCredit < 0) {
                netPremEl.textContent = `Debit ₹${Math.abs(netDebitCredit).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                netPremEl.className = 'metric-value font-mono text-red';
            } else if (netDebitCredit > 0) {
                netPremEl.textContent = `Credit ₹${netDebitCredit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                netPremEl.className = 'metric-value font-mono text-green';
            } else {
                netPremEl.textContent = `Even ₹0.00`;
                netPremEl.className = 'metric-value font-mono';
            }
        }

        try {
            const legsStr = encodeURIComponent(JSON.stringify(this.strategyLegs));
            const res = await fetch(`/api/v1/options/payoff?spot=${this.currentSpot}&legs=${legsStr}`);
            const json = await res.json();

            if (json.success && json.data) {
                const curve = json.data.curve || [];
                const maxProfit = json.data.max_profit;
                const maxLoss = json.data.max_loss;

                const profitText = maxProfit > 999999 ? 'Unlimited' : `+₹${maxProfit.toLocaleString()}`;
                const lossText = maxLoss < -999999 ? 'Unlimited' : `-₹${Math.abs(maxLoss).toLocaleString()}`;

                if (maxProfitEl) maxProfitEl.textContent = profitText;
                if (maxLossEl) maxLossEl.textContent = lossText;
                if (simProfitEl) simProfitEl.textContent = profitText;
                if (simLossEl) simLossEl.textContent = lossText;

                // Calculate breakevens
                const bes = [];
                for (let i = 1; i < curve.length; i++) {
                    if ((curve[i - 1].pnl <= 0 && curve[i].pnl >= 0) || (curve[i - 1].pnl >= 0 && curve[i].pnl <= 0)) {
                        bes.push(curve[i].spot);
                    }
                }
                if (breakevenEl) breakevenEl.textContent = bes.length > 0 ? bes.map(b => `₹${b.toLocaleString()}`).join(', ') : 'None in range';

                this.drawPayoffSvg(container, curve);
            }
        } catch (e) {
            console.error("Payoff calculation failed:", e);
        }
    }

    drawPayoffSvg(container, curve) {
        if (!curve || curve.length === 0) return;

        const width = container.clientWidth || 850;
        const height = 280;
        const padding = { top: 25, right: 40, bottom: 40, left: 70 };

        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const minSpot = curve[0].spot;
        const maxSpot = curve[curve.length - 1].spot;

        let minPnl = Infinity;
        let maxPnl = -Infinity;
        curve.forEach(pt => {
            if (pt.pnl < minPnl) minPnl = pt.pnl;
            if (pt.pnl > maxPnl) maxPnl = pt.pnl;
        });

        const pnlSpan = Math.max(10, maxPnl - minPnl);
        const yMin = minPnl - (pnlSpan * 0.1);
        const yMax = maxPnl + (pnlSpan * 0.1);

        const getX = (spot) => padding.left + ((spot - minSpot) / (maxSpot - minSpot)) * chartW;
        const getY = (pnl) => padding.top + chartH - ((pnl - yMin) / (yMax - yMin)) * chartH;

        const zeroY = getY(0);
        const spotX = getX(this.currentSpot);

        // Path points
        const points = curve.map(pt => `${getX(pt.spot)},${getY(pt.pnl)}`).join(' ');

        // Grid lines
        let gridHtml = `
            <!-- Zero Line -->
            <line x1="${padding.left}" y1="${zeroY}" x2="${width - padding.right}" y2="${zeroY}" stroke="#4E525E" stroke-dasharray="4,4" stroke-width="1.5"></line>
            <text x="${padding.left - 8}" y="${zeroY + 4}" fill="#787B86" font-size="11" text-anchor="end">₹0</text>

            <!-- Current Spot Line -->
            <line x1="${spotX}" y1="${padding.top}" x2="${spotX}" y2="${height - padding.bottom}" stroke="#F5AC00" stroke-dasharray="3,3" stroke-width="1.5"></line>
            <text x="${spotX}" y="${padding.top - 8}" fill="#F5AC00" font-size="11" text-anchor="middle" font-weight="bold">Spot: ₹${this.currentSpot.toLocaleString()}</text>
        `;

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: ${height}px; overflow: visible;">
                ${gridHtml}
                <!-- Payoff Line -->
                <polyline fill="none" stroke="#2962FF" stroke-width="3" points="${points}" stroke-linejoin="round"></polyline>

                <!-- Data Points -->
                ${curve.map(pt => {
            const cx = getX(pt.spot);
            const cy = getY(pt.pnl);
            const isProfit = pt.pnl >= 0;
            return `
                        <circle cx="${cx}" cy="${cy}" r="3.5" fill="${isProfit ? '#089981' : '#F23645'}" stroke="#0B0E14" stroke-width="1.5">
                            <title>Expiry Spot: ₹${pt.spot.toLocaleString()} | P&L: ₹${pt.pnl.toLocaleString()}</title>
                        </circle>
                    `;
        }).join('')}

                <!-- X Axis Labels -->
                <text x="${padding.left}" y="${height - 12}" fill="#787B86" font-size="11" text-anchor="start">₹${minSpot.toLocaleString()}</text>
                <text x="${width - padding.right}" y="${height - 12}" fill="#787B86" font-size="11" text-anchor="end">₹${maxSpot.toLocaleString()}</text>
            </svg>
        `;
    }
}

window.OptionsUI = OptionsUI;
window.optionsController = new OptionsUI();
