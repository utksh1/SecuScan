from typing import Any, Dict, List


def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    matches: List[Dict[str, str]] = []

    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue

        parts = text.split()
        rule = parts[0] if parts else "unknown_rule"
        file_path = parts[-1] if len(parts) > 1 else "unknown_target"
        matches.append({"rule": rule, "path": file_path})

        findings.append(
            {
                "title": f"YARA Match: {rule}",
                "category": "Binary Forensics",
                "severity": "high",
                "description": f"YARA rule '{rule}' matched target artifact '{file_path}'.",
                "remediation": "Quarantine and investigate matched artifacts before restoring to production environments.",
                "metadata": {"rule": rule, "path": file_path, "raw": text},
            }
        )

    return {
        "findings": findings,
        "count": len(findings),
        "matches": matches,
    }
