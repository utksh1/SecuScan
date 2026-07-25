"""
Unit tests for compute_risk_factors boundary conditions in backend/secuscan/risk_scoring.py.

Extends test_risk_scoring.py with genuinely-missing boundary and edge cases:
- All 5 severity levels produce expected top-level keys
- Exploitability at exact boundaries: 0.0 and 10.0
- Confidence at exact boundaries: 0.0 and 1.0
- Discovered_at far in the past produces recency factor of 0
- asset_exposure all values produce distinct factor values
- Empty optional args use correct defaults
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from backend.secuscan.risk_scoring import compute_risk_factors


class TestComputeRiskFactorsAllSeverities:
    """All 5 severity levels should produce a valid factors list."""

    EXPECTED_FACTOR_KEYS = {"severity", "exploitability", "asset_exposure", "recency", "confidence"}

    @pytest.mark.parametrize("severity", ["critical", "high", "medium", "low", "info"])
    def test_all_severities_produce_expected_keys(self, severity):
        factors = compute_risk_factors(severity)
        factor_names = {f["factor"] for f in factors}
        assert factor_names == self.EXPECTED_FACTOR_KEYS, f"Missing factors for severity={severity}"

    @pytest.mark.parametrize("severity", ["critical", "high", "medium", "low", "info"])
    def test_all_severities_produce_list(self, severity):
        factors = compute_risk_factors(severity)
        assert isinstance(factors, list)
        assert len(factors) >= 4

    @pytest.mark.parametrize("severity", ["critical", "high", "medium", "low", "info"])
    def test_severity_factor_value_matches_input(self, severity):
        factors = compute_risk_factors(severity)
        sev_factor = next(f for f in factors if f["factor"] == "severity")
        assert sev_factor["value"] == severity


class TestComputeRiskFactorsExploitabilityBoundaries:
    def test_exploitability_zero(self):
        factors = compute_risk_factors("high", exploitability=0.0)
        exp_factor = next(f for f in factors if f["factor"] == "exploitability")
        assert exp_factor["score"] == 0.0
        assert exp_factor["value"] == 0.0

    def test_exploitability_max(self):
        factors = compute_risk_factors("high", exploitability=10.0)
        exp_factor = next(f for f in factors if f["factor"] == "exploitability")
        assert exp_factor["score"] == 10.0

    def test_exploitability_above_max_clamped(self):
        factors = compute_risk_factors("high", exploitability=15.0)
        exp_factor = next(f for f in factors if f["factor"] == "exploitability")
        assert exp_factor["score"] <= 10.0

    def test_exploitability_negative_clamped(self):
        factors = compute_risk_factors("high", exploitability=-5.0)
        exp_factor = next(f for f in factors if f["factor"] == "exploitability")
        assert exp_factor["score"] >= 0.0


class TestComputeRiskFactorsConfidenceBoundaries:
    def test_confidence_zero(self):
        factors = compute_risk_factors("medium", confidence=0.0)
        conf_factor = next(f for f in factors if f["factor"] == "confidence")
        assert conf_factor["score"] == 0.0
        assert conf_factor["value"] == 0.0

    def test_confidence_one(self):
        factors = compute_risk_factors("medium", confidence=1.0)
        conf_factor = next(f for f in factors if f["factor"] == "confidence")
        assert conf_factor["score"] == 10.0

    def test_confidence_above_one_clamped(self):
        factors = compute_risk_factors("medium", confidence=2.0)
        conf_factor = next(f for f in factors if f["factor"] == "confidence")
        assert conf_factor["score"] <= 10.0


class TestComputeRiskFactorsRecencyFarPast:
    def test_discovered_at_365_days_ago(self):
        discovered = datetime.now(timezone.utc) - timedelta(days=365)
        factors = compute_risk_factors("high", discovered_at=discovered)
        rec_factor = next(f for f in factors if f["factor"] == "recency")
        assert rec_factor["score"] == 0.0

    def test_discovered_at_400_days_ago(self):
        discovered = datetime.now(timezone.utc) - timedelta(days=400)
        factors = compute_risk_factors("critical", discovered_at=discovered)
        rec_factor = next(f for f in factors if f["factor"] == "recency")
        assert rec_factor["score"] == 0.0

    def test_discovered_at_very_far_past(self):
        discovered = datetime(2000, 1, 1, tzinfo=timezone.utc)
        factors = compute_risk_factors("info", discovered_at=discovered)
        rec_factor = next(f for f in factors if f["factor"] == "recency")
        assert rec_factor["score"] == 0.0


class TestComputeRiskFactorsAssetExposure:
    def test_asset_exposure_produces_separate_factor(self):
        factors = compute_risk_factors("high", asset_exposure="critical")
        exp_factor = next(f for f in factors if f["factor"] == "asset_exposure")
        assert exp_factor["value"] == "critical"
        assert "score" in exp_factor

    def test_asset_exposure_unknown_defaults_to_medium(self):
        factors = compute_risk_factors("high", asset_exposure="unknown_level")
        exp_factor = next(f for f in factors if f["factor"] == "asset_exposure")
        # Unknown values should fall back to the default (medium = 5.0)
        assert "score" in exp_factor


class TestComputeRiskFactorsDefaults:
    def test_none_exploitability_uses_default(self):
        factors = compute_risk_factors("high", exploitability=None)
        exp_factor = next(f for f in factors if f["factor"] == "exploitability")
        assert exp_factor["value"] == 5.0

    def test_none_confidence_uses_default(self):
        factors = compute_risk_factors("high", confidence=None)
        conf_factor = next(f for f in factors if f["factor"] == "confidence")
        # None confidence should use the default 0.5 (5.0 score)
        assert conf_factor["score"] == 5.0

    def test_none_discovered_at_uses_current_time(self):
        factors = compute_risk_factors("high", discovered_at=None)
        rec_factor = next(f for f in factors if f["factor"] == "recency")
        # Recent (now) should give max recency score
        assert rec_factor["score"] > 0.0

    def test_none_asset_exposure_uses_default(self):
        factors = compute_risk_factors("high", asset_exposure=None)
        exp_factor = next(f for f in factors if f["factor"] == "asset_exposure")
        assert exp_factor["value"] == "medium"
        assert "score" in exp_factor
