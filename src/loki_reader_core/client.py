"""
LokiClient for querying Grafana Loki logs via REST API.
"""

from typing import Optional

import requests

from .exceptions import LokiAuthError, LokiConnectionError, LokiQueryError
from .models import QueryResult
from .utils import now_ns


class LokiClient:
    """
    Client for querying Grafana Loki logs.

    Example:
        client = LokiClient(
            base_url="https://loki.example.com",
            auth=("user", "pass"),
            org_id="tenant-1"
        )

        result = client.query_range(
            logql='{job="api"} |= "error"',
            start=hours_ago_ns(1),
            end=now_ns(),
            limit=500
        )
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

    def query(
        self,
        logql: str,
        time: Optional[int] = None,
        limit: int = 100
    ) -> QueryResult:
        """
        Execute an instant query at a single point in time.

        Args:
            logql: LogQL query string (e.g., '{job="api"} |= "error"').
            time: Optional timestamp in nanoseconds. Defaults to now.
            limit: Maximum number of entries to return.

        Returns:
            QueryResult containing matching log streams.
        """
        params = {
            "query": logql,
            "limit": limit
        }

        if time is not None:
            params["time"] = str(time)

        response = self._request("GET", "/loki/api/v1/query", params)
        return QueryResult.from_loki_response(response)

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
