"""
Unit tests for database workflow version methods.
"""
import uuid
import json
import pytest
import pytest_asyncio
from backend.secuscan.database import Database


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    # Insert dummy workflows since workflow_versions and workflow_runs have a foreign key to workflows
    await database.execute(
        "INSERT INTO workflows (id, name, steps_json) VALUES (?, ?, ?)",
        ("wf-1", "Default Workflow", "[]")
    )
    await database.execute(
        "INSERT INTO workflows (id, name, steps_json) VALUES (?, ?, ?)",
        ("wf-test-1", "Test Workflow 1", "[]")
    )
    await database.execute(
        "INSERT INTO workflows (id, name, steps_json) VALUES (?, ?, ?)",
        ("wf-A", "Workflow A", "[]")
    )
    await database.execute(
        "INSERT INTO workflows (id, name, steps_json) VALUES (?, ?, ?)",
        ("wf-B", "Workflow B", "[]")
    )
    yield database
    await database.disconnect()


class TestSnapshotWorkflowVersion:
    @pytest.mark.asyncio
    async def test_first_snapshot_has_version_1(self, db):
        v = await db.snapshot_workflow_version(
            "wf-test-1", "Test WF", 60, True, [{"plugin_id": "nmap"}]
        )
        assert v["version_number"] == 1
        assert v["workflow_id"] == "wf-test-1"
        assert v["created_by"] == "system"

    @pytest.mark.asyncio
    async def test_subsequent_snapshots_increment_version(self, db):
        v1 = await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        v2 = await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        assert v2["version_number"] == v1["version_number"] + 1

    @pytest.mark.asyncio
    async def test_snapshot_stores_definition(self, db):
        steps = [{"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}}]
        v = await db.snapshot_workflow_version("wf-1", "My WF", 120, False, steps)
        assert v["definition"]["name"] == "My WF"
        assert v["definition"]["schedule_seconds"] == 120
        assert v["definition"]["enabled"] is False
        assert v["definition"]["steps"] == steps

    @pytest.mark.asyncio
    async def test_snapshots_across_workflows_independent(self, db):
        v_a1 = await db.snapshot_workflow_version("wf-A", "A", 60, True, [])
        v_b1 = await db.snapshot_workflow_version("wf-B", "B", 60, True, [])
        v_a2 = await db.snapshot_workflow_version("wf-A", "A", 60, True, [])
        assert v_a1["version_number"] == 1
        assert v_b1["version_number"] == 1
        assert v_a2["version_number"] == 2


class TestGetWorkflowVersions:
    @pytest.mark.asyncio
    async def test_returns_all_versions_newest_first(self, db):
        await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        versions = await db.get_workflow_versions("wf-1")
        assert len(versions) == 3
        assert versions[0]["version_number"] == 3
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_workflow(self, db):
        versions = await db.get_workflow_versions("does-not-exist")
        assert versions == []


class TestGetWorkflowVersion:
    @pytest.mark.asyncio
    async def test_returns_specific_version(self, db):
        created = await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        found = await db.get_workflow_version("wf-1", created["version_number"])
        assert found is not None
        assert found["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_workflow(self, db):
        result = await db.get_workflow_version("wf-does-not-exist", 99)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_version_number(self, db):
        await db.snapshot_workflow_version("wf-1", "WF", 60, True, [])
        result = await db.get_workflow_version("wf-1", 99)
        assert result is None


class TestRecordWorkflowRun:
    @pytest.mark.asyncio
    async def test_inserts_queued_run(self, db):
        run_id = await db.record_workflow_run("wf-1", None, 1, ["t1", "t2"], "manual")
        assert run_id is not None
        run_row = await db.fetchone("SELECT status, triggered_by FROM workflow_runs WHERE id = ?", (run_id,))
        assert run_row["status"] == "queued"
        assert run_row["triggered_by"] == "manual"

    @pytest.mark.asyncio
    async def test_inserts_empty_task_list(self, db):
        run_id = await db.record_workflow_run("wf-1", None, 1, [], "scheduler")
        raw = await db.fetchone("SELECT task_ids_json FROM workflow_runs WHERE id = ?", (run_id,))
        assert raw["task_ids_json"] == "[]"


class TestFinalizeWorkflowRun:
    @pytest.mark.asyncio
    async def test_sets_status_and_timestamp(self, db):
        run_id = await db.record_workflow_run("wf-1", None, 1, [], "manual")
        await db.finalize_workflow_run(run_id, "completed")
        run_row = await db.fetchone("SELECT status, completed_at FROM workflow_runs WHERE id = ?", (run_id,))
        assert run_row["status"] == "completed"
        assert run_row["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_finalize_with_error_message(self, db):
        run_id = await db.record_workflow_run("wf-1", None, 1, [], "manual")
        await db.finalize_workflow_run(run_id, "failed", error_message="Plugin not found")
        run_row = await db.fetchone("SELECT status, error_message FROM workflow_runs WHERE id = ?", (run_id,))
        assert run_row["status"] == "failed"
        assert run_row["error_message"] == "Plugin not found"


class TestCheckWorkflowRunTasks:
    @pytest.mark.asyncio
    async def test_empty_run_returns_completed(self, db):
        run_id = await db.record_workflow_run("wf-1", None, 1, [], "manual")
        result = await db.check_workflow_run_tasks(run_id)
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_all_tasks_completed_returns_completed(self, db):
        task_ids = []
        for _ in range(3):
            tid = uuid.uuid4().hex
            await db.execute(
                "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, execution_context_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tid, "nmap", "nmap", "127.0.0.1", "{}", "{}", "completed"),
            )
            task_ids.append(tid)
        run_id = await db.record_workflow_run("wf-1", None, 1, task_ids, "manual")
        result = await db.check_workflow_run_tasks(run_id)
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_still_running_returns_none(self, db):
        tid = uuid.uuid4().hex
        await db.execute(
            "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, execution_context_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, "nmap", "nmap", "127.0.0.1", "{}", "{}", "running"),
        )
        run_id = await db.record_workflow_run("wf-1", None, 1, [tid], "manual")
        result = await db.check_workflow_run_tasks(run_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_any_task_failed_returns_failed(self, db):
        tid = uuid.uuid4().hex
        await db.execute(
            "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, execution_context_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, "nmap", "nmap", "127.0.0.1", "{}", "{}", "failed"),
        )
        run_id = await db.record_workflow_run("wf-1", None, 1, [tid], "manual")
        result = await db.check_workflow_run_tasks(run_id)
        assert result == "failed"

    @pytest.mark.asyncio
    async def test_missing_run_id_returns_none(self, db):
        result = await db.check_workflow_run_tasks("no-such-run")
        assert result is None


class TestGetWorkflowRuns:
    @pytest.mark.asyncio
    async def test_returns_paginated_run_history(self, db):
        for _ in range(3):
            run_id = await db.record_workflow_run("wf-1", None, 1, [], "manual")
            await db.finalize_workflow_run(run_id, "completed")
        result = await db.get_workflow_runs("wf-1", limit=10)
        assert result["total"] == 3
        assert len(result["runs"]) == 3

    @pytest.mark.asyncio
    async def test_respects_limit_and_offset(self, db):
        for _ in range(3):
            run_id = await db.record_workflow_run("wf-1", None, 1, [], "manual")
            await db.finalize_workflow_run(run_id, "completed")
        result = await db.get_workflow_runs("wf-1", limit=1, offset=1)
        assert result["total"] == 3
        assert len(result["runs"]) == 1
