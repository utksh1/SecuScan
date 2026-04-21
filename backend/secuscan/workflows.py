"""Workflow automation and scheduling."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from .database import get_db
from .executor import executor

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

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
            SELECT id, name, schedule_seconds, last_run_at, steps_json
            FROM workflows
            WHERE enabled = 1 AND schedule_seconds IS NOT NULL AND schedule_seconds > 0
            """
        )

        now = datetime.now(timezone.utc)
        for row in rows:
            if not self._should_run(now, row.get("last_run_at"), int(row["schedule_seconds"])):
                continue
            await self._run_workflow(row["id"], json.loads(row.get("steps_json") or "[]"))
            await db.execute(
                "UPDATE workflows SET last_run_at = datetime('now') WHERE id = ?",
                (row["id"],),
            )

    def _should_run(self, now: datetime, last_run_at: str | None, schedule_seconds: int) -> bool:
        if not last_run_at:
            return True
        last = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
        elapsed = (now - last).total_seconds()
        return elapsed >= schedule_seconds

    async def _run_workflow(self, workflow_id: str, steps: List[Dict[str, Any]]):
        logger.info("Running workflow %s with %d step(s)", workflow_id, len(steps))
        for step in steps:
            plugin_id = step.get("plugin_id")
            inputs = step.get("inputs") or {}
            if not plugin_id:
                continue
            task_id = await executor.create_task(plugin_id, inputs, preset=step.get("preset"), consent_granted=True)
            asyncio.create_task(executor.execute_task(task_id))


scheduler = WorkflowScheduler()
