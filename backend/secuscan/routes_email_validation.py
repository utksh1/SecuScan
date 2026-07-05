"""
Email-format and notification-target validation helpers.

Extracted from routes.py so they can be unit-tested without pulling in the
FastAPI / xhtml2pdf / reportlab import chain.

Public API
----------
validate_email_format(email: str) -> str
    Strips whitespace and validates against a simple RFC-5321-ish pattern.
    Raises ValueError if the address is blank or malformed.

validate_notification_target(channel_type: str, target: str, *,
                             notification_ssrf_enabled: bool = True) -> str
    Validates the target for the given channel type.
    For "webhook": validates the URL and optionally runs SSRF checks.
    For "email": validates the email format.
    Returns the stripped target on success.
    Raises ValueError on failure (HTTPException is raised by the caller).
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Sentinel strings that map to NotificationChannelType members.
WEBHOOK_TYPE = "webhook"
EMAIL_TYPE = "email"


def validate_email_format(email: str) -> str:
    """Strip and validate an email address.

    Args:
        email: Raw address string.

    Returns:
        The stripped address.

    Raises:
        ValueError: If the address is blank or malformed.
    """
    cleaned = email.strip()
    if not cleaned:
        raise ValueError("Email address is required")
    if not _EMAIL_PATTERN.match(cleaned):
        raise ValueError("Invalid email address")
    return cleaned


def validate_webhook_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Basic URL scheme check for webhook targets.

    Returns (True, None) for http/https URLs; (False, reason) otherwise.
    """
    from .validation import validate_url
    return validate_url(url)


def validate_notification_target(
    channel_type: str,
    target: str,
    *,
    notification_ssrf_enabled: bool = True,
) -> str:
    """Validate and return the cleaned notification target.

    Args:
        channel_type: ``"webhook"`` or ``"email"`` (string sentinel, not enum).
        target:        The target URL or email address.
        notification_ssrf_enabled:
            Pass ``False`` to skip SSRF checks for webhook targets.
            Defaults to ``True`` (mirrors the application default).

    Returns:
        The stripped target string on success.

    Raises:
        ValueError: When the target is blank or fails validation.
    """
    cleaned = target.strip()
    if not cleaned:
        raise ValueError("Notification target is required")

    if channel_type == WEBHOOK_TYPE:
        is_valid, error = validate_webhook_url(cleaned)
        if not is_valid:
            raise ValueError(error or "Invalid webhook URL")

        if notification_ssrf_enabled:
            from .validation import resolve_and_validate_target, validate_webhook_target
            ssrf_ok, ssrf_err = resolve_and_validate_target(cleaned)
            if not ssrf_ok:
                raise ValueError(f"Webhook target blocked by SSRF protection: {ssrf_err}")
            target_ok, target_err = validate_webhook_target(cleaned)
            if not target_ok:
                raise ValueError(f"Webhook target blocked by SSRF protection: {target_err}")
        return cleaned

    # email channel
    return validate_email_format(cleaned)
