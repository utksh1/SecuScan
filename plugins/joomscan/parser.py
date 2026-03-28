import re
from typing import Any, Dict, List


_VERSION_RE = re.compile(r"(?i)joomla!?\s*(?:version)?\s*[:=]\s*([\w\.-]+)")
_VULN_RE = re.compile(r"(?i)(?:vulnerable to|\[!\])\s*[:\-]?\s*(.+)")


def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    version = None

    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue

        version_match = _VERSION_RE.search(text)
        if version_match:
            version = version_match.group(1)
            findings.append(
                {
                    "title": "Joomla Version Detected",
                    "category": "CMS Fingerprint",
                    "severity": "info",
                    "description": f"Detected Joomla version: {version}",
                    "remediation": "Ensure installed Joomla release is fully patched.",
                    "metadata": {"version": version},
                }
            )
            continue

        vuln_match = _VULN_RE.search(text)
        if vuln_match:
            findings.append(
                {
                    "title": "Joomla Vulnerability Indicator",
                    "category": "CMS Vulnerability",
                    "severity": "high",
                    "description": vuln_match.group(1).strip(),
                    "remediation": "Validate CVE applicability and patch/update affected components.",
                    "metadata": {"line": text},
                }
            )
            continue

        if text.startswith("[+") or text.startswith("["):
            findings.append(
                {
                    "title": "JoomScan Observation",
                    "category": "CMS Security",
                    "severity": "low",
                    "description": text,
                    "remediation": "Review the observation and validate if exposure is expected.",
                    "metadata": {"line": text},
                }
            )

    return {
        "findings": findings,
        "count": len(findings),
        "joomla_version": version,
    }
