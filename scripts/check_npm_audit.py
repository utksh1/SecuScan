#!/usr/bin/env python3
"""
Parse npm audit JSON report and enforce policy.

Usage:
    python scripts/check_npm_audit.py \
      --report frontend/npm-audit-report.json \
      --config .audit-config.yaml \
      --min-severity high
"""

import json
import sys
import argparse
import re
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
    "moderate": 2,
    "medium": 2,
    "low": 1,
    "info": 1,
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
    }

def load_npm_audit_report(report_file: str) -> dict:
    """Load npm audit JSON report"""
    with open(report_file) as f:
        return json.load(f)

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

def extract_ghsa_or_cve(issue: dict) -> str:
    """Extract GHSA or CVE identifier from npm issue object"""
    cwe = issue.get("cwe", [])
    cve_id = "UNKNOWN"
    if isinstance(cwe, list) and cwe and isinstance(cwe[0], str) and cwe[0]:
        cve_id = cwe[0]

    # Try parsing URL for GHSA/CVE
    url = issue.get("url", "")
    if isinstance(url, str) and url:
        match = re.search(r'(GHSA-[a-zA-Z0-9-]+|CVE-\d+-\d+)', url)
        if match:
            return match.group(1)

    # Try parsing source
    source = issue.get("source")
    if isinstance(source, str):
        match = re.search(r'(GHSA-[a-zA-Z0-9-]+|CVE-\d+-\d+)', source)
        if match:
            return match.group(1)

    # Try parsing title
    title = issue.get("title", "")
    if isinstance(title, str) and title:
        match = re.search(r'(GHSA-[a-zA-Z0-9-]+|CVE-\d+-\d+)', title)
        if match:
            return match.group(1)

    # Try mapping integer source
    if isinstance(source, int):
        if cve_id == "UNKNOWN" or not cve_id:
            return f"ADVISORY-{source}"

    return cve_id or "UNKNOWN"

def main():
    parser = argparse.ArgumentParser(description="Check npm audit report against policy")
    parser.add_argument("--report", required=True, help="Path to npm audit JSON report")
    parser.add_argument("--config", required=True, help="Path to .audit-config.yaml")
    parser.add_argument(
        "--min-severity",
        choices=["critical", "high", "moderate", "medium", "low"],
        default=None,
    )

    args = parser.parse_args()

    # Load config and report
    config = load_config(args.config)
    policy = config.get("policy", {})
    exceptions = config.get("exceptions", {}) or {}

    # Precedence: argument > config file > default (high)
    min_severity_str = args.min_severity or policy.get("min_severity_to_block", "high")
    min_severity_str = min_severity_str.lower()
    if min_severity_str == "medium":
        min_severity_str = "moderate"

    report_path = Path(args.report)
    if not report_path.exists() or report_path.stat().st_size == 0:
        logger.error(f"Error: Audit report at {args.report} is missing or empty.")
        return 1

    try:
        report = load_npm_audit_report(args.report)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in report: {args.report}")
        return 1

    vulnerabilities = report.get("vulnerabilities", {})
    if not vulnerabilities:
        logger.info("[OK] No npm vulnerabilities found!")
        return 0

    blocking_count = 0
    warning_count = 0
    excepted_count = 0

    min_severity_level = SEVERITY_LEVELS.get(min_severity_str, 3)

    for package_name, vuln_data in vulnerabilities.items():
        if not isinstance(vuln_data, dict):
            continue

        via_list = vuln_data.get("via", [])
        # If via_list is empty or package itself has vulnerability info directly
        if not via_list:
            # Check package-level severity
            severity = vuln_data.get("severity", "unknown").lower()
            severity_level = SEVERITY_LEVELS.get(severity, 1)

            # Check package exceptions
            is_excepted = False
            exception = None
            if package_name in exceptions:
                exception = exceptions[package_name]
                if exception and isinstance(exception, dict):
                    is_excepted = True

            if is_excepted and exception:
                if not is_exception_valid(exception):
                    if policy.get("enforce_expiry", True):
                        logger.error(f"Exception for package {package_name} has expired!")
                        is_excepted = False
                    else:
                        logger.warning(f"Exception for package {package_name} has expired, but enforce_expiry is set to false.")
                        check_expiry_warning(exception, policy.get("warn_before_expiry_days", 14))
                        logger.info(f"  [OK] {package_name} (package-excepted)")
                        excepted_count += 1
                        continue
                else:
                    check_expiry_warning(exception, policy.get("warn_before_expiry_days", 14))
                    logger.info(f"  [OK] {package_name} (package-excepted)")
                    excepted_count += 1
                    continue

            if severity_level >= min_severity_level:
                blocking_count += 1
                logger.error(f"[FAIL] Package {package_name} is vulnerable ({severity})")
            else:
                warning_count += 1
                logger.warning(f"[WARN] Package {package_name} is vulnerable ({severity})")
            continue

        # Check via items
        for issue in via_list:
            if isinstance(issue, str):
                # Depedency link, usually handled by other keys. We don't want to double block unless we have to.
                continue

            if isinstance(issue, dict):
                severity = issue.get("severity", "").lower()
                cvss = issue.get("cvss", {})
                cve_id = extract_ghsa_or_cve(issue)

                # Check exceptions by CVE ID or package name
                is_excepted = False
                exception = None

                if cve_id in exceptions:
                    exception = exceptions[cve_id]
                    if exception and isinstance(exception, dict):
                        excepted_package = exception.get("package")
                        if not excepted_package or excepted_package == package_name:
                            is_excepted = True
                elif package_name in exceptions:
                    exception = exceptions[package_name]
                    if exception and isinstance(exception, dict):
                        is_excepted = True

                if is_excepted and exception:
                    if not is_exception_valid(exception):
                        if policy.get("enforce_expiry", True):
                            logger.error(
                                f"Exception for {cve_id or package_name} has expired! "
                                f"Expiry: {exception.get('expires_at')}"
                            )
                            is_excepted = False
                        else:
                            logger.warning(
                                f"Exception for {cve_id or package_name} has expired, but enforce_expiry is set to false. "
                                f"Expiry: {exception.get('expires_at')}"
                            )
                            check_expiry_warning(exception, policy.get("warn_before_expiry_days", 14))
                            logger.info(f"  [OK] {cve_id}: {package_name} (excepted)")
                            excepted_count += 1
                            continue
                    else:
                        check_expiry_warning(exception, policy.get("warn_before_expiry_days", 14))
                        logger.info(f"  [OK] {cve_id}: {package_name} (excepted)")
                        excepted_count += 1
                        continue

                severity_level = SEVERITY_LEVELS.get(severity, 1)
                if severity_level >= min_severity_level:
                    blocking_count += 1
                    logger.error(
                        f"[FAIL] {cve_id} ({severity}): {package_name} "
                        f"(CVSS {cvss.get('score', 'N/A')})"
                    )
                else:
                    warning_count += 1
                    logger.warning(f"[WARN] {cve_id} ({severity}): {package_name}")

    if excepted_count > 0:
        logger.info(f"[OK] {excepted_count} exceptions successfully applied.")

    if warning_count > 0:
        logger.warning(f"[WARN] {warning_count} low-severity vulnerabilities detected.")

    if blocking_count > 0:
        logger.error(f"[FAIL] {blocking_count} npm vulnerabilities block deployment")
        return 1

    logger.info("[OK] npm audit passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
