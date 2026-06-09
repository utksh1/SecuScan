"""
Tests for workflow scheduler route-level security controls.

Verifies that the scheduler path applies the same consent, target validation,
rate limiting, and concurrency controls as the API path.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.secuscan.workflows import WorkflowScheduler
from backend.secuscan.ratelimit import WorkflowRateLimiter


@pytest.fixture
def scheduler():
    return WorkflowScheduler()


@pytest.fixture
def rate_limiter():
    return WorkflowRateLimiter()


# ---------------------------------------------------------------------------
# WorkflowRateLimiter unit tests
# ---------------------------------------------------------------------------

class TestWorkflowRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_first_run(self, rate_limiter):
        ok, msg = await rate_limiter.check_workflow_rate_limit("wf-1", 60)
        assert ok is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_blocks_second_run_within_interval(self, rate_limiter):
        await rate_limiter.check_workflow_rate_limit("wf-1", 60)
        ok, msg = await rate_limiter.check_workflow_rate_limit("wf-1", 60)
        assert ok is False
        assert "rate limited" in msg.lower()

    @pytest.mark.asyncio
    async def test_allows_different_workflows_independently(self, rate_limiter):
        await rate_limiter.check_workflow_rate_limit("wf-1", 60)
        ok, msg = await rate_limiter.check_workflow_rate_limit("wf-2", 60)
        assert ok is True

    @pytest.mark.asyncio
    async def test_user_workflow_limit(self, rate_limiter):
        ok, msg = await rate_limiter.check_user_workflow_limit("user-1", 5)
        assert ok is True
        await rate_limiter.register_user_workflow("user-1")
        await rate_limiter.register_user_workflow("user-1")
        await rate_limiter.register_user_workflow("user-1")
        await rate_limiter.register_user_workflow("user-1")
        await rate_limiter.register_user_workflow("user-1")
        ok, msg = await rate_limiter.check_user_workflow_limit("user-1", 5)
        assert ok is False
        assert "limit reached" in msg.lower()

    @pytest.mark.asyncio
    async def test_unregister_user_workflow(self, rate_limiter):
        await rate_limiter.register_user_workflow("user-1")
        await rate_limiter.unregister_user_workflow("user-1")
        ok, msg = await rate_limiter.check_user_workflow_limit("user-1", 1)
        assert ok is True


# ---------------------------------------------------------------------------
# WorkflowScheduler._run_workflow security control tests
# ---------------------------------------------------------------------------
# Note: _run_workflow() uses local imports inside the function body
# (e.g., "from .plugins import get_plugin_manager"), so we patch the
# original module paths rather than the local names.

class TestSchedulerSecurityControls:
    @pytest.mark.asyncio
    async def test_skips_step_when_plugin_not_found(self, scheduler):
        steps = [{"plugin_id": "nonexistent-plugin", "inputs": {}}]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock) as mock_get_db, \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm:

            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_pm = MagicMock()
            mock_pm.get_plugin.return_value = None
            mock_get_pm.return_value = mock_pm

            await scheduler._run_workflow("wf-1", steps)
            mock_db.record_workflow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_step_when_target_validation_fails(self, scheduler):
        steps = [{
            "plugin_id": "nmap",
            "inputs": {"target": "invalid-target"},
        }]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock), \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm, \
             patch("backend.secuscan.validation.validate_target", return_value=(False, "Target not allowed")) as mock_val:

            mock_pm = MagicMock()
            plugin = MagicMock()
            plugin.category = "network"
            plugin.safety = {"rate_limit": {"max_per_hour": 50}}
            plugin.fields = []
            mock_pm.get_plugin.return_value = plugin
            mock_get_pm.return_value = mock_pm

            await scheduler._run_workflow("wf-1", steps)
            mock_val.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_step_when_rate_limit_exceeded(self, scheduler):
        steps = [{
            "plugin_id": "nmap",
            "inputs": {"target": "example.com"},
        }]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock), \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm, \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.rate_limiter.can_execute", new_callable=AsyncMock) as mock_rate:

            mock_pm = MagicMock()
            plugin = MagicMock()
            plugin.category = "network"
            plugin.safety = {"rate_limit": {"max_per_hour": 50}}
            plugin.fields = []
            mock_pm.get_plugin.return_value = plugin
            mock_get_pm.return_value = mock_pm
            mock_rate.return_value = (False, "Rate limit exceeded")

            await scheduler._run_workflow("wf-1", steps)
            mock_rate.assert_called_once()

    @pytest.mark.asyncio
    async def test_applies_source_tag_in_inputs(self, scheduler):
        steps = [{
            "plugin_id": "nmap",
            "inputs": {"target": "example.com"},
        }]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock), \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm, \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.rate_limiter.can_execute", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.concurrent_limiter.acquire", return_value=(True, "")), \
             patch("backend.secuscan.executor.executor.create_task", new_callable=AsyncMock, return_value="task-1") as mock_create:

            mock_pm = MagicMock()
            plugin = MagicMock()
            plugin.category = "network"
            plugin.safety = {"rate_limit": {"max_per_hour": 50}}
            plugin.fields = []
            mock_pm.get_plugin.return_value = plugin
            mock_get_pm.return_value = mock_pm

            await scheduler._run_workflow("wf-1", steps)
            args, kwargs = mock_create.call_args
            assert kwargs.get("source") == "scheduler"
            inputs = args[1] if len(args) > 1 else kwargs.get("inputs", {})
            assert inputs.get("_source") == "scheduler"

    @pytest.mark.asyncio
    async def test_applies_safe_mode_consistently(self, scheduler):
        steps = [{
            "plugin_id": "nmap",
            "inputs": {"target": "example.com", "safe_mode": False},
        }]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock), \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm, \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.rate_limiter.can_execute", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.concurrent_limiter.acquire", return_value=(True, "")), \
             patch("backend.secuscan.executor.executor.create_task", new_callable=AsyncMock, return_value="task-1") as mock_create:

            mock_pm = MagicMock()
            plugin = MagicMock()
            plugin.category = "network"
            plugin.safety = {"rate_limit": {"max_per_hour": 50}}
            plugin.fields = []
            mock_pm.get_plugin.return_value = plugin
            mock_get_pm.return_value = mock_pm

            await scheduler._run_workflow("wf-1", steps)
            args, kwargs = mock_create.call_args
            inputs = args[1] if len(args) > 1 else kwargs.get("inputs", {})
            assert "safe_mode" in inputs
            assert inputs["safe_mode"] is True

    @pytest.mark.asyncio
    async def test_acquires_concurrency_slot(self, scheduler):
        steps = [{
            "plugin_id": "nmap",
            "inputs": {"target": "example.com"},
        }]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock), \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm, \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.rate_limiter.can_execute", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.concurrent_limiter.acquire", new_callable=AsyncMock) as mock_acquire, \
             patch("backend.secuscan.executor.executor.create_task", new_callable=AsyncMock, return_value="task-1"):

            mock_pm = MagicMock()
            plugin = MagicMock()
            plugin.category = "network"
            plugin.safety = {"rate_limit": {"max_per_hour": 50}}
            plugin.fields = []
            mock_pm.get_plugin.return_value = plugin
            mock_get_pm.return_value = mock_pm
            mock_acquire.return_value = (True, "")

            await scheduler._run_workflow("wf-1", steps)
            mock_acquire.assert_called_once_with("task-1")

    @pytest.mark.asyncio
    async def test_skips_step_when_concurrency_limit_reached(self, scheduler):
        steps = [{
            "plugin_id": "nmap",
            "inputs": {"target": "example.com"},
        }]
        with patch("backend.secuscan.workflows.get_db", new_callable=AsyncMock), \
             patch("backend.secuscan.plugins.get_plugin_manager") as mock_get_pm, \
             patch("backend.secuscan.validation.validate_target", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.rate_limiter.can_execute", return_value=(True, "")), \
             patch("backend.secuscan.ratelimit.concurrent_limiter.acquire", return_value=(False, "Concurrency limit reached")), \
             patch("backend.secuscan.executor.executor.create_task", new_callable=AsyncMock, return_value="task-1"), \
             patch("backend.secuscan.executor.executor.mark_task_failed", new_callable=AsyncMock) as mock_fail:

            mock_pm = MagicMock()
            plugin = MagicMock()
            plugin.category = "network"
            plugin.safety = {"rate_limit": {"max_per_hour": 50}}
            plugin.fields = []
            mock_pm.get_plugin.return_value = plugin
            mock_get_pm.return_value = mock_pm

            await scheduler._run_workflow("wf-1", steps)
            mock_fail.assert_called_once()


# ---------------------------------------------------------------------------
# WorkflowScheduler.tick rate limit integration
# ---------------------------------------------------------------------------

class TestTickRateLimiting:
    @pytest.mark.asyncio
    async def test_tick_applies_workflow_rate_limiter(self, scheduler):
        db_mock = AsyncMock()
        db_mock.fetchall.return_value = [{
            "id": "wf-1",
            "name": "test",
            "schedule_seconds": 60,
            "last_run_at": None,
            "steps_json": "[]",
        }]
        with patch("backend.secuscan.workflows.get_db", return_value=db_mock), \
             patch.object(scheduler, "_run_workflow", new_callable=AsyncMock) as mock_run, \
             patch("backend.secuscan.workflows.workflow_rate_limiter.check_workflow_rate_limit", new_callable=AsyncMock) as mock_rate:

            mock_rate.return_value = (True, "")
            await scheduler.tick()
            mock_rate.assert_called_once_with("wf-1", 60)
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_tick_skips_rate_limited_workflow(self, scheduler):
        db_mock = AsyncMock()
        db_mock.fetchall.return_value = [{
            "id": "wf-1",
            "name": "test",
            "schedule_seconds": 60,
            "last_run_at": None,
            "steps_json": "[]",
        }]
        with patch("backend.secuscan.workflows.get_db", return_value=db_mock), \
             patch.object(scheduler, "_run_workflow", new_callable=AsyncMock) as mock_run, \
             patch("backend.secuscan.workflows.workflow_rate_limiter.check_workflow_rate_limit", new_callable=AsyncMock) as mock_rate:

            mock_rate.return_value = (False, "Workflow rate limited: wait 30s between runs")
            await scheduler.tick()
            mock_rate.assert_called_once()
            mock_run.assert_not_called()
