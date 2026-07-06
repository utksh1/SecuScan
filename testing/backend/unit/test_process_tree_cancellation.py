"""
Tests for full process-tree cancellation (issue #216).

Covers:
  - _terminate_process_group sends SIGTERM then SIGKILL after grace period.
  - _terminate_process_group handles already-dead processes without error.
  - _terminate_process_group handles ProcessLookupError on getpgid gracefully.
  - _execute_command kills the full process group on asyncio.CancelledError.
  - _execute_command kills the full process group on timeout.
  - start_new_session=True is passed to create_subprocess_exec.
  - _process_pids is populated on subprocess start and cleared on finish.
  - cancel_task terminates the process group before cancelling the asyncio task.
  - Orphan child processes spawned by the root process are killed.
  - Double-cancel of a task that already finished is a no-op.
"""

import asyncio
import os
import signal
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

from backend.secuscan.executor import _terminate_process_group, _CANCEL_GRACE_SECONDS


class TestTerminateProcessGroup:
    @pytest.mark.asyncio
    async def test_already_dead_process_no_error(self):
        with patch("os.getpgid", side_effect=ProcessLookupError("no such process")):
            await _terminate_process_group(99999, "task-dead")

    @pytest.mark.asyncio
    async def test_permission_error_on_getpgid_no_error(self):
        with patch("os.getpgid", side_effect=PermissionError("permission denied")):
            await _terminate_process_group(99999, "task-perm")

    @pytest.mark.asyncio
    async def test_sigterm_sent_to_process_group(self):
        with (
            patch("os.getpgid", return_value=5000),
            patch("os.killpg") as mock_killpg,
        ):
            mock_killpg.side_effect = [None, ProcessLookupError()]
            await _terminate_process_group(1234, "task-sigterm")
            mock_killpg.assert_any_call(5000, signal.SIGTERM)

    @pytest.mark.asyncio
    async def test_process_exits_before_sigkill(self):
        killpg_calls = []
        def fake_killpg(pgid, sig):
            killpg_calls.append(sig)
            if sig == signal.SIGTERM:
                return
            raise ProcessLookupError()

        call_count = [0]
        def fake_killpg_probe(pgid, sig):
            if sig == 0:
                call_count[0] += 1
                if call_count[0] >= 2:
                    raise ProcessLookupError()
            else:
                killpg_calls.append(sig)

        with (
            patch("os.getpgid", return_value=5001),
            patch("os.killpg", side_effect=fake_killpg_probe),
        ):
            await _terminate_process_group(1235, "task-exits-early")
        assert signal.SIGKILL not in killpg_calls

    @pytest.mark.asyncio
    async def test_sigterm_permission_error_no_sigkill(self):
        with (
            patch("os.getpgid", return_value=5002),
            patch("os.killpg", side_effect=PermissionError()) as mock_killpg,
        ):
            await _terminate_process_group(1236, "task-perm-kill")
        mock_killpg.assert_called_once_with(5002, signal.SIGTERM)

    @pytest.mark.asyncio
    async def test_sigkill_sent_when_process_does_not_exit(self):
        probe_count = [0]
        def fake_killpg(pgid, sig):
            if sig == 0:
                probe_count[0] += 1
            elif sig == signal.SIGKILL:
                raise ProcessLookupError()

        with (
            patch("os.getpgid", return_value=5003),
            patch("os.killpg", side_effect=fake_killpg) as mock_killpg,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await _terminate_process_group(1237, "task-stubborn", grace_seconds=1)
        sigs = [c.args[1] for c in mock_killpg.call_args_list]
        assert signal.SIGTERM in sigs
        assert signal.SIGKILL in sigs


class TestExecuteCommandProcessGroup:
    @pytest.mark.asyncio
    async def test_start_new_session_passed_to_subprocess(self):
        mock_proc = AsyncMock()
        mock_proc.pid = 1000
        mock_proc.returncode = 0
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.at_eof.return_value = True
        mock_proc.wait = AsyncMock(return_value=0)

        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_create:
            await executor._execute_command(["echo", "hello"], "task-sess")
            _, kwargs = mock_create.call_args
            assert kwargs.get("start_new_session") is True

    @pytest.mark.asyncio
    async def test_process_pid_stored_in_registry(self):
        mock_proc = AsyncMock()
        mock_proc.pid = 2001
        mock_proc.returncode = 0
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.at_eof.return_value = True
        mock_proc.wait = AsyncMock(return_value=0)

        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()

        captured_pid = {}
        original_wait_for = asyncio.wait_for

        async def capturing_wait_for(coro, timeout=None):
            captured_pid["pid"] = executor._process_pids.get("task-pid")
            try:
                await coro
            except Exception:
                pass

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("asyncio.wait_for", side_effect=capturing_wait_for):
                await executor._execute_command(["echo", "hi"], "task-pid")
        assert captured_pid.get("pid") == 2001

    @pytest.mark.asyncio
    async def test_terminate_group_called_on_timeout(self):
        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()

        mock_proc = AsyncMock()
        mock_proc.pid = 3001
        mock_proc.returncode = -1
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.at_eof.return_value = False
        mock_proc.wait = AsyncMock(return_value=-1)

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
            patch("backend.secuscan.executor._terminate_process_group", new_callable=AsyncMock) as mock_term,
        ):
            output, code = await executor._execute_command(["sleep", "999"], "task-timeout", timeout=1)
        mock_term.assert_awaited_once_with(3001, "task-timeout")
        assert code == -1
        assert "timed out" in output

    @pytest.mark.asyncio
    async def test_terminate_group_called_on_cancel(self):
        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()

        mock_proc = AsyncMock()
        mock_proc.pid = 4001
        mock_proc.returncode = -1
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.at_eof.return_value = False
        mock_proc.wait = AsyncMock(return_value=-1)

        async def raise_cancelled(*args, **kwargs):
            raise asyncio.CancelledError()

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=raise_cancelled),
            patch("backend.secuscan.executor._terminate_process_group", new_callable=AsyncMock) as mock_term,
        ):
            with pytest.raises(asyncio.CancelledError):
                await executor._execute_command(["sleep", "999"], "task-cancel")
        mock_term.assert_awaited_once_with(4001, "task-cancel")

    @pytest.mark.asyncio
    async def test_process_pid_cleared_after_successful_command(self):
        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()

        mock_proc = AsyncMock()
        mock_proc.pid = 5001
        mock_proc.returncode = 0
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.at_eof.return_value = True
        mock_proc.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await executor._execute_command(["echo", "done"], "task-pid-clear")

        assert "task-pid-clear" not in executor._process_pids

    @pytest.mark.asyncio
    async def test_process_pid_cleared_after_timeout(self):
        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()

        mock_proc = AsyncMock()
        mock_proc.pid = 6001
        mock_proc.returncode = -1
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.at_eof.return_value = False
        mock_proc.wait = AsyncMock(return_value=-1)

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
            patch("backend.secuscan.executor._terminate_process_group", new_callable=AsyncMock),
        ):
            await executor._execute_command(["sleep", "99"], "task-pid-timeout", timeout=1)

        assert "task-pid-timeout" not in executor._process_pids


class TestCancelTaskProcessGroup:
    @pytest.mark.asyncio
    async def test_cancel_task_terminates_process_group(self):
        from backend.secuscan.executor import TaskExecutor
        from unittest.mock import MagicMock
        executor = TaskExecutor()

        fake_task = MagicMock()
        fake_task.cancel = MagicMock(return_value=True)
        executor.running_tasks["task-pg"] = fake_task
        executor._process_pids["task-pg"] = 7001

        with (
            patch("backend.secuscan.executor._terminate_process_group", new_callable=AsyncMock) as mock_term,
            patch("backend.secuscan.executor.get_db", new_callable=AsyncMock) as mock_get_db,
        ):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute = AsyncMock()
            mock_db.log_audit = AsyncMock()
            mock_db.transaction = MagicMock(return_value=AsyncMock())

            await executor.cancel_task("task-pg")
        mock_term.assert_awaited_once_with(7001, "task-pg")
        fake_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_task_no_pid_still_cancels_asyncio_task(self):
        from backend.secuscan.executor import TaskExecutor
        from unittest.mock import MagicMock
        executor = TaskExecutor()

        fake_task = MagicMock()
        fake_task.cancel = MagicMock(return_value=True)
        executor.running_tasks["task-nopid"] = fake_task

        with (
            patch("backend.secuscan.executor._terminate_process_group", new_callable=AsyncMock) as mock_term,
            patch("backend.secuscan.executor.get_db", new_callable=AsyncMock) as mock_get_db,
        ):
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute = AsyncMock()
            mock_db.log_audit = AsyncMock()
            mock_db.transaction = MagicMock(return_value=AsyncMock())

            await executor.cancel_task("task-nopid")
        mock_term.assert_not_awaited()
        fake_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_unknown_task_returns_false(self):
        from backend.secuscan.executor import TaskExecutor
        executor = TaskExecutor()
        result = await executor.cancel_task("nonexistent-task-id")
        assert result is False


class TestOrphanPrevention:
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="process groups not supported on Windows")
    async def test_child_process_killed_with_parent(self):
        """Spawn a parent that forks a sleeping child; cancel, verify child dies."""
        parent = await asyncio.create_subprocess_exec(
            sys.executable, "-c",
            "import subprocess, time; subprocess.Popen(['sleep', '30']); time.sleep(30)",
            start_new_session=True,
        )
        child_pid = parent.pid
        pgid = os.getpgid(child_pid)

        await _terminate_process_group(child_pid, "orphan-test", grace_seconds=2)

        try:
            await asyncio.wait_for(parent.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass

        try:
            os.killpg(pgid, 0)
            still_alive = True
        except (ProcessLookupError, PermissionError):
            still_alive = False

        assert not still_alive, "Process group should be gone after terminate_process_group"
