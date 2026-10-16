class OnboardingTour {
    constructor() {
        this.tourSteps = [
            {
                element: '#search-bar',
                title: 'Find Any Stock',
                content: 'Use this search bar (or press Ctrl+K) to find any NSE stock quickly.'
            },
            {
                element: '.vwap-line', // or [data-indicator="vwap"]
                title: 'Intraday Average Price',
                content: 'This line shows the average price. Prices above this line indicate buyers are in control.'
            },
            {
                element: '#btn-1-click-scan',
                title: '1-Click Screener',
                content: 'Click here to find todays active stocks without writing complex formulas.'
            }
        ];
        this.currentStep = 0;
        this.isActive = false;
        
        // Wait for DOM to be ready
        document.addEventListener('DOMContentLoaded', () => this.checkFirstVisit());
    }

    checkFirstVisit() {
        const hasVisited = localStorage.getItem('has_completed_onboarding');
        if (!hasVisited) {
            this.showWelcomeModal();
        }
    }

    showWelcomeModal() {
        const modal = document.createElement('div');
        modal.id = 'welcome-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content welcome-modal-content">
                <div class="modal-header">
                    <div class="modal-title-wrap">
                        <span class="modal-title-icon">🚀</span>
                        <h3>Welcome to NSE Quant Platform</h3>
                    </div>
                    <button class="close-btn close-modal" id="close-welcome-modal" type="button" title="Close">✕</button>
                </div>
                <p class="modal-subtitle">Choose your preferred workspace mode to configure charts, indicators, and tools:</p>
                
                <div class="welcome-choices-grid">
                    <button type="button" id="btn-simple-mode" class="welcome-choice-card">
                        <div class="choice-header">
                            <span class="choice-icon">🌱</span>
                            <span class="choice-title">Simple Mode</span>
                        </div>
                        <p class="choice-desc">Clean charts, plain-English indicators, and 1-click screeners. Ideal for beginners learning price action.</p>
                        <span class="choice-action-badge">Launch Simple →</span>
                    </button>
                    
                    <button type="button" id="btn-pro-mode" class="welcome-choice-card pro-card">
                        <div class="choice-header">
                            <span class="choice-icon">⚡</span>
                            <span class="choice-title">Quant Pro Mode</span>
                        </div>
                        <p class="choice-desc">Black-Scholes Greeks, TradingView indicators, Python backtesting & institutional analytics.</p>
                        <span class="choice-action-badge pro-badge">Launch Pro Mode →</span>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        const dismissWelcome = () => {
            modal.remove();
        };

        document.getElementById('close-welcome-modal')?.addEventListener('click', dismissWelcome);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                dismissWelcome();
            }
        });

        document.getElementById('btn-simple-mode')?.addEventListener('click', () => {
            if (window.uxModeController) window.uxModeController.setMode('simple');
            modal.remove();
            this.startTour();
        });

        document.getElementById('btn-pro-mode')?.addEventListener('click', () => {
            if (window.uxModeController) window.uxModeController.setMode('pro');
            modal.remove();
            this.completeTour();
        });
    }

    startTour() {
        this.currentStep = 0;
        this.isActive = true;
        this.showStep();
    }

    showStep() {
        if (this.currentStep >= this.tourSteps.length) {
            this.completeTour();
            return;
        }

        const step = this.tourSteps[this.currentStep];
        console.log(`Tour Step ${this.currentStep + 1}: ${step.title} - ${step.content}`);
        
        // In a real app, this would position a tooltip next to the target element.
        // We simulate the flow for testing purposes.
        
        // Advance after 2 seconds for demo, or wait for user action
        setTimeout(() => {
            this.currentStep++;
            this.showStep();
        }, 2000);
    }

    completeTour() {
        this.isActive = false;
        localStorage.setItem('has_completed_onboarding', 'true');
        console.log("Onboarding complete.");
    }
}

window.onboardingTour = new OnboardingTour();
