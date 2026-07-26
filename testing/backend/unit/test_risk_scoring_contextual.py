"""
Unit tests for backend.secuscan.risk_scoring._contextual_severity_score.

The function adjusts severity scores based on system exposure and business
criticality context.  This is a pure helper that can be tested in isolation
without any external dependencies.
risk_scoring.py re-exports it so existing call sites keep working unchanged.
"""

import pytest
from backend.secuscan.risk_scoring import _contextual_severity_score


class TestContextualSeverityScore:
    def test_custom_override_bypasses_calculation(self):
        """custom_override takes precedence over all other parameters."""
        result = _contextual_severity_score(
            base_severity=10.0,
            exposure_context="public",
            business_criticality="critical",
            custom_override=7.0,
        )
        assert result == 7.0

    def test_custom_override_clamped_to_10(self):
        """custom_override values above 10.0 are clamped to 10.0."""
        assert _contextual_severity_score(5.0, None, None, custom_override=15.0) == 10.0

    def test_custom_override_clamped_to_0(self):
        """custom_override values below 0.0 are clamped to 0.0."""
        assert _contextual_severity_score(5.0, None, None, custom_override=-2.0) == 0.0

    def test_boosts_for_public_exposure(self):
        """public exposure multiplies base severity by 1.5."""
        result = _contextual_severity_score(6.0, exposure_context="public")
        assert result == 9.0  # 6.0 * 1.5 * 1.0

    def test_boosts_for_internet_facing_exposure(self):
        """internet_facing exposure multiplies base severity by 1.3."""
        result = _contextual_severity_score(5.0, exposure_context="internet_facing")
        assert result == 6.5  # 5.0 * 1.3 * 1.0

    def test_reduces_for_internal_exposure(self):
        """internal exposure multiplies base severity by 0.8."""
        result = _contextual_severity_score(5.0, exposure_context="internal")
        assert result == 4.0  # 5.0 * 0.8 * 1.0

    def test_reduces_for_private_exposure(self):
        """private exposure multiplies base severity by 0.6."""
        result = _contextual_severity_score(5.0, exposure_context="private")
        assert result == 3.0  # 5.0 * 0.6 * 1.0

    def test_unknown_exposure_defaults_to_no_multiplier(self):
        """Unknown exposure context uses default multiplier of 1.0."""
        result = _contextual_severity_score(5.0, exposure_context="unknown_context")
        assert result == 5.0

    def test_no_exposure_context_uses_default_multiplier(self):
        """None exposure_context uses default multiplier of 1.0."""
        result = _contextual_severity_score(5.0, exposure_context=None)
        assert result == 5.0

    def test_boosts_for_critical_business_criticality(self):
        """critical business criticality multiplies by 1.5."""
        result = _contextual_severity_score(6.0, business_criticality="critical")
        assert result == 9.0  # 6.0 * 1.0 * 1.5

    def test_boosts_for_high_business_criticality(self):
        """high business criticality multiplies by 1.25."""
        result = _contextual_severity_score(8.0, business_criticality="high")
        assert result == 10.0  # 8.0 * 1.0 * 1.25 = 10.0

    def test_no_change_for_medium_business_criticality(self):
        """medium business criticality has multiplier of 1.0."""
        result = _contextual_severity_score(5.0, business_criticality="medium")
        assert result == 5.0

    def test_reduces_for_low_business_criticality(self):
        """low business criticality multiplies by 0.8."""
        result = _contextual_severity_score(5.0, business_criticality="low")
        assert result == 4.0  # 5.0 * 1.0 * 0.8

    def test_unknown_business_criticality_defaults_to_no_multiplier(self):
        """Unknown business criticality uses default multiplier of 1.0."""
        result = _contextual_severity_score(5.0, business_criticality="unknown")
        assert result == 5.0

    def test_no_business_criticality_uses_default_multiplier(self):
        """None business_criticality uses default multiplier of 1.0."""
        result = _contextual_severity_score(5.0, business_criticality=None)
        assert result == 5.0

    def test_combined_public_exposure_and_critical_criticality(self):
        """Both exposure and criticality multipliers apply together."""
        # 5.0 * 1.5 (public) * 1.5 (critical) = 11.25 -> clamped to 10.0
        result = _contextual_severity_score(
            5.0, exposure_context="public", business_criticality="critical"
        )
        assert result == 10.0

    def test_combined_private_exposure_and_low_criticality(self):
        """Both multipliers reduce the score together."""
        # 5.0 * 0.6 (private) * 0.8 (low) = 2.4
        result = _contextual_severity_score(
            5.0, exposure_context="private", business_criticality="low"
        )
        assert result == pytest.approx(2.4)

    def test_clamp_at_max_10(self):
        """Result is clamped to 10.0 even when multipliers would exceed it."""
        result = _contextual_severity_score(
            8.0, exposure_context="public", business_criticality="critical"
        )
        # 8.0 * 1.5 * 1.5 = 18.0 -> clamped to 10.0
        assert result == 10.0

    def test_clamp_at_min_0(self):
        """Result is clamped to 0.0 (though inputs should not produce negative)."""
        # Even with negative multipliers, result should not go below 0
        result = _contextual_severity_score(0.0, exposure_context="public", business_criticality="critical")
        assert result == 0.0

    def test_case_insensitive_exposure_context(self):
        """Exposure context lookup is case-insensitive."""
        assert _contextual_severity_score(5.0, exposure_context="PUBLIC") == 7.5
        assert _contextual_severity_score(5.0, exposure_context="Public") == 7.5

    def test_case_insensitive_business_criticality(self):
        """Business criticality lookup is case-insensitive."""
        assert _contextual_severity_score(5.0, business_criticality="CRITICAL") == 7.5
        assert _contextual_severity_score(5.0, business_criticality="Critical") == 7.5
