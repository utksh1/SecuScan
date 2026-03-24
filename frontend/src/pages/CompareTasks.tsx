import React, { useState, useEffect } from 'react'
import { API_BASE } from '../api'

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
}

interface TaskData {
    task_id: string
    tool: string
    target: string
    status: string
    created_at: string
    result?: TaskResult
}

const severityConfig = {
    critical: { color: 'text-rag-red border-rag-red/20', label: 'Critical' },
    high: { color: 'text-rag-amber border-rag-amber/20', label: 'High' },
    medium: { color: 'text-rag-amber-bright border-rag-amber/10', label: 'Medium' },
    low: { color: 'text-rag-blue border-rag-blue/20', label: 'Low' },
    info: { color: 'text-silver/40 border-accent-silver/10', label: 'Info' }
}

export default function CompareTasks() {
    const [task1Id, setTask1Id] = useState('')
    const [task2Id, setTask2Id] = useState('')
    const [task1, setTask1] = useState<TaskData | null>(null)
    const [task2, setTask2] = useState<TaskData | null>(null)
    const [loading, setLoading] = useState(false)

    async function loadTask(id: string): Promise<TaskData | null> {
        if (!id) return null;
        try {
            const [statusRes, resultRes] = await Promise.all([
                fetch(`${API_BASE}/tasks/${id}`),
                fetch(`${API_BASE}/tasks/${id}/result`).catch(() => null)
            ])

            if (!statusRes.ok) return null;
            const statusData = await statusRes.json()

            let result = undefined
            if (resultRes?.ok) {
                const resultData = await resultRes.json()
                result = resultData.result || null
            }

            return { ...statusData, result }
        } catch (err) {
            console.error('Failed to load task:', err)
            return null
        }
    }

    const handleCompare = async () => {
        if (!task1Id || !task2Id) return
        setLoading(true)
        const [t1, t2] = await Promise.all([
            loadTask(task1Id.trim()),
            loadTask(task2Id.trim())
        ])
        setTask1(t1)
        setTask2(t2)
        setLoading(false)
    }

    const renderTaskSummary = (task: TaskData | null, label: string) => {
        if (!task) return (
            <div className="h-full border border-dashed border-accent-silver/10 flex items-center justify-center p-12 bg-charcoal/5">
                <p className="text-[10px] font-black uppercase tracking-[0.4em] text-silver/10 italic">Awaiting_Data_Input_For_{label}</p>
            </div>
        )

        const severityCounts = task.result?.severity_counts || {}
        const hasCounts = Object.keys(severityCounts).length > 0

        return (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="p-10 bg-charcoal-light border border-accent-silver/20 executive-border relative overflow-hidden group">
                     {/* Decorative background number */}
                    <div className="absolute -right-8 -bottom-12 text-[120px] font-serif font-black text-silver/5 pointer-events-none italic select-none">
                        {label === 'Baseline' ? '01' : '02'}
                    </div>

                    <div className="space-y-6 relative z-10">
                        <div className="flex justify-between items-start">
                            <div className="space-y-1">
                                <span className="text-[9px] font-black uppercase tracking-[0.4em] text-rag-blue-bright italic">{label.toUpperCase()}_SCAN_PROFILE</span>
                                <h3 className="text-3xl font-serif font-light text-silver-bright italic tracking-tighter">{task.tool}</h3>
                            </div>
                            <span className="text-[10px] font-mono text-silver/20 uppercase tracking-widest">{task.task_id.split('-')[0]}</span>
                        </div>
                        
                        <div className="flex flex-col gap-2 font-mono italic">
                            <span className="text-[11px] text-silver/60 uppercase tracking-widest leading-none border-l-2 border-accent-silver/10 pl-4">{task.target}</span>
                            <span className="text-[9px] text-silver/20 uppercase tracking-[0.2em] pl-4 pt-1">{new Date(task.created_at).toLocaleString('en-US', { hour12: false }) + ' GMT'}</span>
                        </div>
                    </div>
                </div>

                {hasCounts && (
                    <div className="grid grid-cols-2 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm">
                        {['critical', 'high', 'medium', 'low'].map(sev => {
                            const count = severityCounts[sev as keyof typeof severityCounts] || 0
                            const config = severityConfig[sev as keyof typeof severityConfig]
                            return (
                                <div key={sev} className={`p-8 bg-charcoal flex justify-between items-center ${count > 0 ? '' : 'opacity-20 grayscale'}`}>
                                    <div className="space-y-1">
                                        <span className={`text-[9px] font-black uppercase tracking-widest italic ${config.color.split(' ')[0]}`}>{sev}</span>
                                        <span className="text-[8px] text-silver/20 uppercase tracking-tighter block font-mono">SIGNAL_COUNT</span>
                                    </div>
                                    <span className="text-4xl font-serif font-light text-silver-bright">{count.toString().padStart(2, '0')}</span>
                                </div>
                            )
                        })}
                    </div>
                )}

                {task.result?.summary && task.result.summary.length > 0 && (
                    <div className="space-y-6">
                        <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-silver/20 italic border-l-4 border-accent-silver/10 pl-4">Briefing_Highlights</h4>
                        <div className="space-y-4">
                            {task.result.summary.map((s, i) => (
                                <div key={i} className="flex gap-4 items-start group">
                                    <span className="text-[10px] text-rag-blue/40 mt-1">▶</span>
                                    <p className="text-[11px] text-silver/60 font-light leading-relaxed italic group-hover:text-silver transition-colors">{s}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="min-h-screen flex flex-col scale-in-center">
            <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10 bg-charcoal-dark/50 backdrop-blur-md sticky top-0 z-40">
                <div className="flex items-center gap-8">
                    <div className="w-12 h-12 flex items-center justify-center border border-accent-silver/20 text-silver/40 rounded-sm">
                        <span className="material-symbols-outlined text-sm">compare_arrows</span>
                    </div>
                    <div>
                        <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">Intelligence_Differential</h1>
                        <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">SIDE-BY-SIDE_ANALYTICS_ENCLAVE • VERSION_DELTA_1.0</p>
                    </div>
                </div>
            </header>

            <main className="flex-1 p-12 max-w-[1600px] mx-auto w-full space-y-12">
                
                {/* Comparison Selector */}
                <section className="bg-charcoal p-10 border border-accent-silver/10 executive-border">
                    <div className="grid grid-cols-1 md:grid-cols-7 gap-10 items-end">
                        <div className="md:col-span-3 space-y-4">
                            <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">Baseline_Operation_ID</label>
                            <input
                                type="text"
                                className="w-full bg-black/40 border border-accent-silver/10 p-5 font-mono text-xs text-silver-bright focus:outline-none focus:border-rag-blue/40 transition-all italic placeholder:text-silver/5"
                                placeholder="Alpha_Node_ID (e.g. 1234-abcd...)"
                                value={task1Id}
                                onChange={(e) => setTask1Id(e.target.value)}
                            />
                        </div>
                        <div className="md:col-span-3 space-y-4">
                            <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">Differential_Operation_ID</label>
                            <input
                                type="text"
                                className="w-full bg-black/40 border border-accent-silver/10 p-5 font-mono text-xs text-silver-bright focus:outline-none focus:border-rag-amber/40 transition-all italic placeholder:text-silver/5"
                                placeholder="Omega_Node_ID (e.g. 5678-efgh...)"
                                value={task2Id}
                                onChange={(e) => setTask2Id(e.target.value)}
                            />
                        </div>
                        <button 
                            className={`w-full py-5 text-[10px] font-black uppercase tracking-widest italic transition-all relative overflow-hidden ${
                                loading || !task1Id || !task2Id 
                                ? 'bg-charcoal border border-accent-silver/10 text-silver/10 cursor-not-allowed' 
                                : 'bg-silver-bright text-charcoal-dark hover:bg-white'
                            }`}
                            onClick={handleCompare} 
                            disabled={loading || !task1Id || !task2Id}
                        >
                            {loading ? 'CALCULATING...' : 'EXECUTE_DIFF'}
                        </button>
                    </div>
                </section>

                {/* Comparison Visualizer */}
                {(task1 || task2) && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                        {renderTaskSummary(task1, 'Baseline')}
                        {renderTaskSummary(task2, 'Comparison')}
                    </div>
                )}
                
                {!(task1 || task2) && (
                    <div className="flex flex-col items-center justify-center py-32 space-y-8 opacity-20">
                        <div className="w-1 px-1 h-32 bg-gradient-to-b from-transparent via-silver to-transparent"></div>
                        <p className="text-[10px] font-black uppercase tracking-[1em] text-silver italic">Awaiting_Neural_Differential_Inputs</p>
                    </div>
                )}
            </main>
        </div>
    )
}
