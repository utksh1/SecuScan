"""
Notification serialization helpers for routes.py.

These helpers were originally defined inline in routes.py. They were extracted
into this small import-safe module so that they can be unit-tested directly
without pulling in the heavy routes.py import chain (FastAPI, reporting,
xhtml2pdf, etc.). routes.py re-imports them from here so the public API is
unchanged.
"""

from __future__ import annotations

from typing import Any, Dict


def _serialize_notification_history(row: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a raw database row dict into the API response shape for notification history."""
    return {
        "id": row["id"],
        "rule_id": row["rule_id"],
        "finding_id": row["finding_id"],
        "status": row["status"],
        "error_message": row.get("error_message"),
        "sent_at": row.get("sent_at"),
    }
