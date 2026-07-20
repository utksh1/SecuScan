import re
from typing import Any, Dict, List


PAYLOAD_RE = re.compile(r"(?i)payload:\s*(.+)")
DB_HEADER_RE = re.compile(r"(?i)available databases")


def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    payloads = [match.group(1).strip() for match in PAYLOAD_RE.finditer(output)]

    for payload in payloads[:5]:
        findings.append(
            {
                "title": "SQL Injection Found",
                "category": "Injection",
                "severity": "critical",
                "description": f"Potential injectable vector detected. Example payload: {payload}",
                "remediation": "Use parameterized queries, strict input validation, and least-privilege DB users.",
                "metadata": {"payload": payload},
            }
        )

    lines = output.splitlines()
    db_values: List[str] = []
    for idx, line in enumerate(lines):
        if DB_HEADER_RE.search(line):
            for candidate in lines[idx + 1 :]:
                c = candidate.strip()
                if not c:
                    break
                if c.startswith("["):
                    continue
                db_values.append(c)
            break

    if db_values:
        findings.append(
            {
                "title": "Databases Enumerated",
                "category": "Injection",
                "severity": "high",
                "description": f"Discovered databases: {', '.join(db_values)}",
                "remediation": "Restrict database metadata exposure and patch injectable endpoints.",
                "metadata": {"databases": db_values},
            }
        )

    if not findings and "not injectable" in output.lower():
        findings.append(
            {
                "title": "No SQLi Detected",
                "category": "Injection",
                "severity": "info",
                "description": "The target did not appear injectable in this run.",
                "remediation": "Continue validating with authenticated and context-specific test cases.",
                "metadata": {},
            }
        )

    return {
        "findings": findings,
        "count": len(findings),
    }
