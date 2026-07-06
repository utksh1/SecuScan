"""
API routes for SecuScan backend
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Request, Depends, Body, Query
from fastapi.responses import JSONResponse
from typing import Any, Optional, List, Dict, Callable
import json
import logging
import re
import os
import uuid
import asyncio
from pathlib import Path
from urllib.parse import urlencode, urlparse

from .routes_json_helpers import (
    FINDING_JSON_FIELDS,
    _json_payload,
    _serialize_workflow,
    deserialize_asset_service_rows,
    deserialize_finding_rows,
    iter_raw_output_chunks,
    parse_json_fields,
)

# Re-exported for backward compatibility with integration tests
SSE_RAW_OUTPUT_CHUNK_SIZE = 64 * 1024
from .routes_report_helpers import (
    _slugify_filename_part,
    build_report_filename,
)

__all__ = [
    "FINDING_JSON_FIELDS",
    "parse_json_fields",
    "deserialize_finding_rows",
    "deserialize_asset_service_rows",
    "_slugify_filename_part",
    "build_report_filename",
]

def _parse_workflow_steps(raw_steps: Any) -> List[Dict[str, Any]]:
    if isinstance(raw_steps, list):
        parsed = raw_steps
    elif not raw_steps:
        parsed = []
    else:
        try:
            parsed = json.loads(raw_steps)
        except (TypeError, json.JSONDecodeError):
            parsed = []
    normalized: List[Dict[str, Any]] = []
    for step in parsed if isinstance(parsed, list) else []:
        if not isinstance(step, dict):
            continue
        try:
            model = WorkflowStep(
                plugin_id=str(step.get("plugin_id", "")),
                inputs=step.get("inputs") or {},
                preset=step.get("preset"),
                execution_context=step.get("execution_context") or {},
            )
        except Exception:
            continue
        normalized.append(model.model_dump())
    return normalized

def _serialize_workflow(row: Dict[str, Any], queued_task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Return the workflow shape consumed by the frontend."""
    return {
        "id": row["id"],
        "name": row["name"],
        "schedule_seconds": row.get("schedule_seconds"),
        "schedule_timezone": row.get("schedule_timezone"),
        "enabled": bool(row.get("enabled")),
        "steps": _parse_workflow_steps(row.get("steps_json")),
        "created_at": row.get("created_at"),
        "last_run_at": row.get("last_run_at"),
        "queued_task_ids": queued_task_ids or [],
    }


def _json_payload(value: Any, fallback: str) -> str:
    return json.dumps(value if value is not None else json.loads(fallback))


from .validation import is_filesystem_target  # noqa: E402

logger = logging.getLogger(__name__)

from .cache import get_cache, invalidate_view_cache
from .models import (
    TaskCreateRequest, TaskResponse, TaskResult,
    PluginListResponse, ErrorResponse, BulkDeleteRequest,
    NotificationRuleCreate, NotificationRuleUpdate,
    NotificationChannelType, TaskStatus,
    ExecutionContext, WorkflowStep, ValidationMode, EvidenceLevel,
    NotificationDiagnosticsResponse,
    ScanWebhookSettingsRequest, ScanWebhookSettingsResponse,
)
from .config import settings
from .database import get_db
from .plugins import get_plugin_manager, init_plugins
from . import notification_service
from .executor import executor
from .redaction import redact, redact_inputs
from .ratelimit import (
    rate_limiter, concurrent_limiter, workflow_rate_limiter,
    task_start_limiter, vault_limiter,
    report_download_limiter, read_heavy_limiter,
    resolve_client_identity, admin_limiter,
    scheduler_tick_limiter,
)
from .rate_limiter import check_scan_rate_limit
from .validation import validate_target, validate_task_start_payload, validate_url, validate_preset_name
from .reporting import reporting
from .vault import VaultCrypto
from .workflows import scheduler, _finalize_workflow_run
from .auth import require_api_key, get_current_owner
from .execution_context import is_offensive_validation, normalize_execution_context
from .finding_intelligence import build_asset_summary, build_finding_groups
from .knowledgebase import KnowledgeBase
from .platform_resources import (
    deserialize_resource_rows,
    get_credential_profile,
    get_session_profile,
    get_target_policy,
)

from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_notification_target(channel_type: NotificationChannelType, target: str) -> str:
    cleaned = target.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Notification target is required")

    if channel_type == NotificationChannelType.WEBHOOK:
        is_valid, error = validate_url(cleaned)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error or "Invalid webhook URL")

        if settings.notification_ssrf_enabled:
            from .validation import resolve_and_validate_target, validate_webhook_target
            ssrf_ok, ssrf_err = resolve_and_validate_target(cleaned)
            if not ssrf_ok:
                raise HTTPException(
                    status_code=400,
                    detail=f"Webhook target blocked by SSRF protection: {ssrf_err}"
                )
            # Additional independent check against notification_blocked_ip_ranges
            target_ok, target_err = validate_webhook_target(cleaned)
            if not target_ok:
                raise HTTPException(
                    status_code=400,
                    detail=f"Webhook target blocked by SSRF protection: {target_err}"
                )
        return cleaned

    if not _EMAIL_PATTERN.match(cleaned):
        raise HTTPException(status_code=400, detail="Invalid email address")
    return cleaned


def _serialize_notification_rule(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "severity_threshold": row["severity_threshold"],
        "channel_type": row["channel_type"],
        "target_url_or_email": row["target_url_or_email"],
        "is_active": bool(row.get("is_active")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _serialize_notification_history(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "rule_id": row["rule_id"],
        "finding_id": row["finding_id"],
        "status": row["status"],
        "error_message": row.get("error_message"),
        "sent_at": row.get("sent_at"),
    }


async def get_or_set_cached(key: str, builder):
    """Read from cache, or build and cache a JSON response."""
    cache = await get_cache()
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    value = await builder()
    await cache.set_json(key, value)
    return value


async def require_owned_task(db, task_id: str, owner: str, columns: str = "owner_id") -> Dict[str, Any]:
    """Fetch a task and enforce that it belongs to ``owner`` (issue #401).

    Returns the selected row on success. Raises 404 when the task does not
    exist and 403 when it is owned by a different user/workspace. ``columns``
    must include ``owner_id`` so the ownership comparison can be made.
    """
    row = await db.fetchone(f"SELECT {columns} FROM tasks WHERE id = ?", (task_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if row.get("owner_id") != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")
    return row


def _report_generation_error_response(task_id: str, report_format: str) -> JSONResponse:
    logger.exception("Report generation failed for task_id=%s format=%s", task_id, report_format)
    return JSONResponse(
        status_code=500,
        content={
            "error": "report_generation_failed",
            "message": f"Failed to generate {report_format.upper()} report",
            "details": {
                "task_id": task_id,
                "format": report_format,
            },
        },
    )


async def get_plugin_manager_for_request():
    """
    In debug mode, refresh plugin metadata from disk on demand so frontend catalog
    changes reflect parser/metadata edits without requiring a backend restart.
    """
    if settings.debug:
        return await init_plugins(settings.plugins_dir)
    return get_plugin_manager()


@router.get("/plugins", response_model=PluginListResponse, dependencies=[Depends(read_heavy_limiter)])
async def list_plugins():
    """List all available plugins"""
    plugin_manager = await get_plugin_manager_for_request()
    plugins = plugin_manager.list_plugins()

    return PluginListResponse(
        plugins=plugins,
        total=len(plugins)
    )

@router.get("/plugins/summary")
async def get_plugins_summary():
    """Return plugin summary statistics"""

    plugin_manager = await get_plugin_manager_for_request()
    plugins = plugin_manager.list_plugins()

    total_plugins = len(plugins)
    runnable_count = 0
    unavailable_count = 0
    category_counts: Dict[str, int] = {}

    for plugin in plugins:
        category = plugin.get("category", "unknown")

        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

        availability = plugin.get("availability", {})
        runnable = availability.get("runnable", False)

        if runnable:
            runnable_count += 1
        else:
            unavailable_count += 1
    return {
        "total_plugins": total_plugins,
        "runnable_count": runnable_count,
        "unavailable_count": unavailable_count,
        "category_counts": dict(sorted(category_counts.items()))
    }

@router.get("/plugin/{plugin_id}/schema")
async def get_plugin_schema(plugin_id: str):
    """Get plugin schema for UI generation"""
    plugin_manager = await get_plugin_manager_for_request()
    if schema := plugin_manager.get_plugin_schema(plugin_id):
        return schema
    else:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")


@router.get("/presets", dependencies=[Depends(read_heavy_limiter)])
async def get_all_presets():
    """Get all plugin presets"""
    plugin_manager = await get_plugin_manager_for_request()
    return {
        plugin_id: plugin.presets
        for plugin_id, plugin in plugin_manager.plugins.items()
    }


@router.post("/task/start", dependencies=[Depends(task_start_limiter), Depends(check_scan_rate_limit)])
async def start_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    raw_request: Request,
    owner: str = Depends(get_current_owner),
):
    """
    Start a new scan task.
    """
    # ── Payload size / field-length guard ─────────────────────────────────
    raw_body = await raw_request.body()
    execution_context = normalize_execution_context(request.execution_context)
    ok, status_code, error_msg = validate_task_start_payload(raw_body, request.inputs, execution_context)
    if not ok:
        raise HTTPException(status_code=status_code, detail=error_msg)

    # Validate consent
    if settings.require_consent and not request.consent_granted:
        logger.warning(f"Task start failed: Consent not granted. Request: {request}")
        raise HTTPException(
            status_code=400,
            detail="Consent required. You must acknowledge the legal notice."
        )

    # Get plugin
    plugin_manager = await get_plugin_manager_for_request()
    plugin = plugin_manager.get_plugin(request.plugin_id)

    if not plugin:
        logger.warning(f"Task start failed: Plugin not found: {request.plugin_id}")
        raise HTTPException(status_code=404, detail=f"Plugin not found: {request.plugin_id}")

    preset_ok, preset_error = validate_preset_name(
        request.plugin_id,
        request.preset,
        plugin.presets,
    )
    if not preset_ok:
        logger.warning("Task start failed: %s", preset_error)
        raise HTTPException(status_code=400, detail=preset_error)

    db = await get_db()
    target_policy = await get_target_policy(db, owner, execution_context.get("target_policy_id"))
    credential_profile = await get_credential_profile(db, owner, execution_context.get("credential_profile_id"))
    session_profile = await get_session_profile(db, owner, execution_context.get("session_profile_id"))

    if execution_context.get("target_policy_id") and not target_policy:
        raise HTTPException(status_code=400, detail="Target policy not found for this workspace")
    if execution_context.get("credential_profile_id") and not credential_profile:
        raise HTTPException(status_code=400, detail="Credential profile not found for this workspace")
    if execution_context.get("session_profile_id") and not session_profile:
        raise HTTPException(status_code=400, detail="Session profile not found for this workspace")

    if (credential_profile or session_profile) and not (target_policy and target_policy.get("allow_authenticated_scan")):
        raise HTTPException(
            status_code=400,
            detail="Authenticated scans require a target policy with authenticated scanning enabled.",
        )

    requires_exploit_policy = (
        plugin.safety.get("level") == "exploit"
        or execution_context.get("validation_mode") == ValidationMode.CONTROLLED_EXTRACT.value
    )

    if requires_exploit_policy and not (target_policy and target_policy.get("allow_exploit_validation")):
        raise HTTPException(
            status_code=400,
            detail="Offensive validation requires a target policy that explicitly allows exploit validation.",
        )

    # Server-controlled safe mode: public-target scans are opt-in via target policy.
    safe_mode = bool(
        settings.safe_mode_default
        and not (target_policy and target_policy.get("allow_public_targets"))
    )

    # Ensure downstream scanners/plugins see the effective safe-mode, but prevent client override.
    effective_inputs = dict(request.inputs or {})
    if "safe_mode" in effective_inputs:
        effective_inputs.pop("safe_mode", None)
    effective_inputs["safe_mode"] = safe_mode

    # Validate numeric timeout inputs at request time to prevent unsafe values
    for tkey in ("timeout", "max_scan_time"):
        # Only enforce bounds if the plugin declares the field in its schema
        declared = any(getattr(f, "id", None) == tkey for f in (plugin.fields or []))
        if not declared:
            continue
        if tkey in effective_inputs and effective_inputs[tkey] not in (None, ""):
            try:
                tval = int(effective_inputs[tkey])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"Invalid value for {tkey}: must be an integer")
            if tval <= 0 or tval > settings.sandbox_timeout:
                raise HTTPException(status_code=400, detail=f"{tkey} must be between 1 and {settings.sandbox_timeout} seconds")

    if target := effective_inputs.get("target"):
        target_str = str(target)
        should_validate_target = plugin.category != "code" and not is_filesystem_target(target_str)

        if should_validate_target:
            try:
                is_valid, error_msg = await asyncio.wait_for(
                    asyncio.to_thread(validate_target, target_str, safe_mode),
                    timeout=float(settings.dns_resolution_timeout_seconds),
                )
            except asyncio.TimeoutError:
                logger.warning("Task start failed: Target validation timed out for '%s'", target_str)
                raise HTTPException(
                    status_code=400,
                    detail="Target validation timed out in safe mode (SecuScan Guardrail)",
                )

            if not is_valid:
                logger.warning(f"Task start failed: Target validation failed for '{target}': {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)

    # Check rate limits per (client, plugin) so one client cannot exhaust
    # the quota for all other users of the same plugin.
    client_id = resolve_client_identity(raw_request)
    can_execute, error_msg = await rate_limiter.can_execute(
        request.plugin_id,
        plugin.safety.get("rate_limit", {}).get("max_per_hour", settings.max_tasks_per_hour),
        client_id=client_id,
    )

    if not can_execute:
        raise HTTPException(status_code=429, detail=error_msg)

    # Create task record first so we have a real task_id for the limiter
    try:
        task_id = await executor.create_task(
            request.plugin_id,
            effective_inputs,
            safe_mode=safe_mode,
            preset=request.preset,
            execution_context=execution_context,
            consent_granted=request.consent_granted,
            owner_id=owner,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Atomically acquire a concurrency slot using the real task_id.
    # acquire() is lock-protected internally, so the check and register
    # happen in a single operation — no TOCTOU window between requests.
    can_acquire, error_msg = await concurrent_limiter.acquire(task_id)
    if not can_acquire:
        # Roll back: mark the DB row failed so it isn't left orphaned
        await executor.mark_task_failed(task_id, reason="Concurrency limit reached; task was not started")
        raise HTTPException(status_code=503, detail=error_msg)

    # Slot is held — schedule execution.
    # execute_task releases the slot in its finally block on every exit path.
    #
    # Use BackgroundTasks so the response can be sent without waiting in real
    # ASGI servers, while tests using TestClient still execute the task to keep
    # contract tests deterministic.
    background_tasks.add_task(executor.execute_task, task_id)
    await invalidate_view_cache()

    return {
        "task_id": task_id,
        "status": "queued",
        "created_at": "now",
        "stream_url": f"/api/v1/task/{task_id}/stream"
    }

@router.post("/task/{task_id}/retry", dependencies=[Depends(task_start_limiter) , Depends(check_scan_rate_limit)])
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    raw_request: Request,
    owner: str = Depends(get_current_owner),
):
    """
    Retry a failed or cancelled scan task.
    """
    db = await get_db()
    task = await require_owned_task(db, task_id, owner, columns="id, owner_id, status, plugin_id")

    if task["status"] in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Task is already queued or running")
    elif task["status"] not in ["failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Only failed or cancelled tasks can be retried")

    # Check plugin rate limits
    plugin_manager = await get_plugin_manager_for_request()
    plugin = plugin_manager.get_plugin(task["plugin_id"])
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {task['plugin_id']}")

    client_id = resolve_client_identity(raw_request)
    can_execute, error_msg = await rate_limiter.can_execute(
        task["plugin_id"],
        plugin.safety.get("rate_limit", {}).get("max_per_hour", settings.max_tasks_per_hour),
        client_id=client_id,
    )

    if not can_execute:
        raise HTTPException(status_code=429, detail=error_msg)

    # Atomic update to prevent duplicate reruns if called rapidly
    cursor = await db.execute(
        "UPDATE tasks SET status = 'queued', error_message = NULL, exit_code = NULL, "
        "started_at = NULL, completed_at = NULL "
        "WHERE id = ? AND status IN ('failed', 'cancelled')",
        (task_id,)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=409, detail="Task is already queued or running")

    # Cleanup previous findings and reports for a fresh retry
    await db.execute("DELETE FROM findings WHERE task_id = ?", (task_id,))
    await db.execute("DELETE FROM reports WHERE task_id = ?", (task_id,))

    # Re-acquire concurrency slot
    can_acquire, error_msg = await concurrent_limiter.acquire(task_id)
    if not can_acquire:
        await executor.mark_task_failed(task_id, reason="Concurrency limit reached; task was not retried")
        raise HTTPException(status_code=503, detail=error_msg)

    background_tasks.add_task(executor.execute_task, task_id)
    await invalidate_view_cache()

    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Task retry initiated"
    }

@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str, owner: str = Depends(get_current_owner)):
    """Get task status"""
    db = await get_db()
    await require_owned_task(db, task_id, owner)

    status = await executor.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status

@router.get("/task/{task_id}/stream")
async def stream_task_output(task_id: str, owner: str = Depends(get_current_owner)):
    """Stream task output via Server-Sent Events (SSE)"""
    import asyncio

    db = await get_db()
    await require_owned_task(db, task_id, owner)

    status = await executor.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        # First, send the initial status and phase
        yield {
            "event": "status",
            "data": json.dumps({"status": status["status"], "scan_phase": status.get("scan_phase")})
        }

        # If it's already completed/failed, we just return the raw output if any and close
        if status["status"] in ["completed", "failed", "cancelled"]:
            try:
                db = await get_db()
                task_row = await db.fetchone("SELECT raw_output_path FROM tasks WHERE id = ?", (task_id,))
                if task_row and task_row["raw_output_path"]:
                    for chunk in iter_raw_output_chunks(task_row["raw_output_path"]):
                        yield {
                            "event": "output",
                            "data": json.dumps({"chunk": chunk})
                        }
            except Exception as exc:
                logger.warning("Failed to replay raw output for task %s: %s", task_id, exc)
            return

        # Subscribe to live events
        queue = executor.subscribe(task_id)
        try:
            # Re-check status after subscribe to close the TOCTOU window:
            # the task may have completed between the initial check and this
            # subscription, so we'd never receive a terminal event.
            current_status = await executor.get_task_status(task_id)
            if current_status and current_status["status"] in ["completed", "failed", "cancelled"]:
                try:
                    db = await get_db()
                    task_row = await db.fetchone("SELECT raw_output_path FROM tasks WHERE id = ?", (task_id,))
                    if task_row and task_row["raw_output_path"]:
                        for chunk in iter_raw_output_chunks(task_row["raw_output_path"]):
                            yield {
                                "event": "output",
                                "data": json.dumps({"chunk": chunk})
                            }
                except Exception as exc:
                    logger.warning("Failed to replay raw output for task %s: %s", task_id, exc)
                yield {
                    "event": "status",
                    "data": json.dumps({"status": current_status["status"]})
                }
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # No event in 30s — check if task is still running
                    ts = await executor.get_task_status(task_id)
                    if ts and ts["status"] not in ["completed", "failed", "cancelled"]:
                        continue
                    break

                if event["type"] == "status":
                    yield {
                        "event": "status",
                        "data": json.dumps({"status": event["data"]})
                    }
                    if event["data"] in ["completed", "failed", "cancelled"]:
                        break
                elif event["type"] == "phase":
                    yield {
                        "event": "phase",
                        "data": json.dumps({"scan_phase": event["data"]})
                    }
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

@router.get("/task/{task_id}/report/csv", dependencies=[Depends(report_download_limiter)])
async def download_csv_report(task_id: str, owner: str = Depends(get_current_owner)):
    """Download task results as a CSV report."""
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, owner_id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")

    if task_row["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task is not finished yet")

    try:
        structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
        csv_data = reporting.generate_csv_report(dict(task_row), {"structured": structured_data})
    except Exception:
        return _report_generation_error_response(task_id, "csv")

    await db.log_audit(
        "report_downloaded",
        f"CSV report downloaded for task {task_id}",
        context={"format": "csv", "task_id": task_id, "plugin_id": task_row["plugin_id"]},
        task_id=task_id,
        plugin_id=task_row["plugin_id"],
    )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{build_report_filename(dict(task_row), "csv")}"'}
    )

@router.get("/task/{task_id}/report/html", dependencies=[Depends(report_download_limiter)])
async def download_html_report(task_id: str, owner: str = Depends(get_current_owner)):
    """Download task results as an HTML report."""
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, owner_id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")

    if task_row["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task is not finished yet")

    try:
        structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
        html_content = reporting.generate_html_report(dict(task_row), {"structured": structured_data})
    except Exception:
        return _report_generation_error_response(task_id, "html")

    await db.log_audit(
        "report_downloaded",
        f"HTML report downloaded for task {task_id}",
        context={"format": "html", "task_id": task_id, "plugin_id": task_row["plugin_id"]},
        task_id=task_id,
        plugin_id=task_row["plugin_id"],
    )

    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{build_report_filename(dict(task_row), "html")}"'}
    )

@router.get("/task/{task_id}/report/pdf", dependencies=[Depends(report_download_limiter)])
async def download_pdf_report(task_id: str, owner: str = Depends(get_current_owner)):
    """Download task results as a PDF report."""
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, owner_id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")

    if task_row["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task is not finished yet")

    try:
        structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
        pdf_bytes = bytes(reporting.generate_pdf_report(dict(task_row), {"structured": structured_data}))
    except Exception:
        return _report_generation_error_response(task_id, "pdf")

    await db.log_audit(
        "report_downloaded",
        f"PDF report downloaded for task {task_id}",
        context={"format": "pdf", "task_id": task_id, "plugin_id": task_row["plugin_id"]},
        task_id=task_id,
        plugin_id=task_row["plugin_id"],
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{build_report_filename(dict(task_row), "pdf")}"'}
    )


@router.get("/task/{task_id}/report/sarif", dependencies=[Depends(report_download_limiter)])
async def download_sarif_report(task_id: str, owner: str = Depends(get_current_owner)):
    """Download task results as a SARIF report."""
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, owner_id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")

    if task_row["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Task is not finished yet")

    try:
        structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
        sarif_data = reporting.generate_sarif_report(dict(task_row), {"structured": structured_data})
    except Exception:
        return _report_generation_error_response(task_id, "sarif")

    await db.log_audit(
        "report_downloaded",
        f"SARIF report downloaded for task {task_id}",
        context={"format": "sarif", "task_id": task_id, "plugin_id": task_row["plugin_id"]},
        task_id=task_id,
        plugin_id=task_row["plugin_id"],
    )

    return Response(
        content=sarif_data,
        media_type="application/sarif+json",
        headers={"Content-Disposition": f'attachment; filename="{build_report_filename(dict(task_row), "sarif")}"'}
    )


@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str, owner: str = Depends(get_current_owner)):
    """Get task execution result"""
    db = await get_db()

    # Enforce ownership and existence check first
    await require_owned_task(db, task_id, owner)

    cache_key = f"tasks:result:{task_id}:{owner}"
    cache = await get_cache()
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return cached

    task_row = await db.fetchone(
        """
        SELECT id, owner_id, plugin_id, tool_name, target, status,
               created_at, duration_seconds, structured_json, preset, inputs_json, execution_context_json,
               raw_output_path, command_used, error_message, exit_code
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

    finding_rows = await db.fetchall(
        "SELECT * FROM findings WHERE owner_id = ? AND task_id = ? ORDER BY (risk_score IS NULL) ASC, risk_score DESC, discovered_at DESC",
        (owner, task_id),
    )
    findings = deserialize_finding_rows(finding_rows)
    asset_rows = await db.fetchall(
        "SELECT * FROM asset_services WHERE owner_id = ? AND task_id = ? ORDER BY created_at DESC",
        (owner, task_id),
    )
    asset_services = deserialize_asset_service_rows(asset_rows)

    if not findings and isinstance(structured, dict):
        findings = [item for item in structured.get("findings", []) if isinstance(item, dict)]

    severity_counts: Dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "info")).lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    finding_groups = structured.get("finding_groups") if isinstance(structured, dict) else None
    if not isinstance(finding_groups, list) or not finding_groups:
        finding_groups = build_finding_groups(findings)

    asset_summary = structured.get("asset_summary") if isinstance(structured, dict) else None
    if not isinstance(asset_summary, list) or not asset_summary:
        asset_summary = build_asset_summary(findings, asset_services)

    scan_diff = structured.get("scan_diff") if isinstance(structured, dict) else None
    if not isinstance(scan_diff, dict):
        scan_diff = {"new": [], "resolved": [], "changed": [], "summary": {"new_count": 0, "resolved_count": 0, "changed_count": 0}}

    if isinstance(structured, dict):
        structured["findings"] = findings
        structured["finding_groups"] = finding_groups
        structured["asset_summary"] = asset_summary
        structured["scan_diff"] = scan_diff
        structured["asset_services"] = asset_services
        structured["severity_counts"] = severity_counts

    structured_summary = structured.get("summary") if isinstance(structured, dict) else None
    summary: List[str] = [
        str(item) for item in structured_summary
        if isinstance(item, (str, int, float)) and str(item).strip()
    ] if isinstance(structured_summary, list) else []
    total_findings = len(findings)
    if not summary and total_findings > 0:
        critical_high = severity_counts.get("critical", 0) + severity_counts.get("high", 0)
        if critical_high > 0:
            summary.append(f"Assessment identified {total_findings} security risks, including {critical_high} high-priority items requiring remediation.")
        else:
            summary.append(f"Assessment identified {total_findings} minor observations; no critical or high-severity threats were found.")
    elif not summary:
        summary.append("Security analysis revealed no significant vulnerabilities or exposed risks.")

    if ports := structured.get("open_ports"):
        summary.append(f"Perimeter analysis confirmed {len(ports)} active network entry points.")

    if techs := structured.get("technologies"):
        summary.append(f"Fingerprinting identified {len(techs)} unique technologies powering the target infrastructure.")

    # Read raw output (limit to 100k for performance, but usually enough)
    raw_output = None
    if task_row["raw_output_path"]:
        try:
            with open(task_row["raw_output_path"], 'r') as f:
                raw_output = f.read(100000)
        except Exception:
            pass

    result = {
        "task_id": task_row["id"],
        "plugin_id": task_row["plugin_id"],
        "tool": task_row["tool_name"],
        "target": task_row["target"],
        "timestamp": task_row["created_at"],
        "duration_seconds": task_row["duration_seconds"],
        "status": task_row["status"],
        "preset": task_row["preset"],
        "inputs": redact_inputs(json.loads(task_row["inputs_json"] or "{}")),
        "execution_context": normalize_execution_context(json.loads(task_row["execution_context_json"] or "{}")),
        "summary": summary,
        "severity_counts": severity_counts,
        "findings": findings,
        "finding_groups": finding_groups,
        "asset_summary": asset_summary,
        "scan_diff": scan_diff,
        "structured": structured,
        "raw_output_path": task_row["raw_output_path"],
        "raw_output_excerpt": raw_output,
        "raw_output": raw_output,
        "command_used": task_row["command_used"],
        "errors": [{"message": redact(task_row["error_message"])}] if task_row["error_message"] else [],
        "error_message": redact(task_row["error_message"]) if task_row["error_message"] else None,
        "exit_code": task_row["exit_code"],
        "metadata": {}
    }

    if task_row["status"] in ["completed", "failed", "cancelled"]:
        await cache.set_json(cache_key, result)

    return result


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str, owner: str = Depends(get_current_owner)):
    """Cancel a running task"""
    db = await get_db()
    await require_owned_task(db, task_id, owner)

    cancelled = await executor.cancel_task(task_id)

    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found or not running")

    return {
        "task_id": task_id,
        "status": "cancelled",
        "cancelled_at": "now"
    }


@router.get("/dashboard/summary", dependencies=[Depends(read_heavy_limiter)])
async def get_dashboard_summary(owner: str = Depends(get_current_owner)):
    """Return the caller's aggregate dashboard data, cached per owner."""

    async def build():
        db = await get_db()

        async def query_or_default(label: str, query_fn: Callable[[], Any], default: Any) -> Any:
            try:
                return await query_fn()
            except Exception as exc:
                logger.warning("Dashboard summary query '%s' failed for owner %s: %s", label, owner, exc)
                return default

        # Get data
        # Push severity aggregation to DB — avoids full table scan in Python.
        # Every aggregate below is scoped to the caller so the dashboard never
        # surfaces another user/workspace's tasks or findings (issue #401).
        severity_rows = await query_or_default(
            "severity_counts",
            lambda: db.fetchall(
                """
                SELECT severity, COUNT(*) AS cnt
                FROM findings
                WHERE owner_id = ?
                GROUP BY severity
                """,
                (owner,),
            ),
            [],
        )
        severity_counts = {row["severity"]: row["cnt"] for row in severity_rows}

        task_stats = await query_or_default(
            "task_stats",
            lambda: db.fetchone(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'running') AS running
                FROM tasks
                WHERE owner_id = ?
                """,
                (owner,),
            ),
            {"total": 0, "completed": 0, "running": 0},
        )

        total_findings_row = await query_or_default(
            "total_findings",
            lambda: db.fetchone(
                "SELECT COUNT(*) AS total FROM findings WHERE owner_id = ?", (owner,)
            ),
            None,
        )
        total_findings = total_findings_row["total"] if total_findings_row else sum(severity_counts.values())

        critical_findings: int = severity_counts.get("critical", 0)
        high_findings: int = severity_counts.get("high", 0)
        medium_findings: int = severity_counts.get("medium", 0)
        low_findings: int = severity_counts.get("low", 0)
        info_findings: int = severity_counts.get("info", 0)

        # Fetch only the 5 most recent findings — not the entire table
        recent_rows = await query_or_default(
            "recent_findings",
            lambda: db.fetchall(
                """
                SELECT id, title, category, severity, target, description,
                    remediation, proof, cvss, cve, discovered_at,
                    validated, validation_method, confidence_reason,
                    service_fingerprint, cpe, risk_score, risk_factors_json,
                    evidence_json, asset_refs_json, references_json, metadata_json
                FROM findings
                WHERE owner_id = ?
                ORDER BY discovered_at DESC
                LIMIT 5
                """,
                (owner,),
            ),
            [],
        )
        recent_findings: List[Dict] = parse_json_fields(
            recent_rows,
            ["metadata_json", "risk_factors_json", "evidence_json", "asset_refs_json", "references_json"],
        )
        for finding in recent_findings:
            if "risk_factors_json" in finding:
                finding["risk_factors"] = finding.pop("risk_factors_json")
            if "evidence_json" in finding:
                finding["evidence"] = finding.pop("evidence_json")
            if "asset_refs_json" in finding:
                finding["asset_refs"] = finding.pop("asset_refs_json")
            if "references_json" in finding:
                finding["references"] = finding.pop("references_json")

        risk_scores = [
            f.get("risk_score") for f in recent_findings
            if isinstance(f.get("risk_score"), (int, float))
        ]
        avg_risk_score = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else None

        return {
            "total_findings": total_findings,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "info_findings": info_findings,
            "avg_risk_score": avg_risk_score,
            "last_scan_time": recent_findings[0].get("discovered_at") if recent_findings else None,
            "recent_findings": recent_findings,
            "scan_activity": {
                "total": int(task_stats["total"]) if task_stats and task_stats.get("total") is not None else 0,
                "completed": int(task_stats["completed"]) if task_stats and task_stats.get("completed") is not None else 0,
                "running": int(task_stats["running"]) if task_stats and task_stats.get("running") is not None else 0,
            },
            "running_tasks": parse_json_fields(
                await query_or_default(
                    "running_tasks",
                    lambda: db.fetchall(
                        "SELECT id, plugin_id, tool_name, target, status, created_at FROM tasks WHERE owner_id = ? AND status = 'running' ORDER BY created_at DESC LIMIT 5",
                        (owner,),
                    ),
                    [],
                ),
                []
            ),
            "recent_tasks": parse_json_fields(
                await query_or_default(
                    "recent_tasks",
                    lambda: db.fetchall(
                        "SELECT id, plugin_id, tool_name, target, status, created_at, duration_seconds FROM tasks WHERE owner_id = ? ORDER BY created_at DESC LIMIT 5",
                        (owner,),
                    ),
                    [],
                ),
                []
            )
        }

    return await get_or_set_cached(f"summary:dashboard:{owner}", build)


@router.get("/findings", dependencies=[Depends(read_heavy_limiter)])
async def get_findings(
    owner: str = Depends(get_current_owner),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Return the caller's vulnerability findings with pagination."""

    async def build():
        db = await get_db()
        offset = (page - 1) * per_page
        rows = await db.fetchall(
            "SELECT * FROM findings WHERE owner_id = ? ORDER BY discovered_at DESC LIMIT ? OFFSET ?",
            (owner, per_page, offset),
        )
        total_row = await db.fetchone(
            "SELECT COUNT(*) as count FROM findings WHERE owner_id = ?",
            (owner,),
        )
        total = total_row["count"] if total_row else 0
        findings = deserialize_finding_rows(rows)
        # Build finding_groups from *all* findings so group counts remain accurate
        # regardless of which page is being viewed.
        all_rows = await db.fetchall(
            "SELECT * FROM findings WHERE owner_id = ? ORDER BY discovered_at DESC",
            (owner,),
        )
        all_findings = deserialize_finding_rows(all_rows)
        return {
            "findings": findings,
            "finding_groups": build_finding_groups(all_findings),
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    # Cache key includes pagination params so different pages do not collide.
    return await get_or_set_cached(f"findings:list:{owner}:page={page}:per_page={per_page}", build)


@router.get("/finding-groups", dependencies=[Depends(read_heavy_limiter)])
async def get_finding_groups(
    owner: str = Depends(get_current_owner),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    async def build():
        db = await get_db()
        rows = await db.fetchall(
            "SELECT * FROM findings WHERE owner_id = ? ORDER BY discovered_at DESC",
            (owner,),
        )
        findings = deserialize_finding_rows(rows)
        # Groups are always computed from *all* findings so the returned
        # groups represent the full picture, not a subset.
        return {
            "groups": build_finding_groups(findings),
            "total": len(findings),
            "page": page,
            "per_page": per_page,
        }

    return await get_or_set_cached(f"findings:groups:{owner}:page={page}:per_page={per_page}", build)


@router.get("/task/{task_id}/diff", dependencies=[Depends(read_heavy_limiter)])
async def get_task_diff(task_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT owner_id, structured_json FROM tasks WHERE id = ?",
        (task_id,),
    )
    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")
    if task_row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")

    structured = {}
    if task_row["structured_json"]:
        try:
            structured = json.loads(task_row["structured_json"])
        except json.JSONDecodeError:
            structured = {}
    diff = structured.get("scan_diff") if isinstance(structured, dict) else None
    if not isinstance(diff, dict):
        diff = {"new": [], "resolved": [], "changed": [], "summary": {"new_count": 0, "resolved_count": 0, "changed_count": 0}}
    return diff


@router.get("/reports", dependencies=[Depends(read_heavy_limiter)])
async def get_reports(owner: str = Depends(get_current_owner)):
    """Return the caller's generated reports."""

    async def build():
        db = await get_db()
        rows = await db.fetchall(
            "SELECT * FROM reports WHERE owner_id = ? ORDER BY generated_at DESC",
            (owner,),
        )
        return {"reports": parse_json_fields(rows, ["metadata_json"])}

    return await get_or_set_cached(f"reports:list:{owner}", build)


@router.get("/tasks", dependencies=[Depends(read_heavy_limiter)])
async def list_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    plugin_id: Optional[str] = None,
    status: Optional[str] = None,
    owner: str = Depends(get_current_owner),
):
    """List the caller's tasks with pagination"""
    db = await get_db()

    # Build query — always scoped to the caller so listing can never enumerate
    # another user/workspace's tasks (issue #401).
    query = "SELECT id, plugin_id, tool_name, target, status, created_at, duration_seconds, inputs_json, execution_context_json, preset, error_message, exit_code FROM tasks"
    params = [owner]

    where_clauses = ["owner_id = ?"]
    if plugin_id:
        where_clauses.append("plugin_id = ?")
        params.append(plugin_id)
    if status:
        try:
            status = TaskStatus(status).value
        except ValueError:
            allowed_values = ", ".join([s.value for s in TaskStatus])
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task status '{status}'. Allowed values: {allowed_values}"
            )

        where_clauses.append("status = ?")
        params.append(status)

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
    tasks_list = parse_json_fields(tasks, ["structured_json", "config_json", "metadata_json", "inputs_json", "execution_context_json"])
    for t in tasks_list:
        if "id" in t:
            t["task_id"] = t.pop("id")
        t["inputs"] = redact_inputs(t.pop("inputs_json", {}) or {})
        t["execution_context"] = t.pop("execution_context_json", {}) or {}

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    # Calculate next and previous page numbers
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None

    def build_page_url(page_num):
        if page_num is None:
            return None
        query_params = {
            "page": page_num,
            "per_page": per_page,
        }
        if plugin_id:
            query_params["plugin_id"] = plugin_id
        if status:
            query_params["status"] = status
        return f"/api/v1/tasks?{urlencode(query_params)}"
    return {
        "tasks": tasks_list,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total,
            "next": build_page_url(next_page),
            "previous": build_page_url(prev_page)
        }
    }


SQLITE_CHUNK_SIZE = 500  # safely under SQLITE_LIMIT_VARIABLE_NUMBER = 999

async def delete_task_records(task_ids: List[str]):
    """Helper to delete database records and files for multiple tasks.

    Processes IDs in chunks of SQLITE_CHUNK_SIZE to stay under
    SQLite's SQLITE_LIMIT_VARIABLE_NUMBER = 999 limit.

    The deletion is wrapped in a transaction so that a failure mid-way
    (e.g. crash, constraint violation) does not leave orphaned records.
    """
    if not task_ids:
        return

    db = await get_db()

    # Collect all raw_output_paths across chunks for file cleanup
    all_task_rows = []
    for i in range(0, len(task_ids), SQLITE_CHUNK_SIZE):
        chunk = task_ids[i : i + SQLITE_CHUNK_SIZE]
        placeholders = ",".join(["?"] * len(chunk))
        rows = await db.fetchall(
            f"SELECT raw_output_path FROM tasks WHERE id IN ({placeholders})",
            tuple(chunk)
        )
        all_task_rows.extend(rows)

    # Delete associated records in chunks, atomic within a transaction
    async with db.transaction():
        # Re-check running status inside the transaction to prevent the
        # race where a task starts running between the check and the delete.
        for i in range(0, len(task_ids), SQLITE_CHUNK_SIZE):
            chunk = task_ids[i : i + SQLITE_CHUNK_SIZE]
            placeholders = ",".join(["?"] * len(chunk))
            running = await db.fetchone(
                f"SELECT 1 FROM tasks WHERE id IN ({placeholders}) AND status = 'running' LIMIT 1",
                tuple(chunk)
            )
            if running:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete running tasks. Abort them first."
                )

        for i in range(0, len(task_ids), SQLITE_CHUNK_SIZE):
            chunk = task_ids[i : i + SQLITE_CHUNK_SIZE]
            placeholders = ",".join(["?"] * len(chunk))
            # Delete notification_history first (depends on findings via finding_id)
            await db.execute_no_commit(
                f"DELETE FROM notification_history WHERE finding_id IN (SELECT id FROM findings WHERE task_id IN ({placeholders}))", tuple(chunk)
            )
            await db.execute_no_commit(
                f"DELETE FROM findings             WHERE task_id IN ({placeholders})", tuple(chunk)
            )
            await db.execute_no_commit(
                f"DELETE FROM reports              WHERE task_id IN ({placeholders})", tuple(chunk)
            )
            await db.execute_no_commit(
                f"DELETE FROM audit_log            WHERE task_id IN ({placeholders})", tuple(chunk)
            )
            await db.execute_no_commit(
                f"DELETE FROM crawl_runs           WHERE task_id IN ({placeholders})", tuple(chunk)
            )
            await db.execute_no_commit(
                f"DELETE FROM asset_services       WHERE task_id IN ({placeholders})", tuple(chunk)
            )
            await db.execute_no_commit(
                f"DELETE FROM tasks                WHERE id         IN ({placeholders})", tuple(chunk)
            )

    # Cleanup files on disk (outside the transaction — file deletion is not
    # transactional; a failure here does not leave the DB in an inconsistent
    # state).
    for row in all_task_rows:
        if row and row["raw_output_path"]:
            try:
                path = Path(row["raw_output_path"])
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete raw output file {row['raw_output_path']}: {e}")

@router.delete("/task/{task_id}")
async def delete_task(task_id: str, owner: str = Depends(get_current_owner)):
    """Delete a task and its associated data (findings, reports, audit logs, and files)"""
    db = await get_db()

    # Deleting a non-existent task stays idempotent (200, deletes zero rows),
    # but a task owned by another user/workspace is rejected with 403 so it
    # cannot be deleted across owners (issue #401).
    existing = await db.fetchone("SELECT owner_id FROM tasks WHERE id = ?", (task_id,))
    if existing is not None and existing["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this task")

    # Check if task is running
    status = await executor.get_task_status(task_id)
    if status and status.get("status") == "running":
        raise HTTPException(status_code=400, detail="Cannot delete a running task. Abort it first.")

    # If the task is currently executing but the DB hasn't been updated yet, fail closed.
    if task_id in executor.running_tasks:
        raise HTTPException(status_code=400, detail="Cannot delete a running task. Abort it first.")

    await delete_task_records([task_id])
    await invalidate_view_cache()

    return {
        "task_id": task_id,
        "deleted": True
    }


@router.delete("/tasks/bulk", dependencies=[Depends(admin_limiter)])
async def bulk_delete_tasks(request: BulkDeleteRequest, owner: str = Depends(get_current_owner)):
    """Delete multiple tasks at once (max 500 IDs per request)"""
    task_ids = request.root  # RootModel exposes data via .root
    db = await get_db()

    # Empty list — return early cleanly (test requires 200, not 422)
    if not task_ids:
        return {"deleted_count": 0, "success": True}

    # Scope to tasks owned by the caller. IDs owned by another user/workspace
    # are silently ignored so cross-user enumeration and deletion are
    # impossible (issue #401). len(task_ids) <= 500 guaranteed by Pydantic.
    placeholders = ",".join(["?"] * len(task_ids))
    owned_rows = await db.fetchall(
        f"SELECT id FROM tasks WHERE id IN ({placeholders}) AND owner_id = ?",
        tuple(task_ids) + (owner,),
    )
    owned_ids = [row["id"] for row in owned_rows]
    if not owned_ids:
        return {"deleted_count": 0, "success": True}

    # Check running tasks among the caller's own tasks
    placeholders = ",".join(["?"] * len(owned_ids))
    running_tasks = await db.fetchone(
        f"SELECT id FROM tasks WHERE id IN ({placeholders}) AND status = 'running' LIMIT 1",
        tuple(owned_ids)
    )
    if running_tasks:
        raise HTTPException(status_code=400, detail="Cannot delete running tasks. Abort them first.")

    # If the task is currently executing but the DB hasn't been updated yet, fail closed.
    if any(tid in executor.running_tasks for tid in owned_ids):
        raise HTTPException(status_code=400, detail="Cannot delete running tasks. Abort them first.")

    await delete_task_records(owned_ids)
    await invalidate_view_cache()

    return {
        "deleted_count": len(owned_ids),
        "success": True
    }

@router.delete("/tasks/clear", dependencies=[Depends(admin_limiter)])
async def clear_all_tasks(owner: str = Depends(get_current_owner)):
    """Wipe the caller's scan history and associated data (findings, reports).

    Scoped to the requesting user/workspace so one owner cannot purge another
    owner's history (issue #401).
    """
    db = await get_db()

    # Prevent clearing if any of the caller's tasks are running
    running_tasks = await db.fetchone(
        "SELECT id FROM tasks WHERE owner_id = ? AND status = 'running' LIMIT 1",
        (owner,),
    )
    if running_tasks:
        raise HTTPException(status_code=400, detail="Cannot clear history while tasks are running.")

    # Get the caller's task IDs to delete records and cleanup files
    own_tasks = await db.fetchall("SELECT id FROM tasks WHERE owner_id = ?", (owner,))
    task_ids = [t["id"] for t in own_tasks]
    if task_ids:
        await delete_task_records(task_ids)

    # Sweep up any of the caller's findings not linked to a task (task_id was
    # set NULL by ON DELETE) so nothing of theirs is left behind.
    await db.execute("DELETE FROM findings WHERE owner_id = ?", (owner,))

    await invalidate_view_cache()

    return {
        "cleared": True,
        "message": "All scan history and associated data has been purged."
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
        },
        "execution_context": {
            "validation_modes": [mode.value for mode in ValidationMode],
            "evidence_levels": [level.value for level in EvidenceLevel],
            "default": ExecutionContext().model_dump(),
        }
    }


@router.get("/vault", dependencies=[Depends(vault_limiter)])
async def list_vault_secrets(
    owner: str = Depends(get_current_owner),
):
    db = await get_db()
    rows = await db.fetchall(
        """
        SELECT id, name, created_at, updated_at
        FROM credential_vault
        WHERE owner_id = ?
        ORDER BY name ASC
        """,
        (owner,),
    )
    return {"items": rows, "total": len(rows)}


@router.put("/vault/{name}", dependencies=[Depends(vault_limiter)])
async def upsert_vault_secret(
    name: str,
    payload: Dict[str, str],
    owner: str = Depends(get_current_owner),
):
    value = str(payload.get("value", ""))
    if not value:
        raise HTTPException(status_code=400, detail="Secret value is required")

    db = await get_db()
    crypto = VaultCrypto(settings.resolved_vault_key)
    encrypted = crypto.encrypt(value)
    secret_id = str(uuid.uuid4())

    async with db.transaction():
        existing = await db.fetchone(
            "SELECT id FROM credential_vault WHERE owner_id = ? AND name = ?",
            (owner, name),
        )
        if existing:
            await db.execute(
                "UPDATE credential_vault SET encrypted_value = ?, updated_at = datetime('now') WHERE owner_id = ? AND name = ?",
                (encrypted, owner, name),
            )
        else:
            await db.execute(
                "INSERT INTO credential_vault (id, owner_id, name, encrypted_value) VALUES (?, ?, ?, ?)",
                (secret_id, owner, name, encrypted),
            )
    return {"name": name, "stored": True}

@router.get("/vault/{name}", dependencies=[Depends(vault_limiter)])
async def get_vault_secret(
    name: str,
    owner: str = Depends(get_current_owner),
):
    db = await get_db()

    row = await db.fetchone(
        """
        SELECT encrypted_value
        FROM credential_vault
        WHERE owner_id = ? AND name = ?
        """,
        (owner, name),
    )

    if not row:
        raise HTTPException(status_code=404, detail="Secret not found")

    crypto = VaultCrypto(settings.resolved_vault_key)

    return {
        "name": name,
        "value": crypto.decrypt(row["encrypted_value"]),
    }

@router.delete("/vault/{name}", dependencies=[Depends(vault_limiter)])
async def delete_vault_secret(
    name: str,
    owner: str = Depends(get_current_owner),
):
    db = await get_db()


    cursor = await db.execute(
        """
        DELETE FROM credential_vault
        WHERE owner_id = ? AND name = ?
        """,
        (owner, name),
    )

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Secret not found")

    return {
        "name": name,
        "deleted": True,
    }

@router.get("/target-policies")
async def list_target_policies(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM target_policies WHERE owner_id = ? ORDER BY updated_at DESC, created_at DESC",
        (owner,),
    )
    return {"items": deserialize_resource_rows(rows), "total": len(rows)}


def _validate_lengths(
    name: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    resource_type: str = "Resource",
):
    if name is not None and len(str(name).strip()) > 255:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_type} name exceeds maximum length of 255 characters",
        )
    if description is not None and len(str(description).strip()) > 2000:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_type} description exceeds maximum length of 2000 characters",
        )
    if notes is not None and len(str(notes).strip()) > 2000:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_type} notes exceeds maximum length of 2000 characters",
        )


@router.post("/target-policies", dependencies=[Depends(admin_limiter)])
async def create_target_policy(payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Target policy name is required")
    description = str(payload.get("description", "")).strip()
    _validate_lengths(name=name, description=description, resource_type="Target policy")

    allowed = payload.get("allowed_targets")
    if allowed is not None and not isinstance(allowed, list):
        raise HTTPException(status_code=400, detail="allowed_targets must be a list")

    policy_id = str(uuid.uuid4())
    db = await get_db()
    await db.execute(
        """
        INSERT INTO target_policies (
            id, owner_id, name, description, allow_public_targets,
            allow_exploit_validation, allow_authenticated_scan, default_validation_mode,
            allowed_targets_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_id,
            owner,
            name,
            description or None,
            1 if payload.get("allow_public_targets") else 0,
            1 if payload.get("allow_exploit_validation") else 0,
            1 if payload.get("allow_authenticated_scan") else 0,
            str(payload.get("default_validation_mode") or ValidationMode.PROOF.value),
            _json_payload(payload.get("allowed_targets"), "[]"),
            _json_payload(payload.get("metadata"), "{}"),
        ),
    )
    row = await db.fetchone("SELECT * FROM target_policies WHERE id = ?", (policy_id,))
    return deserialize_resource_rows([row])[0] if row else {"id": policy_id}


@router.patch("/target-policies/{policy_id}", dependencies=[Depends(admin_limiter)])
async def update_target_policy(policy_id: str, payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    db = await get_db()
    row = await db.fetchone("SELECT id FROM target_policies WHERE id = ? AND owner_id = ?", (policy_id, owner))
    if not row:
        raise HTTPException(status_code=404, detail="Target policy not found")

    if "name" in payload or "description" in payload:
        _validate_lengths(
            name=payload.get("name"),
            description=payload.get("description"),
            resource_type="Target policy",
        )

    updates: List[str] = []
    params: List[Any] = []
    for key in ("name", "description", "default_validation_mode"):
        if key in payload:
            updates.append(f"{key} = ?")
            params.append(str(payload[key]).strip() if payload[key] is not None else None)
    for key in ("allow_public_targets", "allow_exploit_validation", "allow_authenticated_scan"):
        if key in payload:
            updates.append(f"{key} = ?")
            params.append(1 if payload[key] else 0)
    if "allowed_targets" in payload:
        updates.append("allowed_targets_json = ?")
        params.append(_json_payload(payload["allowed_targets"], "[]"))
    if "metadata" in payload:
        updates.append("metadata_json = ?")
        params.append(_json_payload(payload["metadata"], "{}"))
    updates.append("updated_at = datetime('now')")
    params.extend([policy_id, owner])
    await db.execute(f"UPDATE target_policies SET {', '.join(updates)} WHERE id = ? AND owner_id = ?", tuple(params))
    updated = await db.fetchone("SELECT * FROM target_policies WHERE id = ?", (policy_id,))
    return deserialize_resource_rows([updated])[0] if updated else {"id": policy_id, "updated": True}


@router.delete("/target-policies/{policy_id}", dependencies=[Depends(admin_limiter)])
async def delete_target_policy(policy_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    await db.execute("DELETE FROM target_policies WHERE id = ? AND owner_id = ?", (policy_id, owner))
    return {"id": policy_id, "deleted": True}


@router.get("/credential-profiles")
async def list_credential_profiles(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM credential_profiles WHERE owner_id = ? ORDER BY updated_at DESC, created_at DESC",
        (owner,),
    )
    return {"items": deserialize_resource_rows(rows), "total": len(rows)}


@router.post("/credential-profiles", dependencies=[Depends(admin_limiter)])
async def create_credential_profile(payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Credential profile name is required")
    _validate_lengths(name=name, resource_type="Credential profile")

    profile_id = str(uuid.uuid4())
    db = await get_db()
    await db.execute(
        """
        INSERT INTO credential_profiles (
            id, owner_id, name, username_secret_name, password_secret_name,
            extra_headers_json, login_recipe_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile_id,
            owner,
            name,
            payload.get("username_secret_name"),
            payload.get("password_secret_name"),
            _json_payload(payload.get("extra_headers"), "{}"),
            _json_payload(payload.get("login_recipe"), "{}"),
        ),
    )
    row = await db.fetchone("SELECT * FROM credential_profiles WHERE id = ?", (profile_id,))
    return deserialize_resource_rows([row])[0] if row else {"id": profile_id}


@router.patch("/credential-profiles/{profile_id}", dependencies=[Depends(admin_limiter)])
async def update_credential_profile(profile_id: str, payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    db = await get_db()
    row = await db.fetchone("SELECT id FROM credential_profiles WHERE id = ? AND owner_id = ?", (profile_id, owner))
    if not row:
        raise HTTPException(status_code=404, detail="Credential profile not found")

    if "name" in payload:
        _validate_lengths(name=payload.get("name"), resource_type="Credential profile")

    updates: List[str] = []
    params: List[Any] = []
    for key in ("name", "username_secret_name", "password_secret_name"):
        if key in payload:
            updates.append(f"{key} = ?")
            params.append(payload[key])
    if "extra_headers" in payload:
        updates.append("extra_headers_json = ?")
        params.append(_json_payload(payload["extra_headers"], "{}"))
    if "login_recipe" in payload:
        updates.append("login_recipe_json = ?")
        params.append(_json_payload(payload["login_recipe"], "{}"))
    updates.append("updated_at = datetime('now')")
    params.extend([profile_id, owner])
    await db.execute(f"UPDATE credential_profiles SET {', '.join(updates)} WHERE id = ? AND owner_id = ?", tuple(params))
    updated = await db.fetchone("SELECT * FROM credential_profiles WHERE id = ?", (profile_id,))
    return deserialize_resource_rows([updated])[0] if updated else {"id": profile_id, "updated": True}


@router.delete("/credential-profiles/{profile_id}", dependencies=[Depends(admin_limiter)])
async def delete_credential_profile(profile_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    await db.execute("DELETE FROM credential_profiles WHERE id = ? AND owner_id = ?", (profile_id, owner))
    return {"id": profile_id, "deleted": True}


@router.get("/session-profiles")
async def list_session_profiles(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM session_profiles WHERE owner_id = ? ORDER BY updated_at DESC, created_at DESC",
        (owner,),
    )
    return {"items": deserialize_resource_rows(rows), "total": len(rows)}


@router.post("/session-profiles", dependencies=[Depends(admin_limiter)])
async def create_session_profile(payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Session profile name is required")
    notes = str(payload.get("notes", "")).strip()
    _validate_lengths(name=name, notes=notes, resource_type="Session profile")

    profile_id = str(uuid.uuid4())
    db = await get_db()
    await db.execute(
        """
        INSERT INTO session_profiles (
            id, owner_id, name, cookie_secret_name, extra_headers_json, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            profile_id,
            owner,
            name,
            payload.get("cookie_secret_name"),
            _json_payload(payload.get("extra_headers"), "{}"),
            notes or None,
        ),
    )
    row = await db.fetchone("SELECT * FROM session_profiles WHERE id = ?", (profile_id,))
    return deserialize_resource_rows([row])[0] if row else {"id": profile_id}


@router.patch("/session-profiles/{profile_id}", dependencies=[Depends(admin_limiter)])
async def update_session_profile(profile_id: str, payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    db = await get_db()
    row = await db.fetchone("SELECT id FROM session_profiles WHERE id = ? AND owner_id = ?", (profile_id, owner))
    if not row:
        raise HTTPException(status_code=404, detail="Session profile not found")

    if "name" in payload or "notes" in payload:
        _validate_lengths(
            name=payload.get("name"),
            notes=payload.get("notes"),
            resource_type="Session profile",
        )

    updates: List[str] = []
    params: List[Any] = []
    for key in ("name", "cookie_secret_name", "notes"):
        if key in payload:
            updates.append(f"{key} = ?")
            params.append(payload[key])
    if "extra_headers" in payload:
        updates.append("extra_headers_json = ?")
        params.append(_json_payload(payload["extra_headers"], "{}"))
    updates.append("updated_at = datetime('now')")
    params.extend([profile_id, owner])
    await db.execute(f"UPDATE session_profiles SET {', '.join(updates)} WHERE id = ? AND owner_id = ?", tuple(params))
    updated = await db.fetchone("SELECT * FROM session_profiles WHERE id = ?", (profile_id,))
    return deserialize_resource_rows([updated])[0] if updated else {"id": profile_id, "updated": True}


@router.delete("/session-profiles/{profile_id}", dependencies=[Depends(admin_limiter)])
async def delete_session_profile(profile_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    await db.execute("DELETE FROM session_profiles WHERE id = ? AND owner_id = ?", (profile_id, owner))
    return {"id": profile_id, "deleted": True}


@router.get("/crawl-runs")
async def list_crawl_runs(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM crawl_runs WHERE owner_id = ? ORDER BY created_at DESC",
        (owner,),
    )
    return {"items": deserialize_resource_rows(rows), "total": len(rows)}


@router.get("/assets/services")
async def list_asset_services(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM asset_services WHERE owner_id = ? ORDER BY created_at DESC",
        (owner,),
    )
    return {"items": deserialize_asset_service_rows(rows), "total": len(rows)}


@router.get("/knowledgebase/status")
async def get_knowledgebase_status():
    return KnowledgeBase().status()


@router.get("/workflows")
async def list_workflows(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM workflows WHERE owner_id = ? ORDER BY created_at DESC",
        (owner,),
    )
    workflows = [_serialize_workflow(row) for row in rows]
    return {"workflows": workflows, "total": len(workflows)}


@router.post("/workflows", dependencies=[Depends(admin_limiter)])
async def create_workflow(payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Workflow name is required")
    _validate_lengths(name=name, resource_type="Workflow")

    steps = _parse_workflow_steps(payload.get("steps", []))
    if not steps:
        raise HTTPException(status_code=400, detail="Workflow requires at least one step")

    schedule_timezone = payload.get("schedule_timezone")
    if schedule_timezone is not None:
        from .workflows import validate_schedule_timezone
        is_valid, err_msg = validate_schedule_timezone(schedule_timezone)
        if not is_valid:
            raise HTTPException(status_code=400, detail=err_msg)
        schedule_timezone = schedule_timezone.strip()

    workflow_id = str(uuid.uuid4())
    schedule_seconds = payload.get("schedule_seconds")
    if schedule_seconds is not None:
        try:
            parsed_schedule = int(schedule_seconds)
            if parsed_schedule < 60:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid schedule_seconds, must be an integer >= 60")
    else:
        parsed_schedule = None

    enabled = bool(payload.get("enabled", True))
    db = await get_db()
    await db.execute(
        """
        INSERT INTO workflows (id, name, owner_id, schedule_seconds, enabled, steps_json, schedule_timezone)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workflow_id,
            name,
            owner,
            parsed_schedule,
            1 if enabled else 0,
            json.dumps(steps),
            schedule_timezone,
        ),
    )
    row = await db.fetchone("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    return _serialize_workflow(row) if row else {"id": workflow_id, "created": True}


async def _verify_workflow_owner(db, workflow_id: str, owner: str):
    """Check the workflow exists and belongs to the caller. Returns the row or raises 404/403."""
    row = await db.fetchone(
        "SELECT * FROM workflows WHERE id = ?", (workflow_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this workflow")
    return row


@router.post("/workflows/{workflow_id}/run", dependencies=[Depends(check_scan_rate_limit)])
async def run_workflow_once(workflow_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    row = await _verify_workflow_owner(db, workflow_id, owner)
    wf_rate_ok, wf_rate_msg = await workflow_rate_limiter.check_workflow_rate_limit(
        workflow_id, settings.workflow_min_interval_seconds
    )
    if not wf_rate_ok:
        raise HTTPException(status_code=429, detail=wf_rate_msg)
    steps = _parse_workflow_steps(row["steps_json"] or "[]")
    active_version = await db.fetchone(
        "SELECT id, version_number FROM workflow_versions "
        "WHERE workflow_id = ? ORDER BY version_number DESC LIMIT 1",
        (workflow_id,),
    )
    if not active_version:
        active_version = await db.snapshot_workflow_version(
            workflow_id=workflow_id,
            name=row["name"],
            schedule_seconds=row["schedule_seconds"],
            enabled=bool(row["enabled"]),
            steps=steps,
            created_by="system",
        )
    version_id = active_version["id"]
    version_number = active_version["version_number"]
    created_task_ids: List[str] = []
    for step in steps:
        execution_context = normalize_execution_context(step.get("execution_context") or {})
        target_policy = await get_target_policy(db, owner, execution_context.get("target_policy_id"))
        safe_mode = bool(
            settings.safe_mode_default
            and not (target_policy and target_policy.get("allow_public_targets"))
        )
        effective_inputs = dict(step.get("inputs", {}) or {})
        effective_inputs.pop("safe_mode", None)
        effective_inputs["safe_mode"] = safe_mode
        task_id = await executor.create_task(
            step.get("plugin_id"),
            effective_inputs,
            safe_mode=safe_mode,
            preset=step.get("preset"),
            execution_context=execution_context,
            consent_granted=True,
            owner_id=owner,
        )

        can_acquire, concurrency_err = await concurrent_limiter.acquire(task_id)
        if not can_acquire:
            await executor.mark_task_failed(task_id, reason="Concurrency limit reached; task was not started")
            logger.warning("Workflow %s: concurrency limit reached for step %s", workflow_id, step.get("plugin_id"))
            continue

        asyncio.create_task(executor.execute_task(task_id))
        created_task_ids.append(task_id)
    await db.execute("UPDATE workflows SET last_run_at = datetime('now') WHERE id = ?", (workflow_id,))
    run_id = await db.record_workflow_run(
        workflow_id=workflow_id,
        version_id=version_id,
        version_number=version_number,
        task_ids=created_task_ids,
        triggered_by="manual",
    )
    asyncio.create_task(_finalize_workflow_run(run_id))
    return {
        "workflow_id": workflow_id,
        "run_id": run_id,
        "version_number": version_number,
        "queued_task_ids": created_task_ids,
        "queued_tasks": created_task_ids,
    }



@router.get("/workflows/{workflow_id}/runs")
async def list_workflow_runs(workflow_id: str, owner: str = Depends(get_current_owner), limit: int = 50, offset: int = 0):
    """Return paginated run history for a workflow."""
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be non-negative")
    db = await get_db()
    await _verify_workflow_owner(db, workflow_id, owner)
    return await db.get_workflow_runs(workflow_id=workflow_id, limit=limit, offset=offset)


@router.get("/workflows/{workflow_id}/versions")
async def list_workflow_versions(workflow_id: str, owner: str = Depends(get_current_owner)):
    """Return all saved version snapshots for a workflow, newest first."""
    db = await get_db()
    await _verify_workflow_owner(db, workflow_id, owner)
    versions = await db.get_workflow_versions(workflow_id=workflow_id)
    return {"workflow_id": workflow_id, "versions": versions, "total": len(versions)}


@router.post("/workflows/{workflow_id}/rollback/{version_number}")
async def rollback_workflow(workflow_id: str, version_number: int, owner: str = Depends(get_current_owner)):
    """Restore a workflow to a previously saved version.

    The target version's full definition replaces the live workflow fields.
    A new version snapshot is recorded so the rollback itself is auditable
    and can be rolled back in turn.
    """
    db = await get_db()
    wf = await _verify_workflow_owner(db, workflow_id, owner)
    target = await db.get_workflow_version(workflow_id, version_number)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for this workflow",
        )
    defn = target["definition"]
    name = defn.get("name", wf["name"])
    steps = defn.get("steps", [])
    schedule_seconds = defn.get("schedule_seconds")
    schedule_timezone = defn.get("schedule_timezone")
    enabled = bool(defn.get("enabled", True))
    await db.execute(
        "UPDATE workflows SET name = ?, steps_json = ?, schedule_seconds = ?, enabled = ?, schedule_timezone = ? WHERE id = ?",
        (name, json.dumps(steps), schedule_seconds, 1 if enabled else 0, schedule_timezone, workflow_id),
    )
    new_version = await db.snapshot_workflow_version(
        workflow_id=workflow_id,
        name=name,
        schedule_seconds=schedule_seconds,
        enabled=enabled,
        steps=steps,
        created_by=f"rollback_to_v{version_number}",
        schedule_timezone=schedule_timezone,
    )
    updated = await db.fetchone("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    return {
        "workflow_id": workflow_id,
        "rolled_back_to_version": version_number,
        "new_version_number": new_version["version_number"],
        "workflow": _serialize_workflow(updated) if updated else None,
    }


@router.patch("/workflows/{workflow_id}", dependencies=[Depends(admin_limiter)])
async def update_workflow(workflow_id: str, payload: Dict[str, Any], owner: str = Depends(get_current_owner)):
    db = await get_db()
    row = await _verify_workflow_owner(db, workflow_id, owner)

    if "name" in payload:
        _validate_lengths(name=payload.get("name"), resource_type="Workflow")

    old_enabled = bool(row["enabled"])
    new_enabled = old_enabled
    enabled_changed = False

    updates = []
    params: List[Any] = []
    if "name" in payload:
        updates.append("name = ?")
        params.append(str(payload["name"]).strip())
    if "steps" in payload:
        updates.append("steps_json = ?")
        params.append(json.dumps(_parse_workflow_steps(payload["steps"])))
    if "schedule_seconds" in payload:
        val = payload["schedule_seconds"]
        updates.append("schedule_seconds = ?")
        params.append(int(val) if val else None)
    if "schedule_timezone" in payload:
        tz_val = payload["schedule_timezone"]
        if tz_val is not None:
            from .workflows import validate_schedule_timezone
            is_valid, err_msg = validate_schedule_timezone(tz_val)
            if not is_valid:
                raise HTTPException(status_code=400, detail=err_msg)
            updates.append("schedule_timezone = ?")
            params.append(tz_val.strip())
        else:
            updates.append("schedule_timezone = ?")
            params.append(None)
    if "enabled" in payload:
        new_enabled = bool(payload["enabled"])

        updates.append("enabled = ?")
        params.append(1 if new_enabled else 0)

        enabled_changed = (new_enabled != old_enabled)
    params.append(workflow_id)
    await db.execute(f"UPDATE workflows SET {', '.join(updates)} WHERE id = ?", tuple(params))
    updated = await db.fetchone("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    if updated is None:
        return {"workflow_id": workflow_id, "updated": True}
    await db.snapshot_workflow_version(
        workflow_id=workflow_id,
        name=updated["name"],
        schedule_seconds=updated["schedule_seconds"],
        enabled=bool(updated["enabled"]),
        steps=json.loads(updated["steps_json"] or "[]"),
        created_by="patch",
        schedule_timezone=updated["schedule_timezone"],
    )

    if enabled_changed:
        await db.log_audit(
            event_type=(
                "workflow_enabled"
                if new_enabled
                else "workflow_disabled"
            ),
            message=(
                f"Workflow {workflow_id} "
                f"{'enabled' if new_enabled else 'disabled'}"
            ),
            context={
                "workflow_id": workflow_id,
                "actor": owner,
                "previous_state": old_enabled,
                "new_state": new_enabled,
            },
        )
    return _serialize_workflow(updated)


@router.delete("/workflows/{workflow_id}", dependencies=[Depends(admin_limiter)])
async def delete_workflow(workflow_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    await _verify_workflow_owner(db, workflow_id, owner)
    await db.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    return {"workflow_id": workflow_id, "deleted": True}


@router.post("/workflows/scheduler/tick", dependencies=[Depends(scheduler_tick_limiter), Depends(check_scan_rate_limit)])
async def trigger_workflow_tick():
    await scheduler.tick()
    return {"tick": "ok"}


@router.get("/notifications/rules")
async def list_notification_rules(owner: str = Depends(get_current_owner)):
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM notification_rules WHERE owner_id = ? ORDER BY created_at DESC",
        (owner,),
    )
    rules = [_serialize_notification_rule(row) for row in rows]
    return {"rules": rules, "total": len(rules)}


@router.post("/notifications/rules")
async def create_notification_rule(payload: NotificationRuleCreate, owner: str = Depends(get_current_owner)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Rule name is required")

    target = _validate_notification_target(payload.channel_type, payload.target_url_or_email)
    rule_id = str(uuid.uuid4())
    db = await get_db()
    await db.execute(
        """
        INSERT INTO notification_rules (
            id, name, owner_id, severity_threshold, channel_type, target_url_or_email, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rule_id,
            name,
            owner,
            payload.severity_threshold.value,
            payload.channel_type.value,
            target,
            1 if payload.is_active else 0,
        ),
    )
    row = await db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?",
        (rule_id,),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create notification rule")
    return _serialize_notification_rule(row)

@router.get("/rate-limit/status")
async def get_rate_limit_status(request: Request):
    """Get current rate limit status for the client."""
    limiter = getattr(request.app.state, 'scan_rate_limiter', None)
    if limiter and hasattr(limiter, 'get_status'):
        client_id = request.client.host if request.client else "unknown"
        status_info = await limiter.get_status(client_id)
        return {
            "status": "enabled",
            "client": client_id,
            "remaining": status_info.get("remaining", 0),
            "reset_in": status_info.get("reset_in", 0),
        }
    return {"status": "disabled", "message": "Rate limiting is not enabled"}


async def _verify_notification_rule_owner(db, rule_id: str, owner: str):
    """Check the notification rule exists and belongs to the caller."""
    row = await db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?",
        (rule_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    if row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this notification rule")
    return row


@router.get("/notifications/rules/{rule_id}")
async def get_notification_rule(rule_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    row = await _verify_notification_rule_owner(db, rule_id, owner)
    return _serialize_notification_rule(row)


@router.patch("/notifications/rules/{rule_id}")
async def update_notification_rule(rule_id: str, payload: NotificationRuleUpdate, owner: str = Depends(get_current_owner)):
    """Patch a notification rule.

    Returns ``409 Conflict`` with the latest persisted rule when an optimistic
    update loses a concurrent edit race so clients can refresh and retry.
    """
    db = await get_db()
    row = await _verify_notification_rule_owner(db, rule_id, owner)

    updates: Dict[str, Any] = {}

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Rule name is required")
        updates["name"] = name

    effective_channel = (
        payload.channel_type
        if payload.channel_type is not None
        else NotificationChannelType(row["channel_type"])
    )
    if payload.target_url_or_email is not None:
        target = _validate_notification_target(
            effective_channel,
            payload.target_url_or_email,
        )
        updates["target_url_or_email"] = target
    elif payload.channel_type is not None:
        target = _validate_notification_target(
            effective_channel,
            row["target_url_or_email"],
        )
        updates["target_url_or_email"] = target

    if payload.severity_threshold is not None:
        updates["severity_threshold"] = payload.severity_threshold.value

    if payload.channel_type is not None:
        updates["channel_type"] = payload.channel_type.value

    if payload.is_active is not None:
        updates["is_active"] = 1 if payload.is_active else 0

    if not updates:
        raise HTTPException(status_code=400, detail="No update fields provided")

    try:
        updated = await notification_service.update_notification_rule(
            db,
            current_rule=row,
            updates=updates,
        )
    except notification_service.NotificationRuleConflictError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "notification_rule_conflict",
                "message": (
                    "Notification rule was updated by another request. "
                    "Refresh the rule and retry your changes."
                ),
                "current_rule": _serialize_notification_rule(exc.current_rule),
            },
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    return _serialize_notification_rule(updated)


@router.delete("/notifications/rules/{rule_id}")
async def delete_notification_rule(rule_id: str, owner: str = Depends(get_current_owner)):
    db = await get_db()
    await _verify_notification_rule_owner(db, rule_id, owner)
    await db.execute("DELETE FROM notification_rules WHERE id = ?", (rule_id,))
    return {"rule_id": rule_id, "deleted": True}


@router.get("/settings/webhook")
async def get_scan_webhook_settings(owner: str = Depends(get_current_owner)):
    """Return the configured scan-completion webhook for the current owner.

    Fires on scan completion/failure (issue #1615) — distinct from the
    per-finding severity-threshold rules under /notifications/rules.
    """
    db = await get_db()
    row = await db.fetchone(
        "SELECT * FROM scan_webhook_settings WHERE owner_id = ?",
        (owner,),
    )
    if not row:
        return {"webhook_url": None, "platform": None, "configured": False, "updated_at": None}
    webhook_url = row["webhook_url"]
    return {
        "webhook_url": webhook_url,
        "platform": notification_service.detect_webhook_platform(webhook_url),
        "configured": True,
        "updated_at": row.get("updated_at"),
    }


@router.put("/settings/webhook")
async def upsert_scan_webhook_settings(
    payload: ScanWebhookSettingsRequest,
    owner: str = Depends(get_current_owner),
):
    """Create or update the scan-completion webhook URL for the current owner."""
    target = _validate_notification_target(NotificationChannelType.WEBHOOK, payload.webhook_url)
    db = await get_db()
    row = await notification_service.set_scan_webhook_url(db, owner, target)
    return {
        "webhook_url": row["webhook_url"],
        "platform": notification_service.detect_webhook_platform(row["webhook_url"]),
        "configured": True,
        "updated_at": row.get("updated_at"),
    }


@router.delete("/settings/webhook")
async def delete_scan_webhook_settings(owner: str = Depends(get_current_owner)):
    """Remove the scan-completion webhook URL for the current owner."""
    db = await get_db()
    deleted = await notification_service.delete_scan_webhook_url(db, owner)
    return {"deleted": deleted}


@router.get("/notifications/history", dependencies=[Depends(read_heavy_limiter)])
async def list_notification_history(
    rule_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    owner: str = Depends(get_current_owner),
):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative")

    db = await get_db()
    query = (
        "SELECT nh.* FROM notification_history nh "
        "JOIN notification_rules nr ON nh.rule_id = nr.id "
        "WHERE nr.owner_id = ?"
    )
    params: List[Any] = [owner]
    if rule_id:
        query += " AND nh.rule_id = ?"
        params.append(rule_id)
    query += " ORDER BY nh.sent_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await db.fetchall(query, tuple(params))
    history = [_serialize_notification_history(row) for row in rows]

    count_query = (
        "SELECT COUNT(*) AS total FROM notification_history nh "
        "JOIN notification_rules nr ON nh.rule_id = nr.id "
        "WHERE nr.owner_id = ?"
    )
    count_params: List[Any] = [owner]
    if rule_id:
        count_query += " AND nh.rule_id = ?"
        count_params.append(rule_id)
    count_row = await db.fetchone(count_query, tuple(count_params))
    total = int(count_row["total"]) if count_row else 0

    return {"history": history, "total": total, "limit": limit, "offset": offset}


@router.get("/finding/{finding_id}")
async def get_finding_details(finding_id: str, owner: str = Depends(get_current_owner)):
    """Get detailed information for a specific finding"""
    db = await get_db()

    finding_row = await db.fetchone(
        """
        SELECT f.*, t.tool_name, t.target as task_target
        FROM findings f
        JOIN tasks t ON f.task_id = t.id
        WHERE f.id = ?
        """,
        (finding_id,)
    )

    if not finding_row:
        raise HTTPException(status_code=404, detail="Finding not found")

    if finding_row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="You do not have access to this finding")

    metadata = {}
    if finding_row["metadata_json"]:
        try:
            metadata = json.loads(finding_row["metadata_json"])
        except json.JSONDecodeError:
            metadata = {}

    risk_factors = []
    if finding_row.get("risk_factors_json"):
        try:
            risk_factors = json.loads(finding_row["risk_factors_json"])
        except (json.JSONDecodeError, TypeError):
            risk_factors = []

    return {
        "id": finding_row["id"],
        "task_id": finding_row["task_id"],
        "plugin_id": finding_row["plugin_id"],
        "tool": finding_row["tool_name"],
        "title": finding_row["title"],
        "category": finding_row["category"],
        "severity": finding_row["severity"],
        "target": finding_row["target"],
        "description": finding_row["description"],
        "remediation": finding_row["remediation"],
        "proof": finding_row["proof"],
        "cvss": finding_row["cvss"],
        "cve": finding_row["cve"],
        "discovered_at": finding_row["discovered_at"],
        "metadata": metadata,
        "exploitability": finding_row.get("exploitability"),
        "confidence": finding_row.get("confidence"),
        "asset_exposure": finding_row.get("asset_exposure"),
        "risk_score": finding_row.get("risk_score"),
        "risk_factors": risk_factors,
        "safe_to_apply": metadata.get("safe_to_apply"),
        "compatible_range": metadata.get("compatible_range"),
        "alternatives": metadata.get("alternatives"),
    }


@router.get("/attack-surface")
async def get_attack_surface(owner: str = Depends(get_current_owner)):
    """Return an aggregated view of the caller's monitored attack surface."""
    db = await get_db()

    # We aggregate unique targets from the caller's own tasks and findings
    tasks = await db.fetchall(
        "SELECT DISTINCT target, tool_name, created_at FROM tasks WHERE owner_id = ? ORDER BY created_at DESC",
        (owner,),
    )
    findings = await db.fetchall(
        "SELECT DISTINCT target, category, severity, discovered_at FROM findings WHERE owner_id = ? ORDER BY discovered_at DESC",
        (owner,),
    )

    entries = []
    seen_targets = set()

    # Add findings as high-priority surface entries
    for f in findings:
        target = f["target"]
        if target not in seen_targets:
            entries.append({
                "id": str(uuid.uuid4()),
                "category": f["category"],
                "item": target,
                "details": f"Active exposure identified in {f['category']}",
                "risk": f["severity"],
                "source": "Audit Scan",
                "last_seen": f["discovered_at"]
            })
            seen_targets.add(target)

    # Add other scanned targets
    for t in tasks:
        target = t["target"]
        if target not in seen_targets:
            entries.append({
                "id": str(uuid.uuid4()),
                "category": "Infrastructure",
                "item": target,
                "details": f"Monitored via {t['tool_name']}",
                "risk": "info",
                "source": "Recon",
                "last_seen": t["created_at"]
            })
            seen_targets.add(target)

    return {"entries": entries}


@router.get("/assets")
async def get_assets(owner: str = Depends(get_current_owner)):
    """Return a list of the caller's tracked assets."""
    db = await get_db()
    # For now, we use unique targets as assets, scoped to the caller (issue #401)
    rows = await db.fetchall(
        """
        SELECT DISTINCT target FROM tasks WHERE owner_id = ?
        UNION
        SELECT DISTINCT target FROM findings WHERE owner_id = ?
        """,
        (owner, owner),
    )
    assets = [{"id": str(uuid.uuid4()), "name": row["target"]} for row in rows]
    return {"assets": assets}

# ── Network Policy Management Endpoints ─────────────────────────────────────

from fastapi.security import APIKeyHeader
from fastapi import Security, status
from .network_policy import get_policy_engine, PolicyAction
from dataclasses import asdict

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_admin_access(
    api_key: Optional[str] = Security(api_key_header),
    request: Request = None,
) -> Optional[str]:
    """Verify admin API key is provided and valid."""
    import hmac

    # Secure-by-default: If admin_api_key setting is not configured, block all access
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin API Key is not configured on the server. Please set SECUSCAN_ADMIN_API_KEY."
        )

    # Entropy check: enforce a strong API key
    if len(settings.admin_api_key) < 16:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin API Key is too weak. It must be at least 16 characters long."
        )

    candidate = api_key
    if request:
        auth_header = request.headers.get("authorization")
        if auth_header:
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:]
            else:
                token = auth_header
            # If the Authorization header matches the admin API key, prefer it.
            # This is important when the client automatically includes the general X-Api-Key in headers.
            if hmac.compare_digest(token, settings.admin_api_key):
                candidate = token
            elif not candidate:
                candidate = token

    if not candidate or not hmac.compare_digest(candidate, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Admin API Key"
        )
    return candidate

@router.get(
    "/admin/diagnostics/notifications",
    response_model=NotificationDiagnosticsResponse,
    dependencies=[Depends(verify_admin_access), Depends(admin_limiter)]
)
async def get_notification_diagnostics():
    """Get active notification delivery configuration and retry policy"""
    return notification_service.get_delivery_configuration()

@router.get("/admin/network-policy", dependencies=[Depends(verify_admin_access), Depends(admin_limiter)])
async def get_network_policy():
    """Get current network policy configuration"""
    engine = get_policy_engine()

    return {
        "allowlist": [asdict(p) for net, p in engine.allowlist],
        "denylist": [asdict(p) for net, p in engine.denylist],
        "audit_entries_count": len(engine.audit_entries),
    }

@router.post("/admin/network-policy/allow", dependencies=[Depends(verify_admin_access), Depends(admin_limiter)])
async def add_allow_rule(request: dict):
    """Add network to allowlist"""
    engine = get_policy_engine()

    try:
        engine.add_allow_rule(
            cidr=request["cidr"],
            reason=request.get("reason", "Operator added"),
        )
        return {"status": "success", "cidr": request["cidr"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/admin/network-policy/deny", dependencies=[Depends(verify_admin_access), Depends(admin_limiter)])
async def add_deny_rule(request: dict):
    """Add network to denylist"""
    engine = get_policy_engine()

    try:
        engine.add_deny_rule(
            cidr=request["cidr"],
            reason=request.get("reason", "Operator added"),
        )
        return {"status": "success", "cidr": request["cidr"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/admin/network-audit-log", dependencies=[Depends(verify_admin_access), Depends(admin_limiter)])
async def get_audit_log(
    plugin_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """Retrieve network audit log entries"""
    engine = get_policy_engine()

    policy_action = None
    if action and action.upper() in ["ALLOW", "DENY"]:
        policy_action = PolicyAction[action.upper()]

    entries = engine.get_audit_entries(
        plugin_id=plugin_id,
        action=policy_action,
        limit=limit
    )

    return {
        "entries": [asdict(e) for e in entries],
        "total": len(entries),
    }

@router.get("/admin/network-audit-log/export", dependencies=[Depends(verify_admin_access), Depends(admin_limiter)])
async def export_audit_log(format: str = "json"):
    """Export audit log in specified format"""
    engine = get_policy_engine()

    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")

    content = engine.export_audit_log(format)

    mime_type = "application/json" if format == "json" else "text/csv"
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=network-audit.{format}"}
    )


@router.get("/admin/vault/diagnostics", dependencies=[Depends(verify_admin_access), Depends(admin_limiter)])
async def get_vault_diagnostics():
    """Report non-secret diagnostics for the credential vault key.
    Surfaces a one-way fingerprint of the active vault key so operators can confirm key-rotation state without the key material ever leaving the server.
    Applies across deployments or before/after a rotation.
    The endpoint never fails on configuration state: when no key is configured it reports ``configured: false`` with a null fingerprint.
    So it can double as a health probe for vault configuration.
    The route is admin-gated: while the fingerprint is non-secret, the key source and configuration status are operational details that belong behind the same boundary as the rest of the ``/admin`` surface.
    """
    if settings.vault_key:
        key_source = "vault_key"
    elif settings.plugin_signature_key:
        key_source = "plugin_signature_key"
    else:
        key_source = None

    try:
        crypto = VaultCrypto(settings.resolved_vault_key)
    except RuntimeError:
        # No SECUSCAN_VAULT_KEY / plugin signature key configured.
        return {
            "configured": False,
            "key_source": None,
            "algorithm": "AES-256-GCM",
            "key_fingerprint": None,
            "fingerprint_algorithm": "sha256-trunc64",
        }

    return {
        "configured": True,
        "key_source": key_source,
        "algorithm": "AES-256-GCM",
        "key_fingerprint": crypto.key_fingerprint,
        "fingerprint_algorithm": "sha256-trunc64",
    }
