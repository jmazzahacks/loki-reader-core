"""
LokiClient for querying Grafana Loki logs via REST API.
"""

from typing import Optional

import requests

from .exceptions import LokiAuthError, LokiConnectionError, LokiQueryError
from .models import QueryResult
from .utils import now_ns, NANOSECONDS_PER_MINUTE, NANOSECONDS_PER_HOUR

APP_LABEL_NAMES = ["application", "app", "job", "service", "service_name", "logger"]
SEVERITY_LABEL_NAMES = ["level", "severity", "log_level", "loglevel"]
SEVERITY_TIERS = ["trace", "debug", "info", "warn", "warning", "error", "fatal", "critical"]


def _is_metric_query(logql: str) -> bool:
    """Check if a LogQL query is a metric query (vs a log selector).

    Metric queries start with aggregation functions and return numeric
    results via the instant endpoint. Log selectors return log streams
    and need the range endpoint.

    Args:
        logql: LogQL query string.

    Returns:
        True if the query is a metric/aggregation query.
    """
    metric_prefixes = [
        "count_over_time", "rate", "bytes_over_time", "bytes_rate",
        "sum", "avg", "min", "max", "stddev", "stdvar",
        "quantile_over_time", "first_over_time", "last_over_time",
        "absent_over_time", "rate_counter", "topk", "bottomk",
        "sort", "sort_desc", "label_replace", "label_join",
    ]
    stripped = logql.strip().lower()
    for prefix in metric_prefixes:
        if stripped.startswith(prefix + "(") or stripped.startswith(prefix + " ("):
            return True
    return False


def _build_severity_regex(min_severity: str) -> str:
    """Build regex matching min_severity and all higher severity tiers.

    Canonical order (low to high): trace, debug, info, warn, error, fatal.
    Aliases: "warning" maps to "warn", "critical" maps to "fatal".

    Args:
        min_severity: Minimum severity level to include.

    Returns:
        Pipe-separated regex string (e.g. "error|fatal|critical").

    Raises:
        ValueError: If min_severity is not a recognized level.
    """
    normalized = min_severity.strip().lower()

    if normalized == "warning":
        normalized = "warn"
    if normalized == "critical":
        normalized = "fatal"

    canonical = ["trace", "debug", "info", "warn", "error", "fatal"]
    idx = canonical.index(normalized)  # raises ValueError if invalid
    selected = canonical[idx:]

    expanded = []
    for level in selected:
        expanded.append(level)
        if level == "warn":
            expanded.append("warning")
        elif level == "fatal":
            expanded.append("critical")

    return "|".join(expanded)


def _resolve_since(
    since_minutes: Optional[int],
    since_hours: Optional[int],
    since_days: Optional[int],
) -> Optional[tuple[int, int]]:
    """Resolve relative time params into a (start_ns, end_ns) tuple.

    Priority: since_minutes > since_hours > since_days.

    Args:
        since_minutes: Number of minutes to look back.
        since_hours: Number of hours to look back.
        since_days: Number of days to look back.

    Returns:
        Tuple of (start_ns, end_ns) or None if all params are None.
    """
    end = now_ns()
    if since_minutes is not None:
        return (end - since_minutes * NANOSECONDS_PER_MINUTE, end)
    if since_hours is not None:
        return (end - since_hours * NANOSECONDS_PER_HOUR, end)
    if since_days is not None:
        return (end - since_days * NANOSECONDS_PER_HOUR * 24, end)
    return None


class LokiClient:
    """
    Client for querying Grafana Loki logs.

    Example:
        client = LokiClient(
            base_url="https://loki.example.com",
            auth=("user", "pass"),
            org_id="tenant-1"
        )

        result = client.query(app="my-api", severity="error", since_hours=1)
    """

    def __init__(
        self,
        base_url: str,
        auth: Optional[tuple[str, str]] = None,
        org_id: Optional[str] = None,
        ca_cert: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30
    ):
        """
        Initialize the Loki client.

        Args:
            base_url: Base URL of the Loki server (e.g., "https://loki.example.com").
            auth: Optional tuple of (username, password) for basic authentication.
            org_id: Optional X-Scope-OrgID header for multi-tenant Loki setups.
            ca_cert: Optional path to CA certificate PEM file for self-signed certs.
            verify_ssl: Whether to verify SSL certificates. Set False to disable (insecure).
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.org_id = org_id
        self.ca_cert = ca_cert
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self._session: Optional[requests.Session] = None
        self._app_label_cache: dict[str, str] = {}
        self._severity_label_cache: Optional[str] = None

    @property
    def session(self) -> requests.Session:
        """
        Get or create HTTP session with configured authentication and SSL settings.

        Returns:
            Configured requests.Session instance.
        """
        if self._session is None:
            self._session = requests.Session()

            if self.auth:
                self._session.auth = self.auth

            if self.org_id:
                self._session.headers["X-Scope-OrgID"] = self.org_id

            if self.ca_cert:
                self._session.verify = self.ca_cert
            else:
                self._session.verify = self.verify_ssl

        return self._session

    def _request(self, method: str, endpoint: str, params: Optional[dict] = None) -> dict:
        """
        Make HTTP request to Loki API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            params: Optional query parameters.

        Returns:
            JSON response as dictionary.

        Raises:
            LokiConnectionError: If connection to Loki fails.
            LokiAuthError: If authentication fails (401/403).
            LokiQueryError: If the query fails or returns an error.
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout
            )
        except requests.exceptions.SSLError as e:
            raise LokiConnectionError(f"SSL error connecting to Loki: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise LokiConnectionError(f"Failed to connect to Loki at {url}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise LokiConnectionError(f"Request to Loki timed out: {e}") from e
        except requests.exceptions.RequestException as e:
            raise LokiConnectionError(f"Request to Loki failed: {e}") from e

        if response.status_code == 401:
            raise LokiAuthError("Authentication failed: invalid credentials")
        if response.status_code == 403:
            raise LokiAuthError("Authorization failed: access denied")

        if response.status_code != 200:
            raise LokiQueryError(
                f"Loki query failed with status {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise LokiQueryError(f"Invalid JSON response from Loki: {e}") from e

        if data.get("status") == "error":
            error_msg = data.get("error", "Unknown error")
            raise LokiQueryError(f"Loki query error: {error_msg}")

        return data

    def _find_app_label(self, app_value: str) -> str:
        """Discover which label name contains the given app value.

        Checks a prioritized list of common label names and returns the
        first one that contains the app value. Results are cached.

        Args:
            app_value: Application name to search for.

        Returns:
            The label name that contains the app value.

        Raises:
            ValueError: If app_value is not found in any common label.
        """
        if app_value in self._app_label_cache:
            return self._app_label_cache[app_value]

        for label_name in APP_LABEL_NAMES:
            values = self.get_label_values(label_name)
            if app_value in values:
                self._app_label_cache[app_value] = label_name
                return label_name

        raise ValueError(
            f"Could not find '{app_value}' in any common label "
            f"({', '.join(APP_LABEL_NAMES)}). Use logql param for custom labels."
        )

    def _find_severity_label(self) -> Optional[str]:
        """Discover which label name is used for severity/level.

        Checks a prioritized list of common severity label names and
        returns the first one that has values. Result is cached.

        Returns:
            The severity label name, or None if not found.
        """
        if self._severity_label_cache is not None:
            return self._severity_label_cache

        for label_name in SEVERITY_LABEL_NAMES:
            values = self.get_label_values(label_name)
            if values:
                self._severity_label_cache = label_name
                return label_name

        return None

    def query(
        self,
        logql: Optional[str] = None,
        app: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        since_minutes: Optional[int] = None,
        since_hours: Optional[int] = None,
        since_days: Optional[int] = None,
    ) -> QueryResult:
        """
        Query Loki logs by application name or LogQL expression.

        For app-based queries, auto-discovers the correct label name and
        builds the LogQL selector. For raw LogQL, passes through directly.

        Metric queries (count_over_time, rate, etc.) use the instant endpoint.
        All other queries use the range endpoint with a time window.

        Args:
            logql: Raw LogQL query string. Mutually exclusive with app.
            app: Application name to search for. Auto-discovers the label.
            severity: Minimum severity level (trace/debug/info/warn/error/fatal).
            limit: Maximum number of entries to return.
            since_minutes: Look back N minutes from now.
            since_hours: Look back N hours from now.
            since_days: Look back N days from now.

        Returns:
            QueryResult containing matching log streams or metric results.

        Raises:
            ValueError: If both logql and app are provided, or neither.
        """
        if logql is not None and app is not None:
            raise ValueError("Cannot combine 'logql' with 'app'")
        if logql is None and app is None:
            raise ValueError("Must provide either 'logql' or 'app'")

        if app is not None:
            label_name = self._find_app_label(app)
            selector = f'{label_name}="{app}"'
            if severity is not None:
                sev_label = self._find_severity_label()
                if sev_label:
                    regex = _build_severity_regex(severity)
                    selector += f', {sev_label}=~"{regex}"'
            logql = "{" + selector + "}"

        has_since = any(
            p is not None for p in [since_minutes, since_hours, since_days]
        )

        if _is_metric_query(logql) and not has_since:
            params = {"query": logql, "limit": limit}
            response = self._request("GET", "/loki/api/v1/query", params)
            return QueryResult.from_loki_response(response)

        time_range = _resolve_since(since_minutes, since_hours, since_days)
        if time_range is None:
            end = now_ns()
            start = end - (30 * 24 * NANOSECONDS_PER_HOUR)
            time_range = (start, end)

        return self.query_range(
            logql=logql,
            start=time_range[0],
            end=time_range[1],
            limit=limit,
            direction="backward",
        )

    def query_range(
        self,
        logql: str,
        start: int,
        end: int,
        limit: int = 1000,
        direction: str = "backward"
    ) -> QueryResult:
        """
        Execute a range query across a time period.

        Args:
            logql: LogQL query string (e.g., '{job="api"} |= "error"').
            start: Start timestamp in nanoseconds.
            end: End timestamp in nanoseconds.
            limit: Maximum number of entries to return.
            direction: Sort direction - "forward" (oldest first) or "backward" (newest first).

        Returns:
            QueryResult containing matching log streams.
        """
        params = {
            "query": logql,
            "start": str(start),
            "end": str(end),
            "limit": limit,
            "direction": direction
        }

        response = self._request("GET", "/loki/api/v1/query_range", params)
        return QueryResult.from_loki_response(response)

    def get_labels(
        self,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> list[str]:
        """
        Get list of available label names.

        Args:
            start: Optional start timestamp in nanoseconds.
            end: Optional end timestamp in nanoseconds.

        Returns:
            List of label names.
        """
        params = {}

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        response = self._request("GET", "/loki/api/v1/labels", params or None)
        return response.get("data", [])

    def get_label_values(
        self,
        label: str,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> list[str]:
        """
        Get list of values for a specific label.

        Args:
            label: Label name to get values for.
            start: Optional start timestamp in nanoseconds.
            end: Optional end timestamp in nanoseconds.

        Returns:
            List of label values.
        """
        params = {}

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        endpoint = f"/loki/api/v1/label/{label}/values"
        response = self._request("GET", endpoint, params or None)
        return response.get("data", [])

    def get_series(
        self,
        match: list[str],
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> list[dict[str, str]]:
        """
        Get list of unique label sets matching the given selectors.

        Args:
            match: List of stream selectors (e.g., ['{job="api"}', '{container="web"}']).
            start: Optional start timestamp in nanoseconds.
            end: Optional end timestamp in nanoseconds.

        Returns:
            List of label dictionaries representing unique streams.
        """
        params = {"match[]": match}

        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)

        response = self._request("GET", "/loki/api/v1/series", params)
        return response.get("data", [])

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self) -> "LokiClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - closes session."""
        self.close()
