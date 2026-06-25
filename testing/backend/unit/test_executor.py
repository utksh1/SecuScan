import asyncio
import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.secuscan.config import settings
from backend.secuscan.database import get_db, init_db
from backend.secuscan.executor import STREAM_LISTENER_QUEUE_MAXSIZE, TaskExecutor
from backend.secuscan.models import TaskStatus
from backend.secuscan.plugins import get_plugin_manager, init_plugins


def _ensure_plugins_loaded():
    try:
        return get_plugin_manager()
    except RuntimeError:
        asyncio.run(init_plugins(settings.plugins_dir))
        return get_plugin_manager()


@pytest.mark.asyncio
async def test_stream_listener_queue_is_bounded_for_slow_consumers():
    executor = TaskExecutor()
    queue = executor.subscribe("task-1")

    for index in range(STREAM_LISTENER_QUEUE_MAXSIZE + 5):
        await executor._broadcast("task-1", "output", f"line-{index}")

    assert queue.maxsize == STREAM_LISTENER_QUEUE_MAXSIZE
    assert queue.qsize() == STREAM_LISTENER_QUEUE_MAXSIZE

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert events[0]["data"] == "line-5"
    assert events[-1]["data"] == f"line-{STREAM_LISTENER_QUEUE_MAXSIZE + 4}"


@pytest.mark.asyncio
async def test_stream_listener_keeps_latest_status_when_queue_is_full():
    executor = TaskExecutor()
    queue = executor.subscribe("task-1")

    for index in range(STREAM_LISTENER_QUEUE_MAXSIZE):
        await executor._broadcast("task-1", "output", f"line-{index}")
    await executor._broadcast("task-1", "status", TaskStatus.COMPLETED.value)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert len(events) == STREAM_LISTENER_QUEUE_MAXSIZE
    assert events[-1] == {
        "type": "status",
        "data": TaskStatus.COMPLETED.value,
    }


def test_parse_results_prefers_report_path_when_available(setup_test_environment, tmp_path):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("secret_scanner")
    assert plugin is not None

    report_file = tmp_path / "gitleaks-report.json"
    report_file.write_text(
        json.dumps(
            [
                {
                    "RuleID": "generic-api-key",
                    "File": "config.py",
                    "StartLine": 10,
                    "Offender": "SG.xxxx",
                }
            ]
        ),
        encoding="utf-8",
    )

    plugin.output["report_path"] = str(report_file)
    executor = TaskExecutor()

    result = executor._parse_results(plugin, "No leaks found")
    assert result["count"] == 1
    assert "Secret Leak" in result["findings"][0]["title"]


def test_parse_results_falls_back_to_stdout_when_report_missing(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("secret_scanner")
    assert plugin is not None

    plugin.output["report_path"] = "/tmp/does-not-exist.json"
    executor = TaskExecutor()
    stdout_json = json.dumps(
        [
            {
                "RuleID": "generic-api-key",
                "File": "stdout.py",
                "StartLine": 7,
                "Offender": "AKIA...",
            }
        ]
    )

    result = executor._parse_results(plugin, stdout_json)
    assert result["count"] == 1
    assert "stdout.py" in result["findings"][0]["title"]


def test_icmp_ping_parser_summarizes_full_packet_loss(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    output = """PING 192.168.1.1 (192.168.1.1): 56 data bytes
Request timeout for icmp_seq 0
76 bytes from 115.247.228.233: Communication prohibited by filter

--- 192.168.1.1 ping statistics ---
7 packets transmitted, 0 packets received, 100.0% packet loss
"""

    result = executor._parse_results(plugin, output)

    assert result["count"] == 1
    assert result["findings"][0]["title"] == "No ICMP Response: 192.168.1.1"
    assert result["findings"][0]["severity"] == "info"
    assert result["metrics"]["packet_loss_percent"] == 100.0
    assert result["metrics"]["filtered"] is True


def test_icmp_ping_parser_handles_packet_loss_only_output(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    output = """PING 8.8.8.8 (8.8.8.8): 56 data bytes

--- 8.8.8.8 ping statistics ---
4 packets transmitted, 4 packets received, 0.0% packet loss
"""

    result = executor._parse_results(plugin, output)

    assert result["count"] == 1
    assert result["findings"][0]["title"] == "Host Reachable: 8.8.8.8"
    assert result["metrics"]["packet_loss_percent"] == 0.0
    assert result["metrics"]["reachable"] is True


def test_classify_command_result_allows_nonfatal_ping_exit_with_statistics(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    status, error = executor._classify_command_result(
        plugin=plugin,
        output="--- 192.168.1.1 ping statistics ---\n7 packets transmitted, 0 packets received, 100.0% packet loss\n",
        exit_code=2,
    )

    assert status == "completed"
    assert error is None


def test_classify_command_result_keeps_real_ping_execution_errors_failed(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("icmp_ping")
    assert plugin is not None

    executor = TaskExecutor()
    status, error = executor._classify_command_result(
        plugin=plugin,
        output="ping: cannot resolve definitely-not-a-host: Unknown host\n",
        exit_code=2,
    )

    assert status == "failed"
    assert error is not None


def test_classify_command_result_fails_on_unknown_option_even_with_zero_exit(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("nikto")
    assert plugin is not None

    executor = TaskExecutor()
    status, error = executor._classify_command_result(
        plugin=plugin,
        output="Unknown option: no404\n",
        exit_code=0,
    )

    assert status == "failed"
    assert error is not None


def test_classify_command_result_fails_on_undefined_flag_even_with_zero_exit(setup_test_environment):
    manager = _ensure_plugins_loaded()
    plugin = manager.get_plugin("nuclei")
    assert plugin is not None

    executor = TaskExecutor()
    status, error = executor._classify_command_result(
        plugin=plugin,
        output="flag provided but not defined: -json\n",
        exit_code=0,
    )

    assert status == "failed"
    assert error is not None


def test_resolve_execution_timeout_clamps_requested_timeout(monkeypatch):
    monkeypatch.setattr(settings, "sandbox_timeout", 600)

    executor = TaskExecutor()

    assert executor._resolve_execution_timeout({"timeout": 9999}) == 600


def test_resolve_execution_timeout_allows_shorter_requested_timeout(monkeypatch):
    monkeypatch.setattr(settings, "sandbox_timeout", 600)

    executor = TaskExecutor()

    assert executor._resolve_execution_timeout({"timeout": 120}) == 120


def test_resolve_execution_timeout_ignores_invalid_values(monkeypatch):
    monkeypatch.setattr(settings, "sandbox_timeout", 600)

    executor = TaskExecutor()

    assert executor._resolve_execution_timeout({"timeout": "invalid"}) == 600


def test_resolve_execution_timeout_prefers_max_scan_time(monkeypatch):
    monkeypatch.setattr(settings, "sandbox_timeout", 600)

    executor = TaskExecutor()

    assert executor._resolve_execution_timeout({"max_scan_time": 90, "timeout": 120}) == 90


@pytest.mark.asyncio
async def test_execute_task_sets_cancelled_status_in_db(setup_test_environment):
    """
    When execute_task() is cancelled, the DB row must be updated to
    CANCELLED status via the explicit except asyncio.CancelledError handler.
    This directly exercises the executor path, not an isolated helper.
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "127.0.0.1", '{"target":"127.0.0.1"}',
         TaskStatus.QUEUED.value, 1, 1)
    )

    executor = TaskExecutor()

    async def raise_cancelled(*args, **kwargs):
        raise asyncio.CancelledError()

    with patch.object(executor, "_execute_command", side_effect=raise_cancelled), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "127.0.0.1"]

        task = asyncio.create_task(executor.execute_task(task_id))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    row = await db.fetchone(
        "SELECT status FROM tasks WHERE id = ?", (task_id,)
    )
    assert row["status"] == TaskStatus.CANCELLED.value, (
        f"Expected CANCELLED in DB, got {row['status']}. "
        "except asyncio.CancelledError handler is not writing to DB."
    )
    mock_limiter.release.assert_called_once_with(task_id)
    await db.disconnect()


@pytest.mark.asyncio
async def test_execute_task_releases_limiter_on_normal_completion(setup_test_environment):
    """
    Concurrency slot must be released in finally even on successful completion.
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "127.0.0.1", '{"target":"127.0.0.1"}',
         TaskStatus.QUEUED.value, 1, 1)
    )

    executor = TaskExecutor()

    async def fake_command(*args, **kwargs):
        return "80/tcp open http", 0

    with patch.object(executor, "_execute_command", side_effect=fake_command), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "nmap"
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "127.0.0.1"]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task(task_id)

    mock_limiter.release.assert_called_once_with(task_id)
    await db.disconnect()



def test_cancelled_error_is_not_subclass_of_exception():
    """
    Documents the Python 3.8+ behaviour: CancelledError is a BaseException,
    not Exception. If this fails, the language changed and the except ordering
    in execute_task() needs revisiting.
    """
    assert not issubclass(asyncio.CancelledError, Exception)

# ---------------------------------------------------------------------------
# Executor-level network policy enforcement tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_task_blocked_by_network_policy(setup_test_environment):
    """
    When the network policy denies the task's target, execute_task() must:
      - mark the task FAILED in the DB
      - broadcast FAILED status
      - never invoke the plugin/scanner
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "10.0.0.1", '{"target":"10.0.0.1"}',
         TaskStatus.QUEUED.value, 1, 1)
    )

    executor = TaskExecutor()

    # Policy engine that always denies
    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (False, "Blocked by denylist rule: test", None)

    with patch("backend.secuscan.executor.settings") as mock_settings, \
         patch("backend.secuscan.executor.get_policy_engine", return_value=mock_engine), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_settings.enforce_network_policy = True
        mock_settings.docker_enabled = False
        mock_settings.raw_output_dir = settings.raw_output_dir
        mock_settings.sandbox_timeout = 600

        mock_limiter.release = AsyncMock()
        mock_pm.return_value.get_plugin.return_value = MagicMock(name="nmap", presets={})
        mock_pm.return_value.build_command.return_value = ["nmap", "10.0.0.1"]

        await executor.execute_task(task_id)

    row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.FAILED.value, (
        f"Expected FAILED, got {row['status']}"
    )
    assert "Network policy denied" in (row["error_message"] or ""), (
        f"Expected denial reason in error_message, got: {row['error_message']}"
    )
    # Plugin execution must not have been attempted
    mock_pm.return_value.build_command.assert_not_called()
    mock_limiter.release.assert_called_once_with(task_id)
    await db.disconnect()

@pytest.mark.asyncio
async def test_execute_task_allowed_by_network_policy(setup_test_environment):
    """
    When the network policy allows the task's target, the plugin must execute normally.
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "8.8.8.8", '{"target":"8.8.8.8"}',
         TaskStatus.QUEUED.value, 1, 0)
    )

    executor = TaskExecutor()

    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (True, "Allowed by allowlist rule: test", None)

    async def fake_command(*args, **kwargs):
        return "80/tcp open http", 0

    with patch("backend.secuscan.executor.settings") as mock_settings, \
         patch("backend.secuscan.executor.get_policy_engine", return_value=mock_engine), \
         patch.object(executor, "_execute_command", side_effect=fake_command), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_settings.enforce_network_policy = True
        mock_settings.docker_enabled = False
        mock_settings.raw_output_dir = settings.raw_output_dir
        mock_settings.sandbox_timeout = 600

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "nmap"
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "8.8.8.8"]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task(task_id)

    row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.COMPLETED.value, (
        f"Expected COMPLETED, got {row['status']}"
    )
    mock_engine.check_access.assert_called_once()
    mock_limiter.release.assert_called_once_with(task_id)
    await db.disconnect()

@pytest.mark.asyncio
async def test_execute_task_network_policy_log_only(setup_test_environment):
    """
    When settings.network_policy_failure_mode == "log_only", even if policy check
    returns disallowed, the task execution should continue (and not mark the task as failed
    due to network policy).
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "10.0.0.1", '{"target":"10.0.0.1"}',
         TaskStatus.QUEUED.value, 1, 0)
    )

    executor = TaskExecutor()

    # Policy denies target
    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (False, "Blocked by denylist rule: test", None)

    async def fake_command(*args, **kwargs):
        return "80/tcp open http", 0

    with patch("backend.secuscan.executor.settings") as mock_settings, \
         patch("backend.secuscan.executor.get_policy_engine", return_value=mock_engine), \
         patch.object(executor, "_execute_command", side_effect=fake_command), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_settings.enforce_network_policy = True
        mock_settings.network_policy_failure_mode = "log_only"
        mock_settings.docker_enabled = False
        mock_settings.raw_output_dir = settings.raw_output_dir
        mock_settings.sandbox_timeout = 600

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "nmap"
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "10.0.0.1"]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task(task_id)

    row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (task_id,))
    # Task should successfully complete because network violation is ignored in log_only mode!
    assert row["status"] == TaskStatus.COMPLETED.value
    mock_engine.check_access.assert_called_once()
    await db.disconnect()

@pytest.mark.asyncio
async def test_docker_network_autocreated_when_missing(setup_test_environment):
    """If docker network is absent, executor auto-creates it and continues."""
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "8.8.8.8", '{"target":"8.8.8.8"}',
         TaskStatus.QUEUED.value, 1, 0)
    )

    executor = TaskExecutor()

    # Policy allows the target so we reach the Docker block
    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (True, "Allowed", None)

    call_count = 0
    async def fake_subprocess(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        proc = MagicMock()
        # First call: docker network inspect (fails, returncode=1)
        # Second call: docker network create (succeeds, returncode=0)
        proc.returncode = 1 if call_count == 1 else 0
        proc.stdout = AsyncMock(return_value=b"")
        proc.stderr = AsyncMock(return_value=b"")
        async def _wait():
            return proc.returncode
        proc.wait = _wait
        return proc

    # Stub the actually executed command to not actually run docker/nmap
    async def fake_command(*args, **kwargs):
        return "80/tcp open http", 0

    with patch("backend.secuscan.executor.settings") as mock_settings, \
         patch("backend.secuscan.executor.get_policy_engine", return_value=mock_engine), \
         patch("backend.secuscan.executor.asyncio.create_subprocess_exec", side_effect=fake_subprocess), \
         patch.object(executor, "_execute_command", side_effect=fake_command), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_settings.enforce_network_policy = True
        mock_settings.docker_enabled = True
        mock_settings.docker_network = "restricted"
        mock_settings.sandbox_memory_mb = 512
        mock_settings.sandbox_cpu_quota = 0.5
        mock_settings.sandbox_timeout = 600
        mock_settings.raw_output_dir = settings.raw_output_dir

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_plugin.output = {"parser": "builtin_nmap", "format": "text"}
        mock_plugin.category = "Network"
        mock_plugin.id = "nmap"
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "8.8.8.8"]
        mock_pm.return_value.plugins_dir = MagicMock()
        mock_pm.return_value.plugins_dir.__truediv__ = MagicMock(
            return_value=MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(exists=lambda: False))
            )
        )

        await executor.execute_task(task_id)

    row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (task_id,))
    # Should NOT be failed due to network - it was auto-created and completed
    assert row["status"] == TaskStatus.COMPLETED.value
    await db.disconnect()

@pytest.mark.asyncio
async def test_docker_network_missing_and_create_fails(setup_test_environment):
    """If docker network inspect AND create both fail, task is marked FAILED."""
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "8.8.8.8", '{"target":"8.8.8.8"}',
         TaskStatus.QUEUED.value, 1, 0)
    )

    executor = TaskExecutor()

    # Policy allows the target so we reach the Docker block
    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (True, "Allowed", None)

    # All subprocess calls (inspect, create isolated, create fallback) return returncode=1
    async def fake_subprocess(*args, **kwargs):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = AsyncMock(return_value=b"")
        proc.stderr = AsyncMock(return_value=b"")
        async def _wait():
            return 1
        proc.wait = _wait
        return proc

    with patch("backend.secuscan.executor.settings") as mock_settings, \
         patch("backend.secuscan.executor.get_policy_engine", return_value=mock_engine), \
         patch("backend.secuscan.executor.asyncio.create_subprocess_exec", side_effect=fake_subprocess), \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter, \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_settings.enforce_network_policy = True
        mock_settings.docker_enabled = True
        mock_settings.docker_network = "restricted"
        mock_settings.sandbox_memory_mb = 512
        mock_settings.sandbox_cpu_quota = 0.5
        mock_settings.sandbox_timeout = 600
        mock_settings.raw_output_dir = settings.raw_output_dir

        mock_limiter.release = AsyncMock()

        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_plugin.presets = {}
        mock_plugin.docker_image = None
        mock_pm.return_value.get_plugin.return_value = mock_plugin
        mock_pm.return_value.build_command.return_value = ["nmap", "8.8.8.8"]

        await executor.execute_task(task_id)

    row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.FAILED.value
    assert "does not exist and could not be created" in (row["error_message"] or "")
    mock_limiter.release.assert_called_once_with(task_id)
    await db.disconnect()


# ---------------------------------------------------------------------------
# Direct tests for extracted helper methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enforce_guardrails_empty_target():
    executor = TaskExecutor()
    # If target is empty, enforce_guardrails should immediately return True
    res = await executor._enforce_guardrails("", "nmap", False, "task-1")
    assert res is True


@pytest.mark.asyncio
async def test_enforce_guardrails_validation_failure(setup_test_environment):
    await init_db(settings.database_path)
    db = await get_db()

    executor = TaskExecutor()
    task_id = str(uuid.uuid4())

    # Pre-populate task in DB so mark_task_failed works
    await db.execute(
        "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, status, consent_granted, safe_mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (task_id, "nmap", "nmap", "127.0.0.1", "{}", TaskStatus.QUEUED.value, 1, 1)
    )

    with patch("backend.secuscan.executor.get_plugin_manager") as mock_pm, \
         patch("backend.secuscan.executor.asyncio.to_thread") as mock_to_thread:

        mock_plugin = MagicMock()
        mock_plugin.category = "Network"
        mock_pm.return_value.get_plugin.return_value = mock_plugin

        # validate_target returns (False, "invalid target")
        mock_to_thread.return_value = (False, "invalid target")

        res = await executor._enforce_guardrails("127.0.0.1", "nmap", True, task_id)
        assert res is False

    row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.FAILED.value
    assert "Safe mode target validation failed" in row["error_message"]
    await db.disconnect()


@pytest.mark.asyncio
async def test_enforce_guardrails_network_policy_failure(setup_test_environment):
    await init_db(settings.database_path)
    db = await get_db()

    executor = TaskExecutor()
    task_id = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, status, consent_granted, safe_mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (task_id, "nmap", "nmap", "10.0.0.1", "{}", TaskStatus.QUEUED.value, 1, 0)
    )

    mock_engine = MagicMock()
    mock_engine.check_access.return_value = (False, "Blocked by policy", None)

    with patch("backend.secuscan.executor.settings") as mock_settings, \
         patch("backend.secuscan.executor.get_policy_engine", return_value=mock_engine), \
         patch("backend.secuscan.executor.get_plugin_manager") as mock_pm:

        mock_settings.enforce_network_policy = True
        mock_settings.network_policy_failure_mode = "block"
        mock_settings.dns_resolution_timeout_seconds = 5

        mock_plugin = MagicMock()
        mock_plugin.category = "Network"
        mock_pm.return_value.get_plugin.return_value = mock_plugin

        res = await executor._enforce_guardrails("10.0.0.1", "nmap", False, task_id)
        assert res is False

    row = await db.fetchone("SELECT status, error_message FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.FAILED.value
    assert "Network policy denied access" in row["error_message"]
    await db.disconnect()


@pytest.mark.asyncio
async def test_ensure_docker_network_exists():
    executor = TaskExecutor()

    proc = MagicMock()
    proc.returncode = 0
    proc.wait = AsyncMock(return_value=0)

    with patch("backend.secuscan.executor.asyncio.create_subprocess_exec", return_value=proc) as mock_create:
        await executor._ensure_docker_network()

        # Should only call inspect network once
        mock_create.assert_called_once_with(
            "docker", "network", "inspect", settings.docker_network,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )


@pytest.mark.asyncio
async def test_execute_modular_scanner(setup_test_environment):
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    # Insert task in DB
    await db.execute(
        """
        INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, inputs_json, status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, owner_id, "mock_scanner", "mock_scanner", "127.0.0.1", "{}", TaskStatus.QUEUED.value, 1, 0)
    )

    class MockScanner:
        name = "MockScanner"
        def __init__(self, task_id, db, safe_mode=False):
            self.task_id = task_id
            self.db = db
            self.safe_mode = safe_mode

        async def run(self, target, inputs):
            return {
                "status": "completed",
                "findings": [
                    {
                        "title": "Mock Finding",
                        "category": "Mock Category",
                        "severity": "low",
                        "description": "Mock description",
                    }
                ],
                "asset_services": []
            }

    executor = TaskExecutor()

    # We patch the MODULAR_SCANNERS dictionary in backend.secuscan.executor
    with patch.dict("backend.secuscan.executor.MODULAR_SCANNERS", {"mock_scanner": MockScanner}):
        status, duration = await executor._execute_modular_scanner(
            db=db,
            task_id=task_id,
            owner_id=owner_id,
            plugin_id="mock_scanner",
            target="127.0.0.1",
            inputs={},
            safe_mode=False
        )

    assert status == TaskStatus.COMPLETED.value
    assert duration >= 0

    # Verify task updated in DB
    row = await db.fetchone("SELECT status, structured_json FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.COMPLETED.value
    structured = json.loads(row["structured_json"])
    assert len(structured["findings"]) == 1
    assert structured["findings"][0]["title"] == "Mock Finding"

    await db.disconnect()


@pytest.mark.asyncio
async def test_execute_task_aborts_when_task_no_longer_queued(setup_test_environment):
    """
    When the optimistic UPDATE ... WHERE status='queued' returns rowcount 0
    (because the task was deleted or its status changed before execution started),
    execute_task() must abort without proceeding further.
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "127.0.0.1", '{"target":"127.0.0.1"}',
         TaskStatus.RUNNING.value, 1, 1)
    )

    executor = TaskExecutor()

    with patch("backend.secuscan.executor.get_plugin_manager") as mock_pm, \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter:
        mock_limiter.release = AsyncMock()
        mock_pm.return_value.get_plugin.return_value = MagicMock(name="nmap", presets={})

        await executor.execute_task(task_id)

    # Verify the task was NOT updated — it stays in its original (RUNNING) state
    row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.RUNNING.value
    mock_pm.return_value.build_command.assert_not_called()
    await db.disconnect()


@pytest.mark.asyncio
async def test_execute_standard_scanner(setup_test_environment):
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())

    # Insert task in DB
    await db.execute(
        """
        INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, inputs_json, status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, owner_id, "mock_cli_plugin", "mock_cli_plugin", "127.0.0.1", "{}", TaskStatus.QUEUED.value, 1, 0)
    )

    executor = TaskExecutor()

    mock_plugin = MagicMock()
    mock_plugin.id = "mock_cli_plugin"
    mock_plugin.name = "mock_cli_plugin"
    mock_plugin.docker_image = None

    with patch("backend.secuscan.executor.get_plugin_manager") as mock_pm, \
         patch.object(executor, "_execute_command", return_value=("Mock output\n", 0)) as mock_exec, \
         patch.object(executor, "_classify_command_result", return_value=(TaskStatus.COMPLETED.value, None)) as mock_classify, \
         patch.object(executor, "_upsert_findings_and_report") as mock_upsert:

        mock_pm.return_value.build_command.return_value = ["ping", "127.0.0.1"]

        status, duration, exit_code = await executor._execute_standard_scanner(
            db=db,
            task_id=task_id,
            owner_id=owner_id,
            plugin=mock_plugin,
            plugin_id="mock_cli_plugin",
            target="127.0.0.1",
            inputs={}
        )

    assert status == TaskStatus.COMPLETED.value
    assert exit_code == 0
    assert duration >= 0

    # Verify task updated in DB
    row = await db.fetchone("SELECT status, exit_code FROM tasks WHERE id = ?", (task_id,))
    assert row["status"] == TaskStatus.COMPLETED.value
    assert row["exit_code"] == 0

    await db.disconnect()


@pytest.mark.asyncio
async def test_execute_task_aborts_when_task_deleted_before_running(setup_test_environment):
    """
    When the task row is deleted before execute_task runs the optimistic
    UPDATE, the rowcount will be 0 and the method must abort gracefully.
    """
    await init_db(settings.database_path)
    db = await get_db()

    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json,
                           status, consent_granted, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "nmap", "nmap", "127.0.0.1", '{"target":"127.0.0.1"}',
         TaskStatus.QUEUED.value, 1, 1)
    )

    executor = TaskExecutor()

    with patch("backend.secuscan.executor.get_plugin_manager") as mock_pm, \
         patch("backend.secuscan.executor.concurrent_limiter") as mock_limiter:
        mock_limiter.release = AsyncMock()
        mock_pm.return_value.get_plugin.return_value = MagicMock(name="nmap", presets={})

        # Delete the task before execute_task can update it
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        await executor.execute_task(task_id)

    assert task_id not in executor.running_tasks
    await db.disconnect()
