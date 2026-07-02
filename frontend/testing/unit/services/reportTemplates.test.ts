import { describe, it, expect } from 'vitest'
import {
  getTemplates,
  getTemplateById,
  renderTemplate,
  renderPreview,
  exportAsFile,
  buildTemplateData,
  type ReportTemplateType,
  type TemplateData,
} from '../../../src/services/reportTemplates'

function makeSampleData(overrides?: Partial<TemplateData>): TemplateData {
  return {
    reportName: 'Test Scan Report',
    reportType: 'executive',
    generatedAt: '2026-06-15T10:00:00Z',
    totalFindings: 42,
    totalAssets: 15,
    totalPages: 8,
    criticalCount: 3,
    highCount: 7,
    mediumCount: 12,
    lowCount: 20,
    topFindings: [
      { title: 'SQL Injection', severity: 'critical', target: 'app.example.com' },
      { title: 'Weak SSH Ciphers', severity: 'high', target: 'mail.example.com' },
      { title: 'Missing CORS Headers', severity: 'medium', target: 'api.example.com' },
    ],
    summaryText: 'Security assessment identified 42 findings across 15 assets.',
    assetBreakdown: [
      { label: 'Web Servers', count: 5 },
      { label: 'API Endpoints', count: 3 },
      { label: 'Mail Servers', count: 2 },
      { label: 'Databases', count: 3 },
      { label: 'DNS', count: 2 },
    ],
    complianceScore: 72,
    ...overrides,
  }
}

describe('getTemplates', () => {
  it('returns all built-in templates when no type filter', () => {
    const all = getTemplates()
    expect(all).toHaveLength(3)
    expect(all.map(t => t.type)).toEqual(['executive', 'technical', 'compliance'])
  })

  it('filters templates by type', () => {
    const exec = getTemplates('executive')
    expect(exec).toHaveLength(1)
    expect(exec[0].type).toBe('executive')

    const tech = getTemplates('technical')
    expect(tech).toHaveLength(1)
    expect(tech[0].type).toBe('technical')

    const comp = getTemplates('compliance')
    expect(comp).toHaveLength(1)
    expect(comp[0].type).toBe('compliance')
  })

  it('returns empty array for unknown type', () => {
    const result = getTemplates('unknown' as any)
    expect(result).toHaveLength(0)
  })
})

describe('getTemplateById', () => {
  it('returns template by id', () => {
    const tpl = getTemplateById('executive-summary')
    expect(tpl).toBeDefined()
    expect(tpl?.id).toBe('executive-summary')
    expect(tpl?.name).toBe('Executive Summary')
  })

  it('returns technical template', () => {
    const tpl = getTemplateById('technical-deep-dive')
    expect(tpl).toBeDefined()
    expect(tpl?.type).toBe('technical')
  })

  it('returns compliance template', () => {
    const tpl = getTemplateById('compliance-audit')
    expect(tpl).toBeDefined()
    expect(tpl?.type).toBe('compliance')
  })

  it('returns undefined for unknown id', () => {
    expect(getTemplateById('nonexistent')).toBeUndefined()
  })
})

describe('buildTemplateData', () => {
  it('builds data from report and summary', () => {
    const data = buildTemplateData(
      { name: 'Nightly Scan', type: 'executive', generated_at: '2026-06-15T10:00:00Z', findings: 42, assets: 15, pages: 8 },
      { critical_findings: 3, high_findings: 7, medium_findings: 12, low_findings: 20 },
    )
    expect(data.reportName).toBe('Nightly Scan')
    expect(data.reportType).toBe('executive')
    expect(data.totalFindings).toBe(42)
    expect(data.totalAssets).toBe(15)
    expect(data.totalPages).toBe(8)
    expect(data.criticalCount).toBe(3)
    expect(data.highCount).toBe(7)
  })

  it('defaults missing summary values to zero', () => {
    const data = buildTemplateData(
      { name: 'Minimal', type: 'technical', generated_at: '', findings: 0, assets: 0, pages: 0 },
      {},
    )
    expect(data.criticalCount).toBe(0)
    expect(data.highCount).toBe(0)
    expect(data.mediumCount).toBe(0)
    expect(data.lowCount).toBe(0)
  })

  it('handles undefined summary gracefully', () => {
    const data = buildTemplateData(
      { name: 'Test', type: 'compliance', generated_at: '2026-01-01', findings: 5, assets: 2, pages: 1 },
      undefined,
    )
    expect(data.criticalCount).toBe(0)
  })
})

describe('renderTemplate', () => {
  it('renders executive template with findings table', () => {
    const tpl = getTemplateById('executive-summary')!
    const data = makeSampleData()
    const output = renderTemplate(tpl, data)

    expect(output).toContain('# Executive Briefing')
    expect(output).toContain('42')
    expect(output).toContain('SQL Injection')
    expect(output).toContain('Compliance Score')
    expect(output).toContain('72')
  })

  it('renders technical template with finding list', () => {
    const tpl = getTemplateById('technical-deep-dive')!
    const data = makeSampleData({ reportType: 'technical' })
    const output = renderTemplate(tpl, data)

    expect(output).toContain('# Technical Report')
    expect(output).toContain('42')
    expect(output).toContain('CRITICAL')
    expect(output).toContain('SQL Injection')
  })

  it('renders compliance template with score', () => {
    const tpl = getTemplateById('compliance-audit')!
    const data = makeSampleData({ reportType: 'compliance', complianceScore: 85 })
    const output = renderTemplate(tpl, data)

    expect(output).toContain('# Compliance Report')
    expect(output).toContain('85')
    expect(output).toContain('PASS')
  })

  it('handles zero findings gracefully', () => {
    const tpl = getTemplateById('executive-summary')!
    const data = makeSampleData({ totalFindings: 0, criticalCount: 0, highCount: 0, topFindings: [] })
    const output = renderTemplate(tpl, data)

    expect(output).toContain('0')
    expect(output).not.toContain('undefined')
  })

  it('handles missing compliance score', () => {
    const tpl = getTemplateById('compliance-audit')!
    const data = makeSampleData({ reportType: 'compliance', complianceScore: undefined })
    const output = renderTemplate(tpl, data)

    expect(output).toContain('# Compliance Report')
  })
})

describe('renderPreview', () => {
  it('renders executive preview', () => {
    const tpl = getTemplateById('executive-summary')!
    const html = renderPreview(tpl, makeSampleData())

    expect(html).toContain('Executive Preview')
    expect(html).toContain('Test Scan Report')
    expect(html).toContain('Critical 3')
  })

  it('renders technical preview', () => {
    const tpl = getTemplateById('technical-deep-dive')!
    const html = renderPreview(tpl, makeSampleData({ reportType: 'technical' }))

    expect(html).toContain('Technical Preview')
    expect(html).toContain('42 findings')
  })

  it('renders compliance preview with score color', () => {
    const tpl = getTemplateById('compliance-audit')!
    const html = renderPreview(tpl, makeSampleData({ reportType: 'compliance', complianceScore: 92 }))

    expect(html).toContain('Compliance Preview')
    expect(html).toContain('92')
  })

  it('escapes HTML in reportName to prevent XSS', () => {
    const tpl = getTemplateById('executive-summary')!
    const data = makeSampleData({ reportName: '<img src=x onerror=alert(1)>' })
    const html = renderPreview(tpl, data)

    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;')
  })

  it('escapes HTML in finding title to prevent XSS', () => {
    const tpl = getTemplateById('technical-deep-dive')!
    const data = makeSampleData({
      reportType: 'technical',
      reportName: 'safe',
      topFindings: [{ title: '<script>alert(1)</script>', severity: 'high', target: 'example.com' }],
    })
    const html = renderPreview(tpl, data)

    expect(html).not.toContain('<script>')
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('escapes quotes in severity badge to prevent attribute injection', () => {
    const tpl = getTemplateById('technical-deep-dive')!
    const data = makeSampleData({
      reportType: 'technical',
      reportName: 'safe',
      topFindings: [{ title: 'test', severity: 'critical" onmouseover="alert(1)', target: 'example.com' }],
    })
    const html = renderPreview(tpl, data)

    expect(html).not.toContain('critical" on')
    expect(html).toContain('critical&quot;')
  })
})

describe('exportAsFile', () => {
  it('creates a download link and removes it', () => {
    const createSpy = vi.spyOn(document, 'createElement')
    const appendSpy = vi.spyOn(document.body, 'appendChild')
    const removeSpy = vi.spyOn(document.body, 'removeChild')
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL')

    exportAsFile('# Test', 'test-report')

    expect(createSpy).toHaveBeenCalledWith('a')
    expect(appendSpy).toHaveBeenCalled()
    expect(removeSpy).toHaveBeenCalled()

    createSpy.mockRestore()
    appendSpy.mockRestore()
    removeSpy.mockRestore()
    revokeSpy.mockRestore()
  })
})

describe('template metadata', () => {
  it('every template has non-empty id, name, description', () => {
    for (const tpl of getTemplates()) {
      expect(tpl.id).toBeTruthy()
      expect(tpl.name).toBeTruthy()
      expect(tpl.description).toBeTruthy()
    }
  })

  it('every template render returns a string', () => {
    const data = makeSampleData()
    for (const tpl of getTemplates()) {
      const result = renderTemplate(tpl, { ...data, reportType: tpl.type })
      expect(typeof result).toBe('string')
      expect(result.length).toBeGreaterThan(10)
    }
  })

  it('every template preview returns an HTML string', () => {
    const data = makeSampleData()
    for (const tpl of getTemplates()) {
      const result = renderPreview(tpl, { ...data, reportType: tpl.type })
      expect(result).toContain('<div')
      expect(result).toContain('</div>')
    }
  })
})
