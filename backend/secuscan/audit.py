"""
Structured append-only audit log helpers.

The runtime database layer in SecuScan is aiosqlite-backed.
"""

from __future__ import annotations

import enum
import json
from datetime import datetime
from typing import Any, Optional


class AuditEventType(str, enum.Enum):
    SCAN_CREATED = "scan_created"
    SCAN_QUEUED = "scan_queued"
    SCAN_RUNNING = "scan_running"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_DELETED = "scan_deleted"
    REPORT_DOWNLOADED = "report_downloaded"


async def log_event(
    event_type: AuditEventType | str,
    scan_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Append a structured audit event.

    Keyword args:
        plugin_id: optional scanner/plugin identifier
        target: optional scan target
        actor: optional user/system actor
        metadata: arbitrary JSON-serializable metadata dictionary
    """

    from .database import get_db
    from .request_context import get_request_id

    event_value = event_type.value if isinstance(event_type, AuditEventType) else str(event_type)
    plugin_id = kwargs.pop("plugin_id", None)
    target = kwargs.pop("target", None)
    actor = kwargs.pop("actor", None)
    metadata = kwargs.pop("metadata", None)

    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {"value": metadata}
    metadata = {**metadata, **kwargs}

    request_id = get_request_id()
    if request_id:
        metadata.setdefault("request_id", request_id)

    db = await get_db()
    await db.execute(
        """
        INSERT INTO audit_log (
            event_type, scan_id, plugin_id, target, actor, metadata,
            severity, message, context_json, task_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_value,
            scan_id,
            plugin_id,
            target,
            actor,
            json.dumps(metadata),
            str(metadata.get("severity", "info")),
            str(metadata.get("message", event_value.replace("_", " ").title())),
            json.dumps(metadata),
            scan_id,
        ),
    )
