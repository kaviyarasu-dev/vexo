import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from core.interfaces import IAlertService, AlertRule, AlertTrigger, Candle
from services.notifiers.in_app import InAppNotifier
from services.notifiers.telegram_notifier import TelegramNotifier
from services.notifiers.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

class AlertService(IAlertService):
    def __init__(self, db_manager):
        self.db = db_manager
        # In a real app, load these from config/settings.py
        self.notifiers = {
            "IN_APP": InAppNotifier(),
            "TELEGRAM": TelegramNotifier(bot_token="", chat_id=""), 
            "EMAIL": EmailNotifier(smtp_server="", smtp_port=25, sender_email="", sender_password="", recipient_email="")
        }
        self.status = "ACTIVE"
        self._init_tables()

    def _init_tables(self):
        def _create(conn):
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    alert_id VARCHAR PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    rule_type VARCHAR NOT NULL,
                    condition_params JSON NOT NULL,
                    channel VARCHAR NOT NULL DEFAULT 'IN_APP',
                    is_active BOOLEAN DEFAULT TRUE,
                    last_triggered_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    watchlist_id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    symbols JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        self.db.execute_write_batch(_create)

    def create_alert(self, symbol: str, rule_type: str, params: Dict[str, Any], channel: str = "IN_APP") -> str:
        alert_id = str(uuid.uuid4())
        
        def _insert(conn):
            conn.execute("""
                INSERT INTO alert_rules (alert_id, symbol, rule_type, condition_params, channel, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [alert_id, symbol, rule_type, json.dumps(params), channel, True])
            
        self.db.execute_write_batch(_insert)
        return alert_id

    def list_alerts(self, symbol: Optional[str] = None) -> List[AlertRule]:
        cursor = self.db.get_read_cursor()
        try:
            if symbol:
                rows = cursor.execute("SELECT alert_id, symbol, rule_type, condition_params, channel, is_active, last_triggered_at FROM alert_rules WHERE symbol = ?", [symbol]).fetchall()
            else:
                rows = cursor.execute("SELECT alert_id, symbol, rule_type, condition_params, channel, is_active, last_triggered_at FROM alert_rules").fetchall()
                
            alerts = []
            for r in rows:
                alerts.append(AlertRule(
                    alert_id=r[0],
                    symbol=r[1],
                    rule_type=r[2],
                    condition_params=json.loads(r[3]),
                    channel=r[4],
                    is_active=r[5],
                    last_triggered_at=r[6]
                ))
            return alerts
        finally:
            cursor.close()

    def delete_alert(self, alert_id: str) -> bool:
        def _delete(conn):
            conn.execute("DELETE FROM alert_rules WHERE alert_id = ?", [alert_id])
        self.db.execute_write_batch(_delete)
        return True

    def is_quiet_hours(self, hour_ist: Optional[int] = None) -> bool:
        if hour_ist is None:
            now_utc = datetime.now(timezone.utc)
            # IST = UTC + 5:30
            ist_time = now_utc + timedelta(hours=5, minutes=30)
            hour_ist = ist_time.hour
        return hour_ist >= 23 or hour_ist < 8

    def evaluate_rules(self, latest_candles: dict[str, Candle]) -> list[AlertTrigger]:
        if self.status == "PAUSED_AUTH_EXPIRED":
            logger.warning("Alert evaluation skipped due to PAUSED_AUTH_EXPIRED.")
            return []

        active_alerts = self.list_alerts()
        triggers = []
        now = datetime.now(timezone.utc)

        for alert in active_alerts:
            if not alert.is_active:
                continue

            # Check 15 min cooldown
            if alert.last_triggered_at:
                # Ensure last_triggered_at is timezone-aware
                last_trig = alert.last_triggered_at
                if last_trig.tzinfo is None:
                    last_trig = last_trig.replace(tzinfo=timezone.utc)
                if (now - last_trig).total_seconds() < 900: # 15 minutes
                    continue
            
            candle = latest_candles.get(alert.symbol)
            if not candle:
                continue

            price = getattr(candle, "close", 0.0)
            if alert.rule_type == "PRICE_CROSS":
                threshold = float(alert.condition_params.get("threshold", 0.0))
                direction = alert.condition_params.get("direction", "ABOVE")
                
                is_triggered = False
                if direction == "ABOVE" and price > threshold:
                    is_triggered = True
                elif direction == "BELOW" and price < threshold:
                    is_triggered = True
                    
                if is_triggered:
                    trigger = AlertTrigger(
                        alert_id=alert.alert_id,
                        symbol=alert.symbol,
                        rule_type=alert.rule_type,
                        trigger_price=price,
                        trigger_time=now,
                        message=f"Price crossed {direction} {threshold}"
                    )
                    triggers.append(trigger)
                    
        return triggers

    def dispatch_alert(self, alert: AlertTrigger) -> bool:
        # First, update the last_triggered_at
        def _update(conn):
            conn.execute(
                "UPDATE alert_rules SET last_triggered_at = ? WHERE alert_id = ?",
                [alert.trigger_time, alert.alert_id]
            )
        self.db.execute_write_batch(_update)

        # Get rule to find channel
        cursor = self.db.get_read_cursor()
        try:
            row = cursor.execute("SELECT channel FROM alert_rules WHERE alert_id = ?", [alert.alert_id]).fetchone()
            if not row:
                return False
            channel = row[0]
        finally:
            cursor.close()

        # Check quiet hours
        if channel in ["TELEGRAM", "EMAIL"] and self.is_quiet_hours():
            logger.info(f"Quiet hours active. Dispatching {alert.alert_id} to IN_APP instead of {channel}.")
            channel = "IN_APP"

        notifier = self.notifiers.get(channel, self.notifiers["IN_APP"])
        return notifier.send(alert)
