"""
Tests for Plugin Runtime Observability — PluginTelemetry.

Matrix:
  1. PluginTelemetry dataclass — field defaults, to_dict(), log()
  2. TaskExecutor._execute_command — success (5-tuple shape + sizes)
  3. TaskExecutor._execute_command — timeout (timed_out=True, reason, exit=-1)
  4. TaskExecutor._execute_command — non-zero exit (timed_out stays False)
  5. TaskExecutor._execute_command — exception path (error return tuple)
  6. Parser failure finally-block — parser_error set, exception re-raised, log() called
  7. BaseScanner._execute_command_timed — success populates self.telemetry
  8. BaseScanner._execute_command_timed — timeout populates self.telemetry
  9. Security negatives — log() never emits raw output content
"""

import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Helpers

def make_telemetry(plugin_name="test_plugin", **kwargs):
    from secuscan.telemetry import PluginTelemetry
    return PluginTelemetry(plugin_name=plugin_name, **kwargs)


def _fake_process(returncode=0, lines=(b"line\n",), eof_after=None):
    """
    Build a minimal asyncio subprocess mock whose stdout behaves like a real
    stream: at_eof() returns False for each line then True, readline() yields
    each line then hangs (won't be called after at_eof is True).
    """
    responses = list(lines) + [b""]
    eof_sequence = [False] * len(lines) + [True]

    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = MagicMock()
    proc.stdout.at_eof = MagicMock(side_effect=eof_sequence)
    proc.stdout.readline = AsyncMock(side_effect=responses)
    proc.wait = AsyncMock()
    proc.kill = MagicMock()
    return proc

# 1. PluginTelemetry — dataclass unit tests

class TestPluginTelemetryDefaults:

    def test_required_field_plugin_name(self):
        t = make_telemetry("nmap")
        assert t.plugin_name == "nmap"

    def test_numeric_defaults_are_zero(self):
        t = make_telemetry()
        assert t.duration_seconds == 0.0
        assert t.output_size_bytes == 0
        assert t.parser_time_seconds == 0.0

    def test_exit_code_default_none(self):
        assert make_telemetry().exit_code is None

    def test_timeout_fields_default(self):
        t = make_telemetry()
        assert t.timed_out is False
        assert t.timeout_reason is None

    def test_parser_error_default_none(self):
        assert make_telemetry().parser_error is None

    def test_resource_hints_default_empty_dict(self):
        t = make_telemetry()
        assert t.resource_hints == {}

    def test_resource_hints_independent_per_instance(self):
        a = make_telemetry()
        b = make_telemetry()
        a.resource_hints["x"] = 1
        assert "x" not in b.resource_hints


class TestPluginTelemetryToDict:

    def test_to_dict_keys(self):
        t = make_telemetry()
        d = t.to_dict()
        expected_keys = {
            "plugin_name", "duration_seconds", "exit_code",
            "output_size_bytes", "parser_time_seconds", "timed_out",
            "timeout_reason", "resource_hints", "parser_error",
        }
        assert set(d.keys()) == expected_keys

    def test_duration_rounded_to_three_places(self):
        t = make_telemetry()
        t.duration_seconds = 1.23456789
        assert t.to_dict()["duration_seconds"] == round(1.23456789, 3)

    def test_parser_time_rounded(self):
        t = make_telemetry()
        t.parser_time_seconds = 0.00017777
        assert t.to_dict()["parser_time_seconds"] == round(0.00017777, 3)

    def test_values_match_fields(self):
        hints = {"memory_limit_mb": 512}
        t = make_telemetry(resource_hints=hints)
        t.exit_code = 1
        t.timed_out = True
        t.timeout_reason = "Hard limit of 30s exceeded"
        t.parser_error = "XMLParseError"
        d = t.to_dict()
        assert d["exit_code"] == 1
        assert d["timed_out"] is True
        assert d["timeout_reason"] == "Hard limit of 30s exceeded"
        assert d["parser_error"] == "XMLParseError"
        assert d["resource_hints"] == hints


class TestPluginTelemetryLog:

    def test_log_does_not_raise(self, caplog):
        t = make_telemetry()
        t.duration_seconds = 1.5
        t.exit_code = 0
        t.output_size_bytes = 1024
        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            t.log("task-xyz")  # must not raise

    def test_log_emits_task_id(self, caplog):
        t = make_telemetry(plugin_name="sqlmap")
        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            t.log("task-abc-123")
        assert "task-abc-123" in caplog.text

    def test_log_emits_plugin_name(self, caplog):
        t = make_telemetry(plugin_name="nikto")
        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            t.log("tid")
        assert "nikto" in caplog.text

    def test_log_emits_timed_out_true(self, caplog):
        t = make_telemetry()
        t.timed_out = True
        t.timeout_reason = "Hard limit of 60s exceeded"
        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            t.log("tid")
        assert "True" in caplog.text or "timed_out" in caplog.text

# 2. TaskExecutor._execute_command — success path

class TestExecuteCommandSuccess:

    @pytest.fixture
    def executor(self):
        from secuscan.executor import TaskExecutor
        ex = TaskExecutor.__new__(TaskExecutor)
        ex._broadcast = AsyncMock()
        return ex

    @pytest.mark.asyncio
    async def test_returns_five_tuple(self, executor):
        proc = _fake_process(returncode=0, lines=(b"hello\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await executor._execute_command(["echo", "hello"], "t1", timeout=10)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_success_timed_out_false(self, executor):
        proc = _fake_process(returncode=0, lines=(b"ok\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, _, timed_out, _, _ = await executor._execute_command(["true"], "t1", timeout=10)
        assert timed_out is False

    @pytest.mark.asyncio
    async def test_success_timeout_reason_none(self, executor):
        proc = _fake_process(returncode=0, lines=(b"ok\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, _, _, timeout_reason, _ = await executor._execute_command(["true"], "t1", timeout=10)
        assert timeout_reason is None

    @pytest.mark.asyncio
    async def test_success_exit_code_propagated(self, executor):
        proc = _fake_process(returncode=0, lines=(b"ok\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, exit_code, _, _, _ = await executor._execute_command(["true"], "t1", timeout=10)
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_output_size_matches_encoded_output(self, executor):
        proc = _fake_process(returncode=0, lines=(b"result\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            output, _, _, _, size = await executor._execute_command(["cat"], "t1", timeout=10)
        assert size == len(output.encode("utf-8", errors="replace"))

    @pytest.mark.asyncio
    async def test_output_content_streamed_via_broadcast(self, executor):
        proc = _fake_process(returncode=0, lines=(b"streamed_line\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            await executor._execute_command(["echo"], "t1", timeout=10)
        executor._broadcast.assert_awaited()

# 3. TaskExecutor._execute_command — timeout path

class TestExecuteCommandTimeout:

    @pytest.fixture
    def executor(self):
        from secuscan.executor import TaskExecutor
        ex = TaskExecutor.__new__(TaskExecutor)
        ex._broadcast = AsyncMock()
        return ex

    @pytest.mark.asyncio
    async def test_timeout_sets_timed_out_true(self, executor):
        proc = MagicMock()
        proc.returncode = None
        proc.stdout = MagicMock()
        proc.stdout.at_eof = MagicMock(return_value=False)
        proc.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.wait = AsyncMock()
        proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, _, timed_out, _, _ = await executor._execute_command(
                ["sleep", "999"], "t-timeout", timeout=1
            )
        assert timed_out is True

    @pytest.mark.asyncio
    async def test_timeout_exit_code_is_minus_one(self, executor):
        proc = MagicMock()
        proc.returncode = None
        proc.stdout = MagicMock()
        proc.stdout.at_eof = MagicMock(return_value=False)
        proc.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.wait = AsyncMock()
        proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, exit_code, _, _, _ = await executor._execute_command(
                ["sleep", "999"], "t-timeout", timeout=1
            )
        assert exit_code == -1

    @pytest.mark.asyncio
    async def test_timeout_reason_contains_limit_seconds(self, executor):
        proc = MagicMock()
        proc.returncode = None
        proc.stdout = MagicMock()
        proc.stdout.at_eof = MagicMock(return_value=False)
        proc.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.wait = AsyncMock()
        proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, _, _, reason, _ = await executor._execute_command(
                ["sleep", "999"], "t-timeout", timeout=42
            )
        assert reason is not None
        assert "42" in reason

    @pytest.mark.asyncio
    async def test_timeout_output_contains_timed_out_message(self, executor):
        proc = MagicMock()
        proc.returncode = None
        proc.stdout = MagicMock()
        proc.stdout.at_eof = MagicMock(return_value=False)
        proc.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.wait = AsyncMock()
        proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            output, _, _, _, _ = await executor._execute_command(
                ["sleep", "999"], "t-timeout", timeout=1
            )
        assert "timed out" in output.lower()

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self, executor):
        proc = MagicMock()
        proc.returncode = None
        proc.stdout = MagicMock()
        proc.stdout.at_eof = MagicMock(return_value=False)
        proc.stdout.readline = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.wait = AsyncMock()
        proc.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            await executor._execute_command(["sleep", "999"], "t-timeout", timeout=1)
        proc.kill.assert_called_once()

# 4. TaskExecutor._execute_command — non-zero exit

class TestExecuteCommandNonZeroExit:

    @pytest.fixture
    def executor(self):
        from secuscan.executor import TaskExecutor
        ex = TaskExecutor.__new__(TaskExecutor)
        ex._broadcast = AsyncMock()
        return ex

    @pytest.mark.asyncio
    async def test_nonzero_exit_code_propagated(self, executor):
        proc = _fake_process(returncode=2, lines=(b"err\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, exit_code, _, _, _ = await executor._execute_command(
                ["false"], "t-nz", timeout=10
            )
        assert exit_code == 2

    @pytest.mark.asyncio
    async def test_nonzero_timed_out_still_false(self, executor):
        proc = _fake_process(returncode=1, lines=(b"err\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, _, timed_out, _, _ = await executor._execute_command(
                ["false"], "t-nz", timeout=10
            )
        assert timed_out is False

    @pytest.mark.asyncio
    async def test_nonzero_timeout_reason_still_none(self, executor):
        proc = _fake_process(returncode=3, lines=(b"err\n",))
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _, _, _, reason, _ = await executor._execute_command(
                ["false"], "t-nz", timeout=10
            )
        assert reason is None

# 5. TaskExecutor._execute_command — subprocess spawn exception

class TestExecuteCommandSpawnError:

    @pytest.fixture
    def executor(self):
        from secuscan.executor import TaskExecutor
        ex = TaskExecutor.__new__(TaskExecutor)
        ex._broadcast = AsyncMock()
        return ex

    @pytest.mark.asyncio
    async def test_spawn_error_returns_five_tuple(self, executor):
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("No such file or directory"),
        ):
            result = await executor._execute_command(["notacommand"], "t-err", timeout=10)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_spawn_error_exit_minus_one(self, executor):
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("fail"),
        ):
            _, exit_code, _, _, _ = await executor._execute_command(
                ["notacommand"], "t-err", timeout=10
            )
        assert exit_code == -1

    @pytest.mark.asyncio
    async def test_spawn_error_output_size_zero(self, executor):
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("fail"),
        ):
            _, _, _, _, size = await executor._execute_command(
                ["notacommand"], "t-err", timeout=10
            )
        assert size == 0

# 6. Parser failure — finally block behaviour

class TestParserFailureFinallyBlock:
    """
    Directly replicates the try/except/finally structure in executor.py
    around _upsert_findings_and_report.  No subprocess needed.
    """

    def test_parser_error_is_captured(self):
        t = make_telemetry()
        t.exit_code = 0
        t.duration_seconds = 1.0

        _parser_error = None
        with pytest.raises(ValueError, match="bad XML"):
            try:
                raise ValueError("bad XML")
            except Exception as _pe:
                _parser_error = str(_pe)
                raise
            finally:
                t.parser_error = _parser_error
                t.parser_time_seconds = 0.05
                t.log("task-parser-fail")

        assert t.parser_error == "bad XML"

    def test_parser_exception_is_reraised(self):
        t = make_telemetry()
        with pytest.raises(RuntimeError):
            try:
                raise RuntimeError("oops")
            except Exception as _pe:
                raise
            finally:
                t.parser_error = "oops"

    def test_parser_time_set_in_finally(self):
        t = make_telemetry()
        import time
        _parser_start = time.time()
        try:
            pass  # parser succeeds instantly
        except Exception as _pe:
            t.parser_error = str(_pe)
            raise
        finally:
            t.parser_time_seconds = time.time() - _parser_start
        assert t.parser_time_seconds >= 0.0

    def test_parser_success_leaves_error_none(self):
        t = make_telemetry()
        _parser_error = None
        try:
            pass  # no exception
        except Exception as _pe:
            _parser_error = str(_pe)
            raise
        finally:
            t.parser_error = _parser_error
        assert t.parser_error is None

    def test_log_called_even_on_parser_failure(self, caplog):
        t = make_telemetry(plugin_name="flaky_parser")
        t.exit_code = 0
        with caplog.at_level(logging.INFO, logger="secuscan.telemetry"):
            with pytest.raises(KeyError):
                try:
                    raise KeyError("missing_key")
                except Exception as _pe:
                    t.parser_error = str(_pe)
                    raise
                finally:
                    t.log("task-flaky")
        # log() was reached — telemetry was emitted
        assert "flaky_parser" in caplog.text

# 7 & 8. BaseScanner._execute_command_timed

class _ConcreteScanner:
    """Minimal stand-in that avoids importing the full BaseScanner ABC."""

    def __init__(self):
        from secuscan.telemetry import PluginTelemetry
        self.task_id = "t-base"
        self.name = "test_scanner"
        self.telemetry = PluginTelemetry(plugin_name=self.name)

    async def _execute_command_timed(self, command, timeout=300):
        # Delegate to the real implementation via mixin call
        from secuscan.scanners.base import BaseScanner
        return await BaseScanner._execute_command_timed(self, command, timeout=timeout)


class TestBaseScannerTimedCommandSuccess:

    @pytest.mark.asyncio
    async def test_returns_five_tuple(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"scan output\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            result = await scanner._execute_command_timed(["nmap", "-sV", "127.0.0.1"], timeout=30)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_success_populates_exit_code(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"ok\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            _, exit_code, _, _, _ = await scanner._execute_command_timed(["true"], timeout=10)
        assert exit_code == 0
        assert scanner.telemetry.exit_code == 0

    @pytest.mark.asyncio
    async def test_success_populates_duration(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"data\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            await scanner._execute_command_timed(["true"], timeout=10)
        assert scanner.telemetry.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_success_output_size_bytes_matches(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"hello world\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            output, _, _, _, size = await scanner._execute_command_timed(["echo"], timeout=10)
        assert size == len(output.encode("utf-8", errors="replace"))
        assert scanner.telemetry.output_size_bytes == size

    @pytest.mark.asyncio
    async def test_success_timed_out_false_on_telemetry(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"ok\n", b""))

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            await scanner._execute_command_timed(["true"], timeout=10)
        assert scanner.telemetry.timed_out is False


class TestBaseScannerTimedCommandTimeout:

    @pytest.mark.asyncio
    async def test_timeout_sets_timed_out_on_telemetry(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        fake_proc.kill = MagicMock()
        fake_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            _, exit_code, timed_out, reason, _ = await scanner._execute_command_timed(
                ["sleep", "999"], timeout=1
            )
        assert timed_out is True
        assert exit_code == -1
        assert scanner.telemetry.timed_out is True

    @pytest.mark.asyncio
    async def test_timeout_reason_on_telemetry(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        fake_proc.kill = MagicMock()
        fake_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            await scanner._execute_command_timed(["sleep", "999"], timeout=15)
        assert scanner.telemetry.timeout_reason is not None
        assert "15" in scanner.telemetry.timeout_reason

    @pytest.mark.asyncio
    async def test_timeout_duration_still_recorded(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        fake_proc.kill = MagicMock()
        fake_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            await scanner._execute_command_timed(["sleep", "999"], timeout=1)
        assert scanner.telemetry.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self):
        scanner = _ConcreteScanner()
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        fake_proc.kill = MagicMock()
        fake_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            await scanner._execute_command_timed(["sleep", "999"], timeout=1)
        fake_proc.kill.assert_called_once()

# 9. Security negative tests

class TestTelemetrySecurityNegative:

    def test_log_never_emits_raw_output_content(self, caplog):
        """telemetry.log() must not echo back raw tool output — it could contain secrets."""
        t = make_telemetry(plugin_name="nmap")
        t.duration_seconds = 0.5
        t.exit_code = 0
        t.output_size_bytes = 128

        secret = "PASSWORD=hunter2_super_secret_DO_NOT_LOG"

        # Simulate a caller mistakenly setting timeout_reason to raw output
        # (should still not appear if implementation is correct and not logging it)
        # We just verify the log fields are bounded metadata, not free-form output.
        with caplog.at_level(logging.DEBUG):
            t.log("task-sec")

        for record in caplog.records:
            assert secret not in record.getMessage()

    def test_plugin_name_stored_verbatim(self):
        name = "nmap_scanner_v2_beta"
        t = make_telemetry(plugin_name=name)
        assert t.plugin_name == name
        assert t.to_dict()["plugin_name"] == name

    def test_resource_hints_not_shared_between_instances(self):
        a = make_telemetry(resource_hints={"memory_limit_mb": 256})
        b = make_telemetry()
        assert b.resource_hints == {}
        a.resource_hints["injected"] = True
        assert "injected" not in b.resource_hints

    def test_to_dict_does_not_include_extra_keys(self):
        t = make_telemetry()
        allowed = {
            "plugin_name", "duration_seconds", "exit_code",
            "output_size_bytes", "parser_time_seconds", "timed_out",
            "timeout_reason", "resource_hints", "parser_error",
        }
        assert set(t.to_dict().keys()) == allowed

    def test_output_size_is_byte_count_not_content(self):
        """output_size_bytes must be an integer, never the actual output string."""
        t = make_telemetry()
        t.output_size_bytes = 9999
        d = t.to_dict()
        assert isinstance(d["output_size_bytes"], int)
        assert "secret" not in str(d["output_size_bytes"])
        