import { describe, it, expect } from 'vitest';
import { calculateReportDiff } from '../../../src/utils/reportDiff';

describe('Report Diff Engine Verification', () => {
  it('should handle completely blank reports cleanly', () => {
    const delta = calculateReportDiff([], []);
    expect(delta.added).toHaveLength(0);
    expect(delta.fixed).toHaveLength(0);
    expect(delta.unchanged).toHaveLength(0);
    expect(delta.severityChanged).toHaveLength(0);
  });

  it('should identify identical items as unchanged', () => {
    const report = [{ 
      id: 'hash1', 
      title: 'SQL Injection', 
      severity: 'HIGH',
      category: 'Injection',
      target: 'example.com',
      description: 'SQL injection vulnerability',
      remediation: 'Use parameterized queries',
      discovered_at: '2024-01-01T00:00:00Z'
    }];
    const delta = calculateReportDiff(report, report);
    expect(delta.unchanged).toHaveLength(1);
    expect(delta.added).toHaveLength(0);
    expect(delta.fixed).toHaveLength(0);
    expect(delta.severityChanged).toHaveLength(0);
  });

  it('should properly segment additions, removals, and severity escalations', () => {
    const oldScan = [
      { 
        id: 'hash1', 
        title: 'Dependency Vulnerability', 
        severity: 'LOW',
        category: 'Dependency',
        target: 'example.com',
        description: 'Outdated dependency',
        remediation: 'Update dependency',
        discovered_at: '2024-01-01T00:00:00Z'
      },
      { 
        id: 'hash2', 
        title: 'Hardcoded API Key', 
        severity: 'CRITICAL',
        category: 'Secrets',
        target: 'example.com',
        description: 'Hardcoded API key found',
        remediation: 'Remove hardcoded key',
        discovered_at: '2024-01-01T00:00:00Z'
      }
    ];
    
    const newScan = [
      { 
        id: 'hash1', 
        title: 'Dependency Vulnerability', 
        severity: 'HIGH',
        category: 'Dependency',
        target: 'example.com',
        description: 'Outdated dependency',
        remediation: 'Update dependency',
        discovered_at: '2024-01-01T00:00:00Z'
      },
      { 
        id: 'hash3', 
        title: 'Reflected XSS', 
        severity: 'MEDIUM',
        category: 'XSS',
        target: 'example.com',
        description: 'Reflected XSS vulnerability',
        remediation: 'Sanitize input',
        discovered_at: '2024-01-02T00:00:00Z'
      }
    ];

    const delta = calculateReportDiff(oldScan, newScan);

    expect(delta.added).toHaveLength(1);
    expect(delta.added[0].id).toBe('hash3');
    
    expect(delta.fixed).toHaveLength(1);
    expect(delta.fixed[0].id).toBe('hash2');
    
    expect(delta.severityChanged).toHaveLength(1);
    expect(delta.severityChanged[0].oldSeverity).toBe('LOW');
    expect(delta.severityChanged[0].newSeverity).toBe('HIGH');
  });

  it('should handle empty old report with new findings', () => {
    const oldScan: any[] = [];
    const newScan = [
      { 
        id: 'hash1', 
        title: 'New Vulnerability', 
        severity: 'HIGH',
        category: 'Injection',
        target: 'example.com',
        description: 'New vulnerability',
        remediation: 'Fix it',
        discovered_at: '2024-01-01T00:00:00Z'
      }
    ];

    const delta = calculateReportDiff(oldScan, newScan);
    expect(delta.added).toHaveLength(1);
    expect(delta.fixed).toHaveLength(0);
    expect(delta.unchanged).toHaveLength(0);
  });

  it('should handle empty new report with all findings fixed', () => {
    const oldScan = [
      { 
        id: 'hash1', 
        title: 'Old Vulnerability', 
        severity: 'HIGH',
        category: 'Injection',
        target: 'example.com',
        description: 'Old vulnerability',
        remediation: 'Fix it',
        discovered_at: '2024-01-01T00:00:00Z'
      }
    ];
    const newScan: any[] = [];

    const delta = calculateReportDiff(oldScan, newScan);
    expect(delta.added).toHaveLength(0);
    expect(delta.fixed).toHaveLength(1);
    expect(delta.unchanged).toHaveLength(0);
  });

  it('should handle mixed severity changes correctly', () => {
    const oldScan = [
      { 
        id: 'hash1', 
        title: 'Vuln 1', 
        severity: 'LOW',
        category: 'General',
        target: 'example.com',
        description: 'Desc',
        remediation: 'Fix',
        discovered_at: '2024-01-01T00:00:00Z'
      },
      { 
        id: 'hash2', 
        title: 'Vuln 2', 
        severity: 'MEDIUM',
        category: 'General',
        target: 'example.com',
        description: 'Desc',
        remediation: 'Fix',
        discovered_at: '2024-01-01T00:00:00Z'
      },
      { 
        id: 'hash3', 
        title: 'Vuln 3', 
        severity: 'HIGH',
        category: 'General',
        target: 'example.com',
        description: 'Desc',
        remediation: 'Fix',
        discovered_at: '2024-01-01T00:00:00Z'
      }
    ];

    const newScan = [
      { 
        id: 'hash1', 
        title: 'Vuln 1', 
        severity: 'HIGH',
        category: 'General',
        target: 'example.com',
        description: 'Desc',
        remediation: 'Fix',
        discovered_at: '2024-01-01T00:00:00Z'
      },
      { 
        id: 'hash2', 
        title: 'Vuln 2', 
        severity: 'LOW',
        category: 'General',
        target: 'example.com',
        description: 'Desc',
        remediation: 'Fix',
        discovered_at: '2024-01-01T00:00:00Z'
      },
      { 
        id: 'hash3', 
        title: 'Vuln 3', 
        severity: 'HIGH',
        category: 'General',
        target: 'example.com',
        description: 'Desc',
        remediation: 'Fix',
        discovered_at: '2024-01-01T00:00:00Z'
      }
    ];

    const delta = calculateReportDiff(oldScan, newScan);
    expect(delta.severityChanged).toHaveLength(2);
    expect(delta.unchanged).toHaveLength(1);
    expect(delta.unchanged[0].id).toBe('hash3');
  });
});
