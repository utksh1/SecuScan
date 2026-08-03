"""
Unit tests for backend.secuscan.finding_intelligence.build_asset_summary.

Covers:
- Returns empty list for empty inputs
- Single service with no findings produces a valid asset entry
- Findings increment finding_count and validated_count correctly
- Highest severity is tracked correctly (critical > high > medium > low > info)
- Multiple findings on same asset are counted together
- Assets are sorted by severity then count (highest first)
- Missing asset_id falls back to stable_id from target/host/port
- Missing asset_id in finding falls back to stable_id from target/asset_refs
"""

import pytest

from backend.secuscan.finding_intelligence import build_asset_summary


class TestBuildAssetSummary:
    def test_empty_inputs_returns_empty_list(self):
        result = build_asset_summary([], [])
        assert result == []

    def test_single_service_no_findings(self):
        services = [
            {
                "asset_id": "asset-1",
                "host": "192.168.1.10",
                "target": "192.168.1.10",
                "port": 443,
                "protocol": "https",
            }
        ]
        result = build_asset_summary([], services)
        assert len(result) == 1
        assert result[0]["finding_count"] == 0
        assert result[0]["validated_count"] == 0
        assert result[0]["highest_severity"] == "info"

    def test_finding_increments_count(self):
        services = [{"asset_id": "asset-1", "host": "10.0.0.1", "target": "10.0.0.1"}]
        findings = [
            {"asset_id": "asset-1", "severity": "high", "validated": False},
            {"asset_id": "asset-1", "severity": "medium", "validated": True},
        ]
        result = build_asset_summary(findings, services)
        assert result[0]["finding_count"] == 2
        assert result[0]["validated_count"] == 1

    def test_highest_severity_tracked(self):
        services = [{"asset_id": "asset-x", "host": "10.0.0.2", "target": "10.0.0.2"}]
        findings = [
            {"asset_id": "asset-x", "severity": "low", "validated": False},
            {"asset_id": "asset-x", "severity": "critical", "validated": False},
            {"asset_id": "asset-x", "severity": "info", "validated": False},
        ]
        result = build_asset_summary(findings, services)
        assert result[0]["highest_severity"] == "critical"

    def test_highest_severity_order_critical_gt_high_gt_medium_gt_low_gt_info(self):
        services = [
            {"asset_id": "a1", "host": "10.0.0.1", "target": "10.0.0.1"},
            {"asset_id": "a2", "host": "10.0.0.2", "target": "10.0.0.2"},
            {"asset_id": "a3", "host": "10.0.0.3", "target": "10.0.0.3"},
            {"asset_id": "a4", "host": "10.0.0.4", "target": "10.0.0.4"},
            {"asset_id": "a5", "host": "10.0.0.5", "target": "10.0.0.5"},
        ]
        findings = [
            {"asset_id": "a1", "severity": "info"},
            {"asset_id": "a2", "severity": "low"},
            {"asset_id": "a3", "severity": "medium"},
            {"asset_id": "a4", "severity": "high"},
            {"asset_id": "a5", "severity": "critical"},
        ]
        result = build_asset_summary(findings, services)
        severities = {r["asset_id"]: r["highest_severity"] for r in result}
        assert severities["a5"] == "critical"
        assert severities["a4"] == "high"
        assert severities["a3"] == "medium"
        assert severities["a2"] == "low"
        assert severities["a1"] == "info"

    def test_sorted_by_severity_then_count(self):
        services = [
            {"asset_id": "s1", "host": "10.0.0.1", "target": "10.0.0.1"},
            {"asset_id": "s2", "host": "10.0.0.2", "target": "10.0.0.2"},
        ]
        findings = [
            {"asset_id": "s1", "severity": "info"},
            {"asset_id": "s2", "severity": "critical"},
        ]
        result = build_asset_summary(findings, services)
        # critical should come before info
        assert result[0]["highest_severity"] == "critical"
        assert result[1]["highest_severity"] == "info"

    def test_multiple_findings_same_asset_aggregated(self):
        services = [{"asset_id": "asset-1", "host": "10.0.0.1", "target": "10.0.0.1"}]
        findings = [
            {"asset_id": "asset-1", "severity": "high", "validated": True},
            {"asset_id": "asset-1", "severity": "medium", "validated": False},
            {"asset_id": "asset-1", "severity": "high", "validated": True},
        ]
        result = build_asset_summary(findings, services)
        assert len(result) == 1
        assert result[0]["finding_count"] == 3
        assert result[0]["validated_count"] == 2
        assert result[0]["highest_severity"] == "high"

    def test_missing_asset_id_falls_back_to_stable_id(self):
        services = [
            {"host": "10.0.0.1", "target": "10.0.0.1", "port": 8080, "protocol": "http"}
        ]
        result = build_asset_summary([], services)
        assert len(result) == 1
        assert result[0]["asset_id"] is not None
        assert result[0]["asset_id"].startswith("asset:")

    def test_finding_without_asset_id_falls_back_to_target(self):
        services = []
        findings = [
            {"target": "https://example.com", "severity": "high"},
        ]
        result = build_asset_summary(findings, services)
        assert len(result) == 1
        assert "example.com" in result[0]["asset_id"] or "example.com" in result[0]["label"]

    def test_service_and_finding_same_asset_merged(self):
        services = [
            {"asset_id": "shared-1", "host": "10.0.0.5", "target": "10.0.0.5", "port": 443}
        ]
        findings = [
            {"asset_id": "shared-1", "severity": "medium", "validated": False}
        ]
        result = build_asset_summary(findings, services)
        assert len(result) == 1
        assert result[0]["finding_count"] == 1
