from typing import Any, Dict, List


def parse(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]

    alert_lines = [
        line
        for line in lines
        if line.startswith("WARN-NEW:") or line.startswith("FAIL-NEW:")
    ]

    findings: List[Dict[str, Any]] = []

    for line in alert_lines[:300]:
        if line.startswith("FAIL-NEW:"):
            severity = "high"
        elif line.startswith("WARN-NEW:"):
            severity = "low"
        else:
            severity = "info"

        findings.append(
            {
                "title": "Recon/Scan Observation",
                "category": "Security Scan",
                "severity": severity,
                "description": line,
                "remediation": "Review scan output and validate findings before remediation planning.",
                "metadata": {"raw": line},
            }
        )

    return {
        "findings": findings,
        "count": len(findings),
        "items": alert_lines[:300],
    }
