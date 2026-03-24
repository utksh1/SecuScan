from typing import Any, Dict, List, Optional
import asyncio
import time
import uuid
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sse_starlette.sse import EventSourceResponse

from .plugins import PluginRegistry
from .db import Database
from .tasks import TaskManager, TaskStatus


def create_app() -> FastAPI:
    app = FastAPI(title="SecuScan API", default_response_class=ORJSONResponse)

    db = Database(db_path="./data/secuscan.db")
    plugins = PluginRegistry(plugins_dir="./plugins")
    tasks = TaskManager(db=db, plugins=plugins)

    @app.on_event("startup")
    async def on_startup() -> None:
        await db.initialize()
        await plugins.load_all()

    # CORS for local frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    @app.get("/api/health")
    async def health() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "version": "0.1.0-dev",
            "uptime_seconds": tasks.uptime_seconds(),
            "active_tasks": tasks.active_count(),
            "docker_available": False,  # toggled later when runner added
            "plugins_loaded": plugins.count(),
        }

    @app.get("/api/version")
    async def version() -> Dict[str, Any]:
        return {
            "version": "0.1.0-dev",
            "build_date": "2025-10-29",
            "python_version": "3.11",
        }

    @app.get("/api/plugins")
    async def list_plugins(
        category: Optional[str] = Query(default=None),
        safety_level: Optional[str] = Query(default=None),
    ) -> Dict[str, Any]:
        items = plugins.list_plugins(category=category, safety_level=safety_level)
        return {"plugins": items, "total": len(items)}

    @app.get("/api/plugins/{plugin_id}/schema")
    async def plugin_schema(plugin_id: str) -> Dict[str, Any]:
        meta = plugins.get(plugin_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return meta

    @app.get("/api/presets")
    async def all_presets() -> Dict[str, Any]:
        return {"presets": plugins.all_presets()}

    @app.post("/api/tasks/start", status_code=201)
    async def start_task(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        plugin_id = payload.get("plugin_id")
        parameters = payload.get("parameters", {})
        consent = bool(payload.get("consent_acknowledged", False))
        if not plugin_id:
            raise HTTPException(status_code=400, detail="plugin_id is required")
        if plugins.get(plugin_id) is None:
            raise HTTPException(status_code=404, detail="Plugin not found")

        task_id = await tasks.enqueue(plugin_id=plugin_id, parameters=parameters, consent=consent)
        return {
            "task_id": task_id,
            "status": "queued",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sse_url": f"/api/tasks/{task_id}/stream",
        }

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        ok = await tasks.cancel(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found or not cancellable")
        return {"task_id": task_id, "status": "cancelled"}

    @app.get("/api/tasks/{task_id}/status")
    async def task_status(task_id: str) -> Dict[str, Any]:
        status = tasks.status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return status

    @app.get("/api/tasks/{task_id}/result")
    async def task_result(task_id: str) -> Dict[str, Any]:
        row = await db.get_task(task_id)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "task_id": row["id"],
            "plugin_id": row["plugin_id"],
            "status": row["status"],
            "summary": (row["summary"] and __import__('json').loads(row["summary"])) or {},
            "structured": (row["structured_json"] and __import__('json').loads(row["structured_json"])) or {},
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "duration_seconds": row["duration_seconds"],
        }

    @app.get("/api/tasks/{task_id}/stream")
    async def task_stream(task_id: str) -> EventSourceResponse:
        if tasks.status(task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")

        async def gen():
            queue = tasks.get_stream(task_id)
            if queue is None:
                yield {"event": "error", "data": {"message": "stream unavailable"}}
                return
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=60)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": {"t": time.time()}}
                    continue
                if item.get("event") == "end":
                    yield {"event": "result", "data": item["data"]}
                    break
                yield {"event": item.get("event", "log"), "data": item.get("data", {})}

        return EventSourceResponse(gen())

    @app.get("/api/tasks")
    async def list_tasks(
        status: Optional[str] = Query(default=None),
        plugin_id: Optional[str] = Query(default=None),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1, le=100),
    ) -> Dict[str, Any]:
        # Prefer DB-backed listing
        items_db = await db.list_tasks()
        # enhance shape to match in-memory when needed
        for it in items_db:
            it.setdefault("task_id", it.get("id"))
        items = items_db
        if status:
            items = [i for i in items if i.get("status") == status]
        if plugin_id:
            items = [i for i in items if i.get("plugin_id") == plugin_id]
        start = (page - 1) * per_page
        end = start + per_page
        sliced = items[start:end]
        return {
            "tasks": sliced,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": len(items),
                "total_pages": (len(items) + per_page - 1) // per_page,
            },
        }

    @app.get("/api/tasks/{task_id}/export")
    async def export_task(task_id: str, format: str = Query(default="json")):
        if format != "json":
            raise HTTPException(status_code=400, detail="Only json export is implemented")
        row = await db.get_task(task_id)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        payload = {
            "task_id": row["id"],
            "plugin_id": row["plugin_id"],
            "status": row["status"],
            "summary": (row["summary"] and __import__('json').loads(row["summary"])) or {},
            "structured": (row["structured_json"] and __import__('json').loads(row["structured_json"])) or {},
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
            "duration_seconds": row["duration_seconds"],
        }
        return payload

    settings_state: Dict[str, Any] = {
        "bind_address": "127.0.0.1",
        "bind_port": 8081,
        "sandbox_enforced": True,
        "rate_limit_enabled": False,
        "theme": "dark",
    }

    @app.get("/api/settings")
    async def get_settings() -> Dict[str, Any]:
        return settings_state

    @app.put("/api/settings")
    async def put_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
        settings_state.update({k: v for k, v in payload.items() if k in settings_state})
        return {"updated": True, **settings_state}

    return app


app = create_app()

