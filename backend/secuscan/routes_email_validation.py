"""
Import-safe notification validation helpers extracted from routes.py.
The _validate_notification_target function raises ValueError for testability;
routes.py wraps it to raise HTTPException.
"""

import re
from typing import Tuple

from .models import NotificationChannelType
from .validation import validate_url
from .config import settings

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NotificationValidationError(Exception):
    """Raised when notification target validation fails."""
    pass


def _validate_notification_target(channel_type: NotificationChannelType, target: str) -> str:
    """Validate a notification delivery target (email address or webhook URL).
    
    Raises NotificationValidationError on failure.
    """
    cleaned = target.strip()
    if not cleaned:
        raise NotificationValidationError("Notification target is required")

    if channel_type == NotificationChannelType.WEBHOOK:
        is_valid, error = validate_url(cleaned)
        if not is_valid:
            raise NotificationValidationError(error or "Invalid webhook URL")

        if settings.notification_ssrf_enabled:
            from .validation import resolve_and_validate_target, validate_webhook_target
            ssrf_ok, ssrf_err = resolve_and_validate_target(cleaned)
            if not ssrf_ok:
                raise NotificationValidationError(
                    f"Webhook target blocked by SSRF protection: {ssrf_err}"
                )
            target_ok, target_err = validate_webhook_target(cleaned)
            if not target_ok:
                raise NotificationValidationError(
                    f"Webhook target blocked by SSRF protection: {target_err}"
                )
        return cleaned

    if not _EMAIL_PATTERN.match(cleaned):
        raise NotificationValidationError("Invalid email address")
    return cleaned


def validate_email_format(email: str) -> Tuple[bool, str]:
    """Validate email format. Returns (is_valid, error_message)."""
    if not email or not email.strip():
        return False, "Email address is required"
    cleaned = email.strip()
    if not _EMAIL_PATTERN.match(cleaned):
        return False, "Invalid email address"
    return True, ""


def strip_target(target: str) -> str:
    """Strip whitespace from a notification target."""
    return target.strip()
