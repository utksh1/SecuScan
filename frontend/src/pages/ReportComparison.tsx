import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Analytics02Icon,
  ArrowRight01Icon,
  Cancel01Icon,
  CheckmarkCircle01Icon,
  GitCompareIcon,
  Radar02Icon,
  Refresh01Icon,
  ShieldCheckIcon,
  WarningDiamondIcon,
} from '@hugeicons/core-free-icons'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Finding {
  id: string
  title: string
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info'
  description?: string
}

export interface ScanReport {
  id: string
  name: string
  generated_at: string
  findings: Finding[]
}

export interface ComparisonResult {
  newFindings: Finding[]
  fixedFindings: Finding[]
  unchangedFindings: Finding[]
  severityChanges: Array<{
    finding: Finding
    oldSeverity?: string
    newSeverity?: string
  }>
}

// ─── Comparison logic ─────────────────────────────────────────────────────────
/**
 * Compares two scan reports deterministically using finding `id` as the key.
 * - New      → in reportB but not reportA
 * - Fixed    → in reportA but not reportB
 * - Unchanged → in both with the same severity
 * - Severity change → in both but severity differs
 */
export function compareReports(
  reportA: ScanReport,
  reportB: ScanReport,
): ComparisonResult {
  const mapA = new Map(reportA.findings.map((f) => [f.id, f]))
  const mapB = new Map(reportB.findings.map((f) => [f.id, f]))

  const newFindings: Finding[] = []
  const fixedFindings: Finding[] = []
  const unchangedFindings: Finding[] = []
  const severityChanges: ComparisonResult['severityChanges'] = []

  for (const [id, finding] of mapB) {
    if (!mapA.has(id)) {
      newFindings.push(finding)
    } else {
      const old = mapA.get(id)!
      if (old.severity !== finding.severity) {
        severityChanges.push({ finding, oldSeverity: old.severity, newSeverity: finding.severity })
      } else {
        unchangedFindings.push(finding)
      }
    }
  }

  for (const [id, finding] of mapA) {
    if (!mapB.has(id)) fixedFindings.push(finding)
  }

  return { newFindings, fixedFindings, unchangedFindings, severityChanges }
}

// ─── Mock data (swap for real API call later) ─────────────────────────────────

const MOCK_REPORTS: ScanReport[] = [
  {
    id: 'r1',
    name: 'Scan_Alpha — Jan 2025',
    generated_at: '2025-01-15T10:00:00Z',
    findings: [
      { id: 'f1', title: 'SQL Injection in /login', severity: 'critical', description: 'Unsanitised user input passed directly to query.' },
      { id: 'f2', title: 'Outdated TLS 1.0 Accepted', severity: 'medium', description: 'Server still accepts TLS 1.0 connections.' },
      { id: 'f3', title: 'Missing CSP Header', severity: 'low', description: 'No Content-Security-Policy header returned.' },
    ],
  },
  {
    id: 'r2',
    name: 'Scan_Beta — Feb 2025',
    generated_at: '2025-02-20T10:00:00Z',
    findings: [
      { id: 'f2', title: 'Outdated TLS 1.0 Accepted', severity: 'high', description: 'Severity escalated after re-assessment.' },
      { id: 'f3', title: 'Missing CSP Header', severity: 'low', description: 'Still not remediated.' },
      { id: 'f4', title: 'Open Redirect on /logout', severity: 'medium', description: 'Redirect destination unvalidated.' },
    ],
  },
  {
    id: 'r3',
    name: 'Scan_Gamma — Mar 2025',
    generated_at: '2025-03-10T10:00:00Z',
    findings: [
      { id: 'f3', title: 'Missing CSP Header', severity: 'low', description: 'Still present.' },
      { id: 'f5', title: 'Reflected XSS in Search', severity: 'high', description: 'New reflected XSS detected in search input.' },
    ],
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Icon({ icon, size = 20, className = '' }: { icon: any; size?: number; className?: string }) {
  return <HugeiconsIcon icon={icon} size={size} strokeWidth={1.9} className={className} />
}

const severityStyles: Record<string, string> = {
  critical: 'bg-rag-red text-black',
  high:     'bg-orange-500 text-black',
  medium:   'bg-rag-amber text-black',
  low:      'bg-rag-green text-black',
  info:     'bg-rag-blue text-black',
  unknown:  'bg-silver/20 text-black',
}

function SeverityBadge({ severity }: { severity?: string }) {
  const key = severity ?? 'unknown'
  return (
    <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-widest border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${severityStyles[key] ?? severityStyles.unknown}`}>
      {key}
    </span>
  )
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
}

// ─── Finding row ──────────────────────────────────────────────────────────────

function FindingRow({ finding }: { finding: Finding }) {
  return (
    <motion.div
      variants={itemVariants}
      className="bg-charcoal border-4 border-black p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] space-y-3"
    >
      <div className="flex justify-between items-start gap-4">
        <span className="text-sm font-black text-silver-bright uppercase tracking-tight italic leading-snug">
          {finding.title}
        </span>
        <SeverityBadge severity={finding.severity} />
      </div>
      {finding.description && (
        <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest leading-loose">
          {finding.description}
        </p>
      )}
    </motion.div>
  )
}

// ─── Comparison section ───────────────────────────────────────────────────────

function ComparisonSection({
  title,
  icon,
  findings,
  accentClass,
  emptyMsg,
}: {
  title: string
  icon: any
  findings: Finding[]
  accentClass: string
  emptyMsg: string
}) {
  return (
    <div className="space-y-4">
      <div className={`flex items-center gap-4 border-b-4 border-black pb-4`}>
        <Icon icon={icon} className={accentClass} />
        <h3 className={`text-base font-black uppercase tracking-widest italic ${accentClass}`}>
          {title}
        </h3>
        <span className={`ml-auto px-3 py-0.5 text-[10px] font-black border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${accentClass} bg-charcoal-dark`}>
          {findings.length}
        </span>
      </div>
      {findings.length === 0 ? (
        <p className="text-[10px] font-mono text-silver/20 uppercase tracking-widest italic py-6 text-center border-4 border-dashed border-black/10">
          {emptyMsg}
        </p>
      ) : (
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-4">
          {findings.map((f) => <FindingRow key={f.id} finding={f} />)}
        </motion.div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ReportComparison() {
  const reports = MOCK_REPORTS // TODO: replace with getReports() API call

  const [baseId, setBaseId]     = useState('')
  const [newerId, setNewerId]   = useState('')
  const [result, setResult]     = useState<ComparisonResult | null>(null)
  const [error, setError]       = useState('')

  function handleCompare() {
    setError('')
    setResult(null)
    if (!baseId || !newerId) { setError('Select both reports before comparing.'); return }
    if (baseId === newerId)  { setError('Select two different reports.'); return }
    const rA = reports.find((r) => r.id === baseId)
    const rB = reports.find((r) => r.id === newerId)
    if (!rA || !rB) { setError('Could not load one or both reports.'); return }
    setResult(compareReports(rA, rB))
  }

  const selectedA = reports.find((r) => r.id === baseId)
  const selectedB = reports.find((r) => r.id === newerId)

  const selectClass =
    'w-full bg-charcoal-dark border-4 border-black px-4 py-3 text-[11px] font-black text-silver-bright uppercase tracking-widest italic shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] focus:outline-none focus:border-rag-blue'

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">

      {/* Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
        <div className="space-y-4">
          <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
            Delta_Engine v1.0
          </div>
          <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
            Report{' '}
            <span
              className="text-transparent"
              style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}
            >
              Delta
            </span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
            COMPARE_SCAN_RUNS // TRACK_REMEDIATION // DETECT_REGRESSION
          </p>
        </div>
        <Icon icon={GitCompareIcon} size={64} className="text-silver/5" aria-hidden="true" />
      </header>

      {/* Selector Panel */}
      <section className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
        <h2 className="text-xs font-black text-silver-bright uppercase tracking-[0.3em] italic border-b-2 border-black pb-4">
          Select_Reports_For_Comparison
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-end">
          {/* Baseline selector */}
          <div className="space-y-3">
            <label className="text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] italic block">
              Baseline_Report (older)
            </label>
            <select value={baseId} onChange={(e) => setBaseId(e.target.value)} className={selectClass}>
              <option value="">— Select baseline —</option>
              {reports.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* Newer selector */}
          <div className="space-y-3">
            <label className="text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] italic block">
              Comparison_Report (newer)
            </label>
            <select value={newerId} onChange={(e) => setNewerId(e.target.value)} className={selectClass}>
              <option value="">— Select comparison —</option>
              {reports.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleCompare}
          className="bg-rag-blue border-4 border-black px-10 py-4 text-[11px] font-black uppercase tracking-widest text-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1.5 hover:translate-y-1.5 transition-all flex items-center gap-3"
        >
          <Icon icon={Radar02Icon} size={16} />
          Run Comparison
          <Icon icon={ArrowRight01Icon} size={16} />
        </button>

        {/* Error */}
        {error && (
          <div className="border-4 border-rag-red bg-rag-red/10 p-6 flex items-center gap-4">
            <Icon icon={Cancel01Icon} className="text-rag-red shrink-0" />
            <p className="text-[10px] font-black text-rag-red uppercase tracking-widest">{error}</p>
          </div>
        )}
      </section>

      {/* Results */}
      <AnimatePresence>
        {result && selectedA && selectedB && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-12"
          >
            {/* Summary bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[
                { label: 'New',              val: result.newFindings.length,       color: 'bg-rag-red' },
                { label: 'Fixed',            val: result.fixedFindings.length,     color: 'bg-rag-green' },
                { label: 'Unchanged',        val: result.unchangedFindings.length, color: 'bg-silver/20' },
                { label: 'Severity_Changed', val: result.severityChanges.length,   color: 'bg-rag-amber' },
              ].map((m) => (
                <div
                  key={m.label}
                  className={`${m.color} border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between h-28`}
                >
                  <span className="text-[9px] font-black uppercase tracking-widest text-black italic">{m.label}</span>
                  <span className="text-5xl font-black text-black font-mono leading-none">{m.val}</span>
                </div>
              ))}
            </div>

            {/* Comparing label */}
            <div className="flex items-center gap-4 text-[10px] font-mono text-silver/30 uppercase tracking-widest">
              <span className="text-silver-bright font-black">{selectedA.name}</span>
              <Icon icon={ArrowRight01Icon} size={14} />
              <span className="text-silver-bright font-black">{selectedB.name}</span>
            </div>

            {/* Four sections */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-12">
              <ComparisonSection
                title="New Findings"
                icon={WarningDiamondIcon}
                findings={result.newFindings}
                accentClass="text-rag-red"
                emptyMsg="No new findings — posture improved."
              />
              <ComparisonSection
                title="Fixed Findings"
                icon={CheckmarkCircle01Icon}
                findings={result.fixedFindings}
                accentClass="text-rag-green"
                emptyMsg="No issues fixed between these scans."
              />
              <ComparisonSection
                title="Unchanged Findings"
                icon={ShieldCheckIcon}
                findings={result.unchangedFindings}
                accentClass="text-silver/40"
                emptyMsg="No unchanged findings."
              />

              {/* Severity changes — special layout */}
              <div className="space-y-4">
                <div className="flex items-center gap-4 border-b-4 border-black pb-4">
                  <Icon icon={Analytics02Icon} className="text-rag-amber" />
                  <h3 className="text-base font-black uppercase tracking-widest italic text-rag-amber">
                    Severity Changes
                  </h3>
                  <span className="ml-auto px-3 py-0.5 text-[10px] font-black border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] text-rag-amber bg-charcoal-dark">
                    {result.severityChanges.length}
                  </span>
                </div>
                {result.severityChanges.length === 0 ? (
                  <p className="text-[10px] font-mono text-silver/20 uppercase tracking-widest italic py-6 text-center border-4 border-dashed border-black/10">
                    No severity changes detected.
                  </p>
                ) : (
                  <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-4">
                    {result.severityChanges.map(({ finding, oldSeverity, newSeverity }) => (
                      <motion.div
                        key={finding.id}
                        variants={itemVariants}
                        className="bg-charcoal border-4 border-black p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] space-y-3"
                      >
                        <span className="text-sm font-black text-silver-bright uppercase tracking-tight italic">
                          {finding.title}
                        </span>
                        <div className="flex items-center gap-3">
                          <SeverityBadge severity={oldSeverity} />
                          <Icon icon={ArrowRight01Icon} size={14} className="text-rag-amber" />
                          <SeverityBadge severity={newSeverity} />
                        </div>
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
        <div className="flex items-center gap-6">
          <div className="w-12 h-1 bg-silver/20"></div>
          DELTA_ANALYSIS_DAEMON // REPORT_DIFF_ENGINE // {new Date().getFullYear()}
        </div>
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="w-2 h-2 bg-silver/20 rounded-full" />
          ))}
        </div>
      </footer>
    </div>
  )
}