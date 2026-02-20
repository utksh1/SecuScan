import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { API_BASE } from '../api'
import { routes } from '../routes'

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

function parseDateSafe(rawValue?: string): Date | null {
    if (!rawValue) return null
    const raw = rawValue.trim()
    if (!raw) return null
    if (raw.toLowerCase() === 'now') return new Date()

    const sqliteAsIso = raw.includes('T') ? raw : raw.replace(' ', 'T')
    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(sqliteAsIso)
    const candidates = hasTimezone ? [sqliteAsIso, raw] : [`${sqliteAsIso}Z`, sqliteAsIso, raw]

    for (const candidate of candidates) {
        const d = new Date(candidate)
        if (!Number.isNaN(d.getTime())) return d
    }
    return null
}

function formatToolLabel(tool?: string, pluginId?: string) {
    const normalized = (tool || '').trim()
    if (!normalized || normalized.toLowerCase() === 'history') {
        return (pluginId || 'scan').replace(/[-_]/g, ' ').toUpperCase()
    }
    return normalized.toUpperCase()
}

const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: { staggerChildren: 0.05 }
    }
}

const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
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
                console.error("Status stream error", err)
            }
        })

        es.addEventListener('output', (e) => {
            try {
                const data = JSON.parse(e.data)
                setRawOutput(prev => prev + data.chunk)
            } catch (err) {
                console.error("Output stream error", err)
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
                fetch(`${API_BASE}/task/${taskId}/status`),
                fetch(`${API_BASE}/task/${taskId}/result`).catch(() => null)
            ])

            if (!statusRes.ok) {
                throw new Error(`Failed to load task status (${statusRes.status})`)
            }

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
            <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-12">
                <div className="space-y-4 text-center">
                    <div className="w-20 h-20 border-8 border-silver-bright/10 border-t-rag-blue animate-spin mx-auto shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"></div>
                    <p className="text-xs font-black text-silver-bright uppercase tracking-[0.5em] italic">Decrypting_Briefing...</p>
                </div>
            </div>
        )
    }

    const findings = result?.structured?.findings || []
    const formatDateLong = (dateStr: string) => {
        const parsed = parseDateSafe(dateStr)
        if (!parsed) return 'UNKNOWN_DATE'
        return `${parsed.toLocaleString('en-US', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: 'Asia/Kolkata',
        })} IST`
    }
    const toolLabel = formatToolLabel(task.tool, task.plugin_id)

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            {/* Neo-Brutalist Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
                <div className="flex items-center gap-8">
                    <button 
                        onClick={() => navigate(routes.history)}
                        className="bg-charcoal border-4 border-black p-4 text-silver-bright shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
                    >
                        <span className="material-symbols-outlined">arrow_back</span>
                    </button>
                    <div className="space-y-4">
                      <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
                        Mission_Dossier_SIG#{taskId?.split('-')[0].toUpperCase()}
                      </div>
                      <h1 className="text-5xl md:text-7xl text-silver-bright uppercase tracking-tighter leading-none italic font-black whitespace-nowrap">
                        Intel <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Briefing</span>
                      </h1>
                    </div>
                </div>

                <div className="flex gap-4">
                    {task.status === 'completed' && (
                        <>
                            <button 
                                onClick={() => window.open(`${API_BASE}/task/${taskId}/report/csv`)}
                                className="bg-charcoal px-6 py-4 border-4 border-black text-xs font-black uppercase tracking-widest italic shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all flex items-center gap-3"
                            >
                                <span className="material-symbols-outlined text-sm">download</span>
                                CSV_EXPORT
                            </button>
                            <button 
                                onClick={() => window.open(`${API_BASE}/task/${taskId}/report/pdf`)}
                                className="bg-silver-bright px-6 py-4 border-4 border-black text-black text-xs font-black uppercase tracking-widest italic shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all flex items-center gap-3"
                            >
                                <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
                                PDF_REPORT
                            </button>
                        </>
                    )}
                </div>
            </header>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-12">
                {/* Core Result Section */}
                <main className="xl:col-span-3 space-y-12">
                    {/* Target Detail Block */}
                    <section className="bg-charcoal border-4 border-black p-10 shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                            <span className="text-7xl font-black italic select-none uppercase font-mono">{toolLabel}</span>
                        </div>
                        <div className="flex flex-col md:flex-row justify-between gap-10 relative z-10">
                            <div className="space-y-6">
                                <div className="space-y-2">
                                    <p className="text-[10px] font-black uppercase tracking-[0.4em] text-silver/20 italic">SUBJECT_ENCLAVE_NODE</p>
                                    <h2 className="text-4xl md:text-6xl font-black text-silver-bright uppercase tracking-tighter italic font-mono group-hover:text-rag-blue transition-colors">
                                        {task.target}
                                    </h2>
                                </div>
                                <div className="flex flex-wrap gap-8 text-[10px] font-black uppercase tracking-[0.2em] font-mono italic text-silver/40">
                                    <div className="flex items-center gap-2">
                                        <span className="material-symbols-outlined text-xs text-rag-blue">terminal</span>
                                        TOOL::{toolLabel}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="material-symbols-outlined text-xs text-rag-blue">history</span>
                                        INIT::{formatDateLong(task.created_at)}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="material-symbols-outlined text-xs text-rag-blue">fingerprint</span>
                                        PLUGIN::{task.plugin_id || 'N/A'}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="material-symbols-outlined text-xs text-rag-blue">badge</span>
                                        TASK::{task.task_id?.slice(0, 8) || 'UNKNOWN'}
                                    </div>
                                    {task.duration_seconds && (
                                        <div className="flex items-center gap-2">
                                            <span className="material-symbols-outlined text-xs text-rag-blue">timer</span>
                                            TIME::{Math.round(task.duration_seconds)}S
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className="shrink-0 flex items-center">
                                <div className={`px-8 py-4 border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] text-xs font-black uppercase tracking-[0.4em] italic ${
                                    task.status === 'completed' ? 'bg-rag-green text-black' : 
                                    task.status === 'failed' ? 'bg-rag-red text-black' : 'bg-rag-amber text-black animate-pulse'
                                }`}>
                                    {task.status}
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Findings Ledger */}
                    {findings.length > 0 && (
                        <section className="space-y-8">
                            <div className="flex items-center gap-4">
                                <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Tactical_Findings</h3>
                                <div className="h-0.5 flex-1 bg-black/10"></div>
                                <span className="text-[10px] font-mono text-silver/20 uppercase font-black">{findings.length} ANOMALIES</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {findings.map((f, idx) => (
                                    <div key={idx} className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 transition-all relative overflow-hidden group">
                                        <div className="flex justify-between items-start mb-6">
                                            <span className={`px-2 py-0.5 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                                                f.severity === 'critical' ? 'bg-rag-red text-black' :
                                                f.severity === 'high' ? 'bg-rag-amber text-black' : 'bg-rag-blue text-black'
                                            }`}>
                                                {f.severity}_SEVERITY
                                            </span>
                                            <span className="text-[10px] font-mono text-silver/10 select-none font-black italic">ENTRY_0{idx + 1}</span>
                                        </div>
                                        <h4 className="text-xl font-black text-silver-bright uppercase tracking-tight italic mb-4 font-mono group-hover:text-rag-red transition-colors">
                                            {f.title}
                                        </h4>
                                        {f.description && (
                                            <p className="text-[11px] font-mono text-silver/40 uppercase tracking-widest leading-relaxed italic border-t-2 border-black border-dashed pt-4">
                                                {f.description}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Raw Stream Terminal */}
                    <section className="space-y-6">
                        <div className="flex justify-between items-center bg-black border-4 border-black p-4 text-silver-bright shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                            <div className="flex items-center gap-4">
                                <span className="material-symbols-outlined text-sm text-rag-green">terminal</span>
                                <h3 className="text-[10px] font-black uppercase tracking-[0.4em] italic leading-none">TTY_DAEMON_PIPE_ACTIVE</h3>
                            </div>
                            <button 
                                onClick={() => setShowRawOutput(!showRawOutput)}
                                className="text-[8px] font-black uppercase text-silver/40 hover:text-white transition-colors"
                            >
                                {showRawOutput ? '[ DISCONNECT ]' : '[ ATTACH ]'}
                            </button>
                        </div>
                        {showRawOutput && (
                            <div className="bg-black border-4 border-black p-10 font-mono text-[12px] leading-loose shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] relative group overflow-hidden h-[600px]">
                                {/* Minimal decorative grid */}
                                <div className="absolute inset-x-0 h-4 top-0 bg-gradient-to-b from-rag-blue/5 to-transparent pointer-events-none"></div>
                                <pre className="text-silver/50 whitespace-pre-wrap selection:bg-rag-blue/30 selection:text-white h-full overflow-y-auto scrollbar-thin scrollbar-thumb-rag-blue/20">
                                    {rawOutput || 'Awaiting transmission data...'}
                                    {task.status === 'running' && <span className="inline-block w-2.5 h-5 bg-rag-blue animate-pulse ml-2 align-middle shadow-[0_0_15px_#3b82f6]"></span>}
                                </pre>
                            </div>
                        )}
                    </section>
                </main>

                {/* Sidebar Metrics */}
                <aside className="space-y-12">
                    {/* Severity Grid */}
                    <section className="space-y-6">
                        <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic border-b-4 border-black pb-4">Threat_Distribution</h3>
                        <div className="grid grid-cols-1 gap-4">
                            {['critical', 'high', 'medium', 'low'].map(sev => {
                                const count = result?.severity_counts?.[sev] || 0
                                const isActive = count > 0
                                return (
                                    <div key={sev} className={`p-6 border-4 border-black flex justify-between items-center transition-all ${
                                        isActive
                                        ? (sev === 'critical' ? 'bg-rag-red text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' : 
                                           sev === 'high' ? 'bg-rag-amber text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' : 
                                           'bg-rag-blue text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]')
                                        : 'bg-charcoal border-accent-silver/20 border-dashed'
                                    }`}>
                                        <div className="space-y-1">
                                            <span className={`text-[10px] font-black uppercase tracking-[0.3em] italic ${isActive ? 'text-black' : 'text-silver-bright'}`}>{sev}</span>
                                            <p className={`text-[8px] font-mono uppercase tracking-widest ${isActive ? 'text-black/70' : 'text-silver/75'}`}>STRIKE_PROB</p>
                                        </div>
                                        <span className={`text-4xl font-black italic ${isActive ? 'text-black' : 'text-silver-bright'}`}>{count.toString().padStart(2, '0')}</span>
                                    </div>
                                )
                            })}
                        </div>
                    </section>

                    {/* Briefing Text */}
                    {result?.summary && result.summary.length > 0 && (
                        <section className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] space-y-6">
                            <h3 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.4em] italic border-b-2 border-black border-dashed pb-4">Briefing_Executive</h3>
                            <div className="space-y-6">
                                {result.summary.map((s, idx) => (
                                    <div key={idx} className="flex gap-4 group">
                                        <span className="text-[10px] font-mono text-rag-blue font-black group-hover:text-rag-red transition-colors">[{idx + 1}]</span>
                                        <p className="text-[11px] font-black text-silver/60 uppercase tracking-widest leading-loose italic group-hover:text-silver-bright transition-colors">
                                            {s}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Diagnostic Monitor */}
                    <div className="bg-charcoal-dark border-4 border-black p-8 space-y-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                         <div className="flex items-center gap-3">
                            <div className="w-2 h-2 bg-rag-green animate-pulse rounded-full"></div>
                            <h3 className="text-[9px] font-black text-silver-bright uppercase tracking-[0.3em] italic">Telemetry_Stream</h3>
                         </div>
                         <div className="space-y-4">
                             <div className="flex justify-between items-center text-[9px] font-black text-silver/20 uppercase tracking-[0.2em] font-mono italic">
                                <span>MEM_SATURATION</span>
                                <span className="text-rag-blue">0.42GB</span>
                             </div>
                             <div className="h-1 bg-black w-full">
                                <div className="h-full bg-rag-blue w-[35%]"></div>
                             </div>
                             <div className="flex justify-between items-center text-[9px] font-black text-silver/20 uppercase tracking-[0.2em] font-mono italic">
                                <span>NET_LATENCY</span>
                                <span className="text-rag-green">12MS</span>
                             </div>
                             <div className="h-1 bg-black w-full">
                                <div className="h-full bg-rag-green w-[15%]"></div>
                             </div>
                         </div>
                    </div>
                </aside>
            </div>

            {/* Tactical Footer */}
            <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
                <div className="flex items-center gap-6">
                    <div className="w-12 h-1 bg-silver/20"></div>
                    CLASSIFIED_EXECUTIVE_SUMMARY // CORE_DAEMON_LOG_ID::{taskId?.split('-')[0].toUpperCase()}
                </div>
                <div className="flex gap-4">
                    {[1,2,3,4].map(i => <div key={i} className="w-20 h-1 bg-silver/20"></div>)}
                </div>
            </footer>
        </div>
    )
}
