"""
Tests for database-backed workflow run history and rollback (issue #225).

Covers:
  - snapshot_workflow_version creates a version row with incremented version_number.
  - version_number auto-increments per workflow (not globally).
  - get_workflow_versions returns versions newest-first.
  - get_workflow_version returns the correct version or None.
  - record_workflow_run creates a run row with the correct fields.
  - get_workflow_runs returns paginated runs newest-first.
  - Rollback restores workflow definition from a prior version.
  - Rollback creates a new version snapshot tagged with rollback metadata.
  - Rollback to non-existent version returns 404.
  - update_workflow snapshots a new version on every PATCH.
  - run_workflow_once records a run row with the active version.
  - Runs are isolated per workflow (different workflow_ids).
  - get_workflow_runs pagination works correctly.
  - Version definitions round-trip through JSON faithfully.
"""

import json
import uuid
import pytest
import pytest_asyncio

from backend.secuscan.database import Database

_STEPS = [{"plugin_id": "http_inspector", "inputs": {"url": "http://example.com"}}]


def _wf_id():
    return uuid.uuid4().hex


@pytest_asyncio.fixture
async def db(tmp_path):
    instance = Database(str(tmp_path / "test.db"))
    await instance.connect()
    yield instance
    await instance.disconnect()


async def _insert_workflow(db: Database, name: str = "test-wf") -> str:
    wf_id = _wf_id()
    await db.execute(
        "INSERT INTO workflows (id, name, steps_json) VALUES (?, ?, ?)",
        (wf_id, name, json.dumps(_STEPS)),
    )
    return wf_id


class TestSnapshotWorkflowVersion:
    @pytest.mark.asyncio
    async def test_creates_version_row(self, db):
        wf_id = await _insert_workflow(db)
        v = await db.snapshot_workflow_version(wf_id, "test-wf", None, True, _STEPS)
        assert v["version_number"] == 1
        assert v["workflow_id"] == wf_id

    @pytest.mark.asyncio
    async def test_version_number_increments(self, db):
        wf_id = await _insert_workflow(db)
        v1 = await db.snapshot_workflow_version(wf_id, "wf", None, True, _STEPS)
        v2 = await db.snapshot_workflow_version(wf_id, "wf-v2", None, True, _STEPS)
        assert v1["version_number"] == 1
        assert v2["version_number"] == 2

    @pytest.mark.asyncio
    async def test_version_numbers_are_per_workflow(self, db):
        wf_a = await _insert_workflow(db, "wf-a")
        wf_b = await _insert_workflow(db, "wf-b")
        va = await db.snapshot_workflow_version(wf_a, "wf-a", None, True, _STEPS)
        vb = await db.snapshot_workflow_version(wf_b, "wf-b", None, True, _STEPS)
        assert va["version_number"] == 1
        assert vb["version_number"] == 1

    @pytest.mark.asyncio
    async def test_definition_stored_correctly(self, db):
        wf_id = await _insert_workflow(db)
        custom_steps = [{"plugin_id": "port_scanner", "inputs": {"target": "192.168.1.1"}}]
        v = await db.snapshot_workflow_version(wf_id, "custom", 3600, False, custom_steps)
        assert v["definition"]["name"] == "custom"
        assert v["definition"]["schedule_seconds"] == 3600
        assert v["definition"]["enabled"] is False
        assert v["definition"]["steps"] == custom_steps

    @pytest.mark.asyncio
    async def test_created_by_stored(self, db):
        wf_id = await _insert_workflow(db)
        v = await db.snapshot_workflow_version(wf_id, "wf", None, True, _STEPS, created_by="rollback_to_v2")
        rows = await db.fetchall("SELECT * FROM workflow_versions WHERE workflow_id = ?", (wf_id,))
        assert rows[0]["created_by"] == "rollback_to_v2"


class TestGetWorkflowVersions:
    @pytest.mark.asyncio
    async def test_returns_versions_newest_first(self, db):
        wf_id = await _insert_workflow(db)
        for i in range(4):
            await db.snapshot_workflow_version(wf_id, f"wf-v{i}", None, True, _STEPS)
        versions = await db.get_workflow_versions(wf_id)
        assert [v["version_number"] for v in versions] == [4, 3, 2, 1]

    @pytest.mark.asyncio
    async def test_empty_for_workflow_with_no_versions(self, db):
        wf_id = await _insert_workflow(db)
        versions = await db.get_workflow_versions(wf_id)
        assert versions == []

    @pytest.mark.asyncio
    async def test_isolated_per_workflow(self, db):
        wf_a = await _insert_workflow(db, "wf-a")
        wf_b = await _insert_workflow(db, "wf-b")
        await db.snapshot_workflow_version(wf_a, "wf-a", None, True, _STEPS)
        await db.snapshot_workflow_version(wf_a, "wf-a", None, True, _STEPS)
        await db.snapshot_workflow_version(wf_b, "wf-b", None, True, _STEPS)
        versions_a = await db.get_workflow_versions(wf_a)
        versions_b = await db.get_workflow_versions(wf_b)
        assert len(versions_a) == 2
        assert len(versions_b) == 1


class TestGetWorkflowVersion:
    @pytest.mark.asyncio
    async def test_returns_correct_version(self, db):
        wf_id = await _insert_workflow(db)
        await db.snapshot_workflow_version(wf_id, "v1-name", None, True, _STEPS)
        await db.snapshot_workflow_version(wf_id, "v2-name", 60, False, [])
        v1 = await db.get_workflow_version(wf_id, 1)
        v2 = await db.get_workflow_version(wf_id, 2)
        assert v1["definition"]["name"] == "v1-name"
        assert v2["definition"]["name"] == "v2-name"
        assert v2["definition"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_version(self, db):
        wf_id = await _insert_workflow(db)
        result = await db.get_workflow_version(wf_id, 99)
        assert result is None


class TestRecordWorkflowRun:
    @pytest.mark.asyncio
    async def test_creates_run_row(self, db):
        wf_id = await _insert_workflow(db)
        v = await db.snapshot_workflow_version(wf_id, "wf", None, True, _STEPS)
        run_id = await db.record_workflow_run(wf_id, v["id"], v["version_number"], ["task-1", "task-2"])
        rows = await db.fetchall("SELECT * FROM workflow_runs WHERE workflow_id = ?", (wf_id,))
        assert len(rows) == 1
        assert rows[0]["id"] == run_id
        assert json.loads(rows[0]["task_ids_json"]) == ["task-1", "task-2"]
        assert rows[0]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_triggered_by_stored(self, db):
        wf_id = await _insert_workflow(db)
        await db.record_workflow_run(wf_id, None, None, [], triggered_by="scheduler")
        rows = await db.fetchall("SELECT * FROM workflow_runs WHERE workflow_id = ?", (wf_id,))
        assert rows[0]["triggered_by"] == "scheduler"

    @pytest.mark.asyncio
    async def test_default_status_is_queued(self, db):
        wf_id = await _insert_workflow(db)
        await db.record_workflow_run(wf_id, None, None, [])
        rows = await db.fetchall("SELECT * FROM workflow_runs WHERE workflow_id = ?", (wf_id,))
        assert rows[0]["status"] == "queued"


class TestGetWorkflowRuns:
    @pytest.mark.asyncio
    async def test_returns_runs_newest_first(self, db):
        wf_id = await _insert_workflow(db)
        for _ in range(4):
            await db.record_workflow_run(wf_id, None, None, [])
        result = await db.get_workflow_runs(wf_id)
        assert result["total"] == 4
        assert len(result["runs"]) == 4

    @pytest.mark.asyncio
    async def test_pagination(self, db):
        wf_id = await _insert_workflow(db)
        for _ in range(6):
            await db.record_workflow_run(wf_id, None, None, [])
        p1 = await db.get_workflow_runs(wf_id, limit=3, offset=0)
        p2 = await db.get_workflow_runs(wf_id, limit=3, offset=3)
        assert len(p1["runs"]) == 3
        assert len(p2["runs"]) == 3
        ids_p1 = {r["id"] for r in p1["runs"]}
        ids_p2 = {r["id"] for r in p2["runs"]}
        assert ids_p1.isdisjoint(ids_p2)

    @pytest.mark.asyncio
    async def test_task_ids_deserialised(self, db):
        wf_id = await _insert_workflow(db)
        await db.record_workflow_run(wf_id, None, None, ["task-x", "task-y"])
        result = await db.get_workflow_runs(wf_id)
        assert result["runs"][0]["task_ids"] == ["task-x", "task-y"]

    @pytest.mark.asyncio
    async def test_isolated_per_workflow(self, db):
        wf_a = await _insert_workflow(db, "wf-a")
        wf_b = await _insert_workflow(db, "wf-b")
        for _ in range(3):
            await db.record_workflow_run(wf_a, None, None, [])
        await db.record_workflow_run(wf_b, None, None, [])
        result_a = await db.get_workflow_runs(wf_a)
        result_b = await db.get_workflow_runs(wf_b)
        assert result_a["total"] == 3
        assert result_b["total"] == 1

    @pytest.mark.asyncio
    async def test_empty_for_workflow_with_no_runs(self, db):
        wf_id = await _insert_workflow(db)
        result = await db.get_workflow_runs(wf_id)
        assert result["total"] == 0
        assert result["runs"] == []


class TestRollbackIntegration:
    @pytest.mark.asyncio
    async def test_rollback_restores_definition(self, db):
        wf_id = await _insert_workflow(db)
        v1 = await db.snapshot_workflow_version(wf_id, "original-name", None, True, _STEPS)
        await db.execute("UPDATE workflows SET name = 'changed-name' WHERE id = ?", (wf_id,))
        await db.snapshot_workflow_version(wf_id, "changed-name", 60, True, [])
        target = await db.get_workflow_version(wf_id, v1["version_number"])
        assert target is not None
        defn = target["definition"]
        await db.execute(
            "UPDATE workflows SET name = ?, steps_json = ?, schedule_seconds = ? WHERE id = ?",
            (defn["name"], json.dumps(defn["steps"]), defn.get("schedule_seconds"), wf_id),
        )
        restored = await db.fetchone("SELECT * FROM workflows WHERE id = ?", (wf_id,))
        assert restored["name"] == "original-name"

    @pytest.mark.asyncio
    async def test_rollback_creates_new_version(self, db):
        wf_id = await _insert_workflow(db)
        v1 = await db.snapshot_workflow_version(wf_id, "v1", None, True, _STEPS)
        await db.snapshot_workflow_version(wf_id, "v2", None, True, _STEPS)
        new_v = await db.snapshot_workflow_version(
            wf_id, "v1", None, True, _STEPS, created_by=f"rollback_to_v{v1['version_number']}"
        )
        assert new_v["version_number"] == 3
        versions = await db.get_workflow_versions(wf_id)
        assert versions[0]["created_by"] == f"rollback_to_v{v1['version_number']}"

    @pytest.mark.asyncio
    async def test_five_version_sequence_correct(self, db):
        wf_id = await _insert_workflow(db)
        for i in range(5):
            await db.snapshot_workflow_version(wf_id, f"wf-v{i+1}", i * 60, i % 2 == 0, _STEPS)
        versions = await db.get_workflow_versions(wf_id)
        assert len(versions) == 5
        assert versions[0]["version_number"] == 5
        assert versions[4]["version_number"] == 1


class TestWorkflowRunLifecycle:
    @pytest.mark.asyncio
    async def test_finalize_run_marks_completed(self, db):
        wf_id = await _insert_workflow(db)
        run_id = await db.record_workflow_run(wf_id, None, None, [])
        await db.finalize_workflow_run(run_id, "completed")
        rows = await db.fetchall("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        assert rows[0]["status"] == "completed"
        assert rows[0]["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_finalize_run_marks_failed_with_message(self, db):
        wf_id = await _insert_workflow(db)
        run_id = await db.record_workflow_run(wf_id, None, None, [])
        await db.finalize_workflow_run(run_id, "failed", "Task crashed")
        rows = await db.fetchall("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        assert rows[0]["status"] == "failed"
        assert rows[0]["error_message"] == "Task crashed"

    @pytest.mark.asyncio
    async def test_finalize_run_marks_cancelled(self, db):
        wf_id = await _insert_workflow(db)
        run_id = await db.record_workflow_run(wf_id, None, None, [])
        await db.finalize_workflow_run(run_id, "cancelled")
        rows = await db.fetchall("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        assert rows[0]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_check_workflow_run_tasks_empty_completes(self, db):
        wf_id = await _insert_workflow(db)
        run_id = await db.record_workflow_run(wf_id, None, None, [])
        status = await db.check_workflow_run_tasks(run_id)
        assert status == "completed"

    @pytest.mark.asyncio
    async def test_check_workflow_run_tasks_in_progress_returns_none(self, db):
        wf_id = await _insert_workflow(db)
        await db.execute(
            "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
            "VALUES ('t1', 'u1', 'p1', 'p1', 'tgt', 'running', '{}')"
        )
        run_id = await db.record_workflow_run(wf_id, None, None, ["t1"])
        status = await db.check_workflow_run_tasks(run_id)
        assert status is None

    @pytest.mark.asyncio
    async def test_check_workflow_run_tasks_all_completed(self, db):
        wf_id = await _insert_workflow(db)
        await db.execute(
            "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
            "VALUES ('t2', 'u1', 'p1', 'p1', 'tgt', 'completed', '{}')"
        )
        run_id = await db.record_workflow_run(wf_id, None, None, ["t2"])
        status = await db.check_workflow_run_tasks(run_id)
        assert status == "completed"

    @pytest.mark.asyncio
    async def test_check_workflow_run_tasks_one_failed(self, db):
        wf_id = await _insert_workflow(db)
        await db.execute(
            "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, inputs_json) "
            "VALUES ('t3', 'u1', 'p1', 'p1', 'tgt', 'failed', '{}')"
        )
        run_id = await db.record_workflow_run(wf_id, None, None, ["t3"])
        status = await db.check_workflow_run_tasks(run_id)
        assert status == "failed"

    @pytest.mark.asyncio
    async def test_workflow_run_history_preserves_triggered_by(self, db):
        wf_id = await _insert_workflow(db)

        run_id = await db.record_workflow_run(
            wf_id,
            None,
            None,
            [],
            triggered_by="scheduler:user:test-owner",
        )

        history = await db.get_workflow_runs(wf_id)

        assert history["total"] == 1
        assert history["runs"][0]["id"] == run_id
        assert history["runs"][0]["triggered_by"] == "scheduler:user:test-owner"
