import pytest
from backend.secuscan.services.diff_service import fingerprint, compute_diff
from backend.secuscan.routes import _parse_findings


def _make_finding(title: str, category: str, target: str, severity: str) -> dict:
    """Minimal finding dict for diff tests — only fields used by the service."""
    return {
        "title": title,
        "category": category,
        "target": target,
        "severity": severity,
    }


# ---------------------------------------------------------------------------
# fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_stability():
    finding = _make_finding("SQL Injection", "web", "api.example.com", "critical")

    fp1 = fingerprint(finding)
    fp2 = fingerprint(finding)
    # Severity is NOT part of the fingerprint — same finding with different
    # severity must produce the same key so severity_changed is detected.
    fp_different_severity = fingerprint({**finding, "severity": "high"})

    assert fp1 == fp2
    assert fp1 == fp_different_severity
    assert fp1 == "SQL Injection\x00web\x00api.example.com"


# ---------------------------------------------------------------------------
# compute_diff — single-category cases
# ---------------------------------------------------------------------------

def test_new_finding_detected():
    existing = _make_finding("Open Port 80", "network", "example.com", "low")
    added = _make_finding("SQL Injection", "web", "example.com", "critical")

    result = compute_diff([existing], [existing, added])

    assert len(result["new_findings"]) == 1
    assert result["new_findings"][0]["title"] == "SQL Injection"
    assert result["fixed_findings"] == []
    assert len(result["unchanged_findings"]) == 1
    assert result["severity_changed"] == []


def test_fixed_finding_detected():
    resolved = _make_finding("Directory Listing", "web", "example.com", "medium")
    remaining = _make_finding("Open Port 443", "network", "example.com", "info")

    result = compute_diff([resolved, remaining], [remaining])

    assert len(result["fixed_findings"]) == 1
    assert result["fixed_findings"][0]["title"] == "Directory Listing"
    assert result["new_findings"] == []
    assert len(result["unchanged_findings"]) == 1
    assert result["severity_changed"] == []


def test_unchanged_finding_detected():
    finding = _make_finding("XSS Vulnerability", "web", "example.com", "high")

    result = compute_diff([finding], [finding])

    assert len(result["unchanged_findings"]) == 1
    assert result["unchanged_findings"][0]["title"] == "XSS Vulnerability"
    assert result["new_findings"] == []
    assert result["fixed_findings"] == []
    assert result["severity_changed"] == []


def test_severity_change_detected():
    finding_a = _make_finding("Weak Cipher Suite", "tls", "example.com", "medium")
    finding_b = {**finding_a, "severity": "high"}

    result = compute_diff([finding_a], [finding_b])

    assert len(result["severity_changed"]) == 1
    change = result["severity_changed"][0]
    assert change["before"]["severity"] == "medium"
    assert change["after"]["severity"] == "high"
    # A severity-changed finding must not also appear in unchanged
    assert result["unchanged_findings"] == []
    assert result["new_findings"] == []
    assert result["fixed_findings"] == []


# ---------------------------------------------------------------------------
# compute_diff — edge cases
# ---------------------------------------------------------------------------

def test_empty_scans_produce_empty_diff():
    result = compute_diff([], [])

    assert result["new_findings"] == []
    assert result["fixed_findings"] == []
    assert result["unchanged_findings"] == []
    assert result["severity_changed"] == []


def test_empty_scan_a_all_findings_are_new():
    findings = [
        _make_finding("SSRF", "web", "example.com", "high"),
        _make_finding("IDOR", "web", "example.com", "medium"),
    ]

    result = compute_diff([], findings)

    assert len(result["new_findings"]) == 2
    assert result["fixed_findings"] == []
    assert result["unchanged_findings"] == []
    assert result["severity_changed"] == []


def test_empty_scan_b_all_findings_are_fixed():
    findings = [
        _make_finding("RCE", "web", "example.com", "critical"),
        _make_finding("LFI", "web", "example.com", "high"),
    ]

    result = compute_diff(findings, [])

    assert result["new_findings"] == []
    assert len(result["fixed_findings"]) == 2
    assert result["unchanged_findings"] == []
    assert result["severity_changed"] == []


# ---------------------------------------------------------------------------
# compute_diff — mixed scenario
# ---------------------------------------------------------------------------

def test_multiple_findings_mixed():
    persisted = _make_finding("XSS", "web", "app.example.com", "medium")
    resolved = _make_finding("LFI", "web", "app.example.com", "high")
    introduced = _make_finding("SSRF", "web", "app.example.com", "critical")

    result = compute_diff([persisted, resolved], [persisted, introduced])

    assert len(result["unchanged_findings"]) == 1
    assert result["unchanged_findings"][0]["title"] == "XSS"

    assert len(result["fixed_findings"]) == 1
    assert result["fixed_findings"][0]["title"] == "LFI"

    assert len(result["new_findings"]) == 1
    assert result["new_findings"][0]["title"] == "SSRF"

    assert result["severity_changed"] == []


# ---------------------------------------------------------------------------
# fingerprint — malformed input
# ---------------------------------------------------------------------------

def test_fingerprint_missing_fields():
    """fingerprint() must not crash when fields are absent."""
    assert fingerprint({}) == "\x00\x00"


def test_fingerprint_none_values():
    """fingerprint() must not crash when fields are None."""
    assert fingerprint({"title": None, "category": None, "target": None}) == "\x00\x00"


def test_compute_diff_malformed_findings():
    """compute_diff() must not crash when findings have missing fields."""
    malformed = [{"title": None, "category": None, "target": None}]
    result = compute_diff(malformed, malformed)
    assert result["new_findings"] == []
    assert result["fixed_findings"] == []


def test_same_scan_both_sides():
    """Passing identical lists produces no new or fixed findings."""
    findings = [_make_finding("SQLi", "web", "example.com", "critical")]
    result = compute_diff(findings, findings)
    assert result["new_findings"] == []
    assert result["fixed_findings"] == []
    assert len(result["unchanged_findings"]) == 1


# ---------------------------------------------------------------------------
# fingerprint — pipe character no longer causes collisions
# ---------------------------------------------------------------------------

def test_fingerprint_pipe_in_title_no_collision():
    """Two findings that would collide under '|' separator are distinct under \\x00."""
    # Under old '|' separator both would produce "a|b|c|d"
    f1 = {"title": "a|b", "category": "c", "target": "d"}
    f2 = {"title": "a", "category": "b|c", "target": "d"}
    assert fingerprint(f1) != fingerprint(f2)


def test_fingerprint_pipe_in_target_no_collision():
    """Pipe in target field must not merge distinct findings."""
    f1 = {"title": "XSS", "category": "web", "target": "a|b"}
    f2 = {"title": "XSS", "category": "web|", "target": "b"}
    assert fingerprint(f1) != fingerprint(f2)


# ---------------------------------------------------------------------------
# _parse_findings — null and non-list findings values
# ---------------------------------------------------------------------------

def test_parse_findings_null_value():
    """findings key present but null must return empty list."""
    assert _parse_findings('{"findings": null}') == []


def test_parse_findings_dict_value():
    """findings key present but a dict (not a list) must return empty list."""
    assert _parse_findings('{"findings": {"key": "val"}}') == []


def test_parse_findings_missing_key():
    """structured_json with no findings key must return empty list."""
    assert _parse_findings('{"results": []}') == []


def test_parse_findings_valid_list():
    """findings key with a proper list must be returned as-is."""
    payload = '{"findings": [{"title": "XSS", "severity": "high"}]}'
    result = _parse_findings(payload)
    assert len(result) == 1
    assert result[0]["title"] == "XSS"


def test_parse_findings_none_input():
    """None input must return empty list."""
    assert _parse_findings(None) == []


def test_parse_findings_invalid_json():
    """Corrupt JSON must return empty list without raising."""
    assert _parse_findings("{not valid json}") == []
