import React, { useState } from 'react'
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
    critical: { color: 'bg-rag-red text-black', border: 'border-rag-red', label: 'Critical' },
    high: { color: 'bg-rag-amber text-black', border: 'border-rag-amber', label: 'High' },
    medium: { color: 'bg-rag-blue text-black', border: 'border-rag-blue', label: 'Medium' },
    low: { color: 'bg-silver-bright text-black', border: 'border-silver-bright', label: 'Low' },
    info: { color: 'bg-charcoal-dark text-silver-bright', border: 'border-white', label: 'Info' }
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

    const renderTaskSummary = (task: TaskData | null, label: string, index: number) => {
        if (!task) return (
            <div className={`h-full border-4 border-dashed border-silver/20 flex flex-col items-center justify-center p-12 bg-charcoal/20 relative overflow-hidden ${index === 1 ? 'border-rag-blue/40' : 'border-rag-amber/40'}`}>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[200px] font-black italic text-silver/5 pointer-events-none select-none">
                    0{index}
                </div>
                <span className="material-symbols-outlined text-4xl text-silver/20 mb-4 font-black">pending</span>
                <p className="text-[10px] font-black uppercase tracking-[0.4em] text-silver/20 italic z-10">AWAITING_TX_LINK_0{index}</p>
            </div>
        )

        const severityCounts = task.result?.severity_counts || {}
        const hasCounts = Object.keys(severityCounts).length > 0
        const accentColor = index === 1 ? 'bg-rag-blue' : 'bg-rag-amber'

        return (
            <div className="space-y-12 h-full flex flex-col group/panel">
                <div className="p-10 bg-charcoal border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative overflow-hidden transition-all group-hover/panel:-translate-y-1">
                     <div className="absolute right-0 top-0 w-32 h-32 opacity-10 -mr-16 -mt-16 pointer-events-none transition-transform duration-700 group-hover/panel:scale-150">
                        <span className="material-symbols-outlined text-[150px] font-black text-silver-bright">layers</span>
                    </div>

                    <div className="space-y-8 relative z-10">
                        <div className="flex justify-between items-start">
                            <div className="space-y-4">
                                <span className={`px-4 py-1 text-[10px] font-black uppercase tracking-[0.3em] italic text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] inline-block ${accentColor}`}>
                                    {label}_{task.status}
                                </span>
                                <h3 className="text-4xl font-black text-silver-bright italic tracking-tighter uppercase leading-none">{task.tool}</h3>
                            </div>
                            <span className="text-[10px] font-mono text-silver/40 uppercase tracking-widest bg-charcoal border-2 border-black px-3 py-1 font-black">
                                {task.task_id.split('-')[0]}
                            </span>
                        </div>
                        
                        <div className="bg-charcoal-dark border-4 border-black p-4 space-y-2">
                            <div className="flex justify-between items-center text-[10px] font-black font-mono">
                                <span className="text-silver/40 uppercase">Target_Vector</span>
                                <span className="text-silver-bright">{task.target}</span>
                            </div>
                            <div className="flex justify-between items-center text-[10px] font-black font-mono border-t-2 border-dashed border-silver/10 pt-2">
                                <span className="text-silver/40 uppercase">Epoch_Stamp</span>
                                <span className="text-silver/80">{new Date(task.created_at).toLocaleString('en-US', { hour12: false }) + 'Z'}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {hasCounts && (
                    <div className="grid grid-cols-2 gap-6 flex-grow-0">
                        {['critical', 'high', 'medium', 'low'].map(sev => {
                            const count = severityCounts[sev as keyof typeof severityCounts] || 0
                            const config = severityConfig[sev as keyof typeof severityConfig]
                            return (
                                <div key={sev} className={`p-6 border-4 flex flex-col gap-2 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] ${count > 0 ? `${config.color} border-black` : 'bg-charcoal-dark border-black text-silver/20'}`}>
                                    <span className="text-[10px] font-black uppercase tracking-widest italic">{sev}</span>
                                    <span className="text-5xl font-black font-mono leading-none tracking-tighter">{count.toString().padStart(2, '0')}</span>
                                </div>
                            )
                        })}
                    </div>
                )}

                {task.result?.summary && task.result.summary.length > 0 && (
                    <div className="space-y-6 flex-grow">
                        <h4 className="text-[10px] font-black uppercase tracking-[0.4em] text-silver-bright italic flex items-center gap-3">
                            <div className={`w-2 h-2 ${accentColor}`}></div>
                            Diagnostic_Brief
                        </h4>
                        <div className="space-y-4">
                            {task.result.summary.map((s, i) => (
                                <div key={i} className="flex gap-4 items-start bg-charcoal border-4 border-black p-4 group">
                                    <span className={`material-symbols-outlined text-[10px] font-black mt-0.5 ${index === 1 ? 'text-rag-blue' : 'text-rag-amber'}`}>chevron_right</span>
                                    <p className="text-xs text-silver-bright font-black font-mono leading-relaxed uppercase selection:bg-white selection:text-black">{s}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
                <div className="space-y-4">
                  <div className="bg-silver-bright text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    Differential Protocol v1.4
                  </div>
                  <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
                    Node <span className="text-transparent stroke-white stroke-1" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Compare</span>
                  </h1>
                  <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic tracking-widest">
                    SYNC_RATE: {loading ? 'ACTIVE_CALCULATION' : 'STANBY_MODE'} // OPSEC_L4
                  </p>
                </div>

                <div className="flex flex-wrap gap-4">
                  <div className="w-16 h-16 bg-charcoal border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] flex items-center justify-center font-black animate-pulse">
                      <span className="material-symbols-outlined text-silver-bright">difference</span>
                  </div>
                </div>
            </header>

            <main className="max-w-[1600px] mx-auto w-full space-y-12 pt-4">
                
                {/* Comparison Selector */}
                <section className="bg-charcoal border-4 border-black p-10 shadow-[10px_10px_0px_0px_rgba(0,0,0,1)]">
                    <div className="grid grid-cols-1 md:grid-cols-7 gap-10 items-end">
                        <div className="md:col-span-3 space-y-4">
                            <label className="text-xs font-black uppercase tracking-[0.3em] text-rag-blue italic flex items-center gap-3 border-b-2 border-black pb-2">
                                <span className="material-symbols-outlined text-sm font-black">looks_one</span> Baseline_Node_ID
                            </label>
                            <input
                                type="text"
                                className="w-full bg-charcoal-dark border-4 border-black p-6 font-mono text-sm text-silver-bright uppercase focus:outline-none focus:border-rag-blue transition-all italic placeholder:text-silver/20"
                                placeholder="TX_HASH_01..."
                                value={task1Id}
                                onChange={(e) => setTask1Id(e.target.value.trim())}
                            />
                        </div>
                        <div className="md:col-span-3 space-y-4">
                           <label className="text-xs font-black uppercase tracking-[0.3em] text-rag-amber italic flex items-center gap-3 border-b-2 border-black pb-2">
                                <span className="material-symbols-outlined text-sm font-black">looks_two</span> Diff_Node_ID
                            </label>
                            <input
                                type="text"
                                className="w-full bg-charcoal-dark border-4 border-black p-6 font-mono text-sm text-silver-bright uppercase focus:outline-none focus:border-rag-amber transition-all italic placeholder:text-silver/20"
                                placeholder="TX_HASH_02..."
                                value={task2Id}
                                onChange={(e) => setTask2Id(e.target.value.trim())}
                            />
                        </div>
                        <button 
                            className={`w-full py-6 text-sm font-black uppercase tracking-[0.2em] italic transition-all relative overflow-hidden border-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] ${
                                loading || !task1Id || !task2Id 
                                ? 'bg-charcoal-dark border-black text-silver/20 cursor-not-allowed shadow-none grayscale' 
                                : 'bg-silver-bright border-black text-black hover:bg-white hover:-translate-y-1'
                            }`}
                            onClick={handleCompare} 
                            disabled={loading || !task1Id || !task2Id}
                        >
                            {loading ? 'CALCULATING...' : 'EXEC_DIFF'}
                        </button>
                    </div>
                </section>

                {/* Comparison Visualizer */}
                <section className="relative">
                    {(task1 || task2) && (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-stretch">
                            {renderTaskSummary(task1, 'Alpha', 1)}
                            
                            {/* VS Badge */}
                            <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-black text-white border-4 border-silver-bright shadow-[0_0_20px_rgba(255,255,255,0.2)] rounded-full items-center justify-center font-black italic text-2xl z-20 select-none">
                                VS
                            </div>

                            {renderTaskSummary(task2, 'Omega', 2)}
                        </div>
                    )}
                    
                    {!(task1 || task2) && (
                        <div className="flex flex-col items-center justify-center py-40 space-y-10 opacity-30">
                            <div className="w-1 px-1 h-32 bg-silver"></div>
                            <span className="material-symbols-outlined text-6xl text-silver animate-pulse font-black">hub</span>
                            <p className="text-xs font-black uppercase tracking-[1em] text-silver italic text-center leading-loose">Awaiting_Neural_Differential<br/>Input_Vector_Tension</p>
                        </div>
                    )}
                </section>
            </main>
        </div>
    )
}
