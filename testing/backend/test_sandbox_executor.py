import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.secuscan.models import SandboxConfig
from backend.secuscan.sandbox_executor import (
    sandbox_execute,
    _terminate_process,
    _build_preexec_fn,
    classify_memory_violation,
)


@pytest.mark.asyncio
async def test_legacy_timeout_compatibility():
    """Test Case 1: Legacy Timeout Compatibility.

    _execute_command(cmd, timeout=1) must apply the timeout and return
    violation_reason "timeout".
    """
    from backend.secuscan.executor import TaskExecutor

    exec_ = TaskExecutor()
    output, exit_code, violation_reason = await exec_._execute_command(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        "test-legacy-timeout",
        timeout=1,
    )
    assert violation_reason == "timeout"
    assert exit_code != 0


@pytest.mark.asyncio
async def test_signal_escalation():
    """Test Case 2: Signal Escalation.

    When a process ignores SIGTERM, verify that terminate() is called first,
    then kill() after the grace period, and process.wait() is called twice (reap).
    """
    mock_process = MagicMock()
    mock_process.returncode = None
    mock_process.terminate = MagicMock()
    mock_process.kill = MagicMock()

    wait_count = 0

    async def wait_side_effect():
        nonlocal wait_count
        wait_count += 1
        if wait_count == 1:
            await asyncio.sleep(999)

    mock_process.wait = wait_side_effect

    with patch("backend.secuscan.sandbox_executor.SIGTERM_GRACE", 0.05):
        await _terminate_process(mock_process)

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()
    assert wait_count == 2


class TestMemoryLimitClassification:
    """Test Case 3: Memory Limit Classification."""

    @pytest.mark.parametrize("exit_code", [-11, 139])
    def test_sigsegv(self, exit_code):
        assert classify_memory_violation(
            exit_code=exit_code,
            stderr_text="",
            rss_bytes=0,
            limit_bytes=512 * 1024 * 1024,
        ) is True

    def test_memory_error_string(self):
        assert classify_memory_violation(
            exit_code=1,
            stderr_text="MemoryError: unable to allocate",
            rss_bytes=0,
            limit_bytes=512 * 1024 * 1024,
        ) is True

    def test_cannot_allocate_memory(self):
        assert classify_memory_violation(
            exit_code=1,
            stderr_text="Cannot allocate memory",
            rss_bytes=0,
            limit_bytes=512 * 1024 * 1024,
        ) is True

    def test_rss_heuristic(self):
        limit_bytes = 512 * 1024 * 1024
        assert classify_memory_violation(
            exit_code=137,
            stderr_text="",
            rss_bytes=limit_bytes,
            limit_bytes=limit_bytes,
        ) is True

    def test_rss_below_threshold(self):
        limit_bytes = 512 * 1024 * 1024
        assert classify_memory_violation(
            exit_code=1,
            stderr_text="",
            rss_bytes=int(limit_bytes * 0.50),
            limit_bytes=limit_bytes,
        ) is False

    def test_zero_exit_not_classified(self):
        limit_bytes = 512 * 1024 * 1024
        assert classify_memory_violation(
            exit_code=0,
            stderr_text="",
            rss_bytes=int(limit_bytes * 0.99),
            limit_bytes=limit_bytes,
        ) is False


@pytest.mark.asyncio
async def test_proactive_output_truncation():
    """Test Case 4: Proactive Output Truncation.

    When subprocess output exceeds max_output_bytes, reading must stop
    at the boundary, the process terminated, and violation_reason returned.
    """
    cfg = SandboxConfig(max_output_bytes=1024, timeout_seconds=30)
    stdout, stderr, exit_code, violation_reason = await sandbox_execute(
        [sys.executable, "-c", "print('A' * 10000000)"],
        cfg,
    )
    assert violation_reason == "output_limit"
    assert len(stdout) <= 2048
    assert exit_code != 0


@pytest.mark.asyncio
async def test_task_cancellation_safety():
    """Test Case 5: Task Cancellation Safety.

    If the parent coroutine is cancelled, the subprocess must be
    terminated and reaped, never orphaned.
    """
    cfg = SandboxConfig(timeout_seconds=30)
    task = asyncio.create_task(
        sandbox_execute(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            cfg,
        )
    )
    await asyncio.sleep(0.2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_platform_guard_non_linux():
    """Test Case 6: Platform Guard Verification.

    On Linux, preexec_fn applies RLIMIT_AS. On other platforms,
    it must be None (checked at call site in sandbox_execute).
    Timeout and output limits must remain active on all platforms.
    """
    built = _build_preexec_fn(SandboxConfig(max_memory_mb=128))
    assert callable(built)

    cfg = SandboxConfig(max_output_bytes=100, timeout_seconds=30)
    stdout, stderr, exit_code, violation_reason = await sandbox_execute(
        [sys.executable, "-c", "print('x' * 5000)"],
        cfg,
    )
    assert violation_reason == "output_limit"
    assert len(stdout) < 500

    cfg2 = SandboxConfig(timeout_seconds=1)
    stdout2, stderr2, exit_code2, vr2 = await sandbox_execute(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cfg2,
    )
    assert vr2 == "timeout"


@pytest.mark.asyncio
async def test_sandbox_execute_normal_completion():
    cfg = SandboxConfig(timeout_seconds=30)
    stdout, stderr, exit_code, violation_reason = await sandbox_execute(
        [sys.executable, "-c", "print('hello world')"],
        cfg,
    )
    assert "hello world" in stdout
    assert exit_code == 0
    assert violation_reason is None


def test_sandbox_violation_exception():
    from backend.secuscan.models import SandboxViolation
    exc = SandboxViolation("timeout")
    assert exc.reason == "timeout"
    assert str(exc) == "timeout"


@pytest.mark.asyncio
async def test_resolve_sandbox_config_global_defaults(monkeypatch):
    from backend.secuscan.sandbox_executor import resolve_sandbox_config
    monkeypatch.setattr(
        "backend.secuscan.config.settings.sandbox_timeout",
        42,
    )
    monkeypatch.setattr(
        "backend.secuscan.config.settings.sandbox_memory_mb",
        256,
    )
    resolved = resolve_sandbox_config(None)
    assert resolved.timeout_seconds == 42
    assert resolved.max_memory_mb == 256
    assert resolved.max_output_bytes == 5_242_880


@pytest.mark.asyncio
async def test_resolve_sandbox_config_plugin_overrides():
    from backend.secuscan.sandbox_executor import resolve_sandbox_config
    resolved = resolve_sandbox_config(
        SandboxConfig(timeout_seconds=999, max_memory_mb=2048)
    )
    assert resolved.timeout_seconds == 999
    assert resolved.max_memory_mb == 2048
    assert resolved.max_output_bytes == 5_242_880
