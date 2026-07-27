"""
Unit tests for _business_criticality_factor in backend/secuscan/risk_scoring.

Imports the real production function so regressions in criticality multiplier mapping
are caught directly rather than only indirectly through compute_risk_score.
"""

from __future__ import annotations

import pytest

from backend.secuscan.risk_scoring import (
    CRITICALITY_MAP,
    _business_criticality_factor,
)


# ---------------------------------------------------------------------------
# _business_criticality_factor
# ---------------------------------------------------------------------------


class TestBusinessCriticalityFactorKnownValues:
    def test_critical_returns_1_5(self):
        assert _business_criticality_factor("critical") == 1.5

    def test_high_returns_1_25(self):
        assert _business_criticality_factor("high") == 1.25

    def test_medium_returns_1_0(self):
        assert _business_criticality_factor("medium") == 1.0

    def test_low_returns_0_8(self):
        assert _business_criticality_factor("low") == 0.8


class TestBusinessCriticalityFactorCaseInsensitivity:
    def test_uppercase(self):
        assert _business_criticality_factor("CRITICAL") == 1.5

    def test_mixed_case(self):
        assert _business_criticality_factor("High") == 1.25

    def test_title_case(self):
        assert _business_criticality_factor("Medium") == 1.0


class TestBusinessCriticalityFactorDefault:
    def test_none_returns_default(self):
        assert _business_criticality_factor(None) == 1.0

    def test_unknown_returns_default(self):
        assert _business_criticality_factor("unknown") == 1.0

    def test_empty_string_returns_default(self):
        assert _business_criticality_factor("") == 1.0

    def test_typo_returns_default(self):
        assert _business_criticality_factor("critial") == 1.0

    def test_whitespace_returns_default(self):
        assert _business_criticality_factor("  high  ") == 1.0

    def test_info_not_in_map_returns_default(self):
        assert _business_criticality_factor("info") == 1.0


class TestBusinessCriticalityFactorMatchesMap:
    def test_all_defined_levels_match_map(self):
        for level, expected in CRITICALITY_MAP.items():
            assert _business_criticality_factor(level) == expected
