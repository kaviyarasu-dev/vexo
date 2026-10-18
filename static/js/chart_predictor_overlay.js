/**
 * Frontend TradingView Canvas Corridor Predictor Overlay
 * Renders forward-projected multi-quantile probability corridor (Q0.10, Q0.50, Q0.90)
 * directly ahead of the latest candlestick on TradingView Lightweight Charts.
 */

(function () {
    class ChartPredictorOverlay {
        constructor() {
            this.canvas = null;
            this.ctx = null;
            this.chartContainer = null;
            this.prediction = null;
            this.isFallback = false;
            this.fallbackData = null;
            this.animationFrame = null;
            this.isEnabled = true;

            this.config = {
                upperColor: '#F5AC00',       // Dashed Gold for Q0.90 High
                lowerColor: '#00E5FF',       // Dashed Cyan for Q0.10 Low
                medianColor: '#089981',      // Solid Emerald/Teal for Q0.50 Median
                corridorFillTop: 'rgba(245, 172, 0, 0.12)',   // Gold gradient top
                corridorFillBottom: 'rgba(0, 229, 255, 0.08)', // Cyan gradient bottom
                lineWidth: 1.5,
                projectionBars: 2            // Forward projection width (bars)
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

            // Reuse or create canvas
            this.canvas = document.getElementById('chart-predictor-canvas');
            if (!this.canvas) {
                this.canvas = document.createElement('canvas');
                this.canvas.id = 'chart-predictor-canvas';
                this.canvas.className = 'chart-predictor-canvas';
                this.canvas.style.cssText = `
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 5;
                `;
                this.chartContainer.appendChild(this.canvas);
            }

            this.ctx = this.canvas.getContext('2d');
            this.handleResize();

            // Subscribe to chart timescale panning/zooming
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
        }

        handleResize() {
            if (!this.canvas || !this.chartContainer) return;
            const dpr = window.devicePixelRatio || 1;
            const w = this.chartContainer.clientWidth;
            const h = this.chartContainer.clientHeight;
            this.canvas.width = Math.floor(w * dpr);
            this.canvas.height = Math.floor(h * dpr);
            if (this.ctx) {
                this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            }
        }

        update(predictionData) {
            if (!predictionData) {
                this.prediction = null;
                this.clear();
                return;
            }
            this.prediction = predictionData;
            this.isFallback = false;
            this.fallbackData = null;
            this.requestRedraw();
        }

        updateFallback(fallbackPayload) {
            this.prediction = null;
            this.isFallback = true;
            this.fallbackData = fallbackPayload;
            this.requestRedraw();
        }

        clear() {
            this.prediction = null;
            this.fallbackData = null;
            this.isFallback = false;
            if (this.ctx && this.canvas && this.chartContainer) {
                this.ctx.clearRect(0, 0, this.chartContainer.clientWidth, this.chartContainer.clientHeight);
            }
        }

        requestRedraw() {
            if (!this.isEnabled) return;
            if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
            this.animationFrame = requestAnimationFrame(() => this.draw());
        }

        draw() {
            if (!this.ctx || !this.canvas || !this.chartContainer) return;
            const w = this.chartContainer.clientWidth;
            const h = this.chartContainer.clientHeight;
            this.ctx.clearRect(0, 0, w, h);

            if (!this.isEnabled) return;
            if (!window.allLoadedCandles || window.allLoadedCandles.length < 2) return;
            if (!window.mainChart || !window.candleSeries) return;

            const timeScale = window.mainChart.timeScale();
            if (!timeScale) return;

            const total = window.allLoadedCandles.length;
            const lastCandle = window.allLoadedCandles[total - 1];
            const prevCandle = window.allLoadedCandles[total - 2];

            const x0 = timeScale.timeToCoordinate(lastCandle.time);
            if (x0 === null || isNaN(x0) || x0 < -50 || x0 > w + 50) return;

            const prevX = timeScale.timeToCoordinate(prevCandle.time);
            const barSpacing = (prevX !== null && !isNaN(prevX)) ? Math.max(6, Math.abs(x0 - prevX)) : 14;

            // Project 1.5 to 2.5 bars into future
            const x1 = Math.min(w - 75, x0 + barSpacing * this.config.projectionBars);
            if (x1 <= x0) return;

            if (this.isFallback && this.fallbackData) {
                this.renderCorridor(
                    x0, x1,
                    this.fallbackData.upper,
                    this.fallbackData.median,
                    this.fallbackData.lower,
                    true
                );
                return;
            }

            if (!this.prediction) return;

            const high90 = Number(this.prediction.high_90);
            const close50 = Number(this.prediction.close_50);
            const low10 = Number(this.prediction.low_10);

            if (isNaN(high90) || isNaN(close50) || isNaN(low10)) return;

            this.renderCorridor(x0, x1, high90, close50, low10, false);
        }

        renderCorridor(x0, x1, upperPrice, medianPrice, lowerPrice, isAtrFallback) {
            const series = window.candleSeries;
            const yUpper = series.priceToCoordinate(upperPrice);
            const yMedian = series.priceToCoordinate(medianPrice);
            const yLower = series.priceToCoordinate(lowerPrice);

            if (yUpper === null || yMedian === null || yLower === null) return;
            if (isNaN(yUpper) || isNaN(yMedian) || isNaN(yLower)) return;

            this.ctx.save();

            // 1. Shaded Corridor Fill (Gradient Between Upper & Lower)
            const grad = this.ctx.createLinearGradient(0, yUpper, 0, yLower);
            if (isAtrFallback) {
                grad.addColorStop(0, 'rgba(148, 163, 184, 0.15)');
                grad.addColorStop(1, 'rgba(100, 116, 139, 0.05)');
            } else {
                grad.addColorStop(0, this.config.corridorFillTop);
                grad.addColorStop(0.5, 'rgba(41, 98, 255, 0.06)');
                grad.addColorStop(1, this.config.corridorFillBottom);
            }

            this.ctx.fillStyle = grad;
            this.ctx.beginPath();
            this.ctx.moveTo(x0, yMedian);
            this.ctx.lineTo(x1, yUpper);
            this.ctx.lineTo(x1, yLower);
            this.ctx.closePath();
            this.ctx.fill();

            // 2. Upper Boundary (Dashed Gold Q0.90)
            this.ctx.strokeStyle = isAtrFallback ? '#94A3B8' : this.config.upperColor;
            this.ctx.lineWidth = this.config.lineWidth;
            this.ctx.setLineDash([4, 4]);
            this.ctx.beginPath();
            this.ctx.moveTo(x0, yMedian);
            this.ctx.lineTo(x1, yUpper);
            this.ctx.stroke();

            // 3. Lower Boundary (Dashed Cyan Q0.10)
            this.ctx.strokeStyle = isAtrFallback ? '#64748B' : this.config.lowerColor;
            this.ctx.lineWidth = this.config.lineWidth;
            this.ctx.setLineDash([4, 4]);
            this.ctx.beginPath();
            this.ctx.moveTo(x0, yMedian);
            this.ctx.lineTo(x1, yLower);
            this.ctx.stroke();

            // 4. Median Projected Line (Solid Q0.50)
            this.ctx.strokeStyle = isAtrFallback ? '#E2E8F0' : this.config.medianColor;
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([]);
            this.ctx.beginPath();
            this.ctx.moveTo(x0, yMedian);
            this.ctx.lineTo(x1, yMedian);
            this.ctx.stroke();

            // 5. Projected Target Anchor Dot at (x1, yMedian)
            this.ctx.fillStyle = isAtrFallback ? '#E2E8F0' : this.config.medianColor;
            this.ctx.beginPath();
            this.ctx.arc(x1, yMedian, 3.5, 0, Math.PI * 2);
            this.ctx.fill();

            // 6. Right-Edge Pill Tags
            const tagLabelUpper = isAtrFallback ? `+ATR ₹${upperPrice.toFixed(2)}` : `Q90 ₹${upperPrice.toFixed(2)}`;
            const tagLabelLower = isAtrFallback ? `-ATR ₹${lowerPrice.toFixed(2)}` : `Q10 ₹${lowerPrice.toFixed(2)}`;
            const tagLabelMed = isAtrFallback ? `BASE ₹${medianPrice.toFixed(2)}` : `Q50 ₹${medianPrice.toFixed(2)}`;

            this.drawTag(tagLabelUpper, x1 + 4, yUpper, isAtrFallback ? '#94A3B8' : this.config.upperColor);
            this.drawTag(tagLabelMed, x1 + 4, yMedian, isAtrFallback ? '#E2E8F0' : this.config.medianColor);
            this.drawTag(tagLabelLower, x1 + 4, yLower, isAtrFallback ? '#64748B' : this.config.lowerColor);

            this.ctx.restore();
        }

        drawTag(text, x, y, color) {
            this.ctx.font = '10px "Roboto Mono", monospace';
            const textWidth = this.ctx.measureText(text).width;
            const padX = 4;
            const h = 14;

            this.ctx.fillStyle = 'rgba(15, 20, 31, 0.85)';
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 1;
            this.ctx.setLineDash([]);
            this.ctx.fillRect(x, y - h / 2, textWidth + padX * 2, h);
            this.ctx.strokeRect(x, y - h / 2, textWidth + padX * 2, h);

            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(text, x + padX, y);
        }
    }

    // Expose singleton instance on window
    window.chartPredictorOverlay = new ChartPredictorOverlay();
    window.PredictorOverlay = window.chartPredictorOverlay;
})();
