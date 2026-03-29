import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { API_BASE, getTaskResult, getTaskStatus, startTask } from '../api'
import { routes, routePath } from '../routes'
import { parseDateSafe, formatDateLong, formatLocaleTime } from '../utils/date'
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    Tooltip as RechartsTooltip,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid
} from 'recharts'

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
    error_message?: string
    inputs?: Record<string, any>
    preset?: string
}

interface Finding {
    id?: string
    title: string
    category: string
    severity: string
    target: string
    description: string
    remediation?: string
    cvss?: number
    cve?: string
    proof?: string
    discovered_at?: string
    metadata?: Record<string, any>
}

interface TaskResult {
    task_id: string
    plugin_id: string
    tool: string
    target: string
    timestamp: string
    duration_seconds?: number
    status: string
    summary?: string[]
    severity_counts?: Record<string, number>
    findings?: Finding[]
    structured?: {
        rows?: Array<Record<string, any>>
        [key: string]: any
    }
    raw_output_path?: string
    raw_output?: string
    command_used?: string
    errors?: Array<{ message: string }>
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
    const [error, setError] = useState<string | null>(null)
    const [activeTab, setActiveTab] = useState<'summary' | 'results' | 'parameters' | 'raw'>('summary')
    const [expandedFindingRows, setExpandedFindingRows] = useState<Record<number, boolean>>({})
    const [expandedDiscoveryRows, setExpandedDiscoveryRows] = useState<Record<number, boolean>>({})
    const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
    const [rawSearch, setRawSearch] = useState('')
    const [wrapRawOutput, setWrapRawOutput] = useState(true)
    const [copiedRawOutput, setCopiedRawOutput] = useState(false)

    const FindingDrawer = ({ finding, onClose }: { finding: Finding, onClose: () => void }) => {
        if (!finding) return null
        const severityColor = severityTone(finding.severity).split(' ')[0]
        
        return (
            <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed top-0 right-0 h-full w-[100%] md:w-[600px] bg-charcoal-dark border-l border-white/10 shadow-[-10px_0px_30px_rgba(0,0,0,0.5)] z-[100] overflow-y-auto"
            >
                <div className="sticky top-0 bg-charcoal-dark/95 backdrop-blur border-b border-white/10 px-8 py-6 flex items-center justify-between z-10">
                    <div className="space-y-1">
                        <span className={`text-[10px] font-black uppercase tracking-[0.2em] px-2 py-0.5 border ${severityTone(finding.severity)}`}>
                            {finding.severity}
                        </span>
                        <h2 className="text-xl font-black text-silver-bright italic uppercase tracking-tight">{finding.title}</h2>
                    </div>
                    <button 
                        onClick={onClose}
                        className="p-2 hover:bg-white/5 transition-colors text-silver/40 hover:text-silver-bright"
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                <div className="p-8 space-y-10">
                    <div className="space-y-4">
                        <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">Description</h3>
                        <p className="text-sm leading-8 text-silver/85 whitespace-pre-wrap">{finding.description}</p>
                    </div>

                    {finding.proof && (
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">Evidence / Proof</h3>
                            <pre className="bg-black/40 border border-white/5 p-5 text-[11px] font-mono text-rag-blue/90 whitespace-pre-wrap break-words leading-6">
                                {finding.proof}
                            </pre>
                        </div>
                    )}

                    {finding.remediation && (
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">Remediation Guidance</h3>
                            <div className="bg-rag-green/5 border border-rag-green/20 p-5">
                                <p className="text-sm leading-8 text-rag-green/90">{finding.remediation}</p>
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">Category</h3>
                            <p className="text-sm font-black text-silver-bright uppercase italic">{finding.category}</p>
                        </div>
                        {finding.cvss && (
                            <div className="space-y-4">
                                <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">CVSS Score</h3>
                                <p className={`text-sm font-black italic ${finding.cvss >= 7 ? 'text-rag-red' : finding.cvss >= 4 ? 'text-rag-amber' : 'text-rag-blue'}`}>
                                    {finding.cvss.toFixed(1)}
                                </p>
                            </div>
                        )}
                        {finding.cve && (
                            <div className="space-y-4">
                                <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">CVE Identifiers</h3>
                                <p className="text-sm font-mono text-rag-blue/80 underline cursor-pointer">{finding.cve}</p>
                            </div>
                        )}
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.36em] pb-2 border-b border-white/5">Detected At</h3>
                            <p className="text-xs text-silver/60 font-mono italic">
                                {finding.discovered_at ? formatDateLong(finding.discovered_at) : formatDateLong(task?.completed_at || '')}
                            </p>
                        </div>
                    </div>

                    {Object.keys(finding.metadata || {}).length > 0 && (
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em] pb-2 border-b border-white/5">Technical Attributes</h3>
                            <div className="grid grid-cols-1 gap-3">
                                {Object.entries(finding.metadata || {}).map(([key, val]) => (
                                    <div key={key} className="flex justify-between items-start text-[11px] border-b border-white/[0.03] pb-2">
                                        <span className="text-silver/40 uppercase tracking-wider">{formatKeyLabel(key)}</span>
                                        <span className="text-silver/70 font-mono break-all text-right max-w-[240px]">{formatValue(val)}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </motion.div>
        )
    }

    useEffect(() => {
        loadTask()

        const es = new EventSource(`${API_BASE}/task/${taskId}/stream`)

        es.addEventListener('status', (e) => {
            try {
                const data = JSON.parse(e.data)
                setTask((prev: Task | null) => prev ? { ...prev, status: data.status } : null)
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
            setError(null)
            const [statusData, resultData] = await Promise.all([
                getTaskStatus(taskId!) as Promise<Task>,
                getTaskResult(taskId!).catch(() => null) as Promise<TaskResult | null>
            ])
            setTask(statusData)

            if (resultData) {
                // The backend returns the result fields at the top level
                setResult(resultData)
                // Use the full output if available
                if (resultData.raw_output) {
                    setRawOutput(resultData.raw_output)
                }
            }
        } catch (err) {
            console.error('Failed to load task:', err)
            setError(err instanceof Error ? err.message : 'Unable to load task details')
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
        if (error) {
            return (
                <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-12">
                    <div className="max-w-xl w-full bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-4 text-center">
                        <p className="text-xs font-black text-rag-red uppercase tracking-[0.4em] italic">Task_Load_Failed</p>
                        <p className="text-sm text-silver-bright font-mono break-words">{error}</p>
                        <button
                            onClick={() => {
                                setLoading(true)
                                loadTask()
                            }}
                            className="bg-rag-blue px-6 py-3 border-4 border-black text-black text-xs font-black uppercase tracking-widest italic shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] active:translate-x-1 active:translate-y-1 active:shadow-none transition-all"
                        >
                            Retry_Load
                        </button>
                    </div>
                </div>
            )
        }

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
    const tableRows = result?.structured?.rows || []
    const summaryItems = result?.summary || []
    const resultEntryCount = tableRows.length || findings.length
    const toolLabel = formatToolLabel(task.tool, task.plugin_id)
    const startedTime = task.started_at
        ? formatLocaleTime(task.started_at, { hour: '2-digit', minute: '2-digit' })
        : '--:--'
    const completedTime = task.completed_at
        ? formatLocaleTime(task.completed_at, { hour: '2-digit', minute: '2-digit' })
        : '--:--'
    const isTerminal = ['completed', 'failed', 'cancelled'].includes(task.status)
    const durationLabel = isTerminal
        ? (task.duration_seconds 
            ? `${Math.floor(task.duration_seconds / 60)}M ${Math.floor(task.duration_seconds % 60)}S`
            : (task.status === 'completed' ? '0M 0S' : 'TERMINATED'))
        : 'ACTIVE'
    const severityCounts = findings.reduce((acc: Record<string, number>, finding: any) => {
        const key = (finding.severity || 'info').toLowerCase()
        acc[key] = (acc[key] || 0) + 1
        return acc
    }, {})

    const formatKeyLabel = (value: string) =>
        value
            .replace(/_/g, ' ')
            .replace(/\b\w/g, char => char.toUpperCase())

    const formatValue = (value: unknown) => {
        if (value === true) return 'ON'
        if (value === false) return 'OFF'
        if (value === null || value === undefined || value === '') return 'NONE'
        if (Array.isArray(value)) return value.join(', ')
        if (typeof value === 'object') return JSON.stringify(value)
        return String(value)
    }

    const stripAnsi = (value: unknown) =>
        String(value ?? '')
            .replace(/\u001b\[[0-9;]*m/g, '')
            .replace(/\[[0-9;]*m/g, '')
            .trim()
    const rawLines = (rawOutput || result?.raw_output || '').split('\n')
    const filteredRawLines = rawSearch
        ? rawLines.filter((line: string) => line.toLowerCase().includes(rawSearch.toLowerCase()))
        : rawLines

    const findInputValue = (...keys: string[]) => {
        for (const key of keys) {
            const value = task.inputs?.[key]
            if (value !== undefined && value !== null && value !== '') {
                return formatValue(value)
            }
        }
        return null
    }

    const statusTone = task.status === 'completed'
        ? 'bg-rag-green/15 text-rag-green border-rag-green/30'
        : task.status === 'failed'
            ? 'bg-rag-red/15 text-rag-red border-rag-red/30'
            : task.status === 'cancelled'
                ? 'bg-silver/10 text-silver/70 border-silver/15'
                : 'bg-rag-amber/15 text-rag-amber border-rag-amber/30'

    const severityTone = (severity?: string) => {
        const normalized = (severity || '').toLowerCase()
        if (normalized === 'critical') return 'text-rag-red border-rag-red/30 bg-rag-red/10'
        if (normalized === 'high') return 'text-rag-amber border-rag-amber/30 bg-rag-amber/10'
        if (normalized === 'medium') return 'text-rag-blue border-rag-blue/30 bg-rag-blue/10'
        if (normalized === 'low') return 'text-rag-green border-rag-green/30 bg-rag-green/10'
        return 'text-silver/65 border-white/10 bg-white/[0.02]'
    }
    const primaryDetail = findInputValue('source_ip', 'ip', 'host', 'hostname') || task.target
    const primaryDetailLabel = task.inputs?.source_ip || task.inputs?.ip ? 'Source IP' : 'Target'
    const secondaryDetail = findInputValue('scan_type', 'preset', 'mode', 'safe_mode', 'passive_detection') || toolLabel
    const secondaryDetailLabel = task.inputs?.scan_type
        ? 'Scan Type'
        : task.inputs?.preset
            ? 'Preset'
            : task.inputs?.mode
                ? 'Mode'
                : task.inputs?.safe_mode !== undefined
                    ? 'Safe Mode'
                    : task.inputs?.passive_detection !== undefined
                        ? 'Passive Detection'
                        : 'Tool'
    const parsedTarget = (() => {
        try {
            return new URL(task.target)
        } catch {
            return null
        }
    })()
    const parameterEntries = [
        ['Target', task.target],
        ['Tool', toolLabel],
        ['Plugin', task.plugin_id || 'N/A'],
        ['Status', task.status],
        ['Start Time', task.started_at ? formatDateLong(task.started_at) : 'PENDING'],
        ['Finish Time', task.completed_at ? formatDateLong(task.completed_at) : 'ACTIVE'],
        ['Duration', durationLabel],
        ['Protocol', parsedTarget?.protocol?.replace(':', '').toUpperCase() || 'N/A'],
        ['Host', parsedTarget?.hostname || task.target],
        ['Path', parsedTarget?.pathname || '/'],
        ['Port', parsedTarget?.port || (parsedTarget?.protocol === 'https:' ? '443' : parsedTarget?.protocol === 'http:' ? '80' : 'N/A')],
        ['Findings', String(result?.structured?.total_count || findings.length).padStart(2, '0')],
        ...Object.entries(task.inputs || {}).map(([key, val]) => [formatKeyLabel(key), formatValue(val)] as [string, string]),
    ]
    const uniqueParameterEntries = Array.from(
        new Map(parameterEntries.map(([label, value]) => [label, value])).entries()
    )
    const orderedSeverities = ['critical', 'high', 'medium', 'low', 'info'] as const
    const dominantSeverity = orderedSeverities.find(level => (severityCounts[level] || 0) > 0) || 'info'
    const executiveBullets = summaryItems.length > 0
        ? summaryItems.slice(0, 4).map(item => stripAnsi(item))
        : [
            `${String(result?.structured?.total_count || findings.length)} security findings indexed for ${task.target}.`,
            `Risk analysis identifies ${severityCounts[dominantSeverity] || 0} ${dominantSeverity.toUpperCase()} priority items.`,
            `Current assessment status: ${task.status.toUpperCase()}.`,
            `Scanning engines performed comprehensive inspection via ${toolLabel}.`,
        ]
    const previewFindings = findings.slice(0, 5)
    const toggleFindingRow = (index: number) => {
        setExpandedFindingRows(prev => ({ ...prev, [index]: !prev[index] }))
    }

    const copyRaw = async () => {
        try {
            await navigator.clipboard.writeText(rawOutput || result?.raw_output || '')
            setCopiedRawOutput(true)
            window.setTimeout(() => setCopiedRawOutput(false), 1500)
        } catch (err) {
            console.error('Failed to copy raw output:', err)
        }
    }

    const DetailCard = ({ label, value, subValue }: { label: string, value: string, subValue?: string }) => (
        <div className="bg-charcoal border border-white/5 p-5 shadow-[0_0_0_1px_rgba(255,255,255,0.02)] min-h-[118px] flex flex-col justify-between">
            <div className="space-y-3">
                <span className="text-[10px] font-black text-silver/35 uppercase tracking-[0.28em] italic block">{label}</span>
                <div className="text-xl md:text-2xl font-black text-silver-bright italic tracking-tight break-words">{value}</div>
            </div>
            {subValue && <div className="pt-4 text-[9px] font-mono text-rag-blue/90 font-black uppercase tracking-[0.22em]">{subValue}</div>}
        </div>
    )

    const tabs = [
        { id: 'summary', label: 'Summary' },
        { id: 'results', label: 'Results' },
        { id: 'parameters', label: 'Scan Parameters' },
        { id: 'raw', label: 'Raw Output' },
    ] as const

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver px-3 py-6 md:px-4 xl:px-5 md:py-8 space-y-8">
            <header className="border-b border-white/8 pb-6">
                <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
                    <div className="flex items-start gap-5">
                    <button 
                        onClick={() => navigate(routes.scans)}
                            className="bg-charcoal border border-white/10 p-3 text-silver-bright transition-colors hover:bg-white/[0.04]"
                    >
                        <span className="material-symbols-outlined">arrow_back</span>
                    </button>
                        <div className="space-y-3">
                            <div className="flex flex-wrap items-center gap-3">
                                <span className="bg-rag-blue text-black px-3 py-1 text-[10px] uppercase tracking-[0.3em] inline-block font-black">
                                    Mission_Dossier_SIG#{taskId?.split('-')[0].toUpperCase()}
                                </span>
                                <span className={`px-3 py-1 text-[10px] uppercase tracking-[0.3em] border ${statusTone}`}>
                                    {task.status}
                                </span>
                            </div>
                            <h1 className="text-4xl md:text-6xl text-silver-bright uppercase tracking-tight leading-none italic font-black">
                                Intel <span className="text-transparent" style={{ WebkitTextStroke: '1.5px var(--accent-silver-bright)' }}>Briefing</span>
                            </h1>
                            <div className="space-y-1">
                                <p className="text-lg md:text-3xl font-black italic uppercase tracking-tight text-silver-bright break-all">
                                    {task.target}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-3 xl:justify-end">
                        {(task.status === 'completed' || task.status === 'failed') && (
                            <button
                                onClick={handleRescan}
                                className="bg-rag-blue px-5 py-3 text-black text-[10px] font-black uppercase tracking-[0.26em] italic transition-colors hover:brightness-110 flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined text-sm">restart_alt</span>
                                Rescan_Target
                            </button>
                        )}
                        {task.status === 'completed' && (
                            <>
                                <button
                                    onClick={() => window.open(`${API_BASE}/task/${taskId}/report/csv`)}
                                    className="bg-charcoal px-5 py-3 border border-white/10 text-[10px] font-black uppercase tracking-[0.26em] italic transition-colors hover:bg-white/[0.04] flex items-center gap-2"
                                >
                                    <span className="material-symbols-outlined text-sm">download</span>
                                    Csv_Export
                                </button>
                            <button
                                onClick={() => window.open(`${API_BASE}/task/${taskId}/report/pdf`)}
                                    className="bg-silver-bright px-5 py-3 text-black text-[10px] font-black uppercase tracking-[0.26em] italic transition-colors hover:brightness-95 flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
                                    Pdf_Report
                            </button>
                        </>
                    )}
                </div>
                </div>
            </header>



            <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <DetailCard
                    label="THREAT_LEVEL"
                    value={dominantSeverity.toUpperCase()}
                    subValue={`RISK_PROFILE::${dominantSeverity === 'critical' || dominantSeverity === 'high' ? 'ELEVATED' : 'MODERATE'}`}
                />
                <DetailCard
                    label="MISSION_START"
                    value={startedTime}
                    subValue={task.started_at ? formatDateLong(task.started_at) : 'PENDING'}
                />
                <DetailCard
                    label="SCAN_DURATION"
                    value={durationLabel}
                    subValue={task.completed_at ? `FINISH::${completedTime}` : (task.status === 'failed' ? 'ERROR_TERMINATED' : task.status === 'cancelled' ? 'USER_CANCELLED' : 'IN_PROGRESS')}
                />
                <DetailCard
                    label="TOTAL_FINDINGS"
                    value={String(result?.structured?.total_count || findings.length).padStart(2, '0')}
                    subValue={`ENGINE::${toolLabel}`}
                />
            </section>

            <AnimatePresence>
                {task.status === 'failed' && task.error_message && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="bg-rag-red/10 border-l-4 border-rag-red p-6 space-y-3"
                    >
                        <div className="flex items-center gap-3 text-rag-red">
                            <span className="material-symbols-outlined font-black">warning</span>
                            <h3 className="text-xs font-black uppercase tracking-[0.3em] italic">Critical_Execution_Fault</h3>
                        </div>
                        <p className="text-sm font-mono text-silver/80 leading-relaxed max-w-4xl">
                            {task.error_message}
                        </p>
                        <div className="pt-2">
                             <span className="text-[9px] font-black text-silver/30 uppercase tracking-[0.2em] italic">Diagnostic_Code::EXEC_FAIL_{task.exit_code || 'ERR'}</span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="border-b border-white/8">
                <div className="flex flex-wrap gap-2">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-3 text-[10px] uppercase tracking-[0.28em] font-black transition-colors border-b-2 ${
                                activeTab === tab.id
                                    ? 'text-silver-bright border-rag-blue'
                                    : 'text-silver/40 border-transparent hover:text-silver/75'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="space-y-8">
                <main className="space-y-6">
                    <AnimatePresence mode="wait">
                        {activeTab === 'summary' && (
                            <motion.section
                                key="summary"
                                variants={containerVariants}
                                initial="hidden"
                                animate="visible"
                                exit="hidden"
                                className="space-y-6"
                            >
                                <motion.div variants={itemVariants} className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.5fr)_420px] gap-6">
                                    <section className="border border-white/8 bg-charcoal p-6">
                                        <div className="flex items-center gap-4 mb-5">
                                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Risk Distribution</h3>
                                            <div className="h-px flex-1 bg-white/8" />
                                        </div>
                                        <div className="h-[300px] w-full mt-4">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart 
                                                    data={orderedSeverities.map(s => ({ 
                                                        name: s.toUpperCase(), 
                                                        count: severityCounts[s] || 0,
                                                        color: s === 'critical' ? '#ff3e3e' : s === 'high' ? '#ff9500' : s === 'medium' ? '#0070f3' : s === 'low' ? '#00d1b2' : '#888888'
                                                    }))}
                                                    margin={{ top: 20, right: 30, left: 0, bottom: 0 }}
                                                >
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                                                    <XAxis 
                                                        dataKey="name" 
                                                        axisLine={false} 
                                                        tickLine={false} 
                                                        tick={{ fill: '#ffffff40', fontSize: 10, fontWeight: 900 }} 
                                                        dy={10}
                                                    />
                                                    <YAxis hide />
                                                    <RechartsTooltip 
                                                        cursor={{ fill: 'white', opacity: 0.05 }}
                                                        contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: 0 }}
                                                    />
                                                    <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                                                        {orderedSeverities.map((s, index) => (
                                                            <Cell 
                                                                key={`cell-${index}`} 
                                                                fill={s === 'critical' ? '#ff3e3e' : s === 'high' ? '#ff9500' : s === 'medium' ? '#0070f3' : s === 'low' ? '#00d1b2' : '#888888'} 
                                                                fillOpacity={0.8}
                                                            />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </section>

                                    <section className="border border-white/8 bg-charcoal p-6">
                                        <div className="flex items-center gap-4 mb-5">
                                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Severity Ratio</h3>
                                            <div className="h-px flex-1 bg-white/8" />
                                        </div>
                                        <div className="h-[300px] w-full flex items-center justify-center">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <PieChart>
                                                    <Pie
                                                        data={orderedSeverities
                                                            .map(s => ({ name: s, value: severityCounts[s] || 0 }))
                                                            .filter(d => d.value > 0)}
                                                        innerRadius={60}
                                                        outerRadius={80}
                                                        paddingAngle={5}
                                                        dataKey="value"
                                                    >
                                                        {orderedSeverities.map((s, index) => (
                                                            <Cell 
                                                                key={`cell-${index}`} 
                                                                fill={s === 'critical' ? '#ff3e3e' : s === 'high' ? '#ff9500' : s === 'medium' ? '#0070f3' : s === 'low' ? '#00d1b2' : '#888888'} 
                                                            />
                                                        ))}
                                                    </Pie>
                                                    <RechartsTooltip/>
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </section>
                                </motion.div>

                                <motion.div variants={itemVariants} className="border border-white/8 bg-charcoal p-6">
                                    <div className="flex items-center gap-4 mb-5">
                                        <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Priority Findings</h3>
                                        <div className="h-px flex-1 bg-white/8" />
                                        <span className="text-[10px] uppercase tracking-[0.24em] text-silver/40">{previewFindings.length} Top Hits</span>
                                    </div>
                                    {previewFindings.length > 0 ? (
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {previewFindings.map((f: any, idx: number) => (
                                                <div 
                                                    key={idx} 
                                                    onClick={() => setSelectedFinding(f)}
                                                    className="border border-white/6 bg-black/20 p-5 hover:bg-white/[0.04] cursor-pointer transition-all group relative overflow-hidden"
                                                >
                                                    <div className={`absolute top-0 left-0 w-1 h-full ${
                                                        f.severity === 'critical' ? 'bg-rag-red' : f.severity === 'high' ? 'bg-rag-amber' : 'bg-rag-blue'
                                                    }`} />
                                                    <div className="flex justify-between items-start mb-3">
                                                        <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 border ${severityTone(f.severity)}`}>
                                                            {f.severity}
                                                        </span>
                                                        <span className="text-[10px] font-mono text-silver/20 group-hover:text-rag-blue transition-colors">#{idx.toString().padStart(3, '0')}</span>
                                                    </div>
                                                    <h4 className="text-sm font-black text-silver-bright uppercase italic mb-2 line-clamp-1">{stripAnsi(f.title)}</h4>
                                                    <p className="text-xs text-silver/50 line-clamp-2 leading-relaxed">{stripAnsi(f.description)}</p>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-sm text-silver/55 italic">No findings identified for this target profile.</p>
                                    )}
                                </motion.div>
                            </motion.section>
                        )}

                        {activeTab === 'results' && (
                            <motion.section
                                key="results"
                                variants={containerVariants}
                                initial="hidden"
                                animate="visible"
                                exit="hidden"
                                className="space-y-6"
                            >
                                <motion.div variants={itemVariants} className="border border-white/8 bg-charcoal p-6">
                                    <div className="flex items-center gap-4 mb-5">
                                        <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Discovery Results</h3>
                                        <div className="h-px flex-1 bg-white/8" />
                                        <span className="text-[10px] uppercase tracking-[0.24em] text-silver/40">
                                            {resultEntryCount} {resultEntryCount === 1 ? 'Entry' : 'Entries'}
                                        </span>
                                    </div>
                                    {tableRows.length > 0 ? (
                                        <div className="relative overflow-x-auto overflow-y-auto max-h-[72vh] border border-white/6 bg-black/20 custom-scrollbar rounded-sm">
                                            <table className="w-full text-left text-[11px] font-mono border-collapse table-fixed">
                                                <thead>
                                                    <tr className="sticky top-0 z-20 border-b border-white/10 text-silver/40 uppercase tracking-[0.22em] bg-[#0c0c0f] shadow-[0_1px_0_0_rgba(255,255,255,0.05)]">
                                                        {Object.keys(tableRows[0]).map((key, kIdx) => (
                                                            <th key={key} className={`px-4 py-4 font-black ${kIdx === 0 ? 'w-[120px]' : ''}`}>{formatKeyLabel(key)}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {tableRows.map((row: any, idx: number) => {
                                                        const isExpanded = expandedDiscoveryRows[idx];
                                                        return (
                                                            <tr key={idx} className="border-b border-white/5 last:border-0 hover:bg-white/[0.03] transition-colors group">
                                                                {Object.entries(row).map(([key, val], vIdx) => {
                                                                    const strVal = stripAnsi(val) || '-';
                                                                    const isLong = strVal.length > 120;
                                                                    return (
                                                                        <td key={vIdx} className={`px-4 py-4 align-top ${vIdx === 0 ? 'text-rag-blue font-bold' : 'text-silver/75'}`}>
                                                                            <div className="space-y-2">
                                                                                <div className={`${!isExpanded && isLong ? 'line-clamp-2' : ''} break-words whitespace-pre-wrap`}>
                                                                                    {strVal}
                                                                                </div>
                                                                                {isLong && vIdx > 0 && (
                                                                                    <button
                                                                                        onClick={() => setExpandedDiscoveryRows(prev => ({ ...prev, [idx]: !prev[idx] }))}
                                                                                        className="text-[9px] uppercase tracking-[0.15em] text-rag-blue/70 hover:text-rag-blue font-black transition-colors"
                                                                                    >
                                                                                        {isExpanded ? '[ COLLAPSE ]' : '[ EXPAND ]'}
                                                                                    </button>
                                                                                )}
                                                                            </div>
                                                                        </td>
                                                                    );
                                                                })}
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : findings.length > 0 ? (
                                        <div className="relative overflow-x-auto overflow-y-auto max-h-[72vh] border border-white/6 bg-black/20 custom-scrollbar rounded-sm">
                                            <table className="w-full text-left border-collapse table-fixed">
                                                <thead>
                                                    <tr className="sticky top-0 z-20 border-b border-white/10 bg-[#0c0c0f] text-[10px] uppercase tracking-[0.2em] text-silver/35 font-black shadow-[0_1px_0_0_rgba(255,255,255,0.05)]">
                                                        <th className="px-4 py-4 w-[100px]">Entry</th>
                                                        <th className="px-4 py-4 w-[280px]">Finding</th>
                                                        <th className="px-4 py-4 w-[130px]">Severity</th>
                                                        <th className="px-4 py-4">Description</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {findings.map((f: Finding, idx: number) => {
                                                        const description = stripAnsi(f.description) || 'No description provided.';
                                                        
                                                        return (
                                                            <tr
                                                                key={idx}
                                                                onClick={() => setSelectedFinding(f)}
                                                                className="border-b border-white/5 last:border-0 hover:bg-white/[0.03] transition-colors group cursor-pointer"
                                                            >
                                                                <td className="px-4 py-6 align-top text-[10px] font-mono uppercase tracking-[0.24em] text-rag-blue/80 font-bold">
                                                                    #{idx.toString().padStart(3, '0')}
                                                                </td>
                                                                <td className="px-4 py-6 align-top">
                                                                    <div className="text-sm md:text-[15px] font-black text-silver-bright uppercase tracking-tight italic break-words leading-tight">
                                                                        {stripAnsi(f.title)}
                                                                    </div>
                                                                </td>
                                                                <td className="px-4 py-6 align-top">
                                                                    <span className={`inline-flex px-3 py-1 text-[10px] font-black uppercase italic border shadow-sm ${severityTone(f.severity)}`}>
                                                                        {f.severity || 'info'}
                                                                    </span>
                                                                </td>
                                                                <td className="px-4 py-6 align-top text-xs md:text-sm text-silver/70 leading-relaxed">
                                                                    <div className="line-clamp-2 break-words whitespace-pre-wrap">
                                                                        {description}
                                                                    </div>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <p className="text-sm text-silver/55 italic">No tabular result set is available for this task.</p>
                                    )}
                                </motion.div>
                            </motion.section>
                        )}

                        {activeTab === 'parameters' && (
                            <motion.section
                                key="parameters"
                                variants={containerVariants}
                                initial="hidden"
                                animate="visible"
                                exit="hidden"
                                className="space-y-6"
                            >
                                <motion.div variants={itemVariants} className="border border-white/8 bg-charcoal p-6">
                                    <div className="flex items-center gap-4 mb-5">
                                        <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Scan Parameters</h3>
                                        <div className="h-px flex-1 bg-white/8" />
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                                        {uniqueParameterEntries.map(([label, value]) => (
                                            <div key={label} className="border border-white/6 bg-black/20 px-4 py-4 min-h-[110px]">
                                                <p className="text-[10px] font-black text-silver/30 uppercase tracking-[0.22em] mb-3">
                                                    {label}
                                                </p>
                                                <p className={`text-sm font-black uppercase break-words leading-6 ${
                                                    value === 'ON' || value === 'TRUE'
                                                        ? 'text-rag-green'
                                                        : value === 'OFF' || value === 'FALSE'
                                                            ? 'text-rag-red'
                                                            : 'text-silver-bright'
                                                }`}>
                                                    {value}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            </motion.section>
                        )}

                        {activeTab === 'raw' && (
                            <motion.section
                                key="raw"
                                variants={containerVariants}
                                initial="hidden"
                                animate="visible"
                                exit="hidden"
                                className="space-y-6"
                            >
                                <motion.div variants={itemVariants} className="border border-white/8 bg-charcoal p-6">
                                    <div className="flex flex-col gap-4 mb-5">
                                        <div className="flex items-center gap-4">
                                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Raw Output</h3>
                                            <div className="h-px flex-1 bg-white/8" />
                                        </div>
                                        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                            <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
                                                <input
                                                    value={rawSearch}
                                                    onChange={(e) => setRawSearch(e.target.value)}
                                                    placeholder="Filter raw output"
                                                    className="bg-black/30 border border-white/10 px-3 py-2 text-sm text-silver-bright outline-none min-w-[240px]"
                                                />
                                                <span className="text-[10px] uppercase tracking-[0.2em] text-silver/40">
                                                    {filteredRawLines.length} lines
                                                </span>
                                            </div>
                                            <div className="flex gap-3">
                                                <button
                                                    onClick={() => setWrapRawOutput(prev => !prev)}
                                                    className="border border-white/10 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-silver/75 font-black"
                                                >
                                                    {wrapRawOutput ? 'Disable Wrap' : 'Enable Wrap'}
                                                </button>
                                                <button
                                                    onClick={copyRaw}
                                                    className="border border-white/10 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-silver/75 font-black"
                                                >
                                                    {copiedRawOutput ? 'Copied' : 'Copy Output'}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="border border-white/6 bg-black/30 p-4 max-h-[720px] overflow-auto">
                                        <pre className={`${wrapRawOutput ? 'whitespace-pre-wrap break-words' : 'whitespace-pre'} text-[11px] leading-6 font-mono text-silver/75`}>
                                            {filteredRawLines.length > 0
                                                ? filteredRawLines.join('\n')
                                                : 'No matching raw output lines.'}
                                        </pre>
                                    </div>
                                </motion.div>
                            </motion.section>
                        )}
                    </AnimatePresence>
                </main>

                <aside className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                    <section className="border border-white/8 bg-charcoal p-5 space-y-5">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Scan Manifest</h3>
                            <div className="h-px flex-1 bg-white/8" />
                        </div>
                        <div className="space-y-4">
                            {[
                                ['Tool', toolLabel],
                                ['Plugin', task.plugin_id || 'N/A'],
                                ['Status', task.status],
                                ['Created', formatDateLong(task.created_at)],
                                ['Started', task.started_at ? formatDateLong(task.started_at) : 'PENDING'],
                                ['Completed', task.completed_at ? formatDateLong(task.completed_at) : 'ACTIVE'],
                            ].map(([label, value]) => (
                                <div key={label} className="border-b border-white/6 pb-3 last:border-0 last:pb-0">
                                    <p className="text-[10px] uppercase tracking-[0.24em] text-silver/30 font-black mb-1">{label}</p>
                                    <p className="text-sm text-silver-bright font-mono break-words">{value}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="border border-white/8 bg-charcoal p-5 space-y-5">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Quick Parameters</h3>
                            <div className="h-px flex-1 bg-white/8" />
                        </div>
                        <div className="space-y-3">
                            {Object.entries(task.inputs || {}).slice(0, 6).map(([key, val]: [string, any]) => (
                                <div key={key} className="flex items-start justify-between gap-4 border-b border-white/6 pb-3 last:border-0 last:pb-0">
                                    <span className="text-[10px] font-black text-silver/30 uppercase tracking-[0.18em]">
                                        {formatKeyLabel(key)}
                                    </span>
                                    <span className="text-[11px] font-black uppercase text-right text-silver-bright break-all">
                                        {formatValue(val)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>

                    {result?.command_used && (
                        <section className="border border-white/8 bg-charcoal p-5 space-y-5">
                            <div className="flex items-center gap-4">
                                <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Operational Command</h3>
                                <div className="h-px flex-1 bg-white/8" />
                            </div>
                            <div className="border border-white/6 bg-black/30 p-4 font-mono text-[10px] text-rag-blue/70 break-all italic leading-6">
                                <span className="text-silver/20 mr-2">$</span>
                                {result.command_used}
                            </div>
                        </section>
                    )}
                </aside>
            </div>

            <footer className="pt-12 border-t border-white/6 flex flex-col md:flex-row justify-between items-center gap-6 text-[9px] font-black uppercase tracking-[0.4em] italic opacity-25">
                <div className="flex items-center gap-6">
                    <div className="w-12 h-1 bg-silver/20"></div>
                    CLASSIFIED_EXECUTIVE_SUMMARY // CORE_DAEMON_LOG_ID::{taskId?.split('-')[0].toUpperCase()}
                </div>
                <div className="flex gap-4">
                    {[1,2,3,4].map(i => <div key={i} className="w-20 h-1 bg-silver/20"></div>)}
                </div>
            </footer>

            <AnimatePresence>
                {selectedFinding && (
                    <>
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setSelectedFinding(null)}
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[90]"
                        />
                        <FindingDrawer finding={selectedFinding as Finding} onClose={() => setSelectedFinding(null)} />
                    </>
                )}
            </AnimatePresence>
        </div>
    )
}
