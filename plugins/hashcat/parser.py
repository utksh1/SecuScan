from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses Hashcat output.
    Looks for the cracked hash list.
    """
    findings = []
    lines = raw_output.strip().split("\n")
    
    for line in lines:
        if ":" in line and not line.startswith("["): # Simple heuristic for cracked hashes
            parts = line.split(":")
            findings.append({
                "type": "cracked_password",
                "title": "Password Cracked",
                "description": f"Hash cracked: {parts[0]} -> {parts[-1]}",
                "severity": "critical",
                "metadata": {"hash": parts[0], "password": parts[-1]}
            })
            
    return findings if findings else [{"type": "info", "title": "No Passwords Cracked", "description": "Hashcat finished without finding any matches.", "severity": "info"}]
