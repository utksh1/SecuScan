import re
from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Nmap standard output.
    """
    findings = []
    ports = []
    services = []
    os_info = "Unknown"
    
    # Extract OS if present
    os_match = re.search(r"OS details: (.*)", output)
    if os_match:
        os_info = os_match.group(1).strip()
    
    # Regex for open ports: 80/tcp open http [version]
    port_pattern = re.compile(r"(\d+)/(tcp|udp)\s+open\s+([\w-]+)(?:\s+(.*))?")
    
    for match in port_pattern.finditer(output):
        port_str, proto, service, version = match.groups()
        port_val = int(port_str)
        ports.append(port_val)
        services.append(service)
        
        # High-risk ports (classic examples)
        high_risk = {21, 22, 23, 139, 445, 3306, 3389, 5432, 6379}
        severity = "info"
        if port_val in high_risk:
            severity = "low" # Still just "open port", but more interesting
            
        title = f"Open Port: {port_str}/{proto} ({service})"
        desc = f"Port {port_str} is open and running {service}."
        if version:
            desc += f" Version detected: {version}"
            
        findings.append({
            "title": title,
            "category": "Network Service",
            "severity": severity,
            "description": desc,
            "remediation": f"Verify if {service} on port {port_str} is required to be exposed. Ensure it is patched and uses strong authentication.",
            "proof": f"{proto} port {port_str} is OPEN",
            "metadata": {
                "port": port_val,
                "protocol": proto,
                "service": service,
                "version": version or "unknown"
            }
        })

    # Look for common vulnerabilities (if -sC was used)
    # This is a very basic heuristic; a real parser would parse XML/NSE output
    if "VULNERABLE" in output or "Exploit" in output:
        findings.append({
            "title": "Potential Vulnerability/Exploit Detected",
            "category": "Vulnerability",
            "severity": "high",
            "description": "Nmap NSE script or version matching indicated a potential vulnerability. See raw output for details.",
            "remediation": "Investigate the specific service version and NSE script results. Apply necessary patches or configuration changes.",
            "proof": "Heuristic match in Nmap output for 'VULNERABLE' or 'Exploit'"
        })
            
    return {
        "findings": findings,
        "open_ports": sorted(list(set(ports))),
        "services": sorted(list(set(services))),
        "os": os_info
    }
