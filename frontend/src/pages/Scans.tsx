import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
    API_BASE,
    deleteTask,
    clearAllTasks,
    bulkDeleteTasks
} from '../api'

import { routePath } from '../routes'
import {
    parseDateSafe,
    formatLocaleDate,
    formatLocaleTime
} from '../utils/date'

import ConfirmationModal from '../components/ConfirmationModal'

interface Task {
    task_id: string
    plugin_id: string
    tool: string
    target: string
    status:
        | 'queued'
        | 'running'
        | 'completed'
        | 'failed'
        | 'cancelled'
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
        transition: {
            type: 'spring',
            stiffness: 200,
            damping: 20
        } as any
    }
} as const

export default function Scans() {
    const navigate = useNavigate()

    const [tasks, setTasks] = useState<Task[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('all')
    const [expandedId, setExpandedId] = useState<string | null>(null)
    const [selectedIds, setSelectedIds] = useState<string[]>([])

    const [confirmModal, setConfirmModal] = useState<{
        open: boolean
        type: 'single' | 'bulk' | 'purge' | null
        task?: Task
    }>({
        open: false,
        type: null
    })

    useEffect(() => {
        loadTasks()

        const interval = setInterval(loadTasks, 5000)

        return () => clearInterval(interval)
    }, [filter])

    async function loadTasks() {
        try {
            const url =
                filter === 'all'
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
            const res = await fetch(`${API_BASE}/task/start`, {
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

    function requestTaskDelete(task: Task) {
        setConfirmModal({
            open: true,
            type: 'single',
            task
        })
    }

    async function confirmTaskDelete(taskId: string) {
        try {
            await deleteTask(taskId)

            setTasks(prev =>
                prev.filter(t => t.task_id !== taskId)
            )

            if (expandedId === taskId) {
                setExpandedId(null)
            }
        } catch (err) {
            console.error('Failed to delete task:', err)

            alert(
                'Failed to delete task. It might still be running.'
            )
        }
    }

    function requestClearAll() {
        setConfirmModal({
            open: true,
            type: 'purge'
        })
    }

    async function confirmClearAll() {
        try {
            await clearAllTasks()

            setTasks([])
            setSelectedIds([])
            setExpandedId(null)
        } catch (err) {
            console.error('Failed to clear history:', err)

            alert(
                'Failed to clear history. Ensure no tasks are currently running.'
            )
        }
    }

    function requestBulkDelete() {
        if (selectedIds.length === 0) return

        setConfirmModal({
            open: true,
            type: 'bulk'
        })
    }

    async function confirmBulkDelete() {
        try {
            await bulkDeleteTasks(selectedIds)

            setTasks(prev =>
                prev.filter(
                    t => !selectedIds.includes(t.task_id)
                )
            )

            setSelectedIds([])
        } catch (err) {
            console.error('Bulk delete failed:', err)

            alert(
                'Failed to delete some tasks. Ensure they are not currently running.'
            )
        }
    }

    function toggleSelection(
        taskId: string,
        e: React.MouseEvent
    ) {
        e.stopPropagation()

        setSelectedIds(prev =>
            prev.includes(taskId)
                ? prev.filter(id => id !== taskId)
                : [...prev, taskId]
        )
    }

    function toggleSelectAll() {
        if (selectedIds.length === tasks.length) {
            setSelectedIds([])
        } else {
            setSelectedIds(tasks.map(t => t.task_id))
        }
    }

    function formatDuration(seconds?: number) {
        if (!seconds) return null

        if (seconds < 60) {
            return `${Math.round(seconds)}s`
        }

        if (seconds < 3600) {
            return `${Math.round(seconds / 60)}m`
        }

        return `${Math.round(seconds / 3600)}h`
    }

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            {/* Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
                <div className="space-y-4">
                    <div className="bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        Operational_Registry_v10.1
                    </div>

                    <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
                        Operational{' '}
                        <span
                            className="text-transparent stroke-white"
                            style={{
                                WebkitTextStroke:
                                    '1px var(--accent-silver-bright)'
                            }}
                        >
                            Registry
                        </span>
                    </h1>

                    <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic flex items-center gap-4">
                        Total_Registry_Keys: {tasks.length} //
                        SYSTEM_STATUS:{' '}
                        {loading ? 'SYNCING...' : 'SYNCED'}

                        <span
                            className={`w-2 h-2 rounded-full ${
                                loading
                                    ? 'bg-rag-amber animate-pulse'
                                    : 'bg-rag-green'
                            }`}
                        ></span>
                    </p>
                </div>
            </header>

            {/* Filters */}
            <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col xl:flex-row justify-between items-center gap-12">
                <div className="flex flex-wrap items-center gap-4">
                    <button
                        onClick={toggleSelectAll}
                        className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 flex items-center gap-3 ${
                            selectedIds.length === tasks.length &&
                            tasks.length > 0
                                ? 'bg-rag-blue text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                                : 'bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20'
                        }`}
                    >
                        <span className="material-symbols-outlined text-sm">
                            {selectedIds.length === tasks.length &&
                            tasks.length > 0
                                ? 'check_box'
                                : 'check_box_outline_blank'}
                        </span>

                        Select_All
                    </button>

                    {statusFilters.map(f => (
                        <button
                            key={f.value}
                            onClick={() => setFilter(f.value)}
                            className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 ${
                                filter === f.value
                                    ? 'bg-silver-bright text-black border-black'
                                    : 'bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20'
                            }`}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-6">
                    {tasks.length > 0 && (
                        <button
                            onClick={requestClearAll}
                            className="px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 bg-rag-red/10 text-rag-red border-rag-red/20 hover:bg-rag-red hover:text-black hover:border-black flex items-center gap-2 italic"
                        >
                            Purge_All_Records

                            <span className="material-symbols-outlined text-sm">
                                delete_forever
                            </span>
                        </button>
                    )}
                </div>
            </section>

            {/* Tasks */}
            <section className="space-y-8">
                <AnimatePresence mode="popLayout">
                    {tasks.length > 0 ? (
                        tasks.map(task => {
                            const createDate = parseDateSafe(
                                task.created_at
                            )

                            return (
                                <motion.div
                                    key={task.task_id}
                                    variants={itemVariants}
                                    initial="hidden"
                                    animate="visible"
                                    exit="hidden"
                                    layout
                                    className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]"
                                >
                                    <div className="flex flex-col xl:flex-row justify-between gap-8">
                                        <div className="space-y-4">
                                            <div className="flex items-center gap-4">
                                                <button
                                                    onClick={e =>
                                                        toggleSelection(
                                                            task.task_id,
                                                            e
                                                        )
                                                    }
                                                    className="w-10 h-10 border-4 border-black flex items-center justify-center"
                                                >
                                                    <span className="material-symbols-outlined text-base">
                                                        {selectedIds.includes(
                                                            task.task_id
                                                        )
                                                            ? 'check'
                                                            : 'add'}
                                                    </span>
                                                </button>

                                                <span className="text-[10px] font-mono text-silver/30 uppercase">
                                                    {
                                                        task.status
                                                    }
                                                </span>
                                            </div>

                                            <div>
                                                <h3 className="text-3xl font-black uppercase italic">
                                                    {task.tool}
                                                </h3>

                                                <p className="text-xs font-mono text-silver/40 uppercase">
                                                    {task.target}
                                                </p>
                                            </div>

                                            <p className="text-xs font-mono text-silver/50">
                                                {formatLocaleDate(
                                                    createDate
                                                )}{' '}
                                                //{' '}
                                                {formatLocaleTime(
                                                    createDate
                                                )}
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-4">
                                            {(task.status ===
                                                'completed' ||
                                                task.status ===
                                                    'failed' ||
                                                task.status ===
                                                    'cancelled') && (
                                                <button
                                                    onClick={() =>
                                                        requestTaskDelete(
                                                            task
                                                        )
                                                    }
                                                    className="bg-rag-red text-black px-6 py-3 text-[10px] font-black uppercase tracking-widest"
                                                >
                                                    Delete_Record
                                                </button>
                                            )}

                                            {(task.status ===
                                                'completed' ||
                                                task.status ===
                                                    'failed') && (
                                                <button
                                                    onClick={() =>
                                                        handleRescan(
                                                            task
                                                        )
                                                    }
                                                    className="bg-rag-blue text-black px-6 py-3 text-[10px] font-black uppercase tracking-widest"
                                                >
                                                    Rescan
                                                </button>
                                            )}

                                            <button
                                                onClick={() =>
                                                    navigate(
                                                        routePath.task(
                                                            task.task_id
                                                        )
                                                    )
                                                }
                                                className="bg-silver-bright text-black px-6 py-3 text-[10px] font-black uppercase tracking-widest"
                                            >
                                                Open
                                            </button>
                                        </div>
                                    </div>
                                </motion.div>
                            )
                        })
                    ) : (
                        <div className="py-40 bg-charcoal/30 border-4 border-dashed border-silver-bright/5 text-center">
                            <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">
                                Archive Isolated
                            </p>
                        </div>
                    )}
                </AnimatePresence>
            </section>

            {/* Bulk Action Bar */}
            <AnimatePresence>
                {selectedIds.length > 0 && (
                    <motion.div
                        initial={{ y: 100, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        exit={{ y: 100, opacity: 0 }}
                        className="fixed bottom-12 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-6"
                    >
                        <div className="bg-black border-4 border-rag-blue p-6 shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] flex items-center justify-between gap-8">
                            <div className="flex items-center gap-6">
                                <div className="bg-rag-blue text-black px-4 py-2 text-xl font-black">
                                    {selectedIds.length}
                                </div>

                                <div>
                                    <p className="text-[10px] font-black text-rag-blue uppercase tracking-widest italic">
                                        Records Selected
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4">
                                <button
                                    onClick={() =>
                                        setSelectedIds([])
                                    }
                                    className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-silver/40"
                                >
                                    Cancel
                                </button>

                                <button
                                    onClick={requestBulkDelete}
                                    className="bg-rag-red text-black px-8 py-3 text-[10px] font-black uppercase tracking-widest"
                                >
                                    Delete_Selected
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Confirmation Modal */}
            <ConfirmationModal
                open={confirmModal.open}
                title={
                    confirmModal.type === 'purge'
                        ? 'Purge All Records'
                        : confirmModal.type === 'bulk'
                        ? 'Delete Selected Records'
                        : 'Delete Scan Record'
                }
                description={
                    confirmModal.type === 'purge'
                        ? 'This action will permanently remove all scan history, findings, assets, and reports. This operation cannot be reversed.'
                        : confirmModal.type === 'bulk'
                        ? `Are you sure you want to delete ${selectedIds.length} selected scan records?`
                        : `Are you sure you want to delete the scan record for "${confirmModal.task?.tool}" targeting "${confirmModal.task?.target}"? Associated findings and reports will also be removed.`
                }
                confirmLabel={
                    confirmModal.type === 'purge'
                        ? 'Purge Everything'
                        : 'Delete'
                }
                danger
                onCancel={() =>
                    setConfirmModal({
                        open: false,
                        type: null
                    })
                }
                onConfirm={async () => {
                    if (
                        confirmModal.type === 'single' &&
                        confirmModal.task
                    ) {
                        await confirmTaskDelete(
                            confirmModal.task.task_id
                        )
                    }

                    if (confirmModal.type === 'bulk') {
                        await confirmBulkDelete()
                    }

                    if (confirmModal.type === 'purge') {
                        await confirmClearAll()
                    }

                    setConfirmModal({
                        open: false,
                        type: null
                    })
                }}
            />
        </div>
    )
}