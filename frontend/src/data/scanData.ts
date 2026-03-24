export type RiskLevel = 'low' | 'medium';
export type ScanMode = 'active' | 'passive';

export interface Tool {
    id: string;
    name: string;
    intent: string;
    riskLevel: RiskLevel;
    mode: ScanMode;
    category: string;
    scanTypes?: string[];
}

export interface Category {
    id: string;
    name: string;
    description: string;
    icon: string;
    scanTypes?: string[];
}

export const categories: Category[] = [
    {
        id: 'network',
        name: 'Network Scanning',
        description: 'Host discovery and port scanning',
        icon: '🌐'
    },
    {
        id: 'webapp',
        name: 'Web Application',
        description: 'Web server and application testing',
        icon: '🔍'
    },
    {
        id: 'sqli',
        name: 'SQL Injection Detection',
        description: 'Non-destructive SQL injection testing',
        icon: '💉',
        scanTypes: ['Parameter discovery', 'Error-based detection', 'Boolean-based testing']
    },
    {
        id: 'secrets',
        name: 'API Key & Secret Exposure',
        description: 'Credential and secret detection',
        icon: '🔑',
        scanTypes: ['Public JavaScript analysis', 'Config & backup file exposure', 'Hardcoded secret detection']
    },
    {
        id: 'tls',
        name: 'TLS/SSL Security',
        description: 'Certificate and encryption analysis',
        icon: '🔒'
    },
    {
        id: 'services',
        name: 'Service Enumeration',
        description: 'Service identification and enumeration',
        icon: '📡'
    },
    {
        id: 'files',
        name: 'Sensitive Files & Misconfig',
        description: 'Directory and configuration scanning',
        icon: '📁'
    },
    {
        id: 'passive',
        name: 'Informational/Passive',
        description: 'Non-intrusive information gathering',
        icon: 'ℹ️'
    }
];

export const tools: Tool[] = [
    // Network Scanning
    { id: 'nmap', name: 'nmap', intent: 'Port scanning and service detection', riskLevel: 'medium', mode: 'active', category: 'network' },
    { id: 'arp-scan', name: 'arp-scan', intent: 'Local network host discovery', riskLevel: 'low', mode: 'active', category: 'network' },

    // Web Application Scanning
    { id: 'ffuf-web', name: 'ffuf', intent: 'Web fuzzing and directory discovery', riskLevel: 'medium', mode: 'active', category: 'webapp' },
    { id: 'nikto-web', name: 'nikto', intent: 'Web server vulnerability scanning', riskLevel: 'medium', mode: 'active', category: 'webapp' },
    { id: 'httpx-web', name: 'httpx', intent: 'HTTP probe and analysis', riskLevel: 'low', mode: 'passive', category: 'webapp' },
    { id: 'whatweb', name: 'whatweb', intent: 'Web technology fingerprinting', riskLevel: 'low', mode: 'passive', category: 'webapp' },

    // SQL Injection Detection
    { id: 'sqlmap', name: 'sqlmap', intent: 'SQL injection detection (non-destructive)', riskLevel: 'medium', mode: 'active', category: 'sqli', scanTypes: ['Parameter discovery', 'Error-based detection', 'Boolean-based testing'] },
    { id: 'ffuf-sqli', name: 'ffuf', intent: 'Parameter fuzzing for SQL injection', riskLevel: 'medium', mode: 'active', category: 'sqli', scanTypes: ['Parameter discovery'] },
    { id: 'httpx-sqli', name: 'httpx', intent: 'HTTP parameter analysis', riskLevel: 'low', mode: 'passive', category: 'sqli', scanTypes: ['Parameter discovery'] },

    // API Key & Secret Exposure
    { id: 'trufflehog', name: 'trufflehog', intent: 'Secret scanning in repositories', riskLevel: 'low', mode: 'passive', category: 'secrets', scanTypes: ['Hardcoded secret detection'] },
    { id: 'gitleaks', name: 'gitleaks', intent: 'Git repository secret detection', riskLevel: 'low', mode: 'passive', category: 'secrets', scanTypes: ['Hardcoded secret detection'] },
    { id: 'ripgrep', name: 'ripgrep', intent: 'Fast text pattern matching', riskLevel: 'low', mode: 'passive', category: 'secrets', scanTypes: ['Public JavaScript analysis', 'Hardcoded secret detection'] },
    { id: 'ffuf-secrets', name: 'ffuf', intent: 'Config and backup file discovery', riskLevel: 'medium', mode: 'active', category: 'secrets', scanTypes: ['Config & backup file exposure'] },

    // TLS/SSL Security
    { id: 'sslscan', name: 'sslscan', intent: 'SSL/TLS cipher and protocol testing', riskLevel: 'low', mode: 'active', category: 'tls' },
    { id: 'testssl', name: 'testssl.sh', intent: 'Comprehensive TLS/SSL testing', riskLevel: 'low', mode: 'active', category: 'tls' },
    { id: 'openssl', name: 'openssl', intent: 'Certificate and cipher analysis', riskLevel: 'low', mode: 'active', category: 'tls' },

    // Service Enumeration
    { id: 'enum4linux', name: 'enum4linux', intent: 'SMB/CIFS enumeration', riskLevel: 'medium', mode: 'active', category: 'services' },
    { id: 'smbclient', name: 'smbclient', intent: 'SMB share access and enumeration', riskLevel: 'medium', mode: 'active', category: 'services' },
    { id: 'smtp-user-enum', name: 'smtp-user-enum', intent: 'SMTP user enumeration', riskLevel: 'medium', mode: 'active', category: 'services' },
    { id: 'dnsenum', name: 'dnsenum', intent: 'DNS enumeration and subdomain discovery', riskLevel: 'low', mode: 'passive', category: 'services' },

    // Sensitive Files & Misconfiguration
    { id: 'ffuf-files', name: 'ffuf', intent: 'Directory and file fuzzing', riskLevel: 'medium', mode: 'active', category: 'files' },
    { id: 'dirsearch', name: 'dirsearch', intent: 'Web path and file discovery', riskLevel: 'medium', mode: 'active', category: 'files' },
    { id: 'nikto-files', name: 'nikto', intent: 'Misconfiguration and file detection', riskLevel: 'medium', mode: 'active', category: 'files' },

    // Informational/Passive
    { id: 'dig', name: 'dig', intent: 'DNS query and record lookup', riskLevel: 'low', mode: 'passive', category: 'passive' },
    { id: 'whois', name: 'whois', intent: 'Domain registration information', riskLevel: 'low', mode: 'passive', category: 'passive' },
    { id: 'httpx-passive', name: 'httpx', intent: 'HTTP header and technology detection', riskLevel: 'low', mode: 'passive', category: 'passive' }
];

export function getToolsByCategory(categoryId: string, scanType?: string): Tool[] {
    let filtered = tools.filter(t => t.category === categoryId);

    if (scanType && scanType !== 'all') {
        filtered = filtered.filter(t =>
            !t.scanTypes || t.scanTypes.includes(scanType)
        );
    }

    return filtered;
}

export function getCategoryById(id: string): Category | undefined {
    return categories.find(c => c.id === id);
}
