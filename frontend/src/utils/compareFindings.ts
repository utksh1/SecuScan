export type ComparableFinding = {
  id?: string
  title: string
  target: string
  category: string
  severity: string
  description?: string
}

export type ComparedFinding = {
  fingerprint: string
  baseline?: ComparableFinding
  comparison?: ComparableFinding
}

export type ReportComparisonResult = {
  newFindings: ComparedFinding[]
  fixedFindings: ComparedFinding[]
  unchangedFindings: ComparedFinding[]
  severityChanged: ComparedFinding[]
}

export function findingFingerprint(finding: ComparableFinding): string {
  const title = (finding.title || '').trim().toLowerCase()
  const target = (finding.target || '').trim().toLowerCase()
  const category = (finding.category || '').trim().toLowerCase()
  return `${title}|${target}|${category}`
}

function indexFindings(findings: ComparableFinding[]): Map<string, ComparableFinding> {
  const map = new Map<string, ComparableFinding>()
  for (const finding of findings) {
    map.set(findingFingerprint(finding), finding)
  }
  return map
}

export function compareFindings(
  baselineFindings: ComparableFinding[],
  comparisonFindings: ComparableFinding[],
): ReportComparisonResult {
  const baseline = indexFindings(baselineFindings)
  const comparison = indexFindings(comparisonFindings)

  const newFindings: ComparedFinding[] = []
  const fixedFindings: ComparedFinding[] = []
  const unchangedFindings: ComparedFinding[] = []
  const severityChanged: ComparedFinding[] = []

  for (const [fingerprint, comparisonFinding] of comparison.entries()) {
    const baselineFinding = baseline.get(fingerprint)
    if (!baselineFinding) {
      newFindings.push({ fingerprint, comparison: comparisonFinding })
      continue
    }

    const baselineSeverity = (baselineFinding.severity || 'info').toLowerCase()
    const comparisonSeverity = (comparisonFinding.severity || 'info').toLowerCase()
    const entry: ComparedFinding = {
      fingerprint,
      baseline: baselineFinding,
      comparison: comparisonFinding,
    }

    if (baselineSeverity === comparisonSeverity) {
      unchangedFindings.push(entry)
    } else {
      severityChanged.push(entry)
    }
  }

  for (const [fingerprint, baselineFinding] of baseline.entries()) {
    if (!comparison.has(fingerprint)) {
      fixedFindings.push({ fingerprint, baseline: baselineFinding })
    }
  }

  return {
    newFindings,
    fixedFindings,
    unchangedFindings,
    severityChanged,
  }
}
