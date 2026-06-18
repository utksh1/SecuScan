"""
Tests for backend.secuscan.execution_context pure helper functions.

Covers:
- normalize_execution_context with ExecutionContext, dict, and unknown types
- is_offensive_validation with each ValidationMode and missing key
- evidence_level_rank for all defined levels and unknown levels
"""

import pytest

from backend.secuscan.execution_context import (
    normalize_execution_context,
    is_offensive_validation,
    evidence_level_rank,
)
from backend.secuscan.models import ExecutionContext, ValidationMode, EvidenceLevel


class TestNormalizeExecutionContext:
    def test_with_execution_context_instance(self):
        ctx = ExecutionContext(
            validation_mode=ValidationMode.PROOF,
            evidence_level=EvidenceLevel.FULL,
        )
        result = normalize_execution_context(ctx)
        assert isinstance(result, dict)
        assert result["validation_mode"] == ValidationMode.PROOF.value
        assert result["evidence_level"] == EvidenceLevel.FULL.value

    def test_with_plain_dict(self):
        raw = {
            "validation_mode": "detect_only",
            "evidence_level": "minimal",
        }
        result = normalize_execution_context(raw)
        assert isinstance(result, dict)
        assert result["validation_mode"] == "detect_only"
        assert result["evidence_level"] == "minimal"

    def test_with_empty_dict(self):
        result = normalize_execution_context({})
        assert isinstance(result, dict)
        # Default values from ExecutionContext()
        assert "validation_mode" in result

    def test_with_none(self):
        result = normalize_execution_context(None)
        assert isinstance(result, dict)
        # Returns default ExecutionContext dump
        assert "validation_mode" in result

    def test_with_unknown_type_returns_default(self):
        result = normalize_execution_context("not a context")
        assert isinstance(result, dict)
        assert "validation_mode" in result


class TestIsOffensiveValidation:
    def test_proof_mode_is_offensive(self):
        ctx = {"validation_mode": ValidationMode.PROOF.value}
        assert is_offensive_validation(ctx) is True

    def test_controlled_extract_mode_is_offensive(self):
        ctx = {"validation_mode": ValidationMode.CONTROLLED_EXTRACT.value}
        assert is_offensive_validation(ctx) is True

    def test_detect_only_mode_is_not_offensive(self):
        ctx = {"validation_mode": ValidationMode.DETECT_ONLY.value}
        assert is_offensive_validation(ctx) is False

    def test_missing_validation_mode_key_defaults_to_proof(self):
        ctx = {}
        # Defaults to PROOF which IS offensive
        assert is_offensive_validation(ctx) is True

    def test_unknown_validation_mode_is_not_offensive(self):
        ctx = {"validation_mode": "unknown_mode"}
        assert is_offensive_validation(ctx) is False

    def test_none_validation_mode_defaults_to_proof(self):
        ctx = {"validation_mode": None}
        assert is_offensive_validation(ctx) is True


class TestEvidenceLevelRank:
    def test_minimal_returns_0(self):
        assert evidence_level_rank(EvidenceLevel.MINIMAL.value) == 0

    def test_standard_returns_1(self):
        assert evidence_level_rank(EvidenceLevel.STANDARD.value) == 1

    def test_full_returns_2(self):
        assert evidence_level_rank(EvidenceLevel.FULL.value) == 2

    def test_unknown_level_defaults_to_1(self):
        assert evidence_level_rank("unknown_level") == 1
        assert evidence_level_rank("") == 1
        assert evidence_level_rank("MINIMAL ") == 1  # not exact match
