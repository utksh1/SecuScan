import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE } from '../api'

interface Task {
    task_id: string
    plugin_id: string
    tool: string
    target: string
    status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
    created_at: string
    started_at?: string
    completed_at?: string
    duration_seconds?: number
}

const statusFilters = [
    { value: 'all', label: 'ALL_OPERATIONS' },
    { value: 'running', label: 'ACTIVE_EXECUTION' },
    { value: 'completed', label: 'TERMINATED_SUCCESS' },
    { value: 'failed', label: 'SYSTEM_FAILURE' },
    { value: 'cancelled', label: 'MANUAL_ABORT' }
]

export default function History() {
    const navigate = useNavigate()
    const [tasks, setTasks] = useState<Task[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('all')
    const [expandedId, setExpandedId] = useState<string | null>(null)

    useEffect(() => {
        loadTasks()
        const interval = setInterval(loadTasks, 5000)
        return () => clearInterval(interval)
    }, [filter])

    async function loadTasks() {
        try {
            const url = filter === 'all'
                ? `${API_BASE}/tasks`
                : `${API_BASE}/tasks?status=${filter}`

            const res = await fetch(url)
            const data = await res.json()
            setTasks(data.tasks || [])
        } catch (err) {
            console.error('Failed to load tasks:', err)
        } finally {
            setLoading(false)
        }
    }

    function formatDuration(seconds?: number) {
        if (!seconds) return null
        if (seconds < 60) return `${Math.round(seconds)}s`
        if (seconds < 3600) return `${Math.round(seconds / 60)}m`
        return `${Math.round(seconds / 3600)}h`
    }

    const formatDateLong = (dateStr: string) =>
        new Date(dateStr).toLocaleString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' GMT'

    return (
        <div className="min-h-screen flex flex-col scale-in-center overflow-x-hidden">
            <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10 bg-charcoal-dark/50 backdrop-blur-md sticky top-0 z-40">
                <div className="flex items-center gap-8">
                    <div className="header-decoration hidden xl:block">
                        <span className="material-symbols-outlined text-accent-silver/30 text-4xl animate-pulse font-light">history_edu</span>
                    </div>
                    <div>
                        <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">Operational Registry Ledger</h1>
                        <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">Historical Signal Repository • Execution Metadata • SYSTEMS ARCHIVE</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-12">
                   <div className="text-right border-l border-accent-silver/10 pl-8">
                        <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Total Signals</span>
                        <span className="text-xl font-light text-silver-bright font-mono">{tasks.length.toString().padStart(3, '0')}</span>
                    </div>
                    <div className="flex items-center gap-4">
                       <button 
                            className={`material-symbols-outlined text-silver/20 hover:text-silver-bright transition-all p-2 border border-accent-silver/10 rounded-full ${loading ? 'animate-spin' : ''}`}
                            onClick={loadTasks}
                        >sync</button>
                    </div>
                </div>
            </header>

            <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
                
                {/* Filtration Bar */}
                <section className="flex flex-col md:flex-row gap-12 items-center justify-between bg-charcoal-dark border border-accent-silver/10 p-8 rounded-sm shadow-xl">
                    <div className="flex flex-wrap gap-8">
                        {statusFilters.map(f => (
                            <button
                                key={f.value}
                                className={`text-[10px] font-bold uppercase tracking-[0.3em] transition-all relative pb-2 group ${
                                    filter === f.value ? 'text-silver-bright italic' : 'text-silver/20 hover:text-silver/40'
                                }`}
                                onClick={() => setFilter(f.value)}
                            >
                                <span className={filter === f.value ? '' : 'opacity-50'}>{f.label}</span>
                                {filter === f.value && (
                                    <span className="absolute bottom-0 left-0 w-full h-px bg-silver-bright shadow-[0_0_10px_white]"></span>
                                )}
                            </button>
                        ))}
                    </div>
                    <div className="flex items-center gap-4 font-mono italic">
                        <span className="text-[9px] text-silver/10 uppercase tracking-widest leading-none">Registry Isolation Protocol: ACTIVE</span>
                        <div className="w-2 h-2 rounded-full bg-rag-blue animate-pulse shadow-[0_0_8px_#3b82f6]"></div>
                    </div>
                </section>

                {/* Operations Feed */}
                <div className="space-y-4">
                    {tasks.length > 0 ? tasks.map(task => (
                        <div 
                            key={task.task_id} 
                            className={`bg-charcoal border border-accent-silver/5 hover:border-accent-silver/20 transition-all cursor-pointer relative group rounded-sm shadow-2xl overflow-hidden ${expandedId === task.task_id ? 'ring-1 ring-silver/20' : ''}`}
                            onClick={() => setExpandedId(expandedId === task.task_id ? null : task.task_id)}
                        >
                            <div className={`absolute left-0 top-0 bottom-0 w-1 transition-all group-hover:w-2 ${
                                task.status === 'completed' ? 'bg-rag-green' : 
                                task.status === 'failed' ? 'bg-rag-red' : 
                                task.status === 'running' ? 'bg-rag-amber' : 'bg-silver/10'
                            }`}></div>

                            <div className="p-8 flex flex-col md:flex-row md:items-center justify-between gap-8">
                                <div className="flex items-center gap-10 flex-1 min-w-0">
                                    <div className={`material-symbols-outlined text-3xl font-light shrink-0 ${
                                        task.status === 'completed' ? 'text-rag-green/20' : 
                                        task.status === 'failed' ? 'text-rag-red/20' : 
                                        task.status === 'running' ? 'text-rag-amber/20 animate-pulse' : 'text-silver/10'
                                    }`}>
                                        {task.status === 'completed' ? 'check_circle' : 
                                         task.status === 'failed' ? 'error' : 
                                         task.status === 'running' ? 'sensors' : 'schedule'}
                                    </div>
                                    
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-4 mb-2">
                                            <span className={`text-[9px] font-black tracking-[0.2em] uppercase px-2 py-0.5 border ${
                                                task.status === 'completed' ? 'text-rag-green border-rag-green/20' : 
                                                task.status === 'failed' ? 'text-rag-red border-rag-red/20' : 
                                                'text-silver/20 border-accent-silver/10'
                                            }`}>{task.status}</span>
                                            <span className="text-[9px] text-silver/20 uppercase tracking-[0.3em] italic font-mono">OP_SIG_{task.task_id.split('-')[0].toUpperCase()}</span>
                                        </div>
                                        <h4 className="text-lg font-serif font-light text-silver-bright uppercase tracking-tight italic line-clamp-1 group-hover:text-white transition-colors">
                                            {task.tool} <span className="text-silver/20 mx-4 uppercase not-italic font-sans text-xs font-black select-none opacity-50">BYPASSING_NODES_ON</span> {task.target}
                                        </h4>
                                        <div className="flex items-center gap-6 mt-2">
                                            <p className="text-[10px] text-silver/40 uppercase tracking-widest italic font-mono flex items-center gap-2 shrink-0">
                                                <span className="material-symbols-outlined text-[10px]">timer</span>
                                                INITIATED: {formatDateLong(task.created_at)}
                                            </p>
                                            <div className="h-px flex-1 bg-accent-silver/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-16 shrink-0">
                                    {task.duration_seconds && (
                                        <div className="text-right">
                                            <p className="text-[8px] text-silver/20 font-bold uppercase tracking-[0.3em] mb-1 italic">Temporal Shift</p>
                                            <p className="text-xl font-mono font-light text-silver-bright">{formatDuration(task.duration_seconds)}</p>
                                        </div>
                                    )}
                                    <div className="w-12 h-12 flex items-center justify-center border border-accent-silver/5 rounded-full group-hover:border-accent-silver/20 group-hover:bg-charcoal-light transition-all">
                                        <span className={`material-symbols-outlined text-silver/20 transition-all duration-700 ${expandedId === task.task_id ? 'rotate-180 text-silver-bright' : ''}`}>expand_more</span>
                                    </div>
                                </div>
                            </div>

                            {expandedId === task.task_id && (
                                <div className="p-px bg-accent-silver/10 animate-in slide-in-from-top-12 duration-700 ease-out">
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-px">
                                        <div className="p-10 bg-charcoal-dark space-y-4">
                                            <p className="text-[10px] text-silver/20 font-black uppercase tracking-[0.4em] italic flex items-center gap-2">
                                                <div className="w-1 h-3 bg-rag-blue"></div>
                                                Execution Script
                                            </p>
                                            <div className="space-y-1">
                                                <p className="text-xs font-black text-silver-bright uppercase tracking-widest font-mono italic">{task.plugin_id}</p>
                                                <p className="text-[9px] text-silver/20 uppercase tracking-tighter">VERSION_BETA_2.4.1</p>
                                            </div>
                                        </div>
                                        <div className="p-10 bg-charcoal-dark space-y-4 col-span-2">
                                            <p className="text-[10px] text-silver/20 font-black uppercase tracking-[0.4em] italic flex items-center gap-2">
                                                <div className="w-1 h-3 bg-rag-blue"></div>
                                                Temporal Synchronization
                                            </p>
                                            <div className="grid grid-cols-2 gap-12 font-mono">
                                                <div className="space-y-1">
                                                    <span className="text-[9px] text-silver/20 uppercase tracking-tighter block">Signal_Lock</span>
                                                    <span className="text-xs text-silver-bright">{task.started_at ? new Date(task.started_at).toLocaleTimeString() : 'WAITING...'}</span>
                                                </div>
                                                <div className="space-y-1">
                                                    <span className="text-[9px] text-silver/20 uppercase tracking-tighter block">Signal_Release</span>
                                                    <span className="text-xs text-silver-bright">{task.completed_at ? new Date(task.completed_at).toLocaleTimeString() : 'N/A'}</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="p-10 bg-charcoal-dark flex flex-col justify-center items-center group/btn">
                                            <button 
                                                className="relative px-12 py-4 bg-transparent border border-silver/20 text-silver-bright text-[10px] font-black uppercase tracking-[0.4em] overflow-hidden transition-all hover:bg-silver-bright hover:text-charcoal-dark italic whitespace-nowrap group-hover/btn:shadow-[0_0_30px_rgba(255,255,255,0.1)]"
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    navigate(`/task/${task.task_id}`)
                                                }}
                                            >
                                                <span className="relative z-10">Inspect_Briefing</span>
                                                <div className="absolute inset-0 bg-white/10 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700 skew-x-12"></div>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )) : (
                        <div className="p-32 bg-charcoal/30 border border-dashed border-accent-silver/10 rounded-sm text-center space-y-8 animate-pulse">
                            <span className="material-symbols-outlined text-silver/5 text-8xl font-light">inventory_2</span>
                            <div className="space-y-2">
                                <p className="text-[12px] text-silver/20 uppercase tracking-[0.8em] font-black italic">End of Signal Stream</p>
                                <p className="text-[9px] text-silver/10 uppercase tracking-[0.4em]">Historical data purge scheduled: 04:00 GMT</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Decorative End Note */}
                <div className="pt-20 border-t border-accent-silver/5 flex justify-between items-center opacity-30 select-none pointer-events-none">
                    <div className="text-[9px] text-silver/40 uppercase tracking-[0.6em] italic">SecuScan Operational Integrity Guaranteed</div>
                    <div className="flex gap-4">
                         {[1,2,3,4,5].map(i => <div key={i} className="w-4 h-0.5 bg-silver/20"></div>)}
                    </div>
                </div>
            </main>
        </div>
    )
}
