"""Tests for LokiClient."""

from unittest.mock import MagicMock, patch

import pytest

from loki_reader_core import LokiClient
from loki_reader_core.exceptions import LokiAuthError, LokiConnectionError, LokiQueryError


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
    def test_query_basic(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [],
                "stats": {"summary": {}}
            }
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")
        result = client.query(logql='{job="test"}')

        assert result.status == "success"
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args.kwargs["params"]["query"] == '{job="test"}'
        assert call_args.kwargs["params"]["limit"] == 100

    @patch("loki_reader_core.client.requests.Session")
    def test_query_with_time(self, mock_session_class: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "streams", "result": []}
        }
        mock_session.request.return_value = mock_response

        client = LokiClient(base_url="http://localhost:3100")
        client.query(logql='{job="test"}', time=1704067200000000000)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["params"]["time"] == "1704067200000000000"

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
