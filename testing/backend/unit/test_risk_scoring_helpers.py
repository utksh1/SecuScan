"""
Unit tests for risk_scoring internal pure helpers.

Covers _clamp, _severity_score, _recency_score, _confidence_score
from backend.secuscan.risk_scoring.
"""

import pytest
from datetime import datetime, timezone, timedelta


class TestClamp:
    def test_within_range_returns_value(self):
        """When value is within bounds, it is returned unchanged."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(5.0, 0.0, 10.0) == 5.0

    def test_below_lo_returns_lo(self):
        """When value is below lo, lo is returned."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(-3.0, 0.0, 10.0) == 0.0

    def test_above_hi_returns_hi(self):
        """When value is above hi, hi is returned."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(15.0, 0.0, 10.0) == 10.0

    def test_default_bounds_are_zero_and_ten(self):
        """Default bounds are 0.0 and 10.0."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(5.0) == 5.0
        assert _clamp(-1.0) == 0.0
        assert _clamp(15.0) == 10.0

    def test_at_boundary_returns_boundary(self):
        """Values exactly at boundaries are returned unchanged."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(0.0, 0.0, 10.0) == 0.0
        assert _clamp(10.0, 0.0, 10.0) == 10.0


class TestSeverityScore:
    def test_critical_returns_10(self):
        """Severity 'critical' maps to 10.0."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("critical") == 10.0

    def test_high_returns_7_5(self):
        """Severity 'high' maps to 7.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("high") == 7.5

    def test_medium_returns_5(self):
        """Severity 'medium' maps to 5.0."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("medium") == 5.0

    def test_low_returns_2_5(self):
        """Severity 'low' maps to 2.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("low") == 2.5

    def test_info_returns_0_5(self):
        """Severity 'info' maps to 0.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("info") == 0.5

    def test_unknown_defaults_to_0_5(self):
        """Unknown severity defaults to 0.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("unknown") == 0.5
        assert _severity_score("") == 0.5

    def test_case_insensitive(self):
        """Severity matching is case-insensitive."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("CRITICAL") == 10.0
        assert _severity_score("High") == 7.5


class TestRecencyScore:
    def test_none_returns_5(self):
        """When discovered_at is None, score is 5.0."""
        from backend.secuscan.risk_scoring import _recency_score
        assert _recency_score(None) == 5.0

    def test_recent_within_week_returns_10(self):
        """A discovery within 7 days returns 10.0."""
        from backend.secuscan.risk_scoring import _recency_score
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        assert _recency_score(recent) == 10.0

    def test_old_within_month_returns_7_5(self):
        """A discovery within 30 days returns 7.5."""
        from backend.secuscan.risk_scoring import _recency_score
        old = datetime.now(timezone.utc) - timedelta(days=15)
        assert _recency_score(old) == 7.5

    def test_old_within_quarter_returns_5(self):
        """A discovery within 90 days returns 5.0."""
        from backend.secuscan.risk_scoring import _recency_score
        old = datetime.now(timezone.utc) - timedelta(days=60)
        assert _recency_score(old) == 5.0


class TestConfidenceScore:
    def test_none_returns_5(self):
        """When confidence is None, score defaults to 5.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(None) == 5.0

    def test_1_returns_10(self):
        """Confidence of 1.0 maps to 10.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(1.0) == 10.0

    def test_0_returns_0(self):
        """Confidence of 0.0 maps to 0.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(0.0) == 0.0

    def test_0_5_returns_5(self):
        """Confidence of 0.5 maps to 5.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(0.5) == 5.0
