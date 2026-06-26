from backend.secuscan.finding_intelligence import build_finding_groups, build_scan_diff


# ---------------------------------------------------------------------------
# build_finding_groups edge cases
# ---------------------------------------------------------------------------


def test_build_finding_groups_empty_list():
    """Empty input returns empty list with no errors."""
    result = build_finding_groups([])
    assert result == []


def test_build_finding_groups_missing_group_id_uses_stable_id():
    """Findings without finding_group_id fall back to stable_id from title and target.
    When id is not provided, two findings with same title/target share a group."""
    findings = [
        {
            # No finding_group_id, no id -> uses stable_id(title, target)
            "title": "SQL Injection",
            "target": "https://example.com",
            "severity": "high",
            "confidence": 0.9,
        },
        {
            "title": "SQL Injection",
            "target": "https://example.com",
            "severity": "medium",
            "confidence": 0.7,
        },
    ]
    groups = build_finding_groups(findings)
    assert len(groups) == 1
    assert len(groups[0]["findings"]) == 2


def test_build_finding_groups_mixed_severity_higher_wins():
    """When group members have different severity, the higher severity wins."""
    findings = [
        {
            "id": "f1",
            "finding_group_id": "sqli",
            "title": "SQL Injection",
            "severity": "low",
            "confidence": 0.5,
        },
        {
            "id": "f2",
            "finding_group_id": "sqli",
            "title": "SQL Injection",
            "severity": "critical",
            "confidence": 0.8,
        },
    ]
    groups = build_finding_groups(findings)
    assert len(groups) == 1
    assert groups[0]["severity"] == "critical"


def test_build_finding_groups_last_seen_at_max():
    """Group last_seen_at uses max() across all findings."""
    findings = [
        {
            "id": "f1",
            "finding_group_id": "xss",
            "title": "XSS",
            "severity": "high",
            "last_seen_at": "2026-06-01T00:00:00Z",
            "confidence": 0.8,
        },
        {
            "id": "f2",
            "finding_group_id": "xss",
            "title": "XSS",
            "severity": "high",
            "last_seen_at": "2026-06-20T00:00:00Z",
            "confidence": 0.8,
        },
    ]
    groups = build_finding_groups(findings)
    assert groups[0]["last_seen_at"] == "2026-06-20T00:00:00Z"


def test_build_finding_groups_first_seen_at_min():
    """Group first_seen_at uses min() across all findings."""
    findings = [
        {
            "id": "f1",
            "finding_group_id": "open-ports",
            "title": "Open Ports",
            "severity": "medium",
            "discovered_at": "2026-06-15T00:00:00Z",
            "confidence": 0.7,
        },
        {
            "id": "f2",
            "finding_group_id": "open-ports",
            "title": "Open Ports",
            "severity": "medium",
            "discovered_at": "2026-06-01T00:00:00Z",
            "confidence": 0.7,
        },
    ]
    groups = build_finding_groups(findings)
    assert groups[0]["first_seen_at"] == "2026-06-01T00:00:00Z"


def test_build_finding_groups_merges_duplicate_group_ids():
    findings = [
        {
            "id": "finding-1",
            "finding_group_id": "group:web:csp",
            "title": "Missing Content-Security-Policy",
            "severity": "medium",
            "category": "Transport Security",
            "target": "https://example.com",
            "occurrence_count": 2,
            "confidence": 0.82,
            "corroborating_sources": ["crawl"],
        },
        {
            "id": "finding-2",
            "finding_group_id": "group:web:csp",
            "title": "Missing Content-Security-Policy",
            "severity": "medium",
            "category": "Transport Security",
            "target": "https://example.com",
            "occurrence_count": 3,
            "confidence": 0.84,
            "corroborating_sources": ["nuclei"],
        },
    ]

    groups = build_finding_groups(findings)

    assert len(groups) == 1
    assert groups[0]["occurrence_count"] == 3
    assert set(groups[0]["corroborating_sources"]) == {"crawl", "nuclei"}
    assert len(groups[0]["findings"]) == 2


def test_build_scan_diff_tracks_new_resolved_and_changed_groups():
    current = [
        {"id": "new-1", "finding_group_id": "group:new", "title": "New finding", "severity": "high", "confidence": 0.9, "validated": False},
        {"id": "chg-2", "finding_group_id": "group:changed", "title": "Changed finding", "severity": "medium", "confidence": 0.8, "validated": True},
    ]
    previous = [
        {"id": "old-1", "finding_group_id": "group:resolved", "title": "Resolved finding", "severity": "low", "confidence": 0.4, "validated": False},
        {"id": "chg-1", "finding_group_id": "group:changed", "title": "Changed finding", "severity": "low", "confidence": 0.3, "validated": False},
    ]

    diff = build_scan_diff(current, previous)

    assert diff["summary"] == {"new_count": 1, "resolved_count": 1, "changed_count": 1}
    assert diff["new"][0]["id"] == "group:new"
    assert diff["resolved"][0]["id"] == "group:resolved"
    assert diff["changed"][0]["group_id"] == "group:changed"


# ---------------------------------------------------------------------------
# build_scan_diff edge cases
# ---------------------------------------------------------------------------


def test_build_scan_diff_empty_both():
    """Empty current and previous lists produce zero counts."""
    diff = build_scan_diff([], [])
    assert diff["summary"]["new_count"] == 0
    assert diff["summary"]["resolved_count"] == 0
    assert diff["summary"]["changed_count"] == 0
    assert diff["new"] == []
    assert diff["resolved"] == []
    assert diff["changed"] == []


def test_build_scan_diff_resolved_items():
    """Items in previous but not in current are marked resolved."""
    previous = [
        {"id": "old-1", "finding_group_id": "gone-group", "title": "Gone finding", "severity": "high", "confidence": 0.8},
    ]
    current = []
    diff = build_scan_diff(current, previous)
    assert diff["summary"]["resolved_count"] == 1
    assert diff["resolved"][0]["id"] == "gone-group"


def test_build_scan_diff_unchanged_groups():
    """Groups that appear in both scans with same severity and confidence are not marked changed."""
    finding = {"id": "f1", "finding_group_id": "stable-group", "title": "Stable finding", "severity": "medium", "confidence": 0.7}
    diff = build_scan_diff([finding], [finding])
    assert diff["summary"]["changed_count"] == 0
    assert diff["new"] == []
    assert diff["resolved"] == []


def test_build_scan_diff_changed_severity():
    """Groups with different severity between scans are marked as changed."""
    current = [
        {"id": "f1", "finding_group_id": "grp", "title": "Finding", "severity": "critical", "confidence": 0.9},
    ]
    previous = [
        {"id": "f2", "finding_group_id": "grp", "title": "Finding", "severity": "info", "confidence": 0.3},
    ]
    diff = build_scan_diff(current, previous)
    assert diff["summary"]["changed_count"] == 1
    changed = diff["changed"][0]
    assert changed["group_id"] == "grp"

