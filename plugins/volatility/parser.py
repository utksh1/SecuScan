from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses Volatility3 output. 
    Usually returns a text table.
    """
    findings = []
    lines = raw_output.strip().split("\n")
    
    if len(lines) < 2:
        return [{"type": "info", "title": "Empty Output", "description": "Volatility returned no results.", "severity": "info"}]
        
    # Simple summary of the first 20 lines as findings
    header = lines[0]
    count = 0
    for line in lines[1:]: 
        if count >= 20:
            break
        if line.strip():
            findings.append({
                "type": "forensics_artifact",
                "title": "Volatility Artifact",
                "description": line.strip(),
                "severity": "medium",
                "metadata": {"header": header, "data": line}
            })
            count += 1
            
    if len(lines) > 21:
        findings.append({
            "type": "info",
            "title": "More Artifacts Available",
            "description": f"Truncated {len(lines) - 21} additional lines. Refer to raw logs.",
            "severity": "info"
        })
        
    return findings
