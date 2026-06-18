"""
Pure helper functions for platform resources — import-safe subset with no database dependencies.

Extracted from platform_resources.py so they can be unit-tested without pulling in
aiosqlite and the rest of the database layer.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .execution_context import normalize_execution_context
from .models import ExecutionContext


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _stable_asset_id(target: str, host: Any, port: Any, protocol: Any) -> str:
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
    return json.dumps(normalize_execution_context(context or {}))


def _deserialize_resource_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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
    results: List[Dict[str, Any]] = []
    for row in rows:
        parsed = _deserialize_resource_row(row)
        if parsed is not None:
            results.append(parsed)
    return results
