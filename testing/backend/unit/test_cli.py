import sys
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from backend.secuscan.cli import run_scan, main

@pytest.mark.anyio
async def test_run_scan_plugin_not_found():
    """Test run_scan when specified plugin does not exist."""
    mock_pm = MagicMock()
    mock_pm.get_plugin.return_value = None
    mock_pm.plugins = {"http_inspector": MagicMock()}

    with patch("backend.secuscan.cli.init_db", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_cache", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_plugins", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.get_plugin_manager", return_value=mock_pm):

        result = await run_scan("127.0.0.1", "non-existent-plugin", "console")
        assert result == 1
        mock_pm.get_plugin.assert_called_with("non-existent-plugin")


@pytest.mark.anyio
async def test_run_scan_successful_execution():
    """Test run_scan with successful execution and console format."""
    mock_plugin = MagicMock()
    mock_plugin.name = "HTTP Inspector"

    mock_pm = MagicMock()
    mock_pm.get_plugin.return_value = mock_plugin

    # Mock TaskExecutor
    mock_executor = MagicMock()
    mock_executor.create_task = AsyncMock(return_value="task-uuid-123")
    mock_executor.execute_task = AsyncMock()

    mock_queue = AsyncMock()
    mock_queue.get.side_effect = [
        {"type": "output", "data": "Scanning..."},
        {"type": "status", "data": "completed"}
    ]
    mock_executor.subscribe.return_value = mock_queue

    # Mock DB row
    mock_db = AsyncMock()
    mock_row = {
        "id": "task-uuid-123",
        "plugin_id": "http_inspector",
        "tool_name": "http_inspector",
        "target": "127.0.0.1",
        "status": "completed",
        "created_at": "2026-05-14T10:30:00",
        "preset": "standard",
        "inputs_json": "{}",
        "command_used": "nikto -h 127.0.0.1",
        "structured_json": "{\"findings\": [{\"title\": \"XSS\", \"severity\": \"MEDIUM\"}]}"
    }
    mock_db.fetchone.return_value = mock_row

    with patch("backend.secuscan.cli.init_db", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_cache", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_plugins", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.get_plugin_manager", return_value=mock_pm), \
         patch("backend.secuscan.cli.executor", mock_executor), \
         patch("backend.secuscan.cli.get_db", return_value=mock_db):

        result = await run_scan("127.0.0.1", "http_inspector", "console")
        assert result == 0
        mock_executor.create_task.assert_called_once_with(
            "http_inspector",
            {"target": "127.0.0.1", "safe_mode": True},
            safe_mode=True,
            consent_granted=True,
        )


def test_cli_help_menu():
    """Test CLI parses help argument correctly."""
    with patch("argparse.ArgumentParser.print_help") as mock_print_help, \
         patch("sys.argv", ["secuscan", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_print_help.assert_called_once()


def test_cli_no_args_calls_print_help():
    """With no arguments, main() calls print_help and returns (no SystemExit)."""
    with patch("argparse.ArgumentParser.print_help") as mock_print_help, \
         patch("sys.argv", ["secuscan"]):
        main()  # should not raise, just calls print_help
        mock_print_help.assert_called_once()


@pytest.mark.anyio
async def test_run_scan_target_dot_defaults_to_secret_scanner():
    """When target is '.', run_scan defaults to secret_scanner plugin."""
    mock_plugin = MagicMock()
    mock_plugin.name = "Secret Scanner"

    mock_pm = MagicMock()
    mock_pm.get_plugin.return_value = mock_plugin
    mock_pm.plugins = {"secret_scanner": mock_plugin}

    mock_executor = MagicMock()
    mock_executor.create_task = AsyncMock(return_value="task-dot-1")
    mock_executor.execute_task = AsyncMock()

    mock_queue = AsyncMock()
    mock_queue.get.side_effect = [{"type": "status", "data": "completed"}]
    mock_executor.subscribe.return_value = mock_queue

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = {
        "id": "task-dot-1",
        "plugin_id": "secret_scanner",
        "tool_name": "secret_scanner",
        "target": ".",
        "status": "completed",
        "created_at": "2026-01-01",
        "preset": None,
        "inputs_json": "{}",
        "command_used": "",
        "structured_json": "{}",
    }

    with patch("backend.secuscan.cli.init_db", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_cache", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_plugins", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.get_plugin_manager", return_value=mock_pm), \
         patch("backend.secuscan.cli.executor", mock_executor), \
         patch("backend.secuscan.cli.get_db", return_value=mock_db):

        result = await run_scan(".", "nmap", "console")
        assert result == 0
        mock_executor.create_task.assert_called_once()


@pytest.mark.anyio
async def test_run_scan_task_not_found_returns_1():
    """When the task record is missing from DB after execution, run_scan returns 1."""
    mock_plugin = MagicMock()
    mock_plugin.name = "Nmap"

    mock_pm = MagicMock()
    mock_pm.get_plugin.return_value = mock_plugin

    mock_executor = MagicMock()
    mock_executor.create_task = AsyncMock(return_value="task-missing-1")
    mock_executor.execute_task = AsyncMock()

    mock_queue = AsyncMock()
    mock_queue.get.side_effect = [{"type": "status", "data": "completed"}]
    mock_executor.subscribe.return_value = mock_queue

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = None  # task record gone

    with patch("backend.secuscan.cli.init_db", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_cache", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_plugins", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.get_plugin_manager", return_value=mock_pm), \
         patch("backend.secuscan.cli.executor", mock_executor), \
         patch("backend.secuscan.cli.get_db", return_value=mock_db):

        result = await run_scan("127.0.0.1", "nmap", "console")
        assert result == 1


@pytest.mark.anyio
async def test_run_scan_failed_task_returns_1():
    """When task status is 'failed', run_scan returns 1 without printing a report."""
    mock_plugin = MagicMock()
    mock_plugin.name = "Nmap"

    mock_pm = MagicMock()
    mock_pm.get_plugin.return_value = mock_plugin

    mock_executor = MagicMock()
    mock_executor.create_task = AsyncMock(return_value="task-failed-1")
    mock_executor.execute_task = AsyncMock()

    mock_queue = AsyncMock()
    mock_queue.get.side_effect = [{"type": "status", "data": "failed"}]
    mock_executor.subscribe.return_value = mock_queue

    mock_db = AsyncMock()
    mock_db.fetchone.return_value = {
        "id": "task-failed-1",
        "plugin_id": "nmap",
        "tool_name": "nmap",
        "target": "127.0.0.1",
        "status": "failed",
        "created_at": "2026-01-01",
        "preset": None,
        "inputs_json": "{}",
        "command_used": "",
        "structured_json": None,
    }

    with patch("backend.secuscan.cli.init_db", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_cache", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.init_plugins", new_callable=AsyncMock), \
         patch("backend.secuscan.cli.get_plugin_manager", return_value=mock_pm), \
         patch("backend.secuscan.cli.executor", mock_executor), \
         patch("backend.secuscan.cli.get_db", return_value=mock_db):

        result = await run_scan("127.0.0.1", "nmap", "console")
        assert result == 1
