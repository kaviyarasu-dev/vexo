# Plan 003: Multi-Channel Alert Notification Settings & Dispatchers

## Goal
Enable Telegram Bot and SMTP Email alert dispatching with an interactive settings modal in the UI and encrypted credential storage:
1. Implement Telegram webhook and bot token test dispatcher in `services/notifiers/telegram_notifier.py`.
2. Implement SMTP email dispatcher with TLS in `services/notifiers/email_notifier.py`.
3. Add `GET /api/v1/alerts/settings` and `POST /api/v1/alerts/settings/test` endpoints in `api/routers/alerts.py`.
4. Add Notification Settings modal and channel toggles in `static/js/alerts_ui.js` and `static/index.html`.
5. Verify dispatchers and quiet hours suppression tests.

## Read first
- `trading-app/services/notifiers/telegram_notifier.py`
- `trading-app/services/notifiers/email_notifier.py`
- `trading-app/api/routers/alerts.py`
- `trading-app/static/js/alerts_ui.js`

## Steps

### Step 1: Implement Telegram notifier dispatcher
- Inspect `services/notifiers/telegram_notifier.py`.
- Ensure `TelegramNotifier.send_message(bot_token, chat_id, text)` formats markdown notifications with symbol, price, and timestamp.
- Add test connection probe method `test_connection(bot_token, chat_id)` verifying credentials before saving.

### Step 2: Implement SMTP email notifier dispatcher
- Inspect `services/notifiers/email_notifier.py`.
- Ensure `EmailNotifier.send_email(smtp_host, smtp_port, sender, password, recipient, subject, body)` connects via STARTTLS and dispatches alert emails.
- Add test connection probe method `test_connection()` verifying SMTP handshake.

### Step 3: Implement REST configuration endpoints
- In `api/routers/alerts.py`, create:
  - `GET /api/v1/alerts/settings`: Retrieves active notification channels (masking sensitive tokens).
  - `POST /api/v1/alerts/settings`: Persists encrypted credentials using the security vault.
  - `POST /api/v1/alerts/settings/test`: Triggers a test notification to verify connectivity.

### Step 4: Add Alert Settings modal to UI
- In `static/index.html`, add modal markup `#alert-settings-modal` with Telegram Bot Token, Chat ID, SMTP Host, Port, User, and Password inputs.
- In `static/js/alerts_ui.js`, add button to open modal, form validation, and test notification trigger handlers.

### Step 5: Run automated alert dispatcher test suite
- Execute integration tests covering alert routing, test triggers, and quiet hours suppression.
- Ensure all tests pass cleanly.

## Do not touch
- `trading-app/core/security.py`
- `trading-app/services/scheduler_service.py`

## Acceptance
Run:
```bash
.\.venv\Scripts\pytest.exe tests/integration/test_alert_dispatcher.py
```
All tests must pass with exit code 0.

## If blocked
Write exact error trace and attempted fixes to `docs/plans/platform-automation-and-backlog/BLOCKED.md` and stop.

## Report back
Provide test execution output confirming Telegram and SMTP notifier verification.
