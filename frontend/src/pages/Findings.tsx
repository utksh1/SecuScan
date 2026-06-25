import React, { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useVirtualizer } from '@tanstack/react-virtual'
import { getFindings } from '../api'
import { formatLocaleDate, parseDateSafe, getCurrentTimeZone } from '../utils/date'
import SavedViewsPanel from '../components/SavedViewsPanel'
import { useSavedViews, FilterPreset } from '../hooks/useSavedViews'
import { exportFindingsAsCSV, exportFindingsAsJSON } from '../utils/exportUtils'

type RiskFactor = {
  factor: string
  label: string
  value: string | number
  score: number
  weight: number
  contribution: number
  detail: string
}

type Finding = {
  id: string
  finding_group_id?: string
  asset_id?: string
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
  risk_score?: number
  risk_factors?: RiskFactor[]
  exploitability?: number
  confidence?: number
  validated?: boolean
  validation_method?: string
  confidence_reason?: string
  evidence?: Array<Record<string, unknown>>
  asset_refs?: string[]
  finding_kind?: 'observation' | 'suspected_issue' | 'validated_issue'
  occurrence_count?: number
  corroborating_sources?: string[]
  evidence_count?: number
  analyst_status?: string
  retest_status?: string
  first_seen_at?: string
  last_seen_at?: string
  service_fingerprint?: string
  cpe?: string
  references?: Array<Record<string, unknown>>
  asset_exposure?: string
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

// Plain-language blurbs for the severity legend help affordance. Ordering mirrors
// `severityOrder` (highest → lowest risk). Reuses `severityConfig` for label + colors.
const severityLegend: { id: (typeof severityOrder)[number]; blurb: string }[] = [
  { id: 'critical', blurb: 'Confirmed or highly likely exploitation with severe impact — triage first.' },
  { id: 'high', blurb: 'Serious weakness, likely exploitable. Remediate promptly.' },
  { id: 'medium', blurb: 'Moderate risk or exploitable only under specific conditions.' },
  { id: 'low', blurb: 'Minor issue or hardening opportunity with limited impact.' },
  { id: 'info', blurb: 'Informational signal — context only, or pending manual validation.' },
]

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

const filterLabelClass ='block text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright'
const filterControlClass =
  'h-11 w-full border-2 border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright focus:border-rag-red focus:outline-none'

type SortMode = 'risk' | 'severity' | 'newest' | 'oldest' | 'target'

// ─── Virtual row types ────────────────────────────────────────────────────────

type HeaderRow = { kind: 'header'; severity: string; count: number }
type FindingRow = { kind: 'finding'; finding: Finding & { status: FindingStatus }; isLastInGroup: boolean }
type VirtualRow = HeaderRow | FindingRow

// Estimated heights for virtualizer
const ROW_HEIGHTS: Record<VirtualRow['kind'], number> = {
  header: 72,
  finding: 140,
}

export default function Findings() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [page, setPage] = useState(1)
  const [totalItems, setTotalItems] = useState(0)
  const perPage = 50
  const [searchQuery, setSearchQuery] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('all')
  const [filterTarget, setFilterTarget] = useState('all')
  const [filterScanner, setFilterScanner] = useState('all')
  const [filterKind, setFilterKind] = useState('all')
  const [filterAnalystStatus, setFilterAnalystStatus] = useState('all')
  const [filterAsset, setFilterAsset] = useState('all')
  const [filterValidatedOnly, setFilterValidatedOnly] = useState(false)
  const [filterHighConfidence, setFilterHighConfidence] = useState(false)
  const [sortMode, setSortMode] = useState<SortMode>('risk')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null)
  const [reviewState, setReviewState] = useState<ReviewState>({})
  const [copiedFindingId, setCopiedFindingId] = useState<string | null>(null)

  // ── Multi-select export state & handlers ───────────────────────────────────
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false)

  const [columnVisibility, setColumnVisibility] = useState({
    category: true,
    findingKind: true,
    cve: true,
    confidence: true,
    occurrenceCount: true,
    cvss: true,
  })

  const [showColumnChooser, setShowColumnChooser] = useState(false)

  const columnLabels = {
    category: 'Category',
    findingKind: 'Finding Kind',
    cve: 'CVE',
    confidence: 'Confidence',
    occurrenceCount: 'Occurrence Count',
    cvss: 'CVSS',
  }

  // ── Severity legend help affordance ────────────────────────────────────────
  const [legendOpen, setLegendOpen] = useState(false)
  const legendRef = useRef<HTMLDivElement>(null)
  const legendButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!legendOpen) return
    function onPointerDown(event: MouseEvent) {
      if (legendRef.current && !legendRef.current.contains(event.target as Node)) {
        setLegendOpen(false)
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setLegendOpen(false)
        legendButtonRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [legendOpen])

  // ── Saved views ────────────────────────────────────────────────────────────
  const { views, loading: viewsLoading, saveView, deleteView, renameView } = useSavedViews()

  const currentPreset: FilterPreset = {
    severity: filterSeverity,
    target: filterTarget,
    scanner: filterScanner,
    sortMode,
    dateFrom,
    dateTo,
    searchQuery,
  }

  function applyPreset(preset: FilterPreset) {
    setFilterSeverity(preset.severity)
    setFilterTarget(preset.target)
    setFilterScanner(preset.scanner)
    setSortMode(preset.sortMode as SortMode)
    setDateFrom(preset.dateFrom)
    setDateTo(preset.dateTo)
    setSearchQuery(preset.searchQuery)
  }

  useEffect(() => {
    setLoading(true)
    getFindings(1, perPage)
      .then((data: any) => {
        const nextFindings = data.findings || []
        setFindings(nextFindings)
        setTotalItems(data.total ?? nextFindings.length)
        setPage(1)
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
        status: reviewState[finding.id] || (
          finding.analyst_status === 'confirmed'
            ? 'reviewed'
            : finding.analyst_status === 'false_positive'
              ? 'suppressed'
              : 'new'
        ),
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

  const uniqueAssets = useMemo(() => {
    const seen = new Set<string>()
    for (const finding of enrichedFindings) {
      const label = finding.asset_id || finding.asset_refs?.[0] || finding.target
      if (label) seen.add(label)
    }
    return Array.from(seen).sort()
  }, [enrichedFindings])

  const uniqueKinds = useMemo(() => {
    const seen = new Set<string>()
    for (const finding of enrichedFindings) {
      if (finding.finding_kind) seen.add(finding.finding_kind)
    }
    return Array.from(seen).sort()
  }, [enrichedFindings])

  const uniqueAnalystStatuses = useMemo(() => {
    const seen = new Set<string>()
    for (const finding of enrichedFindings) {
      if (finding.analyst_status) seen.add(finding.analyst_status)
    }
    return Array.from(seen).sort()
  }, [enrichedFindings])

  const filteredFindings = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()

    const tz = getCurrentTimeZone()
    const dateFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: tz })

    return enrichedFindings.filter((finding) => {
      const matchesSeverity = filterSeverity === 'all' || finding.severity === filterSeverity
      const matchesTarget = filterTarget === 'all' || finding.target === filterTarget
      const matchesScanner = filterScanner === 'all' || finding.plugin_id === filterScanner
      const assetLabel = finding.asset_id || finding.asset_refs?.[0] || finding.target
      const matchesAsset = filterAsset === 'all' || assetLabel === filterAsset
      const matchesKind = filterKind === 'all' || finding.finding_kind === filterKind
      const matchesAnalystStatus = filterAnalystStatus === 'all' || finding.analyst_status === filterAnalystStatus
      const matchesValidated = !filterValidatedOnly || Boolean(finding.validated)
      const matchesHighConfidence = !filterHighConfidence || Number(finding.confidence || 0) >= 0.75

      if (dateFrom || dateTo) {
        const parsed = parseDateSafe(finding.discovered_at)
        if (!parsed) return false
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

      return (
        matchesSeverity &&
        matchesTarget &&
        matchesScanner &&
        matchesAsset &&
        matchesKind &&
        matchesAnalystStatus &&
        matchesValidated &&
        matchesHighConfidence &&
        haystack.includes(query)
      )
    })
  }, [enrichedFindings, filterSeverity, filterTarget, filterScanner, filterAsset, filterKind, filterAnalystStatus, filterValidatedOnly, filterHighConfidence, searchQuery, dateFrom, dateTo])

  // ── Multi-select export state & handlers ───────────────────────────────────
  const visibleIds = useMemo(() => filteredFindings.map((f) => f.id), [filteredFindings])
  const isAllSelected = useMemo(() => {
    if (visibleIds.length === 0) return false
    return visibleIds.every((id) => selectedIds.has(id))
  }, [visibleIds, selectedIds])

  const handleSelectAllToggle = () => {
    if (isAllSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        visibleIds.forEach((id) => next.delete(id))
        return next
      })
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev)
        visibleIds.forEach((id) => next.add(id))
        return next
      })
    }
  }

  const handleCheckboxChange = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })
  }

  const handleExportCSV = () => {
    const selectedFindings = findings.filter((f) => selectedIds.has(f.id))
    exportFindingsAsCSV(selectedFindings)
  }

  const handleExportJSON = () => {
    const selectedFindings = findings.filter((f) => selectedIds.has(f.id))
    exportFindingsAsJSON(selectedFindings)
  }

  const sortedFindings = useMemo(() => {
    const items = [...filteredFindings]
    switch (sortMode) {
      case 'risk':
        return items.sort((a, b) => {
          const ra = a.risk_score ?? 0
          const rb = b.risk_score ?? 0
          return rb - ra
        })
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
        return items
    }
  }, [filteredFindings, sortMode])

  // Build the flat virtual row list: header + findings per severity group
  // For non-severity sort modes, all findings appear in a single flat list
  const virtualRows = useMemo<VirtualRow[]>(() => {
    const rows: VirtualRow[] = []
    if (sortMode === 'severity') {
      for (const severity of severityOrder) {
        const items = filteredFindings.filter((f) => f.severity === severity)
        if (items.length === 0) continue
        rows.push({ kind: 'header', severity, count: items.length })
        items.forEach((finding, idx) => {
          rows.push({
            kind: 'finding',
            finding,
            isLastInGroup: idx === items.length - 1,
          })
        })
      }
    } else {
      // For newest/oldest/target sort — single flat list, no headers
      sortedFindings.forEach((finding, idx) => {
        rows.push({
          kind: 'finding',
          finding,
          isLastInGroup: idx === sortedFindings.length - 1,
        })
      })
    }
    return rows
  }, [filteredFindings, sortedFindings, sortMode])

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

  const selectedFinding =
    sortedFindings.find((finding) => finding.id === selectedFindingId) ??
    sortedFindings[0] ??
    null

  useEffect(() => {
    if (!selectedFinding) {
      setSelectedFindingId(null)
      return
    }
    if (!sortedFindings.some((finding) => finding.id === selectedFinding.id)) {
      setSelectedFindingId(sortedFindings[0]?.id ?? null)
    }
  }, [sortedFindings, selectedFinding])

  // Derives a flat list of active filter chips from non-default filter state.
  const activeFilters = useMemo(() => {
    const chips: { key: string; label: string }[] = []
    if (searchQuery.trim())      chips.push({ key: 'search',  label: `Search: "${searchQuery.trim()}"` })
    if (filterTarget !== 'all')  chips.push({ key: 'target',  label: `Target: ${filterTarget}` })
    if (filterScanner !== 'all') chips.push({ key: 'scanner', label: `Scanner: ${filterScanner}` })
    if (filterAsset !== 'all') chips.push({ key: 'asset', label: `Asset: ${filterAsset}` })
    if (filterKind !== 'all') chips.push({ key: 'kind', label: `Kind: ${filterKind}` })
    if (filterAnalystStatus !== 'all') chips.push({ key: 'analyst', label: `Analyst: ${filterAnalystStatus}` })
    if (filterValidatedOnly) chips.push({ key: 'validated', label: 'Validated Only' })
    if (filterHighConfidence) chips.push({ key: 'confidence', label: 'High Confidence' })
    if (sortMode !== 'risk') chips.push({ key: 'sort',    label: `Sort: ${sortMode}` })
    if (dateFrom)                chips.push({ key: 'from',    label: `From: ${dateFrom}` })
    if (dateTo)                  chips.push({ key: 'to',      label: `To: ${dateTo}` })
    return chips
  }, [searchQuery, filterTarget, filterScanner, filterAsset, filterKind, filterAnalystStatus, filterValidatedOnly, filterHighConfidence, sortMode, dateFrom, dateTo])

  function resetAllFilters() {
    setFilterSeverity('all')
    setFilterTarget('all')
    setFilterScanner('all')
    setFilterAsset('all')
    setFilterKind('all')
    setFilterAnalystStatus('all')
    setFilterValidatedOnly(false)
    setFilterHighConfidence(false)
    setSortMode('risk')
    setDateFrom('')
    setDateTo('')
    setSearchQuery('')
    setSelectedIds(new Set())
  }

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

  async function loadMore() {
    if (loadingMore) return
    setLoadingMore(true)
    const nextPage = page + 1
    try {
      const data = await getFindings(nextPage, perPage)
      const moreFindings = (data.findings || []) as Finding[]
      if (moreFindings.length > 0) {
        setFindings((prev) => [...prev, ...moreFindings])
        setPage(nextPage)
      }
    } finally {
      setLoadingMore(false)
    }
  }

  // ─── Keyboard navigation ────────────────────────────────────────────────────

  function handleListKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (!sortedFindings.length) return
    const currentIdx = selectedFinding
      ? sortedFindings.findIndex((f) => f.id === selectedFinding.id)
      : -1

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = sortedFindings[Math.min(currentIdx + 1, sortedFindings.length - 1)]
      if (next) setSelectedFindingId(next.id)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prev = sortedFindings[Math.max(currentIdx - 1, 0)]
      if (prev) setSelectedFindingId(prev.id)
    }
}

  // ─── Virtualizer ────────────────────────────────────────────────────────────
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: virtualRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => ROW_HEIGHTS[virtualRows[index]?.kind ?? 'finding'],
    overscan: 6,
  })

  // Scroll selected finding into view when it changes
  useEffect(() => {
    if (!selectedFinding) return
    const rowIdx = virtualRows.findIndex(
      (row) => row.kind === 'finding' && row.finding.id === selectedFinding.id,
    )
    if (rowIdx !== -1) {
      virtualizer.scrollToIndex(rowIdx, { align: 'auto', behavior: 'smooth' })
    }
  }, [selectedFindingId]) // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="min-h-screen bg-charcoal-dark text-silver px-4 py-6 md:px-8 md:py-10">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8">
        {/* Header */}
        <header className="border-b-4 border-silver-bright/10 pb-8">
          <div className="mb-4 inline-block bg-rag-red px-4 py-1 text-xs font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Triage Workspace v5.1
          </div>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="space-y-3">
              <h1 className="text-5xl font-black uppercase tracking-tighter text-silver-bright italic md:text-7xl">
                Findings <span className="text-transparent" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Desk</span>
              </h1>
              <p className="text-xs font-mono uppercase tracking-[0.24em] text-silver/45">
                Active triage feed // {triageMetrics.total} total signals // {triageMetrics.unresolved} awaiting analyst action
              </p>
            </div>

            <div className="grid w-full gap-3 sm:grid-cols-2 xl:w-auto xl:grid-cols-4">
              {[
                { label: 'Visible', value: triageMetrics.visible, tone: 'text-silver-bright' },
                { label: 'Critical + High', value: triageMetrics.active, tone: 'text-rag-red' },
                { label: 'Unresolved', value: triageMetrics.unresolved, tone: 'text-rag-amber' },
                { label: 'Reviewed', value: enrichedFindings.filter((finding) => finding.status === 'reviewed').length, tone: 'text-rag-green' },
              ].map((metric) => (
                <div
                  key={metric.label}
                  className="border-2 border-black bg-charcoal px-4 py-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]"
                >
                  <p className="mb-2 text-[10px] font-black uppercase tracking-[0.25em] text-silver/55">{metric.label}</p>
                  <p className={`text-3xl font-black italic tracking-tight ${metric.tone}`}>{String(metric.value).padStart(2, '0')}</p>
                </div>
              ))}
            </div>
          </div>
        </header>

        {/* Filter Bar */}
        <section className="border-2 border-black bg-charcoal/95 p-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] backdrop-blur lg:sticky lg:top-4 lg:z-20">
          <div className="grid gap-4">
            <div className="grid gap-4 2xl:grid-cols-[minmax(320px,1fr)_auto] 2xl:items-end">
              <div className="space-y-2">
                <label className={filterLabelClass}>Search</label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Title, target, CVE, remediation..."
                    className={`${filterControlClass} px-4 pr-12 placeholder:text-silver/20`}
                  />
                  {searchQuery.trim() && (
                    <button
                      type="button"
                      aria-label="Clear search"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-silver/50 hover:text-silver-bright transition"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 pb-2 sm:pb-0 2xl:max-w-[760px] 2xl:justify-end">
                <button
                  type="button"
                  onClick={() => setFilterSeverity('all')}
                  className={`min-h-10 border px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] transition-all ${filterPillClasses(filterSeverity === 'all')}`}
                >
                  All
                </button>
                {severityOrder.map((severity) => (
                  <button
                    key={severity}
                    type="button"
                    onClick={() => setFilterSeverity((current) => (current === severity ? 'all' : severity))}
                    className={`min-h-10 border px-3 py-2 text-[10px] font-black uppercase tracking-[0.18em] transition-all ${
                      filterSeverity === severity
                        ? `${severityConfig[severity].chip} border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]`
                        : 'border-silver-bright/10 bg-charcoal-dark text-silver/65 hover:border-silver-bright/30'
                    }`}
                  >
                    {severityConfig[severity].label} {countsBySeverity[severity] || 0}
                  </button>
                ))}

                {/* Severity scale legend — help affordance (issue #835) */}
                <div className="relative" ref={legendRef}>
                  <button
                    ref={legendButtonRef}
                    type="button"
                    onClick={() => setLegendOpen((open) => !open)}
                    aria-label="What do the severity levels mean?"
                    aria-expanded={legendOpen}
                    aria-haspopup="dialog"
                    aria-controls="severity-legend-popover"
                    className={`flex min-h-10 items-center justify-center border px-2 transition-all ${filterPillClasses(legendOpen)}`}
                  >
                    <span className="material-symbols-outlined text-base" aria-hidden="true">help</span>
                  </button>

                  <AnimatePresence>
                    {legendOpen && (
                      <motion.div
                        id="severity-legend-popover"
                        role="dialog"
                        aria-label="Severity scale legend"
                        initial={{ opacity: 0, y: -8, scaleY: 0.96 }}
                        animate={{ opacity: 1, y: 0, scaleY: 1, transition: { duration: 0.18, ease: 'easeOut' as const } }}
                        exit={{ opacity: 0, y: -6, scaleY: 0.97, transition: { duration: 0.12, ease: 'easeOut' as const } }}
                        style={{ transformOrigin: 'top right' }}
                        className="absolute right-0 top-full z-[60] mt-2 w-[min(20rem,calc(100vw-2rem))] border-4 border-black bg-charcoal shadow-[10px_10px_0px_0px_rgba(0,0,0,1)]"
                      >
                        <div className="flex items-center justify-between border-b-2 border-black px-4 py-3">
                          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-silver-bright">
                            Severity_Scale
                          </p>
                          <button
                            type="button"
                            aria-label="Close severity legend"
                            onClick={() => {
                              setLegendOpen(false)
                              legendButtonRef.current?.focus()
                            }}
                            className="text-silver/40 transition-colors hover:text-silver-bright"
                          >
                            <span className="material-symbols-outlined text-base" aria-hidden="true">close</span>
                          </button>
                        </div>

                        <p className="border-b border-silver-bright/10 px-4 py-2 text-[9px] font-mono uppercase tracking-[0.18em] text-silver/45">
                          Ordered highest → lowest risk
                        </p>

                        <ul className="space-y-3 px-4 py-3">
                          {severityLegend.map(({ id, blurb }) => (
                            <li key={id} className="flex items-start gap-3">
                              <span
                                className={`mt-1 h-3 w-3 shrink-0 rotate-45 ${severityConfig[id].rail}`}
                                aria-hidden="true"
                              />
                              <div className="min-w-0">
                                <p className={`text-[11px] font-black uppercase tracking-[0.18em] ${severityConfig[id].accent}`}>
                                  {severityConfig[id].label}
                                </p>
                                <p className="mt-0.5 text-[10px] font-mono leading-snug text-silver/55">
                                  {blurb}
                                </p>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-8">
                <div className="space-y-2">
                  <label className={filterLabelClass}>Target</label>
                  <select
                    value={filterTarget}
                    onChange={(e) => setFilterTarget(e.target.value)}
                    className={filterControlClass}
                  >
                    <option value="all">All Targets</option>
                    {uniqueTargets.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>Scanner / Tool</label>
                  <select
                    value={filterScanner}
                    onChange={(e) => setFilterScanner(e.target.value)}
                    className={filterControlClass}
                  >
                    <option value="all">All Scanners</option>
                    {uniqueScanners.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>Asset</label>
                  <select
                    value={filterAsset}
                    onChange={(e) => setFilterAsset(e.target.value)}
                    className={filterControlClass}
                  >
                    <option value="all">All Assets</option>
                    {uniqueAssets.map((asset) => (
                      <option key={asset} value={asset}>{asset}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>Finding Kind</label>
                  <select
                    value={filterKind}
                    onChange={(e) => setFilterKind(e.target.value)}
                    className={filterControlClass}
                  >
                    <option value="all">All Kinds</option>
                    {uniqueKinds.map((kind) => (
                      <option key={kind} value={kind}>{kind}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>Analyst State</label>
                  <select
                    value={filterAnalystStatus}
                    onChange={(e) => setFilterAnalystStatus(e.target.value)}
                    className={filterControlClass}
                  >
                    <option value="all">All States</option>
                    {uniqueAnalystStatuses.map((status) => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>Sort By</label>
                  <select
                    value={sortMode}
                    onChange={(e) => setSortMode(e.target.value as SortMode)}
                    className={filterControlClass}
                  >
                    <option value="risk">Risk Score (High → Low)</option>
                    <option value="severity">Severity (High → Low)</option>
                    <option value="newest">Newest First</option>
                    <option value="oldest">Oldest First</option>
                    <option value="target">Target (A → Z)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className={`${filterControlClass} [color-scheme:dark]`}
                  />
                </div>

                <div className="space-y-2">
                  <label className={filterLabelClass}>To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className={`${filterControlClass} [color-scheme:dark]`}
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <label className="inline-flex h-11 items-center gap-3 border border-silver-bright/10 bg-charcoal-dark px-4 text-[10px] font-black uppercase tracking-[0.18em] text-silver/75">
                  <input
                    type="checkbox"
                    checked={filterValidatedOnly}
                    onChange={(event) => setFilterValidatedOnly(event.target.checked)}
                    className="h-4 w-4 accent-[var(--accent-rag-red)]"
                  />
                  Validated Only
                </label>
                <label className="inline-flex h-11 items-center gap-3 border border-silver-bright/10 bg-charcoal-dark px-4 text-[10px] font-black uppercase tracking-[0.18em] text-silver/75">
                  <input
                    type="checkbox"
                    checked={filterHighConfidence}
                    onChange={(event) => setFilterHighConfidence(event.target.checked)}
                    className="h-4 w-4 accent-[var(--accent-rag-blue)]"
                  />
                  High Confidence
                </label>
                <SavedViewsPanel
                  views={views}
                  loading={viewsLoading}
                  saveView={saveView}
                  deleteView={deleteView}
                  renameView={renameView}
                  currentPreset={currentPreset}
                  onApply={applyPreset}
                />
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowColumnChooser(!showColumnChooser)}
                    className="h-11 border border-silver-bright/20 bg-charcoal-dark px-4 text-[10px] font-black uppercase tracking-[0.18em] text-silver/75"
                  >
                    Columns
                  </button>

                  {showColumnChooser && (
                    <div className="absolute right-0 top-12 z-50 w-56 border border-black bg-charcoal-dark p-3 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                      {Object.entries(columnVisibility).map(([key, value]) => (
                        <label
                          key={key}
                          className="mb-2 flex items-center gap-2 text-xs text-silver-bright"
                        >
                          <input
                            type="checkbox"
                            checked={value}
                            onChange={() =>
                              setColumnVisibility((prev) => ({
                                ...prev,
                                [key]: !prev[key as keyof typeof prev],
                              }))
                            }
                          />
                          {columnLabels[key as keyof typeof columnLabels]}
                        </label>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={resetAllFilters}
                  className="h-11 w-full border border-silver-bright/20 bg-charcoal-dark px-4 text-[10px] font-black uppercase tracking-[0.18em] text-silver/65 transition-all hover:border-rag-red hover:text-silver-bright xl:w-auto xl:min-w-[180px]"
                >
                  Reset Filters
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ── Active filter summary strip ── */}
        {activeFilters.length > 0 && (
          <div
            aria-label="active filters"
            className="flex flex-wrap items-center gap-2 border border-silver-bright/10 bg-charcoal/60 px-4 py-3"
          >
            <span className="mr-1 text-[10px] font-black uppercase tracking-[0.2em] text-silver/40">
              Active Filters
            </span>
            {activeFilters.map(({ key, label }) => (
              <span
                key={key}
                className="border border-rag-red/30 bg-rag-red/10 px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-rag-red"
              >
                {label}
              </span>
            ))}
          </div>
        )}

        {/* Main Split Layout */}
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.2fr)_420px]">
          {/* ── Virtualized Findings List ── */}
          <motion.section variants={sectionVariants} initial="hidden" animate="visible">
            {loading ? (
              <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 px-6 py-16 text-center">
                <p className="text-sm font-mono uppercase tracking-[0.25em] text-silver/50">Synchronizing findings feed...</p>
              </div>
            ) : filteredFindings.length === 0 ? (
              <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 px-6 py-20 text-center">
                <p className="text-2xl font-black uppercase tracking-[0.25em] text-silver/25 italic">No Findings Match</p>
                <p className="mt-3 text-xs font-mono uppercase tracking-[0.2em] text-silver/15">Adjust filters to reopen the queue.</p>
              </div>
            ) : (
              <>
                {/* Selection & Export Toolbar */}
                <div className="flex flex-wrap items-center justify-between gap-4 border-2 border-black bg-charcoal p-4 mb-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="select-all-findings"
                      checked={isAllSelected}
                      onChange={handleSelectAllToggle}
                      className="h-4 w-4 accent-[var(--accent-rag-red)] cursor-pointer"
                    />
                    <label
                      htmlFor="select-all-findings"
                      className="text-xs font-black uppercase tracking-wider text-silver-bright cursor-pointer select-none"
                    >
                      Select All Visible ({filteredFindings.length})
                    </label>
                    {selectedIds.size > 0 && (
                      <span className="text-[10px] font-mono uppercase tracking-wider text-silver/50 bg-charcoal-dark px-2 py-0.5 border border-silver-bright/10 ml-2">
                        {selectedIds.size} Selected
                      </span>
                    )}
                  </div>

                  {selectedIds.size > 0 && (
                    <div className="relative">
                      <button
                        type="button"
                        id="bulk-export-btn"
                        onClick={() => setExportDropdownOpen(!exportDropdownOpen)}
                        className="bg-rag-blue text-black border-2 border-black px-4 py-2 text-xs font-black uppercase tracking-wider shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:bg-rag-blue/90 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all flex items-center gap-2"
                      >
                        Bulk Export
                        <span className="material-symbols-outlined text-sm">arrow_drop_down</span>
                      </button>
                      {exportDropdownOpen && (
                        <div className="absolute right-0 mt-2 w-48 border-2 border-black bg-charcoal-dark shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] z-30">
                          <button
                            type="button"
                            onClick={() => {
                              handleExportCSV()
                              setExportDropdownOpen(false)
                            }}
                            className="w-full text-left px-4 py-3 text-xs font-mono uppercase tracking-wider text-silver-bright hover:bg-silver-bright/10 transition-all border-b border-black"
                          >
                            Export as CSV
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              handleExportJSON()
                              setExportDropdownOpen(false)
                            }}
                            className="w-full text-left px-4 py-3 text-xs font-mono uppercase tracking-wider text-silver-bright hover:bg-silver-bright/10 transition-all"
                          >
                            Export as JSON
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div
                  ref={parentRef}
                  role="listbox"
                  aria-label="Findings list"
                  tabIndex={0}
                  onKeyDown={handleListKeyDown}
                  className="border-2 border-black bg-charcoal shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] focus:outline-none focus:ring-2 focus:ring-rag-red/40"
                  style={{ height: '72vh', overflowY: 'auto' }}
                >
                {/* Virtualizer inner container */}
                <div
                  style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}
                >
                  {virtualizer.getVirtualItems().map((virtualItem) => {
                    const row = virtualRows[virtualItem.index]

                    return (
                      <div
                        key={virtualItem.key}
                        data-index={virtualItem.index}
                        ref={virtualizer.measureElement}
                        style={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          transform: `translateY(${virtualItem.start}px)`,
                        }}
                      >
                        {row.kind === 'header' ? (
                          /* ── Severity group header ── */
                          <div className="flex w-full items-center justify-between border-b border-silver-bright/8 px-5 py-4 bg-charcoal">
                            <div className="flex items-center gap-4">
                              <span className={`h-3 w-3 rotate-45 ${severityConfig[row.severity].rail}`} />
                              <div>
                                <p className={`text-lg font-black uppercase tracking-[0.18em] ${severityConfig[row.severity].accent}`}>
                                  {severityConfig[row.severity].label}
                                </p>
                                <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-silver/40">
                                  {row.count} visible in queue
                                </p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          /* ── Finding row ── */
                          (() => {
                            const { finding, isLastInGroup } = row
                            const isSelected = selectedFinding?.id === finding.id
                            const config = severityConfig[finding.severity]

                            return (
                              <div
                                key={finding.id}
                                className={`relative flex items-stretch w-full transition-all ${
                                  !isLastInGroup ? 'border-b border-silver-bright/6' : ''
                                } ${isSelected ? 'bg-silver-bright/6' : 'hover:bg-silver-bright/3'}`}
                              >
                                {/* Checkbox column */}
                                <div className="pl-4 pr-1 flex items-center justify-center">
                                  <input
                                    type="checkbox"
                                    aria-label={`Select ${finding.title}`}
                                    checked={selectedIds.has(finding.id)}
                                    onChange={(e) => handleCheckboxChange(finding.id, e.target.checked)}
                                    className="h-4 w-4 accent-[var(--accent-rag-red)] cursor-pointer"
                                  />
                                </div>

                                {/* Details button */}
                                <button
                                  type="button"
                                  role="option"
                                  aria-selected={isSelected}
                                  onClick={() => setSelectedFindingId(finding.id)}
                                  className="relative block flex-1 px-5 py-5 text-left transition-all focus:outline-none"
                                >
                                  <span className={`absolute inset-y-0 left-0 w-1 ${config.rail}`} />
                                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                                    <div className="min-w-0 flex-1 space-y-3 pl-3">
                                      <div className="flex flex-wrap items-center gap-2">
                                        <span className={`px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${config.chip}`}>
                                          {config.label}
                                        </span>
                                        <span className={`border px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${getStatusTone(finding.status)}`}>
                                          {finding.status}
                                        </span>
                                        {columnVisibility.category && (
                                          <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-silver/35">
                                            {finding.category || 'Uncategorized'}
                                          </span>
                                        )}
                                        {columnVisibility.findingKind && finding.finding_kind ? (
                                          <span className="border border-silver-bright/10 bg-charcoal-dark px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-silver/70">
                                            {finding.finding_kind.replace('_', ' ')}
                                          </span>
                                        ) : null}
                                        {columnVisibility.cve && finding.cve ? (
                                          <span className="border border-rag-blue/20 bg-rag-blue/10 px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-rag-blue">
                                            {finding.cve}
                                          </span>
                                        ) : null}
                                        {columnVisibility.confidence && typeof finding.confidence === 'number' ? (
                                          <span className="border border-silver-bright/10 bg-charcoal-dark px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-silver-bright">
                                            {(finding.confidence * 100).toFixed(0)}% confidence
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
                                      {columnVisibility.occurrenceCount && typeof finding.occurrence_count === 'number' && finding.occurrence_count > 1 ? (
                                        <div className="text-right">
                                          <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Seen</p>
                                          <p className="text-2xl font-black italic text-silver-bright">
                                            {finding.occurrence_count}
                                          </p>
                                        </div>
                                      ) : null}
                                      {columnVisibility.cvss && typeof finding.cvss === 'number' ? (
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
                              </div>
                            )
                          })()
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
              {!loading && findings.length < totalItems && (
                <div className="flex justify-center py-6">
                  <button
                    type="button"
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="bg-silver-bright px-6 py-3 text-[11px] font-black uppercase tracking-[0.18em] text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all active:translate-x-0.5 active:translate-y-0.5 active:shadow-none disabled:opacity-50"
                  >
                    {loadingMore ? 'Loading...' : `Load More (${findings.length}/${totalItems})`}
                  </button>
                </div>
              )}
            </>
          )}
          </motion.section>

          {/* ── Detail Panel (unchanged) ── */}
          <motion.aside variants={sectionVariants} initial="hidden" animate="visible" className="xl:sticky xl:top-32 xl:self-start">
            <div className="border-4 border-black bg-charcoal shadow-[10px_10px_0px_0px_rgba(0,0,0,1)]">
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
                      <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Selected Finding</p>
                      <h2 className="text-3xl font-black uppercase italic tracking-tight text-silver-bright">{selectedFinding.title}</h2>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Target</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">{selectedFinding.target || 'Unknown'}</p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Asset</p>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright break-all">
                          {selectedFinding.asset_id || selectedFinding.asset_refs?.[0] || 'N/A'}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Category</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">{selectedFinding.category || 'Uncategorized'}</p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Finding Kind</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {selectedFinding.finding_kind?.replace('_', ' ') || 'N/A'}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Observed</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {formatLocaleDate(selectedFinding.discovered_at)}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">CVSS</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {typeof selectedFinding.cvss === 'number' ? selectedFinding.cvss.toFixed(1) : 'N/A'}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Validation</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {selectedFinding.validated ? 'Validated' : selectedFinding.validation_method || 'Unvalidated'}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Analyst State</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {selectedFinding.analyst_status || 'N/A'}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">CPE</p>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {selectedFinding.cpe || 'N/A'}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Seen Across Scans</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {selectedFinding.occurrence_count || 1}
                        </p>
                      </div>
                      <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                        <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Evidence Count</p>
                        <p className="mt-2 text-sm font-mono uppercase tracking-[0.14em] text-silver-bright">
                          {selectedFinding.evidence_count || selectedFinding.evidence?.length || 0}
                        </p>
                      </div>
                    </div>

                    {typeof selectedFinding.risk_score === 'number' && (
                      <div className="border-2 border-black bg-charcoal-dark p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        <div className="flex items-center justify-between">
                          <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Risk Score</p>
                          <p className={`text-2xl font-black italic ${
                            selectedFinding.risk_score >= 7 ? 'text-rag-red' :
                            selectedFinding.risk_score >= 4 ? 'text-rag-amber' : 'text-rag-blue'
                          }`}>
                            {selectedFinding.risk_score.toFixed(1)}
                          </p>
                        </div>
                        {selectedFinding.risk_factors && selectedFinding.risk_factors.length > 0 && (
                          <div className="mt-3 space-y-1.5 border-t border-silver-bright/8 pt-3">
                            {selectedFinding.risk_factors.map((rf) => (
                              <div key={rf.factor} className="flex items-center justify-between text-[10px]">
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="font-black uppercase tracking-[0.15em] text-silver/45">{rf.label}</span>
                                  <span className="text-silver/30 text-[9px] font-mono">({(rf.weight * 100).toFixed(0)}%)</span>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  <span className="font-mono text-silver-bright">{rf.score.toFixed(1)}</span>
                                  <span className={`text-[9px] font-mono ${
                                    rf.contribution >= 2 ? 'text-rag-red' :
                                    rf.contribution >= 1 ? 'text-rag-amber' : 'text-silver/40'
                                  }`}>
                                    +{rf.contribution.toFixed(1)}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="space-y-5">
                    <div>
                      <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Evidence Brief</p>
                      <div className="border-l-4 border-rag-red bg-charcoal-dark p-4">
                        <p className="text-sm leading-relaxed text-silver/78">{selectedFinding.description || 'No description provided.'}</p>
                        {selectedFinding.confidence_reason ? (
                          <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.12em] text-silver/45">
                            {selectedFinding.confidence_reason}
                          </p>
                        ) : null}
                      </div>
                    </div>

                    {selectedFinding.evidence && selectedFinding.evidence.length > 0 ? (
                      <div>
                        <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Evidence Items</p>
                        <div className="space-y-2">
                          {selectedFinding.evidence.slice(0, 5).map((item, index) => (
                            <div key={`${selectedFinding.id}-evidence-${index}`} className="border border-silver-bright/8 bg-charcoal-dark p-3 text-[11px] font-mono text-silver/72">
                              <p className="text-[10px] uppercase tracking-[0.18em] text-silver/35">
                                {String(item.label || item.type || 'evidence')}
                              </p>
                              <p className="mt-2 break-words whitespace-pre-wrap text-silver-bright">
                                {String(item.value ?? '')}
                              </p>
                              <p className="mt-2 text-[9px] uppercase tracking-[0.16em] text-silver/30">
                                {String(item.source || 'scanner')} {item.confidence ? `// ${(Number(item.confidence) * 100).toFixed(0)}%` : ''}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {selectedFinding.corroborating_sources && selectedFinding.corroborating_sources.length > 0 ? (
                      <div>
                        <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Corroborating Sources</p>
                        <div className="flex flex-wrap gap-2">
                          {selectedFinding.corroborating_sources.map((source) => (
                            <span key={source} className="border border-silver-bright/10 bg-charcoal-dark px-2 py-1 text-[9px] font-mono uppercase tracking-[0.15em] text-silver-bright">
                              {source}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <div>
                      <p className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Remediation</p>
                      <div className="border-l-4 border-rag-green bg-charcoal-dark p-4">
                        <p className="text-sm leading-relaxed text-rag-green/85">
                          {selectedFinding.remediation || 'No remediation guidance captured.'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3 border-t border-silver-bright/8 pt-5">
                    <p className="text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Workflow Actions</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => updateFindingStatus(selectedFinding.id, 'reviewed')}
                        className="bg-silver-bright px-4 py-3 text-[10px] font-black uppercase tracking-[0.18em] text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
                      >
                        Mark Reviewed
                      </button>
                      <button
                        type="button"
                        onClick={() => updateFindingStatus(selectedFinding.id, 'new')}
                        className="border border-rag-amber/25 bg-rag-amber/10 px-4 py-3 text-[10px] font-black uppercase tracking-[0.18em] text-rag-amber"
                      >
                        Reopen
                      </button>
                      <button
                        type="button"
                        onClick={() => updateFindingStatus(selectedFinding.id, 'suppressed')}
                        className="border border-silver/20 bg-silver/5 px-4 py-3 text-[10px] font-black uppercase tracking-[0.18em] text-silver"
                      >
                        Suppress
                      </button>
                      <button
                        type="button"
                        onClick={() => copyFindingSummary(selectedFinding)}
                        className="border border-rag-blue/25 bg-rag-blue/10 px-4 py-3 text-[10px] font-black uppercase tracking-[0.18em] text-rag-blue"
                      >
                        {copiedFindingId === selectedFinding.id ? 'Copied' : 'Copy Brief'}
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="px-6 py-16 text-center">
                  <p className="text-2xl font-black uppercase tracking-[0.22em] text-silver/20 italic">Queue Clear</p>
                  <p className="mt-3 text-xs font-mono uppercase tracking-[0.2em] text-silver/15">
                    Select a finding to review evidence and remediation.
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
