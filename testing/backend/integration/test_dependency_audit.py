import pytest
import json
import tempfile
from pathlib import Path
import subprocess
import sys
import yaml
from datetime import datetime, timedelta

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"

class TestDependencyAudit:
    """Test dependency audit and policy scripts"""

    def test_check_pip_audit_passes_with_no_vulns(self):
        """Test check_pip_audit.py with a clean report"""
        report = {
            "vulnerabilities": [],
            "stats": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_pip_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "no vulnerabilities" in result.stderr.lower() or "passed" in result.stderr.lower()

    def test_check_pip_audit_fails_with_high_severity(self):
        """Test check_pip_audit.py blocks on high-severity vulnerability"""
        report = {
            "vulnerabilities": [
                {
                    "package": "bad-package",
                    "installed_version": "1.0.0",
                    "cve": "CVE-2026-12345",
                    "vulnerability": {
                        "severity": "high",
                        "advisory": "Critical RCE vulnerability",
                    },
                }
            ],
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_pip_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 1
            assert "CVE-2026-12345" in result.stderr

    def test_pip_exception_bypasses_block(self):
        """Test that documented pip exceptions allow CI to pass"""
        future_date = (datetime.now() + timedelta(days=30)).date().isoformat()

        report = {
            "vulnerabilities": [
                {
                    "package": "accepted-risk",
                    "installed_version": "1.0.0",
                    "cve": "CVE-2026-11111",
                    "vulnerability": {
                        "severity": "high",
                        "advisory": "Requires X condition",
                    },
                }
            ],
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {
                "CVE-2026-11111": {
                    "package": "accepted-risk",
                    "severity": "high",
                    "reason": "Risk accepted; condition doesn't apply",
                    "expires_at": future_date,
                    "approved_by": "security-team",
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_pip_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "exceptions applied" in result.stderr.lower() or "exceptions applied" in result.stdout.lower()

    def test_pip_expired_exception_blocks(self):
        """Test that expired exceptions are treated as violations"""
        past_date = (datetime.now() - timedelta(days=3)).date().isoformat()

        report = {
            "vulnerabilities": [
                {
                    "package": "expired-exception-pkg",
                    "installed_version": "1.0.0",
                    "cve": "CVE-2026-22222",
                    "vulnerability": {
                        "severity": "high",
                        "advisory": "Something bad",
                    },
                }
            ],
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {
                "CVE-2026-22222": {
                    "package": "expired-exception-pkg",
                    "severity": "high",
                    "reason": "Old exception",
                    "expires_at": past_date,
                    "approved_by": "security-team",
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_pip_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 1
            assert "expired" in result.stderr.lower()

    def test_check_npm_audit_passes_with_no_vulns(self):
        """Test check_npm_audit.py with a clean npm report"""
        report = {
            "vulnerabilities": {},
            "metadata": {"vulnerabilities": {"total": 0}},
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_npm_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "no npm vulnerabilities" in result.stderr.lower() or "passed" in result.stderr.lower()

    def test_check_npm_audit_fails_with_high_severity(self):
        """Test check_npm_audit.py blocks on high-severity vulnerability"""
        report = {
            "vulnerabilities": {
                "framer-motion": {
                    "name": "framer-motion",
                    "severity": "high",
                    "via": [
                        {
                            "source": "GHSA-jqrj-82ww",
                            "name": "framer-motion",
                            "url": "https://github.com/advisories/GHSA-jqrj-82ww",
                            "severity": "high",
                            "cwe": ["CWE-94"],
                        }
                    ],
                }
            }
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_npm_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 1
            assert "GHSA-jqrj-82ww" in result.stderr

    def test_npm_exception_bypasses_block(self):
        """Test that npm exceptions bypass blocker"""
        future_date = (datetime.now() + timedelta(days=30)).date().isoformat()

        report = {
            "vulnerabilities": {
                "framer-motion": {
                    "name": "framer-motion",
                    "severity": "high",
                    "via": [
                        {
                            "source": "GHSA-jqrj-82ww",
                            "name": "framer-motion",
                            "url": "https://github.com/advisories/GHSA-jqrj-82ww",
                            "severity": "high",
                            "cwe": ["CWE-94"],
                        }
                    ],
                }
            }
        }

        config = {
            "policy": {"min_severity_to_block": "high"},
            "exceptions": {
                "GHSA-jqrj-82ww": {
                    "package": "framer-motion",
                    "severity": "high",
                    "reason": "Excepted RCE vulnerability",
                    "expires_at": future_date,
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "report.json"
            config_file = Path(tmpdir) / "config.yaml"

            with open(report_file, 'w') as f:
                json.dump(report, f)

            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_npm_audit.py"),
                    "--report", str(report_file),
                    "--config", str(config_file),
                    "--min-severity", "high",
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert "excepted" in result.stderr.lower() or "excepted" in result.stdout.lower()

    def test_generate_sbom(self):
        """Test generate_sbom.py generates CycloneDX 1.4 formats"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sbom_file = Path(tmpdir) / "sbom.json"

            result = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "generate_sbom.py"),
                    "--output", str(sbom_file),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0
            assert sbom_file.exists()

            with open(sbom_file) as f:
                sbom = json.load(f)

            assert sbom.get("bomFormat") == "CycloneDX"
            assert sbom.get("specVersion") == "1.4"
            assert "components" in sbom

    def test_missing_report_returns_exit_code_1(self):
        """Verify check_pip_audit.py and check_npm_audit.py return exit code 1 when the report doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_report = Path(tmpdir) / "does_not_exist.json"
            config_file = Path(tmpdir) / "config.yaml"
            config = {
                "policy": {"min_severity_to_block": "high"},
                "exceptions": {},
            }
            with open(config_file, 'w') as f:
                yaml.dump(config, f)

            # Test check_pip_audit.py
            result_pip = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_pip_audit.py"),
                    "--report", str(missing_report),
                    "--config", str(config_file),
                ],
                capture_output=True,
                text=True,
            )
            assert result_pip.returncode == 1
            assert "is missing or empty" in result_pip.stderr

            # Test check_npm_audit.py
            result_npm = subprocess.run(
                [
                    sys.executable, str(SCRIPTS_DIR / "check_npm_audit.py"),
                    "--report", str(missing_report),
                    "--config", str(config_file),
                ],
                capture_output=True,
                text=True,
            )
            assert result_npm.returncode == 1
            assert "is missing or empty" in result_npm.stderr
