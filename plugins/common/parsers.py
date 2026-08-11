"""Shared parser utilities for plugins."""

def parse_recon_output(output: str, tool_name: str, max_lines: int = 200) -> dict:
    """Parse line-based recon tool output (amass, subfinder, httpx, katana)."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings = []
    for line in lines[:max_lines]:
        normalized = line.lower()
        severity = "low" if any(k in normalized for k in ["vuln", "vulnerable", "exposed", "open", "found", "detected", "alive"]) else "info"
        findings.append({
            "title": f"{tool_name} Observation",
            "category": "Recon",
            "severity": severity,
            "description": line,
            "remediation": "Review discovery output and validate scope and exposure.",
            "metadata": {"raw_line": line}
        })
    return {"findings": findings, "count": len(findings), "items": lines[:max_lines]}


def parse_generic_output(output: str, tool_name: str, max_lines: int = 200) -> dict:
    """Parse generic line-based tool output (sqli_exploiter, xss_exploiter, subdomain_takeover)."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings = []
    for line in lines[:max_lines]:
        normalized = line.lower()
        severity = "high" if any(k in normalized for k in ["vuln", "vulnerable", "exploit", "injection", "takeover"]) else "medium" if any(k in normalized for k in ["potential", "possible", "suspect"]) else "info"
        findings.append({
            "title": f"{tool_name} Finding",
            "category": "Vulnerability",
            "severity": severity,
            "description": line,
            "remediation": "Investigate and remediate identified vulnerabilities.",
            "metadata": {"raw": line}
        })
    return {"findings": findings, "count": len(findings)}


def parse_scanner_output(output: str, tool_name: str, max_lines: int = 200) -> dict:
    """Parse scanner output (api_scanner, cloud_scanner, fuzzer, iac_scanner, kubernetes_scanner, cloud_storage_auditor)."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings = []
    for line in lines[:max_lines]:
        normalized = line.lower()
        severity = "high" if any(k in normalized for k in ["critical", "high", "severe", "vuln"]) else "medium" if any(k in normalized for k in ["medium", "warn", "misconfigur"]) else "low" if any(k in normalized for k in ["low", "info", "note"]) else "info"
        findings.append({
            "title": f"{tool_name} Finding",
            "category": "Security",
            "severity": severity,
            "description": line,
            "remediation": "Review and address security findings.",
            "metadata": {"raw": line}
        })
    return {"findings": findings, "count": len(findings)}


def parse_line_based_output(output: str, tool_name: str, max_lines: int = 300) -> dict:
    """Parse line-based scan output (spider, sitemap_gen, crawler, waf_detector, http_request_logger)."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    findings = []
    for line in lines[:max_lines]:
        normalized = line.lower()
        severity = "high" if any(k in normalized for k in ["critical", "exploit", "injection", "compromised"]) else "low" if any(k in normalized for k in ["open", "found", "vuln", "warning", "detected", "exposed"]) else "info"
        findings.append({
            "title": "Recon/Scan Observation",
            "category": "Security Scan",
            "severity": severity,
            "description": line,
            "remediation": "Review scan output and validate findings before remediation planning.",
            "metadata": {"raw": line}
        })
    return {"findings": findings, "count": len(findings), "items": lines[:max_lines]}
