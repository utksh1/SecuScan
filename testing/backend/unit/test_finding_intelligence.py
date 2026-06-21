from backend.secuscan.finding_intelligence import build_finding_groups, build_scan_diff, build_asset_summary


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



def test_build_asset_summary_empty_inputs():
    # Empty inputs returns empty
    assert build_asset_summary([], []) == []
    # A finding without asset_id or target still creates an asset entry
    # (stable ID is derived from the empty target string)
    r = build_asset_summary([{"title": "XSS", "severity": "high"}], [])
    assert len(r) == 1
    assert r[0]["finding_count"] == 1
    assert r[0]["highest_severity"] == "high"


def test_build_asset_summary_one_asset_from_services():
    services = [
        {
            "asset_id": "asset-1",
            "host": "10.0.0.1",
            "target": "https://example.com",
            "port": 443,
            "protocol": "https",
        },
    ]
    result = build_asset_summary([], services)
    assert len(result) == 1
    assert result[0]["asset_id"] == "asset-1"
    assert result[0]["label"] == "10.0.0.1"
    assert result[0]["finding_count"] == 0


def test_build_asset_summary_finding_count_and_severity():
    findings = [
        {"asset_id": "asset-x", "severity": "low", "validated": False},
        {"asset_id": "asset-x", "severity": "high", "validated": True},
        {"asset_id": "asset-x", "severity": "critical", "validated": False},
        {"asset_id": "asset-x", "severity": "info", "validated": False},
    ]
    result = build_asset_summary(findings, [])
    assert len(result) == 1
    assert result[0]["finding_count"] == 4
    assert result[0]["validated_count"] == 1
    assert result[0]["highest_severity"] == "critical"


def test_build_asset_summary_highest_severity_escalation():
    findings = [
        {"asset_id": "asset-y", "severity": "info"},
        {"asset_id": "asset-y", "severity": "medium"},
    ]
    result = build_asset_summary(findings, [])
    assert result[0]["highest_severity"] == "medium"


def test_build_asset_summary_sorted_by_severity_desc():
    findings = [
        {"asset_id": "a1", "severity": "low", "target": "https://a.com"},
        {"asset_id": "a2", "severity": "critical", "target": "https://b.com"},
        {"asset_id": "a3", "severity": "high", "target": "https://c.com"},
    ]
    result = build_asset_summary(findings, [])
    assert result[0]["asset_id"] == "a2"
    assert result[0]["highest_severity"] == "critical"
    assert result[1]["asset_id"] == "a3"
    assert result[1]["highest_severity"] == "high"
    assert result[2]["asset_id"] == "a1"
    assert result[2]["highest_severity"] == "low"


def test_build_asset_summary_sorted_by_count_desc_within_same_severity():
    findings = [
        {"asset_id": "b1", "severity": "high", "target": "https://b1.com"},
        {"asset_id": "b1", "severity": "high", "target": "https://b1.com"},
        {"asset_id": "b2", "severity": "high", "target": "https://b2.com"},
    ]
    result = build_asset_summary(findings, [])
    assert result[0]["asset_id"] == "b1"
    assert result[0]["finding_count"] == 2
    assert result[1]["asset_id"] == "b2"
    assert result[1]["finding_count"] == 1


def test_build_asset_summary_validated_count():
    findings = [
        {"asset_id": "v1", "severity": "high", "validated": True},
        {"asset_id": "v1", "severity": "high", "validated": True},
        {"asset_id": "v1", "severity": "high", "validated": False},
    ]
    result = build_asset_summary(findings, [])
    assert result[0]["validated_count"] == 2
