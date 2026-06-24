import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

import datetime

from scripts.check_pip_audit import (
    get_cve_id,
    is_exception_valid,
    check_expiry_warning,
    parse_vulnerabilities,
    SEVERITY_LEVELS,
)


# SEVERITY_LEVELS mapping
class TestSeverityLevels:
    def test_severity_critical_highest(self):
        assert SEVERITY_LEVELS["critical"] == 4

    def test_severity_high(self):
        assert SEVERITY_LEVELS["high"] == 3

    def test_severity_medium(self):
        assert SEVERITY_LEVELS["medium"] == 2

    def test_severity_moderate(self):
        assert SEVERITY_LEVELS["moderate"] == 2

    def test_severity_low(self):
        assert SEVERITY_LEVELS["low"] == 1

    def test_severity_unknown(self):
        assert SEVERITY_LEVELS["unknown"] == 1


class TestGetCveId:
    def test_returns_cve_field_directly(self):
        vuln = {"cve": "CVE-2024-12345", "id": "GHSA-xxxx-xxxx"}
        assert get_cve_id(vuln) == "CVE-2024-12345"

    def test_returns_id_when_cve_absent(self):
        vuln = {"id": "GHSA-xxxx-xxxx"}
        assert get_cve_id(vuln) == "GHSA-xxxx-xxxx"

    def test_returns_advisory_nested_id(self):
        vuln = {"advisory": {"id": "CVE-2024-99999"}}
        assert get_cve_id(vuln) == "CVE-2024-99999"

    def test_returns_unknown_when_all_absent(self):
        assert get_cve_id({}) == "UNKNOWN"
        assert get_cve_id({"foo": "bar"}) == "UNKNOWN"


class TestIsExceptionValid:
    def test_returns_true_when_not_expired(self):
        future = datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc)
        exc = {"expires_at": future.isoformat()}
        assert is_exception_valid(exc) is True

    def test_returns_false_when_expired(self):
        past = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        exc = {"expires_at": past.isoformat()}
        assert is_exception_valid(exc) is False

    def test_handles_date_only_iso_format(self):
        future = datetime.date(2099, 12, 31)
        exc = {"expires_at": "2099-12-31"}
        assert is_exception_valid(exc) is True

    def test_handles_naive_datetime(self):
        future = datetime.datetime(2099, 1, 1)
        exc = {"expires_at": future.isoformat()}
        assert is_exception_valid(exc) is True

    def test_returns_false_when_no_expires_at(self):
        assert is_exception_valid({}) is False
        assert is_exception_valid({"expires_at": None}) is False

    def test_returns_false_for_unknown_type(self):
        exc = {"expires_at": 12345}
        assert is_exception_valid(exc) is False


class TestCheckExpiryWarning:
    def test_warns_within_threshold(self, caplog):
        near = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)
        exc = {"package": "requests", "expires_at": near.isoformat()}
        check_expiry_warning(exc, warn_days=14)
        assert "requests" in caplog.text

    def test_does_not_warn_far_from_expiry(self, caplog):
        far = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        exc = {"package": "requests", "expires_at": far.isoformat()}
        check_expiry_warning(exc, warn_days=14)
        assert "requests" not in caplog.text

    def test_ignores_null_expires_at(self):
        exc = {"package": "requests", "expires_at": None}
        check_expiry_warning(exc, warn_days=14)


class TestParseVulnerabilities:
    def test_parses_top_level_vulnerabilities_list(self):
        report = {
            "vulnerabilities": [
                {"name": "requests", "version": "2.0.0", "id": "CVE-2024-1"},
            ]
        }
        vuls = parse_vulnerabilities(report)
        assert len(vuls) == 1
        assert vuls[0]["name"] == "requests"

    def test_parses_dependencies_format(self):
        report = {
            "dependencies": [
                {
                    "name": "flask",
                    "version": "1.0.0",
                    "vulns": [
                        {"id": "GHSA-2222", "severity": "high"},
                    ],
                }
            ]
        }
        vuls = parse_vulnerabilities(report)
        assert len(vuls) == 1
        assert vuls[0]["package"] == "flask"
        assert vuls[0]["cve"] == "GHSA-2222"

    def test_parses_top_level_list_format(self):
        report = [
            {"name": "django", "version": "3.0", "vulns": [{"id": "CVE-2024-3"}]}
        ]
        vuls = parse_vulnerabilities(report)
        assert len(vuls) == 1
        assert vuls[0]["package"] == "django"

    def test_parses_and_skips_null_vulns_in_dependencies(self):
        report = {
            "dependencies": [
                {"name": "good-pkg", "version": "1.0", "vulns": [{"id": "CVE-2024-1"}]},
                {"name": "bad-pkg", "version": "1.0", "vulns": [None]},
            ]
        }
        vuls = parse_vulnerabilities(report)
        assert len(vuls) == 1
        assert vuls[0]["package"] == "good-pkg"

    def test_returns_empty_for_empty_report(self):
        assert parse_vulnerabilities({}) == []
        assert parse_vulnerabilities([]) == []
