import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from '../components/ThemeContext'
import { useToast } from '../components/ToastContext'

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 200, damping: 25 }
  }
}

const DEFAULT_CONFIG = {
    concurrentScans: 8,
    scanTimeout: 3600,
    scanIntensity: 'standard', // 'low', 'standard', 'aggressive'
    dataRetention: 30, // days
    shodanKey: '',
    virustotalKey: '',
    ipWhitelist: '127.0.0.1\n10.0.0.0/8',
    autoPurgeFailed: false,
    autoRescanCritical: true,
    timezone: 'auto',
    theme: 'dark',
    notifications: {
        scanComplete: true,
        criticalFindings: true,
        systemAlerts: true
    }
}

export default function Settings() {
    const { theme, setTheme } = useTheme()
    const { addToast } = useToast()
    
    const [config, setConfig] = useState(() => {
        const saved = localStorage.getItem('secuscan-config')
        if (saved) {
            try {
                return { ...DEFAULT_CONFIG, ...JSON.parse(saved) }
            } catch (e) {
                return DEFAULT_CONFIG
            }
        }
        return DEFAULT_CONFIG
    })

    const [systemTimezone, setSystemTimezone] = useState('Detecting...')

    useEffect(() => {
        try {
            setSystemTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone)
        } catch (e) {
            setSystemTimezone('UTC')
        }
    }, [])

    const handleSave = () => {
        localStorage.setItem('secuscan-config', JSON.stringify(config))
        addToast("Operational parameters synchronized", "success")
        if (config.theme !== theme) {
            setTheme(config.theme)
        }
    }

    const handleReset = () => {
        if (window.confirm("Restore engine to factory specifications? All API keys and custom rules will be cleared.")) {
            setConfig(DEFAULT_CONFIG)
            localStorage.setItem('secuscan-config', JSON.stringify(DEFAULT_CONFIG))
            addToast("Engine parameters reset to factory defaults", "info")
        }
    }

    const handleExport = () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href",     dataStr);
        downloadAnchorNode.setAttribute("download", `secuscan_config_${new Date().toISOString().split('T')[0]}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
        addToast("Encryption export successful", "success")
    }

    const InputField = ({ label, description, type = "text", value, onChange, placeholder }: any) => (
        <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all group">
            <div className="space-y-2 mb-6">
                <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] block italic group-hover:text-rag-blue transition-colors">{label}</label>
                <p className="text-[9px] text-silver/40 uppercase font-mono font-bold tracking-widest leading-relaxed">{description}</p>
            </div>
            <input 
                type={type}
                value={value}
                onChange={(e) => onChange(type === 'number' ? parseInt(e.target.value) || 0 : e.target.value)}
                placeholder={placeholder}
                className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase"
            />
        </div>
    )

    const SelectField = ({ label, description, value, onChange, options }: any) => (
        <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all group">
            <div className="space-y-2 mb-6">
                <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] block italic group-hover:text-rag-blue transition-colors">{label}</label>
                <p className="text-[9px] text-silver/40 uppercase font-mono font-bold tracking-widest leading-relaxed">{description}</p>
            </div>
            <select 
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase appearance-none"
            >
                {options.map((opt: any) => (
                    <option key={opt.value} value={opt.value} className="bg-charcoal text-silver-bright">{opt.label}</option>
                ))}
            </select>
        </div>
    )

    const Toggle = ({ checked, onChange, label, description }: any) => (
        <button 
            onClick={() => onChange(!checked)}
            className={`flex items-center justify-between p-8 bg-charcoal border-4 border-black transition-all group hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 ${
                checked ? 'shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' : 'shadow-none'
            }`}
        >
            <div className="space-y-2 text-left mr-8">
                <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block group-hover:text-rag-green transition-colors">{label}</label>
                <span className="text-[9px] text-silver/30 uppercase tracking-tighter italic font-mono font-bold leading-relaxed">{description}</span>
            </div>
            <div className={`w-14 h-7 border-4 border-black relative shrink-0 transition-all ${checked ? 'bg-rag-green' : 'bg-charcoal-dark'}`}>
                <div className={`absolute top-0 w-5 h-full bg-black transition-all ${checked ? 'left-7' : 'left-0'}`}></div>
            </div>
        </button>
    )

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
                <div className="space-y-4">
                  <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
                    Engine_Nexus_v4.5.3
                  </div>
                  <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
                    Core <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Array</span>
                  </h1>
                  <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
                    HARDWARE_TUNING // AUDIT_STRATEGY // SECTOR_ISOLATION
                  </p>
                </div>

                <div className="flex flex-col items-end gap-4">
                   <div className="bg-charcoal border-4 border-black px-8 py-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                        <span className="text-[10px] font-black text-silver/20 uppercase tracking-[0.4em] block mb-1 italic">SYSTEM_TIMEZONE_SYNC</span>
                        <span className="text-xs font-black font-mono text-rag-blue tracking-widest italic">{systemTimezone.toUpperCase()}</span>
                    </div>
                </div>
            </header>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-12 pt-4">
                <main className="xl:col-span-3 space-y-20">
                    
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Engine_Parameters</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <SelectField 
                                label="Scanner_Intensity" 
                                description="PACKET_DENSITY_PER_SECOND_THRESHOLD"
                                value={config.scanIntensity}
                                onChange={(val: string) => setConfig({...config, scanIntensity: val})}
                                options={[
                                    { label: 'Low (Stealth/Passive)', value: 'low' },
                                    { label: 'Standard (Balanced)', value: 'standard' },
                                    { label: 'Aggressive (Intrusive)', value: 'aggressive' },
                                ]}
                            />
                            <SelectField 
                                label="Retention_Cycle" 
                                description="AUTOMATED_LOG_PURGE_STRATEGY"
                                value={config.dataRetention}
                                onChange={(val: number) => setConfig({...config, dataRetention: val})}
                                options={[
                                    { label: '7 Days', value: 7 },
                                    { label: '30 Days', value: 30 },
                                    { label: '90 Days', value: 90 },
                                    { label: 'Indefinite', value: 0 },
                                ]}
                            />
                            <InputField 
                                label="Concurrent_Operations" 
                                description="MAX_PARALLEL_TASK_EXECUTION"
                                type="number"
                                value={config.concurrentScans}
                                onChange={(val: number) => setConfig({...config, concurrentScans: val})}
                            />
                            <InputField 
                                label="Execution_Timeout" 
                                description="THRESHOLD_IN_SECONDS_PER_NODE"
                                type="number"
                                value={config.scanTimeout}
                                onChange={(val: number) => setConfig({...config, scanTimeout: val})}
                            />
                        </div>
                    </section>

                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Security_Interface</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <SelectField 
                                label="Temporal_Logic" 
                                description="UI_CHRONOS_ALIGNMENT"
                                value={config.timezone}
                                onChange={(val: string) => setConfig({...config, timezone: val})}
                                options={[
                                    { label: `Follow System (${systemTimezone})`, value: 'auto' },
                                    { label: 'UTC (Universal Coordinated)', value: 'UTC' },
                                    { label: 'Fixed (ZULU)', value: 'GMT' },
                                ]}
                            />
                            <SelectField 
                                label="Visual_Spectrum" 
                                description="OPERATIONAL_AESTHETIC_MODE"
                                value={config.theme}
                                onChange={(val: string) => setConfig({...config, theme: val})}
                                options={[
                                    { label: 'Dark (Obsidian)', value: 'dark' },
                                    { label: 'Light (Paper)', value: 'light' },
                                ]}
                            />
                        </div>
                    </section>

                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Intelligence_API_Link</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <InputField 
                                label="Shodan_Enclave" 
                                description="RECON_TELEMETRY_STREAM_TOKEN"
                                placeholder="SHODAN_SECRET"
                                type="password"
                                value={config.shodanKey}
                                onChange={(val: string) => setConfig({...config, shodanKey: val})}
                            />
                            <InputField 
                                label="VirusTotal_Enclave" 
                                description="MALWARE_INTEL_ACCESS_HASH"
                                placeholder="VT_SECRET_HASH"
                                type="password"
                                value={config.virustotalKey}
                                onChange={(val: string) => setConfig({...config, virustotalKey: val})}
                            />
                        </div>
                    </section>

                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Access_Perimeters</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Authorized_Ingress_Vectors</label>
                                <p className="text-[10px] text-silver/40 uppercase font-bold italic mb-6 leading-relaxed">Line-delimited IP/CIDR whitelist for high-privilege access</p>
                            </div>
                            <textarea 
                                value={config.ipWhitelist}
                                onChange={(e) => setConfig({...config, ipWhitelist: e.target.value})}
                                rows={4}
                                className="w-full bg-black/40 border-4 border-black p-6 text-xs font-mono text-rag-amber font-bold focus:outline-none focus:border-rag-amber/50 transition-colors uppercase resize-none"
                            />
                        </div>
                    </section>

                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Audit_Logic_Toggles</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <Toggle 
                                label="System_Signals" 
                                description="CRITICAL_RX_TELEMETRY"
                                checked={config.notifications.systemAlerts}
                                onChange={(val: boolean) => setConfig({...config, notifications: {...config.notifications, systemAlerts: val}})}
                            />
                            <Toggle 
                                label="Auto_Rescan" 
                                description="TRIGGER_NEW_SCAN_ON_CRITICAL"
                                checked={config.autoRescanCritical}
                                onChange={(val: boolean) => setConfig({...config, autoRescanCritical: val})}
                            />
                             <Toggle 
                                label="Garbage_Collection" 
                                description="AUTO_PURGE_FAILED_SESSIONS"
                                checked={config.autoPurgeFailed}
                                onChange={(val: boolean) => setConfig({...config, autoPurgeFailed: val})}
                            />
                        </div>
                    </section>

                    <section className="pt-12">
                        <button 
                            onClick={handleSave}
                            className="bg-rag-blue text-black px-12 py-6 text-xs font-black uppercase tracking-[0.3em] shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-4 italic group"
                        >
                            COMMIT_ENGINE_CHANGES
                            <span className="material-symbols-outlined font-black group-hover:rotate-12 transition-transform">sync</span>
                        </button>
                    </section>
                </main>

                <aside className="xl:col-span-1 space-y-12">
                    <section className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                        <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.5em] italic mb-8">Management_Tools</h3>
                        <div className="space-y-4">
                            <button 
                                onClick={handleExport}
                                className="w-full py-4 bg-charcoal-dark border-4 border-black text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] hover:bg-black hover:text-white transition-all italic"
                            >
                                TELEMETRY_EXPORT
                            </button>
                            <button 
                                onClick={handleReset}
                                className="w-full py-4 bg-rag-amber border-4 border-black text-[10px] font-black text-black uppercase tracking-[0.3em] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all italic"
                            >
                                ENGINE_RESET
                            </button>
                            <button 
                                className="w-full py-4 bg-rag-red border-4 border-black text-[10px] font-black text-black uppercase tracking-[0.3em] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 transition-all italic"
                                onClick={() => {
                                    if (window.confirm("CRITICAL: THIS WILL PURGE ALL HISTORY AND ASSETS. PROCEED?")) {
                                        localStorage.clear();
                                        window.location.reload();
                                    }
                                }}
                            >
                                NUCLEAR_PURGE
                            </button>
                        </div>
                    </section>

                    <section className="bg-charcoal-dark border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                        <div className="space-y-4">
                            <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.5em] italic border-b-4 border-black pb-4">Engine_Status</h3>
                            <div className="space-y-4 font-mono">
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-silver/30 uppercase tracking-tighter">Engine Version</span>
                                    <span className="text-rag-blue font-bold">4.5.3-BETA</span>
                                </div>
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-silver/30 uppercase tracking-tighter">Stack Health</span>
                                    <span className="text-rag-green font-bold">NOMINAL</span>
                                </div>
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-silver/30 uppercase tracking-tighter">Core Sync</span>
                                    <span className="text-silver-bright font-bold">STABLE</span>
                                </div>
                            </div>
                        </div>
                    </section>
                </aside>
            </div>

            <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
                <div className="flex items-center gap-6">
                    <div className="w-12 h-1 bg-silver/20"></div>
                    RESTRICTED_ACCESS_ENCLAVE // SECUSCAN_CORE_REV_4 // CLASSIFIED_VIEW
                </div>
                <div className="flex gap-4">
                    {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="w-2 h-2 bg-silver/20 rounded-full"></div>)}
                </div>
            </footer>
        </div>
    )
}
