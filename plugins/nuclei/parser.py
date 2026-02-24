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
            findings.append({
                "title": data.get("info", {}).get("name", "Nuclei Finding"),
                "category": data.get("type", "vulnerability"),
                "severity": data.get("info", {}).get("severity", "info"),
                "description": data.get("info", {}).get("description", ""),
                "remediation": data.get("info", {}).get("remediation", ""),
                "metadata": {
                    "template_id": data.get("template-id"),
                    "matched_at": data.get("matched-at"),
                    "extracted_results": data.get("extracted-results", []),
                    "curl_command": data.get("curl-command")
                }
            })
        except json.JSONDecodeError:
            # Not JSON, skip (might be info/error logs)
            continue
            
    return {"findings": findings}
