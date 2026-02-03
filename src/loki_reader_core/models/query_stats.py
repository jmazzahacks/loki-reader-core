"""
QueryStats model representing statistics from a Loki query.
"""

from dataclasses import dataclass


@dataclass
class QueryStats:
    """
    Statistics about a Loki query execution.

    Attributes:
        bytes_processed: Total bytes processed during the query.
        lines_processed: Total log lines processed during the query.
        exec_time_seconds: Query execution time in seconds.
    """

    bytes_processed: int
    lines_processed: int
    exec_time_seconds: float

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with statistics.
        """
        return {
            "bytes_processed": self.bytes_processed,
            "lines_processed": self.lines_processed,
            "exec_time_seconds": self.exec_time_seconds
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueryStats":
        """
        Create QueryStats from dictionary.

        Args:
            data: Dictionary with statistics keys.

        Returns:
            QueryStats instance.
        """
        return cls(
            bytes_processed=data.get("bytes_processed", 0),
            lines_processed=data.get("lines_processed", 0),
            exec_time_seconds=data.get("exec_time_seconds", 0.0)
        )

    @classmethod
    def from_loki_stats(cls, stats_data: dict) -> "QueryStats":
        """
        Create QueryStats from Loki API response format.

        Args:
            stats_data: Statistics object from Loki response.

        Returns:
            QueryStats instance.
        """
        summary = stats_data.get("summary", {})
        return cls(
            bytes_processed=summary.get("totalBytesProcessed", 0),
            lines_processed=summary.get("totalLinesProcessed", 0),
            exec_time_seconds=summary.get("execTime", 0.0)
        )
