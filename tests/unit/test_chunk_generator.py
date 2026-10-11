"""Unit tests for CalendarChunker.
Adheres strictly to plan/00A_CONTRACTS_AND_CONVENTIONS.md and plan/04_HISTORICAL_DOWNLOADER_ENGINE.md.
"""

from datetime import date, timedelta
import pytest

from services.chunk_generator import CalendarChunker, DateChunk, generate_chunks


def test_1m_chunk_sizes_and_boundaries():
    """Verify 1m chunks span exactly 100 calendar days with zero gaps or overlaps."""
    start_date = date(2023, 1, 1)
    end_date = date(2023, 12, 31)

    chunks = CalendarChunker.generate_backward_chunks(
        symbol="NSE:RELIANCE-EQ",
        timeframe="1m",
        start_date=start_date,
        end_date=end_date,
    )

    assert len(chunks) > 0

    # First chunk's range_to must equal end_date
    assert chunks[0].range_to == end_date

    # Last chunk's range_from must equal start_date
    assert chunks[-1].range_from == start_date

    # Verify each full chunk is exactly 100 calendar days
    for i in range(len(chunks) - 1):
        days = chunks[i].calendar_days
        assert days == 100, f"Chunk {i} has {days} days, expected 100"

    # Verify backward sequence: no gaps and no overlaps
    for i in range(len(chunks) - 1):
        expected_prev_to = chunks[i].range_from - timedelta(days=1)
        assert chunks[i + 1].range_to == expected_prev_to, (
            f"Gap or overlap detected between chunk {i} ({chunks[i].range_from}) "
            f"and chunk {i+1} ({chunks[i+1].range_to})"
        )

    # Collect all calendar days to ensure complete coverage
    all_dates = set()
    for chunk in chunks:
        cur = chunk.range_from
        while cur <= chunk.range_to:
            assert cur not in all_dates, f"Duplicate date detected: {cur}"
            all_dates.add(cur)
            cur += timedelta(days=1)

    # Total days in 2023 is 365
    expected_days = (end_date - start_date).days + 1
    assert len(all_dates) == expected_days


def test_1d_chunk_sizes_and_boundaries():
    """Verify 1D chunks span exactly 366 calendar days with zero gaps or overlaps."""
    start_date = date(2020, 1, 1)
    end_date = date(2024, 1, 1)

    chunks = CalendarChunker.generate_backward_chunks(
        symbol="NSE:TCS-EQ",
        timeframe="1D",
        start_date=start_date,
        end_date=end_date,
    )

    assert len(chunks) > 0
    assert chunks[0].range_to == end_date
    assert chunks[-1].range_from == start_date

    # Verify full chunks are exactly 366 calendar days
    for i in range(len(chunks) - 1):
        days = chunks[i].calendar_days
        assert days == 366, f"1D chunk {i} has {days} days, expected 366"

    # Verify no gaps and no overlaps
    for i in range(len(chunks) - 1):
        expected_prev_to = chunks[i].range_from - timedelta(days=1)
        assert chunks[i + 1].range_to == expected_prev_to

    # Verify set coverage
    all_dates = set()
    for chunk in chunks:
        cur = chunk.range_from
        while cur <= chunk.range_to:
            assert cur not in all_dates, f"Duplicate date: {cur}"
            all_dates.add(cur)
            cur += timedelta(days=1)

    expected_total_days = (end_date - start_date).days + 1
    assert len(all_dates) == expected_total_days


def test_single_day_chunk():
    """Verify single-day range generates exactly 1 chunk of 1 day."""
    d = date(2024, 6, 15)
    chunks = CalendarChunker.generate_backward_chunks(
        symbol="NSE:INFY-EQ",
        timeframe="1m",
        start_date=d,
        end_date=d,
    )
    assert len(chunks) == 1
    assert chunks[0].range_from == d
    assert chunks[0].range_to == d
    assert chunks[0].calendar_days == 1


def test_invalid_range_returns_empty():
    """Verify start_date > end_date returns empty list."""
    chunks = CalendarChunker.generate_backward_chunks(
        symbol="NSE:INFY-EQ",
        timeframe="1m",
        start_date=date(2024, 6, 15),
        end_date=date(2024, 6, 10),
    )
    assert chunks == []


def test_date_string_formatting():
    """Verify DateChunk string properties format to YYYY-MM-DD."""
    chunks = generate_chunks(
        symbol="NSE:RELIANCE-EQ",
        timeframe="1m",
        start_date="2024-01-01",
        end_date="2024-01-10",
    )
    assert len(chunks) == 1
    assert chunks[0].range_from_str == "2024-01-01"
    assert chunks[0].range_to_str == "2024-01-10"


def test_unsupported_timeframe_raises_error():
    """Verify unsupported timeframe raises ValueError."""
    with pytest.raises(ValueError):
        CalendarChunker.get_chunk_size_days("5m")
