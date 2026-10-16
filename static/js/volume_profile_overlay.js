/**
 * High-Performance Canvas Volume Profile & Market Profile (TPO) Engine
 * Supports Visible Range (VRVP), Session Volume Profile (SVP), and Time Price Opportunity (TPO).
 */

(function () {
    class VolumeProfileOverlay {
        constructor() {
            this.canvas = null;
            this.ctx = null;
            this.chartContainer = null;
            this.activeMode = null; // 'visible_range_vp', 'session_vp', 'tpo', null
            this.config = {
                rows: 70,
                valueAreaPct: 0.70,
                widthPct: 0.28,
                upColor: '#2962FF',        // Blue (TradingView classic)
                downColor: '#F5AC00',      // Yellow / Gold
                pocColor: '#F23645',        // Solid Red
                vaLineColor: '#00E5FF',     // Cyan dashed
                outsideOpacity: 0.35
            };

            this.cachedProfile = null;
            this.mousePos = null;
            this.animationFrame = null;

            document.addEventListener('DOMContentLoaded', () => this.init());
        }

        init() {
            this.chartContainer = document.getElementById('chart-container');
            if (!this.chartContainer) return;

            // Create Canvas
            this.canvas = document.getElementById('volume-profile-canvas');
            if (!this.canvas) {
                this.canvas = document.createElement('canvas');
                this.canvas.id = 'volume-profile-canvas';
                this.canvas.className = 'volume-profile-canvas';
                this.canvas.style.cssText = `
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 4;
                `;
                this.chartContainer.appendChild(this.canvas);
            }
            this.ctx = this.canvas.getContext('2d');
            this.handleResize();

            // Hook chart events
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

            // Hover tooltip on chart
            this.chartContainer.addEventListener('mousemove', (e) => {
                const rect = this.chartContainer.getBoundingClientRect();
                this.mousePos = {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top
                };
                if (this.activeMode) this.requestRedraw();
            });

            this.chartContainer.addEventListener('mouseleave', () => {
                this.mousePos = null;
                if (this.activeMode) this.requestRedraw();
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

        enable(mode = 'visible_range_vp', customConfig = {}) {
            this.activeMode = mode;
            Object.assign(this.config, customConfig);
            if (this.canvas) this.canvas.style.display = 'block';
            console.log(`[VolumeProfile] Enabled mode: ${mode}`);
            this.handleResize();
            this.requestRedraw();
        }

        disable() {
            this.activeMode = null;
            this.cachedProfile = null;
            if (this.ctx && this.canvas) {
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            }
            if (this.canvas) this.canvas.style.display = 'none';
        }

        requestRedraw() {
            if (!this.activeMode) return;
            if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
            this.animationFrame = requestAnimationFrame(() => this.draw());
        }

        updateLegendTagVal(key, text) {
            const tags = document.querySelectorAll('.study-legend-tag');
            tags.forEach(t => {
                if (t.id && t.id.toLowerCase().includes(key.toLowerCase())) {
                    const v = t.querySelector('.study-tag-val');
                    if (v) v.textContent = text;
                }
            });
        }

        draw() {
            if (!this.ctx || !this.canvas || !this.activeMode) return;
            const w = this.chartContainer.clientWidth;
            const h = this.chartContainer.clientHeight;
            this.ctx.clearRect(0, 0, w, h);

            if (!window.allLoadedCandles || window.allLoadedCandles.length < 3) return;
            if (!window.candleSeries || !window.mainChart) return;

            if (this.activeMode === 'visible_range_vp') {
                this.drawVisibleRangeVP(w, h);
            } else if (
                this.activeMode === 'session_vp' || 
                this.activeMode === 'session_vp_hd' || 
                this.activeMode === 'auto_anchored_vp' || 
                this.activeMode === 'fixed_range_vp' || 
                this.activeMode === 'periodic_vp'
            ) {
                this.drawSessionVP(w, h);
            } else if (this.activeMode === 'tpo') {
                this.drawTPOMarketProfile(w, h, false);
            } else if (this.activeMode === 'session_tpo') {
                this.drawTPOMarketProfile(w, h, true);
            }
        }

        getVisibleCandles() {
            if (!window.mainChart || !window.allLoadedCandles) return [];
            const range = window.mainChart.timeScale().getVisibleLogicalRange();
            if (!range) return window.allLoadedCandles.slice(-150);

            const total = window.allLoadedCandles.length;
            const startIdx = Math.max(0, Math.floor(range.from));
            const endIdx = Math.min(total - 1, Math.ceil(range.to));

            if (startIdx >= total || endIdx < 0 || startIdx > endIdx) {
                return window.allLoadedCandles.slice(-100);
            }
            return window.allLoadedCandles.slice(startIdx, endIdx + 1);
        }

        drawVisibleRangeVP(width, height) {
            const candles = this.getVisibleCandles();
            if (candles.length < 5) return;

            let minP = Infinity, maxP = -Infinity;
            candles.forEach(c => {
                if (c.low < minP) minP = c.low;
                if (c.high > maxP) maxP = c.high;
            });
            const pRange = maxP - minP;
            if (pRange <= 0) return;

            const rows = this.config.rows || 70;
            const binSize = pRange / rows;
            const totalVols = new Float64Array(rows);
            const upVols = new Float64Array(rows);
            const downVols = new Float64Array(rows);

            // Populate volume bins
            candles.forEach(c => {
                const vol = c.volume || 1;
                const isUp = c.close >= c.open;
                const startBin = Math.max(0, Math.min(rows - 1, Math.floor((c.low - minP) / binSize)));
                const endBin = Math.max(0, Math.min(rows - 1, Math.floor((c.high - minP) / binSize)));
                const covered = Math.max(1, endBin - startBin + 1);
                const volPerBin = vol / covered;

                for (let b = startBin; b <= endBin; b++) {
                    totalVols[b] += volPerBin;
                    if (isUp) upVols[b] += volPerBin;
                    else downVols[b] += volPerBin;
                }
            });

            // Find POC and Max Volume
            let maxBinVol = 0;
            let pocIdx = 0;
            let totalVolumeSum = 0;

            for (let i = 0; i < rows; i++) {
                totalVolumeSum += totalVols[i];
                if (totalVols[i] > maxBinVol) {
                    maxBinVol = totalVols[i];
                    pocIdx = i;
                }
            }

            if (maxBinVol <= 0) return;

            // Value Area Calculation (70%)
            const inVA = new Uint8Array(rows);
            inVA[pocIdx] = 1;
            let cumVAVol = totalVols[pocIdx];
            const targetVAVol = totalVolumeSum * (this.config.valueAreaPct || 0.70);

            let upIdx = pocIdx + 1;
            let downIdx = pocIdx - 1;

            while (cumVAVol < targetVAVol && (upIdx < rows || downIdx >= 0)) {
                const vUp = upIdx < rows ? totalVols[upIdx] : 0;
                const vDown = downIdx >= 0 ? totalVols[downIdx] : 0;
                if (vUp === 0 && vDown === 0) break;

                if (vUp >= vDown && upIdx < rows) {
                    inVA[upIdx] = 1;
                    cumVAVol += vUp;
                    upIdx++;
                } else if (downIdx >= 0) {
                    inVA[downIdx] = 1;
                    cumVAVol += vDown;
                    downIdx--;
                } else {
                    break;
                }
            }

            // Find VAH and VAL index
            let vahIdx = pocIdx;
            let valIdx = pocIdx;
            for (let i = 0; i < rows; i++) {
                if (inVA[i]) {
                    if (i > vahIdx) vahIdx = i;
                    if (i < valIdx) valIdx = i;
                }
            }

            const maxBarWidth = width * (this.config.widthPct || 0.28);
            const rightEdge = width - 65; // Price scale offset

            let hoveredBin = null;

            // Render horizontal histogram bars
            for (let i = 0; i < rows; i++) {
                const bPrice = minP + (i + 0.5) * binSize;
                const yCoord = window.candleSeries.priceToCoordinate(bPrice);
                if (yCoord == null || yCoord < -10 || yCoord > height + 10) continue;

                const nextP = minP + (i + 1.5) * binSize;
                const yNext = window.candleSeries.priceToCoordinate(nextP);
                const barHeight = Math.max(2, Math.abs((yNext || yCoord) - yCoord) - 0.5);

                const binTot = totalVols[i];
                if (binTot <= 0) continue;

                const barW = (binTot / maxBinVol) * maxBarWidth;
                const upW = (upVols[i] / binTot) * barW;
                const downW = barW - upW;

                const isInsideVA = inVA[i] === 1;
                const opacity = isInsideVA ? 0.85 : this.config.outsideOpacity;

                // Check mouse hover
                if (this.mousePos &&
                    this.mousePos.x >= rightEdge - barW &&
                    this.mousePos.x <= rightEdge &&
                    this.mousePos.y >= yCoord - barHeight/2 &&
                    this.mousePos.y <= yCoord + barHeight/2) {
                    hoveredBin = {
                        price: bPrice,
                        total: binTot,
                        up: upVols[i],
                        down: downVols[i],
                        isPoc: (i === pocIdx),
                        isVA: isInsideVA
                    };
                }

                // Up Volume bar (Blue)
                this.ctx.fillStyle = hexToRgba(this.config.upColor, opacity);
                this.ctx.fillRect(rightEdge - barW, yCoord - barHeight/2, upW, barHeight);

                // Down Volume bar (Yellow)
                this.ctx.fillStyle = hexToRgba(this.config.downColor, opacity);
                this.ctx.fillRect(rightEdge - barW + upW, yCoord - barHeight/2, downW, barHeight);
            }

            // Draw POC (Point of Control) line
            const pocPrice = minP + (pocIdx + 0.5) * binSize;
            const pocY = window.candleSeries.priceToCoordinate(pocPrice);
            if (pocY != null) {
                this.ctx.strokeStyle = this.config.pocColor;
                this.ctx.lineWidth = 2;
                this.ctx.setLineDash([]);
                this.ctx.beginPath();
                this.ctx.moveTo(rightEdge - maxBarWidth - 20, pocY);
                this.ctx.lineTo(rightEdge, pocY);
                this.ctx.stroke();

                // POC Tag
                this.drawTag(`POC ₹${pocPrice.toFixed(2)}`, rightEdge - maxBarWidth - 22, pocY, this.config.pocColor, '#FFFFFF');
            }

            // Draw VAH (Value Area High) line
            const vahPrice = minP + (vahIdx + 0.5) * binSize;
            const vahY = window.candleSeries.priceToCoordinate(vahPrice);
            if (vahY != null) {
                this.ctx.strokeStyle = this.config.vaLineColor;
                this.ctx.lineWidth = 1.5;
                this.ctx.setLineDash([4, 4]);
                this.ctx.beginPath();
                this.ctx.moveTo(rightEdge - maxBarWidth, vahY);
                this.ctx.lineTo(rightEdge, vahY);
                this.ctx.stroke();

                this.drawTag(`VAH ₹${vahPrice.toFixed(2)}`, rightEdge - maxBarWidth - 4, vahY, '#0097A7', '#FFFFFF');
            }

            // Draw VAL (Value Area Low) line
            const valPrice = minP + (valIdx + 0.5) * binSize;
            const valY = window.candleSeries.priceToCoordinate(valPrice);
            if (valY != null) {
                this.ctx.strokeStyle = this.config.vaLineColor;
                this.ctx.lineWidth = 1.5;
                this.ctx.setLineDash([4, 4]);
                this.ctx.beginPath();
                this.ctx.moveTo(rightEdge - maxBarWidth, valY);
                this.ctx.lineTo(rightEdge, valY);
                this.ctx.stroke();

                this.drawTag(`VAL ₹${valPrice.toFixed(2)}`, rightEdge - maxBarWidth - 4, valY, '#0097A7', '#FFFFFF');
            }

            // Hover Tooltip
            if (hoveredBin && this.mousePos) {
                this.drawHoverTooltip(hoveredBin, this.mousePos.x, this.mousePos.y);
            }
        }

        drawSessionVP(width, height) {
            const candles = this.getVisibleCandles();
            if (candles.length < 3) return;

            const sessions = new Map();
            candles.forEach(c => {
                const dateStr = new Date((c.time + 19800) * 1000).toISOString().slice(0, 10);
                if (!sessions.has(dateStr)) sessions.set(dateStr, []);
                sessions.get(dateStr).push(c);
            });

            let latestPoc = 0;

            sessions.forEach((sessCandles) => {
                let minP = Infinity, maxP = -Infinity;
                sessCandles.forEach(c => {
                    if (c.low < minP) minP = c.low;
                    if (c.high > maxP) maxP = c.high;
                });
                const pRange = maxP - minP;
                if (pRange <= 0) return;

                const firstTime = sessCandles[0].time;
                const lastTime = sessCandles[sessCandles.length - 1].time;
                const xStart = window.mainChart.timeScale().timeToCoordinate(firstTime);
                const xEnd = window.mainChart.timeScale().timeToCoordinate(lastTime);
                if (xStart == null) return;

                const clusterWidth = (xEnd != null && xEnd > xStart) ? Math.max(25, (xEnd - xStart) * 0.75) : 35;
                const rows = 40;
                const binSize = pRange / rows;
                const vols = new Float64Array(rows);
                let maxV = 0, pocIdx = 0;

                sessCandles.forEach(c => {
                    const vol = (c.volume && c.volume > 0) ? c.volume : 1;
                    const sBin = Math.max(0, Math.min(rows - 1, Math.floor((c.low - minP) / binSize)));
                    const eBin = Math.max(0, Math.min(rows - 1, Math.floor((c.high - minP) / binSize)));
                    const count = Math.max(1, eBin - sBin + 1);
                    const vPerBin = vol / count;
                    for (let b = sBin; b <= eBin; b++) {
                        vols[b] += vPerBin;
                    }
                });

                for (let i = 0; i < rows; i++) {
                    if (vols[i] > maxV) { maxV = vols[i]; pocIdx = i; }
                }
                if (maxV <= 0) return;

                // Value area
                const totalVol = vols.reduce((a, b) => a + b, 0);
                const inVA = new Uint8Array(rows);
                inVA[pocIdx] = 1;
                let cumVA = vols[pocIdx];
                let up = pocIdx + 1, down = pocIdx - 1;
                while (cumVA < totalVol * 0.70 && (up < rows || down >= 0)) {
                    const vUp = up < rows ? vols[up] : 0;
                    const vDown = down >= 0 ? vols[down] : 0;
                    if (vUp === 0 && vDown === 0) break;
                    if (vUp >= vDown && up < rows) { inVA[up] = 1; cumVA += vUp; up++; }
                    else if (down >= 0) { inVA[down] = 1; cumVA += vDown; down--; }
                    else break;
                }

                // Render histogram bars
                for (let i = 0; i < rows; i++) {
                    const bPrice = minP + (i + 0.5) * binSize;
                    const y = window.candleSeries.priceToCoordinate(bPrice);
                    if (y == null) continue;

                    const barW = (vols[i] / maxV) * clusterWidth;
                    this.ctx.fillStyle = inVA[i] ? hexToRgba(this.config.upColor, 0.75) : hexToRgba(this.config.upColor, 0.30);
                    this.ctx.fillRect(xStart, y - 1, barW, 2.5);
                }

                // Session POC ray
                const pocPrice = minP + (pocIdx + 0.5) * binSize;
                latestPoc = pocPrice;
                const pocY = window.candleSeries.priceToCoordinate(pocPrice);
                if (pocY != null) {
                    this.ctx.strokeStyle = this.config.pocColor;
                    this.ctx.lineWidth = 1.5;
                    this.ctx.beginPath();
                    this.ctx.moveTo(xStart, pocY);
                    this.ctx.lineTo(xStart + clusterWidth + 10, pocY);
                    this.ctx.stroke();
                }
            });

            if (latestPoc > 0) {
                this.updateLegendTagVal('session_vp', `POC ₹${latestPoc.toFixed(2)}`);
            }
        }

        drawTPOMarketProfile(width, height, isPerSession = false) {
            const candles = this.getVisibleCandles();
            if (candles.length < 3) return;

            const brackets = "ABCDEFGHIJKLM";

            if (isPerSession) {
                // Per-Session TPO Market Profile
                const sessions = new Map();
                candles.forEach(c => {
                    const dateStr = new Date((c.time + 19800) * 1000).toISOString().slice(0, 10);
                    if (!sessions.has(dateStr)) sessions.set(dateStr, []);
                    sessions.get(dateStr).push(c);
                });

                let lastPoc = 0;

                sessions.forEach((sessCandles) => {
                    let minP = Infinity, maxP = -Infinity;
                    sessCandles.forEach(c => {
                        if (c.low < minP) minP = c.low;
                        if (c.high > maxP) maxP = c.high;
                    });
                    const pRange = maxP - minP;
                    if (pRange <= 0) return;

                    const firstTime = sessCandles[0].time;
                    const xStart = window.mainChart.timeScale().timeToCoordinate(firstTime);
                    if (xStart == null) return;

                    const rows = 28;
                    const binSize = pRange / rows;
                    const letterSets = Array.from({ length: rows }, () => new Set());

                    sessCandles.forEach((c, cIdx) => {
                        let bracketLetter = 'A';
                        if (sessCandles.length > 1) {
                            const istDate = new Date((c.time + 19800) * 1000);
                            const elapsedMin = Math.max(0, (istDate.getUTCHours() - 9) * 60 + (istDate.getUTCMinutes() - 15));
                            const bIdx = Math.min(12, Math.floor(elapsedMin / 30));
                            bracketLetter = brackets[bIdx] || 'A';
                        } else {
                            bracketLetter = brackets[cIdx % brackets.length];
                        }

                        const sBin = Math.max(0, Math.min(rows - 1, Math.floor((c.low - minP) / binSize)));
                        const eBin = Math.max(0, Math.min(rows - 1, Math.floor((c.high - minP) / binSize)));
                        for (let b = sBin; b <= eBin; b++) {
                            letterSets[b].add(bracketLetter);
                        }
                    });

                    // Find POC
                    let maxLetters = 0, pocIdx = Math.floor(rows / 2);
                    for (let i = 0; i < rows; i++) {
                        if (letterSets[i].size > maxLetters) {
                            maxLetters = letterSets[i].size;
                            pocIdx = i;
                        }
                    }

                    this.ctx.font = '10px Roboto Mono, monospace';

                    for (let i = 0; i < rows; i++) {
                        const bPrice = minP + (i + 0.5) * binSize;
                        const y = window.candleSeries.priceToCoordinate(bPrice);
                        if (y == null) continue;

                        let sortedLetters = Array.from(letterSets[i]).sort().join('');
                        if (!sortedLetters) {
                            const count = Math.max(1, Math.min(10, Math.floor((1 - Math.abs(i - pocIdx) / (rows / 2)) * 8)));
                            sortedLetters = brackets.slice(0, count);
                        }

                        const isPoc = (i === pocIdx);
                        this.ctx.fillStyle = isPoc ? '#F23645' : '#2962FF';
                        this.ctx.fillText(sortedLetters, xStart + 4, y + 3.5);
                    }

                    // Session TPO POC Ray
                    const pocPrice = minP + (pocIdx + 0.5) * binSize;
                    lastPoc = pocPrice;
                    const pocY = window.candleSeries.priceToCoordinate(pocPrice);
                    if (pocY != null) {
                        this.ctx.strokeStyle = '#F23645';
                        this.ctx.lineWidth = 1.5;
                        this.ctx.beginPath();
                        this.ctx.moveTo(xStart, pocY);
                        this.ctx.lineTo(xStart + 60, pocY);
                        this.ctx.stroke();
                    }
                });

                if (lastPoc > 0) {
                    this.updateLegendTagVal('session_tpo', `POC ₹${lastPoc.toFixed(2)}`);
                }
            } else {
                // Visible Range TPO Market Profile (drawn on right edge)
                let minP = Infinity, maxP = -Infinity;
                candles.forEach(c => {
                    if (c.low < minP) minP = c.low;
                    if (c.high > maxP) maxP = c.high;
                });
                const pRange = maxP - minP;
                if (pRange <= 0) return;

                const rows = 35;
                const binSize = pRange / rows;
                const letterSets = Array.from({ length: rows }, () => new Set());

                candles.forEach((c, idx) => {
                    const bIdx = idx % brackets.length;
                    const letter = brackets[bIdx];
                    const sBin = Math.max(0, Math.min(rows - 1, Math.floor((c.low - minP) / binSize)));
                    const eBin = Math.max(0, Math.min(rows - 1, Math.floor((c.high - minP) / binSize)));
                    for (let b = sBin; b <= eBin; b++) {
                        letterSets[b].add(letter);
                    }
                });

                let maxLetters = 0, pocIdx = Math.floor(rows / 2);
                for (let i = 0; i < rows; i++) {
                    if (letterSets[i].size > maxLetters) {
                        maxLetters = letterSets[i].size;
                        pocIdx = i;
                    }
                }

                const rightEdge = width - 65;
                this.ctx.font = '10px Roboto Mono, monospace';

                for (let i = 0; i < rows; i++) {
                    const bPrice = minP + (i + 0.5) * binSize;
                    const y = window.candleSeries.priceToCoordinate(bPrice);
                    if (y == null) continue;

                    let sortedLetters = Array.from(letterSets[i]).sort().join('');
                    if (!sortedLetters) {
                        const count = Math.max(1, Math.min(10, Math.floor((1 - Math.abs(i - pocIdx) / (rows / 2)) * 8)));
                        sortedLetters = brackets.slice(0, count);
                    }

                    const isPoc = (i === pocIdx);
                    this.ctx.fillStyle = isPoc ? '#F23645' : '#2962FF';
                    this.ctx.fillText(sortedLetters, rightEdge - (sortedLetters.length * 7.5), y + 3.5);
                }

                // POC Line
                const pocPrice = minP + (pocIdx + 0.5) * binSize;
                const pocY = window.candleSeries.priceToCoordinate(pocPrice);
                if (pocY != null) {
                    this.ctx.strokeStyle = '#F23645';
                    this.ctx.lineWidth = 1.5;
                    this.ctx.beginPath();
                    this.ctx.moveTo(rightEdge - 140, pocY);
                    this.ctx.lineTo(rightEdge, pocY);
                    this.ctx.stroke();

                    this.drawTag(`TPO POC ₹${pocPrice.toFixed(2)}`, rightEdge - 140, pocY, '#F23645', '#FFFFFF');
                }

                this.updateLegendTagVal('tpo', `POC ₹${pocPrice.toFixed(2)}`);
            }
        }

        drawTag(text, x, y, bg, color) {
            this.ctx.font = 'bold 10px Inter, sans-serif';
            const metrics = this.ctx.measureText(text);
            const w = metrics.width + 10;
            const h = 16;
            this.ctx.fillStyle = bg;
            this.ctx.beginPath();
            this.ctx.roundRect(x - w, y - h/2, w, h, 3);
            this.ctx.fill();

            this.ctx.fillStyle = color;
            this.ctx.fillText(text, x - w + 5, y + 3.5);
        }

        drawHoverTooltip(info, mouseX, mouseY) {
            const lines = [
                `Price: ₹${info.price.toFixed(2)}`,
                `Volume: ${formatVol(info.total)}`,
                `Buy: ${formatVol(info.up)} | Sell: ${formatVol(info.down)}`,
                info.isPoc ? '★ Point of Control (POC)' : (info.isVA ? 'Value Area (70%)' : 'Outside Value Area')
            ];

            this.ctx.font = '11px Inter, sans-serif';
            const pad = 10;
            const maxW = 180;
            const boxH = lines.length * 16 + pad * 2;
            const boxX = Math.max(10, mouseX - maxW - 15);
            const boxY = Math.max(10, mouseY - boxH / 2);

            this.ctx.fillStyle = 'rgba(19, 23, 34, 0.92)';
            this.ctx.strokeStyle = '#2A2E39';
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            this.ctx.roundRect(boxX, boxY, maxW, boxH, 6);
            this.ctx.fill();
            this.ctx.stroke();

            lines.forEach((l, idx) => {
                this.ctx.fillStyle = idx === 0 ? '#F0F3FA' : (idx === 3 ? '#F5AC00' : '#B2B5BE');
                this.ctx.fillText(l, boxX + pad, boxY + pad + (idx + 1) * 14);
            });
        }
    }

    function hexToRgba(hex, alpha) {
        let c = hex.replace('#', '');
        if (c.length === 3) c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
        const r = parseInt(c.substring(0, 2), 16) || 41;
        const g = parseInt(c.substring(2, 4), 16) || 98;
        const b = parseInt(c.substring(4, 6), 16) || 255;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function formatVol(n) {
        if (n >= 1e7) return (n / 1e7).toFixed(2) + ' Cr';
        if (n >= 1e5) return (n / 1e5).toFixed(2) + ' L';
        if (n >= 1e3) return (n / 1e3).toFixed(1) + ' k';
        return Math.round(n).toString();
    }

    window.volumeProfileOverlay = new VolumeProfileOverlay();
})();
