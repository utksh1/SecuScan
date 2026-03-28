import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { API_BASE } from '../api'
import { routePath } from '../routes'

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
    inputs?: any
    preset?: string
}

const statusFilters = [
    { value: 'all', label: 'ALL_OPERATIONS' },
    { value: 'running', label: 'ACTIVE_EXECUTION' },
    { value: 'completed', label: 'TERMINATED_SUCCESS' },
    { value: 'failed', label: 'SYSTEM_FAILURE' },
    { value: 'cancelled', label: 'MANUAL_ABORT' }
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
} as const

const itemVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 200, damping: 20 } as any
  }
} as const

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

    async function handleRescan(task: Task) {
        try {
            const res = await fetch(`${API_BASE}/start-task`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plugin_id: task.plugin_id,
                    inputs: task.inputs || {},
                    consent_granted: true,
                    preset: task.preset
                })
            })
            const data = await res.json()
            if (data.task_id) {
                navigate(routePath.task(data.task_id))
            }
        } catch (err) {
            console.error('Rescan failed:', err)
        }
    }

    function formatDuration(seconds?: number) {
        if (!seconds) return null
        if (seconds < 60) return `${Math.round(seconds)}s`
        if (seconds < 3600) return `${Math.round(seconds / 60)}m`
        return `${Math.round(seconds / 3600)}h`
    }

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            {/* Neo-Brutalist Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
                <div className="space-y-4">
                  <div className="bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    Operational_Registry_v9.0
                  </div>
                  <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
                    Scan <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Archive</span>
                  </h1>
                  <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic flex items-center gap-4">
                    Total_Registry_Keys: {tasks.length} // SYSTEM_STATUS: {loading ? 'SYNCING...' : 'SYNCED'}
                    <span className={`w-2 h-2 rounded-full ${loading ? 'bg-rag-amber animate-pulse' : 'bg-rag-green'}`}></span>
                  </p>
                </div>

                <div className="flex items-center gap-12 border-l-4 border-silver-bright/10 pl-12 hidden lg:flex">
                    <div className="text-right">
                        <span className="text-[10px] font-black text-silver/40 uppercase tracking-[0.3em] block mb-2 italic">Integrity_Check</span>
                        <span className="text-xs font-mono text-rag-green uppercase font-black">OPSEC_CLEARANCE_L5</span>
                    </div>
                </div>
            </header>

            {/* Filtration Block */}
            <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col xl:flex-row justify-between items-center gap-12">
                <div className="flex flex-wrap items-center gap-4">
                    {statusFilters.map(f => (
                        <button
                            key={f.value}
                            onClick={() => setFilter(f.value)}
                            className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 flex items-center gap-2 ${
                                filter === f.value 
                                ? 'bg-silver-bright text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] -translate-x-0.5 -translate-y-0.5' 
                                : 'bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20'
                            }`}
                        >
                            {f.label}
                            {filter === f.value && <span className="w-1 h-3 bg-black"></span>}
                        </button>
                    ))}
                </div>
                <div className="flex items-center gap-4 text-[10px] font-mono text-silver/20 uppercase italic tracking-widest">
                   Isolation_Protocol_Active // <span className="text-rag-blue">v4_stable</span>
                </div>
            </section>

            {/* Timeline Operations Feed */}
            <section className="relative">
                {/* Vertical Timeline Cable */}
                <div className="absolute left-[39px] top-0 bottom-0 w-1 bg-silver-bright/5 hidden md:block"></div>

                <AnimatePresence mode='popLayout'>
                    {tasks.length > 0 ? (
                        <motion.div 
                            variants={containerVariants}
                            initial="hidden"
                            animate="visible"
                            className="space-y-8"
                        >
                            {tasks.map((task) => (
                                <motion.div 
                                    key={task.task_id}
                                    variants={itemVariants}
                                    layout
                                    className={`relative group md:pl-20 transition-all`}
                                >
                                    {/* Timeline Node */}
                                    <div className={`absolute left-[31px] top-12 w-5 h-5 border-4 border-black z-10 hidden md:block transition-all duration-500 ${
                                        task.status === 'completed' ? 'bg-rag-green shadow-[0_0_15px_rgba(34,197,94,0.3)]' :
                                        task.status === 'failed' ? 'bg-rag-red' :
                                        task.status === 'running' ? 'bg-rag-amber animate-pulse' : 'bg-silver/10'
                                    }`}></div>

                                    <div 
                                        className={`bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] transition-all cursor-pointer relative overflow-hidden group/card ${
                                            expandedId === task.task_id ? 'border-rag-blue/40 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)]' : ''
                                        }`}
                                        onClick={() => setExpandedId(expandedId === task.task_id ? null : task.task_id)}
                                    >
                                        <div className="flex flex-col xl:flex-row justify-between gap-8">
                                            <div className="flex-1 space-y-6">
                                                <div className="flex flex-wrap items-center gap-4">
                                                    <span className={`px-2 py-0.5 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                                                        task.status === 'completed' ? 'bg-rag-green text-black' :
                                                        task.status === 'failed' ? 'bg-rag-red text-black' :
                                                        'bg-charcoal-dark text-silver-bright/50'
                                                    }`}>
                                                        {task.status}
                                                    </span>
                                                    <span className="text-[10px] font-mono text-silver/20 uppercase tracking-widest italic">
                                                        OP_ID_{task.task_id.split('-')[0].toUpperCase()}
                                                    </span>
                                                </div>

                                                <div className="space-y-2">
                                                    <h3 className="text-3xl font-black text-silver-bright uppercase tracking-tighter italic leading-none group-hover/card:text-rag-blue transition-colors">
                                                        {task.tool}
                                                    </h3>
                                                    <p className="text-xs font-mono text-silver/40 uppercase tracking-widest flex items-center gap-3">
                                                        <span className="material-symbols-outlined text-sm">target</span>
                                                        {task.target}
                                                    </p>
                                                </div>
                                            </div>

                                            <div className="flex flex-row xl:flex-col items-center xl:items-end justify-between xl:justify-center gap-8 shrink-0">
                                                <div className="text-left xl:text-right">
                                                    <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-1 italic">Historical_Execution</p>
                                                    <p className="text-xs font-mono text-silver-bright/80 uppercase">
                                                        {new Date(task.created_at).toLocaleDateString([], { timeZone: 'Asia/Kolkata' })} // {new Date(task.created_at).toLocaleTimeString([], { hour12: false, timeZone: 'Asia/Kolkata' })} IST
                                                    </p>
                                                </div>
                                                {task.duration_seconds && (
                                                    <div className="bg-charcoal-dark border-2 border-black px-4 py-2 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)]">
                                                        <p className="text-[10px] font-black font-mono text-rag-blue leading-none">{formatDuration(task.duration_seconds)?.toUpperCase()}</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Expandable Details Block */}
                                        <AnimatePresence>
                                            {expandedId === task.task_id && (
                                                <motion.div 
                                                    initial={{ height: 0, opacity: 0 }}
                                                    animate={{ height: 'auto', opacity: 1 }}
                                                    exit={{ height: 0, opacity: 0 }}
                                                    className="overflow-hidden"
                                                >
                                                    <div className="mt-12 pt-12 border-t-4 border-black grid grid-cols-1 md:grid-cols-3 gap-12 bg-charcoal-dark/20 -mx-8 -mb-8 p-8 border-dashed">
                                                        <div className="space-y-4">
                                                            <h5 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic flex items-center gap-3">
                                                                <span className="w-1.5 h-3 bg-rag-blue"></span> Signal_Metadata
                                                            </h5>
                                                            <div className="space-y-2">
                                                                <p className="text-[10px] font-mono text-silver/40">PLUGIN: <span className="text-silver-bright uppercase">{task.plugin_id}</span></p>
                                                                <p className="text-[10px] font-mono text-silver/40">SESSION: <span className="text-silver-bright uppercase">ENCRYPTED_VTX</span></p>
                                                            </div>
                                                        </div>

                                                        <div className="space-y-4">
                                                            <h5 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.3em] italic flex items-center gap-3">
                                                                <span className="w-1.5 h-3 bg-rag-amber"></span> Time_Matrix
                                                            </h5>
                                                            <div className="grid grid-cols-2 gap-4">
                                                                <div className="space-y-1">
                                                                    <span className="text-[8px] text-silver/20 uppercase font-black tracking-widest">In_Lock</span>
                                                                    <span className="text-[10px] font-mono text-silver-bright block">{task.started_at ? `${new Date(task.started_at).toLocaleTimeString([], { hour12: false, timeZone: 'Asia/Kolkata' })} IST` : 'PENDING'}</span>
                                                                </div>
                                                                <div className="space-y-1">
                                                                    <span className="text-[8px] text-silver/20 uppercase font-black tracking-widest">Release</span>
                                                                    <span className="text-[10px] font-mono text-silver-bright block">{task.completed_at ? `${new Date(task.completed_at).toLocaleTimeString([], { hour12: false, timeZone: 'Asia/Kolkata' })} IST` : 'N/A'}</span>
                                                                </div>
                                                            </div>
                                                        </div>

                                                         <div className="flex items-center justify-end gap-6">
                                                            {(task.status === 'completed' || task.status === 'failed') && (
                                                                <button 
                                                                    className="bg-rag-blue text-black px-8 py-4 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 group/btn italic"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation()
                                                                        handleRescan(task)
                                                                    }}
                                                                >
                                                                    Rescan_Signal
                                                                    <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">replay</span>
                                                                </button>
                                                            )}
                                                            <button 
                                                                className="bg-silver-bright text-black px-8 py-4 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 group/btn italic"
                                                                onClick={(e) => {
                                                                    e.stopPropagation()
                                                                    navigate(routePath.task(task.task_id))
                                                                }}
                                                            >
                                                                Open_Deep_Brief
                                                                <span className="material-symbols-outlined text-sm group-hover/btn:translate-x-1 transition-transform">arrow_right_alt</span>
                                                            </button>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </motion.div>
                            ))}
                        </motion.div>
                    ) : (
                        <div className="py-40 bg-charcoal/30 border-4 border-dashed border-silver-bright/5 text-center flex flex-col items-center gap-8">
                            <span className="material-symbols-outlined text-silver/5 text-9xl">inventory_2</span>
                            <div className="space-y-2">
                                <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">Archive Isolated</p>
                                <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">No historical signal streams available for current selection</p>
                            </div>
                        </div>
                    )}
                </AnimatePresence>
            </section>

            {/* Restricted Footer */}
            <footer className="pt-24 opacity-20 pointer-events-none select-none flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic">
                <div className="flex items-center gap-4">
                    <span className="w-8 h-8 border-4 border-silver/20 flex items-center justify-center font-serif text-lg">S</span>
                    SECUSCAN ARCHIVE INTEGRITY PROTOCOL v9.0
                </div>
                <div className="flex gap-2">
                    {[1,2,3,4,5,6,7,8,9,10,11,12].map(i => <div key={i} className="w-1.5 h-3 bg-silver/20"></div>)}
                </div>
            </footer>
        </div>
    )
}
