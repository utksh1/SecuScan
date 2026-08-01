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


# ── Unified group keys (issue #1834) ──────────────────────────────────────────


class TestUnifiedGroupKeys:
    """Every producer of a group id must agree.

    Before this, ``build_finding_groups`` fell back to hashing
    ``(title, target)`` while ``normalize_and_correlate_findings`` grouped by
    ``(plugin, asset, signature)``, so an uncorrelated finding grouped
    differently from a correlated one.
    """

    @staticmethod
    def _uncorrelated(**overrides):
        """A finding with neither ``finding_group_id`` nor ``id`` — the only
        case that reaches the fallback."""
        base = {
            "title": "Open port",
            "target": "example.com",
            "plugin_id": "nmap",
            "category": "network",
            "severity": "info",
        }
        base.update(overrides)
        return base

    def test_same_title_and_target_but_different_ports_stay_separate(self):
        """The reported bug: distinct issues merged on title+target alone."""
        groups = build_finding_groups([
            self._uncorrelated(metadata={"port": 80, "protocol": "tcp"}),
            self._uncorrelated(metadata={"port": 443, "protocol": "tcp"}),
        ])
        assert len(groups) == 2

    def test_identical_findings_still_collapse(self):
        groups = build_finding_groups([
            self._uncorrelated(metadata={"port": 80, "protocol": "tcp"}),
            self._uncorrelated(metadata={"port": 80, "protocol": "tcp"}),
        ])
        assert len(groups) == 1
        assert groups[0]["occurrence_count"] >= 1

    def test_same_issue_from_different_plugins_stays_separate(self):
        """Matches the live correlate path, which keys on plugin_id."""
        groups = build_finding_groups([
            self._uncorrelated(plugin_id="nmap", metadata={"port": 80}),
            self._uncorrelated(plugin_id="masscan", metadata={"port": 80}),
        ])
        assert len(groups) == 2

    def test_same_title_on_different_targets_stay_separate(self):
        groups = build_finding_groups([
            self._uncorrelated(target="a.example.com"),
            self._uncorrelated(target="b.example.com"),
        ])
        assert len(groups) == 2

    def test_distinct_cves_stay_separate(self):
        groups = build_finding_groups([
            self._uncorrelated(cve="CVE-2023-1111"),
            self._uncorrelated(cve="CVE-2023-2222"),
        ])
        assert len(groups) == 2

    def test_explicit_group_id_still_wins_over_the_fallback(self):
        groups = build_finding_groups([
            self._uncorrelated(finding_group_id="group:fixed", metadata={"port": 80}),
            self._uncorrelated(finding_group_id="group:fixed", metadata={"port": 443}),
        ])
        assert len(groups) == 1
        assert groups[0]["id"] == "group:fixed"

    def test_id_still_wins_when_no_group_id(self):
        groups = build_finding_groups([
            self._uncorrelated(id="f-1"),
            self._uncorrelated(id="f-2"),
        ])
        assert {g["id"] for g in groups} == {"f-1", "f-2"}

    def test_fallback_matches_the_correlate_path_key(self):
        """An uncorrelated finding lands on the same id the writer would give it."""
        from backend.secuscan.finding_intelligence import (
            compute_finding_group_id,
            resolve_asset_id,
        )

        finding = self._uncorrelated(metadata={"port": 8080, "protocol": "tcp"})
        expected = compute_finding_group_id(
            finding,
            plugin_id="nmap",
            asset_id=resolve_asset_id(finding, "example.com"),
        )
        assert build_finding_groups([finding])[0]["id"] == expected

    def test_missing_plugin_id_does_not_raise(self):
        groups = build_finding_groups([{"title": "x", "target": "t"}])
        assert len(groups) == 1


class TestGenerateFindingKeyAgreesWithCorrelatePath:
    """``generate_finding_key`` used to fold ``owner_id`` into the digest, so it
    could never reproduce a stored ``finding_group_id``. Owner scoping lives in
    the unique index on ``(owner_id, finding_group_id)`` instead."""

    def test_key_is_independent_of_owner(self):
        from backend.secuscan.finding_intelligence import generate_finding_key

        finding = {"title": "Open port", "category": "network",
                   "metadata": {"port": 80, "protocol": "tcp"}}
        a = generate_finding_key(finding, "nmap", "example.com", "owner-a")
        b = generate_finding_key(finding, "nmap", "example.com", "owner-b")
        assert a == b

    def test_key_matches_compute_finding_group_id(self):
        from backend.secuscan.finding_intelligence import (
            compute_finding_group_id,
            generate_finding_key,
            resolve_asset_id,
        )

        finding = {"title": "Open port", "category": "network",
                   "metadata": {"port": 80, "protocol": "tcp"}}
        assert generate_finding_key(finding, "nmap", "example.com", "owner-a") == (
            compute_finding_group_id(
                finding,
                plugin_id="nmap",
                asset_id=resolve_asset_id(finding, "example.com"),
            )
        )


class TestPersistedGroupIdIsStable:
    """``finding_group_id`` is written to the database and carries a unique
    index on ``(owner_id, finding_group_id)`` (migration 008). Changing the
    hash material silently orphans every stored row, so these digests are
    pinned deliberately — update them only alongside a migration."""

    def test_known_digests_unchanged(self):
        from backend.secuscan.finding_intelligence import (
            compute_finding_group_id,
            resolve_asset_id,
        )

        cases = [
            (
                {"title": "Open port", "category": "net",
                 "metadata": {"port": 80, "protocol": "tcp"}},
                "nmap", "example.com", "group:cafd1788390e6a54",
            ),
            (
                {"title": "XSS", "category": "web", "cve": "CVE-2023-1234"},
                "nuclei", "https://a.test", "group:2e364c6cba80965a",
            ),
            (
                {"title": "", "category": "", "metadata": {}},
                "", "", "group:602c571d42c25266",
            ),
        ]
        for finding, plugin_id, target, expected in cases:
            actual = compute_finding_group_id(
                finding,
                plugin_id=plugin_id,
                asset_id=resolve_asset_id(finding, target),
            )
            assert actual == expected, f"group id drifted for {plugin_id or '<empty>'}"
