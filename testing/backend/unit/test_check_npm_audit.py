import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

import datetime

from scripts.check_npm_audit import (
    extract_ghsa_or_cve,
    is_exception_valid,
    check_expiry_warning,
    SEVERITY_LEVELS,
)


# SEVERITY_LEVELS mapping
class TestSeverityLevels:
    def test_critical_highest(self):
        assert SEVERITY_LEVELS["critical"] == 4

    def test_high(self):
        assert SEVERITY_LEVELS["high"] == 3

    def test_moderate_and_medium_equal(self):
        assert SEVERITY_LEVELS["moderate"] == 2
        assert SEVERITY_LEVELS["medium"] == 2

    def test_low(self):
        assert SEVERITY_LEVELS["low"] == 1

    def test_unknown(self):
        assert SEVERITY_LEVELS["unknown"] == 1


class TestExtractGhsaOrCve:
    def test_extracts_ghsa_from_url(self):
        issue = {"url": "https://github.com/advisories/GHSA-abcd-1234-wxyz"}
        assert extract_ghsa_or_cve(issue) == "GHSA-abcd-1234-wxyz"

    def test_extracts_cve_from_url(self):
        issue = {"url": "https://nvd.nist.gov/vuln/detail/CVE-2024-99999"}
        assert extract_ghsa_or_cve(issue) == "CVE-2024-99999"

    def test_extracts_from_source_field(self):
        issue = {"source": "https://github.com/advisories/GHSA-xxxx-yyyy"}
        assert extract_ghsa_or_cve(issue) == "GHSA-xxxx-yyyy"

    def test_extracts_from_title_field(self):
        issue = {"title": "Regular Expression Denial of Service in CVE-2024-0001"}
        assert extract_ghsa_or_cve(issue) == "CVE-2024-0001"

    def test_extracts_ghsa_from_title(self):
        issue = {"title": "Prototype Pollution in GHSA-pqr5-stuv-6789"}
        assert extract_ghsa_or_cve(issue) == "GHSA-pqr5-stuv-6789"

    def test_returns_unknown_when_no_match(self):
        assert extract_ghsa_or_cve({}) == "UNKNOWN"
        assert extract_ghsa_or_cve({"url": "https://example.com"}) == "UNKNOWN"


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
        exc = {"package": "lodash", "expires_at": near.isoformat()}
        check_expiry_warning(exc, warn_days=14)
        assert "lodash" in caplog.text

    def test_does_not_warn_far_from_expiry(self, caplog):
        far = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        exc = {"package": "lodash", "expires_at": far.isoformat()}
        check_expiry_warning(exc, warn_days=14)
        assert "lodash" not in caplog.text

    def test_ignores_null_expires_at(self):
        exc = {"package": "lodash", "expires_at": None}
        check_expiry_warning(exc, warn_days=14)
