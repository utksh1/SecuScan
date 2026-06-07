"""
Tests for workflow run/delete race conditions and disabled-workflow behavior.
"""

import asyncio
import pytest


class _FakeDB:
    def __init__(self, workflows=None):
        self._workflows = {w["id"]: dict(w) for w in (workflows or [])}
        self._tasks = {}
        self._task_counter = 0

    def get_workflow(self, wf_id):
        return self._workflows.get(wf_id)

    def delete_workflow(self, wf_id):
        self._workflows.pop(wf_id, None)

    def create_task(self, wf_id, plugin_id, status="pending"):
        self._task_counter += 1
        tid = f"task-{self._task_counter}"
        self._tasks[tid] = {"id": tid, "workflow_id": wf_id,
                            "plugin_id": plugin_id, "status": status}
        return tid

    def get_task(self, task_id):
        return self._tasks.get(task_id)

    def mark_task_failed(self, task_id, reason=""):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["fail_reason"] = reason


class _FakeLimiter:
    def __init__(self, *, full=False):
        self._full = full
        self.acquired = []

    async def acquire(self, task_id):
        if self._full:
            return False, None
        self.acquired.append(task_id)
        return True, task_id

    async def release(self, task_id):
        pass


class _FakeExecutor:
    def __init__(self, db):
        self._db = db
        self.created = []
        self.executed = []
        self.failed = []

    async def create_task(self, plugin_id, inputs, preset=None, consent_granted=False):
        tid = self._db.create_task("wf", plugin_id)
        self.created.append(tid)
        return tid

    async def execute_task(self, task_id):
        self._db._tasks[task_id]["status"] = "completed"
        self.executed.append(task_id)

    async def mark_task_failed(self, task_id, reason=""):
        self._db.mark_task_failed(task_id, reason)
        self.failed.append(task_id)


class WorkflowRunner:
    def __init__(self, db, executor, limiter):
        self._db = db
        self._executor = executor
        self._limiter = limiter

    async def _run_workflow(self, workflow_id, steps):
        wf = self._db.get_workflow(workflow_id)
        if wf is None:
            return
        if not wf.get("enabled", True):
            return
        for step in steps:
            plugin_id = step.get("plugin_id")
            if not plugin_id:
                continue
            inputs = step.get("inputs", {})
            task_id = await self._executor.create_task(
                plugin_id, inputs,
                preset=step.get("preset"),
                consent_granted=True,
            )
            can_acquire, _ = await self._limiter.acquire(task_id)
            if not can_acquire:
                await self._executor.mark_task_failed(
                    task_id, reason="Concurrency limit reached"
                )
                continue
            asyncio.create_task(self._executor.execute_task(task_id))

    async def run_workflow_once(self, workflow_id):
        wf = self._db.get_workflow(workflow_id)
        if wf is None:
            raise KeyError(f"Workflow {workflow_id} not found")
        if not wf.get("enabled", True):
            raise ValueError(f"Workflow {workflow_id} is disabled")
        steps = wf.get("steps", [])
        created_task_ids = []
        for step in steps:
            plugin_id = step.get("plugin_id")
            if not plugin_id:
                continue
            inputs = step.get("inputs", {})
            task_id = await self._executor.create_task(
                plugin_id, inputs,
                preset=step.get("preset"),
                consent_granted=True,
            )
            can_acquire, _ = await self._limiter.acquire(task_id)
            if not can_acquire:
                await self._executor.mark_task_failed(
                    task_id, reason="Concurrency limit reached"
                )
                continue
            asyncio.create_task(self._executor.execute_task(task_id))
            created_task_ids.append(task_id)
        return created_task_ids


SAMPLE_WORKFLOW = {
    "id": "wf-1",
    "name": "Daily Scan",
    "enabled": True,
    "steps": [
        {"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}},
    ],
}


@pytest.fixture
def db():
    return _FakeDB(workflows=[SAMPLE_WORKFLOW])


@pytest.fixture
def limiter_open():
    return _FakeLimiter(full=False)


@pytest.fixture
def limiter_full():
    return _FakeLimiter(full=True)


@pytest.fixture
def executor(db):
    return _FakeExecutor(db)


@pytest.fixture
def runner_open(db, executor, limiter_open):
    return WorkflowRunner(db, executor, limiter_open)


class TestRunDeleteRace:

    @pytest.mark.asyncio
    async def test_scheduled_run_after_delete_is_silent(self, runner_open, db, executor):
        db.delete_workflow("wf-1")
        steps = [{"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}}]
        await runner_open._run_workflow("wf-1", steps)
        assert executor.created == []

    @pytest.mark.asyncio
    async def test_manual_run_after_delete_raises(self, runner_open, db):
        db.delete_workflow("wf-1")
        with pytest.raises(KeyError):
            await runner_open.run_workflow_once("wf-1")

    @pytest.mark.asyncio
    async def test_delete_after_run_tasks_still_exist(self, runner_open, db, executor):
        db._workflows["wf-1"]["steps"].append(
            {"plugin_id": "nikto", "inputs": {"target": "127.0.0.1"}}
        )
        task_ids = await runner_open.run_workflow_once("wf-1")
        db.delete_workflow("wf-1")
        assert len(task_ids) == 2
        for tid in task_ids:
            assert db.get_task(tid) is not None


class TestToggleRace:

    @pytest.mark.asyncio
    async def test_scheduled_run_on_disabled_creates_no_tasks(self, runner_open, db, executor):
        db._workflows["wf-1"]["enabled"] = False
        steps = [{"plugin_id": "nmap", "inputs": {}}]
        await runner_open._run_workflow("wf-1", steps)
        assert executor.created == []

    @pytest.mark.asyncio
    async def test_manual_run_on_disabled_raises(self, runner_open, db):
        db._workflows["wf-1"]["enabled"] = False
        with pytest.raises(ValueError, match="disabled"):
            await runner_open.run_workflow_once("wf-1")

    @pytest.mark.asyncio
    async def test_re_enabling_allows_run(self, runner_open, db, executor):
        db._workflows["wf-1"]["enabled"] = False
        db._workflows["wf-1"]["enabled"] = True
        task_ids = await runner_open.run_workflow_once("wf-1")
        assert len(task_ids) == 1


class TestDisabledWorkflowBehavior:

    @pytest.mark.asyncio
    async def test_disabled_scheduled_no_tasks_no_exception(self, runner_open, db, executor):
        db._workflows["wf-1"]["enabled"] = False
        await runner_open._run_workflow("wf-1", db._workflows["wf-1"]["steps"])
        assert not executor.created
        assert not executor.failed

    @pytest.mark.asyncio
    async def test_disabled_manual_raises_value_error(self, runner_open, db):
        db._workflows["wf-1"]["enabled"] = False
        with pytest.raises(ValueError):
            await runner_open.run_workflow_once("wf-1")

    @pytest.mark.asyncio
    async def test_disabled_db_state_unchanged(self, runner_open, db, executor):
        db._workflows["wf-1"]["enabled"] = False
        await runner_open._run_workflow("wf-1", db._workflows["wf-1"]["steps"])
        assert db._tasks == {}

    @pytest.mark.asyncio
    async def test_enabled_workflow_runs_normally(self, runner_open, db, executor):
        task_ids = await runner_open.run_workflow_once("wf-1")
        assert len(task_ids) == 1
        assert db.get_task(task_ids[0])["status"] in ("pending", "completed")


class TestConcurrencyLimiterIntegration:

    @pytest.mark.asyncio
    async def test_task_marked_failed_when_limiter_full(self, db, executor, limiter_full):
        runner = WorkflowRunner(db, executor, limiter_full)
        steps = [{"plugin_id": "nmap", "inputs": {}}]
        await runner._run_workflow("wf-1", steps)
        assert len(executor.created) == 1
        assert len(executor.failed) == 1
        task = db.get_task(executor.failed[0])
        assert task["status"] == "failed"
        assert "Concurrency" in task["fail_reason"]

    @pytest.mark.asyncio
    async def test_manual_run_task_failed_when_limiter_full(self, db, executor, limiter_full):
        runner = WorkflowRunner(db, executor, limiter_full)
        result = await runner.run_workflow_once("wf-1")
        assert result == []
        assert executor.failed

    @pytest.mark.asyncio
    async def test_limiter_slot_acquired_when_open(self, runner_open, db, executor, limiter_open):
        await runner_open.run_workflow_once("wf-1")
        assert limiter_open.acquired
        assert not executor.failed


class TestDeterminism:

    @pytest.mark.asyncio
    async def test_repeated_runs_consistent(self, db, executor, limiter_open):
        runner = WorkflowRunner(db, executor, limiter_open)
        ids_1 = await runner.run_workflow_once("wf-1")
        executor.created.clear()
        executor.failed.clear()
        ids_2 = await runner.run_workflow_once("wf-1")
        assert len(ids_1) == len(ids_2)

    @pytest.mark.asyncio
    async def test_no_tasks_for_missing_plugin_id(self, db, executor, limiter_open):
        runner = WorkflowRunner(db, executor, limiter_open)
        steps = [{"plugin_id": "", "inputs": {}}, {"plugin_id": None, "inputs": {}}]
        await runner._run_workflow("wf-1", steps)
        assert executor.created == []
