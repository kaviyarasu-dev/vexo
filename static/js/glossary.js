/**
 * static/js/glossary.js
 * Contextual educational tooltip popover engine for NSE Quant Platform.
 * Displays three-part schema (Definition, Analogy, Risk Caution) in Simple Mode ONLY.
 */

// If GlossaryTooltipController is already defined by glossary_tooltip.js, reuse; otherwise define
if (typeof GlossaryTooltipController === 'undefined') {
    class GlossaryTooltipController {
        constructor() {
            this.glossary = {};
            this.activeElement = null;
            this.popoverEl = null;
            this.hoverTimeout = null;
            this.isLoaded = false;
            
            this.fallbackGlossary = {
                "vwap": {
                    "term": "Session VWAP (Volume Weighted Average Price)",
                    "plain_label": "Intraday Average Price",
                    "simple_definition": "The true average price paid for all shares traded today, giving more weight to transactions with large volume.",
                    "definition": "The true average price paid for all shares traded today, giving more weight to transactions with large volume.",
                    "everyday_analogy": "Like the wholesale mandi price of onions over a full morning. If retail shops are selling far above it, you're paying a premium; if selling below, you're buying at a discount.",
                    "analogy": "Like the wholesale mandi price of onions over a full morning. If retail shops are selling far above it, you're paying a premium; if selling below, you're buying at a discount.",
                    "risk_caution": "Buying when the price is far above VWAP means you are paying significantly more than the day's average buyer, making you vulnerable to sharp mean-reversion pullbacks.",
                    "risk_warning": "Buying when the price is far above VWAP means you are paying significantly more than the day's average buyer, making you vulnerable to sharp mean-reversion pullbacks."
                },
                "rsi": {
                    "term": "RSI (Relative Strength Index)",
                    "plain_label": "Momentum Meter",
                    "simple_definition": "A momentum oscillator measuring the speed and change of price movements on a scale of 0 to 100 to identify overstretched moves.",
                    "definition": "A momentum oscillator measuring the speed and change of price movements on a scale of 0 to 100 to identify overstretched moves.",
                    "everyday_analogy": "Like a car's speedometer. Driving at 120 km/h in city traffic (RSI > 70) means the engine is running red-hot; crawling in first gear (RSI < 30) indicates deeply depressed momentum.",
                    "analogy": "Like a car's speedometer. Driving at 120 km/h in city traffic (RSI > 70) means the engine is running red-hot; crawling in first gear (RSI < 30) indicates deeply depressed momentum.",
                    "risk_caution": "An 'oversold' stock (RSI < 30) can easily drop another 20% or 30% during strong downtrends. Never buy blindly on low RSI alone without a trend reversal trigger.",
                    "risk_warning": "An 'oversold' stock (RSI < 30) can easily drop another 20% or 30% during strong downtrends. Never buy blindly on low RSI alone without a trend reversal trigger."
                },
                "macd": {
                    "term": "MACD (Moving Average Convergence Divergence)",
                    "plain_label": "Trend Change Detector",
                    "simple_definition": "A trend-following momentum indicator showing the relationship between two exponential moving averages of a security's price.",
                    "definition": "A trend-following momentum indicator showing the relationship between two exponential moving averages of a security's price.",
                    "everyday_analogy": "Like two sprinters running together: one fast runner (short-term momentum) and one steady runner (long-term trend). When the fast runner crosses ahead of the steady runner, momentum is accelerating upward.",
                    "analogy": "Like two sprinters running together: one fast runner (short-term momentum) and one steady runner (long-term trend). When the fast runner crosses ahead of the steady runner, momentum is accelerating upward.",
                    "risk_caution": "MACD produces frequent false whipsaws in choppy, sideways markets, causing losses if signals are taken without confirming higher-timeframe trend context.",
                    "risk_warning": "MACD produces frequent false whipsaws in choppy, sideways markets, causing losses if signals are taken without confirming higher-timeframe trend context."
                },
                "bollinger_bands": {
                    "term": "Bollinger Bands",
                    "plain_label": "Normal Price Range Tunnel",
                    "simple_definition": "A statistical volatility band plotted around a moving average where roughly 95% of historical price activity occurs.",
                    "definition": "A statistical volatility band plotted around a moving average where roughly 95% of historical price activity occurs.",
                    "everyday_analogy": "Like rubber guardrails on a winding highway. Most of the time cars stay within the lanes, but hitting the outer railing signals extreme expansion or an upcoming sharp bounce.",
                    "analogy": "Like rubber guardrails on a winding highway. Most of the time cars stay within the lanes, but hitting the outer railing signals extreme expansion or an upcoming sharp bounce.",
                    "risk_caution": "When bands squeeze tightly together, a violent breakout in either direction is imminent. Buying blindly at the upper band during a squeeze can lead to immediate capital drawdowns.",
                    "risk_warning": "When bands squeeze tightly together, a violent breakout in either direction is imminent. Buying blindly at the upper band during a squeeze can lead to immediate capital drawdowns."
                },
                "atr": {
                    "term": "ATR (Average True Range)",
                    "plain_label": "Daily Price Swing Size",
                    "simple_definition": "A technical volatility indicator that measures the absolute average price movement between highs and lows over a specific number of bars, including gaps.",
                    "definition": "A technical volatility indicator that measures the absolute average price movement between highs and lows over a specific number of bars, including gaps.",
                    "everyday_analogy": "Like the daily tidal range at a beach. Knowing whether the tide moves 2 feet or 10 feet dictates how far up the sand you must place your beach umbrella.",
                    "analogy": "Like the daily tidal range at a beach. Knowing whether the tide moves 2 feet or 10 feet dictates how far up the sand you must place your beach umbrella.",
                    "risk_caution": "Ignoring ATR when placing stop losses results in getting prematurely stopped out by normal market noise in high-volatility stocks.",
                    "risk_warning": "Ignoring ATR when placing stop losses results in getting prematurely stopped out by normal market noise in high-volatility stocks."
                },
                "stt": {
                    "term": "Securities Transaction Tax (STT)",
                    "plain_label": "Government Trade Tax",
                    "simple_definition": "A statutory direct tax levied by the Government of India on every purchase and sale of equity securities and derivatives on recognized Indian stock exchanges.",
                    "definition": "A statutory direct tax levied by the Government of India on every purchase and sale of equity securities and derivatives on recognized Indian stock exchanges.",
                    "everyday_analogy": "Like road toll tax deducted whenever you pass through a national highway toll booth, payable regardless of whether your trip was productive or frustrating.",
                    "analogy": "Like road toll tax deducted whenever you pass through a national highway toll booth, payable regardless of whether your trip was productive or frustrating.",
                    "risk_caution": "High-frequency scalping and overtrading small intraday gains can lead to accumulated STT and transaction charges exceeding gross trading profits.",
                    "risk_warning": "High-frequency scalping and overtrading small intraday gains can lead to accumulated STT and transaction charges exceeding gross trading profits."
                },
                "r_multiple": {
                    "term": "R-Multiple",
                    "plain_label": "Risk-to-Reward Ratio",
                    "simple_definition": "A mathematical measurement of trading gain or loss expressed strictly as a multiple of the initial planned risk (1R = distance from entry to stop loss).",
                    "definition": "A mathematical measurement of trading gain or loss expressed strictly as a multiple of the initial planned risk (1R = distance from entry to stop loss).",
                    "everyday_analogy": "If you bet ₹1,000 on a coin flip with odds that pay ₹3,000 when you win, you made +3.0R. If you lose, you lost exactly -1.0R.",
                    "analogy": "If you bet ₹1,000 on a coin flip with odds that pay ₹3,000 when you win, you made +3.0R. If you lose, you lost exactly -1.0R.",
                    "risk_caution": "Focusing solely on win rate while ignoring R-multiples leads to account ruin: winning 9 tiny trades (+0.2R each = +1.8R) and suffering 1 undisciplined loss (-5.0R) results in a net loss.",
                    "risk_warning": "Focusing solely on win rate while ignoring R-multiples leads to account ruin: winning 9 tiny trades (+0.2R each = +1.8R) and suffering 1 undisciplined loss (-5.0R) results in a net loss."
                },
                "max_pain": {
                    "term": "Options Max Pain Strike",
                    "plain_label": "Options Settlement Magnet",
                    "simple_definition": "The strike price at which option buyers would lose the maximum cumulative money and option sellers would experience the least payout at expiration.",
                    "definition": "The strike price at which option buyers would lose the maximum cumulative money and option sellers would experience the least payout at expiration.",
                    "everyday_analogy": "Like a gravitational center on weekly expiry Thursdays where underlying spot prices often get tethered to minimize net option writer payouts.",
                    "analogy": "Like a gravitational center on weekly expiry Thursdays where underlying spot prices often get tethered to minimize net option writer payouts.",
                    "risk_caution": "Max Pain is a dynamic calculation, not a guaranteed price target. Breaking news, global geopolitical events, or massive institutional order flows can easily overpower option open interest.",
                    "risk_warning": "Max Pain is a dynamic calculation, not a guaranteed price target. Breaking news, global geopolitical events, or massive institutional order flows can easily overpower option open interest."
                }
            };

            this.glossary = { ...this.fallbackGlossary };

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.init());
            } else {
                this.init();
            }
        }

        async init() {
            this.createPopoverDOM();
            this.bindEvents();
            await this.loadGlossaryData();
        }

        createPopoverDOM() {
            if (document.getElementById('glossary-popover-card')) {
                this.popoverEl = document.getElementById('glossary-popover-card');
                return;
            }

            const el = document.createElement('div');
            el.id = 'glossary-popover-card';
            el.className = 'glossary-popover hidden';
            el.setAttribute('role', 'tooltip');
            el.setAttribute('aria-hidden', 'true');
            el.innerHTML = `
                <div class="glossary-header">
                    <div class="glossary-title-wrap">
                        <div class="glossary-title" id="glossary-card-title">Term</div>
                        <div class="glossary-plain-label" id="glossary-card-plain-label">Plain Label</div>
                    </div>
                    <button class="glossary-close-btn" id="glossary-card-close" aria-label="Close tooltip">&times;</button>
                </div>
                <div class="glossary-definition" id="glossary-card-def">Definition</div>
                <div class="glossary-section glossary-analogy-box">
                    <div class="section-title"><span>💡</span> Everyday Analogy</div>
                    <div id="glossary-card-analogy">Analogy content</div>
                </div>
                <div class="glossary-section glossary-caution-box">
                    <div class="section-title"><span>⚠️</span> Risk Caution</div>
                    <div id="glossary-card-caution">Risk warning content</div>
                </div>
                <div class="glossary-arrow" id="glossary-card-arrow"></div>
            `;
            document.body.appendChild(el);
            this.popoverEl = el;

            const closeBtn = el.querySelector('#glossary-card-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.hideTooltip();
                });
            }

            el.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

        async loadGlossaryData() {
            const potentialEndpoints = [
                '/config/glossary.json',
                '/data/glossary.json',
                '/static/config/glossary.json',
                'config/glossary.json',
                'data/glossary.json'
            ];

            for (const url of potentialEndpoints) {
                try {
                    const res = await fetch(url);
                    if (res.ok) {
                        const data = await res.json();
                        if (data && typeof data === 'object' && Object.keys(data).length > 0) {
                            this.glossary = { ...this.fallbackGlossary, ...data };
                            this.isLoaded = true;
                            return;
                        }
                    }
                } catch (err) {
                    // Continue to next endpoint fallback
                }
            }
            this.isLoaded = true;
        }

        setGlossary(data) {
            if (data && typeof data === 'object') {
                this.glossary = { ...data };
            }
        }

        isSimpleMode() {
            // Tooltips appear in Simple mode ONLY — hidden in Pro mode.
            if (window.uxModeController && window.uxModeController.currentMode) {
                return window.uxModeController.currentMode === 'simple';
            }
            const savedMode = localStorage.getItem('quant_app_mode');
            if (savedMode) {
                return savedMode === 'simple';
            }
            if (document.documentElement.classList.contains('mode-simple')) return true;
            if (document.documentElement.classList.contains('mode-pro')) return false;
            if (document.body.classList.contains('pro-mode-enabled')) return false;
            return true;
        }

        bindEvents() {
            document.addEventListener('mouseover', (e) => {
                const target = e.target.closest('[data-glossary]');
                if (target) {
                    if (!this.isSimpleMode()) {
                        this.hideTooltip();
                        return;
                    }
                    clearTimeout(this.hoverTimeout);
                    this.hoverTimeout = setTimeout(() => {
                        this.showTooltip(target);
                    }, 60);
                }
            });

            document.addEventListener('mouseout', (e) => {
                const target = e.target.closest('[data-glossary]');
                if (target && target === this.activeElement) {
                    clearTimeout(this.hoverTimeout);
                    this.hoverTimeout = setTimeout(() => {
                        this.hideTooltip();
                    }, 200);
                }
            });

            document.addEventListener('click', (e) => {
                const target = e.target.closest('[data-glossary]');
                if (target) {
                    if (!this.isSimpleMode()) {
                        this.hideTooltip();
                        return;
                    }
                    e.preventDefault();
                    e.stopPropagation();
                    if (this.activeElement === target && this.popoverEl && !this.popoverEl.classList.contains('hidden')) {
                        this.hideTooltip();
                    } else {
                        this.showTooltip(target);
                    }
                } else {
                    this.hideTooltip();
                }
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.hideTooltip();
                }
            });

            window.addEventListener('uxModeChanged', (e) => {
                if (e.detail && e.detail.mode !== 'simple') {
                    this.hideTooltip();
                }
            });

            window.addEventListener('resize', () => {
                if (this.activeElement) {
                    this.positionPopover(this.activeElement);
                }
            });
            window.addEventListener('scroll', () => {
                if (this.activeElement) {
                    this.positionPopover(this.activeElement);
                }
            }, { passive: true });
        }

        showTooltip(element) {
            if (!this.isSimpleMode() || !this.popoverEl) {
                return;
            }

            const key = element.getAttribute('data-glossary');
            if (!key) return;

            let entry = this.glossary[key.toLowerCase().trim()];

            if (!entry) {
                console.warn(`Glossary key [${key}] not found in config/glossary.json`);
                const formatted = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                entry = {
                    term: formatted,
                    plain_label: formatted,
                    simple_definition: `Information and quantitative definition for ${formatted}.`,
                    everyday_analogy: `Everyday analogy and real-world intuition for ${formatted} will be detailed here.`,
                    risk_caution: "Always analyze historical risk and execute disciplined position sizing before taking trading exposure."
                };
            }

            const titleEl = this.popoverEl.querySelector('#glossary-card-title');
            const plainLabelEl = this.popoverEl.querySelector('#glossary-card-plain-label');
            const defEl = this.popoverEl.querySelector('#glossary-card-def');
            const analogyEl = this.popoverEl.querySelector('#glossary-card-analogy');
            const cautionEl = this.popoverEl.querySelector('#glossary-card-caution');

            if (titleEl) titleEl.textContent = `📘 ${entry.term || entry.plain_label || key}`;
            if (plainLabelEl) plainLabelEl.textContent = entry.plain_label || '';
            if (defEl) defEl.textContent = entry.simple_definition || entry.definition || '';
            if (analogyEl) analogyEl.textContent = entry.everyday_analogy || entry.analogy || '';
            if (cautionEl) cautionEl.textContent = entry.risk_caution || entry.risk_warning || '';

            this.activeElement = element;
            this.popoverEl.classList.remove('hidden');
            this.positionPopover(element);
            requestAnimationFrame(() => {
                if (this.popoverEl) {
                    this.popoverEl.classList.add('visible');
                    this.popoverEl.setAttribute('aria-hidden', 'false');
                }
            });
        }

        positionPopover(element) {
            if (!this.popoverEl) return;

            const rect = element.getBoundingClientRect();
            const popoverRect = this.popoverEl.getBoundingClientRect();
            const arrow = this.popoverEl.querySelector('#glossary-card-arrow');

            const margin = 10;
            const popoverWidth = popoverRect.width || 340;
            const popoverHeight = popoverRect.height || 260;

            let left = rect.left + (rect.width / 2) - (popoverWidth / 2);
            if (left < margin) {
                left = margin;
            } else if (left + popoverWidth > window.innerWidth - margin) {
                left = window.innerWidth - popoverWidth - margin;
            }

            let top = rect.top - popoverHeight - 12;
            let placeBelow = false;

            if (top < margin) {
                top = rect.bottom + 12;
                placeBelow = true;
                if (top + popoverHeight > window.innerHeight - margin) {
                    top = Math.max(margin, window.innerHeight - popoverHeight - margin);
                }
            }

            this.popoverEl.style.left = `${Math.round(left)}px`;
            this.popoverEl.style.top = `${Math.round(top)}px`;

            if (arrow) {
                const arrowLeft = Math.max(16, Math.min(popoverWidth - 24, rect.left + (rect.width / 2) - left - 5));
                arrow.style.left = `${Math.round(arrowLeft)}px`;
                if (placeBelow) {
                    arrow.className = 'glossary-arrow glossary-arrow-top';
                } else {
                    arrow.className = 'glossary-arrow glossary-arrow-bottom';
                }
            }
        }

        hideTooltip() {
            if (this.popoverEl && !this.popoverEl.classList.contains('hidden')) {
                this.popoverEl.classList.remove('visible');
                this.popoverEl.setAttribute('aria-hidden', 'true');
                setTimeout(() => {
                    if (this.popoverEl && !this.popoverEl.classList.contains('visible')) {
                        this.popoverEl.classList.add('hidden');
                    }
                }, 180);
            }
            this.activeElement = null;
        }
    }

    window.GlossaryTooltipController = GlossaryTooltipController;
}

if (!window.glossaryController) {
    window.glossaryController = new window.GlossaryTooltipController();
    window.glossaryTooltipController = window.glossaryController;
}
