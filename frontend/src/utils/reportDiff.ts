export interface Finding {
  id: string
  severity: string
  category: string
  title: string
  target: string
  description: string
  remediation: string
  discovered_at: string
  cvss?: number
  cve?: string
  plugin_id?: string
}

export interface DiffResults {
  added: Finding[]
  fixed: Finding[]
  unchanged: Finding[]
  severityChanged: {
    finding: Finding;
    oldSeverity: string;
    newSeverity: string;
  }[];
}

/**
 * Compares two arrays of scan findings and returns categorized deltas.
 * Uses O(N+M) time complexity with Map lookups for performance on large datasets.
 */
export function calculateReportDiff(oldFindings: Finding[] = [], newFindings: Finding[] = []): DiffResults {
  const oldMap = new Map<string, Finding>();
  const newMap = new Map<string, Finding>();

  // Map both sets for instant O(1) lookups
  oldFindings.forEach(f => oldMap.set(f.id, f));
  newFindings.forEach(f => newMap.set(f.id, f));

  const added: Finding[] = [];
  const fixed: Finding[] = [];
  const unchanged: Finding[] = [];
  const severityChanged: DiffResults['severityChanged'] = [];

  // Iterate through the new findings to spot additions, variations, or matches
  newFindings.forEach(newFinding => {
    const oldFinding = oldMap.get(newFinding.id);
    if (!oldFinding) {
      added.push(newFinding);
    } else if (oldFinding.severity !== newFinding.severity) {
      severityChanged.push({
        finding: newFinding,
        oldSeverity: oldFinding.severity,
        newSeverity: newFinding.severity
      });
    } else {
      unchanged.push(newFinding);
    }
  });

  // Iterate through the old findings to spot what was successfully remediated (fixed)
  oldFindings.forEach(oldFinding => {
    if (!newMap.has(oldFinding.id)) {
      fixed.push(oldFinding);
    }
  });

  return { added, fixed, unchanged, severityChanged };
}
