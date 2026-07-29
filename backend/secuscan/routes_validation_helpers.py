"""
Validation helpers for routes.py.

These helpers were originally defined inline in routes.py. They were extracted
into this small import-safe module so that they can be unit-tested directly
without pulling in the heavy routes.py import chain (FastAPI, reporting,
xhtml2pdf, etc.). routes.py re-imports them from here so the public API is
unchanged.
"""

from __future__ import annotations

from typing import Any, Optional


def _validate_lengths(
    name: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    resource_type: str = "Resource",
) -> None:
    """Validate field lengths and raise HTTPException if any exceed limits.

    Limits: name <= 255 chars, description <= 2000 chars, notes <= 2000 chars.
    """
    # Lazy import to avoid pulling FastAPI into the test import chain
    from starlette.exceptions import HTTPException

    if name is not None and len(str(name).strip()) > 255:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_type} name exceeds maximum length of 255 characters",
        )
    if description is not None and len(str(description).strip()) > 2000:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_type} description exceeds maximum length of 2000 characters",
        )
    if notes is not None and len(str(notes).strip()) > 2000:
        raise HTTPException(
            status_code=400,
            detail=f"{resource_type} notes exceeds maximum length of 2000 characters",
        )
