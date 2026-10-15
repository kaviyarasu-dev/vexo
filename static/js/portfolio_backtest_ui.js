/**
 * Portfolio & Multi-Stock Basket Backtest Controller
 * Handles Dual-Mode Switcher, Universe Presets, Portfolio Sizing & Contention,
 * Consolidated Lightweight Charts Equity Curve vs. NIFTY 50 Benchmark,
 * and Sortable Asset Contribution Breakdown Table.
 */
class PortfolioBacktestController {
    constructor(backtestUI) {
        this.ui = backtestUI;
        this.activeMode = 'single'; // 'single' | 'portfolio'
        this.selectedUniverse = 'NIFTY_50';
        this.customSymbols = ['NSE:RELIANCE-EQ', 'NSE:TCS-EQ', 'NSE:INFY-EQ', 'NSE:HDFCBANK-EQ', 'NSE:ICICIBANK-EQ'];
        this.universes = [];
        this.portfolioResult = null;

        // Visual Tabs & Filters
        this.activeSubtab = 'overview';
        this.contribSortKey = 'net_pnl';
        this.contribSortAsc = false;
        this.contribSearchTerm = '';
        this.tradesFilter = 'ALL';
        this.tradesSearchTerm = '';

        // Charts
        this.equityChart = null;
        this.drawdownChart = null;
        this.equitySeries = null;
        this.benchmarkSeries = null;
        this.drawdownSeries = null;

        this.init();
    }

    /**
     * Initializes mode switcher, universe chips, subtabs, and event listeners.
     */
    init() {
        this.bindModeSwitcher();
        this.bindUniverseControls();
        this.bindPortfolioSubtabs();
        this.bindContributionSorting();
        this.bindTradeLedgerFilters();
        this.bindAlertRetry();
        this.loadUniverses();

        // Window resize observer
        window.addEventListener('resize', () => {
            if (this.activeMode === 'portfolio') {
                this.resizeCharts();
            }
        });
    }

    /**
     * Binds Dual-Mode Switcher buttons.
     */
    bindModeSwitcher() {
        const switcher = document.getElementById('studio-mode-switcher');
        if (!switcher) return;

        const btns = switcher.querySelectorAll('.mode-toggle-btn');
        btns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.currentTarget.dataset.mode;
                if (mode) {
                    this.switchMode(mode);
                }
            });
        });
    }

    switchMode(mode) {
        if (this.ui && typeof this.ui.switchMode === 'function') {
            return this.ui.switchMode(mode);
        }
    }

    /**
     * Binds universe chips, custom ticker input, sizing model selection, and date presets.
     */
    bindUniverseControls() {
        // Date Presets
        const datePresets = document.querySelectorAll('#portfolio-date-presets .pill-btn');
        datePresets.forEach(btn => {
            btn.addEventListener('click', (e) => {
                datePresets.forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                const preset = e.currentTarget.dataset.preset;
                let startYear = 2020;
                if (preset === '1Y') startYear = 2022;
                else if (preset === '3Y') startYear = 2020;
                else if (preset === '5Y') startYear = 2018;

                const startInput = document.getElementById('portfolio-start-date');
                const endInput = document.getElementById('portfolio-end-date');
                if (startInput) startInput.value = `${startYear}-01-01`;
                if (endInput) endInput.value = '2023-12-31';
            });
        });

        // Sizing Model Change
        const sizingSelect = document.getElementById('portfolio-sizing-model');
        const sizingValLabel = document.getElementById('portfolio-sizing-val-label');
        const sizingValInput = document.getElementById('portfolio-sizing-val');

        if (sizingSelect) {
            sizingSelect.addEventListener('change', (e) => {
                const model = e.target.value;
                if (model === 'EQUAL_WEIGHT') {
                    if (sizingValLabel) sizingValLabel.textContent = 'Sizing Value (% per Slot)';
                    if (sizingValInput) { sizingValInput.value = 10; sizingValInput.step = 1; }
                } else if (model === 'INVERSE_ATR') {
                    if (sizingValLabel) sizingValLabel.textContent = 'Max Risk per Pos (% of Capital)';
                    if (sizingValInput) { sizingValInput.value = 1.0; sizingValInput.step = 0.5; }
                } else if (model === 'FIXED_AMOUNT') {
                    if (sizingValLabel) sizingValLabel.textContent = 'Fixed Rupee Amount (₹ / Slot)';
                    if (sizingValInput) { sizingValInput.value = 100000; sizingValInput.step = 10000; }
                }
            });
        }

        // Custom Tickers Add Button & Input
        const addCustomBtn = document.getElementById('btn-add-custom-symbol');
        const customInput = document.getElementById('portfolio-custom-symbols-input');

        const addCustomSymbolFromInput = () => {
            if (!customInput) return;
            const raw = customInput.value.trim().toUpperCase();
            if (!raw) return;

            // Handle comma-separated list
            const tokens = raw.split(',').map(s => s.trim()).filter(Boolean);
            tokens.forEach(tok => {
                let sym = tok;
                if (!sym.startsWith('NSE:')) sym = 'NSE:' + sym;
                if (!sym.endsWith('-EQ') && !sym.endsWith('-INDEX')) sym = sym + '-EQ';
                if (!this.customSymbols.includes(sym)) {
                    this.customSymbols.push(sym);
                }
            });

            customInput.value = '';
            this.renderCustomTags();
        };

        if (addCustomBtn) {
            addCustomBtn.addEventListener('click', addCustomSymbolFromInput);
        }
        if (customInput) {
            customInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addCustomSymbolFromInput();
                }
            });
        }

        this.renderCustomTags();
    }

    /**
     * Renders custom symbol tags in the custom basket card.
     */
    renderCustomTags() {
        const tagContainer = document.getElementById('portfolio-custom-tags');
        const countBadge = document.getElementById('portfolio-custom-count-badge');
        if (countBadge) countBadge.textContent = this.customSymbols.length;
        if (!tagContainer) return;

        tagContainer.innerHTML = '';
        this.customSymbols.forEach((sym, idx) => {
            const tag = document.createElement('span');
            tag.className = 'custom-symbol-tag';
            tag.innerHTML = `${sym} <span class="tag-remove" data-idx="${idx}" title="Remove">✕</span>`;
            tagContainer.appendChild(tag);
        });

        tagContainer.querySelectorAll('.tag-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.dataset.idx, 10);
                if (!isNaN(idx)) {
                    this.customSymbols.splice(idx, 1);
                    this.renderCustomTags();
                }
            });
        });
    }

    /**
     * Binds portfolio subtabs (Overview, Asset Contributions, Heatmap, Trades).
     */
    bindPortfolioSubtabs() {
        const subtabsContainer = document.getElementById('portfolio-subtabs');
        if (!subtabsContainer) return;

        const subtabs = subtabsContainer.querySelectorAll('.subtab-btn');
        subtabs.forEach(btn => {
            btn.addEventListener('click', (e) => {
                subtabs.forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                const subtab = target.dataset.portfolioSubtab;
                this.activeSubtab = subtab;

                const overviewPane = document.getElementById('portfolio-subtab-overview');
                const contribPane = document.getElementById('portfolio-subtab-contributions');
                const heatmapPane = document.getElementById('portfolio-subtab-heatmap');
                const tradesPane = document.getElementById('portfolio-subtab-trades');

                if (overviewPane) overviewPane.classList.toggle('hidden', subtab !== 'overview');
                if (contribPane) contribPane.classList.toggle('hidden', subtab !== 'contributions');
                if (heatmapPane) heatmapPane.classList.toggle('hidden', subtab !== 'heatmap');
                if (tradesPane) tradesPane.classList.toggle('hidden', subtab !== 'trades');

                if (subtab === 'overview') {
                    requestAnimationFrame(() => this.resizeCharts());
                }
            });
        });
    }

    /**
     * Binds Asset Contribution Table sorting and search filtering.
     */
    bindContributionSorting() {
        const headers = document.querySelectorAll('.th-sortable-contrib');
        headers.forEach(th => {
            th.addEventListener('click', (e) => {
                const sortKey = e.currentTarget.dataset.contribSort;
                if (!sortKey) return;
                if (this.contribSortKey === sortKey) {
                    this.contribSortAsc = !this.contribSortAsc;
                } else {
                    this.contribSortKey = sortKey;
                    this.contribSortAsc = (sortKey === 'symbol');
                }
                if (this.portfolioResult && this.portfolioResult.asset_contributions) {
                    this.renderAssetContributionTable(this.portfolioResult.asset_contributions);
                }
            });
        });

        const searchInput = document.getElementById('input-search-contributions');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.contribSearchTerm = e.target.value.trim().toUpperCase();
                if (this.portfolioResult && this.portfolioResult.asset_contributions) {
                    this.renderAssetContributionTable(this.portfolioResult.asset_contributions);
                }
            });
        }
    }

    /**
     * Binds portfolio combined trade ledger filter pills and search input.
     */
    bindTradeLedgerFilters() {
        const pills = document.querySelectorAll('#portfolio-trades-filter-pills .filter-pill');
        pills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                pills.forEach(p => p.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.tradesFilter = e.currentTarget.dataset.portFilter || 'ALL';
                if (this.portfolioResult && this.portfolioResult.trades) {
                    this.renderPortfolioTradeLedger(this.portfolioResult.trades);
                }
            });
        });

        const searchTrades = document.getElementById('input-search-portfolio-trades');
        if (searchTrades) {
            searchTrades.addEventListener('input', (e) => {
                this.tradesSearchTerm = e.target.value.trim().toUpperCase();
                if (this.portfolioResult && this.portfolioResult.trades) {
                    this.renderPortfolioTradeLedger(this.portfolioResult.trades);
                }
            });
        }

        const exportBtn = document.getElementById('btn-export-portfolio-trades-csv');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportPortfolioTradesCSV();
            });
        }
    }

    /**
     * Binds error banner retry button.
     */
    bindAlertRetry() {
        const retryBtn = document.getElementById('btn-portfolio-alert-retry');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.runPortfolioBacktest();
            });
        }
    }

    /**
     * Fetches available universes from /api/v1/backtest/portfolio/universes
     * and renders preset chips.
     */
    async loadUniverses() {
        try {
            const resp = await fetch('/api/v1/backtest/portfolio/universes');
            if (!resp.ok) return;
            const data = await resp.json();
            const list = data.universes || data;
            if (Array.isArray(list)) {
                this.universes = list;
                this.renderUniverseChips();
            }
        } catch (e) {
            console.error('Failed to load portfolio universes:', e);
        }
    }

    /**
     * Renders universe selection chips.
     */
    renderUniverseChips() {
        const container = document.getElementById('portfolio-universe-chips');
        if (!container) return;

        let html = '';
        this.universes.forEach(u => {
            const active = u.id === this.selectedUniverse ? 'active' : '';
            html += `
                <button type="button" class="universe-chip ${active}" data-universe="${u.id}">
                    <span class="chip-name">${u.name}</span>
                    <span class="badge-count-pill">${u.count}</span>
                </button>
            `;
        });

        const customActive = this.selectedUniverse === 'CUSTOM' ? 'active' : '';
        html += `
            <button type="button" class="universe-chip ${customActive}" data-universe="CUSTOM">
                <span class="chip-name">Custom Basket</span>
                <span class="badge-count-pill" id="portfolio-custom-count-badge">${this.customSymbols.length}</span>
            </button>
        `;

        container.innerHTML = html;

        // Bind clicks
        container.querySelectorAll('.universe-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                container.querySelectorAll('.universe-chip').forEach(c => c.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                const uniId = target.dataset.universe;
                this.selectedUniverse = uniId;

                const customBox = document.getElementById('portfolio-custom-symbols-box');
                if (customBox) {
                    customBox.classList.toggle('hidden', uniId !== 'CUSTOM');
                }

                const badge = document.getElementById('portfolio-active-universe-badge');
                if (badge) {
                    if (uniId === 'CUSTOM') {
                        badge.textContent = `Custom Basket (${this.customSymbols.length} Stocks)`;
                    } else {
                        const match = this.universes.find(u => u.id === uniId);
                        badge.textContent = match ? `${match.name} (${match.count} Stocks)` : uniId;
                    }
                }
            });
        });
    }

    /**
     * Collects portfolio configuration inputs and executes portfolio backtest.
     * Calls POST /api/v1/backtest/portfolio/run.
     */
    async runPortfolioBacktest() {
        const alertBox = document.getElementById('portfolio-alert-banner');
        if (alertBox) alertBox.classList.add('hidden');

        // Validation for Custom basket
        if (this.selectedUniverse === 'CUSTOM' && this.customSymbols.length === 0) {
            this.showErrorBanner('Please add at least 1 NSE symbol to your custom portfolio basket.');
            return;
        }

        const strategy = this.ui ? this.ui.activeStrategy : 'SMA_CROSS';
        const timeframe = document.getElementById('portfolio-timeframe-select')?.value || '1D';
        const startDate = document.getElementById('portfolio-start-date')?.value || '2020-01-01';
        const endDate = document.getElementById('portfolio-end-date')?.value || '2023-12-31';
        const initialCap = parseFloat(document.getElementById('bt-initial-capital')?.value) || 1000000.0;
        const maxPositions = parseInt(document.getElementById('portfolio-max-positions')?.value, 10) || 10;
        const sizingModel = document.getElementById('portfolio-sizing-model')?.value || 'EQUAL_WEIGHT';
        const sizingVal = parseFloat(document.getElementById('portfolio-sizing-val')?.value) || 10.0;
        const rankingMetric = document.getElementById('portfolio-ranking-metric')?.value || 'AUTO';
        const slippage = parseFloat(document.getElementById('bt-slippage-slider')?.value) || 5.0;
        const slVal = parseFloat(document.getElementById('portfolio-stop-loss')?.value);
        const tpVal = parseFloat(document.getElementById('portfolio-take-profit')?.value);

        // Get strategy parameters from the active strategy UI
        const baseFormData = (this.ui && typeof this.ui.gatherFormData === 'function') ? this.ui.gatherFormData() : {};
        const params = baseFormData.parameters || {};

        const payload = {
            strategy: strategy,
            universe_type: this.selectedUniverse === 'CUSTOM' ? 'CUSTOM' : 'PREDEFINED',
            universe_name: this.selectedUniverse === 'CUSTOM' ? null : this.selectedUniverse,
            symbols: this.selectedUniverse === 'CUSTOM' ? this.customSymbols : null,
            timeframe: timeframe,
            start_date: startDate,
            end_date: endDate,
            initial_capital: initialCap,
            max_open_positions: maxPositions,
            sizing_model: sizingModel,
            sizing_val: sizingVal,
            ranking_metric: rankingMetric,
            slippage_bps: slippage,
            stop_loss_pct: !isNaN(slVal) ? slVal : null,
            take_profit_pct: !isNaN(tpVal) ? tpVal : null,
            parameters: params
        };

        const statusText = document.getElementById('studio-status-text');
        const statusChip = document.getElementById('studio-status-chip');
        const runBtn = document.getElementById('btn-run-studio-backtest');

        if (statusText) statusText.textContent = 'Backtesting Portfolio Basket...';
        if (statusChip) statusChip.classList.add('running');
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner-inline">⏳</span> Backtesting Real Basket Data...';
        }

        try {
            const resp = await fetch('/api/v1/backtest/portfolio/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) {
                const errJson = await resp.json().catch(() => ({}));
                const msg = errJson.detail || errJson.message || `HTTP ${resp.status}: Backtest error`;
                throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
            }

            const data = await resp.json();
            this.portfolioResult = data;

            // Render all portfolio components
            this.renderPortfolioOverview(data, payload);
            this.renderPortfolioCharts(data.equity_curve, data.benchmark_curve);
            this.renderAssetContributionTable(data.asset_contributions || []);
            this.renderPortfolioHeatmap(data.monthly_returns || {});
            this.renderPortfolioTradeLedger(data.trades || []);

            // Inform trader if any symbols were skipped due to missing DuckDB history
            if (data.skipped_symbols && data.skipped_symbols.length > 0) {
                const skippedList = data.skipped_symbols.slice(0, 4).join(', ');
                const moreCount = data.skipped_symbols.length > 4 ? ` (+${data.skipped_symbols.length - 4} more)` : '';
                this.showInfoBanner(`Real Data Backtest executed across ${data.symbols_tested.length} stocks. Skipped ${data.skipped_symbols.length} stocks without real DuckDB history: ${skippedList}${moreCount}.`);
            } else {
                this.hideAlertBanner();
            }

            if (statusText) statusText.textContent = 'Portfolio Ready';
            if (statusChip) statusChip.classList.remove('running');
        } catch (err) {
            console.error('Portfolio Backtest execution error:', err);
            this.showErrorBanner(`Backtest Failed: ${err.message}`);
            if (statusText) statusText.textContent = 'Backtest Failed';
            if (statusChip) statusChip.classList.remove('running');
        } finally {
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="btn-icon">🧺</span> <span class="btn-text">Run Portfolio Basket Backtest</span>';
            }
        }
    }

    /**
     * Displays institutional alert banner on simulation failure.
     * @param {string} msg
     */
    showErrorBanner(msg) {
        const alertBox = document.getElementById('portfolio-alert-banner');
        const alertMsg = document.getElementById('portfolio-alert-msg');
        if (alertBox && alertMsg) {
            alertMsg.textContent = msg;
            alertBox.classList.remove('hidden');
        }
    }

    showInfoBanner(msg) {
        const alertBox = document.getElementById('portfolio-alert-banner');
        const alertMsg = document.getElementById('portfolio-alert-msg');
        if (alertBox && alertMsg) {
            alertMsg.textContent = msg;
            alertBox.classList.remove('hidden');
        }
    }

    hideAlertBanner() {
        const alertBox = document.getElementById('portfolio-alert-banner');
        if (alertBox) {
            alertBox.classList.add('hidden');
        }
    }

    /**
     * Populates Portfolio Overview header and 9 KPI Metric cards.
     */
    renderPortfolioOverview(data, payload = {}) {
        const metrics = data.metrics || {};

        // Meta tags
        const stratMap = {
            'SMA_CROSS': 'SMA Crossover',
            'RSI_REVERSION': 'RSI Reversal',
            'BOLLINGER_BANDS': 'Bollinger Bands',
            'SUPERTREND': 'Supertrend',
            'MACD': 'MACD Momentum'
        };
        const stratDisplay = stratMap[data.strategy] || data.strategy;
        const uniDisplay = data.universe_name === 'CUSTOM' ? 'Custom Basket' : (data.universe_name || 'NIFTY 50');

        const tagStrat = document.getElementById('meta-portfolio-strategy-tag');
        const tagUni = document.getElementById('meta-portfolio-universe-tag');
        const tagSlots = document.getElementById('meta-portfolio-slots-tag');
        const tagCap = document.getElementById('meta-portfolio-capital-tag');

        if (tagStrat) tagStrat.innerHTML = `Strategy: <strong>${stratDisplay}</strong>`;
        if (tagUni) tagUni.innerHTML = `Universe: <strong>${uniDisplay} (${data.symbols_tested ? data.symbols_tested.length : 0} Stocks)</strong>`;
        if (tagSlots) tagSlots.innerHTML = `Slots: <strong>${payload.max_open_positions || 10} Concurrent</strong>`;
        if (tagCap) tagCap.innerHTML = `Capital: <strong>₹${Number(metrics.initial_capital || 1000000).toLocaleString('en-IN')}</strong>`;

        // Headline Net Return
        const netProfit = metrics.net_profit || 0;
        const returnPct = metrics.return_pct || 0;
        const headlineEl = document.getElementById('portfolio-headline-net-pnl');
        if (headlineEl) {
            const sign = netProfit >= 0 ? '+' : '';
            headlineEl.textContent = `${sign}₹${Number(netProfit.toFixed(2)).toLocaleString('en-IN')} (${sign}${returnPct.toFixed(2)}%)`;
            headlineEl.className = `pnl-val font-mono ${netProfit >= 0 ? 'text-green' : 'text-red'}`;
        }

        // 9 KPI Cards
        const cagrVal = typeof metrics.cagr === 'number' ? (metrics.cagr * 100).toFixed(2) + '%' : '0.00%';
        const cagrEl = document.getElementById('port-m-cagr');
        if (cagrEl) {
            cagrEl.textContent = cagrVal;
            cagrEl.className = `m-value font-mono ${metrics.cagr >= 0 ? 'text-green' : 'text-red'}`;
        }

        const bmCagrEl = document.getElementById('port-m-bm-cagr');
        if (bmCagrEl) {
            const bmCagr = typeof metrics.benchmark_cagr === 'number' ? (metrics.benchmark_cagr * 100).toFixed(2) + '%' : '0.00%';
            bmCagrEl.textContent = `NIFTY 50: ${bmCagr}`;
        }

        const netPnlEl = document.getElementById('port-m-net-pnl');
        if (netPnlEl) {
            const sign = netProfit >= 0 ? '+' : '';
            netPnlEl.textContent = `${sign}₹${Number(netProfit.toFixed(2)).toLocaleString('en-IN')}`;
            netPnlEl.className = `m-value font-mono ${netProfit >= 0 ? 'text-green' : 'text-red'}`;
        }

        const finalEquityEl = document.getElementById('port-m-final-equity');
        if (finalEquityEl) {
            finalEquityEl.textContent = `Final Equity: ₹${Number((metrics.final_equity || 0).toFixed(2)).toLocaleString('en-IN')}`;
        }

        const maxDdEl = document.getElementById('port-m-max-dd');
        if (maxDdEl) {
            const dd = typeof metrics.max_drawdown === 'number' ? (metrics.max_drawdown * 100).toFixed(2) + '%' : '0.00%';
            maxDdEl.textContent = `-${dd}`;
        }

        const winRateEl = document.getElementById('port-m-win-rate');
        if (winRateEl) {
            const wr = typeof metrics.win_rate === 'number' ? (metrics.win_rate * 100).toFixed(1) + '%' : '0.0%';
            winRateEl.textContent = wr;
        }

        const winLossCountEl = document.getElementById('port-m-win-loss-count');
        if (winLossCountEl) {
            winLossCountEl.textContent = `${metrics.winning_trades || 0} Wins / ${metrics.losing_trades || 0} Losses (${metrics.total_trades || 0} Total)`;
        }

        const pfEl = document.getElementById('port-m-profit-factor');
        if (pfEl) pfEl.textContent = (metrics.profit_factor || 0).toFixed(2);

        const sharpeEl = document.getElementById('port-m-sharpe');
        if (sharpeEl) sharpeEl.textContent = (metrics.sharpe_ratio || 0).toFixed(2);

        const sortinoEl = document.getElementById('port-m-sortino');
        if (sortinoEl) sortinoEl.textContent = (metrics.sortino_ratio || 0).toFixed(2);

        const exposureEl = document.getElementById('port-m-exposure');
        if (exposureEl) {
            const exp = typeof metrics.avg_exposure_ratio === 'number' ? (metrics.avg_exposure_ratio * 100).toFixed(1) + '%' : '0.0%';
            exposureEl.textContent = exp;
        }

        const feesEl = document.getElementById('port-m-fees');
        if (feesEl) {
            feesEl.textContent = `₹${Number((metrics.total_statutory_costs || 0).toFixed(2)).toLocaleString('en-IN')}`;
        }
    }

    /**
     * Renders the portfolio equity curve and benchmark comparison on Lightweight Charts.
     * @param {Array<{timestamp: string, equity: number}>} portfolioCurve
     * @param {Array<{timestamp: string, value: number}>} benchmarkCurve
     */
    renderPortfolioCharts(portfolioCurve, benchmarkCurve) {
        if (!window.LightweightCharts) {
            console.error('LightweightCharts library not found');
            return;
        }

        const isLight = document.body.classList.contains('theme-light');
        const bgColor = isLight ? '#FFFFFF' : '#151924';
        const textColor = isLight ? '#0F172A' : '#D1D4DC';
        const gridColor = isLight ? '#F1F5F9' : '#232733';

        // 1. Portfolio Equity & Benchmark Chart Container
        const equityContainer = document.getElementById('portfolio-equity-chart');
        if (equityContainer) {
            equityContainer.innerHTML = '';
            const width = equityContainer.clientWidth || 800;

            this.equityChart = LightweightCharts.createChart(equityContainer, {
                width: width,
                height: 320,
                layout: {
                    background: { color: bgColor },
                    textColor: textColor,
                    fontFamily: 'Inter, sans-serif'
                },
                grid: {
                    vertLines: { color: gridColor },
                    horzLines: { color: gridColor }
                },
                rightPriceScale: {
                    borderColor: gridColor,
                    scaleMargins: { top: 0.1, bottom: 0.1 }
                },
                timeScale: {
                    borderColor: gridColor,
                    timeVisible: true
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal
                }
            });

            // Primary Line: Portfolio Equity (Teal #00E676)
            this.equitySeries = this.equityChart.addAreaSeries({
                topColor: 'rgba(0, 230, 118, 0.45)',
                bottomColor: 'rgba(0, 230, 118, 0.02)',
                lineColor: '#00E676',
                lineWidth: 2,
                priceFormat: {
                    type: 'price',
                    precision: 2,
                    minMove: 0.01
                }
            });

            // Benchmark Line: NIFTY 50 Benchmark Buy & Hold (Blue #2962FF)
            this.benchmarkSeries = this.equityChart.addLineSeries({
                color: '#2962FF',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceFormat: {
                    type: 'price',
                    precision: 2,
                    minMove: 0.01
                }
            });

            if (portfolioCurve && portfolioCurve.length > 0) {
                const eqData = portfolioCurve.map(pt => ({
                    time: pt.timestamp,
                    value: pt.equity
                }));
                this.equitySeries.setData(eqData);
            }

            if (benchmarkCurve && benchmarkCurve.length > 0) {
                const bmData = benchmarkCurve.map(pt => ({
                    time: pt.timestamp,
                    value: pt.value
                }));
                this.benchmarkSeries.setData(bmData);
            }

            this.equityChart.timeScale().fitContent();

            // Crosshair Legend Sync
            this.equityChart.subscribeCrosshairMove(param => {
                const legEq = document.getElementById('port-leg-equity-val');
                const legBm = document.getElementById('port-leg-bm-val');
                if (!param || !param.time) {
                    if (legEq) legEq.textContent = '--';
                    if (legBm) legBm.textContent = '--';
                    return;
                }
                if (legEq && this.equitySeries) {
                    const price = param.seriesPrices.get(this.equitySeries);
                    if (price !== undefined) {
                        legEq.textContent = `₹${Number(price.toFixed(2)).toLocaleString('en-IN')}`;
                    }
                }
                if (legBm && this.benchmarkSeries) {
                    const bmPrice = param.seriesPrices.get(this.benchmarkSeries);
                    if (bmPrice !== undefined) {
                        legBm.textContent = `₹${Number(bmPrice.toFixed(2)).toLocaleString('en-IN')}`;
                    }
                }
            });
        }

        // 2. Underwater Portfolio Drawdown Chart Container
        const ddContainer = document.getElementById('portfolio-drawdown-chart');
        if (ddContainer) {
            ddContainer.innerHTML = '';
            const width = ddContainer.clientWidth || 800;

            this.drawdownChart = LightweightCharts.createChart(ddContainer, {
                width: width,
                height: 150,
                layout: {
                    background: { color: bgColor },
                    textColor: textColor,
                    fontFamily: 'Inter, sans-serif'
                },
                grid: {
                    vertLines: { color: gridColor },
                    horzLines: { color: gridColor }
                },
                rightPriceScale: {
                    borderColor: gridColor,
                    scaleMargins: { top: 0.05, bottom: 0.1 }
                },
                timeScale: {
                    borderColor: gridColor,
                    timeVisible: true
                }
            });

            // Underwater Drawdown (Coral #FF5252)
            this.drawdownSeries = this.drawdownChart.addAreaSeries({
                topColor: 'rgba(255, 82, 82, 0.02)',
                bottomColor: 'rgba(255, 82, 82, 0.45)',
                lineColor: '#FF5252',
                lineWidth: 2,
                priceFormat: {
                    type: 'custom',
                    formatter: val => `${val.toFixed(2)}%`
                }
            });

            if (portfolioCurve && portfolioCurve.length > 0) {
                let peak = portfolioCurve[0].equity;
                const ddData = portfolioCurve.map(pt => {
                    if (pt.equity > peak) peak = pt.equity;
                    const dd = peak > 0 ? ((pt.equity - peak) / peak) * 100 : 0;
                    return {
                        time: pt.timestamp,
                        value: Math.min(0, dd)
                    };
                });
                this.drawdownSeries.setData(ddData);
            }

            this.drawdownChart.timeScale().fitContent();

            // Crosshair sync on drawdown
            this.drawdownChart.subscribeCrosshairMove(param => {
                const legDd = document.getElementById('port-leg-dd-val');
                if (!legDd) return;
                if (!param || !param.time) {
                    legDd.textContent = '0.00%';
                    return;
                }
                const val = param.seriesPrices.get(this.drawdownSeries);
                if (val !== undefined) {
                    legDd.textContent = `${val.toFixed(2)}%`;
                }
            });

            // Synchronize timescales
            this.equityChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (this.drawdownChart && range) {
                    this.drawdownChart.timeScale().setVisibleLogicalRange(range);
                }
            });
            this.drawdownChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (this.equityChart && range) {
                    this.equityChart.timeScale().setVisibleLogicalRange(range);
                }
            });
        }
    }

    /**
     * Resizes Lightweight Charts smoothly to match container dimensions.
     */
    resizeCharts() {
        requestAnimationFrame(() => {
            const eqContainer = document.getElementById('portfolio-equity-chart');
            if (this.equityChart && eqContainer) {
                const w = eqContainer.clientWidth;
                if (w > 0) this.equityChart.applyOptions({ width: w });
            }
            const ddContainer = document.getElementById('portfolio-drawdown-chart');
            if (this.drawdownChart && ddContainer) {
                const w = ddContainer.clientWidth;
                if (w > 0) this.drawdownChart.applyOptions({ width: w });
            }
        });
    }

    /**
     * Populates the Asset Contribution Breakdown table.
     * @param {Array<{symbol: string, trade_count: number, win_rate: number, net_pnl: number, alpha_contribution_pct: number}>} contributions
     */
    renderAssetContributionTable(contributions) {
        const tbody = document.getElementById('tbody-asset-contributions');
        const countBadge = document.getElementById('portfolio-contrib-count');
        if (countBadge) countBadge.textContent = contributions ? contributions.length : 0;
        if (!tbody) return;

        if (!contributions || contributions.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center p-4 text-muted">No asset contributions recorded for this basket backtest.</td></tr>`;
            return;
        }

        // Filter by search term
        let list = [...contributions];
        if (this.contribSearchTerm) {
            list = list.filter(c => c.symbol.toUpperCase().includes(this.contribSearchTerm));
        }

        // Sort by active sort key
        list.sort((a, b) => {
            let valA = a[this.contribSortKey];
            let valB = b[this.contribSortKey];
            if (typeof valA === 'string') {
                return this.contribSortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
            }
            return this.contribSortAsc ? (valA - valB) : (valB - valA);
        });

        // Find max absolute net_pnl for normalizing visual impact bars
        const maxAbsPnl = Math.max(...contributions.map(c => Math.abs(c.net_pnl || 0)), 1);

        let html = '';
        list.forEach(item => {
            const isProfit = item.net_pnl >= 0;
            const sign = isProfit ? '+' : '';
            const pnlFormatted = `${sign}₹${Number((item.net_pnl || 0).toFixed(2)).toLocaleString('en-IN')}`;
            const alphaFormatted = `${item.alpha_contribution_pct >= 0 ? '+' : ''}${(item.alpha_contribution_pct || 0).toFixed(2)}%`;
            const winRateFormatted = `${((item.win_rate || 0) * 100).toFixed(1)}%`;

            // Percentage bar width
            const barPct = Math.min(100, Math.max(4, Math.round((Math.abs(item.net_pnl) / maxAbsPnl) * 100)));
            const barClass = isProfit ? 'bar-gain' : 'bar-loss';

            html += `
                <tr>
                    <td class="font-bold">
                        <span class="symbol-ticker-pill">${item.symbol}</span>
                    </td>
                    <td class="text-center font-mono">${item.trade_count}</td>
                    <td class="text-center font-mono ${item.win_rate >= 0.5 ? 'text-green' : 'text-amber'}">${winRateFormatted}</td>
                    <td class="text-right font-mono ${isProfit ? 'text-green' : 'text-red'} font-bold">${pnlFormatted}</td>
                    <td class="text-right font-mono ${item.alpha_contribution_pct >= 0 ? 'text-green' : 'text-red'}">${alphaFormatted}</td>
                    <td>
                        <div class="contribution-bar-wrap" title="${pnlFormatted} (${alphaFormatted})">
                            <div class="contribution-bar ${barClass}" style="width: ${barPct}%;"></div>
                        </div>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    /**
     * Renders Monthly & Yearly Returns Heatmap Matrix.
     * @param {Object} monthlyReturns { "2020": { "1": 0.02, "2": -0.01, ... } }
     */
    renderPortfolioHeatmap(monthlyReturns) {
        const container = document.getElementById('portfolio-monthly-heatmap-container');
        if (!container) return;

        const years = Object.keys(monthlyReturns).sort();
        if (years.length === 0) {
            container.innerHTML = `<div class="p-4 text-center text-muted">No monthly return data generated.</div>`;
            return;
        }

        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        let tableHtml = `
            <table class="quant-table heatmap-matrix-table">
                <thead>
                    <tr>
                        <th>Year</th>
                        ${months.map(m => `<th class="text-center">${m}</th>`).join('')}
                        <th class="text-center font-bold">Year Total</th>
                    </tr>
                </thead>
                <tbody>
        `;

        years.forEach(yr => {
            const yrData = monthlyReturns[yr] || {};
            let yearTotal = 1.0;

            let rowHtml = `<tr><td class="font-bold font-mono">${yr}</td>`;

            for (let m = 1; m <= 12; m++) {
                const ret = yrData[m] !== undefined ? yrData[m] : (yrData[String(m)] !== undefined ? yrData[String(m)] : null);
                if (ret === null) {
                    rowHtml += `<td class="text-center text-muted font-mono cell-na">-</td>`;
                } else {
                    yearTotal *= (1.0 + ret);
                    const pct = (ret * 100).toFixed(1);
                    let cellClass = 'cell-gain-low';
                    if (ret > 0.05) cellClass = 'cell-gain-high';
                    else if (ret >= 0) cellClass = 'cell-gain-low';
                    else if (ret < -0.05) cellClass = 'cell-loss-high';
                    else cellClass = 'cell-loss-low';

                    rowHtml += `<td class="text-center font-mono ${cellClass}">${pct >= 0 ? '+' : ''}${pct}%</td>`;
                }
            }

            const yrPct = ((yearTotal - 1.0) * 100).toFixed(1);
            const yrClass = yrPct >= 0 ? 'text-green font-bold' : 'text-red font-bold';
            rowHtml += `<td class="text-center font-mono ${yrClass}">${yrPct >= 0 ? '+' : ''}${yrPct}%</td></tr>`;
            tableHtml += rowHtml;
        });

        tableHtml += '</tbody></table>';
        container.innerHTML = tableHtml;
    }

    /**
     * Populates the combined chronological trade ledger.
     * @param {Array<Object>} trades
     */
    renderPortfolioTradeLedger(trades) {
        const tbody = document.getElementById('portfolio-trades-table-body');
        const countBadge = document.getElementById('portfolio-trades-count');
        const pillAll = document.getElementById('port-pill-all-count');
        const pillWin = document.getElementById('port-pill-win-count');
        const pillLoss = document.getElementById('port-pill-loss-count');

        if (!trades) trades = [];

        const winCount = trades.filter(t => (t.net_pnl || 0) > 0).length;
        const lossCount = trades.filter(t => (t.net_pnl || 0) <= 0).length;

        if (countBadge) countBadge.textContent = trades.length;
        if (pillAll) pillAll.textContent = trades.length;
        if (pillWin) pillWin.textContent = winCount;
        if (pillLoss) pillLoss.textContent = lossCount;

        if (!tbody) return;

        if (trades.length === 0) {
            tbody.innerHTML = `<tr><td colspan="14" class="text-center p-4 text-muted">No basket trades recorded.</td></tr>`;
            return;
        }

        // Filter trades
        let list = [...trades];
        if (this.tradesFilter === 'WIN') {
            list = list.filter(t => (t.net_pnl || 0) > 0);
        } else if (this.tradesFilter === 'LOSS') {
            list = list.filter(t => (t.net_pnl || 0) <= 0);
        }

        if (this.tradesSearchTerm) {
            list = list.filter(t => (t.symbol || '').toUpperCase().includes(this.tradesSearchTerm));
        }

        let html = '';
        list.forEach((t, i) => {
            const isProfit = (t.net_pnl || 0) >= 0;
            const sign = isProfit ? '+' : '';
            const netFormatted = `${sign}₹${Number((t.net_pnl || 0).toFixed(2)).toLocaleString('en-IN')}`;
            const retFormatted = `${sign}${(t.return_pct || 0).toFixed(2)}%`;
            const feesFormatted = `₹${Number((t.taxes_and_fees || 0).toFixed(2)).toLocaleString('en-IN')}`;
            const grossFormatted = `₹${Number((t.gross_pnl || 0).toFixed(2)).toLocaleString('en-IN')}`;

            html += `
                <tr>
                    <td class="font-mono text-muted">${i + 1}</td>
                    <td class="font-bold"><span class="symbol-ticker-pill">${t.symbol}</span></td>
                    <td class="font-mono">${t.entry_date || '--'}</td>
                    <td class="font-mono">${t.exit_date || '--'}</td>
                    <td><span class="side-tag ${t.side === 'BUY' ? 'tag-buy' : 'tag-sell'}">${t.side}</span></td>
                    <td class="text-right font-mono">₹${Number((t.entry_price || 0).toFixed(2)).toLocaleString('en-IN')}</td>
                    <td class="text-right font-mono">₹${Number((t.exit_price || 0).toFixed(2)).toLocaleString('en-IN')}</td>
                    <td class="text-right font-mono">${t.quantity || 0}</td>
                    <td class="text-right font-mono">${grossFormatted}</td>
                    <td class="text-right font-mono text-amber">${feesFormatted}</td>
                    <td class="text-right font-mono ${isProfit ? 'text-green' : 'text-red'} font-bold">${netFormatted}</td>
                    <td class="text-right font-mono ${isProfit ? 'text-green' : 'text-red'}">${retFormatted}</td>
                    <td><span class="reason-badge">${t.exit_reason || 'SIGNAL'}</span></td>
                    <td class="text-center font-mono">${t.holding_days || 1}d</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    /**
     * Exports combined basket trade ledger to CSV.
     */
    exportPortfolioTradesCSV() {
        if (!this.portfolioResult || !this.portfolioResult.trades || this.portfolioResult.trades.length === 0) {
            alert('No trades available to export.');
            return;
        }

        const trades = this.portfolioResult.trades;
        const headers = ['#', 'Symbol', 'Entry Date', 'Exit Date', 'Side', 'Entry Price', 'Exit Price', 'Quantity', 'Gross PnL', 'Taxes & Fees', 'Net PnL', 'Return %', 'Exit Reason', 'Holding Days'];

        const rows = trades.map((t, idx) => [
            idx + 1,
            `"${t.symbol}"`,
            t.entry_date,
            t.exit_date,
            t.side,
            t.entry_price,
            t.exit_price,
            t.quantity,
            t.gross_pnl,
            t.taxes_and_fees,
            t.net_pnl,
            t.return_pct,
            `"${t.exit_reason || 'SIGNAL'}"`,
            t.holding_days || 1
        ]);

        const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `portfolio_basket_trades_${this.selectedUniverse}_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Expose on window
window.PortfolioBacktestController = PortfolioBacktestController;

// Expose switchMode on BacktestUI prototype if not already defined
if (typeof BacktestUI !== 'undefined' && !BacktestUI.prototype.switchMode) {
    BacktestUI.prototype.switchMode = function(mode) {
        if (!this.portfolioController) {
            this.portfolioController = new PortfolioBacktestController(this);
        }
        return this.portfolioController.switchMode(mode);
    };
}

