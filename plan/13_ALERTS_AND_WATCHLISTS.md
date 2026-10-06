# Phase 13: Watchlist Management & Multi-Channel Alert Engine

```yaml
EXECUTION_CONTRACT:
  depends_on:
    - "plan/00_MASTER_ARCHITECTURE.md"
    - "plan/01_ENVIRONMENT_CONFIG_AND_AUTH.md"
    - "plan/02_DATABASE_SCHEMA_AND_DUCKDB_ENGINE.md"
    - "plan/04_HISTORICAL_DOWNLOADER_ENGINE.md"
    - "plan/05_RESAMPLING_AND_QUANT_METRICS_ENGINE.md"
  reads:
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#1-canonical-interface-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#4-canonical-database-schema-registry"
    - "plan/00A_CONTRACTS_AND_CONVENTIONS.md#7-global-rategovernor-specification"
  produces:
    - "services/alert_service.py"
    - "services/notifiers/telegram_notifier.py"
    - "services/notifiers/email_notifier.py"
    - "api/v1/alerts.py"
    - "static/js/alerts_view.js"
  exposes:
    - "IAlertService"
  must_not_modify:
    - "plan/*"
    - "db/migrations.py"
  test_plan:
    unit_tests: "tests/unit/test_alert_rules.py"
    integration_tests: "tests/integration/test_alert_dispatcher.py"
    contract_tests: "tests/contract/test_alert_contract.py"
    fixtures: "tests/fixtures/sample_alert_rule.json"
    command: "pytest tests/unit/test_alert_rules.py tests/integration/test_alert_dispatcher.py -v"
  definition_of_done:
    - item: 1
      command: "python -c 'from services.alert_service import AlertService; from db.connection import get_db; s = AlertService(get_db()); alert_id = s.create_alert(symbol=\"NSE:RELIANCE-EQ\", rule_type=\"PRICE_CROSS\", params={\"threshold\": 2600.0, \"direction\": \"ABOVE\"}); assert alert_id is not None'"
      result: "Creates persistent alert rule in alert_rules table."
    - item: 2
      command: "pytest tests/unit/test_alert_rules.py -k test_alert_cooldown_deduplication"
      result: "Alert does not re-trigger within 15-minute cooldown window for identical price condition."
    - item: 3
      command: "python -c 'from services.alert_service import AlertService; from db.connection import get_db; s = AlertService(get_db()); assert s.is_quiet_hours(hour_ist=23)'"
      result: "Quiet hours policy correctly suppresses external push notifications between 23:00 and 08:00 IST."
  failure_modes_and_recovery:
    - failure: "Telegram or SMTP endpoint network timeout"
      detection: "Notification dispatch raises requests.exceptions.Timeout"
      recovery: "Retry with exponential backoff (2s, 8s, 32s); if exhausted, record FAILED in notification log and preserve in-app bell notification"
    - failure: "Fyers token expires during intraday market monitoring"
      detection: "Quote evaluation probe returns 401 or token expired"
      recovery: "Transition alert engine status to PAUSED_AUTH_EXPIRED; emit high-priority in-app alert prompt; resume automatically once token is refreshed"
  handoff:
    - "IAlertService operational with in-app, Telegram, and Email dispatch."
    - "Watchlist management and rate-governed evaluation loops verified."
    - "Ready for Phase 14 institutional backtesting engine."
```

---

## 1. Goal & User Jobs Served
Develop a real-time watchlist management and multi-channel alert evaluation daemon adhering to the 00A Canonical Registry.

### Core User Jobs:
1. **Monitor (Retail Beginner)**: "Send me a simple Telegram message when Reliance drops below its 20-day average so I don't miss an entry."
2. **Monitor (Quant Trader)**: "Alert me when any Nifty 50 stock crosses its Session VWAP with a Volume Z-Score $> 2.0$."
3. **Safety & Peace of Mind**: "Don't spam me with 50 notifications a minute, respect my sleep hours (quiet hours), and never blow my Fyers API rate limit."

---

## 2. SOLID Principles Application
- **Single Responsibility Principle (SRP)**:
  - `AlertEvaluator`: Solely responsible for evaluating candle and quote snapshots against active rule conditions.
  - `AlertService`: Implements `IAlertService`, managing CRUD operations on watchlists and alert definitions in DuckDB.
  - `TelegramNotifier` / `EmailNotifier`: Each handles protocol-specific message delivery only.
- **Open/Closed Principle (OCP)**:
  - Alert notification channels implement an `INotificationChannel` interface (`send(message) -> bool`). Adding WhatsApp, Discord, or desktop native notifications requires registering a new channel class without altering evaluation logic.
- **Dependency Inversion Principle (DIP)**:
  - Downstream evaluators depend on `IAlertService` and `IMarketDataProvider` abstractions.

---

## 3. Alert Rule Typology & Specifications

```
                       [ Incoming Price Snapshot / Bar Close ]
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
      [ Price Threshold Rules ]                       [ Quantitative Rules ]
      - Price > Threshold                             - Price Crosses Session VWAP
      - Price < Threshold                             - RSI(14) Crosses Below 30
      - 52-Week High Breakout                         - Volume Z-Score > 2.0
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          ▼
                                [ Evaluation Engine ]
                                          │
                     [ Safeguards: Cooldown & Quiet Hours ]
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
            [ In-App Bell ]        [ Telegram Bot ]         [ Email / SMTP ]
```

### 3.1. Supported Alert Rule Types
1. **`PRICE_CROSS`**: Triggers when current price crosses above or below a specified level (e.g. `NSE:RELIANCE-EQ > 2600.0`).
2. **`VWAP_CROSS`**: Triggers when price crosses above or below the intraday Session VWAP.
3. **`RSI_THRESHOLD`**: Triggers when RSI crosses into overbought ($> 70$) or oversold ($< 30$) zones.
4. **`VOLUME_SURGE`**: Triggers when 5-minute candle volume exceeds $2.5\times$ the 20-period moving average.
5. **`SCREENER_MATCH`**: Triggers when a stock in a user watchlist newly appears in a saved screener scan.

---

## 4. Operational Safeguards & RateGovernor Integration

### 4.1. RateGovernor Budget Allocation
- Alert evaluation must **NEVER** monopolize API rate limits.
- **Batching Policy**:
  - Intraday price monitoring dispatches multi-symbol quote queries:
    `fyers.quotes({"symbols": "NSE:RELIANCE-EQ,NSE:TCS-EQ,NSE:INFY-EQ,..."})` (up to 50 symbols per call).
  - Executed strictly via RateGovernor **Lane 2 (Medium Priority)**.
  - Frequency: Once every 30 seconds during market hours ($09:15\text{ to } 15:30\text{ IST}$).
  - Consumes only **2 requests / minute** (out of the 180 req/min target), leaving $> 98\%$ of the budget available for interactive chart queries.

### 4.2. Deduplication & Cooldown State Machine
To prevent spam during high-volatility oscillation around a threshold:
- **Alert State Machine**: `PENDING` $\rightarrow$ `ARMED` $\rightarrow$ `TRIGGERED` $\rightarrow$ `COOLING_DOWN` $\rightarrow$ `MUTED` / `ARMED`.
- **Cooldown Window**: Once triggered, the rule enters `COOLING_DOWN` for **15 minutes**. Identical condition matches during cooldown are logged locally but suppressed from external notification dispatch.
- **Reset Condition**: The rule re-arms only after price moves back across the trigger boundary by at least $0.25\%$.

### 4.3. Quiet Hours Policy
- External notifications (Telegram and Email) are strictly suppressed between **23:00:00 and 08:00:00 IST**.
- Alerts triggered during quiet hours are recorded in the in-app notification center but do not trigger push notifications.

### 4.4. Token Expiration Behavior
- If `validate_session()` fails during an alert evaluation cycle:
  - System logs warning: `"Fyers token expired. Pausing intraday alert evaluations."`
  - Alert engine transitions to `PAUSED_AUTH_EXPIRED`.
  - Emits in-app banner: `"Live market alerts paused. Please re-authenticate."`
  - Resumes automatically without data loss once token is refreshed.

---

## 5. Interface Contract (`core/interfaces.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class AlertRule:
    alert_id: str
    symbol: str
    rule_type: str                   # 'PRICE_CROSS', 'VWAP_CROSS', 'RSI_THRESHOLD'
    condition_params: Dict[str, Any]
    channel: str                     # 'IN_APP', 'EMAIL', 'TELEGRAM'
    is_active: bool = True
    last_triggered_at: Optional[datetime] = None

@dataclass
class AlertTrigger:
    alert_id: str
    symbol: str
    rule_type: str
    trigger_price: float
    trigger_time: datetime
    message: str

class IAlertService(ABC):
    @abstractmethod
    def create_alert(self, symbol: str, rule_type: str, params: Dict[str, Any], channel: str = "IN_APP") -> str:
        """Persists new alert rule into DuckDB alert_rules table."""
        pass

    @abstractmethod
    def list_alerts(self, symbol: Optional[str] = None) -> List[AlertRule]:
        """Lists active alerts."""
        pass

    @abstractmethod
    def delete_alert(self, alert_id: str) -> bool:
        """Deletes alert rule."""
        pass

    @abstractmethod
    def evaluate_rules(self, quotes: Dict[str, Any]) -> List[AlertTrigger]:
        """Evaluates active rules against latest quote/candle snapshot."""
        pass

    @abstractmethod
    def dispatch_alert(self, trigger: AlertTrigger) -> bool:
        """Dispatches trigger to target channel with deduplication and quiet hour checks."""
        pass
```

---

## 6. Implementation Steps
1. Implement `services/notifiers/`:
   - `telegram_notifier.py` using standard HTTPS POST to `https://api.telegram.org/bot{token}/sendMessage`.
   - `email_notifier.py` using standard Python `smtplib` / TLS.
2. Implement `services/alert_service.py` (`IAlertService`):
   - Integrates state machine and 15-minute cooldown timer.
   - Evaluates quiet hours (`23:00 to 08:00 IST`).
3. Add background evaluation task in `api/server.py`:
   - Runs every 30s during trading hours via `asyncio.create_task`.
   - Calls Fyers quotes in 50-symbol batches via RateGovernor Lane 2.
4. Expose REST endpoints in `api/v1/alerts.py`.
5. Implement `static/js/alerts_view.js` with in-app notification bell and rule creation modal.

---

## 7. Verification & Acceptance Criteria
- Creating an alert persists record in `alert_rules` table with unique UUID.
- Cooldown verification: When price crosses above ₹2,600 multiple times within 5 minutes, exactly ONE Telegram/Email notification is dispatched.
- Quiet hours test: Running evaluation with system clock set to 23:30 IST suppresses external webhook calls while successfully logging the in-app notification.
- RateGovernor compliance: 1 hour of continuous alert evaluation dispatches $\le 120$ quote requests total ($\le 2\text{ req/min}$), well within Lane 2 budget.
- Token expiration probe: Simulating an expired access token cleanly halts evaluation and updates engine status to `PAUSED_AUTH_EXPIRED` without crashing.
