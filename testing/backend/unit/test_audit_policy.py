import sys
import os
import json
import yaml
import pytest
import datetime
from pathlib import Path
from unittest.mock import patch

# Dynamically add scripts folder to python path
SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# pyrefly: ignore [missing-import]
import check_pip_audit

# pyrefly: ignore [missing-import]
import check_npm_audit

# ==============================================================================
# 1. UNIT TESTS: DATE AND EXCEPTION VALIDATION
# ==============================================================================


def test_pip_is_exception_valid():
    """Test pip-audit is_exception_valid with various dates and formats"""
    # Active timezone-aware UTC current time
    current_utc = datetime.datetime.now(datetime.timezone.utc)

    # 1. Past date string (Expired)
    exc_past = {"expires_at": "2025-01-01"}
    assert (
        check_pip_audit.is_exception_valid(exc_past, current_date=current_utc) is False
    )

    # 2. Future date string (Valid)
    exc_future = {"expires_at": "2035-12-31"}
    assert (
        check_pip_audit.is_exception_valid(exc_future, current_date=current_utc) is True
    )

    # 3. Date object (Valid/Expired)
    exc_date_past = {"expires_at": datetime.date(2025, 1, 1)}
    assert (
        check_pip_audit.is_exception_valid(exc_date_past, current_date=current_utc)
        is False
    )

    exc_date_future = {"expires_at": datetime.date(2035, 12, 31)}
    assert (
        check_pip_audit.is_exception_valid(exc_date_future, current_date=current_utc)
        is True
    )

    # 4. Datetime object
    exc_dt_future = {
        "expires_at": datetime.datetime(
            2035, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc
        )
    }
    assert (
        check_pip_audit.is_exception_valid(exc_dt_future, current_date=current_utc)
        is True
    )

    # 5. Missing / Null fields
    assert check_pip_audit.is_exception_valid({}, current_date=current_utc) is False
    assert (
        check_pip_audit.is_exception_valid(
            {"expires_at": None}, current_date=current_utc
        )
        is False
    )


def test_npm_is_exception_valid():
    """Test npm-audit is_exception_valid with various dates and formats"""
    current_utc = datetime.datetime.now(datetime.timezone.utc)

    # 1. Past date string
    exc_past = {"expires_at": "2025-01-01"}
    assert (
        check_npm_audit.is_exception_valid(exc_past, current_date=current_utc) is False
    )

    # 2. Future date string
    exc_future = {"expires_at": "2035-12-31"}
    assert (
        check_npm_audit.is_exception_valid(exc_future, current_date=current_utc) is True
    )

    # 3. Missing / Null fields
    assert check_npm_audit.is_exception_valid({}, current_date=current_utc) is False
    assert (
        check_npm_audit.is_exception_valid(
            {"expires_at": None}, current_date=current_utc
        )
        is False
    )


# ==============================================================================
# 2. UNIT TESTS: UPSTREAM JSON SHAPES AND EXTRACTION
# ==============================================================================


def test_pip_parse_vulnerabilities_variations():
    """Test pip-audit parse_vulnerabilities with Variant A (Dictionary Wrapped) and Variant B (Flat List)"""
    vulns_mock = [
        {
            "id": "GHSA-c5u2-73g7-4w73",
            "description": "Mock high severity vuln",
            "severity": "HIGH",
        }
    ]

    # Variant A: Dictionary Wrapped
    dict_report = {
        "dependencies": [{"name": "requests", "version": "2.25.0", "vulns": vulns_mock}]
    }
    parsed_a = check_pip_audit.parse_vulnerabilities(dict_report)
    assert len(parsed_a) == 1
    assert parsed_a[0]["package"] == "requests"
    assert parsed_a[0]["cve"] == "GHSA-c5u2-73g7-4w73"
    assert parsed_a[0]["vulnerability"]["severity"] == "HIGH"

    # Variant B: Flat List Array
    list_report = [{"name": "requests", "version": "2.25.0", "vulns": vulns_mock}]
    parsed_b = check_pip_audit.parse_vulnerabilities(list_report)
    assert len(parsed_b) == 1
    assert parsed_b[0]["package"] == "requests"
    assert parsed_b[0]["cve"] == "GHSA-c5u2-73g7-4w73"
    assert parsed_b[0]["vulnerability"]["severity"] == "HIGH"


def test_npm_extract_ghsa_or_cve():
    """Test npm-audit extract_ghsa_or_cve with different structures, specifically testing integer source IDs"""
    # 1. Standard CWE list
    issue_cwe = {"cwe": ["GHSA-c5u2-73g7-4w73"], "severity": "high"}
    assert check_npm_audit.extract_ghsa_or_cve(issue_cwe) == "GHSA-c5u2-73g7-4w73"

    # 2. URL parsing
    issue_url = {
        "url": "https://github.com/advisories/GHSA-1234-abcd-efgh",
        "severity": "high",
    }
    assert check_npm_audit.extract_ghsa_or_cve(issue_url) == "GHSA-1234-abcd-efgh"

    # 3. Source string matching
    issue_src_str = {"source": "GHSA-5678-ijkl-mnop", "severity": "high"}
    assert check_npm_audit.extract_ghsa_or_cve(issue_src_str) == "GHSA-5678-ijkl-mnop"

    # 4. Edge case: Source integer mapping (advisory integer source ID)
    issue_src_int = {"source": 1085097, "severity": "high"}
    assert check_npm_audit.extract_ghsa_or_cve(issue_src_int) == "ADVISORY-1085097"


# ==============================================================================
# 3. POLICY ENGINE INTEGRATION TESTS (FIXTURE BOUNDARIES)
# ==============================================================================


@pytest.fixture
def base_config():
    """Returns a basic YAML config structure"""
    return {
        "version": 1.0,
        "policy": {
            "min_severity_to_block": "high",
            "enforce_expiry": True,
            "warn_before_expiry_days": 14,
        },
        "exceptions": {},
        "excluded_packages": [],
    }


def test_empty_or_malformed_report_gate(tmp_path, base_config):
    """Verify checkers fail (exit code 1) on missing, empty, or malformed JSON reports"""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # 1. Missing report
    missing_report = tmp_path / "missing.json"

    # Pip audit
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(missing_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # Npm audit
    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(missing_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 1

    # 2. Empty report (0 bytes)
    empty_report = tmp_path / "empty.json"
    empty_report.touch()

    # Pip audit
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(empty_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # Npm audit
    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(empty_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 1

    # 3. Malformed report (invalid JSON)
    malformed_report = tmp_path / "malformed.json"
    with open(malformed_report, "w") as f:
        f.write("{invalid_json: true}")

    # Pip audit
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(malformed_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # Npm audit
    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(malformed_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 1


def test_expired_exception_fixture(tmp_path, base_config):
    """Fixture 1: Verify expired exception causes build gate failure (exit code 1)"""
    # Setup configuration with expired exception (expires_at: 2025-01-01)
    base_config["exceptions"]["GHSA-c5u2-73g7-4w73"] = {
        "package": "requests",
        "expires_at": "2025-01-01",
        "reason": "Expired exception test",
    }

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # 1. Pip audit expired exception test
    pip_report = tmp_path / "expired_exception_pip.json"
    pip_data = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "GHSA-c5u2-73g7-4w73",
                        "severity": "HIGH",
                        "description": "High vulnerability",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # 2. Npm audit expired exception test
    npm_report = tmp_path / "expired_exception_npm.json"
    npm_data = {
        "vulnerabilities": {
            "requests": {
                "name": "requests",
                "severity": "high",
                "via": [
                    {
                        "source": "GHSA-c5u2-73g7-4w73",
                        "name": "requests",
                        "severity": "high",
                        "url": "https://github.com/advisories/GHSA-c5u2-73g7-4w73",
                    }
                ],
            }
        }
    }
    with open(npm_report, "w") as f:
        json.dump(npm_data, f)

    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(npm_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 1

    # 3. Verification of policy bypass flag: enforce_expiry = False
    base_config["policy"]["enforce_expiry"] = False
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 0

    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(npm_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 0


def test_blocking_severity_fixture(tmp_path, base_config):
    """Fixture 2: Verify high severity advisory triggers gate failure when threshold is MEDIUM/MODERATE"""
    # Allowed threshold set to medium/moderate (e.g. blocking anything >= medium)
    base_config["policy"]["min_severity_to_block"] = "medium"
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # 1a. Pip audit: CRITICAL (uppercase) vulnerability should fail
    pip_report_upper = tmp_path / "blocking_severity_pip_upper.json"
    pip_data_upper = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "GHSA-c5u2-73g7-4w73",
                        "severity": "CRITICAL",
                        "description": "Critical vulnerability",
                    }
                ],
            }
        ]
    }
    with open(pip_report_upper, "w") as f:
        json.dump(pip_data_upper, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report_upper),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # 1b. Pip audit: critical (lowercase) vulnerability should fail
    pip_report_lower = tmp_path / "blocking_severity_pip_lower.json"
    pip_data_lower = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "GHSA-c5u2-73g7-4w74",
                        "severity": "critical",
                        "description": "Critical vulnerability lowercase",
                    }
                ],
            }
        ]
    }
    with open(pip_report_lower, "w") as f:
        json.dump(pip_data_lower, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report_lower),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # 2. Npm audit: high vulnerability should fail
    npm_report = tmp_path / "blocking_severity_npm.json"
    npm_data = {
        "vulnerabilities": {
            "lodash": {
                "name": "lodash",
                "severity": "high",
                "via": [
                    {
                        "source": 1085097,
                        "name": "lodash",
                        "severity": "high",
                        "url": "https://github.com/advisories/GHSA-lodash-123",
                    }
                ],
            }
        }
    }
    with open(npm_report, "w") as f:
        json.dump(npm_data, f)

    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(npm_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 1


def test_valid_exception_fixture(tmp_path, base_config):
    """Fixture 3: Verify vulnerability with valid future exception returns clean exit code (0)"""
    # Setup configuration with future exception (expires_at: 2035-12-31)
    base_config["exceptions"]["GHSA-c5u2-73g7-4w73"] = {
        "package": "requests",
        "expires_at": "2035-12-31",
        "reason": "Vulnerability monitored; valid future exception test",
    }

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # 1. Pip audit valid exception
    pip_report = tmp_path / "valid_exception_pip.json"
    pip_data = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "GHSA-c5u2-73g7-4w73",
                        "severity": "HIGH",
                        "description": "High vulnerability",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 0

    # 2. Npm audit valid exception
    npm_report = tmp_path / "valid_exception_npm.json"
    npm_data = {
        "vulnerabilities": {
            "requests": {
                "name": "requests",
                "severity": "high",
                "via": [
                    {
                        "source": "GHSA-c5u2-73g7-4w73",
                        "name": "requests",
                        "severity": "high",
                        "url": "https://github.com/advisories/GHSA-c5u2-73g7-4w73",
                    }
                ],
            }
        }
    }
    with open(npm_report, "w") as f:
        json.dump(npm_data, f)

    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(npm_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 0


def test_pip_alias_exception_matching(tmp_path, base_config):
    """Test that pip exception matches by vulnerability alias (e.g. CVE ID)"""
    # 1. Setup config with CVE exception
    base_config["exceptions"]["CVE-2026-9999"] = {
        "package": "pyyaml",
        "expires_at": "2035-12-31",
        "reason": "Alias matching test",
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # 2. Setup pip report where the vuln ID is PYSEC-2026-9999, but aliases contains CVE-2026-9999
    pip_report = tmp_path / "alias_pip_report.json"
    pip_data = {
        "dependencies": [
            {
                "name": "pyyaml",
                "version": "6.0.0",
                "vulns": [
                    {
                        "id": "PYSEC-2026-9999",
                        "aliases": ["CVE-2026-9999", "GHSA-xxxx-xxxx-xxxx"],
                        "severity": "HIGH",
                        "description": "YAML deserialization",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data, f)

    # Run check_pip_audit.py, it should succeed (exit code 0) since the alias is excepted
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 0


def test_exception_expiry_warnings_and_bypass(tmp_path, base_config):
    """Test exception close-to-expiry warning triggers, and enforce_expiry flag logic"""
    # 1. Close-to-expiry warning test
    current_utc = datetime.datetime.now(datetime.timezone.utc)
    close_expiry_date = (current_utc + datetime.timedelta(days=5)).date().isoformat()

    exception = {
        "package": "requests",
        "expires_at": close_expiry_date,
        "reason": "Soon expiring exception",
    }

    # We should see warning printed or logged when checking expiry warning
    with patch("check_pip_audit.logger.warning") as mock_warn:
        check_pip_audit.check_expiry_warning(
            exception, warn_days=14, current_date=current_utc
        )
        assert mock_warn.called
        assert "expires in" in mock_warn.call_args[0][0]

    # 2. Exception expiry bypass when enforce_expiry is False
    base_config["exceptions"]["CVE-2025-0001"] = {
        "package": "requests",
        "expires_at": "2020-01-01",  # Definitely expired
        "reason": "Expired but bypassed",
    }
    base_config["policy"]["enforce_expiry"] = False

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    pip_report = tmp_path / "expired_pip_report.json"
    pip_data = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "CVE-2025-0001",
                        "severity": "HIGH",
                        "description": "High vulnerability",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 0


def test_blocking_severity_thresholds(tmp_path, base_config):
    """Test blocking severity threshold case-insensitivity, unknown severity, and strict gating"""
    # 1. Case-insensitivity test: severity "hIgH" or "CRITICAL"
    base_config["policy"]["min_severity_to_block"] = "HiGh"
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    pip_report = tmp_path / "case_severity.json"
    pip_data = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "CVE-2026-9999",
                        "severity": "hIgH",
                        "description": "High vuln",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data, f)

    # hIgH should trigger high blocking severity and return exit code 1
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1

    # 2. Unknown severity: should not block when min-severity is high
    pip_data_unknown = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.25.0",
                "vulns": [
                    {
                        "id": "CVE-2026-9999",
                        "severity": "unknown",
                        "description": "Unknown severity",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data_unknown, f)

    # unknown is below HiGh threshold, should pass (0)
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 0

    # 3. Unknown severity: should block when min-severity is low
    base_config["policy"]["min_severity_to_block"] = "low"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # unknown is level 1, which blocks when min-severity is low
    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1


def test_real_pip_audit_fixture_flow(tmp_path, base_config):
    """Verify that parse_vulnerabilities parses real pip-audit flat list shape and main() blocks on high severity"""
    fixture_path = (
        Path(__file__).resolve().parents[0]
        / "fixtures"
        / "audit"
        / "pip_audit_real_shape.json"
    )
    with open(fixture_path) as f:
        report_data = json.load(f)

    parsed = check_pip_audit.parse_vulnerabilities(report_data)
    assert len(parsed) == 1
    assert parsed[0]["package"] == "requests"
    assert parsed[0]["cve"] == "GHSA-c5u2-73g7-4w73"
    assert parsed[0]["vulnerability"]["severity"] == "high"

    # Check that main() exits 1 when it contains a high issue
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(fixture_path),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 1


def test_real_npm_audit_fixture_flow(tmp_path, base_config):
    """Verify extract_ghsa_or_cve handles integer sources and that main() blocks on high severity from real npm shape"""
    fixture_path = (
        Path(__file__).resolve().parents[0]
        / "fixtures"
        / "audit"
        / "npm_audit_real_shape.json"
    )
    with open(fixture_path) as f:
        report_data = json.load(f)

    # Check that it loads properly
    vulnerabilities = report_data.get("vulnerabilities", {})
    assert "framer-motion" in vulnerabilities
    via_list = vulnerabilities["framer-motion"].get("via", [])
    assert len(via_list) == 1
    issue = via_list[0]
    assert isinstance(issue["source"], int)

    cve_id = check_npm_audit.extract_ghsa_or_cve(issue)
    # The URL contains the GHSA string
    assert cve_id == "GHSA-jqrj-82ww"

    # Check that main() exits 1 when it contains a high issue
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(fixture_path),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 1


def test_expired_exception_low_severity_no_block(tmp_path, base_config):
    """Expired exception on a LOW severity vuln should NOT block when threshold=high"""
    # Set exception for CVE-2025-LOW
    base_config["exceptions"]["CVE-2025-LOW"] = {
        "package": "somepkg",
        "expires_at": "2020-01-01",  # expired
        "reason": "old",
    }
    base_config["policy"]["min_severity_to_block"] = "high"

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(base_config, f)

    # Pip report with severity="low"
    pip_report = tmp_path / "low_severity_expired_pip.json"
    pip_data = {
        "dependencies": [
            {
                "name": "somepkg",
                "version": "1.0.0",
                "vulns": [
                    {
                        "id": "CVE-2025-LOW",
                        "severity": "low",
                        "description": "Low severity vuln",
                    }
                ],
            }
        ]
    }
    with open(pip_report, "w") as f:
        json.dump(pip_data, f)

    with patch(
        "sys.argv",
        [
            "check_pip_audit.py",
            "--report",
            str(pip_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_pip_audit.main() == 0

    # Npm report with severity="low"
    npm_report = tmp_path / "low_severity_expired_npm.json"
    npm_data = {
        "vulnerabilities": {
            "somepkg": {
                "name": "somepkg",
                "severity": "low",
                "via": [
                    {
                        "source": "CVE-2025-LOW",
                        "name": "somepkg",
                        "severity": "low",
                        "url": "https://github.com/advisories/CVE-2025-LOW",
                    }
                ],
            }
        }
    }
    with open(npm_report, "w") as f:
        json.dump(npm_data, f)

    with patch(
        "sys.argv",
        [
            "check_npm_audit.py",
            "--report",
            str(npm_report),
            "--config",
            str(config_file),
        ],
    ):
        assert check_npm_audit.main() == 0


# ==============================================================================
# 4. DIRECT UNIT TESTS: MALFORMED CONFIGS & REPORTS
# ==============================================================================


def test_load_config_malformed_yaml(tmp_path):
    """Test load_config function directly with malformed/invalid YAML"""
    malformed_yaml_file = tmp_path / "malformed_config.yaml"
    with open(malformed_yaml_file, "w") as f:
        f.write("{invalid_yaml: [}")

    # check_pip_audit should catch yaml.YAMLError and return defaults
    config_pip = check_pip_audit.load_config(str(malformed_yaml_file))
    assert isinstance(config_pip, dict)
    assert config_pip["policy"]["min_severity_to_block"] == "high"

    # check_npm_audit should catch yaml.YAMLError and return defaults
    config_npm = check_npm_audit.load_config(str(malformed_yaml_file))
    assert isinstance(config_npm, dict)
    assert config_npm["policy"]["min_severity_to_block"] == "high"


def test_load_config_missing_file():
    """Test load_config function directly with missing config file"""
    missing_file_path = "non_existent_file_path_xyz.yaml"

    # check_pip_audit should return defaults
    config_pip = check_pip_audit.load_config(missing_file_path)
    assert isinstance(config_pip, dict)
    assert config_pip["policy"]["min_severity_to_block"] == "high"

    # check_npm_audit should return defaults
    config_npm = check_npm_audit.load_config(missing_file_path)
    assert isinstance(config_npm, dict)
    assert config_npm["policy"]["min_severity_to_block"] == "high"


def test_load_report_malformed_json(tmp_path):
    """Test load_report function directly with malformed JSON"""
    malformed_json_file = tmp_path / "malformed_report.json"
    with open(malformed_json_file, "w") as f:
        f.write("{invalid_json: [}")

    # check_pip_audit.load_pip_audit_report should raise json.JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        check_pip_audit.load_pip_audit_report(str(malformed_json_file))

    # check_npm_audit.load_npm_audit_report should raise json.JSONDecodeError
    with pytest.raises(json.JSONDecodeError):
        check_npm_audit.load_npm_audit_report(str(malformed_json_file))


def test_pip_parse_vulnerabilities_malformed_structure():
    """Test pip-audit parse_vulnerabilities directly with unexpected/malformed report structures"""
    # 1. Report is completely empty dict
    assert check_pip_audit.parse_vulnerabilities({}) == []

    # 2. Report is an unexpected type (e.g. integer or string)
    assert check_pip_audit.parse_vulnerabilities(42) == []
    assert check_pip_audit.parse_vulnerabilities("not a dict") == []

    # 3. Report list has non-dict items
    assert check_pip_audit.parse_vulnerabilities([None, 123, "string"]) == []

    # 4. Report dict contains invalid dependencies (not list)
    assert check_pip_audit.parse_vulnerabilities({"dependencies": "not a list"}) == []

    # 5. Report list contains dicts with missing or malformed keys
    bad_dep_report = [
        {
            "name": "requests",
            "version": "2.25.0",
            "vulns": "not a list",  # vulns key is not a list
        }
    ]
    assert check_pip_audit.parse_vulnerabilities(bad_dep_report) == []

    bad_vuln_report = [
        {
            "name": "requests",
            "version": "2.25.0",
            "vulns": [None, "invalid_vuln_format"],  # elements in list are not dicts
        }
    ]
    assert check_pip_audit.parse_vulnerabilities(bad_vuln_report) == []


def test_npm_extract_ghsa_or_cve_malformed_structure():
    """Test npm-audit extract_ghsa_or_cve handles malformed structures and empty keys gracefully"""
    # 1. Empty dict
    assert check_npm_audit.extract_ghsa_or_cve({}) == "UNKNOWN"

    # 2. CWEs is not a list
    assert check_npm_audit.extract_ghsa_or_cve({"cwe": "not a list"}) == "UNKNOWN"

    # 3. CWE list with non-string elements
    assert check_npm_audit.extract_ghsa_or_cve({"cwe": [None, 123]}) == "UNKNOWN"

    # 4. URL or source field is not a string
    assert check_npm_audit.extract_ghsa_or_cve({"url": 12345}) == "UNKNOWN"
    assert check_npm_audit.extract_ghsa_or_cve({"source": []}) == "UNKNOWN"
