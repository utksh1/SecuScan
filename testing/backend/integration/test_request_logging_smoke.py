# testing/backend/integration/test_request_logging_smoke.py

import io
import json
import logging
import re

import pytest
from backend.secuscan.logging_utils import JSONFormatter, RequestIDFilter

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

@pytest.fixture
def log_capture():
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(RequestIDFilter())
    handler.setFormatter(JSONFormatter())
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield buf
    finally:
        root.removeHandler(handler)
        handler.close()

def _parse_log_lines(buf):
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]

def test_request_id_appears_in_json_logs(test_client, log_capture):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")
    assert request_id, "Middleware must echo X-Request-ID header"
    assert UUID4_RE.match(request_id), "Request ID must be a valid UUID4"

    entries = _parse_log_lines(log_capture)
    assert entries, "At least one JSON log line must be emitted"

    for entry in entries:
        for key in ("timestamp", "level", "request_id", "logger", "message"):
            assert key in entry, f"Log entry missing key '{key}': {entry}"

    correlated = [e for e in entries if e["request_id"] == request_id]
    assert correlated, (
        f"No log line carries request_id={request_id!r}. "
        f"Seen IDs: {[e['request_id'] for e in entries]}"
    )

def test_passthrough_request_id(test_client, log_capture):
    custom_id = "smoke-test-trace-abc123"
    response = test_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("X-Request-ID") == custom_id

    entries = _parse_log_lines(log_capture)
    correlated = [e for e in entries if e["request_id"] == custom_id]
    assert correlated, "Passthrough request ID must appear in logs"
