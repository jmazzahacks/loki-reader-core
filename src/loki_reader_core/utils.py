"""
Timestamp utility functions for working with Loki's nanosecond timestamps.
"""

import time


NANOSECONDS_PER_SECOND = 1_000_000_000
NANOSECONDS_PER_MINUTE = NANOSECONDS_PER_SECOND * 60
NANOSECONDS_PER_HOUR = NANOSECONDS_PER_MINUTE * 60


def now_ns() -> int:
    """
    Get current time as Unix nanoseconds.

    Returns:
        Current timestamp in nanoseconds.
    """
    return int(time.time() * NANOSECONDS_PER_SECOND)


def seconds_to_ns(seconds: int | float) -> int:
    """
    Convert Unix seconds to nanoseconds.

    Args:
        seconds: Unix timestamp in seconds (may be fractional).

    Returns:
        Timestamp in nanoseconds.
    """
    return round(seconds * NANOSECONDS_PER_SECOND)


def ns_to_seconds(nanoseconds: int) -> int:
    """
    Convert Unix nanoseconds to seconds.

    Args:
        nanoseconds: Unix timestamp in nanoseconds.

    Returns:
        Timestamp in seconds.
    """
    return nanoseconds // NANOSECONDS_PER_SECOND


def minutes_ago_ns(minutes: int) -> int:
    """
    Get timestamp N minutes ago as nanoseconds.

    Args:
        minutes: Number of minutes in the past.

    Returns:
        Timestamp in nanoseconds.
    """
    return now_ns() - (minutes * NANOSECONDS_PER_MINUTE)


def hours_ago_ns(hours: int) -> int:
    """
    Get timestamp N hours ago as nanoseconds.

    Args:
        hours: Number of hours in the past.

    Returns:
        Timestamp in nanoseconds.
    """
    return now_ns() - (hours * NANOSECONDS_PER_HOUR)


def days_ago_ns(days: int) -> int:
    """
    Get timestamp N days ago as nanoseconds.

    Args:
        days: Number of days in the past.

    Returns:
        Timestamp in nanoseconds.
    """
    return now_ns() - (days * NANOSECONDS_PER_HOUR * 24)
