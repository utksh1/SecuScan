import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getDashboardSummary, getHealth, cancelTask, startTask } from '../api'
import { ExecutiveStatsBar } from '../components/ExecutiveStatsBar'
import { routePath, routes } from '../routes'

type Finding = {
  id: string
  severity: string
  title: string
  target: string
  discovered_at: string
}

type Task = {
  id: string
  plugin_id: string
  tool_name: string
  target: string
  status: string
  created_at: string
  duration_seconds?: number | null
}

type Asset = {
  id: string
  target: string
  description: string
  risk_level: string
  last_scanned: string
}

type Summary = {
  total_assets: number
  active_assets: number
  critical_assets: number
  total_attack_surface: number
  total_findings: number
  critical_findings: number
  high_findings: number
  medium_findings: number
  low_findings: number
  info_findings: number
  last_scan_time: string | null
  recent_findings: Finding[]
  running_tasks: Task[]
  recent_tasks: Task[]
  has_high_risk_assets: boolean
  high_risk_assets: Asset[]
  attack_surface_by_category: Record<string, number>
  scan_activity: { total: number; completed: number; running: number }
}

function asString(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback
}

function asNumber(value: unknown, fallback = 0) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asOptionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function parseDateSafe(rawValue: string | null | undefined): Date | null {
  if (!rawValue) return null
  const raw = rawValue.trim()
  if (!raw) return null
  if (raw.toLowerCase() === 'now') return new Date()

  // Handle SQLite DATETIME ("YYYY-MM-DD HH:MM:SS"), ISO strings, and timezone-less values.
  const sqliteAsIso = raw.includes('T') ? raw : raw.replace(' ', 'T')
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(sqliteAsIso)
  const candidates = hasTimezone
    ? [sqliteAsIso, raw]
    : [`${sqliteAsIso}Z`, sqliteAsIso, raw]

  for (const value of candidates) {
    const parsed = new Date(value)
    if (!Number.isNaN(parsed.getTime())) return parsed
  }

  return null
}

function normalizeSummary(data: Partial<Summary> | null | undefined): Summary {
  const summary = data && typeof data === 'object' ? data : {}
  const rawScanActivity = summary.scan_activity && typeof summary.scan_activity === 'object'
    ? summary.scan_activity
    : emptySummary.scan_activity

  return {
    total_assets: asNumber(summary.total_assets),
    active_assets: asNumber(summary.active_assets),
    critical_assets: asNumber(summary.critical_assets),
    total_attack_surface: asNumber(summary.total_attack_surface),
    total_findings: asNumber(summary.total_findings),
    critical_findings: asNumber(summary.critical_findings),
    high_findings: asNumber(summary.high_findings),
    medium_findings: asNumber(summary.medium_findings),
    low_findings: asNumber(summary.low_findings),
    info_findings: asNumber(summary.info_findings),
    last_scan_time: typeof summary.last_scan_time === 'string' ? summary.last_scan_time : null,
    recent_findings: Array.isArray(summary.recent_findings)
      ? summary.recent_findings.map((finding) => ({
        id: asString(finding?.id),
        severity: asString(finding?.severity, 'low'),
        title: asString(finding?.title, 'Untitled finding'),
        target: asString(finding?.target, 'Unknown target'),
        discovered_at: asString(finding?.discovered_at),
      }))
      : [],
    running_tasks: Array.isArray(summary.running_tasks)
      ? summary.running_tasks.map((task) => ({
        id: asString(task?.id),
        plugin_id: asString(task?.plugin_id),
        tool_name: asString(task?.tool_name, 'Unknown tool'),
        target: asString(task?.target, 'Unknown target'),
        status: asString(task?.status, 'unknown'),
        created_at: asString(task?.created_at),
        duration_seconds: asOptionalNumber(task?.duration_seconds),
      }))
      : [],
    recent_tasks: Array.isArray(summary.recent_tasks)
      ? summary.recent_tasks.map((task) => ({
        id: asString(task?.id),
        plugin_id: asString(task?.plugin_id),
        tool_name: asString(task?.tool_name, 'Unknown tool'),
        target: asString(task?.target, 'Unknown target'),
        status: asString(task?.status, 'unknown'),
        created_at: asString(task?.created_at),
        duration_seconds: asOptionalNumber(task?.duration_seconds),
      }))
      : [],
    high_risk_assets: Array.isArray(summary.high_risk_assets)
      ? summary.high_risk_assets.map((asset) => ({
        id: asString(asset?.id),
        target: asString(asset?.target, 'Unknown target'),
        description: asString(asset?.description),
        risk_level: asString(asset?.risk_level, 'low'),
        last_scanned: asString(asset?.last_scanned, new Date().toISOString()),
      }))
      : [],
    has_high_risk_assets: Boolean(summary.has_high_risk_assets),
    attack_surface_by_category:
      summary.attack_surface_by_category && typeof summary.attack_surface_by_category === 'object' && !Array.isArray(summary.attack_surface_by_category)
        ? Object.fromEntries(
          Object.entries(summary.attack_surface_by_category).map(([key, value]) => [key, asNumber(value)])
        )
        : {},
    scan_activity: {
      total: asNumber(rawScanActivity.total),
      completed: asNumber(rawScanActivity.completed),
      running: asNumber(rawScanActivity.running),
    },
  }
}

const emptySummary: Summary = {
  total_assets: 0,
  active_assets: 0,
  critical_assets: 0,
  total_attack_surface: 0,
  total_findings: 0,
  critical_findings: 0,
  high_findings: 0,
  medium_findings: 0,
  low_findings: 0,
  info_findings: 0,
  last_scan_time: null,
  recent_findings: [],
  running_tasks: [],
  recent_tasks: [],
  has_high_risk_assets: false,
  high_risk_assets: [],
  attack_surface_by_category: {},
  scan_activity: { total: 0, completed: 0, running: 0 },
}

function formatBriefingDate(dateStr: string | null) {
  const d = parseDateSafe(dateStr)
  if (!d) return '00 JAN, 26, 00:00 IST'
  const formatted = d.toLocaleString('en-US', {
    day: '2-digit',
    month: 'short',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Kolkata',
  }).toUpperCase()
  return `${formatted} IST`
}

function formatTaskInit(dateStr: string) {
  const parsed = parseDateSafe(dateStr)
  if (!parsed) return { date: 'UNKNOWN DATE', time: 'UNKNOWN TIME' }
  const date = parsed.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  }).toUpperCase()
  const time = parsed.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Asia/Kolkata',
  })
  return { date, time }
}

function formatDuration(seconds?: number | null) {
  if (seconds == null || !Number.isFinite(seconds) || seconds <= 0) return 'N/A'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs.toString().padStart(2, '0')}s`
}

function displayToolName(task: Task) {
  const name = task.tool_name?.trim()
  if (!name || name.toLowerCase() === 'history') {
    return (task.plugin_id || 'scan').replace(/[-_]/g, ' ').toUpperCase()
  }
  return name.toUpperCase()
}

function getRiskProfile(summary: Summary) {
  if (summary.critical_findings > 0) return { label: 'Severe', color: 'text-rag-red', accent: 'bg-rag-red' }
  if (summary.high_findings > 0 || summary.total_findings > 20) return { label: 'Moderate', color: 'text-rag-amber', accent: 'bg-rag-amber' }
  return { label: 'Stable', color: 'text-rag-green', accent: 'bg-rag-green' }
}

function severityTone(severity: string) {
  switch (severity) {
    case 'critical':
      return 'text-rag-red border-rag-red/20'
    case 'high':
      return 'text-rag-amber border-rag-amber/20'
    case 'medium':
      return 'text-silver-bright border-accent-silver/20'
    default:
      return 'text-rag-green border-rag-green/20'
  }
}

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.19, 1, 0.22, 1] as const },
  },
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary>(emptySummary)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null)
  const [targetNode, setTargetNode] = useState('127.0.0.1')
  const [initiating, setInitiating] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        await getHealth()
        if (!cancelled) setBackendConnected(true)
      } catch {
        if (!cancelled) {
          setBackendConnected(false)
          setError('Unable to reach the SecuScan backend')
          setLoading(false)
        }
        return
      }

      getDashboardSummary()
        .then((data) => {
          if (cancelled) return
          setSummary(normalizeSummary(data as Partial<Summary>))
          setError(null)
        })
        .catch((err) => {
          if (cancelled) return
          setError(err.message)
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }

    load()
    const interval = setInterval(load, 10000)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const handleAbort = async (taskId: string) => {
    try {
      await cancelTask(taskId)
      // Refresh summary immediately
      const data = await getDashboardSummary() as Summary
      setSummary(normalizeSummary(data))
    } catch (err) {
      console.error('Failed to abort task:', err)
    }
  }

  const handleStartMission = async (pluginId: string) => {
    if (!targetNode.trim()) return
    try {
      setInitiating(true)
      const res = await startTask(pluginId, { host: targetNode }, true)
      if (res.task_id) {
        navigate(routePath.task(res.task_id))
      }
    } catch (err) {
      console.error('Failed to start mission:', err)
      setError('Mission initiation failed. Check target node accessibility.')
    } finally {
      setInitiating(false)
    }
  }

  const risk = getRiskProfile(summary)
  const criticalHigh = summary.critical_findings + summary.high_findings
  const safeAssetsPercent = summary.total_assets > 0
    ? Math.max(0, Math.round(((summary.total_assets - summary.critical_assets) / summary.total_assets) * 100))
    : 100
  const progressWidth = summary.scan_activity.total > 0
    ? Math.max(8, Math.min(100, (summary.scan_activity.completed / summary.scan_activity.total) * 100))
    : 0
  const attackSurfaceBreakdown = Object.entries(summary.attack_surface_by_category).slice(0, 3)
  const coverageGaps = Math.max(0, summary.total_assets - summary.active_assets)
  const coveragePercent = summary.total_assets > 0
    ? Math.round((summary.active_assets / summary.total_assets) * 100)
    : 0
  const statusBadgeClasses = backendConnected === null
    ? 'border-accent-silver/10 bg-silver/5 text-silver-bright'
    : backendConnected
      ? 'border-rag-green/30 bg-rag-green/10 text-rag-green'
      : 'border-rag-red/30 bg-rag-red/10 text-rag-red'
  const statusLabel = backendConnected === null
    ? 'Checking Backend'
    : backendConnected
      ? 'Backend Connected'
      : 'Backend Offline'

  return (
    <div className="min-h-screen flex flex-col bg-charcoal-dark selection:bg-silver-bright selection:text-charcoal-dark">
      <header className="w-full px-6 md:px-12 pt-12 pb-12 flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between border-b-4 border-silver-bright/10 mb-12 font-black">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: [0.19, 1, 0.22, 1] }}
          className="space-y-4"
        >
          <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            SECUSCAN_WORKSPACE v2.4
          </div>
          <h1 className="text-5xl md:text-7xl lg:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic whitespace-nowrap">
            SecuScan <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Workspace</span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
            CENTRAL_INTELLIGENCE_OVERVIEW // ACTIVE_NODES: {summary.total_assets} // THREAT_LEVEL: {risk.label.toUpperCase()}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.8, ease: [0.19, 1, 0.22, 1] }}
          className="flex flex-col md:flex-row items-start md:items-center gap-8 md:gap-10"
        >
          {/* Integrity Metric - High Visibility */}
          <div className="flex items-center gap-6 px-6 py-4 bg-charcoal border-4 border-black shadow-[8px_8px_0px_0px_rgba(31,31,31,1)] group transition-all">
            <div className="flex flex-col items-end text-right">
              <span className="text-[11px] font-black text-silver-bright/90 uppercase tracking-[0.4em] italic mb-1">
                SYSTEM_STATUS_SYNC
              </span>
              <div className="flex items-baseline gap-6">
                <div className="flex items-baseline gap-3">
                  <span className="text-2xl font-mono text-silver-bright font-black tracking-tighter italic leading-none">
                    {formatBriefingDate(summary.last_scan_time).split(',')[0].toUpperCase() || 'NODATA'}
                  </span>
                  <span className="text-base font-mono text-rag-blue/90 font-black italic leading-none">
                    {formatBriefingDate(summary.last_scan_time).split(',')[1]?.trim() || '26'}
                  </span>
                </div>
                <div className="h-5 w-px bg-silver/20 self-center mx-1"></div>
                <span className="text-lg font-mono text-rag-blue font-black italic leading-none">
                  {formatBriefingDate(summary.last_scan_time).split(',')[2]?.trim() || '00:00'}
                </span>
              </div>
            </div>
            <div className="w-14 h-14 bg-charcoal-dark border-4 border-black flex items-center justify-center text-rag-blue shadow-inner group-hover:bg-rag-blue group-hover:text-black transition-all">
              <span className="material-symbols-outlined text-2xl font-black">database</span>
            </div>
          </div>

        </motion.div>
      </header>

      <main className="flex-1 px-6 md:px-12 pb-20 space-y-12 max-w-[1700px] w-full mx-auto">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.section
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mt-12 py-20 border-t border-accent-silver/10 text-xs text-silver/80 uppercase tracking-[0.25em] flex items-center gap-4"
            >
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-4 h-4 border border-accent-silver/20 border-t-silver-bright rounded-full"
              />
              Syncing operational data...
            </motion.section>
          ) : error ? (
            <motion.section
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-12 py-20 border-t border-rag-red/20 text-xs text-rag-red uppercase tracking-[0.25em]"
            >
              Briefing unavailable: {error}
            </motion.section>
          ) : (
            <motion.div
              key="content"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="space-y-24"
            >
              {/* Section I: Executive Pulse */}
              <motion.section variants={itemVariants} className="w-full">
                <ExecutiveStatsBar
                  riskLabel={risk.label}
                  criticalVulns={summary.critical_findings}
                  totalAssets={summary.total_assets}
                  attackSurface={summary.scan_activity.running}
                  compliancePercent={safeAssetsPercent}
                  riskNote={summary.critical_findings > 0
                    ? `Status escalated. ${summary.critical_findings} major vulnerabilities detected on production nodes.`
                    : summary.high_findings > 4
                      ? `Risk exposure has increased by ${summary.high_findings}% following recent network expansion.`
                      : "Security posture remains stable. Monitoring systems active across all sectors."}
                />
              </motion.section>

              {/* MISSION CONTROL CENTER */}
              <motion.section variants={itemVariants} className="bg-charcoal border-4 border-black p-10 shadow-[10px_10px_0px_0px_rgba(31,31,31,1)] relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none select-none">
                  <span className="text-8xl font-black italic uppercase font-mono tracking-tighter">MISSION_READY</span>
                </div>
                
                <div className="flex flex-col xl:flex-row justify-between gap-16 relative z-10">
                  <div className="flex-1 space-y-10">
                    <header className="space-y-4">
                      <div className="bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        Control_Deck_Initialized
                      </div>
                      <h2 className="text-4xl md:text-5xl font-black text-silver-bright uppercase tracking-tighter italic leading-none">
                        Mission <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Control</span>
                      </h2>
                    </header>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                      <div className="space-y-4">
                        <label className="text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] block italic">Subject_Enclave_Target</label>
                        <div className="flex items-center gap-4 bg-charcoal-dark border-4 border-black p-4 focus-within:border-rag-blue transition-colors group/input">
                          <span className="material-symbols-outlined text-silver/20 group-focus-within/input:text-rag-blue">dns</span>
                          <input 
                            type="text" 
                            value={targetNode}
                            onChange={(e) => setTargetNode(e.target.value)}
                            placeholder="IP_OR_DOMAIN_REQD"
                            className="bg-transparent border-none outline-none text-silver-bright font-mono text-lg flex-1 uppercase tracking-wider placeholder:text-silver/10"
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-6 pt-6">
                        <div className="flex flex-col">
                          <span className="text-[8px] font-black text-silver/40 uppercase tracking-[0.2em] mb-1">Clearance_Level</span>
                          <span className="text-xs font-mono text-rag-green font-black uppercase italic">LEVEL_5_OPS</span>
                        </div>
                        <div className="h-8 w-px bg-silver/10"></div>
                        <div className="flex flex-col">
                          <span className="text-[8px] font-black text-silver/40 uppercase tracking-[0.2em] mb-1">System_Posture</span>
                          <span className="text-xs font-mono text-rag-blue font-black uppercase italic">INFILTRATOR_A3</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 xl:flex xl:flex-row gap-6 shrink-0">
                    {[
                      { id: 'nmap-recon', label: 'RECON', sub: 'PORTSCAN', color: 'bg-rag-blue' },
                      { id: 'zap-scan', label: 'WEB', sub: 'AUDIT', color: 'bg-rag-amber' },
                      { id: 'sqlmap-scan', label: 'DB', sub: 'INJECT', color: 'bg-rag-red' },
                      { id: 'browser-scan', label: 'BROWSER', sub: 'EXPLOIT', color: 'bg-silver-bright' }
                    ].map((tool) => (
                      <button
                        key={tool.id}
                        disabled={initiating}
                        onClick={() => handleStartMission(tool.id)}
                        className={`group relative flex flex-col items-center justify-center w-36 h-36 border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 active:scale-95 transition-all bg-charcoal-dark overflow-hidden ${initiating ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <div className={`absolute top-0 left-0 w-full h-1 ${tool.color}`}></div>
                        <div className="text-2xl font-black text-silver-bright mb-1 tracking-tighter italic group-hover:scale-110 transition-transform">{tool.label}</div>
                        <div className="text-[9px] font-black text-silver/40 uppercase tracking-widest">{tool.sub}</div>
                        <div className={`absolute bottom-0 right-0 p-1 opacity-0 group-hover:opacity-100 transition-opacity ${tool.color} text-black`}>
                          <span className="material-symbols-outlined text-xs">arrow_forward</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </motion.section>

              {/* Secondary Layout: Vulnerability & Activity */}
              <motion.section variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-20">
                <div className="space-y-10">
                  <header>
                    <h3 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright flex items-center gap-3">
                      <span className="w-2 h-2 border border-accent-silver/40 rotate-45"></span>
                      Vulnerability Summary
                    </h3>
                  </header>

                  <div className="divide-y divide-accent-silver/5 bg-charcoal/30 p-10 border border-accent-silver/5">
                    {[
                      ['Critical Risk', summary.critical_findings, 'text-rag-red', summary.critical_findings > 0 ? 'DECREASING' : 'STABLE'],
                      ['High Severity', summary.high_findings, 'text-rag-amber', 'ACTION REQ'],
                      ['Medium Alert', summary.medium_findings, 'text-silver-bright', null],
                      ['Low Exposure', summary.low_findings, 'text-rag-amber/70', null],
                      ['Informational', summary.info_findings, 'text-silver/70', null],
                    ].map(([label, count, color, note]) => {
                      const total = summary.total_findings || 1;
                      const percentage = (count as number / total) * 100;
                      return (
                        <div key={String(label)} className="py-6 flex flex-col gap-4 group first:pt-0 last:pb-0">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className={`text-xs font-bold uppercase tracking-[0.15em] ${color}`}>{label}</span>
                            </div>
                            <div className="flex items-baseline gap-3">
                              <span className="text-2xl font-light text-silver-bright font-mono">
                                {count as number}
                              </span>
                              {note ? (
                                <span className={`min-w-[120px] text-right text-[11px] font-bold uppercase tracking-widest ${note === 'STABLE' ? 'text-rag-green' : 'text-silver/80'}`}>
                                  {note}
                                </span>
                              ) : null}
                            </div>
                          </div>
                          <div className="h-0.5 w-full bg-accent-silver/5 relative overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${percentage}%` }}
                              className={`absolute h-full ${String(color).replace('text-', 'bg-')} opacity-30`}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>


                </div>

                <div className="space-y-10">
                  <header className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <h3 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright flex items-center gap-3">
                        <span className="w-2 h-2 border border-accent-silver/40 rotate-45"></span>
                        Task Activity Feed
                      </h3>
                      {summary.scan_activity.running > 0 && (
                        <div className="flex items-center gap-2 bg-rag-green/10 px-3 py-1 rounded-full border border-rag-green/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-rag-green animate-pulse shadow-[0_0_4px_rgba(46,213,115,0.6)]" />
                          <span className="text-[10px] font-bold text-rag-green uppercase tracking-widest">Live</span>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-6">
                      <Link className="text-[10px] font-bold text-silver/70 hover:text-silver-bright uppercase tracking-widest transition-all" to={routes.history}>
                        Full Schedule
                      </Link>
                      <Link className="text-[10px] font-bold text-silver/70 hover:text-silver-bright uppercase tracking-widest transition-all" to={routes.findings}>
                        Audit Ledger
                      </Link>
                    </div>
                  </header>

                  <div className="space-y-4 bg-transparent">
                    {summary.recent_tasks.length === 0 && (
                      <div className="bg-charcoal/30 p-12 text-center border border-accent-silver/5 relative overflow-hidden">
                        <div className="absolute inset-0 bg-accent-silver/2 animate-pulse" />
                        <p className="text-[10px] text-silver/70 uppercase tracking-[0.3em] italic relative z-10">
                          Surveillance systems idle. No activity detected.
                        </p>
                      </div>
                    )}

                    {/* Unified Tasks Feed */}
                    <div className="grid grid-cols-1 gap-2">
                      {summary.recent_tasks.map((task) => {
                        const isActive = task.status === 'running' || task.status === 'queued';
                        const isFailed = task.status === 'failed';
                        const isCancelled = task.status === 'cancelled';
                        const taskInit = formatTaskInit(task.created_at);

                        return (
                          <motion.div
                            key={task.id}
                            whileHover={{ backgroundColor: "rgba(255, 255, 255, 0.04)", x: 4 }}
                            className={`bg-charcoal px-6 py-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between group border border-accent-silver/5 transition-all duration-300 relative overflow-hidden ${!isActive ? 'opacity-80 hover:opacity-100' : ''}`}
                          >
                            <div className={`absolute top-0 left-0 w-1 h-full ${isActive ? 'bg-rag-green/60 shadow-[0_0_8px_var(--rag-green)]' :
                                isFailed ? 'bg-rag-red/40' :
                                  isCancelled ? 'bg-silver/20' :
                                    'bg-rag-green/20'
                              }`} />

                            <div className="flex items-center gap-5">
                              <div className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-rag-green animate-pulse shadow-[0_0_8px_rgba(46,213,115,0.4)]' :
                                  isFailed ? 'bg-rag-red' :
                                    isCancelled ? 'bg-silver/40' :
                                      'bg-rag-green'
                                }`} />
                              <div>
                                <div className="flex items-center gap-3">
                                  <p className="text-[13px] font-semibold text-silver-bright tracking-wide group-hover:text-white transition-colors">
                                    {displayToolName(task)}
                                  </p>
                                  <span className={`text-[8px] font-mono px-1.5 py-0.5 border rounded-sm ${isActive ? 'text-rag-green border-rag-green/20 bg-rag-green/5' :
                                      isFailed ? 'text-rag-red border-rag-red/20 bg-rag-red/5' :
                                        'text-silver/70 border-silver/20'
                                    }`}>
                                    {task.status.toUpperCase()}
                                  </span>
                                </div>
                                <p className="text-[10px] text-silver/85 uppercase tracking-widest mt-1 flex items-center gap-2 font-mono italic">
                                  TARGET:: {task.target || 'N/A'}
                                </p>
                                <p className="text-[10px] text-silver/80 uppercase tracking-widest mt-1 flex items-center gap-3 font-mono">
                                  <span>PLUGIN:: {task.plugin_id || 'N/A'}</span>
                                  <span>TASK:: {task.id.slice(0, 8)}</span>
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-6">
                              <div className="text-right hidden sm:block">
                                <span className={`text-[9px] font-bold uppercase tracking-[0.2em] block mb-0.5 ${isActive ? 'text-rag-green' : 'text-silver/80'}`}>
                                  {isActive ? 'Live Processing' : 'Cycle Log'}
                                </span>
                                <span className="text-[9px] font-mono text-silver/80 uppercase block">
                                  INIT:: {taskInit.date} @ {taskInit.time} IST
                                </span>
                                <span className="text-[9px] font-mono text-silver/70 uppercase block mt-0.5">
                                  DURATION:: {formatDuration(task.duration_seconds)}
                                </span>
                              </div>

                              {isActive ? (
                                <>
                                  <div className="h-8 w-px bg-white/5 hidden sm:block" />
                                  <button
                                    onClick={() => handleAbort(task.id)}
                                    className="text-[10px] font-bold text-silver/40 hover:text-rag-red uppercase tracking-widest transition-colors flex items-center gap-2"
                                  >
                                    <span className="material-symbols-outlined text-[14px]">cancel</span>
                                    Abort
                                  </button>
                                </>
                              ) : (
                                <Link
                                  to={routePath.task(task.id)}
                                  className="text-[10px] font-bold text-silver/20 hover:text-silver-bright uppercase tracking-widest transition-colors"
                                >
                                  Details
                                </Link>
                              )}
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>


                  </div>

                  {/* Operational Stats: Minimized and Integrated */}
                  <div className="pt-6 grid grid-cols-1 md:grid-cols-3 gap-px bg-accent-silver/10 border border-accent-silver/5">
                    <div className="bg-charcoal px-6 py-5">
                      <span className="text-xs font-bold text-silver/70 uppercase tracking-[0.2em] block mb-2">Total Cycles</span>
                      <span className="text-2xl font-light text-silver-bright font-mono italic">{summary.scan_activity.total}</span>
                    </div>
                    <div className="bg-charcoal px-8 py-8 md:col-span-2">
                      <div className="flex justify-between items-baseline mb-3">
                        <span className="text-[10px] font-bold text-silver/80 uppercase tracking-widest">Efficiency Posture</span>
                        <span className="text-[10px] text-rag-green font-mono uppercase">{progressWidth.toFixed(0)}% SYNCHRONIZED</span>
                      </div>
                      <div className="h-1 w-full bg-accent-silver/10 relative overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${progressWidth}%` }}
                          transition={{ duration: 1.5, ease: "circOut" }}
                          className="absolute inset-y-0 left-0 bg-rag-green shadow-[0_0_8px_rgba(46,213,115,0.4)]"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </motion.section>

              {/* Detail Plane: Asset Ledger & Composition */}
              <motion.section variants={itemVariants} className="pt-8 relative">
                <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-20 items-start">
                  <div className="space-y-12">
                    <header className="flex justify-between items-center">
                      <h3
                        className="text-2xl text-silver-bright font-light italic tracking-tight"
                        style={{ fontFamily: 'var(--font-display)' }}
                      >
                        {summary.has_high_risk_assets ? "High Risk Asset Ledger" : "Operational Asset Ledger"}
                      </h3>
                      <Link to={routes.assets} className="text-[10px] font-bold text-silver/70 hover:text-silver-bright uppercase tracking-widest transition-all">
                        Inventory Matrix
                      </Link>
                    </header>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-accent-silver/10 border border-accent-silver/5 overflow-hidden">
                      {summary.high_risk_assets.length === 0 ? (
                        <div className="bg-charcoal p-16 text-center md:col-span-3 text-[10px] text-silver/70 uppercase tracking-[0.3em] font-light">
                          No assets currently registered in the inventory
                        </div>
                      ) : (
                        summary.high_risk_assets.map((asset, idx) => (
                          <motion.div 
                            key={asset.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: idx * 0.1 }}
                            whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.02)' }}
                            className="bg-charcoal p-8 group transition-all cursor-pointer border-r border-b border-accent-silver/5 flex flex-col min-h-[220px]"
                          >
                            <div className="flex justify-between items-start mb-6">
                              <span className={`text-[9px] font-bold px-2 py-0.5 uppercase tracking-tighter ${
                                asset.risk_level === 'critical' ? 'bg-rag-red text-white' :
                                asset.risk_level === 'high' ? 'bg-rag-amber text-black' :
                                'bg-accent-silver/20 text-silver/60'
                              }`}>
                                {asset.risk_level.toUpperCase()}
                              </span>
                              <span className="text-[10px] font-mono text-silver/60 group-hover:text-silver/80 transition-colors">
                                #{String(idx + 1).padStart(2, '0')}
                              </span>
                            </div>
                            
                            <div className="mb-6 flex-grow">
                              <h4 className="text-lg font-medium text-silver-bright truncate group-hover:text-accent-cyan transition-colors mb-2 italic">
                                {asset.target}
                              </h4>
                              <p className="text-[10px] text-silver/70 font-mono tracking-widest line-clamp-2 uppercase">
                                {asset.description || `${asset.risk_level} priority infrastructure node`}
                              </p>
                            </div>

                            <div className="flex items-center justify-between pt-6 border-t border-accent-silver/5 mt-auto">
                              <div className="flex flex-col">
                                <span className="text-[8px] uppercase text-silver/80 tracking-[0.2em] font-bold">Trace ID</span>
                                <span className="text-[10px] text-silver/85 font-mono">{asset.id.slice(0, 8)}</span>
                              </div>
                              <div className="flex flex-col items-end">
                                <span className="text-[8px] uppercase text-silver/80 tracking-[0.2em] font-bold">Last Pulse</span>
                                <span className="text-[10px] text-rag-green font-mono uppercase tracking-tighter">
                                  {new Date(asset.last_scanned).toLocaleDateString([], { timeZone: 'Asia/Kolkata' })}
                                </span>
                              </div>
                            </div>
                          </motion.div>
                        ))
                      )}
                    </div>
                  </div>

                  <aside className="space-y-12">
                    <div className="space-y-10 bg-charcoal/30 p-10 border border-accent-silver/5">
                      <div>
                        <div className="text-xs text-silver/80 uppercase tracking-[0.2em] font-bold mb-6">Monitoring Coverage</div>
                        <div className="flex items-end justify-between items-baseline mb-4">
                          <span
                            className="text-5xl text-silver-bright font-light leading-none"
                            style={{ fontFamily: 'var(--font-display)' }}
                          >
                            {coveragePercent}%
                          </span>
                          <div className="text-right">
                            <span className="text-[11px] text-silver/80 uppercase block tracking-[0.15em]">Outstanding Gaps</span>
                            <span className="text-lg text-rag-amber font-mono font-light leading-none">{coverageGaps}</span>
                          </div>
                        </div>
                        <div className="h-[3px] w-full bg-accent-silver/5 overflow-hidden mt-8">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${coveragePercent}%` }}
                            transition={{ duration: 2, ease: "circOut" }}
                            className="h-full bg-rag-green"
                          />
                        </div>
                        <p className="text-xs text-silver/80 leading-relaxed font-light mt-8 uppercase tracking-[0.15em]">
                          Environmental visibility index: active monitors vs registered estate.
                        </p>
                      </div>

                      <div className="pt-10 border-t border-accent-silver/5">
                        <div className="text-xs text-silver/80 uppercase tracking-[0.2em] font-bold mb-8">Surface Composition</div>
                        {attackSurfaceBreakdown.length === 0 && (
                          <div className="text-xs text-silver/80 uppercase tracking-[0.15em] italic">Telemetry unavailable</div>
                        )}
                        <div className="space-y-8">
                          {attackSurfaceBreakdown.map(([label, value]) => (
                            <div key={label} className="space-y-3">
                              <div className="flex items-center justify-between gap-4">
                                <span className="text-xs font-bold uppercase tracking-[0.15em] text-silver-bright">{label}</span>
                                <span className="text-xs font-mono text-silver/85">{value} UNITS</span>
                              </div>
                              <div className="h-px bg-accent-silver/10">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{
                                    width: `${summary.total_attack_surface > 0 ? Math.max(5, (value / summary.total_attack_surface) * 100) : 0}%`,
                                  }}
                                  transition={{ duration: 1.2, ease: "easeOut" }}
                                  className="h-px bg-silver/60"
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="p-8 border border-accent-silver/5 text-center">
                      <p className="text-[11px] text-silver/70 uppercase tracking-[0.25em]">
                        Archived Telemetry • Index 01-A
                      </p>
                    </div>
                  </aside>
                </div>
              </motion.section>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="px-12 py-12 text-center border-t border-accent-silver/5">
        <p className="text-[10px] text-silver/70 uppercase tracking-[0.5em] font-light">
          SecuScan Intelligence Systems • Class 1 Operational View
        </p>
      </footer>
    </div>
  )
}
