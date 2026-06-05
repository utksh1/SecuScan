"""
Short-lived HMAC-SHA256 signed tokens for report artifact downloads.

A token encodes task_id, format, owner_id, and an expiry epoch.  Its
signature binds all four fields so any change invalidates the token.

Token wire format (URL-safe, no padding):
    base64url( task_id ) . base64url( format ) . base64url( owner_id )
    . base64url( str(expiry_epoch) ) . hex(hmac)

The HMAC is computed over the first four pipe-joined fields using a key
derived from SECUSCAN_VAULT_KEY.  This keeps the token self-contained
(no database lookup for validation) while preventing forgery.
"""

import base64
import hashlib
import hmac
import time
from typing import Tuple

from .config import settings

_SEP = "."
_ALLOWED_FORMATS = frozenset(["csv", "html", "pdf", "sarif"])


def _signing_key() -> bytes:
    """32-byte key derived from the vault key — same material, separate purpose."""
    raw = settings.resolved_vault_key          # already 32 bytes, base64url-encoded
    return hashlib.sha256(b"report-download-token:" + raw).digest()


def _b64_encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()


def _b64_decode(value: str) -> str:
    padding = 4 - len(value) % 4
    padded = value + "=" * (padding % 4)
    return base64.urlsafe_b64decode(padded).decode()


def _sign(task_id: str, fmt: str, owner_id: str, expiry: int) -> str:
    payload = f"{task_id}|{fmt}|{owner_id}|{expiry}"
    return hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()


def generate_token(task_id: str, fmt: str, owner_id: str, ttl_seconds: int) -> str:
    """Return a signed download token valid for *ttl_seconds* from now.

    Raises ValueError if *fmt* is not a recognised report format.
    """
    if fmt not in _ALLOWED_FORMATS:
        raise ValueError(f"Unknown report format '{fmt}'. Allowed: {sorted(_ALLOWED_FORMATS)}")
    expiry = int(time.time()) + ttl_seconds
    sig = _sign(task_id, fmt, owner_id, expiry)
    parts = [
        _b64_encode(task_id),
        _b64_encode(fmt),
        _b64_encode(owner_id),
        _b64_encode(str(expiry)),
        sig,
    ]
    return _SEP.join(parts)


class TokenError(Exception):
    """Base class for token validation failures."""


class TokenExpiredError(TokenError):
    pass


class TokenFormatMismatchError(TokenError):
    pass


class TokenTaskMismatchError(TokenError):
    pass


class TokenInvalidError(TokenError):
    pass


def validate_token(
    token: str,
    expected_task_id: str,
    expected_fmt: str,
    expected_owner_id: str,
) -> None:
    """Validate a signed download token.

    Raises a subclass of TokenError describing the specific failure so
    callers can log useful diagnostics without leaking details to the
    HTTP response (callers should return a generic 401 for all failures).

    Does NOT raise on success.
    """
    parts = token.split(_SEP)
    if len(parts) != 5:
        raise TokenInvalidError("Malformed token: wrong number of segments")

    try:
        task_id = _b64_decode(parts[0])
        fmt = _b64_decode(parts[1])
        owner_id = _b64_decode(parts[2])
        expiry = int(_b64_decode(parts[3]))
        stored_sig = parts[4]
    except Exception as exc:
        raise TokenInvalidError(f"Malformed token: decode failed: {exc}") from exc

    expected_sig = _sign(task_id, fmt, owner_id, expiry)
    if not hmac.compare_digest(expected_sig, stored_sig):
        raise TokenInvalidError("Token signature invalid")

    if time.time() > expiry:
        raise TokenExpiredError(f"Token expired at epoch {expiry}")

    if task_id != expected_task_id:
        raise TokenTaskMismatchError(
            f"Token task_id '{task_id}' does not match path '{expected_task_id}'"
        )
    if fmt != expected_fmt:
        raise TokenFormatMismatchError(
            f"Token format '{fmt}' does not match path '{expected_fmt}'"
        )
    if owner_id != expected_owner_id:
        raise TokenInvalidError("Token owner does not match authenticated user")
