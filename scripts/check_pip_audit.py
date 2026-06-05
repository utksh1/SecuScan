#!/usr/bin/env python3
"""
Parse pip-audit JSON report and enforce policy.

Usage:
    python scripts/check_pip_audit.py \
      --report backend/pip-audit-report.json \
      --config .audit-config.yaml \
      --min-severity high
"""

import json
import sys
import argparse
from pathlib import Path
import datetime
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Severity ordering
SEVERITY_LEVELS = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "moderate": 2,
    "low": 1,
    "unknown": 1,
}

def load_config(config_file: str) -> dict:
    """Load audit configuration"""
    try:
        with open(config_file) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_file}, using defaults")
    except yaml.YAMLError as e:
        logger.error(f"Malformed config file {config_file}: {e}, using defaults")

    return {
        "policy": {
            "min_severity_to_block": "high",
            "enforce_expiry": True,
            "warn_before_expiry_days": 14,
        },
        "exceptions": {},
        "excluded_packages": [],
    }

def load_pip_audit_report(report_file: str) -> dict:
    """Load pip-audit JSON report"""
    with open(report_file) as f:
        return json.load(f)

def get_cve_id(vuln: dict) -> str:
    """Extract CVE ID from vulnerability record"""
    # Format: "CVE-2024-12345" or "GHSA-xxxx-xxxx-xxxx"
    if "cve" in vuln:
        return vuln["cve"]
    if "id" in vuln:
        return vuln["id"]
    return vuln.get("advisory", {}).get("id", "UNKNOWN")

def is_exception_valid(exception: dict, current_date: datetime.datetime = None) -> bool:
    """Check if exception is still valid (not expired)"""
    if current_date is None:
        current_date = datetime.datetime.now(datetime.timezone.utc)
    else:
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=datetime.timezone.utc)

    if "expires_at" not in exception:
        logger.warning("Exception missing expires_at; treating as expired")
        return False

    expires_at = exception["expires_at"]
    if expires_at is None:
        logger.warning("Exception expires_at is null; treating as expired")
        return False

    try:
        if isinstance(expires_at, str):
            if len(expires_at) == 10:
                expiry_date = datetime.date.fromisoformat(expires_at)
                expiry = datetime.datetime.combine(expiry_date, datetime.time.max, tzinfo=datetime.timezone.utc)
            else:
                expiry = datetime.datetime.fromisoformat(expires_at)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(expires_at, datetime.datetime):
            expiry = expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(expires_at, datetime.date):
            expiry = datetime.datetime.combine(expires_at, datetime.time.max, tzinfo=datetime.timezone.utc)
        else:
            logger.error(f"Unknown type for expires_at: {type(expires_at)}")
            return False

        return current_date < expiry
    except Exception as e:
        logger.error(f"Error parsing expiry date '{expires_at}': {e}")
        return False

def check_expiry_warning(exception: dict, warn_days: int, current_date: datetime.datetime = None):
    """Warn if exception is close to expiry"""
    if current_date is None:
        current_date = datetime.datetime.now(datetime.timezone.utc)
    else:
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=datetime.timezone.utc)

    if "expires_at" not in exception or exception["expires_at"] is None:
        return

    expires_at = exception["expires_at"]
    try:
        if isinstance(expires_at, str):
            if len(expires_at) == 10:
                expiry_date = datetime.date.fromisoformat(expires_at)
                expiry = datetime.datetime.combine(expiry_date, datetime.time.max, tzinfo=datetime.timezone.utc)
            else:
                expiry = datetime.datetime.fromisoformat(expires_at)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(expires_at, datetime.datetime):
            expiry = expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(expires_at, datetime.date):
            expiry = datetime.datetime.combine(expires_at, datetime.time.max, tzinfo=datetime.timezone.utc)
        else:
            return

        days_until_expiry = (expiry - current_date).days
        if 0 < days_until_expiry <= warn_days:
            logger.warning(
                f"Exception for {exception.get('package', 'unknown')} expires in {days_until_expiry} days! "
                f"Expiry: {expires_at}"
            )
    except Exception:
        pass

def parse_vulnerabilities(report) -> list:
    """Extract all vulnerability structures in a standard format"""
    vuls = []

    # 1. Top-level "vulnerabilities" list
    if isinstance(report, dict) and "vulnerabilities" in report and isinstance(report["vulnerabilities"], list):
        for v in report["vulnerabilities"]:
            if isinstance(v, dict):
                vuls.append(v)

    # 2. Dependencies with inner vulns
    if isinstance(report, dict) and "dependencies" in report and isinstance(report["dependencies"], list):
        for dep in report["dependencies"]:
            if not isinstance(dep, dict):
                continue
            package_name = dep.get("name", "unknown")
            version = dep.get("version", "unknown")
            vulns = dep.get("vulns", [])
            if isinstance(vulns, list):
                for v in vulns:
                    if not isinstance(v, dict):
                        continue
                    vuln_record = {
                        "package": package_name,
                        "installed_version": version,
                        "cve": v.get("id") or v.get("cve") or "UNKNOWN",
                        "aliases": v.get("aliases") or [],
                        "vulnerability": {
                            "severity": v.get("severity") or v.get("vulnerability", {}).get("severity") or "unknown",
                            "advisory": v.get("description") or v.get("advisory") or v.get("vulnerability", {}).get("advisory") or "",
                        }
                    }
                    vuls.append(vuln_record)

    # 3. Top-level list
    if isinstance(report, list):
        for dep in report:
            if not isinstance(dep, dict):
                continue
            package_name = dep.get("name", "unknown")
            version = dep.get("version", "unknown")
            vulns = dep.get("vulns", [])
            if isinstance(vulns, list):
                for v in vulns:
                    if not isinstance(v, dict):
                        continue
                    vuln_record = {
                        "package": package_name,
                        "installed_version": version,
                        "cve": v.get("id") or v.get("cve") or "UNKNOWN",
                        "aliases": v.get("aliases") or [],
                        "vulnerability": {
                            "severity": v.get("severity") or v.get("vulnerability", {}).get("severity") or "unknown",
                            "advisory": v.get("description") or v.get("advisory") or v.get("vulnerability", {}).get("advisory") or "",
                        }
                    }
                    vuls.append(vuln_record)

    return vuls

def main():
    parser = argparse.ArgumentParser(
        description="Check pip-audit report against policy"
    )
    parser.add_argument("--report", required=True, help="Path to pip-audit JSON report")
    parser.add_argument("--config", required=True, help="Path to .audit-config.yaml")
    parser.add_argument(
        "--min-severity",
        choices=["critical", "high", "medium", "low"],
        default=None,
        help="Minimum severity to block CI",
    )

    args = parser.parse_args()

    # Load config and report
    config = load_config(args.config)
    policy = config.get("policy", {})
    exceptions = config.get("exceptions", {}) or {}

    # Precedence: argument > config file > default (high)
    min_severity_str = args.min_severity or policy.get("min_severity_to_block", "high")
    min_severity_str = min_severity_str.lower()

    report_path = Path(args.report)
    if not report_path.exists() or report_path.stat().st_size == 0:
        logger.error(f"Error: Audit report at {args.report} is missing or empty.")
        return 1

    try:
        report = load_pip_audit_report(args.report)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in report: {args.report}")
        return 1

    vulnerabilities = parse_vulnerabilities(report)
    if not vulnerabilities:
        logger.info("[OK] No vulnerabilities found!")
        return 0

    # Filter and enforce policy
    blocking_vulns = []
    warning_vulns = []
    excepted_vulns = []

    min_severity_level = SEVERITY_LEVELS.get(min_severity_str, 3)

    for vuln in vulnerabilities:
        cve_id = get_cve_id(vuln)
        package = vuln.get("package", "unknown")
        version = vuln.get("installed_version", "unknown")

        inner_vuln = vuln.get("vulnerability") or {}
        severity = inner_vuln.get("severity") or vuln.get("severity") or "unknown"
        severity = severity.lower()
        advisory = inner_vuln.get("advisory") or vuln.get("advisory") or ""

        # Check if excepted
        is_excepted = False
        exception = None

        if cve_id in exceptions:
            exception = exceptions[cve_id]
            if exception and isinstance(exception, dict):
                excepted_package = exception.get("package")
                if not excepted_package or excepted_package == package:
                    is_excepted = True

        if not is_excepted:
            aliases = vuln.get("aliases") or []
            if not aliases and isinstance(vuln.get("vulnerability"), dict):
                aliases = vuln["vulnerability"].get("aliases") or []
            for alias in aliases:
                if alias in exceptions:
                    exception = exceptions[alias]
                    if exception and isinstance(exception, dict):
                        excepted_package = exception.get("package")
                        if not excepted_package or excepted_package == package:
                            is_excepted = True
                            break

        if not is_excepted and package in exceptions:
            exception = exceptions[package]
            if exception and isinstance(exception, dict):
                is_excepted = True

        if is_excepted and exception:
            # Validate exception
            if not is_exception_valid(exception):
                if policy.get("enforce_expiry", True):
                    logger.error(
                        f"Exception for {cve_id or package} has expired! "
                        f"Expiry: {exception.get('expires_at')}"
                    )
                    is_excepted = False
                else:
                    logger.warning(
                        f"Exception for {cve_id or package} has expired, but enforce_expiry is set to false. "
                        f"Expiry: {exception.get('expires_at')}"
                    )
                    check_expiry_warning(exception, policy.get("warn_before_expiry_days", 14))
                    excepted_vulns.append((cve_id, package, version, exception.get("reason")))
                    continue
            else:
                check_expiry_warning(exception, policy.get("warn_before_expiry_days", 14))
                excepted_vulns.append((cve_id, package, version, exception.get("reason")))
                continue

        # Check severity
        severity_level = SEVERITY_LEVELS.get(severity, 1)
        if severity_level >= min_severity_level:
            blocking_vulns.append((cve_id, package, version, severity, advisory))
        else:
            warning_vulns.append((cve_id, package, version, severity, advisory))

    # Report results
    if excepted_vulns:
        logger.info(f"[OK] {len(excepted_vulns)} exceptions applied:")
        for cve, pkg, ver, reason in excepted_vulns:
            logger.info(f"  - {cve} ({pkg}=={ver}): {reason}")

    if warning_vulns:
        logger.warning(f"[WARN] {len(warning_vulns)} low-severity vulnerabilities found:")
        for cve, pkg, ver, sev, adv in warning_vulns:
            logger.warning(f"  - {cve} ({sev}): {pkg}=={ver}")

    if blocking_vulns:
        logger.error(f"[FAIL] {len(blocking_vulns)} vulnerabilities block deployment:")
        for cve, pkg, ver, sev, adv in blocking_vulns:
            logger.error(f"  - {cve} ({sev}): {pkg}=={ver}")
            logger.error(f"    Advisory: {adv}")
            logger.error(f"    To exception: Add entry to .audit-config.yaml with expiry date")

        return 1  # Fail CI

    logger.info("[OK] Dependency audit passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
