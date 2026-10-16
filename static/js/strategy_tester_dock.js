/**
 * Strategy Tester Chart Dock & Execution Signals Engine
 * Renders visual Buy/Sell arrow markers on the main chart series
 * and docks a TradingView-identical quantitative summary bar at the bottom.
 */

(function () {
    class StrategyTesterDock {
        constructor() {
            this.dockEl = null;
            this.currentStrategy = null;
            this.currentMarkers = [];
            this.currentResult = null;
            this.isOpen = false;

            document.addEventListener('DOMContentLoaded', () => this.init());
        }

        init() {
            this.createDockMarkup();
        }

        createDockMarkup() {
            if (document.getElementById('strategy-tester-dock')) return;

            const dock = document.createElement('div');
            dock.id = 'strategy-tester-dock';
            dock.className = 'strategy-tester-dock';
            dock.style.cssText = `
                display: none;
                background: #1e222d;
                border-top: 1px solid #2a2e39;
                padding: 12px 20px;
                color: #d1d4dc;
                font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif;
                z-index: 10;
                box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.3);
            `;

            dock.innerHTML = `
                <div class="strategy-dock-header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span style="display:inline-flex; align-items:center; gap:6px; font-weight:700; font-size:13px; color:#ffffff;">
                            <span style="color:#2962FF;">⚡</span> Strategy Tester: <span id="strategy-dock-title" style="color:#2962FF;">SMA Crossover</span>
                        </span>
                        <span id="strategy-dock-status" style="font-size:11px; color:#10b981;">● Real Data Execution · 100% Capital</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <button id="btn-dock-deep-dive" style="
                            background: #2962FF;
                            color: #ffffff;
                            border: none;
                            padding: 6px 14px;
                            border-radius: 4px;
                            font-size: 12px;
                            font-weight: 600;
                            cursor: pointer;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                            transition: background 0.15s ease;
                        ">
                            🔬 Deep Dive in Backtest Lab
                        </button>
                        <button id="btn-dock-close" style="
                            background: transparent;
                            border: 1px solid #363a45;
                            color: #787b86;
                            padding: 4px 8px;
                            border-radius: 4px;
                            font-size: 13px;
                            cursor: pointer;
                            line-height: 1;
                        " title="Close Strategy Tester">✕</button>
                    </div>
                </div>

                <div class="strategy-dock-kpis" style="display:grid; grid-template-columns:repeat(5, 1fr); gap:12px;">
                    <div style="background:#131722; padding:8px 12px; border-radius:6px; border-left:3px solid #2962FF;">
                        <div style="font-size:11px; color:#787b86; margin-bottom:2px;">Net Profit</div>
                        <div id="kpi-net-profit" style="font-size:15px; font-weight:700; color:#089981;">₹0.00</div>
                    </div>
                    <div style="background:#131722; padding:8px 12px; border-radius:6px; border-left:3px solid #089981;">
                        <div style="font-size:11px; color:#787b86; margin-bottom:2px;">Win Rate</div>
                        <div id="kpi-win-rate" style="font-size:15px; font-weight:700; color:#ffffff;">0.0%</div>
                    </div>
                    <div style="background:#131722; padding:8px 12px; border-radius:6px; border-left:3px solid #FF9800;">
                        <div style="font-size:11px; color:#787b86; margin-bottom:2px;">Profit Factor</div>
                        <div id="kpi-profit-factor" style="font-size:15px; font-weight:700; color:#ffffff;">0.00</div>
                    </div>
                    <div style="background:#131722; padding:8px 12px; border-radius:6px; border-left:3px solid #F23645;">
                        <div style="font-size:11px; color:#787b86; margin-bottom:2px;">Max Drawdown</div>
                        <div id="kpi-max-dd" style="font-size:15px; font-weight:700; color:#F23645;">0.0%</div>
                    </div>
                    <div style="background:#131722; padding:8px 12px; border-radius:6px; border-left:3px solid #787b86;">
                        <div style="font-size:11px; color:#787b86; margin-bottom:2px;">Total Trades</div>
                        <div id="kpi-total-trades" style="font-size:15px; font-weight:700; color:#ffffff;">0</div>
                    </div>
                </div>
            `;

            const chartWrapper = document.querySelector('.chart-section') || document.querySelector('.chart-column') || document.getElementById('chart-container');
            if (chartWrapper && chartWrapper.parentNode) {
                chartWrapper.parentNode.insertBefore(dock, chartWrapper.nextSibling);
            } else {
                document.body.appendChild(dock);
            }

            this.dockEl = dock;

            // Hook close button
            dock.querySelector('#btn-dock-close').addEventListener('click', () => this.close());

            // Hook Deep Dive button
            dock.querySelector('#btn-dock-deep-dive').addEventListener('click', () => {
                this.navigateToBacktest();
            });
        }

        navigateToBacktest() {
            const strategyId = this.currentStrategy || 'strat_sma_cross';
            const inputs = this.currentInputs || {};
            const symbol = this.currentSymbol || window.currentActiveSymbol || window.activeSymbol || 'NSE:RELIANCE-EQ';
            const timeframe = this.currentTimeframe || window.currentSymbolTimeframe || window.activeTimeframe || '1D';

            console.log(`[StrategyTester] Deep Dive into Backtest Lab: strategy=${strategyId}, symbol=${symbol}, tf=${timeframe}`, inputs);

            // 1. Switch to Backtest Tab
            if (typeof window.switchAppView === 'function') {
                window.switchAppView('backtest');
            } else if (typeof window.switchView === 'function') {
                window.switchView('backtest');
            } else {
                const backtestTab = document.querySelector('.view-tab[data-view="backtest"]');
                if (backtestTab) backtestTab.click();
            }

            // 2. Pre-fill strategy, symbol, timeframe, and parameters into Backtest UI
            const applyParams = () => {
                if (window.backtestUI && typeof window.backtestUI.setStrategyAndParams === 'function') {
                    window.backtestUI.setStrategyAndParams(strategyId, inputs, symbol, timeframe);
                }
            };

            if (window.backtestUI && typeof window.backtestUI.setStrategyAndParams === 'function') {
                applyParams();
            } else {
                setTimeout(applyParams, 120);
            }
        }

        async runStrategy(strategyId, customInputs = {}) {
            console.log(`[StrategyTester] Running strategy: ${strategyId}`, customInputs);
            this.currentStrategy = strategyId;
            this.currentInputs = customInputs;
            this.currentSymbol = window.currentActiveSymbol || window.activeSymbol || 'NSE:RELIANCE-EQ';
            this.currentTimeframe = window.currentSymbolTimeframe || window.activeTimeframe || '1D';

            // Strategy mapping to backtest service names
            const strategyMap = {
                strat_sma_cross: 'SMA_CROSS',
                strat_ema_cross: 'SMA_CROSS',
                strat_rsi_reversal: 'RSI_REVERSION',
                strat_bb_breakout: 'BOLLINGER_BANDS',
                strat_bollinger_breakout: 'BOLLINGER_BANDS',
                strat_supertrend: 'SUPERTREND',
                strat_macd: 'MACD'
            };

            let backendStrategyName = strategyMap[strategyId];
            if (!backendStrategyName && customInputs && customInputs.base_type) {
                backendStrategyName = strategyMap[customInputs.base_type] || 'SMA_CROSS';
            }
            if (!backendStrategyName) {
                backendStrategyName = 'SMA_CROSS';
            }

            // Active symbol
            const symbol = this.currentSymbol;
            const timeframe = this.currentTimeframe;

            // Show dock in loading state
            this.showDockLoading(strategyId);

            try {
                const response = await fetch('/api/v1/backtest/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        strategy: backendStrategyName,
                        symbol: symbol,
                        timeframe: timeframe,
                        start_date: '2022-01-01',
                        end_date: '2024-12-31',
                        initial_capital: 1000000.0,
                        trade_type: 'DELIVERY',
                        parameters: customInputs,
                        slippage_bps: 5.0,
                        position_size_type: 'PERCENT_CAPITAL',
                        position_size_val: 100.0
                    })
                });

                const json = await response.json();
                if (json.success && json.data) {
                    this.currentResult = json.data;
                    this.renderResults(json.data);
                    this.renderChartTradeMarkers(json.data.trades || []);
                } else {
                    console.warn('[StrategyTester] Backtest response failed:', json);
                    const errMsg = (json && (json.detail || json.message)) || 'No strategy trades generated.';
                    this.renderEmptyOrError(errMsg);
                }
            } catch (err) {
                console.error('[StrategyTester] Execution error:', err);
                this.renderEmptyOrError('Execution error occurred while running backtest.');
            }
        }

        showDockLoading(strategyId) {
            if (!this.dockEl) this.createDockMarkup();
            if (!this.dockEl) return;

            this.dockEl.style.display = 'block';
            this.isOpen = true;

            const name = strategyId.replace(/^strat_/, '').replace(/_/g, ' ').toUpperCase();
            this.dockEl.querySelector('#strategy-dock-title').textContent = name;
            this.dockEl.querySelector('#strategy-dock-status').textContent = '⏳ Backtesting on real market data...';
        }

        renderResults(res) {
            if (!this.dockEl) return;

            const netPnl = res.net_pnl || (res.gross_pnl - (res.total_taxes_and_fees || 0)) || 0;
            const pnlColor = netPnl >= 0 ? '#089981' : '#F23645';
            const pnlPrefix = netPnl >= 0 ? '+₹' : '-₹';

            const netPnlEl = this.dockEl.querySelector('#kpi-net-profit');
            netPnlEl.textContent = `${pnlPrefix}${Math.abs(Math.round(netPnl)).toLocaleString('en-IN')}`;
            netPnlEl.style.color = pnlColor;

            this.dockEl.querySelector('#kpi-win-rate').textContent = `${(res.win_rate || 0).toFixed(1)}%`;
            this.dockEl.querySelector('#kpi-profit-factor').textContent = (res.profit_factor || 0).toFixed(2);
            this.dockEl.querySelector('#kpi-max-dd').textContent = `${(res.max_drawdown_pct || 0).toFixed(1)}%`;
            this.dockEl.querySelector('#kpi-total-trades').textContent = (res.total_trades || 0);

            this.dockEl.querySelector('#strategy-dock-status').textContent = `● Execution completed across ${res.total_trades || 0} signals`;
        }

        renderChartTradeMarkers(trades) {
            this.currentMarkers = [];

            if (trades && trades.length > 0) {
                for (const t of trades) {
                    // Entry Marker
                    const entryTime = this.parseTimeToUnix(t.entry_time);
                    if (entryTime) {
                        this.currentMarkers.push({
                            time: entryTime,
                            position: 'belowBar',
                            color: '#089981',
                            shape: 'arrowUp',
                            text: 'BUY',
                            id: `trade_entry_${entryTime}`
                        });
                    }

                    // Exit Marker
                    const exitTime = this.parseTimeToUnix(t.exit_time);
                    if (exitTime) {
                        this.currentMarkers.push({
                            time: exitTime,
                            position: 'aboveBar',
                            color: '#F23645',
                            shape: 'arrowDown',
                            text: 'SELL',
                            id: `trade_exit_${exitTime}`
                        });
                    }
                }
            }

            // Sync with chart pattern manager to combine markers cleanly
            if (window.chartPatternManager && typeof window.chartPatternManager.updateChartMarkers === 'function') {
                window.chartPatternManager.updateChartMarkers();
            } else if (window.candleSeries) {
                window.candleSeries.setMarkers(this.currentMarkers);
            }
        }

        renderEmptyOrError(message) {
            // Strictly zero synthetic data: Clear markers and show authentic error/empty state
            this.currentMarkers = [];
            if (window.candleSeries) {
                window.candleSeries.setMarkers([]);
            }
            if (window.chartPatternManager && typeof window.chartPatternManager.updateChartMarkers === 'function') {
                window.chartPatternManager.updateChartMarkers();
            }

            if (this.dockEl) {
                const netPnlEl = this.dockEl.querySelector('#kpi-net-profit');
                netPnlEl.textContent = '₹0';
                netPnlEl.style.color = '#787B86';
                this.dockEl.querySelector('#kpi-win-rate').textContent = '0.0%';
                this.dockEl.querySelector('#kpi-profit-factor').textContent = '0.00';
                this.dockEl.querySelector('#kpi-max-dd').textContent = '0.0%';
                this.dockEl.querySelector('#kpi-total-trades').textContent = '0';
                this.dockEl.querySelector('#strategy-dock-status').textContent = `⚠️ ${message || 'No backtest trades generated'}`;
            }
        }

        parseTimeToUnix(val) {
            if (!val) return null;
            if (typeof val === 'number') return val;
            const d = new Date(val);
            if (isNaN(d.getTime())) return null;
            return Math.floor(d.getTime() / 1000);
        }

        close() {
            if (this.dockEl) {
                this.dockEl.style.display = 'none';
            }
            this.isOpen = false;
            this.currentStrategy = null;
            this.currentMarkers = [];

            // Remove trade markers from series
            if (window.chartPatternManager && typeof window.chartPatternManager.updateChartMarkers === 'function') {
                window.chartPatternManager.updateChartMarkers();
            } else if (window.candleSeries) {
                window.candleSeries.setMarkers([]);
            }
        }
    }

    window.strategyTesterDock = new StrategyTesterDock();
    window.applyChartStrategy = function (strategyId, customInputs) {
        window.strategyTesterDock.runStrategy(strategyId, customInputs);
    };
})();
