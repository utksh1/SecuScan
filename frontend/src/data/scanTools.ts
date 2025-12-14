export type RiskLevel = 'passive' | 'active' | 'aggressive'
export type PresetCompatibility = 'quick-recon' | 'deep-scan' | 'both' | 'none'

export interface ScanTool {
    id: string
    name: string
    purpose: string
    riskLevel: RiskLevel
    presetCompatibility: PresetCompatibility
    requiresConsent: boolean
    category: string
    subcategory?: string
    disabled?: boolean
    disabledReason?: string
}

export const scanTools: ScanTool[] = [
    // QUICK START
    { id: 'network-scanner', name: 'Network Scanner', purpose: 'Scan network hosts and services', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'quick-start' },
    { id: 'website-scanner', name: 'Website Scanner', purpose: 'Comprehensive web application scan', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'quick-start' },
    { id: 'url-fuzzer', name: 'URL Fuzzer', purpose: 'Discover hidden paths and files', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'quick-start' },
    { id: 'api-scanner', name: 'API Scanner', purpose: 'Test API endpoints and security', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'quick-start' },
    { id: 'whois-lookup', name: 'Whois Lookup', purpose: 'Domain registration information', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'quick-start' },
    { id: 'website-recon', name: 'Website Recon', purpose: 'Passive website reconnaissance', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'quick-start' },

    // RECON TOOLS - Web Recon
    { id: 'google-dorking', name: 'Google Dorking', purpose: 'Search engine reconnaissance', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'recon', subcategory: 'web' },
    { id: 'website-recon-2', name: 'Website Recon', purpose: 'Passive website analysis', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'recon', subcategory: 'web' },
    { id: 'url-fuzzer-2', name: 'URL Fuzzer', purpose: 'Directory and file discovery', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'recon', subcategory: 'web' },
    { id: 'waf-detection', name: 'WAF Detection', purpose: 'Detect web application firewall', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'recon', subcategory: 'web' },
    { id: 'people-email-discovery', name: 'People / Email Discovery', purpose: 'Find email addresses and contacts', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'recon', subcategory: 'web' },

    // RECON TOOLS - Network Recon
    { id: 'domain-finder', name: 'Domain Finder', purpose: 'Discover related domains', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'recon', subcategory: 'network' },
    { id: 'subdomain-finder', name: 'Subdomain Finder', purpose: 'Enumerate subdomains', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'recon', subcategory: 'network' },
    { id: 'virtual-host-finder', name: 'Virtual Host Finder', purpose: 'Discover virtual hosts', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'recon', subcategory: 'network' },
    { id: 'port-scanner', name: 'Port Scanner', purpose: 'Scan network ports', riskLevel: 'active', presetCompatibility: 'both', requiresConsent: false, category: 'recon', subcategory: 'network' },

    // VULNERABILITY SCANNERS - Web
    { id: 'website-scanner-vuln', name: 'Website Scanner', purpose: 'Web vulnerability assessment', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'api-scanner-vuln', name: 'API Scanner', purpose: 'API security testing', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'wordpress-scanner', name: 'WordPress Scanner', purpose: 'WordPress security audit', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'drupal-scanner', name: 'Drupal Scanner', purpose: 'Drupal security audit', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'joomla-scanner', name: 'Joomla Scanner', purpose: 'Joomla security audit', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'sharepoint-scanner', name: 'SharePoint Scanner', purpose: 'SharePoint security testing', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },

    // VULNERABILITY SCANNERS - Network & Cloud
    { id: 'network-scanner-vuln', name: 'Network Scanner', purpose: 'Network vulnerability scan', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'vulnerability', subcategory: 'network' },
    { id: 'credential-hygiene', name: 'Credential Hygiene', purpose: 'Check credential security', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'network' },
    { id: 'ssl-tls-scanner', name: 'SSL/TLS Scanner', purpose: 'TLS configuration audit', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'vulnerability', subcategory: 'network' },
    { id: 'cloud-scanner', name: 'Cloud Scanner', purpose: 'Cloud infrastructure security', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'network', disabled: true, disabledReason: 'UI-ready, backend pending' },
    { id: 'kubernetes-scanner', name: 'Kubernetes Scanner', purpose: 'K8s security assessment', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'network', disabled: true, disabledReason: 'UI-ready, backend pending' },

    // EXPLOIT DETECTION (Safe Mode)
    { id: 'cve-validation', name: 'CVE Validation', purpose: 'Non-destructive CVE checks', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'sqli-detection', name: 'SQL Injection Detection', purpose: 'Detect SQLi vulnerabilities (no extraction)', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'xss-detection', name: 'XSS Detection', purpose: 'Detect XSS reflection points', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'subdomain-takeover', name: 'Subdomain Takeover Detection', purpose: 'Check for takeover risks', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'secret-scanner', name: 'Secret Exposure Scanner', purpose: 'Find exposed API keys and secrets', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'http-logger', name: 'HTTP Request Logger', purpose: 'Log and analyze HTTP traffic', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },

    // UTILITIES
    { id: 'icmp-ping', name: 'ICMP Ping', purpose: 'Basic connectivity test', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'utils' },
    { id: 'whois-lookup-util', name: 'Whois Lookup', purpose: 'Domain information', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'utils' },

    // AUTOMATION / ROBOTS
    { id: 'quick-recon-preset', name: 'Quick Recon Preset', purpose: 'Fast passive reconnaissance', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'robots' },
    { id: 'deep-scan-preset', name: 'Deep Scan Preset', purpose: 'Comprehensive active scanning', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: false, category: 'robots' },
    { id: 'custom-workflow', name: 'Custom Workflow', purpose: 'Build custom scan workflows', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'robots', disabled: true, disabledReason: 'UI-ready, backend pending' },
]

export function getToolsByCategory(category: string, subcategory?: string): ScanTool[] {
    return scanTools.filter(tool => {
        if (subcategory) {
            return tool.category === category && tool.subcategory === subcategory
        }
        return tool.category === category
    })
}

export function getToolById(id: string): ScanTool | undefined {
    return scanTools.find(tool => tool.id === id)
}

export const tabCategories = [
    { id: 'quick-start', name: 'Quick Start' },
    { id: 'recon', name: 'Recon Tools' },
    { id: 'vulnerability', name: 'Vulnerability Scanners' },
    { id: 'exploit', name: 'Exploit Detection' },
    { id: 'utils', name: 'Utils' },
    { id: 'robots', name: 'Robots' },
]
