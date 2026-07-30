"""
Unit tests for _contextual_severity_score in backend/secuscan/risk_scoring.py

Covers:
- custom_override bypasses calculation and returns clamped value
- base_severity * exposure_mult * criticality_mult is correctly clamped to [0, 10]
- exposure_context=None and unknown values default to multiplier 1.0
- business_criticality=None and unknown values default to multiplier 1.0
- known exposure_context values apply correct multipliers
- known business_criticality values apply correct multipliers
- result is always a float in [0, 10]
- extreme combinations are clamped
"""

from __future__ import annotations

import pytest

from backend.secuscan.risk_scoring import (
    _contextual_severity_score,
)


# ---------------------------------------------------------------------------
# custom_override
# ---------------------------------------------------------------------------


class TestCustomOverride:
    def test_custom_override_within_bounds_returns_clamped_value(self):
        """A custom_override within [0, 10] is returned unchanged."""
        assert _contextual_severity_score(5.0, custom_override=7.5) == 7.5

    def test_custom_override_above_10_clamped_to_10(self):
        """A custom_override above 10.0 is clamped to 10.0."""
        assert _contextual_severity_score(5.0, custom_override=15.0) == 10.0

    def test_custom_override_negative_clamped_to_0(self):
        """A negative custom_override is clamped to 0.0."""
        assert _contextual_severity_score(5.0, custom_override=-2.0) == 0.0

    def test_custom_override_exactly_0(self):
        """A custom_override of exactly 0.0 returns 0.0."""
        assert _contextual_severity_score(5.0, custom_override=0.0) == 0.0

    def test_custom_override_exactly_10(self):
        """A custom_override of exactly 10.0 returns 10.0."""
        assert _contextual_severity_score(5.0, custom_override=10.0) == 10.0

    def test_custom_override_bypasses_exposure_and_criticality(self):
        """When custom_override is set, exposure_context and business_criticality are ignored."""
        result = _contextual_severity_score(
            5.0,
            exposure_context="public",
            business_criticality="critical",
            custom_override=3.0,
        )
        assert result == 3.0


# ---------------------------------------------------------------------------
# exposure_context multipliers
# ---------------------------------------------------------------------------


class TestExposureContextMultipliers:
    def test_none_exposure_defaults_to_1(self):
        """None exposure_context uses the default multiplier of 1.0."""
        # 5.0 * 1.0 * 1.0 = 5.0
        assert _contextual_severity_score(5.0) == 5.0

    def test_unknown_exposure_defaults_to_1(self):
        """An unknown exposure_context value uses the default multiplier of 1.0."""
        assert _contextual_severity_score(5.0, exposure_context="unknown") == 5.0

    def test_public_exposure_multiplier_is_1_5(self):
        """public exposure applies 1.5x multiplier."""
        # 5.0 * 1.5 * 1.0 = 7.5
        assert _contextual_severity_score(5.0, exposure_context="public") == 7.5

    def test_internet_facing_multiplier_is_1_3(self):
        """internet_facing exposure applies 1.3x multiplier."""
        # 5.0 * 1.3 * 1.0 = 6.5
        assert _contextual_severity_score(5.0, exposure_context="internet_facing") == 6.5

    def test_internal_exposure_multiplier_is_0_8(self):
        """internal exposure applies 0.8x multiplier."""
        # 5.0 * 0.8 * 1.0 = 4.0
        assert _contextual_severity_score(5.0, exposure_context="internal") == 4.0

    def test_private_exposure_multiplier_is_0_6(self):
        """private exposure applies 0.6x multiplier."""
        # 5.0 * 0.6 * 1.0 = 3.0
        assert _contextual_severity_score(5.0, exposure_context="private") == 3.0

    def test_exposure_context_case_insensitive(self):
        """exposure_context lookup is case-insensitive."""
        assert _contextual_severity_score(5.0, exposure_context="PUBLIC") == 7.5
        assert _contextual_severity_score(5.0, exposure_context="Public") == 7.5


# ---------------------------------------------------------------------------
# business_criticality multipliers
# ---------------------------------------------------------------------------


class TestBusinessCriticalityMultipliers:
    def test_none_criticality_defaults_to_1(self):
        """None business_criticality uses the default multiplier of 1.0."""
        assert _contextual_severity_score(5.0, business_criticality=None) == 5.0

    def test_unknown_criticality_defaults_to_1(self):
        """An unknown business_criticality value uses the default multiplier of 1.0."""
        assert _contextual_severity_score(5.0, business_criticality="unknown") == 5.0

    def test_critical_criticality_multiplier_is_1_5(self):
        """critical business_criticality applies 1.5x multiplier."""
        # 5.0 * 1.0 * 1.5 = 7.5
        assert _contextual_severity_score(5.0, business_criticality="critical") == 7.5

    def test_high_criticality_multiplier_is_1_25(self):
        """high business_criticality applies 1.25x multiplier."""
        # 5.0 * 1.0 * 1.25 = 6.25
        assert _contextual_severity_score(5.0, business_criticality="high") == 6.25

    def test_medium_criticality_multiplier_is_1_0(self):
        """medium business_criticality applies 1.0x multiplier (no change)."""
        assert _contextual_severity_score(5.0, business_criticality="medium") == 5.0

    def test_low_criticality_multiplier_is_0_8(self):
        """low business_criticality applies 0.8x multiplier."""
        # 5.0 * 1.0 * 0.8 = 4.0
        assert _contextual_severity_score(5.0, business_criticality="low") == 4.0

    def test_criticality_case_insensitive(self):
        """business_criticality lookup is case-insensitive."""
        assert _contextual_severity_score(5.0, business_criticality="CRITICAL") == 7.5


# ---------------------------------------------------------------------------
# combined multipliers
# ---------------------------------------------------------------------------


class TestCombinedMultipliers:
    def test_public_exposure_and_critical_criticality(self):
        """public (1.5) * critical (1.5) = 2.25x combined multiplier."""
        # 5.0 * 2.25 = 11.25, clamped to 10.0
        assert _contextual_severity_score(
            5.0, exposure_context="public", business_criticality="critical"
        ) == 10.0

    def test_private_exposure_and_low_criticality(self):
        """private (0.6) * low (0.8) = 0.48x combined multiplier."""
        # 5.0 * 0.48 = 2.4
        result = _contextual_severity_score(
            5.0, exposure_context="private", business_criticality="low"
        )
        assert result == pytest.approx(2.4)


# ---------------------------------------------------------------------------
# clamping boundary cases
# ---------------------------------------------------------------------------


class TestClamping:
    def test_extreme_high_product_is_clamped_to_10(self):
        """base_severity * exposure_mult * criticality_mult > 10 is clamped to 10.0."""
        # 10.0 * 1.5 * 1.5 = 22.5 -> 10.0
        assert _contextual_severity_score(
            10.0, exposure_context="public", business_criticality="critical"
        ) == 10.0

    def test_extreme_negative_result_is_clamped_to_0(self):
        """A negative result from the multiplication is clamped to 0.0."""
        # Negative base severity: -5.0 * 1.0 * 1.0 = -5.0 -> 0.0
        assert _contextual_severity_score(-5.0) == 0.0

    def test_base_0_severity_returns_0(self):
        """base_severity of 0.0 returns 0.0 regardless of multipliers."""
        assert _contextual_severity_score(0.0) == 0.0
        assert _contextual_severity_score(
            0.0, exposure_context="public", business_criticality="critical"
        ) == 0.0

    def test_result_at_exact_upper_bound(self):
        """A result exactly at 10.0 is returned as 10.0."""
        # 10.0 * 1.0 * 1.0 = 10.0
        assert _contextual_severity_score(10.0) == 10.0

    def test_returns_float(self):
        """The return value is always a float."""
        for args in [
            {"base_severity": 5.0},
            {"base_severity": 5.0, "exposure_context": "public"},
            {"base_severity": 5.0, "business_criticality": "critical"},
            {"base_severity": 2.0, "exposure_context": "internal", "business_criticality": "low"},
            {"base_severity": 5.0, "custom_override": 3.0},
        ]:
            result = _contextual_severity_score(**args)
            assert isinstance(result, float), f"Failed for args: {args}"
