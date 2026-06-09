"""Workflow automation and scheduling."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .config import settings
from .database import get_db
from .executor import executor

from .ratelimit import concurrent_limiter
from .request_context import get_request_id, set_request_id
from .utils.scheduler import should_run_cron_workflow


from .execution_context import normalize_execution_context
from .platform_resources import get_target_policy

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]


class WorkflowScheduler:
    def __init__(self, clock: Optional[Clock] = None):
        self._task: asyncio.Task | None = None
        self._running = False
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        return self._clock()

    async def start(self):
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Workflow scheduler started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Workflow scheduler stopped")

    async def _run_loop(self):
        while self._running:
            try:
                await self.tick()
            except Exception as exc:
                logger.error("Workflow scheduler tick failed: %s", exc)
            await asyncio.sleep(5)

    async def tick(self):
        db = await get_db()
        rows = await db.fetchall(
            """
            SELECT id, name, schedule_seconds, cron_expression, timezone,
                   blackout_start, blackout_end, last_run_at, steps_json
            FROM workflows
            WHERE enabled = 1
              AND (
                    (schedule_seconds IS NOT NULL AND schedule_seconds > 0)
                 OR (cron_expression IS NOT NULL AND TRIM(cron_expression) != '')
              )
            """
        )
        now = self._now()
        for row in rows:
            cron_expr = (row.get("cron_expression") or "").strip()
            if cron_expr:
                if not should_run_cron_workflow(
                    now,
                    row.get("last_run_at"),
                    cron_expr,
                    row.get("timezone") or "UTC",
                    row.get("blackout_start"),
                    row.get("blackout_end"),
                ):
                    continue
            elif not self._should_run_interval(
                now, row.get("last_run_at"), int(row["schedule_seconds"])
            ):
                continue

            await self._run_workflow(
                row["id"], json.loads(row.get("steps_json") or "[]")
            )
            await db.execute(
                "UPDATE workflows SET last_run_at = datetime('now') WHERE id = ?",
                (row["id"],),
            )

    def _should_run_interval(
        self, now: datetime, last_run_at: str | None, schedule_seconds: int
    ) -> bool:
        if not last_run_at:
            return True
        last = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (now - last).total_seconds()
        return elapsed >= schedule_seconds

    async def _run_workflow(self, workflow_id: str, steps: List[Dict[str, Any]]):
        logger.info("Running workflow %s with %d step(s)", workflow_id, len(steps))
        db = await get_db()
        for step in steps:
            plugin_id = step.get("plugin_id")
            inputs = step.get("inputs") or {}
            if not plugin_id:
                continue

            request_id = get_request_id()
            execution_context = normalize_execution_context(
                step.get("execution_context") or {}
            )
            target_policy = await get_target_policy(
                db, "default", execution_context.get("target_policy_id")
            )
            safe_mode = bool(
                settings.safe_mode_default
                and not (target_policy and target_policy.get("allow_public_targets"))
            )
            effective_inputs = dict(inputs)
            effective_inputs.pop("safe_mode", None)
            effective_inputs["safe_mode"] = safe_mode

            task_id = await executor.create_task(
                plugin_id,
                effective_inputs,
                safe_mode=safe_mode,
                preset=step.get("preset"),
                execution_context=execution_context,
                consent_granted=True,
            )

            can_acquire, error_msg = await concurrent_limiter.acquire(task_id)
            if not can_acquire:
                await executor.mark_task_failed(
                    task_id,
                    reason=error_msg
                    or "Concurrency limit reached; task was not started",
                )
                logger.warning(
                    "Workflow %s step skipped for task %s: %s",
                    workflow_id,
                    task_id,
                    error_msg,
                )
                continue

            async def run_task(task_id: str) -> None:
                set_request_id(request_id)
                await executor.execute_task(task_id)

            asyncio.create_task(run_task(task_id))


scheduler = WorkflowScheduler()
