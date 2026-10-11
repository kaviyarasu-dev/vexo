import logging
import requests
import time
from core.interfaces import AlertTrigger
from services.notifiers import INotificationChannel

logger = logging.getLogger(__name__)

class TelegramNotifier(INotificationChannel):
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        
    def send(self, trigger: AlertTrigger) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("TelegramNotifier missing bot_token or chat_id.")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": f"ALERT [{trigger.rule_type}] {trigger.symbol}\nPrice: {trigger.trigger_price}\n{trigger.message}",
            "parse_mode": "Markdown"
        }
        
        # Exponential backoff (2s, 8s, 32s)
        backoffs = [2, 8, 32]
        for attempt, backoff in enumerate(backoffs):
            try:
                resp = requests.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                logger.info(f"Telegram notification sent for {trigger.symbol}")
                return True
            except requests.exceptions.Timeout:
                logger.warning(f"Telegram timeout on attempt {attempt+1}. Retrying in {backoff}s...")
                time.sleep(backoff)
            except requests.exceptions.RequestException as e:
                logger.error(f"Telegram dispatch failed: {e}")
                return False
                
        logger.error(f"Telegram dispatch exhausted retries for {trigger.symbol}")
        return False
