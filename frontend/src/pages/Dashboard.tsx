import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getDashboardSummary, getHealth, cancelTask } from '../api'
import { ExecutiveStatsBar } from '../components/ExecutiveStatsBar'

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
}

type Asset = {
  id: string
  target: string
  description: string
  risk_level: string
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
  last_scan_time: string | null
  recent_findings: Finding[]
  running_tasks: Task[]
  recent_tasks: Task[]
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
        }))
      : [],
    high_risk_assets: Array.isArray(summary.high_risk_assets)
      ? summary.high_risk_assets.map((asset) => ({
          id: asString(asset?.id),
          target: asString(asset?.target, 'Unknown asset'),
          description: asString(asset?.description),
          risk_level: asString(asset?.risk_level, 'high'),
        }))
      : [],
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
  last_scan_time: null,
  recent_findings: [],
  running_tasks: [],
  recent_tasks: [],
  high_risk_assets: [],
  attack_surface_by_category: {},
  scan_activity: { total: 0, completed: 0, running: 0 },
}

function formatBriefingDate(dateStr: string | null) {
  if (!dateStr) return 'NO ANALYSIS AVAILABLE'
  return (
    new Date(dateStr).toLocaleString('en-US', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }) + ' GMT'
  ).toUpperCase()
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
    transition: { duration: 0.5, ease: [0.19, 1, 0.22, 1] },
  },
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary>(emptySummary)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null)

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
      <header className="w-full px-6 md:px-12 pt-12 pb-10 flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: [0.19, 1, 0.22, 1] }}
        >
          <h1
            className="text-3xl tracking-tight leading-tight"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            <span className="font-black text-silver-bright italic uppercase tracking-tighter mr-2">SecuScan</span>
            <span className="font-light text-silver-bright/80 italic">Briefing</span>
          </h1>
        </motion.div>

        <motion.div 
          className="flex flex-col gap-8 md:flex-row md:items-center md:gap-16"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 1 }}
        >
          <div className="text-left md:text-right flex flex-col gap-2">
            <span className="text-[10px] font-bold [color:var(--text-muted)] uppercase tracking-[0.2em] block">
              Last Integrity Check
            </span>
            <span className="text-sm font-light [color:var(--text-primary)] font-mono tracking-tight">{formatBriefingDate(summary.last_scan_time)}</span>
          </div>
          <div className="hidden md:block h-10 w-px bg-accent-silver/10"></div>
          <div className="flex items-center gap-6">
            <div className={`relative flex items-center px-4 py-2 border transition-colors duration-500 ${statusBadgeClasses}`}>
              <span className="text-[10px] font-bold uppercase tracking-[0.25em]">
                {statusLabel}
              </span>
              {backendConnected && (
                <motion.span 
                  className="absolute inset-0 bg-rag-green/5"
                  animate={{ opacity: [0, 0.1, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
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
              className="mt-12 py-20 border-t border-accent-silver/10 text-xs text-silver/40 uppercase tracking-[0.25em] flex items-center gap-4"
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

              {/* Secondary Layout: Vulnerability & Activity */}
              <motion.section variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-20">
                <div className="space-y-10">
                  <header>
                    <h3 className="text-sm font-bold uppercase tracking-[0.2em] [color:var(--text-primary)] flex items-center gap-3">
                      <span className="w-2 h-2 border border-accent-silver/40 rotate-45"></span>
                      Vulnerability Summary
                    </h3>
                  </header>

                  <div className="divide-y divide-accent-silver/5 bg-charcoal/30 p-10 border border-accent-silver/5">
                    {[
                      ['Critical Risk', summary.critical_findings, 'text-rag-red', summary.critical_findings > 0 ? 'DECREASING' : 'STABLE'],
                      ['High Severity', summary.high_findings, 'text-rag-amber', 'ACTION REQ'],
                      ['Medium Alert', summary.medium_findings, 'text-silver-bright', null],
                      ['Low Exposure', summary.low_findings, 'text-rag-green', null],
                    ].map(([label, count, color, note]) => {
                      const total = summary.total_findings || 1;
                      const percentage = (count as number / total) * 100;
                      return (
                        <div key={String(label)} className="py-6 flex flex-col gap-4 group first:pt-0 last:pb-0">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className={`text-xs font-bold uppercase tracking-[0.15em] ${color}`}>{label}</span>
                            </div>
                            <div className="flex items-baseline gap-4">
                              <span className="text-2xl font-light [color:var(--text-primary)] font-mono">
                                {count as number}
                              </span>
                              {note ? (
                                <span className={`text-[11px] font-bold uppercase tracking-widest ${note === 'STABLE' ? 'text-rag-green' : '[color:var(--text-muted)]'}`}>
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
                        Operational Activity Feed
                      </h3>
                      {summary.scan_activity.running > 0 && (
                        <div className="flex items-center gap-2 bg-rag-green/10 px-3 py-1 rounded-full border border-rag-green/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-rag-green animate-pulse shadow-[0_0_4px_rgba(46,213,115,0.6)]" />
                          <span className="text-[10px] font-bold text-rag-green uppercase tracking-widest">Live</span>
                        </div>
                      )}
                    </div>
                    <Link className="text-xs font-bold text-silver/40 hover:text-silver-bright uppercase tracking-widest transition-all" to="/findings">
                      Audit Ledger
                    </Link>
                  </header>

                  <div className="space-y-4 bg-transparent">
                    {summary.recent_tasks.length === 0 && (
                      <div className="bg-charcoal/30 p-12 text-center border border-accent-silver/5 relative overflow-hidden">
                        <div className="absolute inset-0 bg-accent-silver/2 animate-pulse" />
                        <p className="text-[10px] text-silver/20 uppercase tracking-[0.3em] italic relative z-10">
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
                          
                          return (
                            <motion.div
                                key={task.id}
                                whileHover={{ backgroundColor: "rgba(255, 255, 255, 0.04)", x: 4 }}
                                className={`bg-charcoal px-6 py-4 flex flex-col gap-4 md:flex-row md:items-center md:justify-between group border border-accent-silver/5 transition-all duration-300 relative overflow-hidden ${!isActive ? 'opacity-80 hover:opacity-100' : ''}`}
                            >
                                <div className={`absolute top-0 left-0 w-1 h-full ${
                                  isActive ? 'bg-rag-green/60 shadow-[0_0_8px_var(--rag-green)]' : 
                                  isFailed ? 'bg-rag-red/40' : 
                                  isCancelled ? 'bg-silver/20' : 
                                  'bg-rag-green/20'
                                }`} />
                                
                                <div className="flex items-center gap-5">
                                    <div className={`w-1.5 h-1.5 rounded-full ${
                                      isActive ? 'bg-rag-green animate-pulse shadow-[0_0_8px_rgba(46,213,115,0.4)]' : 
                                      isFailed ? 'bg-rag-red' : 
                                      isCancelled ? 'bg-silver/40' : 
                                      'bg-rag-green'
                                    }`} />
                                    <div>
                                        <div className="flex items-center gap-3">
                                          <p className="text-[13px] font-semibold [color:var(--text-primary)] tracking-wide group-hover:text-white transition-colors">
                                            {task.tool_name.toUpperCase()}
                                          </p>
                                          <span className={`text-[8px] font-mono px-1.5 py-0.5 border rounded-sm ${
                                            isActive ? 'text-rag-green border-rag-green/20 bg-rag-green/5' : 
                                            isFailed ? 'text-rag-red border-rag-red/20 bg-rag-red/5' : 
                                            'text-silver/40 border-silver/10'
                                          }`}>
                                            {task.status.toUpperCase()}
                                          </span>
                                        </div>
                                        <p className="text-[10px] [color:var(--text-muted)] uppercase tracking-widest mt-1 flex items-center gap-2 font-mono italic">
                                          {task.target} 
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-6">
                                    <div className="text-right hidden sm:block">
                                        <span className={`text-[9px] font-bold uppercase tracking-[0.2em] block mb-0.5 ${isActive ? 'text-rag-green' : 'text-silver/30'}`}>
                                          {isActive ? 'Live Processing' : 'Cycle Log'}
                                        </span>
                                        <span className="text-[9px] font-mono text-silver/20">
                                            {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })} @ {new Date(task.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }).toUpperCase()}
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
                                        to={`/tasks`} 
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
                      <span className="text-xs font-bold text-silver/30 uppercase tracking-[0.2em] block mb-2">Total Cycles</span>
                      <span className="text-2xl font-light text-silver-bright font-mono italic">{summary.scan_activity.total}</span>
                    </div>
                    <div className="bg-charcoal px-8 py-8 md:col-span-2">
                       <div className="flex justify-between items-baseline mb-3">
                          <span className="text-[10px] font-bold text-silver/30 uppercase tracking-widest">Efficiency Posture</span>
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
                        High Risk Asset Ledger
                      </h3>
                      <Link to="/assets" className="text-[10px] font-bold text-silver/40 hover:text-silver-bright uppercase tracking-widest transition-all">
                        Inventory Matrix
                      </Link>
                    </header>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-accent-silver/10 border border-accent-silver/5 overflow-hidden">
                      {summary.high_risk_assets.length === 0 && (
                        <div className="bg-charcoal p-16 text-center md:col-span-2 text-[10px] text-silver/20 uppercase tracking-[0.3em] font-light">
                          No assets currently flagged for risk escalation
                        </div>
                      )}

                      {summary.high_risk_assets.map((asset, index) => (
                        <motion.div
                          key={asset.id}
                          whileHover={{ x: 4 }}
                          className={`charcoal-gradient px-8 py-10 flex flex-col justify-between min-h-[160px] group transition-all duration-500 border-l-2 relative overflow-hidden ${
                            asset.risk_level === 'critical' ? 'border-rag-red/60' : 'border-rag-amber/60'
                          } ${index === 0 ? 'md:col-span-2' : ''}`}
                        >
                          <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-[0.07] transition-opacity">
                             <span className="material-symbols-outlined text-8xl">precision_manufacturing</span>
                          </div>
                          <div className="flex justify-between items-start mb-6 relative z-10">
                            <div className="min-w-0">
                              <h4 className={`${index === 0 ? 'text-xl' : 'text-sm'} font-semibold [color:var(--text-primary)] uppercase tracking-widest truncate group-hover:text-white transition-colors`}>
                                {asset.target}
                              </h4>
                              <p className={`text-xs [color:var(--text-muted)] font-light mt-2 leading-relaxed ${index === 0 ? 'max-w-xl' : 'line-clamp-2'}`}>
                                {asset.description || `${asset.risk_level} priority infrastructure asset. Pending mitigation strategy for detected escalation.`}
                              </p>
                            </div>
                            <span className={`text-[10px] font-mono px-3 py-1 border rounded-sm shrink-0 ${
                              asset.risk_level === 'critical' ? 'text-rag-red border-rag-red/20 bg-rag-red/5 font-bold shadow-[0_0_8px_rgba(239,68,68,0.2)]' : 'text-rag-amber border-rag-amber/20 bg-rag-amber/5 font-bold'
                            }`}>
                              {asset.risk_level.toUpperCase()}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-[9px] font-bold text-silver/30 uppercase tracking-widest mt-auto relative z-10">
                            <span className="flex items-center gap-1.5">
                               <span className="material-symbols-outlined text-[12px]">fingerprint</span>
                               ID: {asset.id.slice(0, 8)}
                            </span>
                            <span className="w-1 h-1 rounded-full bg-silver/10"></span>
                            <span className="flex items-center gap-1.5">
                               <span className="material-symbols-outlined text-[12px]">pending_actions</span>
                               Awaiting Resolution
                            </span>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>

                  <aside className="space-y-12">
                    <div className="space-y-10 bg-charcoal/30 p-10 border border-accent-silver/5">
                      <div>
                        <div className="text-xs text-silver/30 uppercase tracking-[0.2em] font-bold mb-6">Monitoring Coverage</div>
                        <div className="flex items-end justify-between items-baseline mb-4">
                          <span
                            className="text-5xl text-silver-bright font-light leading-none"
                            style={{ fontFamily: 'var(--font-display)' }}
                          >
                            {coveragePercent}%
                          </span>
                          <div className="text-right">
                             <span className="text-[11px] text-silver/25 uppercase block tracking-[0.15em]">Outstanding Gaps</span>
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
                        <p className="text-xs [color:var(--text-muted)] leading-relaxed font-light mt-8 uppercase tracking-[0.15em]">
                          Environmental visibility index: active monitors vs registered estate.
                        </p>
                      </div>

                      <div className="pt-10 border-t border-accent-silver/5">
                        <div className="text-xs text-silver/30 uppercase tracking-[0.2em] font-bold mb-8">Surface Composition</div>
                        {attackSurfaceBreakdown.length === 0 && (
                          <div className="text-xs text-silver/25 uppercase tracking-[0.15em] italic">Telemetry unavailable</div>
                        )}
                        <div className="space-y-8">
                          {attackSurfaceBreakdown.map(([label, value]) => (
                            <div key={label} className="space-y-3">
                              <div className="flex items-center justify-between gap-4">
                                <span className="text-xs font-bold uppercase tracking-[0.15em] text-silver-bright">{label}</span>
                                <span className="text-xs font-mono text-silver/45">{value} UNITS</span>
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
                       <p className="text-[11px] text-silver/25 uppercase tracking-[0.25em]">
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
        <p className="text-[10px] text-silver/20 uppercase tracking-[0.5em] font-light">
          SecuScan Intelligence Systems • Class 1 Operational View
        </p>
      </footer>
    </div>
  )
}
