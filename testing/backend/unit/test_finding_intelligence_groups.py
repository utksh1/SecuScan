"""
Unit tests for build_finding_groups and build_scan_diff functions.

These two public pipeline functions are currently untested. They form the core
of the finding grouping and scan-diff APIs.
"""

from backend.secuscan.finding_intelligence import (
    build_finding_groups,
    build_scan_diff,
)


class TestBuildFindingGroups:
    def test_single_finding_produces_group(self):
        findings = [{
            "id": "f1",
            "title": "SQL Injection",
            "severity": "critical",
            "category": "injection",
            "target": "https://example.com",
            "asset_id": "asset-1",
        }]
        groups = build_finding_groups(findings)
        assert len(groups) == 1
        assert groups[0]["id"] == "f1"
        assert groups[0]["title"] == "SQL Injection"
        assert groups[0]["findings"] == [findings[0]]

    def test_findings_with_same_group_id_merged(self):
        findings = [
            {"finding_group_id": "grp-1", "id": "f1", "title": "XSS 1", "severity": "high"},
            {"finding_group_id": "grp-1", "id": "f2", "title": "XSS 2", "severity": "high"},
        ]
        groups = build_finding_groups(findings)
        assert len(groups) == 1
        assert groups[0]["id"] == "grp-1"
        assert len(groups[0]["findings"]) == 2

    def test_findings_without_group_id_grouped_by_id(self):
        findings = [
            {"id": "f1", "title": "A", "severity": "low"},
            {"id": "f2", "title": "B", "severity": "low"},
        ]
        groups = build_finding_groups(findings)
        assert len(groups) == 2

    def test_empty_list_returns_empty(self):
        groups = build_finding_groups([])
        assert groups == []

    def test_missing_optional_fields_handled(self):
        findings = [{"id": "f1", "title": "Minimal"}]
        groups = build_finding_groups(findings)
        assert groups[0]["occurrence_count"] == 1
        assert groups[0]["evidence_count"] == 0
        assert groups[0]["finding_kind"] == "observation"
        assert groups[0]["validated"] is False

    def test_occurrence_count_normalized(self):
        findings = [{"id": "f1", "title": "A", "occurrence_count": "5"}]
        groups = build_finding_groups(findings)
        assert groups[0]["occurrence_count"] == 5

    def test_evidence_count_from_list(self):
        findings = [{"id": "f1", "title": "A", "evidence": [{"url": "x"}, {"url": "y"}]}]
        groups = build_finding_groups(findings)
        assert groups[0]["evidence_count"] == 2

    def test_corroborating_sources_preserved(self):
        findings = [{"id": "f1", "title": "A", "corroborating_sources": ["nmap", "nessus"]}]
        groups = build_finding_groups(findings)
        assert groups[0]["corroborating_sources"] == ["nmap", "nessus"]


class TestBuildScanDiff:
    def test_new_findings_only_in_current(self):
        current = [{"id": "f1", "title": "New Finding"}]
        previous = []
        diff = build_scan_diff(current, previous)
        assert len(diff["new"]) == 1
        assert len(diff["resolved"]) == 0
        assert len(diff["changed"]) == 0

    def test_resolved_findings_only_in_previous(self):
        current = []
        previous = [{"id": "f1", "title": "Old Finding"}]
        diff = build_scan_diff(current, previous)
        assert len(diff["resolved"]) == 1
        assert len(diff["new"]) == 0
        assert len(diff["changed"]) == 0

    def test_changed_severity(self):
        current = [{"id": "f1", "title": "XSS", "severity": "medium"}]
        previous = [{"id": "f1", "title": "XSS", "severity": "low"}]
        diff = build_scan_diff(current, previous)
        assert len(diff["changed"]) == 1
        assert diff["changed"][0]["before"]["severity"] == "low"
        assert diff["changed"][0]["after"]["severity"] == "medium"

    def test_changed_validated_flag(self):
        current = [{"id": "f1", "title": "Issue", "validated": True}]
        previous = [{"id": "f1", "title": "Issue", "validated": False}]
        diff = build_scan_diff(current, previous)
        assert len(diff["changed"]) == 1

    def test_changed_confidence(self):
        current = [{"id": "f1", "title": "Issue", "confidence": 0.8}]
        previous = [{"id": "f1", "title": "Issue", "confidence": 0.3}]
        diff = build_scan_diff(current, previous)
        assert len(diff["changed"]) == 1

    def test_unchanged_findings_not_in_diff(self):
        current = [{"id": "f1", "title": "Same", "severity": "low", "validated": False, "confidence": 0.5}]
        previous = [{"id": "f1", "title": "Same", "severity": "low", "validated": False, "confidence": 0.5}]
        diff = build_scan_diff(current, previous)
        assert len(diff["new"]) == 0
        assert len(diff["resolved"]) == 0
        assert len(diff["changed"]) == 0

    def test_summary_counts_correct(self):
        current = [{"id": "f1", "title": "A"}]
        previous = [{"id": "f2", "title": "B"}]
        diff = build_scan_diff(current, previous)
        assert diff["summary"]["new_count"] == 1
        assert diff["summary"]["resolved_count"] == 1
        assert diff["summary"]["changed_count"] == 0

    def test_both_empty_returns_empty(self):
        diff = build_scan_diff([], [])
        assert diff["new"] == []
        assert diff["resolved"] == []
        assert diff["changed"] == []
        assert diff["summary"]["new_count"] == 0
