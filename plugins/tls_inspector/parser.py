import re
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse OpenSSL s_client output for TLS details.
    """
    findings = []
    metadata = {}
    
    # Extract Cipher
    if match := re.search(r"Cipher\s+:\s+(.*)", output):
        metadata["cipher"] = match.group(1).strip()
        
    # Extract Protocol
    if match := re.search(r"Protocol\s+:\s+(.*)", output):
        metadata["protocol"] = match.group(1).strip()
        if "TLSv1.0" in metadata["protocol"] or "TLSv1.1" in metadata["protocol"]:
            findings.append({
                "title": f"Weak TLS Protocol: {metadata['protocol']}",
                "category": "Cryptography",
                "severity": "medium",
                "description": f"The server supports {metadata['protocol']}, which is considered weak and deprecated.",
                "remediation": "Disable TLS 1.0/1.1 and enable TLS 1.2 or 1.3."
            })

    # Extract Certificate info
    if "BEGIN CERTIFICATE" in output:
        metadata["has_certificate"] = True
    
    if "Verify return code: 0 (ok)" in output:
        metadata["certificate_verified"] = True
    else:
        metadata["certificate_verified"] = False
        findings.append({
            "title": "SSL Certificate Validation Failed",
            "category": "Cryptography",
            "severity": "medium",
            "description": "The SSL certificate could not be verified by OpenSSL. This could indicate a self-signed certificate, an expired certificate, or a missing chain.",
            "remediation": "Ensure a valid, trusted certificate is installed and the full chain is provided."
        })

    return {
        "findings": findings,
        "metadata": metadata
    }
