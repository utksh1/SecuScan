import json
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse ffuf JSON output.
    """
    findings = []
    
    try:
        data = json.loads(output)
        results = data.get("results", [])
        for res in results:
            url = res.get("url")
            status = res.get("status")
            content_length = res.get("length")
            
            findings.append({
                "title": f"Discovered Endpoint: {url}",
                "category": "Information Disclosure",
                "severity": "info" if status >= 200 and status < 300 else "low",
                "description": f"Found an endpoint at {url} with HTTP status {status} and content length {content_length}.",
                "remediation": "Ensure this endpoint does not expose sensitive information or administrative functions.",
                "metadata": {
                    "url": url,
                    "status": status,
                    "content_length": content_length
                }
            })
    except json.JSONDecodeError:
        # Might be partial or text output if ffuf failed
        pass
            
    return {"findings": findings}
