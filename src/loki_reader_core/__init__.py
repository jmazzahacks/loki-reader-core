"""
Python library for querying Grafana Loki logs via REST API
"""

from .client import LokiClient
from .exceptions import LokiAuthError, LokiConnectionError, LokiError, LokiQueryError
from .models import LogEntry, LogStream, QueryResult, QueryStats

__version__ = "0.0.1"

__all__ = [
    "LokiClient",
    "LogEntry",
    "LogStream",
    "QueryResult",
    "QueryStats",
    "LokiError",
    "LokiConnectionError",
    "LokiQueryError",
    "LokiAuthError",
]
