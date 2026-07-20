from typing import Any, Dict, List


def parse(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings: List[Dict[str, Any]] = []

    for line in lines[:300]:
        severity = "info"
        low_line = line.lower()
        if any(keyword in low_line for keyword in ["open", "found", "vuln", "warning", "detected", "exposed"]):
            severity = "low"
        if any(keyword in low_line for keyword in ["critical", "exploit", "injection", "compromised"]):
            severity = "high"

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
        "items": lines[:300],
    }
