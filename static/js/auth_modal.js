/**
 * Fyers Authentication Status Popup & Real-Time Token Validator.
 * Strictly adheres to Zero-Mock / Strict-Broker rules.
 */

document.addEventListener('DOMContentLoaded', () => {
    const authBadge = document.getElementById('auth-badge');
    const authCountdown = document.getElementById('auth-countdown');
    const authModal = document.getElementById('auth-modal');
    const statusBadge = document.getElementById('auth-modal-status-badge');
    const feedbackBanner = document.getElementById('auth-feedback-banner');
    const inputManual = document.getElementById('input-manual-token');
    const btnSaveManual = document.getElementById('btn-save-manual-token');
    const btnReauth = document.getElementById('btn-reauth');
    const btnLoginBrowser = document.getElementById('btn-login-browser');

    window.isFyersAuthenticated = false;

    window.openAuthModal = function() {
        if (!authModal) return;
        clearAuthFeedback();
        authModal.classList.remove('hidden');
        checkAuthStatus(false);
    };

    window.closeAuthModal = function() {
        if (!authModal) return;
        authModal.classList.add('hidden');
    };

    // Check URL parameters for OAuth redirect callback results
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('auth') === 'success') {
        window.history.replaceState({}, document.title, window.location.pathname);
        showAuthFeedback('success', '✅ <strong>OAuth Login Successful!</strong> Live Fyers session connected.<br>Catching up real trade data...');
        window.dispatchEvent(new CustomEvent('fyersAuthSucceeded'));
    } else if (urlParams.get('auth') === 'error') {
        const errorMsg = urlParams.get('msg') || 'OAuth authentication failed';
        window.history.replaceState({}, document.title, window.location.pathname);
        window.openAuthModal();
        showAuthFeedback('error', `❌ <strong>Login Error</strong>: ${errorMsg}`);
    }

    // Initial check on page load: auto-open popup if token is expired, missing, or disconnected
    checkAuthStatus(true);

    // Periodic check every 60 seconds
    setInterval(() => checkAuthStatus(false), 60000);

    async function checkAuthStatus(autoOpenIfExpired = false) {
        try {
            const res = await fetch('/api/v1/auth/status?probe=true');
            if (res.ok) {
                const json = await res.json();
                if (json && json.success && json.data) {
                    updateAuthUI(json.data, autoOpenIfExpired);
                    return json.data;
                }
            }
            // If request failed or server error, mark as disconnected
            updateAuthUI({
                auth_status: 'DISCONNECTED',
                is_authenticated: false,
                message: 'Could not connect to authentication service.'
            }, autoOpenIfExpired);
        } catch (err) {
            console.warn('Auth status check error:', err);
            updateAuthUI({
                auth_status: 'DISCONNECTED',
                is_authenticated: false,
                message: 'Network error checking authentication.'
            }, autoOpenIfExpired);
        }
        return null;
    }

    function updateAuthUI(data, autoOpenIfExpired = false) {
        const isAuth = Boolean(data && data.is_authenticated && data.auth_status === 'CONNECTED');
        window.isFyersAuthenticated = isAuth;

        const authStatus = (data && data.auth_status) ? data.auth_status : (isAuth ? 'CONNECTED' : 'EXPIRED');

        // 1. Update Topbar Auth Badge
        if (authBadge && authCountdown) {
            if (authStatus === 'CONNECTED') {
                authBadge.className = 'auth-badge auth-ok';
                authCountdown.textContent = data.countdown || 'Active';
                authBadge.title = `Fyers Token Active (Expires in ${data.countdown || 'today'})`;
            } else if (authStatus === 'EXPIRED') {
                authBadge.className = 'auth-badge auth-error';
                authCountdown.textContent = 'Expired';
                authBadge.title = 'Fyers Access Token Expired · Click to Authenticate';
            } else {
                authBadge.className = 'auth-badge auth-error';
                authCountdown.textContent = 'Disconnected';
                authBadge.title = 'Fyers Disconnected · Click to Authenticate';
            }
        }

        // 2. Update Modal Status Badge
        if (statusBadge) {
            statusBadge.className = `badge-pill auth-status-pill auth-pill-${authStatus.toLowerCase()}`;
            statusBadge.textContent = authStatus;
        }

        // 3. Update Modal Cards
        const modalCountdown = document.getElementById('auth-modal-countdown');
        const modalRefresh = document.getElementById('auth-modal-refresh');
        if (modalCountdown) modalCountdown.textContent = data.countdown || (isAuth ? 'Active' : 'Expired');
        if (modalRefresh) modalRefresh.textContent = `${data.days_remaining_refresh || 0} days`;

        // 4. Update Chart Header Live Badge
        const chartLiveBadge = document.getElementById('chart-live-status');
        const chartLiveText = document.getElementById('live-status-text');
        if (chartLiveBadge && chartLiveText) {
            if (isAuth) {
                chartLiveBadge.className = 'chart-live-badge live';
                chartLiveText.textContent = 'LIVE 5s';
                chartLiveBadge.title = 'Real-time Live Market Data Stream Active (5s Polling)';
            } else {
                chartLiveBadge.className = 'chart-live-badge auth-needed';
                chartLiveText.textContent = 'CONNECT FYERS';
                chartLiveBadge.title = 'Fyers Broker Disconnected / Expired · Click to Authenticate';
            }
        }

        // 5. Automatic open rule: If token is expired or disconnected, automatically open the popup
        if (!isAuth && autoOpenIfExpired && authModal) {
            authModal.classList.remove('hidden');
            if (data.message) {
                showAuthFeedback('warning', `⚠️ <strong>${authStatus}</strong>: ${data.message}<br>Please log in or paste a valid Access Token below.`);
            }
        }
    }

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

    // Modal open/close listeners
    authBadge?.addEventListener('click', () => window.openAuthModal());
    document.getElementById('chart-live-status')?.addEventListener('click', () => window.openAuthModal());
    document.getElementById('btn-banner-login')?.addEventListener('click', () => window.openAuthModal());
    document.getElementById('btn-empty-login')?.addEventListener('click', () => window.openAuthModal());

    authModal?.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => window.closeAuthModal());
    });

    authModal?.addEventListener('click', (e) => {
        if (e.target === authModal) {
            window.closeAuthModal();
        }
    });

    // Save and validate manual token or authorization code
    btnSaveManual?.addEventListener('click', async () => {
        const tokenVal = inputManual ? inputManual.value.trim() : '';
        if (!tokenVal) {
            showAuthFeedback('error', '⚠️ Please enter or paste an auth_code, redirect URL, or access token.');
            if (inputManual) inputManual.focus();
            return;
        }

        btnSaveManual.disabled = true;
        const originalText = btnSaveManual.innerHTML;
        btnSaveManual.innerHTML = '🔄 Exchanging & Validating...';
        clearAuthFeedback();

        try {
            const res = await fetch('/api/v1/auth/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: tokenVal, access_token: tokenVal })
            });
            const data = await res.json();

            if (data && data.success && data.data) {
                updateAuthUI(data.data, false);
                if (inputManual) inputManual.value = '';
                showAuthFeedback('success', `✅ <strong>Session Verified!</strong> ${data.data.message || 'Fyers authenticated successfully.'}<br>Syncing and catching up real trade data...`);
                
                // Hide warning banners on chart
                document.getElementById('chart-outdated-banner')?.classList.add('hidden');
                document.getElementById('chart-auth-empty-state')?.classList.add('hidden');

                // Close modal and dispatch event to resume without page reload
                setTimeout(() => {
                    window.closeAuthModal();
                    window.dispatchEvent(new CustomEvent('fyersAuthSucceeded'));
                }, 750);
            } else {
                const errMsg = data.error?.message || 'Token or auth code was rejected by Fyers broker.';
                showAuthFeedback('error', `❌ <strong>Authentication Failed</strong>: ${errMsg}`);
            }
        } catch (e) {
            showAuthFeedback('error', `❌ Network error validating token: ${e.message}`);
        } finally {
            btnSaveManual.disabled = false;
            btnSaveManual.innerHTML = originalText;
        }
    });

    // Quick verification / refresh button
    btnReauth?.addEventListener('click', async () => {
        btnReauth.disabled = true;
        const orig = btnReauth.innerHTML;
        btnReauth.innerHTML = '🔄 Checking...';
        clearAuthFeedback();

        try {
            const data = await checkAuthStatus(false);
            if (data && data.is_authenticated) {
                showAuthFeedback('success', `✅ Fyers session is active and verified! (Expires in ${data.countdown})`);
                setTimeout(() => {
                    window.closeAuthModal();
                    window.dispatchEvent(new CustomEvent('fyersAuthSucceeded'));
                }, 600);
            } else {
                showAuthFeedback('warning', `⚠️ Session is not active (${data?.auth_status || 'EXPIRED'}). Please provide an active access token.`);
            }
        } catch (e) {
            showAuthFeedback('error', `❌ Error checking status: ${e.message}`);
        } finally {
            btnReauth.disabled = false;
            btnReauth.innerHTML = orig;
        }
    });

    // OAuth login in browser
    btnLoginBrowser?.addEventListener('click', () => {
        window.open('/api/v1/auth/login', '_blank');
        showAuthFeedback('warning', '👉 Browser opened for Fyers login. Complete login, copy the redirected URL or token, and paste it into the box above.');
    });
});
