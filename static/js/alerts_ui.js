/**
 * alerts_ui.js
 * Price & Technical Alerts Monitor with Quiet Hours Engine (23:00 - 08:00 IST)
 */

class AlertsUI {
    constructor() {
        this.alerts = [];
        this.isQuietHours = false;
        this.istTimeStr = '';
    }

    init() {
        this.bindEvents();
        this.refresh();
        // Check quiet hours & refresh alerts every 30 seconds
        setInterval(() => this.refresh(), 30000);
    }

    bindEvents() {
        // Bell icon click in top bar toggles drawer
        const bellBtn = document.getElementById('btn-alerts');
        if (bellBtn) {
            bellBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const drawer = document.getElementById('alerts-drawer');
                const isOpen = drawer && !drawer.classList.contains('hidden');
                this.toggleDrawer(!isOpen);
            });
        }

        // Close drawer button
        document.getElementById('close-alerts-drawer')?.addEventListener('click', () => {
            this.toggleDrawer(false);
        });

        // Pre-fill active symbol when opening form
        const symbolInput = document.getElementById('alert-input-symbol');
        if (symbolInput && window.currentActiveSymbol) {
            symbolInput.value = window.currentActiveSymbol;
        }

        // Rule type change
        const ruleTypeSelect = document.getElementById('alert-rule-type');
        if (ruleTypeSelect) {
            ruleTypeSelect.addEventListener('change', (e) => {
                this.updateFormFields(e.target.value);
            });
        }

        // Submit alert form
        const form = document.getElementById('new-alert-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCreateAlert();
            });
        }
    }

    toggleDrawer(open) {
        const drawer = document.getElementById('alerts-drawer');
        const backdrop = document.getElementById('drawer-backdrop');
        const dlDrawer = document.getElementById('downloader-drawer');
        if (!drawer) return;
        if (open) {
            if (dlDrawer) dlDrawer.classList.add('hidden');
            drawer.classList.remove('hidden');
            if (backdrop) backdrop.classList.remove('hidden');
            // Update symbol input with currently viewed symbol
            const symbolInput = document.getElementById('alert-input-symbol');
            if (symbolInput && window.currentActiveSymbol) {
                symbolInput.value = window.currentActiveSymbol;
            }
            this.refresh();
        } else {
            drawer.classList.add('hidden');
            if (!dlDrawer || dlDrawer.classList.contains('hidden')) {
                if (backdrop) backdrop.classList.add('hidden');
            }
        }
    }

    updateFormFields(ruleType) {
        const priceParams = document.getElementById('alert-params-price');
        const techParams = document.getElementById('alert-params-tech');
        if (ruleType === 'PRICE_CROSS') {
            priceParams?.classList.remove('hidden');
            techParams?.classList.add('hidden');
        } else {
            priceParams?.classList.add('hidden');
            techParams?.classList.remove('hidden');
        }
    }

    async refresh() {
        await this.checkStatusAndQuietHours();
        await this.fetchAlerts();
    }

    async checkStatusAndQuietHours() {
        // Compute IST time
        const now = new Date();
        const istOffset = 5.5 * 60 * 60 * 1000;
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        const istTime = new Date(utc + istOffset);
        const hour = istTime.getHours();
        const minutes = String(istTime.getMinutes()).padStart(2, '0');
        const seconds = String(istTime.getSeconds()).padStart(2, '0');

        this.istTimeStr = `${String(hour).padStart(2, '0')}:${minutes}:${seconds} IST`;
        this.isQuietHours = (hour >= 23 || hour < 8);

        // Update Quiet Hours Banner in drawer
        const qhBanner = document.getElementById('quiet-hours-banner');
        if (qhBanner) {
            if (this.isQuietHours) {
                qhBanner.className = 'quiet-hours-card quiet-active';
                qhBanner.innerHTML = `
                    <div class="qh-title">🌙 Quiet Hours Active (23:00 – 08:00 IST)</div>
                    <div class="qh-desc">Current Time: <strong>${this.istTimeStr}</strong>. Sound & dispatch notifications are muted during night sleep hours.</div>
                `;
            } else {
                qhBanner.className = 'quiet-hours-card quiet-inactive';
                qhBanner.innerHTML = `
                    <div class="qh-title">☀️ Active Market Hours (08:00 – 23:00 IST)</div>
                    <div class="qh-desc">Current Time: <strong>${this.istTimeStr}</strong>. Real-time price triggers and technical alerts are operational.</div>
                `;
            }
        }
    }

    async fetchAlerts() {
        try {
            const res = await fetch('/api/v1/alerts');
            const json = await res.json();
            if (json.success && Array.isArray(json.data)) {
                this.alerts = json.data;
                this.renderAlertsList();
                this.updateBadgeCount();
            }
        } catch (e) {
            console.error("Failed to fetch alerts:", e);
        }
    }

    updateBadgeCount() {
        const badge = document.getElementById('alert-badge-count');
        if (badge) {
            const activeCount = this.alerts.filter(a => a.is_active).length;
            badge.textContent = activeCount;
            badge.style.display = activeCount > 0 ? 'inline-block' : 'inline-block';
        }
    }

    renderAlertsList() {
        const container = document.getElementById('active-alerts-list');
        if (!container) return;

        if (this.alerts.length === 0) {
            container.innerHTML = `<div class="empty-alerts text-muted text-center p-4">No active alerts configured. Set a price trigger below.</div>`;
            return;
        }

        container.innerHTML = '';
        this.alerts.forEach(alert => {
            const card = document.createElement('div');
            card.className = `alert-item-card ${alert.is_active ? 'active' : 'inactive'}`;

            let conditionDesc = '';
            const p = alert.condition_params || {};
            if (alert.rule_type === 'PRICE_CROSS') {
                const dir = p.direction === 'ABOVE' ? '>' : '<';
                conditionDesc = `Price ${dir} ₹${Number(p.threshold || 0).toLocaleString('en-IN')}`;
            } else if (alert.rule_type === 'RSI_THRESHOLD') {
                conditionDesc = `RSI ${p.direction || '<'} ${p.threshold || 30}`;
            } else {
                conditionDesc = `Rule: ${alert.rule_type}`;
            }

            card.innerHTML = `
                <div class="alert-info">
                    <div class="alert-symbol"><strong>${alert.symbol}</strong> <span class="badge-channel">${alert.channel}</span></div>
                    <div class="alert-condition">${conditionDesc}</div>
                </div>
                <div class="alert-actions">
                    <button class="btn-delete-alert" data-id="${alert.alert_id}" title="Delete alert">🗑️</button>
                </div>
            `;

            card.querySelector('.btn-delete-alert').onclick = () => {
                this.handleDeleteAlert(alert.alert_id);
            };

            container.appendChild(card);
        });
    }

    async handleCreateAlert() {
        const symbol = document.getElementById('alert-input-symbol')?.value.trim() || 'NSE:RELIANCE-EQ';
        const ruleType = document.getElementById('alert-rule-type')?.value || 'PRICE_CROSS';
        const channel = document.getElementById('alert-channel')?.value || 'IN_APP';

        let params = {};
        if (ruleType === 'PRICE_CROSS') {
            const direction = document.getElementById('alert-price-dir')?.value || 'ABOVE';
            const threshold = parseFloat(document.getElementById('alert-price-threshold')?.value || '2800');
            params = { direction: direction, threshold: threshold };
        } else {
            const threshold = parseFloat(document.getElementById('alert-tech-threshold')?.value || '30');
            params = { direction: 'BELOW', threshold: threshold };
        }

        try {
            const res = await fetch('/api/v1/alerts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    rule_type: ruleType,
                    condition_params: params,
                    channel: channel
                })
            });
            const json = await res.json();
            if (json.success) {
                // Show feedback
                const feedback = document.getElementById('alert-form-feedback');
                if (feedback) {
                    feedback.textContent = `✅ Alert created for ${symbol}!`;
                    feedback.classList.remove('hidden');
                    setTimeout(() => feedback.classList.add('hidden'), 3000);
                }
                this.fetchAlerts();
            }
        } catch (e) {
            console.error("Create alert error:", e);
        }
    }

    async handleDeleteAlert(alertId) {
        try {
            const res = await fetch(`/api/v1/alerts/${alertId}`, { method: 'DELETE' });
            const json = await res.json();
            if (json.success) {
                this.fetchAlerts();
            }
        } catch (e) {
            console.error("Delete alert error:", e);
        }
    }
}

window.AlertsUI = AlertsUI;
window.alertsController = new AlertsUI();
