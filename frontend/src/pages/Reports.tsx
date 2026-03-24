import React, { useEffect, useState } from 'react'
import { getDashboardSummary, getReports } from '../api'

type Report = {
  id: string
  name: string
  type: 'executive' | 'technical' | 'compliance'
  generated_at: string
  status: 'ready' | 'generating' | 'failed'
  findings: number
  assets: number
  pages: number
}

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([])
  const [summary, setSummary] = useState<any>({ total_findings: 0, total_assets: 0, critical_findings: 0, high_findings: 0, total_attack_surface: 0 })
  const [selectedType, setSelectedType] = useState('all')
  const [hoveredReport, setHoveredReport] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getReports(), getDashboardSummary()]).then(([reportData, summaryData]: any) => {
      setReports(reportData.reports || [])
      setSummary(summaryData || {})
    })
  }, [])

  const filteredReports = reports.filter((report) => selectedType === 'all' || report.type === selectedType)
  const formatDateLong = (dateStr: string) => 
    new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10">
        <div className="flex items-center gap-8">
            <div className="header-decoration hidden xl:block">
                <div className="flex gap-1 items-center">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="w-2 h-2 border border-accent-silver/30 rotate-45"></div>
                    ))}
                </div>
            </div>
            <div>
              <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase">Analysis Repository</h1>
              <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-2 italic">Historical Intelligence • Encrypted Archive • BRIEFING LOGS</p>
            </div>
        </div>
        
        <div className="flex items-center gap-12">
          <div className="text-right border-l border-accent-silver/10 pl-8">
            <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Archive Version</span>
            <span className="text-xs font-mono text-silver-bright/80 uppercase">v2.4.0-STABLE</span>
          </div>
          <div className="flex items-center gap-4">
             <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">search</button>
             <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">download_for_offline</button>
          </div>
        </div>
      </header>

      <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
        
        {/* Metric Overview Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm relative">
            <div className="absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-silver/20 to-transparent"></div>
            {[
                { label: 'Archived Briefings', val: reports.length, color: 'text-silver-bright', suffix: 'Files' },
                { label: 'Total Surface Impact', val: summary.total_assets || 0, color: 'text-silver/60', suffix: 'Nodes' },
                { label: 'Aggregate Risk Delta', val: '−12%', color: 'text-rag-green', suffix: 'Improvement' },
                { label: 'Compliance Index', val: '98.2', color: 'text-rag-green', suffix: 'Percentile' },
            ].map((m, i) => (
                <div key={i} className="p-10 bg-charcoal flex flex-col justify-center gap-2 group hover:bg-charcoal-light/50 transition-all cursor-default">
                    <span className="text-[8px] font-bold text-silver/20 uppercase tracking-[0.3em] italic leading-none">{m.label}</span>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-4xl font-serif font-light ${m.color}`}>{m.val.toString().padStart(2, '0')}</span>
                        <span className="text-[8px] text-silver/10 uppercase tracking-widest font-mono">{m.suffix}</span>
                    </div>
                </div>
            ))}
        </div>

        <div className="flex flex-col lg:flex-row gap-12 items-stretch pt-4">
            {/* Filter Sidebar */}
            <div className="w-full lg:w-80 space-y-12 flex-shrink-0">
                <div className="space-y-10">
                    <div className="space-y-4">
                        <label className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Classification Spectrum</label>
                        <div className="flex flex-col gap-2">
                            {['all', 'executive', 'technical', 'compliance'].map(t => (
                                <button 
                                    key={t}
                                    onClick={() => setSelectedType(t)}
                                    className={`px-6 py-4 text-[10px] uppercase tracking-[0.2em] text-left border transition-all rounded-sm flex justify-between items-center group ${
                                        selectedType === t ? 'bg-silver/5 border-silver/40 text-silver-bright italic translate-x-1' : 'bg-charcoal border-accent-silver/5 text-silver/20 hover:border-silver/20'
                                    }`}
                                >
                                    <span>{t} Briefings</span>
                                    <div className={`w-1 h-3 transition-all ${selectedType === t ? 'bg-silver-bright h-5' : 'bg-silver/5 group-hover:bg-silver/20'}`}></div>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="p-8 bg-charcoal border border-accent-silver/5 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 opacity-[0.05] pointer-events-none">
                            <span className="material-symbols-outlined text-6xl">verified</span>
                        </div>
                        <h4 className="text-[10px] font-bold text-silver-bright uppercase tracking-[0.2em] mb-4">Integrity Verification</h4>
                        <p className="text-[10px] text-silver/40 font-light leading-relaxed italic">
                            Each report is cryptographically signed and hashed. Modifications outside the secure shell are strictly prohibited and detectable by the system audit daemon.
                        </p>
                    </div>
                </div>

                <div className="space-y-6 pt-6 opacity-40 hover:opacity-100 transition-opacity">
                    <div className="flex items-center gap-4">
                        <div className="w-2 h-2 bg-rag-green rounded-full"></div>
                        <span className="text-[9px] text-silver-bright uppercase tracking-widest font-mono italic">Audit Log Active</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="w-2 h-2 bg-accent-silver/10 rounded-full"></div>
                        <span className="text-[9px] text-silver/30 uppercase tracking-widest font-mono italic">Sync Mode: Encrypted</span>
                    </div>
                </div>
            </div>

            {/* Reports Ledger */}
            <div className="flex-1 space-y-8 min-w-0 pb-20">
                <div className="flex justify-between items-baseline border-b border-accent-silver/10 pb-4">
                    <h2 className="text-[10px] font-bold uppercase tracking-[0.5em] text-silver/40 italic">Briefing Archive Ledger ({filteredReports.length})</h2>
                    <span className="text-[8px] text-silver/20 uppercase tracking-widest font-mono">Archive Volume: 12.4 GB</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm relative shadow-2xl">
                    <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[radial-gradient(#3f3f46_1px,transparent_1px)] [background-size:32px_32px]"></div>

                    {filteredReports.length > 0 ? filteredReports.map((report) => (
                      <div 
                        key={report.id} 
                        className="bg-charcoal p-12 flex flex-col justify-between gap-10 group hover:bg-charcoal-light transition-all cursor-pointer relative overflow-hidden border-r border-b border-accent-silver/5"
                        onMouseEnter={() => setHoveredReport(report.id)}
                        onMouseLeave={() => setHoveredReport(null)}
                      >
                        {/* Status Indicator Bar */}
                        <div className={`absolute top-0 left-0 h-1 transition-all duration-700 ${
                            report.status === 'ready' ? 'bg-rag-green w-full opacity-20' : 
                            report.status === 'failed' ? 'bg-rag-red w-full' : 'bg-rag-amber w-1/2 animate-pulse'
                        } group-hover:opacity-100`}></div>

                        <div className="space-y-6">
                            <div className="flex justify-between items-start">
                                <span className={`text-[9px] font-bold uppercase tracking-[0.3em] px-3 py-1 border ${
                                    report.type === 'executive' ? 'border-silver-bright/20 text-silver-bright bg-white/5' : 
                                    report.type === 'compliance' ? 'border-rag-green/20 text-rag-green bg-rag-green/5' : 
                                    'border-accent-silver/10 text-silver/40'
                                }`}>{report.type} BRIEFING</span>
                                <span className="material-symbols-outlined text-silver/10 group-hover:text-silver-bright transition-colors text-xl">description</span>
                            </div>
                            
                            <div>
                                <h3 className="text-2xl font-serif font-light text-silver-bright italic tracking-tight group-hover:underline underline-offset-[12px] decoration-silver/20 leading-snug">{report.name}</h3>
                                <p className="text-[10px] text-silver/30 uppercase tracking-widest mt-4 font-mono italic">ARCHIVE_ID: {report.id.slice(0, 8)}</p>
                            </div>
                        </div>

                        <div className="space-y-8">
                            <div className="grid grid-cols-3 gap-6 py-6 border-y border-dashed border-accent-silver/10">
                                <div className="space-y-1">
                                    <span className="text-[8px] text-silver/20 uppercase font-bold tracking-widest block">Findings</span>
                                    <span className="text-sm font-mono text-silver-bright">{report.findings}</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-[8px] text-silver/20 uppercase font-bold tracking-widest block">Assets</span>
                                    <span className="text-sm font-mono text-silver-bright">{report.assets}</span>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-[8px] text-silver/20 uppercase font-bold tracking-widest block">Pages</span>
                                    <span className="text-sm font-mono text-silver-bright">{report.pages}</span>
                                </div>
                            </div>
                            
                            <div className="flex justify-between items-center pt-2">
                                <span className="text-[10px] text-silver/40 uppercase tracking-widest italic">{formatDateLong(report.generated_at)}</span>
                                <div className="flex gap-4">
                                    <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors text-lg">visibility</button>
                                    <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors text-lg">download</button>
                                </div>
                            </div>
                        </div>

                         {/* Background Hover Decoration */}
                         <div className={`absolute -right-8 -bottom-8 material-symbols-outlined text-9xl text-white/5 transition-all duration-1000 transform ${hoveredReport === report.id ? 'scale-110 rotate-12 rotate-y-[-20deg] opacity-10' : 'scale-100 rotate-0 opacity-0'}`}>
                            {report.type === 'executive' ? 'leaderboard' : report.type === 'compliance' ? 'verified_user' : 'terminal'}
                         </div>
                      </div>
                    )) : (
                      <div className="bg-charcoal p-48 text-center flex flex-col items-center gap-10 col-span-2 border border-dashed border-accent-silver/10">
                        <div className="w-24 h-24 flex items-center justify-center border border-accent-silver/5 rounded-full">
                            <span className="material-symbols-outlined text-silver/5 text-6xl">folder_off</span>
                        </div>
                        <div className="space-y-4">
                            <p className="text-xs text-silver/20 uppercase tracking-[0.6em] font-medium italic">Archive Buffer Empty</p>
                            <p className="text-[10px] text-silver/10 uppercase tracking-widest">Reports will manifest here upon mission task completion</p>
                        </div>
                      </div>
                    )}
                </div>
            </div>
        </div>
      </main>
    </div>
  )
}
