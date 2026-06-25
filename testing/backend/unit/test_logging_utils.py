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


def test_request_id_filter_adds_request_id_field():
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
    assert hasattr(record, "request_id")
    assert record.request_id != ""


def test_json_formatter_adds_request_id_field():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    formatter = JSONFormatter()
    result = json.loads(formatter.format(record))

    assert "request_id" in result


def test_json_formatter_timestamp_is_iso_format():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    formatter = JSONFormatter()
    result = json.loads(formatter.format(record))

    from datetime import datetime
    ts = result["timestamp"]
    # ISO format with timezone
    assert "T" in ts
    assert "+" in ts or "Z" in ts
    # Should parse as datetime
    assert datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_json_formatter_log_level_names():
    for level, name in [(logging.DEBUG, "DEBUG"), (logging.INFO, "INFO"),
                        (logging.WARNING, "WARNING"), (logging.ERROR, "ERROR")]:
        record = logging.LogRecord(
            name="test",
            level=level,
            pathname=__file__,
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        formatter = JSONFormatter()
        result = json.loads(formatter.format(record))
        assert result["level"] == name


def test_json_formatter_no_exception_key_when_no_exc_info():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="normal log",
        args=(),
        exc_info=None,
    )

    formatter = JSONFormatter()
    result = json.loads(formatter.format(record))

    assert "exception" not in result
    assert result["message"] == "normal log"
