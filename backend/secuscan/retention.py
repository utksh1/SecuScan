"""
Artifact retention — background cleanup for scan tasks and their raw files.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RetentionResult:
    """Returned by run_cleanup() regardless of dry_run flag."""
    dry_run: bool
    tasks_removed: List[str] = field(default_factory=list)
    files_removed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def task_count(self) -> int:
        return len(self.tasks_removed)

    @property
    def file_count(self) -> int:
        return len(self.files_removed)


# ---------------------------------------------------------------------------
# Core cleanup logic
# ---------------------------------------------------------------------------

async def run_cleanup(
    db,
    *,
    max_age_days: int = 0,
    max_task_count: int = 0,
    keep_statuses: Optional[Set[str]] = None,
    dry_run: bool = False,
) -> RetentionResult:
    """
    Identify and (unless dry_run) delete tasks that violate retention policy.

    Parameters
    ----------
    db              : Database instance (from database.get_db())
    max_age_days    : Tasks created more than this many days ago are eligible.
                      0 means this policy is disabled.
    max_task_count  : Keep only the newest N tasks; surplus oldest are eligible.
                      0 means this policy is disabled.
    keep_statuses   : Set of status values that are *never* purged.
                      Defaults to {"running", "queued"} if None.
    dry_run         : When True, return what would be deleted without touching DB or disk.
    """
    if keep_statuses is None:
        keep_statuses = {"running", "queued"}

    result = RetentionResult(dry_run=dry_run)

    if max_age_days == 0 and max_task_count == 0:
        logger.debug("retention: all policies disabled, nothing to do")
        return result

    # Collect candidate task IDs from each active policy
    candidates: Set[str] = set()

    if max_age_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        rows = await db.fetchall(
            "SELECT id FROM tasks WHERE created_at < ? AND status NOT IN ({placeholders})".format(
                placeholders=",".join("?" * len(keep_statuses))
            ),
            (cutoff_str, *keep_statuses),
        )
        for row in rows:
            candidates.add(row["id"])

    if max_task_count > 0:
        # Fetch all tasks ordered newest-first; anything beyond position max_task_count is eligible
        all_tasks = await db.fetchall(
            "SELECT id, status FROM tasks ORDER BY created_at DESC"
        )
        for idx, row in enumerate(all_tasks):
            if idx >= max_task_count and row["status"] not in keep_statuses:
                candidates.add(row["id"])

    if not candidates:
        logger.debug("retention: no tasks eligible for removal")
        return result

    # Resolve raw_output_path for each candidate so we can delete the file
    placeholders = ",".join("?" * len(candidates))
    candidate_list = list(candidates)
    task_rows = await db.fetchall(
        f"SELECT id, raw_output_path FROM tasks WHERE id IN ({placeholders})",
        tuple(candidate_list),
    )

    for row in task_rows:
        task_id = row["id"]
        raw_path = row.get("raw_output_path")
        result.tasks_removed.append(task_id)
        if raw_path:
            result.files_removed.append(raw_path)

    if dry_run:
        logger.info(
            "retention dry-run: would remove %d task(s), %d file(s)",
            result.task_count,
            result.file_count,
        )
        return result

    # --- Real deletion ---
    for task_id in result.tasks_removed:
        try:
            await _delete_task(db, task_id)
        except Exception as exc:  # pragma: no cover
            msg = f"retention: failed to delete task {task_id}: {exc}"
            logger.error(msg)
            result.errors.append(msg)

    for file_path in result.files_removed:
        try:
            p = Path(file_path)
            if p.exists():
                p.unlink()
        except Exception as exc:
            msg = f"retention: failed to delete file {file_path}: {exc}"
            logger.error(msg)
            result.errors.append(msg)

    logger.info(
        "retention: removed %d task(s), %d file(s), %d error(s)",
        result.task_count,
        result.file_count,
        len(result.errors),
    )
    return result


async def _delete_task(db, task_id: str) -> None:
    """Delete a single task and its child rows, then write an audit entry."""
    # Child rows: findings and audit_log have ON DELETE SET NULL (not CASCADE),
    # so we clean them explicitly before removing the task row.
    await db.execute("DELETE FROM findings WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM reports WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM audit_log WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    # Audit the deletion itself (task_id is gone from DB now, store in context)
    await db.log_audit(
        event_type="retention_purge",
        message=f"Task {task_id} removed by retention policy",
        severity="info",
        context={"purged_task_id": task_id},
    )


# ---------------------------------------------------------------------------
# Background cleanup loop
# ---------------------------------------------------------------------------

class RetentionScheduler:
    """
    Runs run_cleanup() on a configurable interval inside the FastAPI lifespan.

    Usage (in main.py lifespan):
        await retention_scheduler.start()
        ...
        await retention_scheduler.stop()
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, *, interval_seconds: int, **cleanup_kwargs) -> None:
        """Start the background loop. Safe to call multiple times."""
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(interval_seconds=interval_seconds, **cleanup_kwargs)
        )
        logger.info("Retention scheduler started (interval=%ds)", interval_seconds)

    async def stop(self) -> None:
        """Cancel the background loop and wait for it to finish."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Retention scheduler stopped")

    @property
    def is_running(self) -> bool:
        return bool(self._task and not self._task.done())

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run_loop(self, *, interval_seconds: int, **cleanup_kwargs) -> None:
        while self._running:
            try:
                await self._tick(**cleanup_kwargs)
            except Exception as exc:
                logger.error("Retention scheduler tick failed: %s", exc)
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break

    async def _tick(self, **cleanup_kwargs) -> None:
        from .database import get_db  # local import avoids circular at module load
        db = await get_db()
        result = await run_cleanup(db, **cleanup_kwargs)
        if result.task_count or result.errors:
            logger.info(
                "Retention tick: removed %d task(s), %d file(s), %d error(s)",
                result.task_count,
                result.file_count,
                len(result.errors),
            )

retention_scheduler = RetentionScheduler()
