/**
 * static/js/guided_tutorial.js
 * 4-Step Guided First-Scan Interactive Onboarding Walkthrough for NSE Quant Platform.
 * Shown once to new visitors; skippable at any step; progress tracked in localStorage.
 */

class GuidedTutorialController {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.isActive = false;
        this.containerEl = null;
        this.spotlightEl = null;
        this.cardEl = null;

        this.steps = [
            {
                stepNumber: 1,
                target: '#search-trigger',
                fallbackSelector: '.topbar-left',
                badge: 'Step 1 of 4: Universe',
                title: 'The Universe (Where We Look)',
                content: 'We start by scanning the Nifty 500 — the top 500 largest listed companies in India. Scanning liquid, institutional-grade stocks eliminates illiquid penny stocks and operator manipulation traps.'
            },
            {
                stepNumber: 2,
                target: '[data-overlay="vwap"]',
                fallbackSelector: '.overlays',
                badge: 'Step 2 of 4: Setup',
                title: 'The Setup (What We Look For)',
                content: 'We look for abnormal volume and institutional accumulation. When trading volume spikes 2x above its 20-day average and price holds above VWAP (Intraday Average), large institutional buyers are active.'
            },
            {
                stepNumber: 3,
                target: '#chart-container',
                fallbackSelector: '.chart-workspace',
                badge: 'Step 3 of 4: Result',
                title: 'The Result (What It Found)',
                content: 'Clicking any matching stock opens its interactive chart instantly, plotting volume-weighted moving levels, trend channels, and candlestick volatility metrics.'
            },
            {
                stepNumber: 4,
                target: '#pro-toolbar',
                fallbackSelector: '.chart-workspace',
                badge: 'Step 4 of 4: Risk',
                title: 'The Risk (How to Stay Safe)',
                content: 'Before ever thinking about profit, always define your Stop Loss exit. Never risk more than 1% to 2% of your total trading capital on any single setup, and beware of survivorship bias.'
            }
        ];

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        this.buildDOM();
        this.bindGlobalShortcuts();

        // Check if tutorial was already completed or skipped
        const isCompleted = localStorage.getItem('quant_tutorial_completed');
        if (!isCompleted || isCompleted !== 'true') {
            // Restore last active step or start at 1
            const savedStep = parseInt(localStorage.getItem('quant_tutorial_step') || '1', 10);
            this.currentStep = (savedStep >= 1 && savedStep <= this.totalSteps) ? savedStep : 1;
            // Delay slightly for initial DOM render to stabilize
            setTimeout(() => {
                this.start();
            }, 500);
        }
    }

    buildDOM() {
        if (document.getElementById('guided-tutorial-container')) {
            this.containerEl = document.getElementById('guided-tutorial-container');
            this.spotlightEl = document.getElementById('guided-tutorial-spotlight');
            this.cardEl = document.getElementById('guided-tutorial-card');
            return;
        }

        const container = document.createElement('div');
        container.id = 'guided-tutorial-container';
        container.className = 'tutorial-overlay-container hidden';
        container.style.display = 'none';

        container.innerHTML = `
            <div class="tutorial-backdrop" id="guided-tutorial-backdrop"></div>
            <div class="tutorial-spotlight" id="guided-tutorial-spotlight"></div>
            <div class="tutorial-card" id="guided-tutorial-card" role="dialog" aria-modal="true">
                <div class="tutorial-card-header">
                    <span class="tutorial-step-badge" id="tutorial-badge">Step 1 of 4</span>
                    <button class="tutorial-close-btn" id="tutorial-btn-close" aria-label="Skip Tutorial">&times;</button>
                </div>
                <h3 class="tutorial-title" id="tutorial-title">Tutorial Title</h3>
                <p class="tutorial-body" id="tutorial-body">Tutorial Body</p>
                
                <div class="tutorial-dots" id="tutorial-dots">
                    <div class="tutorial-dot" data-step="1"></div>
                    <div class="tutorial-dot" data-step="2"></div>
                    <div class="tutorial-dot" data-step="3"></div>
                    <div class="tutorial-dot" data-step="4"></div>
                </div>

                <div class="tutorial-footer">
                    <button class="tutorial-skip-btn" id="tutorial-btn-skip">Skip Tour</button>
                    <div class="tutorial-nav-group">
                        <button class="tutorial-btn-prev" id="tutorial-btn-prev">Back</button>
                        <button class="tutorial-btn-next" id="tutorial-btn-next">Next</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(container);
        this.containerEl = container;
        this.spotlightEl = container.querySelector('#guided-tutorial-spotlight');
        this.cardEl = container.querySelector('#guided-tutorial-card');

        // Bind interactive events
        const btnClose = container.querySelector('#tutorial-btn-close');
        const btnSkip = container.querySelector('#tutorial-btn-skip');
        const btnPrev = container.querySelector('#tutorial-btn-prev');
        const btnNext = container.querySelector('#tutorial-btn-next');
        const backdrop = container.querySelector('#guided-tutorial-backdrop');

        if (btnClose) btnClose.addEventListener('click', () => this.skip());
        if (btnSkip) btnSkip.addEventListener('click', () => this.skip());
        if (btnPrev) btnPrev.addEventListener('click', () => this.prev());
        if (btnNext) btnNext.addEventListener('click', () => this.next());
        if (backdrop) backdrop.addEventListener('click', () => this.skip());
    }

    bindGlobalShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (!this.isActive) return;

            if (e.key === 'Escape') {
                e.preventDefault();
                this.skip();
            } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
                e.preventDefault();
                this.next();
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.prev();
            }
        });

        window.addEventListener('resize', () => {
            if (this.isActive) {
                this.renderStep(this.currentStep);
            }
        });
    }

    start() {
        if (!this.containerEl) this.buildDOM();
        this.isActive = true;
        this.containerEl.style.display = 'block';
        this.containerEl.classList.remove('hidden');
        this.renderStep(this.currentStep);
    }

    goToStep(stepNumber) {
        if (stepNumber < 1) stepNumber = 1;
        if (stepNumber > this.totalSteps) stepNumber = this.totalSteps;
        this.currentStep = stepNumber;
        localStorage.setItem('quant_tutorial_step', stepNumber.toString());
        this.renderStep(this.currentStep);
    }

    next() {
        if (this.currentStep < this.totalSteps) {
            this.goToStep(this.currentStep + 1);
        } else {
            this.finish();
        }
    }

    prev() {
        if (this.currentStep > 1) {
            this.goToStep(this.currentStep - 1);
        }
    }

    skip() {
        this.isActive = false;
        if (this.containerEl) {
            this.containerEl.style.display = 'none';
            this.containerEl.classList.add('hidden');
        }
        localStorage.setItem('quant_tutorial_completed', 'true');
        console.log('Guided tutorial skipped by user.');
    }

    finish() {
        this.isActive = false;
        if (this.containerEl) {
            this.containerEl.style.display = 'none';
            this.containerEl.classList.add('hidden');
        }
        localStorage.setItem('quant_tutorial_completed', 'true');
        console.log('Guided tutorial completed.');
    }

    resetTutorial() {
        localStorage.removeItem('quant_tutorial_completed');
        localStorage.removeItem('quant_tutorial_step');
        this.currentStep = 1;
        this.start();
    }

    renderStep(stepIndex) {
        const step = this.steps[stepIndex - 1];
        if (!step) return;

        const badgeEl = this.cardEl.querySelector('#tutorial-badge');
        const titleEl = this.cardEl.querySelector('#tutorial-title');
        const bodyEl = this.cardEl.querySelector('#tutorial-body');
        const btnPrev = this.cardEl.querySelector('#tutorial-btn-prev');
        const btnNext = this.cardEl.querySelector('#tutorial-btn-next');

        if (badgeEl) badgeEl.textContent = step.badge;
        if (titleEl) titleEl.textContent = step.title;
        if (bodyEl) bodyEl.textContent = step.content;

        // Update progress dots
        const dots = this.cardEl.querySelectorAll('.tutorial-dot');
        dots.forEach((dot, idx) => {
            const dotStep = idx + 1;
            dot.className = 'tutorial-dot';
            if (dotStep === stepIndex) {
                dot.classList.add('active');
            } else if (dotStep < stepIndex) {
                dot.classList.add('completed');
            }
        });

        // Navigation button labels and states
        if (btnPrev) {
            btnPrev.style.display = stepIndex === 1 ? 'none' : 'inline-block';
        }
        if (btnNext) {
            btnNext.textContent = stepIndex === this.totalSteps ? 'Finish Tour' : 'Next';
        }

        // Locate target element
        let targetEl = document.querySelector(step.target);
        if (!targetEl && step.fallbackSelector) {
            targetEl = document.querySelector(step.fallbackSelector);
        }

        this.positionSpotlightAndCard(targetEl);
    }

    positionSpotlightAndCard(targetEl) {
        const padding = 6;
        const cardWidth = 400;
        const cardHeight = 220;
        const margin = 16;

        if (targetEl && targetEl.offsetParent !== null) {
            const rect = targetEl.getBoundingClientRect();
            // Position spotlight cutout around element
            this.spotlightEl.style.display = 'block';
            this.spotlightEl.style.left = `${Math.max(0, rect.left - padding)}px`;
            this.spotlightEl.style.top = `${Math.max(0, rect.top - padding)}px`;
            this.spotlightEl.style.width = `${rect.width + padding * 2}px`;
            this.spotlightEl.style.height = `${rect.height + padding * 2}px`;

            // Position dialogue card near element
            let cardTop = rect.bottom + margin;
            let cardLeft = rect.left;

            // Horizontal bounds check
            if (cardLeft + cardWidth > window.innerWidth - margin) {
                cardLeft = window.innerWidth - cardWidth - margin;
            }
            if (cardLeft < margin) {
                cardLeft = margin;
            }

            // Vertical bounds check: if overflow at bottom, position above element
            if (cardTop + cardHeight > window.innerHeight - margin) {
                cardTop = rect.top - cardHeight - margin;
                if (cardTop < margin) {
                    cardTop = margin;
                }
            }

            this.cardEl.style.left = `${Math.round(cardLeft)}px`;
            this.cardEl.style.top = `${Math.round(cardTop)}px`;
            this.cardEl.style.transform = 'none';
        } else {
            // Target not found or hidden: center card on screen and hide spotlight
            this.spotlightEl.style.display = 'none';
            this.cardEl.style.left = '50%';
            this.cardEl.style.top = '50%';
            this.cardEl.style.transform = 'translate(-50%, -50%)';
        }
    }
}

// Global instance
window.guidedTutorial = new GuidedTutorialController();
