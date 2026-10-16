/**
 * Backtest Paper Deploy & Telemetry Sync Module
 * Bridges Quant Backtest Studio strategies with the Paper Trading Engine.
 */
class BacktestPaperDeployHelper {
    static async deployFromConfig(config) {
        if (!config || !config.strategy || !config.symbol) {
            throw new Error('Invalid strategy configuration: strategy and symbol are required.');
        }

        const payload = {
            strategy_name: config.strategy,
            symbol: config.symbol,
            timeframe: config.timeframe || '1D',
            parameters: config.parameters || {},
            trade_type: config.trade_type || 'DELIVERY',
            allocated_capital: parseFloat(config.initial_capital) || 100000.0
        };

        const res = await fetch('/api/v1/paper-trading/deploy-strategy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.detail || data.message || 'Failed to deploy strategy');
        }

        // Notify user and synchronize UI dock
        if (window.chartPaperTradeManager && typeof window.chartPaperTradeManager.showToast === 'function') {
            window.chartPaperTradeManager.showToast(
                'Strategy Deployed! 🤖',
                `${payload.strategy_name} deployed on ${payload.symbol} (₹${payload.allocated_capital.toLocaleString('en-IN')})`,
                'success'
            );
        }

        if (window.paperTerminalDock) {
            if (window.paperTerminalDock.isCollapsed) {
                window.paperTerminalDock.toggleCollapse();
            }
            window.paperTerminalDock.switchTab('strategies');
            await window.paperTerminalDock.refreshAll();
        }

        return data.data;
    }

    static async evaluateActiveStrategies(symbol = null) {
        const url = symbol 
            ? `/api/v1/paper-trading/auto-strategies/evaluate?symbol=${encodeURIComponent(symbol)}`
            : '/api/v1/paper-trading/auto-strategies/evaluate';

        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();
        return data;
    }
}

// Attach globally
window.BacktestPaperDeployHelper = BacktestPaperDeployHelper;
