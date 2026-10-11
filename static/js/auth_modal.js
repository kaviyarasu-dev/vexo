document.addEventListener('DOMContentLoaded', () => {
    const authBadge = document.getElementById('auth-badge');
    const authCountdown = document.getElementById('auth-countdown');
    const authModal = document.getElementById('auth-modal');
    
    // Check Auth Status every minute
    setInterval(checkAuthStatus, 60000);
    // Initial check
    checkAuthStatus();

    async function checkAuthStatus() {
        try {
            const res = await fetch('/api/v1/auth/status');
            if (res.ok) {
                const data = await res.json();
                if (data.success && data.data) {
                    updateAuthUI(data.data);
                }
            } else {
                mockAuthUI();
            }
        } catch (e) {
            mockAuthUI();
        }
    }

    function mockAuthUI() {
        updateAuthUI({
            is_authenticated: true,
            token_expires_at: new Date(Date.now() + 7 * 3600000 + 42 * 60000).toISOString(),
            days_remaining_refresh: 12
        });
    }

    function updateAuthUI(authData) {
        if (!authData.is_authenticated) {
            authBadge.className = 'auth-badge auth-error';
            authCountdown.textContent = 'Expired';
            return;
        }

        const expiresAt = new Date(authData.token_expires_at);
        const now = new Date();
        const diffMs = expiresAt - now;

        if (diffMs <= 0) {
            authBadge.className = 'auth-badge auth-error';
            authCountdown.textContent = '00h 00m';
        } else {
            const diffHours = Math.floor(diffMs / 3600000);
            const diffMins = Math.floor((diffMs % 3600000) / 60000);
            
            authCountdown.textContent = `${String(diffHours).padStart(2, '0')}h ${String(diffMins).padStart(2, '0')}m`;
            
            if (diffHours >= 2) {
                authBadge.className = 'auth-badge auth-ok';
            } else if (diffHours < 2 && (diffHours > 0 || diffMins >= 30)) {
                authBadge.className = 'auth-badge auth-warn';
            } else {
                authBadge.className = 'auth-badge auth-error';
            }
        }

        document.getElementById('auth-modal-countdown').textContent = authCountdown.textContent;
        document.getElementById('auth-modal-refresh').textContent = `${authData.days_remaining_refresh} days`;
    }

    const feedbackBanner = document.getElementById('auth-feedback-banner');

    function showAuthFeedback(type, message) {
        if (!feedbackBanner) return;
        feedbackBanner.className = `auth-feedback-banner ${type}`;
        feedbackBanner.innerHTML = message;
        feedbackBanner.classList.remove('hidden');
    }

    function clearAuthFeedback() {
        if (!feedbackBanner) return;
        feedbackBanner.className = 'auth-feedback-banner hidden';
        feedbackBanner.innerHTML = '';
    }

    authBadge.addEventListener('click', () => {
        clearAuthFeedback();
        authModal.classList.remove('hidden');
        checkAuthStatus();
    });

    authModal?.addEventListener('click', (e) => {
        if (e.target === authModal) {
            authModal.classList.add('hidden');
        }
    });

    // Quick Refresh Button Handler with Live Visual Feedback
    const btnReauth = document.getElementById('btn-reauth');
    btnReauth?.addEventListener('click', async () => {
        btnReauth.disabled = true;
        const originalText = btnReauth.innerHTML;
        btnReauth.innerHTML = '🔄 Refreshing...';
        clearAuthFeedback();

        try {
            const res = await fetch('/api/v1/auth/refresh', { method: 'POST' });
            const data = await res.json();

            if (data.success && data.data) {
                updateAuthUI(data.data);
                showAuthFeedback('success', `✅ ${data.data.message || 'Token renewed successfully!'}`);
            } else {
                const errMsg = data.error?.message || 'Token renewal failed.';
                if (errMsg.includes('SEBI') || errMsg.includes('disabled') || errMsg.includes('expired')) {
                    showAuthFeedback('warning', `
                        <div style="font-weight: 600; margin-bottom: 4px;">⚠️ SEBI Regulatory Notice</div>
                        <div>Fyers automated background renewal is disabled to comply with SEBI regulations.</div>
                        <div style="margin-top: 6px;">👉 Click <strong>🌐 Login via Browser</strong> or paste your fresh token below.</div>
                    `);
                    // Automatically reveal the manual token container
                    const manualContainer = document.getElementById('manual-token-container');
                    const chevron = document.getElementById('manual-token-chevron');
                    if (manualContainer) {
                        manualContainer.classList.remove('hidden');
                        if (chevron) chevron.textContent = '▲';
                    }
                } else {
                    showAuthFeedback('error', `❌ ${errMsg}`);
                }
            }
        } catch(e) {
            showAuthFeedback('error', `❌ Network error refreshing token: ${e.message}`);
        } finally {
            btnReauth.disabled = false;
            btnReauth.innerHTML = originalText;
        }
    });

    // Toggle Manual Token Input Section
    const btnToggleManual = document.getElementById('btn-toggle-manual-token');
    const manualContainer = document.getElementById('manual-token-container');
    const chevron = document.getElementById('manual-token-chevron');

    btnToggleManual?.addEventListener('click', () => {
        if (!manualContainer) return;
        const isHidden = manualContainer.classList.toggle('hidden');
        if (chevron) chevron.textContent = isHidden ? '▼' : '▲';
    });

    // Save Manual Token Handler
    const btnSaveManual = document.getElementById('btn-save-manual-token');
    const inputManual = document.getElementById('input-manual-token');

    btnSaveManual?.addEventListener('click', async () => {
        const tokenVal = inputManual ? inputManual.value.trim() : '';
        if (!tokenVal) {
            showAuthFeedback('error', '⚠️ Please paste a valid Fyers access token.');
            return;
        }

        btnSaveManual.disabled = true;
        btnSaveManual.textContent = '💾 Saving...';

        try {
            const res = await fetch('/api/v1/auth/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ access_token: tokenVal })
            });
            const data = await res.json();
            if (data.success && data.data) {
                updateAuthUI(data.data);
                inputManual.value = '';
                showAuthFeedback('success', `✅ Access token activated! Session valid until 06:00 AM IST tomorrow (${data.data.countdown}).`);
                // Close manual container
                if (manualContainer) manualContainer.classList.add('hidden');
                if (chevron) chevron.textContent = '▼';
            } else {
                showAuthFeedback('error', `❌ Failed to save token: ${data.error?.message || 'Invalid token'}`);
            }
        } catch(e) {
            showAuthFeedback('error', `❌ Network error saving token: ${e.message}`);
        } finally {
            btnSaveManual.disabled = false;
            btnSaveManual.textContent = '💾 Save';
        }
    });

    document.getElementById('btn-login-browser')?.addEventListener('click', () => {
        window.location.href = '/api/v1/auth/login';
    });
});
