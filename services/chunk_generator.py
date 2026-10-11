"""Calendar-Day Chunk Generator for Historical Market Data Ingestion.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import Generator, List, Optional, Union

logger = logging.getLogger(__name__)

# Verified Fyers v3 API Calendar-Day Constraints
CHUNK_DAYS_1M = 100   # Max 100 calendar days (error -353 on 101+)
CHUNK_DAYS_1D = 366   # Max 366 calendar days (error -339 on 367+)


@dataclass(frozen=True)
class DateChunk:
    """Represents a discrete, non-overlapping calendar-day interval for historical API ingestion."""
    symbol: str
    timeframe: str
    range_from: date
    range_to: date
    chunk_index: int = 0

    @property
    def range_from_str(self) -> str:
        """Fyers API date format (YYYY-MM-DD)."""
        return self.range_from.strftime("%Y-%m-%d")

    @property
    def range_to_str(self) -> str:
        """Fyers API date format (YYYY-MM-DD)."""
        return self.range_to.strftime("%Y-%m-%d")

    @property
    def calendar_days(self) -> int:
        """Exact count of calendar days spanned (inclusive)."""
        return (self.range_to - self.range_from).days + 1


def _to_date(d: Union[date, datetime, str]) -> date:
    """Normalize date/datetime/string to datetime.date."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.strptime(d.strip(), "%Y-%m-%d").date()
    raise ValueError(f"Unsupported date type: {type(d)}")


class CalendarChunker:
    """Mathematical calendar-day chunker conforming to Fyers API v3 historical range limits.
    
    Guarantees:
    - 1-minute (`1m`) resolution: Chunks span at most 100 calendar days.
    - Daily (`1D`) resolution: Chunks span at most 366 calendar days.
    - Zero calendar gaps: Every single calendar day between start and end is covered.
    - Zero calendar overlaps: Adjacent chunks never share dates.
    - Backward walking: Walks from end_date back in time towards start_date.
    """

    MAX_CHUNK_DAYS_1M = CHUNK_DAYS_1M
    MAX_CHUNK_DAYS_1D = CHUNK_DAYS_1D

    @staticmethod
    def get_chunk_size_days(timeframe: str) -> int:
        """Returns max calendar-day span for a given timeframe."""
        if timeframe == "1m":
            return CHUNK_DAYS_1M
        if timeframe == "1D":
            return CHUNK_DAYS_1D
        raise ValueError(f"Unsupported timeframe for historical chunking: '{timeframe}'. Only '1m' and '1D' supported.")

    @classmethod
    def generate_backward_chunks(
        cls,
        symbol: str,
        timeframe: str,
        start_date: Union[date, datetime, str],
        end_date: Optional[Union[date, datetime, str]] = None,
    ) -> List[DateChunk]:
        """Generates backward-walking chunks from end_date back to start_date.
        
        Args:
            symbol: Canonical ticker string (e.g. 'NSE:RELIANCE-EQ').
            timeframe: '1m' or '1D'.
            start_date: Lower boundary of historical target.
            end_date: Upper boundary of historical target (defaults to today).
            
        Returns:
            List of DateChunk instances ordered from newest to oldest.
        """
        start = _to_date(start_date)
        end = _to_date(end_date) if end_date is not None else date.today()

        if start > end:
            return []

        chunk_size_days = cls.get_chunk_size_days(timeframe)
        span_delta = timedelta(days=chunk_size_days - 1)

        chunks: List[DateChunk] = []
        current_to = end
        index = 0

        while current_to >= start:
            current_from = current_to - span_delta
            if current_from < start:
                current_from = start

            chunks.append(
                DateChunk(
                    symbol=symbol,
                    timeframe=timeframe,
                    range_from=current_from,
                    range_to=current_to,
                    chunk_index=index,
                )
            )

            # Advance backward with 0 overlap: day before current_from
            current_to = current_from - timedelta(days=1)
            index += 1

        return chunks

    @classmethod
    def generate_chunks_stream(
        cls,
        symbol: str,
        timeframe: str,
        start_date: Union[date, datetime, str],
        end_date: Optional[Union[date, datetime, str]] = None,
    ) -> Generator[DateChunk, None, None]:
        """Generator version of generate_backward_chunks yielding chunks one by one."""
        for chunk in cls.generate_backward_chunks(symbol, timeframe, start_date, end_date):
            yield chunk


def generate_chunks(
    symbol: str,
    timeframe: str,
    start_date: Union[date, datetime, str],
    end_date: Optional[Union[date, datetime, str]] = None,
) -> List[DateChunk]:
    """Convenience module function for CalendarChunker.generate_backward_chunks."""
    return CalendarChunker.generate_backward_chunks(symbol, timeframe, start_date, end_date)
