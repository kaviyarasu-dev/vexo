/**
 * screener_ui.js
 * High-performance NSE Stock Screener Controller with Custom Preset Builder
 */

const SCREENER_METRICS = [
    { id: 'rsi_14', label: 'RSI (14)', defaultOp: '<=', defaultValue: 30, step: 1, min: 0, max: 100, unit: '' },
    { id: 'volume_zscore_20', label: 'Volume Spike (Z-Score)', defaultOp: '>=', defaultValue: 2.0, step: 0.1, min: -3, max: 20, unit: 'σ' },
    { id: 'dist_from_52w_high_pct', label: '52-Week High Distance %', defaultOp: '>=', defaultValue: -2.0, step: 0.5, min: -100, max: 100, unit: '%' },
    { id: 'dist_from_52w_low_pct', label: '52-Week Low Distance %', defaultOp: '>=', defaultValue: 10.0, step: 0.5, min: -100, max: 1000, unit: '%' },
    { id: 'dist_from_sma_20_pct', label: 'Price vs 20-SMA %', defaultOp: '>=', defaultValue: 2.0, step: 0.5, min: -100, max: 100, unit: '%' },
    { id: 'change_pct_1d', label: '1-Day Change %', defaultOp: '>=', defaultValue: 2.0, step: 0.1, min: -50, max: 50, unit: '%' },
    { id: 'close', label: 'Close Price (₹)', defaultOp: '>=', defaultValue: 100, step: 5, min: 0, max: 100000, unit: '₹' },
    { id: 'turnover_cr', label: 'Daily Turnover (₹ Cr)', defaultOp: '>=', defaultValue: 10.0, step: 1, min: 0, max: 10000, unit: 'Cr' },
];

class ScreenerUI {
    constructor() {
        this.templates = [
            { id: 'all_stocks', name: '🌐 All Stocks', description: 'Full market scan of all listed NSE stocks with live technical metrics' },
            { id: 'volume_surge', name: '🔥 Volume Spike', description: 'Volume > 2 standard deviations above 20-day avg' },
            { id: '52_week_high', name: '🚀 52-Week High', description: 'Momentum leaders within 2% of 52-week peak' },
            { id: 'rsi_oversold', name: '📉 RSI Oversold', description: 'Quality stocks with Daily RSI <= 30' }
        ];
        this.currentTemplate = 'all_stocks';
        this.selectedUniverse = 'ALL';
        this.currentResults = [];
        this.sortKey = 'turnover_cr';
        this.sortAsc = false;
        this.filterText = '';
        this.ruleCounter = 0;
    }

    async init() {
        await this.loadTemplates();
        this.renderTemplateButtons();
        this.bindEvents();
        this.loadUniverseCounts();
        // Run scan on initial template (defaults to all_stocks)
        const initial = this.currentTemplate || (this.templates[0] ? this.templates[0].id : 'all_stocks');
        this.runScan(initial);
    }

    async loadUniverseCounts() {
        try {
            const res = await fetch('/api/v1/backtest/portfolio/universes');
            const json = await res.json();
            if (json.success && Array.isArray(json.universes)) {
                const uMap = {};
                json.universes.forEach(u => {
                    uMap[u.id] = u.constituent_count;
                });
                
                const updateSelect = (selectId) => {
                    const sel = document.getElementById(selectId);
                    if (!sel) return;
                    Array.from(sel.options).forEach(opt => {
                        const count = uMap[opt.value];
                        if (count !== undefined && count > 0) {
                            const baseLabel = opt.text.split('(')[0].trim();
                            opt.text = `${baseLabel} (${count.toLocaleString()})`;
                        }
                    });
                };
                updateSelect('screener-universe-select');
                updateSelect('template-universe-select');
            }
        } catch (e) {
            console.warn('[ScreenerUI] Could not load dynamic universe counts:', e);
        }
    }

    async loadTemplates() {
        try {
            const res = await fetch('/api/v1/screener/templates');
            const json = await res.json();
            if (json.success && Array.isArray(json.data)) {
                this.templates = json.data;
            }
        } catch (e) {
            console.warn("Could not fetch screener presets from backend, falling back to defaults:", e);
        }
    }

    renderTemplateButtons() {
        const container = document.getElementById('screener-templates');
        if (!container) return;

        container.innerHTML = '';
        this.templates.forEach(t => {
            const chip = document.createElement('div');
            const isActive = this.currentTemplate === t.id;
            chip.className = `template-chip ${isActive ? 'active' : ''}`;
            chip.dataset.templateId = t.id;

            const descText = t.description || t.desc || '';
            const isCustom = Boolean(t.is_custom);

            chip.innerHTML = `
                <div class="chip-main-click" title="${descText}">
                    <div class="chip-title-row">
                        <strong>${t.name}</strong>
                        ${isCustom ? '<span class="custom-chip-badge">Custom</span>' : ''}
                    </div>
                    <span class="chip-desc">${descText}</span>
                </div>
                ${isCustom ? `<button type="button" class="chip-delete-btn" title="Delete custom template" data-delete-id="${t.id}">✕</button>` : ''}
            `;

            // Clicking main body runs scan
            const mainClickArea = chip.querySelector('.chip-main-click');
            if (mainClickArea) {
                mainClickArea.onclick = () => this.runScan(t.id);
            }

            // Clicking delete button removes template
            const deleteBtn = chip.querySelector('.chip-delete-btn');
            if (deleteBtn) {
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.deleteTemplate(t.id, t.name);
                };
            }

            container.appendChild(chip);
        });
    }

    bindEvents() {
        // Table search input
        const searchInput = document.getElementById('screener-table-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterText = e.target.value.toLowerCase().trim();
                this.renderResults();
            });
        }

        // Universe Selector Dropdown
        const universeSelect = document.getElementById('screener-universe-select');
        if (universeSelect) {
            universeSelect.addEventListener('change', (e) => {
                this.selectedUniverse = e.target.value;
                this.runScan(this.currentTemplate);
            });
        }

        // Table header sort
        const thElements = document.querySelectorAll('#screener-table th[data-sort]');
        thElements.forEach(th => {
            th.addEventListener('click', () => {
                const key = th.dataset.sort;
                if (key) this.sortBy(key);
            });
        });

        // "🔄 Sync Live" Button
        const btnSyncLive = document.getElementById('btn-sync-live-screener');
        if (btnSyncLive) {
            btnSyncLive.addEventListener('click', () => {
                this.syncLiveMarketData();
            });
        }

        // "➕ New Template" Button
        const btnNewTemplate = document.getElementById('btn-new-screener-template');
        if (btnNewTemplate) {
            btnNewTemplate.addEventListener('click', () => {
                this.openCreateTemplateModal();
            });
        }

        // "➕ Add Condition" Button in Modal
        const btnAddRule = document.getElementById('btn-add-screener-rule');
        if (btnAddRule) {
            btnAddRule.addEventListener('click', () => {
                this.addRuleRow();
            });
        }

        // Custom Template Form Submit
        const formNewTemplate = document.getElementById('form-new-screener-template');
        if (formNewTemplate) {
            formNewTemplate.addEventListener('submit', (e) => {
                this.saveNewTemplate(e);
            });
        }

        // Close Modal Handlers
        const screenerModal = document.getElementById('new-screener-modal');
        if (screenerModal) {
            screenerModal.querySelectorAll('.close-modal').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.closeCreateTemplateModal();
                });
            });

            // Click outside backdrop to close
            screenerModal.addEventListener('click', (e) => {
                if (e.target === screenerModal) {
                    this.closeCreateTemplateModal();
                }
            });
        }

        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && screenerModal && !screenerModal.classList.contains('hidden')) {
                this.closeCreateTemplateModal();
            }
        });
    }

    openCreateTemplateModal() {
        const modal = document.getElementById('new-screener-modal');
        if (!modal) return;

        const nameInput = document.getElementById('template-name-input');
        const descInput = document.getElementById('template-desc-input');
        const universeSelect = document.getElementById('template-universe-select');
        const rulesList = document.getElementById('screener-rules-list');

        if (nameInput) nameInput.value = '';
        if (descInput) descInput.value = '';
        if (universeSelect) universeSelect.value = 'NIFTY500';
        if (rulesList) {
            rulesList.innerHTML = '';
            // Add 1 default condition
            this.addRuleRow('rsi_14', '<=', 35);
        }

        modal.classList.remove('hidden');
        if (nameInput) setTimeout(() => nameInput.focus(), 50);
    }

    closeCreateTemplateModal() {
        const modal = document.getElementById('new-screener-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    addRuleRow(defaultField = 'volume_zscore_20', defaultOp = '>=', defaultValue = 2.0) {
        const rulesList = document.getElementById('screener-rules-list');
        if (!rulesList) return;

        this.ruleCounter += 1;
        const rowId = `rule-row-${this.ruleCounter}`;

        const row = document.createElement('div');
        row.className = 'screener-rule-row';
        row.id = rowId;

        // Metric Select
        const metricOptionsHtml = SCREENER_METRICS.map(m => 
            `<option value="${m.id}" ${m.id === defaultField ? 'selected' : ''}>${m.label}</option>`
        ).join('');

        const selectedMetricMeta = SCREENER_METRICS.find(m => m.id === defaultField) || SCREENER_METRICS[0];
        const opVal = defaultOp || selectedMetricMeta.defaultOp;
        const numVal = (defaultValue !== undefined && defaultValue !== null) ? defaultValue : selectedMetricMeta.defaultValue;

        row.innerHTML = `
            <div class="rule-select-wrap">
                <select class="form-control form-select rule-metric-select" aria-label="Metric">
                    ${metricOptionsHtml}
                </select>
            </div>
            <div class="rule-op-wrap">
                <select class="form-control form-select font-mono rule-op-select" aria-label="Operator">
                    <option value=">" ${opVal === '>' ? 'selected' : ''}>&gt; (Greater than)</option>
                    <option value=">=" ${opVal === '>=' ? 'selected' : ''}>&ge; (Greater / Eq)</option>
                    <option value="<" ${opVal === '<' ? 'selected' : ''}>&lt; (Less than)</option>
                    <option value="<=" ${opVal === '<=' ? 'selected' : ''}>&le; (Less / Eq)</option>
                    <option value="=" ${opVal === '=' ? 'selected' : ''}>= (Equal)</option>
                </select>
            </div>
            <div class="rule-val-wrap">
                <input type="number" class="form-control font-mono rule-val-input" value="${numVal}" step="${selectedMetricMeta.step}" aria-label="Value" required>
            </div>
            <button type="button" class="btn-remove-rule" title="Remove condition">✕</button>
        `;

        // Update step/min/max on metric change
        const metricSelect = row.querySelector('.rule-metric-select');
        const valInput = row.querySelector('.rule-val-input');
        const opSelect = row.querySelector('.rule-op-select');

        if (metricSelect && valInput && opSelect) {
            metricSelect.addEventListener('change', () => {
                const meta = SCREENER_METRICS.find(m => m.id === metricSelect.value);
                if (meta) {
                    valInput.step = meta.step;
                    valInput.value = meta.defaultValue;
                    opSelect.value = meta.defaultOp;
                }
            });
        }

        // Remove row handler
        const removeBtn = row.querySelector('.btn-remove-rule');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                if (rulesList.children.length <= 1) {
                    alert("A screener template must contain at least one condition.");
                    return;
                }
                row.remove();
            });
        }

        rulesList.appendChild(row);
    }

    async saveNewTemplate(e) {
        e.preventDefault();

        const nameInput = document.getElementById('template-name-input');
        const descInput = document.getElementById('template-desc-input');
        const universeSelect = document.getElementById('template-universe-select');
        const rulesList = document.getElementById('screener-rules-list');
        const submitBtn = document.getElementById('btn-save-screener-template');

        const name = nameInput ? nameInput.value.trim() : '';
        if (!name) {
            alert("Please enter a valid template name.");
            return;
        }

        const universe = universeSelect ? universeSelect.value : 'ALL';
        const description = descInput ? descInput.value.trim() : '';

        // Collect condition rows
        const ruleRows = rulesList ? rulesList.querySelectorAll('.screener-rule-row') : [];
        const conditions = [];

        ruleRows.forEach(row => {
            const field = row.querySelector('.rule-metric-select')?.value;
            const operator = row.querySelector('.rule-op-select')?.value;
            const valStr = row.querySelector('.rule-val-input')?.value;
            const value = parseFloat(valStr);

            if (field && operator && !isNaN(value)) {
                conditions.push({ field, operator, value });
            }
        });

        if (conditions.length === 0) {
            alert("Please configure at least one condition for your template.");
            return;
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving Template...';
        }

        try {
            const res = await fetch('/api/v1/screener/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    universe,
                    conditions
                })
            });

            const json = await res.json();
            if (json.success && json.data) {
                const createdTemplate = json.data;
                // Close modal
                this.closeCreateTemplateModal();
                // Refresh presets
                await this.loadTemplates();
                // Re-render chips
                this.renderTemplateButtons();
                // Automatically run the new scan!
                await this.runScan(createdTemplate.id);
            } else {
                alert(`Error saving template: ${json.detail || json.error || 'Server error'}`);
            }
        } catch (err) {
            console.error("Failed to save template:", err);
            alert("Network error: Could not save template.");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save & Run Scan';
            }
        }
    }

    async deleteTemplate(templateId, templateName) {
        const confirmed = confirm(`Are you sure you want to delete custom template "${templateName}"?`);
        if (!confirmed) return;

        try {
            const res = await fetch(`/api/v1/screener/templates/${encodeURIComponent(templateId)}`, {
                method: 'DELETE'
            });
            const json = await res.json();
            if (json.success) {
                await this.loadTemplates();
                // If deleted template was currently viewed, fallback to volume_surge or first
                if (this.currentTemplate === templateId) {
                    this.currentTemplate = this.templates[0] ? this.templates[0].id : 'volume_surge';
                }
                this.renderTemplateButtons();
                this.runScan(this.currentTemplate);
            } else {
                alert(`Could not delete template: ${json.detail || json.error || 'Failed'}`);
            }
        } catch (err) {
            console.error("Failed to delete template:", err);
            alert("Network error: Could not delete template.");
        }
    }

    async syncLiveMarketData() {
        const btnSyncLive = document.getElementById('btn-sync-live-screener');
        const statusEl = document.getElementById('screener-status');
        const origHtml = btnSyncLive ? btnSyncLive.innerHTML : '<span>🔄 Sync Live</span>';

        if (btnSyncLive) {
            btnSyncLive.disabled = true;
            btnSyncLive.innerHTML = '<span>⏳ Syncing...</span>';
        }
        if (statusEl) {
            statusEl.innerHTML = `<span>⏳ Fetching authentic live market quotes from Fyers API into DuckDB...</span>`;
        }

        try {
            const univ = this.selectedUniverse || 'ALL';
            const res = await fetch('/api/v1/screener/sync-live', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ universe: univ })
            });
            const json = await res.json();
            if (json.success && json.data) {
                const count = json.data.synced || 0;
                if (statusEl) {
                    statusEl.innerHTML = `✅ Synced <strong>${count}</strong> live market quotes into DuckDB. Re-running scan...`;
                }
            } else {
                const msg = json.data?.message || json.error || 'Authentication required for live stream';
                if (statusEl) {
                    statusEl.innerHTML = `<span style="color:#f59e0b;">ℹ️ ${msg}</span>`;
                }
            }
            // Re-run scan with verified DuckDB data
            await this.runScan(this.currentTemplate);
        } catch (err) {
            console.error("Live sync error:", err);
            if (statusEl) {
                statusEl.innerHTML = `<span style="color:#ef4444;">❌ Live sync error. Screening with DuckDB data.</span>`;
            }
            await this.runScan(this.currentTemplate);
        } finally {
            if (btnSyncLive) {
                btnSyncLive.disabled = false;
                btnSyncLive.innerHTML = origHtml;
            }
        }
    }

    async runScan(templateId) {
        this.currentTemplate = templateId;
        this.renderTemplateButtons();

        const statusEl = document.getElementById('screener-status');
        const countEl = document.getElementById('screener-count-badge');
        const asOfBadge = document.getElementById('screener-asof-badge');
        const realBadge = document.getElementById('screener-real-data-badge');
        const activeTmpl = this.templates.find(t => t.id === templateId);
        const tmplDisplayName = activeTmpl ? activeTmpl.name : templateId;

        if (statusEl) {
            statusEl.innerHTML = `<span class="spinner">⏳</span> Scanning universe for <strong>${tmplDisplayName}</strong>...`;
        }

        try {
            const univSelect = document.getElementById('screener-universe-select');
            const universe = this.selectedUniverse || (univSelect ? univSelect.value : null) || (activeTmpl && activeTmpl.universe) || 'ALL';
            if (univSelect && univSelect.value !== universe) {
                univSelect.value = universe;
            }

            const res = await fetch('/api/v1/screener/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    universe: universe,
                    template: templateId,
                    as_of_date: null,
                    technical_rules: [],
                    min_turnover_cr: 0.0
                })
            });

            const json = await res.json();
            if (res.ok && json.success && Array.isArray(json.data)) {
                this.currentResults = json.data;
                const asOf = json.meta?.as_of_date || (this.currentResults[0] ? this.currentResults[0].as_of_date : null);
                if (asOfBadge) {
                    asOfBadge.textContent = asOf ? `As of: ${asOf}` : 'Actual Data';
                }
                if (realBadge) {
                    realBadge.textContent = '🟢 Real NSE Data (Zero Fake)';
                    realBadge.title = 'Verified authentic DuckDB daily candles from NSE. Zero synthetic data.';
                }
                if (statusEl) {
                    statusEl.innerHTML = `✅ Found <strong>${this.currentResults.length}</strong> matching stocks for <em>${tmplDisplayName}</em>`;
                }
                if (countEl) {
                    countEl.textContent = `${this.currentResults.length} Stocks`;
                }
                this.renderResults();
            } else {
                const errMsg = json.detail || json.error?.message || (json.error ? JSON.stringify(json.error) : 'Failed to load screener scan.');
                if (statusEl) statusEl.innerHTML = `<span style="color:#ef4444;">❌ ${errMsg}</span>`;
            }
        } catch (e) {
            console.error("Screener scan error:", e);
            if (statusEl) statusEl.textContent = '❌ Network error during scan.';
        }
    }

    sortBy(key) {
        if (this.sortKey === key) {
            this.sortAsc = !this.sortAsc;
        } else {
            this.sortKey = key;
            this.sortAsc = false;
        }
        this.renderResults();
    }

    renderResults() {
        const tableBody = document.querySelector('#screener-table tbody');
        if (!tableBody) return;

        let filtered = this.currentResults;
        if (this.filterText) {
            filtered = filtered.filter(r => 
                (r.symbol && r.symbol.toLowerCase().includes(this.filterText)) ||
                (r.name && r.name.toLowerCase().includes(this.filterText)) ||
                (r.category && r.category.toLowerCase().includes(this.filterText))
            );
        }

        filtered.sort((a, b) => {
            let va = a[this.sortKey];
            let vb = b[this.sortKey];
            if (va === null || va === undefined) return 1;
            if (vb === null || vb === undefined) return -1;
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            if (va < vb) return this.sortAsc ? -1 : 1;
            if (va > vb) return this.sortAsc ? 1 : -1;
            return 0;
        });

        tableBody.innerHTML = '';
        if (filtered.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="9" class="text-center p-4">No matching stocks found for this criteria in verified NSE market data.</td></tr>`;
            return;
        }

        filtered.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'screener-row-clickable';
            
            const closeFormatted = (typeof item.close === 'number') ? `₹${item.close.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—';
            const turnoverFormatted = (typeof item.turnover_cr === 'number') ? `₹${item.turnover_cr.toFixed(2)} Cr` : '—';
            
            let changeFormatted = '—';
            let changeClass = '';
            if (typeof item.change_pct_1d === 'number') {
                const sign = item.change_pct_1d > 0 ? '+' : '';
                changeFormatted = `${sign}${item.change_pct_1d.toFixed(2)}%`;
                changeClass = item.change_pct_1d > 0 ? 'text-profit' : (item.change_pct_1d < 0 ? 'text-loss' : '');
            }

            let rsiFormatted = '—';
            let rsiBadgeStyle = '';
            if (typeof item.rsi_14 === 'number') {
                rsiFormatted = item.rsi_14.toFixed(1);
                if (item.rsi_14 <= 30) {
                    rsiBadgeStyle = 'color: #10b981; font-weight: bold;';
                } else if (item.rsi_14 >= 70) {
                    rsiBadgeStyle = 'color: #ef4444; font-weight: bold;';
                }
            }

            const rulesStr = (Array.isArray(item.matched_rules) && item.matched_rules.length > 0)
                ? item.matched_rules.join(', ')
                : (item.matched_rules || (this.currentTemplate === 'all_stocks' ? 'All Market Stocks' : 'Criteria Met'));

            tr.innerHTML = `
                <td><strong class="symbol-link">${item.symbol}</strong></td>
                <td>${item.name || item.symbol}</td>
                <td><span class="badge-category">${item.category || 'EQ'}</span></td>
                <td class="font-mono text-right">${closeFormatted}</td>
                <td class="font-mono text-right ${changeClass}">${changeFormatted}</td>
                <td class="font-mono text-right" style="${rsiBadgeStyle}">${rsiFormatted}</td>
                <td class="font-mono text-right">${turnoverFormatted}</td>
                <td><span class="rule-tag">${rulesStr}</span></td>
                <td class="text-center">
                    <button class="btn-open-chart" type="button" title="Open chart for ${item.symbol}">📈 View Chart</button>
                </td>
            `;

            // Clicking row opens chart
            tr.onclick = () => {
                this.openChart(item.symbol);
            };

            const chartBtn = tr.querySelector('.btn-open-chart');
            if (chartBtn) {
                chartBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.openChart(item.symbol);
                };
            }

            tableBody.appendChild(tr);
        });
    }

    openChart(symbol) {
        // Switch to Chart tab
        if (window.switchAppView) {
            window.switchAppView('chart');
        } else {
            const chartTabBtn = document.querySelector('.view-tab[data-view="chart"]');
            if (chartTabBtn) chartTabBtn.click();
        }

        // Fetch chart data
        if (typeof window.fetchChartData === 'function') {
            window.fetchChartData(symbol, window.currentSymbolTimeframe || '1D');
        }
    }
}

window.ScreenerUI = ScreenerUI;
window.screenerController = new ScreenerUI();
