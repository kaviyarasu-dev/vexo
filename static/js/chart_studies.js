/**
 * Active Studies & Dynamic Sub-Panes Engine for TradingView Lightweight Charts
 */

(function () {
    // --- 1. Client-Side Technical Indicator Computations ---

    function computeSMA(candles, period = 20) {
        if (!candles || candles.length === 0) return [];
        const result = [];
        let sum = 0;
        for (let i = 0; i < candles.length; i++) {
            sum += candles[i].close;
            if (i >= period) {
                sum -= candles[i - period].close;
            }
            if (i >= period - 1) {
                result.push({
                    time: candles[i].time,
                    value: Math.round((sum / period) * 100) / 100
                });
            }
        }
        return result;
    }

    function computeEMA(candles, period = 20) {
        if (!candles || candles.length === 0) return [];
        const k = 2 / (period + 1);
        const result = [];
        let ema = candles[0].close;

        for (let i = 0; i < candles.length; i++) {
            const c = candles[i];
            if (i < period) {
                ema = (c.close + ema * i) / (i + 1);
            } else {
                ema = c.close * k + ema * (1 - k);
            }
            if (i >= period - 1) {
                result.push({
                    time: c.time,
                    value: Math.round(ema * 100) / 100
                });
            }
        }
        return result;
    }

    function computeBollingerBands(candles, period = 20, stdDevMult = 2.0) {
        if (!candles || candles.length === 0) return { upper: [], middle: [], lower: [] };
        const upper = [], middle = [], lower = [];

        for (let i = period - 1; i < candles.length; i++) {
            let sum = 0;
            for (let j = i - period + 1; j <= i; j++) {
                sum += candles[j].close;
            }
            const ma = sum / period;

            let sumSqDiff = 0;
            for (let j = i - period + 1; j <= i; j++) {
                sumSqDiff += Math.pow(candles[j].close - ma, 2);
            }
            const std = Math.sqrt(sumSqDiff / period);

            const t = candles[i].time;
            middle.push({ time: t, value: Math.round(ma * 100) / 100 });
            upper.push({ time: t, value: Math.round((ma + std * stdDevMult) * 100) / 100 });
            lower.push({ time: t, value: Math.round((ma - std * stdDevMult) * 100) / 100 });
        }
        return { upper, middle, lower };
    }

    function computeSupertrend(candles, period = 10, multiplier = 3.0) {
        if (!candles || candles.length < period) return { st: [], isUp: [] };
        
        // 1. Calculate True Range and ATR
        const trs = [candles[0].high - candles[0].low];
        for (let i = 1; i < candles.length; i++) {
            const h = candles[i].high;
            const l = candles[i].low;
            const prevC = candles[i - 1].close;
            trs.push(Math.max(h - l, Math.abs(h - prevC), Math.abs(l - prevC)));
        }

        const atrs = [];
        let atr = trs.slice(0, period).reduce((a, b) => a + b, 0) / period;
        for (let i = 0; i < candles.length; i++) {
            if (i < period - 1) {
                atrs.push(0);
            } else if (i === period - 1) {
                atrs.push(atr);
            } else {
                atr = (atr * (period - 1) + trs[i]) / period;
                atrs.push(atr);
            }
        }

        const stPoints = [];
        let prevFinalUpper = 0;
        let prevFinalLower = 0;
        let prevDir = 1;

        for (let i = period - 1; i < candles.length; i++) {
            const hl2 = (candles[i].high + candles[i].low) / 2;
            const basicUpper = hl2 + (multiplier * atrs[i]);
            const basicLower = hl2 - (multiplier * atrs[i]);

            let finalUpper = basicUpper;
            let finalLower = basicLower;

            if (i > period - 1) {
                finalUpper = (basicUpper < prevFinalUpper || candles[i - 1].close > prevFinalUpper) ? basicUpper : prevFinalUpper;
                finalLower = (basicLower > prevFinalLower || candles[i - 1].close < prevFinalLower) ? basicLower : prevFinalLower;
            }

            let dir = prevDir;
            if (prevDir === 1) {
                dir = candles[i].close < finalLower ? -1 : 1;
            } else {
                dir = candles[i].close > finalUpper ? 1 : -1;
            }

            const stVal = dir === 1 ? finalLower : finalUpper;
            stPoints.push({
                time: candles[i].time,
                value: Math.round(stVal * 100) / 100,
                color: dir === 1 ? '#089981' : '#F23645'
            });

            prevFinalUpper = finalUpper;
            prevFinalLower = finalLower;
            prevDir = dir;
        }

        return stPoints;
    }

    function computeRSI(candles, period = 14) {
        if (!candles || candles.length <= period) return [];
        const result = [];
        let gains = 0;
        let losses = 0;

        for (let i = 1; i <= period; i++) {
            const diff = candles[i].close - candles[i - 1].close;
            if (diff >= 0) gains += diff;
            else losses += Math.abs(diff);
        }

        let avgGain = gains / period;
        let avgLoss = losses / period;
        let rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        let rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + rs));

        result.push({
            time: candles[period].time,
            value: Math.round(rsi * 100) / 100
        });

        for (let i = period + 1; i < candles.length; i++) {
            const diff = candles[i].close - candles[i - 1].close;
            const currentGain = diff > 0 ? diff : 0;
            const currentLoss = diff < 0 ? Math.abs(diff) : 0;

            avgGain = (avgGain * (period - 1) + currentGain) / period;
            avgLoss = (avgLoss * (period - 1) + currentLoss) / period;

            rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
            rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + rs));

            result.push({
                time: candles[i].time,
                value: Math.round(rsi * 100) / 100
            });
        }
        return result;
    }

    function computeMACD(candles, fast = 12, slow = 26, signal = 9) {
        if (!candles || candles.length < slow + signal) return { macd: [], signal: [], hist: [] };
        const kFast = 2 / (fast + 1);
        const kSlow = 2 / (slow + 1);
        const kSig = 2 / (signal + 1);

        let emaFast = candles[0].close;
        let emaSlow = candles[0].close;
        const macdLine = [];

        for (let i = 0; i < candles.length; i++) {
            emaFast = candles[i].close * kFast + emaFast * (1 - kFast);
            emaSlow = candles[i].close * kSlow + emaSlow * (1 - kSlow);
            if (i >= slow - 1) {
                macdLine.push({
                    time: candles[i].time,
                    value: emaFast - emaSlow
                });
            }
        }

        let emaSignal = macdLine[0].value;
        const macdPoints = [];
        const signalPoints = [];
        const histPoints = [];

        for (let i = 0; i < macdLine.length; i++) {
            emaSignal = macdLine[i].value * kSig + emaSignal * (1 - kSig);
            if (i >= signal - 1) {
                const m = macdLine[i].value;
                const s = emaSignal;
                const h = m - s;
                macdPoints.push({ time: macdLine[i].time, value: Math.round(m * 100) / 100 });
                signalPoints.push({ time: macdLine[i].time, value: Math.round(s * 100) / 100 });
                histPoints.push({
                    time: macdLine[i].time,
                    value: Math.round(h * 100) / 100,
                    color: h >= 0 ? '#089981' : '#F23645'
                });
            }
        }

        return { macd: macdPoints, signal: signalPoints, hist: histPoints };
    }

    function computeStochastic(candles, kPeriod = 14, dPeriod = 3, smooth = 3) {
        if (!candles || candles.length < kPeriod + dPeriod) return { k: [], d: [] };
        const fastK = [];

        for (let i = kPeriod - 1; i < candles.length; i++) {
            let lowest = Infinity;
            let highest = -Infinity;
            for (let j = i - kPeriod + 1; j <= i; j++) {
                if (candles[j].low < lowest) lowest = candles[j].low;
                if (candles[j].high > highest) highest = candles[j].high;
            }
            const range = highest - lowest;
            const kVal = range === 0 ? 50 : ((candles[i].close - lowest) / range) * 100;
            fastK.push({ time: candles[i].time, value: kVal });
        }

        // Smooth %K
        const smoothedK = [];
        for (let i = smooth - 1; i < fastK.length; i++) {
            let sum = 0;
            for (let j = i - smooth + 1; j <= i; j++) sum += fastK[j].value;
            smoothedK.push({ time: fastK[i].time, value: sum / smooth });
        }

        // %D is SMA of smoothed %K
        const dLine = [];
        for (let i = dPeriod - 1; i < smoothedK.length; i++) {
            let sum = 0;
            for (let j = i - dPeriod + 1; j <= i; j++) sum += smoothedK[j].value;
            dLine.push({ time: smoothedK[i].time, value: Math.round((sum / dPeriod) * 100) / 100 });
        }

        const finalK = smoothedK.slice(dPeriod - 1).map(pt => ({
            time: pt.time,
            value: Math.round(pt.value * 100) / 100
        }));

        return { k: finalK, d: dLine };
    }

    function computeATR(candles, period = 14) {
        if (!candles || candles.length <= period) return [];
        const trs = [candles[0].high - candles[0].low];
        for (let i = 1; i < candles.length; i++) {
            const h = candles[i].high;
            const l = candles[i].low;
            const prevC = candles[i - 1].close;
            trs.push(Math.max(h - l, Math.abs(h - prevC), Math.abs(l - prevC)));
        }

        const result = [];
        let atr = trs.slice(0, period).reduce((a, b) => a + b, 0) / period;
        result.push({ time: candles[period - 1].time, value: Math.round(atr * 100) / 100 });

        for (let i = period; i < candles.length; i++) {
            atr = (atr * (period - 1) + trs[i]) / period;
            result.push({ time: candles[i].time, value: Math.round(atr * 100) / 100 });
        }
        return result;
    }

    function computeVWAP(candles, tf) {
        if (typeof window.calculateVWAP === 'function') {
            return window.calculateVWAP(candles, tf);
        }
        if (!candles || candles.length === 0) return [];
        let cumPV = 0, cumVol = 0;
        return candles.map(c => {
            const typ = (c.high + c.low + c.close) / 3;
            const vol = (c.volume && c.volume > 0) ? c.volume : 1;
            cumPV += typ * vol;
            cumVol += vol;
            return { time: c.time, value: Math.round((cumPV / cumVol) * 100) / 100 };
        });
    }

    // --- 2. Active Studies Manager Singleton ---

    class ActiveStudiesManager {
        constructor() {
            this.activeStudies = new Map();
            this.instanceCounter = 1;
            this.subpanesContainer = null;
            this.activeSettingsInstanceId = null;

            document.addEventListener('DOMContentLoaded', () => {
                this.init();
            });
        }

        init() {
            this.subpanesContainer = document.getElementById('chart-subpanes-container');
            if (!this.subpanesContainer) {
                // Create container if absent
                const workspace = document.querySelector('.chart-workspace');
                if (workspace) {
                    this.subpanesContainer = document.createElement('div');
                    this.subpanesContainer.id = 'chart-subpanes-container';
                    this.subpanesContainer.className = 'chart-subpanes-container';
                    workspace.appendChild(this.subpanesContainer);
                }
            }

            // Sync crosshair from main chart
            if (window.mainChart) {
                window.mainChart.subscribeCrosshairMove(param => {
                    this.syncCrosshairToSubpanes(param);
                });
            }

            window.addEventListener('resize', () => this.handleResize());
            window.addEventListener('themeChanged', (e) => this.handleTheme(e.detail?.theme));
        }

        addStudy(studyId, customInputs = {}, customName = null) {
            const instanceId = `study_${this.instanceCounter++}`;
            console.log(`[StudiesManager] Adding ${studyId} as ${instanceId}`);

            const baseKey = customInputs.base_type || studyId;

            const studyMetaMap = {
                sma: { name: 'SMA', overlay: true, defaultInputs: { period: 20, color: '#2962FF', lineWidth: 2 } },
                ema: { name: 'EMA', overlay: true, defaultInputs: { period: 20, color: '#FF6D00', lineWidth: 2 } },
                vwap: { name: 'VWAP', overlay: true, defaultInputs: { color: '#F5AC00', lineWidth: 2 } },
                bollinger_bands: { name: 'Bollinger Bands', overlay: true, defaultInputs: { period: 20, stdDev: 2.0, color: '#2962FF' } },
                supertrend: { name: 'Supertrend', overlay: true, defaultInputs: { period: 10, multiplier: 3.0 } },
                rsi: { name: 'RSI', overlay: false, defaultInputs: { period: 14, overbought: 70, oversold: 30, color: '#7E57C2' } },
                macd: { name: 'MACD', overlay: false, defaultInputs: { fast: 12, slow: 26, signal: 9 } },
                stochastic: { name: 'Stochastic', overlay: false, defaultInputs: { kPeriod: 14, dPeriod: 3, smooth: 3 } },
                atr: { name: 'ATR', overlay: false, defaultInputs: { period: 14, color: '#FF5252' } },
                // Volume & Market Profiles
                visible_range_vp: { name: 'Visible Range Volume Profile', overlay: true, isProfile: true, defaultInputs: { rows: 70, valueAreaPct: 0.70 } },
                session_vp: { name: 'Session Volume Profile', overlay: true, isProfile: true, defaultInputs: { rows: 50, valueAreaPct: 0.70 } },
                session_vp_hd: { name: 'Session Volume Profile HD', overlay: true, isProfile: true, defaultInputs: { rows: 120, valueAreaPct: 0.70 } },
                auto_anchored_vp: { name: 'Auto Anchored Volume Profile', overlay: true, isProfile: true, defaultInputs: { rows: 70, valueAreaPct: 0.70 } },
                fixed_range_vp: { name: 'Fixed Range Volume Profile', overlay: true, isProfile: true, defaultInputs: { rows: 70, valueAreaPct: 0.70 } },
                periodic_vp: { name: 'Periodic Volume Profile', overlay: true, isProfile: true, defaultInputs: { rows: 50, valueAreaPct: 0.70 } },
                tpo: { name: 'Time Price Opportunity (TPO)', overlay: true, isProfile: true, defaultInputs: { bracketMinutes: 30 } },
                session_tpo: { name: 'Session TPO', overlay: true, isProfile: true, defaultInputs: { bracketMinutes: 30 } }
            };

            const studyMeta = studyMetaMap[baseKey] || studyMetaMap[studyId] || { name: customName || studyId.toUpperCase(), overlay: true, defaultInputs: {} };
            const displayName = customName || studyMeta.name;
            const isOverlay = (customInputs.overlay !== undefined) ? customInputs.overlay : studyMeta.overlay;

            const inputs = Object.assign({}, studyMeta.defaultInputs, customInputs);

            const instance = {
                instanceId,
                studyId: baseKey,
                originalId: studyId,
                name: displayName,
                overlay: isOverlay,
                isProfile: !!studyMeta.isProfile,
                inputs,
                seriesList: [],
                paneChart: null,
                paneWrapper: null,
                legendEl: null,
                isVisible: true
            };

            if (instance.isProfile) {
                if (window.volumeProfileOverlay) {
                    window.volumeProfileOverlay.enable(studyId, inputs);
                }
                this.createOverlayLegendTag(instance);
            } else if (instance.overlay) {
                this.mountOverlayStudy(instance);
            } else {
                this.mountSubPaneStudy(instance);
            }

            this.activeStudies.set(instanceId, instance);

            // Compute data immediately if candles exist
            if (window.allLoadedCandles && window.allLoadedCandles.length > 0) {
                this.recalculateStudy(instance, window.allLoadedCandles);
            }

            return instanceId;
        }

        mountOverlayStudy(instance) {
            if (!window.mainChart) {
                setTimeout(() => {
                    if (window.mainChart) {
                        this.mountOverlayStudy(instance);
                        if (window.allLoadedCandles && window.allLoadedCandles.length > 0) {
                            this.recalculateStudy(instance, window.allLoadedCandles);
                        }
                    }
                }, 150);
                return;
            }

            const factory = typeof window.mainChart.addLineSeries === 'function'
                ? (opts) => window.mainChart.addLineSeries(opts)
                : (opts) => window.mainChart.addSeries(LightweightCharts.LineSeries, opts);

            if (instance.studyId === 'sma' || instance.studyId === 'ema' || instance.studyId === 'vwap') {
                const s = factory({
                    color: instance.inputs.color || '#2962FF',
                    lineWidth: instance.inputs.lineWidth || 2,
                    title: `${instance.name} ${instance.inputs.period || ''}`.trim()
                });
                instance.seriesList.push(s);
            } else if (instance.studyId === 'bollinger_bands') {
                const upper = factory({ color: instance.inputs.color || '#2962FF', lineWidth: 1, title: 'BB Upper' });
                const mid = factory({ color: '#FF6D00', lineWidth: 1, title: 'BB Mid' });
                const lower = factory({ color: instance.inputs.color || '#2962FF', lineWidth: 1, title: 'BB Lower' });
                instance.seriesList.push(upper, mid, lower);
            } else if (instance.studyId === 'supertrend') {
                const s = factory({
                    lineWidth: 2,
                    title: `Supertrend ${instance.inputs.period},${instance.inputs.multiplier}`
                });
                instance.seriesList.push(s);
            }

            this.createOverlayLegendTag(instance);
        }

        createOverlayLegendTag(instance) {
            const overlayContainer = document.getElementById('chart-legend-overlay');
            if (!overlayContainer) return;

            let legendTags = document.getElementById('chart-legend-study-tags');
            if (!legendTags) {
                legendTags = document.createElement('div');
                legendTags.id = 'chart-legend-study-tags';
                legendTags.className = 'chart-legend-study-tags';
                overlayContainer.appendChild(legendTags);
            }

            const tag = document.createElement('div');
            tag.className = 'study-legend-tag';
            tag.id = `legend-tag-${instance.instanceId}`;
            tag.innerHTML = `
                <span class="study-tag-title">${escapeText(instance.name)} <span class="study-tag-val font-mono">--</span></span>
                <span class="study-tag-controls">
                    <button class="study-tag-btn btn-eye" title="Hide/Show">👁️</button>
                    <button class="study-tag-btn btn-gear" title="Settings">⚙️</button>
                    <button class="study-tag-btn btn-close" title="Remove">✕</button>
                </span>
            `;

            tag.querySelector('.btn-eye').onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.toggleVisibility(instance.instanceId);
            };
            tag.querySelector('.btn-gear').onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.openSettingsModal(instance.instanceId);
            };
            tag.querySelector('.btn-close').onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.removeStudy(instance.instanceId);
            };

            legendTags.appendChild(tag);
            instance.legendEl = tag;
        }

        mountSubPaneStudy(instance) {
            if (!this.subpanesContainer) this.init();
            if (!this.subpanesContainer) return;

            const wrapper = document.createElement('div');
            wrapper.className = 'chart-subpane-wrapper';
            wrapper.id = `subpane-${instance.instanceId}`;

            // HUD Header inside subpane
            const hud = document.createElement('div');
            hud.className = 'subpane-legend-hud';
            hud.innerHTML = `
                <div class="subpane-hud-left">
                    <span class="subpane-hud-title font-mono">${escapeText(instance.name)}</span>
                    <span class="subpane-hud-val font-mono" id="hud-val-${instance.instanceId}">--</span>
                </div>
                <div class="subpane-hud-right">
                    <button class="subpane-hud-btn btn-eye" title="Hide/Show">👁️</button>
                    <button class="subpane-hud-btn btn-gear" title="Settings">⚙️</button>
                    <button class="subpane-hud-btn btn-close" title="Remove">✕</button>
                </div>
            `;

            hud.querySelector('.btn-eye').onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.toggleVisibility(instance.instanceId);
            };
            hud.querySelector('.btn-gear').onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.openSettingsModal(instance.instanceId);
            };
            hud.querySelector('.btn-close').onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.removeStudy(instance.instanceId);
            };

            wrapper.appendChild(hud);

            const chartMount = document.createElement('div');
            chartMount.className = 'subpane-chart-mount';
            wrapper.appendChild(chartMount);

            this.subpanesContainer.appendChild(wrapper);

            // Create Subpane Chart
            const isDark = !document.body.classList.contains('theme-light');
            const subChart = LightweightCharts.createChart(chartMount, {
                width: chartMount.clientWidth || 800,
                height: 125,
                layout: {
                    background: { type: 'solid', color: isDark ? '#0B0E14' : '#FFFFFF' },
                    textColor: isDark ? '#D1D4DC' : '#1E293B',
                },
                grid: {
                    vertLines: { color: isDark ? '#2A2E39' : '#E2E8F0' },
                    horzLines: { color: isDark ? '#2A2E39' : '#E2E8F0' },
                },
                timeScale: {
                    timeVisible: true,
                    secondsVisible: false,
                    visible: true
                }
            });

            instance.paneChart = subChart;
            instance.paneWrapper = wrapper;
            instance.legendEl = hud;

            // Synchronize visible range bidirectionally with main chart
            if (window.mainChart && window.mainChart.timeScale()) {
                const mainTS = window.mainChart.timeScale();
                const subTS = subChart.timeScale();

                subTS.subscribeVisibleLogicalRangeChange(range => {
                    if (range && !instance._isSyncing) {
                        instance._isSyncing = true;
                        mainTS.setVisibleLogicalRange(range);
                        instance._isSyncing = false;
                    }
                });

                mainTS.subscribeVisibleLogicalRangeChange(range => {
                    if (range && !instance._isSyncing) {
                        instance._isSyncing = true;
                        subTS.setVisibleLogicalRange(range);
                        instance._isSyncing = false;
                    }
                });
            }

            // Series creation inside subpane
            if (instance.studyId === 'rsi') {
                const line = subChart.addLineSeries({
                    color: instance.inputs.color || '#7E57C2',
                    lineWidth: 2,
                    priceScaleId: 'right'
                });
                instance.seriesList.push(line);

                // Add 70 & 30 reference lines
                line.createPriceLine({ price: instance.inputs.overbought || 70, color: '#787B86', lineStyle: 2, title: 'OB 70' });
                line.createPriceLine({ price: instance.inputs.oversold || 30, color: '#787B86', lineStyle: 2, title: 'OS 30' });
            } else if (instance.studyId === 'macd') {
                const hist = subChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                const macdLine = subChart.addLineSeries({ color: '#2962FF', lineWidth: 1.5 });
                const sigLine = subChart.addLineSeries({ color: '#FF6D00', lineWidth: 1.5 });
                instance.seriesList.push(hist, macdLine, sigLine);
            } else if (instance.studyId === 'stochastic') {
                const kLine = subChart.addLineSeries({ color: '#2962FF', lineWidth: 1.5 });
                const dLine = subChart.addLineSeries({ color: '#FF6D00', lineWidth: 1.5 });
                instance.seriesList.push(kLine, dLine);
                kLine.createPriceLine({ price: 80, color: '#787B86', lineStyle: 2, title: '80' });
                kLine.createPriceLine({ price: 20, color: '#787B86', lineStyle: 2, title: '20' });
            } else if (instance.studyId === 'atr') {
                const line = subChart.addLineSeries({ color: instance.inputs.color || '#FF5252', lineWidth: 2 });
                instance.seriesList.push(line);
            }

            // Sync Crosshair from subpane
            subChart.subscribeCrosshairMove(param => {
                if (window.mainChart && param && param.point) {
                    window.mainChart.setCrosshairPosition(param.point.x, param.point.y, subChart);
                }
                this.updateLegendValues(instance, param);
            });
        }

        recalculateStudy(instance, candles) {
            if (!instance || !instance.seriesList || instance.seriesList.length === 0) return;
            if (!candles || candles.length === 0) return;

            const tf = window.currentSymbolTimeframe || '1D';

            try {
                if (instance.studyId === 'sma') {
                    const data = computeSMA(candles, instance.inputs.period || 20);
                    instance.seriesList[0].setData(data);
                } else if (instance.studyId === 'ema') {
                    const data = computeEMA(candles, instance.inputs.period || 20);
                    instance.seriesList[0].setData(data);
                } else if (instance.studyId === 'vwap') {
                    if (typeof window.calculateVWAP === 'function') {
                        const data = window.calculateVWAP(candles, tf);
                        instance.seriesList[0].setData(data);
                    }
                } else if (instance.studyId === 'bollinger_bands') {
                    const bb = computeBollingerBands(candles, instance.inputs.period || 20, instance.inputs.stdDev || 2.0);
                    instance.seriesList[0].setData(bb.upper);
                    instance.seriesList[1].setData(bb.middle);
                    instance.seriesList[2].setData(bb.lower);
                } else if (instance.studyId === 'supertrend') {
                    const st = computeSupertrend(candles, instance.inputs.period || 10, instance.inputs.multiplier || 3.0);
                    instance.seriesList[0].setData(st);
                } else if (instance.studyId === 'rsi') {
                    const data = computeRSI(candles, instance.inputs.period || 14);
                    instance.seriesList[0].setData(data);
                } else if (instance.studyId === 'macd') {
                    const res = computeMACD(candles, instance.inputs.fast || 12, instance.inputs.slow || 26, instance.inputs.signal || 9);
                    instance.seriesList[0].setData(res.hist);
                    instance.seriesList[1].setData(res.macd);
                    instance.seriesList[2].setData(res.signal);
                } else if (instance.studyId === 'stochastic') {
                    const res = computeStochastic(candles, instance.inputs.kPeriod || 14, instance.inputs.dPeriod || 3, instance.inputs.smooth || 3);
                    instance.seriesList[0].setData(res.k);
                    instance.seriesList[1].setData(res.d);
                } else if (instance.studyId === 'atr') {
                    const data = computeATR(candles, instance.inputs.period || 14);
                    instance.seriesList[0].setData(data);
                }
            } catch (err) {
                console.error(`[StudiesManager] Recalculation error on ${instance.instanceId}:`, err);
            }
        }

        recalculateAll(candles) {
            this.activeStudies.forEach(instance => {
                this.recalculateStudy(instance, candles);
            });
            if (window.volumeProfileOverlay) {
                window.volumeProfileOverlay.requestRedraw();
            }
        }

        toggleVisibility(instanceId) {
            const instance = this.activeStudies.get(instanceId);
            if (!instance) return;

            instance.isVisible = !instance.isVisible;
            instance.seriesList.forEach(s => {
                s.applyOptions({ visible: instance.isVisible });
            });

            if (instance.paneWrapper) {
                instance.paneWrapper.style.display = instance.isVisible ? '' : 'none';
            }

            if (instance.isProfile) {
                if (window.volumeProfileOverlay) {
                    if (instance.isVisible) {
                        window.volumeProfileOverlay.enable(instance.studyId, instance.inputs);
                    } else {
                        window.volumeProfileOverlay.disable();
                    }
                }
                const canvas = document.getElementById('volume-profile-canvas');
                if (canvas) canvas.style.display = instance.isVisible ? 'block' : 'none';
            }

            if (instance.legendEl) {
                const btnEye = instance.legendEl.querySelector('.btn-eye');
                if (btnEye) {
                    btnEye.textContent = instance.isVisible ? '👁️' : '🙈';
                    btnEye.classList.toggle('hidden-study', !instance.isVisible);
                    btnEye.style.opacity = instance.isVisible ? '1' : '0.45';
                }
            }
        }

        removeStudy(instanceId) {
            const instance = this.activeStudies.get(instanceId);
            if (!instance) return;

            console.log(`[StudiesManager] Removing study ${instanceId}`);

            if (instance.isProfile && window.volumeProfileOverlay) {
                window.volumeProfileOverlay.disable();
            }

            // Remove series
            if (instance.overlay && window.mainChart) {
                instance.seriesList.forEach(s => {
                    try { window.mainChart.removeSeries(s); } catch (e) {}
                });
            } else if (instance.paneChart) {
                try {
                    instance.paneChart.remove();
                } catch (e) {}
            }

            // Remove DOM elements
            if (instance.paneWrapper) {
                instance.paneWrapper.remove();
            }
            if (instance.legendEl) {
                instance.legendEl.remove();
            }

            this.activeStudies.delete(instanceId);
            this.handleResize();
        }

        syncCrosshairToSubpanes(param) {
            if (!param || !param.point) return;
            this.activeStudies.forEach(instance => {
                if (instance.paneChart && typeof instance.paneChart.setCrosshairPosition === 'function') {
                    const mount = instance.paneWrapper?.querySelector('.subpane-chart-mount');
                    if (mount && param.point.x >= 0 && param.point.x <= mount.clientWidth) {
                        instance.paneChart.setCrosshairPosition(param.point.x, param.point.y, window.mainChart);
                    }
                }
                this.updateLegendValues(instance, param);
            });
        }

        updateLegendValues(instance, param) {
            if (!instance.legendEl || !param || !param.seriesData) return;
            const s = instance.seriesList[0];
            if (!s) return;

            const valObj = param.seriesData.get(s);
            const valEl = instance.legendEl.querySelector('.study-tag-val, .subpane-hud-val');
            if (valEl) {
                if (valObj && typeof valObj.value === 'number') {
                    valEl.textContent = valObj.value.toFixed(2);
                } else if (valObj && typeof valObj.close === 'number') {
                    valEl.textContent = valObj.close.toFixed(2);
                } else {
                    valEl.textContent = '--';
                }
            }
        }

        handleResize() {
            this.activeStudies.forEach(instance => {
                if (instance.paneChart && instance.paneWrapper) {
                    const mount = instance.paneWrapper.querySelector('.subpane-chart-mount');
                    if (mount) {
                        instance.paneChart.applyOptions({
                            width: mount.clientWidth,
                            height: 125
                        });
                    }
                }
            });
        }

        handleTheme(theme) {
            const isDark = (theme !== 'light');
            this.activeStudies.forEach(instance => {
                if (instance.paneChart) {
                    instance.paneChart.applyOptions({
                        layout: {
                            background: { type: 'solid', color: isDark ? '#0B0E14' : '#FFFFFF' },
                            textColor: isDark ? '#D1D4DC' : '#1E293B',
                        },
                        grid: {
                            vertLines: { color: isDark ? '#2A2E39' : '#E2E8F0' },
                            horzLines: { color: isDark ? '#2A2E39' : '#E2E8F0' },
                        }
                    });
                }
            });
        }

        openSettingsModal(instanceId) {
            const instance = this.activeStudies.get(instanceId);
            if (!instance) return;

            this.activeSettingsInstanceId = instanceId;
            let modal = document.getElementById('study-settings-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'study-settings-modal';
                modal.className = 'study-settings-modal-backdrop modal-overlay';
                modal.innerHTML = `
                    <div class="study-settings-card modal-content">
                        <div class="study-settings-header">
                            <span class="study-settings-title" id="settings-modal-title">Settings</span>
                            <button class="study-settings-close-btn" id="close-settings-modal">✕</button>
                        </div>
                        <div class="study-settings-body" id="settings-modal-body">
                            <!-- Inputs rendered dynamically -->
                        </div>
                        <div class="study-settings-footer">
                            <button class="btn-secondary" id="btn-cancel-settings">Cancel</button>
                            <button class="btn-primary" id="btn-save-settings">Apply</button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);

                document.getElementById('close-settings-modal').onclick = () => this.closeSettingsModal();
                document.getElementById('btn-cancel-settings').onclick = () => this.closeSettingsModal();
                document.getElementById('btn-save-settings').onclick = () => this.saveSettingsModal();
            }

            const titleEl = document.getElementById('settings-modal-title');
            const bodyEl = document.getElementById('settings-modal-body');
            titleEl.textContent = `${instance.name} Inputs`;
            bodyEl.innerHTML = '';

            // Generate inputs based on instance.inputs
            Object.keys(instance.inputs).forEach(key => {
                const val = instance.inputs[key];
                const row = document.createElement('div');
                row.className = 'settings-field-row';

                const label = document.createElement('label');
                label.className = 'settings-field-label';
                label.textContent = formatKeyLabel(key);

                let input;
                if (typeof val === 'number') {
                    input = document.createElement('input');
                    input.type = 'number';
                    input.className = 'form-control font-mono';
                    input.value = val;
                    input.step = Number.isInteger(val) ? '1' : '0.1';
                } else if (typeof val === 'string' && val.startsWith('#')) {
                    input = document.createElement('input');
                    input.type = 'color';
                    input.className = 'form-control-color';
                    input.value = val;
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'form-control';
                    input.value = val;
                }
                input.id = `input-setting-${key}`;

                row.appendChild(label);
                row.appendChild(input);
                bodyEl.appendChild(row);
            });

            modal.classList.remove('hidden');
            modal.style.display = 'flex';
        }

        saveSettingsModal() {
            const instanceId = this.activeSettingsInstanceId;
            const instance = this.activeStudies.get(instanceId);
            if (!instance) return;

            Object.keys(instance.inputs).forEach(key => {
                const el = document.getElementById(`input-setting-${key}`);
                if (el) {
                    if (typeof instance.inputs[key] === 'number') {
                        instance.inputs[key] = parseFloat(el.value) || instance.inputs[key];
                    } else {
                        instance.inputs[key] = el.value;
                    }
                }
            });

            // Recreate/update series options
            if (instance.inputs.color && instance.seriesList[0]) {
                instance.seriesList[0].applyOptions({ color: instance.inputs.color });
            }

            if (instance.isProfile && window.volumeProfileOverlay) {
                window.volumeProfileOverlay.enable(instance.studyId, instance.inputs);
            }

            if (window.allLoadedCandles) {
                this.recalculateStudy(instance, window.allLoadedCandles);
            }

            this.closeSettingsModal();
        }

        closeSettingsModal() {
            const modal = document.getElementById('study-settings-modal');
            if (modal) {
                modal.classList.add('hidden');
                modal.style.display = 'none';
            }
            this.activeSettingsInstanceId = null;
        }
    }

    function formatKeyLabel(key) {
        return key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
    }

    function escapeText(str) {
        return String(str || '').replace(/[&<>"']/g, '');
    }

    window.activeStudiesManager = new ActiveStudiesManager();
})();
