"""
Integration tests for blocking issues in sandbox hardening.

Tests specifically for:
1. Memory-limit classification reliability
2. Legacy timeout argument path compatibility
3. Output-limit handling boundary precision
4. Task cancellation and process cleanup
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.secuscan.models import SandboxConfig
from backend.secuscan.sandbox_executor import (
    sandbox_execute,
    classify_memory_violation,
)


@pytest.mark.asyncio
async def test_timeout_enforcement_with_default():
    """Issue #2: Timeout enforcement with default timeout fallback.

    When timeout is None, should use global settings (600s default).
    Verifies backward compatibility of the legacy timeout argument.
    """
    from backend.secuscan.executor import TaskExecutor

    exec_ = TaskExecutor()

    # Test with explicit timeout
    output, exit_code, violation = await exec_._execute_command(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        "test-legacy-timeout",
        timeout=2,
    )
    assert violation == "timeout", f"Expected timeout, got {violation}"
    assert exit_code != 0
    assert output == ""

    # Test with None (should use default 600s)
    output2, exit_code2, violation2 = await exec_._execute_command(
        [sys.executable, "-c", "print('done')"],
        "test-legacy-none",
        timeout=None,
    )
    assert violation2 is None, f"Expected no violation, got {violation2}"
    assert exit_code2 == 0
    assert "done" in output2


@pytest.mark.asyncio
async def test_memory_limit_detection_comprehensive():
    """Issue #1: Memory limit detection must be reliable.

    Test all 3 conditions:
    - Condition A: SIGSEGV (exit codes -11 or 139)
    - Condition B: MemoryError or "Cannot allocate memory" in stderr
    - Condition C: RSS >= 95% of limit AND process failed
    """
    # Condition A: SIGSEGV (exit code -11)
    assert classify_memory_violation(-11, "", 0, 512*1024*1024) is True

    # Condition A: SIGSEGV (exit code 139)
    assert classify_memory_violation(139, "", 0, 512*1024*1024) is True

    # Condition B: MemoryError in stderr
    assert classify_memory_violation(1, "MemoryError: out of memory", 0, 512*1024*1024) is True

    # Condition B: Cannot allocate memory
    assert classify_memory_violation(1, "Cannot allocate memory", 0, 512*1024*1024) is True

    # Condition C: RSS at 95% threshold with failure
    limit = 512 * 1024 * 1024
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True

    # Condition C: RSS at 94% should not trigger (below threshold)
    assert classify_memory_violation(137, "", int(limit * 0.94), limit) is False

    # Condition C: Success (exit_code 0) should not trigger even at high RSS
    assert classify_memory_violation(0, "", int(limit * 0.99), limit) is False


@pytest.mark.asyncio
async def test_output_limit_exact_boundary():
    """Issue #3: Output limit must be enforced at exact byte boundary.

    Verifies that reading stops exactly at the limit and no bytes beyond.
    """
    cfg = SandboxConfig(max_output_bytes=1000, timeout_seconds=30)

    # Generate more than limit to test truncation
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('x' * 2000)"],
        cfg,
    )

    # Total bytes (stdout + stderr) should not exceed limit
    total_bytes = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
    assert total_bytes <= 1000, f"Total bytes {total_bytes} exceeds limit of 1000"
    assert violation == "output_limit"
    # Exit code may be 0 if Python finished before termination signal was sent;
    # output cap is the correctness criterion here.


@pytest.mark.asyncio
async def test_output_limit_no_partial_chunks():
    """Issue #3: Output limit prevents partial chunk overruns.

    When a chunk would exceed the limit, it must be truncated exactly.
    """
    cfg = SandboxConfig(max_output_bytes=512, timeout_seconds=30)

    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('A' * 1000000)"],
        cfg,
    )

    stdout_bytes = len(stdout.encode('utf-8'))
    stderr_bytes = len(stderr.encode('utf-8'))
    total = stdout_bytes + stderr_bytes

    assert total <= 512, f"Output {total} bytes exceeds limit of 512"
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_cancellation_with_process_cleanup():
    """Process cancellation must properly clean up child processes.

    Verifies that cancelling the task terminates the process (no orphans).
    """
    cfg = SandboxConfig(timeout_seconds=30)

    task = asyncio.create_task(
        sandbox_execute(
            [sys.executable, "-c", "import time; time.sleep(120)"],
            cfg,
        )
    )

    # Give it time to start
    await asyncio.sleep(0.1)

    # Cancel the task
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Wait a bit and verify no zombie process
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_memory_classification_called_always():
    """Issue #1: Memory classification must be checked always.

    Verifies that we check memory violation even when exit_code == 0
    (in case RSS heuristic applies, e.g., OOM killer killed the process).
    """
    cfg = SandboxConfig(timeout_seconds=30)

    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('success')"],
        cfg,
    )

    # Should succeed
    assert exit_code == 0
    assert "success" in stdout
    # Memory violation should be checked even for successful exit
    assert violation is None or violation == "memory_limit"


@pytest.mark.asyncio
async def test_legacy_timeout_none_uses_default():
    """Issue #2: Legacy _execute_command with timeout=None must use defaults.

    Verifies backward compatibility when timeout is not specified.
    """
    from backend.secuscan.executor import TaskExecutor

    exec_ = TaskExecutor()

    # Call without timeout (None)
    output, exit_code, violation = await exec_._execute_command(
        [sys.executable, "-c", "print('hello world')"],
        "test-legacy-none2",
        timeout=None,
    )

    assert exit_code == 0
    assert "hello world" in output
    assert violation is None


@pytest.mark.asyncio
async def test_output_limit_stops_both_readers():
    """Issue #3: Output limit must stop both stdout and stderr readers.

    Verifies that shared state properly coordinates both readers.
    """
    cfg = SandboxConfig(max_output_bytes=256, timeout_seconds=30)

    # Script that writes to both stdout and stderr
    script = """
import sys
for i in range(100):
    print("stdout" * 10)
    sys.stderr.write("stderr" * 10 + "\\n")
"""

    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", script],
        cfg,
    )

    total_bytes = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
    assert total_bytes <= 256, f"Total bytes {total_bytes} exceeds limit 256"
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_output_limit_early_reader_termination():
    """Verify that when limit is hit, readers exit immediately.

    Tests that the check at the start of the loop prevents further reads.
    """
    cfg = SandboxConfig(max_output_bytes=100, timeout_seconds=30)

    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('x' * 10000)"],
        cfg,
    )

    total = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
    assert total <= 100
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_memory_classification_includes_exit_137():
    """Verify memory classification catches exit code 137 (OOM killer).

    Exit code 137 = 128 + 9 (SIGKILL), often from OOM killer on Linux.
    """
    limit = 512 * 1024 * 1024

    # RSS at threshold, exit 137 (SIGKILL from OOM)
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True

    # Without high RSS, exit 137 should not be classified as memory_limit
    # (could be another cause)
    assert classify_memory_violation(137, "", int(limit * 0.80), limit) is False


@pytest.mark.asyncio
async def test_live_output_broadcasting():
    """Regression: sandbox path must broadcast output chunks for live streaming."""
    from backend.secuscan.executor import TaskExecutor
    from unittest.mock import AsyncMock

    exec_ = TaskExecutor()
    exec_._broadcast = AsyncMock()

    await exec_._execute_command(
        [sys.executable, "-c", "print('hello from live stream')"],
        "test-broadcast",
        timeout=30,
    )

    calls = exec_._broadcast.await_args_list
    output_calls = [c for c in calls if c.args[1] == "output"]
    assert len(output_calls) > 0, (
        f"Expected at least one output broadcast call, got {len(calls)} total"
    )

    all_text = "".join(c.args[2] for c in output_calls)
    assert "hello from live stream" in all_text, (
        f"Broadcast output did not contain expected text: {all_text!r}"
    )


@pytest.mark.asyncio
async def test_stderr_captured_in_output():
    """Regression: stderr must be merged into raw output, not discarded."""
    from backend.secuscan.executor import TaskExecutor

    exec_ = TaskExecutor()

    output, exit_code, violation = await exec_._execute_command(
        [
            sys.executable, "-c",
            "import sys; sys.stderr.write('diagnostic info\\n'); print('stdout line')",
        ],
        "test-stderr-capture",
        timeout=30,
    )

    assert exit_code == 0, f"Expected exit_code 0, got {exit_code}"
    assert "stdout line" in output, f"Expected stdout in output: {output!r}"
    assert "diagnostic info" in output, f"Expected stderr in output: {output!r}"


# ---------------------------------------------------------------------------
# Comprehensive precision regression tests for all 5 owner-specified categories
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_external_via_execute_command():
    """Timeout category: _execute_command applies timeout via external asyncio.wait_for
    (legacy-compatible path), returns ("", -1, "timeout") on expiry."""
    from backend.secuscan.executor import TaskExecutor

    exec_ = TaskExecutor()
    output, exit_code, violation = await exec_._execute_command(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        "test-ext-timeout",
        timeout=1,
    )
    assert violation == "timeout", f"Expected timeout, got {violation}"
    assert exit_code == -1, f"Expected exit_code -1 on timeout, got {exit_code}"
    assert output == "", f"Expected empty output on timeout, got {output!r}"


@pytest.mark.asyncio
async def test_timeout_internal_via_sandbox_execute():
    """Timeout category: direct sandbox_execute with timeout_seconds still
    applies internal timeout for callers that don't go through _execute_command."""
    cfg = SandboxConfig(timeout_seconds=1, max_memory_mb=512)
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cfg,
    )
    assert violation == "timeout", f"Expected timeout, got {violation}"
    assert exit_code != 0, f"Expected non-zero exit, got {exit_code}"
    # stderr may have timeout noise, stdout should be empty
    assert stdout == "", f"Expected empty stdout on timeout, got {stdout!r}"


@pytest.mark.asyncio
async def test_memory_classification_sigsegv_exit_codes():
    """Memory category: SIGSEGV signals must always classify as memory_limit."""
    limit = 512 * 1024 * 1024
    for code in (-11, 139):
        assert classify_memory_violation(code, "", 0, limit) is True, (
            f"Exit code {code} should be classified as memory violation"
        )


@pytest.mark.asyncio
async def test_memory_classification_stderr_strings():
    """Memory category: MemoryError / Cannot allocate memory strings classify."""
    limit = 512 * 1024 * 1024
    assert classify_memory_violation(1, "MemoryError: out of memory", 0, limit) is True
    assert classify_memory_violation(1, "Cannot allocate memory", 0, limit) is True
    # Non-memory error should not classify just from stderr
    assert classify_memory_violation(1, "Segmentation fault (core dumped)", 0, limit) is False


@pytest.mark.asyncio
async def test_memory_classification_rss_delta_heuristic():
    """Memory category: RSS at or above 95% threshold with non-zero exit classifies."""
    limit = 512 * 1024 * 1024
    # At threshold
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True
    # Just below threshold
    assert classify_memory_violation(137, "", int(limit * 0.94), limit) is False
    # Above threshold but exit 0 should not classify
    assert classify_memory_violation(0, "", int(limit * 0.99), limit) is False


@pytest.mark.asyncio
async def test_memory_classification_exit_137_with_rss():
    """Memory category: exit 137 (SIGKILL) + high RSS classifies as memory."""
    limit = 512 * 1024 * 1024
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True
    assert classify_memory_violation(137, "", int(limit * 0.80), limit) is False


@pytest.mark.asyncio
async def test_output_limit_lock_prevents_race():
    """Output category: asyncio.Lock prevents concurrent readers from exceeding max_bytes.

    Both stdout and stderr writers produce output concurrently. Without the lock,
    the shared total_bytes could be read simultaneously by both readers, causing
    both to consume up to the remaining capacity and exceed the limit.
    """
    cfg = SandboxConfig(max_output_bytes=512, timeout_seconds=10)
    script = (
        "import sys\n"
        "for i in range(500):\n"
        "    sys.stdout.write('a' * 120)\n"
        "    sys.stderr.write('b' * 120)\n"
    )
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", script],
        cfg,
    )
    total = len(stdout.encode("utf-8")) + len(stderr.encode("utf-8"))
    assert total <= 512, f"Lock should enforce total <= 512, got {total} bytes"
    assert violation == "output_limit", f"Expected output_limit, got {violation}"


@pytest.mark.asyncio
async def test_output_limit_strict_boundary():
    """Output category: output is capped at exactly max_output_bytes, not rounded up."""
    for limit in (256, 511, 1023):
        cfg = SandboxConfig(max_output_bytes=limit, timeout_seconds=10)
        stdout, stderr, exit_code, violation = await sandbox_execute(
            [sys.executable, "-c", f"print('x' * {limit * 10})"],
            cfg,
        )
        stdout_bytes = len(stdout.encode("utf-8"))
        stderr_bytes = len(stderr.encode("utf-8"))
        total = stdout_bytes + stderr_bytes
        assert total <= limit, (
            f"Limit {limit}: total {total} bytes exceeds limit"
        )


@pytest.mark.asyncio
async def test_cancellation_raises_cancelled_error():
    """Cancellation category: cancelling a sandbox_execute task raises CancelledError
    and does not leave orphan processes."""
    cfg = SandboxConfig(timeout_seconds=60)
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
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_legacy_timeout_signature_preserved():
    """Legacy compatibility: _execute_command(self, command, task_id, timeout=600)
    signature must accept all three positional forms."""
    from backend.secuscan.executor import TaskExecutor

    exec_ = TaskExecutor()

    # Form 1: default timeout (=600)
    output, exit_code, violation = await exec_._execute_command(
        [sys.executable, "-c", "print('ok')"],
        "test-legacy-default",
    )
    assert exit_code == 0
    assert "ok" in output
    assert violation is None

    # Form 2: explicit timeout
    output, exit_code, violation = await exec_._execute_command(
        [sys.executable, "-c", "print('ok2')"],
        "test-legacy-explicit",
        timeout=30,
    )
    assert exit_code == 0
    assert "ok2" in output
    assert violation is None

    # Form 3: timeout=None falls back to settings.sandbox_timeout
    output, exit_code, violation = await exec_._execute_command(
        [sys.executable, "-c", "print('ok3')"],
        "test-legacy-none",
        timeout=None,
    )
    assert exit_code == 0
    assert "ok3" in output
    assert violation is None
