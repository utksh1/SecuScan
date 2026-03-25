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
        
        title = f"Open Port: {port_str}/{proto} ({service})"
        desc = f"Port {port_str} is open and running {service}."
        if version:
            desc += f" Version detected: {version}"
            
        findings.append({
            "title": title,
            "category": "Network Service",
            "severity": "low",
            "description": desc,
            "remediation": "Review if this service needs to be exposed to the network.",
            "metadata": {
                "port": port_val,
                "protocol": proto,
                "service": service,
                "version": version or "unknown"
            }
        })

    # Look for common vulnerabilities (if -sC was used)
    if "VULNERABLE" in output:
        # Very basic check for script output indicators
        findings.append({
            "title": "Potential Vulnerability Detected by Nmap Script",
            "category": "Vulnerability",
            "severity": "medium",
            "description": "Nmap NSE script indicated a potential vulnerability. See raw output for details.",
            "remediation": "Review the specific script output and patch the affected service."
        })
            
    return {
        "findings": findings,
        "open_ports": sorted(list(set(ports))),
        "services": sorted(list(set(services))),
        "os": os_info
    }
