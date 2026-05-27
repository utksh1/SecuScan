"""
Task execution engine with Docker sandboxing
"""

import asyncio
from asyncio import subprocess
import uuid
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path

from .redaction import redact
from .database import get_db
from .plugins import get_plugin_manager
from .models import TaskStatus
from .ratelimit import concurrent_limiter
from .config import settings

logger = logging.getLogger(__name__)


def extract_target(inputs: Dict[str, Any]) -> str:
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

    # -------------------------
    # Event system
    # -------------------------
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

        listeners = self._listeners.get(task_id)

        if not listeners:
            return

        event = {"type": event_type, "data": data}

        for q in listeners:
            await q.put(event)

    # -------------------------
    # CORE EXECUTION HELPERS
    # -------------------------
    async def _execute_command(self, command, task_id, timeout=60):
        """
        Execute command safely
        """

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            output = (stdout or b"").decode(errors="ignore") + (stderr or b"").decode(
                errors="ignore"
            )

            return output, proc.returncode

        except asyncio.TimeoutError:

            proc.kill()

            try:
                await proc.communicate()
            except Exception:
                pass

            return "TIMEOUT", 1

    def _parse_results(self, plugin, output: str):
        """
        Parse plugin results consistently
        """

        findings = []

        try:

            report_path = getattr(plugin, "output", {}).get("report_path")

            if report_path and Path(report_path).exists():

                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    findings = data

                elif isinstance(data, dict):
                    findings = data.get("findings", [data])

                return {
                    "count": len(findings),
                    "findings": findings,
                    "title": getattr(plugin, "name", "Scan Result"),
                }

        except Exception as e:
            logger.warning(f"Failed reading report file: {e}")

        try:

            parsed = json.loads(output)

            if isinstance(parsed, list):
                findings = parsed

            elif isinstance(parsed, dict):
                findings = parsed.get("findings", [parsed])

            return {
                "count": len(findings),
                "findings": findings,
                "title": getattr(plugin, "name", "Scan Result"),
            }

        except Exception:
            pass

        if "packet loss" in output.lower():

            findings.append(
                {
                    "type": "icmp_ping",
                    "summary": output.strip(),
                }
            )

            return {
                "count": len(findings),
                "findings": findings,
                "title": getattr(plugin, "name", "Scan Result"),
            }

        return {
            "count": 0,
            "findings": [],
            "raw": output,
            "title": getattr(plugin, "name", "Scan Result"),
        }

    def _classify_command_result(self, plugin, output: str, exit_code: int):
        """
        Classify execution result
        """

        output_lower = output.lower()

        error_patterns = [
            "unknown option",
            "flag provided but not defined",
            "unrecognized option",
            "invalid option",
            "no such option",
        ]

        for pattern in error_patterns:

            if pattern in output_lower:
                return (TaskStatus.FAILED.value, output.strip())

        if "packet loss" in output_lower or "statistics" in output_lower:
            return TaskStatus.COMPLETED.value, None

        if exit_code == 0:
            return TaskStatus.COMPLETED.value, None

        return (TaskStatus.FAILED.value, output.strip())

    def _normalize_parsed_result(self, result, *args, **kwargs):
        """
        Normalize parsed result while keeping backward compatibility
        """

        if isinstance(result, dict):

            if "findings" in result:
                return result

            return {
                "count": 1,
                "findings": [result],
            }

        if isinstance(result, list):

            return {
                "count": len(result),
                "findings": result,
            }

        return {
            "count": 0,
            "findings": [],
            "result": result,
        }

    async def _invalidate_cached_views(self):
        return True

    async def get_task_status(self, task_id: str):

        return {
            "task_id": task_id,
            "status": "unknown",
        }

    async def mark_task_failed(
        self,
        task_id: str,
        error: str = "",
        reason: str = "",
    ):
        """
        Backward compatible failure handler
        """

        db = await get_db()

        message = error or reason or "Task failed"

        await db.execute(
            """
            UPDATE tasks
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            (
                TaskStatus.FAILED.value,
                message,
                task_id,
            ),
        )

        return {
            "task_id": task_id,
            "error": message,
        }

    def _resolve_execution_timeout(self, inputs):
        return 60

    # -------------------------
    # TASK FLOW
    # -------------------------
    async def create_task(
        self,
        plugin_id: str,
        inputs: Dict[str, Any],
        preset: Optional[str] = None,
        consent_granted: bool = False,
    ) -> str:

        task_id = str(uuid.uuid4())

        plugin_manager = get_plugin_manager()

        plugin = plugin_manager.get_plugin(plugin_id)

        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")

        db = await get_db()

        await db.execute(
            """
            INSERT INTO tasks (
                id,
                plugin_id,
                tool_name,
                target,
                inputs_json,
                preset,
                status,
                consent_granted,
                safe_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                inputs.get("safe_mode", True),
            ),
        )

        return task_id

    async def execute_task(self, task_id: str):

        db = await get_db()

        self.running_tasks[task_id] = asyncio.current_task()

        start_time = time.time()

        try:

            await db.execute(
                """
                UPDATE tasks
                SET status = ?, started_at = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.RUNNING.value,
                    datetime.now().isoformat(),
                    task_id,
                ),
            )

            task_row = await db.fetchone(
                """
                SELECT plugin_id, inputs_json
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            )

            if not task_row:
                raise ValueError("Task not found")

            plugin_id = task_row["plugin_id"]

            inputs = json.loads(task_row["inputs_json"])

            plugin_manager = get_plugin_manager()

            plugin = plugin_manager.get_plugin(plugin_id)

            if not plugin:
                raise ValueError(f"Plugin not found: {plugin_id}")

            command = plugin_manager.build_command(plugin_id, inputs)

            if not command:
                raise ValueError("Command build failed")

            timeout = self._resolve_execution_timeout(inputs)

            output, exit_code = await self._execute_command(
                command,
                task_id,
                timeout,
            )

            output = redact(output)

            parsed_result = self._parse_results(plugin, output)

            normalized_result = self._normalize_parsed_result(parsed_result)

            final_status, error = self._classify_command_result(
                plugin,
                output,
                exit_code,
            )

            await db.execute(
                """
                UPDATE tasks
                SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?,
                    exit_code = ?,
                    output_json = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    final_status,
                    datetime.now().isoformat(),
                    time.time() - start_time,
                    exit_code,
                    json.dumps(normalized_result),
                    error,
                    task_id,
                ),
            )

            await self._broadcast(
                task_id,
                "status",
                final_status,
            )

            await self._invalidate_cached_views()

        except asyncio.CancelledError:

            await db.execute(
                """
                UPDATE tasks
                SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.CANCELLED.value,
                    datetime.now().isoformat(),
                    time.time() - start_time,
                    task_id,
                ),
            )

            await self._broadcast(
                task_id,
                "status",
                TaskStatus.CANCELLED.value,
            )

            raise

        except Exception as e:

            logger.exception(f"Task execution failed: {e}")

            await db.execute(
                """
                UPDATE tasks
                SET
                    status = ?,
                    completed_at = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.FAILED.value,
                    datetime.now().isoformat(),
                    str(e),
                    task_id,
                ),
            )

        finally:

            self.running_tasks.pop(task_id, None)

            try:
                await concurrent_limiter.release(task_id)
            except Exception:
                pass

    async def cancel_task(self, task_id: str) -> bool:

        db = await get_db()

        task = self.running_tasks.get(task_id)

        if not task:
            return False

        if task.done():
            return False

        task.cancel()

        await db.log_audit(
            "task_cancelled",
            "Task cancellation requested by user",
            task_id=task_id,
        )

        return True


# Global instance
executor = TaskExecutor()
