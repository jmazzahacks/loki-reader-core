"""
LogStream model representing a stream of logs with common labels.
"""

from dataclasses import dataclass

from .log_entry import LogEntry


@dataclass
class LogStream:
    """
    A stream of log entries sharing common labels.

    Attributes:
        labels: Dictionary of label key-value pairs (e.g., {"job": "api", "container": "web"}).
        entries: List of LogEntry objects in this stream.
    """

    labels: dict[str, str]
    entries: list[LogEntry]

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with labels and entries.
        """
        return {
            "labels": self.labels,
            "entries": [entry.to_dict() for entry in self.entries]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogStream":
        """
        Create LogStream from dictionary.

        Args:
            data: Dictionary with labels and entries keys.

        Returns:
            LogStream instance.
        """
        entries = [LogEntry.from_dict(e) for e in data.get("entries", [])]
        return cls(
            labels=data["labels"],
            entries=entries
        )

    @classmethod
    def from_loki_stream(cls, stream_data: dict) -> "LogStream":
        """
        Create LogStream from Loki API response format.

        Args:
            stream_data: Dictionary with 'stream' (labels) and 'values' (log entries).

        Returns:
            LogStream instance.
        """
        labels = stream_data.get("stream", {})
        values = stream_data.get("values", [])
        entries = [LogEntry.from_loki_value(v) for v in values]
        return cls(labels=labels, entries=entries)
