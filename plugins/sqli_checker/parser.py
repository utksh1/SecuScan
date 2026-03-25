import re
from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses SQLi Checker (Ghauri) output.
    """
    findings = []
    
    # Look for injectable parameters
    param_matches = re.findall(r"Payload: (.*)", raw_output)
    db_matches = re.findall(r"available databases \[.*\]:\n(.*?)(?=\n\n|\Z)", raw_output, re.S)
    
    if param_matches:
        count = 0
        for payload in param_matches:
            if count >= 3:
                break
            findings.append({
                "type": "vulnerability",
                "title": "SQL Injection Found",
                "description": f"Target is injectable! Sample payload: {payload}",
                "severity": "critical"
            })
            count += 1
            
    if db_matches:
        dbs = db_matches[0].strip().split("\n")
        findings.append({
            "type": "info",
            "title": "Databases Enumerated",
            "description": f"Found {len(dbs)} databases: {', '.join([d.strip() for d in dbs])}",
            "severity": "medium"
        })
        
    if not findings and ("is not injectable" in raw_output or "does not seem to be injectable" in raw_output):
        findings.append({
            "type": "info",
            "title": "Not Injectable",
            "description": "The target does not appear to be vulnerable to common SQLi patterns.",
            "severity": "info"
        })
        
    return findings if findings else [{"type": "info", "title": "Scan Complete", "description": "Ghauri finished execution.", "severity": "info"}]
