import re
from typing import Any, Dict, List

def parse(output: str) -> Dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings: List[Dict[str, Any]] = []
    open_ports = []
    
    # Regex to capture port/protocol, state, and service
    # Example: 80/tcp open http
    port_re = re.compile(r"(\d+)/(tcp|udp)\s+(\w+)\s+(.+)")
    
    for line in lines:
        if match := port_re.search(line):
            port, proto, state, service = match.groups()
            if state.lower() == "open":
                open_ports.append({
                    "port": port,
                    "protocol": proto,
                    "service": service
                })

    # Summary counts
    total_open = len(open_ports)
    
    if total_open > 0:
        # Determine highest severity based on sensitive ports
        # 21 (FTP), 23 (Telnet), 3389 (RDP), 445 (SMB), 3306 (MySQL)
        critical_ports = ["21", "23", "445", "3389", "3306", "5432"]
        highest_severity = "low"
        
        ports_desc = []
        for p in open_ports:
            status = f"{p['port']}/{p['protocol']} ({p['service']})"
            ports_desc.append(status)
            if p["port"] in critical_ports:
                highest_severity = "medium"

        # Create one consolidated major finding
        findings.append({
            "title": "Open Network Services Detected",
            "category": "Insecure Surface",
            "severity": highest_severity,
            "description": f"Target has {total_open} active network entry points: " + ", ".join(ports_desc),
            "remediation": "Audit the necessity of these services. Enforce firewall restrictions and ensure all listening services are patched and logically isolated.",
            "metadata": {"open_ports": open_ports},
        })

    # Basic info for the execution trace
    if not open_ports and "Host is up" in output:
        findings.append({
            "title": "Host Status: Active",
            "category": "Recon",
            "severity": "info",
            "description": "Target host responded to probes but no open ports were identified in the scanned range.",
            "remediation": "Perform a deeper scan with --top-ports 1000 or specific port ranges if needed.",
        })

    summary_text = [f"Found {total_open} open ports."]
    if total_open > 0:
        summary_text.append(f"Exposed services: {', '.join([p['service'] for p in open_ports[:5]])}{'...' if total_open > 5 else ''}")

    return {
        "findings": findings,
        "count": len(findings),
        "summary": summary_text,
        "structured": {
            "rows": open_ports,
            "type": "ports",
            "total_count": total_open,
            "host_status": "up" if "host is up" in output.lower() else "unknown"
        }
    }
