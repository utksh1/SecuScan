"""
Unit tests for backend.secuscan.execution_context pure helpers.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.execution_context import (
    normalize_execution_context,
    is_offensive_validation,
    evidence_level_rank,
)
from backend.secuscan.models import ExecutionContext, ValidationMode, EvidenceLevel


class TestNormalizeExecutionContext:
    def test_with_execution_context_model(self):
        ctx = ExecutionContext(validation_mode="proof", evidence_level="standard")
        result = normalize_execution_context(ctx)
        assert isinstance(result, dict)
        assert "validation_mode" in result

    def test_with_dict(self):
        raw = {"validation_mode": "proof", "evidence_level": "standard"}
        result = normalize_execution_context(raw)
        assert isinstance(result, dict)
        assert result["validation_mode"] == "proof"

    def test_with_non_dict_raw(self):
        result = normalize_execution_context("not a context")
        assert isinstance(result, dict)
        # should return default ExecutionContext
        assert "validation_mode" in result

    def test_with_none(self):
        result = normalize_execution_context(None)
        assert isinstance(result, dict)


class TestIsOffensiveValidation:
    def test_proof_is_offensive(self):
        assert is_offensive_validation({"validation_mode": "proof"}) is True

    def test_controlled_extract_is_offensive(self):
        assert is_offensive_validation({"validation_mode": "controlled_extract"}) is True

    def test_detect_is_not_offensive(self):
        assert is_offensive_validation({"validation_mode": "detect"}) is False

    def test_missing_key_defaults_to_proof(self):
        # defaults to ValidationMode.PROOF which is offensive
        assert is_offensive_validation({}) is True

    def test_unknown_mode_is_not_offensive(self):
        assert is_offensive_validation({"validation_mode": "unknown_mode"}) is False


class TestEvidenceLevelRank:
    def test_minimal_returns_0(self):
        assert evidence_level_rank(EvidenceLevel.MINIMAL.value) == 0

    def test_standard_returns_1(self):
        assert evidence_level_rank(EvidenceLevel.STANDARD.value) == 1

    def test_full_returns_2(self):
        assert evidence_level_rank(EvidenceLevel.FULL.value) == 2

    def test_unknown_defaults_to_1(self):
        assert evidence_level_rank("unknown_level") == 1

    def test_string_inputs(self):
        assert evidence_level_rank("minimal") == 0
        assert evidence_level_rank("standard") == 1
        assert evidence_level_rank("full") == 2
