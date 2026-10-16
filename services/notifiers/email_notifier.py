import logging
import smtplib
from email.message import EmailMessage
from core.interfaces import AlertTrigger
from services.notifiers import INotificationChannel

logger = logging.getLogger(__name__)

class EmailNotifier(INotificationChannel):
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str, recipient_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send(self, trigger: AlertTrigger) -> bool:
        if not all([self.smtp_server, self.sender_email, self.recipient_email]):
            logger.warning("EmailNotifier missing configuration.")
            return False

        msg = EmailMessage()
        msg.set_content(f"Alert for {trigger.symbol}!\nRule: {trigger.rule_type}\nPrice: {trigger.trigger_price}\n{trigger.message}")
        msg['Subject'] = f"Trading Alert: {trigger.symbol} ({trigger.rule_type})"
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email

        try:
            # We assume STARTTLS
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                if self.sender_password:
                    server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            logger.info(f"Email notification sent for {trigger.symbol}")
            return True
        except Exception as e:
            logger.error(f"Email dispatch failed: {e}")
            return False
