"""
API routes for SecuScan backend
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from typing import Any, Optional, List, Dict, Callable
import json
import logging

def parse_json_fields(rows: List[Dict], fields: List[str]) -> List[Dict]:
    """Helper to parse stringified JSON fields from SQLite."""
    parsed = []
    for row in rows:
        item = dict(row)
        for field in fields:
            if item.get(field) and isinstance(item[field], str):
                try:
                    item[field] = json.loads(item[field])
                except json.JSONDecodeError:
                    pass
        parsed.append(item)
    return parsed

logger = logging.getLogger(__name__)

from .cache import get_cache
from .models import (
    TaskCreateRequest, TaskResponse, TaskResult,
    PluginListResponse, ErrorResponse
)
from .config import settings
from .database import get_db
from .plugins import get_plugin_manager
from .executor import executor
from .ratelimit import rate_limiter, concurrent_limiter
from .validation import validate_target
from .reporting import reporting

from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/v1")


async def get_or_set_cached(key: str, builder):
    """Read from cache, or build and cache a JSON response."""
    cache = await get_cache()
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    value = await builder()
    await cache.set_json(key, value)
    return value


async def invalidate_view_cache():
    """Clear aggregate caches after writes."""
    cache = await get_cache()
    for prefix in ["summary:", "assets:", "findings:", "surface:", "reports:", "tasks:"]:
        await cache.delete_prefix(prefix)


@router.get("/plugins", response_model=PluginListResponse)
async def list_plugins():
    """List all available plugins"""
    plugin_manager = get_plugin_manager()
    plugins = plugin_manager.list_plugins()
    
    return PluginListResponse(
        plugins=plugins,
        total=len(plugins)
    )


@router.get("/plugin/{plugin_id}/schema")
async def get_plugin_schema(plugin_id: str):
    """Get plugin schema for UI generation"""
    plugin_manager = get_plugin_manager()
    schema = plugin_manager.get_plugin_schema(plugin_id)
    
    if not schema:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    
    return schema


@router.get("/presets")
async def get_all_presets():
    """Get all plugin presets"""
    plugin_manager = get_plugin_manager()
    presets = {}
    
    for plugin_id, plugin in plugin_manager.plugins.items():
        presets[plugin_id] = plugin.presets
    
    return presets


@router.post("/task/start")
async def start_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new scan task
    """
    # Validate consent
    if settings.require_consent and not request.consent_granted:
        logger.warning(f"Task start failed: Consent not granted. Request: {request}")
        raise HTTPException(
            status_code=400,
            detail="Consent required. You must acknowledge the legal notice."
        )
    
    # Get plugin
    plugin_manager = get_plugin_manager()
    plugin = plugin_manager.get_plugin(request.plugin_id)
    
    if not plugin:
        logger.warning(f"Task start failed: Plugin not found: {request.plugin_id}")
        raise HTTPException(status_code=404, detail=f"Plugin not found: {request.plugin_id}")
    
    # Validate target if present
    target = request.inputs.get("target")
    if target:
        safe_mode = request.inputs.get("safe_mode", settings.safe_mode_default)
        is_valid, error_msg = validate_target(target, safe_mode)
        
        if not is_valid:
            logger.warning(f"Task start failed: Target validation failed for '{target}': {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
    
    # Check rate limits
    can_execute, error_msg = await rate_limiter.can_execute(
        request.plugin_id,
        plugin.safety.get("rate_limit", {}).get("max_per_hour", settings.max_tasks_per_hour)
    )
    
    if not can_execute:
        raise HTTPException(status_code=429, detail=error_msg)
    
    # Check concurrent task limit
    can_acquire, error_msg = await concurrent_limiter.acquire("temp")
    if not can_acquire:
        raise HTTPException(status_code=503, detail=error_msg)
    await concurrent_limiter.release("temp")
    
    # Create task
    try:
        task_id = await executor.create_task(
            request.plugin_id,
            request.inputs,
            request.preset,
            request.consent_granted
        )
        
        # Execute task in background
        background_tasks.add_task(executor.execute_task, task_id)
        await invalidate_view_cache()
        
        return {
            "task_id": task_id,
            "status": "queued",
            "created_at": "now",
            "stream_url": f"/api/v1/task/{task_id}/stream"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Get task status"""
    status = await executor.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status

@router.get("/task/{task_id}/stream")
async def stream_task_output(task_id: str):
    """Stream task output via Server-Sent Events (SSE)"""
    import asyncio

    status = await executor.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        # First, send the initial status
        yield {
            "event": "status",
            "data": json.dumps({"status": status["status"]})
        }

        # If it's already completed/failed, we just return the raw output if any and close
        if status["status"] in ["completed", "failed", "cancelled"]:
            try:
                db = await get_db()
                task_row = await db.fetchone("SELECT raw_output_path FROM tasks WHERE id = ?", (task_id,))
                if task_row and task_row["raw_output_path"]:
                    with open(task_row["raw_output_path"], "r") as f:
                        yield {
                            "event": "output",
                            "data": json.dumps({"chunk": f.read()})
                        }
            except Exception:
                pass
            return

        # Otherwise, subscribe to the live task events
        queue = executor.subscribe(task_id)
        try:
            while True:
                # Wait for the next event from the executor
                event = await queue.get()

                if event["type"] == "status":
                    yield {
                        "event": "status",
                        "data": json.dumps({"status": event["data"]})
                    }
                    if event["data"] in ["completed", "failed", "cancelled"]:
                        break
                elif event["type"] == "output":
                    yield {
                        "event": "output",
                        "data": json.dumps({"chunk": event["data"]})
                    }
        except asyncio.CancelledError:
            pass
        finally:
            executor.unsubscribe(task_id, queue)

    return EventSourceResponse(event_generator())

@router.get("/task/{task_id}/report/csv")
async def download_csv_report(task_id: str):
    """Download task results as a CSV report."""
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, plugin_id, tool_name, target, status, created_at, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_row["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task is not finished yet")

    structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
    csv_data = reporting.generate_csv_report(dict(task_row), {"structured": structured_data})

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=secuscan_{task_id}.csv"}
    )

@router.get("/task/{task_id}/report/pdf")
async def download_pdf_report(task_id: str):
    """Download task results as a PDF report."""
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, plugin_id, tool_name, target, status, created_at, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_row["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task is not finished yet")

    structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
    pdf_bytes = reporting.generate_pdf_report(dict(task_row), {"structured": structured_data})

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=secuscan_{task_id}.pdf"}
    )


@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    """Get task execution result"""
    db = await get_db()
    
    task_row = await db.fetchone(
        """
        SELECT id, plugin_id, tool_name, target, status,
               created_at, duration_seconds, structured_json,
               raw_output_path, error_message
        FROM tasks WHERE id = ?
        """,
        (task_id,)
    )
    
    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    structured = {}
    if task_row["structured_json"]:
        try:
            structured = json.loads(task_row["structured_json"])
        except json.JSONDecodeError:
            structured = {}

    findings = structured.get("findings", []) if isinstance(structured, dict) else []
    severity_counts: Dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "info")).lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    summary: List[str] = []
    if severity_counts:
        ordered = ["critical", "high", "medium", "low", "info"]
        parts = [f"{severity_counts[level]} {level}" for level in ordered if severity_counts.get(level)]
        if parts:
            summary.append(f"Findings profile: {', '.join(parts)}.")
    if structured.get("open_ports"):
        summary.append(f"Observed {len(structured['open_ports'])} exposed ports.")
    if structured.get("technologies"):
        summary.append(f"Identified {len(structured['technologies'])} technologies.")
    
    # Read raw output excerpt
    raw_excerpt = None
    if task_row["raw_output_path"]:
        try:
            with open(task_row["raw_output_path"], 'r') as f:
                raw_excerpt = f.read(1000)  # First 1000 chars
        except:
            pass
    
    return {
        "task_id": task_row["id"],
        "plugin_id": task_row["plugin_id"],
        "tool": task_row["tool_name"],
        "target": task_row["target"],
        "timestamp": task_row["created_at"],
        "duration_seconds": task_row["duration_seconds"],
        "status": task_row["status"],
        "summary": summary,
        "severity_counts": severity_counts,
        "structured": structured,
        "raw_output_path": task_row["raw_output_path"],
        "raw_output_excerpt": raw_excerpt,
        "errors": [{"message": task_row["error_message"]}] if task_row["error_message"] else [],
        "metadata": {}
    }


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    cancelled = await executor.cancel_task(task_id)
    
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found or not running")
    
    return {
        "task_id": task_id,
        "status": "cancelled",
        "cancelled_at": "now"
    }


@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Return aggregate dashboard data from the primary store, cached in Redis."""

    async def build():
        db = await get_db()
        
        # Get data
        raw_assets = await db.fetchall("SELECT * FROM assets ORDER BY updated_at DESC")
        assets = parse_json_fields(raw_assets, ["open_ports", "technologies", "services", "metadata_json"])
        
        raw_findings = await db.fetchall("SELECT * FROM findings ORDER BY discovered_at DESC")
        findings = parse_json_fields(raw_findings, ["metadata_json"])
        
        raw_atks = await db.fetchall(
            "SELECT * FROM attack_surface_entries ORDER BY last_seen DESC"
        )
        attack_surface = parse_json_fields(raw_atks, ["metadata_json"])
        
        task_stats = await db.fetchone(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                COUNT(*) FILTER (WHERE status = 'running') AS running
            FROM tasks
            """
        )

        critical_findings: int = sum(1 for item in findings if item.get("severity") == "critical")
        high_findings: int = sum(1 for item in findings if item.get("severity") == "high")
        medium_findings: int = sum(1 for item in findings if item.get("severity") == "medium")
        low_findings: int = len(findings) - critical_findings - high_findings - medium_findings

        recent_findings: List[Dict] = findings[:5]
        high_risk_assets: List[Dict] = [item for item in assets if item.get("risk_level") in {"critical", "high"}][:4]

        return {
            "total_assets": len(assets),
            "active_assets": sum(1 for item in assets if item.get("status") == "active"),
            "critical_assets": sum(1 for item in assets if item.get("risk_level") == "critical"),
            "total_attack_surface": len(attack_surface),
            "total_findings": len(findings),
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "last_scan_time": assets[0].get("last_scanned") if assets else None,
            "recent_findings": recent_findings,
            "high_risk_assets": high_risk_assets,
            "attack_surface_by_category": {
                str(item.get("category", "unknown")): sum(1 for x in attack_surface if x.get("category") == item.get("category"))
                for item in attack_surface
            },
            "scan_activity": {
                "total": int(task_stats["total"]) if task_stats and task_stats.get("total") is not None else 0,
                "completed": int(task_stats["completed"]) if task_stats and task_stats.get("completed") is not None else 0,
                "running": int(task_stats["running"]) if task_stats and task_stats.get("running") is not None else 0,
            },
            "running_tasks": parse_json_fields(
                await db.fetchall(
                    "SELECT id, plugin_id, tool_name, target, status, created_at FROM tasks WHERE status = 'running' ORDER BY created_at DESC LIMIT 5"
                ),
                []
            ),
            "recent_tasks": parse_json_fields(
                await db.fetchall(
                    "SELECT id, plugin_id, tool_name, target, status, created_at, duration_seconds FROM tasks ORDER BY created_at DESC LIMIT 5"
                ),
                []
            )
        }

    return await build()


@router.get("/assets")
async def get_assets():
    """Return discovered assets."""

    async def build():
        db = await get_db()
        rows = await db.fetchall("SELECT * FROM assets ORDER BY updated_at DESC")
        return {"assets": parse_json_fields(rows, ["open_ports", "technologies", "services", "metadata_json"])}

    return await get_or_set_cached("assets:list", build)


@router.get("/findings")
async def get_findings():
    """Return vulnerability findings."""

    async def build():
        db = await get_db()
        rows = await db.fetchall("SELECT * FROM findings ORDER BY discovered_at DESC")
        return {"findings": parse_json_fields(rows, ["metadata_json"])}

    return await get_or_set_cached("findings:list", build)


@router.get("/attack-surface")
async def get_attack_surface():
    """Return attack surface entries."""

    async def build():
        db = await get_db()
        rows = await db.fetchall(
            "SELECT * FROM attack_surface_entries ORDER BY last_seen DESC"
        )
        return {"entries": rows}

    return await get_or_set_cached("surface:list", build)


@router.get("/reports")
async def get_reports():
    """Return generated reports."""

    async def build():
        db = await get_db()
        rows = await db.fetchall("SELECT * FROM reports ORDER BY generated_at DESC")
        return {"reports": parse_json_fields(rows, ["metadata_json"])}

    return await get_or_set_cached("reports:list", build)


@router.get("/tasks")
async def list_tasks(
    page: int = 1,
    per_page: int = 25,
    plugin_id: Optional[str] = None,
    status: Optional[str] = None
):
    """List all tasks with pagination"""
    db = await get_db()
    
    # Build query
    query = "SELECT id, plugin_id, tool_name, target, status, created_at, duration_seconds FROM tasks"
    params = []
    
    where_clauses = []
    if plugin_id:
        where_clauses.append("plugin_id = ?")
        params.append(plugin_id)
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    tasks = await db.fetchall(query, tuple(params))
    
    # Get total count
    count_query = "SELECT COUNT(*) as total FROM tasks"
    if where_clauses:
        count_query += " WHERE " + " AND ".join(where_clauses)
    
    count_result = await db.fetchone(count_query, tuple(params[:-2]) if where_clauses else ())
    total: int = int(count_result["total"]) if count_result and count_result.get("total") is not None else 0
    
    # Parse JSON fields and format for frontend
    tasks_list = parse_json_fields(tasks, ["structured_json", "config_json", "metadata_json"])
    for t in tasks_list:
        if "id" in t:
            t["task_id"] = t.pop("id")
    
    total_pages = 0
    if per_page > 0:
        total_pages = (total + per_page - 1) // per_page

    return {
        "tasks": tasks_list,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total
        }
    }


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    db = await get_db()
    
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    await invalidate_view_cache()
    
    return {
        "task_id": task_id,
        "deleted": True
    }


@router.get("/settings")
async def get_settings():
    """Get current settings"""
    return {
        "network": {
            "bind_address": settings.bind_address,
            "port": settings.bind_port,
            "allow_remote": False
        },
        "sandbox": {
            "engine": "docker" if settings.docker_enabled else "subprocess",
            "default_timeout": settings.sandbox_timeout,
            "resource_limits": {
                "cpu_quota": settings.sandbox_cpu_quota,
                "memory_mb": settings.sandbox_memory_mb
            }
        },
        "safety": {
            "require_consent": settings.require_consent,
            "safe_mode_default": settings.safe_mode_default,
            "allowed_networks": settings.allowed_networks
        }
    }
