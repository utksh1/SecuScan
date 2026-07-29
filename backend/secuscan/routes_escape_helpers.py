"""
SQL escape helpers for routes.py.

These helpers were originally defined inline in routes.py. They were extracted
into this small import-safe module so that they can be unit-tested directly
without pulling in the heavy routes.py import chain (FastAPI, reporting,
xhtml2pdf, etc.). routes.py re-imports them from here so the public API is
unchanged.
"""

from __future__ import annotations


def _escape_like(value: str) -> str:
    """Escape SQLite LIKE wildcards so user input cannot inject % or _ patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
