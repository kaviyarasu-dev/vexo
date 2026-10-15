document.addEventListener('DOMContentLoaded', () => {
    // Enforce Pro Mode Permanently
    document.body.classList.add('pro-mode-enabled');
    document.documentElement.classList.add('mode-pro');
    document.documentElement.classList.remove('mode-simple');
    localStorage.setItem('quant_app_mode', 'pro');

    if (window.uxModeController) {
        window.uxModeController.setMode('pro');
    } else {
        window.dispatchEvent(new CustomEvent('uxModeChanged', { detail: { mode: 'pro' } }));
        window.dispatchEvent(new Event('mode-changed'));
    }

    // Ensure Dark Theme Default
    document.body.classList.add('theme-dark');

    // =========================================================================
    // Universal Modal & Drawer Manager (Close on Esc & Click Outside)
    // =========================================================================
    const dlDrawer = document.getElementById('downloader-drawer');
    const alertsDrawer = document.getElementById('alerts-drawer');
    const drawerBackdrop = document.getElementById('drawer-backdrop');

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.add('hidden');

        if (modal.id === 'welcome-modal') {
            modal.remove();
        } else if (modal.id === 'search-modal') {
            if (typeof window.closeSymbolSearch === 'function') {
                window.closeSymbolSearch();
            } else {
                const searchInput = document.getElementById('symbol-search-input');
                if (searchInput) searchInput.value = '';
            }
        } else if (modal.id === 'new-screener-modal') {
            if (window.screenerController && typeof window.screenerController.closeCreateTemplateModal === 'function') {
                window.screenerController.closeCreateTemplateModal();
            }
        } else if (modal.id === 'study-modal-backdrop' || modal.id === 'study-modal') {
            if (typeof window.closeStudyDialog === 'function') {
                window.closeStudyDialog();
            }
        }
    }

    function closeAllModals() {
        let count = 0;
        const studyBackdrop = document.getElementById('study-modal-backdrop');
        if (studyBackdrop && studyBackdrop.classList.contains('open')) {
            if (typeof window.closeStudyDialog === 'function') {
                window.closeStudyDialog();
                count++;
            }
        }
        document.querySelectorAll('.modal').forEach(m => {
            if (!m.classList.contains('hidden') || m.id === 'welcome-modal') {
                closeModal(m);
                count++;
            }
        });
        return count > 0;
    }

    function openDownloaderDrawer() {
        if (!dlDrawer) return;
        if (alertsDrawer) alertsDrawer.classList.add('hidden');
        dlDrawer.classList.remove('hidden');
        if (drawerBackdrop) drawerBackdrop.classList.remove('hidden');
    }

    function closeDrawers() {
        if (dlDrawer) dlDrawer.classList.add('hidden');
        if (alertsDrawer) alertsDrawer.classList.add('hidden');
        if (drawerBackdrop) drawerBackdrop.classList.add('hidden');
    }

    window.closeAppModal = closeModal;
    window.closeAllAppModals = closeAllModals;
    window.closeAppDrawers = closeDrawers;

    // 1. Close buttons inside modals and drawers
    document.addEventListener('click', (e) => {
        const closeBtn = e.target.closest('.close-modal, #close-search-modal, #close-log-trade-modal, #btn-cancel-log-trade');
        if (closeBtn) {
            const parentModal = closeBtn.closest('.modal');
            if (parentModal) {
                closeModal(parentModal);
            }
        }
    });

    // 2. Track mousedown target to prevent false closes on text drag selection
    let lastMouseDownTarget = null;
    document.addEventListener('mousedown', (e) => {
        lastMouseDownTarget = e.target;
    });

    // 3. Click Outside (Backdrop Click) for Modals & Drawers
    document.addEventListener('click', (e) => {
        // A. Modal Backdrop Click:
        const activeModal = e.target.closest('.modal');
        if (activeModal && !e.target.closest('.modal-content')) {
            if (lastMouseDownTarget && !lastMouseDownTarget.closest('.modal-content')) {
                closeModal(activeModal);
            }
        }

        // B. Drawer Backdrop Click:
        if (e.target.id === 'drawer-backdrop' || e.target.classList.contains('drawer-backdrop')) {
            closeDrawers();
            return;
        }

        // C. Click Outside Drawers:
        const dlOpen = dlDrawer && !dlDrawer.classList.contains('hidden');
        const alertsOpen = alertsDrawer && !alertsDrawer.classList.contains('hidden');
        if (dlOpen || alertsOpen) {
            const btnDownloader = document.getElementById('btn-downloader');
            const btnAlerts = document.getElementById('btn-alerts');
            
            const clickedInsideDrawer = (dlDrawer && dlDrawer.contains(e.target)) || (alertsDrawer && alertsDrawer.contains(e.target));
            const clickedOnTrigger = (btnDownloader && btnDownloader.contains(e.target)) || (btnAlerts && btnAlerts.contains(e.target));
            const clickedInsideModal = !!e.target.closest('.modal');

            if (!clickedInsideDrawer && !clickedOnTrigger && !clickedInsideModal) {
                closeDrawers();
            }
        }
    });

    // 4. Universal Escape Key Handler
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            let handled = false;

            // Close all open modals
            const openModals = document.querySelectorAll('.modal:not(.hidden)');
            const studyBackdrop = document.getElementById('study-modal-backdrop');
            if (openModals.length > 0 || document.getElementById('welcome-modal') || (studyBackdrop && studyBackdrop.classList.contains('open'))) {
                closeAllModals();
                handled = true;
            }

            // Close all open drawers
            const dlOpen = dlDrawer && !dlDrawer.classList.contains('hidden');
            const alertsOpen = alertsDrawer && !alertsDrawer.classList.contains('hidden');
            if (dlOpen || alertsOpen) {
                closeDrawers();
                handled = true;
            }

            // Close active options toast if visible
            const activeToast = document.querySelector('.options-toast:not(.hidden)');
            if (activeToast) {
                activeToast.remove();
                handled = true;
            }

            // Close glossary popover if visible
            const glossaryPopover = document.querySelector('.glossary-popover');
            if (glossaryPopover && !glossaryPopover.classList.contains('hidden')) {
                glossaryPopover.classList.add('hidden');
                handled = true;
            }

            if (handled) {
                e.preventDefault();
                e.stopPropagation();
            }
        }
    });

    // Downloader Drawer Triggers
    document.getElementById('btn-downloader')?.addEventListener('click', (e) => {
        e.stopPropagation();
        const isHidden = dlDrawer ? dlDrawer.classList.contains('hidden') : true;
        if (isHidden) {
            openDownloaderDrawer();
        } else {
            closeDrawers();
        }
    });

    document.getElementById('close-drawer')?.addEventListener('click', () => {
        closeDrawers();
    });

    // Export Modal State & Logic
    function updateExportModalState(rowCount, symbol, tf) {
        const rowEstEl = document.getElementById('export-row-estimate');
        if (rowEstEl) {
            rowEstEl.textContent = `Symbol: ${symbol} | Timeframe: ${tf} | Loaded Rows: ${rowCount.toLocaleString()}`;
        }

        const excelOpt = document.getElementById('export-excel-opt');
        const excelWarning = document.getElementById('excel-warning');
        const excelNote = document.getElementById('excel-note');
        const optExcelLabel = document.getElementById('opt-excel-label');
        const parquetRadio = document.querySelector('input[name="export-format"][value="parquet"]');

        if (rowCount > 1048575) {
            if (excelOpt) excelOpt.disabled = true;
            if (excelWarning) excelWarning.classList.remove('hidden');
            if (optExcelLabel) optExcelLabel.classList.add('disabled-option');
            if (parquetRadio) parquetRadio.checked = true;
            if (excelNote) {
                excelNote.innerHTML = '<span class="amber-text">⚠️ Over 1,048,575 rows:</span> Excel disabled to prevent file corruption. Parquet selected.';
                excelNote.classList.add('amber-active');
            }
        } else {
            if (excelOpt) excelOpt.disabled = false;
            if (excelWarning) excelWarning.classList.add('hidden');
            if (optExcelLabel) optExcelLabel.classList.remove('disabled-option');
            if (excelNote) {
                excelNote.innerHTML = '<span class="note-dim">💡 Note:</span> Excel auto-disables above 1,048,575 rows to prevent corruption. Use Parquet instead.';
                excelNote.classList.remove('amber-active');
            }
        }
    }

    document.getElementById('btn-export')?.addEventListener('click', () => {
        const modal = document.getElementById('export-modal');
        if (!modal) return;
        modal.classList.remove('hidden');

        const symbol = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
        const tf = window.currentSymbolTimeframe || '1D';
        const actualCount = (window.allLoadedCandles && window.allLoadedCandles.length > 0) 
            ? window.allLoadedCandles.length 
            : 3000;

        updateExportModalState(actualCount, symbol, tf);
    });

    document.getElementById('btn-confirm-export')?.addEventListener('click', () => {
        const modal = document.getElementById('export-modal');
        const symbol = window.currentActiveSymbol || 'NSE:RELIANCE-EQ';
        const tf = window.currentSymbolTimeframe || '1D';
        const format = document.querySelector('input[name="export-format"]:checked')?.value || 'parquet';

        const safeSymbol = symbol.replace(/[:\/]/g, '_');
        const ext = (format === 'excel') ? 'xlsx' : format;
        const filename = `${safeSymbol}_${tf}.${ext}`;
        const url = `/api/v1/export?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(tf)}&format=${encodeURIComponent(format)}`;

        // Trigger native browser download directly via anchor
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            if (a.parentNode) a.parentNode.removeChild(a);
        }, 1500);

        if (modal) closeModal(modal);
    });

    // View Navigation Switcher (Chart, Screener, Options, Backtest, Journal)
    function switchAppView(viewName) {
        document.querySelectorAll('.view-tab').forEach(tab => {
            if (tab.dataset.view === viewName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        document.querySelectorAll('.app-view').forEach(view => {
            if (view.id === `view-${viewName}`) {
                view.classList.remove('hidden');
            } else {
                view.classList.add('hidden');
            }
        });

        // Sub-component initialization on demand
        if (viewName === 'chart') {
            if (typeof handleResize === 'function') {
                setTimeout(handleResize, 50);
            }
        } else if (viewName === 'screener') {
            if (window.screenerController && typeof window.screenerController.init === 'function') {
                if (!window.screenerInitialized) {
                    window.screenerController.init();
                    window.screenerInitialized = true;
                }
            }
        } else if (viewName === 'options') {
            if (window.optionsController && typeof window.optionsController.init === 'function') {
                if (!window.optionsInitialized) {
                    window.optionsController.init();
                    window.optionsInitialized = true;
                }
            }
            if (window.optionsAnalyticsController && typeof window.optionsAnalyticsController.init === 'function') {
                if (!window.optionsAnalyticsInitialized) {
                    window.optionsAnalyticsController.init();
                    window.optionsAnalyticsInitialized = true;
                }
            }
        } else if (viewName === 'backtest') {
            if (!window.backtestInitialized && typeof BacktestUI === 'function') {
                window.backtestUI = new BacktestUI('backtest-workspace-container');
                window.backtestInitialized = true;
            } else if (window.backtestUI) {
                const mode = window.backtestUI.activeMode || 'single';
                window.backtestUI.switchMode(mode);
            }
        } else if (viewName === 'journal') {
            if (window.journalUI && typeof window.journalUI.refresh === 'function') {
                window.journalUI.refresh();
            } else if (!window.journalInitialized && typeof JournalUI === 'function') {
                window.journalUI = new JournalUI();
                window.journalInitialized = true;
            }
        }
    }

    window.switchAppView = switchAppView;
    window.switchView = switchAppView; // Universal alias for view switching

    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const view = e.currentTarget.dataset.view;
            switchAppView(view);
        });
    });

    // Initialize Alerts UI
    if (window.alertsController && typeof window.alertsController.init === 'function') {
        window.alertsController.init();
    }
});
