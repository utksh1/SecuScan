"""
Unit tests for backend/secuscan/finding_intelligence.py _fingerprint_score
and build_scan_diff functions.

Covers:
  - _fingerprint_score: deduplication fingerprint computation
  - build_scan_diff: computes added/resolved/changed findings between two scans
"""

from __future__ import annotations

import pytest

from backend.secuscan import finding_intelligence as fi


# ---------------------------------------------------------------------------
# _fingerprint_score
# ---------------------------------------------------------------------------


class TestFingerprintScore:
    """_fingerprint_score return value shape and determinism."""

    def test_returns_tuple_of_float_and_str(self):
        """Must return a (float, str) tuple."""
        result = fi._fingerprint_score({})
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], str)

    def test_is_deterministic_for_same_finding(self):
        """Same finding dict must always produce the same score."""
        finding = {"severity": "high", "validated": True}
        a = fi._fingerprint_score(finding)
        b = fi._fingerprint_score(finding)
        assert a == b

    def test_changes_when_validated_changes(self):
        """Validated findings should score differently from non-validated."""
        a = fi._fingerprint_score({"validated": True})
        b = fi._fingerprint_score({"validated": False})
        assert a != b

    def test_changes_when_metadata_match_strength_changes(self):
        """match_strength in metadata changes the fingerprint."""
        a = fi._fingerprint_score(
            {"metadata": {"match_strength": "exact"}}
        )
        b = fi._fingerprint_score(
            {"metadata": {"match_strength": "fuzzy"}}
        )
        assert a != b

    def test_changes_when_cpe_match_strength_changes(self):
        """cpe_match_strength in metadata changes the fingerprint."""
        a = fi._fingerprint_score(
            {"metadata": {"cpe_match_strength": "strong_fuzzy"}}
        )
        b = fi._fingerprint_score(
            {"metadata": {"cpe_match_strength": "family"}}
        )
        assert a != b

    def test_empty_finding_handled_gracefully(self):
        """Empty finding dict must not raise."""
        score, reason = fi._fingerprint_score({})
        assert isinstance(score, float)
        assert isinstance(reason, str)

    def test_none_metadata_treated_as_empty(self):
        """metadata = None is treated as empty dict."""
        score, reason = fi._fingerprint_score({"metadata": None})
        assert isinstance(score, float)

    def test_metadata_not_a_dict_uses_empty(self):
        """metadata that is not a dict is treated as empty dict."""
        score, reason = fi._fingerprint_score({"metadata": "not a dict"})
        assert isinstance(score, float)

    def test_validated_true_preferred_when_no_match_strength(self):
        """validated=True is used as fallback when no match_strength exists."""
        finding = {"validated": True, "metadata": {}}
        score, reason = fi._fingerprint_score(finding)
        assert reason == "validated"
        assert score == 1.0

    def test_known_match_strengths(self):
        """Known match_strength values produce documented scores."""
        for strength, expected_score in [
            ("validated", 1.0),
            ("exact", 0.95),
            ("strong_fuzzy", 0.8),
            ("fuzzy", 0.7),
            ("family", 0.45),
            ("none", 0.25),
        ]:
            score, reason = fi._fingerprint_score(
                {"metadata": {"match_strength": strength}}
            )
            assert score == expected_score, f"match_strength={strength} failed"

    def test_unknown_match_strength_defaults_to_035(self):
        """Unknown match_strength values default to 0.35."""
        score, reason = fi._fingerprint_score(
            {"metadata": {"match_strength": "unknown_value"}}
        )
        assert score == 0.35

    def test_case_insensitive_match_strength(self):
        """match_strength is case-insensitive."""
        a = fi._fingerprint_score(
            {"metadata": {"match_strength": "EXACT"}}
        )
        b = fi._fingerprint_score(
            {"metadata": {"match_strength": "exact"}}
        )
        assert a == b


# ---------------------------------------------------------------------------
# build_scan_diff
# ---------------------------------------------------------------------------


class TestBuildScanDiff:
    """build_scan_diff added/resolved/changed finding groups."""

    def _finding(self, id, severity="high", validated=False, confidence=0.8):
        """Helper to build a minimal finding dict."""
        return {
            "id": id,
            "finding_group_id": None,
            "severity": severity,
            "validated": validated,
            "confidence": confidence,
        }

    def test_empty_current_and_previous_returns_empty_diff(self):
        """No findings in either scan produces empty new/resolved/changed."""
        result = fi.build_scan_diff([], [])
        assert result["new"] == []
        assert result["resolved"] == []
        assert result["changed"] == []
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0

    def test_all_new_findings_appear_in_new(self):
        """Findings only in current scan are new."""
        current = [self._finding("f1"), self._finding("f2")]
        previous = []
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["new_count"] == 2
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0

    def test_all_resolved_findings_appear_in_resolved(self):
        """Findings only in previous scan are resolved."""
        current = []
        previous = [self._finding("f1"), self._finding("f2")]
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 2
        assert result["summary"]["changed_count"] == 0

    def test_unchanged_findings_not_in_new_or_resolved(self):
        """Findings present in both scans with no change are not in new/resolved."""
        f1 = self._finding("f1")
        current = [f1]
        previous = [dict(f1)]
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0

    def test_severity_change_appears_in_changed(self):
        """Findings with different severity are in the changed list."""
        current = [self._finding("f1", severity="high")]
        previous = [self._finding("f1", severity="low")]
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["changed_count"] == 1
        assert result["changed"][0]["group_id"] == "f1"
        assert result["changed"][0]["before"]["severity"] == "low"
        assert result["changed"][0]["after"]["severity"] == "high"

    def test_validated_change_appears_in_changed(self):
        """Findings with different validated flag are in the changed list."""
        current = [self._finding("f1", validated=True)]
        previous = [self._finding("f1", validated=False)]
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["changed_count"] == 1

    def test_confidence_change_appears_in_changed(self):
        """Findings with different confidence (rounded to 2dp) are in changed."""
        current = [self._finding("f1", confidence=0.85)]
        previous = [self._finding("f1", confidence=0.50)]
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["changed_count"] == 1

    def test_confidence_rounding_threshold(self):
        """Confidence change below 0.01 is NOT treated as changed."""
        current = [self._finding("f1", confidence=0.801)]
        previous = [self._finding("f1", confidence=0.799)]
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["changed_count"] == 0

    def test_uses_finding_group_id_when_present(self):
        """Findings are matched by finding_group_id, not id, when present."""
        f1a = {"finding_group_id": "grp1", "severity": "high"}
        f1b = {"id": "f1", "finding_group_id": "grp1", "severity": "high"}
        current = [f1a]
        previous = [f1b]
        result = fi.build_scan_diff(current, previous)
        # Same finding_group_id -> not new, not resolved, not changed
        assert result["summary"]["new_count"] == 0
        assert result["summary"]["resolved_count"] == 0
        assert result["summary"]["changed_count"] == 0

    def test_new_finding_with_group_id_uses_group_id(self):
        """New finding with finding_group_id uses that as the key."""
        f1 = {"finding_group_id": "grp1", "id": "f1", "severity": "high"}
        current = [f1]
        previous = []
        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["new_count"] == 1

    def test_mixed_new_resolved_changed_together(self):
        """Scan with new, resolved, and changed findings."""
        # f1: new (only in current)
        f1 = self._finding("f1")
        # f2: resolved (only in previous)
        f2 = self._finding("f2")
        # f3: unchanged
        f3 = self._finding("f3", severity="low")
        # f4: changed (severity differs)
        f4_old = self._finding("f4", severity="low")
        f4_new = self._finding("f4", severity="high")

        current = [f1, f3, f4_new]
        previous = [f2, f3, f4_old]

        result = fi.build_scan_diff(current, previous)
        assert result["summary"]["new_count"] == 1
        assert result["summary"]["resolved_count"] == 1
        assert result["summary"]["changed_count"] == 1

    def test_summary_totals_match_counts(self):
        """summary new_count/resolved_count/changed_count match actual list lengths."""
        current = [self._finding("f1")]
        previous = [self._finding("f2")]
        result = fi.build_scan_diff(current, previous)
        s = result["summary"]
        assert s["new_count"] == len(result["new"])
        assert s["resolved_count"] == len(result["resolved"])
        assert s["changed_count"] == len(result["changed"])
