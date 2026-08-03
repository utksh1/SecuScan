export function escapeCSV(val: any): string {
  if (val === null || val === undefined) return ''
  const str = String(val)
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

export function serializeFindingsToCSV(findings: any[]): string {
  const headers = [
    'ID',
    'Title',
    'Severity',
    'Category',
    'Target',
    'Discovered At',
    'CVSS',
    'CVE',
    'Risk Score',
    'Confidence',
    'Validated',
    'Analyst Status',
    'Description',
    'Remediation'
  ]

  const rows = findings.map((f) => [
    f.id || '',
    f.title || '',
    f.severity || '',
    f.category || '',
    f.target || '',
    f.discovered_at || '',
    f.cvss !== undefined && f.cvss !== null ? String(f.cvss) : '',
    f.cve || '',
    f.risk_score !== undefined && f.risk_score !== null ? String(f.risk_score) : '',
    f.confidence !== undefined && f.confidence !== null ? String(f.confidence) : '',
    f.validated ? 'true' : 'false',
    f.analyst_status || '',
    f.description || '',
    f.remediation || ''
  ])

  return [
    headers.join(','),
    ...rows.map((row) => row.map(escapeCSV).join(','))
  ].join('\n')
}

export function downloadFile(content: string, filename: string, contentType: string): void {
  const blob = new Blob([content], { type: contentType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function exportFindingsAsCSV(findings: any[]): void {
  const csvContent = serializeFindingsToCSV(findings)
  const dateStr = new Date().toISOString().split('T')[0]
  downloadFile(csvContent, `secuscan_findings_${dateStr}.csv`, 'text/csv;charset=utf-8;')
}

export function exportFindingsAsJSON(findings: any[]): void {
  const jsonContent = JSON.stringify(findings, null, 2)
  const dateStr = new Date().toISOString().split('T')[0]
  downloadFile(jsonContent, `secuscan_findings_${dateStr}.json`, 'application/json')
}
