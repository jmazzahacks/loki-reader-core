"""Tests for timestamp utility functions."""

import time

from loki_reader_core.utils import (
    NANOSECONDS_PER_HOUR,
    NANOSECONDS_PER_MINUTE,
    NANOSECONDS_PER_SECOND,
    days_ago_ns,
    hours_ago_ns,
    minutes_ago_ns,
    now_ns,
    ns_to_seconds,
    seconds_to_ns,
)


class TestConstants:
    """Test nanosecond constants."""

    def test_nanoseconds_per_second(self) -> None:
        assert NANOSECONDS_PER_SECOND == 1_000_000_000

    def test_nanoseconds_per_minute(self) -> None:
        assert NANOSECONDS_PER_MINUTE == 60_000_000_000

    def test_nanoseconds_per_hour(self) -> None:
        assert NANOSECONDS_PER_HOUR == 3_600_000_000_000


class TestNowNs:
    """Test now_ns function."""

    def test_returns_integer(self) -> None:
        result = now_ns()
        assert isinstance(result, int)

    def test_returns_reasonable_value(self) -> None:
        result = now_ns()
        expected = int(time.time() * NANOSECONDS_PER_SECOND)
        # Allow 1 second tolerance
        assert abs(result - expected) < NANOSECONDS_PER_SECOND


class TestSecondsToNs:
    """Test seconds_to_ns function."""

    def test_converts_zero(self) -> None:
        assert seconds_to_ns(0) == 0

    def test_converts_one_second(self) -> None:
        assert seconds_to_ns(1) == NANOSECONDS_PER_SECOND

    def test_converts_unix_timestamp(self) -> None:
        unix_ts = 1704067200  # 2024-01-01 00:00:00 UTC
        result = seconds_to_ns(unix_ts)
        assert result == unix_ts * NANOSECONDS_PER_SECOND


class TestNsToSeconds:
    """Test ns_to_seconds function."""

    def test_converts_zero(self) -> None:
        assert ns_to_seconds(0) == 0

    def test_converts_one_second(self) -> None:
        assert ns_to_seconds(NANOSECONDS_PER_SECOND) == 1

    def test_truncates_partial_seconds(self) -> None:
        ns = NANOSECONDS_PER_SECOND + 500_000_000  # 1.5 seconds
        assert ns_to_seconds(ns) == 1

    def test_roundtrip(self) -> None:
        original = 1704067200
        assert ns_to_seconds(seconds_to_ns(original)) == original


class TestMinutesAgoNs:
    """Test minutes_ago_ns function."""

    def test_returns_past_timestamp(self) -> None:
        result = minutes_ago_ns(5)
        current = now_ns()
        assert result < current

    def test_correct_offset(self) -> None:
        before = now_ns()
        result = minutes_ago_ns(10)
        after = now_ns()

        expected_offset = 10 * NANOSECONDS_PER_MINUTE
        actual_offset_min = before - result
        actual_offset_max = after - result

        assert actual_offset_min <= expected_offset <= actual_offset_max + NANOSECONDS_PER_SECOND


class TestHoursAgoNs:
    """Test hours_ago_ns function."""

    def test_returns_past_timestamp(self) -> None:
        result = hours_ago_ns(1)
        current = now_ns()
        assert result < current

    def test_correct_offset(self) -> None:
        before = now_ns()
        result = hours_ago_ns(2)
        after = now_ns()

        expected_offset = 2 * NANOSECONDS_PER_HOUR
        actual_offset_min = before - result
        actual_offset_max = after - result

        assert actual_offset_min <= expected_offset <= actual_offset_max + NANOSECONDS_PER_SECOND


class TestDaysAgoNs:
    """Test days_ago_ns function."""

    def test_returns_past_timestamp(self) -> None:
        result = days_ago_ns(1)
        current = now_ns()
        assert result < current

    def test_correct_offset(self) -> None:
        before = now_ns()
        result = days_ago_ns(7)
        after = now_ns()

        expected_offset = 7 * 24 * NANOSECONDS_PER_HOUR
        actual_offset_min = before - result
        actual_offset_max = after - result

        assert actual_offset_min <= expected_offset <= actual_offset_max + NANOSECONDS_PER_SECOND
