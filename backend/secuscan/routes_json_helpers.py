"""
Pure JSON deserialization helpers for routes.py.

These helpers were originally defined inline in routes.py. They were extracted
into this small import-safe module so that they can be unit-tested directly
without pulling in the heavy routes.py import chain (FastAPI, reporting,
xhtml2pdf, etc.). routes.py re-imports them from here so the public API is
unchanged.

The functions are pure: they take rows (dicts) and return new lists of dicts.
They never mutate their inputs.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .models import WorkflowStep  # noqa: E402


def parse_json_fields(rows: List[Dict], fields: List[str]) -> List[Dict]:
    """Parse stringified JSON fields from a list of row dicts.

    For each row in *rows*, the named *fields* are checked. If a field is
    present, truthy, and a string, it is parsed with :func:`json.loads`.
    Parsing failures are silently preserved (the original string is kept).

    Args:
        rows:   Iterable of row dicts (typically from a SQL query).
        fields: Column names whose values may be JSON-encoded strings.

    Returns:
        A new list of row dicts with the named fields parsed.
    """
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


FINDING_JSON_FIELDS = [
    "metadata_json",
    "risk_factors_json",
    "evidence_json",
    "asset_refs_json",
    "references_json",
    "corroborating_sources_json",
]


def deserialize_finding_rows(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Parse JSON fields on finding rows and rename them to friendly keys.

    The ``*_json`` suffix is stripped from the parsed values:
    ``metadata_json`` -> ``metadata``, ``evidence_json`` -> ``evidence``, etc.
    Rows that do not contain a given ``*_json`` key are passed through.
    """
    findings = parse_json_fields(rows, FINDING_JSON_FIELDS)
    for finding in findings:
        if "metadata_json" in finding:
            finding["metadata"] = finding.pop("metadata_json")
        if "risk_factors_json" in finding:
            finding["risk_factors"] = finding.pop("risk_factors_json")
        if "evidence_json" in finding:
            finding["evidence"] = finding.pop("evidence_json")
        if "asset_refs_json" in finding:
            finding["asset_refs"] = finding.pop("asset_refs_json")
        if "references_json" in finding:
            finding["references"] = finding.pop("references_json")
        if "corroborating_sources_json" in finding:
            finding["corroborating_sources"] = finding.pop("corroborating_sources_json")

        # Expose remediation safety fields at the top level
        metadata = finding.get("metadata")
        if isinstance(metadata, dict):
            finding["safe_to_apply"] = metadata.get("safe_to_apply")
            finding["compatible_range"] = metadata.get("compatible_range")
            finding["alternatives"] = metadata.get("alternatives")
        else:
            finding["safe_to_apply"] = None
            finding["compatible_range"] = None
            finding["alternatives"] = None
    return findings


def deserialize_asset_service_rows(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Parse JSON fields on asset-service rows and rename them.

    Only ``metadata_json`` and ``cert_san_json`` are parsed; both are renamed
    to ``metadata`` and ``cert_san`` respectively.
    """
    items = parse_json_fields(rows, ["metadata_json", "cert_san_json"])
    for item in items:
        if "metadata_json" in item:
            item["metadata"] = item.pop("metadata_json")
        if "cert_san_json" in item:
            item["cert_san"] = item.pop("cert_san_json")
    return items


# ---------------------------------------------------------------------------
# Workflow and payload helpers extracted from routes.py
# ---------------------------------------------------------------------------

from typing import Optional


def _parse_workflow_steps(raw_steps: Any) -> List[Dict[str, Any]]:
    """Parse and normalize raw workflow steps from a JSON string or list.

    Handles three input forms:
    - A list of step dicts (pass-through)
    - A JSON string (parsed with json.loads)
    - None or falsy (returns empty list)

    Each step dict is validated against the WorkflowStep model; invalid
    entries are silently skipped.
    """
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


def _json_payload(value: Any, fallback: str) -> str:
    """Return JSON-encoded value, or fall back to the parsed fallback string.

    If *value* is not None it is JSON-serialized directly. If it is None,
    *fallback* is parsed as JSON and that result is JSON-serialized.
    """
    return json.dumps(value if value is not None else json.loads(fallback))


def _serialize_workflow(
    row: Dict[str, Any],
    queued_task_ids: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Return the workflow shape consumed by the frontend.

    Args:
        row: A database row dict for a workflow record.
        queued_task_ids: Optional list of currently-queued task IDs.

    Returns:
        A dict with id, name, schedule_seconds, enabled, steps, created_at,
        last_run_at, and queued_task_ids fields.
    """
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


# ---------------------------------------------------------------------------
# SSE output helpers extracted from routes.py
# ---------------------------------------------------------------------------

# Default chunk size for SSE output streaming (64 KB)
_SSE_CHUNK_SIZE = 64 * 1024


def iter_raw_output_chunks(path: str, chunk_size: int = _SSE_CHUNK_SIZE):
    """Yield raw output from *path* in bounded chunks.

    Each yielded value is a string of at most *chunk_size* bytes.
    An empty or short file produces fewer chunks. Unicode is decoded
    with errors='replace' to avoid crashing on malformed bytes.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as output_file:
        while True:
            chunk = output_file.read(chunk_size)
            if not chunk:
                break
            yield chunk
