from typing import Any, Dict, List


def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    lines = [line.strip() for line in output.splitlines() if line.strip()]

    if not lines:
        return {"findings": [], "count": 0}

    header = lines[0]
    rows = lines[1:]

    for row in rows[:25]:
        findings.append(
            {
                "title": "Volatility Artifact",
                "category": "Memory Forensics",
                "severity": "medium",
                "description": row,
                "remediation": "Validate suspicious process/module artifacts against trusted baselines.",
                "metadata": {"header": header, "row": row},
            }
        )

    if len(rows) > 25:
        findings.append(
            {
                "title": "Volatility Output Truncated",
                "category": "Memory Forensics",
                "severity": "info",
                "description": f"Showing first 25 rows out of {len(rows)}.",
                "remediation": "Review raw output for complete artifact list.",
                "metadata": {"total_rows": len(rows)},
            }
        )

    return {
        "findings": findings,
        "count": len(findings),
    }
