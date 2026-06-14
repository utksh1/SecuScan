import json
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Semgrep JSON output.
    """
    findings = []
    try:
        data = json.loads(output)
        results = data.get("results", [])
        
        # Mapping Semgrep severity to SecuScan severity
        severity_map = {
            "INFO": "info",
            "WARNING": "medium",
            "ERROR": "high"
        }
        
        for res in results:
            check_id = res.get("check_id", "Unknown Rule")
            path = res.get("path", "Unknown Path")
            extra = res.get("extra", {})
            message = extra.get("message", "No message provided")
            semgrep_severity = extra.get("severity", "INFO")
            
            # Map severity
            severity = severity_map.get(semgrep_severity, "low")
            
            # Extract line info
            start_info = res.get("start", {})
            line_no = start_info.get("line", 0)
            
            # Code snippet as evidence
            lines = extra.get("lines", "")
            
            findings.append({
                "title": f"Semgrep issue: {check_id} in {path}",
                "category": "Code Security",
                "severity": severity,
                "description": message,
                "remediation": f"Review rule {check_id} and the affected code snippet.",
                "metadata": {
                    "rule_id": check_id,
                    "file": path,
                    "line": line_no,
                    "evidence": lines,
                    "semgrep_severity": semgrep_severity
                }
            })
    except Exception:
        pass
        
    return {
        "findings": findings,
        "count": len(findings)
    }
