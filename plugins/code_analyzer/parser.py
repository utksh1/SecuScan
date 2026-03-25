import json
from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Bandit JSON output.
    """
    findings = []
    try:
        data = json.loads(output)
        results = data.get("results", [])
        for res in results:
            issue_text = res.get("issue_text", "Unknown issue")
            file_path = res.get("filename", "Unknown")
            line_no = res.get("line_number", 0)
            severity = res.get("issue_severity", "low").lower()
            confidence = res.get("issue_confidence", "low").lower()
            
            findings.append({
                "title": f"Bandit issue: {issue_text} in {file_path}",
                "category": "Code Security",
                "severity": severity,
                "description": f"Severity: {severity}, Confidence: {confidence}. Found in {file_path} at line {line_no}.",
                "remediation": "Review the affected code and follow secure coding practices.",
                "metadata": {
                    "issue_text": issue_text,
                    "file": file_path,
                    "line": line_no,
                    "test_id": res.get("test_id", "unknown"),
                    "more_info": res.get("more_info", "")
                }
            })
    except Exception:
        pass
        
    return {
        "findings": findings,
        "count": len(findings)
    }
