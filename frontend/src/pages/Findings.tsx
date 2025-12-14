import React, { useEffect, useMemo, useState } from 'react'
import { getFindings } from '../api'

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
}

export default function Findings() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [filterSeverity, setFilterSeverity] = useState('all')
  const [filterCategory, setFilterCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getFindings().then((data: any) => {
      setFindings(data.findings || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const categories = useMemo(() => [...new Set(findings.map((f) => f.category))], [findings])
  
  const filteredFindings = useMemo(() => {
    return findings.filter((finding) => {
      const matchesSeverity = filterSeverity === 'all' || finding.severity === filterSeverity
      const matchesCategory = filterCategory === 'all' || finding.category === filterCategory
      const text = `${finding.title} ${finding.target} ${finding.description}`.toLowerCase()
      return matchesSeverity && matchesCategory && text.includes(searchQuery.toLowerCase())
    })
  }, [findings, filterSeverity, filterCategory, searchQuery])

  const countsBySeverity = useMemo(() => {
      return {
          critical: findings.filter(f => f.severity === 'critical').length,
          high: findings.filter(f => f.severity === 'high').length,
          medium: findings.filter(f => f.severity === 'medium').length,
          low: findings.filter(f => f.severity === 'low').length,
      }
  }, [findings])

  const formatDateLong = (dateStr: string) =>
    new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10">
        <div className="flex items-center gap-8">
            <div className="header-decoration hidden xl:block">
                <div className="flex gap-1.5 items-end h-8">
                    {[4, 8, 12, 6, 10].map((h, i) => (
                        <div key={i} className="w-1 bg-accent-silver/20 animate-pulse" style={{ height: `${h * 2}px`, animationDelay: `${i * 0.1}s` }}></div>
                    ))}
                </div>
            </div>
            <div>
              <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase">Threat Intelligence Matrix</h1>
              <p className="text-[10px] font-light text-silver/60 uppercase tracking-[0.4em] mt-2">Executive Vulnerability Briefing • Active Vectors</p>
            </div>
        </div>
        
        <div className="flex items-center gap-12">
          <div className="text-right border-l border-accent-silver/10 pl-8">
            <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Authenticated Entry</span>
            <span className="text-xs font-mono text-rag-green/80 uppercase">OP-SEC LEVEL 4</span>
          </div>
          <div className="flex items-center gap-4">
             <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">print</button>
             <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">share</button>
          </div>
        </div>
      </header>

      <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-700">
        
        {/* Metric Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm">
            {[
                { label: 'Critical Exposure', val: countsBySeverity.critical, color: 'text-rag-red', bg: 'bg-rag-red/5' },
                { label: 'High Priority', val: countsBySeverity.high, color: 'text-rag-amber', bg: 'bg-rag-amber/5' },
                { label: 'Medium Risk', val: countsBySeverity.medium, color: 'text-silver-bright', bg: 'bg-charcoal' },
                { label: 'Total Findings', val: findings.length, color: 'text-silver/40', bg: 'bg-charcoal' },
                { label: 'Risk Score (Avg)', val: '7.8', color: 'text-rag-amber', bg: 'bg-charcoal', hiddenOnMobile: true },
            ].map((m, i) => (
                <div key={i} className={`p-8 ${m.bg} flex flex-col justify-center gap-1.5 ${m.hiddenOnMobile ? 'hidden lg:flex' : ''}`}>
                    <span className="text-[8px] font-bold text-silver/30 uppercase tracking-[0.2em] italic leading-none">{m.label}</span>
                    <span className={`text-3xl font-serif font-light ${m.color}`}>{m.val.toString().padStart(2, '0')}</span>
                </div>
            ))}
        </div>

        <div className="flex flex-col lg:flex-row gap-12 items-stretch pt-4">
            {/* Filter Sidebar */}
            <div className="w-full lg:w-80 space-y-10 flex-shrink-0">
                <div className="space-y-8">
                    <div className="space-y-4">
                        <label className="text-[9px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">Target Pattern Search</label>
                        <div className="relative group">
                            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-silver/20 group-focus-within:text-silver-bright transition-colors text-sm">filter_list</span>
                            <input 
                                type="text" 
                                className="w-full bg-charcoal border border-accent-silver/10 pl-12 pr-4 py-3 text-xs text-silver-bright focus:outline-none focus:border-accent-silver/30 transition-all rounded-sm placeholder:text-silver/10 font-mono italic"
                                placeholder="IDENTIFY TARGET..." 
                                value={searchQuery} 
                                onChange={(e) => setSearchQuery(e.target.value)} 
                            />
                        </div>
                    </div>

                    <div className="space-y-4">
                        <label className="text-[9px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">Severity Spectrum</label>
                        <div className="flex flex-col gap-1.5">
                            {['all', 'critical', 'high', 'medium', 'low'].map(s => (
                                <button 
                                    key={s}
                                    onClick={() => setFilterSeverity(s)}
                                    className={`px-4 py-2.5 text-[10px] uppercase tracking-widest text-left border transition-all rounded-sm flex justify-between items-center ${
                                        filterSeverity === s ? 'bg-silver/10 border-silver/40 text-silver-bright' : 'bg-charcoal border-accent-silver/5 text-silver/30 hover:border-silver/20'
                                    }`}
                                >
                                    <span>{s}</span>
                                    {filterSeverity === s && <div className="w-1 h-1 bg-silver-bright rounded-full"></div>}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-4">
                        <label className="text-[9px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">Vector Category</label>
                        <select 
                            className="w-full bg-charcoal border border-accent-silver/10 px-4 py-3 text-[10px] text-silver-bright uppercase tracking-widest focus:outline-none focus:border-accent-silver/30 rounded-sm appearance-none cursor-pointer italic" 
                            value={filterCategory} 
                            onChange={(e) => setFilterCategory(e.target.value)}
                        >
                            <option value="all">ALL REACHABLE VECTORS</option>
                            {categories.map((cat) => <option key={cat} value={cat}>{cat.toUpperCase()}</option>)}
                        </select>
                    </div>
                </div>

                <div className="pt-10 border-t border-accent-silver/10 hidden lg:block">
                     <div className="p-6 bg-charcoal-light/10 border border-dashed border-accent-silver/10 rounded-sm">
                        <p className="text-[10px] text-silver/40 font-light italic leading-relaxed text-center">
                            Briefing data is synchronized across the secure enclave. All modifications are logged and audited.
                        </p>
                     </div>
                </div>
            </div>

            {/* Findings Ledger */}
            <div className="flex-1 space-y-6">
                <div className="flex justify-between items-center border-b border-accent-silver/10 pb-4">
                    <h2 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Intelligence Ledger Master Record ({filteredFindings.length})</h2>
                    <div className="flex gap-4">
                        <span className="text-[8px] text-rag-green uppercase tracking-widest animate-pulse">● System-Wide Sync Active</span>
                    </div>
                </div>
                
                <div className="space-y-2">
                    {filteredFindings.length > 0 ? filteredFindings.map((finding) => (
                      <div 
                        key={finding.id} 
                        className={`group bg-charcoal border border-accent-silver/10 transition-all overflow-hidden ${
                          expandedFinding === finding.id ? 'border-silver/40 shadow-2xl z-10' : 'hover:border-silver/20'
                        }`}
                      >
                        <div 
                            className="p-8 flex flex-col md:grid md:grid-cols-12 md:gap-8 items-center cursor-pointer relative"
                            onClick={() => setExpandedFinding(expandedFinding === finding.id ? null : finding.id)}
                        >
                          <div className="col-span-1 flex justify-center md:justify-start">
                             <div className={`w-3 h-3 rounded-full ${
                                finding.severity === 'critical' ? 'bg-rag-red shadow-[0_0_12px_rgba(239,68,68,0.4)]' : 
                                finding.severity === 'high' ? 'bg-rag-amber shadow-[0_0_12px_rgba(245,158,11,0.4)]' : 
                                'bg-silver/20'
                             }`}></div>
                          </div>

                          <div className="col-span-11 md:grid md:grid-cols-11 gap-4 items-center w-full">
                              <div className="col-span-7 space-y-1 text-center md:text-left">
                                  <div className="flex flex-wrap justify-center md:justify-start items-center gap-2 mb-2">
                                      <span className={`text-[9px] font-bold uppercase tracking-[0.2em] px-2 py-0.5 border ${
                                          finding.severity === 'critical' ? 'border-rag-red/20 text-rag-red bg-rag-red/5' : 
                                          finding.severity === 'high' ? 'border-rag-amber/20 text-rag-amber bg-rag-amber/5' : 
                                          'border-accent-silver/10 text-silver/40'
                                      }`}>{finding.severity}</span>
                                      <span className="text-[9px] text-silver/20 uppercase tracking-widest font-mono">[{finding.category}]</span>
                                  </div>
                                  <h4 className="text-lg font-serif font-light text-silver-bright tracking-tight group-hover:text-white transition-colors italic">{finding.title}</h4>
                                  <p className="text-[10px] text-silver/40 uppercase tracking-tighter italic font-mono truncate">{finding.target} • Discovery {new Date(finding.discovered_at).toLocaleDateString()}</p>
                              </div>

                              <div className="col-span-2 hidden md:flex flex-col items-end gap-1">
                                  {finding.cvss && (
                                      <>
                                          <span className="text-[8px] text-silver/20 font-bold uppercase tracking-widest">Score Vector</span>
                                          <span className="text-sm font-mono text-silver-bright">{finding.cvss.toFixed(1)}</span>
                                      </>
                                  )}
                              </div>

                              <div className="col-span-2 hidden md:flex flex-col items-end gap-1">
                                  <span className="text-[8px] text-silver/20 font-bold uppercase tracking-widest">Serial Number</span>
                                  <span className="text-xs font-mono text-silver/40">#{finding.id.split('-')[0].toUpperCase()}</span>
                              </div>
                          </div>
                        </div>

                        {expandedFinding === finding.id && (
                            <div className="px-12 md:px-24 py-16 border-t border-accent-silver/5 bg-charcoal-dark/40 animate-in fade-in slide-in-from-top-4 duration-500">
                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-20">
                                    <div className="space-y-12">
                                        <div className="space-y-6">
                                            <h5 className="text-[10px] font-bold text-silver/40 uppercase tracking-[0.3em] italic border-b border-accent-silver/10 pb-3">Technical Description</h5>
                                            <p className="text-base leading-relaxed text-silver/80 font-serif font-light italic">{finding.description}</p>
                                        </div>
                                        <div className="flex gap-px bg-accent-silver/10 overflow-hidden executive-border p-px">
                                            {finding.cve && (
                                                <div className="p-6 bg-charcoal-dark/50 flex-1 flex flex-col gap-1">
                                                    <span className="text-[8px] text-silver/40 uppercase font-bold tracking-widest">CVE Matrix ID</span>
                                                    <span className="text-sm font-mono text-silver-bright italic">{finding.cve}</span>
                                                </div>
                                            )}
                                            <div className="p-6 bg-charcoal-dark/50 flex-1 flex flex-col gap-1">
                                                <span className="text-[8px] text-silver/40 uppercase font-bold tracking-widest">Last Synced</span>
                                                <span className="text-sm font-mono text-silver/60">JUST NOW</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="space-y-12">
                                        <div className="space-y-6">
                                            <h5 className="text-[10px] font-bold text-silver/40 uppercase tracking-[0.3em] italic border-b border-accent-silver/10 pb-3">Remediation Protocol</h5>
                                            <div className="p-8 bg-charcoal/50 border-l-4 border-rag-green/30 italic">
                                                <p className="text-base text-silver/90 font-light leading-relaxed">
                                                    {finding.remediation || 'Structural remediation plan is currently classified. Please contact the secure enclave architecture lead for mission-critical mitigation directives.'}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex flex-col sm:flex-row gap-4">
                                            <button className="flex-1 px-8 py-4 bg-charcoal border border-accent-silver/20 text-[10px] text-silver/40 uppercase tracking-[0.3em] font-bold hover:bg-silver/5 hover:text-silver-bright transition-all italic">Discard Finding Case</button>
                                            <button className="flex-1 px-8 py-4 bg-rag-green/10 border border-rag-green/30 text-[10px] text-rag-green uppercase tracking-[0.3em] font-bold hover:bg-rag-green/20 transition-all italic">Validate Resolution</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                      </div>
                    )) : (
                      <div className="bg-charcoal p-40 text-center flex flex-col items-center gap-8 border border-accent-silver/5 italic border-dashed">
                        <span className="material-symbols-outlined text-silver/5 text-8xl">verified_user</span>
                        <p className="text-xs text-silver/10 uppercase tracking-[0.6em] font-medium leading-loose">The matrix is clear • Current spectrum contains no documented anomalies</p>
                      </div>
                    )}
                </div>
            </div>
        </div>
      </main>
    </div>
  )
}
