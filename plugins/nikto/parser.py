import json
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Nikto JSON output from stdout.
    Note: Nikto often includes some headers/trailers before/after JSON.
    """
    findings = []
    
    # Try to find the JSON part
    try:
        # If the output is pure JSON
        data = json.loads(output)
    except json.JSONDecodeError:
        # Try to find a JSON block starting with { and ending with }
        import re
        match = re.search(r'(\{.*\})', output, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                return {"findings": [], "raw": output}
        else:
            return {"findings": [], "raw": output}

    # Nikto JSON structure: {"vulnerabilities": [...]}
    vulns = data.get("vulnerabilities", [])
    for vuln in vulns:
        findings.append({
            "title": vuln.get("msg", "Nikto Finding"),
            "category": "Web Vulnerability",
            "severity": "medium", # Nikto doesn't always provide severity, defaulting to medium
            "description": f"OSVDB ID: {vuln.get('osvdb', 'N/A')}. {vuln.get('msg')}",
            "remediation": "Update the affected software or configuration.",
            "metadata": {
                "osvdb": vuln.get("osvdb"),
                "url": vuln.get("url"),
                "method": vuln.get("method")
            }
        })
            
    return {"findings": findings}
