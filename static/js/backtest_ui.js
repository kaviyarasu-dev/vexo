/**
 * Quant Backtest Studio & Strategy Tester
 * Built to TradingView Strategy Tester & Zerodha Streak Standards
 */
class BacktestUI {
    constructor(containerId = 'backtest-workspace-container') {
        this.container = document.getElementById(containerId) || document.getElementById('backtest-app');
        this.activeStrategy = 'SMA_CROSS';
        this.activeSubtab = 'overview';
        this.tradeFilter = 'ALL';
        this.result = null;
        this.equityChart = null;
        this.drawdownChart = null;
        this.equitySeries = null;
        this.benchmarkSeries = null;
        this.drawdownSeries = null;

        // Universe Scan State
        this.currentMatches = [];
        this.pastMatches = [];
        this.isScanning = false;
        this.currentSignalFilter = 'ALL';
        this.currentSearchTerm = '';
        this.pastSearchTerm = '';
        this.pastSortKey = 'win_rate';
        this.pastSortAsc = false;

        // Default Configuration
        this.config = {
            strategy: 'SMA_CROSS',
            symbol: 'NSE:RELIANCE-EQ',
            timeframe: '1D',
            start_date: '2020-01-01',
            end_date: '2023-12-31',
            initial_capital: 1000000,
            trade_type: 'DELIVERY',
            slippage_bps: 5.0,
            stop_loss_pct: 3.0,
            take_profit_pct: 8.0,
            position_size_type: 'PERCENT_CAPITAL',
            position_size_val: 100.0,
            parameters: {
                short_window: 20,
                long_window: 50
            }
        };

        this.init();
    }

    init() {
        if (!this.container) return;
        this.renderStudio();
        this.bindEvents();
        // Automatically run initial backtest and scan universe
        this.runBacktest();
        this.scanUniverse();
    }

    renderStudio() {
        this.container.innerHTML = `
            <div class="backtest-studio-wrapper">
                <!-- Studio Header -->
                <div class="backtest-studio-header">
                    <div class="header-left">
                        <div class="header-title-badge">
                            <span class="studio-icon">🧪</span>
                            <h2>Quant Backtest Studio</h2>
                            <span class="badge-pro">PRO SUITE</span>
                        </div>
                        <p class="studio-subtitle">TradingView Strategy Tester & Zerodha Streak Quantitative Rule Engine with Indian Statutory Cost Model</p>
                    </div>
                    <div class="header-right">
                        <div class="status-chip" id="studio-status-chip">
                            <span class="status-dot"></span>
                            <span id="studio-status-text">Engine Ready</span>
                        </div>
                    </div>
                </div>

                <!-- Main Split Studio Grid -->
                <div class="backtest-studio-grid">
                    <!-- LEFT COLUMN: Configurator Panel -->
                    <aside class="backtest-config-panel">
                        <!-- 1. Strategy Selector -->
                        <div class="config-card">
                            <div class="config-card-header">
                                <span class="step-num">1</span>
                                <h3>Select Strategy</h3>
                            </div>
                            <div class="strategy-list" id="strategy-cards-container">
                                <div class="strategy-card active" data-strategy="SMA_CROSS">
                                    <div class="strategy-card-top">
                                        <span class="strategy-name">SMA Crossover</span>
                                        <span class="badge-tag badge-trend">Trend Following</span>
                                    </div>
                                    <p class="strategy-desc">Buys when Fast SMA crosses above Slow SMA; sells on reverse cross.</p>
                                </div>
                                <div class="strategy-card" data-strategy="RSI_REVERSION">
                                    <div class="strategy-card-top">
                                        <span class="strategy-name">RSI Reversal</span>
                                        <span class="badge-tag badge-meanrev">Mean Reversion</span>
                                    </div>
                                    <p class="strategy-desc">Enters on oversold bounce (RSI &lt; 30) and exits on overbought peak (RSI &gt; 70).</p>
                                </div>
                                <div class="strategy-card" data-strategy="BOLLINGER_BANDS">
                                    <div class="strategy-card-top">
                                        <span class="strategy-name">Bollinger Bands</span>
                                        <span class="badge-tag badge-volatility">Volatility</span>
                                    </div>
                                    <p class="strategy-desc">Mean reversion buying at the Lower Band and taking profit at the Upper Band.</p>
                                </div>
                                <div class="strategy-card" data-strategy="SUPERTREND">
                                    <div class="strategy-card-top">
                                        <span class="strategy-name">Supertrend</span>
                                        <span class="badge-tag badge-trend">Trend Following</span>
                                    </div>
                                    <p class="strategy-desc">ATR trailing band capturing prolonged breakouts and directional trends.</p>
                                </div>
                                <div class="strategy-card" data-strategy="MACD">
                                    <div class="strategy-card-top">
                                        <span class="strategy-name">MACD Momentum</span>
                                        <span class="badge-tag badge-momentum">Momentum</span>
                                    </div>
                                    <p class="strategy-desc">Generates signals on MACD line crossing the 9-day Signal EMA.</p>
                                </div>
                            </div>
                        </div>

                        <!-- 2. Dynamic Strategy Parameters -->
                        <div class="config-card">
                            <div class="config-card-header">
                                <span class="step-num">2</span>
                                <h3>Strategy Parameters</h3>
                            </div>
                            <div id="dynamic-params-container" class="params-fields-box">
                                <!-- Rendered dynamically based on active strategy -->
                            </div>
                        </div>

                        <!-- 3. Asset & Timeframe -->
                        <div class="config-card">
                            <div class="config-card-header">
                                <span class="step-num">3</span>
                                <h3>Asset & Timeframe</h3>
                            </div>
                            <div class="form-group mb-2">
                                <label class="field-label">Quick Select Stock</label>
                                <div class="quick-chips-group">
                                    <button type="button" class="chip-btn active" data-symbol="NSE:RELIANCE-EQ">RELIANCE</button>
                                    <button type="button" class="chip-btn" data-symbol="NSE:TCS-EQ">TCS</button>
                                    <button type="button" class="chip-btn" data-symbol="NSE:INFY-EQ">INFY</button>
                                    <button type="button" class="chip-btn" data-symbol="NSE:HDFCBANK-EQ">HDFCBANK</button>
                                    <button type="button" class="chip-btn" data-symbol="NSE:NIFTY50-INDEX">NIFTY50</button>
                                </div>
                            </div>

                            <div class="form-group mb-2">
                                <label class="field-label" for="bt-symbol-input">Trading Symbol</label>
                                <input type="text" id="bt-symbol-input" class="studio-input font-mono" value="NSE:RELIANCE-EQ" placeholder="e.g. NSE:RELIANCE-EQ">
                            </div>

                            <div class="form-row-2 mb-2">
                                <div class="form-group">
                                    <label class="field-label" for="bt-timeframe-select">Candle Timeframe</label>
                                    <select id="bt-timeframe-select" class="studio-select">
                                        <option value="1D" selected>1 Day (Daily)</option>
                                        <option value="1h">1 Hour</option>
                                        <option value="15m">15 Minutes</option>
                                        <option value="5m">5 Minutes</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="field-label">Date Preset</label>
                                    <div class="pill-group" id="bt-date-presets">
                                        <button type="button" class="pill-btn" data-preset="1Y">1Y</button>
                                        <button type="button" class="pill-btn active" data-preset="3Y">3Y</button>
                                        <button type="button" class="pill-btn" data-preset="5Y">5Y</button>
                                    </div>
                                </div>
                            </div>

                            <div class="form-row-2">
                                <div class="form-group">
                                    <label class="field-label" for="bt-start-date">Start Date</label>
                                    <input type="date" id="bt-start-date" class="studio-input" value="2020-01-01">
                                </div>
                                <div class="form-group">
                                    <label class="field-label" for="bt-end-date">End Date</label>
                                    <input type="date" id="bt-end-date" class="studio-input" value="2023-12-31">
                                </div>
                            </div>
                        </div>

                        <!-- 4. Risk & Position Sizing Rules -->
                        <div class="config-card">
                            <div class="config-card-header">
                                <span class="step-num">4</span>
                                <h3>Risk & Sizing Rules</h3>
                            </div>
                            <div class="form-row-2 mb-2">
                                <div class="form-group">
                                    <label class="field-label" for="bt-stop-loss">Stop Loss (%)</label>
                                    <div class="input-with-unit">
                                        <input type="number" id="bt-stop-loss" class="studio-input" value="3.0" step="0.5" min="0" max="50">
                                        <span class="unit-tag">%</span>
                                    </div>
                                </div>
                                <div class="form-group">
                                    <label class="field-label" for="bt-take-profit">Take Profit (%)</label>
                                    <div class="input-with-unit">
                                        <input type="number" id="bt-take-profit" class="studio-input" value="8.0" step="0.5" min="0" max="100">
                                        <span class="unit-tag">%</span>
                                    </div>
                                </div>
                            </div>

                            <div class="form-row-2">
                                <div class="form-group">
                                    <label class="field-label" for="bt-size-type">Position Sizing</label>
                                    <select id="bt-size-type" class="studio-select">
                                        <option value="PERCENT_CAPITAL" selected>% of Capital</option>
                                        <option value="FIXED_AMOUNT">Fixed Amount (₹)</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="field-label" for="bt-size-val">Sizing Value</label>
                                    <input type="number" id="bt-size-val" class="studio-input font-mono" value="100" min="1">
                                </div>
                            </div>
                        </div>

                        <!-- 5. Capital & Indian Cost Engine -->
                        <div class="config-card">
                            <div class="config-card-header">
                                <span class="step-num">5</span>
                                <h3>Capital & Statutory Costs</h3>
                            </div>
                            <div class="form-group mb-2">
                                <label class="field-label" for="bt-initial-capital">Initial Capital (₹)</label>
                                <div class="input-with-unit">
                                    <span class="unit-prefix">₹</span>
                                    <input type="number" id="bt-initial-capital" class="studio-input font-mono" value="1000000" step="50000">
                                </div>
                                <div class="capital-quick-chips mt-1">
                                    <button type="button" class="chip-mini" data-cap="100000">₹1L</button>
                                    <button type="button" class="chip-mini" data-cap="500000">₹5L</button>
                                    <button type="button" class="chip-mini active" data-cap="1000000">₹10L</button>
                                    <button type="button" class="chip-mini" data-cap="2500000">₹25L</button>
                                </div>
                            </div>

                            <div class="form-row-2 mb-2">
                                <div class="form-group">
                                    <label class="field-label" for="bt-trade-type">Trade Execution Type</label>
                                    <select id="bt-trade-type" class="studio-select">
                                        <option value="DELIVERY" selected>Delivery (CNC)</option>
                                        <option value="INTRADAY">Intraday (MIS)</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="field-label">Brokerage Model</label>
                                    <div class="broker-badge">
                                        <span class="broker-icon">🛡️</span>
                                        <span>Zerodha ₹20 / Flat</span>
                                    </div>
                                </div>
                            </div>

                            <div class="form-group">
                                <div class="slider-header">
                                    <label class="field-label" for="bt-slippage-slider">Execution Slippage</label>
                                    <span class="slider-value font-mono" id="bt-slippage-display">5 bps</span>
                                </div>
                                <input type="range" id="bt-slippage-slider" class="studio-range" min="0" max="25" step="1" value="5">
                            </div>
                        </div>

                        <!-- 6. Action Button -->
                        <div class="action-card">
                            <button type="button" id="btn-run-studio-backtest" class="btn-run-backtest">
                                <span class="btn-icon">🚀</span>
                                <span class="btn-text">Run Strategy Backtest</span>
                            </button>
                        </div>
                    </aside>

                    <!-- RIGHT COLUMN: Studio Results Dashboard -->
                    <main class="backtest-results-panel">
                        <!-- 1. CURRENT MATCH TABLE SECTION -->
                        <section class="studio-universe-section" id="section-current-matches">
                            <div class="studio-section-header">
                                <div class="section-header-left">
                                    <span class="section-header-icon pulse-live">⚡</span>
                                    <div class="section-header-title-box">
                                        <h3 class="section-title">Current Match Table</h3>
                                        <span class="section-subtitle">Stocks matching active <strong id="current-matches-strat-name">SMA Crossover</strong> signals</span>
                                    </div>
                                    <span class="badge-count" id="badge-current-matches-count">0 Signals</span>
                                </div>
                                <div class="section-header-right">
                                    <div class="pill-filter-group" id="current-matches-filter-group">
                                        <button type="button" class="filter-chip active" data-signal-filter="ALL">All</button>
                                        <button type="button" class="filter-chip chip-buy" data-signal-filter="BUY">BUY</button>
                                        <button type="button" class="filter-chip chip-sell" data-signal-filter="SELL">SELL</button>
                                    </div>
                                    <div class="search-input-wrapper">
                                        <input type="text" id="input-search-current-matches" class="table-search-input" placeholder="Filter symbol...">
                                    </div>
                                    <button type="button" id="btn-refresh-matches-scan" class="btn-refresh-scan" title="Rescan Universe">
                                        <span class="refresh-icon">🔄</span> Rescan
                                    </button>
                                    <button type="button" id="btn-toggle-current-table" class="btn-toggle-collapse" title="Collapse/Expand">▼</button>
                                </div>
                            </div>
                            <div class="studio-section-content" id="content-current-matches">
                                <div class="table-container">
                                    <table class="quant-table" id="table-current-matches">
                                        <thead>
                                            <tr>
                                                <th class="th-stock">Stock / Symbol</th>
                                                <th class="th-signal text-center">Signal</th>
                                                <th class="th-trigger-time">Triggered</th>
                                                <th class="th-price text-right">Trigger Price</th>
                                                <th class="th-price text-right">Current Price</th>
                                                <th class="th-move text-right">Move %</th>
                                                <th class="th-reason">Signal Context</th>
                                                <th class="th-action text-center">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody id="tbody-current-matches">
                                            <tr>
                                                <td colspan="8" class="text-center p-4 text-muted">Scanning universe for active signals...</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <div class="table-empty-box d-none" id="empty-current-matches">
                                    <span class="empty-icon">🔎</span>
                                    <p class="empty-title">No Fresh Signals in Latest Sessions</p>
                                    <p class="empty-desc">No stocks have fresh entry/exit triggers on the latest candles for this strategy. Check past match table below or adjust strategy parameters.</p>
                                </div>
                            </div>
                        </section>

                        <!-- 2. PAST MATCH TABLE SECTION -->
                        <section class="studio-universe-section" id="section-past-matches">
                            <div class="studio-section-header">
                                <div class="section-header-left">
                                    <span class="section-header-icon">📊</span>
                                    <div class="section-header-title-box">
                                        <h3 class="section-title">Past Match Table</h3>
                                        <span class="section-subtitle">Win/Loss track record &amp; Net Return for <strong id="past-matches-strat-name">SMA Crossover</strong> across all stocks</span>
                                    </div>
                                    <span class="badge-count" id="badge-past-matches-count">0 Stocks Scanned</span>
                                </div>
                                <div class="section-header-right">
                                    <div class="search-input-wrapper">
                                        <input type="text" id="input-search-past-matches" class="table-search-input" placeholder="Search stocks...">
                                    </div>
                                    <div class="sort-select-wrapper">
                                        <label>Sort:</label>
                                        <select id="select-past-sort" class="sort-select">
                                            <option value="win_rate" selected>Win Rate (%)</option>
                                            <option value="net_pnl">Net Return (₹)</option>
                                            <option value="total_trades">Total Trades</option>
                                            <option value="profit_factor">Profit Factor</option>
                                            <option value="symbol">Symbol A-Z</option>
                                        </select>
                                    </div>
                                    <button type="button" id="btn-toggle-past-table" class="btn-toggle-collapse" title="Collapse/Expand">▼</button>
                                </div>
                            </div>
                            <div class="studio-section-content" id="content-past-matches">
                                <div class="table-container">
                                    <table class="quant-table" id="table-past-matches">
                                        <thead>
                                            <tr>
                                                <th class="th-sortable" data-sort-key="symbol">Stock Name / Symbol <span class="sort-arrow">↕</span></th>
                                                <th class="th-sortable text-center" data-sort-key="total_trades">Trades <span class="sort-arrow">↕</span></th>
                                                <th class="th-sortable text-center" data-sort-key="win_count">Wins <span class="sort-arrow">↕</span></th>
                                                <th class="th-sortable text-center" data-sort-key="loss_count">Losses <span class="sort-arrow">↕</span></th>
                                                <th class="th-sortable" data-sort-key="win_rate" style="min-width: 140px;">Win Rate % <span class="sort-arrow">↕</span></th>
                                                <th class="th-sortable text-right" data-sort-key="net_pnl">Net Return (₹ / %) <span class="sort-arrow">↕</span></th>
                                                <th class="th-sortable text-right" data-sort-key="profit_factor">Profit Factor <span class="sort-arrow">↕</span></th>
                                                <th class="th-action text-center">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody id="tbody-past-matches">
                                            <tr>
                                                <td colspan="8" class="text-center p-4 text-muted">Calculating historical win/loss matrix across universe...</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </section>

                        <!-- 3. CURRENT VIEW (Detailed Single-Stock Studio) -->
                        <section class="studio-current-view-section" id="section-current-view">
                            <div class="current-view-title-bar">
                                <div class="view-title-left">
                                    <span class="section-header-icon">🎯</span>
                                    <div>
                                        <h3 class="current-view-title">Current View: Detailed Stock Backtest</h3>
                                        <span class="current-view-subtitle">Interactive Performance Dashboard, Equity Curves, and Trade Ledger</span>
                                    </div>
                                </div>
                                <div class="current-view-stock-indicator">
                                    <span class="active-stock-tag" id="current-view-active-stock">NSE:RELIANCE-EQ</span>
                                </div>
                            </div>

                            <!-- Results Top Bar -->
                            <div class="results-header-bar">
                            <div class="results-meta-tags">
                                <div class="meta-tag" id="meta-strategy-tag">Strategy: <strong>SMA Crossover</strong></div>
                                <div class="meta-tag" id="meta-symbol-tag">Asset: <strong>NSE:RELIANCE-EQ</strong></div>
                                <div class="meta-tag" id="meta-period-tag">Period: <strong>2020 - 2023</strong></div>
                                <div class="meta-tag" id="meta-capital-tag">Capital: <strong>₹10,00,000</strong></div>
                            </div>
                            <div class="results-pnl-badge" id="results-headline-pnl">
                                <span class="pnl-title">Net Return:</span>
                                <span class="pnl-val text-green font-mono" id="headline-net-pnl">+₹0.00 (+0.00%)</span>
                            </div>
                        </div>

                        <!-- Studio Sub-Navigation Tabs -->
                        <div class="results-subtabs">
                            <button type="button" class="subtab-btn active" data-subtab="overview">
                                <span>📊</span> Overview &amp; Equity Curve
                            </button>
                            <button type="button" class="subtab-btn" data-subtab="summary">
                                <span>📈</span> Performance Summary &amp; Heatmap
                            </button>
                            <button type="button" class="subtab-btn" data-subtab="trades">
                                <span>📜</span> List of Trades (<span id="tab-trades-count">0</span>)
                            </button>
                        </div>

                        <!-- SUBTAB 1: Overview & Interactive Charts -->
                        <div class="subtab-content" id="subtab-overview">
                            <!-- 8 Primary Metric Cards -->
                            <div class="metrics-dashboard-grid">
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">CAGR</span>
                                        <span class="m-icon">🎯</span>
                                    </div>
                                    <div class="m-value font-mono" id="m-cagr">--%</div>
                                    <div class="m-sub">Compounded Annual Return</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Net Profit</span>
                                        <span class="m-icon">💰</span>
                                    </div>
                                    <div class="m-value font-mono" id="m-net-pnl">--</div>
                                    <div class="m-sub" id="m-gross-pnl">Gross: --</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Max Drawdown</span>
                                        <span class="m-icon">📉</span>
                                    </div>
                                    <div class="m-value font-mono text-red" id="m-max-dd">--%</div>
                                    <div class="m-sub">Peak to Valley Decline</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Win Rate</span>
                                        <span class="m-icon">🏆</span>
                                    </div>
                                    <div class="m-value font-mono" id="m-win-rate">--%</div>
                                    <div class="m-sub" id="m-win-loss-count">0 Wins / 0 Losses</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Profit Factor</span>
                                        <span class="m-icon">⚖️</span>
                                    </div>
                                    <div class="m-value font-mono" id="m-profit-factor">--</div>
                                    <div class="m-sub">Gross Wins / Gross Losses</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Sharpe Ratio</span>
                                        <span class="m-icon">📐</span>
                                    </div>
                                    <div class="m-value font-mono" id="m-sharpe">--</div>
                                    <div class="m-sub">Risk-Adjusted Return</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Taxes &amp; Fees</span>
                                        <span class="m-icon">🏛️</span>
                                    </div>
                                    <div class="m-value font-mono text-amber" id="m-fees">₹0</div>
                                    <div class="m-sub">STT, GST, Stamp &amp; Zerodha</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-top">
                                        <span class="m-label">Sortino Ratio</span>
                                        <span class="m-icon">🛡️</span>
                                    </div>
                                    <div class="m-value font-mono" id="m-sortino">--</div>
                                    <div class="m-sub">Downside Risk Ratio</div>
                                </div>
                            </div>

                            <!-- Interactive TradingView Lightweight Charts -->
                            <div class="charts-suite">
                                <!-- Equity & Benchmark Chart -->
                                <div class="chart-container-box">
                                    <div class="chart-box-header">
                                        <div class="chart-title-left">
                                            <span class="chart-bullet bullet-strategy"></span>
                                            <span class="chart-name">Strategy Equity Curve</span>
                                            <span class="chart-bullet bullet-benchmark ml-2"></span>
                                            <span class="chart-name text-muted">Buy &amp; Hold Benchmark</span>
                                        </div>
                                        <div class="chart-live-legend font-mono" id="equity-chart-legend">
                                            Strategy: <span id="leg-strat-val" class="text-green font-bold">--</span> | 
                                            Benchmark: <span id="leg-bm-val" class="text-blue">--</span>
                                        </div>
                                    </div>
                                    <div id="bt-equity-chart" class="tv-chart-viewport" style="height: 320px;"></div>
                                </div>

                                <!-- Underwater Drawdown Chart -->
                                <div class="chart-container-box mt-3">
                                    <div class="chart-box-header">
                                        <div class="chart-title-left">
                                            <span class="chart-bullet bullet-drawdown"></span>
                                            <span class="chart-name">Underwater Drawdown (%)</span>
                                        </div>
                                        <div class="chart-live-legend font-mono" id="drawdown-chart-legend">
                                            Drawdown: <span id="leg-dd-val" class="text-red font-bold">0.00%</span>
                                        </div>
                                    </div>
                                    <div id="bt-drawdown-chart" class="tv-chart-viewport" style="height: 150px;"></div>
                                </div>
                            </div>
                        </div>

                        <!-- SUBTAB 2: Performance Summary & Streak Heatmap -->
                        <div class="subtab-content hidden" id="subtab-summary">
                            <div class="summary-section-card">
                                <div class="section-title-row">
                                    <div class="title-with-icon">
                                        <span>📅</span>
                                        <h4>Monthly &amp; Yearly Returns Matrix (Streak Heatmap)</h4>
                                    </div>
                                    <div class="heatmap-legend">
                                        <span class="legend-chip chip-gain-high">&gt; +5%</span>
                                        <span class="legend-chip chip-gain-low">0 to +5%</span>
                                        <span class="legend-chip chip-loss-low">-5% to 0</span>
                                        <span class="legend-chip chip-loss-high">&lt; -5%</span>
                                    </div>
                                </div>
                                <div class="heatmap-table-wrapper" id="monthly-heatmap-container">
                                    <!-- Rendered dynamically -->
                                    <div class="p-4 text-center text-muted">Calculating monthly returns matrix...</div>
                                </div>
                            </div>

                            <!-- Detailed Trade Analytics Breakdown -->
                            <div class="summary-section-card mt-3">
                                <div class="section-title-row">
                                    <div class="title-with-icon">
                                        <span>🔍</span>
                                        <h4>Risk, Win/Loss &amp; Execution Breakdown</h4>
                                    </div>
                                </div>
                                <div class="stats-table-grid">
                                    <div class="stat-row">
                                        <span class="stat-name">Total Completed Trades</span>
                                        <span class="stat-val font-mono" id="stat-total-trades">0</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Winning Trades</span>
                                        <span class="stat-val font-mono text-green" id="stat-win-trades">0</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Losing Trades</span>
                                        <span class="stat-val font-mono text-red" id="stat-loss-trades">0</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Win / Loss Ratio</span>
                                        <span class="stat-val font-mono" id="stat-win-loss-ratio">--</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Largest Winning Trade</span>
                                        <span class="stat-val font-mono text-green" id="stat-max-win">--</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Largest Losing Trade</span>
                                        <span class="stat-val font-mono text-red" id="stat-max-loss">--</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Average Profit per Win</span>
                                        <span class="stat-val font-mono text-green" id="stat-avg-win">--</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Average Loss per Loss</span>
                                        <span class="stat-val font-mono text-red" id="stat-avg-loss">--</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Trade Expectancy (per trade)</span>
                                        <span class="stat-val font-mono" id="stat-expectancy">--</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Average Holding Duration</span>
                                        <span class="stat-val font-mono" id="stat-avg-holding">-- bars</span>
                                    </div>
                                    <div class="stat-row">
                                        <span class="stat-name">Total Market Turnover</span>
                                        <span class="stat-val font-mono" id="stat-turnover">--</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- SUBTAB 3: Trade-by-Trade Log -->
                        <div class="subtab-content hidden" id="subtab-trades">
                            <div class="trades-toolbar">
                                <div class="filter-pills" id="trades-filter-pills">
                                    <button type="button" class="filter-pill active" data-filter="ALL">All Trades (<span id="pill-all-count">0</span>)</button>
                                    <button type="button" class="filter-pill" data-filter="WIN">Winning Only (<span id="pill-win-count">0</span>)</button>
                                    <button type="button" class="filter-pill" data-filter="LOSS">Losing Only (<span id="pill-loss-count">0</span>)</button>
                                </div>
                                <button type="button" id="btn-export-trades-csv" class="btn-export-csv">
                                    <span>📥</span> Export CSV Ledger
                                </button>
                            </div>

                            <div class="trades-table-scroll">
                                <table class="trades-data-table" id="trades-data-table">
                                    <thead>
                                        <tr>
                                            <th>#</th>
                                            <th>Entry Date</th>
                                            <th>Exit Date</th>
                                            <th>Side</th>
                                            <th>Entry Price</th>
                                            <th>Exit Price</th>
                                            <th>Qty</th>
                                            <th>Gross PnL</th>
                                            <th>Taxes &amp; Fees</th>
                                            <th>Net PnL (₹)</th>
                                            <th>Return %</th>
                                            <th>Exit Reason</th>
                                            <th>Held</th>
                                        </tr>
                                    </thead>
                                    <tbody id="trades-table-body">
                                        <tr>
                                            <td colspan="13" class="text-center p-4 text-muted">No trades recorded yet. Run a backtest to populate trade ledger.</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>

                    <!-- Footer: Audit & Disclaimer -->
                        <div class="backtest-footer-audit">
                            <div class="audit-badge">
                                <span>🔒 Tamper-Proof Audit Hash:</span>
                                <code class="font-mono text-cyan" id="audit-hash-display">SHA256-PENDING</code>
                            </div>
                            <p class="sebi-disclaimer-text">
                                <strong>SEBI Statutory Notice:</strong> This backtesting engine is a quantitative research tool for self-directed traders. Past performance computed under hypothetical parameters is not indicative of future market returns. Realized execution may vary due to slippage, liquidity, and exchange matching delays.
                            </p>
                        </div>
                    </main>
                </div>
            </div>
        `;

        this.updateDynamicParams();
    }

    updateDynamicParams() {
        const container = document.getElementById('dynamic-params-container');
        if (!container) return;

        if (this.activeStrategy === 'SMA_CROSS') {
            container.innerHTML = `
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="field-label" for="param-short-window">Fast SMA Window</label>
                        <input type="number" id="param-short-window" class="studio-input font-mono" value="${this.config.parameters.short_window || 20}" min="2" max="200">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-long-window">Slow SMA Window</label>
                        <input type="number" id="param-long-window" class="studio-input font-mono" value="${this.config.parameters.long_window || 50}" min="5" max="500">
                    </div>
                </div>
            `;
        } else if (this.activeStrategy === 'RSI_REVERSION') {
            container.innerHTML = `
                <div class="form-row-3">
                    <div class="form-group">
                        <label class="field-label" for="param-rsi-period">RSI Period</label>
                        <input type="number" id="param-rsi-period" class="studio-input font-mono" value="${this.config.parameters.rsi_period || 14}" min="2" max="100">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-oversold">Oversold (Buy)</label>
                        <input type="number" id="param-oversold" class="studio-input font-mono" value="${this.config.parameters.oversold || 30}" min="5" max="50">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-overbought">Overbought (Sell)</label>
                        <input type="number" id="param-overbought" class="studio-input font-mono" value="${this.config.parameters.overbought || 70}" min="50" max="95">
                    </div>
                </div>
            `;
        } else if (this.activeStrategy === 'BOLLINGER_BANDS') {
            container.innerHTML = `
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="field-label" for="param-bb-period">Band Period</label>
                        <input type="number" id="param-bb-period" class="studio-input font-mono" value="${this.config.parameters.period || 20}" min="5" max="100">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-bb-std">Std Deviation</label>
                        <input type="number" id="param-bb-std" class="studio-input font-mono" value="${this.config.parameters.std_dev || 2.0}" step="0.1" min="0.5" max="5.0">
                    </div>
                </div>
            `;
        } else if (this.activeStrategy === 'SUPERTREND') {
            container.innerHTML = `
                <div class="form-row-2">
                    <div class="form-group">
                        <label class="field-label" for="param-st-period">ATR Period</label>
                        <input type="number" id="param-st-period" class="studio-input font-mono" value="${this.config.parameters.period || 10}" min="3" max="50">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-st-multiplier">Multiplier</label>
                        <input type="number" id="param-st-multiplier" class="studio-input font-mono" value="${this.config.parameters.multiplier || 3.0}" step="0.5" min="1.0" max="10.0">
                    </div>
                </div>
            `;
        } else if (this.activeStrategy === 'MACD') {
            container.innerHTML = `
                <div class="form-row-3">
                    <div class="form-group">
                        <label class="field-label" for="param-macd-fast">Fast EMA</label>
                        <input type="number" id="param-macd-fast" class="studio-input font-mono" value="${this.config.parameters.fast_period || 12}" min="2" max="100">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-macd-slow">Slow EMA</label>
                        <input type="number" id="param-macd-slow" class="studio-input font-mono" value="${this.config.parameters.slow_period || 26}" min="5" max="200">
                    </div>
                    <div class="form-group">
                        <label class="field-label" for="param-macd-sig">Signal EMA</label>
                        <input type="number" id="param-macd-sig" class="studio-input font-mono" value="${this.config.parameters.signal_period || 9}" min="2" max="50">
                    </div>
                </div>
            `;
        }
    }

    bindEvents() {
        // 1. Strategy Card Clicks
        const strategyCards = this.container.querySelectorAll('.strategy-card');
        strategyCards.forEach(card => {
            card.addEventListener('click', (e) => {
                strategyCards.forEach(c => c.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                this.activeStrategy = target.dataset.strategy;
                this.config.strategy = this.activeStrategy;
                this.config.parameters = {}; // Reset parameters for chosen strategy
                this.updateDynamicParams();
                // Automatically run single backtest & universe scan for new strategy
                this.runBacktest();
                this.scanUniverse();
            });
        });

        // 2. Quick Stock Chips
        const stockChips = this.container.querySelectorAll('.chip-btn');
        stockChips.forEach(chip => {
            chip.addEventListener('click', (e) => {
                stockChips.forEach(c => c.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                const symbol = target.dataset.symbol;
                const symInput = document.getElementById('bt-symbol-input');
                if (symInput) symInput.value = symbol;
                this.config.symbol = symbol;
                this.selectStockAndBacktest(symbol);
            });
        });

        // 3. Symbol Search Input
        const symInput = document.getElementById('bt-symbol-input');
        if (symInput) {
            symInput.addEventListener('change', (e) => {
                const sym = e.target.value.trim().toUpperCase();
                if (sym) {
                    this.config.symbol = sym;
                    this.selectStockAndBacktest(sym);
                }
            });
        }

        // 4. Date Presets (1Y, 3Y, 5Y)
        const datePresets = this.container.querySelectorAll('#bt-date-presets .pill-btn');
        datePresets.forEach(btn => {
            btn.addEventListener('click', (e) => {
                datePresets.forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                const preset = target.dataset.preset;
                let startYear = 2023 - 3;
                if (preset === '1Y') startYear = 2022;
                else if (preset === '3Y') startYear = 2020;
                else if (preset === '5Y') startYear = 2018;

                const startInput = document.getElementById('bt-start-date');
                const endInput = document.getElementById('bt-end-date');
                if (startInput) startInput.value = `${startYear}-01-01`;
                if (endInput) endInput.value = '2023-12-31';
            });
        });

        // 5. Slippage Slider
        const slipSlider = document.getElementById('bt-slippage-slider');
        const slipDisplay = document.getElementById('bt-slippage-display');
        if (slipSlider && slipDisplay) {
            slipSlider.addEventListener('input', (e) => {
                slipDisplay.textContent = `${e.target.value} bps`;
            });
        }

        // 6. Capital Quick Chips
        const capChips = this.container.querySelectorAll('.chip-mini');
        const capInput = document.getElementById('bt-initial-capital');
        capChips.forEach(chip => {
            chip.addEventListener('click', (e) => {
                capChips.forEach(c => c.classList.remove('active'));
                e.currentTarget.classList.add('active');
                const cap = e.currentTarget.dataset.cap;
                if (capInput) capInput.value = cap;
            });
        });

        // 7. Sub-Navigation Tabs (Overview, Summary, Trades)
        const subtabs = this.container.querySelectorAll('.subtab-btn');
        subtabs.forEach(btn => {
            btn.addEventListener('click', (e) => {
                subtabs.forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                const subtab = target.dataset.subtab;
                this.activeSubtab = subtab;

                document.getElementById('subtab-overview').classList.toggle('hidden', subtab !== 'overview');
                document.getElementById('subtab-summary').classList.toggle('hidden', subtab !== 'summary');
                document.getElementById('subtab-trades').classList.toggle('hidden', subtab !== 'trades');

                // Trigger chart reflow if switching to overview
                if (subtab === 'overview') {
                    this.resizeCharts();
                }
            });
        });

        // 8. Trade Filter Pills
        const filterPills = this.container.querySelectorAll('#trades-filter-pills .filter-pill');
        filterPills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                filterPills.forEach(p => p.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                this.tradeFilter = target.dataset.filter;
                this.renderTradesTable();
            });
        });

        // 9. Export CSV Button
        const csvBtn = document.getElementById('btn-export-trades-csv');
        if (csvBtn) {
            csvBtn.addEventListener('click', () => {
                this.exportTradesCSV();
            });
        }

        // 10. Run Backtest Button
        const runBtn = document.getElementById('btn-run-studio-backtest');
        if (runBtn) {
            runBtn.addEventListener('click', () => {
                this.runBacktest();
                this.scanUniverse();
            });
        }

        // 11. Rescan Universe Button
        const rescanBtn = document.getElementById('btn-refresh-matches-scan');
        if (rescanBtn) {
            rescanBtn.addEventListener('click', () => {
                this.scanUniverse();
            });
        }

        // 12. Current Matches Filter Chips (ALL, BUY, SELL)
        const currentFilterChips = this.container.querySelectorAll('#current-matches-filter-group .filter-chip');
        currentFilterChips.forEach(chip => {
            chip.addEventListener('click', (e) => {
                currentFilterChips.forEach(c => c.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.currentSignalFilter = e.currentTarget.dataset.signalFilter || 'ALL';
                this.renderCurrentMatchesTable();
            });
        });

        // 13. Current Matches Search Input
        const currentSearchInput = document.getElementById('input-search-current-matches');
        if (currentSearchInput) {
            currentSearchInput.addEventListener('input', (e) => {
                this.currentSearchTerm = e.target.value.trim().toUpperCase();
                this.renderCurrentMatchesTable();
            });
        }

        // 14. Past Matches Search Input
        const pastSearchInput = document.getElementById('input-search-past-matches');
        if (pastSearchInput) {
            pastSearchInput.addEventListener('input', (e) => {
                this.pastSearchTerm = e.target.value.trim().toUpperCase();
                this.renderPastMatchesTable();
            });
        }

        // 15. Past Matches Sort Dropdown
        const pastSortSelect = document.getElementById('select-past-sort');
        if (pastSortSelect) {
            pastSortSelect.addEventListener('change', (e) => {
                this.pastSortKey = e.target.value;
                this.pastSortAsc = (this.pastSortKey === 'symbol');
                this.renderPastMatchesTable();
            });
        }

        // 16. Past Matches Sortable Headers
        const pastSortHeaders = this.container.querySelectorAll('#table-past-matches th.th-sortable');
        pastSortHeaders.forEach(th => {
            th.addEventListener('click', (e) => {
                const sortKey = e.currentTarget.dataset.sortKey;
                if (!sortKey) return;
                if (this.pastSortKey === sortKey) {
                    this.pastSortAsc = !this.pastSortAsc;
                } else {
                    this.pastSortKey = sortKey;
                    this.pastSortAsc = (sortKey === 'symbol');
                }
                if (pastSortSelect) pastSortSelect.value = sortKey;
                this.renderPastMatchesTable();
            });
        });

        // 17. Section Collapse / Expand Toggles
        const toggleCurrentBtn = document.getElementById('btn-toggle-current-table');
        if (toggleCurrentBtn) {
            toggleCurrentBtn.addEventListener('click', () => {
                this.toggleCollapse('content-current-matches', 'btn-toggle-current-table');
            });
        }

        const togglePastBtn = document.getElementById('btn-toggle-past-table');
        if (togglePastBtn) {
            togglePastBtn.addEventListener('click', () => {
                this.toggleCollapse('content-past-matches', 'btn-toggle-past-table');
            });
        }

        // Window resize handler for charts
        window.addEventListener('resize', () => {
            this.resizeCharts();
        });
    }

    gatherFormData() {
        // Collect current state from inputs
        const symbol = document.getElementById('bt-symbol-input')?.value.trim() || 'NSE:RELIANCE-EQ';
        const timeframe = document.getElementById('bt-timeframe-select')?.value || '1D';
        const startDate = document.getElementById('bt-start-date')?.value || '2020-01-01';
        const endDate = document.getElementById('bt-end-date')?.value || '2023-12-31';
        const initialCap = parseFloat(document.getElementById('bt-initial-capital')?.value) || 1000000;
        const tradeType = document.getElementById('bt-trade-type')?.value || 'DELIVERY';
        const slippageBps = parseFloat(document.getElementById('bt-slippage-slider')?.value) || 5.0;
        const slVal = parseFloat(document.getElementById('bt-stop-loss')?.value);
        const tpVal = parseFloat(document.getElementById('bt-take-profit')?.value);
        const sizeType = document.getElementById('bt-size-type')?.value || 'PERCENT_CAPITAL';
        const sizeVal = parseFloat(document.getElementById('bt-size-val')?.value) || 100.0;

        // Dynamic parameters based on active strategy
        const params = {};
        if (this.activeStrategy === 'SMA_CROSS') {
            params.short_window = parseInt(document.getElementById('param-short-window')?.value) || 20;
            params.long_window = parseInt(document.getElementById('param-long-window')?.value) || 50;
        } else if (this.activeStrategy === 'RSI_REVERSION') {
            params.rsi_period = parseInt(document.getElementById('param-rsi-period')?.value) || 14;
            params.oversold = parseFloat(document.getElementById('param-oversold')?.value) || 30;
            params.overbought = parseFloat(document.getElementById('param-overbought')?.value) || 70;
        } else if (this.activeStrategy === 'BOLLINGER_BANDS') {
            params.period = parseInt(document.getElementById('param-bb-period')?.value) || 20;
            params.std_dev = parseFloat(document.getElementById('param-bb-std')?.value) || 2.0;
        } else if (this.activeStrategy === 'SUPERTREND') {
            params.period = parseInt(document.getElementById('param-st-period')?.value) || 10;
            params.multiplier = parseFloat(document.getElementById('param-st-multiplier')?.value) || 3.0;
        } else if (this.activeStrategy === 'MACD') {
            params.fast_period = parseInt(document.getElementById('param-macd-fast')?.value) || 12;
            params.slow_period = parseInt(document.getElementById('param-macd-slow')?.value) || 26;
            params.signal_period = parseInt(document.getElementById('param-macd-sig')?.value) || 9;
        }

        return {
            strategy: this.activeStrategy,
            symbol: symbol,
            timeframe: timeframe,
            start_date: startDate,
            end_date: endDate,
            initial_capital: initialCap,
            trade_type: tradeType,
            slippage_bps: slippageBps,
            stop_loss_pct: !isNaN(slVal) ? slVal : null,
            take_profit_pct: !isNaN(tpVal) ? tpVal : null,
            position_size_type: sizeType,
            position_size_val: sizeVal,
            parameters: params
        };
    }

    async runBacktest() {
        const payload = this.gatherFormData();
        const statusText = document.getElementById('studio-status-text');
        const statusChip = document.getElementById('studio-status-chip');
        const runBtn = document.getElementById('btn-run-studio-backtest');

        if (statusText) statusText.textContent = 'Simulating...';
        if (statusChip) statusChip.classList.add('running');
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner-inline">⏳</span> Simulating Strategy...';
        }

        try {
            const resp = await fetch('/api/v1/backtest/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) {
                const errJson = await resp.json().catch(() => ({}));
                throw new Error(errJson.detail || errJson.message || `HTTP ${resp.status}`);
            }

            const data = await resp.json();
            const result = data.data || data.result;

            if (!result) {
                throw new Error('Empty response from backtest engine');
            }

            this.result = result;
            this.config = payload;

            // Render all UI components
            this.renderOverviewResults(result, payload);
            this.renderLightweightCharts(result);
            this.renderMonthlyHeatmap(result.monthly_returns || {});
            this.renderSummaryStats(result);
            this.renderTradesTable();

            if (statusText) statusText.textContent = 'Completed';
            if (statusChip) statusChip.classList.remove('running');
        } catch (err) {
            console.error('Backtest error:', err);
            if (statusText) statusText.textContent = 'Error';
            alert(`Backtest execution error: ${err.message}`);
        } finally {
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="btn-icon">🚀</span><span class="btn-text">Run Strategy Backtest</span>';
            }
        }
    }

    setStrategyAndParams(strategyName, params = {}, symbol = null, timeframe = null) {
        console.log(`[BacktestUI] Pre-filling strategy: ${strategyName}`, params, symbol, timeframe);
        const map = {
            'SMA_CROSS': 'SMA_CROSS',
            'SMA_CROSSOVER': 'SMA_CROSS',
            'strat_sma_cross': 'SMA_CROSS',
            'strat_ema_cross': 'SMA_CROSS',
            'RSI_REVERSION': 'RSI_REVERSION',
            'RSI_REVERSAL': 'RSI_REVERSION',
            'strat_rsi_reversal': 'RSI_REVERSION',
            'BOLLINGER_BANDS': 'BOLLINGER_BANDS',
            'strat_bb_breakout': 'BOLLINGER_BANDS',
            'strat_bollinger_breakout': 'BOLLINGER_BANDS',
            'SUPERTREND': 'SUPERTREND',
            'strat_supertrend': 'SUPERTREND',
            'MACD': 'MACD',
            'strat_macd': 'MACD'
        };

        const targetStrategy = map[strategyName] || 'SMA_CROSS';
        this.activeStrategy = targetStrategy;
        this.config.strategy = targetStrategy;

        // Highlight active strategy card
        if (this.container) {
            const strategyCards = this.container.querySelectorAll('.strategy-card');
            strategyCards.forEach(card => {
                if (card.dataset.strategy === targetStrategy) {
                    card.classList.add('active');
                } else {
                    card.classList.remove('active');
                }
            });
        }

        // Set symbol if provided
        if (symbol) {
            this.config.symbol = symbol;
            const symInput = document.getElementById('bt-symbol-input');
            if (symInput) symInput.value = symbol;
            if (this.container) {
                const stockChips = this.container.querySelectorAll('.chip-btn');
                stockChips.forEach(chip => {
                    if (chip.dataset.symbol === symbol) {
                        chip.classList.add('active');
                    } else {
                        chip.classList.remove('active');
                    }
                });
            }
        }

        // Set timeframe if provided
        if (timeframe) {
            this.config.timeframe = timeframe;
            const tfSelect = document.getElementById('bt-timeframe-select');
            if (tfSelect) tfSelect.value = timeframe;
        }

        // Normalize strategy parameters
        if (targetStrategy === 'SMA_CROSS') {
            const shortWin = params.short_window || params.fast_period || params.period || 20;
            const longWin = params.long_window || params.slow_period || params.multiplier || 50;
            this.config.parameters = { short_window: parseInt(shortWin, 10), long_window: parseInt(longWin, 10) };
        } else if (targetStrategy === 'RSI_REVERSION') {
            const rsiPer = params.rsi_period || params.period || 14;
            const oversold = params.oversold || (params.multiplier && params.multiplier < 50 ? params.multiplier : 30);
            const overbought = params.overbought || 70;
            this.config.parameters = { rsi_period: parseInt(rsiPer, 10), oversold: parseFloat(oversold), overbought: parseFloat(overbought) };
        } else if (targetStrategy === 'BOLLINGER_BANDS') {
            const period = params.period || 20;
            const stdDev = params.std_dev || params.stdDev || params.multiplier || 2.0;
            this.config.parameters = { period: parseInt(period, 10), std_dev: parseFloat(stdDev) };
        } else if (targetStrategy === 'SUPERTREND') {
            const period = params.period || 10;
            const mult = params.multiplier || 3.0;
            this.config.parameters = { period: parseInt(period, 10), multiplier: parseFloat(mult) };
        } else if (targetStrategy === 'MACD') {
            const fastPer = params.fast_period || params.period || 12;
            const slowPer = params.slow_period || params.multiplier || 26;
            const sigPer = params.signal_period || params.sec2 || 9;
            this.config.parameters = { fast_period: parseInt(fastPer, 10), slow_period: parseInt(slowPer, 10), signal_period: parseInt(sigPer, 10) };
        }

        // Set stop loss / take profit if passed
        if (params.stop_loss_pct || params.rows) {
            this.config.stop_loss_pct = parseFloat(params.stop_loss_pct || params.rows);
            const slInput = document.getElementById('bt-stop-loss');
            if (slInput) slInput.value = this.config.stop_loss_pct;
        }
        if (params.take_profit_pct || params.sec2) {
            this.config.take_profit_pct = parseFloat(params.take_profit_pct || params.sec2);
            const tpInput = document.getElementById('bt-take-profit');
            if (tpInput) tpInput.value = this.config.take_profit_pct;
        }

        // Re-render parameter fields with updated values
        this.updateDynamicParams();

        // Run the backtest with pre-filled inputs
        this.runBacktest();

        // Resize charts to fit viewport smoothly
        setTimeout(() => this.resizeCharts(), 120);
    }

    renderOverviewResults(result, config) {
        // Meta tags
        const stratMap = {
            'SMA_CROSS': 'SMA Crossover',
            'RSI_REVERSION': 'RSI Reversal',
            'BOLLINGER_BANDS': 'Bollinger Bands',
            'SUPERTREND': 'Supertrend',
            'MACD': 'MACD Momentum'
        };
        const stratName = stratMap[config.strategy] || config.strategy;
        document.getElementById('meta-strategy-tag').innerHTML = `Strategy: <strong>${stratName}</strong>`;
        document.getElementById('meta-symbol-tag').innerHTML = `Asset: <strong>${config.symbol}</strong>`;
        document.getElementById('meta-period-tag').innerHTML = `Period: <strong>${config.start_date} to ${config.end_date}</strong>`;
        document.getElementById('meta-capital-tag').innerHTML = `Capital: <strong>₹${Number(config.initial_capital).toLocaleString('en-IN')}</strong>`;

        const activeStockBadge = document.getElementById('current-view-active-stock');
        if (activeStockBadge) activeStockBadge.textContent = config.symbol;

        // Sync table row highlights
        if (this.container) {
            this.container.querySelectorAll('#tbody-current-matches tr, #tbody-past-matches tr').forEach(tr => {
                tr.classList.toggle('active-selected-row', tr.dataset.symbol === config.symbol);
            });
        }

        // Headline Net Return
        const netPnl = result.net_pnl || 0;
        const initialCap = config.initial_capital || 1000000;
        const netReturnPct = (netPnl / initialCap) * 100;
        const headlineEl = document.getElementById('headline-net-pnl');
        const sign = netPnl >= 0 ? '+' : '';
        headlineEl.textContent = `${sign}₹${Number(netPnl.toFixed(2)).toLocaleString('en-IN')} (${sign}${netReturnPct.toFixed(2)}%)`;
        headlineEl.className = `pnl-val font-mono ${netPnl >= 0 ? 'text-green' : 'text-red'}`;

        // KPI Cards
        const cagr = typeof result.cagr === 'number' ? (result.cagr * 100).toFixed(2) + '%' : '0.00%';
        const cagrEl = document.getElementById('m-cagr');
        cagrEl.textContent = cagr;
        cagrEl.className = `m-value font-mono ${parseFloat(cagr) >= 0 ? 'text-green' : 'text-red'}`;

        const netPnlEl = document.getElementById('m-net-pnl');
        netPnlEl.textContent = `${sign}₹${Number(netPnl.toFixed(2)).toLocaleString('en-IN')}`;
        netPnlEl.className = `m-value font-mono ${netPnl >= 0 ? 'text-green' : 'text-red'}`;

        document.getElementById('m-gross-pnl').textContent = `Gross: ₹${Number((result.gross_pnl || 0).toFixed(2)).toLocaleString('en-IN')}`;

        const maxDd = typeof result.max_drawdown_pct === 'number' ? (result.max_drawdown_pct * 100).toFixed(2) + '%' : '0.00%';
        document.getElementById('m-max-dd').textContent = maxDd;

        const winRate = typeof result.win_rate === 'number' ? (result.win_rate * 100).toFixed(1) + '%' : '0.0%';
        document.getElementById('m-win-rate').textContent = winRate;

        const totalTrades = result.total_trades || (result.trades ? result.trades.length : 0);
        const extra = result.extra_metrics || {};
        const winCount = extra.win_trades_count || 0;
        const lossCount = extra.loss_trades_count || 0;
        document.getElementById('m-win-loss-count').textContent = `${winCount} Wins / ${lossCount} Losses (${totalTrades} total)`;

        document.getElementById('m-profit-factor').textContent = (result.profit_factor || 0).toFixed(2);
        document.getElementById('m-sharpe').textContent = (result.sharpe_ratio || 0).toFixed(2);
        document.getElementById('m-sortino').textContent = (result.sortino_ratio || 0).toFixed(2);
        document.getElementById('m-fees').textContent = `₹${Number((result.total_taxes_and_fees || 0).toFixed(2)).toLocaleString('en-IN')}`;

        // Tab trades count
        document.getElementById('tab-trades-count').textContent = totalTrades;
        document.getElementById('pill-all-count').textContent = totalTrades;
        document.getElementById('pill-win-count').textContent = winCount;
        document.getElementById('pill-loss-count').textContent = lossCount;

        // Audit Hash
        document.getElementById('audit-hash-display').textContent = result.data_version_hash || 'SHA256-UNVERIFIED';
    }

    renderLightweightCharts(result) {
        if (!window.LightweightCharts) {
            console.error('TradingView LightweightCharts library not found');
            return;
        }

        const isLight = document.body.classList.contains('theme-light');
        const bgColor = isLight ? '#FFFFFF' : '#151924';
        const textColor = isLight ? '#0F172A' : '#D1D4DC';
        const gridColor = isLight ? '#F1F5F9' : '#232733';

        // 1. Setup Equity Chart
        const equityContainer = document.getElementById('bt-equity-chart');
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

            // Strategy Equity Area Series
            const areaOptions = {
                topColor: 'rgba(34, 197, 94, 0.45)',
                bottomColor: 'rgba(34, 197, 94, 0.02)',
                lineColor: '#22c55e',
                lineWidth: 2,
                title: 'Strategy Equity'
            };
            if (typeof this.equityChart.addAreaSeries === 'function') {
                this.equitySeries = this.equityChart.addAreaSeries(areaOptions);
            } else if (typeof this.equityChart.addSeries === 'function') {
                this.equitySeries = this.equityChart.addSeries(LightweightCharts.AreaSeries, areaOptions);
            }

            // Benchmark Buy & Hold Line Series
            const lineOptions = {
                color: '#38bdf8',
                lineWidth: 1.5,
                lineStyle: LightweightCharts.LineStyle ? LightweightCharts.LineStyle.Dotted : 2,
                title: 'Benchmark'
            };
            if (typeof this.equityChart.addLineSeries === 'function') {
                this.benchmarkSeries = this.equityChart.addLineSeries(lineOptions);
            } else if (typeof this.equityChart.addSeries === 'function') {
                this.benchmarkSeries = this.equityChart.addSeries(LightweightCharts.LineSeries, lineOptions);
            }

            // Populate data
            const eqData = (result.equity_curve || []).map(pt => ({
                time: String(pt.timestamp).split('T')[0],
                value: pt.equity
            })).filter((v, i, a) => a.findIndex(t => t.time === v.time) === i); // deduplicate dates

            const bmData = (result.benchmark_curve || []).map(pt => ({
                time: String(pt.timestamp).split('T')[0],
                value: pt.equity
            })).filter((v, i, a) => a.findIndex(t => t.time === v.time) === i);

            if (this.equitySeries && eqData.length > 0) {
                this.equitySeries.setData(eqData);
            }
            if (this.benchmarkSeries && bmData.length > 0) {
                this.benchmarkSeries.setData(bmData);
            }

            this.equityChart.timeScale().fitContent();

            // Crosshair Tooltip
            const stratLeg = document.getElementById('leg-strat-val');
            const bmLeg = document.getElementById('leg-bm-val');
            this.equityChart.subscribeCrosshairMove(param => {
                if (!param || !param.time || !param.seriesData) {
                    if (eqData.length > 0) {
                        const lastEq = eqData[eqData.length - 1].value;
                        if (stratLeg) stratLeg.textContent = `₹${Number(lastEq.toFixed(2)).toLocaleString('en-IN')}`;
                    }
                    if (bmData.length > 0) {
                        const lastBm = bmData[bmData.length - 1].value;
                        if (bmLeg) bmLeg.textContent = `₹${Number(lastBm.toFixed(2)).toLocaleString('en-IN')}`;
                    }
                    return;
                }
                const eqVal = param.seriesData.get(this.equitySeries)?.value;
                const bmVal = param.seriesData.get(this.benchmarkSeries)?.value;
                if (typeof eqVal === 'number' && stratLeg) {
                    stratLeg.textContent = `₹${Number(eqVal.toFixed(2)).toLocaleString('en-IN')}`;
                }
                if (typeof bmVal === 'number' && bmLeg) {
                    bmLeg.textContent = `₹${Number(bmVal.toFixed(2)).toLocaleString('en-IN')}`;
                }
            });
        }

        // 2. Setup Drawdown Chart
        const ddContainer = document.getElementById('bt-drawdown-chart');
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
                    scaleMargins: { top: 0.1, bottom: 0.1 }
                },
                timeScale: {
                    borderColor: gridColor,
                    timeVisible: true
                }
            });

            const ddOptions = {
                topColor: 'rgba(239, 68, 68, 0.05)',
                bottomColor: 'rgba(239, 68, 68, 0.4)',
                lineColor: '#ef4444',
                lineWidth: 1.5,
                title: 'Drawdown %'
            };
            if (typeof this.drawdownChart.addAreaSeries === 'function') {
                this.drawdownSeries = this.drawdownChart.addAreaSeries(ddOptions);
            } else if (typeof this.drawdownChart.addSeries === 'function') {
                this.drawdownSeries = this.drawdownChart.addSeries(LightweightCharts.AreaSeries, ddOptions);
            }

            const ddData = (result.drawdown_curve || []).map(pt => ({
                time: String(pt.timestamp).split('T')[0],
                value: pt.drawdown
            })).filter((v, i, a) => a.findIndex(t => t.time === v.time) === i);

            if (this.drawdownSeries && ddData.length > 0) {
                this.drawdownSeries.setData(ddData);
            }

            this.drawdownChart.timeScale().fitContent();

            const ddLeg = document.getElementById('leg-dd-val');
            this.drawdownChart.subscribeCrosshairMove(param => {
                if (!param || !param.time || !param.seriesData) {
                    if (ddData.length > 0 && ddLeg) {
                        ddLeg.textContent = `${ddData[ddData.length - 1].value.toFixed(2)}%`;
                    }
                    return;
                }
                const val = param.seriesData.get(this.drawdownSeries)?.value;
                if (typeof val === 'number' && ddLeg) {
                    ddLeg.textContent = `${val.toFixed(2)}%`;
                }
            });
        }
    }

    resizeCharts() {
        const eqContainer = document.getElementById('bt-equity-chart');
        if (this.equityChart && eqContainer) {
            this.equityChart.resize(eqContainer.clientWidth, 320);
            this.equityChart.timeScale().fitContent();
        }
        const ddContainer = document.getElementById('bt-drawdown-chart');
        if (this.drawdownChart && ddContainer) {
            this.drawdownChart.resize(ddContainer.clientWidth, 150);
            this.drawdownChart.timeScale().fitContent();
        }
    }

    renderMonthlyHeatmap(monthlyData) {
        const container = document.getElementById('monthly-heatmap-container');
        if (!container) return;

        const years = Object.keys(monthlyData).sort();
        if (years.length === 0) {
            container.innerHTML = '<div class="p-4 text-center text-muted">No monthly returns data available.</div>';
            return;
        }

        const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        let html = `
            <table class="heatmap-table">
                <thead>
                    <tr>
                        <th class="year-hdr">Year</th>
                        ${monthNames.map(m => `<th>${m}</th>`).join('')}
                        <th class="total-hdr">Full Year</th>
                    </tr>
                </thead>
                <tbody>
        `;

        years.forEach(year => {
            const yData = monthlyData[year] || {};
            html += `<tr><td class="year-cell">${year}</td>`;

            months.forEach(m => {
                const val = yData[m] || 0.0;
                const formatted = val !== 0 ? (val > 0 ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`) : '-';

                // Color intensity logic
                let cellClass = 'cell-zero';
                if (val > 5.0) cellClass = 'cell-gain-high';
                else if (val > 0.0) cellClass = 'cell-gain-low';
                else if (val < -5.0) cellClass = 'cell-loss-high';
                else if (val < 0.0) cellClass = 'cell-loss-low';

                html += `<td class="${cellClass}">${formatted}</td>`;
            });

            const total = yData['total'] || 0.0;
            const formattedTotal = total > 0 ? `+${total.toFixed(2)}%` : `${total.toFixed(2)}%`;
            const totalClass = total >= 0 ? 'text-green cell-total' : 'text-red cell-total';
            html += `<td class="${totalClass}"><strong>${formattedTotal}</strong></td></tr>`;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;
    }

    renderSummaryStats(result) {
        const extra = result.extra_metrics || {};
        const totalTrades = result.total_trades || 0;
        const winTrades = extra.win_trades_count || 0;
        const lossTrades = extra.loss_trades_count || 0;

        document.getElementById('stat-total-trades').textContent = totalTrades;
        document.getElementById('stat-win-trades').textContent = winTrades;
        document.getElementById('stat-loss-trades').textContent = lossTrades;
        document.getElementById('stat-win-loss-ratio').textContent = (extra.win_loss_ratio || 0).toFixed(2);

        document.getElementById('stat-max-win').textContent = `+₹${Number((extra.max_win || 0).toFixed(2)).toLocaleString('en-IN')}`;
        document.getElementById('stat-max-loss').textContent = `-₹${Number(Math.abs(extra.max_loss || 0).toFixed(2)).toLocaleString('en-IN')}`;
        document.getElementById('stat-avg-win').textContent = `+₹${Number((extra.avg_win || 0).toFixed(2)).toLocaleString('en-IN')}`;
        document.getElementById('stat-avg-loss').textContent = `-₹${Number((extra.avg_loss || 0).toFixed(2)).toLocaleString('en-IN')}`;
        document.getElementById('stat-expectancy').textContent = `₹${Number((extra.expectancy || 0).toFixed(2)).toLocaleString('en-IN')}`;
        document.getElementById('stat-avg-holding').textContent = `${extra.avg_holding_bars || 0} bars`;
        document.getElementById('stat-turnover').textContent = `₹${Number((extra.total_turnover || 0).toFixed(2)).toLocaleString('en-IN')}`;
    }

    renderTradesTable() {
        const tbody = document.getElementById('trades-table-body');
        if (!tbody) return;

        let trades = (this.result && this.result.trades) ? this.result.trades : [];

        // Filter
        if (this.tradeFilter === 'WIN') {
            trades = trades.filter(t => t.net_pnl > 0);
        } else if (this.tradeFilter === 'LOSS') {
            trades = trades.filter(t => t.net_pnl <= 0);
        }

        if (trades.length === 0) {
            tbody.innerHTML = `<tr><td colspan="13" class="text-center p-4 text-muted">No trades match the filter "${this.tradeFilter}".</td></tr>`;
            return;
        }

        let html = '';
        trades.forEach((t, idx) => {
            const isWin = t.net_pnl > 0;
            const sign = isWin ? '+' : '';
            const pnlColor = isWin ? 'text-green' : 'text-red';

            // Format exit reason badge
            let reasonBadge = '<span class="reason-tag tag-signal">SIGNAL</span>';
            if (t.exit_reason === 'STOP_LOSS') {
                reasonBadge = '<span class="reason-tag tag-sl">STOP LOSS</span>';
            } else if (t.exit_reason === 'TAKE_PROFIT') {
                reasonBadge = '<span class="reason-tag tag-tp">TAKE PROFIT</span>';
            } else if (t.exit_reason === 'END_OF_DATA') {
                reasonBadge = '<span class="reason-tag tag-eod">LAST CLOSE</span>';
            }

            const entryDate = String(t.entry_time).split('T')[0];
            const exitDate = String(t.exit_time).split('T')[0];

            html += `
                <tr class="${isWin ? 'tr-win' : 'tr-loss'}">
                    <td class="font-mono text-muted">${t.trade_id || idx + 1}</td>
                    <td class="font-mono">${entryDate}</td>
                    <td class="font-mono">${exitDate}</td>
                    <td><span class="badge-side-buy">BUY</span></td>
                    <td class="font-mono">₹${Number(t.entry_price).toFixed(2)}</td>
                    <td class="font-mono">₹${Number(t.exit_price).toFixed(2)}</td>
                    <td class="font-mono">${t.qty}</td>
                    <td class="font-mono ${t.gross_pnl >= 0 ? 'text-green' : 'text-red'}">${t.gross_pnl >= 0 ? '+' : ''}₹${Number(t.gross_pnl.toFixed(2)).toLocaleString('en-IN')}</td>
                    <td class="font-mono text-amber">₹${Number(t.fees.toFixed(2)).toLocaleString('en-IN')}</td>
                    <td class="font-mono ${pnlColor} font-bold">${sign}₹${Number(t.net_pnl.toFixed(2)).toLocaleString('en-IN')}</td>
                    <td class="font-mono ${pnlColor}">${sign}${Number(t.pnl_pct).toFixed(2)}%</td>
                    <td>${reasonBadge}</td>
                    <td class="font-mono text-muted">${t.holding_period_bars} bars</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    exportTradesCSV() {
        const trades = (this.result && this.result.trades) ? this.result.trades : [];
        if (trades.length === 0) {
            alert('No trades available to export.');
            return;
        }

        const headers = ['Trade_ID', 'Entry_Date', 'Exit_Date', 'Side', 'Qty', 'Entry_Price', 'Exit_Price', 'Gross_PnL', 'Taxes_And_Fees', 'Net_PnL', 'Return_Pct', 'Exit_Reason', 'Holding_Bars'];
        const csvRows = [headers.join(',')];

        trades.forEach(t => {
            const row = [
                t.trade_id,
                `"${t.entry_time}"`,
                `"${t.exit_time}"`,
                t.side || 'BUY',
                t.qty,
                t.entry_price,
                t.exit_price,
                t.gross_pnl,
                t.fees,
                t.net_pnl,
                t.pnl_pct,
                `"${t.exit_reason || 'SIGNAL'}"`,
                t.holding_period_bars
            ];
            csvRows.push(row.join(','));
        });

        const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvRows.join('\n'));
        const link = document.createElement('a');
        link.setAttribute('href', csvContent);
        const fileName = `backtest_ledger_${this.config.symbol.replace(/[^a-zA-Z0-9]/g, '_')}_${this.config.strategy}.csv`;
        link.setAttribute('download', fileName);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async scanUniverse() {
        if (this.isScanning) return;
        this.isScanning = true;

        const stratMap = {
            'SMA_CROSS': 'SMA Crossover',
            'RSI_REVERSION': 'RSI Reversal',
            'BOLLINGER_BANDS': 'Bollinger Bands',
            'SUPERTREND': 'Supertrend',
            'MACD': 'MACD Momentum'
        };
        const friendlyStrat = stratMap[this.activeStrategy] || this.activeStrategy;

        const stratTitle1 = document.getElementById('current-matches-strat-name');
        const stratTitle2 = document.getElementById('past-matches-strat-name');
        if (stratTitle1) stratTitle1.textContent = friendlyStrat;
        if (stratTitle2) stratTitle2.textContent = friendlyStrat;

        const badgeCurrent = document.getElementById('badge-current-matches-count');
        const badgePast = document.getElementById('badge-past-matches-count');
        if (badgeCurrent) badgeCurrent.textContent = 'Scanning...';
        if (badgePast) badgePast.textContent = 'Scanning...';

        const tbodyCurrent = document.getElementById('tbody-current-matches');
        const tbodyPast = document.getElementById('tbody-past-matches');
        if (tbodyCurrent && this.currentMatches.length === 0) {
            tbodyCurrent.innerHTML = '<tr><td colspan="8" class="text-center p-4 text-muted"><span class="spinner-inline">⏳</span> Scanning universe for active signals...</td></tr>';
        }
        if (tbodyPast && this.pastMatches.length === 0) {
            tbodyPast.innerHTML = '<tr><td colspan="8" class="text-center p-4 text-muted"><span class="spinner-inline">⏳</span> Backtesting universe across historical data...</td></tr>';
        }

        const rescanBtn = document.getElementById('btn-refresh-matches-scan');
        if (rescanBtn) rescanBtn.classList.add('loading');

        try {
            const payload = this.gatherFormData();
            const resp = await fetch('/api/v1/backtest/scan-universe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy: payload.strategy,
                    timeframe: payload.timeframe,
                    start_date: payload.start_date,
                    end_date: payload.end_date,
                    initial_capital: payload.initial_capital,
                    parameters: payload.parameters,
                    slippage_bps: payload.slippage_bps,
                    stop_loss_pct: payload.stop_loss_pct,
                    take_profit_pct: payload.take_profit_pct,
                    position_size_type: payload.position_size_type,
                    position_size_val: payload.position_size_val,
                    max_symbols: 100
                })
            });

            if (!resp.ok) {
                throw new Error(`Universe scan error HTTP ${resp.status}`);
            }

            const data = await resp.json();
            this.currentMatches = data.current_matches || [];
            this.pastMatches = data.past_matches || [];

            this.renderCurrentMatchesTable();
            this.renderPastMatchesTable();

        } catch (err) {
            console.error('[BacktestUI] Universe scan failed:', err);
            if (badgeCurrent) badgeCurrent.textContent = 'Scan Error';
            if (badgePast) badgePast.textContent = 'Scan Error';
        } finally {
            this.isScanning = false;
            if (rescanBtn) rescanBtn.classList.remove('loading');
        }
    }

    renderCurrentMatchesTable() {
        const tbody = document.getElementById('tbody-current-matches');
        const emptyBox = document.getElementById('empty-current-matches');
        const badgeCount = document.getElementById('badge-current-matches-count');
        if (!tbody) return;

        let filtered = [...this.currentMatches];

        // Apply signal filter (BUY / SELL)
        if (this.currentSignalFilter && this.currentSignalFilter !== 'ALL') {
            filtered = filtered.filter(m => m.signal === this.currentSignalFilter);
        }

        // Apply symbol search
        if (this.currentSearchTerm) {
            filtered = filtered.filter(m => 
                (m.symbol && m.symbol.toUpperCase().includes(this.currentSearchTerm)) ||
                (m.name && m.name.toUpperCase().includes(this.currentSearchTerm))
            );
        }

        if (badgeCount) {
            badgeCount.textContent = `${this.currentMatches.length} Signals (${filtered.length} shown)`;
        }

        if (filtered.length === 0) {
            tbody.innerHTML = '';
            if (emptyBox) emptyBox.classList.remove('d-none');
            return;
        }

        if (emptyBox) emptyBox.classList.add('d-none');

        tbody.innerHTML = filtered.map(item => {
            const isBuy = item.signal === 'BUY';
            const badgeClass = isBuy ? 'badge-signal-buy' : 'badge-signal-sell';
            const icon = isBuy ? '▲' : '▼';
            const chgClass = (item.change_pct >= 0) ? 'text-green' : 'text-red';
            const chgSign = (item.change_pct >= 0) ? '+' : '';
            const isActiveStock = (item.symbol === this.config.symbol);
            const rowClass = isActiveStock ? 'active-selected-row' : '';

            let timeLabel = item.signal_date || '';
            if (item.bars_ago === 0) timeLabel = `Today (${item.signal_date})`;
            else if (item.bars_ago === 1) timeLabel = `1d ago (${item.signal_date})`;
            else if (item.bars_ago > 1) timeLabel = `${item.bars_ago}d ago (${item.signal_date})`;

            return `
                <tr class="${rowClass}" data-symbol="${item.symbol}">
                    <td>
                        <div class="symbol-cell">
                            <span class="symbol-ticker">${item.symbol}</span>
                            <span class="symbol-fullname">${item.name || ''}</span>
                        </div>
                    </td>
                    <td class="text-center">
                        <span class="${badgeClass}">${icon} ${item.signal}</span>
                    </td>
                    <td class="text-muted font-mono" style="font-size: 11px;">
                        ${timeLabel}
                    </td>
                    <td class="text-right font-mono">
                        ₹${Number(item.signal_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td class="text-right font-mono font-bold">
                        ₹${Number(item.current_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td class="text-right font-mono font-bold ${chgClass}">
                        ${chgSign}${item.change_pct}%
                    </td>
                    <td class="text-secondary" style="font-size: 11px;">
                        ${item.indicator_details || '-'}
                    </td>
                    <td class="text-center">
                        <button type="button" class="btn-select-stock" data-symbol="${item.symbol}">
                            Select &amp; Backtest →
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Attach click listeners to rows & buttons
        tbody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', (e) => {
                const sym = row.dataset.symbol;
                if (sym) this.selectStockAndBacktest(sym);
            });
        });
    }

    renderPastMatchesTable() {
        const tbody = document.getElementById('tbody-past-matches');
        const badgeCount = document.getElementById('badge-past-matches-count');
        if (!tbody) return;

        let filtered = [...this.pastMatches];

        // Apply symbol search
        if (this.pastSearchTerm) {
            filtered = filtered.filter(m => 
                (m.symbol && m.symbol.toUpperCase().includes(this.pastSearchTerm)) ||
                (m.name && m.name.toUpperCase().includes(this.pastSearchTerm))
            );
        }

        // Apply sorting
        const key = this.pastSortKey || 'win_rate';
        const asc = this.pastSortAsc || false;

        filtered.sort((a, b) => {
            let valA = a[key];
            let valB = b[key];
            if (typeof valA === 'string') {
                return asc ? valA.localeCompare(valB) : valB.localeCompare(valA);
            }
            valA = Number(valA) || 0;
            valB = Number(valB) || 0;
            return asc ? (valA - valB) : (valB - valA);
        });

        if (badgeCount) {
            badgeCount.textContent = `${this.pastMatches.length} Stocks Scanned (${filtered.length} shown)`;
        }

        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center p-4 text-muted">No stocks matched the filter search.</td></tr>';
            return;
        }

        tbody.innerHTML = filtered.map(item => {
            const pnlClass = (item.net_pnl >= 0) ? 'text-green' : 'text-red';
            const pnlSign = (item.net_pnl >= 0) ? '+' : '';
            const isActiveStock = (item.symbol === this.config.symbol);
            const rowClass = isActiveStock ? 'active-selected-row' : '';

            const pfClass = (item.profit_factor >= 1.5) ? 'text-green' : (item.profit_factor < 1.0 ? 'text-red' : 'text-primary');

            return `
                <tr class="${rowClass}" data-symbol="${item.symbol}">
                    <td>
                        <div class="symbol-cell">
                            <span class="symbol-ticker">${item.symbol}</span>
                            <span class="symbol-fullname">${item.name || ''}</span>
                        </div>
                    </td>
                    <td class="text-center font-mono font-bold">
                        ${item.total_trades}
                    </td>
                    <td class="text-center">
                        <span class="badge-win">${item.win_count}W</span>
                    </td>
                    <td class="text-center">
                        <span class="badge-loss">${item.loss_count}L</span>
                    </td>
                    <td>
                        <div class="win-rate-flex-cell">
                            <div class="win-rate-track">
                                <div class="win-rate-fill" style="width: ${Math.min(100, Math.max(0, item.win_rate))}%;"></div>
                            </div>
                            <span class="font-mono font-bold" style="font-size: 11px;">${item.win_rate}%</span>
                        </div>
                    </td>
                    <td class="text-right font-mono font-bold ${pnlClass}">
                        ${pnlSign}₹${Number(item.net_pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        <span style="font-size: 10px; opacity: 0.85; margin-left: 4px;">(${pnlSign}${item.net_pnl_pct}%)</span>
                    </td>
                    <td class="text-right font-mono font-bold ${pfClass}">
                        ${item.profit_factor}
                    </td>
                    <td class="text-center">
                        <button type="button" class="btn-select-stock" data-symbol="${item.symbol}">
                            View Backtest →
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Attach click listeners to rows & buttons
        tbody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', (e) => {
                const sym = row.dataset.symbol;
                if (sym) this.selectStockAndBacktest(sym);
            });
        });
    }

    selectStockAndBacktest(symbol) {
        if (!symbol) return;
        console.log(`[BacktestUI] Switching active stock to: ${symbol}`);
        this.config.symbol = symbol;

        // Update symbol input
        const symInput = document.getElementById('bt-symbol-input');
        if (symInput) symInput.value = symbol;

        // Update quick chips
        if (this.container) {
            const stockChips = this.container.querySelectorAll('.chip-btn');
            stockChips.forEach(chip => {
                chip.classList.toggle('active', chip.dataset.symbol === symbol);
            });
        }

        // Update active stock tags
        const activeStockTag = document.getElementById('current-view-active-stock');
        if (activeStockTag) activeStockTag.textContent = symbol;
        const metaSymTag = document.getElementById('meta-symbol-tag');
        if (metaSymTag) metaSymTag.innerHTML = `Asset: <strong>${symbol}</strong>`;

        // Update active row highlighting across both tables
        if (this.container) {
            this.container.querySelectorAll('#tbody-current-matches tr, #tbody-past-matches tr').forEach(tr => {
                tr.classList.toggle('active-selected-row', tr.dataset.symbol === symbol);
            });
        }

        // Run full backtest for this stock
        this.runBacktest();

        // Smoothly scroll to the Current View section so user sees updated charts/stats
        const currentViewSection = document.getElementById('section-current-view');
        if (currentViewSection) {
            currentViewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    toggleCollapse(contentId, btnId) {
        const content = document.getElementById(contentId);
        const btn = document.getElementById(btnId);
        if (!content) return;
        const isCollapsed = content.classList.toggle('collapsed');
        if (btn) btn.textContent = isCollapsed ? '▲' : '▼';
    }
}

// Auto-initialize when container is present
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('backtest-workspace-container')) {
        window.backtestUI = new BacktestUI('backtest-workspace-container');
    }
});
