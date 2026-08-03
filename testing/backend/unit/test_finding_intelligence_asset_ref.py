"""
Unit tests for finding_intelligence asset reference and signature helper functions.

Covers:
- _extract_best_url: extracts best URL from finding metadata/evidence/target
- _guess_asset_ref: determines the asset_ref for a finding
- _issue_signature: generates a stable deduplication key from finding fields
- _finding_kind_for: classifies a finding as observation, suspected_issue, or validated_issue
"""

from __future__ import annotations

import pytest

from backend.secuscan.finding_intelligence import (
    _extract_best_url,
    _guess_asset_ref,
    _issue_signature,
    _finding_kind_for,
)


# ---------------------------------------------------------------------------
# _extract_best_url
# ---------------------------------------------------------------------------

class TestExtractBestUrl:
    def test_url_in_metadata_url(self):
        finding = {"metadata": {"url": "https://example.com/login"}}
        assert _extract_best_url(finding) == "https://example.com/login"

    def test_url_in_metadata_matched_at(self):
        finding = {"metadata": {"matched_at": "https://example.com/api"}}
        assert _extract_best_url(finding) == "https://example.com/api"

    def test_url_in_metadata_endpoint(self):
        finding = {"metadata": {"endpoint": "https://example.com/admin"}}
        assert _extract_best_url(finding) == "https://example.com/admin"

    def test_url_in_evidence(self):
        finding = {"evidence": [{"value": "https://example.com/admin"}]}
        assert _extract_best_url(finding) == "https://example.com/admin"

    def test_url_in_evidence_skips_non_url(self):
        finding = {"evidence": [{"value": "not-a-url"}]}
        assert _extract_best_url(finding) == ""

    def test_falls_back_to_target(self):
        finding = {"target": "https://example.com"}
        assert _extract_best_url(finding) == "https://example.com"

    def test_non_url_target_returns_empty(self):
        finding = {"target": "/path/only"}
        assert _extract_best_url(finding) == ""

    def test_empty_finding_returns_empty(self):
        assert _extract_best_url({}) == ""

    def test_metadata_not_dict(self):
        finding = {"metadata": "not-a-dict"}
        assert _extract_best_url(finding) == ""

    def test_evidence_not_list(self):
        finding = {"evidence": "not-a-list"}
        assert _extract_best_url(finding) == ""


# ---------------------------------------------------------------------------
# _guess_asset_ref
# ---------------------------------------------------------------------------

class TestGuessAssetRef:
    def test_uses_existing_asset_ref(self):
        finding = {"asset_refs": ["https://example.com/admin"]}
        assert _guess_asset_ref(finding, "https://example.com") == "https://example.com/admin"

    def test_extracts_from_best_url(self):
        finding = {"metadata": {"url": "https://example.com:8080/api"}}
        assert "example.com" in _guess_asset_ref(finding, "https://example.com")

    def test_uses_host_from_metadata(self):
        finding = {"metadata": {"host": "evil.com", "port": 443, "protocol": "tcp"}}
        result = _guess_asset_ref(finding, "https://example.com")
        assert "evil.com" in result

    def test_falls_back_to_target(self):
        finding = {}
        result = _guess_asset_ref(finding, "https://example.com")
        assert "example.com" in result

    def test_empty_asset_refs_returns_empty(self):
        finding = {"asset_refs": []}
        assert _guess_asset_ref(finding, "") == ""


# ---------------------------------------------------------------------------
# _issue_signature
# ---------------------------------------------------------------------------

class TestIssueSignature:
    def test_cve_prefix(self):
        finding = {"cve": "CVE-2021-44228"}
        assert _issue_signature(finding).startswith("cve:")

    def test_cve_normalized_to_lowercase(self):
        finding = {"cve": "CVE-2021-44228"}
        sig = _issue_signature(finding)
        assert sig == "cve:cve-2021-44228"

    def test_no_cve_uses_fields(self):
        finding = {
            "category": "Transport Security",
            "title": "Missing CSP",
            "validation_method": "header-check",
        }
        sig = _issue_signature(finding)
        assert "transport-security" in sig
        assert "missing-csp" in sig
        assert "header-check" in sig

    def test_metadata_detail_used_in_signature(self):
        finding = {
            "category": "api exposure",
            "title": "Open API Endpoint",
            "metadata": {"service": "graphql"},
        }
        sig = _issue_signature(finding)
        assert "graphql" in sig

    def test_empty_finding_returns_non_empty_string(self):
        sig = _issue_signature({})
        # Returns a non-empty string (falls back to 'finding' when compact is all dashes)
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_signature_is_deterministic(self):
        finding = {"category": "a", "title": "b"}
        sig1 = _issue_signature(finding)
        sig2 = _issue_signature(finding)
        assert sig1 == sig2

    def test_different_finding_different_signature(self):
        sig1 = _issue_signature({"category": "a", "title": "b"})
        sig2 = _issue_signature({"category": "a", "title": "c"})
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# _finding_kind_for
# ---------------------------------------------------------------------------

class TestFindingKindFor:
    def test_validated_observation_category_is_observation(self):
        # "information disclosure" is in _OBSERVATION_CATEGORIES, so validated_issue
        # requires category NOT in _OBSERVATION_CATEGORIES
        finding = {"validated": True, "category": "information disclosure", "severity": "high"}
        assert _finding_kind_for(finding) == "observation"

    def test_observation_category_no_cve_is_observation(self):
        finding = {"category": "asset discovery", "severity": "info"}
        assert _finding_kind_for(finding) == "observation"

    def test_critical_severity_is_suspected_issue(self):
        finding = {"severity": "critical"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_high_severity_is_suspected_issue(self):
        finding = {"severity": "high"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_medium_severity_is_suspected_issue(self):
        finding = {"severity": "medium"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_cve_is_suspected_issue(self):
        finding = {"cve": "CVE-2021-44228", "category": "asset discovery"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_cpe_cve_correlation_observation_category_is_observation(self):
        # "asset discovery" is in _OBSERVATION_CATEGORIES, returns observation
        finding = {"validation_method": "cpe_cve_correlation", "category": "asset discovery"}
        assert _finding_kind_for(finding) == "observation"

    def test_low_severity_no_cve_is_observation(self):
        finding = {"severity": "low"}
        assert _finding_kind_for(finding) == "observation"

    def test_info_severity_is_observation(self):
        finding = {"severity": "info", "category": "transport security"}
        assert _finding_kind_for(finding) == "observation"

    def test_observation_category_with_cve_is_suspected(self):
        finding = {"category": "service exposure", "cve": "CVE-2021-44228"}
        assert _finding_kind_for(finding) == "suspected_issue"

    def test_empty_finding_is_observation(self):
        assert _finding_kind_for({}) == "observation"
