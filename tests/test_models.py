"""Tests for data models."""

from loki_reader_core.models import (
    LogEntry, LogStream, MetricSample, MetricSeries, QueryResult, QueryStats
)


class TestLogEntry:
    """Test LogEntry model."""

    def test_create_entry(self) -> None:
        entry = LogEntry(timestamp=1704067200000000000, message="test log")
        assert entry.timestamp == 1704067200000000000
        assert entry.message == "test log"

    def test_to_dict(self) -> None:
        entry = LogEntry(timestamp=1704067200000000000, message="test log")
        result = entry.to_dict()
        assert result == {
            "timestamp": 1704067200000000000,
            "message": "test log"
        }

    def test_from_dict(self) -> None:
        data = {"timestamp": 1704067200000000000, "message": "test log"}
        entry = LogEntry.from_dict(data)
        assert entry.timestamp == 1704067200000000000
        assert entry.message == "test log"

    def test_from_dict_string_timestamp(self) -> None:
        data = {"timestamp": "1704067200000000000", "message": "test log"}
        entry = LogEntry.from_dict(data)
        assert entry.timestamp == 1704067200000000000

    def test_from_loki_value(self) -> None:
        value = ["1704067200000000000", "test log message"]
        entry = LogEntry.from_loki_value(value)
        assert entry.timestamp == 1704067200000000000
        assert entry.message == "test log message"

    def test_roundtrip(self) -> None:
        original = LogEntry(timestamp=1704067200000000000, message="test")
        restored = LogEntry.from_dict(original.to_dict())
        assert restored.timestamp == original.timestamp
        assert restored.message == original.message


class TestLogStream:
    """Test LogStream model."""

    def test_create_stream(self) -> None:
        entries = [
            LogEntry(timestamp=1704067200000000000, message="log 1"),
            LogEntry(timestamp=1704067201000000000, message="log 2"),
        ]
        stream = LogStream(labels={"job": "api"}, entries=entries)
        assert stream.labels == {"job": "api"}
        assert len(stream.entries) == 2

    def test_to_dict(self) -> None:
        entries = [LogEntry(timestamp=1704067200000000000, message="log 1")]
        stream = LogStream(labels={"job": "api"}, entries=entries)
        result = stream.to_dict()
        assert result["labels"] == {"job": "api"}
        assert len(result["entries"]) == 1
        assert result["entries"][0]["message"] == "log 1"

    def test_from_dict(self) -> None:
        data = {
            "labels": {"job": "api", "env": "prod"},
            "entries": [
                {"timestamp": 1704067200000000000, "message": "log 1"},
                {"timestamp": 1704067201000000000, "message": "log 2"},
            ]
        }
        stream = LogStream.from_dict(data)
        assert stream.labels == {"job": "api", "env": "prod"}
        assert len(stream.entries) == 2
        assert stream.entries[0].message == "log 1"

    def test_from_loki_stream(self) -> None:
        loki_data = {
            "stream": {"job": "api", "container": "web"},
            "values": [
                ["1704067200000000000", "first log"],
                ["1704067201000000000", "second log"],
            ]
        }
        stream = LogStream.from_loki_stream(loki_data)
        assert stream.labels == {"job": "api", "container": "web"}
        assert len(stream.entries) == 2
        assert stream.entries[0].timestamp == 1704067200000000000
        assert stream.entries[1].message == "second log"

    def test_roundtrip(self) -> None:
        original = LogStream(
            labels={"job": "test"},
            entries=[LogEntry(timestamp=123, message="msg")]
        )
        restored = LogStream.from_dict(original.to_dict())
        assert restored.labels == original.labels
        assert len(restored.entries) == len(original.entries)


class TestMetricSample:
    """Test MetricSample model."""

    def test_create_sample(self) -> None:
        sample = MetricSample(timestamp=1704067200000000000, value=42.5)
        assert sample.timestamp == 1704067200000000000
        assert sample.value == 42.5

    def test_to_dict(self) -> None:
        sample = MetricSample(timestamp=1704067200000000000, value=42.5)
        result = sample.to_dict()
        assert result == {
            "timestamp": 1704067200000000000,
            "value": 42.5
        }

    def test_from_dict(self) -> None:
        data = {"timestamp": 1704067200000000000, "value": 42.5}
        sample = MetricSample.from_dict(data)
        assert sample.timestamp == 1704067200000000000
        assert sample.value == 42.5

    def test_from_loki_value(self) -> None:
        # Loki returns [unix_seconds_float, "string_value"]
        value = [1704067200, "42.5"]
        sample = MetricSample.from_loki_value(value)
        # Should convert seconds to nanoseconds
        assert sample.timestamp == 1704067200000000000
        # Should parse string value to float
        assert sample.value == 42.5

    def test_from_loki_value_float_timestamp(self) -> None:
        # Loki sometimes returns fractional seconds
        value = [1704067200.5, "100"]
        sample = MetricSample.from_loki_value(value)
        assert sample.timestamp == 1704067200500000000
        assert sample.value == 100.0

    def test_roundtrip(self) -> None:
        original = MetricSample(timestamp=1704067200000000000, value=99.9)
        restored = MetricSample.from_dict(original.to_dict())
        assert restored.timestamp == original.timestamp
        assert restored.value == original.value


class TestMetricSeries:
    """Test MetricSeries model."""

    def test_create_series(self) -> None:
        samples = [
            MetricSample(timestamp=1704067200000000000, value=10.0),
            MetricSample(timestamp=1704067260000000000, value=20.0),
        ]
        series = MetricSeries(labels={"application": "api"}, samples=samples)
        assert series.labels == {"application": "api"}
        assert len(series.samples) == 2

    def test_to_dict(self) -> None:
        samples = [MetricSample(timestamp=1704067200000000000, value=10.0)]
        series = MetricSeries(labels={"application": "api"}, samples=samples)
        result = series.to_dict()
        assert result["labels"] == {"application": "api"}
        assert len(result["samples"]) == 1
        assert result["samples"][0]["value"] == 10.0

    def test_from_dict(self) -> None:
        data = {
            "labels": {"application": "api"},
            "samples": [
                {"timestamp": 1704067200000000000, "value": 10.0},
                {"timestamp": 1704067260000000000, "value": 20.0},
            ]
        }
        series = MetricSeries.from_dict(data)
        assert series.labels == {"application": "api"}
        assert len(series.samples) == 2
        assert series.samples[1].value == 20.0

    def test_from_loki_matrix(self) -> None:
        loki_data = {
            "metric": {"application": "hive-watcher", "severity": "info"},
            "values": [
                [1704067200, "150"],
                [1704067260, "175"],
                [1704067320, "200"],
            ]
        }
        series = MetricSeries.from_loki_matrix(loki_data)
        assert series.labels == {"application": "hive-watcher", "severity": "info"}
        assert len(series.samples) == 3
        assert series.samples[0].timestamp == 1704067200000000000
        assert series.samples[0].value == 150.0
        assert series.samples[2].value == 200.0

    def test_from_loki_vector(self) -> None:
        loki_data = {
            "metric": {"application": "hive-watcher"},
            "value": [1704067200, "42"]
        }
        series = MetricSeries.from_loki_vector(loki_data)
        assert series.labels == {"application": "hive-watcher"}
        assert len(series.samples) == 1
        assert series.samples[0].timestamp == 1704067200000000000
        assert series.samples[0].value == 42.0

    def test_roundtrip(self) -> None:
        original = MetricSeries(
            labels={"job": "test"},
            samples=[MetricSample(timestamp=123000000000, value=5.5)]
        )
        restored = MetricSeries.from_dict(original.to_dict())
        assert restored.labels == original.labels
        assert len(restored.samples) == len(original.samples)
        assert restored.samples[0].value == original.samples[0].value


class TestQueryStats:
    """Test QueryStats model."""

    def test_create_stats(self) -> None:
        stats = QueryStats(
            bytes_processed=1024,
            lines_processed=100,
            exec_time_seconds=0.5
        )
        assert stats.bytes_processed == 1024
        assert stats.lines_processed == 100
        assert stats.exec_time_seconds == 0.5

    def test_to_dict(self) -> None:
        stats = QueryStats(
            bytes_processed=1024,
            lines_processed=100,
            exec_time_seconds=0.5
        )
        result = stats.to_dict()
        assert result == {
            "bytes_processed": 1024,
            "lines_processed": 100,
            "exec_time_seconds": 0.5
        }

    def test_from_dict(self) -> None:
        data = {
            "bytes_processed": 2048,
            "lines_processed": 200,
            "exec_time_seconds": 1.5
        }
        stats = QueryStats.from_dict(data)
        assert stats.bytes_processed == 2048
        assert stats.lines_processed == 200
        assert stats.exec_time_seconds == 1.5

    def test_from_dict_with_defaults(self) -> None:
        stats = QueryStats.from_dict({})
        assert stats.bytes_processed == 0
        assert stats.lines_processed == 0
        assert stats.exec_time_seconds == 0.0

    def test_from_loki_stats(self) -> None:
        loki_stats = {
            "summary": {
                "totalBytesProcessed": 4096,
                "totalLinesProcessed": 500,
                "execTime": 2.5
            },
            "querier": {},
            "ingester": {}
        }
        stats = QueryStats.from_loki_stats(loki_stats)
        assert stats.bytes_processed == 4096
        assert stats.lines_processed == 500
        assert stats.exec_time_seconds == 2.5


class TestQueryResult:
    """Test QueryResult model."""

    def test_create_result(self) -> None:
        streams = [
            LogStream(labels={"job": "api"}, entries=[])
        ]
        stats = QueryStats(bytes_processed=0, lines_processed=0, exec_time_seconds=0.0)
        result = QueryResult(status="success", streams=streams, stats=stats)
        assert result.status == "success"
        assert len(result.streams) == 1
        assert result.stats is not None

    def test_create_result_no_stats(self) -> None:
        result = QueryResult(status="success", streams=[], stats=None)
        assert result.stats is None

    def test_to_dict(self) -> None:
        streams = [
            LogStream(
                labels={"job": "api"},
                entries=[LogEntry(timestamp=123, message="test")]
            )
        ]
        stats = QueryStats(bytes_processed=100, lines_processed=1, exec_time_seconds=0.1)
        result = QueryResult(status="success", streams=streams, stats=stats)

        data = result.to_dict()
        assert data["status"] == "success"
        assert len(data["streams"]) == 1
        assert data["stats"]["bytes_processed"] == 100

    def test_to_dict_no_stats(self) -> None:
        result = QueryResult(status="success", streams=[], stats=None)
        data = result.to_dict()
        assert data["stats"] is None

    def test_from_dict(self) -> None:
        data = {
            "status": "success",
            "streams": [
                {
                    "labels": {"job": "test"},
                    "entries": [{"timestamp": 123, "message": "msg"}]
                }
            ],
            "stats": {
                "bytes_processed": 100,
                "lines_processed": 1,
                "exec_time_seconds": 0.1
            }
        }
        result = QueryResult.from_dict(data)
        assert result.status == "success"
        assert len(result.streams) == 1
        assert result.stats.bytes_processed == 100

    def test_from_loki_response(self) -> None:
        loki_response = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "api", "level": "error"},
                        "values": [
                            ["1704067200000000000", "error message 1"],
                            ["1704067201000000000", "error message 2"],
                        ]
                    }
                ],
                "stats": {
                    "summary": {
                        "totalBytesProcessed": 2048,
                        "totalLinesProcessed": 50,
                        "execTime": 0.25
                    }
                }
            }
        }
        result = QueryResult.from_loki_response(loki_response)
        assert result.status == "success"
        assert len(result.streams) == 1
        assert result.streams[0].labels["job"] == "api"
        assert len(result.streams[0].entries) == 2
        assert result.stats.bytes_processed == 2048

    def test_total_entries(self) -> None:
        streams = [
            LogStream(
                labels={"job": "api"},
                entries=[
                    LogEntry(timestamp=1, message="a"),
                    LogEntry(timestamp=2, message="b"),
                ]
            ),
            LogStream(
                labels={"job": "web"},
                entries=[
                    LogEntry(timestamp=3, message="c"),
                ]
            )
        ]
        result = QueryResult(status="success", streams=streams, stats=None)
        assert result.total_entries == 3

    def test_total_entries_empty(self) -> None:
        result = QueryResult(status="success", streams=[], stats=None)
        assert result.total_entries == 0

    def test_from_loki_response_matrix(self) -> None:
        loki_response = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"application": "hive-watcher", "severity": "info"},
                        "values": [
                            [1704067200, "150"],
                            [1704067260, "175"],
                        ]
                    },
                    {
                        "metric": {"application": "hive-watcher", "severity": "error"},
                        "values": [
                            [1704067200, "5"],
                            [1704067260, "3"],
                        ]
                    }
                ],
                "stats": {
                    "summary": {
                        "totalBytesProcessed": 2684354560,
                        "totalLinesProcessed": 1000000,
                        "execTime": 1.5
                    }
                }
            }
        }
        result = QueryResult.from_loki_response(loki_response)
        assert result.status == "success"
        assert result.result_type == "matrix"
        assert len(result.streams) == 0
        assert len(result.metric_series) == 2
        assert result.metric_series[0].labels["severity"] == "info"
        assert len(result.metric_series[0].samples) == 2
        assert result.metric_series[0].samples[0].value == 150.0
        assert result.metric_series[1].samples[1].value == 3.0
        assert result.stats.bytes_processed == 2684354560

    def test_from_loki_response_vector(self) -> None:
        loki_response = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"application": "hive-watcher"},
                        "value": [1704067200, "12345"]
                    },
                    {
                        "metric": {"application": "thumbor"},
                        "value": [1704067200, "6789"]
                    }
                ],
                "stats": {
                    "summary": {
                        "totalBytesProcessed": 1024,
                        "totalLinesProcessed": 50,
                        "execTime": 0.1
                    }
                }
            }
        }
        result = QueryResult.from_loki_response(loki_response)
        assert result.status == "success"
        assert result.result_type == "vector"
        assert len(result.streams) == 0
        assert len(result.metric_series) == 2
        assert result.metric_series[0].labels["application"] == "hive-watcher"
        assert result.metric_series[0].samples[0].value == 12345.0
        assert result.metric_series[1].labels["application"] == "thumbor"
        assert result.metric_series[1].samples[0].value == 6789.0

    def test_from_loki_response_streams_has_result_type(self) -> None:
        loki_response = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [],
                "stats": {
                    "summary": {
                        "totalBytesProcessed": 0,
                        "totalLinesProcessed": 0,
                        "execTime": 0.0
                    }
                }
            }
        }
        result = QueryResult.from_loki_response(loki_response)
        assert result.result_type == "streams"
        assert len(result.metric_series) == 0

    def test_total_samples(self) -> None:
        series = [
            MetricSeries(
                labels={"app": "a"},
                samples=[
                    MetricSample(timestamp=1, value=10.0),
                    MetricSample(timestamp=2, value=20.0),
                ]
            ),
            MetricSeries(
                labels={"app": "b"},
                samples=[
                    MetricSample(timestamp=3, value=30.0),
                ]
            )
        ]
        result = QueryResult(
            status="success",
            streams=[],
            stats=None,
            result_type="matrix",
            metric_series=series,
        )
        assert result.total_samples == 3

    def test_to_dict_with_metric_series(self) -> None:
        series = [
            MetricSeries(
                labels={"app": "test"},
                samples=[MetricSample(timestamp=123000000000, value=42.0)]
            )
        ]
        result = QueryResult(
            status="success",
            streams=[],
            stats=None,
            result_type="matrix",
            metric_series=series,
        )
        data = result.to_dict()
        assert data["result_type"] == "matrix"
        assert len(data["metric_series"]) == 1
        assert data["metric_series"][0]["labels"] == {"app": "test"}

    def test_from_dict_with_metric_series(self) -> None:
        data = {
            "status": "success",
            "streams": [],
            "stats": None,
            "result_type": "matrix",
            "metric_series": [
                {
                    "labels": {"app": "test"},
                    "samples": [{"timestamp": 123000000000, "value": 42.0}]
                }
            ]
        }
        result = QueryResult.from_dict(data)
        assert result.result_type == "matrix"
        assert len(result.metric_series) == 1
        assert result.metric_series[0].samples[0].value == 42.0
