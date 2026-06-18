import secrets

"""
API key authentication for SecuScan backend.

A random key is generated at startup and written to <data_dir>/.api_key.
Clients must supply it via:
  - Authorization: Bearer <key>
  - X-Api-Key: <key>
"""

from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

# Re-export init_api_key from the import-safe helpers module.
from .auth_helpers import init_api_key, _api_key  # noqa: E402


async def require_api_key(
    request: Request = None,
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_api_key: str | None = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency — rejects requests that do not carry the correct API key.

    Accepts the key in either:
    - ``Authorization: Bearer <key>``
    - ``X-Api-Key: <key>``
    """
    if request is not None and request.url.path.startswith("/api/v1/admin"):
        # Admin endpoints have their own separate verify_admin_access dependency.
        # We bypass require_api_key verification to avoid blocking valid admin key requests.
        return ""

    if _api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not initialised",
        )

    candidate: str | None = None
    if bearer is not None:
        candidate = bearer.credentials
    elif x_api_key is not None:
        candidate = x_api_key

    if candidate is None or not secrets.compare_digest(candidate, _api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return candidate
