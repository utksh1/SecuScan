import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from '../components/ThemeContext'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 }
}

export default function Settings() {
    const { theme, setTheme } = useTheme()
    const [sessionTimeout, setSessionTimeout] = useState('30')
    const [notifications, setNotifications] = useState({
        scanComplete: true,
        criticalFindings: true,
        weeklyDigest: false,
        systemAlerts: true
    })

    const Toggle = ({ checked, onChange, label, description }: any) => (
        <button 
            onClick={() => onChange(!checked)}
            className={`flex items-center justify-between p-8 bg-charcoal border-4 border-black transition-all group hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 ${
                checked ? 'shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' : 'shadow-none'
            }`}
        >
            <div className="space-y-2 text-left">
                <label className="text-xs font-black text-silver-bright uppercase tracking-widest block group-hover:text-rag-blue transition-colors">{label}</label>
                <span className="text-[10px] text-silver/40 uppercase tracking-tighter italic font-mono font-bold">{description}</span>
            </div>
            <div className={`w-16 h-8 border-4 border-black relative transition-all ${checked ? 'bg-rag-green' : 'bg-charcoal-dark shadow-inner'}`}>
                <div className={`absolute top-0 w-6 h-full bg-black transition-all ${checked ? 'left-8' : 'left-0'}`}></div>
            </div>
        </button>
    )

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            {/* Neo-Brutalist Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
                <div className="space-y-4">
                  <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
                    Protocol_Control v4.0
                  </div>
                  <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
                    System <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Config</span>
                  </h1>
                  <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
                    OVERRIDE_PARAMETERS // CORE_STABILITY // ACCESS_VECTORS
                  </p>
                </div>

                <div className="flex items-center gap-6">
                   <div className="bg-charcoal border-4 border-black px-8 py-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                        <span className="text-[10px] font-black text-silver/20 uppercase tracking-[0.4em] block mb-1 italic">ENCLAVE_ID</span>
                        <span className="text-xs font-black font-mono text-silver-bright tracking-widest">SECUSCAN-LX-01</span>
                    </div>
                </div>
            </header>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-12 pt-4">
                {/* Main Settings Grid */}
                <main className="xl:col-span-3 space-y-16">
                    
                    {/* UI Architecture */}
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Interface_Matrix</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <motion.div variants={itemVariants} initial="hidden" animate="visible" className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Visual Spectrum</label>
                                    <p className="text-[10px] text-silver/40 uppercase font-bold italic mb-6">Select primary rendering engine</p>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    {(['dark', 'light'] as const).map(t => (
                                        <button 
                                            key={t}
                                            onClick={() => setTheme(t)}
                                            className={`py-4 text-[10px] font-black uppercase tracking-[0.3em] border-4 transition-all ${
                                                theme === t 
                                                ? 'bg-rag-red text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' 
                                                : 'bg-charcoal-dark border-black text-silver/20 hover:text-white hover:border-silver-bright/20'
                                            }`}
                                        >
                                            {t}
                                        </button>
                                    ))}
                                </div>
                            </motion.div>

                            <motion.div variants={itemVariants} initial="hidden" animate="visible" className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Information Density</label>
                                    <p className="text-[10px] text-silver/40 uppercase font-bold italic mb-6">Granular telemetry distribution</p>
                                </div>
                                <div className="flex items-center gap-6 pt-4">
                                    <span className="text-[10px] font-black text-silver/20 uppercase tracking-[0.2em]">MIN</span>
                                    <div className="flex-1 h-4 bg-charcoal-dark border-4 border-black p-1">
                                        <div className="h-full bg-rag-blue w-[85%] shadow-[0_0_10px_#3b82f6]"></div>
                                    </div>
                                    <span className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">MAX</span>
                                </div>
                            </motion.div>
                        </div>
                    </section>

                    {/* Access Protocols */}
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Security_Protocols</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <motion.div variants={itemVariants} initial="hidden" animate="visible" className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
                                <div className="flex justify-between items-start">
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Session_Dormancy</label>
                                        <p className="text-[10px] text-silver/40 uppercase font-bold italic">Automatic termination interval</p>
                                    </div>
                                    <select 
                                        className="bg-charcoal-dark border-4 border-black p-4 text-[10px] font-black font-mono text-silver-bright uppercase focus:outline-none appearance-none cursor-pointer italic"
                                        value={sessionTimeout}
                                        onChange={(e) => setSessionTimeout(e.target.value)}
                                    >
                                        <option value="15">15M_SECURE</option>
                                        <option value="30">30M_NORMAL</option>
                                        <option value="60">1H_EXTENDED</option>
                                        <option value="never">INF_PERSISTENT</option>
                                    </select>
                                </div>
                                <div className="h-0.5 bg-black/10 w-full mb-4"></div>
                                <div className="flex justify-between items-center group">
                                    <div className="space-y-1">
                                        <span className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Authorized Vectors</span>
                                        <span className="text-[9px] text-silver/20 uppercase italic font-mono font-bold tracking-widest">Global IP Isolation</span>
                                    </div>
                                    <span className="text-[10px] text-rag-green font-black font-mono italic px-4 py-2 border-2 border-black bg-rag-green/10">0.0.0.0/0_ACTIVE</span>
                                </div>
                            </motion.div>

                            <motion.div variants={itemVariants} initial="hidden" animate="visible" className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-center items-center gap-8 group">
                                <div className="w-20 h-20 border-4 border-black border-dashed flex items-center justify-center bg-charcoal-dark group-hover:border-solid group-hover:bg-rag-amber transition-all duration-500 cursor-pointer shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                                    <span className="material-symbols-outlined text-silver/20 group-hover:text-black transition-colors text-4xl">shield_person</span>
                                </div>
                                <div className="text-center space-y-4">
                                    <p className="text-[10px] font-black text-silver/20 uppercase tracking-[0.4em] italic leading-none block">MULTI_FACTOR_SYNC</p>
                                    <button className="bg-silver-bright border-4 border-black px-8 py-3 text-[10px] font-black uppercase text-black italic tracking-widest hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 transition-all">ESTABLISH_MFA_HANDSHAKE</button>
                                </div>
                            </motion.div>
                        </div>
                    </section>

                    {/* Notification Signal Matrix */}
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Transmission_Signal_Matrix</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <Toggle 
                                label="Mission_Final_Signal" 
                                description="TX_FINALIZATION_PACKET" 
                                checked={notifications.scanComplete} 
                                onChange={(val: boolean) => setNotifications({...notifications, scanComplete: val})}
                            />
                            <Toggle 
                                label="Criticality_Override" 
                                description="URGENT_LEVEL_CRITICAL_RX" 
                                checked={notifications.criticalFindings} 
                                onChange={(val: boolean) => setNotifications({...notifications, criticalFindings: val})}
                            />
                            <Toggle 
                                label="Temporal_Archive_RX" 
                                description="WEEKLY_BRIEFING_BULLET_IN" 
                                checked={notifications.weeklyDigest} 
                                onChange={(val: boolean) => setNotifications({...notifications, weeklyDigest: val})}
                            />
                            <Toggle 
                                label="Enclave_Stabilizer" 
                                description="CORE_UPTIME_AND_HEALTH_LOGS" 
                                checked={notifications.systemAlerts} 
                                onChange={(val: boolean) => setNotifications({...notifications, systemAlerts: val})}
                            />
                        </motion.div>
                    </section>
                </main>

                {/* Sidebar Diagnostics */}
                <aside className="xl:col-span-1 space-y-12">
                    <section className="bg-charcoal-dark border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-10 group overflow-hidden relative">
                         <div className="absolute top-0 right-0 w-32 h-32 opacity-[0.02] -mr-16 -mt-16 pointer-events-none group-hover:scale-150 transition-transform duration-[4s]">
                            <span className="material-symbols-outlined text-[200px] text-silver-bright">construction</span>
                        </div>
                        <div className="space-y-8 relative z-10">
                            <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.5em] italic border-b-4 border-black pb-4">Internal_Diagnostics</h3>
                            <div className="space-y-6">
                                {[
                                    { label: 'Core Version', val: '2.4.0-STABLE', color: 'text-silver-bright' },
                                    { label: 'Uptime', val: '00:12:44:02', color: 'text-rag-green' },
                                    { label: 'IOPS', val: '4,221 REQ/S', color: 'text-rag-blue' },
                                    { label: 'Latency', val: '12.2 MS', color: 'text-rag-green' },
                                ].map((row, i) => (
                                    <div key={i} className="flex justify-between items-end border-b-2 border-black border-dashed pb-3">
                                        <span className="text-[9px] font-black text-silver/20 uppercase tracking-[0.2em] italic">{row.label}</span>
                                        <span className={`text-[10px] font-black font-mono italic ${row.color}`}>{row.val}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="space-y-4 pt-10">
                             <div className="flex justify-between items-baseline">
                                 <span className="text-[9px] font-black text-silver/20 uppercase tracking-widest italic leading-none">MEM_ALLOCATION</span>
                                 <span className="text-[8px] font-mono text-rag-green font-black">STABLE</span>
                            </div>
                            <div className="flex gap-1.5 h-16 items-end">
                                {[40, 60, 30, 80, 50, 70, 45, 90, 30, 55, 65, 40].map((h, i) => (
                                    <div key={i} className="flex-1 bg-black/10 relative overflow-hidden h-full group/bar">
                                        <div 
                                            className={`absolute bottom-0 w-full transition-all duration-700 bg-rag-blue/20 group-hover/bar:bg-rag-blue ${i === 7 ? 'bg-rag-red' : ''}`} 
                                            style={{ height: `${h}%` }}
                                        ></div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>

                    <section className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                        <h3 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.4em] italic mb-6">Enclave_Health</h3>
                        <div className="space-y-4">
                            <button className="w-full py-4 bg-charcoal-dark border-4 border-black text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] hover:bg-black hover:text-white transition-all italic">ENCRYPTED_DB_EXPORT</button>
                            <button className="w-full py-4 bg-charcoal-dark border-4 border-black text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] hover:bg-black hover:text-white transition-all italic">REVALIDATE_PROTOCOLS</button>
                            <button className="w-full py-4 bg-rag-red border-4 border-black text-[10px] font-black text-black uppercase tracking-[0.3em] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 transition-all italic">NUCLEAR_PURGE</button>
                        </div>
                    </section>
                </aside>
            </div>

            {/* Tactical Footer */}
            <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
                <div className="flex items-center gap-6">
                    <div className="w-12 h-1 bg-silver/20"></div>
                    RESTRICTED_ACCESS_VIEW // PROTOCOL_LEVEL_SEVEN // ENCLAVE_REVISION_ALPHA
                </div>
                <div className="flex gap-4">
                    {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="w-2 h-2 bg-silver/20 rounded-full"></div>)}
                </div>
            </footer>
        </div>
    )
}
