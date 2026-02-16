"""
MetricSample model representing a single numeric datapoint from a Loki metric query.
"""

from dataclasses import dataclass

import math

from ..utils import NANOSECONDS_PER_SECOND


@dataclass
class MetricSample:
    """
    A single metric datapoint from a Loki metric query.

    Attributes:
        timestamp: Unix timestamp in nanoseconds when the sample was recorded.
        value: The numeric value of the metric at this timestamp.
    """

    timestamp: int
    value: float

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with timestamp and value.
        """
        return {
            "timestamp": self.timestamp,
            "value": self.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricSample":
        """
        Create MetricSample from dictionary.

        Args:
            data: Dictionary with timestamp and value keys.

        Returns:
            MetricSample instance.
        """
        return cls(
            timestamp=int(data["timestamp"]),
            value=float(data["value"])
        )

    @classmethod
    def from_loki_value(cls, value: list) -> "MetricSample":
        """
        Create MetricSample from Loki's [timestamp, value] format.

        Loki returns metric values as [unix_seconds_float, "string_value"].
        The timestamp is in seconds (possibly fractional) and the value is a string.

        Args:
            value: List of [timestamp_seconds, value_string] from Loki API.

        Returns:
            MetricSample instance with timestamp converted to nanoseconds.
        """
        timestamp_seconds = float(value[0])
        whole_seconds = math.floor(timestamp_seconds)
        fractional = timestamp_seconds - whole_seconds
        timestamp_ns = (whole_seconds * NANOSECONDS_PER_SECOND
                        + round(fractional * NANOSECONDS_PER_SECOND))
        return cls(
            timestamp=timestamp_ns,
            value=float(value[1])
        )
