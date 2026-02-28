from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Subfinder output (one subdomain per line).
    """
    lines = output.strip().split("\n")
    subdomains = [line.strip() for line in lines if line.strip()]
    
    findings = []
    for sub in subdomains:
        findings.append({
            "title": f"Subdomain Discovered: {sub}",
            "category": "Subdomain",
            "severity": "info",
            "description": f"Discovered subdomain: {sub}",
            "remediation": "Verify if this subdomain is intended to be public and secure.",
            "metadata": {
                "subdomain": sub
            }
        })
        
    return {
        "findings": findings,
        "count": len(subdomains),
        "subdomains": subdomains
    }
