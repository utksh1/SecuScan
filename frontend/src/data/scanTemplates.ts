export interface ScanTemplateStep {
  toolId: string
  toolName: string
  description: string
  optional?: boolean
}

export interface ScanTemplate {
  id: string
  name: string
  description: string
  category: string
  estimatedDuration: string
  riskLevel: 'passive' | 'active' | 'aggressive'
  steps: ScanTemplateStep[]
}

export const scanTemplates: ScanTemplate[] = [
  {
    id: 'basic-web-recon',
    name: 'Basic Web Recon',
    description: 'Comprehensive reconnaissance of a web target — port scan, HTTP header inspection, subdomain discovery, and DNS enumeration.',
    category: 'recon',
    estimatedDuration: '10-15 min',
    riskLevel: 'active',
    steps: [
      { toolId: 'nmap', toolName: 'Nmap', description: 'Port scan for open services' },
      { toolId: 'http_inspector', toolName: 'HTTP Inspector', description: 'Inspect HTTP headers and endpoint behavior' },
      { toolId: 'subdomain_discovery', toolName: 'Subdomain Discovery', description: 'Enumerate subdomains via passive sources' },
      { toolId: 'dns_enum', toolName: 'DNS Enumeration', description: 'DNS record analysis and zone transfer attempt' },
    ],
  },
  {
    id: 'api-surface-check',
    name: 'API Surface Check',
    description: 'Audit an API endpoint for common weaknesses — header analysis, secret leakage, and template-based vulnerability screening.',
    category: 'vulnerability',
    estimatedDuration: '8-12 min',
    riskLevel: 'active',
    steps: [
      { toolId: 'http_inspector', toolName: 'HTTP Inspector', description: 'Analyze API endpoint responses and headers' },
      { toolId: 'secret_scanner', toolName: 'Secret Scanner', description: 'Detect hardcoded secrets in responses and source' },
      { toolId: 'nuclei', toolName: 'Nuclei', description: 'Template-based vulnerability scanning' },
    ],
  },
  {
    id: 'subdomain-audit',
    name: 'Subdomain Audit',
    description: 'Deep subdomain enumeration paired with DNS reconnaissance and targeted service discovery.',
    category: 'recon',
    estimatedDuration: '12-18 min',
    riskLevel: 'active',
    steps: [
      { toolId: 'subdomain_discovery', toolName: 'Subdomain Discovery', description: 'Passive and active subdomain enumeration' },
      { toolId: 'dns_enum', toolName: 'DNS Enumeration', description: 'DNS record analysis across discovered subdomains' },
      { toolId: 'nmap', toolName: 'Nmap', description: 'Service discovery on resolved subdomains' },
    ],
  },
  {
    id: 'local-network-inventory',
    name: 'Local Network Inventory',
    description: 'Map all live hosts and services on the local network segment.',
    category: 'recon',
    estimatedDuration: '5-10 min',
    riskLevel: 'active',
    steps: [
      { toolId: 'nmap', toolName: 'Nmap', description: 'Network sweep for live hosts and open ports' },
      { toolId: 'scapy_recon', toolName: 'Scapy Recon', description: 'Low-level packet crafting for OS fingerprinting', optional: true },
    ],
  },
  {
    id: 'quick-vulnerability-sweep',
    name: 'Quick Vulnerability Sweep',
    description: 'Rapid multi-vector vulnerability assessment combining template-based scanning, web server audit, and directory fuzzing.',
    category: 'vulnerability',
    estimatedDuration: '15-25 min',
    riskLevel: 'active',
    steps: [
      { toolId: 'nuclei', toolName: 'Nuclei', description: 'Template-driven vulnerability detection' },
      { toolId: 'nikto', toolName: 'Nikto', description: 'Web server vulnerability scanning' },
      { toolId: 'dir_discovery', toolName: 'Directory Discovery', description: 'Fuzzing for hidden files and directories' },
    ],
  },
]
