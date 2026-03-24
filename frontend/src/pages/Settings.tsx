import React, { useState } from 'react'

export default function Settings() {
    const [theme, setTheme] = useState('dark')
    const [sessionTimeout, setSessionTimeout] = useState('30')
    const [notifications, setNotifications] = useState({
        scanComplete: true,
        criticalFindings: true,
        weeklyDigest: false,
        systemAlerts: true
    })
    const [scanDefaults, setScanDefaults] = useState({
        defaultMode: 'light',
        autoConsent: false,
        saveHistory: true
    })

    const Toggle = ({ checked, onChange, label, description }: any) => (
        <div className="flex items-center justify-between p-6 bg-charcoal border border-accent-silver/5 hover:border-accent-silver/20 transition-all group">
            <div className="space-y-1">
                <label className="text-[10px] font-bold text-silver-bright uppercase tracking-widest block">{label}</label>
                <span className="text-[9px] text-silver/30 uppercase tracking-tighter italic font-mono">{description}</span>
            </div>
            <button 
                onClick={() => onChange(!checked)}
                className={`w-12 h-6 border transition-all relative flex items-center px-1 ${
                    checked ? 'bg-rag-green/10 border-rag-green/40' : 'bg-charcoal-dark border-accent-silver/10'
                }`}
            >
                <div className={`w-3 h-3 transition-all ${checked ? 'translate-x-6 bg-rag-green shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'translate-x-0 bg-silver/20'}`}></div>
            </button>
        </div>
    )

    return (
        <div className="min-h-screen flex flex-col">
            <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10">
                <div className="flex items-center gap-8">
                    <div className="header-decoration hidden xl:block">
                        <span className="material-symbols-outlined text-accent-silver/30 text-4xl animate-pulse">settings</span>
                    </div>
                    <div>
                        <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">Protocol Configuration</h1>
                        <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">System Parameters • Operational Overrides • SECURITY ENCLAVE</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-12">
                   <div className="text-right border-l border-accent-silver/10 pl-8">
                        <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Node Identification</span>
                        <span className="text-xs font-mono text-silver-bright uppercase">SECUSCAN-LX-01</span>
                    </div>
                </div>
            </header>

            <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
                
                <div className="flex flex-col lg:flex-row gap-12 items-stretch pt-4">
                    {/* Main Settings Area */}
                    <div className="flex-1 space-y-12 min-w-0">
                        
                        {/* Appearance & Interface */}
                        <section className="space-y-6">
                            <div className="flex items-center gap-6">
                                <h3 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">User interface dynamics</h3>
                                <div className="h-px flex-1 bg-accent-silver/5"></div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm shadow-xl">
                                <div className="p-8 bg-charcoal space-y-4">
                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] font-bold text-silver-bright uppercase tracking-widest">Visual Matrix Theme</label>
                                        <span className="text-[9px] text-silver/30 uppercase italic font-mono mb-4">Select the primary rendering spectrum</span>
                                    </div>
                                    <div className="grid grid-cols-3 gap-2">
                                        {['dark', 'light', 'system'].map(t => (
                                            <button 
                                                key={t}
                                                onClick={() => setTheme(t)}
                                                className={`py-3 text-[9px] uppercase tracking-widest border transition-all ${
                                                    theme === t ? 'bg-silver-bright text-charcoal-dark border-silver-bright font-bold italic' : 'bg-charcoal-dark border-accent-silver/10 text-silver/30 hover:border-silver/40'
                                                }`}
                                            >
                                                {t}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="p-8 bg-charcoal space-y-4">
                                    <div className="flex flex-col gap-1.5">
                                        <label className="text-[10px] font-bold text-silver-bright uppercase tracking-widest">Interface Density</label>
                                        <span className="text-[9px] text-silver/30 uppercase italic font-mono mb-4">Set information granularity baseline</span>
                                    </div>
                                    <div className="flex gap-4 items-center">
                                        <span className="text-[10px] text-silver/20 uppercase tracking-widest">Low</span>
                                        <div className="flex-1 h-1.5 bg-charcoal-dark border border-accent-silver/10 relative">
                                            <div className="absolute top-0 left-0 w-3/4 h-full bg-silver/20"></div>
                                        </div>
                                        <span className="text-[10px] text-silver-bright uppercase tracking-widest italic">High</span>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Security Protocols */}
                        <section className="space-y-6">
                            <div className="flex items-center gap-6">
                                <h3 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Access security architecture</h3>
                                <div className="h-px flex-1 bg-accent-silver/5"></div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm shadow-xl">
                                <div className="p-8 bg-charcoal space-y-6">
                                    <div className="flex justify-between items-start">
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-silver-bright uppercase tracking-widest">Session Expiration</label>
                                            <span className="text-[9px] text-silver/30 uppercase italic font-mono">Automated protocol termination</span>
                                        </div>
                                        <select 
                                            className="bg-charcoal-dark border border-accent-silver/10 px-4 py-2 text-[10px] text-silver-bright focus:outline-none focus:border-silver/40 rounded-sm italic font-mono"
                                            value={sessionTimeout}
                                            onChange={(e) => setSessionTimeout(e.target.value)}
                                        >
                                            <option value="15">15M_SECURE</option>
                                            <option value="30">30M_NORMAL</option>
                                            <option value="60">1H_EXTENDED</option>
                                            <option value="never">INF_PERSISTENT</option>
                                        </select>
                                    </div>
                                    <div className="h-px bg-accent-silver/5"></div>
                                    <div className="flex justify-between items-center group">
                                        <div className="space-y-1">
                                            <span className="text-[10px] font-bold text-silver-bright uppercase tracking-widest block">Authorized IP Range</span>
                                            <span className="text-[9px] text-silver/30 uppercase italic font-mono">Restricted access vectors</span>
                                        </div>
                                        <span className="text-[10px] text-rag-green font-mono italic">GLOBAL_ANY</span>
                                    </div>
                                </div>
                                <div className="p-8 bg-charcoal flex flex-col justify-center items-center gap-6">
                                    <div className="w-16 h-16 border border-dashed border-accent-silver/20 flex items-center justify-center rounded-full group hover:border-silver-bright/40 transition-all cursor-pointer">
                                        <span className="material-symbols-outlined text-silver/20 group-hover:text-silver-bright transition-colors text-3xl">shield_lock</span>
                                    </div>
                                    <div className="text-center space-y-2">
                                        <span className="text-[10px] font-extrabold text-silver/20 uppercase tracking-[0.4em] italic mb-1 block">Multi-Factor Intel</span>
                                        <button className="text-[10px] text-silver-bright uppercase tracking-widest border border-accent-silver/10 px-6 py-2 hover:bg-white/5 transition-all italic">Synchronize MFA Agent</button>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Signaling & Transmission */}
                        <section className="space-y-6">
                            <div className="flex items-center gap-6">
                                <h3 className="text-[10px] font-bold uppercase tracking-[0.4em] text-silver/30 italic">Notification Signal paths</h3>
                                <div className="h-px flex-1 bg-accent-silver/5"></div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-accent-silver/5 overflow-hidden rounded-sm border border-accent-silver/10">
                                <Toggle 
                                    label="Mission End Signal" 
                                    description="Transmission upon scan finalization" 
                                    checked={notifications.scanComplete} 
                                    onChange={(val: boolean) => setNotifications({...notifications, scanComplete: val})}
                                />
                                <Toggle 
                                    label="Criticality Alert" 
                                    description="Urgent signal for risk_level:critical" 
                                    checked={notifications.criticalFindings} 
                                    onChange={(val: boolean) => setNotifications({...notifications, criticalFindings: val})}
                                />
                                <Toggle 
                                    label="Temporal Deep Archive" 
                                    description="Weekly briefing packet transmission" 
                                    checked={notifications.weeklyDigest} 
                                    onChange={(val: boolean) => setNotifications({...notifications, weeklyDigest: val})}
                                />
                                <Toggle 
                                    label="Enclave System Logs" 
                                    description="Core stability and update notifications" 
                                    checked={notifications.systemAlerts} 
                                    onChange={(val: boolean) => setNotifications({...notifications, systemAlerts: val})}
                                />
                            </div>
                        </section>
                    </div>

                    {/* Technical Sidebar Infrastructure */}
                    <aside className="w-full lg:w-96 space-y-12 flex-shrink-0 relative">
                        {/* System Health / Data Visualization in Sidebar to fill empty space */}
                        <div className="p-10 bg-charcoal-dark border border-accent-silver/10 rounded-sm space-y-10 relative overflow-hidden group shadow-2xl">
                             <div className="absolute top-0 right-0 w-32 h-32 opacity-[0.02] -mr-16 -mt-16 pointer-events-none group-hover:scale-150 transition-transform duration-[3s]">
                                <span className="material-symbols-outlined text-[200px]">dns</span>
                            </div>
                            
                            <div className="space-y-6 relative z-10">
                                <h3 className="text-[11px] font-bold text-silver-bright uppercase tracking-[0.5em] italic flex items-center gap-4">
                                    Enclave Diagnostics
                                    <div className="flex-1 h-px bg-accent-silver/10"></div>
                                </h3>
                                
                                <div className="space-y-8">
                                    {[
                                        { label: 'Compute Version', val: '1.0.0-PROX', color: 'text-silver-bright' },
                                        { label: 'Latency Matrix', val: '14 MS', color: 'text-rag-green' },
                                        { label: 'Signal Strength', val: '-42 dBm', color: 'text-rag-green' },
                                        { label: 'Disk Persistence', val: 'RAID-0_STRIPED', color: 'text-silver/40' },
                                    ].map((row, i) => (
                                        <div key={i} className="flex justify-between items-end border-b border-accent-silver/5 pb-3 group/row">
                                            <span className="text-[9px] text-silver/20 uppercase tracking-widest font-mono group-hover/row:text-silver-bright/20 transition-colors">{row.label}</span>
                                            <span className={`text-[10px] font-mono leading-none ${row.color} italic`}>{row.val}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-6 pt-10">
                                <div className="flex justify-between items-baseline">
                                     <span className="text-[9px] font-bold text-silver/30 uppercase tracking-widest">Memory Allocation</span>
                                     <span className="text-[8px] text-silver/10 font-mono italic">ACTIVE_POOL</span>
                                </div>
                                <div className="flex gap-1 h-12">
                                    {[30, 45, 20, 60, 80, 40, 55, 30, 25, 40, 65, 50, 20, 15].map((h, i) => (
                                        <div key={i} className="flex-1 flex flex-col justify-end">
                                            <div className="w-full bg-accent-silver/5 relative group/bar">
                                                <div 
                                                    className={`w-full bg-silver/10 group-hover/bar:bg-rag-green/40 transition-all ${i % 3 === 0 ? 'bg-rag-amber/20' : ''}`} 
                                                    style={{ height: `${h}%` }}
                                                ></div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="p-10 space-y-8 border border-dashed border-accent-silver/10 rounded-sm">
                            <h3 className="text-[10px] font-bold text-silver-bright uppercase tracking-[0.3em] italic">Archive Maintenance</h3>
                            <div className="space-y-4">
                                <button className="w-full py-4 bg-charcoal border border-accent-silver/10 text-[9px] text-silver/40 uppercase tracking-[0.4em] hover:bg-silver/5 hover:text-white transition-all italic font-bold">Encrypted Data Export</button>
                                <button className="w-full py-4 bg-charcoal border border-accent-silver/10 text-[9px] text-silver/40 uppercase tracking-[0.4em] hover:bg-silver/5 hover:text-white transition-all italic font-bold">Clear Operational Cache</button>
                                <button className="w-full py-4 bg-rag-red/5 border border-rag-red/20 text-[9px] text-rag-red/40 uppercase tracking-[0.4em] hover:bg-rag-red/10 hover:text-rag-red transition-all italic font-bold">Nuclear Data Purge</button>
                            </div>
                        </div>

                        {/* Subtle Background Watermark */}
                        <div className="absolute -bottom-20 -right-20 pointer-events-none opacity-[0.03] select-none rotate-[-15deg] hidden lg:block">
                            <h2 className="text-[200px] font-serif font-black italic tracking-tighter leading-none">ALPHA</h2>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    )
}
