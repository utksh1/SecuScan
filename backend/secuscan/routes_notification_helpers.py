"""
Notification rule/history serialization helpers.

Extracted from routes.py so they can be unit-tested without pulling in the
FastAPI / xhtml2pdf / reportlab import chain.

Public API
----------
serialize_notification_rule(row: Dict) -> Dict
    Converts a database row dict into the API response shape for a notification
    rule. Handles missing optional fields and coerces ``is_active`` to bool.
"""

from __future__ import annotations

from typing import Any, Dict


def serialize_notification_rule(row: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a notification rule DB row into the API response format.

    Args:
        row: A database row dict. Required keys: ``id``, ``name``,
             ``severity_threshold``, ``channel_type``, ``target_url_or_email``,
             ``is_active``. Optional keys: ``created_at``, ``updated_at``.

    Returns:
        A dict with the API response shape.
    """
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
