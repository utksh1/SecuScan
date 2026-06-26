"""
Unit tests for finding_intelligence build_asset_summary and related helpers.

Covers:
- build_asset_summary: groups findings by asset and computes per-asset stats
- _normalize_url_path: extracts and normalizes URL paths
- _typed_evidence: normalizes evidence items into a standard dict format
"""

from __future__ import annotations

import pytest

from backend.secuscan.finding_intelligence import (
    _normalize_url_path,
    _typed_evidence,
    build_asset_summary,
)


# ---------------------------------------------------------------------------
# _normalize_url_path
# ---------------------------------------------------------------------------

class TestNormalizeUrlPath:
    def test_full_url(self):
        result = _normalize_url_path("https://example.com/admin/users")
        assert result == "/admin/users"

    def test_url_root(self):
        result = _normalize_url_path("https://example.com/")
        assert result == "/"

    def test_url_trailing_slash_normalized(self):
        result = _normalize_url_path("https://example.com/api/")
        assert result == "/api"

    def test_relative_path(self):
        result = _normalize_url_path("/api/v2/users")
        assert result == "/api/v2/users"

    def test_relative_path_trailing_slash(self):
        result = _normalize_url_path("/api/v2/")
        assert result == "/api/v2"

    def test_empty_relative_path(self):
        result = _normalize_url_path("/")
        assert result == "/"

    def test_empty_string(self):
        result = _normalize_url_path("")
        assert result == ""

    def test_path_only_no_leading_slash(self):
        result = _normalize_url_path("api/users")
        assert result == ""


# ---------------------------------------------------------------------------
# _typed_evidence
# ---------------------------------------------------------------------------

class TestTypedEvidence:
    def test_dict_item(self):
        result = _typed_evidence(
            {"type": "header", "label": "Server", "value": "nginx"},
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["type"] == "header"
        assert result["label"] == "Server"
        assert result["value"] == "nginx"
        assert result["source"] == "nuclei"
        assert result["observed_at"] == "2024-01-01T00:00:00Z"
        assert result["confidence"] == 0.85

    def test_non_dict_item(self):
        result = _typed_evidence(
            "plain text evidence",
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["type"] == "evidence"
        assert result["label"] == "Evidence"
        assert result["value"] == "plain text evidence"
        assert result["source"] == "nuclei"
        assert result["confidence"] == 0.85

    def test_confidence_clamped_to_valid_range(self):
        result = _typed_evidence(
            {"value": "x", "confidence": 1.5},
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["confidence"] == 1.0  # clamped to max

    def test_confidence_clamped_to_zero(self):
        result = _typed_evidence(
            {"value": "x", "confidence": -0.5},
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["confidence"] == 0.0  # clamped to min

    def test_item_source_overrides_default(self):
        result = _typed_evidence(
            {"value": "x", "source": "nikto"},
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["source"] == "nikto"

    def test_item_observed_at_overrides_default(self):
        result = _typed_evidence(
            {"value": "x", "observed_at": "2024-06-01T00:00:00Z"},
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["observed_at"] == "2024-06-01T00:00:00Z"

    def test_artifact_ref_preserved(self):
        result = _typed_evidence(
            {"value": "x", "artifact_ref": "artifact:123"},
            source="nuclei",
            observed_at="2024-01-01T00:00:00Z",
            confidence=0.85,
        )
        assert result["artifact_ref"] == "artifact:123"


# ---------------------------------------------------------------------------
# build_asset_summary
# ---------------------------------------------------------------------------

class TestBuildAssetSummary:
    def test_empty_inputs(self):
        result = build_asset_summary([], [])
        assert result == []

    def test_findings_only(self):
        findings = [
            {
                "asset_id": "asset:abc",
                "target": "https://example.com",
                "severity": "high",
                "validated": True,
            },
            {
                "asset_id": "asset:abc",
                "target": "https://example.com",
                "severity": "low",
                "validated": False,
            },
            {
                "asset_id": "asset:xyz",
                "target": "https://test.com",
                "severity": "critical",
                "validated": True,
            },
        ]
        result = build_asset_summary(findings, [])
        assert len(result) == 2
        asset_abc = next(a for a in result if a["asset_id"] == "asset:abc")
        assert asset_abc["finding_count"] == 2
        assert asset_abc["validated_count"] == 1
        assert asset_abc["highest_severity"] == "high"

    def test_services_only(self):
        services = [
            {"asset_id": "asset:svc1", "host": "example.com", "target": "https://example.com"},
            {"asset_id": "asset:svc2", "host": "test.com", "target": "https://test.com"},
        ]
        result = build_asset_summary([], services)
        assert len(result) == 2
        assert result[0]["finding_count"] == 0
        assert result[0]["validated_count"] == 0

    def test_highest_severity_takes_max(self):
        findings = [
            {"asset_id": "asset:test", "severity": "info"},
            {"asset_id": "asset:test", "severity": "critical"},
            {"asset_id": "asset:test", "severity": "low"},
        ]
        result = build_asset_summary(findings, [])
        assert len(result) == 1
        assert result[0]["highest_severity"] == "critical"

    def test_results_sorted_by_severity_then_count(self):
        findings = [
            {"asset_id": "asset:a", "severity": "low"},
            {"asset_id": "asset:b", "severity": "critical"},
            {"asset_id": "asset:c", "severity": "critical"},
        ]
        result = build_asset_summary(findings, [])
        # critical assets come first, then sorted by label
        critical_assets = [a for a in result if a["highest_severity"] == "critical"]
        low_assets = [a for a in result if a["highest_severity"] == "low"]
        assert all(a["highest_severity"] == "critical" for a in critical_assets)
        assert all(a["highest_severity"] == "low" for a in low_assets)

    def test_missing_asset_id_uses_stable_id(self):
        findings = [
            {"target": "https://example.com", "severity": "high"},
        ]
        result = build_asset_summary(findings, [])
        assert len(result) == 1
        assert result[0]["finding_count"] == 1
        assert result[0]["highest_severity"] == "high"
