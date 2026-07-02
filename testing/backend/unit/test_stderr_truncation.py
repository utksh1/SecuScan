import asyncio
import sys
import pytest
from unittest.mock import MagicMock

from backend.secuscan.executor import (
    RollingBuffer,
    HeadBuffer,
    UnboundedBuffer,
    TaskExecutor,
)
from backend.secuscan.models import StderrTruncationMode


# ── Buffer Unit Tests ─────────────────────────────────────────────────────────

def test_rolling_buffer_under_limit():
    buf = RollingBuffer(limit=10)
    buf.write(b"hello")
    assert buf.data == b"hello"
    assert buf.total_written == 5


def test_rolling_buffer_exact_limit():
    buf = RollingBuffer(limit=10)
    buf.write(b"abcdefghij")
    assert buf.data == b"abcdefghij"
    assert buf.total_written == 10


def test_rolling_buffer_over_limit():
    buf = RollingBuffer(limit=10)
    buf.write(b"abcdefghijkl")  # 12 bytes
    assert buf.data == b"cdefghijkl"
    assert buf.total_written == 12


def test_rolling_buffer_multiple_writes():
    buf = RollingBuffer(limit=5)
    buf.write(b"abc")
    buf.write(b"def")
    assert buf.data == b"bcdef"
    assert buf.total_written == 6


def test_head_buffer_under_limit():
    buf = HeadBuffer(limit=10)
    buf.write(b"hello")
    assert buf.data == b"hello"
    assert buf.total_written == 5
    assert not buf.truncated


def test_head_buffer_over_limit():
    buf = HeadBuffer(limit=10)
    buf.write(b"abcdefghijkl")  # 12 bytes
    assert buf.data == b"abcdefghij"
    assert buf.total_written == 12
    assert buf.truncated


def test_unbounded_buffer():
    buf = UnboundedBuffer()
    buf.write(b"hello" * 1000)
    assert buf.total_written == 5000
    assert len(buf.data) == 5000


# ── Executor Integration Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_command_with_tail_truncation():
    executor = TaskExecutor()
    # Python script printing 15 bytes to stderr
    script = "import sys; sys.stderr.write('1234567890abcde')"
    cmd = [sys.executable, "-c", script]

    # Limit to 10 bytes
    output, exit_code = await executor._execute_command(
        command=cmd,
        task_id="test-tail",
        timeout=10,
        stderr_truncation_mode="tail",
        max_stderr_bytes=10,
    )

    assert exit_code == 0
    assert "--- STDERR (truncated, showing last 10 bytes) ---" in output
    assert "67890abcde" in output
    assert "12345" not in output


@pytest.mark.asyncio
async def test_execute_command_with_head_truncation():
    executor = TaskExecutor()
    # Python script printing 15 bytes to stderr
    script = "import sys; sys.stderr.write('1234567890abcde')"
    cmd = [sys.executable, "-c", script]

    # Limit to 10 bytes
    output, exit_code = await executor._execute_command(
        command=cmd,
        task_id="test-head",
        timeout=10,
        stderr_truncation_mode="head",
        max_stderr_bytes=10,
    )

    assert exit_code == 0
    assert "--- STDERR (truncated, showing first 10 bytes) ---" in output
    assert "1234567890" in output
    assert "abcde" not in output


@pytest.mark.asyncio
async def test_execute_command_with_no_truncation():
    executor = TaskExecutor()
    script = "import sys; sys.stderr.write('1234567890abcde')"
    cmd = [sys.executable, "-c", script]

    output, exit_code = await executor._execute_command(
        command=cmd,
        task_id="test-none",
        timeout=10,
        stderr_truncation_mode="none",
    )

    assert exit_code == 0
    assert "--- STDERR ---" in output
    assert "1234567890abcde" in output
    assert "truncated" not in output
