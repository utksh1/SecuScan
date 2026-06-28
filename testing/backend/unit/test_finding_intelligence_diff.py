"""
Unit tests for finding_intelligence.build_scan_diff.

Tests the scan-delta logic that detects new, resolved, and changed finding
groups between two finding lists.
"""

from backend.secuscan.finding_intelligence import build_scan_diff


def _make_finding(overrides=None):
    defaults = {
        "id": "f1",
        "finding_group_id": None,
        "title": "Test Finding",
        "severity": "high",
        "validated": False,
        "confidence": 0.8,
        "category": "test",
        "target": "https://example.com",
    }
    if overrides:
        defaults.update(overrides)
    return defaults


class TestBuildScanDiff:
    def test_empty_both_returns_empty_counts(self):
        """When both lists are empty, all counts are zero."""
        result = build_scan_diff([], [])
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0
        assert result["new"] == []
        assert result["resolved"] == []
        assert result["changed"] == []

    def test_new_findings_only_in_current(self):
        """Findings only in current appear in new, not resolved."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1"})
        result = build_scan_diff([f1], [])
        assert result["summary"]["new_count"] == 1
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0
        assert len(result["new"]) == 1
        assert result["new"][0]["id"] == "g1"

    def test_resolved_findings_only_in_previous(self):
        """Findings only in previous appear in resolved, not new."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1"})
        result = build_scan_diff([], [f1])
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 1
        assert result["summary"]["changed_count"] == 0
        assert len(result["resolved"]) == 1
        assert result["resolved"][0]["id"] == "g1"

    def test_unchanged_findings_not_in_changed(self):
        """Findings present in both with no change are not in changed."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "severity": "high", "validated": False, "confidence": 0.8})
        result = build_scan_diff([f1], [f1])
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0
        assert result["changed"] == []

    def test_severity_change_appears_in_changed(self):
        """A severity change between current and previous is recorded in changed."""
        before = _make_finding({"id": "f1", "finding_group_id": "g1", "severity": "high", "validated": False, "confidence": 0.8})
        after = _make_finding({"id": "f1", "finding_group_id": "g1", "severity": "critical", "validated": False, "confidence": 0.8})
        result = build_scan_diff([after], [before])
        assert result["summary"]["changed_count"] == 1
        changed = result["changed"][0]
        assert changed["before"]["severity"] == "high"
        assert changed["after"]["severity"] == "critical"
        assert changed["group_id"] == "g1"

    def test_validated_flag_change_appears_in_changed(self):
        """A validated flag change is recorded in changed."""
        before = _make_finding({"id": "f1", "finding_group_id": "g1", "validated": False})
        after = _make_finding({"id": "f1", "finding_group_id": "g1", "validated": True})
        result = build_scan_diff([after], [before])
        assert result["summary"]["changed_count"] == 1
        assert result["changed"][0]["before"]["validated"] is False
        assert result["changed"][0]["after"]["validated"] is True

    def test_confidence_change_rounded_to_2dp(self):
        """A confidence change (rounded to 2dp) is recorded in changed."""
        before = _make_finding({"id": "f1", "finding_group_id": "g1", "confidence": 0.80})
        after = _make_finding({"id": "f1", "finding_group_id": "g1", "confidence": 0.85})
        result = build_scan_diff([after], [before])
        assert result["summary"]["changed_count"] == 1

    def test_confidence_change_ignores_beyond_2dp(self):
        """Changes in confidence beyond 2dp precision do not trigger changed."""
        # 0.801 and 0.802 both round to 0.80
        before = _make_finding({"id": "f1", "finding_group_id": "g1", "confidence": 0.801})
        after = _make_finding({"id": "f1", "finding_group_id": "g1", "confidence": 0.802})
        result = build_scan_diff([after], [before])
        assert result["summary"]["changed_count"] == 0

    def test_grouping_key_uses_finding_group_id_when_present(self):
        """The group key is finding_group_id when present, falling back to id."""
        f_prev = _make_finding({"id": "prev-id", "finding_group_id": "shared-group"})
        f_curr = _make_finding({"id": "curr-id", "finding_group_id": "shared-group", "severity": "low"})
        result = build_scan_diff([f_curr], [f_prev])
        # Same group key, only changed because severity differs
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 0

    def test_grouping_key_falls_back_to_id_when_no_finding_group_id(self):
        """When finding_group_id is absent, id is used as the group key."""
        f_prev = _make_finding({"id": "same-id", "finding_group_id": None})
        f_curr = _make_finding({"id": "same-id", "finding_group_id": None, "severity": "critical"})
        result = build_scan_diff([f_curr], [f_prev])
        assert result["summary"]["changed_count"] == 1

    def test_mixed_new_resolved_and_changed_together(self):
        """All three categories can appear simultaneously."""
        # new: only in current
        new_f = _make_finding({"id": "f-new", "finding_group_id": "g-new"})
        # resolved: only in previous
        res_f = _make_finding({"id": "f-res", "finding_group_id": "g-res"})
        # changed
        before = _make_finding({"id": "f-chg", "finding_group_id": "g-chg", "severity": "low"})
        after = _make_finding({"id": "f-chg", "finding_group_id": "g-chg", "severity": "high"})
        result = build_scan_diff([new_f, after], [res_f, before])
        assert result["summary"]["new_count"] == 1
        assert result["summary"]["resolved_count"] == 1
        assert result["summary"]["changed_count"] == 1
