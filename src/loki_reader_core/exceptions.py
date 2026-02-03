"""
Custom exceptions for loki-reader-core.
"""


class LokiError(Exception):
    """Base exception for all Loki-related errors."""
    pass


class LokiConnectionError(LokiError):
    """Raised when connection to Loki server fails."""
    pass


class LokiQueryError(LokiError):
    """Raised when a Loki query fails or returns an error."""
    pass


class LokiAuthError(LokiError):
    """Raised when authentication to Loki fails."""
    pass
