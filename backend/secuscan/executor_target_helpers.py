from __future__ import annotations

from typing import Any, Dict


def extract_target(inputs: Dict[str, Any]) -> str:
    """Best-effort target extraction across plugin shapes."""
    return (
        inputs.get("target")
        or inputs.get("url")
        or inputs.get("host")
        or inputs.get("domain")
        or ""
    )
