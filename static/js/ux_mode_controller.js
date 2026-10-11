class UxModeController {
    constructor() {
        this.currentMode = localStorage.getItem('quant_app_mode') || 'simple';
        this.init();
    }

    async init() {
        if (window.translationRegistry) {
            await window.translationRegistry.loadTranslations();
        }
        this.applyMode(this.currentMode);
        this.attachListeners();
    }

    applyMode(mode) {
        this.currentMode = mode;
        if (mode === 'simple') {
            document.documentElement.classList.add('mode-simple');
            document.documentElement.classList.remove('mode-pro');
            document.body.classList.remove('pro-mode-enabled');
        } else {
            document.documentElement.classList.add('mode-pro');
            document.documentElement.classList.remove('mode-simple');
            document.body.classList.add('pro-mode-enabled');
        }

        window.dispatchEvent(new CustomEvent('uxModeChanged', { detail: { mode: mode } }));
        window.dispatchEvent(new Event('mode-changed'));
        this.updateDOMTranslations();
    }

    setMode(mode) {
        if (mode === 'simple' || mode === 'pro') {
            localStorage.setItem('quant_app_mode', mode);
            this.applyMode(mode);
        }
    }

    toggleMode() {
        this.setMode(this.currentMode === 'simple' ? 'pro' : 'simple');
    }

    attachListeners() {
        const toggleBtns = document.querySelectorAll('.ux-mode-toggle');
        toggleBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const requestedMode = e.currentTarget.getAttribute('data-mode') || this.toggleMode();
                if (requestedMode && (requestedMode === 'simple' || requestedMode === 'pro')) {
                    this.setMode(requestedMode);
                }
            });
        });
    }

    updateDOMTranslations() {
        if (!window.translationRegistry || !window.translationRegistry.translations || Object.keys(window.translationRegistry.translations).length === 0) return;

        const elements = document.querySelectorAll('[data-indicator]');
        elements.forEach(el => {
            const key = el.getAttribute('data-indicator');
            const data = window.translationRegistry.get(key);
            if (data) {
                if (this.currentMode === 'simple') {
                    el.textContent = data.plain_label || data.pro_label || key;
                    el.title = `${data.beginner_summary || ''}\n\nRisk: ${data.risk_tip || ''}`.trim();
                } else {
                    el.textContent = data.pro_label || key;
                    el.title = '';
                }
            }
        });
    }
}

window.uxModeController = new UxModeController();
