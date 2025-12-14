import React, { useEffect, useMemo, useState } from 'react'
import { getAttackSurface, getDashboardSummary, getFindings } from '../api'

type Entry = {
  id: string
  category: string
  item: string
  details: string
  risk: string
  source: string
  last_seen: string
}

export default function AttackSurface() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [summary, setSummary] = useState<any>({ attack_surface_by_category: {}, total_attack_surface: 0 })
  const [findings, setFindings] = useState<any[]>([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedRisk, setSelectedRisk] = useState('all')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([getAttackSurface(), getDashboardSummary(), getFindings()]).then(([surfaceData, summaryData, findingData]: any) => {
      setEntries(surfaceData.entries || [])
      setSummary(summaryData || { attack_surface_by_category: {}, total_attack_surface: 0 })
      setFindings(findingData.findings || [])
      setExpandedCategories(new Set(Object.keys(summaryData.attack_surface_by_category || {}).slice(0, 3)))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const categories = useMemo(() => [...new Set(entries.map((entry) => entry.category))], [entries])
  const filteredEntries = entries.filter((entry) => (selectedCategory === 'all' || entry.category === selectedCategory) && (selectedRisk === 'all' || entry.risk === selectedRisk))
  const groupedEntries = filteredEntries.reduce((acc, entry) => {
    acc[entry.category] = acc[entry.category] || []
    acc[entry.category].push(entry)
    return acc
  }, {} as Record<string, Entry[]>)

  const formatDateLong = (dateStr: string) =>
    new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT'

  const riskCounts = {
    critical: entries.filter((a) => a.risk === 'critical').length,
    high: entries.filter((a) => a.risk === 'high').length,
    medium: entries.filter((a) => a.risk === 'medium').length,
    low: entries.filter((a) => a.risk === 'low').length,
    info: entries.filter((a) => a.risk === 'info').length,
  }

  const totalEntries = Math.max(entries.length, 1)

  return (
    <div className="min-h-screen flex flex-col scale-in-center">
      <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10 bg-charcoal-dark/50 backdrop-blur-md sticky top-0 z-40">
        <div className="flex items-center gap-8">
            <div className="header-decoration hidden xl:block">
                <span className="material-symbols-outlined text-accent-silver/30 text-4xl animate-pulse">radar</span>
            </div>
            <div>
              <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">Attack Surface Vector Matrix</h1>
              <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">Autonomous Signal Interception • Boundary Surveillance • Perimeter Intelligence</p>
            </div>
        </div>
        
        <div className="flex items-center gap-12">
           <div className="text-right border-l border-accent-silver/10 pl-8">
                <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Monitored Vectors</span>
                <span className="text-xl font-light text-silver-bright font-mono">{entries.length.toString().padStart(3, '0')}</span>
            </div>
            <div className="flex items-center gap-4">
               <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">sync</button>
            </div>
        </div>
      </header>

      <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
        
        {/* Risk Distribution Stripe */}
        <section className="space-y-6">
            <div className="flex items-center gap-6">
                <h3 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Threat Vector Distribution</h3>
                <div className="h-px flex-1 bg-accent-silver/5"></div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm shadow-xl">
                {[
                    { label: 'Critical Risks', val: riskCounts.critical, color: 'text-rag-red', bg: 'bg-rag-red' },
                    { label: 'High Threats', val: riskCounts.high, color: 'text-rag-amber', bg: 'bg-rag-amber' },
                    { label: 'Medium Exposure', val: riskCounts.medium, color: 'text-rag-blue', bg: 'bg-rag-blue' },
                    { label: 'Low/Info Signals', val: riskCounts.low + riskCounts.info, color: 'text-silver/40', bg: 'bg-silver/40' },
                    { label: 'Managed Total', val: entries.length, color: 'text-silver-bright', bg: 'bg-silver-bright' },
                ].map((stat, i) => (
                    <div key={i} className="bg-charcoal p-8 space-y-2 group transition-all hover:bg-charcoal-light">
                        <span className="text-[9px] font-bold text-silver/20 uppercase tracking-widest block group-hover:text-silver/40">{stat.label}</span>
                        <div className="flex items-center gap-4">
                            <span className={`text-3xl font-serif font-light ${stat.color}`}>{stat.val}</span>
                            <div className="flex-1 h-0.5 bg-accent-silver/5 relative overflow-hidden">
                                <div className={`absolute inset-y-0 left-0 ${stat.bg} opacity-20`} style={{ width: `${(stat.val / totalEntries) * 100}%` }}></div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </section>

        <div className="flex flex-col lg:flex-row gap-12 items-stretch py-4">
            {/* Filter & Inventory Sidebar */}
            <aside className="w-full lg:w-96 space-y-12 flex-shrink-0">
                <div className="p-10 bg-charcoal-dark border border-accent-silver/10 rounded-sm space-y-10 relative overflow-hidden group shadow-2xl">
                     <div className="absolute top-0 right-0 w-32 h-32 opacity-[0.02] -mr-16 -mt-16 pointer-events-none">
                        <span className="material-symbols-outlined text-[200px]">filter_alt</span>
                    </div>
                    
                    <div className="space-y-8 relative z-10">
                        <h3 className="text-[11px] font-bold text-silver-bright uppercase tracking-[0.5em] italic flex items-center gap-4">
                            Selection Logic
                            <div className="flex-1 h-px bg-accent-silver/10"></div>
                        </h3>
                        
                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[9px] font-bold text-silver/30 uppercase tracking-widest italic font-mono block">Category Vector</label>
                                <select 
                                    className="w-full bg-charcoal border border-accent-silver/10 px-4 py-3 text-[10px] text-silver-bright focus:outline-none focus:border-silver/40 rounded-sm italic font-mono uppercase"
                                    value={selectedCategory} 
                                    onChange={(e) => setSelectedCategory(e.target.value)}
                                >
                                    <option value="all">ALL_CATEGORIES</option>
                                    {categories.map((cat) => <option key={cat} value={cat}>{cat.toUpperCase()}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-[9px] font-bold text-silver/30 uppercase tracking-widest italic font-mono block">Risk Spectrum</label>
                                <select 
                                    className="w-full bg-charcoal border border-accent-silver/10 px-4 py-3 text-[10px] text-silver-bright focus:outline-none focus:border-silver/40 rounded-sm italic font-mono uppercase"
                                    value={selectedRisk} 
                                    onChange={(e) => setSelectedRisk(e.target.value)}
                                >
                                    <option value="all">ALL_RISK_LEVELS</option>
                                    {['critical', 'high', 'medium', 'low', 'info'].map((risk) => <option key={risk} value={risk}>{risk.toUpperCase()}_SIGNALS</option>)}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-8 pt-6 border-t border-accent-silver/5">
                        <h3 className="text-[11px] font-bold text-silver-bright uppercase tracking-[0.5em] italic flex items-center gap-4">
                            Vector Integrity
                            <div className="flex-1 h-px bg-accent-silver/10"></div>
                        </h3>
                         <div className="space-y-6">
                            {Object.entries(summary.attack_surface_by_category || {}).map(([category, count], i) => (
                                <div key={i} className="space-y-2 group transition-all">
                                    <div className="flex justify-between items-baseline font-mono italic">
                                        <span className="text-[9px] text-silver/20 uppercase tracking-widest group-hover:text-silver-bright/40 transition-colors">{category}</span>
                                        <span className="text-[10px] text-silver-bright">{String(count)}</span>
                                    </div>
                                    <div className="h-1 bg-accent-silver/5 rounded-full overflow-hidden">
                                        <div className="h-full bg-silver/20 group-hover:bg-rag-blue/40 transition-all" style={{ width: `${(Number(count) / totalEntries) * 100}%` }}></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="p-10 space-y-8 border border-dashed border-accent-silver/10 rounded-sm bg-charcoal/5">
                    <h3 className="text-[10px] font-bold text-silver-bright uppercase tracking-[0.3em] italic">Vulnerability Correlation</h3>
                    <div className="space-y-4">
                        {findings.slice(0, 3).map((finding) => (
                            <div key={finding.id} className="p-4 bg-charcoal border border-accent-silver/5 hover:border-accent-silver/20 transition-all rounded-sm space-y-2">
                                <div className="flex justify-between items-center">
                                    <span className={`text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 border ${
                                        finding.severity === 'critical' ? 'text-rag-red border-rag-red/20 bg-rag-red/5' : 'text-rag-amber border-rag-amber/20 bg-rag-amber/5'
                                    }`}>{finding.severity}</span>
                                    {finding.cvss && <span className="text-[9px] font-mono text-silver/20 italic">CVSS {finding.cvss}</span>}
                                </div>
                                <div className="text-[10px] font-bold text-silver-bright uppercase tracking-tight line-clamp-1">{finding.title}</div>
                                <div className="text-[9px] text-silver/30 italic font-mono truncate">{finding.target}</div>
                            </div>
                        ))}
                    </div>
                    <button className="w-full py-4 text-[9px] text-silver/40 uppercase tracking-[0.4em] hover:text-white transition-all italic border-t border-accent-silver/10 pt-8">Request Master Correlation Briefing</button>
                </div>
            </aside>

            {/* Attack Surface Explorer Matrix */}
            <div className="flex-1 space-y-8 min-w-0 pb-20">
                <div className="flex justify-between items-baseline mb-2">
                    <div className="flex items-center gap-4">
                        <h2 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Target Discovery Ledger ({filteredEntries.length})</h2>
                        <div className="h-px w-24 bg-accent-silver/10"></div>
                    </div>
                    <span className="text-[8px] text-silver/20 uppercase tracking-widest italic font-mono">Status: ACTIVE_SURVEILLANCE</span>
                </div>
                
                <div className="space-y-12">
                     {Object.entries(groupedEntries).map(([category, group]) => (
                        <div key={category} className="space-y-6">
                            <button 
                                className="w-full flex justify-between items-center py-4 px-8 bg-charcoal border-l-4 border-l-rag-blue border-y border-r border-accent-silver/10 group hover:border-accent-silver/30 transition-all"
                                onClick={() => {
                                    const next = new Set(expandedCategories)
                                    next.has(category) ? next.delete(category) : next.add(category)
                                    setExpandedCategories(next)
                                }}
                            >
                                <div className="flex items-baseline gap-6">
                                    <span className="text-xs font-black text-silver-bright uppercase tracking-[0.3em] font-mono italic">{category}</span>
                                    <span className="text-[10px] text-silver/20 font-mono italic">[{group.length.toString().padStart(2, '0')}_VECTOR_NODES]</span>
                                </div>
                                <span className={`material-symbols-outlined text-silver/20 group-hover:text-silver-bright transition-all duration-300 ${expandedCategories.has(category) ? 'rotate-180' : ''}`}>expand_more</span>
                            </button>

                            {expandedCategories.has(category) && (
                                <div className="grid grid-cols-1 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm shadow-2xl animate-in slide-in-from-top-4 duration-500">
                                    {group.map((entry) => (
                                        <div key={entry.id} className="p-8 bg-charcoal hover:bg-charcoal-light transition-all flex flex-col md:flex-row gap-8 items-start md:items-center relative group">
                                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-rag-blue/0 group-hover:bg-rag-blue transition-all"></div>
                                            
                                            <div className="w-32 flex-shrink-0">
                                                <span className={`text-[9px] font-bold uppercase tracking-widest px-3 py-1 border block text-center ${
                                                    entry.risk === 'critical' ? 'text-rag-red border-rag-red/20 bg-rag-red/5' : 
                                                    entry.risk === 'high' ? 'text-rag-amber border-rag-amber/20 bg-rag-amber/5' : 
                                                    'text-rag-blue border-rag-blue/20 bg-rag-blue/5'
                                                }`}>{entry.risk}</span>
                                            </div>

                                            <div className="flex-1 space-y-2">
                                                <div className="text-sm font-bold text-silver-bright font-mono italic tracking-tight uppercase group-hover:text-rag-blue transition-colors">{entry.item}</div>
                                                <div className="text-[10px] text-silver/40 font-mono leading-relaxed italic">{entry.details}</div>
                                            </div>

                                            <div className="flex gap-12 items-center text-right shrink-0">
                                                <div className="space-y-1">
                                                    <span className="text-[8px] text-silver/20 uppercase tracking-widest block font-mono">Vector Source</span>
                                                    <span className="text-[10px] text-silver-bright uppercase font-bold italic">{entry.source}</span>
                                                </div>
                                                <div className="space-y-1 w-40">
                                                    <span className="text-[8px] text-silver/20 uppercase tracking-widest block font-mono">Last Intercept</span>
                                                    <span className="text-[10px] text-silver/40 font-mono italic">{formatDateLong(entry.last_seen)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {entries.length === 0 && (
                    <div className="p-20 bg-charcoal border border-dashed border-accent-silver/10 rounded-sm text-center space-y-6">
                        <span className="material-symbols-outlined text-silver/5 text-6xl">radar</span>
                        <div className="text-[10px] text-silver/10 uppercase tracking-[0.5em] italic">No attack surface records stored in secure enclave.</div>
                    </div>
                )}
            </div>
        </div>
      </main>
    </div>
  )
}
