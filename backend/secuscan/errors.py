# backend/secuscan/errors.py
"""
Structured error helpers for /task/start validation failures.
All detail payloads follow the shape: {code, message, hints?}
Raw user input values are never included in error responses.
"""

from enum import Enum
from typing import Any


class TaskErrorCode(str, Enum):
    CONSENT_REQUIRED    = "consent_required"
    PLUGIN_NOT_FOUND    = "plugin_not_found"
    INVALID_TARGET      = "invalid_target"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CONCURRENCY_LIMIT   = "concurrency_limit"


def task_error_detail(
    code: TaskErrorCode,
    message: str,
    hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a consistent error detail dict for HTTPException.
    Never pass raw user-supplied values as message or hints content.
    """
    payload: dict[str, Any] = {"code": code.value, "message": message}
    if hints:
        payload["hints"] = hints
    return payload