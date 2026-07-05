"""
Import-safe notification validation helpers.

This module provides pure validation functions that can be tested without
FastAPI or Pydantic dependencies. The _validate_notification_target function
is a simplified version of the logic in routes.py.
"""

import re
from typing import Tuple

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NotificationValidationError(Exception):
    """Raised when notification target validation fails."""
    pass


# Channel type sentinel values (matching NotificationChannelType enum values)
_WEBHOOK = "webhook"
_EMAIL = "email"


def validate_email_format(email: str) -> Tuple[bool, str]:
    """
    Validate email format. Returns (is_valid, error_message).
    """
    if not email or not email.strip():
        return False, "Email address is required"
    cleaned = email.strip()
    if not _EMAIL_PATTERN.match(cleaned):
        return False, "Invalid email address"
    return True, ""


def strip_target(target: str) -> str:
    """Strip whitespace from a notification target."""
    return target.strip()


def validate_notification_target(channel_type: str, target: str) -> str:
    """
    Validate a notification delivery target (email or webhook).
    
    Args:
        channel_type: "webhook" or "email" (NotificationChannelType values)
        target: The target address/URL
        
    Returns:
        The cleaned target string
        
    Raises:
        NotificationValidationError: If validation fails
    """
    cleaned = target.strip()
    if not cleaned:
        raise NotificationValidationError("Notification target is required")

    if channel_type == _WEBHOOK:
        # Basic URL validation
        if not cleaned.startswith(("http://", "https://")):
            raise NotificationValidationError("Invalid webhook URL")
        return cleaned

    if channel_type == _EMAIL:
        if not _EMAIL_PATTERN.match(cleaned):
            raise NotificationValidationError("Invalid email address")
        return cleaned

    raise NotificationValidationError(f"Unknown channel type: {channel_type}")
