"""
Unit tests for database workflow version methods.
"""
import asyncio
import uuid
from backend.secuscan.database import Database


def run(coro):
    return asyncio.run(coro)


def make_db():
    return Database(":memory:")


class TestSnapshotWorkflowVersion:
    def test_first_snapshot_has_version_1(self):
        db = make_db()
        run(db.connect())
        try:
            v = run(
                db.snapshot_workflow_version(
                    "wf-test-1", "Test WF", 60, True, [{"plugin_id": "nmap"}]
                )
            )
            assert v["version_number"] == 1
            assert v["workflow_id"] == "wf-test-1"
            assert v["created_by"] == "system"
        finally:
            run(db.disconnect())

    def test_subsequent_snapshots_increment_version(self):
        db = make_db()
        run(db.connect())
        try:
            v1 = run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            v2 = run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            assert v2["version_number"] == v1["version_number"] + 1
        finally:
            run(db.disconnect())

    def test_snapshot_stores_definition(self):
        db = make_db()
        run(db.connect())
        try:
            steps = [{"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}}]
            v = run(db.snapshot_workflow_version("wf-1", "My WF", 120, False, steps))
            assert v["definition"]["name"] == "My WF"
            assert v["definition"]["schedule_seconds"] == 120
            assert v["definition"]["enabled"] is False
            assert v["definition"]["steps"] == steps
        finally:
            run(db.disconnect())

    def test_snapshots_across_workflows_independent(self):
        db = make_db()
        run(db.connect())
        try:
            v_a1 = run(db.snapshot_workflow_version("wf-A", "A", 60, True, []))
            v_b1 = run(db.snapshot_workflow_version("wf-B", "B", 60, True, []))
            v_a2 = run(db.snapshot_workflow_version("wf-A", "A", 60, True, []))
            assert v_a1["version_number"] == 1
            assert v_b1["version_number"] == 1
            assert v_a2["version_number"] == 2
        finally:
            run(db.disconnect())


class TestGetWorkflowVersions:
    def test_returns_all_versions_newest_first(self):
        db = make_db()
        run(db.connect())
        try:
            run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            versions = run(db.get_workflow_versions("wf-1"))
            assert len(versions) == 3
            assert versions[0]["version_number"] == 3
            assert versions[1]["version_number"] == 2
            assert versions[2]["version_number"] == 1
        finally:
            run(db.disconnect())

    def test_returns_empty_for_unknown_workflow(self):
        db = make_db()
        run(db.connect())
        try:
            versions = run(db.get_workflow_versions("does-not-exist"))
            assert versions == []
        finally:
            run(db.disconnect())


class TestGetWorkflowVersion:
    def test_returns_specific_version(self):
        db = make_db()
        run(db.connect())
        try:
            created = run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            found = run(db.get_workflow_version("wf-1", created["version_number"]))
            assert found is not None
            assert found["id"] == created["id"]
        finally:
            run(db.disconnect())

    def test_returns_none_for_missing_workflow(self):
        db = make_db()
        run(db.connect())
        try:
            result = run(db.get_workflow_version("wf-does-not-exist", 99))
            assert result is None
        finally:
            run(db.disconnect())

    def test_returns_none_for_missing_version_number(self):
        db = make_db()
        run(db.connect())
        try:
            run(db.snapshot_workflow_version("wf-1", "WF", 60, True, []))
            result = run(db.get_workflow_version("wf-1", 99))
            assert result is None
        finally:
            run(db.disconnect())


class TestRecordWorkflowRun:
    def test_inserts_queued_run(self):
        db = make_db()
        run(db.connect())
        try:
            run_id = run(
                db.record_workflow_run("wf-1", None, 1, ["t1", "t2"], "manual")
            )
            assert run_id is not None
            run_row = run(
                db.fetchone(
                    "SELECT status, triggered_by FROM workflow_runs WHERE id = ?",
                    (run_id,),
                )
            )
            assert run_row["status"] == "queued"
            assert run_row["triggered_by"] == "manual"
        finally:
            run(db.disconnect())

    def test_inserts_empty_task_list(self):
        db = make_db()
        run(db.connect())
        try:
            run_id = run(db.record_workflow_run("wf-1", None, 1, [], "scheduler"))
            raw = run(
                db.fetchone(
                    "SELECT task_ids_json FROM workflow_runs WHERE id = ?", (run_id,)
                )
            )
            assert raw["task_ids_json"] == "[]"
        finally:
            run(db.disconnect())


class TestFinalizeWorkflowRun:
    def test_sets_status_and_timestamp(self):
        db = make_db()
        run(db.connect())
        try:
            run_id = run(db.record_workflow_run("wf-1", None, 1, [], "manual"))
            run(db.finalize_workflow_run(run_id, "completed"))
            run_row = run(
                db.fetchone(
                    "SELECT status, completed_at FROM workflow_runs WHERE id = ?",
                    (run_id,),
                )
            )
            assert run_row["status"] == "completed"
            assert run_row["completed_at"] is not None
        finally:
            run(db.disconnect())

    def test_finalize_with_error_message(self):
        db = make_db()
        run(db.connect())
        try:
            run_id = run(db.record_workflow_run("wf-1", None, 1, [], "manual"))
            run(
                db.finalize_workflow_run(
                    run_id, "failed", error_message="Plugin not found"
                )
            )
            run_row = run(
                db.fetchone(
                    "SELECT status, error_message FROM workflow_runs WHERE id = ?",
                    (run_id,),
                )
            )
            assert run_row["status"] == "failed"
            assert run_row["error_message"] == "Plugin not found"
        finally:
            run(db.disconnect())


class TestCheckWorkflowRunTasks:
    def test_empty_run_returns_completed(self):
        db = make_db()
        run(db.connect())
        try:
            run_id = run(db.record_workflow_run("wf-1", None, 1, [], "manual"))
            result = run(db.check_workflow_run_tasks(run_id))
            assert result == "completed"
        finally:
            run(db.disconnect())

    def test_all_tasks_completed_returns_completed(self):
        db = make_db()
        run(db.connect())
        try:
            task_ids = []
            for _ in range(3):
                tid = uuid.uuid4().hex
                run(
                    db.execute(
                        "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, execution_context_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (tid, "nmap", "nmap", "127.0.0.1", "{}", "{}", "completed"),
                    )
                )
                task_ids.append(tid)
            run_id = run(db.record_workflow_run("wf-1", None, 1, task_ids, "manual"))
            result = run(db.check_workflow_run_tasks(run_id))
            assert result == "completed"
        finally:
            run(db.disconnect())

    def test_still_running_returns_none(self):
        db = make_db()
        run(db.connect())
        try:
            tid = uuid.uuid4().hex
            run(
                db.execute(
                    "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, execution_context_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (tid, "nmap", "nmap", "127.0.0.1", "{}", "{}", "running"),
                )
            )
            run_id = run(db.record_workflow_run("wf-1", None, 1, [tid], "manual"))
            result = run(db.check_workflow_run_tasks(run_id))
            assert result is None
        finally:
            run(db.disconnect())

    def test_any_task_failed_returns_failed(self):
        db = make_db()
        run(db.connect())
        try:
            tid = uuid.uuid4().hex
            run(
                db.execute(
                    "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, execution_context_json, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (tid, "nmap", "nmap", "127.0.0.1", "{}", "{}", "failed"),
                )
            )
            run_id = run(db.record_workflow_run("wf-1", None, 1, [tid], "manual"))
            result = run(db.check_workflow_run_tasks(run_id))
            assert result == "failed"
        finally:
            run(db.disconnect())

    def test_missing_run_id_returns_none(self):
        db = make_db()
        run(db.connect())
        try:
            result = run(db.check_workflow_run_tasks("no-such-run"))
            assert result is None
        finally:
            run(db.disconnect())


class TestGetWorkflowRuns:
    def test_returns_paginated_run_history(self):
        db = make_db()
        run(db.connect())
        try:
            for _ in range(3):
                run_id = run(db.record_workflow_run("wf-1", None, 1, [], "manual"))
                run(db.finalize_workflow_run(run_id, "completed"))
            result = run(db.get_workflow_runs("wf-1", limit=10))
            assert result["total"] == 3
            assert len(result["runs"]) == 3
        finally:
            run(db.disconnect())

    def test_respects_limit_and_offset(self):
        db = make_db()
        run(db.connect())
        try:
            for _ in range(3):
                run_id = run(db.record_workflow_run("wf-1", None, 1, [], "manual"))
                run(db.finalize_workflow_run(run_id, "completed"))
            result = run(db.get_workflow_runs("wf-1", limit=1, offset=1))
            assert result["total"] == 3
            assert len(result["runs"]) == 1
        finally:
            run(db.disconnect())
