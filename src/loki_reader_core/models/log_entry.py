"""
LogEntry model representing a single log line from Loki.
"""

from dataclasses import dataclass


@dataclass
class LogEntry:
    """
    A single log entry from a Loki stream.

    Attributes:
        timestamp: Unix timestamp in nanoseconds when the log was recorded.
        message: The log message content.
    """

    timestamp: int
    message: str

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with timestamp and message.
        """
        return {
            "timestamp": self.timestamp,
            "message": self.message
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        """
        Create LogEntry from dictionary.

        Args:
            data: Dictionary with timestamp and message keys.

        Returns:
            LogEntry instance.
        """
        return cls(
            timestamp=int(data["timestamp"]),
            message=data["message"]
        )

    @classmethod
    def from_loki_value(cls, value: list) -> "LogEntry":
        """
        Create LogEntry from Loki's [timestamp, message] format.

        Args:
            value: List of [timestamp_string, message_string] from Loki API.

        Returns:
            LogEntry instance.
        """
        return cls(
            timestamp=int(value[0]),
            message=value[1]
        )
