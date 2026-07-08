"""
Unit tests for backend/secuscan/execution_context.py

Covers:
- normalize_execution_context(ExecutionContext) round-trips the same data
- normalize_execution_context({}) returns ExecutionContext() defaults
- normalize_execution_context(None) returns ExecutionContext() defaults
- normalize_execution_context accepts an arbitrary dict and normalises it
- is_offensive_validation distinguishes detect_only from proof/controlled_extract
- is_offensive_validation defaults to PROOF (i.e. offensive) when no mode provided
- is_offensive_validation treats unknown validation modes as non-offensive
- evidence_level_rank returns 0/1/2 for minimal/standard/full
- evidence_level_rank defaults to 1 (standard) for unknown levels
- The original dict is not mutated by normalize_execution_context
"""

from __future__ import annotations

import pytest

from backend.secuscan.execution_context import (
    evidence_level_rank,
    is_offensive_validation,
    normalize_execution_context,
)
from backend.secuscan.models import (
    EvidenceLevel,
    ExecutionContext,
    ValidationMode,
)


# ---------------------------------------------------------------------------
# normalize_execution_context
# ---------------------------------------------------------------------------


class TestNormalizeExecutionContext:
    def test_execution_context_instance_round_trip(self):
        """An ExecutionContext instance returns its model_dump."""
        original = ExecutionContext(
            validation_mode=ValidationMode.PROOF,
            evidence_level=EvidenceLevel.STANDARD,
        )
        normalized = normalize_execution_context(original)
        assert normalized["validation_mode"] == ValidationMode.PROOF.value
        assert normalized["evidence_level"] == EvidenceLevel.STANDARD.value

    def test_empty_dict_returns_defaults(self):
        """An empty dict is normalised to ExecutionContext() defaults."""
        normalized = normalize_execution_context({})
        # defaults from the ExecutionContext model
        assert normalized["validation_mode"] == ValidationMode.PROOF.value
        assert normalized["evidence_level"] == EvidenceLevel.STANDARD.value

    def test_none_returns_defaults(self):
        """None input falls back to ExecutionContext() defaults."""
        normalized = normalize_execution_context(None)
        assert normalized["validation_mode"] == ValidationMode.PROOF.value
        assert normalized["evidence_level"] == EvidenceLevel.STANDARD.value

    def test_arbitrary_dict_is_normalised(self):
        """An arbitrary dict is converted via ExecutionContext(**raw)."""
        normalized = normalize_execution_context(
            {"validation_mode": "detect_only", "evidence_level": "minimal"}
        )
        assert normalized["validation_mode"] == "detect_only"
        assert normalized["evidence_level"] == "minimal"

    def test_normalize_returns_dict(self):
        """The return value is always a plain dict."""
        for value in (None, {}, {"validation_mode": "proof"}):
            assert isinstance(normalize_execution_context(value), dict)

    def test_normalize_does_not_mutate_input(self):
        """normalize_execution_context must not mutate the input dict."""
        original = {"validation_mode": "detect_only", "evidence_level": "minimal"}
        snapshot = dict(original)
        normalize_execution_context(original)
        assert original == snapshot


# ---------------------------------------------------------------------------
# is_offensive_validation
# ---------------------------------------------------------------------------


class TestIsOffensiveValidation:
    def test_detect_only_is_not_offensive(self):
        assert is_offensive_validation({"validation_mode": "detect_only"}) is False

    def test_proof_is_offensive(self):
        assert is_offensive_validation({"validation_mode": "proof"}) is True

    def test_controlled_extract_is_offensive(self):
        assert is_offensive_validation({"validation_mode": "controlled_extract"}) is True

    def test_missing_validation_mode_defaults_to_offensive(self):
        """No validation_mode key → defaults to PROOF → offensive."""
        assert is_offensive_validation({}) is True

    def test_none_validation_mode_defaults_to_offensive(self):
        assert is_offensive_validation({"validation_mode": None}) is True

    def test_unknown_validation_mode_is_not_offensive(self):
        """An unknown validation_mode is treated as non-offensive (safe default)."""
        assert is_offensive_validation({"validation_mode": "exploit_everything"}) is False

    def test_empty_string_validation_mode_defaults_to_offensive(self):
        """An empty-string validation_mode is treated like a missing value and
        falls back to PROOF (i.e. offensive). The ``or`` operator in
        ``is_offensive_validation`` deliberately uses truthiness, not a key
        presence check, so the falsy empty string behaves like a missing key."""
        assert is_offensive_validation({"validation_mode": ""}) is True

    def test_extra_keys_are_ignored(self):
        """Unrelated keys do not influence the offensive classification."""
        assert is_offensive_validation(
            {"validation_mode": "detect_only", "evidence_level": "full"}
        ) is False
        assert is_offensive_validation(
            {"validation_mode": "proof", "evidence_level": "minimal"}
        ) is True


# ---------------------------------------------------------------------------
# evidence_level_rank
# ---------------------------------------------------------------------------


class TestEvidenceLevelRank:
    def test_minimal_rank(self):
        assert evidence_level_rank(EvidenceLevel.MINIMAL.value) == 0

    def test_standard_rank(self):
        assert evidence_level_rank(EvidenceLevel.STANDARD.value) == 1

    def test_full_rank(self):
        assert evidence_level_rank(EvidenceLevel.FULL.value) == 2

    def test_ranks_are_strictly_ordered(self):
        ranks = [
            evidence_level_rank(EvidenceLevel.MINIMAL.value),
            evidence_level_rank(EvidenceLevel.STANDARD.value),
            evidence_level_rank(EvidenceLevel.FULL.value),
        ]
        assert ranks == sorted(ranks)
        assert len(set(ranks)) == 3

    def test_unknown_level_defaults_to_standard(self):
        """An unknown level falls back to the rank of standard (1)."""
        assert evidence_level_rank("extreme") == 1
        assert evidence_level_rank("") == 1

    def test_returns_int(self):
        for level in ("minimal", "standard", "full", "unknown", ""):
            assert isinstance(evidence_level_rank(level), int)
