import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { API_BASE, startTask } from '../api'
import { routes, routePath } from '../routes'

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
    inputs?: Record<string, any>
    preset?: string
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
    raw_output?: string
    command_used?: string
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
                // The backend returns the result fields at the top level
                setResult(resultData)
                // Use the full output if available
                if (resultData.raw_output) {
                    setRawOutput(resultData.raw_output)
                } else if (resultData.raw_output_excerpt) {
                    setRawOutput(resultData.raw_output_excerpt)
                }
            }
        } catch (err) {
            console.error('Failed to load task:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleRescan = async () => {
        if (!task) return
        try {
            setLoading(true)
            const res = await startTask(
                task.plugin_id,
                task.inputs || {},
                true, // Assuming consent was already granted for previous task
                task.preset
            )
            navigate(routePath.task(res.task_id))
        } catch (err) {
            console.error('Rescan failed:', err)
            // Error handling UI can go here
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

    const SummaryCard = ({ label, value, subValue }: { label: string, value: string, subValue?: string }) => (
        <div className="bg-charcoal border-4 border-black p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] space-y-2">
            <span className="text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] italic">{label}</span>
            <div className="text-3xl font-black text-silver-bright italic tracking-tighter">{value}</div>
            {subValue && <div className="text-[9px] font-mono text-rag-blue font-black uppercase tracking-widest">{subValue}</div>}
        </div>
    )

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
                    {(task.status === 'completed' || task.status === 'failed') && (
                        <button
                            onClick={handleRescan}
                            className="bg-rag-blue px-6 py-4 border-4 border-black text-black text-xs font-black uppercase tracking-widest italic shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all flex items-center gap-3"
                        >
                            <span className="material-symbols-outlined text-sm">restart_alt</span>
                            RESCAN_TARGET
                        </button>
                    )}
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

            {/* Metric Overview */}
            <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <SummaryCard 
                    label="DISCOVERY_COUNT" 
                    value={(result?.structured?.total_count || findings.length).toString().padStart(2, '0')} 
                    subValue={`${result?.structured?.type?.toUpperCase() || 'FINDINGS'}_LOCALIZED`}
                />
                <SummaryCard 
                    label="MISSION_START" 
                    value={task.started_at ? parseDateSafe(task.started_at)?.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }) || '00:00' : '--:--'} 
                    subValue={task.started_at ? formatDateLong(task.started_at).split(' ')[0] : 'PENDING'}
                />
                <SummaryCard 
                    label="MISSION_FINISH" 
                    value={task.completed_at ? parseDateSafe(task.completed_at)?.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }) || '00:00' : '--:--'} 
                    subValue={task.completed_at ? formatDateLong(task.completed_at).split(' ')[0] : 'ACTIVE'}
                />
                <SummaryCard 
                    label="SCAN_DURATION" 
                    value={task.duration_seconds ? `${Math.floor(task.duration_seconds / 60)}M ${Math.floor(task.duration_seconds % 60)}S` : '00:00'} 
                    subValue="TOTAL_ELAPSED_TIME"
                />
            </section>

            {/* Results Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                <main className="lg:col-span-2 space-y-12">
                    {/* Primary Results Table */}
                    {result?.structured?.rows && result.structured.rows.length > 0 && (
                        <section className="space-y-6">
                            <div className="flex items-center gap-4">
                                <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Discovery_Results</h3>
                                <div className="h-0.5 flex-1 bg-black/10"></div>
                                <span className="text-[10px] font-black text-silver/30 uppercase italic">{result.structured.rows.length} Entries</span>
                            </div>
                            
                            <div className="border-4 border-black bg-black/40 overflow-hidden shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
                                <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
                                    <table className="w-full text-left text-[11px] font-mono border-collapse">
                                        <thead className="sticky top-0 z-20">
                                            <tr className="bg-black text-silver/40 uppercase tracking-widest font-black italic">
                                                {Object.keys(result.structured.rows[0]).map(key => (
                                                    <th key={key} className="p-4 border-r-2 border-black border-b-4">{key}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y-4 divide-black">
                                            {result.structured.rows.map((row: any, idx: number) => (
                                                <tr key={idx} className="hover:bg-white/5 transition-colors group">
                                                    {Object.values(row).map((val: any, vIdx: number) => (
                                                        <td key={vIdx} className={`p-4 border-r-2 border-black font-black uppercase tracking-tight ${vIdx === 0 ? 'text-rag-blue' : 'text-silver/70'}`}>
                                                            {val?.toString() || '-'}
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </section>
                    )}

                    {/* Findings Details */}
                    {findings.length > 0 && (
                        <section className="space-y-8">
                            <div className="flex items-center gap-4">
                                <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Tactical_Intelligence</h3>
                                <div className="h-0.5 flex-1 bg-black/10"></div>
                            </div>
                            <div className="space-y-6">
                                {findings.map((f: any, idx: number) => (
                                    <div key={idx} className="bg-charcoal border-4 border-black p-8 space-y-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative overflow-hidden group hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all">
                                        <div className="flex justify-between items-start">
                                            <div className="space-y-2">
                                                <span className="text-[8px] font-mono text-silver/30 uppercase tracking-[0.3em] italic">Finding_ID::SIG#{idx.toString().padStart(3, '0')}</span>
                                                <h4 className="text-xl font-black text-silver-bright uppercase tracking-tighter italic group-hover:text-rag-blue transition-colors">{f.title}</h4>
                                            </div>
                                            <span className={`px-3 py-1 text-[10px] font-black uppercase italic border-2 border-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] ${
                                                f.severity === 'critical' ? 'bg-rag-red text-black' :
                                                f.severity === 'high' ? 'bg-rag-amber text-black' :
                                                f.severity === 'medium' ? 'bg-rag-blue text-black' :
                                                'bg-charcoal text-silver-bright border-silver-bright/20'
                                            }`}>
                                                {f.severity}_SEVERITY
                                            </span>
                                        </div>
                                        <p className="text-xs text-silver/50 leading-loose italic border-t-2 border-black border-dashed pt-4">{f.description}</p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}
                </main>

                <aside className="space-y-12">
                    {/* Scan Parameters Dashboard */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic border-b-4 border-black pb-4 w-full">Scan_Parameters</h3>
                        </div>
                        <div className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                            {Object.entries(task.inputs || {}).map(([key, val]: [string, any]) => (
                                <div key={key} className="flex justify-between items-center gap-4 border-b border-black/20 pb-4 last:border-0 last:pb-0">
                                    <span className="text-[9px] font-black text-silver/20 uppercase tracking-[0.2em] font-mono">{key}</span>
                                    <span className={`text-[10px] font-black uppercase text-right ${val === true ? 'text-rag-green' : val === false ? 'text-rag-red' : 'text-silver-bright'}`}>
                                        {val === true ? 'ON' : val === false ? 'OFF' : val?.toString() || 'NONE'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Operational Command */}
                    {result?.command_used && (
                        <section className="space-y-6">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic border-b-4 border-black pb-4">Operational_Command</h3>
                            <div className="bg-charcoal-dark border-4 border-black p-6 font-mono text-[10px] text-rag-blue/60 break-all shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] italic">
                                <span className="text-silver/20 mr-2">$</span>
                                {result.command_used}
                            </div>
                        </section>
                    )}
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
