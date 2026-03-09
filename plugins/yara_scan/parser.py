import re
from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses YARA output into structured findings.
    Format usually: rule_name [tags] file_path
    """
    findings = []
    lines = raw_output.strip().split("\n")
    
    for line in lines:
        if not line:
            continue
            
        # Example: mal_rule [malware,evil] /tmp/malware.bin
        parts = line.split(" ", 1)
        if len(parts) >= 2:
            rule_name = parts[0]
            rest = parts[1]
            path = rest.split(" ")[-1]
            
            findings.append({
                "type": "malware_match",
                "title": f"YARA Match: {rule_name}",
                "description": f"Rule '{rule_name}' matched on file: {path}",
                "severity": "critical",
                "metadata": {
                    "rule": rule_name,
                    "file": path,
                    "raw": line
                }
            })
            
    return findings if findings else [{"type": "info", "title": "No YARA Matches", "description": "No rules were triggered on the target.", "severity": "info"}]
