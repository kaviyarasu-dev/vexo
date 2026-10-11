import abc
from core.interfaces import AlertTrigger

class INotificationChannel(abc.ABC):
    @abc.abstractmethod
    def send(self, trigger: AlertTrigger) -> bool:
        """Dispatches the alert trigger to the target channel."""
        pass
