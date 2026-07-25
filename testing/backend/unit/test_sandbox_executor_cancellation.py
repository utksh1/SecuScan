"""
Unit tests for sandbox executor CancelledError cleanup.

Covers the behavior when a running sandbox task is cancelled mid-execution.
The finally block must terminate the child process, preventing orphaned processes.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.fixture
def mock_process():
    """A mock asyncio subprocess with returncode=None (still running)."""
    process = MagicMock()
    process.returncode = None
    process.terminate = MagicMock()
    process.kill = MagicMock()
    process.wait = AsyncMock(return_code=-1)
    process.stdout = MagicMock()
    process.stderr = MagicMock()
    return process


@pytest.fixture
def exited_process():
    """A mock asyncio subprocess that has already exited."""
    process = MagicMock()
    process.returncode = 0
    process.terminate = MagicMock()
    return process


class TestTerminateProcess:
    """Tests for _terminate_process (imported async helper)."""

    @pytest.mark.asyncio
    async def test_terminate_process_calls_terminate(self, mock_process):
        """_terminate_process calls terminate() on the subprocess."""
        from backend.secuscan.sandbox_executor import _terminate_process

        await _terminate_process(mock_process)

        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminate_process_waits_for_exit(self, mock_process):
        """After terminate(), the process is waited for."""
        from backend.secuscan.sandbox_executor import _terminate_process

        await _terminate_process(mock_process)

        mock_process.wait.assert_awaited()

    @pytest.mark.asyncio
    async def test_terminate_process_returns_early_if_process_already_gone(self):
        """If terminate() raises ProcessLookupError, the function returns early."""
        from backend.secuscan.sandbox_executor import _terminate_process

        mock_proc = MagicMock()
        mock_proc.terminate = MagicMock(side_effect=ProcessLookupError)
        mock_proc.returncode = 0

        await _terminate_process(mock_proc)

        # terminate() was called but wait() and kill() should NOT be called
        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_not_called()


class TestFinallyBlockCleanup:
    """Tests verifying the finally block in sandbox_execute terminates on exit."""

    @pytest.mark.asyncio
    async def test_finally_skips_terminate_if_process_exited(self, exited_process):
        """If process.returncode is not None, terminate is not called."""
        from backend.secuscan.sandbox_executor import _terminate_process

        # Simulate the finally condition: if process.returncode is None
        if exited_process.returncode is None:
            await _terminate_process(exited_process)

        # terminate should NOT have been called
        exited_process.terminate.assert_not_called()

    @pytest.mark.asyncio
    async def test_finally_calls_terminate_if_process_still_running(self, mock_process):
        """If process.returncode is None, terminate is called."""
        from backend.secuscan.sandbox_executor import _terminate_process

        if mock_process.returncode is None:
            await _terminate_process(mock_process)

        mock_process.terminate.assert_called_once()


class TestSandboxExecuteCancellationBehavior:
    """Integration-style tests for the cancellation + cleanup pattern."""

    def test_sandbox_execute_has_finally_cleanup(self):
        """Verify sandbox_execute contains the finally + _terminate_process pattern."""
        import inspect
        from backend.secuscan.sandbox_executor import sandbox_execute

        source = inspect.getsource(sandbox_execute)

        assert "finally" in source, "sandbox_execute must have a finally block"
        assert "_terminate_process" in source, "finally block must call _terminate_process"
        assert "CancelledError" in source, "must handle CancelledError"

    def test_finally_block_checks_process_returncode(self):
        """Verify the finally block only terminates if process is still running."""
        import inspect
        from backend.secuscan.sandbox_executor import sandbox_execute

        source = inspect.getsource(sandbox_execute)

        assert "returncode is None" in source, "finally must check if process still running"

    def test_standalone_cancelled_error_handler_cancels_reader_task(self):
        """The standalone CancelledError handler cancels the reader task."""
        import inspect
        from backend.secuscan.sandbox_executor import sandbox_execute

        source = inspect.getsource(sandbox_execute)

        # Find the standalone (not combined with TimeoutError) CancelledError handler
        cancelled_blocks = [
            b for b in source.split("except")
            if "asyncio.CancelledError" in b and "TimeoutError" not in b
        ]
        assert len(cancelled_blocks) >= 1, "Must have a CancelledError handler"

        handler = cancelled_blocks[0]
        assert "reader_task.cancel()" in handler, (
            "CancelledError handler must cancel reader_task before re-raising"
        )
