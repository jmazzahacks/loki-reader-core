"""
Python library for querying Grafana Loki logs via REST API
"""

from .client import LokiClient
from .exceptions import LokiAuthError, LokiConnectionError, LokiError, LokiQueryError
from .models import LogEntry, LogStream, MetricSample, MetricSeries, QueryResult, QueryStats

__version__ = "0.1.0"

__all__ = [
    "LokiClient",
    "LogEntry",
    "LogStream",
    "MetricSample",
    "MetricSeries",
    "QueryResult",
    "QueryStats",
    "LokiError",
    "LokiConnectionError",
    "LokiQueryError",
    "LokiAuthError",
]
