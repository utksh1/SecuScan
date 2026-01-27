import React, { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: { type: 'spring', stiffness: 300, damping: 25 }
  }
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

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      
      {/* Neo-Brutalist Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <div className="bg-rag-red text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Vulnerability Matrix v4.2
          </div>
          <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
            Threat <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Detection</span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic">
            Total Vectors Logged: {findings.length} // Displaying: {filteredFindings.length}
          </p>
        </div>

        <div className="flex flex-wrap gap-4">
          <button className="bg-charcoal px-6 py-4 border-2 border-silver-bright/20 hover:border-silver-bright text-silver-bright transition-all flex items-center gap-3 group shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none">
            <span className="material-symbols-outlined text-sm">print</span>
            <span className="text-xs font-black uppercase tracking-widest leading-none">Export_Brief</span>
          </button>
        </div>
      </header>

      {/* Severity Counters Grid */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {[
          { color: 'bg-rag-red', label: 'Critical', count: countsBySeverity.critical },
          { color: 'bg-rag-amber', label: 'High', count: countsBySeverity.high },
          { color: 'bg-rag-blue', label: 'Medium', count: countsBySeverity.medium },
          { color: 'bg-silver-bright', label: 'Low', count: countsBySeverity.low },
        ].map((s) => (
          <div key={s.label} className={`${s.color} border-4 border-black p-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-2 group hover:-translate-y-1 transition-transform cursor-default`}>
            <span className="text-xs font-black text-black uppercase tracking-widest select-none">{s.label}</span>
            <span className="text-4xl font-black text-black font-mono leading-none">{s.count.toString().padStart(2, '0')}</span>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-12 pt-8">
        
        {/* Sidebar Filters */}
        <aside className="xl:col-span-1 space-y-12">
          <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
            <div className="space-y-4">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] flex items-center gap-2 italic">
                <span className="w-2 h-2 bg-rag-red animate-pulse"></span> Search_Signal
              </label>
              <input 
                type="text" 
                className="w-full bg-charcoal-dark border-2 border-silver-bright/10 p-4 text-xs font-mono text-silver-bright placeholder:text-silver/10 focus:outline-none focus:border-rag-red transition-all"
                placeholder="CVE / TARGET / KEYWORD..." 
                value={searchQuery} 
                onChange={(e) => setSearchQuery(e.target.value)} 
              />
            </div>

            <div className="space-y-4">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Severity_Filter</label>
              <div className="grid grid-cols-1 gap-2">
                {['all', 'critical', 'high', 'medium', 'low'].map(s => (
                  <button 
                    key={s}
                    onClick={() => setFilterSeverity(s)}
                    className={`px-4 py-3 text-left text-[10px] font-black uppercase tracking-widest border-2 transition-all flex justify-between items-center ${
                      filterSeverity === s 
                        ? 'bg-rag-red border-black text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' 
                        : 'bg-charcoal-dark border-silver-bright/10 text-silver/40 hover:border-silver/40'
                    }`}
                  >
                    {s}
                    {filterSeverity === s && <span className="material-symbols-outlined text-xs">check_circle</span>}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Category_Isolation</label>
              <select 
                className="w-full bg-charcoal-dark border-2 border-silver-bright/10 p-4 text-[10px] font-mono text-silver-bright uppercase focus:outline-none focus:border-rag-blue appearance-none cursor-pointer" 
                value={filterCategory} 
                onChange={(e) => setFilterCategory(e.target.value)}
              >
                <option value="all">ALL CATEGORIES</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>{cat.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </section>
        </aside>

        {/* Findings List */}
        <section className="xl:col-span-3">
          <div className="space-y-6">
            <AnimatePresence mode='popLayout'>
              {filteredFindings.length > 0 ? (
                <motion.div 
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  className="space-y-6"
                >
                  {filteredFindings.map((f) => (
                    <motion.div 
                      key={f.id}
                      variants={itemVariants}
                      layout
                      className={`group bg-charcoal border-2 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer relative overflow-hidden ${
                        expandedFinding === f.id ? 'border-silver-bright/40' : 'hover:border-silver-bright/20'
                      }`}
                      onClick={() => setExpandedFinding(expandedFinding === f.id ? null : f.id)}
                    >
                      {/* Severity Side Bar */}
                      <div className={`absolute left-0 top-0 bottom-0 w-2 ${
                        f.severity === 'critical' ? 'bg-rag-red' : 
                        f.severity === 'high' ? 'bg-rag-amber' : 
                        f.severity === 'medium' ? 'bg-rag-blue' : 'bg-silver-bright/20'
                      }`}></div>

                      <div className="flex flex-col md:flex-row justify-between gap-6">
                        <div className="space-y-4 flex-1">
                          <div className="flex flex-wrap items-center gap-4">
                             <span className={`px-2 py-0.5 text-[9px] font-black uppercase italic ${
                                f.severity === 'critical' ? 'bg-rag-red text-black' : 
                                f.severity === 'high' ? 'bg-rag-amber text-black' : 
                                'bg-charcoal-dark text-silver-bright/50 border border-silver-bright/10'
                             }`}>
                              {f.severity}
                             </span>
                             <span className="text-[10px] font-mono text-silver/20 uppercase tracking-widest">{f.category}</span>
                             {f.cve && (
                               <span className="bg-rag-blue/10 text-rag-blue px-2 py-0.5 text-[9px] font-mono border border-rag-blue/20">{f.cve}</span>
                             )}
                          </div>
                          <h3 className="text-2xl font-black text-silver-bright uppercase tracking-tight italic group-hover:text-rag-red transition-colors decoration-rag-red/30 group-hover:underline underline-offset-8">
                            {f.title}
                          </h3>
                          <div className="flex items-center gap-6">
                            <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest flex items-center gap-2">
                              <span className="material-symbols-outlined text-xs">target</span> {f.target}
                            </p>
                            <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest flex items-center gap-2">
                              <span className="material-symbols-outlined text-xs">event</span> {new Date(f.discovered_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>

                        <div className="flex flex-row md:flex-col items-end justify-between md:justify-center gap-4">
                          {f.cvss && (
                             <div className="text-right">
                               <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-1 italic">CVSS_Score</p>
                               <p className={`text-2xl font-black font-mono leading-none ${f.cvss >= 9 ? 'text-rag-red' : 'text-silver-bright'}`}>{f.cvss.toFixed(1)}</p>
                             </div>
                          )}
                          <div className="p-3 bg-charcoal-dark border border-white/5 group-hover:border-white/20 transition-all rounded-sm flex items-center justify-center">
                            <span className={`material-symbols-outlined transition-transform duration-500 text-silver/20 group-hover:text-silver-bright ${expandedFinding === f.id ? 'rotate-180' : ''}`}>expand_more</span>
                          </div>
                        </div>
                      </div>

                      {/* Expansion Area */}
                      <AnimatePresence>
                        {expandedFinding === f.id && (
                          <motion.div 
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-8 pt-8 border-t-2 border-dashed border-silver-bright/5 grid grid-cols-1 md:grid-cols-2 gap-12">
                              <div className="space-y-6">
                                <h4 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic flex items-center gap-2">
                                  <span className="w-1 h-3 bg-rag-red"></span> Brief_Report
                                </h4>
                                <p className="text-sm font-mono text-silver/60 leading-relaxed uppercase selection:bg-rag-red selection:text-black">
                                  {f.description}
                                </p>
                              </div>
                              <div className="space-y-6">
                                <h4 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic flex items-center gap-2">
                                  <span className="w-1 h-3 bg-rag-green"></span> Remediations
                                </h4>
                                <div className="bg-charcoal-dark p-6 border-l-4 border-rag-green shadow-[4px_4px_0px_0px_rgba(0,0,0,0.5)]">
                                  <p className="text-xs font-mono text-rag-green/80 leading-relaxed uppercase">
                                    {f.remediation}
                                  </p>
                                </div>
                                <div className="pt-4 flex gap-4">
                                  <button className="bg-silver-bright px-4 py-2 text-[9px] font-black text-black uppercase hover:bg-white transition-all shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none">Assign_Ticket</button>
                                  <button className="border border-silver/20 px-4 py-2 text-[9px] font-black text-silver uppercase hover:text-white transition-all">Ignore_Signal</button>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  ))}
                </motion.div>
              ) : (
                <div className="py-40 bg-charcoal/30 border-4 border-dashed border-silver-bright/5 text-center flex flex-col items-center gap-8">
                  <span className="material-symbols-outlined text-silver/5 text-9xl">shield_check</span>
                  <div className="space-y-2">
                    <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">No Threat Signals Detected</p>
                    <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">Environment synchronization verified // OPSEC GREEN</p>
                  </div>
                </div>
              )}
            </AnimatePresence>
          </div>
        </section>
      </div>

      {/* Decorative End Note */}
      <footer className="pt-20 opacity-20 select-none pointer-events-none flex justify-between items-center text-[9px] font-black uppercase tracking-[0.5em] italic">
        <span>Restricted Intelligence Repository • SecuScan SOC 2024</span>
        <div className="flex gap-2">
          {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="w-6 h-1 bg-silver/20"></div>)}
        </div>
      </footer>
    </div>
  )
}
