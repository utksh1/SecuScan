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


def test_cancelled_error_is_not_subclass_of_exception():
    """
    Documents the Python 3.8+ behaviour: CancelledError is a BaseException,
    not Exception. If this fails, the language changed and the except ordering
    in execute_task() needs revisiting.
    """
    assert not issubclass(asyncio.CancelledError, Exception)
