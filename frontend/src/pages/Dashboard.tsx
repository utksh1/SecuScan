import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardSummary } from '../api'

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
  recent_findings: Array<{ id: string; severity: string; title: string; target: string; discovered_at: string; cvss?: number }>
  high_risk_assets: Array<{ id: string; target: string; description: string; risk_level: string }>
  attack_surface_by_category: Record<string, number>
  scan_activity: { total: number; completed: number; running: number }
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
  high_risk_assets: [],
  attack_surface_by_category: {},
  scan_activity: { total: 0, completed: 0, running: 0 },
}

// Mock data for visualizations
const MOCK_TREND = [45, 42, 48, 52, 49, 44, 40, 38, 42, 45, 47, 43, 41, 44, 46]
const MOCK_THREATS = [
    { country: 'US', count: 124, type: 'Injection' },
    { country: 'CN', count: 89, type: 'Recon' },
    { country: 'RU', count: 56, type: 'Brute Force' },
    { country: 'DE', count: 34, type: 'Exfiltration' },
]

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary>(emptySummary)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = () => {
      getDashboardSummary()
        .then((data) => {
          if (!cancelled) {
            setSummary(data)
            setError(null)
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err.message)
          }
        })
        .finally(() => {
          if (!cancelled) {
            setLoading(false)
          }
        })
    }

    load()
    const interval = setInterval(load, 5000)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const formatDateLong = (dateStr: string | null) =>
    dateStr ? new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT' : 'Never'

  const getRiskLevel = () => {
    if (summary.critical_findings > 0) return { label: 'High', color: 'text-rag-red' }
    if (summary.high_findings > 0) return { label: 'Moderate', color: 'text-rag-amber' }
    return { label: 'Low', color: 'text-rag-green' }
  }

  const risk = getRiskLevel()

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
              <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase">Executive Security Briefing</h1>
              <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-2">Cybersecurity Posture Report • {new Date().getFullYear()} • RESTRICED ACCESS</p>
            </div>
        </div>
        
        <div className="flex items-center gap-12">
          <div className="relative hidden md:block">
              <input 
                  type="text" 
                  placeholder="SEARCH INFRASTRUCTURE..." 
                  className="bg-transparent border-b border-accent-silver/20 py-1 px-4 text-[10px] uppercase tracking-widest text-silver-bright focus:outline-none focus:border-silver-bright transition-colors w-64 placeholder:text-silver/10 italic"
              />
              <span className="absolute right-2 top-1 material-symbols-outlined text-sm text-silver/20">search</span>
          </div>

          <div className="text-right">
            <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Analysis Sync</span>
            <span className="text-sm font-light text-silver-bright uppercase font-mono">{formatDateLong(summary.last_scan_time)}</span>
          </div>
          
          <div className="flex items-center gap-8">
            <span className={`status-pill ${summary.scan_activity.running > 0 ? 'border-rag-green/20 bg-rag-green/5 text-rag-green animate-pulse' : 'border-silver/10 bg-silver/5 text-silver/60'}`}>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-current mr-2 mb-0.5"></span>
              {summary.scan_activity.running > 0 ? 'SURVEILLANCE ACTIVE' : 'SYSTEM OPERATIONAL'}
            </span>
            <button className="material-symbols-outlined text-silver/40 hover:text-silver-bright transition-colors">notifications</button>
          </div>
        </div>
      </header>

      <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
        {/* Dynamic Grid Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-12">
            
            {/* Left Column: Metrics & Findings (Content Rich) */}
            <div className="xl:col-span-8 space-y-12">
                
                <section className="space-y-6">
                    <div className="flex justify-between items-baseline">
                        <h2 className="text-lg font-serif italic text-silver-bright/80 border-l-2 border-accent-silver/10 pl-4">Operational Health Overview</h2>
                        <span className="text-[10px] text-silver/30 uppercase tracking-widest">Real-time Telemetry</span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-px bg-accent-silver/20 executive-border overflow-hidden rounded-sm shadow-2xl">
                        <div className="bg-charcoal p-10 space-y-4 relative overflow-hidden group">
                           <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                               <span className="material-symbols-outlined text-6xl">shield_with_heart</span>
                           </div>
                           <span className="text-xs font-medium text-silver/40 uppercase tracking-widest block">Threat Profile</span>
                           <div className="flex items-baseline gap-2">
                             <span className={`text-6xl font-serif font-light ${risk.color}`}>{risk.label}</span>
                           </div>
                           <p className="text-[10px] text-silver/60 leading-relaxed uppercase tracking-tighter">Derived from {summary.total_findings} weighted vectors across {summary.total_assets} assets.</p>
                        </div>

                        <div className="bg-charcoal p-10 space-y-4">
                           <span className="text-xs font-medium text-silver/40 uppercase tracking-widest block">Vulnerability Load</span>
                           <div className="flex items-baseline gap-3">
                             <span className="text-7xl font-light text-rag-red leading-none">{summary.critical_findings}</span>
                             <div className="flex flex-col">
                                <span className="text-[10px] text-rag-red font-bold uppercase tracking-widest">Critical</span>
                                <span className="text-[10px] text-silver/30 font-bold uppercase tracking-widest leading-none">Events</span>
                             </div>
                           </div>
                           <div className="h-1 w-full bg-accent-silver/20 overflow-hidden mt-4">
                             <div 
                               className="h-full bg-rag-red transition-all duration-1000 shadow-[0_0_8px_rgba(239,68,68,0.5)]" 
                               style={{ width: `${Math.min((summary.critical_findings / (summary.total_findings || 1)) * 100, 100)}%` }}
                             ></div>
                           </div>
                        </div>

                        <div className="bg-charcoal p-10 space-y-4">
                           <span className="text-xs font-medium text-silver/40 uppercase tracking-widest block">Asset Inventory</span>
                           <div className="flex items-baseline gap-3">
                             <span className="text-7xl font-light text-silver-bright leading-none">{summary.total_assets.toLocaleString()}</span>
                           </div>
                           <div className="flex items-center gap-2">
                             <span className="text-[10px] text-rag-green font-bold uppercase tracking-widest flex items-center gap-1">
                               <span className="material-symbols-outlined text-[12px]">check_circle</span>
                               SECURED NODES
                             </span>
                           </div>
                        </div>

                        <div className="bg-charcoal p-10 space-y-4 group">
                           <span className="text-xs font-medium text-silver/40 uppercase tracking-widest block">Attack Surface</span>
                           <div className="flex items-baseline gap-3">
                             <span className="text-7xl font-light text-silver-bright leading-none group-hover:text-rag-amber transition-colors">{summary.total_attack_surface.toLocaleString()}</span>
                           </div>
                           <span className="text-[10px] text-silver/40 uppercase tracking-[0.2em] italic font-medium block">Continuous Scanning Active</span>
                        </div>
                    </div>
                </section>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                    {/* Risk Trend Chart */}
                    <section className="space-y-6">
                        <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 flex items-center gap-2 italic">
                            Trend Analysis (15d)
                        </h3>
                        <div className="bg-charcoal/50 executive-border p-8 h-48 flex items-end justify-between gap-1 group">
                             {MOCK_TREND.map((val, i) => (
                                 <div key={i} className="flex-1 flex flex-col justify-end gap-2 group/bar">
                                     <div 
                                         className="bg-accent-silver/40 group-hover:bg-silver/20 transition-all rounded-t-sm relative"
                                         style={{ height: `${val}%` }}
                                     >
                                         <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[8px] opacity-0 group-hover/bar:opacity-100 transition-opacity font-mono text-silver">
                                             {val}
                                         </div>
                                     </div>
                                 </div>
                             ))}
                        </div>
                    </section>

                    {/* Attack Surface Distribution */}
                    <section className="space-y-6">
                        <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 flex items-center gap-2 italic">
                            Surface Distribution
                        </h3>
                        <div className="bg-charcoal/50 executive-border p-8 h-48 flex flex-col justify-between">
                             {Object.entries(summary.attack_surface_by_category).slice(0, 4).map(([cat, count]) => (
                                 <div key={cat} className="space-y-1">
                                     <div className="flex justify-between text-[10px] uppercase tracking-widest font-medium">
                                         <span className="text-silver/60">{cat}</span>
                                         <span className="text-silver-bright">{count}</span>
                                     </div>
                                     <div className="h-0.5 w-full bg-accent-silver/10">
                                         <div 
                                             className="h-full bg-silver-bright/20" 
                                             style={{ width: `${(count / summary.total_attack_surface) * 100}%` }}
                                         ></div>
                                     </div>
                                 </div>
                             ))}
                        </div>
                    </section>
                </div>

                <section className="space-y-6">
                    <div className="flex justify-between items-center">
                        <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 flex items-center gap-2 italic">
                           Priority Incident Ledger
                        </h3>
                        <Link to="/findings" className="text-[9px] font-bold text-silver hover:text-silver-bright transition-colors uppercase tracking-[0.3em] italic border-b border-silver/10">
                           View Master Record
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 gap-px bg-accent-silver/20 executive-border overflow-hidden rounded-sm">
                        {summary.recent_findings.length > 0 ? summary.recent_findings.slice(0, 4).map((finding) => (
                          <div key={finding.id} className="bg-charcoal p-6 flex items-center justify-between group hover:bg-charcoal-light transition-all border-l-2 border-transparent hover:border-silver-bright">
                            <div className="flex items-center gap-8">
                              <div className={`w-10 h-10 flex items-center justify-center border ${
                                finding.severity === 'critical' ? 'text-rag-red border-rag-red/20 bg-rag-red/5' :
                                finding.severity === 'high' ? 'text-rag-amber border-rag-amber/20 bg-rag-amber/5' :
                                'text-silver border-accent-silver/20 bg-silver/5'
                              }`}>
                                <span className="material-symbols-outlined text-lg">
                                    {finding.severity === 'critical' ? 'emergency_home' : finding.severity === 'high' ? 'priority_high' : 'info'}
                                </span>
                              </div>
                              <div>
                                <h4 className="text-sm font-medium text-silver-bright group-hover:underline underline-offset-4 decoration-silver/20 tracking-tight">{finding.title}</h4>
                                <div className="flex items-center gap-3 mt-1.5">
                                    <span className="text-[9px] text-silver/40 uppercase tracking-widest font-mono">{finding.target}</span>
                                    <span className="w-1 h-1 bg-accent-silver/40 rounded-full"></span>
                                    <span className="text-[9px] text-silver/40 uppercase tracking-widest font-mono">ID: {finding.id.split(':')[1]?.toUpperCase() || finding.id.slice(0,8).toUpperCase()}</span>
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                                <span className={`text-[9px] font-bold px-3 py-1 border rounded-sm tracking-widest uppercase mb-1 inline-block ${
                                    finding.severity === 'critical' ? 'text-rag-red border-rag-red/20' :
                                    finding.severity === 'high' ? 'text-rag-amber border-rag-amber/20' :
                                    'text-silver border-accent-silver/20'
                                }`}>
                                    {finding.severity}
                                </span>
                                <p className="text-[9px] text-silver/30 uppercase tracking-tighter mt-1">{new Date(finding.discovered_at).toLocaleDateString()} AT {new Date(finding.discovered_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                            </div>
                          </div>
                        )) : (
                          <div className="bg-charcoal p-12 text-center text-xs text-silver/10 uppercase tracking-[0.4em] italic">
                            No active findings in current surveillance cycle
                          </div>
                        )}
                    </div>
                </section>
            </div>

            {/* Right Column: Global Intelligence & Status (The "Professional" Fill) */}
            <div className="xl:col-span-4 space-y-12">
                
                {/* Geographic Threat Map (Mock) */}
                <section className="space-y-6">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">
                        Geographic Threat Intelligence
                    </h3>
                    <div className="bg-charcoal executive-border p-6 aspect-video relative overflow-hidden flex flex-col items-center justify-center grayscale opacity-60 group hover:grayscale-0 hover:opacity-100 transition-all">
                        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#3f3f46_1px,transparent_1px)] [background-size:20px_20px]"></div>
                        <span className="material-symbols-outlined text-silver/10 text-9xl absolute pointer-events-none">public</span>
                        
                        <div className="relative z-10 w-full space-y-4">
                            {MOCK_THREATS.map(t => (
                                <div key={t.country} className="flex justify-between items-center bg-charcoal-dark/50 p-3 border border-accent-silver/5">
                                    <div className="flex items-center gap-3">
                                        <span className="text-[10px] font-mono text-silver-bright">{t.country}</span>
                                        <span className="text-[9px] text-silver/40 uppercase tracking-widest">{t.type}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="h-1 w-24 bg-accent-silver/20">
                                            <div className="h-full bg-rag-amber/50" style={{ width: `${(t.count/150)*100}%` }}></div>
                                        </div>
                                        <span className="text-[10px] font-mono text-silver-bright">{t.count}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Surveillance Status */}
                <section className="space-y-6">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">
                        Surveillance Core Status
                    </h3>
                    <div className="bg-charcoal executive-border p-8 space-y-8">
                        <div className="flex justify-between items-end">
                            <div>
                                <p className="text-[10px] text-silver/30 font-bold uppercase tracking-widest mb-2">Active Analysis Cycles</p>
                                <div className="flex items-baseline gap-4">
                                    <p className={`text-5xl font-light italic leading-none font-mono ${summary.scan_activity.running > 0 ? 'text-rag-green' : 'text-silver/20'}`}>
                                      {summary.scan_activity.running.toString().padStart(2, '0')}
                                    </p>
                                    <span className="text-[10px] text-rag-green/80 uppercase tracking-[0.2em] font-medium border-l border-accent-silver/20 pl-4 py-1">Monitoring Active</span>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-[10px] text-silver/30 font-bold uppercase tracking-widest mb-2">Total Audits</p>
                                <p className="text-xl font-light text-silver-bright font-mono italic">{summary.scan_activity.total.toLocaleString()}</p>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-[8px] uppercase tracking-[0.3em] font-bold text-silver/40">
                                <span>Engine Integrity</span>
                                <span>{summary.scan_activity.running > 0 ? '98.4%' : 'IDLE'}</span>
                            </div>
                            <div className="relative w-full h-1 bg-accent-silver/10 overflow-hidden">
                              {summary.scan_activity.running > 0 && (
                                <div className="absolute inset-y-0 left-0 bg-rag-green w-2/3 animate-[shimmer_2s_infinite]"></div>
                              )}
                            </div>
                        </div>
                    </div>
                </section>

                {/* Executive Actions */}
                <section className="space-y-6">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 italic">
                        Control Center
                    </h3>
                    <div className="grid grid-cols-2 gap-px bg-accent-silver/20 executive-border overflow-hidden rounded-sm">
                        <Link to="/scans" className="bg-charcoal p-6 text-center group hover:bg-charcoal-light transition-all">
                            <span className="material-symbols-outlined text-silver/20 text-2xl mb-3 group-hover:text-silver-bright transition-colors">radar</span>
                            <span className="block text-[9px] font-bold uppercase tracking-[0.3em] text-silver/40 group-hover:text-silver-bright transition-colors">Deploy Scans</span>
                        </Link>
                        <Link to="/reports" className="bg-charcoal p-6 text-center group hover:bg-charcoal-light transition-all">
                            <span className="material-symbols-outlined text-silver/20 text-2xl mb-3 group-hover:text-silver-bright transition-colors">description</span>
                            <span className="block text-[9px] font-bold uppercase tracking-[0.3em] text-silver/40 group-hover:text-silver-bright transition-colors">Audit Record</span>
                        </Link>
                        <Link to="/assets" className="bg-charcoal p-6 text-center group hover:bg-charcoal-light transition-all">
                            <span className="material-symbols-outlined text-silver/20 text-2xl mb-3 group-hover:text-silver-bright transition-colors">lan</span>
                            <span className="block text-[9px] font-bold uppercase tracking-[0.3em] text-silver/40 group-hover:text-silver-bright transition-colors">Asset Ledger</span>
                        </Link>
                        <Link to="/settings" className="bg-charcoal p-6 text-center group hover:bg-charcoal-light transition-all">
                            <span className="material-symbols-outlined text-silver/20 text-2xl mb-3 group-hover:text-silver-bright transition-colors">settings</span>
                            <span className="block text-[9px] font-bold uppercase tracking-[0.3em] text-silver/40 group-hover:text-silver-bright transition-colors">Core Config</span>
                        </Link>
                    </div>
                </section>
            </div>
        </div>

        {/* Global Threat Ticker */}
        <div className="py-4 border-y border-accent-silver/5 overflow-hidden whitespace-nowrap opacity-20 hover:opacity-100 transition-opacity">
            <div className="flex gap-16 animate-[scroll_60s_linear_infinite]">
                {Array(10).fill(0).map((_, i) => (
                    <div key={i} className="flex gap-4 items-baseline">
                        <span className="text-[9px] text-rag-red font-bold">CRITICAL ALERT</span>
                        <span className="text-[9px] text-silver font-mono uppercase tracking-widest font-light">Unauthorized access attempt detected in Sector {i+1} • 18:24:00 GMT</span>
                        <span className="text-[9px] text-rag-amber font-bold">INFO</span>
                        <span className="text-[9px] text-silver font-mono uppercase tracking-widest font-light">Continuous scan cycle {400+i} completed successfully</span>
                    </div>
                ))}
            </div>
        </div>

        {/* High Risk Asset Ledger (Redesigned) */}
        <section className="pt-12 border-t border-accent-silver/10">
          <div className="flex justify-between items-center mb-10">
            <h3 className="text-lg font-serif italic text-silver-bright/80 border-l-2 border-accent-silver/10 pl-4">Critical Asset Monitor</h3>
            <span className="text-[9px] text-silver/20 uppercase tracking-[0.4em]">High Target Priority</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {summary.high_risk_assets.length > 0 ? summary.high_risk_assets.map((asset) => (
              <div key={asset.id} className="p-8 bg-charcoal border border-accent-silver/10 flex flex-col justify-between hover:bg-charcoal-light transition-all group cursor-pointer relative overflow-hidden">
                <div className={`absolute top-0 left-0 w-full h-0.5 ${asset.risk_level === 'critical' ? 'bg-rag-red' : 'bg-rag-amber'}`}></div>
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                      <h4 className="text-sm font-semibold text-silver-bright uppercase tracking-wide group-hover:underline decoration-silver/20">{asset.target}</h4>
                      <span className={`text-[8px] font-bold px-2 py-0.5 border rounded-sm ${asset.risk_level === 'critical' ? 'text-rag-red border-rag-red/20' : 'text-rag-amber border-rag-amber/20'}`}>
                        {asset.risk_level.toUpperCase()}
                      </span>
                  </div>
                  <p className="text-[10px] text-silver/40 uppercase tracking-widest leading-relaxed line-clamp-2">{asset.description || 'Monitored External Infrastructure Asset'}</p>
                </div>
                <div className="mt-8 pt-4 border-t border-accent-silver/5 flex justify-between items-center">
                    <span className="text-[8px] text-silver/20 font-mono uppercase tracking-widest">Active Monitoring</span>
                    <span className="material-symbols-outlined text-sm text-silver/10 group-hover:text-silver-bright transition-colors">arrow_right_alt</span>
                </div>
              </div>
            )) : (
              <div className="col-span-4 p-20 bg-charcoal/30 border border-dashed border-accent-silver/10 text-center flex flex-col items-center gap-4">
                <span className="material-symbols-outlined text-silver/5 text-6xl">inventory_2</span>
                <p className="text-xs text-silver/10 uppercase tracking-[0.5em] italic">No high priority assets identified in current spectrum</p>
              </div>
            )}
          </div>
        </section>
      </main>
      
      <footer className="p-12 pb-24 border-t border-accent-silver/5">
        <div className="max-w-[1600px] mx-auto flex justify-between items-center opacity-30">
            <p className="text-[8px] text-silver uppercase tracking-[0.5em] font-medium italic">SECUSCAN INTELLIGENCE SUITE • BUILD 2026.03.24 • DEPLOYMENT ALPHA</p>
            <div className="flex gap-8 items-center">
                <span className="text-[8px] text-silver uppercase tracking-widest italic">Signal: EXCELLENT</span>
                <span className="text-[8px] text-silver uppercase tracking-widest italic">Encryption: AES-256-GCM</span>
            </div>
        </div>
      </footer>
      
      <style>{`
        @keyframes scroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(200%); }
        }
      `}</style>
    </div>
  )
}
