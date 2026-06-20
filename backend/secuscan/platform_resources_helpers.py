"""
Pure synchronous helpers extracted from platform_resources for safe import.
Re-exported from platform_resources.py so existing call sites keep working.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .models import ExecutionContext


def _stable_asset_id(target: str, host: Any, port: Any, protocol: Any) -> str:
    """Generate a stable deterministic asset ID from target/host/port/protocol."""
    material = "||".join(
        [
            str(target or "").strip().lower(),
            str(host or "").strip().lower(),
            str(port or "").strip().lower(),
            str(protocol or "").strip().lower(),
        ]
    )
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"asset:{digest}"


def serialize_execution_context(context: ExecutionContext | Dict[str, Any] | None) -> str:
    """Serialize an execution context to a JSON string."""
    return json.dumps(_normalize_execution_context(context or {}))


def _normalize_execution_context(raw: Any) -> Dict[str, Any]:
    """Return a validated execution-context payload as a plain dict."""
    from .models import ExecutionContext as EC
    if isinstance(raw, EC):
        return raw.model_dump(mode="json")
    if isinstance(raw, dict):
        return EC(**raw).model_dump(mode="json")
    return EC().model_dump(mode="json")


def _deserialize_resource_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Deserialize _json suffix columns in a database row back to their parsed forms."""
    if row is None:
        return None
    item = dict(row)
    for key in list(item.keys()):
        if key.endswith("_json") and isinstance(item[key], str):
            try:
                item[key[:-5]] = json.loads(item[key])
            except json.JSONDecodeError:
                item[key[:-5]] = item[key]
    return item


def deserialize_resource_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deserialize _json suffix columns for a list of database rows."""
    results: List[Dict[str, Any]] = []
    for row in rows:
        parsed = _deserialize_resource_row(row)
        if parsed is not None:
            results.append(parsed)
    return results
