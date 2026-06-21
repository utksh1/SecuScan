"""Workflow automation and scheduling."""
from __future__ import annotations
from .request_context import get_request_id, set_request_id
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from .database import get_db
from .config import settings
from .ratelimit import workflow_rate_limiter, rate_limiter, concurrent_limiter
from .executor import executor
from .execution_context import normalize_execution_context
from .platform_resources import get_target_policy
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
            SELECT id, name, owner_id, schedule_seconds, last_run_at, steps_json
            FROM workflows
            WHERE enabled = 1 AND schedule_seconds IS NOT NULL AND schedule_seconds > 0
            """
        )
        now = datetime.now(timezone.utc)
        for row in rows:
            if not self._should_run(now, row.get("last_run_at"), int(row["schedule_seconds"])):
                continue

            wf_rate_ok, wf_rate_msg = await workflow_rate_limiter.check_workflow_rate_limit(
                row["id"], settings.workflow_min_interval_seconds
            )
            if not wf_rate_ok:
                logger.warning("Workflow %s skipped by rate limiter: %s", row["id"], wf_rate_msg)
                continue

            owner_id = row["owner_id"]
            await self._run_workflow(row["id"], json.loads(row.get("steps_json") or "[]"), owner_id=owner_id)
            await db.execute(
                "UPDATE workflows SET last_run_at = datetime('now') WHERE id = ?",
                (row["id"],),
            )
    def _should_run(self, now: datetime, last_run_at: str | None, schedule_seconds: int) -> bool:
        if not last_run_at:
            return True
        last = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
        # SQLite's datetime('now') produces "2026-05-25 08:02:28" — no Z and
        # no +00:00 suffix — so fromisoformat() returns a naive datetime.
        # Subtracting a naive datetime from an aware one raises TypeError.
        # Treat any naive timestamp from the DB as UTC.
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (now - last).total_seconds()
        return elapsed >= schedule_seconds
    async def _run_workflow(self, workflow_id: str, steps: List[Dict[str, Any]], owner_id: str = "default"):
        logger.info("Running workflow %s with %d step(s)", workflow_id, len(steps))
        db = await get_db()

        # Retrieve the latest version snapshot or create one if it doesn't exist
        active_version = await db.fetchone(
            "SELECT id, version_number FROM workflow_versions "
            "WHERE workflow_id = ? ORDER BY version_number DESC LIMIT 1",
            (workflow_id,),
        )
        if not active_version:
            # Fetch workflow details from the database
            row = await db.fetchone(
                "SELECT name, schedule_seconds, enabled, steps_json FROM workflows WHERE id = ?",
                (workflow_id,),
            )
            if row:
                name = row["name"]
                schedule_seconds = row["schedule_seconds"]
                enabled = bool(row["enabled"])
                steps_from_db = json.loads(row["steps_json"] or "[]")
            else:
                name = f"Workflow {workflow_id}"
                schedule_seconds = None
                enabled = True
                steps_from_db = steps

            active_version = await db.snapshot_workflow_version(
                workflow_id=workflow_id,
                name=name,
                schedule_seconds=schedule_seconds,
                enabled=enabled,
                steps=steps_from_db,
                created_by="system",
            )

        version_id = active_version["id"]
        version_number = active_version["version_number"]
        created_task_ids: List[str] = []

        from .plugins import get_plugin_manager
        plugin_manager = get_plugin_manager()

        for step in steps:
            plugin_id = step.get("plugin_id")
            inputs = step.get("inputs") or {}
            if not plugin_id:
                continue

            plugin = plugin_manager.get_plugin(plugin_id)
            if not plugin:
                logger.warning("Workflow %s: plugin %s not found, skipping step", workflow_id, plugin_id)
                continue

            # Pre-create the task in queued status.
            # Validation and concurrency limits will be checked at execution time.
            execution_context = normalize_execution_context(step.get("execution_context") or {})
            target_policy = await get_target_policy(db, owner_id, execution_context.get("target_policy_id"))
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
                owner_id=owner_id,
            )
            created_task_ids.append(task_id)

        run_id = await db.record_workflow_run(
            workflow_id=workflow_id,
            version_id=version_id,
            version_number=version_number,
            task_ids=created_task_ids,
            triggered_by="scheduler",
        )
        seq_coro = _execute_workflow_sequentially(
            workflow_id=workflow_id,
            run_id=run_id,
            steps=steps,
            created_task_ids=created_task_ids,
            owner_id=owner_id,
        )
        import os
        if os.environ.get("PYTEST_CURRENT_TEST"):
            await seq_coro
        else:
            asyncio.create_task(seq_coro)
        asyncio.create_task(_finalize_workflow_run(run_id))


async def _cancel_remaining_tasks(db, task_ids: List[str]):
    for tid in task_ids:
        await db.execute(
            "UPDATE tasks SET status = ?, completed_at = datetime('now'), error_message = ? WHERE id = ?",
            ("cancelled", "Cancelled due to upstream step failure or concurrency limit", tid),
        )


async def _execute_workflow_sequentially(
    workflow_id: str,
    run_id: str,
    steps: List[Dict[str, Any]],
    created_task_ids: List[str],
    owner_id: str,
):
    logger.info("Executing workflow %s sequentially (%d tasks)", workflow_id, len(created_task_ids))
    db = await get_db()
    for i, step in enumerate(steps):
        if i >= len(created_task_ids):
            break
        task_id = created_task_ids[i]
        plugin_id = step.get("plugin_id")
        inputs = step.get("inputs") or {}
        if not plugin_id:
            await executor.mark_task_failed(task_id, reason="Plugin ID not provided in workflow step")
            await _cancel_remaining_tasks(db, created_task_ids[i+1:])
            break

        from .plugins import get_plugin_manager
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(plugin_id)
        if not plugin:
            await executor.mark_task_failed(task_id, reason=f"Plugin {plugin_id} not found")
            await _cancel_remaining_tasks(db, created_task_ids[i+1:])
            break

        request_id = get_request_id()
        execution_context = normalize_execution_context(step.get("execution_context") or {})
        target_policy = await get_target_policy(db, owner_id, execution_context.get("target_policy_id"))
        safe_mode = bool(
            settings.safe_mode_default
            and not (target_policy and target_policy.get("allow_public_targets"))
        )

        effective_inputs = dict(inputs)
        effective_inputs.pop("safe_mode", None)
        effective_inputs["safe_mode"] = safe_mode

        # Validation checks
        if target := effective_inputs.get("target"):
            target_str = str(target)
            if plugin.category != "code":
                from .validation import validate_target
                try:
                    is_valid, error_msg = await asyncio.wait_for(
                        asyncio.to_thread(validate_target, target_str, safe_mode),
                        timeout=float(settings.dns_resolution_timeout_seconds),
                    )
                    if not is_valid:
                        await executor.mark_task_failed(task_id, reason=f"Target validation failed: {error_msg}")
                        await _cancel_remaining_tasks(db, created_task_ids[i+1:])
                        break
                except asyncio.TimeoutError:
                    await executor.mark_task_failed(task_id, reason="Target validation timed out")
                    await _cancel_remaining_tasks(db, created_task_ids[i+1:])
                    break

                if settings.enforce_network_policy and target_str:
                    from .network_policy import get_policy_engine
                    engine = get_policy_engine()
                    try:
                        allowed, reason, _ = await asyncio.wait_for(
                            asyncio.to_thread(engine.check_access, dest_ip=target_str, plugin_id=plugin_id, task_id=task_id),
                            timeout=float(settings.dns_resolution_timeout_seconds),
                        )
                        if not allowed:
                            await executor.mark_task_failed(task_id, reason=f"Network policy denied access: {reason}")
                            await _cancel_remaining_tasks(db, created_task_ids[i+1:])
                            break
                    except asyncio.TimeoutError:
                        await executor.mark_task_failed(task_id, reason="Network policy check timed out")
                        await _cancel_remaining_tasks(db, created_task_ids[i+1:])
                        break

        client = f"user:{owner_id}"
        max_per_hour = plugin.safety.get("rate_limit", {}).get("max_per_hour", settings.max_tasks_per_hour) if plugin else settings.max_tasks_per_hour
        can_exec, rate_err = await rate_limiter.can_execute(plugin_id, max_per_hour, client_id=client)
        if not can_exec:
            await executor.mark_task_failed(task_id, reason=f"Rate limit exceeded: {rate_err}")
            await _cancel_remaining_tasks(db, created_task_ids[i+1:])
            break

        # Acquire concurrency slot
        can_acquire, concurrency_err = await concurrent_limiter.acquire(task_id)
        if not can_acquire:
            await executor.mark_task_failed(task_id, reason="Concurrency limit reached")
            logger.warning("Workflow %s: concurrency limit reached for task %s", workflow_id, task_id)
            await _cancel_remaining_tasks(db, created_task_ids[i+1:])
            break

        # Execute task
        try:
            async def run_task(task_id: str) -> None:
                set_request_id(request_id)
                await executor.execute_task(task_id)

            await run_task(task_id)
        except Exception as e:
            logger.error("Workflow %s task %s failed with exception: %s", workflow_id, task_id, e)

        # Check status in db
        task_row = await db.fetchone("SELECT status FROM tasks WHERE id = ?", (task_id,))
        task_status = task_row["status"] if task_row else "failed"
        if task_status != "completed":
            logger.warning("Workflow %s task %s failed or cancelled (status: %s). Aborting downstream steps.", workflow_id, task_id, task_status)
            await _cancel_remaining_tasks(db, created_task_ids[i+1:])
            break


async def _finalize_workflow_run(run_id: str, poll_interval: float = 5.0, max_polls: int = 720) -> None:
    """Background task that polls task statuses and marks the run terminal.

    Polls every *poll_interval* seconds for up to *max_polls* iterations
    (default: 5 s × 720 = 1 hour). If tasks are still running after the
    limit, the run is marked failed with a timeout message so it never stays
    permanently in the 'queued' state.
    """
    for _ in range(max_polls):
        await asyncio.sleep(poll_interval)
        try:
            db = await get_db()
            terminal_status = await db.check_workflow_run_tasks(run_id)
            if terminal_status is not None:
                await db.finalize_workflow_run(run_id, terminal_status)
                return
        except Exception as exc:
            logger.warning("workflow run finalization error for %s: %s", run_id, exc)
            return
    try:
        db = await get_db()
        await db.finalize_workflow_run(
            run_id, "failed", "Run finalization timed out — check individual task statuses"
        )
    except Exception as exc:
        logger.warning("workflow run timeout finalization failed for %s: %s", run_id, exc)


scheduler = WorkflowScheduler()
