"""
Task execution engine with Docker sandboxing
"""

import asyncio
from asyncio import subprocess
import uuid
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import re

from .redaction import redact
from .cache import get_cache
from .config import settings
from .database import get_db
from .plugins import get_plugin_manager
from .models import TaskStatus
from .ratelimit import concurrent_limiter

# Modular Scanners
from .scanners.port_scanner import PortScanner
from .scanners.web_scanner import WebScanner
from .scanners.recon_scanner import ReconScanner

MODULAR_SCANNERS = {
    "port_scanner": PortScanner,
    "web_scanner": WebScanner,
    "recon_scanner": ReconScanner
}

logger = logging.getLogger(__name__)


def extract_target(inputs: Dict[str, Any]) -> str:
    """Best-effort target extraction across plugin shapes."""
    return (
        inputs.get("target")
        or inputs.get("url")
        or inputs.get("host")
        or inputs.get("domain")
        or ""
    )


class TaskExecutor:
    """Executes security scanning tasks in isolated environments"""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._listeners:
            self._listeners[task_id] = []
        q = asyncio.Queue()
        self._listeners[task_id].append(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue):
        if task_id in self._listeners and q in self._listeners[task_id]:
            self._listeners[task_id].remove(q)
            if not self._listeners[task_id]:
                self._listeners.pop(task_id, None)

    async def _broadcast(self, task_id: str, event_type: str, data: Any):
        if task_id in self._listeners:
            event = {"type": event_type, "data": data}
            for q in self._listeners[task_id]:
                await q.put(event)

    async def create_task(
        self,
        plugin_id: str,
        inputs: Dict[str, Any],
        preset: Optional[str] = None,
        consent_granted: bool = False
    ) -> str:

        task_id = str(uuid.uuid4())
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(plugin_id)

        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")

        if preset and preset in plugin.presets:
            inputs = {**plugin.presets[preset], **inputs}

        db = await get_db()

        await db.execute(
            """
            INSERT INTO tasks (
                id, plugin_id, tool_name, target, inputs_json, preset,
                status, consent_granted, safe_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                plugin_id,
                plugin.name,
                extract_target(inputs),
                json.dumps(inputs),
                preset,
                TaskStatus.QUEUED.value,
                consent_granted,
                inputs.get("safe_mode", True)
            )
        )

        await db.log_audit(
            "task_created",
            f"Task created for {plugin.name}",
            context={"task_id": task_id, "plugin_id": plugin_id},
            task_id=task_id,
            plugin_id=plugin_id
        )

        return task_id

    async def execute_task(self, task_id: str):
        db = await get_db()
        self.running_tasks[task_id] = asyncio.current_task()

        start_time = None  # ✅ FIX: important safety fix

        try:
            start_time = time.time()

            await db.execute(
                "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                (TaskStatus.RUNNING.value, datetime.now().isoformat(), task_id)
            )

            task_row = await db.fetchone(
                "SELECT plugin_id, inputs_json, safe_mode FROM tasks WHERE id = ?",
                (task_id,)
            )

            if not task_row:
                raise ValueError(f"Task not found: {task_id}")

            plugin_id = task_row["plugin_id"]
            inputs = json.loads(task_row["inputs_json"])
            target = extract_target(inputs)

            if plugin_id in MODULAR_SCANNERS:
                scanner_class = MODULAR_SCANNERS[plugin_id]
                scanner = scanner_class(task_id, db)

                result = await scanner.run(target, inputs)

                duration = time.time() - start_time

                final_status = (
                    TaskStatus.COMPLETED.value
                    if result.get("status") != "failed"
                    else TaskStatus.FAILED.value
                )

                await db.execute(
                    """
                    UPDATE tasks SET
                        status = ?,
                        completed_at = ?,
                        duration_seconds = ?,
                        structured_json = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
                    (
                        final_status,
                        datetime.now().isoformat(),
                        duration,
                        json.dumps(result),
                        result.get("error_message"),
                        task_id
                    )
                )

            else:
                plugin_manager = get_plugin_manager()
                plugin = plugin_manager.get_plugin(plugin_id)

                command = plugin_manager.build_command(plugin_id, inputs)

                if not command:
                    raise ValueError("Failed to build command")

                output, exit_code = await self._execute_command(
                    command,
                    task_id,
                    timeout=self._resolve_execution_timeout(inputs),
                )

                duration = time.time() - start_time

                output = redact(output)

                final_status, error_message = self._classify_command_result(
                    plugin, output, exit_code
                )

                await db.execute(
                    """
                    UPDATE tasks SET
                        status = ?,
                        completed_at = ?,
                        duration_seconds = ?,
                        exit_code = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
                    (
                        final_status,
                        datetime.now().isoformat(),
                        duration,
                        exit_code,
                        error_message,
                        task_id
                    )
                )

            await self._broadcast(task_id, "status", final_status)
            await self._invalidate_cached_views()

        except asyncio.CancelledError:
            duration = (time.time() - start_time) if start_time else 0

            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.CANCELLED.value,
                    datetime.now().isoformat(),
                    duration,
                    task_id,
                )
            )

            await self._broadcast(task_id, "status", TaskStatus.CANCELLED.value)
            raise

        except Exception as e:
            duration = (time.time() - start_time) if start_time else 0

            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.FAILED.value,
                    datetime.now().isoformat(),
                    duration,
                    str(e),
                    task_id
                )
            )

            await self._broadcast(task_id, "status", TaskStatus.FAILED.value)

        finally:
            self.running_tasks.pop(task_id, None)
            await concurrent_limiter.release(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        db = await get_db()  # ✅ FIX: missing db

        if task_id not in self.running_tasks:
            return False

        task = self.running_tasks[task_id]
        task.cancel()

        if settings.docker_enabled:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "kill", f"secuscan_task_{task_id}",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                await proc.communicate()
            except Exception as e:
                logger.error(f"Docker kill failed: {e}")

        await self._broadcast(task_id, "status", TaskStatus.CANCELLED.value)
        await self._invalidate_cached_views()

        await db.log_audit(
            "task_cancelled",
            "Task cancelled by user",
            task_id=task_id
        )

        return True

