from backend.secuscan.finding_intelligence import build_finding_groups, build_scan_diff


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
        {
            "id": "new-1",
            "finding_group_id": "group:new",
            "title": "New finding",
            "severity": "high",
            "confidence": 0.9,
            "validated": False,
        },
        {
            "id": "chg-2",
            "finding_group_id": "group:changed",
            "title": "Changed finding",
            "severity": "medium",
            "confidence": 0.8,
            "validated": True,
        },
    ]
    previous = [
        {
            "id": "old-1",
            "finding_group_id": "group:resolved",
            "title": "Resolved finding",
            "severity": "low",
            "confidence": 0.4,
            "validated": False,
        },
        {
            "id": "chg-1",
            "finding_group_id": "group:changed",
            "title": "Changed finding",
            "severity": "low",
            "confidence": 0.3,
            "validated": False,
        },
    ]

    diff = build_scan_diff(current, previous)

    assert diff["summary"] == {"new_count": 1, "resolved_count": 1, "changed_count": 1}
    assert diff["new"][0]["id"] == "group:new"
    assert diff["resolved"][0]["id"] == "group:resolved"
    assert diff["changed"][0]["group_id"] == "group:changed"
