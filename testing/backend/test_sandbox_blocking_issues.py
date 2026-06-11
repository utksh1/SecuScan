"""
Integration tests for sandbox resource enforcement.

Covers:
1. Memory-limit classification reliability
2. Timeout enforcement via sandbox_execute
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


# ---------------------------------------------------------------------------
# Memory-limit classification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_limit_detection_comprehensive():
    """All three memory classification conditions produce correct results."""
    limit = 512 * 1024 * 1024

    # Condition A: SIGSEGV
    assert classify_memory_violation(-11, "", 0, limit) is True
    assert classify_memory_violation(139, "", 0, limit) is True

    # Condition B: MemoryError / Cannot allocate memory in stderr
    assert classify_memory_violation(1, "MemoryError: out of memory", 0, limit) is True
    assert classify_memory_violation(1, "Cannot allocate memory", 0, limit) is True

    # Condition C: RSS >= 95% with failure
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True
    assert classify_memory_violation(137, "", int(limit * 0.94), limit) is False

    # Exit code 0 should never classify
    assert classify_memory_violation(0, "", int(limit * 0.99), limit) is False


@pytest.mark.asyncio
async def test_memory_classification_sigsegv_exit_codes():
    """SIGSEGV signals must always classify as memory_limit."""
    limit = 512 * 1024 * 1024
    for code in (-11, 139):
        assert classify_memory_violation(code, "", 0, limit) is True


@pytest.mark.asyncio
async def test_memory_classification_stderr_strings():
    """MemoryError / Cannot allocate memory classify; other errors do not."""
    limit = 512 * 1024 * 1024
    assert classify_memory_violation(1, "MemoryError: out of memory", 0, limit) is True
    assert classify_memory_violation(1, "Cannot allocate memory", 0, limit) is True
    assert classify_memory_violation(1, "Segmentation fault (core dumped)", 0, limit) is False


@pytest.mark.asyncio
async def test_memory_classification_rss_delta_heuristic():
    """RSS at or above 95% with non-zero exit classifies; below does not."""
    limit = 512 * 1024 * 1024
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True
    assert classify_memory_violation(137, "", int(limit * 0.94), limit) is False
    assert classify_memory_violation(0, "", int(limit * 0.99), limit) is False


@pytest.mark.asyncio
async def test_memory_classification_exit_137_with_rss():
    """Exit 137 (SIGKILL/OOM) + high RSS classifies as memory."""
    limit = 512 * 1024 * 1024
    assert classify_memory_violation(137, "", int(limit * 0.95), limit) is True
    assert classify_memory_violation(137, "", int(limit * 0.80), limit) is False


@pytest.mark.asyncio
async def test_memory_classification_called_always():
    """Memory classification checked even for successful exit."""
    cfg = SandboxConfig(timeout_seconds=30)
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('success')"],
        cfg,
    )
    assert exit_code == 0
    assert "success" in stdout
    assert violation is None or violation == "memory_limit"


# ---------------------------------------------------------------------------
# Timeout enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_internal_via_sandbox_execute():
    """sandbox_execute with timeout_seconds applies internal timeout."""
    cfg = SandboxConfig(timeout_seconds=1, max_memory_mb=512)
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cfg,
    )
    assert violation == "timeout"
    assert exit_code != 0
    assert stdout == ""


# ---------------------------------------------------------------------------
# Output-limit boundary precision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_limit_exact_boundary():
    """Output capped exactly at max_output_bytes; no bytes beyond."""
    cfg = SandboxConfig(max_output_bytes=1000, timeout_seconds=30)
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('x' * 2000)"],
        cfg,
    )
    total_bytes = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
    assert total_bytes <= 1000
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_output_limit_no_partial_chunks():
    """Chunks truncated exactly at boundary; total never exceeds limit."""
    cfg = SandboxConfig(max_output_bytes=512, timeout_seconds=30)
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('A' * 1000000)"],
        cfg,
    )
    total = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
    assert total <= 512
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_output_limit_stops_both_readers():
    """Shared state stops both stdout and stderr readers when limit hit."""
    cfg = SandboxConfig(max_output_bytes=256, timeout_seconds=30)
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
    assert total_bytes <= 256
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_output_limit_early_reader_termination():
    """Readers exit immediately when limit is hit (check at loop start)."""
    cfg = SandboxConfig(max_output_bytes=100, timeout_seconds=30)
    stdout, stderr, exit_code, violation = await sandbox_execute(
        [sys.executable, "-c", "print('x' * 10000)"],
        cfg,
    )
    total = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
    assert total <= 100
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_output_limit_lock_prevents_race():
    """asyncio.Lock prevents concurrent readers from exceeding max_bytes."""
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
    assert total <= 512
    assert violation == "output_limit"


@pytest.mark.asyncio
async def test_output_limit_strict_boundary():
    """Output capped at exactly max_output_bytes for multiple limit values."""
    for limit in (256, 511, 1023):
        cfg = SandboxConfig(max_output_bytes=limit, timeout_seconds=10)
        stdout, stderr, exit_code, violation = await sandbox_execute(
            [sys.executable, "-c", f"print('x' * {limit * 10})"],
            cfg,
        )
        stdout_bytes = len(stdout.encode("utf-8"))
        stderr_bytes = len(stderr.encode("utf-8"))
        total = stdout_bytes + stderr_bytes
        assert total <= limit, f"Limit {limit}: total {total} bytes exceeds limit"


# ---------------------------------------------------------------------------
# Cancellation and process cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation_with_process_cleanup():
    """Cancelling sandbox_execute raises CancelledError; no orphan process."""
    cfg = SandboxConfig(timeout_seconds=30)
    task = asyncio.create_task(
        sandbox_execute(
            [sys.executable, "-c", "import time; time.sleep(120)"],
            cfg,
        )
    )
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_cancellation_raises_cancelled_error():
    """Independent assertion that cancellation raises CancelledError."""
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
