import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  ArrowLeft02Icon,
  Analytics02Icon,
  Refresh01Icon,
} from '@hugeicons/core-free-icons'
import { getFindings, getReports } from '../api'
import { routes } from '../routes'
import { formatDateLong } from '../utils/date'
import {
  compareFindings,
  type ComparableFinding,
  type ComparedFinding,
  type ReportComparisonResult,
} from '../utils/compareFindings'

type ReportOption = {
  id: string
  task_id: string
  name: string
  generated_at: string
  findings: number
  status: string
}

function reportHasFindings(
  report: ReportOption,
  findingsByTask: Record<string, ComparableFinding[]>,
): boolean {
  const fromApi = Number(report.findings)
  if (fromApi > 0) return true
  return (findingsByTask[report.task_id]?.length ?? 0) > 0
}

/** Compare uses finding diffs; include ready reports and failed scans that still produced findings. */
function comparableReports(
  rows: ReportOption[],
  findingsByTask: Record<string, ComparableFinding[]>,
): ReportOption[] {
  return rows.filter(
    (r) => r.status === 'ready' || (r.status === 'failed' && reportHasFindings(r, findingsByTask)),
  )
}

function reportOptionLabel(report: ReportOption): string {
  const statusNote = report.status === 'failed' ? ' (scan failed)' : ''
  return `${report.name}${statusNote} — ${formatDateLong(report.generated_at)}`
}

const severityChip: Record<string, string> = {
  critical: 'bg-rag-red text-black',
  high: 'bg-rag-amber text-black',
  medium: 'bg-rag-blue text-black',
  low: 'bg-charcoal-dark text-silver-bright border border-silver-bright/15',
  info: 'bg-charcoal-dark text-silver border border-silver/15',
}

function toComparableFinding(raw: Record<string, unknown>): ComparableFinding | null {
  const title = typeof raw.title === 'string' ? raw.title : ''
  const target = typeof raw.target === 'string' ? raw.target : ''
  const category = typeof raw.category === 'string' ? raw.category : ''
  const severity = typeof raw.severity === 'string' ? raw.severity : 'info'
  if (!title && !target) return null
  return {
    id: typeof raw.id === 'string' ? raw.id : undefined,
    title: title || 'Untitled finding',
    target: target || 'Unknown target',
    category: category || 'General',
    severity,
    description: typeof raw.description === 'string' ? raw.description : undefined,
  }
}

function FindingRow({ item, showBaseline, showComparison }: {
  item: ComparedFinding
  showBaseline?: boolean
  showComparison?: boolean
}) {
  const finding = (showComparison ? item.comparison : item.baseline) ?? item.comparison ?? item.baseline
  if (!finding) return null
  const severity = (finding.severity || 'info').toLowerCase()
  const chip = severityChip[severity] ?? severityChip.info

  return (
    <div className="border-2 border-black bg-charcoal-dark/50 p-4 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`px-2 py-0.5 text-[9px] font-black uppercase border-2 border-black ${chip}`}>
          {severity}
        </span>
        <span className="text-[9px] font-mono text-silver/40 uppercase">{finding.category}</span>
      </div>
      <p className="text-sm font-black text-silver-bright uppercase tracking-tight">{finding.title}</p>
      <p className="text-[10px] font-mono text-silver/50">{finding.target}</p>
      {showBaseline && showComparison && item.baseline && item.comparison && (
        <p className="text-[9px] font-black uppercase tracking-widest text-rag-amber">
          {item.baseline.severity} → {item.comparison.severity}
        </p>
      )}
    </div>
  )
}

function CompareSection({
  title,
  items,
  tone,
  showBaseline,
  showComparison,
}: {
  title: string
  items: ComparedFinding[]
  tone: string
  showBaseline?: boolean
  showComparison?: boolean
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between border-b-2 border-black pb-2">
        <h3 className={`text-lg font-black uppercase tracking-tighter italic ${tone}`}>{title}</h3>
        <span className="text-[10px] font-mono text-silver/40">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-[10px] font-black uppercase tracking-widest text-silver/30 italic">None</p>
      ) : (
        <div
          className="space-y-3 max-h-80 overflow-y-auto pr-1"
          role="region"
          aria-label={`${title} findings list`}
          tabIndex={0}
        >
          {items.map((item) => (
            <FindingRow
              key={item.fingerprint}
              item={item}
              showBaseline={showBaseline}
              showComparison={showComparison}
            />
          ))}
        </div>
      )}
    </section>
  )
}

export default function ReportCompare() {
  const [reports, setReports] = useState<ReportOption[]>([])
  const [findingsByTask, setFindingsByTask] = useState<Record<string, ComparableFinding[]>>({})
  const [baselineReportId, setBaselineReportId] = useState('')
  const [comparisonReportId, setComparisonReportId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = () => {
    setLoading(true)
    setError(null)
    Promise.all([getReports(), getFindings()])
      .then((results) => {
        const reportData = results[0] as { reports?: ReportOption[] }
        const findingsData = results[1] as { findings?: Record<string, unknown>[] }

        const byTask: Record<string, ComparableFinding[]> = {}
        for (const raw of findingsData.findings || []) {
          const row = raw as Record<string, unknown>
          const finding = toComparableFinding(row)
          if (!finding) continue
          const taskId = typeof row.task_id === 'string' ? row.task_id : ''
          if (taskId) {
            if (!byTask[taskId]) byTask[taskId] = []
            byTask[taskId].push(finding)
          }
        }
        setFindingsByTask(byTask)

        const rawReports = (reportData.reports || []).map((r) => ({
          ...r,
          findings: Number(r.findings ?? 0),
        }))
        setReports(comparableReports(rawReports, byTask))
      })
      .catch(() => setError('Failed to load reports or findings'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadData()
  }, [])

  const baselineReport = reports.find((r) => r.id === baselineReportId)
  const comparisonReport = reports.find((r) => r.id === comparisonReportId)

  const comparison: ReportComparisonResult | null = useMemo(() => {
    if (!baselineReport || !comparisonReport) return null
    if (baselineReport.id === comparisonReport.id) return null
    const baselineFindings = findingsByTask[baselineReport.task_id] || []
    const comparisonFindings = findingsByTask[comparisonReport.task_id] || []
    return compareFindings(baselineFindings, comparisonFindings)
  }, [baselineReport, comparisonReport, findingsByTask])

  const sameReportSelected = Boolean(
    baselineReportId && comparisonReportId && baselineReportId === comparisonReportId,
  )

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-10">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 pb-10 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <Link
            to={routes.reports}
            className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-silver/50 hover:text-silver-bright"
          >
            <HugeiconsIcon icon={ArrowLeft02Icon} size={16} />
            Back to reports
          </Link>
          <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
            Report_Diff v1.0
          </div>
          <h1 className="text-5xl md:text-7xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
            Compare <span className="text-rag-amber">Reports</span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic">
            BASELINE_VS_COMPARISON // NEW_FIXED_UNCHANGED_SEVERITY
          </p>
        </div>
        <button
          onClick={loadData}
          className="bg-charcoal border-4 border-black p-4 text-silver-bright shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          title="Refresh"
          aria-label="Refresh reports"
        >
          <HugeiconsIcon icon={Refresh01Icon} size={20} />
        </button>
      </header>

      {loading && (
        <p className="text-[10px] font-black uppercase tracking-[0.4em] text-silver/30 animate-pulse">
          Loading comparison data...
        </p>
      )}

      {!loading && error && (
        <div className="border-4 border-rag-red bg-rag-red/10 p-6 text-rag-red text-[10px] font-black uppercase tracking-widest">
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <label className="space-y-3 block">
              <span
                id="baseline-select-label"
                className="text-[10px] font-black uppercase tracking-widest text-silver-bright"
              >
                Baseline report (older)
              </span>
              <select
                value={baselineReportId}
                onChange={(e) => setBaselineReportId(e.target.value)}
                aria-labelledby="baseline-select-label"
                aria-label="Baseline report (older)"
                className="w-full bg-charcoal border-4 border-black p-4 text-sm font-mono text-silver-bright"
              >
                <option value="">Select baseline...</option>
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {reportOptionLabel(r)}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-3 block">
              <span
                id="comparison-select-label"
                className="text-[10px] font-black uppercase tracking-widest text-silver-bright"
              >
                Comparison report (newer)
              </span>
              <select
                value={comparisonReportId}
                onChange={(e) => setComparisonReportId(e.target.value)}
                aria-labelledby="comparison-select-label"
                aria-label="Comparison report (newer)"
                className="w-full bg-charcoal border-4 border-black p-4 text-sm font-mono text-silver-bright"
              >
                <option value="">Select comparison...</option>
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {reportOptionLabel(r)}
                  </option>
                ))}
              </select>
            </label>
          </section>

          {reports.length < 2 && (
            <p className="text-[10px] font-black uppercase tracking-widest text-silver/40">
              At least two reports with findings are required to compare. Run scans that finish
              with results, then refresh.
            </p>
          )}

          {sameReportSelected && (
            <p className="text-[10px] font-black uppercase tracking-widest text-rag-amber">
              Select two different reports to compare.
            </p>
          )}

          {comparison && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="border-4 border-black bg-charcoal p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-10"
            >
              <div className="flex items-center gap-3 text-silver-bright">
                <HugeiconsIcon icon={Analytics02Icon} size={28} />
                <div>
                  <p className="text-[10px] font-black uppercase tracking-widest text-silver/40">Diff ready</p>
                  <p className="text-sm font-mono">
                    {baselineReport?.name} → {comparisonReport?.name}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                <CompareSection
                  title="New findings"
                  items={comparison.newFindings}
                  tone="text-rag-red"
                  showComparison
                />
                <CompareSection
                  title="Fixed findings"
                  items={comparison.fixedFindings}
                  tone="text-rag-green"
                  showBaseline
                />
                <CompareSection
                  title="Unchanged"
                  items={comparison.unchangedFindings}
                  tone="text-silver-bright"
                  showComparison
                />
                <CompareSection
                  title="Severity changed"
                  items={comparison.severityChanged}
                  tone="text-rag-amber"
                  showBaseline
                  showComparison
                />
              </div>
            </motion.div>
          )}

          {!comparison && baselineReportId && comparisonReportId && !sameReportSelected && (
            <p className="text-[10px] font-black uppercase tracking-widest text-silver/40">
              No findings to compare for the selected reports.
            </p>
          )}
        </>
      )}
    </div>
  )
}