from typing import Any, Dict, List


def parse(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings: List[Dict[str, Any]] = []

    for line in lines[:200]:
        normalized = line.lower()
        severity = "info"
        if any(keyword in normalized for keyword in ["vuln", "vulnerable", "exposed", "open", "found", "detected", "alive"]):
            severity = "low"

        findings.append({
            "title": "theHarvester Observation",
            "category": "Recon",
            "severity": severity,
            "description": line,
            "remediation": "Review discovery output and validate scope and exposure.",
            "metadata": {"raw_line": line},
        })

    return {
        "findings": findings,
        "count": len(findings),
        "items": lines[:200],
    }
