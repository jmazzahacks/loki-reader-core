"""
QueryResult model representing the result of a Loki query.
"""

from dataclasses import dataclass

from .log_stream import LogStream
from .query_stats import QueryStats


@dataclass
class QueryResult:
    """
    Result of a Loki query containing streams and statistics.

    Attributes:
        status: Response status from Loki (typically "success").
        streams: List of LogStream objects containing the query results.
        stats: Optional QueryStats with execution statistics.
    """

    status: str
    streams: list[LogStream]
    stats: QueryStats | None

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with status, streams, and stats.
        """
        return {
            "status": self.status,
            "streams": [stream.to_dict() for stream in self.streams],
            "stats": self.stats.to_dict() if self.stats else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueryResult":
        """
        Create QueryResult from dictionary.

        Args:
            data: Dictionary with status, streams, and stats keys.

        Returns:
            QueryResult instance.
        """
        streams = [LogStream.from_dict(s) for s in data.get("streams", [])]
        stats = QueryStats.from_dict(data["stats"]) if data.get("stats") else None
        return cls(
            status=data["status"],
            streams=streams,
            stats=stats
        )

    @classmethod
    def from_loki_response(cls, response_data: dict) -> "QueryResult":
        """
        Create QueryResult from Loki API response format.

        Args:
            response_data: Full response from Loki query API.

        Returns:
            QueryResult instance.
        """
        status = response_data.get("status", "unknown")
        data = response_data.get("data", {})

        result_list = data.get("result", [])
        streams = [LogStream.from_loki_stream(s) for s in result_list]

        stats_data = data.get("stats")
        stats = QueryStats.from_loki_stats(stats_data) if stats_data else None

        return cls(status=status, streams=streams, stats=stats)

    @property
    def total_entries(self) -> int:
        """
        Get total number of log entries across all streams.

        Returns:
            Total entry count.
        """
        return sum(len(stream.entries) for stream in self.streams)
