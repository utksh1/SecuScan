import json
from typing import Any, Dict, List


def _make_finding(title: str, category: str, severity: str, description: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "severity": severity,
        "description": description,
        "remediation": "Review Drupal exposure and update vulnerable modules/themes.",
        "metadata": metadata,
    }

def _map_severity(key: str) -> str:
    key = key.lower()

    if any(token in key for token in ("critical", "vuln")):
        return "high"

    if any(token in key for token in ("warning", "interesting", "exposed")):
        return "medium"

    return "low"

def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []

    try:
        data = json.loads(output)
    except Exception:
        for line in output.splitlines():
            text = line.strip()
            if not text:
                continue
            findings.append(
                _make_finding(
                    title="DroopeScan Finding",
                    category="CMS Security",
                    severity="low",
                    description=text,
                    metadata={"line": text},
                )
            )
        return {"findings": findings, "count": len(findings)}

    if isinstance(data, dict):
        for key, values in data.items():
            if not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, dict):
                    continue
                description = str(item.get("description") or item.get("url") or item)
                severity = _map_severity(key)
                findings.append(
                    _make_finding(
                        title=f"DroopeScan {key}",
                        category=(
                            "CMS Vulnerability"
                            if severity in {"high", "medium"}
                            else "CMS Discovery"
                        ),
                        severity=severity,
                        description=description,
                        metadata=item,
                    )
                )

    return {
        "findings": findings,
        "count": len(findings),
    }
