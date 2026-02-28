import re
from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse WHOIS output using regex for key fields.
    """
    findings = []
    
    # Extract important fields
    registrar = re.search(r"Registrar:\s*(.*)", output, re.IGNORECASE)
    expiry = re.search(r"Registry Expiry Date:\s*(.*)", output, re.IGNORECASE)
    nameservers = re.findall(r"Name Server:\s*(.*)", output, re.IGNORECASE)
    
    summary_data = {
        "registrar": registrar.group(1).strip() if registrar else "Unknown",
        "expiry": expiry.group(1).strip() if expiry else "Unknown",
        "nameservers": [ns.strip() for ns in nameservers]
    }
    
    findings.append({
        "title": f"WHOIS Record for {summary_data['registrar']}",
        "category": "Domain Info",
        "severity": "info",
        "description": f"Registrar: {summary_data['registrar']}\nExpiry: {summary_data['expiry']}\nName Servers: {', '.join(summary_data['nameservers'])}",
        "remediation": "Review domain registration data for accuracy and privacy settings (WHOIS privacy).",
        "metadata": summary_data
    })
    
    return {
        "findings": findings,
        "detail": summary_data
    }
