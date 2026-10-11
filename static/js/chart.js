let mainChart, volumeChart, oscillatorChart;
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
    
    candleSeries = createCandlestickSeries(mainChart, {
        upColor: '#089981', 
        downColor: '#F23645', 
        borderVisible: false, 
        wickUpColor: '#089981', 
        wickDownColor: '#F23645'
    });
    
    vwapSeries = createLineSeries(mainChart, {
        color: '#F5AC00',
        lineWidth: 2,
        title: 'VWAP',
    });

    emaSeries = createLineSeries(mainChart, {
        color: '#2962FF',
        lineWidth: 2,
        title: 'EMA 20',
    });

    // Volume pane
    volumeChart = LightweightCharts.createChart(volContainer, chartOptions);
    volumeSeries = createHistogramSeries(volumeChart, {
        color: '#2962FF',
        priceFormat: { type: 'volume' },
        priceScaleId: '', // overlay
    });

    // Crosshair Sync Logic & Live Legend OHLC Update
    mainChart.subscribeCrosshairMove(param => {
        if (volumeChart && typeof volumeChart.setCrosshairPosition === 'function') {
            if (!param || !param.point || param.point.x < 0 || param.point.x > container.clientWidth || param.point.y < 0 || param.point.y > container.clientHeight) {
                if (typeof volumeChart.clearCrosshairPosition === 'function') volumeChart.clearCrosshairPosition();
            } else {
                volumeChart.setCrosshairPosition(param.point.x, param.point.y, mainChart);
            }
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

    // Backward lazy-loading on scroll to left edge
    if (mainChart && mainChart.timeScale()) {
        mainChart.timeScale().subscribeVisibleLogicalRangeChange(newRange => {
            if (!newRange) return;
            if (newRange.from < 20 && window.nextCandleCursor && !window.isLoadingMoreCandles) {
                loadOlderCandles();
            }
        });
    }
}

function handleResize() {
    if (mainChart) {
        const container = document.getElementById('chart-container');
        if (container) {
            mainChart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
        }
    }
    if (volumeChart && document.body.classList.contains('pro-mode-enabled')) {
        const volContainer = document.getElementById('volume-pane');
        if (volContainer) {
            volumeChart.applyOptions({ width: volContainer.clientWidth, height: volContainer.clientHeight });
        }
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

async function fetchChartData(symbol, timeframe) {
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

    try {
        // Fetch up to 3000 candles initially for a rich view
        const response = await fetch(`/api/v1/candles?symbol=${encodeURIComponent(sym)}&timeframe=${encodeURIComponent(tf)}&limit=3000`);
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data && Array.isArray(data.data.candles) && data.data.candles.length > 0) {
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
                    updateActiveSymbolDisplay();
                    handleResize();
                    return;
                }
            }
        }
    } catch (e) {
        console.warn("Candle API error, using demonstration sample data:", e);
    }

    // Fall back to sample demonstration candles if database has 0 historical candles for symbol
    mockData(sym);
    handleResize();
}

function mockData(symbol) {
    const data = [];
    const volData = [];
    let time = Math.floor(Date.now() / 1000) - (300 * 86400);

    // Compute consistent base price based on symbol string hash
    let price = 2500;
    if (symbol) {
        let hash = 0;
        for (let i = 0; i < symbol.length; i++) hash = ((hash << 5) - hash) + symbol.charCodeAt(i);
        price = Math.abs(hash % 3000) + 150;
    }

    for (let i = 0; i < 300; i++) {
        time += 86400;
        const change = (Math.random() - 0.48) * (price * 0.02);
        const open = price;
        const close = open + change;
        const high = Math.max(open, close) + Math.random() * (price * 0.008);
        const low = Math.min(open, close) - Math.random() * (price * 0.008);
        const volume = Math.floor(Math.random() * 500000) + 20000;
        price = close;
        data.push({ 
            time, 
            open: Math.round(open * 100) / 100, 
            high: Math.round(high * 100) / 100, 
            low: Math.round(low * 100) / 100, 
            close: Math.round(close * 100) / 100,
            volume: volume
        });
        volData.push({ 
            time, 
            value: volume, 
            color: close >= open ? '#089981' : '#F23645' 
        });
    }

    if (candleSeries) candleSeries.setData(data);
    if (volumeSeries) volumeSeries.setData(volData);
    window.allLoadedCandles = data;
    window.allLoadedVolumes = volData;
    if (mainChart) mainChart.timeScale().fitContent();
    if (volumeChart) volumeChart.timeScale().fitContent();
    updateOverlays();
    updateActiveSymbolDisplay();
}

window.fetchChartData = fetchChartData;
window.updateOverlays = updateOverlays;
window.updateActiveSymbolDisplay = updateActiveSymbolDisplay;
window.resetLegendToLatest = resetLegendToLatest;
