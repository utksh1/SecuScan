from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    findings = []
    hosts = []
    
    lines = output.strip().split("\n")
    for line in lines:
        if line.startswith("UP:"):
            parts = line[3:].strip().split(" - ")
            ip = parts[0]
            mac = parts[1] if len(parts) > 1 else "Unknown"
            
            hosts.append({"ip": ip, "mac": mac})
            findings.append({
                "title": f"Live Host Discovered: {ip}",
                "category": "Network Discovery",
                "severity": "info",
                "description": f"Host {ip} is active on the network. MAC Address: {mac}",
                "remediation": "Review if this host is authorized to be on the network.",
                "metadata": {
                    "ip": ip,
                    "mac": mac
                }
            })
            
    return {
        "findings": findings,
        "count": len(hosts),
        "hosts": hosts
    }
