import json
from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Gitleaks JSON report.
    Note: Gitleaks output is usually saved to a file, but we might get it as a string if configured.
    """
    findings = []
    try:
        data = json.loads(output)
        for item in data:
            rule = item.get("RuleID", "Secret Detected")
            file_path = item.get("File", "Unknown")
            line_num = item.get("StartLine", 0)
            
            findings.append({
                "title": f"Secret Leak: {rule} in {file_path}",
                "category": "Credential Leak",
                "severity": "critical",
                "description": f"A potential secret ({rule}) was found in {file_path} at line {line_num}.",
                "remediation": "Revoke the affected credential and update the code to use environment variables or a vault.",
                "metadata": {
                    "rule": rule,
                    "file": file_path,
                    "line": line_num,
                    "offender": item.get("Offender", "****")
                }
            })
    except Exception:
        # If not JSON, maybe it's just a message
        if "No leaks found" in output:
            return {"findings": [], "count": 0}
        
    return {
        "findings": findings,
        "count": len(findings)
    }
