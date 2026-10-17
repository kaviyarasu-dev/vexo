let mainChart, volumeChart;
let candleSeries, volumeSeries, vwapSeries, emaSeries;

window.currentActiveSymbol = 'NSE:RELIANCE-EQ';
window.currentSymbolTimeframe = '1D';

// Dual-compatibility helpers for Lightweight Charts (v4 and v5)
function createCandlestickSeries(chart, options) {
    if (typeof chart.addCandlestickSeries === 'function') {
        return chart.addCandlestickSeries(options);
    }
    if (typeof chart.addSeries === 'function' && typeof LightweightCharts.CandlestickSeries !== 'undefined') {
        return chart.addSeries(LightweightCharts.CandlestickSeries, options);
    }
    console.error("Candlestick series factory not found on chart", chart);
    return null;
}

function createLineSeries(chart, options) {
    if (typeof chart.addLineSeries === 'function') {
        return chart.addLineSeries(options);
    }
    if (typeof chart.addSeries === 'function' && typeof LightweightCharts.LineSeries !== 'undefined') {
        return chart.addSeries(LightweightCharts.LineSeries, options);
    }
    console.error("Line series factory not found on chart", chart);
    return null;
}

function createHistogramSeries(chart, options) {
    if (typeof chart.addHistogramSeries === 'function') {
        return chart.addHistogramSeries(options);
    }
    if (typeof chart.addSeries === 'function' && typeof LightweightCharts.HistogramSeries !== 'undefined') {
        return chart.addSeries(LightweightCharts.HistogramSeries, options);
    }
    console.error("Histogram series factory not found on chart", chart);
    return null;
}

document.addEventListener('DOMContentLoaded', () => {
    initBottomChartDock();
    initCharts();
    window.addEventListener('resize', handleResize);
    window.addEventListener('mode-changed', handleResize);

    // Timeframe selector buttons
    document.querySelectorAll('.tf-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            const tf = e.currentTarget.dataset.tf;
            window.currentSymbolTimeframe = tf;
            fetchChartData(window.currentActiveSymbol, tf);
        });
    });

    // Overlay selector buttons (VWAP & EMA)
    document.querySelectorAll('.overlay-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.toggle('active');
            updateOverlays();
        });
    });

    // Initial data fetch
    fetchChartData(window.currentActiveSymbol, window.currentSymbolTimeframe);
});

function initCharts() {
    const container = document.getElementById('chart-container');
    const volContainer = document.getElementById('volume-pane');
    if (!container || !volContainer) return;

    const chartOptions = {
        layout: {
            background: { type: 'solid', color: '#0B0E14' },
            textColor: '#D1D4DC',
        },
        grid: {
            vertLines: { color: '#2A2E39' },
            horzLines: { color: '#2A2E39' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode ? LightweightCharts.CrosshairMode.Normal : 1,
        },
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
        }
    };

    // Main Candle pane
    mainChart = LightweightCharts.createChart(container, chartOptions);
    window.mainChart = mainChart;
    
    candleSeries = createCandlestickSeries(mainChart, {
        upColor: '#089981', 
        downColor: '#F23645', 
        borderVisible: false, 
        wickUpColor: '#089981', 
        wickDownColor: '#F23645'
    });
    window.candleSeries = candleSeries;
    
    vwapSeries = createLineSeries(mainChart, {
        color: '#F5AC00',
        lineWidth: 2,
        title: 'VWAP',
    });
    window.vwapSeries = vwapSeries;

    emaSeries = createLineSeries(mainChart, {
        color: '#2962FF',
        lineWidth: 2,
        title: 'EMA 20',
    });
    window.emaSeries = emaSeries;

    // Volume pane
    const volOptions = Object.assign({}, chartOptions, {
        width: volContainer.clientWidth > 0 ? volContainer.clientWidth : (container.clientWidth || 800),
        height: volContainer.clientHeight > 0 ? volContainer.clientHeight : 100,
    });
    volumeChart = LightweightCharts.createChart(volContainer, volOptions);
    window.volumeChart = volumeChart;
    volumeSeries = createHistogramSeries(volumeChart, {
        color: '#2962FF',
        priceFormat: { type: 'volume' },
        priceScaleId: '', // overlay
    });
    window.volumeSeries = volumeSeries;

    // Crosshair Sync Logic & Live Legend OHLC Update
    mainChart.subscribeCrosshairMove(param => {
        if (volumeChart && typeof volumeChart.setCrosshairPosition === 'function') {
            if (!param || !param.point || param.point.x < 0 || param.point.x > container.clientWidth || param.point.y < 0 || param.point.y > container.clientHeight) {
                if (typeof volumeChart.clearCrosshairPosition === 'function') volumeChart.clearCrosshairPosition();
            } else {
                volumeChart.setCrosshairPosition(param.point.x, param.point.y, mainChart);
            }
        }

        // Forward crosshair to active studies subpanes
        if (window.activeStudiesManager && typeof window.activeStudiesManager.syncCrosshairToSubpanes === 'function') {
            window.activeStudiesManager.syncCrosshairToSubpanes(param);
        }

        // Live Legend OHLC update
        if (param && param.time && param.seriesData && candleSeries) {
            const bar = param.seriesData.get(candleSeries);
            if (bar && typeof bar.open === 'number') {
                updateLegendValues(bar.open, bar.high, bar.low, bar.close, null, false);
                return;
            }
        }
        resetLegendToLatest();
    });

    volumeChart.subscribeCrosshairMove(param => {
        if (!mainChart || typeof mainChart.setCrosshairPosition !== 'function') return;
        if (!param || !param.point || param.point.x < 0 || param.point.x > volContainer.clientWidth || param.point.y < 0 || param.point.y > volContainer.clientHeight) {
            if (typeof mainChart.clearCrosshairPosition === 'function') mainChart.clearCrosshairPosition();
        } else {
            mainChart.setCrosshairPosition(param.point.x, param.point.y, volumeChart);
        }
    });

    // Backward lazy-loading on scroll to left edge & volume profile redraw on pan/zoom
    if (mainChart && mainChart.timeScale()) {
        mainChart.timeScale().subscribeVisibleLogicalRangeChange(newRange => {
            if (!newRange) return;
            if (window.volumeProfileOverlay && typeof window.volumeProfileOverlay.requestRedraw === 'function') {
                window.volumeProfileOverlay.requestRedraw();
            }
            if (window.chartDrawingManager && typeof window.chartDrawingManager.requestRender === 'function') {
                window.chartDrawingManager.requestRender();
            }
            if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.requestRedraw === 'function') {
                window.chartPredictorOverlay.requestRedraw();
            }
            if (newRange.from < 20 && window.nextCandleCursor && !window.isLoadingMoreCandles) {
                loadOlderCandles();
            }
        });
    }
}

function initBottomChartDock() {
    const dock = document.getElementById('bottom-chart-dock');
    const toggleBtn = document.getElementById('btn-bottom-chart-toggle');
    const header = document.getElementById('bottom-chart-header');
    if (!dock) return;

    let savedState = null;
    try {
        savedState = localStorage.getItem('trading_app_bottom_chart_state');
    } catch (e) {}

    // Default to closed (collapsed = true) unless explicitly saved as 'open'
    const isCollapsed = (savedState !== 'open');
    dock.classList.toggle('collapsed', isCollapsed);

    function toggleBottomChart() {
        const currentlyCollapsed = dock.classList.contains('collapsed');
        const nextCollapsed = !currentlyCollapsed;
        dock.classList.toggle('collapsed', nextCollapsed);
        try {
            localStorage.setItem('trading_app_bottom_chart_state', nextCollapsed ? 'closed' : 'open');
        } catch (e) {}
        handleResize();
        requestAnimationFrame(handleResize);
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleBottomChart();
        });
    }

    if (header) {
        header.addEventListener('click', () => {
            toggleBottomChart();
        });
    }
}
window.initBottomChartDock = initBottomChartDock;

function handleResize() {
    if (mainChart) {
        const container = document.getElementById('chart-container');
        if (container && container.clientWidth > 0 && container.clientHeight > 0) {
            mainChart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
        }
    }
    const dock = document.getElementById('bottom-chart-dock');
    const isBottomOpen = dock && !dock.classList.contains('collapsed');
    if (volumeChart) {
        const volContainer = document.getElementById('volume-pane');
        if (volContainer && isBottomOpen && volContainer.clientWidth > 0 && volContainer.clientHeight > 0) {
            volumeChart.applyOptions({ width: volContainer.clientWidth, height: volContainer.clientHeight });
        }
    }
    if (window.activeStudiesManager && typeof window.activeStudiesManager.handleResize === 'function') {
        window.activeStudiesManager.handleResize();
    }
    if (window.chartDrawingManager && typeof window.chartDrawingManager.handleResize === 'function') {
        window.chartDrawingManager.handleResize();
    }
    if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.handleResize === 'function') {
        window.chartPredictorOverlay.handleResize();
        window.chartPredictorOverlay.requestRedraw();
    }
}

function applyChartTheme(theme) {
    const isDark = (theme !== 'light');
    const options = {
        layout: {
            background: { type: 'solid', color: isDark ? '#0B0E14' : '#FFFFFF' },
            textColor: isDark ? '#D1D4DC' : '#1E293B',
        },
        grid: {
            vertLines: { color: isDark ? '#2A2E39' : '#E2E8F0' },
            horzLines: { color: isDark ? '#2A2E39' : '#E2E8F0' },
        }
    };
    if (mainChart) mainChart.applyOptions(options);
    if (volumeChart) volumeChart.applyOptions(options);
}
window.applyChartTheme = applyChartTheme;

window.addEventListener('themeChanged', (e) => {
    if (e.detail && e.detail.theme) {
        applyChartTheme(e.detail.theme);
    }
});

function calculateVWAP(candles, timeframe) {
    if (!candles || candles.length === 0) return [];
    const vwapPoints = [];
    const isDailyOrWeekly = (timeframe === '1D' || timeframe === '1W');

    if (isDailyOrWeekly) {
        // 20-period rolling VWAP for daily/weekly charts
        const windowSize = 20;
        for (let i = 0; i < candles.length; i++) {
            let cumPV = 0;
            let cumVol = 0;
            const startIdx = Math.max(0, i - windowSize + 1);
            for (let j = startIdx; j <= i; j++) {
                const c = candles[j];
                const typ = (c.high + c.low + c.close) / 3;
                const vol = (typeof c.volume === 'number' && c.volume > 0) ? c.volume : 1;
                cumPV += typ * vol;
                cumVol += vol;
            }
            const val = cumVol > 0 ? (cumPV / cumVol) : candles[i].close;
            vwapPoints.push({
                time: candles[i].time,
                value: Math.round(val * 100) / 100
            });
        }
        return vwapPoints;
    }

    // Intraday Session VWAP (resets daily at 09:15 IST)
    let cumPV = 0;
    let cumVol = 0;
    let lastDate = '';

    for (const c of candles) {
        // IST is UTC+5:30 -> add 19800 seconds to unix timestamp
        const istDateStr = new Date((c.time + 19800) * 1000).toISOString().slice(0, 10);
        if (istDateStr !== lastDate) {
            lastDate = istDateStr;
            cumPV = 0;
            cumVol = 0;
        }

        const typPrice = (c.high + c.low + c.close) / 3;
        const vol = (typeof c.volume === 'number' && c.volume > 0) ? c.volume : 1;
        cumPV += typPrice * vol;
        cumVol += vol;

        const vwapVal = cumVol > 0 ? (cumPV / cumVol) : c.close;
        vwapPoints.push({
            time: c.time,
            value: Math.round(vwapVal * 100) / 100
        });
    }
    return vwapPoints;
}

function calculateEMA(candles, period = 20) {
    if (!candles || candles.length === 0) return [];
    const k = 2 / (period + 1);
    const emaPoints = [];
    let ema = candles[0].close;

    for (let i = 0; i < candles.length; i++) {
        const c = candles[i];
        if (i < period) {
            ema = (c.close + ema * i) / (i + 1);
        } else {
            ema = c.close * k + ema * (1 - k);
        }
        emaPoints.push({
            time: c.time,
            value: Math.round(ema * 100) / 100
        });
    }
    return emaPoints;
}

function updateOverlays() {
    if (!window.allLoadedCandles || window.allLoadedCandles.length === 0) return;
    const tf = window.currentSymbolTimeframe || '1D';

    const vwapBtn = document.querySelector('.overlay-btn[data-overlay="vwap"]');
    const emaBtn = document.querySelector('.overlay-btn[data-overlay="ema"]');

    const isVwapActive = vwapBtn ? vwapBtn.classList.contains('active') : false;
    const isEmaActive = emaBtn ? emaBtn.classList.contains('active') : false;

    if (vwapSeries) {
        if (isVwapActive) {
            const vwapData = calculateVWAP(window.allLoadedCandles, tf);
            vwapSeries.setData(vwapData);
            vwapSeries.applyOptions({ visible: true });
        } else {
            vwapSeries.setData([]);
            vwapSeries.applyOptions({ visible: false });
        }
    }

    if (emaSeries) {
        if (isEmaActive) {
            const emaData = calculateEMA(window.allLoadedCandles, 20);
            emaSeries.setData(emaData);
            emaSeries.applyOptions({ visible: true });
        } else {
            emaSeries.setData([]);
            emaSeries.applyOptions({ visible: false });
        }
    }
}

function formatPrice(num) {
    if (num == null || isNaN(num)) return '--';
    return Number(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function updateActiveSymbolDisplay() {
    const rawSym = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
    const tf = window.currentSymbolTimeframe || '1D';

    let exchange = 'NSE';
    let ticker = rawSym;
    let series = 'EQ';

    if (rawSym.includes(':')) {
        const parts = rawSym.split(':');
        exchange = parts[0] || 'NSE';
        ticker = parts[1] || ticker;
    }
    if (ticker.includes('-')) {
        const parts = ticker.split('-');
        ticker = parts[0] || ticker;
        series = parts[1] || 'EQ';
    }

    const proName = document.getElementById('pro-symbol-name');
    if (proName) proName.textContent = rawSym;

    const legTicker = document.getElementById('legend-ticker');
    const legSeries = document.getElementById('legend-series');
    const legExchange = document.querySelector('.legend-badge.legend-exchange');
    const legTf = document.getElementById('legend-tf');

    if (legTicker) legTicker.textContent = ticker;
    if (legSeries) legSeries.textContent = series;
    if (legExchange) legExchange.textContent = exchange;
    if (legTf) legTf.textContent = tf;

    resetLegendToLatest();
}

function resetLegendToLatest() {
    if (!window.allLoadedCandles || window.allLoadedCandles.length === 0) {
        const oEl = document.getElementById('legend-val-o');
        const hEl = document.getElementById('legend-val-h');
        const lEl = document.getElementById('legend-val-l');
        const cEl = document.getElementById('legend-val-c');
        const chgEl = document.getElementById('legend-val-chg');
        if (oEl) oEl.textContent = '--';
        if (hEl) hEl.textContent = '--';
        if (lEl) lEl.textContent = '--';
        if (cEl) cEl.textContent = '--';
        if (chgEl) chgEl.textContent = '--';
        return;
    }

    const latest = window.allLoadedCandles[window.allLoadedCandles.length - 1];
    const prev = window.allLoadedCandles.length > 1 ? window.allLoadedCandles[window.allLoadedCandles.length - 2] : null;
    const base = prev ? prev.close : latest.open;
    updateLegendValues(latest.open, latest.high, latest.low, latest.close, base, true);
}

function updateLegendValues(open, high, low, close, basePrice = null, updateToolbar = false) {
    const oEl = document.getElementById('legend-val-o');
    const hEl = document.getElementById('legend-val-h');
    const lEl = document.getElementById('legend-val-l');
    const cEl = document.getElementById('legend-val-c');
    const chgEl = document.getElementById('legend-val-chg');

    if (oEl) oEl.textContent = formatPrice(open);
    if (hEl) hEl.textContent = formatPrice(high);
    if (lEl) lEl.textContent = formatPrice(low);
    if (cEl) cEl.textContent = formatPrice(close);

    const ref = (basePrice != null && basePrice > 0) ? basePrice : open;
    const diff = close - ref;
    const diffPct = ref ? ((diff / ref) * 100) : 0;
    const isUp = diff >= 0;
    const sign = isUp ? '+' : '';
    const diffText = `${sign}${formatPrice(diff)} (${sign}${diffPct.toFixed(2)}%)`;

    if (chgEl) {
        chgEl.textContent = diffText;
        chgEl.style.color = isUp ? '#089981' : '#F23645';
    }

    if (updateToolbar) {
        const proPrice = document.getElementById('pro-symbol-price');
        const proChange = document.getElementById('pro-symbol-change');
        if (proPrice) proPrice.textContent = `₹${formatPrice(close)}`;
        if (proChange) {
            proChange.textContent = `${sign}${diffPct.toFixed(2)}%`;
            proChange.className = `active-symbol-change badge-pill font-mono ${isUp ? 'positive' : 'negative'}`;
        }
    }
    if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.updateLTP === 'function') {
        window.chartPaperTradeManager.updateLTP(close);
    }
}

window.allLoadedCandles = [];
window.allLoadedVolumes = [];
window.nextCandleCursor = null;
window.isLoadingMoreCandles = false;

async function loadOlderCandles() {
    if (!window.nextCandleCursor || window.isLoadingMoreCandles) return;
    window.isLoadingMoreCandles = true;
    const sym = window.currentActiveSymbol;
    const tf = window.currentSymbolTimeframe;

    try {
        const response = await fetch(`/api/v1/candles?symbol=${encodeURIComponent(sym)}&timeframe=${encodeURIComponent(tf)}&limit=3000&cursor=${encodeURIComponent(window.nextCandleCursor)}`);
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data && Array.isArray(data.data.candles) && data.data.candles.length > 0) {
                const newCandles = [];
                const newVolumes = [];

                for (const c of data.data.candles) {
                    const t = c.time || (c.timestamp ? Math.floor(new Date(c.timestamp).getTime() / 1000) : 0);
                    if (!t || isNaN(t)) continue;
                    newCandles.push({
                        time: t,
                        open: Number(c.open),
                        high: Number(c.high),
                        low: Number(c.low),
                        close: Number(c.close),
                        volume: Number(c.volume || 0)
                    });
                    newVolumes.push({
                        time: t,
                        value: Number(c.volume || 0),
                        color: Number(c.close) >= Number(c.open) ? '#089981' : '#F23645'
                    });
                }

                // Merge with existing, deduplicating by timestamp
                const candleMap = new Map();
                for (const c of newCandles) candleMap.set(c.time, c);
                for (const c of window.allLoadedCandles) candleMap.set(c.time, c);
                const mergedCandles = Array.from(candleMap.values()).sort((a, b) => a.time - b.time);

                const volMap = new Map();
                for (const v of newVolumes) volMap.set(v.time, v);
                for (const v of window.allLoadedVolumes) volMap.set(v.time, v);
                const mergedVolumes = Array.from(volMap.values()).sort((a, b) => a.time - b.time);

                window.allLoadedCandles = mergedCandles;
                window.allLoadedVolumes = mergedVolumes;
                window.nextCandleCursor = data.data.next_cursor || null;

                if (candleSeries) candleSeries.setData(mergedCandles);
                if (volumeSeries) volumeSeries.setData(mergedVolumes);
                updateOverlays();
                if (window.activeStudiesManager && typeof window.activeStudiesManager.recalculateAll === 'function') {
                    window.activeStudiesManager.recalculateAll(mergedCandles);
                }
                if (window.volumeProfileOverlay && typeof window.volumeProfileOverlay.requestRedraw === 'function') {
                    window.volumeProfileOverlay.requestRedraw();
                }
                if (window.chartPatternManager && typeof window.chartPatternManager.rescan === 'function') {
                    window.chartPatternManager.rescan();
                }
                if (window.chartOptionsOverlay && typeof window.chartOptionsOverlay.recalculateAll === 'function') {
                    window.chartOptionsOverlay.recalculateAll();
                }
                if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.requestRedraw === 'function') {
                    window.chartPredictorOverlay.requestRedraw();
                }
                updateActiveSymbolDisplay();
            } else {
                window.nextCandleCursor = null; // Reached end of historical data
            }
        }
    } catch (e) {
        console.warn("Could not load older candles:", e);
    } finally {
        window.isLoadingMoreCandles = false;
    }
}

window.chartLivePollTimer = null;

function updateLiveStatusBadge(authStatus, isLive) {
    const badge = document.getElementById('chart-live-status');
    const textSpan = document.getElementById('live-status-text');
    if (!badge || !textSpan) return;

    if (authStatus === 'AUTH_REQUIRED') {
        badge.className = 'chart-live-badge auth-needed';
        textSpan.textContent = 'CONNECT FYERS';
        badge.title = 'Fyers Broker Disconnected / Expired · Click to Authenticate';
        badge.onclick = () => {
            if (typeof window.openAuthModal === 'function') window.openAuthModal();
            else {
                const m = document.getElementById('auth-modal');
                if (m) m.classList.remove('hidden');
            }
        };
    } else if (isLive) {
        badge.className = 'chart-live-badge live';
        textSpan.textContent = 'LIVE 5s';
        badge.title = 'Real-time Live Market Data Stream Active (5s Polling)';
        badge.onclick = () => {
            if (typeof window.openAuthModal === 'function') window.openAuthModal();
        };
    } else {
        badge.className = 'chart-live-badge live';
        textSpan.textContent = 'CACHED';
        badge.title = 'Offline Historical DuckDB Cache · Click for Auth Status';
        badge.onclick = () => {
            if (typeof window.openAuthModal === 'function') window.openAuthModal();
        };
    }
}

function stopLiveCandlePolling() {
    if (window.chartLivePollTimer) {
        clearInterval(window.chartLivePollTimer);
        window.chartLivePollTimer = null;
    }
}

function startLiveCandlePolling(sym, tf) {
    stopLiveCandlePolling();

    window.chartLivePollTimer = setInterval(async () => {
        if (document.hidden) return;
        if (window.currentActiveSymbol !== sym || window.currentSymbolTimeframe !== tf) return;

        try {
            const resp = await fetch(`/api/v1/candles/live?symbol=${encodeURIComponent(sym)}&timeframe=${encodeURIComponent(tf)}`);
            if (!resp.ok) return;
            const resJson = await resp.json();
            if (!resJson || !resJson.success || !resJson.data) return;

            const liveData = resJson.data;
            updateLiveStatusBadge(liveData.auth_status, liveData.is_live);

            if (liveData.candle) {
                const c = liveData.candle;
                const t = c.time;
                if (t && !isNaN(t)) {
                    const updatedCandle = {
                        time: t,
                        open: Number(c.open),
                        high: Number(c.high),
                        low: Number(c.low),
                        close: Number(c.close),
                        volume: Number(c.volume || 0)
                    };
                    const updatedVolume = {
                        time: t,
                        value: Number(c.volume || 0),
                        color: Number(c.close) >= Number(c.open) ? '#089981' : '#F23645'
                    };

                    if (candleSeries) candleSeries.update(updatedCandle);
                    if (volumeSeries) volumeSeries.update(updatedVolume);

                    if (window.allLoadedCandles && window.allLoadedCandles.length > 0) {
                        const lastIdx = window.allLoadedCandles.length - 1;
                        if (window.allLoadedCandles[lastIdx].time === t) {
                            window.allLoadedCandles[lastIdx] = updatedCandle;
                            if (window.allLoadedVolumes && window.allLoadedVolumes.length > 0) {
                                window.allLoadedVolumes[window.allLoadedVolumes.length - 1] = updatedVolume;
                            }
                            if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.requestRedraw === 'function') {
                                window.chartPredictorOverlay.requestRedraw();
                            }
                        } else if (t > window.allLoadedCandles[lastIdx].time) {
                            window.allLoadedCandles.push(updatedCandle);
                            if (window.allLoadedVolumes) window.allLoadedVolumes.push(updatedVolume);
                            if (typeof window.fetchPredictionForCurrentChart === 'function') {
                                window.fetchPredictionForCurrentChart();
                            }
                        }
                    }

                    if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.updateLTP === 'function') {
                        window.chartPaperTradeManager.updateLTP(updatedCandle.close);
                    }
                    updateActiveSymbolDisplay();
                }
            } else if (liveData.quote && liveData.quote.ltp) {
                if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.updateLTP === 'function') {
                    window.chartPaperTradeManager.updateLTP(liveData.quote.ltp);
                }
            }
        } catch (err) {
            console.debug("Live candle poll error:", err);
        }
    }, 5000);
}

async function fetchChartData(symbol, timeframe) {
    stopLiveCandlePolling();
    window.currentActiveSymbol = symbol || window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
    window.currentSymbolTimeframe = timeframe || window.currentSymbolTimeframe || '1D';
    const sym = window.currentActiveSymbol;
    const tf = window.currentSymbolTimeframe;

    // Reset pagination state
    window.nextCandleCursor = null;
    window.isLoadingMoreCandles = false;
    window.allLoadedCandles = [];
    window.allLoadedVolumes = [];

    // Update active symbol in header placeholder
    const placeholder = document.querySelector('#search-trigger .placeholder');
    if (placeholder) {
        placeholder.textContent = `${sym} (${tf})`;
    }
    updateActiveSymbolDisplay();

    // Show syncing badge state
    const badge = document.getElementById('chart-live-status');
    const textSpan = document.getElementById('live-status-text');
    if (badge && textSpan) {
        badge.className = 'chart-live-badge syncing';
        textSpan.textContent = 'SYNCING...';
    }

    try {
        // Fetch up to 3000 candles initially with on-demand JIT sync from Fyers
        const response = await fetch(`/api/v1/candles?symbol=${encodeURIComponent(sym)}&timeframe=${encodeURIComponent(tf)}&limit=3000&refresh_live=true`);
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data) {
                updateLiveStatusBadge(data.data.auth_status, data.data.is_live);

                if (Array.isArray(data.data.candles) && data.data.candles.length > 0) {
                    const formattedCandles = [];
                    const formattedVolumes = [];

                    const sorted = data.data.candles.slice().sort((a, b) => {
                        const ta = a.time || (a.timestamp ? Math.floor(new Date(a.timestamp).getTime() / 1000) : 0);
                        const tb = b.time || (b.timestamp ? Math.floor(new Date(b.timestamp).getTime() / 1000) : 0);
                        return ta - tb;
                    });

                    for (const c of sorted) {
                        const t = c.time || (c.timestamp ? Math.floor(new Date(c.timestamp).getTime() / 1000) : 0);
                        if (!t || isNaN(t)) continue;
                        formattedCandles.push({
                            time: t,
                            open: Number(c.open),
                            high: Number(c.high),
                            low: Number(c.low),
                            close: Number(c.close),
                            volume: Number(c.volume || 0)
                        });
                        formattedVolumes.push({
                            time: t,
                            value: Number(c.volume || 0),
                            color: Number(c.close) >= Number(c.open) ? '#089981' : '#F23645'
                        });
                    }

                    if (formattedCandles.length > 0) {
                        window.allLoadedCandles = formattedCandles;
                        window.allLoadedVolumes = formattedVolumes;
                        window.nextCandleCursor = data.data.next_cursor || null;

                        if (candleSeries) candleSeries.setData(formattedCandles);
                        if (volumeSeries) volumeSeries.setData(formattedVolumes);
                        if (mainChart) mainChart.timeScale().fitContent();
                        if (volumeChart) volumeChart.timeScale().fitContent();
                        updateOverlays();
                        if (window.activeStudiesManager && typeof window.activeStudiesManager.recalculateAll === 'function') {
                            window.activeStudiesManager.recalculateAll(formattedCandles);
                        }
                        if (window.volumeProfileOverlay && typeof window.volumeProfileOverlay.requestRedraw === 'function') {
                            window.volumeProfileOverlay.requestRedraw();
                        }
                        if (window.chartPatternManager && typeof window.chartPatternManager.rescan === 'function') {
                            window.chartPatternManager.rescan();
                        }
                        if (window.chartOptionsOverlay && typeof window.chartOptionsOverlay.recalculateAll === 'function') {
                            window.chartOptionsOverlay.recalculateAll();
                        }
                        if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.onSymbolOrCandlesChanged === 'function') {
                            window.chartPaperTradeManager.onSymbolOrCandlesChanged();
                        }
                        if (window.chartDrawingManager && typeof window.chartDrawingManager.onSymbolOrCandlesChanged === 'function') {
                            window.chartDrawingManager.onSymbolOrCandlesChanged(sym);
                        }
                        updateActiveSymbolDisplay();
                        handleResize();
                        fetchPredictionForCurrentChart();

                        // Handle Auth Status Banners
                        const isAuthRequired = (data.data.auth_status === 'AUTH_REQUIRED');
                        const outdatedBanner = document.getElementById('chart-outdated-banner');
                        const outdatedText = document.getElementById('outdated-banner-text');
                        const emptyState = document.getElementById('chart-auth-empty-state');

                        if (isAuthRequired) {
                            if (emptyState) emptyState.classList.add('hidden');
                            if (outdatedBanner && outdatedText) {
                                const lastCandle = formattedCandles[formattedCandles.length - 1];
                                const lastDate = new Date((lastCandle.time + 19800) * 1000).toISOString().slice(0, 10);
                                outdatedText.textContent = `Market data may be outdated (Last trade in DB: ${lastDate}). Fyers broker session expired. Connect Fyers to catch up live trades.`;
                                outdatedBanner.classList.remove('hidden');
                            }
                            // Do not run live background polling when auth is invalid
                            stopLiveCandlePolling();
                            return;
                        }

                        // Authenticated: hide banners and start live ticker polling
                        if (outdatedBanner) outdatedBanner.classList.add('hidden');
                        if (emptyState) emptyState.classList.add('hidden');
                        startLiveCandlePolling(sym, tf);
                        return;
                    }
                } else {
                    // Empty candles returned
                    if (candleSeries) candleSeries.setData([]);
                    if (volumeSeries) volumeSeries.setData([]);
                    window.allLoadedCandles = [];
                    window.allLoadedVolumes = [];

                    const isAuthRequired = (data.data && data.data.auth_status === 'AUTH_REQUIRED');
                    const emptyState = document.getElementById('chart-auth-empty-state');
                    const outdatedBanner = document.getElementById('chart-outdated-banner');
                    if (outdatedBanner) outdatedBanner.classList.add('hidden');

                    if (isAuthRequired) {
                        if (emptyState) emptyState.classList.remove('hidden');
                        if (typeof window.openAuthModal === 'function') window.openAuthModal();
                    } else {
                        if (emptyState) emptyState.classList.add('hidden');
                    }

                    updateActiveSymbolDisplay();
                    handleResize();
                    return;
                }
            }
        }
    } catch (e) {
        console.warn("Candle API error:", e);
    }

    // In case of network error or empty response, clear and do not mock
    if (candleSeries) candleSeries.setData([]);
    if (volumeSeries) volumeSeries.setData([]);
    updateActiveSymbolDisplay();
    handleResize();
}

async function fetchPredictionForCurrentChart() {
    const sym = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
    const tf = window.currentSymbolTimeframe || '1D';

    const hudEl = document.getElementById('predictive-hud');
    const regimeEl = document.getElementById('hud-regime-label');
    const dirEl = document.getElementById('hud-dir-badge');
    const rangeEl = document.getElementById('hud-range-corridor');

    // Handle graceful fallback for assets with sparse data (< 200 bars)
    if (!window.allLoadedCandles || window.allLoadedCandles.length < 200) {
        if (hudEl) {
            hudEl.className = 'predictive-hud insufficient';
            hudEl.title = 'Status: Insufficient Data (< 200 bars) · Rendering Classical ATR(14) Corridor Fallback';
        }
        if (regimeEl) regimeEl.textContent = 'Status: Insufficient Data (< 200 bars)';
        if (dirEl) dirEl.textContent = 'ATR';
        if (rangeEl) rangeEl.textContent = '';

        // Compute Classical ATR(14) fallback envelope
        if (window.allLoadedCandles && window.allLoadedCandles.length >= 15) {
            const candles = window.allLoadedCandles;
            const period = 14;
            let trSum = 0;
            for (let i = candles.length - period; i < candles.length; i++) {
                const c = candles[i];
                const prev = candles[i - 1];
                const tr = Math.max(c.high - c.low, Math.abs(c.high - prev.close), Math.abs(c.low - prev.close));
                trSum += tr;
            }
            const atr = trSum / period;
            const lastClose = candles[candles.length - 1].close;
            const upper = lastClose + 1.5 * atr;
            const lower = Math.max(0, lastClose - 1.5 * atr);

            if (rangeEl) rangeEl.textContent = `₹${lower.toFixed(2)} - ₹${upper.toFixed(2)}`;

            if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.updateFallback === 'function') {
                window.chartPredictorOverlay.updateFallback({
                    upper: upper,
                    median: lastClose,
                    lower: lower,
                    atr: atr
                });
            }
        } else if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.clear === 'function') {
            window.chartPredictorOverlay.clear();
        }
        return;
    }

    try {
        const resp = await fetch(`/api/v1/predict/candle?symbol=${encodeURIComponent(sym)}&timeframe=${encodeURIComponent(tf)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const resJson = await resp.json();
        if (!resJson || !resJson.success || !resJson.data) throw new Error("Invalid prediction response");

        const pred = resJson.data;
        const dirProb = pred.directional_prob != null ? pred.directional_prob : 0.50;
        const isBullish = pred.is_bullish ?? (dirProb >= 0.50);
        const probPct = Math.round(dirProb * 100);

        if (hudEl) {
            hudEl.className = 'predictive-hud';
            if (dirProb > 0.60) {
                hudEl.classList.add('bullish');
            } else if (dirProb < 0.40) {
                hudEl.classList.add('bearish');
            } else {
                hudEl.classList.add('neutral');
            }
            hudEl.title = `AI Conformal Prediction · Direction: ${isBullish ? 'Bullish' : 'Bearish'} (${probPct}%) · 80% Coverage Corridor: ₹${pred.low_10} - ₹${pred.high_90} · Latency: ${pred.inference_latency_ms}ms`;
        }

        if (regimeEl) {
            regimeEl.textContent = `AI: ${pred.regime_label || 'ACTIVE'}`;
        }

        if (dirEl) {
            const arrow = dirProb >= 0.50 ? '▲' : '▼';
            dirEl.textContent = `${arrow} ${probPct}%`;
        }

        if (rangeEl) {
            rangeEl.textContent = `₹${pred.low_10} - ₹${pred.high_90}`;
        }

        if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.update === 'function') {
            window.chartPredictorOverlay.update(pred);
        }
    } catch (e) {
        console.warn("[Chart] Prediction fetch error:", e);
        if (hudEl) {
            hudEl.className = 'predictive-hud insufficient';
            hudEl.title = 'Status: Insufficient Data (< 200 bars) · Rendering Classical ATR(14) Corridor Fallback';
        }
        if (regimeEl) regimeEl.textContent = 'Status: Insufficient Data (< 200 bars)';
        if (dirEl) dirEl.textContent = '--%';
        if (rangeEl) rangeEl.textContent = '';
        if (window.chartPredictorOverlay && typeof window.chartPredictorOverlay.clear === 'function') {
            window.chartPredictorOverlay.clear();
        }
    }
}

// Auto-resume chart catch-up after user logs in or validates token in Auth Status popup
window.addEventListener('fyersAuthSucceeded', () => {
    console.log('[Chart] fyersAuthSucceeded received. Catching up live market data...');
    fetchChartData(window.currentActiveSymbol, window.currentSymbolTimeframe);
});

window.fetchChartData = fetchChartData;
window.fetchPredictionForCurrentChart = fetchPredictionForCurrentChart;
window.startLiveCandlePolling = startLiveCandlePolling;
window.stopLiveCandlePolling = stopLiveCandlePolling;
window.updateLiveStatusBadge = updateLiveStatusBadge;
window.updateOverlays = updateOverlays;
window.updateActiveSymbolDisplay = updateActiveSymbolDisplay;
window.resetLegendToLatest = resetLegendToLatest;
window.calculateVWAP = calculateVWAP;
window.calculateEMA = calculateEMA;

