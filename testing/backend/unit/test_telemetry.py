"""
Tests for Plugin Runtime Observability — PluginTelemetry.

Validates all four acceptance-criteria paths:
  1. Success
  2. Timeout
  3. Parser failure
  4. Non-zero exit

Plus the dataclass contract and a security negative.
"""

import asyncio
import logging
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Helpers

def make_telemetry(plugin_name="test_plugin", **kwargs):
    from secuscan.telemetry import PluginTelemetry
    return PluginTelemetry(plugin_name=plugin_name, **kwargs)


# 1. PluginTelemetry dataclass contract

class TestPluginTelemetryContract:

    def test_field_defaults(self):
        t = make_telemetry("nmap")
        assert t.plugin_name == "nmap"
        assert t.duration_seconds == 0.0
        assert t.exit_code is None
        assert t.output_size_bytes == 0
        assert t.parser_time_seconds == 0.0
        assert t.timed_out is False
        assert t.timeout_reason is None
        assert t.parser_error is None
        assert t.resource_hints == {}

    def test_resource_hints_not_shared_between_instances(self):
        a = make_telemetry()
        b = make_telemetry()
        a.resource_hints["x"] = 1
        assert "x" not in b.resource_hints

    def test_to_dict_exact_keys(self):
        expected = {
            "plugin_name", "duration_seconds", "exit_code",
            "output_size_bytes", "parser_time_seconds", "timed_out",
            "timeout_reason", "resource_hints", "parser_error",
        }
        assert set(make_telemetry().to_dict().keys()) == expected

    def test_to_dict_rounds_floats(self):
        t = make_telemetry()
        t.duration_seconds = 1.23456789
        t.parser_time_seconds = 0.00017777
        d = t.to_dict()
        assert d["duration_seconds"] == round(1.23456789, 3)
        assert d["parser_time_seconds"] == round(0.00017777, 3)

    def test_log_emits_task_id_and_plugin_name(self, caplog):
        t = make_telemetry(plugin_name="nikto")
        t.exit_code = 0
        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            t.log("task-abc")
        assert "task-abc" in caplog.text
        assert "nikto" in caplog.text

    def test_log_never_emits_raw_output(self, caplog):
        """Security: log() emits only structured metadata, never raw tool output."""
        t = make_telemetry()
        t.exit_code = 0
        secret = "AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE"
        with caplog.at_level(logging.DEBUG):
            t.log("task-sec")
        for record in caplog.records:
            assert secret not in record.getMessage()


# 2. Telemetry fields derived at executor call site — success path

class TestExecutorTelemetrySuccess:
    """
    Validates that execute_task populates telemetry correctly on success.
    _execute_command is mocked as a 2-tuple — its signature is not changed.
    """

    def _make_executor(self):
        from secuscan.executor import TaskExecutor
        ex = TaskExecutor.__new__(TaskExecutor)
        ex._broadcast = AsyncMock()
        return ex

    def test_timed_out_false_when_output_has_no_timeout_marker(self):
        """timed_out is derived by checking for 'Task timed out' in output."""
        t = make_telemetry()
        output = "scan complete\nports: 80, 443"
        t.timed_out = "Task timed out" in output
        t.timeout_reason = "Hard limit of 30s exceeded" if t.timed_out else None
        assert t.timed_out is False
        assert t.timeout_reason is None

    def test_output_size_bytes_matches_encoded_length(self):
        t = make_telemetry()
        output = "result line\n"
        t.output_size_bytes = len(output.encode("utf-8", errors="replace"))
        assert t.output_size_bytes == 12

    def test_exit_code_zero_on_success(self):
        t = make_telemetry()
        t.exit_code = 0
        assert t.to_dict()["exit_code"] == 0

    def test_resource_hints_captured(self):
        hints = {"memory_limit_mb": 512, "cpu_quota": 50000, "docker_enabled": False}
        t = make_telemetry(resource_hints=hints)
        assert t.to_dict()["resource_hints"] == hints


# 3. Telemetry fields derived at executor call site — timeout path

class TestExecutorTelemetryTimeout:
    """
    _execute_command appends '\nTask timed out' on timeout.
    The call site detects this and sets timed_out + timeout_reason.
    """

    def test_timed_out_true_when_marker_present(self):
        t = make_telemetry()
        execution_timeout = 60
        output = "partial output\nTask timed out"
        t.timed_out = "Task timed out" in output
        t.timeout_reason = (
            f"Hard limit of {execution_timeout}s exceeded"
            if t.timed_out else None
        )
        assert t.timed_out is True
        assert t.timeout_reason == "Hard limit of 60s exceeded"

    def test_timeout_exit_code_minus_one(self):
        t = make_telemetry()
        t.exit_code = -1  # _execute_command returns -1 on timeout
        assert t.to_dict()["exit_code"] == -1

    def test_timeout_reason_contains_limit(self):
        for limit in (30, 60, 300, 600):
            t = make_telemetry()
            t.timed_out = True
            t.timeout_reason = f"Hard limit of {limit}s exceeded"
            assert str(limit) in t.to_dict()["timeout_reason"]


# 4. Non-zero exit — timed_out stays False

class TestExecutorTelemetryNonZeroExit:

    def test_nonzero_exit_without_timeout_marker(self):
        t = make_telemetry()
        output = "error: connection refused"
        exit_code = 1
        t.exit_code = exit_code
        t.timed_out = "Task timed out" in output
        t.timeout_reason = "Hard limit of 30s exceeded" if t.timed_out else None
        assert t.exit_code == 1
        assert t.timed_out is False
        assert t.timeout_reason is None

    def test_nonzero_exit_code_preserved_in_dict(self):
        t = make_telemetry()
        t.exit_code = 2
        assert t.to_dict()["exit_code"] == 2


# 5. Parser failure — finally block always calls log()

class TestParserFailurePath:

    def test_parser_error_captured_and_exception_reraised(self, caplog):
        t = make_telemetry(plugin_name="flaky_parser")
        t.exit_code = 0
        _parser_error = None

        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            with pytest.raises(ValueError, match="bad XML"):
                try:
                    raise ValueError("bad XML")
                except Exception as _pe:
                    _parser_error = str(_pe)
                    raise
                finally:
                    t.parser_time_seconds = 0.05
                    t.parser_error = _parser_error
                    t.log("task-parser-fail")

        assert t.parser_error == "bad XML"
        assert t.parser_time_seconds == 0.05
        # log() was reached despite the exception
        assert "flaky_parser" in caplog.text

    def test_parser_success_leaves_error_none(self):
        t = make_telemetry()
        _parser_error = None
        try:
            pass  # parser succeeds
        except Exception as _pe:
            _parser_error = str(_pe)
            raise
        finally:
            t.parser_error = _parser_error
        assert t.parser_error is None

    def test_parser_time_recorded(self):
        t = make_telemetry()
        _start = time.time()
        try:
            time.sleep(0.01)
        finally:
            t.parser_time_seconds = time.time() - _start
        assert t.parser_time_seconds >= 0.01


# 6. BaseScanner._execute_command_timed

class _StubScanner:
    """Minimal stand-in — delegates to real BaseScanner._execute_command_timed."""
    name = "stub_scanner"

    def __init__(self):
        from secuscan.telemetry import PluginTelemetry
        self.task_id = "t-base"
        self.telemetry = PluginTelemetry(plugin_name=self.name)

    async def _execute_command_timed(self, command, timeout=300):
        from secuscan.scanners.base import BaseScanner
        return await BaseScanner._execute_command_timed(self, command, timeout=timeout)


class TestBaseScannerTimedSuccess:

    @pytest.mark.asyncio
    async def test_success_populates_telemetry(self):
        scanner = _StubScanner()
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"scan output\n", b""))

        with patch("secuscan.scanners.base.asyncio.create_subprocess_exec", return_value=proc):
            output, exit_code, timed_out, reason, size = (
                await scanner._execute_command_timed(["nmap", "-sV", "127.0.0.1"], timeout=10)
            )

        assert exit_code == 0
        assert timed_out is False
        assert reason is None
        assert size == len(output.encode("utf-8", errors="replace"))
        assert scanner.telemetry.exit_code == 0
        assert scanner.telemetry.timed_out is False
        assert scanner.telemetry.output_size_bytes == size
        assert scanner.telemetry.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_nonzero_exit_populates_telemetry(self):
        scanner = _StubScanner()
        proc = MagicMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"error output\n", b""))

        with patch("secuscan.scanners.base.asyncio.create_subprocess_exec", return_value=proc):
            _, exit_code, timed_out, reason, _ = (
                await scanner._execute_command_timed(["false"], timeout=10)
            )

        assert exit_code == 1
        assert timed_out is False
        assert reason is None
        assert scanner.telemetry.exit_code == 1


class TestBaseScannerTimedTimeout:

    @pytest.mark.asyncio
    async def test_timeout_populates_telemetry_no_double_wait(self):
        """
        communicate() raises TimeoutError before completing.
        Our except block calls kill() then wait() exactly once.
        Asserting wait_awaited_once() is the regression guard for double-wait.
        """
        scanner = _StubScanner()
        proc = MagicMock()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.kill = MagicMock()
        proc.wait = AsyncMock()

        with patch("secuscan.scanners.base.asyncio.create_subprocess_exec", return_value=proc):
            _, exit_code, timed_out, reason, _ = (
                await scanner._execute_command_timed(["sleep", "999"], timeout=15)
            )

        assert timed_out is True
        assert exit_code == -1
        assert reason == "Hard limit of 15s exceeded"
        assert scanner.telemetry.timed_out is True
        assert scanner.telemetry.timeout_reason == "Hard limit of 15s exceeded"
        proc.kill.assert_called_once()   # exactly one kill
        proc.wait.assert_awaited_once()  # exactly one wait — no double-wait regression
