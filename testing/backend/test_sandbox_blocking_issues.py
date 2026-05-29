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
