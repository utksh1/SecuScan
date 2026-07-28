"""Pure helper functions extracted from backend/secuscan/plugins.py.

This module is import-safe: it has no FastAPI/Pydantic/DB dependencies.
"""
from __future__ import annotations

import re


def _is_absolute_path(value: str) -> bool:
    """Check if a path is absolute regardless of the server OS.

    Handles Unix (/), Windows drive-letter (C:\\, C:/),
    and UNC (\\\\server\\share) absolute path styles.
    """
    if value.startswith("/"):
        return True
    if value.startswith("\\"):
        return True
    return bool(re.match(r"^[a-zA-Z]:[/\\]", value))
