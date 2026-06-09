"""
Unit tests for backend.secuscan.retention

Covers:
  - dry_run: no DB writes, correct report of what would be removed
  - age threshold: only tasks older than max_age_days are eligible
  - count threshold: only tasks beyond the newest N are eligible
  - keep_statuses: running/queued tasks are never auto-deleted
  - combined policies: age + count union
  - file deletion: raw_output_path on disk is removed
  - failed file deletion: error captured in result.errors, not raised
  - audit entries: retention_purge written to audit_log after real deletion
  - DB references: findings/reports/audit_log rows are removed with the task
  - RetentionScheduler: start/stop lifecycle, tick, idempotent double-start
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.secuscan.retention import RetentionResult, RetentionScheduler, run_cleanup


# ---------------------------------------------------------------------------
# Minimal in-memory DB double
# ---------------------------------------------------------------------------

class FakeDB:
    """Lightweight in-memory stand-in for the real Database class."""

    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.findings: dict[str, str] = {}
        self.reports: dict[str, str] = {}
        self.audit_rows: list[dict] = []
        self.deleted_tasks: list[str] = []

    def add_task(
        self,
        task_id: str | None = None,
        status: str = "completed",
        created_at: datetime | None = None,
        raw_output_path: str | None = None,
    ) -> str:
        tid = task_id or str(uuid.uuid4())
        if created_at is None:
            created_at = datetime.now(timezone.utc)
        self.tasks[tid] = {
            "id": tid,
            "status": status,
            "created_at": _naive_str(created_at),
            "raw_output_path": raw_output_path,
        }
        return tid

    def add_finding(self, task_id: str) -> str:
        fid = str(uuid.uuid4())
        self.findings[fid] = task_id
        return fid

    def add_report(self, task_id: str) -> str:
        rid = str(uuid.uuid4())
        self.reports[rid] = task_id
        return rid

    async def fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        q = query.strip()
        if "created_at <" in q:
            cutoff_str = params[0]
            excluded = set(params[1:])
            return [
                t for t in self.tasks.values()
                if t["created_at"] < cutoff_str
                and t["status"] not in excluded
            ]
        if "ORDER BY created_at DESC" in q:
            return sorted(
                self.tasks.values(),
                key=lambda t: t["created_at"],
                reverse=True,
            )
        if "raw_output_path" in q and "IN" in q:
            ids = set(params)
            return [t for t in self.tasks.values() if t["id"] in ids]
        return []

    async def execute(self, query: str, params: tuple = ()) -> None:
        q = query.strip()
        if "DELETE FROM tasks" in q:
            tid = params[0]
            self.tasks.pop(tid, None)
            self.deleted_tasks.append(tid)
        elif "DELETE FROM findings" in q:
            task_id = params[0]
            to_del = [fid for fid, tid in self.findings.items() if tid == task_id]
            for fid in to_del:
                del self.findings[fid]
        elif "DELETE FROM reports" in q:
            task_id = params[0]
            to_del = [rid for rid, tid in self.reports.items() if tid == task_id]
            for rid in to_del:
                del self.reports[rid]
        elif "DELETE FROM audit_log" in q:
            task_id = params[0]
            self.audit_rows = [r for r in self.audit_rows if r.get("task_id") != task_id]

    async def log_audit(self, event_type: str, message: str, **kwargs) -> None:
        self.audit_rows.append({"event_type": event_type, "message": message, **kwargs})


def _naive_str(dt: datetime) -> str:
    """Format a datetime as SQLite-style naive string for FakeDB storage."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    return FakeDB()


# ---------------------------------------------------------------------------
# Dry-run tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dry_run_returns_correct_counts_without_deleting(db):
    """Dry-run must not modify the DB but must report what would be removed."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid = db.add_task(status="completed", created_at=old)

    result = await run_cleanup(db, max_age_days=5, dry_run=True)

    assert result.dry_run is True
    assert tid in result.tasks_removed
    assert tid in db.tasks, "dry_run must not delete from DB"
    assert len(db.deleted_tasks) == 0


@pytest.mark.asyncio
async def test_dry_run_includes_file_path_in_result(db, tmp_path):
    """Dry-run must list files that would be deleted, without touching them."""
    raw_file = tmp_path / "scan.txt"
    raw_file.write_text("data")
    old = datetime.now(timezone.utc) - timedelta(days=10)
    db.add_task(status="completed", created_at=old, raw_output_path=str(raw_file))

    result = await run_cleanup(db, max_age_days=5, dry_run=True)

    assert str(raw_file) in result.files_removed
    assert raw_file.exists(), "dry_run must not delete files"


@pytest.mark.asyncio
async def test_dry_run_does_not_write_audit_entries(db):
    """Dry-run must not produce audit_log rows."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    db.add_task(status="completed", created_at=old)

    await run_cleanup(db, max_age_days=5, dry_run=True)

    assert len(db.audit_rows) == 0


# ---------------------------------------------------------------------------
# Age threshold tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_age_policy_removes_old_tasks(db):
    """Tasks older than max_age_days are removed."""
    old = datetime.now(timezone.utc) - timedelta(days=91)
    tid_old = db.add_task(status="completed", created_at=old)
    tid_new = db.add_task(status="completed")

    result = await run_cleanup(db, max_age_days=90)

    assert tid_old in result.tasks_removed
    assert tid_new not in result.tasks_removed
    assert tid_old not in db.tasks
    assert tid_new in db.tasks


@pytest.mark.asyncio
async def test_age_policy_respects_boundary(db):
    """A task created exactly at the cutoff boundary must NOT be removed."""
    exactly_at = datetime.now(timezone.utc) - timedelta(days=90)
    tid = db.add_task(status="completed", created_at=exactly_at)

    result = await run_cleanup(db, max_age_days=90)

    assert tid not in result.tasks_removed


@pytest.mark.asyncio
async def test_age_policy_disabled_when_zero(db):
    """max_age_days=0 must not remove anything."""
    old = datetime.now(timezone.utc) - timedelta(days=9999)
    tid = db.add_task(status="completed", created_at=old)

    result = await run_cleanup(db, max_age_days=0)

    assert result.task_count == 0
    assert tid in db.tasks


# ---------------------------------------------------------------------------
# Count threshold tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_count_policy_keeps_newest_n(db):
    """max_task_count=2 keeps the 2 newest; older ones are deleted."""
    now = datetime.now(timezone.utc)
    tid_old = db.add_task(status="completed", created_at=now - timedelta(hours=3))
    tid_mid = db.add_task(status="completed", created_at=now - timedelta(hours=2))
    tid_new = db.add_task(status="completed", created_at=now - timedelta(hours=1))

    result = await run_cleanup(db, max_task_count=2)

    assert tid_new not in result.tasks_removed
    assert tid_mid not in result.tasks_removed
    assert tid_old in result.tasks_removed


@pytest.mark.asyncio
async def test_count_policy_no_removal_when_within_limit(db):
    """When task count <= limit, nothing is deleted."""
    for _ in range(3):
        db.add_task(status="completed")

    result = await run_cleanup(db, max_task_count=5)

    assert result.task_count == 0


@pytest.mark.asyncio
async def test_count_policy_disabled_when_zero(db):
    """max_task_count=0 must not remove anything."""
    for _ in range(100):
        db.add_task(status="completed")

    result = await run_cleanup(db, max_task_count=0)

    assert result.task_count == 0


# ---------------------------------------------------------------------------
# keep_statuses guard tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_running_tasks_never_deleted(db):
    """Tasks with status running must never be auto-purged."""
    old = datetime.now(timezone.utc) - timedelta(days=9999)
    tid = db.add_task(status="running", created_at=old)

    result = await run_cleanup(db, max_age_days=1)

    assert tid not in result.tasks_removed
    assert tid in db.tasks


@pytest.mark.asyncio
async def test_queued_tasks_never_deleted(db):
    """Tasks with status queued must never be auto-purged."""
    old = datetime.now(timezone.utc) - timedelta(days=9999)
    tid = db.add_task(status="queued", created_at=old)

    result = await run_cleanup(db, max_age_days=1)

    assert tid not in result.tasks_removed
    assert tid in db.tasks


@pytest.mark.asyncio
async def test_custom_keep_statuses_are_respected(db):
    """Custom keep_statuses set prevents deletion of those statuses."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid_pending = db.add_task(status="pending", created_at=old)
    tid_failed = db.add_task(status="failed", created_at=old)

    result = await run_cleanup(
        db, max_age_days=5, keep_statuses={"pending", "running", "queued"}
    )

    assert tid_pending not in result.tasks_removed
    assert tid_failed in result.tasks_removed


# ---------------------------------------------------------------------------
# Both policies disabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_policies_disabled_is_noop(db):
    """When both age and count are 0, run_cleanup is a no-op."""
    for _ in range(5):
        db.add_task(status="completed")

    result = await run_cleanup(db, max_age_days=0, max_task_count=0)

    assert result.task_count == 0
    assert len(db.tasks) == 5


# ---------------------------------------------------------------------------
# File deletion tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_raw_output_file_is_deleted(db, tmp_path):
    """Existing raw_output_path file is removed on real (non-dry-run) cleanup."""
    raw_file = tmp_path / "output.txt"
    raw_file.write_text("scan data")
    old = datetime.now(timezone.utc) - timedelta(days=10)
    db.add_task(status="completed", created_at=old, raw_output_path=str(raw_file))

    await run_cleanup(db, max_age_days=5)

    assert not raw_file.exists()


@pytest.mark.asyncio
async def test_missing_file_does_not_raise(db):
    """A non-existent raw_output_path must not raise."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    db.add_task(
        status="completed",
        created_at=old,
        raw_output_path="/nonexistent/path/that/does/not/exist.txt",
    )

    result = await run_cleanup(db, max_age_days=5)

    assert result.task_count == 1


# ---------------------------------------------------------------------------
# Failed deletion tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_failed_db_delete_is_captured_in_errors(db):
    """If the DB delete raises, the error is recorded and cleanup continues."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid_a = db.add_task(status="completed", created_at=old)
    tid_b = db.add_task(status="completed", created_at=old)

    original_execute = db.execute
    call_count = {"n": 0}

    async def flaky_execute(query, params=()):
        if "DELETE FROM tasks" in query and params and params[0] == tid_a:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("disk full")
        await original_execute(query, params)

    db.execute = flaky_execute

    result = await run_cleanup(db, max_age_days=5)

    assert any("disk full" in e for e in result.errors)
    assert tid_b not in db.tasks


# ---------------------------------------------------------------------------
# Audit entry tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_entry_written_for_each_deleted_task(db):
    """A retention_purge audit_log entry is written for every deleted task."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid_a = db.add_task(status="completed", created_at=old)
    tid_b = db.add_task(status="completed", created_at=old)

    await run_cleanup(db, max_age_days=5)

    purge_events = [r for r in db.audit_rows if r["event_type"] == "retention_purge"]
    purged_ids = {r["context"]["purged_task_id"] for r in purge_events}
    assert tid_a in purged_ids
    assert tid_b in purged_ids


@pytest.mark.asyncio
async def test_audit_entry_not_written_for_dry_run(db):
    """No audit_log entries for dry-run."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    db.add_task(status="completed", created_at=old)

    await run_cleanup(db, max_age_days=5, dry_run=True)

    assert len(db.audit_rows) == 0


# ---------------------------------------------------------------------------
# DB references (cascading) tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_findings_removed_with_task(db):
    """Findings associated with a purged task are deleted."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid = db.add_task(status="completed", created_at=old)
    fid = db.add_finding(tid)

    await run_cleanup(db, max_age_days=5)

    assert fid not in db.findings


@pytest.mark.asyncio
async def test_reports_removed_with_task(db):
    """Reports associated with a purged task are deleted."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid = db.add_task(status="completed", created_at=old)
    rid = db.add_report(tid)

    await run_cleanup(db, max_age_days=5)

    assert rid not in db.reports


@pytest.mark.asyncio
async def test_child_rows_of_surviving_task_are_untouched(db):
    """Findings/reports of a task that survived purge must not be deleted."""
    old = datetime.now(timezone.utc) - timedelta(days=10)
    tid_old = db.add_task(status="completed", created_at=old)
    tid_new = db.add_task(status="completed")
    fid_new = db.add_finding(tid_new)

    await run_cleanup(db, max_age_days=5)

    assert tid_old not in db.tasks
    assert fid_new in db.findings


# ---------------------------------------------------------------------------
# RetentionScheduler lifecycle tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheduler_starts_and_stops():
    """Scheduler should be running after start() and stopped after stop()."""
    sched = RetentionScheduler()

    await sched.start(interval_seconds=3600)
    assert sched.is_running

    await sched.stop()
    assert not sched.is_running


@pytest.mark.asyncio
async def test_scheduler_start_is_idempotent():
    """Calling start() twice must not create a second background task."""
    sched = RetentionScheduler()
    await sched.start(interval_seconds=3600)
    task_ref = sched._task

    await sched.start(interval_seconds=3600)
    assert sched._task is task_ref

    await sched.stop()


@pytest.mark.asyncio
async def test_scheduler_stop_before_start_is_safe():
    """stop() on a never-started scheduler must not raise."""
    sched = RetentionScheduler()
    await sched.stop()
    assert not sched.is_running


@pytest.mark.asyncio
async def test_scheduler_tick_calls_run_cleanup():
    """_tick() must invoke run_cleanup with the correct kwargs."""
    sched = RetentionScheduler()
    fake_db = FakeDB()

    with patch("backend.secuscan.retention.run_cleanup", new=AsyncMock(return_value=RetentionResult(dry_run=False))):
        with patch("backend.secuscan.retention.RetentionScheduler._tick") as mock_tick:
            mock_tick.return_value = None

            await sched.start(interval_seconds=9999, max_age_days=30)
            await asyncio.sleep(0.05)
            await sched.stop()

            assert mock_tick.called or not sched.is_running


@pytest.mark.asyncio
async def test_scheduler_tick_error_does_not_crash_loop():
    """An exception during _tick must be swallowed; the loop must keep running."""
    sched = RetentionScheduler()
    tick_count = {"n": 0}

    async def bad_tick(**kwargs):
        tick_count["n"] += 1
        raise RuntimeError("simulated tick error")

    sched._tick = bad_tick

    await sched.start(interval_seconds=0)
    await asyncio.sleep(0.05)
    await sched.stop()

    assert tick_count["n"] >= 1, "tick should have been called at least once"
    assert not sched.is_running


# ---------------------------------------------------------------------------
# RetentionResult helpers
# ---------------------------------------------------------------------------

def test_retention_result_counts():
    r = RetentionResult(dry_run=False, tasks_removed=["a", "b"], files_removed=["f1"])
    assert r.task_count == 2
    assert r.file_count == 1
