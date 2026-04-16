import re
from typing import Any, Dict, List


SESSION_RE = re.compile(r"(?i)(command shell|meterpreter) session\s+(\d+)\s+opened")
VULN_RE = re.compile(r"(?i)found vulnerability\s*:?\s*(.+)")


def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []

    for match in SESSION_RE.finditer(output):
        session_type = match.group(1)
        session_id = match.group(2)
        findings.append(
            {
                "title": "Metasploit Session Opened",
                "category": "Exploitation",
                "severity": "critical",
                "description": f"{session_type.title()} session {session_id} opened.",
                "remediation": "Treat target as compromised and perform containment and forensic review.",
                "metadata": {"session_type": session_type, "session_id": session_id},
            }
        )

    for match in VULN_RE.finditer(output):
        findings.append(
            {
                "title": "Metasploit Vulnerability Match",
                "category": "Exploitation",
                "severity": "high",
                "description": match.group(1).strip(),
                "remediation": "Patch vulnerable services and verify exploit path is closed.",
                "metadata": {"line": match.group(0)},
            }
        )

    if not findings and "exploit failed" in output.lower():
        findings.append(
            {
                "title": "Metasploit Attempt Failed",
                "category": "Exploitation",
                "severity": "medium",
                "description": "Exploit execution did not open a session.",
                "remediation": "Review module configuration and target reachability.",
                "metadata": {},
            }
        )

    return {
        "findings": findings,
        "count": len(findings),
    }
