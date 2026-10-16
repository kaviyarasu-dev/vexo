/**
 * journal_analytics.js
 * Journal Analytics UI: Monthly Green/Red Wall Calendar, Diagnostics Dashboard & Tabbed Workspace.
 * Integrates seamlessly with JournalUI to deliver institutional-grade journal visualization.
 */

(function () {
    class JournalAnalyticsController {
        constructor() {
            this.activeSubtab = 'calendar'; // 'calendar' | 'diagnostics' | 'trades' | 'mistakes'
            const now = new Date();
            this.currentYear = now.getFullYear();
            this.currentMonth = now.getMonth() + 1; // 1-12
            this.calendarData = null;
            this.diagnosticsData = null;
            this.selectedDateFilter = null;
            this.selectedBroker = 'AUTO';
            this.stagedFile = null;
        }

        async init() {
            this.bindSubtabs();
            this.bindCalendarControls();
            this.bindImportModal();
            this.hookJournalUI();

            // Load initial view data
            await this.loadCalendarMonth(this.currentYear, this.currentMonth);
            await this.loadDiagnostics();
        }

        hookJournalUI() {
            if (window.journalUI) {
                const origRefresh = window.journalUI.refresh.bind(window.journalUI);
                window.journalUI.refresh = async () => {
                    await origRefresh();
                    await this.loadCalendarMonth(this.currentYear, this.currentMonth);
                    await this.loadDiagnostics();
                };

                // Add switchJournalSubtab to window
                window.journalAnalyticsController = this;
            }
        }

        // ==========================================
        // 1. Subtab Bar Switching
        // ==========================================
        bindSubtabs() {
            document.querySelectorAll('.journal-subtab').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const subtab = e.currentTarget.dataset.subtab;
                    if (subtab) this.switchSubtab(subtab);
                });
            });

            // Date filter clear button
            const clearBtn = document.getElementById('btn-clear-date-filter');
            clearBtn?.addEventListener('click', () => this.clearDateFilter());
        }

        switchSubtab(subtabName) {
            this.activeSubtab = subtabName;

            // Update subtab buttons
            document.querySelectorAll('.journal-subtab').forEach(btn => {
                if (btn.dataset.subtab === subtabName) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // Update subpanels
            const panels = {
                calendar: document.getElementById('journal-calendar-panel'),
                diagnostics: document.getElementById('journal-diagnostics-panel'),
                trades: document.getElementById('journal-trades-panel'),
                mistakes: document.getElementById('journal-mistakes-panel')
            };

            Object.entries(panels).forEach(([name, el]) => {
                if (!el) return;
                if (name === subtabName) {
                    el.classList.remove('hidden');
                } else {
                    el.classList.add('hidden');
                }
            });

            if (subtabName === 'calendar' && !this.calendarData) {
                this.loadCalendarMonth(this.currentYear, this.currentMonth);
            } else if (subtabName === 'diagnostics' && !this.diagnosticsData) {
                this.loadDiagnostics();
            }
        }

        // ==========================================
        // 2. Wall Calendar Engine & Controls
        // ==========================================
        bindCalendarControls() {
            const btnPrev = document.getElementById('btn-calendar-prev');
            const btnNext = document.getElementById('btn-calendar-next');
            const btnToday = document.getElementById('btn-calendar-today');

            btnPrev?.addEventListener('click', () => {
                let y = this.currentYear;
                let m = this.currentMonth - 1;
                if (m < 1) {
                    m = 12;
                    y -= 1;
                }
                this.loadCalendarMonth(y, m);
            });

            btnNext?.addEventListener('click', () => {
                let y = this.currentYear;
                let m = this.currentMonth + 1;
                if (m > 12) {
                    m = 1;
                    y += 1;
                }
                this.loadCalendarMonth(y, m);
            });

            btnToday?.addEventListener('click', () => {
                const now = new Date();
                this.loadCalendarMonth(now.getFullYear(), now.getMonth() + 1);
            });
        }

        async loadCalendarMonth(year, month) {
            this.currentYear = year;
            this.currentMonth = month;
            try {
                const res = await fetch(`/api/v1/journal/calendar?year=${year}&month=${month}`);
                if (res.ok) {
                    this.calendarData = await res.json();
                    this.renderCalendar();
                } else {
                    console.error('[JournalAnalytics] Failed to fetch calendar:', res.statusText);
                }
            } catch (e) {
                console.error('[JournalAnalytics] Error fetching calendar:', e);
            }
        }

        renderCalendar() {
            if (!this.calendarData) return;

            const { year, month, days } = this.calendarData;
            const kpis = this.calendarData.kpis || this.calendarData.monthly_kpis;
            const weeks = this.calendarData.weeks || this.calendarData.weekly_summaries;

            // 1. Month Title
            const monthNames = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            const titleEl = document.getElementById('calendar-month-title');
            if (titleEl) {
                titleEl.textContent = `${monthNames[month - 1]} ${year}`;
            }

            const badgeEl = document.getElementById('calendar-active-month-badge');
            if (badgeEl) {
                badgeEl.textContent = `${monthNames[month - 1]} ${year} • IST`;
            }

            // 2. Render 6 Monthly KPIs
            this.renderMonthlyKPIs(kpis);

            // 3. Render Calendar 8-Column Grid
            const gridContainer = document.getElementById('journal-calendar-grid');
            if (!gridContainer) return;

            gridContainer.innerHTML = '';

            // Header Row: Mon - Sun + Weekly Total
            const colHeaders = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Week Total'];
            colHeaders.forEach((col, idx) => {
                const headerCell = document.createElement('div');
                headerCell.className = `calendar-header-cell ${idx === 7 ? 'weekly-col-header' : ''}`;
                headerCell.textContent = col;
                gridContainer.appendChild(headerCell);
            });

            // If empty month with no days
            if (!days || days.length === 0) {
                const emptyNotice = document.createElement('div');
                emptyNotice.className = 'calendar-empty-state';
                emptyNotice.textContent = 'No trade calendar data available for this month.';
                gridContainer.appendChild(emptyNotice);
                return;
            }

            // Group days into weeks based on day_of_week (0=Mon, 6=Sun)
            const firstDayOfWeek = days[0].day_of_week; // 0..6
            let currentWeekIndex = 0;
            let currentDayIdx = 0;

            // Renders up to 6 rows
            while (currentDayIdx < days.length) {
                // Render Monday through Sunday for this week
                for (let dow = 0; dow < 7; dow++) {
                    if (currentDayIdx === 0 && dow < firstDayOfWeek) {
                        // Padding empty cells before day 1
                        const emptyCell = document.createElement('div');
                        emptyCell.className = 'calendar-day-cell cell-empty';
                        gridContainer.appendChild(emptyCell);
                    } else if (currentDayIdx < days.length) {
                        const day = days[currentDayIdx];
                        const dayCell = this.createDayCell(day);
                        gridContainer.appendChild(dayCell);
                        currentDayIdx++;
                    } else {
                        // Trailing padding cells after last day of month
                        const emptyCell = document.createElement('div');
                        emptyCell.className = 'calendar-day-cell cell-empty';
                        gridContainer.appendChild(emptyCell);
                    }
                }

                // Append Weekly Summary Cell
                const weekSummary = (weeks && weeks[currentWeekIndex])
                    ? weeks[currentWeekIndex]
                    : null;
                const weekCell = this.createWeekSummaryCell(weekSummary);
                gridContainer.appendChild(weekCell);
                currentWeekIndex++;
            }
        }

        renderMonthlyKPIs(kpis) {
            if (!kpis) return;

            const netPnlEl = document.getElementById('cal-kpi-net-pnl');
            if (netPnlEl) {
                const pnl = kpis.monthly_net_pnl !== undefined ? kpis.monthly_net_pnl : (kpis.total_realized_pnl || 0);
                const sign = pnl >= 0 ? '+₹' : '-₹';
                netPnlEl.textContent = `${sign}${Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                netPnlEl.className = `metric-value font-mono ${pnl > 0 ? 'text-green' : pnl < 0 ? 'text-red' : ''}`;
            }

            const winLossDaysEl = document.getElementById('cal-kpi-win-loss-days');
            if (winLossDaysEl) {
                winLossDaysEl.textContent = `${kpis.win_days || 0}W / ${kpis.loss_days || 0}L`;
            }

            const winDayPctEl = document.getElementById('cal-kpi-win-day-pct');
            if (winDayPctEl) {
                const pct = ((kpis.win_day_pct || 0) * 100).toFixed(1);
                winDayPctEl.textContent = `${pct}%`;
                winDayPctEl.className = `metric-value font-mono ${parseFloat(pct) >= 50 ? 'text-green' : 'text-red'}`;
            }

            const winStreakEl = document.getElementById('cal-kpi-win-streak');
            if (winStreakEl) {
                winStreakEl.textContent = `${kpis.max_win_streak || 0} ${kpis.max_win_streak === 1 ? 'Day' : 'Days'}`;
            }

            const lossStreakEl = document.getElementById('cal-kpi-loss-streak');
            if (lossStreakEl) {
                lossStreakEl.textContent = `${kpis.max_loss_streak || 0} ${kpis.max_loss_streak === 1 ? 'Day' : 'Days'}`;
            }

            const avgWinLossEl = document.getElementById('cal-kpi-avg-win-loss');
            if (avgWinLossEl) {
                const avgWin = Math.round(kpis.avg_win_day_pnl !== undefined ? kpis.avg_win_day_pnl : (kpis.avg_win_day || 0));
                const avgLoss = Math.round(kpis.avg_loss_day_pnl !== undefined ? kpis.avg_loss_day_pnl : (kpis.avg_loss_day || 0));
                avgWinLossEl.textContent = `+₹${avgWin.toLocaleString('en-IN')} / -₹${avgLoss.toLocaleString('en-IN')}`;
            }
        }

        createDayCell(day) {
            const cell = document.createElement('div');
            cell.className = 'calendar-day-cell';
            cell.dataset.date = day.date;

            const tradesCount = day.trades_count !== undefined ? day.trades_count : (day.trade_count || 0);
            const hasTrades = tradesCount > 0;
            const pnl = day.net_pnl !== undefined ? day.net_pnl : (day.realized_pnl || 0);

            if (hasTrades) {
                cell.classList.add('cell-has-trades');
                if (pnl > 0) {
                    cell.classList.add('cell-win');
                } else if (pnl < 0) {
                    cell.classList.add('cell-loss');
                } else {
                    cell.classList.add('cell-even');
                }
            } else {
                cell.classList.add('cell-no-trades');
            }

            if (this.selectedDateFilter === day.date) {
                cell.classList.add('cell-selected');
            }

            const dayNum = document.createElement('div');
            dayNum.className = 'cell-day-num';
            dayNum.textContent = day.day_of_month;
            cell.appendChild(dayNum);

            if (hasTrades) {
                const pnlEl = document.createElement('div');
                const sign = pnl >= 0 ? '+₹' : '-₹';
                pnlEl.className = `cell-pnl-val font-mono ${pnl > 0 ? 'text-green' : pnl < 0 ? 'text-red' : ''}`;
                pnlEl.textContent = `${sign}${Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
                cell.appendChild(pnlEl);

                const badge = document.createElement('div');
                badge.className = 'cell-trade-badge';
                badge.textContent = `${tradesCount}T • ${day.win_count || 0}W ${day.loss_count || 0}L`;
                cell.appendChild(badge);

                // Hover tooltip
                cell.title = `${day.date}: Net ₹${pnl.toFixed(2)} (${tradesCount} Trades: ${day.win_count || 0} Wins, ${day.loss_count || 0} Losses)`;

                // Click-to-filter interaction
                cell.addEventListener('click', () => {
                    this.filterTradesByDate(day.date);
                });
            }

            return cell;
        }

        createWeekSummaryCell(weekSummary) {
            const cell = document.createElement('div');
            cell.className = 'calendar-week-cell';

            const tradesCount = weekSummary ? (weekSummary.trades_count !== undefined ? weekSummary.trades_count : (weekSummary.trade_count || 0)) : 0;

            if (!weekSummary || tradesCount === 0) {
                cell.innerHTML = `
                    <div class="week-cell-title">Week</div>
                    <div class="week-pnl-val text-muted">₹0</div>
                    <div class="week-trades-sub">0 Trades</div>
                `;
                return cell;
            }

            const pnl = weekSummary.net_pnl !== undefined ? weekSummary.net_pnl : (weekSummary.weekly_pnl || 0);
            const sign = pnl >= 0 ? '+₹' : '-₹';
            const pnlClass = pnl > 0 ? 'text-green' : pnl < 0 ? 'text-red' : '';
            const winRate = weekSummary.win_rate !== undefined ? weekSummary.win_rate : (tradesCount > 0 ? (weekSummary.win_count || 0) / tradesCount : 0);
            const winPct = (winRate * 100).toFixed(0);

            cell.className = `calendar-week-cell ${pnl > 0 ? 'week-win' : pnl < 0 ? 'week-loss' : ''}`;
            cell.innerHTML = `
                <div class="week-cell-title">Week ${weekSummary.week_number}</div>
                <div class="week-pnl-val font-mono ${pnlClass}">${sign}${Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
                <div class="week-trades-sub">${tradesCount} Trd • ${winPct}% Win</div>
            `;
            return cell;
        }

        // ==========================================
        // 3. Click-to-Filter Trade Ledger
        // ==========================================
        filterTradesByDate(dateStr) {
            this.selectedDateFilter = dateStr;

            // Re-render calendar so selected date gets glowing outline
            this.renderCalendar();

            // Switch to Trades tab
            this.switchSubtab('trades');

            // Update filter indicator
            const indicator = document.getElementById('journal-date-filter-indicator');
            const textEl = document.getElementById('journal-date-filter-text');
            if (indicator && textEl) {
                textEl.textContent = `Filtered by Date: ${dateStr}`;
                indicator.classList.remove('hidden');
            }

            // Filter trades table
            this.applyTableDateFilter(dateStr);
        }

        clearDateFilter() {
            this.selectedDateFilter = null;
            const indicator = document.getElementById('journal-date-filter-indicator');
            indicator?.classList.add('hidden');

            if (window.journalUI && typeof window.journalUI.renderTrades === 'function') {
                window.journalUI.renderTrades();
            }

            // Re-render calendar to clear cell-selected state
            this.renderCalendar();
        }

        applyTableDateFilter(dateStr) {
            if (!window.journalUI || !window.journalUI.trades) return;

            const allTrades = window.journalUI.trades;
            const filtered = allTrades.filter(t => {
                const exitMatch = t.exit_time && String(t.exit_time).substring(0, 10) === dateStr;
                const entryMatch = t.entry_time && String(t.entry_time).substring(0, 10) === dateStr;
                return exitMatch || entryMatch;
            });

            const tbody = document.querySelector('#journal-trades-table tbody');
            const countBadge = document.getElementById('journal-trade-count-badge');
            if (countBadge) {
                countBadge.textContent = `${filtered.length} Trades (${dateStr})`;
            }

            if (!tbody) return;

            if (filtered.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="empty-journal-state">
                            <p>No trades executed on ${dateStr}.</p>
                            <button type="button" class="btn-secondary" onclick="window.journalAnalyticsController.clearDateFilter()">Clear Date Filter</button>
                        </td>
                    </tr>
                `;
                return;
            }

            const sorted = [...filtered].sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));

            tbody.innerHTML = sorted.map(t => {
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

        // ==========================================
        // 4. Quantitative Diagnostics Engine
        // ==========================================
        async loadDiagnostics() {
            try {
                const res = await fetch('/api/v1/journal/diagnostics');
                if (res.ok) {
                    this.diagnosticsData = await res.json();
                    this.renderDiagnostics();
                } else {
                    console.error('[JournalAnalytics] Failed to fetch diagnostics:', res.statusText);
                }
            } catch (e) {
                console.error('[JournalAnalytics] Error fetching diagnostics:', e);
            }
        }

        renderDiagnostics() {
            if (!this.diagnosticsData) return;

            const { time_of_day, direction, duration, holding_duration, instruments, instrument } = this.diagnosticsData;

            this.renderDiagnosticSection('diag-tod-container', time_of_day);
            this.renderDiagnosticSection('diag-direction-container', direction);
            this.renderDiagnosticSection('diag-duration-container', duration || holding_duration);
            this.renderDiagnosticSection('diag-instrument-container', instruments || instrument);
        }

        renderDiagnosticSection(containerId, buckets) {
            const container = document.getElementById(containerId);
            if (!container) return;

            if (!buckets || buckets.length === 0) {
                container.innerHTML = '<div class="text-muted text-xs p-2">No data recorded for this dimension.</div>';
                return;
            }

            // Find maximum trade count to scale horizontal bars
            const maxTrades = Math.max(...buckets.map(b => (b.trades_count !== undefined ? b.trades_count : (b.trade_count || 0))), 1);

            container.innerHTML = buckets.map(b => {
                const tradesCount = b.trades_count !== undefined ? b.trades_count : (b.trade_count || 0);
                const winPct = ((b.win_rate || 0) * 100).toFixed(1);
                const pnl = b.net_pnl || 0;
                const sign = pnl >= 0 ? '+₹' : '-₹';
                const pnlClass = pnl > 0 ? 'text-green' : pnl < 0 ? 'text-red' : 'text-muted';
                const barWidth = Math.max(Math.round((tradesCount / maxTrades) * 100), 4);
                const barClass = pnl >= 0 ? 'bar-green' : 'bar-red';

                return `
                    <div class="diag-bucket-item">
                        <div class="diag-bucket-header">
                            <span class="diag-bucket-label font-bold">${b.label}</span>
                            <span class="diag-bucket-pnl font-mono ${pnlClass}">${sign}${Math.abs(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                        <div class="diag-bar-track">
                            <div class="diag-bar-fill ${barClass}" style="width: ${barWidth}%;"></div>
                        </div>
                        <div class="diag-bucket-meta text-xs text-muted">
                            <span>${tradesCount} Trades</span>
                            <span class="${parseFloat(winPct) >= 50 ? 'text-green' : 'text-red'} font-semibold">${winPct}% Win</span>
                            <span>PF: ${b.profit_factor > 90 ? '∞' : (b.profit_factor || 0).toFixed(2)}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // ==========================================
        // 5. Multi-Broker Import Modal
        // ==========================================
        bindImportModal() {
            const btnOpen = document.getElementById('btn-import-tradebook');
            const modal = document.getElementById('import-tradebook-modal');
            const btnClose = document.getElementById('close-import-tradebook-modal');
            const btnCancel = document.getElementById('btn-modal-cancel-import');
            const dropzone = document.getElementById('tradebook-dropzone');
            const fileInput = document.getElementById('tradebook-modal-file-input');
            const btnDoImport = document.getElementById('btn-modal-do-import');

            // Open Modal
            btnOpen?.addEventListener('click', () => {
                this.resetImportModal();
                modal?.classList.remove('hidden');
            });

            // Close Modal
            const closeModal = () => modal?.classList.add('hidden');
            btnClose?.addEventListener('click', closeModal);
            btnCancel?.addEventListener('click', closeModal);
            modal?.addEventListener('click', (e) => {
                if (e.target === modal) closeModal();
            });

            // Broker Preset Buttons
            document.querySelectorAll('.broker-preset-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    document.querySelectorAll('.broker-preset-btn').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    this.selectedBroker = e.currentTarget.dataset.broker || 'AUTO';
                });
            });

            // Dropzone interactions
            dropzone?.addEventListener('click', () => fileInput?.click());

            dropzone?.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.classList.add('dropzone-active');
            });

            dropzone?.addEventListener('dragleave', () => {
                dropzone.classList.remove('dropzone-active');
            });

            dropzone?.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.classList.remove('dropzone-active');
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    this.handleStagedFile(e.dataTransfer.files[0]);
                }
            });

            fileInput?.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    this.handleStagedFile(e.target.files[0]);
                }
            });

            // Do Import Execution
            btnDoImport?.addEventListener('click', () => this.executeImport());
        }

        resetImportModal() {
            this.stagedFile = null;
            this.selectedBroker = 'AUTO';
            document.querySelectorAll('.broker-preset-btn').forEach(b => {
                if (b.dataset.broker === 'AUTO') b.classList.add('active');
                else b.classList.remove('active');
            });

            const badge = document.getElementById('import-detected-broker-badge');
            badge?.classList.add('hidden');

            const status = document.getElementById('import-modal-status');
            if (status) {
                status.classList.add('hidden');
                status.textContent = '';
            }

            const btnDoImport = document.getElementById('btn-modal-do-import');
            if (btnDoImport) btnDoImport.disabled = true;

            const fileInput = document.getElementById('tradebook-modal-file-input');
            if (fileInput) fileInput.value = '';
        }

        async handleStagedFile(file) {
            this.stagedFile = file;

            const btnDoImport = document.getElementById('btn-modal-do-import');
            if (btnDoImport) btnDoImport.disabled = false;

            // Read first chunk of text to detect broker format
            try {
                const text = await file.slice(0, 1024).text();
                const detected = this.detectBrokerFormat(text);

                const badge = document.getElementById('import-detected-broker-badge');
                const badgeText = document.getElementById('detected-broker-text');

                if (badge && badgeText) {
                    badge.classList.remove('hidden');
                    if (detected) {
                        badge.className = 'detected-broker-badge badge-success';
                        badgeText.innerHTML = `Auto-Detected Format: <strong>${detected}</strong> ✓`;
                    } else {
                        badge.className = 'detected-broker-badge badge-warning';
                        badgeText.innerHTML = `Format: <strong>Custom / Unverified</strong> (Will attempt auto-detection)`;
                    }
                }
            } catch (err) {
                console.warn('[JournalAnalytics] Could not preview CSV header:', err);
            }
        }

        detectBrokerFormat(headerText) {
            const h = headerText.toLowerCase();
            if (h.includes('trade date') && h.includes('trade price') && (h.includes('order number') || h.includes('fyers'))) {
                return 'FYERS';
            }
            if (h.includes('trade_date') && h.includes('trade_type') && h.includes('order_execution_time')) {
                return 'Zerodha Console';
            }
            if (h.includes('isin') && (h.includes('execution date') || h.includes('type')) && h.includes('rate')) {
                return 'Groww';
            }
            return null;
        }

        async executeImport() {
            if (!this.stagedFile) return;

            const status = document.getElementById('import-modal-status');
            const btnDoImport = document.getElementById('btn-modal-do-import');

            if (status) {
                status.className = 'import-status-banner info';
                status.textContent = 'Uploading and reconciling tradebook fills...';
                status.classList.remove('hidden');
            }
            if (btnDoImport) btnDoImport.disabled = true;

            const formData = new FormData();
            formData.append('file', this.stagedFile);
            if (this.selectedBroker && this.selectedBroker !== 'AUTO') {
                formData.append('broker', this.selectedBroker);
            }

            try {
                const res = await fetch('/api/v1/journal/import', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();

                if (res.ok) {
                    if (status) {
                        status.className = 'import-status-banner success';
                        status.textContent = `✓ Successfully imported ${data.imported_trades} trades via ${data.broker_detected}!`;
                    }

                    setTimeout(async () => {
                        const modal = document.getElementById('import-tradebook-modal');
                        modal?.classList.add('hidden');
                        if (window.journalUI) {
                            await window.journalUI.refresh();
                        } else {
                            await this.loadCalendarMonth(this.currentYear, this.currentMonth);
                            await this.loadDiagnostics();
                        }
                    }, 1200);
                } else {
                    const msg = (data.error && data.error.message) || data.detail || 'Import failed.';
                    if (status) {
                        status.className = 'import-status-banner error';
                        status.textContent = `Error: ${msg}`;
                    }
                    if (btnDoImport) btnDoImport.disabled = false;
                }
            } catch (err) {
                console.error('[JournalAnalytics] Import request failed:', err);
                if (status) {
                    status.className = 'import-status-banner error';
                    status.textContent = 'Network or server error during tradebook import.';
                }
                if (btnDoImport) btnDoImport.disabled = false;
            }
        }
    }

    // Expose class and instantiate on DOMContentLoaded
    window.JournalAnalyticsController = JournalAnalyticsController;

    document.addEventListener('DOMContentLoaded', () => {
        window.journalAnalyticsController = new JournalAnalyticsController();
        window.journalAnalyticsController.init();
    });
})();
