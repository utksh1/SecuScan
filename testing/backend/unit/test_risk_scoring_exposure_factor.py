"""
Unit tests for _system_exposure_factor in backend/secuscan/risk_scoring.

Imports the real production function so regressions in exposure multiplier mapping
are caught directly rather than only indirectly through compute_risk_score.
"""

from __future__ import annotations

import pytest

from backend.secuscan.risk_scoring import (
    EXPOSURE_CONTEXT_MAP,
    _system_exposure_factor,
)


# ---------------------------------------------------------------------------
# _system_exposure_factor
# ---------------------------------------------------------------------------


class TestSystemExposureFactorKnownValues:
    def test_public_returns_1_5(self):
        assert _system_exposure_factor("public") == 1.5

    def test_internet_facing_returns_1_3(self):
        assert _system_exposure_factor("internet_facing") == 1.3

    def test_internal_returns_0_8(self):
        assert _system_exposure_factor("internal") == 0.8

    def test_private_returns_0_6(self):
        assert _system_exposure_factor("private") == 0.6


class TestSystemExposureFactorCaseInsensitivity:
    def test_uppercase(self):
        assert _system_exposure_factor("PUBLIC") == 1.5

    def test_mixed_case(self):
        assert _system_exposure_factor("Internet_Facing") == 1.3

    def test_title_case(self):
        assert _system_exposure_factor("Internal") == 0.8


class TestSystemExposureFactorDefault:
    def test_none_returns_default(self):
        assert _system_exposure_factor(None) == 1.0

    def test_unknown_returns_default(self):
        assert _system_exposure_factor("unknown") == 1.0

    def test_empty_string_returns_default(self):
        assert _system_exposure_factor("") == 1.0

    def test_typo_returns_default(self):
        assert _system_exposure_factor("publc") == 1.0

    def test_whitespace_returns_default(self):
        assert _system_exposure_factor("  public  ") == 1.0


class TestSystemExposureFactorMatchesMap:
    def test_all_defined_contexts_match_map(self):
        for context, expected in EXPOSURE_CONTEXT_MAP.items():
            assert _system_exposure_factor(context) == expected
