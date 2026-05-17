"""
Integration tests for task cancellation and cleanup endpoints.

Covered endpoints:
  POST   /api/v1/task/{task_id}/cancel
  DELETE /api/v1/task/{task_id}
  DELETE /api/v1/tasks/bulk
  DELETE /api/v1/tasks/clear

Each test asserts database side-effects, not only HTTP status codes.
File cleanup behaviour is covered using the temporary directories
supplied by the setup_test_environment fixture.
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from backend.secuscan import database as database_module
from backend.secuscan.executor import executor
from backend.secuscan.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_task(client):
    """Start an http_inspector task and return its task_id."""
    with patch(
        "backend.secuscan.executor.TaskExecutor._execute_command",
        return_value=("mock output", 0),
    ):
        payload = {
            "plugin_id": "http_inspector",
            "preset": "quick",
            "inputs": {"url": "http://127.0.0.1:8000"},
            "consent_granted": True,
        }
        resp = client.post("/api/v1/task/start", json=payload)
        assert resp.status_code == 200, resp.text
        return resp.json()["task_id"]


def _wait_for_status(client, task_id, target_statuses, *, timeout=3.0):
    """Poll /status until the task reaches one of *target_statuses*."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/v1/task/{task_id}/status")
        if resp.status_code == 200 and resp.json()["status"] in target_statuses:
            return resp.json()
        time.sleep(0.05)
    return client.get(f"/api/v1/task/{task_id}/status").json()


def _db_row(task_id):
    """Return the raw DB row for a task (None if deleted)."""
    async def _fetch():
        db = await database_module.get_db()
        return await db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return asyncio.run(_fetch())


def _count_table(table, task_id=None):
    """Return the row count for *table*, optionally filtered by task_id."""
    async def _fetch():
        db = await database_module.get_db()
        if task_id:
            return await db.fetchone(
                f"SELECT COUNT(*) AS n FROM {table} WHERE task_id = ?", (task_id,)
            )
        return await db.fetchone(f"SELECT COUNT(*) AS n FROM {table}")
    row = asyncio.run(_fetch())
    return row["n"] if row else 0


def _insert_finding(task_id, plugin_id="http_inspector"):
    """Insert a synthetic finding row linked to *task_id*."""
    import uuid
    async def _do():
        db = await database_module.get_db()
        await db.execute(
            """
            INSERT INTO findings
                (id, task_id, plugin_id, title, category, severity, target, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), task_id, plugin_id,
             "Test Finding", "web", "high", "http://127.0.0.1", "desc"),
        )
    asyncio.run(_do())


def _insert_report(task_id):
    """Insert a synthetic report row linked to *task_id*."""
    import uuid
    async def _do():
        db = await database_module.get_db()
        await db.execute(
            """
            INSERT INTO reports (id, task_id, name, type)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), task_id, "Test Report", "technical"),
        )
    asyncio.run(_do())


def _insert_audit_log(task_id):
    """Insert a synthetic audit_log row linked to *task_id*."""
    async def _do():
        db = await database_module.get_db()
        await db.execute(
            """
            INSERT INTO audit_log (event_type, severity, message, task_id)
            VALUES (?, ?, ?, ?)
            """,
            ("test_event", "info", "test message", task_id),
        )
    asyncio.run(_do())


def _set_task_status(task_id, status):
    """Directly update a task's status in the database."""
    async def _do():
        db = await database_module.get_db()
        await db.execute(
            "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
        )
    asyncio.run(_do())


def _delete_bulk(client, task_ids):
    """Send a DELETE /api/v1/tasks/bulk request with task_ids as query params."""
    params = [("task_ids", tid) for tid in task_ids]
    return client.delete("/api/v1/tasks/bulk", params=params)


# ---------------------------------------------------------------------------
# Cancel tests
# ---------------------------------------------------------------------------

class TestCancelTask:
    def test_cancel_queued_task_returns_cancelled_status(self, test_client):
        """
        A task registered in executor.running_tasks should be cancellable;
        the route must return status='cancelled'.
        """
        task_id = _start_task(test_client)

        # Use an AsyncMock so executor.cancel_task() finds and cancels it
        mock_task = AsyncMock()
        executor.running_tasks[task_id] = mock_task

        try:
            resp = test_client.post(f"/api/v1/task/{task_id}/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_id"] == task_id
            assert data["status"] == "cancelled"
        finally:
            executor.running_tasks.pop(task_id, None)

    def test_cancel_updates_status_in_database(self, test_client):
        """
        After cancellation the tasks table must reflect status='cancelled'.
        """
        task_id = _start_task(test_client)

        mock_task = AsyncMock()
        executor.running_tasks[task_id] = mock_task

        try:
            test_client.post(f"/api/v1/task/{task_id}/cancel")
            row = _db_row(task_id)
            assert row is not None
            assert row["status"] == "cancelled"
        finally:
            executor.running_tasks.pop(task_id, None)

    def test_cancel_nonexistent_task_returns_404(self, test_client):
        """
        Cancelling a task_id that does not exist must return 404.
        """
        resp = test_client.post("/api/v1/task/nonexistent-id-xyz/cancel")
        assert resp.status_code == 404

    def test_cancel_already_completed_task_returns_404(self, test_client):
        """
        A completed task is no longer in running_tasks, so the executor
        returns False and the route must return 404.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})

        resp = test_client.post(f"/api/v1/task/{task_id}/cancel")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Single-task delete tests
# ---------------------------------------------------------------------------

class TestDeleteSingleTask:
    def test_delete_removes_task_row(self, test_client):
        """
        Deleting a completed task must remove its row from the tasks table.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})

        resp = test_client.delete(f"/api/v1/task/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        assert _db_row(task_id) is None

    def test_delete_removes_associated_findings(self, test_client):
        """
        Findings linked to the deleted task must be removed.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})

        # Record baseline (executor may have written its own findings)
        baseline = _count_table("findings", task_id)
        _insert_finding(task_id)
        assert _count_table("findings", task_id) == baseline + 1

        test_client.delete(f"/api/v1/task/{task_id}")
        assert _count_table("findings", task_id) == 0

    def test_delete_removes_associated_reports(self, test_client):
        """
        Report rows linked to the deleted task must be removed.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})

        baseline = _count_table("reports", task_id)
        _insert_report(task_id)
        assert _count_table("reports", task_id) == baseline + 1

        test_client.delete(f"/api/v1/task/{task_id}")
        assert _count_table("reports", task_id) == 0

    def test_delete_removes_associated_audit_log_entries(self, test_client):
        """
        Audit log rows referencing the deleted task must be removed.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})
        _insert_audit_log(task_id)
        assert _count_table("audit_log", task_id) >= 1

        test_client.delete(f"/api/v1/task/{task_id}")
        assert _count_table("audit_log", task_id) == 0

    def test_delete_removes_raw_output_file(self, test_client, setup_test_environment):
        """
        When a raw output file exists on disk, deleting the task must also
        remove the file.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})

        raw_dir = Path(setup_test_environment) / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        dummy_file = raw_dir / f"{task_id}.txt"
        dummy_file.write_text("scan output")

        async def _set_path():
            db = await database_module.get_db()
            await db.execute(
                "UPDATE tasks SET raw_output_path = ? WHERE id = ?",
                (str(dummy_file), task_id),
            )
        asyncio.run(_set_path())

        test_client.delete(f"/api/v1/task/{task_id}")
        assert not dummy_file.exists()

    def test_delete_missing_task_id_still_returns_success(self, test_client):
        """
        Deleting a task_id that does not exist performs a no-op delete and
        returns 200 with deleted=True (idempotent behaviour).
        """
        resp = test_client.delete("/api/v1/task/nonexistent-id-xyz")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_running_task_returns_400(self, test_client):
        """
        Attempting to delete a task that is still running must return 400.
        """
        task_id = _start_task(test_client)
        _wait_for_status(test_client, task_id, {"completed", "failed"})

        # Force status to 'running' so the route guard triggers
        _set_task_status(task_id, "running")

        resp = test_client.delete(f"/api/v1/task/{task_id}")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Bulk delete tests
# ---------------------------------------------------------------------------

class TestBulkDeleteTasks:
    def test_bulk_delete_removes_only_requested_tasks(self, test_client):
        """
        Only the task_ids supplied in the request body should be deleted;
        other tasks must remain in the database.
        """
        id_a = _start_task(test_client)
        id_b = _start_task(test_client)
        id_c = _start_task(test_client)
        for tid in (id_a, id_b, id_c):
            _wait_for_status(test_client, tid, {"completed", "failed"})

        resp = _delete_bulk(test_client, [id_a, id_b])
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["deleted_count"] == 2

        assert _db_row(id_a) is None
        assert _db_row(id_b) is None
        assert _db_row(id_c) is not None

    def test_bulk_delete_removes_associated_findings(self, test_client):
        """
        Findings for all bulk-deleted tasks must be removed.
        """
        id_a = _start_task(test_client)
        id_b = _start_task(test_client)
        for tid in (id_a, id_b):
            _wait_for_status(test_client, tid, {"completed", "failed"})

        baseline_a = _count_table("findings", id_a)
        baseline_b = _count_table("findings", id_b)
        _insert_finding(id_a)
        _insert_finding(id_b)
        assert _count_table("findings", id_a) == baseline_a + 1
        assert _count_table("findings", id_b) == baseline_b + 1

        _delete_bulk(test_client, [id_a, id_b])

        assert _count_table("findings", id_a) == 0
        assert _count_table("findings", id_b) == 0

    def test_bulk_delete_with_running_task_returns_400(self, test_client):
        """
        If any task in the bulk list is currently running, the whole
        request must be rejected with 400.
        """
        id_a = _start_task(test_client)
        id_b = _start_task(test_client)
        _wait_for_status(test_client, id_a, {"completed", "failed"})
        _wait_for_status(test_client, id_b, {"completed", "failed"})

        _set_task_status(id_b, "running")

        resp = _delete_bulk(test_client, [id_a, id_b])
        assert resp.status_code == 400
        assert _db_row(id_a) is not None

    def test_bulk_delete_empty_list_returns_success(self, test_client):
        """
        An empty task_ids list is a valid no-op request.
        """
        resp = _delete_bulk(test_client, [])
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 0


# ---------------------------------------------------------------------------
# Clear-all tests
# ---------------------------------------------------------------------------

class TestClearAllTasks:
    def test_clear_removes_all_tasks(self, test_client):
        """
        After /tasks/clear the tasks table must be empty.
        """
        for _ in range(3):
            tid = _start_task(test_client)
            _wait_for_status(test_client, tid, {"completed", "failed"})

        resp = test_client.delete("/api/v1/tasks/clear")
        assert resp.status_code == 200
        assert resp.json()["cleared"] is True
        assert _count_table("tasks") == 0

    def test_clear_removes_all_findings(self, test_client):
        """
        All findings must be purged when scan history is cleared.
        """
        for _ in range(2):
            tid = _start_task(test_client)
            _wait_for_status(test_client, tid, {"completed", "failed"})
            _insert_finding(tid)

        assert _count_table("findings") >= 2

        test_client.delete("/api/v1/tasks/clear")
        assert _count_table("findings") == 0

    def test_clear_removes_orphaned_raw_files(self, test_client, setup_test_environment):
        """
        Raw output files that live in the data/raw directory must be deleted
        even when they are not referenced by any remaining task row.
        """
        raw_dir = Path(setup_test_environment) / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        orphan = raw_dir / "orphaned_output.txt"
        orphan.write_text("leftover data")

        tid = _start_task(test_client)
        _wait_for_status(test_client, tid, {"completed", "failed"})

        test_client.delete("/api/v1/tasks/clear")
        assert not orphan.exists()

    def test_clear_blocked_while_task_running(self, test_client):
        """
        Clearing history is forbidden if any task has status='running'.
        The request must return 400 and leave the database untouched.
        """
        tid = _start_task(test_client)
        _wait_for_status(test_client, tid, {"completed", "failed"})
        _set_task_status(tid, "running")

        resp = test_client.delete("/api/v1/tasks/clear")
        assert resp.status_code == 400
        assert _count_table("tasks") >= 1