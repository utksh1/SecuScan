"""
Pure workflow helpers extracted from routes.py for safe import in unit tests.

routes.py re-exports these functions so existing call sites keep working.
"""
import json
from typing import Any, Dict, List, Optional

from .models import WorkflowStep


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


def _serialize_workflow(
    row: Dict[str, Any],
    queued_task_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return the workflow shape consumed by the frontend."""
    return {
        "id": row["id"],
        "name": row["name"],
        "schedule_seconds": row.get("schedule_seconds"),
        "enabled": bool(row.get("enabled")),
        "steps": _parse_workflow_steps(row.get("steps_json")),
        "created_at": row.get("created_at"),
        "last_run_at": row.get("last_run_at"),
        "queued_task_ids": queued_task_ids or [],
    }
