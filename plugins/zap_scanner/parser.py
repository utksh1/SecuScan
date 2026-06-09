import json
from typing import Any, Dict, List

SEVERITY_MAP = {
    "high": "high",
    "critical": "critical",
    "medium": "medium",
    "low": "low",
    "info": "info",
}


def parse(output: str) -> Dict[str, Any]:
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, ValueError):
        return {"findings": [], "count": 0, "items": []}

    raw_findings: List[Dict[str, Any]] = data.get("findings", data.get("items", []))
    findings: List[Dict[str, Any]] = []

    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        severity_raw = item.get("severity", "info") or "info"
        severity = SEVERITY_MAP.get(severity_raw.lower(), "info")
        findings.append({
            "title": item.get("title", "Security Observation"),
            "category": "DAST",
            "severity": severity,
            "description": item.get("description", ""),
            "remediation": item.get("remediation", "Review scan output and validate findings before remediation."),
            "metadata": item.get("metadata", {}),
        })

    return {
        "findings": findings,
        "count": len(findings),
        "items": raw_findings,
    }
