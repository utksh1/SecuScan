import { describe, expect, it } from 'vitest'
import {
  compareFindings,
  findingFingerprint,
  type ComparableFinding,
} from '../../../src/utils/compareFindings'

const base = (overrides: Partial<ComparableFinding> = {}): ComparableFinding => ({
  title: 'Open port',
  target: '127.0.0.1',
  category: 'network',
  severity: 'high',
  ...overrides,
})

describe('findingFingerprint', () => {
  it('is stable for same title target category', () => {
    const a = base({ title: 'Open Port', target: '127.0.0.1' })
    const b = base({ title: 'open port', target: '127.0.0.1' })
    expect(findingFingerprint(a)).toBe(findingFingerprint(b))
  })
})

describe('compareFindings', () => {
  it('detects new findings in comparison scan', () => {
    const baseline = [base({ title: 'Old issue' })]
    const comparison = [base({ title: 'Old issue' }), base({ title: 'New issue' })]
    const result = compareFindings(baseline, comparison)
    expect(result.newFindings).toHaveLength(1)
    expect(result.newFindings[0].comparison?.title).toBe('New issue')
  })

  it('detects fixed findings removed in comparison scan', () => {
    const baseline = [base({ title: 'Fixed issue' }), base({ title: 'Still here' })]
    const comparison = [base({ title: 'Still here' })]
    const result = compareFindings(baseline, comparison)
    expect(result.fixedFindings).toHaveLength(1)
    expect(result.fixedFindings[0].baseline?.title).toBe('Fixed issue')
  })

  it('detects unchanged findings with same severity', () => {
    const baseline = [base({ title: 'Stable', severity: 'medium' })]
    const comparison = [base({ title: 'Stable', severity: 'medium' })]
    const result = compareFindings(baseline, comparison)
    expect(result.unchangedFindings).toHaveLength(1)
    expect(result.severityChanged).toHaveLength(0)
  })

  it('detects severity changes for matching findings', () => {
    const baseline = [base({ title: 'Escalated', severity: 'medium' })]
    const comparison = [base({ title: 'Escalated', severity: 'critical' })]
    const result = compareFindings(baseline, comparison)
    expect(result.severityChanged).toHaveLength(1)
    expect(result.unchangedFindings).toHaveLength(0)
  })

  it('handles empty findings on both sides', () => {
    const result = compareFindings([], [])
    expect(result.newFindings).toHaveLength(0)
    expect(result.fixedFindings).toHaveLength(0)
    expect(result.unchangedFindings).toHaveLength(0)
    expect(result.severityChanged).toHaveLength(0)
  })
})
