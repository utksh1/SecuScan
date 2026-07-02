"""
Pure target-extraction helpers for the executor module.

These helpers were originally defined inline in executor.py. They were extracted
into this small import-safe module so that they can be unit-tested directly
without pulling in the heavy executor.py import chain (FastAPI, cache, config,
etc.). executor.py re-imports them from here so the public API is unchanged.
"""
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
