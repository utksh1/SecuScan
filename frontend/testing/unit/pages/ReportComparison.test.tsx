import { describe, it, expect } from 'vitest'
import { compareReports, type ScanReport } from '../../../src/pages/ReportComparison'

const reportA: ScanReport = {
  id: 'r1',
  name: 'January Scan',
  generated_at: '2025-01-01T00:00:00Z',
  findings: [
    { id: 'f1', title: 'SQL Injection',  severity: 'critical' },
    { id: 'f2', title: 'Open Port 8080', severity: 'low' },
  ],
}

const reportB: ScanReport = {
  id: 'r2',
  name: 'February Scan',
  generated_at: '2025-02-01T00:00:00Z',
  findings: [
    { id: 'f2', title: 'Open Port 8080', severity: 'low' },
    { id: 'f3', title: 'XSS in Search',  severity: 'high' },
  ],
}

describe('compareReports', () => {
  it('detects new findings', () => {
    const r = compareReports(reportA, reportB)
    expect(r.newFindings).toHaveLength(1)
    expect(r.newFindings[0].id).toBe('f3')
  })

  it('detects fixed findings', () => {
    const r = compareReports(reportA, reportB)
    expect(r.fixedFindings).toHaveLength(1)
    expect(r.fixedFindings[0].id).toBe('f1')
  })

  it('detects unchanged findings', () => {
    const r = compareReports(reportA, reportB)
    expect(r.unchangedFindings).toHaveLength(1)
    expect(r.unchangedFindings[0].id).toBe('f2')
  })

  it('handles empty findings gracefully', () => {
    const r = compareReports(
      { ...reportA, findings: [] },
      { ...reportB, findings: [] }
    )
    expect(r.newFindings).toHaveLength(0)
    expect(r.fixedFindings).toHaveLength(0)
    expect(r.unchangedFindings).toHaveLength(0)
    expect(r.severityChanges).toHaveLength(0)
  })

  it('detects severity changes', () => {
    const escalated: ScanReport = {
      ...reportB,
      findings: [{ id: 'f2', title: 'Open Port 8080', severity: 'high' }], // was low
    }
    const r = compareReports(reportA, escalated)
    expect(r.severityChanges).toHaveLength(1)
    expect(r.severityChanges[0].oldSeverity).toBe('low')
    expect(r.severityChanges[0].newSeverity).toBe('high')
  })
})