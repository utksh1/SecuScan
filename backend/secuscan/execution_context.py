"""Execution-context defaults and policy helpers."""

from __future__ import annotations

from typing import Any, Dict

from .models import EvidenceLevel, ExecutionContext, ValidationMode


def normalize_execution_context(raw: Any) -> Dict[str, Any]:
    """Return a validated execution-context payload as a plain dict."""
    if isinstance(raw, ExecutionContext):
        return raw.model_dump(mode="json")
    if isinstance(raw, dict):
        return ExecutionContext(**raw).model_dump(mode="json")
    return ExecutionContext().model_dump(mode="json")


def is_offensive_validation(context: Dict[str, Any]) -> bool:
    """True when validation mode goes beyond detect-only."""
    mode = str(context.get("validation_mode") or ValidationMode.PROOF.value)
    return mode in {
        ValidationMode.PROOF.value,
        ValidationMode.CONTROLLED_EXTRACT.value,
    }


def evidence_level_rank(level: str) -> int:
    """Comparable evidence-level rank."""
    ordering = {
        EvidenceLevel.MINIMAL.value: 0,
        EvidenceLevel.STANDARD.value: 1,
        EvidenceLevel.FULL.value: 2,
    }
    return ordering.get(level, 1)
