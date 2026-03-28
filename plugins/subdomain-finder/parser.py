import re
from typing import Any, Dict, List

def parse(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings: List[Dict[str, Any]] = []
    discovery_rows = []
    
    # Regex to capture subdomain and optionally an IP address following it
    # Expected: "backend.utksh.bar  52.0.200.63" or just "backend.utksh.bar"
    subdomain_re = re.compile(r"([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(\s+[\d\.]+)?")

    for line in lines:
        if match := subdomain_re.search(line):
            subdomain, ip = match.groups()
            ip = ip.strip() if ip else "-"
            
            discovery_rows.append({
                "subdomain": subdomain,
                "ip": ip,
                "service": "Found via Recon",
                "state": "Live"
            })

    total_results = len(discovery_rows)
    
    if total_results > 0:
        findings.append({
            "title": f"Discovery: {total_results} Subdomains Identified",
            "category": "Recon",
            "severity": "info",
            "description": f"Identified {total_results} subdomains for the target. Expand results table for full details.",
            "remediation": "Audit the necessity of these endpoints. Ensure sensitive subdomains (stg, dev, internal) are not publicly exposed.",
            "metadata": {"discovered_count": total_results},
        })

    return {
        "findings": findings,
        "count": len(findings),
        "structured": {
            "rows": discovery_rows,
            "type": "subdomains",
            "total_count": total_results
        }
    }
