export interface ScanPreset {
    id: string;
    name: string;
    description: string;
    riskLevel: 'low' | 'medium' | 'high';
    toolIds: string[];
    requiresExplicitConsent: boolean;
}

export const scanPresets: ScanPreset[] = [
    {
        id: 'quick-recon',
        name: 'Quick Recon',
        description: 'Passive and light active reconnaissance',
        riskLevel: 'low',
        requiresExplicitConsent: false,
        toolIds: [
            'dig',
            'whois',
            'httpx-passive',
            'httpx-web',
            'whatweb',
            'dnsenum',
            'sslscan',
            'openssl'
        ]
    },
    {
        id: 'deep-scan',
        name: 'Deep Scan',
        description: 'Comprehensive active scanning with aggressive tools',
        riskLevel: 'high',
        requiresExplicitConsent: true,
        toolIds: [
            'nmap',
            'ffuf-web',
            'nikto-web',
            'sqlmap',
            'ffuf-sqli',
            'enum4linux',
            'smbclient',
            'smtp-user-enum',
            'ffuf-files',
            'dirsearch',
            'nikto-files'
        ]
    }
];

export function getPresetById(id: string): ScanPreset | undefined {
    return scanPresets.find(p => p.id === id);
}
