"""
Structured append-only audit log helpers.

The runtime database layer in SecuScan is currently aiosqlite-backed. The
SQLAlchemy model below documents the intended table contract for future ORM
adapters while the async helper writes through the existing database manager.
"""

from __future__ import annotations

import enum
import json
from datetime import datetime
from typing import Any, Optional

try:  # pragma: no cover - exercised only when SQLAlchemy is installed.
    from sqlalchemy import DateTime, Enum as SAEnum, Index, Integer, JSON, String
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
except Exception:  # pragma: no cover
    DateTime = Integer = JSON = String = SAEnum = None  # type: ignore
    DeclarativeBase = object  # type: ignore
    Mapped = Any  # type: ignore

    def mapped_column(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        return None

    def Index(*args: Any, **kwargs: Any) -> None:  # type: ignore
        return None


class AuditEventType(str, enum.Enum):
    SCAN_CREATED = "scan_created"
    SCAN_QUEUED = "scan_queued"
    SCAN_RUNNING = "scan_running"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_DELETED = "scan_deleted"
    REPORT_DOWNLOADED = "report_downloaded"


class AuditBase(DeclarativeBase):
    pass


class AuditLogEntry(AuditBase):
    """SQLAlchemy model proposal for the append-only audit_log table."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_event_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[AuditEventType] = mapped_column(SAEnum(AuditEventType), nullable=False)
    scan_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    plugin_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)


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
