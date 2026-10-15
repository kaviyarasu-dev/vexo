/**
 * options_analytics.js
 * Options Open Interest (ΔOI) Analytics, Strategy Net Greeks HUD & Interactive Pre-Expiry Payoff Simulator.
 * Integrates directly with OptionsUI to deliver institutional-grade derivatives analysis.
 */

(function () {
    class OptionsAnalyticsController {
        constructor() {
            this.activeTab = 'matrix'; // 'matrix' | 'open_interest' | 'payoff'
            this.activeSymbol = 'NSE:NIFTY50-INDEX';
            this.currentSpot = 25050.0;
            this.underlyingCatalog = null;
            this.oiData = null;
            this.oiViewMode = 'combined'; // 'total' | 'change' | 'combined'
            this.targetDays = 2.0;
            this.ivShockPct = 0.0;
            this.cachedPayoff = null;
            this.cachedGreeks = null;
            this.isSimulating = false;
        }

        async init() {
            this.bindSubtabs();
            this.bindQuickChips();
            this.bindOIControls();
            this.bindSimulationSliders();
            this.bindPresetButtons();
            await this.loadUnderlyings();
            this.hookOptionsUI();
            await this.loadOpenInterest(this.activeSymbol);
            await this.updateStrategyGreeksAndPayoff();
        }

        hookOptionsUI() {
            const optUi = window.optionsUI || window.optionsController;
            if (optUi) {
                window.optionsUI = optUi;
                window.optionsController = optUi;
                const origLoad = optUi.loadOptionsData.bind(optUi);
                optUi.loadOptionsData = async (symbol, isNewSymbol) => {
                    this.activeSymbol = symbol;
                    await origLoad(symbol, isNewSymbol);
                    this.currentSpot = optUi.currentSpot || 25050.0;
                    await this.loadOpenInterest(symbol);
                    await this.updateStrategyGreeksAndPayoff();
                };

                const origApply = optUi.applyStrategyPreset.bind(optUi);
                optUi.applyStrategyPreset = (preset) => {
                    this.applyExpandedPreset(preset);
                };

                if (window.OptionsUI && window.OptionsUI.prototype) {
                    window.OptionsUI.prototype.switchOptionsTab = (tabName) => {
                        this.switchOptionsTab(tabName);
                    };
                }
            }
        }

        bindSubtabs() {
            document.querySelectorAll('.options-subtab').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const tab = e.currentTarget.dataset.subtab;
                    if (tab) this.switchOptionsTab(tab);
                });
            });
        }

        switchOptionsTab(tabName) {
            this.activeTab = tabName;
            document.querySelectorAll('.options-subtab').forEach(b => {
                b.classList.toggle('active', b.dataset.subtab === tabName);
            });

            const matrixPanel = document.getElementById('options-matrix-panel');
            const oiPanel = document.getElementById('options-oi-panel');
            const payoffPanel = document.getElementById('options-payoff-panel');

            if (matrixPanel) matrixPanel.classList.toggle('hidden', tabName !== 'matrix');
            if (oiPanel) oiPanel.classList.toggle('hidden', tabName !== 'open_interest');
            if (payoffPanel) payoffPanel.classList.toggle('hidden', tabName !== 'payoff');

            if (tabName === 'open_interest') {
                if (this.oiData) {
                    this.renderOIDualBarChart();
                } else {
                    this.loadOpenInterest(this.activeSymbol);
                }
            } else if (tabName === 'payoff') {
                const optUi = window.optionsUI || window.optionsController;
                if (optUi && typeof optUi.renderPayoffSimulator === 'function') {
                    optUi.renderPayoffSimulator();
                }
                this.updateStrategyGreeksAndPayoff();
            }
        }

        bindQuickChips() {
            document.querySelectorAll('.options-chip-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.options-chip-btn').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    const sym = e.currentTarget.dataset.symbol;
                    if (sym) {
                        const select = document.getElementById('options-symbol-select');
                        if (select) select.value = sym;
                        this.activeSymbol = sym;
                        if (window.optionsUI) {
                            window.optionsUI.activeSymbol = sym;
                            window.optionsUI.loadOptionsData(sym, true);
                        }
                    }
                });
            });
        }

        async loadUnderlyings() {
            try {
                const res = await fetch('/api/v1/options/underlyings');
                const json = await res.json();
                if (json.success && json.data) {
                    this.underlyingCatalog = json.data;
                    this.populateUnderlyingsSelect(json.data);
                }
            } catch (e) {
                console.error("Failed to load F&O underlyings catalog:", e);
            }
        }

        populateUnderlyingsSelect(catalog) {
            const select = document.getElementById('options-symbol-select');
            if (!select) return;

            const curVal = select.value || 'NSE:NIFTY50-INDEX';
            select.innerHTML = '';

            const optGroupIdx = document.createElement('optgroup');
            optGroupIdx.label = 'Major Indices';
            (catalog.indices || []).forEach(idx => {
                const opt = document.createElement('option');
                opt.value = idx.symbol.startsWith('NSE:') ? idx.symbol : `NSE:${idx.symbol}-INDEX`;
                opt.textContent = `${idx.display_name} (Lot: ${idx.lot_size}) - ₹${idx.spot_price.toLocaleString()}`;
                optGroupIdx.appendChild(opt);
            });
            select.appendChild(optGroupIdx);

            const optGroupEq = document.createElement('optgroup');
            optGroupEq.label = 'NSE F&O Equities (180+)';
            (catalog.equities || []).forEach(eq => {
                const opt = document.createElement('option');
                opt.value = eq.symbol.startsWith('NSE:') ? eq.symbol : `NSE:${eq.symbol}-EQ`;
                opt.textContent = `${eq.symbol} (Lot: ${eq.lot_size}) - ₹${eq.spot_price.toLocaleString()}`;
                optGroupEq.appendChild(opt);
            });
            select.appendChild(optGroupEq);

            select.value = curVal;

            // Search Filter
            const searchInput = document.getElementById('options-symbol-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    const q = e.target.value.trim().toUpperCase();
                    Array.from(select.options).forEach(opt => {
                        const match = opt.textContent.toUpperCase().includes(q) || opt.value.toUpperCase().includes(q);
                        opt.style.display = match ? '' : 'none';
                    });
                });
            }
        }

        async loadOpenInterest(symbol) {
            try {
                const clean = symbol.replace(/^NSE:/, '').replace(/-(INDEX|EQ|FUT)$/, '');
                const res = await fetch(`/api/v1/options/open-interest?symbol=${encodeURIComponent(clean)}`);
                const json = await res.json();
                if (json.success && json.data) {
                    this.oiData = json.data;
                    this.renderOIStructuralBadges(json.data);
                    this.renderOIDualBarChart();
                }
            } catch (e) {
                console.error("Failed to load Open Interest data:", e);
            }
        }

        renderOIStructuralBadges(data) {
            const resEl = document.getElementById('oi-resistance-val');
            const supEl = document.getElementById('oi-support-val');
            const mpEl = document.getElementById('oi-maxpain-val');
            const pcrEl = document.getElementById('oi-pcr-combined-val');
            const sentimentBadge = document.getElementById('oi-sentiment-badge');

            if (resEl) resEl.textContent = `₹${Number(data.major_resistance_strike).toLocaleString('en-IN')}`;
            if (supEl) supEl.textContent = `₹${Number(data.major_support_strike).toLocaleString('en-IN')}`;
            if (mpEl) mpEl.textContent = `₹${Number(data.max_pain_strike).toLocaleString('en-IN')}`;

            if (pcrEl) {
                pcrEl.textContent = `OI: ${data.pcr_oi.toFixed(2)} | ΔOI: ${data.pcr_oi_change.toFixed(2)}`;
            }

            if (sentimentBadge) {
                sentimentBadge.textContent = data.sentiment;
                sentimentBadge.className = 'badge-mini';
                if (data.sentiment === 'BULLISH') {
                    sentimentBadge.classList.add('badge-green');
                } else if (data.sentiment === 'BEARISH') {
                    sentimentBadge.classList.add('badge-red');
                } else {
                    sentimentBadge.classList.add('badge-accent');
                }
            }
        }

        bindOIControls() {
            document.querySelectorAll('.oi-toggle-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.oi-toggle-btn').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    this.oiViewMode = e.currentTarget.dataset.view || 'combined';
                    this.renderOIDualBarChart();
                });
            });
        }

        renderOIDualBarChart() {
            const container = document.getElementById('oi-dual-bar-chart');
            if (!container || !this.oiData || !this.oiData.strikes_data) return;

            const strikes = this.oiData.strikes_data;
            if (strikes.length === 0) {
                container.innerHTML = '<div class="text-center p-8 text-muted">No Open Interest data available.</div>';
                return;
            }

            const width = container.clientWidth || 920;
            const rowHeight = 24;
            const headerHeight = 35;
            const height = headerHeight + strikes.length * rowHeight + 20;

            const midX = width / 2;
            const barMaxW = (width - 180) / 2;

            // Compute scaling maxima
            let maxOI = 1;
            let maxChg = 1;
            strikes.forEach(s => {
                if (s.call_oi > maxOI) maxOI = s.call_oi;
                if (s.put_oi > maxOI) maxOI = s.put_oi;
                if (Math.abs(s.call_oi_change) > maxChg) maxChg = Math.abs(s.call_oi_change);
                if (Math.abs(s.put_oi_change) > maxChg) maxChg = Math.abs(s.put_oi_change);
            });

            const spot = this.oiData.spot;
            let rowsHtml = '';

            strikes.forEach((item, idx) => {
                const y = headerHeight + idx * rowHeight;
                const isATM = Math.abs(item.strike - spot) <= (strikes[1] ? Math.abs(strikes[1].strike - strikes[0].strike) / 2 : 50);

                let callBarW = 0;
                let putBarW = 0;
                let callChgW = 0;
                let putChgW = 0;

                if (this.oiViewMode === 'total' || this.oiViewMode === 'combined') {
                    callBarW = (item.call_oi / maxOI) * barMaxW;
                    putBarW = (item.put_oi / maxOI) * barMaxW;
                }
                if (this.oiViewMode === 'change' || this.oiViewMode === 'combined') {
                    callChgW = (Math.abs(item.call_oi_change) / maxChg) * (barMaxW * 0.45);
                    putChgW = (Math.abs(item.put_oi_change) / maxChg) * (barMaxW * 0.45);
                }

                const callX = midX - 50 - callBarW;
                const putX = midX + 50;

                // Format numbers
                const fmtK = (num) => Math.abs(num) >= 100000 ? `${(num / 100000).toFixed(1)}L` : (Math.abs(num) >= 1000 ? `${(num / 1000).toFixed(0)}k` : num);

                rowsHtml += `
                    <g class="oi-row ${isATM ? 'oi-atm-row' : ''}">
                        <!-- Background Zebra -->
                        <rect x="0" y="${y}" width="${width}" height="${rowHeight}" fill="${isATM ? 'rgba(56, 189, 248, 0.08)' : (idx % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent')}" />
                        
                        <!-- Call Total OI Bar (Red/Rose) -->
                        <rect x="${callX}" y="${y + 4}" width="${callBarW}" height="${rowHeight - 8}" fill="#f43f5e" opacity="0.85" rx="3">
                            <title>Call OI: ${item.call_oi.toLocaleString()} contracts | ΔOI: ${item.call_oi_change > 0 ? '+' : ''}${item.call_oi_change.toLocaleString()}</title>
                        </rect>
                        
                        <!-- Call ΔOI Badge -->
                        <text x="${midX - 58}" y="${y + 16}" fill="${item.call_oi_change >= 0 ? '#fda4af' : '#94a3b8'}" font-size="10" text-anchor="end" font-family="monospace">
                            ${item.call_oi_change > 0 ? '+' : ''}${fmtK(item.call_oi_change)}
                        </text>

                        <!-- Strike Price Center Label -->
                        <rect x="${midX - 45}" y="${y + 3}" width="90" height="${rowHeight - 6}" fill="${isATM ? '#0284c7' : '#1e293b'}" rx="4" />
                        <text x="${midX}" y="${y + 16}" fill="${isATM ? '#ffffff' : '#f8fafc'}" font-size="11" font-weight="${isATM ? 'bold' : 'normal'}" text-anchor="middle" font-family="monospace">
                            ${item.strike} ${isATM ? '★' : ''}
                        </text>

                        <!-- Put ΔOI Badge -->
                        <text x="${midX + 58}" y="${y + 16}" fill="${item.put_oi_change >= 0 ? '#86efac' : '#94a3b8'}" font-size="10" text-anchor="start" font-family="monospace">
                            ${item.put_oi_change > 0 ? '+' : ''}${fmtK(item.put_oi_change)}
                        </text>

                        <!-- Put Total OI Bar (Green/Emerald) -->
                        <rect x="${putX}" y="${y + 4}" width="${putBarW}" height="${rowHeight - 8}" fill="#10b981" opacity="0.85" rx="3">
                            <title>Put OI: ${item.put_oi.toLocaleString()} contracts | ΔOI: ${item.put_oi_change > 0 ? '+' : ''}${item.put_oi_change.toLocaleString()}</title>
                        </rect>
                    </g>
                `;
            });

            container.innerHTML = `
                <div class="oi-chart-header-row mb-2">
                    <span class="text-rose font-bold">◄ CALL OI (Ceiling / Resistance)</span>
                    <span class="font-mono text-muted text-xs">Spot: ₹${spot.toLocaleString()}</span>
                    <span class="text-emerald font-bold">PUT OI (Floor / Support) ►</span>
                </div>
                <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: ${height}px; overflow: visible;">
                    <!-- Column Header Legends -->
                    <text x="${midX - 100}" y="20" fill="#f43f5e" font-size="11" font-weight="bold" text-anchor="end">CALL OPEN INTEREST</text>
                    <text x="${midX}" y="20" fill="#94a3b8" font-size="11" font-weight="bold" text-anchor="middle">STRIKE</text>
                    <text x="${midX + 100}" y="20" fill="#10b981" font-size="11" font-weight="bold" text-anchor="start">PUT OPEN INTEREST</text>
                    
                    <!-- Center Divider -->
                    <line x1="${midX}" y1="30" x2="${midX}" y2="${height}" stroke="rgba(255,255,255,0.1)" stroke-dasharray="2 2" />
                    
                    ${rowsHtml}
                </svg>
            `;
        }

        bindSimulationSliders() {
            const targetDaysSlider = document.getElementById('slider-target-days');
            const targetDaysVal = document.getElementById('slider-target-days-val');
            const ivShockSlider = document.getElementById('slider-iv-shock');
            const ivShockVal = document.getElementById('slider-iv-shock-val');

            if (targetDaysSlider) {
                targetDaysSlider.addEventListener('input', (e) => {
                    this.targetDays = parseFloat(e.target.value);
                    if (targetDaysVal) targetDaysVal.textContent = `T+${this.targetDays.toFixed(1)} Days`;
                    this.debounceSimulation();
                });
            }

            if (ivShockSlider) {
                ivShockSlider.addEventListener('input', (e) => {
                    this.ivShockPct = parseFloat(e.target.value);
                    if (ivShockVal) ivShockVal.textContent = `${this.ivShockPct >= 0 ? '+' : ''}${this.ivShockPct.toFixed(0)}% IV`;
                    this.debounceSimulation();
                });
            }
        }

        debounceSimulation() {
            if (this.simTimeout) clearTimeout(this.simTimeout);
            this.simTimeout = setTimeout(() => {
                this.updateStrategyGreeksAndPayoff();
            }, 60);
        }

        bindPresetButtons() {
            document.querySelectorAll('.strategy-preset-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const preset = e.currentTarget.dataset.preset;
                    if (preset) this.applyExpandedPreset(preset);
                });
            });
        }

        applyExpandedPreset(preset) {
            if (!window.optionsUI || !window.optionsUI.matrix || window.optionsUI.matrix.length === 0) {
                if (window.optionsUI && window.optionsUI.showToast) {
                    window.optionsUI.showToast("Cannot apply preset: Real option chain not loaded.", "error");
                }
                return;
            }

            const matrix = window.optionsUI.matrix;
            const spot = (window.optionsUI && window.optionsUI.currentSpot) ? window.optionsUI.currentSpot : this.currentSpot;
            let step = 50;
            if (matrix.length >= 2) {
                step = Math.abs(matrix[1].strike_price - matrix[0].strike_price) || 50;
            }
            const atm = Math.round(spot / step) * step;

            const findLeg = (targetStrike, optType) => {
                let closest = null;
                let minDiff = Infinity;
                for (const row of matrix) {
                    const diff = Math.abs(row.strike_price - targetStrike);
                    if (diff < minDiff) {
                        minDiff = diff;
                        closest = row;
                    }
                }
                if (!closest) return { strike: targetStrike, premium: 10.0, iv: 15.0 };
                const opt = optType === 'CE' ? closest.call : closest.put;
                const prem = (opt && opt.ltp > 0) ? opt.ltp : 10.0;
                const iv = (opt && opt.iv > 0) ? opt.iv : 15.0;
                return { strike: closest.strike_price, premium: prem, iv: iv };
            };

            let legs = [];
            if (preset === 'bull_call') {
                const l1 = findLeg(atm, 'CE');
                const l2 = findLeg(atm + step * 2, 'CE');
                legs = [
                    { strike: l1.strike, option_type: 'CE', position: 'LONG', premium: l1.premium, quantity: 1, iv: l1.iv },
                    { strike: l2.strike, option_type: 'CE', position: 'SHORT', premium: l2.premium, quantity: 1, iv: l2.iv }
                ];
            } else if (preset === 'bear_call') {
                const l1 = findLeg(atm + step, 'CE');
                const l2 = findLeg(atm + step * 3, 'CE');
                legs = [
                    { strike: l1.strike, option_type: 'CE', position: 'SHORT', premium: l1.premium, quantity: 1, iv: l1.iv },
                    { strike: l2.strike, option_type: 'CE', position: 'LONG', premium: l2.premium, quantity: 1, iv: l2.iv }
                ];
            } else if (preset === 'bull_put') {
                const l1 = findLeg(atm - step, 'PE');
                const l2 = findLeg(atm - step * 3, 'PE');
                legs = [
                    { strike: l1.strike, option_type: 'PE', position: 'SHORT', premium: l1.premium, quantity: 1, iv: l1.iv },
                    { strike: l2.strike, option_type: 'PE', position: 'LONG', premium: l2.premium, quantity: 1, iv: l2.iv }
                ];
            } else if (preset === 'bear_put') {
                const l1 = findLeg(atm, 'PE');
                const l2 = findLeg(atm - step * 2, 'PE');
                legs = [
                    { strike: l1.strike, option_type: 'PE', position: 'LONG', premium: l1.premium, quantity: 1, iv: l1.iv },
                    { strike: l2.strike, option_type: 'PE', position: 'SHORT', premium: l2.premium, quantity: 1, iv: l2.iv }
                ];
            } else if (preset === 'straddle') {
                const l1 = findLeg(atm, 'CE');
                const l2 = findLeg(atm, 'PE');
                legs = [
                    { strike: l1.strike, option_type: 'CE', position: 'LONG', premium: l1.premium, quantity: 1, iv: l1.iv },
                    { strike: l2.strike, option_type: 'PE', position: 'LONG', premium: l2.premium, quantity: 1, iv: l2.iv }
                ];
            } else if (preset === 'strangle') {
                const l1 = findLeg(atm + step * 2, 'CE');
                const l2 = findLeg(atm - step * 2, 'PE');
                legs = [
                    { strike: l1.strike, option_type: 'CE', position: 'LONG', premium: l1.premium, quantity: 1, iv: l1.iv },
                    { strike: l2.strike, option_type: 'PE', position: 'LONG', premium: l2.premium, quantity: 1, iv: l2.iv }
                ];
            } else if (preset === 'iron_condor') {
                const cShort = findLeg(atm + step, 'CE');
                const cLong = findLeg(atm + step * 3, 'CE');
                const pShort = findLeg(atm - step, 'PE');
                const pLong = findLeg(atm - step * 3, 'PE');
                legs = [
                    { strike: cShort.strike, option_type: 'CE', position: 'SHORT', premium: cShort.premium, quantity: 1, iv: cShort.iv },
                    { strike: cLong.strike, option_type: 'CE', position: 'LONG', premium: cLong.premium, quantity: 1, iv: cLong.iv },
                    { strike: pShort.strike, option_type: 'PE', position: 'SHORT', premium: pShort.premium, quantity: 1, iv: pShort.iv },
                    { strike: pLong.strike, option_type: 'PE', position: 'LONG', premium: pLong.premium, quantity: 1, iv: pLong.iv }
                ];
            } else if (preset === 'iron_butterfly') {
                const cAtm = findLeg(atm, 'CE');
                const pAtm = findLeg(atm, 'PE');
                const cWing = findLeg(atm + step * 2, 'CE');
                const pWing = findLeg(atm - step * 2, 'PE');
                legs = [
                    { strike: cAtm.strike, option_type: 'CE', position: 'SHORT', premium: cAtm.premium, quantity: 1, iv: cAtm.iv },
                    { strike: pAtm.strike, option_type: 'PE', position: 'SHORT', premium: pAtm.premium, quantity: 1, iv: pAtm.iv },
                    { strike: cWing.strike, option_type: 'CE', position: 'LONG', premium: cWing.premium, quantity: 1, iv: cWing.iv },
                    { strike: pWing.strike, option_type: 'PE', position: 'LONG', premium: pWing.premium, quantity: 1, iv: pWing.iv }
                ];
            }

            const optUi = window.optionsUI || window.optionsController;
            if (optUi) {
                optUi.strategyLegs = legs;
                optUi.hasCustomLegs = true;
                optUi.renderLegsTable();
                optUi.updateStrategyLegsBadge();
            }

            this.updateStrategyGreeksAndPayoff();
        }

        async updateStrategyGreeksAndPayoff() {
            const optUi = window.optionsUI || window.optionsController;
            const legs = (optUi && optUi.strategyLegs) ? optUi.strategyLegs : [];
            const cleanSym = this.activeSymbol.replace(/^NSE:/, '').replace(/-(INDEX|EQ|FUT)$/, '');
            const spot = (optUi && optUi.currentSpot) ? optUi.currentSpot : this.currentSpot;

            if (legs.length === 0) {
                this.renderNetGreeksHUD({
                    net_delta: 0,
                    net_gamma: 0,
                    net_theta: 0,
                    net_vega: 0,
                    delta_inr: 0,
                    theta_inr: 0,
                    vega_inr: 0,
                    total_cost_inr: 0
                });
                this.renderEmptyState();
                return;
            }

            try {
                // 1. Fetch Strategy Net Greeks
                const greeksReq = {
                    symbol: cleanSym,
                    spot: spot,
                    t_days: 4.0,
                    r: 0.065,
                    legs: legs.map(l => ({
                        strike: l.strike,
                        option_type: l.option_type,
                        position: l.position,
                        premium: l.premium,
                        quantity: l.quantity || 1,
                        iv: l.iv || 15.0
                    }))
                };

                // 2. Fetch Payoff Simulation
                const payoffReq = {
                    symbol: cleanSym,
                    spot: spot,
                    t_days_remaining: 5.0,
                    target_days: this.targetDays,
                    iv_shock_pct: this.ivShockPct,
                    r: 0.065,
                    legs: greeksReq.legs
                };

                const [greeksRes, payoffRes] = await Promise.all([
                    fetch('/api/v1/options/strategy/greeks', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(greeksReq)
                    }).then(r => r.json()),
                    fetch('/api/v1/options/strategy/payoff', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payoffReq)
                    }).then(r => r.json())
                ]);

                if (greeksRes.success && greeksRes.data) {
                    this.renderNetGreeksHUD(greeksRes.data);
                }

                if (payoffRes.success && payoffRes.data) {
                    this.renderPayoffSimulator(payoffRes.data);
                }
            } catch (e) {
                console.error("Strategy calculation failed:", e);
            }
        }

        renderNetGreeksHUD(data) {
            const deltaEl = document.getElementById('hud-delta-val');
            const deltaInrEl = document.getElementById('hud-delta-inr');
            const gammaEl = document.getElementById('hud-gamma-val');
            const thetaEl = document.getElementById('hud-theta-val');
            const thetaInrEl = document.getElementById('hud-theta-inr');
            const vegaEl = document.getElementById('hud-vega-val');
            const vegaInrEl = document.getElementById('hud-vega-inr');
            const costPill = document.getElementById('strategy-cost-pill');

            if (deltaEl) {
                deltaEl.textContent = (data.net_delta >= 0 ? '+' : '') + data.net_delta.toFixed(4);
                deltaEl.className = `greek-hud-val font-mono ${data.net_delta >= 0 ? 'text-green' : 'text-red'}`;
            }
            if (deltaInrEl) {
                deltaInrEl.textContent = `${data.delta_inr >= 0 ? '+' : ''}₹${data.delta_inr.toLocaleString()} / pt move`;
            }
            if (gammaEl) {
                gammaEl.textContent = data.net_gamma.toFixed(6);
            }
            if (thetaEl) {
                thetaEl.textContent = (data.net_theta >= 0 ? '+' : '') + data.net_theta.toFixed(2);
                thetaEl.className = `greek-hud-val font-mono ${data.net_theta >= 0 ? 'text-green' : 'text-red'}`;
            }
            if (thetaInrEl) {
                thetaInrEl.textContent = `${data.theta_inr >= 0 ? '+' : ''}₹${data.theta_inr.toLocaleString()} / day decay`;
            }
            if (vegaEl) {
                vegaEl.textContent = (data.net_vega >= 0 ? '+' : '') + data.net_vega.toFixed(3);
                vegaEl.className = `greek-hud-val font-mono ${data.net_vega >= 0 ? 'text-green' : 'text-red'}`;
            }
            if (vegaInrEl) {
                vegaInrEl.textContent = `${data.vega_inr >= 0 ? '+' : ''}₹${data.vega_inr.toLocaleString()} / 1% IV shift`;
            }
            if (costPill) {
                if (data.total_cost_inr > 0) {
                    costPill.textContent = `Credit: +₹${data.total_cost_inr.toLocaleString()}`;
                    costPill.className = 'badge-pill badge-green';
                } else if (data.total_cost_inr < 0) {
                    costPill.textContent = `Debit: -₹${Math.abs(data.total_cost_inr).toLocaleString()}`;
                    costPill.className = 'badge-pill badge-red';
                } else {
                    costPill.textContent = 'Even: ₹0';
                    costPill.className = 'badge-pill';
                }
            }
        }

        renderPayoffSimulator(data) {
            const maxProfitEl = document.getElementById('payoff-max-profit');
            const maxLossEl = document.getElementById('payoff-max-loss');
            const breakevenEl = document.getElementById('payoff-breakevens');
            const container = document.getElementById('payoff-chart-svg');

            if (maxProfitEl) {
                maxProfitEl.textContent = data.max_profit > 999999 ? 'Unlimited' : `+₹${data.max_profit.toLocaleString()}`;
            }
            if (maxLossEl) {
                maxLossEl.textContent = data.max_loss < -999999 ? 'Unlimited' : `-₹${Math.abs(data.max_loss).toLocaleString()}`;
            }
            if (breakevenEl) {
                breakevenEl.textContent = (data.breakevens && data.breakevens.length > 0)
                    ? data.breakevens.map(b => `₹${b.toLocaleString()}`).join(', ')
                    : 'None in range';
            }

            if (!container) return;

            const expCurve = data.expiration_curve || [];
            const targetCurve = data.target_date_curve || [];
            if (expCurve.length === 0) return;

            const width = container.clientWidth || 880;
            const height = 290;
            const padding = { top: 25, right: 35, bottom: 45, left: 75 };

            const chartW = width - padding.left - padding.right;
            const chartH = height - padding.top - padding.bottom;

            const spots = expCurve.map(pt => pt.spot);
            const minSpot = Math.min(...spots);
            const maxSpot = Math.max(...spots);

            let minPnl = Math.min(...expCurve.map(p => p.pnl), ...targetCurve.map(p => p.pnl));
            let maxPnl = Math.max(...expCurve.map(p => p.pnl), ...targetCurve.map(p => p.pnl));

            if (minPnl >= 0) minPnl = -1000;
            if (maxPnl <= 0) maxPnl = 1000;

            const pnlPad = (maxPnl - minPnl) * 0.12;
            minPnl -= pnlPad;
            maxPnl += pnlPad;

            const getX = (s) => padding.left + ((s - minSpot) / (maxSpot - minSpot)) * chartW;
            const getY = (pnl) => padding.top + chartH - ((pnl - minPnl) / (maxPnl - minPnl)) * chartH;

            const zeroY = getY(0);

            // Construct SVG paths
            let expPath = `M ${getX(expCurve[0].spot)} ${getY(expCurve[0].pnl)}`;
            for (let i = 1; i < expCurve.length; i++) {
                expPath += ` L ${getX(expCurve[i].spot)} ${getY(expCurve[i].pnl)}`;
            }

            let targetPath = '';
            if (targetCurve.length > 0) {
                targetPath = `M ${getX(targetCurve[0].spot)} ${getY(targetCurve[0].pnl)}`;
                for (let i = 1; i < targetCurve.length; i++) {
                    targetPath += ` L ${getX(targetCurve[i].spot)} ${getY(targetCurve[i].pnl)}`;
                }
            }

            // Spot ray
            const spotX = getX(data.spot);

            // Breakeven pins
            let bePins = '';
            (data.breakevens || []).forEach(be => {
                const beX = getX(be);
                if (beX >= padding.left && beX <= width - padding.right) {
                    bePins += `
                        <line x1="${beX}" y1="${padding.top}" x2="${beX}" y2="${height - padding.bottom}" stroke="#f59e0b" stroke-dasharray="3 3" opacity="0.7" />
                        <circle cx="${beX}" cy="${zeroY}" r="4" fill="#f59e0b" />
                        <text x="${beX}" y="${height - 28}" fill="#f59e0b" font-size="9" text-anchor="middle" font-family="monospace">BE: ₹${be.toLocaleString()}</text>
                    `;
                }
            });

            container.innerHTML = `
                <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: ${height}px; overflow: visible;">
                    <!-- Grid Lines -->
                    <line x1="${padding.left}" y1="${zeroY}" x2="${width - padding.right}" y2="${zeroY}" stroke="#475569" stroke-width="1.5" stroke-dasharray="2 2" />
                    <text x="${padding.left - 10}" y="${zeroY + 4}" fill="#94a3b8" font-size="10" text-anchor="end" font-family="monospace">₹0</text>
                    
                    <!-- Spot Ray -->
                    <line x1="${spotX}" y1="${padding.top}" x2="${spotX}" y2="${height - padding.bottom}" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4 4" />
                    <text x="${spotX}" y="${padding.top - 6}" fill="#38bdf8" font-size="10" font-weight="bold" text-anchor="middle" font-family="monospace">Spot: ₹${Number(data.spot).toLocaleString()}</text>

                    <!-- Breakeven Pins -->
                    ${bePins}

                    <!-- Expiration Hockey-Stick Curve (White/Dashed) -->
                    <path d="${expPath}" fill="none" stroke="#f8fafc" stroke-width="2.5" stroke-dasharray="4 2" opacity="0.9" />

                    <!-- Theoretical Pre-Expiry Curve (Vibrant Cyan) -->
                    ${targetPath ? `<path d="${targetPath}" fill="none" stroke="#38bdf8" stroke-width="3" opacity="0.95" />` : ''}

                    <!-- Axis Labels -->
                    <text x="${padding.left}" y="${height - 10}" fill="#64748b" font-size="10" font-family="monospace">₹${minSpot.toLocaleString()}</text>
                    <text x="${width - padding.right}" y="${height - 10}" fill="#64748b" font-size="10" text-anchor="end" font-family="monospace">₹${maxSpot.toLocaleString()}</text>
                    
                    <text x="${padding.left - 10}" y="${padding.top + 10}" fill="#10b981" font-size="10" text-anchor="end" font-family="monospace">+₹${Math.round(maxPnl).toLocaleString()}</text>
                    <text x="${padding.left - 10}" y="${height - padding.bottom - 4}" fill="#f43f5e" font-size="10" text-anchor="end" font-family="monospace">-₹${Math.abs(Math.round(minPnl)).toLocaleString()}</text>
                </svg>
            `;
        }

        // Contract Aliases
        async loadOpenInterestData(symbol) {
            return await this.loadOpenInterest(symbol);
        }

        renderOIBarChart(oiData) {
            if (oiData) this.oiData = oiData;
            return this.renderOIDualBarChart();
        }

        renderNetGreeksHUD(data) {
            const deltaEl = document.getElementById('hud-delta-val');
            const deltaInrEl = document.getElementById('hud-delta-inr');
            const gammaEl = document.getElementById('hud-gamma-val');
            const thetaEl = document.getElementById('hud-theta-val');
            const thetaInrEl = document.getElementById('hud-theta-inr');
            const vegaEl = document.getElementById('hud-vega-val');
            const vegaInrEl = document.getElementById('hud-vega-inr');
            const costPill = document.getElementById('strategy-cost-pill');

            if (deltaEl) {
                deltaEl.textContent = (data.net_delta >= 0 ? '+' : '') + data.net_delta.toFixed(4);
                deltaEl.className = `greek-hud-val font-mono ${data.net_delta >= 0 ? 'text-green' : 'text-red'}`;
            }
            if (deltaInrEl) {
                deltaInrEl.textContent = `${data.delta_inr >= 0 ? '+' : ''}₹${data.delta_inr.toLocaleString()} / pt move`;
            }
            if (gammaEl) {
                gammaEl.textContent = data.net_gamma.toFixed(6);
            }
            if (thetaEl) {
                thetaEl.textContent = (data.net_theta >= 0 ? '+' : '') + data.net_theta.toFixed(2);
                thetaEl.className = `greek-hud-val font-mono ${data.net_theta >= 0 ? 'text-green' : 'text-red'}`;
            }
            if (thetaInrEl) {
                thetaInrEl.textContent = `${data.theta_inr >= 0 ? '+' : ''}₹${data.theta_inr.toLocaleString()} / day decay`;
            }
            if (vegaEl) {
                vegaEl.textContent = (data.net_vega >= 0 ? '+' : '') + data.net_vega.toFixed(3);
                vegaEl.className = `greek-hud-val font-mono ${data.net_vega >= 0 ? 'text-green' : 'text-red'}`;
            }
            if (vegaInrEl) {
                vegaInrEl.textContent = `${data.vega_inr >= 0 ? '+' : ''}₹${data.vega_inr.toLocaleString()} / 1% IV shift`;
            }
            if (costPill) {
                if (data.total_cost_inr > 0) {
                    costPill.textContent = `Credit: +₹${data.total_cost_inr.toLocaleString()}`;
                    costPill.className = 'badge-pill badge-green';
                } else if (data.total_cost_inr < 0) {
                    costPill.textContent = `Debit: -₹${Math.abs(data.total_cost_inr).toLocaleString()}`;
                    costPill.className = 'badge-pill badge-red';
                } else {
                    costPill.textContent = 'Even: ₹0';
                    costPill.className = 'badge-pill';
                }
            }
        }

        async updatePayoffSimulation() {
            return await this.updateStrategyGreeksAndPayoff();
        }

        renderPreExpiryPayoffChart(data) {
            return this.renderPayoffSimulator(data);
        }

        applyStrategyPreset(presetName) {
            return this.applyExpandedPreset(presetName);
        }

        renderEmptyState() {
            const container = document.getElementById('payoff-chart-svg');
            if (container) {
                container.innerHTML = '<div class="text-center p-8 text-muted">Select a strategy preset or configure option legs to simulate pre-expiry payoff.</div>';
            }
        }
    }

    // Expose on window
    window.OptionsAnalyticsController = OptionsAnalyticsController;

    // Auto-init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        window.optionsAnalyticsController = new OptionsAnalyticsController();
        window.optionsAnalyticsController.init();
    });
})();
