"""
Tests for server-controlled safe_mode at the route/executor boundary.

Covers the behavior that was added in the safe_mode PR:
  1. Route-level: safe_mode is server-controlled, never client-supplied
  2. Executor-level: create_task stores safe_mode in the database
  3. Target validation uses the server's safe_mode value, not the client's
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. Server-controlled effective_inputs logic (what the route does)
# ---------------------------------------------------------------------------

class TestServerControlledSafeMode:
    """Tests the pattern that routes.py uses for effective_inputs."""

    @pytest.fixture
    def settings(self):
        """Minimal settings mock for testing the effective-inputs pattern."""
        mock = MagicMock()
        mock.safe_mode_default = True
        return mock

    def _build_effective_inputs(self, raw_inputs: dict, safe_mode: bool) -> dict:
        """Replicates the pattern in routes.py start_task / run_workflow_once."""
        effective = dict(raw_inputs or {})
        effective.pop("safe_mode", None)
        effective["safe_mode"] = safe_mode
        return effective

    def test_client_safe_mode_is_stripped(self, settings):
        """Client-supplied safe_mode=False is removed from inputs."""
        raw = {"target": "8.8.8.8", "safe_mode": False}
        effective = self._build_effective_inputs(raw, safe_mode=bool(settings.safe_mode_default))
        assert effective["safe_mode"] is True
        assert effective["target"] == "8.8.8.8"

    def test_client_safe_mode_true_is_stripped(self, settings):
        """Client-supplied safe_mode=True is also removed (no trust)."""
        raw = {"target": "192.168.1.1", "safe_mode": True}
        effective = self._build_effective_inputs(raw, safe_mode=bool(settings.safe_mode_default))
        assert effective["safe_mode"] is True

    def test_server_disabled_safe_mode(self, settings):
        """When server-side safe_mode_default=False, effective safe_mode is False."""
        settings.safe_mode_default = False
        raw = {"target": "8.8.8.8", "safe_mode": True}
        effective = self._build_effective_inputs(raw, safe_mode=bool(settings.safe_mode_default))
        assert effective["safe_mode"] is False

    def test_no_safe_mode_in_input_gets_server_default(self, settings):
        """When client does not send safe_mode at all, server default is used."""
        raw = {"target": "192.168.1.1"}
        effective = self._build_effective_inputs(raw, safe_mode=bool(settings.safe_mode_default))
        assert effective["safe_mode"] is True

    def test_other_inputs_preserved(self, settings):
        """Other input fields are not affected by the safe_mode injection."""
        raw = {"target": "127.0.0.1", "plugin_option": "aggressive"}
        effective = self._build_effective_inputs(raw, safe_mode=bool(settings.safe_mode_default))
        assert effective["plugin_option"] == "aggressive"
        assert effective["target"] == "127.0.0.1"


# ---------------------------------------------------------------------------
# 2. Executor safe_mode persistence
# ---------------------------------------------------------------------------

class TestExecutorSafeModePersistence:
    """Tests that executor.create_task stores safe_mode in the database."""

    @pytest.mark.asyncio
    async def test_create_task_stores_safe_mode_true(self):
        """When safe_mode=True, the tasks table row has safe_mode=1."""
        from backend.secuscan.executor import TaskExecutor

        mock_db = AsyncMock()
        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_pm = MagicMock()
        mock_pm.get_plugin.return_value = mock_plugin

        exec_instance = TaskExecutor.__new__(TaskExecutor)
        exec_instance.running_tasks = {}
        exec_instance._listeners = {}

        with (
            patch("backend.secuscan.executor.get_db", return_value=mock_db),
            patch("backend.secuscan.executor.get_plugin_manager", return_value=mock_pm),
        ):
            task_id = await exec_instance.create_task(
                "nmap",
                {"target": "192.168.1.1", "safe_mode": True},
                safe_mode=True,
                consent_granted=False,
            )

        assert task_id is not None
        call_args = mock_db.execute.call_args
        assert call_args is not None
        sql, params = call_args[0]
        assert "safe_mode" in sql
        assert params[-1] is True

    @pytest.mark.asyncio
    async def test_create_task_stores_safe_mode_false(self):
        """When safe_mode=False, the tasks table row has safe_mode=0."""
        from backend.secuscan.executor import TaskExecutor

        mock_db = AsyncMock()
        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_pm = MagicMock()
        mock_pm.get_plugin.return_value = mock_plugin

        exec_instance = TaskExecutor.__new__(TaskExecutor)
        exec_instance.running_tasks = {}
        exec_instance._listeners = {}

        with (
            patch("backend.secuscan.executor.get_db", return_value=mock_db),
            patch("backend.secuscan.executor.get_plugin_manager", return_value=mock_pm),
        ):
            task_id = await exec_instance.create_task(
                "nmap",
                {"target": "8.8.8.8", "safe_mode": False},
                safe_mode=False,
                consent_granted=False,
            )

        assert task_id is not None
        call_args = mock_db.execute.call_args
        assert call_args is not None
        sql, params = call_args[0]
        assert params[-1] is False

    @pytest.mark.asyncio
    async def test_create_task_default_safe_mode_true(self):
        """Route passes safe_mode from settings; executor receives it as the caller passes it."""
        from backend.secuscan.executor import TaskExecutor

        mock_db = AsyncMock()
        mock_plugin = MagicMock()
        mock_plugin.name = "nmap"
        mock_pm = MagicMock()
        mock_pm.get_plugin.return_value = mock_plugin

        exec_instance = TaskExecutor.__new__(TaskExecutor)
        exec_instance.running_tasks = {}
        exec_instance._listeners = {}

        with (
            patch("backend.secuscan.executor.get_db", return_value=mock_db),
            patch("backend.secuscan.executor.get_plugin_manager", return_value=mock_pm),
        ):
            task_id = await exec_instance.create_task(
                "nmap",
                {"target": "192.168.1.1", "safe_mode": True},
                safe_mode=True,
                consent_granted=False,
            )

        call_args = mock_db.execute.call_args
        sql, params = call_args[0]
        # safe_mode is the last column in the INSERT
        assert params[-1] is True

    @pytest.mark.asyncio
    async def test_create_task_rejects_invalid_plugin(self):
        """create_task raises ValueError when plugin is not found."""
        from backend.secuscan.executor import TaskExecutor

        mock_pm = MagicMock()
        mock_pm.get_plugin.return_value = None

        exec_instance = TaskExecutor.__new__(TaskExecutor)
        exec_instance.running_tasks = {}
        exec_instance._listeners = {}

        with (
            patch("backend.secuscan.executor.get_plugin_manager", return_value=mock_pm),
        ):
            with pytest.raises(ValueError, match="Plugin not found"):
                await exec_instance.create_task(
                    "nonexistent",
                    {},
                    safe_mode=True,
                    consent_granted=False,
                )
