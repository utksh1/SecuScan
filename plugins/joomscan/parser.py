import re
from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses JoomScan text output into structured findings.
    """
    findings = []
    
    # Simple regex parsing for JoomScan output
    patterns = {
        "Firewall": r"\[\+\] Firewall Detector: (.*)",
        "Version": r"\[\+\] Core Joomla Version: (.*)",
        "Vulnerability": r"\[\+\] Vulnerable to: (.*)",
        "Interesting": r"\[\+\] (.*)"
    }
    
    lines = raw_output.split("\n")
    for line in lines:
        for cat, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                val = match.group(1).strip()
                severity = "high" if "Vulnerability" in cat else "low"
                findings.append({
                    "type": cat.lower(),
                    "title": f"JoomScan: {cat}",
                    "description": val,
                    "severity": severity
                })
                break
                
    return findings if findings else [{"type": "info", "title": "JoomScan Output", "description": "Refer to raw output for details.", "severity": "info"}]
