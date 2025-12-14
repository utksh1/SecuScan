import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { API_BASE } from '../api'

interface Task {
    task_id: string
    plugin_id: string
    tool: string
    target: string
    status: string
    created_at: string
    started_at?: string
    completed_at?: string
    duration_seconds?: number
    exit_code?: number
}

interface TaskResult {
    summary?: string[]
    severity_counts?: Record<string, number>
    structured?: {
        findings?: Array<{
            severity: string
            title: string
            description?: string
            [key: string]: any
        }>
        [key: string]: any
    }
    raw_output_excerpt?: string
    errors?: Array<{ message: string }>
}

export default function TaskDetails() {
    const { taskId } = useParams()
    const navigate = useNavigate()

    const [task, setTask] = useState<Task | null>(null)
    const [result, setResult] = useState<TaskResult | null>(null)
    const [rawOutput, setRawOutput] = useState<string>('')
    const [loading, setLoading] = useState(true)
    const [showRawOutput, setShowRawOutput] = useState(true)

    useEffect(() => {
        loadTask()

        const es = new EventSource(`${API_BASE}/task/${taskId}/stream`)

        es.addEventListener('status', (e) => {
            try {
                const data = JSON.parse(e.data)
                setTask(prev => prev ? { ...prev, status: data.status } : null)

                if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                    es.close()
                    loadTask()
                }
            } catch (err) {
                console.error("Failed to parse status event", err)
            }
        })

        es.addEventListener('output', (e) => {
            try {
                const data = JSON.parse(e.data)
                setRawOutput(prev => prev + data.chunk)
            } catch (err) {
                console.error("Failed to parse output event", err)
            }
        })

        es.onerror = (err) => {
            console.error("EventSource error:", err)
            es.close()
        }

        return () => es.close()
    }, [taskId])

    async function loadTask() {
        try {
            const [statusRes, resultRes] = await Promise.all([
                fetch(`${API_BASE}/tasks/${taskId}`),
                fetch(`${API_BASE}/tasks/${taskId}/result`).catch(() => null)
            ])

            const statusData = await statusRes.json()
            setTask(statusData)

            if (resultRes?.ok) {
                const resultData = await resultRes.json()
                setResult(resultData.result || null)
                setRawOutput(resultData.output || '')
            }
        } catch (err) {
            console.error('Failed to load task:', err)
        } finally {
            setLoading(false)
        }
    }

    if (loading || !task) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <span className="material-symbols-outlined animate-spin text-4xl text-silver/20 font-light">sync</span>
                    <span className="text-[10px] font-bold uppercase tracking-[0.4em] italic opacity-40 animate-pulse">Decrypting System Log...</span>
                </div>
            </div>
        )
    }

    const findings = result?.structured?.findings || []
    const formatDateLong = (dateStr: string) =>
        new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT'

    return (
        <div className="min-h-screen flex flex-col scale-in-center overflow-x-hidden">
            <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10 bg-charcoal-dark/50 backdrop-blur-md sticky top-0 z-40">
                <div className="flex items-center gap-8">
                    <button 
                        className="w-12 h-12 flex items-center justify-center border border-accent-silver/20 hover:border-silver/40 text-silver/40 hover:text-white transition-all rounded-sm group relative overflow-hidden"
                        onClick={() => navigate('/history')}
                    >
                         <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <span className="material-symbols-outlined text-sm relative z-10">arrow_back</span>
                    </button>
                    <div>
                        <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">Intelligence Briefing Dossier</h1>
                        <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">Ref_ID: SIG_{taskId?.split('-')[0].toUpperCase()} • CLASSIFIED DATA ENCLAVE</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-6">
                    {task.status === 'completed' && (
                        <div className="flex gap-4">
                             <button 
                                className="px-8 py-3 bg-transparent border border-accent-silver/20 text-[9px] text-silver/60 uppercase font-black tracking-widest hover:border-silver/60 hover:text-white transition-all italic whitespace-nowrap"
                                onClick={() => window.open(`${API_BASE}/task/${taskId}/report/csv`)}
                            >
                                [ Export_Spreadsheet ]
                            </button>
                            <button 
                                className="px-8 py-3 bg-silver-bright text-charcoal-dark text-[9px] font-black uppercase tracking-widest hover:bg-white transition-all italic shadow-2xl relative group"
                                onClick={() => window.open(`${API_BASE}/task/${taskId}/report/pdf`)}
                            >
                                <span className="relative z-10">Generate_Briefing_PDF</span>
                                <div className="absolute inset-x-0 bottom-0 h-0.5 bg-black/20 group-hover:h-1 transition-all"></div>
                            </button>
                        </div>
                    )}
                </div>
            </header>

            <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
                    {/* Left Column: Core Analysis */}
                    <div className="lg:col-span-3 space-y-12 min-w-0">
                        {/* Target Summary Section */}
                        <section className="space-y-6">
                            <div className="flex justify-between items-center bg-charcoal-dark border border-accent-silver/5 p-1 relative group overflow-hidden">
                                <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                                    task.status === 'completed' ? 'bg-rag-green' : 'bg-rag-amber'
                                }`}></div>
                                <div className="p-10 flex-1 space-y-6">
                                     <div className="flex justify-between items-start">
                                        <div className="space-y-1">
                                            <span className="text-[8px] text-silver/20 font-black uppercase tracking-[0.4em] italic block">Subject Node Infrastructure</span>
                                            <h2 className="text-6xl font-serif font-light text-silver-bright italic tracking-tighter leading-none">{task.target}</h2>
                                        </div>
                                        <div className={`px-4 py-2 border text-[10px] font-black uppercase tracking-[0.4em] italic italic font-mono ${
                                            task.status === 'completed' ? 'text-rag-green border-rag-green/20' : 'text-rag-amber border-rag-amber/20'
                                        }`}>{task.status}</div>
                                    </div>
                                    
                                    <div className="flex flex-wrap gap-12 text-[10px] font-bold uppercase tracking-[0.3em] text-silver/30 italic font-mono border-t border-accent-silver/5 pt-6">
                                        <span className="flex items-center gap-2">
                                            <span className="material-symbols-outlined text-[10px] text-rag-blue">terminal</span>
                                            AGENT_PROTOCOL: {task.tool}
                                        </span>
                                        <span className="flex items-center gap-2">
                                            <span className="material-symbols-outlined text-[10px] text-rag-blue">schedule</span>
                                            SIGNAL_INIT: {formatDateLong(task.created_at)}
                                        </span>
                                        {task.duration_seconds && (
                                            <span className="flex items-center gap-2">
                                                <span className="material-symbols-outlined text-[10px] text-rag-blue">hourglass_top</span>
                                                PROCESS_TIME: {Math.round(task.duration_seconds).toString().padStart(3, '0')}s
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Findings Grid */}
                        {findings.length > 0 && (
                            <section className="space-y-8">
                                <div className="flex items-baseline gap-6">
                                    <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic">Tactical Findings Ledger</h3>
                                    <div className="flex-1 h-px bg-accent-silver/10"></div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {findings.map((f, idx) => (
                                        <div key={idx} className="p-8 bg-charcoal border border-accent-silver/5 hover:border-silver/20 transition-all group relative">
                                            <div className={`absolute left-0 top-0 bottom-0 w-1 transition-all group-hover:w-2 ${
                                                f.severity === 'critical' ? 'bg-rag-red' : 
                                                f.severity === 'high' ? 'bg-rag-amber' : 'bg-rag-blue'
                                            }`}></div>
                                            <div className="flex justify-between items-start mb-6 font-mono italic">
                                                <span className={`text-[9px] font-black tracking-widest uppercase ${
                                                    f.severity === 'critical' ? 'text-rag-red' : 
                                                    f.severity === 'high' ? 'text-rag-amber' : 'text-rag-blue-bright/60'
                                                }`}>[ {f.severity}_THREAT_DETECTED ]</span>
                                                <span className="text-[10px] text-silver/10 select-none">#{idx + 1}</span>
                                            </div>
                                            <h4 className="text-md font-serif font-light text-silver-bright uppercase tracking-wide italic mb-4 group-hover:text-white transition-colors">{f.title}</h4>
                                            {f.description && <p className="text-[11px] text-silver/40 font-light leading-relaxed italic border-t border-accent-silver/5 pt-4">{f.description}</p>}
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* TTY Stream Monitor */}
                        <section className="space-y-8">
                             <div className="flex justify-between items-center border-b border-accent-silver/10 pb-4">
                                <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic">Subprocess_Intervention_Stream</h3>
                                <button 
                                    onClick={() => setShowRawOutput(!showRawOutput)}
                                    className="text-[9px] font-black uppercase tracking-widest text-silver/30 hover:text-white transition-colors border border-accent-silver/20 px-4 py-1 italic"
                                >
                                    {showRawOutput ? '[ DISCONNECT_MONITOR ]' : '[ ATTACH_MONITOR ]'}
                                </button>
                            </div>
                            {showRawOutput && (
                                <div className="bg-black/40 border border-accent-silver/10 p-10 rounded-sm font-mono text-[11px] overflow-x-auto leading-relaxed shadow-inner backdrop-blur-sm group/tty">
                                    <div className="flex items-center gap-3 mb-10 border-b border-accent-silver/5 pb-6 opacity-40">
                                        <div className="flex gap-1.5">
                                            <div className="w-2.5 h-2.5 rounded-full border border-rag-red opacity-80 shadow-[0_0_8px_red]"></div>
                                            <div className="w-2.5 h-2.5 rounded-full border border-rag-amber opacity-80 shadow-[0_0_8px_orange]"></div>
                                            <div className="w-2.5 h-2.5 rounded-full border border-rag-green opacity-80 shadow-[0_0_8px_green]"></div>
                                        </div>
                                        <span className="ml-6 text-[9px] uppercase tracking-[0.5em] font-black italic">ACTIVE_DAEMON_PIPE_TX#8821</span>
                                        <div className="flex-1 h-px bg-accent-silver/5 ml-4"></div>
                                    </div>
                                    <pre className="text-silver/60 whitespace-pre-wrap selection:bg-rag-blue/30 selection:text-white group-hover/tty:text-silver/80 transition-colors duration-700 italic">
                                        {rawOutput || 'Awaiting signal transmission from remote node...'}
                                        {task.status === 'running' && <span className="inline-block w-2 h-4 bg-rag-blue animate-pulse ml-2 align-middle shadow-[0_0_10px_#3b82f6]"></span>}
                                    </pre>
                                </div>
                            )}
                        </section>
                    </div>

                    {/* Right Column: Briefing Sidebar */}
                    <aside className="space-y-12">
                        {/* Risk Matrix Component */}
                        <section className="space-y-8">
                            <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic border-b border-accent-silver/10 pb-4 flex justify-between items-center">
                                Risk_Matrix 
                                <span className="material-symbols-outlined text-xs">grid_view</span>
                            </h3>
                            <div className="grid grid-cols-1 gap-px bg-accent-silver/5 executive-border overflow-hidden rounded-sm">
                                {['critical', 'high', 'medium', 'low'].map(sev => {
                                    const count = result?.severity_counts?.[sev] || 0
                                    return (
                                        <div key={sev} className={`p-8 bg-charcoal flex justify-between items-center transition-all ${count > 0 ? 'bg-charcoal-light shadow-inner' : 'opacity-10 opacity-5 grayscale'}`}>
                                            <div className="space-y-1">
                                                <span className={`text-[10px] font-black uppercase tracking-[.3em] italic ${
                                                    sev === 'critical' ? 'text-rag-red' : 
                                                    sev === 'high' ? 'text-rag-amber' : 'text-rag-blue'
                                                }`}>{sev}</span>
                                                <span className="text-[8px] text-silver/20 uppercase tracking-widest block font-mono italic">SIGNAL_STRENGTH</span>
                                            </div>
                                            <span className="text-4xl font-serif font-light text-silver-bright">{count.toString().padStart(2, '0')}</span>
                                        </div>
                                    )
                                })}
                            </div>
                        </section>

                        {/* Intelligence Summary Section */}
                        {result?.summary && result.summary.length > 0 && (
                            <section className="space-y-8">
                                <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic border-b border-accent-silver/10 pb-4">Briefing_Intelligence</h3>
                                <div className="space-y-6">
                                    {result.summary.map((s, idx) => (
                                        <div key={idx} className="flex gap-6 items-start group">
                                            <span className="text-[9px] text-silver/10 font-mono mt-1 font-black group-hover:text-rag-blue transition-colors">[{ (idx + 1).toString().padStart(2, '0') }]</span>
                                            <p className="text-[11px] font-light text-silver/60 leading-relaxed italic group-hover:text-silver-bright transition-colors">{s}</p>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* Operational Diagnostics Section */}
                        <section className="p-10 border border-dashed border-accent-silver/10 rounded-sm bg-charcoal/5 space-y-8">
                             <h3 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic">System_Stability</h3>
                             <div className="space-y-6">
                                <div className="flex justify-between items-center font-mono italic">
                                    <span className="text-[9px] text-silver/20 uppercase tracking-widest">Memory_Saturation</span>
                                    <span className="text-[10px] text-rag-green">0.45GB</span>
                                </div>
                                <div className="h-0.5 bg-accent-silver/5 w-full relative overflow-hidden">
                                    <div className="absolute inset-y-0 left-0 bg-rag-green w-[32%] opacity-60"></div>
                                </div>
                                <div className="flex justify-between items-center font-mono italic">
                                    <span className="text-[9px] text-silver/20 uppercase tracking-widest">Network_Latency</span>
                                    <span className="text-[10px] text-rag-green">14MS</span>
                                </div>
                                <div className="h-0.5 bg-accent-silver/5 w-full relative overflow-hidden">
                                     <div className="absolute inset-y-0 left-0 bg-rag-blue w-[12%] opacity-60"></div>
                                </div>
                             </div>
                             
                             {result?.errors && result.errors.length > 0 && (
                                <div className="pt-8 space-y-4">
                                    <p className="text-[9px] font-black text-rag-red uppercase tracking-[0.4em] italic border-t border-rag-red/20 pt-6">Corruption_Detected</p>
                                    <div className="space-y-3">
                                        {result.errors.map((e, idx) => (
                                            <p key={idx} className="text-[10px] font-mono text-rag-red/60 italic leading-tight">ERR_{idx.toString().padStart(3, '0')}: {e.message}</p>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </section>
                         
                        <div className="pt-12 text-center select-none pointer-events-none opacity-10">
                            <span className="text-[8px] font-black uppercase tracking-[1em] text-silver">SECURITY_CLEARANCE_ALFA_SEVEN</span>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    )
}
