/**
 * TradingView 5-Minute HTML5 Canvas OrderBlock Overlay
 * Renders institutional order-block zones, mitigation boundaries,
 * ladder levels (Z, S1-S4, R1-R4, R:R), and equal high/low liquidity pools.
 */

(function () {
    class ChartOrderBlockOverlay {
        constructor() {
            this.canvas = null;
            this.ctx = null;
            this.chartContainer = null;
            this.data = null;
            this.activeSymbol = null;
            this.animationFrame = null;
            this.isEnabled = true;

            this.colors = {
                bullishFill: 'rgba(34, 197, 94, 0.15)',
                bullishBorder: 'rgba(34, 197, 94, 0.8)',
                bearishFill: 'rgba(239, 68, 68, 0.15)',
                bearishBorder: 'rgba(239, 68, 68, 0.8)',
                mitigatedFill: 'rgba(148, 163, 184, 0.08)',
                mitigatedBorder: 'rgba(148, 163, 184, 0.25)',
                zLine: '#38bdf8',            // Cyan for reference Z
                invalidationLine: '#ef4444', // Red for invalidation
                targetLine: '#eab308',       // Gold for swing targets
                liquidityLine: '#a855f7'     // Purple for EQH/EQL pools
            };

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }

        init() {
            this.chartContainer = document.getElementById('chart-container');
            if (!this.chartContainer) return;

            this.canvas = document.getElementById('chart-orderblock-canvas');
            if (!this.canvas) {
                this.canvas = document.createElement('canvas');
                this.canvas.id = 'chart-orderblock-canvas';
                this.canvas.className = 'chart-orderblock-canvas';
                this.canvas.style.cssText = `
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 6;
                `;
                this.chartContainer.appendChild(this.canvas);
            }

            this.ctx = this.canvas.getContext('2d');
            this.handleResize();

            // Subscribe to timescale pan & zoom
            if (window.mainChart) {
                const ts = window.mainChart.timeScale();
                if (ts && typeof ts.subscribeVisibleLogicalRangeChange === 'function') {
                    ts.subscribeVisibleLogicalRangeChange(() => this.requestRedraw());
                }
            }

            window.addEventListener('resize', () => {
                this.handleResize();
                this.requestRedraw();
            });

            // Listen for timeframe or symbol changes
            window.addEventListener('chart-data-loaded', (e) => {
                const sym = e.detail?.symbol || window.currentActiveSymbol;
                const tf = e.detail?.timeframe || window.currentSymbolTimeframe;
                this.onChartUpdate(sym, tf);
            });
        }

        handleResize() {
            if (!this.canvas || !this.chartContainer) return;
            const dpr = window.devicePixelRatio || 1;
            const w = this.chartContainer.clientWidth;
            const h = this.chartContainer.clientHeight;
            this.canvas.width = Math.floor(w * dpr);
            this.canvas.height = Math.floor(h * dpr);
            this.ctx.setTransform(1, 0, 0, 1, 0, 0);
            this.ctx.scale(dpr, dpr);
        }

        requestRedraw() {
            if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
            this.animationFrame = requestAnimationFrame(() => this.render());
        }

        async onChartUpdate(symbol, timeframe) {
            this.activeSymbol = symbol;
            if (timeframe !== '5m') {
                this.clear();
                return;
            }
            await this.fetchZones(symbol);
        }

        async fetchZones(symbol) {
            try {
                const res = await fetch(`/api/v1/orderblock/zones?symbol=${encodeURIComponent(symbol)}`);
                if (!res.ok) return;
                const payload = await res.json();
                if (payload.success && payload.data) {
                    this.data = payload.data;
                    this.requestRedraw();
                }
            } catch (err) {
                console.warn('[OrderBlockOverlay] Failed to fetch zones:', err);
            }
        }

        clear() {
            if (!this.ctx || !this.canvas) return;
            const dpr = window.devicePixelRatio || 1;
            this.ctx.clearRect(0, 0, this.canvas.width / dpr, this.canvas.height / dpr);
        }

        render() {
            this.clear();
            if (!this.isEnabled) return;
            if (window.currentSymbolTimeframe !== '5m') return;
            if (!this.data || !window.candleSeries || !window.mainChart) return;

            const timeScale = window.mainChart.timeScale();
            const series = window.candleSeries;
            const chartW = this.chartContainer.clientWidth;

            // 1. Render Historical Mitigated Zones (faded gray)
            const historical = this.data.historical_zones || [];
            for (const hz of historical) {
                this.drawZoneBox(hz, series, chartW, this.colors.mitigatedFill, this.colors.mitigatedBorder, true);
            }

            // 2. Render Active Unmitigated Zone
            const active = this.data.active_zone;
            if (active) {
                const isBull = (active.block_type === 'BULLISH');
                const fillColor = isBull ? this.colors.bullishFill : this.colors.bearishFill;
                const borderColor = isBull ? this.colors.bullishBorder : this.colors.bearishBorder;
                this.drawZoneBox(active, series, chartW, fillColor, borderColor, false);

                // 3. Render Levels Ladder (Z, S1-S4, R1-R4, R:R)
                const ladder = this.data.ladder;
                if (ladder) {
                    this.drawLadderLines(ladder, isBull, series, chartW);
                }
            }

            // 4. Render Equal Highs / Lows Liquidity Pools
            const pools = this.data.liquidity_pools || [];
            for (const p of pools) {
                this.drawLiquidityPool(p, series, chartW);
            }
        }

        drawZoneBox(zone, series, chartW, fillColor, borderColor, isMitigated) {
            const topY = series.priceToCoordinate(zone.top_price);
            const botY = series.priceToCoordinate(zone.bottom_price);
            if (topY === null || botY === null) return;

            const y = Math.min(topY, botY);
            const h = Math.abs(botY - topY);
            const startX = 60; // Left offset
            const width = chartW - startX - 70; // Extend across chart up to price scale

            this.ctx.fillStyle = fillColor;
            this.ctx.fillRect(startX, y, width, h);

            this.ctx.strokeStyle = borderColor;
            this.ctx.lineWidth = 1;
            this.ctx.setLineDash(isMitigated ? [4, 4] : [6, 3]);
            this.ctx.strokeRect(startX, y, width, h);
            this.ctx.setLineDash([]);

            // Badge label on the right
            this.ctx.fillStyle = borderColor;
            this.ctx.font = '10px Inter, sans-serif';
            const label = isMitigated ? `Mitigated ${zone.block_type} OB` : `Active ${zone.block_type} OB [₹${zone.bottom_price} - ₹${zone.top_price}]`;
            this.ctx.fillText(label, startX + 8, y + 14);
        }

        drawLadderLines(ladder, isBull, series, chartW) {
            const zY = series.priceToCoordinate(ladder.z_price);
            const invalY = series.priceToCoordinate(ladder.invalidation_price);
            const targetY = series.priceToCoordinate(isBull ? ladder.r2 : ladder.s2);

            const startX = 60;
            const endX = chartW - 70;

            // Z Reference Ray
            if (zY !== null) {
                this.drawLineWithTag(startX, zY, endX, zY, this.colors.zLine, `Z: ₹${ladder.z_price}`, false);
            }

            // Invalidation Ray (S1 / R1)
            if (invalY !== null) {
                this.drawLineWithTag(startX, invalY, endX, invalY, this.colors.invalidationLine, `Stop (S1): ₹${ladder.invalidation_price}`, false);
            }

            // Primary Target Ray (R2 / S2)
            if (targetY !== null) {
                const targetPrice = isBull ? ladder.r2 : ladder.s2;
                this.drawLineWithTag(startX, targetY, endX, targetY, this.colors.targetLine, `Target (T2): ₹${targetPrice} (R:R ${ladder.risk_reward_ratio}x)`, true);
            }
        }

        drawLiquidityPool(pool, series, chartW) {
            const y = series.priceToCoordinate(pool.price_level);
            if (y === null) return;

            const startX = 60;
            const endX = chartW - 70;
            const tag = pool.pool_type === 'EQUAL_HIGHS' ? `EQH Pool (${pool.touches}x): ₹${pool.price_level}` : `EQL Pool (${pool.touches}x): ₹${pool.price_level}`;

            this.ctx.strokeStyle = this.colors.liquidityLine;
            this.ctx.lineWidth = 1;
            this.ctx.setLineDash([3, 3]);
            this.ctx.beginPath();
            this.ctx.moveTo(startX, y);
            this.ctx.lineTo(endX, y);
            this.ctx.stroke();
            this.ctx.setLineDash([]);

            this.ctx.fillStyle = this.colors.liquidityLine;
            this.ctx.font = '9px Inter, sans-serif';
            this.ctx.fillText(tag, endX - 140, y - 4);
        }

        drawLineWithTag(x1, y1, x2, y2, color, label, isDashed) {
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 1.5;
            this.ctx.setLineDash(isDashed ? [6, 4] : []);
            this.ctx.beginPath();
            this.ctx.moveTo(x1, y1);
            this.ctx.lineTo(x2, y2);
            this.ctx.stroke();
            this.ctx.setLineDash([]);

            // Label Box
            this.ctx.fillStyle = color;
            this.ctx.font = 'bold 10px Inter, sans-serif';
            this.ctx.fillText(label, x2 - 130, y1 - 4);
        }
    }

    window.ChartOrderBlockOverlay = ChartOrderBlockOverlay;
    window.orderBlockOverlay = new ChartOrderBlockOverlay();
    window.initOrderBlockOverlay = () => window.orderBlockOverlay.init();
})();
