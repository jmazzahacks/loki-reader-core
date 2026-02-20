"""Tests for LokiClient."""

from unittest.mock import MagicMock, patch, call

import pytest

from loki_reader_core import LokiClient
from loki_reader_core.client import _is_metric_query, _build_severity_regex, _resolve_since
from loki_reader_core.exceptions import LokiAuthError, LokiConnectionError, LokiQueryError


MOCK_LOKI_RESPONSE = {
    "status": "success",
    "data": {
        "resultType": "streams",
        "result": [],
        "stats": {"summary": {}}
    }
}


class TestLokiClientInit:
    """Test LokiClient initialization."""

    def test_init_basic(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        assert client.base_url == "http://localhost:3100"
        assert client.auth is None
        assert client.org_id is None
        assert client.ca_cert is None
        assert client.verify_ssl is True
        assert client.timeout == 30

    def test_init_with_trailing_slash(self) -> None:
        client = LokiClient(base_url="http://localhost:3100/")
        assert client.base_url == "http://localhost:3100"

    def test_init_with_auth(self) -> None:
        client = LokiClient(
            base_url="http://localhost:3100",
            auth=("user", "pass")
        )
        assert client.auth == ("user", "pass")

    def test_init_with_org_id(self) -> None:
        client = LokiClient(
            base_url="http://localhost:3100",
            org_id="tenant-1"
        )
        assert client.org_id == "tenant-1"

    def test_init_with_ca_cert(self) -> None:
        client = LokiClient(
            base_url="https://localhost:3100",
            ca_cert="/path/to/ca.pem"
        )
        assert client.ca_cert == "/path/to/ca.pem"

    def test_init_verify_ssl_false(self) -> None:
        client = LokiClient(
            base_url="https://localhost:3100",
            verify_ssl=False
        )
        assert client.verify_ssl is False

    def test_init_custom_timeout(self) -> None:
        client = LokiClient(
            base_url="http://localhost:3100",
            timeout=60
        )
        assert client.timeout == 60

    def test_init_label_caches_empty(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        assert client._app_label_cache == {}
        assert client._severity_label_cache is None


class TestLokiClientSession:
    """Test LokiClient session management."""

    def test_session_created_lazily(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        assert client._session is None
        _ = client.session
        assert client._session is not None

    def test_session_reused(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        session1 = client.session
        session2 = client.session
        assert session1 is session2

    def test_session_has_auth(self) -> None:
        client = LokiClient(
            base_url="http://localhost:3100",
            auth=("user", "pass")
        )
        assert client.session.auth == ("user", "pass")

    def test_session_has_org_id_header(self) -> None:
        client = LokiClient(
            base_url="http://localhost:3100",
            org_id="tenant-1"
        )
        assert client.session.headers["X-Scope-OrgID"] == "tenant-1"

    def test_session_verify_with_ca_cert(self) -> None:
        client = LokiClient(
            base_url="https://localhost:3100",
            ca_cert="/path/to/ca.pem"
        )
        assert client.session.verify == "/path/to/ca.pem"

    def test_session_verify_false(self) -> None:
        client = LokiClient(
            base_url="https://localhost:3100",
            verify_ssl=False
        )
        assert client.session.verify is False

    def test_session_verify_default(self) -> None:
        client = LokiClient(base_url="https://localhost:3100")
        assert client.session.verify is True


class TestLokiClientContextManager:
    """Test LokiClient context manager."""

    def test_context_manager_returns_client(self) -> None:
        with LokiClient(base_url="http://localhost:3100") as client:
            assert isinstance(client, LokiClient)

    def test_context_manager_closes_session(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        _ = client.session  # Create session

        with client:
            pass

        assert client._session is None


class TestLokiClientRequest:
    """Test LokiClient HTTP request handling."""

    @patch("loki_reader_core.client.requests.Session")
    def test_connection_error(self, mock_session_class: MagicMock) -> None:
        import requests

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection refused")

        client = LokiClient(base_url="http://localhost:3100")

        with pytest.raises(LokiConnectionError) as exc_info:
            client.query(logql='{job="test"}')

        assert "Failed to connect" in str(exc_info.value)

    @patch("loki_reader_core.client.requests.Session")
    def test_ssl_error(self, mock_session_class: MagicMock) -> None:
        import requests

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.SSLError("Certificate verify failed")

        client = LokiClient(base_url="https://localhost:3100")

        with pytest.raises(LokiConnectionError) as exc_info:
            client.query(logql='{job="test"}')

        assert "SSL error" in str(exc_info.value)

    @patch("loki_reader_core.client.requests.Session")
    def test_timeout_error(self, mock_session_class: MagicMock) -> None:
        import requests

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.Timeout("Request timed out")

        client = LokiClient(base_url="http://localhost:3100")

        with pytest.raises(LokiConnectionError) as exc_info:
            client.query(logql='{job="test"}')

        assert "timed out" in str(exc_info.value)

    @patch("loki_reader_core.client.requests.Session")
    def test_auth_error_401(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")

        with pytest.raises(LokiAuthError) as exc_info:
            client.query(logql='{job="test"}')

        assert "invalid credentials" in str(exc_info.value)

    @patch("loki_reader_core.client.requests.Session")
    def test_auth_error_403(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")

        with pytest.raises(LokiAuthError) as exc_info:
            client.query(logql='{job="test"}')

        assert "access denied" in str(exc_info.value)

    @patch("loki_reader_core.client.requests.Session")
    def test_query_error_status(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")

        with pytest.raises(LokiQueryError) as exc_info:
            client.query(logql='{job="test"}')

        assert "500" in str(exc_info.value)

    @patch("loki_reader_core.client.requests.Session")
    def test_query_error_response(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "parse error: unexpected token"
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")

        with pytest.raises(LokiQueryError) as exc_info:
            client.query(logql='{job="test"}')

        assert "parse error" in str(exc_info.value)


class TestLokiClientQuery:
    """Test LokiClient query methods."""

    @patch("loki_reader_core.client.requests.Session")
    def test_query_range_basic(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "api"},
                        "values": [["1704067200000000000", "test log"]]
                    }
                ],
                "stats": {"summary": {"totalBytesProcessed": 100}}
            }
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")
        result = client.query_range(
            logql='{job="api"}',
            start=1704067100000000000,
            end=1704067200000000000
        )

        assert result.status == "success"
        assert len(result.streams) == 1
        assert result.streams[0].labels["job"] == "api"

        call_args = mock_session.request.call_args
        assert call_args.kwargs["params"]["start"] == "1704067100000000000"
        assert call_args.kwargs["params"]["end"] == "1704067200000000000"
        assert call_args.kwargs["params"]["direction"] == "backward"


class TestLokiClientUtilityMethods:
    """Test LokiClient utility methods."""

    @patch("loki_reader_core.client.requests.Session")
    def test_get_labels(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["job", "container", "namespace"]
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")
        labels = client.get_labels()

        assert labels == ["job", "container", "namespace"]

    @patch("loki_reader_core.client.requests.Session")
    def test_get_label_values(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": ["api-server", "web-server", "worker"]
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")
        values = client.get_label_values("job")

        assert values == ["api-server", "web-server", "worker"]

        call_args = mock_session.request.call_args
        assert "/label/job/values" in call_args.kwargs["url"]

    @patch("loki_reader_core.client.requests.Session")
    def test_get_series(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {"job": "api", "container": "web"},
                {"job": "api", "container": "worker"}
            ]
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")
        series = client.get_series(match=['{job="api"}'])

        assert len(series) == 2
        assert series[0]["container"] == "web"


class TestIsMetricQuery:
    """Test _is_metric_query helper function."""

    def test_count_over_time(self) -> None:
        assert _is_metric_query('count_over_time({job="api"}[5m])') is True

    def test_rate(self) -> None:
        assert _is_metric_query('rate({job="api"}[5m])') is True

    def test_sum_by(self) -> None:
        assert _is_metric_query('sum(rate({job="api"}[5m])) by (level)') is True

    def test_log_selector(self) -> None:
        assert _is_metric_query('{job="api"}') is False

    def test_log_selector_with_filter(self) -> None:
        assert _is_metric_query('{job="api"} |= "error"') is False


class TestBuildSeverityRegex:
    """Test _build_severity_regex helper function."""

    def test_severity_info(self) -> None:
        assert _build_severity_regex("info") == "info|warn|warning|error|fatal|critical"

    def test_severity_error(self) -> None:
        assert _build_severity_regex("error") == "error|fatal|critical"

    def test_severity_fatal(self) -> None:
        assert _build_severity_regex("fatal") == "fatal|critical"

    def test_severity_debug(self) -> None:
        assert _build_severity_regex("debug") == "debug|info|warn|warning|error|fatal|critical"

    def test_severity_trace(self) -> None:
        assert _build_severity_regex("trace") == "trace|debug|info|warn|warning|error|fatal|critical"

    def test_severity_warn_alias(self) -> None:
        assert _build_severity_regex("warn") == "warn|warning|error|fatal|critical"

    def test_severity_warning_alias(self) -> None:
        assert _build_severity_regex("warning") == "warn|warning|error|fatal|critical"

    def test_severity_critical_alias(self) -> None:
        assert _build_severity_regex("critical") == "fatal|critical"

    def test_severity_invalid(self) -> None:
        with pytest.raises(ValueError):
            _build_severity_regex("unknown")


class TestResolveSince:
    """Test _resolve_since helper function."""

    def test_since_minutes(self) -> None:
        result = _resolve_since(10, None, None)
        assert result is not None
        start, end = result
        assert end > start
        # 10 minutes in nanoseconds
        assert (end - start) == 10 * 60 * 1_000_000_000

    def test_since_hours(self) -> None:
        result = _resolve_since(None, 2, None)
        assert result is not None
        start, end = result
        assert (end - start) == 2 * 60 * 60 * 1_000_000_000

    def test_since_days(self) -> None:
        result = _resolve_since(None, None, 3)
        assert result is not None
        start, end = result
        assert (end - start) == 3 * 24 * 60 * 60 * 1_000_000_000

    def test_none_returns_none(self) -> None:
        assert _resolve_since(None, None, None) is None

    def test_minutes_takes_priority(self) -> None:
        result = _resolve_since(10, 2, 3)
        assert result is not None
        start, end = result
        assert (end - start) == 10 * 60 * 1_000_000_000


class TestLabelDiscovery:
    """Test label discovery methods."""

    def test_find_app_label_application(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            mock_glv.return_value = ["myapp", "otherapp"]
            result = client._find_app_label("myapp")
            assert result == "application"
            mock_glv.assert_called_once_with("application")

    def test_find_app_label_job(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            def side_effect(label: str) -> list[str]:
                if label == "job":
                    return ["myapp", "worker"]
                return []
            mock_glv.side_effect = side_effect

            result = client._find_app_label("myapp")
            assert result == "job"

    def test_find_app_label_not_found(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            mock_glv.return_value = []
            with pytest.raises(ValueError, match="Could not find 'myapp'"):
                client._find_app_label("myapp")

    def test_find_severity_label(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            mock_glv.return_value = ["info", "error", "warn"]
            result = client._find_severity_label()
            assert result == "level"
            mock_glv.assert_called_once_with("level")

    def test_find_severity_label_none(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            mock_glv.return_value = []
            result = client._find_severity_label()
            assert result is None

    def test_label_discovery_cached(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            mock_glv.return_value = ["myapp"]

            client._find_app_label("myapp")
            client._find_app_label("myapp")

            # Only called once - second call uses cache
            mock_glv.assert_called_once_with("application")

    def test_severity_label_cached(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "get_label_values") as mock_glv:
            mock_glv.return_value = ["info", "error"]

            client._find_severity_label()
            client._find_severity_label()

            mock_glv.assert_called_once_with("level")


class TestLokiClientQueryRedesign:
    """Test redesigned query() method."""

    def test_query_app_only(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "_find_app_label", return_value="application"), \
             patch.object(client, "query_range") as mock_qr:
            mock_qr.return_value = MagicMock()

            client.query(app="myapp")

            mock_qr.assert_called_once()
            args = mock_qr.call_args
            assert args.kwargs["logql"] == '{application="myapp"}'
            assert args.kwargs["limit"] == 100
            assert args.kwargs["direction"] == "backward"

    def test_query_app_with_severity(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "_find_app_label", return_value="application"), \
             patch.object(client, "_find_severity_label", return_value="level"), \
             patch.object(client, "query_range") as mock_qr:
            mock_qr.return_value = MagicMock()

            client.query(app="myapp", severity="error")

            args = mock_qr.call_args
            assert args.kwargs["logql"] == '{application="myapp", level=~"error|fatal|critical"}'

    def test_query_app_since_minutes(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "_find_app_label", return_value="application"), \
             patch.object(client, "query_range") as mock_qr:
            mock_qr.return_value = MagicMock()

            client.query(app="myapp", since_minutes=10)

            args = mock_qr.call_args
            start = args.kwargs["start"]
            end = args.kwargs["end"]
            diff_minutes = (end - start) / (60 * 1_000_000_000)
            assert diff_minutes == 10

    def test_query_logql_passthrough(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "query_range") as mock_qr:
            mock_qr.return_value = MagicMock()

            client.query(logql='{custom="query"}')

            args = mock_qr.call_args
            assert args.kwargs["logql"] == '{custom="query"}'

    def test_query_logql_with_app_raises(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with pytest.raises(ValueError, match="Cannot combine"):
            client.query(logql='{job="test"}', app="myapp")

    def test_query_metric_instant(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "_request") as mock_req:
            mock_req.return_value = {
                "status": "success",
                "data": {"resultType": "vector", "result": []}
            }

            client.query(logql='count_over_time({job="api"}[5m])')

            mock_req.assert_called_once()
            args = mock_req.call_args
            assert args.args[1] == "/loki/api/v1/query"

    def test_query_neither_raises(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with pytest.raises(ValueError, match="Must provide"):
            client.query()

    def test_query_default_30_day_lookback(self) -> None:
        client = LokiClient(base_url="http://localhost:3100")
        with patch.object(client, "_find_app_label", return_value="job"), \
             patch.object(client, "query_range") as mock_qr:
            mock_qr.return_value = MagicMock()

            client.query(app="myapp")

            args = mock_qr.call_args
            start = args.kwargs["start"]
            end = args.kwargs["end"]
            diff_days = (end - start) / (24 * 60 * 60 * 1_000_000_000)
            assert diff_days == 30
