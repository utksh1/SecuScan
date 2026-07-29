"""
Curated scan templates for common security workflows.
Each template defines a scan configuration with plugin, preset, inputs, and description.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ScanTemplate(BaseModel):
    id: str
    name: str
    description: str
    category: str  # "reconnaissance", "vulnerability", "web", "network", "compliance"
    complexity: str  # "basic", "intermediate", "advanced"
    estimated_duration: str  # e.g. "5-10 min", "30-60 min"
    plugin_id: str
    preset: Optional[str] = None
    inputs: Dict[str, Any] = {}
    execution_context: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    icon: str = "scan"  # material-symbols-outlined icon name

# Curated templates
TEMPLATES: List[ScanTemplate] = [
    ScanTemplate(
        id="quick-port-scan",
        name="Quick Port Scan",
        description="Scan top 1000 ports on a target to identify open services and entry points.",
        category="network",
        complexity="basic",
        estimated_duration="2-5 min",
        plugin_id="port_scanner",
        preset="quick",
        inputs={},
        tags=["recon", "ports", "quick"],
        icon="radar",
    ),
    ScanTemplate(
        id="full-port-scan",
        name="Full Port Enumeration",
        description="Comprehensive port scan of all 65535 ports with service fingerprinting and OS detection.",
        category="network",
        complexity="intermediate",
        estimated_duration="15-30 min",
        plugin_id="port_scanner",
        preset="full",
        inputs={},
        tags=["recon", "ports", "comprehensive"],
        icon="grid_view",
    ),
    ScanTemplate(
        id="web-vulnerability-scan",
        name="Web Application Vulnerability Scan",
        description="Automated web vulnerability assessment including XSS, SQLi, CSRF, and misconfigurations.",
        category="web",
        complexity="intermediate",
        estimated_duration="10-30 min",
        plugin_id="web_scanner",
        preset="balanced",
        inputs={},
        tags=["web", "vulnerabilities", "owasp"],
        icon="language",
    ),
    ScanTemplate(
        id="full-web-audit",
        name="Deep Web Application Audit",
        description="Thorough web application security audit with aggressive crawling, all vulnerability checks, and evidence collection.",
        category="web",
        complexity="advanced",
        estimated_duration="30-60 min",
        plugin_id="web_scanner",
        preset="aggressive",
        inputs={},
        tags=["web", "deep", "owasp", "comprehensive"],
        icon="travel_explore",
    ),
    ScanTemplate(
        id="recon-subdomain",
        name="Subdomain Enumeration",
        description="Discover subdomains and related targets through passive DNS, certificates, and search engines.",
        category="reconnaissance",
        complexity="basic",
        estimated_duration="3-8 min",
        plugin_id="recon_scanner",
        preset="subdomain_enum",
        inputs={},
        tags=["recon", "subdomains", "passive"],
        icon="dns",
    ),
    ScanTemplate(
        id="recon-full",
        name="Full Reconnaissance Suite",
        description="Comprehensive recon including subdomains, technologies, WHOIS, DNS records, and OSINT data.",
        category="reconnaissance",
        complexity="advanced",
        estimated_duration="20-45 min",
        plugin_id="recon_scanner",
        preset="full_recon",
        inputs={},
        tags=["recon", "osint", "comprehensive"],
        icon="travel_explore",
    ),
    ScanTemplate(
        id="api-security-scan",
        name="API Security Assessment",
        description="Test REST/GraphQL APIs for common vulnerabilities including auth bypasses, injection, and rate limiting issues.",
        category="web",
        complexity="intermediate",
        estimated_duration="10-20 min",
        plugin_id="api_scanner",
        preset="default",
        inputs={},
        tags=["api", "rest", "graphql", "security"],
        icon="api",
    ),
    ScanTemplate(
        id="vulnerability-scan",
        name="Network Vulnerability Assessment",
        description="Scan network targets for known CVEs, misconfigurations, and common vulnerabilities.",
        category="vulnerability",
        complexity="intermediate",
        estimated_duration="15-40 min",
        plugin_id="network_scanner",
        preset="balanced",
        inputs={},
        tags=["cve", "vulnerabilities", "network"],
        icon="bug_report",
    ),
    ScanTemplate(
        id="xss-validation",
        name="XSS Validation & Exploit Testing",
        description="Validate XSS findings with proof-of-concept generation and browser-based execution confirmation.",
        category="vulnerability",
        complexity="advanced",
        estimated_duration="5-15 min",
        plugin_id="xss_exploiter",
        preset="default",
        inputs={},
        tags=["xss", "validation", "exploit"],
        icon="javascript",
    ),
    ScanTemplate(
        id="zap-scan",
        name="OWASP ZAP Automated Scan",
        description="Leverage OWASP ZAP for comprehensive web application security testing with both passive and active scanning.",
        category="web",
        complexity="intermediate",
        estimated_duration="20-60 min",
        plugin_id="zap_scanner",
        preset="default",
        inputs={},
        tags=["zap", "owasp", "web", "automated"],
        icon="security",
    ),
    ScanTemplate(
        id="quick-external-audit",
        name="Quick External Security Audit",
        description="Rapid external-facing security check covering open ports, basic web checks, and common exposures.",
        category="network",
        complexity="basic",
        estimated_duration="5-10 min",
        plugin_id="port_scanner",
        preset="quick",
        inputs={},
        tags=["external", "quick", "audit"],
        icon="shield",
    ),
    ScanTemplate(
        id="pci-recon-scan",
        name="PCI DSS Reconnaissance Scan",
        description="Discovery scan tailored for PCI DSS compliance, identifying all live services and entry points in scope.",
        category="compliance",
        complexity="intermediate",
        estimated_duration="10-20 min",
        plugin_id="recon_scanner",
        preset="full_recon",
        inputs={},
        tags=["pci", "compliance", "recon"],
        icon="verified",
    ),
]


def get_templates() -> List[Dict[str, Any]]:
    return [t.model_dump() for t in TEMPLATES]


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    for t in TEMPLATES:
        if t.id == template_id:
            return t.model_dump()
    return None


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    return [t.model_dump() for t in TEMPLATES if t.category == category]
