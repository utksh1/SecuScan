import re
from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse DNSRecon output.
    """
    findings = []
    records = []
    
    # Simple regex to find common record types: [*] TYPE value
    record_pattern = re.compile(r"\[\*\]\s+([A-Z]+)\s+(.*)")
    
    for match in record_pattern.finditer(output):
        rec_type, value = match.groups()
        records.append({"type": rec_type, "value": value})
        
        findings.append({
            "title": f"DNS Record Found: {rec_type}",
            "category": "DNS Configuration",
            "severity": "info",
            "description": f"Found {rec_type} record: {value}",
            "remediation": "Review DNS records for misconfigurations or unintended information exposure.",
            "metadata": {
                "type": rec_type,
                "value": value
            }
        })
        
    if "Zone Transfer Successful" in output:
        findings.append({
            "title": "Critical: DNS Zone Transfer Successful",
            "category": "DNS Misconfiguration",
            "severity": "critical",
            "description": "The DNS server allowed a full zone transfer (AXFR). This exposes all internal DNS records.",
            "remediation": "Restrict AXFR transfers to authorized slave servers only."
        })
            
    return {
        "findings": findings,
        "count": len(records),
        "records": records
    }
