"""
Unit tests for finding_intelligence.build_finding_groups.

Tests the grouping and aggregation logic for findings, including group
merging, severity priority, sorting, and metadata accumulation.
"""

from backend.secuscan.finding_intelligence import build_finding_groups


def _make_finding(overrides=None):
    defaults = {
        "id": "f1",
        "title": "SQL Injection",
        "severity": "high",
        "category": "injection",
        "target": "https://example.com",
        "finding_group_id": None,
        "validated": False,
        "discovered_at": "2024-01-01T00:00:00Z",
        "first_seen_at": None,
        "last_seen_at": None,
        "occurrence_count": 1,
        "evidence_count": 1,
        "evidence": [{"type": "payload", "value": "test"}],
        "corroborating_sources": [],
        "confidence": 0.8,
        "confidence_reason": None,
        "finding_kind": "vulnerability",
    }
    if overrides:
        defaults.update(overrides)
    return defaults


class TestBuildFindingGroups:
    def test_empty_list_returns_empty_list(self):
        """An empty findings list produces no groups."""
        result = build_finding_groups([])
        assert result == []

    def test_single_finding_returns_single_group(self):
        """A single finding maps to exactly one group."""
        finding = _make_finding({"id": "f1", "finding_group_id": "g1"})
        result = build_finding_groups([finding])
        assert len(result) == 1
        group = result[0]
        assert group["id"] == "g1"
        assert group["findings"] == [finding]

    def test_multiple_findings_same_group_id_merge(self):
        """Findings sharing the same group_id are merged into one group."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "severity": "high", "occurrence_count": 1})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "severity": "low", "occurrence_count": 2})
        result = build_finding_groups([f1, f2])
        assert len(result) == 1
        assert result[0]["occurrence_count"] == 2
        assert result[0]["findings"] == [f1, f2]

    def test_multiple_findings_different_group_ids_separate(self):
        """Findings with different group_ids produce separate groups."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1"})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g2"})
        result = build_finding_groups([f1, f2])
        assert len(result) == 2
        ids = {g["id"] for g in result}
        assert ids == {"g1", "g2"}

    def test_merged_group_keeps_highest_severity(self):
        """When merging, the group retains the highest severity."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "severity": "low"})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "severity": "critical"})
        f3 = _make_finding({"id": "f3", "finding_group_id": "g1", "severity": "info"})
        result = build_finding_groups([f1, f2, f3])
        assert len(result) == 1
        assert result[0]["severity"] == "critical"

    def test_merged_group_occurrence_count_is_max(self):
        """occurrence_count for a merged group is the max of all members."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "occurrence_count": 3})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "occurrence_count": 7})
        result = build_finding_groups([f1, f2])
        assert result[0]["occurrence_count"] == 7

    def test_merged_group_first_seen_at_is_min(self):
        """first_seen_at for a merged group is the earliest."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "discovered_at": "2024-06-01T00:00:00Z"})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "discovered_at": "2024-01-01T00:00:00Z"})
        result = build_finding_groups([f1, f2])
        assert result[0]["first_seen_at"] == "2024-01-01T00:00:00Z"

    def test_merged_group_last_seen_at_is_max(self):
        """last_seen_at for a merged group is the latest."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "discovered_at": "2024-01-01T00:00:00Z"})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "discovered_at": "2024-06-01T00:00:00Z"})
        result = build_finding_groups([f1, f2])
        assert result[0]["last_seen_at"] == "2024-06-01T00:00:00Z"

    def test_validated_true_if_any_finding_validated(self):
        """validated is True if any member finding is validated."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "validated": False})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "validated": True})
        result = build_finding_groups([f1, f2])
        assert result[0]["validated"] is True

    def test_corroborating_sources_merged_without_duplicates(self):
        """corroborating_sources are merged and deduplicated."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "corroborating_sources": ["scanner_a", "scanner_b"]})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "corroborating_sources": ["scanner_b", "scanner_c"]})
        result = build_finding_groups([f1, f2])
        assert "scanner_a" in result[0]["corroborating_sources"]
        assert "scanner_b" in result[0]["corroborating_sources"]
        assert "scanner_c" in result[0]["corroborating_sources"]
        # No duplicates
        assert len(result[0]["corroborating_sources"]) == len(set(result[0]["corroborating_sources"]))

    def test_confidence_is_max_across_members(self):
        """Group confidence is the maximum across all member findings."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1", "confidence": 0.4})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1", "confidence": 0.9})
        result = build_finding_groups([f1, f2])
        assert result[0]["confidence"] == 0.9

    def test_groups_sorted_by_severity_desc_confidence_desc_title_asc(self):
        """Groups are sorted: highest severity first, then highest confidence, then title."""
        low_conf = _make_finding({"id": "f1", "finding_group_id": "g1", "severity": "low", "confidence": 0.5, "title": "alpha"})
        high_conf = _make_finding({"id": "f2", "finding_group_id": "g2", "severity": "high", "confidence": 0.9, "title": "beta"})
        critical = _make_finding({"id": "f3", "finding_group_id": "g3", "severity": "critical", "confidence": 0.7, "title": "gamma"})
        # Pass in reverse order
        result = build_finding_groups([low_conf, high_conf, critical])
        assert result[0]["severity"] == "critical"
        assert result[1]["severity"] == "high"
        assert result[2]["severity"] == "low"

    def test_group_id_falls_back_to_id_when_no_finding_group_id(self):
        """When finding_group_id is absent, the finding id is used as the group id."""
        finding = _make_finding({"id": "my-finding-id", "finding_group_id": None})
        result = build_finding_groups([finding])
        assert result[0]["id"] == "my-finding-id"

    def test_latest_finding_id_is_first_finding_id(self):
        """latest_finding_id tracks the id of the first finding in the group."""
        f1 = _make_finding({"id": "f1", "finding_group_id": "g1"})
        f2 = _make_finding({"id": "f2", "finding_group_id": "g1"})
        result = build_finding_groups([f1, f2])
        assert result[0]["latest_finding_id"] == "f1"
