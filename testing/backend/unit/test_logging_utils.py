import json
import logging
import sys

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


def test_json_formatter_handles_null_bytes_in_message():
    """A message containing null bytes should not cause JSON serialization to fail."""
    import json
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token=abc123" + chr(0) + "extra",
        args=(),
        exc_info=None,
    )
    formatter = JSONFormatter()
    result_str = formatter.format(record)
    # Should not raise and should produce valid JSON
    result = json.loads(result_str)
    assert isinstance(result, dict)
    assert "timestamp" in result
    assert "level" in result


def test_json_formatter_handles_non_string_message():
    """A record whose getMessage() would return a non-string value should not crash."""
    import json
    # Create a record with a dict msg and args that when interpolated produce a non-string
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="%(key)s",
        args=({"key": "value"},),
        exc_info=None,
    )
    formatter = JSONFormatter()
    # Should not raise
    result_str = formatter.format(record)
    result = json.loads(result_str)
    assert isinstance(result, dict)


def test_json_formatter_combines_exc_info_and_custom_request_id():
    """Both exception info and a custom request_id should appear in the output."""
    import json
    try:
        raise ValueError("test error")
    except ValueError:
        exc_info = sys.exc_info()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="error with context",
        args=(),
        exc_info=exc_info,
    )
    # Manually set request_id on the record to simulate RequestIDFilter behavior
    record.request_id = "req-123-custom-id"
    formatter = JSONFormatter()
    result = json.loads(formatter.format(record))
    assert "exception" in result
    assert "ValueError" in result["exception"]
    assert result["request_id"] == "req-123-custom-id"


def test_json_formatter_handles_very_long_message():
    """A 1MB+ message string should be handled without crashing."""
    import json
    long_msg = "A" * (1024 * 1024)  # 1MB
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=long_msg,
        args=(),
        exc_info=None,
    )
    formatter = JSONFormatter()
    result_str = formatter.format(record)
    result = json.loads(result_str)
    assert result["message"] == long_msg
    assert len(result["message"]) == 1024 * 1024
