from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .models import WorkflowStep  # noqa: E402


def parse_json_fields(rows: List[Dict], fields: List[str]) -> List[Dict]:
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
    from .time_utils import to_utc_iso

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

        for ts_field in ("discovered_at", "first_seen_at", "last_seen_at"):
            if finding.get(ts_field):
                finding[ts_field] = to_utc_iso(finding[ts_field])

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
    return json.dumps(value if value is not None else json.loads(fallback))


def _serialize_workflow(
    row: Dict[str, Any],
    queued_task_ids: Optional[list[str]] = None,
) -> Dict[str, Any]:
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
    with open(path, "r", encoding="utf-8", errors="replace") as output_file:
        while True:
            chunk = output_file.read(chunk_size)
            if not chunk:
                break
            yield chunk
