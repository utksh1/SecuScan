import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { getFindings } from '../api'
import { formatLocaleDate, parseDateSafe, getCurrentTimeZone } from '../utils/date'
import SavedViewsPanel from '../components/SavedViewsPanel'
import { useSavedViews, FilterPreset } from '../hooks/useSavedViews'

type Finding = {
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

type FindingStatus = 'new' | 'reviewed' | 'suppressed'

type ReviewState = Record<string, FindingStatus>

const severityOrder = ['critical', 'high', 'medium', 'low', 'info'] as const
const severityConfig: Record<string, { label: string; accent: string; chip: string; rail: string }> = {
  critical: {
    label: 'Critical',
    accent: 'text-rag-red',
    chip: 'bg-rag-red text-black',
    rail: 'bg-rag-red',
  },
  high: {
    label: 'High',
    accent: 'text-rag-amber',
    chip: 'bg-rag-amber text-black',
    rail: 'bg-rag-amber',
  },
  medium: {
    label: 'Medium',
    accent: 'text-rag-blue',
    chip: 'bg-rag-blue text-black',
    rail: 'bg-rag-blue',
  },
  low: {
    label: 'Low',
    accent: 'text-silver-bright',
    chip: 'bg-charcoal-dark text-silver-bright border border-silver-bright/15',
    rail: 'bg-silver/50',
  },
  info: {
    label: 'Info',
    accent: 'text-silver',
    chip: 'bg-charcoal-dark text-silver border border-silver/15',
    rail: 'bg-silver/20',
  },
}

const sectionVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.19, 1, 0.22, 1] as const },
  },
}

function normalizeSeverity(value: string) {
  return severityConfig[value] ? value : 'info'
}

function getStatusTone(status: FindingStatus) {
  switch (status) {
    case 'reviewed':
      return 'text-rag-green border-rag-green/25 bg-rag-green/10'
    case 'suppressed':
      return 'text-silver border-silver/20 bg-silver/5'
    default:
      return 'text-rag-amber border-rag-amber/20 bg-rag-amber/10'
  }
}

function filterPillClasses(isActive: boolean) {
  return isActive
    ? 'border-black bg-silver-bright text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
    : 'border-silver-bright/10 bg-charcoal-dark text-silver/65 hover:border-silver-bright/30 hover:text-silver-bright'
}

const filterLabelClass = 'text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright'
const filterControlClass =
  'h-11 w-full border-2 border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright focus:border-rag-red focus:outline-none'

type SortMode = 'severity' | 'newest' | 'oldest' | 'target'

export default function Findings() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('all')
  const [filterTarget, setFilterTarget] = useState('all')
  const [filterScanner, setFilterScanner] = useState('all')
  const [sortMode, setSortMode] = useState<SortMode>('severity')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null)
  const [reviewState, setReviewState] = useState<ReviewState>({})
  const [copiedFindingId, setCopiedFindingId] = useState<string | null>(null)

  // ── Saved views hook ───────────────────────────────────────────────────────
  const { views, loading: viewsLoading, saveView, deleteView, renameView } = useSavedViews()

  /** Apply a saved preset to all filter controls. */
  function applyPreset(preset: FilterPreset) {
    setFilterSeverity(preset.severity)
    setFilterTarget(preset.target)
    setFilterScanner(preset.scanner)
    setSortMode(preset.sortMode as SortMode)
    setDateFrom(preset.dateFrom)
    setDateTo(preset.dateTo)
    setSearchQuery(preset.searchQuery)
  }

  /** Snapshot the current filter controls as a FilterPreset. */
  const currentPreset: FilterPreset = {
    severity: filterSeverity,
    target: filterTarget,
    scanner: filterScanner,
    sortMode,
    dateFrom,
    dateTo,
    searchQuery,
  }

  useEffect(() => {
    setLoading(true)
    getFindings()
      .then((data: any) => {
        const nextFindings = data.findings || []
        setFindings(nextFindings)
        setSelectedFindingId((current) => current ?? nextFindings[0]?.id ?? null)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    try {
      const saved = localStorage.getItem('secuscan-finding-review-state')
      if (saved) {
        setReviewState(JSON.parse(saved))
      }
    } catch {
      // Ignore malformed local review state.
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('secuscan-finding-review-state', JSON.stringify(reviewState))
  }, [reviewState])

  const enrichedFindings = useMemo(
    () =>
      findings.map((finding) => ({
        ...finding,
        severity: normalizeSeverity(finding.severity),
        status: reviewState[finding.id] || 'new',
      })),
    [findings, reviewState],
  )

  // Collect unique targets and categories so we can build filter dropdowns.
  const uniqueTargets = useMemo(() => {
    const seen = new Set<string>()
    for (const f of enrichedFindings) {
      if (f.target) seen.add(f.target)
    }
    return Array.from(seen).sort()
  }, [enrichedFindings])

  // plugin_id values serve as the "scanner/tool" filter per issue #43
  const uniqueScanners = useMemo(() => {
    const seen = new Set<string>()
    for (const f of enrichedFindings) {
      if (f.plugin_id) seen.add(f.plugin_id)
    }
    return Array.from(seen).sort()
  }, [enrichedFindings])

  const filteredFindings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()

    // Compare dates using the *displayed* calendar day in the user's configured
    // timezone, not raw UTC timestamps. This way a finding at 2026-05-13T20:00:00Z
    // that shows as May 14 in IST correctly matches a From Date of 2026-05-14.
    const tz = getCurrentTimeZone()
    const dateFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: tz })

    return enrichedFindings.filter((finding) => {
      const matchesSeverity = filterSeverity === 'all' || finding.severity === filterSeverity
      const matchesTarget = filterTarget === 'all' || finding.target === filterTarget
      const matchesScanner = filterScanner === 'all' || finding.plugin_id === filterScanner

      // Date range check — derive the calendar day in the display timezone
      if (dateFrom || dateTo) {
        const parsed = parseDateSafe(finding.discovered_at)
        if (!parsed) return false
        // en-CA locale gives us YYYY-MM-DD which matches the <input type="date"> value
        const displayDay = dateFormatter.format(parsed)
        if (dateFrom && displayDay < dateFrom) return false
        if (dateTo && displayDay > dateTo) return false
      }

      const haystack = [
        finding.title,
        finding.target,
        finding.description,
        finding.remediation,
        finding.cve,
        finding.category,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return matchesSeverity && matchesTarget && matchesScanner && haystack.includes(query)
    })
  }, [enrichedFindings, filterSeverity, filterTarget, filterScanner, searchQuery, dateFrom, dateTo])

  const sortedFindings = useMemo(() => {
    const items = [...filteredFindings]
    switch (sortMode) {
      case 'newest':
        return items.sort((a, b) => {
          const da = parseDateSafe(a.discovered_at)?.getTime() ?? 0
          const db = parseDateSafe(b.discovered_at)?.getTime() ?? 0
          return db - da
        })
      case 'oldest':
        return items.sort((a, b) => {
          const da = parseDateSafe(a.discovered_at)?.getTime() ?? 0
          const db = parseDateSafe(b.discovered_at)?.getTime() ?? 0
          return da - db
        })
      case 'target':
        return items.sort((a, b) =>
          (a.target || '').localeCompare(b.target || '')
        )
      case 'severity':
      default:
        // Keep the original severity-group ordering; groupedFindings handles it.
        return items
    }
  }, [filteredFindings, sortMode])

  const groupedFindings = useMemo(
    () =>
      severityOrder.map((severity) => ({
        severity,
        items: sortedFindings.filter((finding) => finding.severity === severity),
      })),
    [sortedFindings],
  )

  const selectedFinding =
    filteredFindings.find((finding) => finding.id === selectedFindingId) ??
    filteredFindings[0] ??
    null

  useEffect(() => {
    if (!selectedFinding) {
      setSelectedFindingId(null)
      return
    }

    if (!filteredFindings.some((finding) => finding.id === selectedFinding.id)) {
      setSelectedFindingId(filteredFindings[0]?.id ?? null)
    }
  }, [filteredFindings, selectedFinding])

  const countsBySeverity = useMemo(() => {
    return severityOrder.reduce<Record<string, number>>((acc, severity) => {
      acc[severity] = enrichedFindings.filter((finding) => finding.severity === severity).length
      return acc
    }, {})
  }, [enrichedFindings])

  const triageMetrics = useMemo(
    () => ({
      total: enrichedFindings.length,
      visible: filteredFindings.length,
      active: countsBySeverity.critical + countsBySeverity.high,
      unresolved: enrichedFindings.filter((finding) => finding.status === 'new').length,
    }),
    [enrichedFindings, filteredFindings, countsBySeverity],
  )

  function updateFindingStatus(id: string, status: FindingStatus) {
    setReviewState((current) => ({ ...current, [id]: status }))
  }

  async function copyFindingSummary(finding: Finding & { status: FindingStatus }) {
    const summary = [
      `${finding.title} (${finding.severity.toUpperCase()})`,
      `Target: ${finding.target || 'N/A'}`,
      `Category: ${finding.category || 'Uncategorized'}`,
      finding.cve ? `CVE: ${finding.cve}` : null,
      `Status: ${finding.status.toUpperCase()}`,
      `Observed: ${formatLocaleDate(finding.discovered_at)}`,
      `Description: ${finding.description || 'No description provided.'}`,
      `Remediation: ${finding.remediation || 'No remediation provided.'}`,
    ]
      .filter(Boolean)
      .join('\n')

    try {
      await navigator.clipboard.writeText(summary)
      setCopiedFindingId(finding.id)
      window.setTimeout(() => setCopiedFindingId((current) => (current === finding.id ? null : current)), 1600)
    } catch {
      setCopiedFindingId(null)
    }
  }

  function renderFindingRow(finding: Finding & { severity: string; status: FindingStatus }) {
    const isSelected = selectedFinding?.id === finding.id
    const cfg = severityConfig[finding.severity]

    return (
      <button
        key={finding.id}
        type="button"
        onClick={() => setSelectedFindingId(finding.id)}
        className={`relative block w-full px-5 py-5 text-left transition-all ${
          isSelected ? 'bg-silver-bright/6' : 'hover:bg-silver-bright/3'
        }`}
      >
        <span className={`absolute inset-y-0 left-0 w-1 ${cfg.rail}`} />
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1 space-y-3 pl-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${cfg.chip}`}>
                {cfg.label}
              </span>
              <span className={`border px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${getStatusTone(finding.status)}`}>
                {finding.status}
              </span>
              <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-silver/35">
                {finding.category || 'Uncategorized'}
              </span>
              {finding.cve ? (
                <span className="border border-rag-blue/20 bg-rag-blue/10 px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-rag-blue">
                  {finding.cve}
                </span>
              ) : null}
            </div>

            <div>
              <h3 className="text-xl font-black uppercase tracking-tight text-silver-bright">{finding.title}</h3>
              <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.16em] text-silver/45">
                Target // {finding.target || 'Unknown'} // Observed // {formatLocaleDate(finding.discovered_at)}
              </p>
            </div>

            <p className="max-w-4xl text-sm leading-relaxed text-silver/70">
              {finding.description || 'No description provided.'}
            </p>
          </div>

          <div className="flex flex-row items-end gap-6 lg:min-w-[140px] lg:flex-col lg:items-end">
            {typeof finding.cvss === 'number' ? (
              <div className="text-right">
                <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">CVSS</p>
                <p className={`text-3xl font-black italic ${finding.cvss >= 9 ? 'text-rag-red' : 'text-silver-bright'}`}>
                  {finding.cvss.toFixed(1)}
                </p>
              </div>
            ) : null}

            <span className={`material-symbols-outlined text-lg ${isSelected ? 'text-silver-bright' : 'text-silver/30'}`}>
              east
            </span>
          </div>
        </div>
      </button>
    )
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col">

        {/* ── Page Header ──────────────────────────────────────────────────── */}
        <header className="border-b border-silver-bright/8 px-6 py-6 md:px-10 md:py-8">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            {/* Left: eyebrow + title + stats */}
            <div>
              <p className="mb-1 text-[10px] font-black uppercase tracking-[0.3em] text-silver/35">
                SecuScan · Triage Interface
              </p>
              <h1 className="text-5xl font-black uppercase italic tracking-tighter text-silver-bright md:text-6xl">
                Findings
              </h1>
              <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.22em] text-silver/40">
                {triageMetrics.total} Total
                {' · '}
                <span className="text-rag-red">{triageMetrics.active} Urgent</span>
                {' · '}
                {triageMetrics.unresolved} Triaging
              </p>
            </div>

            {/* Right: severity quick-filter pills */}
            <div className="flex flex-wrap items-center gap-1">
              <button
                type="button"
                onClick={() => setFilterSeverity('all')}
                className={`border px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.18em] transition-all ${
                  filterSeverity === 'all'
                    ? 'border-silver-bright bg-silver-bright text-black'
                    : 'border-silver-bright/15 bg-transparent text-silver/50 hover:border-silver-bright/40 hover:text-silver-bright'
                }`}
              >
                All
              </button>
              {severityOrder.map((severity) => (
                <button
                  key={severity}
                  type="button"
                  onClick={() => setFilterSeverity((cur) => cur === severity ? 'all' : severity)}
                  className={`border px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.18em] transition-all ${
                    filterSeverity === severity
                      ? `${severityConfig[severity].chip} border-black`
                      : 'border-silver-bright/15 bg-transparent text-silver/50 hover:border-silver-bright/40 hover:text-silver-bright'
                  }`}
                >
                  {severityConfig[severity].label}
                </button>
              ))}
            </div>
          </div>
        </header>

        <div className="flex flex-col gap-0 px-6 py-6 md:px-10 md:py-8 xl:flex-row xl:gap-6 xl:items-start">

          {/* ── Left column: filter + findings list ─────────────────────── */}
          <div className="flex min-w-0 flex-1 flex-col gap-4">

            {/* Filter panel */}
            <section className="border border-silver-bright/8 bg-charcoal/80 p-5 backdrop-blur lg:sticky lg:top-4 lg:z-20">

              {/* Search */}
              <div className="mb-4">
                <label className="mb-1.5 block text-[9px] font-black uppercase tracking-[0.25em] text-silver/40">
                  Search Scope
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Query via titles, target endpoints, CVE IDs..."
                  className="h-10 w-full border border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright placeholder:text-silver/20 focus:border-silver-bright/30 focus:outline-none"
                />
              </div>

              {/* Dropdowns + date row */}
              <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                {/* Target Host */}
                <div>
                  <label className="mb-1.5 block text-[9px] font-black uppercase tracking-[0.22em] text-silver/40">
                    Target Host
                  </label>
                  <select
                    value={filterTarget}
                    onChange={(e) => setFilterTarget(e.target.value)}
                    className="h-10 w-full border border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright focus:border-silver-bright/30 focus:outline-none"
                  >
                    <option value="all">All targets</option>
                    {uniqueTargets.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                {/* Engine / Scanner */}
                <div>
                  <label className="mb-1.5 block text-[9px] font-black uppercase tracking-[0.22em] text-silver/40">
                    Engine/Scanner
                  </label>
                  <select
                    value={filterScanner}
                    onChange={(e) => setFilterScanner(e.target.value)}
                    className="h-10 w-full border border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright focus:border-silver-bright/30 focus:outline-none"
                  >
                    <option value="all">All scanners</option>
                    {uniqueScanners.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                {/* Discovered From */}
                <div>
                  <label className="mb-1.5 block text-[9px] font-black uppercase tracking-[0.22em] text-silver/40">
                    Discovered From
                  </label>
                  <div className="relative flex h-10">
                    <input
                      id="date-from-input"
                      type="date"
                      value={dateFrom}
                      onChange={(e) => setDateFrom(e.target.value)}
                      className="h-10 w-full border border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright [color-scheme:dark] focus:border-silver-bright/30 focus:outline-none [&::-webkit-calendar-picker-indicator]:opacity-0 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:inset-0 [&::-webkit-calendar-picker-indicator]:w-full [&::-webkit-calendar-picker-indicator]:cursor-pointer"
                    />
                    <button
                      type="button"
                      aria-label="Open date picker for Discovered From"
                      onClick={() => (document.getElementById('date-from-input') as HTMLInputElement)?.showPicker?.()}
                      className="absolute right-0 top-0 flex h-10 w-10 items-center justify-center border-l border-silver-bright/10 bg-charcoal-dark text-silver/40 transition-colors hover:bg-silver-bright/5 hover:text-silver-bright"
                    >
                      <span className="material-symbols-outlined text-[16px]">calendar_month</span>
                    </button>
                  </div>
                </div>

                {/* Discovered To */}
                <div>
                  <label className="mb-1.5 block text-[9px] font-black uppercase tracking-[0.22em] text-silver/40">
                    Discovered To
                  </label>
                  <div className="relative flex h-10">
                    <input
                      id="date-to-input"
                      type="date"
                      value={dateTo}
                      onChange={(e) => setDateTo(e.target.value)}
                      className="h-10 w-full border border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright [color-scheme:dark] focus:border-silver-bright/30 focus:outline-none [&::-webkit-calendar-picker-indicator]:opacity-0 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:inset-0 [&::-webkit-calendar-picker-indicator]:w-full [&::-webkit-calendar-picker-indicator]:cursor-pointer"
                    />
                    <button
                      type="button"
                      aria-label="Open date picker for Discovered To"
                      onClick={() => (document.getElementById('date-to-input') as HTMLInputElement)?.showPicker?.()}
                      className="absolute right-0 top-0 flex h-10 w-10 items-center justify-center border-l border-silver-bright/10 bg-charcoal-dark text-silver/40 transition-colors hover:bg-silver-bright/5 hover:text-silver-bright"
                    >
                      <span className="material-symbols-outlined text-[16px]">calendar_month</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Sort tabs + Saved Views */}
              <div className="mt-4 flex items-center justify-between gap-2 flex-wrap">
                {/* Segmented sort tabs */}
                <div className="flex items-center gap-0">
                  {(
                    [
                      { value: 'severity', label: 'By Severity' },
                      { value: 'newest',   label: 'Newest' },
                      { value: 'oldest',   label: 'Oldest' },
                      { value: 'target',   label: 'Target Alpha' },
                    ] as { value: SortMode; label: string }[]
                  ).map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setSortMode(value)}
                      className={`border px-4 py-2 text-[10px] font-black uppercase tracking-[0.16em] transition-all -ml-px first:ml-0 ${
                        sortMode === value
                          ? 'relative z-10 border-silver-bright bg-silver-bright text-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]'
                          : 'border-silver-bright/15 bg-transparent text-silver/50 hover:text-silver-bright hover:border-silver-bright/30'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                {/* Saved Views button (uses the panel component) */}
                <SavedViewsPanel
                  views={views}
                  loading={viewsLoading}
                  saveView={saveView}
                  deleteView={deleteView}
                  renameView={renameView}
                  currentPreset={currentPreset}
                  onApply={applyPreset}
                />
              </div>
            </section>

            {/* Findings list */}
            <motion.section variants={sectionVariants} initial="hidden" animate="visible" className="space-y-3">
              {loading ? (
                <div className="border border-dashed border-silver-bright/10 bg-charcoal/40 px-6 py-16 text-center">
                  <p className="text-sm font-mono uppercase tracking-[0.25em] text-silver/50">Synchronizing findings feed...</p>
                </div>
              ) : filteredFindings.length === 0 ? (
                <div className="border border-dashed border-silver-bright/10 bg-charcoal/40 px-6 py-20 text-center">
                  <p className="text-2xl font-black uppercase italic tracking-[0.25em] text-silver/20">Queue Cleared</p>
                  <p className="mt-3 text-xs font-mono uppercase tracking-[0.2em] text-silver/15">
                    No items match your active profile matrices.
                  </p>
                </div>
              ) : sortMode === 'severity' ? (
                groupedFindings.map(({ severity, items }) => {
                  if (items.length === 0) return null
                  const config = severityConfig[severity]
                  return (
                    <div key={severity} className="border border-silver-bright/8 bg-charcoal">
                      <div className="flex items-center gap-3 border-b border-silver-bright/8 px-5 py-3">
                        <span className={`h-2.5 w-2.5 rotate-45 ${config.rail}`} />
                        <p className={`text-[11px] font-black uppercase tracking-[0.2em] ${config.accent}`}>{config.label}</p>
                        <p className="text-[9px] font-mono uppercase tracking-[0.15em] text-silver/30">{items.length} in queue</p>
                      </div>
                      <div className="divide-y divide-silver-bright/6">
                        {items.map((finding) => renderFindingRow(finding))}
                      </div>
                    </div>
                  )
                })
              ) : (
                <div className="border border-silver-bright/8 bg-charcoal">
                  <div className="flex items-center gap-3 border-b border-silver-bright/8 px-5 py-3">
                    <span className="h-2.5 w-2.5 rotate-45 bg-silver-bright" />
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-silver-bright">
                      {sortMode === 'newest' ? 'Newest First' : sortMode === 'oldest' ? 'Oldest First' : 'By Target'}
                    </p>
                    <p className="text-[9px] font-mono uppercase tracking-[0.15em] text-silver/30">{sortedFindings.length} in queue</p>
                  </div>
                  <div className="divide-y divide-silver-bright/6">
                    {sortedFindings.map((finding) => renderFindingRow(finding))}
                  </div>
                </div>
              )}
            </motion.section>
          </div>

          {/* ── Right column: detail panel ──────────────────────────────── */}
          <motion.aside
            variants={sectionVariants}
            initial="hidden"
            animate="visible"
            className="w-full xl:sticky xl:top-4 xl:w-[420px] xl:self-start xl:shrink-0"
          >
            <div className="border border-silver-bright/8 bg-charcoal">
              {selectedFinding ? (
                <div className="space-y-6 p-6">
                  <div className="space-y-4 border-b border-silver-bright/8 pb-6">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${severityConfig[selectedFinding.severity].chip}`}>
                        {severityConfig[selectedFinding.severity].label}
                      </span>
                      <span className={`border px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${getStatusTone(selectedFinding.status)}`}>
                        {selectedFinding.status}
                      </span>
                      {selectedFinding.cve ? (
                        <span className="border border-rag-blue/20 bg-rag-blue/10 px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-rag-blue">
                          {selectedFinding.cve}
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <p className="mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Selected Finding</p>
                      <h2 className="text-2xl font-black uppercase italic tracking-tight text-silver-bright">{selectedFinding.title}</h2>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Target</p>
                        <p className="mt-1.5 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">{selectedFinding.target || 'Unknown'}</p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Category</p>
                        <p className="mt-1.5 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">{selectedFinding.category || 'Uncategorized'}</p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Observed</p>
                        <p className="mt-1.5 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">{formatLocaleDate(selectedFinding.discovered_at)}</p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Severity Score</p>
                        <p className="mt-1.5 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {typeof selectedFinding.cvss === 'number' ? selectedFinding.cvss.toFixed(1) : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <p className="mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Evidence Brief</p>
                      <div className="border-l-2 border-rag-red bg-charcoal-dark p-4">
                        <p className="text-sm leading-relaxed text-silver/70">{selectedFinding.description || 'No description provided.'}</p>
                      </div>
                    </div>
                    <div>
                      <p className="mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Remediation</p>
                      <div className="border-l-2 border-rag-green bg-charcoal-dark p-4">
                        <p className="text-sm leading-relaxed text-rag-green/80">{selectedFinding.remediation || 'No remediation guidance captured.'}</p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3 border-t border-silver-bright/8 pt-5">
                    <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/30">Workflow Actions</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <button type="button" onClick={() => updateFindingStatus(selectedFinding.id, 'reviewed')}
                        className="border border-silver-bright bg-silver-bright px-4 py-2.5 text-[9px] font-black uppercase tracking-[0.18em] text-black transition-all active:opacity-80">
                        Mark Reviewed
                      </button>
                      <button type="button" onClick={() => updateFindingStatus(selectedFinding.id, 'new')}
                        className="border border-rag-amber/25 bg-rag-amber/10 px-4 py-2.5 text-[9px] font-black uppercase tracking-[0.18em] text-rag-amber">
                        Reopen
                      </button>
                      <button type="button" onClick={() => updateFindingStatus(selectedFinding.id, 'suppressed')}
                        className="border border-silver/20 bg-silver/5 px-4 py-2.5 text-[9px] font-black uppercase tracking-[0.18em] text-silver">
                        Suppress
                      </button>
                      <button type="button" onClick={() => copyFindingSummary(selectedFinding)}
                        className="border border-rag-blue/25 bg-rag-blue/10 px-4 py-2.5 text-[9px] font-black uppercase tracking-[0.18em] text-rag-blue">
                        {copiedFindingId === selectedFinding.id ? 'Copied' : 'Copy Brief'}
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center px-6 py-24 text-center">
                  <p className="text-2xl font-black uppercase italic tracking-[0.18em] text-silver/15">Queue Neutral</p>
                  <p className="mt-3 max-w-[240px] text-[10px] font-mono uppercase leading-relaxed tracking-[0.16em] text-silver/12">
                    Select a live finding from the queue to mount inspection context.
                  </p>
                </div>
              )}
            </div>
          </motion.aside>

        </div>
      </div>
    </div>
  )
}