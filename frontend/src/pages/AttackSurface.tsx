import React, { useEffect, useMemo, useState } from 'react'
import { getAttackSurface, getDashboardSummary, getFindings, getAssets } from '../api'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { formatLocaleDate, formatLocaleTime, getTimeZoneAbbreviation } from '../utils/date'

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

const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.05,
        },
    },
}

const itemVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { type: 'spring' as const, stiffness: 200, damping: 25 }
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
        if (isRefresh) setRefreshing(true)
        else setLoading(true)

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
            setExpandedCategories(new Set(Object.keys(parsedSummary.attack_surface_by_category || {}).slice(0, 2)))
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }

    useEffect(() => {
        loadData()
    }, [])

    const categories = useMemo(() => [...new Set(entries.map((entry) => entry.category))], [entries])
    
    const filteredEntries = useMemo(() => {
        return entries.filter((entry) => {
            const categoryMatch = selectedCategory === 'all' || entry.category === selectedCategory
            const riskMatch = selectedRisk === 'all' || entry.risk === selectedRisk
            return categoryMatch && riskMatch
        })
    }, [entries, selectedCategory, selectedRisk])

    const sortedEntries = useMemo(() => {
        const list = [...filteredEntries]
        const toTimestamp = (value: string) => {
            const ts = new Date(value).getTime()
            return Number.isNaN(ts) ? 0 : ts
        }
        const riskRank = (risk: string) => RISK_ORDER[(RISK_LEVELS.includes(risk as Severity) ? risk : 'info') as Severity]

        list.sort((a, b) => {
            switch (sortBy) {
                case 'last_seen_asc': return toTimestamp(a.last_seen) - toTimestamp(b.last_seen)
                case 'risk_desc': return riskRank(b.risk) - riskRank(a.risk)
                case 'risk_asc': return riskRank(a.risk) - riskRank(b.risk)
                case 'item_asc': return a.item.localeCompare(b.item)
                case 'item_desc': return b.item.localeCompare(a.item)
                case 'last_seen_desc':
                default: return toTimestamp(b.last_seen) - toTimestamp(a.last_seen)
            }
        })
        return list
    }, [filteredEntries, sortBy])

    const groupedEntries = useMemo(() => {
        return sortedEntries.reduce((acc, entry) => {
            acc[entry.category] = acc[entry.category] || []
            acc[entry.category].push(entry)
            return acc
        }, {} as Record<string, Entry[]>)
    }, [sortedEntries])

    const riskCounts = useMemo(() => {
        return RISK_LEVELS.reduce((acc, risk) => {
            acc[risk] = entries.filter((entry) => entry.risk === risk).length
            return acc
        }, { critical: 0, high: 0, medium: 0, low: 0, info: 0 } as Record<Severity, number>)
    }, [entries])

    if (loading) {
        return (
            <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-12">
                <div className="space-y-4 text-center">
                    <div className="w-20 h-20 border-8 border-silver-bright/10 border-t-rag-red animate-spin mx-auto shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"></div>
                    <p className="text-xs font-black text-silver-bright uppercase tracking-[0.5em] italic">Probing_Surface...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            {/* Neo-Brutalist Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
                <div className="space-y-4">
                  <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    Visibility_Control_Plane v1.2
                  </div>
                  <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic">
                    Surface <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Ledger</span>
                  </h1>
                  <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed max-w-2xl">
                    EXTERNAL EXPOSURE ANALYSIS // INFRASTRUCTURE FOOTPRINT: {summary.total_attack_surface} NODES
                  </p>
                </div>

                <div className="flex gap-4">
                    <button 
                        onClick={() => loadData(true)}
                        disabled={refreshing}
                        className="bg-charcoal px-8 py-4 border-4 border-black text-silver-bright font-black uppercase tracking-widest italic shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all flex items-center gap-3"
                    >
                        <span className={`material-symbols-outlined text-sm ${refreshing ? 'animate-spin' : ''}`}>sync</span>
                        REPROBE_ENCLAVE
                    </button>
                </div>
            </header>

            {/* Quick Metrics Grid */}
            <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
                {[
                    { label: 'Surface_Nodes', val: entries.length, color: 'bg-rag-blue', icon: 'hub' },
                    { label: 'High_Exposure', val: riskCounts.critical + riskCounts.high, color: 'bg-rag-red', icon: 'warning' },
                    { label: 'Total_Assets', val: assets.length, color: 'bg-silver-bright', icon: 'inventory' },
                    { label: 'Map_Relays', val: findings.length, color: 'bg-rag-amber', icon: 'leak_add' },
                ].map((m) => (
                    <div key={m.label} className={`${m.color} border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between h-40 group hover:-translate-y-1 transition-transform`}>
                        <div className="flex justify-between items-start">
                           <span className="text-[10px] font-black text-black uppercase tracking-[0.2em] italic">{m.label}</span>
                           <span className="material-symbols-outlined text-black/20 group-hover:text-black transition-colors">{m.icon}</span>
                        </div>
                        <span className="text-5xl font-black text-black font-mono leading-none tracking-tighter">{m.val.toString().padStart(3, '0')}</span>
                    </div>
                ))}
            </section>



            <div className="grid grid-cols-1 xl:grid-cols-4 gap-12">
                {/* Filtration Sidebar */}
                <aside className="xl:col-span-1 space-y-12">
                    <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
                        <div className="space-y-4">
                            <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Category_Isolation</label>
                            <select 
                                className="w-full bg-charcoal-dark border-4 border-black p-4 text-[10px] font-black font-mono text-silver-bright uppercase focus:outline-none appearance-none cursor-pointer" 
                                value={selectedCategory} 
                                onChange={(e) => setSelectedCategory(e.target.value)}
                            >
                                <option value="all">ALL CATEGORIES</option>
                                {categories.map((cat) => (
                                    <option key={cat} value={cat}>{cat.toUpperCase()}</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-4">
                            <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Risk_Filter</label>
                            <div className="grid grid-cols-1 gap-2">
                                {['all', ...RISK_LEVELS].map(r => (
                                    <button 
                                        key={r}
                                        onClick={() => setSelectedRisk(r as any)}
                                        className={`px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest border-4 transition-all flex justify-between items-center ${
                                            selectedRisk === r 
                                            ? 'bg-rag-red border-black text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' 
                                            : 'bg-charcoal-dark border-black text-silver/40 hover:text-white'
                                        }`}
                                    >
                                        {r}
                                        {selectedRisk === r && <span className="material-symbols-outlined text-xs">radar</span>}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button 
                            className="w-full border-4 border-black border-dashed py-4 text-[10px] font-black uppercase text-silver/20 hover:text-silver-bright hover:border-solid transition-all"
                            onClick={() => {
                                setSelectedCategory('all')
                                setSelectedRisk('all')
                                setSortBy('last_seen_desc')
                            }}
                        >
                            RESET_INTERFACE
                        </button>
                    </section>
                </aside>

                {/* Entry Ledger Section */}
                <main className="xl:col-span-3 space-y-8">
                    <div className="flex flex-col md:flex-row justify-between items-end gap-6 border-b-4 border-black pb-8">
                        <h2 className="text-5xl font-black text-silver-bright italic uppercase tracking-tighter">Surface_Ledger</h2>
                        <div className="flex items-center gap-6">
                            <span className="text-[9px] font-black text-silver/20 uppercase tracking-widest font-mono">Sorted_By:</span>
                            <select 
                                className="bg-transparent border-0 text-[10px] font-black text-rag-blue uppercase tracking-widest outline-none cursor-pointer"
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value as any)}
                            >
                                <option value="last_seen_desc">RECENCY_DESC</option>
                                <option value="last_seen_asc">RECENCY_ASC</option>
                                <option value="risk_desc">CRITICALITY_HI</option>
                                <option value="risk_asc">CRITICALITY_LO</option>
                            </select>
                        </div>
                    </div>

                    <AnimatePresence mode="popLayout">
                        <motion.div 
                            variants={containerVariants}
                            initial="hidden"
                            animate="visible"
                            className="space-y-6"
                        >
                            {Object.entries(groupedEntries).map(([category, group]) => (
                                <div key={category} className="space-y-4">
                                    <div className="flex items-center gap-4 py-2">
                                        <span className="bg-silver-bright text-black px-3 py-0.5 text-[9px] font-black uppercase italic shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] border-2 border-black">
                                            {category}
                                        </span>
                                        <div className="h-0.5 flex-1 bg-black/10"></div>
                                        <span className="text-[9px] font-mono text-silver/20 uppercase font-black">{group.length} NODES_ACTIVE</span>
                                    </div>

                                    <div className="grid grid-cols-1 gap-6">
                                        {group.map((entry) => (
                                            <motion.div 
                                                key={entry.id}
                                                variants={itemVariants}
                                                className="group bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all relative overflow-hidden"
                                            >
                                                <div className="flex flex-col md:flex-row justify-between gap-8">
                                                    <div className="flex-1 space-y-4">
                                                        <div className="flex items-center gap-3">
                                                            <span className={`px-2 py-0.5 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                                                                entry.risk === 'critical' ? 'bg-rag-red text-black' :
                                                                entry.risk === 'high' ? 'bg-rag-amber text-black' :
                                                                entry.category === 'Scanning...' ? 'bg-rag-amber/20 text-rag-amber border-rag-amber/40 animate-pulse' :
                                                                'bg-charcoal-dark text-silver-bright/40'
                                                            }`}>
                                                                {entry.category === 'Scanning...' ? 'SCANNING' : entry.risk}
                                                            </span>
                                                            <span className="text-[10px] font-mono text-silver/20 uppercase font-black italic">SOURCE::{entry.source}</span>
                                                        </div>
                                                        <h3 className="text-2xl font-black text-silver-bright uppercase tracking-tight italic group-hover:text-rag-red transition-colors font-mono">
                                                            {entry.item}
                                                        </h3>
                                                        <p className="text-xs font-mono text-silver/40 uppercase tracking-widest leading-relaxed">
                                                            {entry.details}
                                                        </p>
                                                    </div>

                                                    <div className="flex flex-row md:flex-col items-end justify-between md:justify-center gap-6 shrink-0">
                                                       <div className="text-right">
                                                          <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-1 italic">LAST_DETECTED</p>
                                                          <p className="text-[10px] font-mono text-silver-bright uppercase font-black">
                                                            {formatLocaleDate(entry.last_seen)} // {formatLocaleTime(entry.last_seen, { hour12: false })} {getTimeZoneAbbreviation()}
                                                          </p>
                                                       </div>
                                                       <button className="bg-charcoal-dark border-4 border-black p-2 text-silver/20 group-hover:text-silver-bright group-hover:bg-black transition-all">
                                                          <span className="material-symbols-outlined text-sm">open_in_new</span>
                                                       </button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            ))}

                            {entries.length === 0 && (
                                <div className="py-40 bg-charcoal/30 border-4 border-dashed border-black/5 text-center flex flex-col items-center gap-8">
                                    <span className="material-symbols-outlined text-silver/5 text-9xl">leak_remove</span>
                                    <div className="space-y-2">
                                        <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">Surface Isolated</p>
                                        <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">No active exposure vectors found in current data stream</p>
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </main>
            </div>

            {/* Tactical Footer */}
            <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
                <div className="flex items-center gap-6">
                    <div className="w-12 h-1 bg-silver/20"></div>
                    RESTRICTED VIEW // SOC CORE ENCLAVE // {new Date().getFullYear()}
                </div>
                <div className="flex gap-4">
                    {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="w-2 h-2 bg-silver/20 rounded-full"></div>)}
                </div>
            </footer>
        </div>
    )
}
