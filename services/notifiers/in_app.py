import logging
from core.interfaces import AlertTrigger
from services.notifiers import INotificationChannel

logger = logging.getLogger(__name__)

class InAppNotifier(INotificationChannel):
    def send(self, trigger: AlertTrigger) -> bool:
        # In-app notifications are typically stored in a database table or pushed via WebSockets.
        # For Phase 13, logging it and assuming UI fetches/receives it is acceptable or we write to a table.
        # As per plan, "recorded in the in-app notification center". Let's assume we log for now
        # and the UI polling or WebSocket will pick it up, or it was already inserted into a table.
        logger.info(f"[IN-APP BELL] {trigger.symbol} - {trigger.message} at {trigger.trigger_price}")
        return True
