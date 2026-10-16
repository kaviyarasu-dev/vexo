class JournalUI {
    constructor() {
        this.trades = [];
        this.metrics = {
            win_rate: 0,
            average_r: 0,
            expectancy: 0,
            cost_of_mistakes: 0,
            total_trades: 0,
            net_pnl: 0
        };
        this.isInitialized = false;
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.refresh();
        this.isInitialized = true;
    }

    bindEvents() {
        // 1. Open Log Trade Modal
        const btnOpenLog = document.getElementById('btn-open-log-trade');
        const modalLog = document.getElementById('log-trade-modal');
        const btnCloseLog = document.getElementById('close-log-trade-modal');
        const btnCancelLog = document.getElementById('btn-cancel-log-trade');

        btnOpenLog?.addEventListener('click', () => {
            modalLog?.classList.remove('hidden');
        });

        const closeModal = () => modalLog?.classList.add('hidden');
        btnCloseLog?.addEventListener('click', closeModal);
        btnCancelLog?.addEventListener('click', closeModal);
        modalLog?.addEventListener('click', (e) => {
            if (e.target === modalLog) closeModal();
        });

        // 2. Form submission for Manual Trade
        const form = document.getElementById('log-trade-form');
        form?.addEventListener('submit', (e) => this.handleTradeSubmit(e));

        // 3. File upload for FYERS CSV Tradebook
        const btnImport = document.getElementById('btn-import-tradebook');
        const fileInput = document.getElementById('tradebook-upload');
        btnImport?.addEventListener('click', () => fileInput?.click());
        fileInput?.addEventListener('change', (e) => this.handleFileUpload(e));

        // 4. Sample Trades Button
        const btnSample = document.getElementById('btn-load-sample-trades');
        btnSample?.addEventListener('click', () => this.handleLoadSampleTrades());

        // 5. Clear All Journal Trades
        const btnClear = document.getElementById('btn-clear-journal');
        btnClear?.addEventListener('click', () => this.handleClearTrades());

        // 6. Delete Trade row delegation
        const table = document.getElementById('journal-trades-table');
        table?.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.btn-delete-trade');
            if (deleteBtn) {
                const tradeId = deleteBtn.dataset.tradeId;
                if (tradeId) this.handleDeleteTrade(tradeId);
            }
        });
    }

    async refresh() {
        await this.fetchMetrics();
        await this.fetchTrades();
        this.renderMetrics();
        this.renderTrades();
        this.renderEquityCurve();
        this.renderMistakeCloud();
    }

    async fetchMetrics() {
        try {
            const res = await fetch('/api/v1/journal/metrics');
            if (res.ok) {
                this.metrics = await res.json();
            }
        } catch (e) {
            console.error('[JournalUI] Error fetching metrics:', e);
        }
    }

    async fetchTrades() {
        try {
            const res = await fetch('/api/v1/journal/trades');
            if (res.ok) {
                this.trades = await res.json();
            }
        } catch (e) {
            console.error('[JournalUI] Error fetching trades:', e);
        }
    }

    renderMetrics() {
        const container = document.getElementById('journal-metrics');
        if (!container) return;

        const m = this.metrics || {};
        const winRate = ((m.win_rate || 0) * 100).toFixed(1);
        const avgR = (m.average_r || 0).toFixed(2);
        const expectancy = (m.expectancy || 0).toFixed(2);
        const netPnl = (m.net_pnl || 0);
        const costMistakes = (m.cost_of_mistakes || 0);

        const netPnlClass = netPnl >= 0 ? 'text-green' : 'text-red';
        const formattedNetPnl = (netPnl >= 0 ? '+₹' : '-₹') + Math.abs(netPnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const formattedCostMistakes = '₹' + costMistakes.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

        container.innerHTML = `
            <div class="metric-card">
                <h3>Win Rate</h3>
                <p class="${parseFloat(winRate) >= 50 ? 'text-green' : ''}">${winRate}%</p>
                <span class="text-sm text-muted">${m.total_trades || 0} Total Executions</span>
            </div>
            <div class="metric-card">
                <h3>Average R</h3>
                <p class="${parseFloat(avgR) >= 1 ? 'text-green' : ''}">${avgR}R</p>
                <span class="text-sm text-muted">Risk-Adjusted Return</span>
            </div>
            <div class="metric-card">
                <h3>Expectancy</h3>
                <p class="${parseFloat(expectancy) > 0 ? 'text-green' : 'text-red'}">${expectancy}R</p>
                <span class="text-sm text-muted">Per Trade Mathematical Edge</span>
            </div>
            <div class="metric-card">
                <h3>Net Realized P&L</h3>
                <p class="${netPnlClass}">${formattedNetPnl}</p>
                <span class="text-sm text-muted">Post-Brokerage & Statutory Taxes</span>
            </div>
            <div class="metric-card mistake-cost">
                <h3>Cost of Mistakes</h3>
                <p>${formattedCostMistakes}</p>
                <span class="text-sm text-muted">Capital Lost to Execution Errors</span>
            </div>
        `;

        const mistakeBadge = document.getElementById('journal-mistake-cost-badge');
        if (mistakeBadge) {
            mistakeBadge.textContent = `Cost of Mistakes: ${formattedCostMistakes}`;
        }
    }

    renderTrades() {
        const tbody = document.querySelector('#journal-trades-table tbody');
        const countBadge = document.getElementById('journal-trade-count-badge');
        if (countBadge) {
            countBadge.textContent = `${this.trades.length} Trades`;
        }

        if (!tbody) return;

        if (this.trades.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-journal-state">
                        <p>No trades found in the journal database.</p>
                        <button type="button" class="btn-primary" onclick="window.journalUI.handleLoadSampleTrades()">⚡ Load Institutional Sample Trades</button>
                    </td>
                </tr>
            `;
            return;
        }

        const sortedTrades = [...this.trades].sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));

        tbody.innerHTML = sortedTrades.map(t => {
            const entryDate = t.entry_time ? new Date(t.entry_time).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-';
            const directionClass = t.direction === 'LONG' ? 'badge-pill text-green' : 'badge-pill text-red';
            const pnl = t.pnl_net || 0;
            const pnlClass = pnl >= 0 ? 'text-green font-bold' : 'text-red font-bold';
            const formattedPnl = (pnl >= 0 ? '+₹' : '-₹') + Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2 });
            const rMult = (t.r_multiple !== null && t.r_multiple !== undefined) ? `${t.r_multiple > 0 ? '+' : ''}${t.r_multiple.toFixed(2)}R` : '-';
            const rClass = (t.r_multiple || 0) >= 0 ? 'text-green' : 'text-red';

            const tagsHtml = (t.mistake_tags && t.mistake_tags.length > 0)
                ? t.mistake_tags.map(tag => `<span class="badge-pill text-red" style="font-size: 11px; margin-right: 4px;">${tag}</span>`).join('')
                : '<span class="text-muted" style="font-size: 11px;">Clean Discipline ✓</span>';

            return `
                <tr>
                    <td style="white-space: nowrap; font-size: 12px;">${entryDate}</td>
                    <td class="font-bold">${t.symbol}</td>
                    <td><span class="${directionClass}">${t.direction}</span></td>
                    <td class="font-mono">${t.quantity}</td>
                    <td class="font-mono">₹${(t.entry_price || 0).toFixed(2)}</td>
                    <td class="font-mono">${t.exit_price ? '₹' + t.exit_price.toFixed(2) : '-'}</td>
                    <td class="font-mono ${rClass}">${rMult}</td>
                    <td class="${pnlClass} font-mono">${formattedPnl}</td>
                    <td>${tagsHtml}</td>
                    <td class="text-center">
                        <button class="btn-delete-trade" data-trade-id="${t.trade_id}" title="Delete trade">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    renderEquityCurve() {
        const container = document.getElementById('equity-curve-chart');
        if (!container) return;

        if (this.trades.length === 0) {
            container.innerHTML = `
                <div style="height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); font-size: 13px;">
                    Log trades or click "Load Sample Trades" to visualize your cumulative equity curve.
                </div>
            `;
            return;
        }

        // Chronological order for equity curve
        const sortedTrades = [...this.trades].sort((a, b) => new Date(a.entry_time) - new Date(b.entry_time));

        let cumulative = 0;
        const curvePoints = [{ xLabel: 'Start', pnl: 0, cumulative: 0 }];
        sortedTrades.forEach((t, idx) => {
            cumulative += (t.pnl_net || 0);
            const dateStr = t.entry_time ? new Date(t.entry_time).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : `T#${idx + 1}`;
            curvePoints.push({
                xLabel: dateStr,
                symbol: t.symbol,
                pnl: t.pnl_net || 0,
                cumulative: cumulative
            });
        });

        // Summary badge
        const summaryBadge = document.getElementById('journal-equity-summary');
        if (summaryBadge) {
            const finalPnl = curvePoints[curvePoints.length - 1].cumulative;
            const sign = finalPnl >= 0 ? '+₹' : '-₹';
            summaryBadge.textContent = `Cumulative Equity: ${sign}${Math.abs(finalPnl).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
            summaryBadge.className = `badge-pill ${finalPnl >= 0 ? 'text-green' : 'text-red'}`;
        }

        // High-fidelity SVG render
        const width = 850;
        const height = 260;
        const padLeft = 70;
        const padRight = 30;
        const padTop = 25;
        const padBottom = 35;

        const allValues = curvePoints.map(p => p.cumulative);
        let minVal = Math.min(0, ...allValues);
        let maxVal = Math.max(0, ...allValues);
        if (minVal === maxVal) {
            minVal -= 1000;
            maxVal += 1000;
        }
        const valRange = maxVal - minVal;

        const getX = (idx) => padLeft + (idx / (curvePoints.length - 1)) * (width - padLeft - padRight);
        const getY = (val) => padTop + (1 - (val - minVal) / valRange) * (height - padTop - padBottom);

        const zeroY = getY(0);

        // Path generator
        let lineD = '';
        curvePoints.forEach((p, idx) => {
            const x = getX(idx);
            const y = getY(p.cumulative);
            lineD += (idx === 0) ? `M ${x} ${y}` : ` L ${x} ${y}`;
        });

        // Area path
        const firstX = getX(0);
        const lastX = getX(curvePoints.length - 1);
        const areaD = `${lineD} L ${lastX} ${zeroY} L ${firstX} ${zeroY} Z`;

        const isOverallPositive = cumulative >= 0;
        const strokeColor = isOverallPositive ? '#4ade80' : '#f87171';
        const fillColor = isOverallPositive ? 'url(#greenGradient)' : 'url(#redGradient)';

        // Data point circles
        const circlesHtml = curvePoints.map((p, idx) => {
            const x = getX(idx);
            const y = getY(p.cumulative);
            const pointPnl = (p.pnl >= 0 ? '+₹' : '-₹') + Math.abs(p.pnl).toLocaleString('en-IN', { minimumFractionDigits: 2 });
            const pointCum = (p.cumulative >= 0 ? '+₹' : '-₹') + Math.abs(p.cumulative).toLocaleString('en-IN', { minimumFractionDigits: 2 });
            const title = `${p.xLabel} ${p.symbol || ''}\nTrade P&L: ${pointPnl}\nCumulative: ${pointCum}`;
            return `<circle cx="${x}" cy="${y}" r="4" fill="${strokeColor}" stroke="#131722" stroke-width="2">
                <title>${title}</title>
            </circle>`;
        }).join('');

        // Grid lines and labels
        const gridSteps = 4;
        let gridHtml = '';
        for (let i = 0; i <= gridSteps; i++) {
            const val = minVal + (valRange * (i / gridSteps));
            const y = getY(val);
            const formattedLabel = (val >= 0 ? '₹' : '-₹') + Math.abs(Math.round(val)).toLocaleString('en-IN');
            gridHtml += `
                <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="rgba(255, 255, 255, 0.08)" stroke-dasharray="3,3" />
                <text x="${padLeft - 8}" y="${y + 4}" fill="#787B86" font-size="10" text-anchor="end" font-family="monospace">${formattedLabel}</text>
            `;
        }

        // Zero line
        gridHtml += `
            <line x1="${padLeft}" y1="${zeroY}" x2="${width - padRight}" y2="${zeroY}" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1.5" />
        `;

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: 100%; overflow: visible;" preserveAspectRatio="none">
                <defs>
                    <linearGradient id="greenGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#4ade80" stop-opacity="0.35"/>
                        <stop offset="100%" stop-color="#4ade80" stop-opacity="0.0"/>
                    </linearGradient>
                    <linearGradient id="redGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#f87171" stop-opacity="0.35"/>
                        <stop offset="100%" stop-color="#f87171" stop-opacity="0.0"/>
                    </linearGradient>
                </defs>
                ${gridHtml}
                <path d="${areaD}" fill="${fillColor}" />
                <path d="${lineD}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linejoin="round" />
                ${circlesHtml}
            </svg>
        `;
    }

    renderMistakeCloud() {
        const container = document.getElementById('mistake-cloud');
        if (!container) return;

        const counts = {};
        const costs = {};

        this.trades.forEach(t => {
            const tags = t.mistake_tags || [];
            const loss = (t.pnl_net || 0) < 0 ? Math.abs(t.pnl_net || 0) : 0;
            tags.forEach(tag => {
                counts[tag] = (counts[tag] || 0) + 1;
                costs[tag] = (costs[tag] || 0) + loss;
            });
        });

        const entries = Object.entries(counts);
        if (entries.length === 0) {
            container.innerHTML = `
                <div style="color: var(--text-secondary); font-size: 13px; padding: 12px;">
                    🎯 No psychological mistakes logged. 100% disciplined execution!
                </div>
            `;
            return;
        }

        container.innerHTML = entries.map(([tag, count]) => {
            const cost = costs[tag] || 0;
            const costFormatted = cost > 0 ? `₹${cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '₹0';
            return `
                <div class="mistake-tag-chip">
                    <span>${tag}</span>
                    <span class="tag-count-badge" title="Recurrence count">${count}x</span>
                    <span class="tag-cost-badge" title="Capital lost to this mistake">- ${costFormatted}</span>
                </div>
            `;
        }).join('');
    }

    async handleTradeSubmit(event) {
        event.preventDefault();
        const modal = document.getElementById('log-trade-modal');

        const symbol = document.getElementById('trade-input-symbol')?.value?.trim();
        const direction = document.getElementById('trade-input-direction')?.value;
        const tradeType = document.getElementById('trade-input-type')?.value;
        const entryPrice = parseFloat(document.getElementById('trade-input-entry')?.value);
        const exitPrice = parseFloat(document.getElementById('trade-input-exit')?.value);
        const quantity = parseInt(document.getElementById('trade-input-qty')?.value, 10);
        const stopLoss = parseFloat(document.getElementById('trade-input-sl')?.value);
        const notes = document.getElementById('trade-input-notes')?.value;

        const selectedTags = [];
        document.querySelectorAll('input[name="mistake-tag"]:checked').forEach(cb => {
            selectedTags.push(cb.value);
        });

        if (!symbol || isNaN(entryPrice) || isNaN(quantity) || isNaN(stopLoss)) {
            alert('Please fill all required trade fields.');
            return;
        }

        try {
            const res = await fetch('/api/v1/journal/trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    direction: direction,
                    trade_type: tradeType,
                    entry_price: entryPrice,
                    exit_price: isNaN(exitPrice) ? null : exitPrice,
                    quantity: quantity,
                    stop_loss: stopLoss,
                    mistake_tags: selectedTags,
                    notes: notes
                })
            });

            if (res.ok) {
                modal?.classList.add('hidden');
                event.target.reset();
                await this.refresh();
            } else {
                const err = await res.json();
                alert(`Error saving trade: ${err.detail || err.message || 'Unknown error'}`);
            }
        } catch (e) {
            console.error('[JournalUI] Save trade error:', e);
            alert('Failed to save trade.');
        }
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('broker', 'FYERS');

        try {
            const res = await fetch('/api/v1/journal/import', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                alert(`Successfully imported ${data.imported_trades} trades!`);
                await this.refresh();
            } else {
                alert(`Import failed: ${data.detail || 'Invalid format'}`);
            }
        } catch (e) {
            console.error('[JournalUI] Upload error:', e);
            alert('Error uploading tradebook CSV.');
        } finally {
            event.target.value = '';
        }
    }

    async handleLoadSampleTrades() {
        try {
            const res = await fetch('/api/v1/journal/sample-data', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                await this.refresh();
                alert(`Successfully loaded ${data.seeded_count || 92} sample trades from tradebook!`);
            } else {
                alert('Failed to load sample trades.');
            }
        } catch (e) {
            console.error('[JournalUI] Sample data error:', e);
            alert('Error loading sample trades.');
        }
    }

    async handleClearTrades() {
        if (!confirm('Are you sure you want to clear all trades in the journal?')) return;
        try {
            const res = await fetch('/api/v1/journal/clear', { method: 'DELETE' });
            if (res.ok) {
                await this.refresh();
            } else {
                alert('Failed to clear journal.');
            }
        } catch (e) {
            console.error('[JournalUI] Clear trades error:', e);
            alert('Error clearing journal.');
        }
    }

    async handleDeleteTrade(tradeId) {
        if (!confirm('Delete this trade entry?')) return;
        try {
            const res = await fetch(`/api/v1/journal/trades/${tradeId}`, { method: 'DELETE' });
            if (res.ok) {
                await this.refresh();
            } else {
                alert('Failed to delete trade.');
            }
        } catch (e) {
            console.error('[JournalUI] Delete trade error:', e);
            alert('Error deleting trade.');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.journalUI = new JournalUI();
});
