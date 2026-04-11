import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { getAssets, getFindings } from '../api'
import { routes } from '../routes'
import { formatLocaleDate } from '../utils/date'

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

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05
    }
  }
}

const itemVariants: Variants = {
  hidden: { opacity: 0, scale: 0.98, y: 10 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 20 }
  }
}

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

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver selection:bg-rag-blue selection:text-white p-6 md:p-12 space-y-12">
      
      {/* Neo-Brutalist Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <div className="bg-rag-blue text-charcoal-dark px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Registry Protocol v2.4
          </div>
          <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
            Asset <span className="text-transparent stroke-white stroke-1" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Inventory</span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest">
            {assets.length} Active Node Records // Filtered: {filteredAssets.length}
          </p>
        </div>

        <div className="flex flex-wrap gap-4">
          <button className="bg-charcoal px-6 py-4 border-2 border-silver-bright/20 hover:border-silver-bright text-silver-bright transition-all flex items-center gap-3 group shadow-[6px_6px_0px_0px_rgba(0,0,0,0.5)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none">
            <span className="material-symbols-outlined text-sm">download</span>
            <span className="text-xs font-black uppercase tracking-widest">Export.db</span>
          </button>
          <button className="bg-silver-bright px-6 py-4 border-2 border-black text-charcoal-dark transition-all flex items-center gap-3 hover:bg-white shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none">
            <span className="material-symbols-outlined text-sm">sync</span>
            <span className="text-xs font-black uppercase tracking-widest">Rescan.all</span>
          </button>
        </div>
      </header>

      <main className="grid grid-cols-1 xl:grid-cols-4 gap-12">
        
        {/* Left Sidebar: Controls & Stats */}
        <aside className="xl:col-span-1 space-y-6">
          
          {/* Quick Metrics */}
          <section className="grid grid-cols-2 gap-4">
            <div className="bg-charcoal p-6 border-2 border-rag-red/30 shadow-[4px_4px_0px_0px_rgba(255,51,102,0.1)]">
              <span className="text-[10px] font-black text-rag-red uppercase tracking-widest block mb-1">Critical</span>
              <span className="text-4xl font-black text-silver-bright font-mono">{countsByRisk.critical.toString().padStart(2, '0')}</span>
            </div>
            <div className="bg-charcoal p-6 border-2 border-rag-amber/30 shadow-[4px_4px_0px_0px_rgba(255,170,0,0.1)]">
              <span className="text-[10px] font-black text-rag-amber uppercase tracking-widest block mb-1">High</span>
              <span className="text-4xl font-black text-silver-bright font-mono">{countsByRisk.high.toString().padStart(2, '0')}</span>
            </div>
          </section>

          {/* Search & Filters */}
          <section className="bg-charcoal border-4 border-black p-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-5">
            <div className="space-y-3">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] flex items-center gap-2">
                <span className="w-2 h-2 bg-rag-blue"></span> Search_Target
              </label>
              <div className="relative group">
                <input 
                  type="text" 
                  className="w-full bg-charcoal-dark border-2 border-silver-bright/10 p-4 text-xs font-mono text-silver-bright focus:outline-none focus:border-rag-blue transition-all"
                  placeholder="IP / HOST / DESC..." 
                  value={searchQuery} 
                  onChange={(e) => setSearchQuery(e.target.value)} 
                />
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] flex items-center gap-2">
                <span className="w-2 h-2 bg-rag-amber"></span> Risk_Level
              </label>
              <div className="grid grid-cols-2 gap-2">
                {['all', 'critical', 'high', 'medium', 'low'].map(r => (
                  <button 
                    key={r}
                    onClick={() => setFilterRisk(r)}
                    className={`px-3 py-3 text-[10px] font-black uppercase tracking-widest border-2 transition-all ${
                      filterRisk === r 
                        ? 'bg-rag-blue border-black text-charcoal-dark shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' 
                        : 'bg-charcoal-dark border-silver-bright/10 text-silver/40 hover:border-silver/40'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] flex items-center gap-2">
                <span className="w-2 h-2 bg-rag-green"></span> Resource_Tier
              </label>
              <select 
                className="w-full bg-charcoal-dark border-2 border-silver-bright/10 p-4 text-[10px] font-mono text-silver-bright uppercase tracking-widest focus:outline-none focus:border-rag-green appearance-none cursor-pointer" 
                value={filterType} 
                onChange={(e) => setFilterType(e.target.value)}
              >
                <option value="all">ANY REACHABLE TIER</option>
                {[...new Set(assets.map((asset) => asset.type))].map((type) => (
                  <option key={type} value={type}>{type.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </section>

          {/* Distribution Graph (Mini) */}
          <section className="bg-charcoal p-8 border-2 border-silver-bright/10 space-y-6">
            <h3 className="text-[10px] font-black text-silver/40 uppercase tracking-widest italic">Threat Spectrum</h3>
            <div className="space-y-4">
              {Object.entries(countsByRisk).map(([risk, count]) => (
                <div key={risk} className="space-y-1.5 text-[10px] font-mono uppercase">
                  <div className="flex justify-between">
                    <span className="text-silver/40">{risk}</span>
                    <span className="text-silver-bright">{count}</span>
                  </div>
                  <div className="h-1.5 w-full bg-charcoal-dark overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${(count / (assets.length || 1)) * 100}%` }}
                      className={`h-full ${
                        risk === 'critical' ? 'bg-rag-red' : risk === 'high' ? 'bg-rag-amber' : 'bg-silver/40'
                      }`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </aside>

        {/* Right Content: The Grid */}
        <div className="xl:col-span-3">
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
          >
            {filteredAssets.length > 0 ? filteredAssets.map((asset) => (
              <motion.div 
                key={asset.id} 
                variants={itemVariants}
                onClick={() => setSelectedAsset(asset)}
                className="group bg-charcoal border-2 border-silver-bright/10 p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,0.3)] hover:border-silver-bright hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,0.5)] transition-all cursor-pointer relative"
              >
                {/* Status Indicator */}
                <div className={`absolute top-0 right-0 w-16 h-1 w-full flex ${
                  asset.risk_level === 'critical' ? 'bg-rag-red' : 
                  asset.risk_level === 'high' ? 'bg-rag-amber' : 'bg-silver/20'
                }`}></div>

                <div className="flex justify-between items-start mb-6">
                  <div className="bg-charcoal-dark px-2 py-0.5 text-[9px] font-mono text-silver/60 uppercase border border-silver-bright/10">
                    ID: {asset.id.slice(0, 8)}
                  </div>
                  {asset.status === 'active' && (
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-black text-rag-green uppercase tracking-[0.2em] italic">Active_Pulse</span>
                      <div className="w-2 h-2 bg-rag-green rounded-full animate-ping"></div>
                    </div>
                  )}
                  {asset.status === 'scanning' && (
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-black text-rag-amber uppercase tracking-[0.2em] italic">Scanning...</span>
                      <div className="w-2 h-2 bg-rag-amber rounded-full animate-pulse"></div>
                    </div>
                  )}
                </div>

                <h3 className="text-2xl font-black text-silver-bright uppercase tracking-tight mb-2 group-hover:text-rag-blue transition-colors">
                  {asset.target}
                </h3>
                <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest mb-8 h-8 line-clamp-2 italic">
                  {asset.description || 'MONITORED_NODAL_POINT'}
                </p>

                <div className="grid grid-cols-2 gap-4 border-t-2 border-silver-bright/10 pt-6">
                  <div className="space-y-1">
                    <span className="text-[8px] font-black text-silver/40 uppercase tracking-widest block">Type.Tier</span>
                    <span className="text-[10px] font-mono text-silver-bright">{asset.type}</span>
                  </div>
                  <div className="space-y-1 text-right">
                    <span className="text-[8px] font-black text-silver/40 uppercase tracking-widest block">Exposure.Surface</span>
                    <span className="text-[10px] font-mono text-rag-green italic">{(asset.open_ports?.length || 0)} Vectors</span>
                  </div>
                </div>
              </motion.div>
            )) : (
              <div className="col-span-full py-32 bg-charcoal/50 border-4 border-dashed border-silver-bright/10 text-center space-y-8">
                <span className="material-symbols-outlined text-silver/5 text-9xl">radar</span>
                <div className="space-y-2">
                  <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">Null Yield In Current Spectrum</p>
                  <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">Adjust filters to broaden detection radius</p>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </main>

      {/* Asset Deep-Dive Modal */}
      <AnimatePresence>
        {selectedAsset && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 md:p-12">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedAsset(null)}
              className="absolute inset-0 bg-charcoal-dark/95 backdrop-blur-xl"
            />
            
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative w-full max-w-4xl bg-charcoal-dark border-8 border-black shadow-[24px_24px_0px_0px_rgba(0,0,0,1)] flex flex-col max-h-[90vh] overflow-hidden"
            >
              {/* Modal Header */}
              <div className="p-8 md:p-12 bg-charcoal border-b-8 border-black flex justify-between items-start">
                <div className="space-y-4">
                  <div className="bg-rag-amber text-charcoal-dark px-3 py-1 text-[10px] font-black uppercase tracking-widest inline-block shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
                    Deep Intelligence Report
                  </div>
                  <h2 className="text-4xl md:text-6xl font-black text-silver-bright uppercase tracking-tighter leading-none italic break-all">
                    {selectedAsset.target}
                  </h2>
                </div>
                <button 
                  onClick={() => setSelectedAsset(null)}
                  className="bg-rag-red w-14 h-14 border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] flex items-center justify-center text-black hover:bg-white transition-all active:translate-x-1 active:translate-y-1 active:shadow-none"
                >
                  <span className="material-symbols-outlined font-black">close</span>
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-y-auto p-8 md:p-12 space-y-12 bg-[#0d0e12] [background-size:20px_20px] [background-image:radial-gradient(rgba(255,255,255,0.02)_1px,transparent_1px)]">
                
                {/* Info Grid */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-px bg-black shadow-[10px_10px_0px_0px_rgba(0,0,0,0.5)]">
                  <div className="bg-charcoal p-8 space-y-2">
                    <span className="text-[10px] font-black text-silver/30 uppercase tracking-[0.2em]">Risk_Profile</span>
                    <p className={`text-xl font-black uppercase ${
                      selectedAsset.risk_level === 'critical' ? 'text-rag-red' : 
                      selectedAsset.risk_level === 'high' ? 'text-rag-amber' : 'text-silver-bright'
                    }`}>{selectedAsset.risk_level}</p>
                  </div>
                  <div className="bg-charcoal p-8 space-y-2">
                    <span className="text-[10px] font-black text-silver/30 uppercase tracking-[0.2em]">Asset_Type</span>
                    <p className="text-xl font-black text-silver-bright uppercase">{selectedAsset.type}</p>
                  </div>
                  <div className="bg-charcoal p-8 space-y-2">
                    <span className="text-[10px] font-black text-silver/30 uppercase tracking-[0.2em]">Active_Ports</span>
                    <p className="text-xl font-black text-rag-green font-mono">{(selectedAsset.open_ports?.length || 0)}/65535</p>
                  </div>
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                  
                  {/* Vulnerabilities List */}
                  <section className="space-y-6">
                    <h3 className="text-base font-black text-silver-bright uppercase tracking-widest flex items-center gap-3">
                      <span className="w-3 h-3 bg-rag-red"></span> Detected_Flaws
                    </h3>
                    <div className="space-y-4">
                      {assetFindings.length > 0 ? assetFindings.map(f => (
                        <div key={f.id} className="bg-charcoal p-6 border-2 border-silver-bright/5 hover:border-rag-red/30 transition-all group">
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-[9px] font-mono text-rag-red">{f.severity.toUpperCase()} EXPOSURE</span>
                            <span className="text-[8px] font-mono text-silver/20">{formatLocaleDate(f.discovered_at)}</span>
                          </div>
                          <p className="text-sm font-black text-silver-bright uppercase tracking-tight group-hover:text-rag-red transition-colors italic">{f.title}</p>
                        </div>
                      )) : (
                        <div className="py-12 bg-black/20 border-2 border-dashed border-silver-bright/5 text-center px-6">
                          <p className="text-[10px] font-mono text-silver/20 uppercase tracking-widest italic">No active threat vectors documented.</p>
                        </div>
                      )}
                    </div>
                  </section>

                  {/* Vectors and Tech */}
                  <section className="space-y-12">
                    <div className="space-y-6">
                      <h3 className="text-base font-black text-silver-bright uppercase tracking-widest flex items-center gap-3">
                        <span className="w-3 h-3 bg-rag-green"></span> Port_Matrix
                      </h3>
                      <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                        {(selectedAsset.open_ports || []).map(p => (
                          <div key={p} className="bg-charcoal-dark border-2 border-rag-green/20 px-3 py-1.5 text-rag-green hover:bg-rag-green hover:text-black transition-all">
                            {p.toString().padStart(5, '0')}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-6">
                      <h3 className="text-base font-black text-silver-bright uppercase tracking-widest flex items-center gap-3">
                        <span className="w-3 h-3 bg-rag-blue"></span> Technology_Stack
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {(selectedAsset.technologies || []).map(t => (
                          <span key={t} className="bg-charcoal-dark border border-silver-bright/10 px-3 py-1 text-[9px] font-black text-silver/60 uppercase tracking-widest hover:text-silver-bright transition-all">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </section>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="p-8 bg-charcoal border-t-8 border-black flex justify-between items-center">
                 <Link 
                  to={routes.findings} 
                  className="bg-black px-6 py-3 text-[10px] font-black uppercase tracking-widest text-silver-bright hover:bg-rag-blue hover:text-charcoal-dark transition-all shadow-[4px_4px_0px_0px_rgba(255,255,255,0.1)] active:shadow-none active:translate-x-1 active:translate-y-1"
                >
                  View_Intelligence_Matrix
                </Link>
                <div className="text-[8px] font-mono text-silver/20 uppercase text-right leading-none">
                  Intel_Ref: SEC-ASSET-{selectedAsset.id.split('-')[0].toUpperCase()}<br/>
                  End of System Log
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
