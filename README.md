# loki-reader-core

A lightweight Python library for querying Grafana Loki logs via REST API.

## Features

- Simple, intuitive client for Loki's HTTP API
- Supports `query`, `query_range`, label discovery, and series matching
- SSL/TLS support including custom CA certificates for self-signed certs
- Multi-tenant support via `X-Scope-OrgID` header
- Basic authentication
- Clean dataclass models with `to_dict()`/`from_dict()` serialization
- All timestamps as Unix nanoseconds (Loki's native format)

## Installation

From PyPI:

```bash
pip install loki-reader-core
```

From GitHub:

```bash
pip install loki-reader-core @ git+ssh://git@github.com/jmazzahacks/loki-reader-core.git@main
```

## Usage

### Basic Query

```python
from loki_reader_core import LokiClient
from loki_reader_core.utils import hours_ago_ns, now_ns

client = LokiClient(base_url="https://loki.example.com")

result = client.query_range(
    logql='{job="api-server"} |= "error"',
    start=hours_ago_ns(1),
    end=now_ns(),
    limit=500
)

for stream in result.streams:
    print(f"Labels: {stream.labels}")
    for entry in stream.entries:
        print(f"  [{entry.timestamp}] {entry.message}")
```

### With Authentication and Self-Signed Certificates

```python
client = LokiClient(
    base_url="https://loki.internal.company.com:8443",
    auth=("username", "password"),
    ca_cert="/path/to/ca.pem"
)
```

### Multi-Tenant Setup

```python
client = LokiClient(
    base_url="https://loki.example.com",
    org_id="tenant-1"
)
```

### Exploring Labels

```python
labels = client.get_labels()
values = client.get_label_values("application")
series = client.get_series(match=['{application="my-app"}'])
```

### Context Manager

```python
with LokiClient(base_url="https://loki.example.com") as client:
    result = client.query(logql='{job="api"}')
```

## API Reference

### LokiClient

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | required | Loki server URL |
| `auth` | `tuple[str, str]` | `None` | Basic auth `(username, password)` |
| `org_id` | `str` | `None` | `X-Scope-OrgID` for multi-tenant |
| `ca_cert` | `str` | `None` | Path to CA certificate PEM file |
| `verify_ssl` | `bool` | `True` | Set `False` to disable SSL verification |
| `timeout` | `int` | `30` | Request timeout in seconds |

### Methods

| Method | Description |
|--------|-------------|
| `query(logql, time, limit)` | Instant query at a single point in time |
| `query_range(logql, start, end, limit, direction)` | Query across a time range |
| `get_labels(start, end)` | List available label names |
| `get_label_values(label, start, end)` | List values for a specific label |
| `get_series(match, start, end)` | List streams matching selectors |

### Timestamp Utilities

```python
from loki_reader_core.utils import (
    now_ns,          # Current time as nanoseconds
    seconds_to_ns,   # Convert Unix seconds to nanoseconds
    ns_to_seconds,   # Convert nanoseconds to Unix seconds
    minutes_ago_ns,  # Timestamp N minutes ago
    hours_ago_ns,    # Timestamp N hours ago
    days_ago_ns,     # Timestamp N days ago
)
```

## Development

### Setup

```bash
# Create virtual environment
python -m venv .

# Activate virtual environment
source bin/activate

# Install dependencies
pip install -r dev-requirements.txt
pip install -e .
```

### Running Tests

```bash
source bin/activate
pytest tests/ -v
```

## License

MIT

## Author

Jason Byteforge (@jmazzahacks)
