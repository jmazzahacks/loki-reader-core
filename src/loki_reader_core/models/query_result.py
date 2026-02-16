"""
QueryResult model representing the result of a Loki query.
"""

from dataclasses import dataclass, field

from .log_stream import LogStream
from .metric_series import MetricSeries
from .query_stats import QueryStats


@dataclass
class QueryResult:
    """
    Result of a Loki query containing streams, metric series, and statistics.

    Attributes:
        status: Response status from Loki (typically "success").
        streams: List of LogStream objects (populated for log queries).
        stats: Optional QueryStats with execution statistics.
        result_type: Loki result type ("streams", "matrix", or "vector").
        metric_series: List of MetricSeries objects (populated for metric queries).
    """

    status: str
    streams: list[LogStream]
    stats: QueryStats | None
    result_type: str = "streams"
    metric_series: list[MetricSeries] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with status, streams, metric_series, and stats.
        """
        return {
            "status": self.status,
            "result_type": self.result_type,
            "streams": [stream.to_dict() for stream in self.streams],
            "metric_series": [s.to_dict() for s in self.metric_series],
            "stats": self.stats.to_dict() if self.stats else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueryResult":
        """
        Create QueryResult from dictionary.

        Args:
            data: Dictionary with status, streams, metric_series, and stats keys.

        Returns:
            QueryResult instance.
        """
        streams = [LogStream.from_dict(s) for s in data.get("streams", [])]
        metric_series = [
            MetricSeries.from_dict(s) for s in data.get("metric_series", [])
        ]
        stats = QueryStats.from_dict(data["stats"]) if data.get("stats") else None
        return cls(
            status=data["status"],
            streams=streams,
            stats=stats,
            result_type=data.get("result_type", "streams"),
            metric_series=metric_series,
        )

    @classmethod
    def from_loki_response(cls, response_data: dict) -> "QueryResult":
        """
        Create QueryResult from Loki API response format.

        Handles all three Loki result types:
        - streams: log lines with labels
        - matrix: time series of numeric values (from rate, count_over_time, etc.)
        - vector: instant numeric values

        Args:
            response_data: Full response from Loki query API.

        Returns:
            QueryResult instance.
        """
        status = response_data.get("status", "unknown")
        data = response_data.get("data", {})
        result_type = data.get("resultType", "streams")
        result_list = data.get("result", [])

        stats_data = data.get("stats")
        stats = QueryStats.from_loki_stats(stats_data) if stats_data else None

        streams: list[LogStream] = []
        metric_series: list[MetricSeries] = []

        if result_type == "matrix":
            metric_series = [
                MetricSeries.from_loki_matrix(r) for r in result_list
            ]
        elif result_type == "vector":
            metric_series = [
                MetricSeries.from_loki_vector(r) for r in result_list
            ]
        else:
            streams = [LogStream.from_loki_stream(s) for s in result_list]

        return cls(
            status=status,
            streams=streams,
            stats=stats,
            result_type=result_type,
            metric_series=metric_series,
        )

    @property
    def total_entries(self) -> int:
        """
        Get total number of log entries across all streams.

        Returns:
            Total entry count.
        """
        return sum(len(stream.entries) for stream in self.streams)

    @property
    def total_samples(self) -> int:
        """
        Get total number of metric samples across all series.

        Returns:
            Total sample count.
        """
        return sum(len(series.samples) for series in self.metric_series)
