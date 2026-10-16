/**
 * Options Overlays Engine on Candlestick Chart
 * Renders Max Pain benchmark price line, Put-Call Ratio (PCR) oscillator/HUD,
 * and Strike Open Interest distribution on the active chart.
 */

(function () {
    class ChartOptionsOverlay {
        constructor() {
            this.activeStudies = new Map(); // studyId -> { priceLines, tags, etc }
            this.maxPainLine = null;

            document.addEventListener('DOMContentLoaded', () => this.init());
        }

        init() {
            // Ready for chart overlay hooks
        }

        async applyOptionsStudy(studyId) {
            console.log(`[OptionsOverlay] Applying options study: ${studyId}`);

            const symbol = window.activeSymbol || 'NSE:NIFTY50-INDEX';

            // Check if symbol is likely F&O eligible (indices or liquid equities)
            const isFO = symbol.includes('NIFTY') ||
                         symbol.includes('BANK') ||
                         symbol.includes('FINNIFTY') ||
                         symbol.includes('RELIANCE') ||
                         symbol.includes('TCS') ||
                         symbol.includes('INFY') ||
                         symbol.includes('HDFC') ||
                         symbol.includes('ICICI') ||
                         symbol.includes('SBIN') ||
                         symbol.includes('TATAMOTORS');

            if (!isFO) {
                this.showToast('⚠️ Options metrics available for F&O underlying symbols only.', 'warning');
                return;
            }

            if (this.activeStudies.has(studyId)) {
                this.removeOptionsStudy(studyId);
                return;
            }

            if (studyId === 'opt_max_pain') {
                await this.renderMaxPain(symbol);
            } else if (studyId === 'opt_pcr') {
                await this.renderPCR(symbol);
            } else if (studyId === 'opt_strike_oi_profile') {
                await this.renderStrikeOI(symbol);
            } else {
                await this.renderMaxPain(symbol);
            }
        }

        async renderMaxPain(symbol) {
            try {
                const response = await fetch(`/api/v1/options/max-pain?symbol=${encodeURIComponent(symbol)}`);
                const json = await response.json();

                if (json.success && json.data && json.data.max_pain_strike) {
                    const strike = json.data.max_pain_strike;

                    // Remove prior line if exists
                    if (this.maxPainLine && window.candleSeries) {
                        try { window.candleSeries.removePriceLine(this.maxPainLine); } catch (e) {}
                    }

                    if (window.candleSeries && typeof window.candleSeries.createPriceLine === 'function') {
                        this.maxPainLine = window.candleSeries.createPriceLine({
                            price: strike,
                            color: '#00E5FF',
                            lineWidth: 2,
                            lineStyle: 2, // Dashed
                            axisLabelVisible: true,
                            title: `Max Pain ₹${strike}`
                        });
                    }

                    this.createOptionsLegendTag('opt_max_pain', `Max Pain: ₹${strike}`, '#00E5FF');
                    this.activeStudies.set('opt_max_pain', { line: this.maxPainLine, strike });
                    this.showToast(`🎯 Max Pain benchmark line plotted at ₹${strike}`);
                } else {
                    this.showToast('Unable to fetch options Max Pain for this symbol.', 'warning');
                }
            } catch (err) {
                console.error('[OptionsOverlay] Error rendering Max Pain:', err);
                this.showToast('Failed to load options Max Pain data.', 'error');
            }
        }

        async renderPCR(symbol) {
            try {
                const response = await fetch(`/api/v1/options/max-pain?symbol=${encodeURIComponent(symbol)}`);
                const json = await response.json();

                if (json.success && json.data) {
                    const callTotal = (json.data.call_oi || []).reduce((a, b) => a + b, 0);
                    const putTotal = (json.data.put_oi || []).reduce((a, b) => a + b, 0);
                    const pcr = callTotal > 0 ? (putTotal / callTotal) : 1.0;
                    const pcrVal = pcr.toFixed(2);

                    const sentiment = pcr > 1.2 ? 'Bullish (High Put Writing)' : (pcr < 0.75 ? 'Bearish (Call Dominance)' : 'Neutral Range');
                    const color = pcr > 1.0 ? '#089981' : '#F23645';

                    this.createOptionsLegendTag('opt_pcr', `PCR: ${pcrVal} (${sentiment})`, color);
                    this.activeStudies.set('opt_pcr', { pcr: pcrVal });
                    this.showToast(`📊 Put-Call Ratio (PCR): ${pcrVal} - ${sentiment}`);
                }
            } catch (err) {
                console.error('[OptionsOverlay] Error rendering PCR:', err);
            }
        }

        async renderStrikeOI(symbol) {
            try {
                const response = await fetch(`/api/v1/options/chain?symbol=${encodeURIComponent(symbol)}`);
                const json = await response.json();

                if (json.success && json.data && json.data.matrix) {
                    const matrix = json.data.matrix;
                    // Highlight highest Call and Put OI strikes
                    let maxCallOI = 0, maxCallStrike = 0;
                    let maxPutOI = 0, maxPutStrike = 0;

                    matrix.forEach(row => {
                        const cOI = row.call ? (row.call.oi || 0) : 0;
                        const pOI = row.put ? (row.put.oi || 0) : 0;
                        if (cOI > maxCallOI) { maxCallOI = cOI; maxCallStrike = row.strike_price; }
                        if (pOI > maxPutOI) { maxPutOI = pOI; maxPutStrike = row.strike_price; }
                    });

                    // Add resistance & support lines
                    if (window.candleSeries) {
                        const callResLine = window.candleSeries.createPriceLine({
                            price: maxCallStrike,
                            color: '#F23645',
                            lineWidth: 2,
                            lineStyle: 1, // Dotted
                            axisLabelVisible: true,
                            title: `Call OI Wall ₹${maxCallStrike}`
                        });

                        const putSupLine = window.candleSeries.createPriceLine({
                            price: maxPutStrike,
                            color: '#089981',
                            lineWidth: 2,
                            lineStyle: 1, // Dotted
                            axisLabelVisible: true,
                            title: `Put OI Floor ₹${maxPutStrike}`
                        });

                        this.activeStudies.set('opt_strike_oi_profile', { lines: [callResLine, putSupLine] });
                        this.createOptionsLegendTag('opt_strike_oi_profile', `OI Range: ₹${maxPutStrike} - ₹${maxCallStrike}`, '#FF9800');
                        this.showToast(`🧱 OI Key Levels: Resistance ₹${maxCallStrike} | Support ₹${maxPutStrike}`);
                    }
                }
            } catch (err) {
                console.error('[OptionsOverlay] Error rendering Strike OI:', err);
            }
        }

        createOptionsLegendTag(studyId, labelText, color) {
            const overlayContainer = document.getElementById('chart-legend-overlay');
            if (!overlayContainer) return;

            let legendTags = document.getElementById('chart-legend-study-tags');
            if (!legendTags) {
                legendTags = document.createElement('div');
                legendTags.id = 'chart-legend-study-tags';
                legendTags.className = 'chart-legend-study-tags';
                overlayContainer.appendChild(legendTags);
            }

            // Remove existing tag if already present
            const existing = document.getElementById(`opt-tag-${studyId}`);
            if (existing) existing.remove();

            const tag = document.createElement('div');
            tag.className = 'study-legend-tag';
            tag.id = `opt-tag-${studyId}`;
            tag.style.borderColor = `${color}66`;
            tag.innerHTML = `
                <span class="study-tag-title" style="color:${color}; font-weight:600;">${labelText}</span>
                <span class="study-tag-controls">
                    <button class="study-tag-btn btn-close" title="Remove">✕</button>
                </span>
            `;

            tag.querySelector('.btn-close').onclick = () => this.removeOptionsStudy(studyId);
            legendTags.appendChild(tag);
        }

        removeOptionsStudy(studyId) {
            const item = this.activeStudies.get(studyId);
            if (item) {
                if (item.line && window.candleSeries) {
                    try { window.candleSeries.removePriceLine(item.line); } catch (e) {}
                }
                if (item.lines && Array.isArray(item.lines) && window.candleSeries) {
                    item.lines.forEach(l => {
                        try { window.candleSeries.removePriceLine(l); } catch (e) {}
                    });
                }
                this.activeStudies.delete(studyId);
            }

            const tag = document.getElementById(`opt-tag-${studyId}`);
            if (tag) tag.remove();

            this.showToast(`Options study removed.`);
        }

        showToast(msg, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast-alert ${type}`;
            toast.textContent = msg;
            toast.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: ${type === 'warning' ? '#FF9800' : (type === 'error' ? '#F23645' : '#00E5FF')};
                color: #000000;
                font-weight: 600;
                padding: 10px 18px;
                border-radius: 6px;
                font-size: 13px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.4);
                z-index: 10001;
                transition: opacity 0.3s ease;
            `;
            document.body.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    }

    window.chartOptionsOverlay = new ChartOptionsOverlay();
    window.applyChartOptionsStudy = function (studyId) {
        window.chartOptionsOverlay.applyOptionsStudy(studyId);
    };
})();
