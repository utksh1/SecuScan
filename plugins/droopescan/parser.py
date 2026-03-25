import json
from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses DroopeScan JSON output into structured findings.
    """
    try:
        data = json.loads(raw_output)
        findings = []
        
        for category, items in data.items():
            if not items:
                continue
                
            for item in items:
                title = item.get("description", f"Discovered {category}")
                findings.append({
                    "type": "discovery",
                    "title": f"DroopeScan: {category.capitalize()}",
                    "description": title,
                    "severity": "low" if category != "vulnerabilities" else "high",
                    "metadata": item
                })
                
        return findings
    except Exception as e:
        # Fallback for text output if JSON fails
        lines = raw_output.strip().split("\n")
        findings = []
        for line in lines:
            if "[+]" in line:
                findings.append({
                    "type": "discovery",
                    "title": "DroopeScan Finding",
                    "description": line.replace("[+]", "").strip(),
                    "severity": "low"
                })
        return findings if findings else [{"type": "info", "title": "No Findings", "description": "DroopeScan completed with no structured findings.", "severity": "info"}]
