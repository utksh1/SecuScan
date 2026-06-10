import json
import logging

from backend.secuscan.logging_utils import RequestIDFilter, JSONFormatter


def test_request_id_filter_fallback(monkeypatch):
    monkeypatch.setattr(
        "backend.secuscan.logging_utils.get_request_id",
        lambda: None,
    )

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    filt = RequestIDFilter()
    assert filt.filter(record) is True
    assert record.request_id == "no-request-id"


def test_json_formatter_serializes_log_record():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"

    formatter = JSONFormatter()
    result = json.loads(formatter.format(record))

    assert result["level"] == "INFO"
    assert result["logger"] == "test_logger"
    assert result["message"] == "hello world"
    assert result["request_id"] == "req-123"
    assert "timestamp" in result


def test_json_formatter_serializes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = __import__("sys").exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="failure",
        args=(),
        exc_info=exc_info,
    )

    formatter = JSONFormatter()
    result = json.loads(formatter.format(record))

    assert "exception" in result
    assert "ValueError" in result["exception"]