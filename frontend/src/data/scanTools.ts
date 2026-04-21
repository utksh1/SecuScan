export type RiskLevel = 'passive' | 'active' | 'aggressive'
export type PresetCompatibility = 'quick-recon' | 'deep-scan' | 'both' | 'none'

export const RECENT_TOOLS_STORAGE_KEY = 'secuscan_recent_tools'
export const RECENT_TOOLS_LIMIT = 6

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
    isQuickStart?: boolean
}

export const scanTools: ScanTool[] = [
    // --- RECONNAISSANCE ---
    { id: 'nmap', name: 'Nmap', purpose: 'Comprehensive network discovery and port scanning', riskLevel: 'active', presetCompatibility: 'both', requiresConsent: true, category: 'recon', isQuickStart: true },
    { id: 'subdomain_discovery', name: 'Subdomain Discovery', purpose: 'Passive and active subdomain enumeration', riskLevel: 'active', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'recon', isQuickStart: true },
    { id: 'dns_enum', name: 'DNS Enumeration', purpose: 'Detailed DNS record analysis and zone transfers', riskLevel: 'active', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'recon' },
    { id: 'http_inspector', name: 'HTTP Inspector', purpose: 'Read-only analysis of web endpoints and headers', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'recon' },
    { id: 'scapy_recon', name: 'Scapy Recon', purpose: 'Low-level network probing and packet crafting', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'recon', subcategory: 'network' },
    
    // --- VULNERABILITY SCANNERS ---
    { id: 'nikto', name: 'Nikto', purpose: 'Comprehensive web server security scanning', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: true, category: 'vulnerability', isQuickStart: true },
    { id: 'wpscan', name: 'WPScan', purpose: 'Specialized WordPress vulnerability auditor', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', isQuickStart: true },
    { id: 'nuclei', name: 'Nuclei', purpose: 'Template-based vulnerability detection at scale', riskLevel: 'active', presetCompatibility: 'both', requiresConsent: true, category: 'vulnerability', isQuickStart: true },
    { id: 'dir_discovery', name: 'Directory Discovery', purpose: 'Fuzzing for hidden files and directories', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: true, category: 'vulnerability' },
    { id: 'sqli_checker', name: 'SQLi Checker', purpose: 'Lightweight SQL injection feasibility testing', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'web' },
    { id: 'sqlmap', name: 'SQLMap', purpose: 'Automated SQL injection and database takeover', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', isQuickStart: true },
    { id: 'tls_inspector', name: 'TLS Inspector', purpose: 'SSL/TLS certificate and cipher strength audit', riskLevel: 'passive', presetCompatibility: 'quick-recon', requiresConsent: false, category: 'vulnerability', subcategory: 'network' },
    { id: 'joomscan', name: 'JoomScan', purpose: 'Joomla CMS vulnerability and config auditor', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'web' },
    { id: 'droopescan', name: 'DroopeScan', purpose: 'Drupal/Silverstripe plugin and theme auditor', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'web' },
    { id: 'secret_scanner', name: 'Secret Scanner', purpose: 'Detection of hardcoded secrets in source code', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'code_analyzer', name: 'Code Analyzer (Bandit)', purpose: 'Static analysis for Python security flaws', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'web' },
    { id: 'ssh_runner', name: 'SSH Runner', purpose: 'Automated SSH configuration and auth auditing', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },

    // --- EXPERT & EXPLOIT ---
    { id: 'hashcat', name: 'Hashcat', purpose: 'Advanced password recovery and hash cracking', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'yara_scan', name: 'YARA Scan', purpose: 'Pattern matching forensics and malware detection', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'metasploit', name: 'Metasploit', purpose: 'Payload deployment and exploit framework', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'volatility', name: 'Volatility3', purpose: 'Advanced memory forensics and artifact extraction', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    // --- PENDING EXPLOIT MODULES (From Reference) ---
    { id: 'sniper', name: 'Sniper: Auto-Exploiter', purpose: 'Validate critical CVEs by automatic exploitation.', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'sqli_exploiter', name: 'SQLi Exploiter', purpose: 'Exploit SQL injection in web apps to extract data.', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'xss_exploiter', name: 'XSS Exploiter', purpose: 'Exploit XSS in real life-attacks, extract cookies and data.', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'http_request_logger', name: 'HTTP Request Logger', purpose: 'Handle incoming HTTP requests and record data.', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: true, category: 'exploit' },
    { id: 'subdomain_takeover', name: 'Subdomain Takeover', purpose: 'Discover dangling DNS entries pointing to external services.', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'exploit' },

    // --- UTILITIES ---
    { id: 'icmp_ping', name: 'ICMP Ping', purpose: 'Check if a server is live and responds to ICMP Echo requests.', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'utils' },
    { id: 'whois_lookup', name: 'Whois Lookup', purpose: 'Find the owner of a domain name or IP address and their contact data.', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'utils' },

    // --- ROBOTS ---
    { id: 'crawler', name: 'Crawler', purpose: 'Recursive web crawler for link discovery', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'robots' },
    { id: 'spider', name: 'Spider', purpose: 'Advanced web spider with JS execution support', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'robots' },
    { id: 'waf_detector', name: 'WAF Detector', purpose: 'Automatically identify Web Application Firewalls protecting targets', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: false, category: 'robots' },
    { id: 'sitemap_gen', name: 'Sitemap Generator', purpose: 'Build complete XML sitemaps by autonomously parsing targets', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'robots' },
    { id: 'fuzzer', name: 'Payload Fuzzer', purpose: 'Autonomously fuzz target fields with massive dictionaries', riskLevel: 'aggressive', presetCompatibility: 'none', requiresConsent: true, category: 'robots' },

    // --- PENDING / FUTURE ---
    { id: 'cloud_scanner', name: 'Cloud Scanner', purpose: 'Cloud infrastructure security (AWS/GCP/Azure)', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },
    { id: 'kubernetes_scanner', name: 'K8s Scanner', purpose: 'Kubernetes cluster security assessment', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },
    { id: 'api_scanner', name: 'API Scanner', purpose: 'Check for specific API vulnerabilities (REST and GraphQL)', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'web' },
    { id: 'sharepoint_scanner', name: 'Sharepoint Scanner', purpose: 'Check SharePoint for security issues, misconfigs, and more', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'web' },
    { id: 'network_scanner', name: 'Network Scanner', purpose: 'Check for 10,000+ CVEs and server misconfigurations', riskLevel: 'active', presetCompatibility: 'deep-scan', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },
    { id: 'password_auditor', name: 'Password Auditor', purpose: 'Discover weak credentials in network services and web apps', riskLevel: 'active', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },
    
    // --- ADVANCED PROSPECTIVE SCANNERS ---
    { id: 'zap_scanner', name: 'DAST Web Proxy (ZAP)', purpose: 'Dynamic proxy spidering and payload injection', riskLevel: 'aggressive', presetCompatibility: 'deep-scan', requiresConsent: true, category: 'vulnerability', subcategory: 'web' },
    { id: 'container_scanner', name: 'Container Scan (Trivy)', purpose: 'Scan Docker images and registries for known vulnerabilities', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },
    { id: 'cloud_storage_auditor', name: 'S3 / Blob Auditor', purpose: 'Find misconfigured S3 buckets and exposed cloud storage', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: true, category: 'vulnerability', subcategory: 'network' },
    { id: 'iac_scanner', name: 'IaC Scanner (Checkov)', purpose: 'Analyze Terraform and CloudFormation code for flaws', riskLevel: 'passive', presetCompatibility: 'none', requiresConsent: false, category: 'vulnerability', subcategory: 'code' },
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
