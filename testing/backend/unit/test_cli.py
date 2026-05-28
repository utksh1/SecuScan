import sys
from unittest.mock import patch, MagicMock, AsyncMock
# pyrefly: ignore [missing-import]
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
        mock_executor.create_task.assert_called_once_with("http_inspector", {"target": "127.0.0.1"}, consent_granted=True)


def test_cli_help_menu():
    """Test CLI parses help argument correctly."""
    with patch("argparse.ArgumentParser.print_help") as mock_print_help, \
         patch("sys.argv", ["secuscan", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_print_help.assert_called_once()
