import re
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse HTTP header output for security insights.
    """
    findings = []
    headers = {}
    techs = []
    
    # Extract headers
    for line in output.split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            headers[key.strip().lower()] = val.strip()

    # Information Disclosure
    if server := headers.get("server"):
        techs.append(server)
        findings.append({
            "title": f"Server Banner: {server}",
            "severity": "low",
            "category": "Information Disclosure",
            "description": f"The 'Server' header is disclosing banner information: {server}.",
            "remediation": "Configure the web server to suppress or genericize the Server header."
        })
        
    if powered_by := headers.get("x-powered-by"):
        techs.append(powered_by)
        findings.append({
            "title": f"X-Powered-By Disclosure: {powered_by}",
            "severity": "low",
            "category": "Information Disclosure",
            "description": f"The 'X-Powered-By' header is disclosing technology details: {powered_by}.",
            "remediation": "Disable the X-Powered-By header in application or server config."
        })

    # Missing Security Headers
    security_headers = {
        "x-frame-options": ("Missing X-Frame-Options Header", "The lack of X-Frame-Options makes the site vulnerable to clickjacking."),
        "x-content-type-options": ("Missing X-Content-Type-Options Header", "Without this header set to 'nosniff', the browser may try to MIME-sniff the content, potentially executing malicious code."),
        "content-security-policy": ("Missing Content-Security-Policy Header", "CSP helps mitigate XSS and other injection attacks. It is currently missing."),
        "strict-transport-security": ("Missing Strict-Transport-Security Header", "HSTS should be enabled to force HTTPS connections.")
    }
    
    for hname, (title, desc) in security_headers.items():
        if hname not in headers:
            findings.append({
                "title": title,
                "severity": "medium",
                "category": "Security Headers",
                "description": desc,
                "remediation": f"Implement the {hname} header in the web server configuration."
            })
            
    return {
        "findings": findings,
        "technologies": sorted(list(set(techs))),
        "headers": headers
    }
