from __future__ import annotations
from typing import Any, Dict, Optional, List
import asyncio
import json
import time
import uuid

from .db import Database
from .plugins import PluginRegistry


class TaskStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskManager:
    def __init__(self, db: Database, plugins: PluginRegistry) -> None:
        self.db = db
        self.plugins = plugins
        self._streams: Dict[str, asyncio.Queue] = {}
        self._status: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()

    def uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)

    def active_count(self) -> int:
        return len([s for s in self._status.values() if s.get("status") == TaskStatus.RUNNING])

    async def enqueue(self, plugin_id: str, parameters: Dict[str, Any], consent: bool) -> str:
        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._status[task_id] = {
            "task_id": task_id,
            "plugin_id": plugin_id,
            "status": TaskStatus.QUEUED,
            "created_at": now,
            "progress_percent": 0,
        }
        self._streams[task_id] = asyncio.Queue(maxsize=100)
        await self.db.insert_task({
            "id": task_id,
            "plugin_id": plugin_id,
            "parameters": json.dumps(parameters),
            "status": TaskStatus.QUEUED,
            "created_at": now,
            "consent_acknowledged": consent,
        })
        # Start execution asynchronously
        asyncio.create_task(self._execute(task_id, plugin_id, parameters))
        return task_id

    async def cancel(self, task_id: str) -> bool:
        st = self._status.get(task_id)
        if not st:
            return False
        st["status"] = TaskStatus.CANCELLED
        q = self._streams.get(task_id)
        if q:
            await q.put({"event": "status", "data": {"status": TaskStatus.CANCELLED}})
            await q.put({"event": "end", "data": {"status": TaskStatus.CANCELLED}})
        return True

    def status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._status.get(task_id)

    def get_stream(self, task_id: str) -> Optional[asyncio.Queue]:
        return self._streams.get(task_id)

    def list_tasks(self, status: Optional[str] = None, plugin_id: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self._status.values())
        if status:
            items = [i for i in items if i.get("status") == status]
        if plugin_id:
            items = [i for i in items if i.get("plugin_id") == plugin_id]
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    async def _execute(self, task_id: str, plugin_id: str, parameters: Dict[str, Any]) -> None:
        q = self._streams[task_id]
        self._status[task_id]["status"] = TaskStatus.RUNNING
        await q.put({"event": "status", "data": {"status": TaskStatus.RUNNING}})
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        await self.db.mark_started(task_id, started_at)
        t0 = time.time()

        # Execute based on plugin metadata
        result_summary: Dict[str, Any]
        try:
            meta = self.plugins.get(plugin_id) or {}
            execution = meta.get("execution", {})
            engine = execution.get("engine", "python")
            for pct in (10, 25, 50, 75):
                await asyncio.sleep(0.15)
                self._status[task_id]["progress_percent"] = pct
                await q.put({"event": "progress", "data": {"percent": pct}})

            if engine == "python":
                module_path = execution.get("module")
                if not module_path:
                    raise RuntimeError("Missing execution.module for python engine")
                # Lazy import to avoid import cycles
                import importlib
                mod = importlib.import_module(module_path)
                outcome = await mod.run(parameters)
                result_summary = {
                    "task_id": task_id,
                    "plugin_id": plugin_id,
                    "status": TaskStatus.COMPLETED,
                    **outcome,
                }
            else:
                # CLI engine stubbed; real impl would run in Docker and parse output
                result_summary = {
                    "task_id": task_id,
                    "plugin_id": plugin_id,
                    "status": TaskStatus.COMPLETED,
                    "summary": {"description": f"CLI tool {plugin_id} executed (stub)"},
                    "structured": {},
                }

            self._status[task_id]["status"] = TaskStatus.COMPLETED
            await q.put({"event": "progress", "data": {"percent": 100}})
            await q.put({"event": "end", "data": result_summary})
            completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            duration = time.time() - t0
            await self.db.mark_completed(
                task_id,
                completed_at,
                duration,
                json.dumps(result_summary.get("summary") or {}),
                json.dumps(result_summary.get("structured") or {}),
            )
        except Exception as exc:  # minimal error propagation for stub
            self._status[task_id]["status"] = TaskStatus.FAILED
            await q.put({"event": "error", "data": {"message": str(exc)}})
            await q.put({"event": "end", "data": {"status": TaskStatus.FAILED}})
            completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            await self.db.mark_failed(task_id, completed_at, json.dumps({"error": str(exc)}))


