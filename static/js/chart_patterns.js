/**
 * Chart Pattern Recognition & Educational Tooltip Engine
 * Scans active candles, attaches Lightweight Charts badge markers,
 * and renders interactive educational tooltips on hover.
 */

(function () {
    class ChartPatternManager {
        constructor() {
            this.activePatterns = new Set();
            this.markersMap = new Map(); // patternId -> array of markers
            this.tooltipEl = null;
            this.isScanning = false;

            document.addEventListener('DOMContentLoaded', () => this.init());
        }

        init() {
            this.createTooltipElement();
            this.setupHoverHandler();
        }

        createTooltipElement() {
            if (document.getElementById('chart-pattern-tooltip')) return;

            const tip = document.createElement('div');
            tip.id = 'chart-pattern-tooltip';
            tip.className = 'chart-pattern-tooltip';
            tip.style.cssText = `
                position: absolute;
                display: none;
                z-index: 1000;
                pointer-events: none;
                max-width: 280px;
                background: #1e222d;
                border: 1px solid #2a2e39;
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
                padding: 12px 14px;
                font-size: 12px;
                color: #d1d4dc;
                font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif;
                transition: opacity 0.15s ease, transform 0.15s ease;
            `;
            document.body.appendChild(tip);
            this.tooltipEl = tip;
        }

        setupHoverHandler() {
            const chartContainer = document.getElementById('chart-container');
            if (!chartContainer) return;

            chartContainer.addEventListener('mousemove', (e) => {
                if (!window.mainChart || !window.candleSeries || this.markersMap.size === 0) {
                    this.hideTooltip();
                    return;
                }

                // Check crosshair or hovered candle time
                const rect = chartContainer.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                // Match with any active marker at this coordinate
                const hoveredMarker = this.findMarkerNear(x, y);
                if (hoveredMarker && hoveredMarker.customData) {
                    this.showTooltip(hoveredMarker.customData, e.clientX, e.clientY);
                } else {
                    this.hideTooltip();
                }
            });

            chartContainer.addEventListener('mouseleave', () => this.hideTooltip());
        }

        findMarkerNear(x, y) {
            if (!window.mainChart || !window.candleSeries) return null;
            const timeScale = window.mainChart.timeScale();

            for (const markers of this.markersMap.values()) {
                for (const m of markers) {
                    const coordX = timeScale.timeToCoordinate(m.time);
                    if (coordX == null) continue;
                    const coordY = window.candleSeries.priceToCoordinate(m.customData ? m.customData.price : 0);
                    if (coordY == null) continue;

                    // Proximity radius 20px
                    const dx = Math.abs(x - coordX);
                    const dy = Math.abs(y - coordY);
                    if (dx <= 18 && dy <= 30) {
                        return m;
                    }
                }
            }
            return null;
        }

        showTooltip(data, clientX, clientY) {
            if (!this.tooltipEl) return;

            const sentimentColor = data.sentiment === 'bullish' ? '#089981' : (data.sentiment === 'bearish' ? '#F23645' : '#2962FF');
            const sentimentBadge = data.sentiment ? `<span style="display:inline-block; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700; text-transform:uppercase; background:${sentimentColor}22; color:${sentimentColor}; border:1px solid ${sentimentColor}55;">${data.sentiment}</span>` : '';

            this.tooltipEl.innerHTML = `
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                    <strong style="color:#ffffff; font-size:13px;">${escapeHtml(data.pattern_name)}</strong>
                    ${sentimentBadge}
                </div>
                <div style="margin-bottom:8px; line-height:1.45; color:#b2b5be;">
                    ${escapeHtml(data.description)}
                </div>
                <div style="background:#131722; padding:8px; border-radius:6px; margin-bottom:6px; border-left:3px solid ${sentimentColor};">
                    <div style="font-size:11px; font-weight:600; color:#d1d4dc; margin-bottom:2px;">Confirmation Rule:</div>
                    <div style="font-size:11px; color:#787b86;">${escapeHtml(data.confirmation_rule)}</div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:#787b86; padding-top:4px;">
                    <span>Historical Accuracy:</span>
                    <strong style="color:#089981;">${data.historical_accuracy_pct}%</strong>
                </div>
            `;

            // Position tooltip above cursor
            const tipWidth = 280;
            const tipHeight = 160;
            let posX = clientX + 15;
            let posY = clientY - tipHeight - 10;

            if (posX + tipWidth > window.innerWidth) posX = clientX - tipWidth - 15;
            if (posY < 10) posY = clientY + 20;

            this.tooltipEl.style.left = `${posX}px`;
            this.tooltipEl.style.top = `${posY}px`;
            this.tooltipEl.style.display = 'block';
        }

        hideTooltip() {
            if (this.tooltipEl) {
                this.tooltipEl.style.display = 'none';
            }
        }

        async applyPattern(patternId) {
            console.log(`[PatternRecognition] Toggling pattern: ${patternId}`);
            if (this.activePatterns.has(patternId)) {
                this.removePattern(patternId);
                return;
            }

            this.activePatterns.add(patternId);
            await this.rescan();
            this.updateLegendTags();
            this.showToast(`Pattern "${patternId.replace(/_/g, ' ').toUpperCase()}" applied to chart.`);
        }

        removePattern(patternId) {
            this.activePatterns.delete(patternId);
            this.markersMap.delete(patternId);
            this.updateChartMarkers();
            this.updateLegendTags();
            this.showToast(`Pattern "${patternId.replace(/_/g, ' ').toUpperCase()}" removed.`);
        }

        updateLegendTags() {
            const overlayContainer = document.getElementById('chart-legend-overlay');
            if (!overlayContainer) return;

            let legendTags = document.getElementById('chart-legend-study-tags');
            if (!legendTags) {
                legendTags = document.createElement('div');
                legendTags.id = 'chart-legend-study-tags';
                legendTags.className = 'chart-legend-study-tags';
                overlayContainer.appendChild(legendTags);
            }

            // Remove existing pattern tags
            document.querySelectorAll('.pattern-legend-tag').forEach(t => t.remove());

            this.activePatterns.forEach(pid => {
                const markers = this.markersMap.get(pid) || [];
                const name = pid.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const tag = document.createElement('div');
                tag.className = 'study-legend-tag pattern-legend-tag';
                tag.id = `legend-tag-patt-${pid}`;
                tag.innerHTML = `
                    <span class="study-tag-title">🎯 ${name} <span class="study-tag-val font-mono">(${markers.length})</span></span>
                    <span class="study-tag-controls">
                        <button class="study-tag-btn btn-close" title="Remove Pattern">✕</button>
                    </span>
                `;
                tag.querySelector('.btn-close').onclick = (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    this.removePattern(pid);
                };
                legendTags.appendChild(tag);
            });
        }

        async rescan() {
            if (this.activePatterns.size === 0) {
                this.markersMap.clear();
                this.updateChartMarkers();
                this.updateLegendTags();
                return;
            }

            const candles = window.allLoadedCandles;
            if (!candles || candles.length < 3) return;

            try {
                const response = await fetch('/api/v1/studies/patterns', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        candles: candles.slice(-500), // last 500 candles for snappy response
                        patterns: Array.from(this.activePatterns)
                    })
                });

                const json = await response.json();
                if (json.success && json.data && json.data.markers) {
                    // Group markers by pattern_id
                    this.markersMap.clear();
                    json.data.markers.forEach(m => {
                        const pid = m.customData ? m.customData.pattern_id : 'unknown';
                        if (!this.markersMap.has(pid)) this.markersMap.set(pid, []);
                        this.markersMap.get(pid).push(m);
                    });
                    this.updateChartMarkers();
                    this.updateLegendTags();
                }
            } catch (err) {
                console.error('[PatternRecognition] Scan error:', err);
            }
        }

        updateChartMarkers() {
            if (!window.candleSeries) {
                setTimeout(() => {
                    if (window.candleSeries) this.updateChartMarkers();
                }, 200);
                return;
            }

            // Flatten all markers and sort by time
            const allMarkers = [];
            for (const markers of this.markersMap.values()) {
                allMarkers.push(...markers);
            }

            // Also preserve strategy execution markers if strategy tester is active
            if (window.strategyTesterDock && window.strategyTesterDock.currentMarkers) {
                allMarkers.push(...window.strategyTesterDock.currentMarkers);
            }

            allMarkers.sort((a, b) => a.time - b.time);
            window.candleSeries.setMarkers(allMarkers);
            console.log(`[PatternRecognition] Set ${allMarkers.length} markers on chart series.`);
        }

        showToast(msg) {
            const toast = document.createElement('div');
            toast.className = 'toast-alert info';
            toast.textContent = msg;
            toast.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: #2962FF;
                color: #ffffff;
                padding: 10px 18px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
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

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    window.chartPatternManager = new ChartPatternManager();
    window.applyChartPattern = function (patternId) {
        window.chartPatternManager.applyPattern(patternId);
    };
})();
