import React, { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useVirtualizer } from '@tanstack/react-virtual'
import { getFindings, FindingsResponse } from '../api'
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
    accent: 'text-rag-green',
    chip: 'bg-rag-green text-black',
    rail: 'bg-rag-green',
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
    ? 'border-black bg-white text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
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
      .then((data: FindingsResponse) => {
      .catch(err => console.error(err))