import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAssets, getFindings } from '../api'

type Asset = {
  id: string
  target: string
  type: string
  description: string
  risk_level: string
  status: string
  last_scanned: string | null
  scan_count: number
  open_ports: number[]
  technologies: string[]
  services: Array<{ port: number; protocol: string; service: string; version?: string }>
}

type Finding = { id: string; target: string; title: string; severity: string; discovered_at: string }

export default function Assets() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)
  const [filterRisk, setFilterRisk] = useState('all')
  const [filterType, setFilterType] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([getAssets(), getFindings()]).then(([assetData, findingData]: any) => {
      setAssets(assetData.assets || [])
      setFindings(findingData.findings || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const filteredAssets = useMemo(
    () =>
      assets.filter((asset) => {
        const matchesRisk = filterRisk === 'all' || asset.risk_level === filterRisk
        const matchesType = filterType === 'all' || asset.type === filterType
        const text = `${asset.target} ${asset.description}`.toLowerCase()
        return matchesRisk && matchesType && text.includes(searchQuery.toLowerCase())
      }),
    [assets, filterRisk, filterType, searchQuery],
  )

  const countsByRisk = useMemo(() => {
      return {
          critical: assets.filter(a => a.risk_level === 'critical').length,
          high: assets.filter(a => a.risk_level === 'high').length,
          medium: assets.filter(a => a.risk_level === 'medium').length,
          low: assets.filter(a => a.risk_level === 'low').length,
      }
  }, [assets])

  const assetFindings = selectedAsset ? findings.filter((v) => v.target === selectedAsset.target) : []

  const formatDateLong = (dateStr: string | null) =>
    dateStr ? new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT' : 'Never'

  return (
    <div className="min-h-screen flex flex-col">
      <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10">
        <div className="flex items-center gap-8">
            <div className="header-decoration hidden xl:block">
                <div className="flex gap-2">
                    {[1,2,3].map(i => <div key={i} className="w-1 h-3 bg-accent-silver/30"></div>)}
                </div>
            </div>
            <div>
              <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase">Asset Infrastructure Registry</h1>
              <p className="text-[10px] font-light text-silver/60 uppercase tracking-[0.4em] mt-2">Active Node Inventory • SECURE ACCESS REQUIRED</p>
            </div>
        </div>
        
        <div className="flex items-center gap-12">
          <div className="text-right border-l border-accent-silver/10 pl-8">
            <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Managed Nodes</span>
            <span className="text-xl font-light text-silver-bright font-mono">{assets.length.toString().padStart(3, '0')}</span>
          </div>
          <div className="flex items-center gap-4">
             <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">download</button>
             <button className="material-symbols-outlined text-silver/20 hover:text-silver-bright transition-colors p-2 border border-accent-silver/10 rounded-full">sync</button>
          </div>
        </div>
      </header>

      <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-700">
        
        {/* Quick Summary Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm">
            <div className="bg-charcoal p-6 flex flex-col justify-center gap-1">
                <span className="text-[8px] font-bold text-silver/30 uppercase tracking-[0.2em] italic">Critical Level</span>
                <span className={`text-2xl font-serif font-light ${countsByRisk.critical > 0 ? 'text-rag-red' : 'text-silver/20'}`}>{countsByRisk.critical}</span>
            </div>
            <div className="bg-charcoal p-6 flex flex-col justify-center gap-1">
                <span className="text-[8px] font-bold text-silver/30 uppercase tracking-[0.2em] italic">High Priority</span>
                <span className={`text-2xl font-serif font-light ${countsByRisk.high > 0 ? 'text-rag-amber' : 'text-silver/20'}`}>{countsByRisk.high}</span>
            </div>
            <div className="bg-charcoal p-6 flex flex-col justify-center gap-1">
                <span className="text-[8px] font-bold text-silver/30 uppercase tracking-[0.2em] italic">Total Findings</span>
                <span className="text-2xl font-serif font-light text-silver-bright">{findings.length}</span>
            </div>
            <div className="bg-charcoal p-6 flex flex-col justify-center gap-1">
                <span className="text-[8px] font-bold text-silver/30 uppercase tracking-[0.2em] italic">Unique IP Space</span>
                <span className="text-2xl font-serif font-light text-silver-bright">{[...new Set(assets.map(a => a.target))].length}</span>
            </div>
            <div className="bg-charcoal p-6 hidden lg:flex flex-col justify-center gap-1 col-span-2">
                <span className="text-[8px] font-bold text-silver/30 uppercase tracking-[0.2em] italic">Inventory Integrity</span>
                <div className="flex items-center gap-4">
                  <span className="text-2xl font-serif font-light text-rag-green">99.8%</span>
                  <div className="flex-1 h-0.5 bg-accent-silver/10 relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 bg-rag-green w-[99.8%]"></div>
                  </div>
                </div>
            </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-stretch pt-4">
            {/* Search and Filters Sidebar-ish */}
            <div className="w-full lg:w-80 space-y-8 flex-shrink-0">
                <div className="space-y-6">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">Search & Filter</h3>
                    <div className="space-y-4">
                        <div className="relative group">
                            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-silver/20 group-focus-within:text-silver-bright transition-colors text-sm">search</span>
                            <input 
                                type="text" 
                                className="w-full bg-charcoal border border-accent-silver/10 pl-12 pr-4 py-3 text-xs text-silver-bright focus:outline-none focus:border-accent-silver/30 transition-all rounded-sm placeholder:text-silver/10 font-mono italic"
                                placeholder="TARGET SEARCH..." 
                                value={searchQuery} 
                                onChange={(e) => setSearchQuery(e.target.value)} 
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[8px] font-bold uppercase tracking-widest text-silver/20 block px-1">Risk Profile</label>
                            <div className="grid grid-cols-2 gap-2">
                                {['all', 'critical', 'high', 'medium', 'low'].map(r => (
                                    <button 
                                        key={r}
                                        onClick={() => setFilterRisk(r)}
                                        className={`px-3 py-2 text-[9px] uppercase tracking-widest border transition-all rounded-sm ${
                                            filterRisk === r ? 'bg-silver/10 border-silver/40 text-silver-bright' : 'bg-charcoal border-accent-silver/10 text-silver/30 hover:border-silver/20'
                                        }`}
                                    >
                                        {r}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="space-y-2 pt-4">
                            <label className="text-[8px] font-bold uppercase tracking-widest text-silver/20 block px-1">Resource Tier</label>
                            <select 
                                className="w-full bg-charcoal border border-accent-silver/10 px-4 py-3 text-[10px] text-silver-bright uppercase tracking-widest focus:outline-none focus:border-accent-silver/30 rounded-sm appearance-none cursor-pointer italic" 
                                value={filterType} 
                                onChange={(e) => setFilterType(e.target.value)}
                            >
                                <option value="all">ALL REACHABLE TYPES</option>
                                {[...new Set(assets.map((asset) => asset.type))].map((type) => <option key={type} value={type}>{type.toUpperCase()}</option>)}
                            </select>
                        </div>
                    </div>
                </div>

                <div className="pt-8 border-t border-accent-silver/10 hidden lg:block">
                     <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 italic mb-6">Threat Distribution</h3>
                     <div className="space-y-4">
                        {Object.entries(countsByRisk).map(([risk, count]) => (
                            <div key={risk} className="flex flex-col gap-1.5">
                                <div className="flex justify-between text-[9px] uppercase tracking-[0.2em]">
                                    <span className="text-silver/40">{risk} level</span>
                                    <span className="text-silver-bright font-mono">{count}</span>
                                </div>
                                <div className="h-0.5 w-full bg-accent-silver/10 overflow-hidden">
                                    <div 
                                        className={`h-full transition-all duration-1000 ${risk === 'critical' ? 'bg-rag-red' : risk === 'high' ? 'bg-rag-amber' : 'bg-silver/40'}`}
                                        style={{ width: `${(count / (assets.length || 1)) * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                     </div>
                </div>
            </div>

            {/* Asset Ledger Table-like Grid */}
            <div className="flex-1 space-y-8 min-w-0 pb-20">
                <div className="flex justify-between items-baseline mb-2">
                    <div className="flex items-center gap-4">
                        <h2 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Registry Master Record ({filteredAssets.length})</h2>
                        <div className="h-px w-24 bg-accent-silver/10"></div>
                    </div>
                    <span className="text-[8px] text-silver/20 uppercase tracking-widest">Sorting: Criticality Spectrum</span>
                </div>
                
                <div className="grid grid-cols-1 gap-px bg-accent-silver/5 executive-border overflow-hidden rounded-sm shadow-2xl relative">
                    {/* Background decoration to fill "empty space" visually */}
                    <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[radial-gradient(#3f3f46_1px,transparent_1px)] [background-size:32px_32px]"></div>

                    <div className="hidden md:grid grid-cols-12 gap-4 px-10 py-5 bg-charcoal-dark border-b border-accent-silver/10 text-[8px] font-bold uppercase tracking-[0.4em] text-silver/20 z-10">
                        <div className="col-span-1">Status</div>
                        <div className="col-span-5">Identity / Virtual Endpoint</div>
                        <div className="col-span-2">Resource Type</div>
                        <div className="col-span-2 text-right">Engagement Space</div>
                        <div className="col-span-2 text-right">Inventory Timestamp</div>
                    </div>

                    {filteredAssets.length > 0 ? filteredAssets.map((asset) => {
                        const ports = Array.isArray(asset.open_ports) ? asset.open_ports : [];
                        return (
                      <div 
                        key={asset.id} 
                        className="bg-charcoal px-10 py-7 grid grid-cols-1 md:grid-cols-12 gap-4 items-center group hover:bg-charcoal-light transition-all cursor-pointer relative overflow-hidden z-10"
                        onClick={() => setSelectedAsset(asset)}
                      >
                        {/* Hover Decoration */}
                        <div className="absolute inset-y-0 left-0 w-1 bg-transparent group-hover:bg-silver-bright transition-all shadow-[0_0_15px_rgba(255,255,255,0.3)]"></div>
                        
                        <div className="col-span-1 flex justify-center md:justify-start">
                            <div className={`w-3.5 h-3.5 rounded-sm rotate-45 ${
                                asset.risk_level === 'critical' ? 'bg-rag-red shadow-[0_0_12px_rgba(239,68,68,0.5)]' : 
                                asset.risk_level === 'high' ? 'bg-rag-amber shadow-[0_0_12px_rgba(245,158,11,0.5)]' : 
                                'bg-rag-green/20'
                            }`}></div>
                        </div>

                        <div className="col-span-5 flex flex-col gap-1.5">
                            <h4 className="text-base font-medium text-silver-bright uppercase tracking-wide group-hover:underline underline-offset-8 decoration-silver/20">{asset.target}</h4>
                            <div className="flex items-center gap-3">
                                <p className="text-[10px] text-silver/30 uppercase tracking-[0.1em] italic font-mono truncate max-w-sm">{asset.description || 'Monitored Infrastructure Endpoint'}</p>
                                {asset.status === 'active' && <span className="w-1.5 h-1.5 bg-rag-green rounded-full animate-pulse"></span>}
                            </div>
                        </div>

                        <div className="col-span-2">
                            <span className="px-3 py-1 border border-accent-silver/10 text-[9px] text-silver-bright/60 uppercase tracking-widest bg-charcoal-dark/80 rounded-sm italic font-medium">
                                {asset.type}
                            </span>
                        </div>

                        <div className="col-span-2 text-right">
                             <div className="flex flex-col items-end gap-2">
                                <span className="text-[10px] text-silver-bright font-mono italic">{(ports).length} Segment{(ports).length !== 1 ? 's' : ''}</span>
                                <div className="flex gap-1">
                                    {(ports).slice(0, 8).map(p => (
                                        <div key={p} className="w-1 h-3.5 bg-accent-silver/20 border-r border-accent-silver/5 hover:bg-rag-green/40 transition-colors"></div>
                                    ))}
                                    {(ports).length > 8 && <span className="text-[8px] text-silver/20 ml-1">+</span>}
                                </div>
                             </div>
                        </div>

                        <div className="col-span-2 text-right">
                            <p className="text-[10px] text-silver/50 uppercase tracking-widest font-mono group-hover:text-silver-bright transition-colors">{asset.last_scanned ? new Date(asset.last_scanned).toLocaleDateString() : 'Pending'}</p>
                            <p className="text-[8px] text-silver/10 uppercase tracking-[0.2em] italic mt-1">Surveillance Logged</p>
                        </div>
                      </div>
                    )}) : (
                      <div className="bg-charcoal p-40 text-center flex flex-col items-center gap-8">
                        <span className="material-symbols-outlined text-silver/5 text-9xl">radar</span>
                        <div className="space-y-4">
                            <p className="text-xs text-silver/20 uppercase tracking-[0.6em] font-medium italic">Spectral Scan Yields Null Result</p>
                            <p className="text-[9px] text-silver/10 uppercase tracking-widest">No assets aligned with current filter vectors</p>
                        </div>
                      </div>
                    )}
                </div>
            </div>
        </div>
      </main>

      {/* Deep-Dive Analysis Sidebar */}
      {selectedAsset && (
        <div className="fixed inset-0 z-[60] flex justify-end">
            <div className="absolute inset-0 bg-charcoal-dark/95 backdrop-blur-md animate-in fade-in duration-500" onClick={() => setSelectedAsset(null)}></div>
            <div className="relative w-full max-w-2xl bg-charcoal h-full border-l border-accent-silver/20 shadow-[-20px_0_50px_rgba(0,0,0,0.8)] flex flex-col animate-in slide-in-from-right duration-500 overflow-hidden">
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <div className="p-16 space-y-16">
                        <div className="flex justify-between items-start">
                            <div className="space-y-4">
                                <div className="flex items-center gap-3">
                                    <span className="text-[9px] font-bold text-silver/30 uppercase tracking-[0.4em] italic">Infrastructure Deep-Dive</span>
                                    <div className="h-px w-12 bg-accent-silver/10"></div>
                                </div>
                                <h2 className="text-5xl font-serif font-light text-silver-bright italic tracking-tighter leading-none">{selectedAsset.target}</h2>
                                <div className="flex items-center gap-4 pt-4">
                                    <span className={`px-4 py-1.5 border text-[10px] font-bold tracking-[0.2em] rounded-sm uppercase ${
                                        selectedAsset.risk_level === 'critical' ? 'border-rag-red/20 text-rag-red bg-rag-red/5' : 
                                        selectedAsset.risk_level === 'high' ? 'border-rag-amber/20 text-rag-amber bg-rag-amber/5' : 
                                        'border-accent-silver/10 text-silver/60 bg-white/5'
                                    }`}>
                                        {selectedAsset.risk_level.toUpperCase()} THREAT VECTOR
                                    </span>
                                    <span className="text-[10px] text-silver/20 uppercase tracking-widest italic font-mono">Sync ID: {selectedAsset.id.slice(0,12)}</span>
                                </div>
                            </div>
                            <button 
                                className="w-14 h-14 flex items-center justify-center border border-accent-silver/10 hover:border-silver-bright text-silver/20 hover:text-silver-bright transition-all rounded-full group bg-charcoal-dark"
                                onClick={() => setSelectedAsset(null)}
                            >
                                <span className="material-symbols-outlined group-hover:rotate-90 transition-transform">close</span>
                            </button>
                        </div>

                        <div className="grid grid-cols-3 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm">
                            <div className="p-10 bg-charcoal-light/20 flex flex-col gap-2">
                                <p className="text-[9px] text-silver/40 font-bold uppercase tracking-widest italic leading-none">Resource Tier</p>
                                <p className="text-sm font-light text-silver-bright uppercase tracking-tight">{selectedAsset.type}</p>
                            </div>
                            <div className="p-10 bg-charcoal-light/20 flex flex-col gap-2">
                                <p className="text-[9px] text-silver/40 font-bold uppercase tracking-widest italic leading-none">Exposure Space</p>
                                <p className="text-sm font-light text-silver-bright italic font-mono">{selectedAsset.open_ports?.length || 0} Ports Active</p>
                            </div>
                            <div className="p-10 bg-charcoal-light/20 flex flex-col gap-2">
                                <p className="text-[9px] text-silver/40 font-bold uppercase tracking-widest italic leading-none">Surveillance</p>
                                <p className="text-sm font-light text-rag-green uppercase tracking-tight italic">Continuous</p>
                            </div>
                        </div>

                        <section className="space-y-8">
                            <div className="flex justify-between items-center border-b border-accent-silver/10 pb-4">
                                <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-silver/30 italic">Active Security Ledger ({assetFindings.length})</h3>
                                {assetFindings.length > 0 && <Link to="/findings" className="text-[9px] text-silver/40 hover:text-silver-bright transition-colors uppercase tracking-[0.2em] italic underline underline-offset-4">Open Matrix</Link>}
                            </div>
                            <div className="space-y-4">
                                {assetFindings.length > 0 ? assetFindings.map(f => (
                                    <div key={f.id} className="p-6 bg-charcoal-dark/50 border border-accent-silver/10 hover:border-silver-bright transition-all group">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className={`text-[9px] font-bold tracking-[0.2em] uppercase ${
                                                f.severity === 'critical' ? 'text-rag-red' : f.severity === 'high' ? 'text-rag-amber' : 'text-silver'
                                            }`}>{f.severity} severity</span>
                                            <span className="text-[9px] text-silver/20 font-mono italic">DISCOVERED {new Date(f.discovered_at).toLocaleDateString()}</span>
                                        </div>
                                        <p className="text-base font-medium text-silver-bright italic tracking-tight group-hover:underline decoration-silver/20 underline-offset-4">{f.title}</p>
                                    </div>
                                )) : (
                                    <div className="py-16 bg-charcoal-dark/30 border border-dashed border-accent-silver/10 text-center flex flex-col items-center gap-4">
                                        <span className="material-symbols-outlined text-silver/5 text-4xl">check_circle</span>
                                        <p className="text-[10px] italic text-silver/10 uppercase tracking-[0.3em]">No active threat vectors documented in current spectrum</p>
                                    </div>
                                )}
                            </div>
                        </section>

                        <section className="grid grid-cols-1 md:grid-cols-2 gap-12">
                            <div className="space-y-8">
                                <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-silver/30 border-b border-accent-silver/10 pb-4 italic">Detected Services</h3>
                                <div className="flex flex-wrap gap-2">
                                    {(selectedAsset.technologies || []).length > 0 ? selectedAsset.technologies.map(t => (
                                        <span key={t} className="px-3 py-1 bg-charcoal-dark border border-accent-silver/10 text-[10px] font-mono text-silver hover:text-silver-bright transition-all cursor-default uppercase">{t}</span>
                                    )) : (
                                        <span className="text-[10px] italic text-silver/20 uppercase tracking-widest">Awaiting fingerprint sync...</span>
                                    )}
                                </div>
                            </div>
                            <div className="space-y-8">
                                <h3 className="text-xs font-bold uppercase tracking-[0.3em] text-silver/30 border-b border-accent-silver/10 pb-4 italic">Vector Map</h3>
                                <div className="grid grid-cols-3 gap-2">
                                    {(selectedAsset.open_ports || []).map(p => (
                                        <div key={p} className="flex flex-col items-center p-3 bg-charcoal-dark border border-rag-green/20 group hover:border-rag-green transition-all relative overflow-hidden">
                                            <div className="absolute top-0 right-0 w-2 h-2 bg-rag-green opacity-10 group-hover:opacity-100 transition-opacity"></div>
                                            <span className="text-[10px] font-mono font-bold text-rag-green italic">PORT {p}</span>
                                            <span className="text-[8px] text-silver/20 uppercase tracking-tighter mt-1 italic">UNRESTRICTED</span>
                                        </div>
                                    ))}
                                    {(selectedAsset.open_ports || []).length === 0 && (
                                        <div className="col-span-3 p-8 border border-dashed border-accent-silver/10 text-center">
                                            <span className="text-[10px] italic text-silver/20 uppercase tracking-widest">No active open vectors</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </section>
                    </div>
                </div>
                
                <div className="p-12 border-t border-accent-silver/10 bg-charcoal-dark/50 flex justify-between items-baseline">
                    <button className="text-[10px] font-bold text-silver/40 hover:text-silver-bright uppercase tracking-[0.3em] italic transition-colors flex items-center gap-2">
                        <span className="material-symbols-outlined text-sm">print</span>
                        Print Intelligence Report
                    </button>
                    <p className="text-[9px] text-silver/20 uppercase tracking-widest font-mono">End of File • Ref: {selectedAsset.id.split('-')[0].toUpperCase()}</p>
                </div>
            </div>
        </div>
      )}
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(0,0,0,0.1);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.05);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.1);
        }
      `}</style>
    </div>
  )
}
