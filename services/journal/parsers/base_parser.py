from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class RawTradeFill:
    symbol: str
    side: str  # 'BUY' | 'SELL'
    quantity: int
    price: float
    timestamp: datetime
    broker: str
    trade_id: Optional[str] = None
    order_id: Optional[str] = None


class IBrokerParser(ABC):
    @abstractmethod
    def can_parse(self, csv_text: str) -> bool:
        """Returns True if this parser can handle the provided CSV format."""
        pass

    @abstractmethod
    def parse_fills(self, csv_text: str) -> List[RawTradeFill]:
        """Parses CSV text into a standardized list of RawTradeFill instances."""
        pass
