/**
 * OrderBlock Standalone Stock Popup Modal Controller
 * Renders high-fidelity institutional card matching Screenshot 1:
 * - Header with rupee change reconciliation (+2.82% · +3.11)
 * - Day-path staircase sparkline (trend consistency vs chop)
 * - Whole-board mid-rank percentile (p99.8 · #1/130 or p0.2 · #1/80 ex-⊘)
 * - CONV conviction score with 5-dot visual rating
 * - Embedded 5-minute candlestick HTML5 Canvas chart with shaded OB Z zone,
 *   dotted level rays (R1, R2, S1-S4), dashed VWAP, and glowing active price marker
 * - 4-Point institutional alignment chip and full chart switch trigger
 */

(function () {
    class OrderBlockPopupModal {
        constructor() {
            this.modalEl = null;
            this.chartCanvas = null;
            this.chartCtx = null;
            this.sparkCanvas = null;
            this.sparkCtx = null;
            this.isOpen = false;
            this.currentSymbol = null;
            this.cachedData = null;

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }

        init() {
            this.modalEl = document.getElementById('orderblock-stock-modal');
            if (!this.modalEl) {
                this.buildModalDOM();
            } else {
                this.chartCanvas = document.getElementById('ob-candlestick-canvas');
                if (this.chartCanvas) this.chartCtx = this.chartCanvas.getContext('2d');
                this.sparkCanvas = document.getElementById('ob-sparkline-canvas');
                if (this.sparkCanvas) this.sparkCtx = this.sparkCanvas.getContext('2d');
            }
            this.bindEvents();
        }

        buildModalDOM() {
            this.modalEl = document.createElement('div');
            this.modalEl.id = 'orderblock-stock-modal';
            this.modalEl.className = 'modal hidden orderblock-modal-backdrop';
            this.modalEl.innerHTML = `
                <div class="orderblock-modal-dialog">
                    <div class="orderblock-card" id="ob-modal-card">
                        <!-- Card Header -->
                        <div class="ob-card-header">
                            <div class="ob-header-main">
                                <div class="ob-sym-row">
                                    <h3 id="ob-card-symbol" class="ob-card-title font-mono font-bold">--</h3>
                                    <span id="ob-card-sector" class="ob-sector-badge font-mono">--</span>
                                </div>
                                <div class="ob-price-row">
                                    <span id="ob-card-price" class="ob-price font-mono font-bold">₹--</span>
                                    <span id="ob-card-daymove" class="ob-daymove font-mono text-sm">--%</span>
                                </div>
                            </div>
                            <div class="ob-header-spark">
                                <canvas id="ob-sparkline-canvas" width="120" height="42" class="ob-spark-canvas"></canvas>
                                <span class="ob-spark-label">Day Path</span>
                            </div>
                            <button id="ob-modal-close" class="close-btn ob-close-btn close-modal" type="button" title="Close (Esc)">✕</button>
                        </div>

                        <!-- Sub-header Badges: Rank, Conviction, Pick Rule -->
                        <div class="ob-badges-row font-mono text-xs">
                            <div class="ob-badge-item">
                                <span class="ob-badge-lbl text-muted">RANK</span>
                                <span id="ob-badge-rank" class="ob-badge-val font-bold text-cyan">p99.8 · #1/130</span>
                            </div>
                            <div class="ob-badge-item">
                                <span class="ob-badge-lbl text-muted">CONV</span>
                                <span id="ob-badge-conv" class="ob-badge-val font-bold text-gold">97 ●●●●●</span>
                            </div>
                            <div class="ob-badge-item">
                                <span class="ob-badge-lbl text-muted">RULE</span>
                                <span id="ob-badge-rule" class="ob-badge-val font-bold text-green">PICK · BULLISH #1</span>
                            </div>
                        </div>

                        <!-- Embedded 5-Minute Candlestick Chart -->
                        <div class="ob-chart-container">
                            <div class="ob-chart-header font-mono text-xs text-muted">
                                <span>5m Session Candles (09:20 - 15:30 IST)</span>
                                <span id="ob-chart-vwap-tag" class="text-cyan font-bold">VWAP: ₹--</span>
                            </div>
                            <div class="ob-canvas-wrap">
                                <canvas id="ob-candlestick-canvas" width="500" height="230"></canvas>
                            </div>
                        </div>

                        <!-- Institutional Metric Ladders -->
                        <div class="ob-metrics-grid font-mono text-xs">
                            <div class="ob-metric-box">
                                <span class="ob-metric-name text-muted">Order Block (OB)</span>
                                <span id="ob-val-block" class="ob-metric-val">₹-- - ₹--</span>
                            </div>
                            <div class="ob-metric-box">
                                <span class="ob-metric-name text-muted">Zone Z / Invalidation</span>
                                <span id="ob-val-z-inval" class="ob-metric-val text-cyan">₹-- · ₹--</span>
                            </div>
                            <div class="ob-metric-box">
                                <span class="ob-metric-name text-muted">Targets (T1 / T2)</span>
                                <span id="ob-val-targets" class="ob-metric-val text-gold">₹-- · ₹--</span>
                            </div>
                            <div class="ob-metric-box">
                                <span class="ob-metric-name text-muted">Risk-to-Reward (R:R)</span>
                                <span id="ob-val-rr" class="ob-metric-val text-accent font-bold">1:2.7</span>
                            </div>
                        </div>

                        <!-- Footer Actions & 4-Point Alignment -->
                        <div class="ob-card-footer">
                            <div class="ob-align-chip-wrap">
                                <span class="text-xs text-muted mr-1">Alignment:</span>
                                <span id="ob-card-align-chip" class="alignment-badge-chip font-mono text-xs">4/4 Full Edge</span>
                            </div>
                            <div class="ob-footer-btns">
                                <button id="btn-ob-open-chart" class="btn-primary btn-sm" type="button">📈 Open Full Chart</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(this.modalEl);

            this.chartCanvas = document.getElementById('ob-candlestick-canvas');
            if (this.chartCanvas) this.chartCtx = this.chartCanvas.getContext('2d');

            this.sparkCanvas = document.getElementById('ob-sparkline-canvas');
            if (this.sparkCanvas) this.sparkCtx = this.sparkCanvas.getContext('2d');
        }

        bindEvents() {
            if (!this.modalEl) return;
            const closeBtn = document.getElementById('ob-modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.closeModal();
                });
            }

            // Click outside card (backdrop click) closes the modal
            this.modalEl.addEventListener('click', (e) => {
                if (!e.target.closest('.orderblock-card')) {
                    this.closeModal();
                }
            });

            // Prevent clicks inside the card from bubbling to backdrop handlers
            const card = document.getElementById('ob-modal-card') || this.modalEl.querySelector('.orderblock-card');
            if (card) {
                card.addEventListener('click', (e) => {
                    if (e.target.closest('#ob-modal-close, .close-modal')) {
                        this.closeModal();
                    } else {
                        e.stopPropagation();
                    }
                });
            }

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) this.closeModal();
            });

            const openChartBtn = document.getElementById('btn-ob-open-chart');
            if (openChartBtn) {
                openChartBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (this.currentSymbol && typeof window.switchChartSymbol === 'function') {
                        window.switchChartSymbol(this.currentSymbol);
                        if (typeof window.switchAppView === 'function') window.switchAppView('chart');
                        this.closeModal();
                    }
                });
            }
        }

        async openModal(symbol, summaryData = {}) {
            this.currentSymbol = symbol;
            if (!this.modalEl) this.init();

            // Populate preliminary data
            const cleanSym = symbol.replace('NSE:', '').replace('-EQ', '');
            document.getElementById('ob-card-symbol').textContent = cleanSym;
            document.getElementById('ob-card-sector').textContent = summaryData.sector || 'Equities';
            document.getElementById('ob-card-price').textContent = summaryData.price ? `₹${Number(summaryData.price).toFixed(2)}` : (summaryData.current_price ? `₹${Number(summaryData.current_price).toFixed(2)}` : '₹--');

            const movePct = summaryData.day_move_pct !== undefined ? summaryData.day_move_pct : 0;
            const moveFormatted = summaryData.day_move_formatted || `${movePct >= 0 ? '+' : ''}${Number(movePct).toFixed(2)}%`;
            const moveEl = document.getElementById('ob-card-daymove');
            moveEl.textContent = moveFormatted;
            moveEl.className = `ob-daymove font-mono text-sm ${movePct >= 0 ? 'text-green' : 'text-red'}`;

            // Show modal
            this.modalEl.classList.remove('hidden');
            this.isOpen = true;

            // Preliminary canvas feedback
            if (this.chartCanvas && this.chartCtx) {
                const w = this.chartCanvas.width;
                const h = this.chartCanvas.height;
                this.chartCtx.fillStyle = '#080d16';
                this.chartCtx.fillRect(0, 0, w, h);
                this.chartCtx.fillStyle = 'rgba(56, 189, 248, 0.7)';
                this.chartCtx.font = '12px Inter, sans-serif';
                this.chartCtx.textAlign = 'center';
                this.chartCtx.fillText('Loading 5m institutional telemetry...', w / 2, h / 2);
            }

            // Fetch enriched popup data
            try {
                const res = await fetch(`/api/v1/orderblock/popup-data?symbol=${encodeURIComponent(symbol)}`);
                if (res.ok) {
                    const payload = await res.json();
                    if (payload.success && payload.data) {
                        if (!payload.data.candles_5m || payload.data.candles_5m.length === 0) {
                            try {
                                const cRes = await fetch(`/api/v1/candles?symbol=${encodeURIComponent(symbol)}&timeframe=5m&limit=50`);
                                if (cRes.ok) {
                                    const cJson = await cRes.json();
                                    if (cJson.success && cJson.data && cJson.data.candles && cJson.data.candles.length > 0) {
                                        payload.data.candles_5m = cJson.data.candles.map(c => {
                                            const d = new Date(c.time * 1000);
                                            return {
                                                time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
                                                open: c.open,
                                                high: c.high,
                                                low: c.low,
                                                close: c.close,
                                                volume: c.volume
                                            };
                                        });
                                    }
                                }
                            } catch (cErr) {
                                console.debug('[OrderBlockPopupModal] Secondary candle fetch notice:', cErr);
                            }
                        }

                        this.cachedData = payload.data;
                        this.renderCardContent(payload.data);
                        return;
                    }
                }
            } catch (err) {
                console.warn('[OrderBlockPopupModal] Failed to fetch popup data:', err);
            }
        }

        renderCardContent(data) {
            // Update Header & Rupee Move
            const cleanSym = data.symbol.replace('NSE:', '').replace('-EQ', '');
            document.getElementById('ob-card-symbol').textContent = cleanSym;
            document.getElementById('ob-card-sector').textContent = data.sector;
            document.getElementById('ob-card-price').textContent = `₹${Number(data.price).toFixed(2)}`;

            const moveEl = document.getElementById('ob-card-daymove');
            moveEl.textContent = data.day_move_formatted || `${data.day_move_pct >= 0 ? '+' : ''}${Number(data.day_move_pct).toFixed(2)}%`;
            moveEl.className = `ob-daymove font-mono text-sm ${data.day_move_pct >= 0 ? 'text-green' : 'text-red'}`;

            // Badges
            document.getElementById('ob-badge-rank').textContent = data.rank_formatted || `p99.8 · #${data.rank}`;
            document.getElementById('ob-badge-conv').textContent = `${data.conv_score} ${data.conv_dots}`;
            
            const ruleEl = document.getElementById('ob-badge-rule');
            ruleEl.textContent = data.rule_label;
            ruleEl.className = `ob-badge-val font-bold ${data.side === 'BULLISH' ? 'text-green' : 'text-red'}`;

            // VWAP
            document.getElementById('ob-chart-vwap-tag').textContent = `VWAP: ₹${Number(data.vwap).toFixed(2)}`;

            // Metrics
            const act = data.active_zone;
            if (act) {
                document.getElementById('ob-val-block').textContent = `₹${Number(act.bottom_price).toFixed(2)} - ₹${Number(act.top_price).toFixed(2)}`;
            }
            const lad = data.ladder;
            if (lad) {
                document.getElementById('ob-val-z-inval').textContent = `₹${Number(lad.z_price).toFixed(2)} · ₹${Number(lad.invalidation_price).toFixed(2)}`;
                const t1 = data.side === 'BULLISH' ? lad.r1 : lad.s1;
                const t2 = data.side === 'BULLISH' ? lad.r2 : lad.s2;
                document.getElementById('ob-val-targets').textContent = `₹${Number(t1).toFixed(2)} · ₹${Number(t2).toFixed(2)}`;
                document.getElementById('ob-val-rr').textContent = `1:${Number(lad.risk_reward_ratio).toFixed(1)}`;
            }

            // Alignment
            if (window.orderBlockDashboard && typeof window.orderBlockDashboard.computeAlignment === 'function') {
                const align = window.orderBlockDashboard.computeAlignment(data);
                const chipEl = document.getElementById('ob-card-align-chip');
                chipEl.textContent = align.badge;
                chipEl.className = `alignment-badge-chip font-mono text-xs ${align.color === 'green' ? 'edge-full' : (align.color === 'yellow' ? 'edge-half' : 'edge-pass')}`;
            }

            // Render Canvases
            this.renderDayPathSparkline(data.sparkline_points || []);
            this.renderEmbeddedCandlestickChart(data);
        }

        renderDayPathSparkline(points) {
            if (!this.sparkCanvas || !this.sparkCtx) return;
            const ctx = this.sparkCtx;
            const w = this.sparkCanvas.width;
            const h = this.sparkCanvas.height;

            ctx.clearRect(0, 0, w, h);
            if (!points || points.length < 2) return;

            const prices = points.map(p => Number(p.price));
            const minP = Math.min(...prices);
            const maxP = Math.max(...prices);
            const range = Math.max(0.01, maxP - minP);
            const pad = 4;

            const isTrendUp = prices[prices.length - 1] >= prices[0];
            const strokeColor = isTrendUp ? '#10b981' : '#ef4444';

            // Draw Staircase Step Path
            ctx.beginPath();
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 1.8;

            const stepW = (w - (2 * pad)) / (points.length - 1);
            let prevX = pad;
            let prevY = (h - pad) - ((prices[0] - minP) / range) * (h - (2 * pad));

            ctx.moveTo(prevX, prevY);
            for (let i = 1; i < prices.length; i++) {
                const currX = pad + (i * stepW);
                const currY = (h - pad) - ((prices[i] - minP) / range) * (h - (2 * pad));
                // Horizontal step then vertical transition (staircase)
                ctx.lineTo(currX, prevY);
                ctx.lineTo(currX, currY);
                prevX = currX;
                prevY = currY;
            }
            ctx.stroke();

            // Endpoint marker
            ctx.beginPath();
            ctx.arc(prevX, prevY, 2.5, 0, Math.PI * 2);
            ctx.fillStyle = strokeColor;
            ctx.fill();
        }

        renderEmbeddedCandlestickChart(data) {
            if (!this.chartCanvas || !this.chartCtx) return;
            const ctx = this.chartCtx;
            const w = this.chartCanvas.width;
            const h = this.chartCanvas.height;
            const padX = 35;
            const padY = 25;

            ctx.clearRect(0, 0, w, h);

            // Dark backdrop
            ctx.fillStyle = '#080d16';
            ctx.fillRect(0, 0, w, h);

            const candles = data.candles_5m || [];
            if (candles.length === 0) {
                ctx.fillStyle = 'rgba(148, 163, 184, 0.7)';
                ctx.font = '12px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Intraday 5m session candles synchronizing...', w / 2, (h / 2) - 8);
                ctx.fillStyle = 'rgba(100, 116, 139, 0.9)';
                ctx.font = '11px Inter, sans-serif';
                ctx.fillText('Click "Open Full Chart" below to view full historical chart', w / 2, (h / 2) + 12);
                return;
            }

            // Compute price min/max bounds
            let minP = Math.min(...candles.map(c => c.low));
            let maxP = Math.max(...candles.map(c => c.high));

            const act = data.active_zone;
            if (act) {
                minP = Math.min(minP, act.bottom_price);
                maxP = Math.max(maxP, act.top_price);
            }
            const lad = data.ladder;
            if (lad) {
                if (lad.s1) minP = Math.min(minP, lad.s1);
                if (lad.s4) minP = Math.min(minP, lad.s4);
                if (lad.r1) maxP = Math.max(maxP, lad.r1);
                if (lad.r4) maxP = Math.max(maxP, lad.r4);
            }

            const rangeP = Math.max(0.01, maxP - minP);
            const priceToY = (p) => (h - padY) - ((p - minP) / rangeP) * (h - (2 * padY));

            // Gridlines & Price labels
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {
                const p = minP + (i * (rangeP / 4));
                const y = priceToY(p);
                ctx.beginPath();
                ctx.moveTo(padX, y);
                ctx.lineTo(w - padX, y);
                ctx.stroke();

                ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
                ctx.font = '9px Inter, monospace';
                ctx.textAlign = 'right';
                ctx.fillText(p.toFixed(1), padX - 4, y + 3);
            }

            // 1. Shaded Order Block Zone
            if (act) {
                const topY = priceToY(act.top_price);
                const botY = priceToY(act.bottom_price);
                const zoneY = Math.min(topY, botY);
                const zoneH = Math.max(4, Math.abs(botY - topY));
                const isBull = (data.side === 'BULLISH');

                ctx.fillStyle = isBull ? 'rgba(34, 197, 94, 0.18)' : 'rgba(239, 68, 68, 0.18)';
                ctx.fillRect(padX, zoneY, w - (2 * padX), zoneH);

                ctx.strokeStyle = isBull ? 'rgba(34, 197, 94, 0.7)' : 'rgba(239, 68, 68, 0.7)';
                ctx.lineWidth = 1;
                ctx.strokeRect(padX, zoneY, w - (2 * padX), zoneH);

                // Zone Label Tag
                ctx.fillStyle = isBull ? '#22c55e' : '#ef4444';
                ctx.font = 'bold 9px Inter, sans-serif';
                ctx.textAlign = 'left';
                ctx.fillText(`OB Z ${Number(lad ? lad.z_price : act.top_price).toFixed(2)}`, padX + 6, zoneY + 12);
            }

            // 2. Dotted Level Rays
            if (lad) {
                const drawRay = (price, color, label, isDashed = true) => {
                    if (!price) return;
                    const y = priceToY(price);
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1;
                    ctx.setLineDash(isDashed ? [3, 3] : []);
                    ctx.beginPath();
                    ctx.moveTo(padX, y);
                    ctx.lineTo(w - padX, y);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    ctx.fillStyle = color;
                    ctx.font = '8px Inter, monospace';
                    ctx.textAlign = 'right';
                    ctx.fillText(label, w - padX - 4, y - 3);
                };

                if (data.side === 'BULLISH') {
                    drawRay(lad.r2, '#10b981', `R2 ${lad.r2}`);
                    drawRay(lad.r1, '#10b981', `R1 ${lad.r1}`);
                    drawRay(lad.invalidation_price, '#f59e0b', `S1 ${lad.invalidation_price}`);
                    if (lad.s2) drawRay(lad.s2, 'rgba(245, 158, 11, 0.5)', `S2 ${lad.s2}`);
                } else {
                    drawRay(lad.s2, '#ef4444', `S2 ${lad.s2}`);
                    drawRay(lad.s1, '#ef4444', `S1 ${lad.s1}`);
                    drawRay(lad.invalidation_price, '#f59e0b', `R1 ${lad.invalidation_price}`);
                    if (lad.r2) drawRay(lad.r2, 'rgba(245, 158, 11, 0.5)', `R2 ${lad.r2}`);
                }
            }

            // 3. Dashed Blue VWAP Line
            if (data.vwap) {
                const vwapY = priceToY(data.vwap);
                ctx.strokeStyle = '#38bdf8';
                ctx.lineWidth = 1.2;
                ctx.setLineDash([5, 4]);
                ctx.beginPath();
                ctx.moveTo(padX, vwapY);
                ctx.lineTo(w - padX, vwapY);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // 4. Candlesticks
            const candleCount = candles.length;
            const barAreaW = w - (2 * padX);
            const barW = Math.max(3, Math.min(10, (barAreaW / candleCount) * 0.7));
            const stepW = barAreaW / candleCount;

            candles.forEach((c, i) => {
                const x = padX + (i * stepW) + (stepW / 2);
                const openY = priceToY(c.open);
                const closeY = priceToY(c.close);
                const highY = priceToY(c.high);
                const lowY = priceToY(c.low);
                const isBull = c.close >= c.open;
                const color = isBull ? '#10b981' : '#ef4444';

                // Wick
                ctx.strokeStyle = color;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(x, highY);
                ctx.lineTo(x, lowY);
                ctx.stroke();

                // Candle Body
                const bodyY = Math.min(openY, closeY);
                const bodyH = Math.max(2, Math.abs(closeY - openY));
                ctx.fillStyle = color;
                ctx.fillRect(x - (barW / 2), bodyY, barW, bodyH);
            });

            // 5. Glowing Ring Marker at Current Price
            if (candles.length > 0) {
                const lastX = padX + ((candles.length - 1) * stepW) + (stepW / 2);
                const lastY = priceToY(data.price || candles[candles.length - 1].close);

                // Halo
                ctx.beginPath();
                ctx.arc(lastX, lastY, 7, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(56, 189, 248, 0.3)';
                ctx.fill();

                // Core Ring
                ctx.beginPath();
                ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
                ctx.fillStyle = '#38bdf8';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1.2;
                ctx.stroke();
            }
        }

        closeModal() {
            if (!this.modalEl) return;
            this.modalEl.classList.add('hidden');
            this.isOpen = false;
        }
    }

    // Expose Global Singletons
    window.OrderBlockPopupModal = OrderBlockPopupModal;
    window.orderBlockPopupModal = new OrderBlockPopupModal();
    window.openOrderBlockModal = (symbol, data) => window.orderBlockPopupModal.openModal(symbol, data);
})();
