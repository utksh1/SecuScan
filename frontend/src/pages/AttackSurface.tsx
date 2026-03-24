import React, { useEffect, useMemo, useState } from 'react'
import { getAttackSurface, getDashboardSummary, getFindings, getAssets } from '../api'
import { motion, Variants } from 'framer-motion'
import NetworkMap from '../components/NetworkMap'

type Entry = {
  id: string
  category: string
  item: string
  details: string
  risk: string
  source: string
  last_seen: string
  asset_id?: string
}

type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

type Finding = {
    id: string
    title: string
    severity: Severity
    target?: string
    cvss?: number
}

type DashboardSummary = {
    attack_surface_by_category: Record<string, number>
    total_attack_surface: number
}

type AttackSurfaceResponse = {
    entries?: Entry[]
}

type AssetsResponse = {
    assets?: Array<Record<string, unknown>>
}

type FindingsResponse = {
    findings?: Finding[]
}

const RISK_LEVELS: Severity[] = ['critical', 'high', 'medium', 'low', 'info']
const RISK_ORDER: Record<Severity, number> = { critical: 5, high: 4, medium: 3, low: 2, info: 1 }

const RISK_STYLES: Record<Severity, string> = {
    critical: 'text-rag-red border-rag-red/20 bg-rag-red/5',
    high: 'text-rag-amber border-rag-amber/20 bg-rag-amber/5',
    medium: 'text-rag-blue border-rag-blue/20 bg-rag-blue/5',
    low: 'text-rag-green border-rag-green/20 bg-rag-green/5',
    info: 'text-silver/70 border-accent-silver/20 bg-accent-silver/5',
}

const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.06,
            delayChildren: 0.1,
        },
    },
}

const itemVariants: Variants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
        opacity: 1,
        y: 0,
        transition: {
          duration: 0.4,
          ease: [0.19, 1, 0.22, 1] as any
        },
    },
}

export default function AttackSurface() {
  const [entries, setEntries] = useState<Entry[]>([])
    const [assets, setAssets] = useState<Array<Record<string, unknown>>>([])
    const [summary, setSummary] = useState<DashboardSummary>({ attack_surface_by_category: {}, total_attack_surface: 0 })
    const [findings, setFindings] = useState<Finding[]>([])
  const [selectedCategory, setSelectedCategory] = useState('all')
    const [selectedRisk, setSelectedRisk] = useState<'all' | Severity>('all')
    const [sortBy, setSortBy] = useState<'last_seen_desc' | 'last_seen_asc' | 'risk_desc' | 'risk_asc' | 'item_asc' | 'item_desc'>('last_seen_desc')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
    const [refreshing, setRefreshing] = useState(false)

    const loadData = async (isRefresh = false) => {
        if (isRefresh) {
            setRefreshing(true)
        } else {
            setLoading(true)
        }

        try {
            const [surfaceData, summaryData, findingData, assetData] = await Promise.all([
                getAttackSurface(),
                getDashboardSummary(),
                getFindings(),
                getAssets(),
            ])

            const parsedSurface = (surfaceData || {}) as AttackSurfaceResponse
            const parsedSummary = (summaryData || {}) as DashboardSummary
            const parsedFindings = (findingData || {}) as FindingsResponse
            const parsedAssets = (assetData || {}) as AssetsResponse

            setEntries(parsedSurface.entries || [])
            setAssets(parsedAssets.assets || [])
            setSummary({
                attack_surface_by_category: parsedSummary.attack_surface_by_category || {},
                total_attack_surface: parsedSummary.total_attack_surface || 0,
            })
            setFindings(parsedFindings.findings || [])
            setExpandedCategories((prev) => {
                if (prev.size > 0) return prev
                return new Set(Object.keys(parsedSummary.attack_surface_by_category || {}).slice(0, 3))
            })
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }

    useEffect(() => {
    setLoading(true)
        loadData()
  }, [])

  const categories = useMemo(() => [...new Set(entries.map((entry) => entry.category))], [entries])
    const filteredEntries = entries.filter((entry) => {
        const categoryMatch = selectedCategory === 'all' || entry.category === selectedCategory
        const riskMatch = selectedRisk === 'all' || entry.risk === selectedRisk
        return categoryMatch && riskMatch
    })

    const sortedEntries = useMemo(() => {
        const list = [...filteredEntries]
        const toTimestamp = (value: string) => {
            const ts = new Date(value).getTime()
            return Number.isNaN(ts) ? 0 : ts
        }
        const riskRank = (risk: string) => RISK_ORDER[(RISK_LEVELS.includes(risk as Severity) ? risk : 'info') as Severity]

        list.sort((a, b) => {
            switch (sortBy) {
                case 'last_seen_asc':
                    return toTimestamp(a.last_seen) - toTimestamp(b.last_seen)
                case 'risk_desc':
                    return riskRank(b.risk) - riskRank(a.risk)
                case 'risk_asc':
                    return riskRank(a.risk) - riskRank(b.risk)
                case 'item_asc':
                    return a.item.localeCompare(b.item)
                case 'item_desc':
                    return b.item.localeCompare(a.item)
                case 'last_seen_desc':
                default:
                    return toTimestamp(b.last_seen) - toTimestamp(a.last_seen)
            }
        })

        return list
    }, [filteredEntries, sortBy])

  const groupedEntries = sortedEntries.reduce((acc, entry) => {
    acc[entry.category] = acc[entry.category] || []
    acc[entry.category].push(entry)
    return acc
  }, {} as Record<string, Entry[]>)

    const formatDateLong = (dateStr: string) => {
        const date = new Date(dateStr)
        if (Number.isNaN(date.getTime())) return 'Unknown'
        return `${date.toLocaleString('en-US', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
        })} UTC`
    }

    const riskCounts = RISK_LEVELS.reduce(
        (acc, risk) => {
            acc[risk] = entries.filter((entry) => entry.risk === risk).length
            return acc
        },
        { critical: 0, high: 0, medium: 0, low: 0, info: 0 } as Record<Severity, number>
    )

    const topCategory = Object.entries(summary.attack_surface_by_category || {}).sort((a, b) => Number(b[1]) - Number(a[1]))[0]

    if (loading) {
        return (
            <div className="min-h-screen bg-charcoal-dark p-8 lg:p-10">
                <div className="mx-auto max-w-[1700px] space-y-6 animate-pulse">
                    <div className="h-8 w-72 rounded bg-charcoal-light/80" />
                    <div className="h-4 w-96 rounded bg-charcoal-light/80" />
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                        <div className="h-28 rounded-sm bg-charcoal border border-accent-silver/10" />
                        <div className="h-28 rounded-sm bg-charcoal border border-accent-silver/10" />
                        <div className="h-28 rounded-sm bg-charcoal border border-accent-silver/10" />
                        <div className="h-28 rounded-sm bg-charcoal border border-accent-silver/10" />
                    </div>
                    <div className="h-80 rounded-sm bg-charcoal border border-accent-silver/10" />
                </div>
            </div>
        )
    }

  return (
        <div className="min-h-screen bg-charcoal-dark">
            <motion.main
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="mx-auto max-w-[1700px] px-6 py-8 lg:px-10 lg:py-10 space-y-8"
            >
                <motion.header variants={itemVariants} className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between pb-8">
                    <div>
                        <div className="flex items-center gap-3 mb-4">
                          <span className="w-10 h-px bg-accent-silver/20"></span>
                          <p className="text-xs font-bold text-silver/30 uppercase tracking-[0.4em]">Section II: External Exposure Control Plane</p>
                        </div>
                        <h1
                            className="text-4xl lg:text-5xl font-light tracking-tight text-silver-bright italic"
                            style={{ fontFamily: 'var(--font-display)' }}
                        >
                            Attack <span className="font-black not-italic uppercase tracking-tighter">Surface</span>
                        </h1>
                        <p className="mt-4 text-sm text-silver/50 uppercase tracking-[0.15em] max-w-2xl leading-relaxed">
                            Monitor exposed assets, prioritize vectors, and inspect external visibility drift across your infrastructure footprint.
                        </p>
                    </div>

                    <button
                        onClick={() => loadData(true)}
                        disabled={refreshing}
                        className="inline-flex items-center gap-2 border border-accent-silver/20 bg-charcoal px-5 py-2.5 text-[10px] text-silver-bright uppercase tracking-[0.3em] hover:border-silver/40 hover:bg-charcoal-light disabled:opacity-60 disabled:cursor-not-allowed transition-all"
                    >
                        <span className={`material-symbols-outlined text-base ${refreshing ? 'animate-spin' : ''}`}>refresh</span>
                        {refreshing ? 'Refreshing...' : 'Sync Snapshot'}
                    </button>
                </motion.header>

                <motion.section variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-px bg-accent-silver/10 border border-accent-silver/5">
                    <div className="bg-charcoal px-8 py-8 border-l border-rag-blue/20">
                        <div className="text-xs font-bold text-silver/30 uppercase tracking-[0.2em] mb-4">Visible Entries</div>
                        <div className="text-5xl font-light text-silver-bright font-mono italic">{entries.length}</div>
                    </div>
                    <div className="bg-charcoal px-8 py-8 border-l border-rag-red/20">
                        <div className="text-xs font-bold text-silver/30 uppercase tracking-[0.2em] mb-4">Critical + High</div>
                        <div className="text-5xl font-light text-rag-red font-mono italic">{riskCounts.critical + riskCounts.high}</div>
                    </div>
                    <div className="bg-charcoal px-8 py-8 border-l border-accent-silver/20">
                        <div className="text-xs font-bold text-silver/30 uppercase tracking-[0.2em] mb-4">Asset Coverage</div>
                        <div className="text-5xl font-light text-silver-bright font-mono italic">{assets.length}</div>
                    </div>
                    <div className="bg-charcoal px-8 py-8 border-l border-rag-green/20">
                        <div className="text-xs font-bold text-silver/30 uppercase tracking-[0.2em] mb-4">Top Category</div>
                        <div className="text-2xl font-semibold text-silver-bright truncate uppercase tracking-wider">{topCategory?.[0] || 'N/A'}</div>
                        <div className="text-xs text-silver/40 uppercase tracking-widest mt-2 font-mono">
                           {topCategory ? `${topCategory[1]} NODES` : 'NO TELEMETRY'}
                        </div>
                    </div>
                </motion.section>

                <motion.section variants={itemVariants} className="border border-accent-silver/10 bg-charcoal/80 p-4 lg:p-6 relative overflow-hidden">
                    <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(circle_at_center,_white_1px,_transparent_1px)] [background-size:20px_20px]" />
                    <div className="mb-4 flex items-center justify-between">
                        <h2 className="text-[11px] font-bold text-silver/40 uppercase tracking-[0.35em]">Network Topology</h2>
                        <span className="text-[10px] text-silver/30 uppercase tracking-widest">Updated from latest asset + discovery signals</span>
                    </div>
                    <NetworkMap assets={assets} entries={entries} />
                </motion.section>

                <motion.section variants={itemVariants} className="border border-accent-silver/10 bg-charcoal/80 px-4 py-8 lg:px-10">
                    <div className="flex flex-wrap items-end gap-6 lg:gap-8">
                        <div>
                            <label className="mb-3 block text-xs font-bold uppercase tracking-[0.2em] text-silver/30">Category</label>
                            <select
                                className="min-w-[220px] border border-accent-silver/20 bg-charcoal-dark px-4 py-3 text-sm text-silver-bright uppercase tracking-wider outline-none focus:border-silver/40 transition-colors"
                                value={selectedCategory}
                                onChange={(e) => setSelectedCategory(e.target.value)}
                            >
                                <option value="all">All categories</option>
                                {categories.map((cat) => (
                                    <option key={cat} value={cat}>{cat}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-3 block text-xs font-bold uppercase tracking-[0.2em] text-silver/30">Risk</label>
                            <select
                                className="min-w-[220px] border border-accent-silver/20 bg-charcoal-dark px-4 py-3 text-sm text-silver-bright uppercase tracking-wider outline-none focus:border-silver/40 transition-colors"
                                value={selectedRisk}
                                onChange={(e) => setSelectedRisk(e.target.value as 'all' | Severity)}
                            >
                                <option value="all">All risk levels</option>
                                {RISK_LEVELS.map((risk) => (
                                    <option key={risk} value={risk}>{risk}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-3 block text-xs font-bold uppercase tracking-[0.2em] text-silver/30">Sort</label>
                            <select
                                className="min-w-[250px] border border-accent-silver/20 bg-charcoal-dark px-4 py-3 text-sm text-silver-bright uppercase tracking-wider outline-none focus:border-silver/40 transition-colors"
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                            >
                                <option value="last_seen_desc">Last Seen: Newest</option>
                                <option value="last_seen_asc">Last Seen: Oldest</option>
                                <option value="risk_desc">Risk: High to Low</option>
                                <option value="risk_asc">Risk: Low to High</option>
                                <option value="item_asc">Target: A to Z</option>
                                <option value="item_desc">Target: Z to A</option>
                            </select>
                        </div>
                        <button
                            className="border border-accent-silver/20 px-6 py-3 text-xs text-silver/70 uppercase tracking-[0.25em] hover:bg-charcoal-light hover:text-silver-bright transition-all"
                            onClick={() => {
                                setSelectedCategory('all')
                                setSelectedRisk('all')
                                setSortBy('last_seen_desc')
                            }}
                        >
                            Reset
                        </button>
                    </div>
                </motion.section>

                <motion.section variants={itemVariants} className="space-y-4 min-w-0">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                            <h2 className="text-[11px] font-bold text-silver/40 uppercase tracking-[0.35em]">Entries ({filteredEntries.length})</h2>
                            <div className="flex items-center gap-2 flex-wrap">
                                {RISK_LEVELS.map((risk) => (
                                    <span key={risk} className={`inline-flex rounded border px-2 py-1 text-[10px] uppercase tracking-wider ${RISK_STYLES[risk]}`}>
                                        {risk}: {riskCounts[risk]}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {filteredEntries.length === 0 && (
                            <div className="border border-dashed border-accent-silver/20 bg-charcoal/40 p-10 text-center">
                                <p className="text-[10px] text-silver/35 uppercase tracking-[0.3em]">No entries match the selected filters.</p>
                            </div>
                        )}

                        <div className="space-y-4">
                            {Object.entries(groupedEntries).map(([category, group]) => (
                                <div key={category} className="border border-accent-silver/10 bg-charcoal/80 overflow-hidden">
                                    <button
                                        className="w-full flex items-center justify-between gap-6 px-6 py-5 border-b border-accent-silver/10 hover:bg-charcoal-light/60 transition-all"
                                        onClick={() => {
                                            const next = new Set(expandedCategories)
                                            if (next.has(category)) {
                                                next.delete(category)
                                            } else {
                                                next.add(category)
                                            }
                                            setExpandedCategories(next)
                                        }}
                                    >
                                        <div className="text-left">
                                            <p className="text-base font-semibold text-silver-bright uppercase tracking-wider">{category}</p>
                                            <p className="text-xs text-silver/35 uppercase tracking-[0.2em] mt-1 font-mono">{group.length} NODES</p>
                                        </div>
                                        <span className={`material-symbols-outlined text-silver/40 transition-transform ${expandedCategories.has(category) ? 'rotate-180' : ''}`}>
                                            expand_more
                                        </span>
                                    </button>

                                    {expandedCategories.has(category) && (
                                        <div className="divide-y divide-accent-silver/5">
                                            {group.map((entry) => (
                                                <div key={entry.id} className="px-6 py-6 grid gap-6 lg:grid-cols-[140px_1fr_200px_240px] lg:items-start bg-charcoal/70 hover:bg-charcoal-light/20 transition-colors">
                                                    <div>
                                                        <span className={`inline-flex rounded-sm border px-3 py-1.5 text-xs font-bold uppercase tracking-wider ${RISK_STYLES[(RISK_LEVELS.includes(entry.risk as Severity) ? entry.risk : 'info') as Severity]}`}>
                                                            {entry.risk}
                                                        </span>
                                                    </div>

                                                    <div className="min-w-0">
                                                        <p className="text-sm font-bold text-silver-bright break-words font-mono tracking-tight">{entry.item}</p>
                                                        <p className="mt-2 text-sm text-silver/50 leading-relaxed italic">{entry.details}</p>
                                                    </div>

                                                    <div>
                                                        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-silver/30 mb-1">Source Vector</p>
                                                        <p className="text-sm text-silver/80 font-mono">{entry.source}</p>
                                                    </div>

                                                    <div>
                                                        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-silver/30 mb-1">Last Detection</p>
                                                        <p className="text-sm text-silver/60 font-mono tracking-tighter">{formatDateLong(entry.last_seen)}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                </motion.section>

                <motion.section variants={itemVariants} className="grid grid-cols-1 xl:grid-cols-2 gap-px bg-accent-silver/5">
                    <div className="border border-accent-silver/10 bg-charcoal/40 p-10 space-y-8">
                        <div className="flex items-center gap-4">
                            <span className="w-1.5 h-6 bg-rag-blue/50"></span>
                            <h3 className="text-sm font-bold text-silver/40 uppercase tracking-[0.4em]">Infrastructure Distribution Matrix</h3>
                        </div>
                        <div className="space-y-6">
                            {Object.entries(summary.attack_surface_by_category || {}).sort((a,b) => b[1] - a[1]).map(([category, count]) => {
                                const percent = Math.round((Number(count) / Math.max(entries.length, 1)) * 100)
                                return (
                                    <div key={category} className="group cursor-default">
                                        <div className="mb-3 flex items-end justify-between text-xs font-bold text-silver/50 uppercase tracking-[0.2em] group-hover:text-silver-bright transition-colors">
                                            <span>{category}</span>
                                            <span className="font-mono text-silver-bright/40">{count} NODES / {percent}%</span>
                                        </div>
                                        <div className="h-1 bg-accent-silver/5 border border-white/5 overflow-hidden">
                                            <motion.div 
                                                initial={{ width: 0 }}
                                                animate={{ width: `${percent}%` }}
                                                transition={{ duration: 1, ease: [0.19, 1, 0.22, 1] }}
                                                className="h-full bg-rag-blue/60 group-hover:bg-rag-blue transition-colors"
                                            />
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    <div className="border border-accent-silver/10 bg-charcoal/40 p-10 space-y-8">
                        <div className="flex items-center gap-4">
                            <span className="w-1.5 h-6 bg-rag-red/50"></span>
                            <h3 className="text-sm font-bold text-silver/40 uppercase tracking-[0.4em]">High-Priority Surface Findings</h3>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {findings.slice(0, 4).sort((a,b) => (RISK_ORDER[b.severity] || 0) - (RISK_ORDER[a.severity] || 0)).map((finding) => (
                                <div key={finding.id} className="border border-accent-silver/10 bg-charcoal-dark p-5 group hover:bg-charcoal/60 transition-all">
                                    <div className="mb-4 flex items-center justify-between gap-4">
                                        <span className={`inline-flex rounded-sm border px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest ${RISK_STYLES[finding.severity]}`}>
                                            {finding.severity}
                                        </span>
                                        {typeof finding.cvss === 'number' && (
                                            <span className="text-[10px] font-mono text-silver/20 uppercase tracking-widest">CVSS {finding.cvss.toFixed(1)}</span>
                                        )}
                                    </div>
                                    <p className="text-sm font-bold text-silver-bright line-clamp-2 tracking-tight uppercase mb-3" style={{ fontFamily: 'var(--font-display)' }}>{finding.title}</p>
                                    <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                                        <span className="material-symbols-outlined text-xs text-silver/20">target</span>
                                        <p className="text-[10px] text-silver/40 uppercase tracking-wider truncate font-mono">{finding.target || 'INTERNAL_ENCLAVE'}</p>
                                    </div>
                                </div>
                            ))}

                            {findings.length === 0 && (
                                <div className="col-span-full py-12 text-center border border-dashed border-accent-silver/10">
                                    <p className="text-xs text-silver/20 uppercase tracking-[0.4em] font-mono">No active findings detected in surface probe</p>
                                </div>
                            )}
                        </div>
                    </div>
                </motion.section>
            </motion.main>
        </div>
  )
}
