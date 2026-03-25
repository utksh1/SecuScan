import re
from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses Metasploit console output.
    Looks for session openings.
    """
    findings = []
    
    # Check for session openings
    session_match = re.search(r"Command shell session (\d+) opened", raw_output)
    meterpreter_match = re.search(r"Meterpreter session (\d+) opened", raw_output)
    
    if session_match:
        findings.append({
            "type": "exploitation_success",
            "title": "Exploit Successful: Session Opened",
            "description": f"Metasploit session {session_match.group(1)} was successfully opened.",
            "severity": "critical"
        })
        
    if meterpreter_match:
        findings.append({
            "type": "exploitation_success",
            "title": "Exploit Successful: Meterpreter Opened",
            "description": f"Meterpreter session {meterpreter_match.group(1)} was successfully opened.",
            "severity": "critical"
        })
        
    if not findings and "Exploit failed" in raw_output:
        findings.append({
            "type": "exploitation_failure",
            "title": "Exploit Failed",
            "description": "The exploit attempt did not result in a session.",
            "severity": "info"
        })
        
    if not findings:
        findings.append({
            "type": "info",
            "title": "Metasploit Finished",
            "description": "Execution completed. Check raw logs for console output.",
            "severity": "info"
        })
        
    return findings
