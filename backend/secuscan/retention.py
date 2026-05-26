"""
Artifact retention manager for SecuScan.

Purges terminal-status tasks (completed / failed / cancelled) and their
on-disk artifacts (raw output files, report files) according to operator-
configured age and count thresholds.  Every deletion is recorded in the
audit_log.  A dry-run mode reports what *would* be removed without touching
anything.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Sequence

from .config import settings
from .database import get_db

logger = logging.getLogger(__name__)

# Statuses that are safe to purge — never touch queued / running.
_PURGEABLE_STATUSES = {"completed", "failed", "cancelled"}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RetentionResult:
    """Summary returned by a single purge run."""
    dry_run: bool
    tasks_removed: int = 0
    files_removed: int = 0
    file_errors: List[str] = field(default_factory=list)
    task_ids_removed: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        prefix = "[DRY-RUN] " if self.dry_run else ""
        return (
            f"{prefix}tasks={self.tasks_removed} "
            f"files={self.files_removed} "
            f"file_errors={len(self.file_errors)}"
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ArtifactRetentionManager:
    """
    Evaluate and execute the configured retention policy.

    Policy is applied in this order:
      1. Age threshold  — drop tasks older than ``max_age_days``
      2. Count threshold — if more than ``max_count`` purgeable tasks remain,
                           drop the oldest ones until the limit is met.

    Both thresholds are independent; either can be disabled by setting the
    value to ``0`` / ``None``.

    Parameters
    ----------
    max_age_days:
        Tasks whose ``created_at`` is older than this many days are eligible
        for removal.  ``0`` or ``None`` disables age-based purging.
    max_count:
        Maximum number of purgeable tasks to retain after cleanup.  ``0`` or
        ``None`` disables count-based purging.
    keep_statuses:
        Which terminal statuses to *keep*.  Tasks whose status is NOT in this
        set (and IS purgeable) will be included in the purge candidates.
        Defaults to all three terminal statuses being kept unless the age /
        count thresholds force removal.
    """

    def __init__(
        self,
        max_age_days: Optional[int] = None,
        max_count: Optional[int] = None,
        keep_statuses: Optional[Sequence[str]] = None,
    ):
        self.max_age_days = max_age_days or 0
        self.max_count = max_count or 0

        # Resolve which statuses are eligible for purge.
        # keep_statuses restricts what we preserve; anything purgeable that
        # is NOT in keep_statuses becomes a candidate immediately (before
        # age/count filtering adds more).
        if keep_statuses is not None:
            requested = {s.lower() for s in keep_statuses}
            # Only honour statuses that are actually purgeable.
            self._keep_statuses = _PURGEABLE_STATUSES & requested
        else:
            self._keep_statuses = set(_PURGEABLE_STATUSES)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def purge(self, dry_run: bool = False) -> RetentionResult:
        """
        Run the retention policy and return a :class:`RetentionResult`.

        In dry-run mode nothing is written to the database or filesystem;
        audit entries are **not** created either (there is nothing to record).
        """
        result = RetentionResult(dry_run=dry_run)

        db = await get_db()

        # Fetch all purgeable tasks ordered oldest-first.
        rows = await db.fetchall(
            """
            SELECT id, created_at, raw_output_path, status
            FROM   tasks
            WHERE  status IN ('completed', 'failed', 'cancelled')
            ORDER  BY created_at ASC
            """
        )

        if not rows:
            return result

        candidates: List[dict] = []

        # --- Age threshold ---
        if self.max_age_days > 0:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self.max_age_days)
            for row in rows:
                created = _parse_ts(row["created_at"])
                if created is not None and created < cutoff:
                    candidates.append(row)

        # --- Count threshold ---
        if self.max_count > 0:
            # Work on rows that are NOT already marked for removal.
            candidate_ids = {r["id"] for r in candidates}
            remaining = [r for r in rows if r["id"] not in candidate_ids]
            excess = len(remaining) - self.max_count
            if excess > 0:
                # remaining is already sorted oldest-first, so we take the
                # leading `excess` entries.
                candidates.extend(remaining[:excess])

        if not candidates:
            return result

        # Deduplicate while preserving order.
        seen: set = set()
        deduped = []
        for r in candidates:
            if r["id"] not in seen:
                seen.add(r["id"])
                deduped.append(r)
        candidates = deduped

        if dry_run:
            result.tasks_removed = len(candidates)
            result.task_ids_removed = [r["id"] for r in candidates]
            # Estimate file count (raw + report file_path).
            for row in candidates:
                if row.get("raw_output_path"):
                    result.files_removed += 1
            report_rows = await db.fetchall(
                "SELECT file_path FROM reports WHERE task_id IN ({})".format(
                    ",".join("?" * len(candidates))
                ),
                tuple(r["id"] for r in candidates),
            )
            result.files_removed += sum(1 for rr in report_rows if rr.get("file_path"))
            return result

        # --- Real purge ---
        task_ids = [r["id"] for r in candidates]
        placeholders = ",".join("?" * len(task_ids))

        # Collect report file paths before deleting rows.
        report_rows = await db.fetchall(
            f"SELECT file_path FROM reports WHERE task_id IN ({placeholders})",
            tuple(task_ids),
        )

        # Delete DB rows (cascade order: children first).
        await db.execute(
            f"DELETE FROM findings   WHERE task_id IN ({placeholders})",
            tuple(task_ids),
        )
        await db.execute(
            f"DELETE FROM reports    WHERE task_id IN ({placeholders})",
            tuple(task_ids),
        )
        await db.execute(
            f"DELETE FROM audit_log  WHERE task_id IN ({placeholders})",
            tuple(task_ids),
        )
        await db.execute(
            f"DELETE FROM tasks      WHERE id       IN ({placeholders})",
            tuple(task_ids),
        )

        result.tasks_removed = len(task_ids)
        result.task_ids_removed = task_ids

        # Delete on-disk files.
        file_paths: List[Optional[str]] = [r.get("raw_output_path") for r in candidates]
        file_paths += [rr.get("file_path") for rr in report_rows]

        for fp in file_paths:
            if not fp:
                continue
            err = _delete_file(fp)
            if err:
                result.file_errors.append(err)
            else:
                result.files_removed += 1

        # Audit entry — single record summarising the batch.
        await db.log_audit(
            event_type="retention_purge",
            severity="info",
            message=(
                f"Retention purge removed {result.tasks_removed} task(s) "
                f"and {result.files_removed} file(s). "
                f"file_errors={len(result.file_errors)}"
            ),
            context={
                "task_ids": task_ids,
                "file_errors": result.file_errors,
                "max_age_days": self.max_age_days,
                "max_count": self.max_count,
            },
        )

        logger.info("Retention purge complete: %s", result)
        return result

    # ------------------------------------------------------------------
    # Background loop (used by main.py lifespan)
    # ------------------------------------------------------------------

    async def run_loop(self, interval_seconds: int) -> None:
        """
        Run :meth:`purge` in a background loop every *interval_seconds*.

        Designed to be spawned as an ``asyncio.Task`` inside the FastAPI
        lifespan context so it is cancelled cleanly on shutdown.
        """
        logger.info(
            "Artifact retention loop started (interval=%ds, max_age_days=%d, max_count=%d)",
            interval_seconds,
            self.max_age_days,
            self.max_count,
        )
        while True:
            try:
                result = await self.purge(dry_run=False)
                if result.tasks_removed:
                    logger.info("Retention: %s", result)
            except Exception as exc:  # pragma: no cover — unexpected errors
                logger.error("Retention loop error: %s", exc, exc_info=True)
            await asyncio.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# Module-level singleton (initialised in main.py)
# ---------------------------------------------------------------------------

_manager: Optional[ArtifactRetentionManager] = None


def init_retention() -> ArtifactRetentionManager:
    """Create and cache the global :class:`ArtifactRetentionManager`."""
    global _manager
    _manager = ArtifactRetentionManager(
        max_age_days=settings.artifact_max_age_days,
        max_count=settings.artifact_max_count,
        keep_statuses=settings.artifact_keep_statuses,
    )
    return _manager


def get_retention_manager() -> ArtifactRetentionManager:
    if _manager is None:
        raise RuntimeError("Retention manager not initialised — call init_retention() first.")
    return _manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(value: str | datetime | None) -> Optional[datetime]:
    """Parse an ISO-8601 string (or pass through a datetime) to an aware UTC dt."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    logger.warning("Could not parse timestamp %r — skipping age check", value)
    return None


def _delete_file(path_str: str) -> Optional[str]:
    """
    Delete a file from disk.  Returns ``None`` on success, or an error
    message string if deletion failed (so callers can record it without
    raising).
    """
    try:
        p = Path(path_str)
        if p.exists():
            p.unlink()
        return None
    except OSError as exc:
        msg = f"Failed to delete {path_str!r}: {exc}"
        logger.error(msg)
        return msg