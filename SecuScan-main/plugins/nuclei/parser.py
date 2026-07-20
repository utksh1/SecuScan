import json
import re
from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Nuclei JSON-per-line output.
    """
    findings = []
    
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            info = data.get("info", {})
            findings.append({
                "title": info.get("name", "Nuclei Finding"),
                "category": data.get("type", "vulnerability"),
                "severity": info.get("severity", "info"),
                "description": info.get("description", ""),
                "remediation": info.get("remediation", ""),
                "proof": data.get("curl-command"),
                "cvss": info.get("classification", {}).get("cvss-score"),
                "cve": ", ".join(info.get("classification", {}).get("cve-id", [])) if info.get("classification", {}).get("cve-id") else None,
                "metadata": {
                    "template_id": data.get("template-id"),
                    "matched_at": data.get("matched-at"),
                    "extracted_results": data.get("extracted-results", []),
                }
            })
        except json.JSONDecodeError:
            continue
            
    return {"findings": findings}
