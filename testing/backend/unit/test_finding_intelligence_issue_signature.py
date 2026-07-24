import sys

sys.path.insert(0, ".")

from backend.secuscan.finding_intelligence import _issue_signature


def test_cve_returns_cve_signature():
    finding = {"cve": "CVE-2024-1234"}
    assert _issue_signature(finding) == "cve:cve-2024-1234"


def test_cve_normalizes_case():
    finding = {"cve": "CVE-2021-99999"}
    result = _issue_signature(finding)
    assert result.startswith("cve:")
    assert "2021" in result


def test_no_cve_uses_metadata_template():
    finding = {
        "category": "vulnerability",
        "title": "SQL Injection",
        "validation_method": "nuclei",
        "metadata": {"template": "sqli-error"},
    }
    result = _issue_signature(finding)
    assert "vulnerability" in result
    assert "sql-injection" in result
    assert "nuclei" in result
    assert "sqli-error" in result


def test_no_cve_uses_metadata_header():
    finding = {
        "category": "web",
        "title": "Open Redirect",
        "metadata": {"header": "location"},
    }
    result = _issue_signature(finding)
    assert "open-redirect" in result
    assert "location" in result


def test_no_cve_uses_metadata_service():
    finding = {
        "category": "network",
        "title": "SSL Issue",
        "metadata": {"service": "https"},
    }
    result = _issue_signature(finding)
    assert "ssl-issue" in result
    assert "https" in result


def test_no_metadata_falls_back_to_base_fields():
    finding = {
        "category": "info",
        "title": "Info Finding",
        "validation_method": "scan",
    }
    result = _issue_signature(finding)
    assert "info" in result
    assert "info-finding" in result
    assert "scan" in result


def test_empty_finding_returns_compact_pipes():
    finding = {}
    result = _issue_signature(finding)
    assert result == "||||"


def test_empty_metadata_defaults_to_empty():
    finding = {
        "category": "x",
        "title": "y",
        "validation_method": "z",
        "metadata": {},
    }
    result = _issue_signature(finding)
    assert "x" in result
    assert "y" in result
    assert "z" in result


def test_metadata_not_dict_ignored():
    finding = {
        "category": "cat",
        "title": "title",
        "metadata": "not-a-dict",
    }
    result = _issue_signature(finding)
    assert "cat" in result
