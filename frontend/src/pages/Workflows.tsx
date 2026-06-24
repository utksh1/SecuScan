import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getWorkflows,
  createWorkflow,
  runWorkflow,
  updateWorkflow,
  deleteWorkflow,
  getWorkflowRuns,
  getWorkflowVersions,
  rollbackWorkflow,
  type Workflow,
  type WorkflowCreatePayload,
  type WorkflowRun,
  type WorkflowVersion,
} from '../api'
import { formatDateLong, parseDateSafe } from '../utils/date'
import { useToast } from '../components/ToastContext'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

const emptySteps = [{
  plugin_id: '',
  inputs: {},
  execution_context: {
    scan_profile: 'standard',
    validation_mode: 'proof',
    evidence_level: 'standard',
  },
}]

function timeAgo(iso?: string | null) {
  if (!iso) return null
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function formatSchedule(scheduleSeconds?: number | null) {
  if (!scheduleSeconds || scheduleSeconds <= 0) return 'Manual'
  if (scheduleSeconds < 60) return `Every ${scheduleSeconds}s`

  const minutes = scheduleSeconds / 60
  if (Number.isInteger(minutes) && minutes < 60) {
    return `Every ${minutes}m`
  }

  const hours = scheduleSeconds / 3600
  if (Number.isInteger(hours) && hours < 24) {
    return `Every ${hours}h`
  }

  const days = scheduleSeconds / 86400
  if (Number.isInteger(days)) {
    return `Every ${days}d`
  }

  return `Every ${scheduleSeconds}s`
}

interface DeleteDialogProps {
  name: string
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
}

function DeleteDialog({ name, onConfirm, onCancel, loading }: DeleteDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] w-full max-w-sm space-y-6">
        <div className="space-y-2">
          <h3 className="text-lg font-black text-silver-bright uppercase tracking-tight">Delete Workflow</h3>
          <p className="text-[11px] text-silver/50 uppercase tracking-widest font-black">
            Delete <span className="text-silver-bright">{name}</span>? This cannot be undone.
          </p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 border-4 border-black px-4 py-3 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 bg-rag-red border-4 border-black px-4 py-3 text-[10px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all disabled:opacity-40"
          >
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

interface CreateSheetProps {
  onClose: () => void
  onCreated: (w: Workflow) => void
}

function CreateSheet({ onClose, onCreated }: CreateSheetProps) {
  const [name, setName] = useState('')
  const [scheduleSeconds, setScheduleSeconds] = useState('3600')
  const [enabled, setEnabled] = useState(true)
  const [stepsJson, setStepsJson] = useState(JSON.stringify(emptySteps, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setJsonError(null)
    setError(null)

    let steps
    try {
      steps = JSON.parse(stepsJson)
    } catch {
      setJsonError('Invalid JSON in steps field')
      return
    }

    const trimmedSchedule = scheduleSeconds.trim()
    const parsedSchedule = trimmedSchedule === '' ? null : Number(trimmedSchedule)
    if (
      parsedSchedule !== null &&
      (!Number.isInteger(parsedSchedule) || parsedSchedule <= 0)
    ) {
      setError('Schedule must be a positive whole number of seconds')
      return
    }

    setLoading(true)
    try {
      const payload: WorkflowCreatePayload = { name, schedule_seconds: parsedSchedule, enabled, steps }
      const created = await createWorkflow(payload)
      onCreated(created)
    } catch {
      setError('Failed to create workflow')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/60">
      <div className="bg-charcoal border-4 border-black w-full max-w-lg shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-8 py-6 border-b-4 border-black">
          <h2 className="text-xl font-black text-silver-bright uppercase tracking-tight">New Workflow</h2>
          <button onClick={onClose} className="text-silver/40 hover:text-silver-bright transition-colors">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          <div className="space-y-2">
            <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em]">Name</label>
            <input
              required
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="My Workflow"
              className="w-full bg-charcoal-dark border-4 border-black px-4 py-3 text-sm text-silver-bright placeholder:text-silver/30 focus:outline-none focus:border-rag-red transition-colors"
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em]">Schedule (seconds)</label>
            <input
              value={scheduleSeconds}
              onChange={e => setScheduleSeconds(e.target.value)}
              placeholder="3600"
              inputMode="numeric"
              className="w-full bg-charcoal-dark border-4 border-black px-4 py-3 text-sm text-silver-bright font-mono placeholder:text-silver/30 focus:outline-none focus:border-rag-red transition-colors"
            />
          </div>

          <div className="flex items-center justify-between">
            <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em]">Enabled</label>
            <button
              type="button"
              onClick={() => setEnabled(v => !v)}
              className={`w-12 h-6 border-4 border-black transition-colors relative ${enabled ? 'bg-rag-green' : 'bg-charcoal-dark'}`}
            >
              <span className={`absolute top-0 bottom-0 w-4 bg-black transition-all ${enabled ? 'right-0' : 'left-0'}`} />
            </button>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em]">Steps (JSON)</label>
            <textarea
              rows={6}
              value={stepsJson}
              onChange={e => { setStepsJson(e.target.value); setJsonError(null) }}
              className="w-full bg-charcoal-dark border-4 border-black px-4 py-3 text-xs text-silver-bright font-mono placeholder:text-silver/30 focus:outline-none focus:border-rag-red transition-colors resize-none"
            />
            {jsonError && <p className="text-[10px] text-rag-red font-black uppercase tracking-widest">{jsonError}</p>}
          </div>

          {error && <p className="text-[10px] text-rag-red font-black uppercase tracking-widest">{error}</p>}

          <div className="flex gap-4 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border-4 border-black px-4 py-3 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-silver-bright border-4 border-black px-4 py-3 text-[10px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all disabled:opacity-40"
            >
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface WorkflowCardProps {
  workflow: Workflow
  onToggle: () => void
  onRun: () => void
  onDelete: () => void
  onOpenHistory: () => void
  running: boolean
  toggling: boolean
}

function WorkflowCard({ workflow, onToggle, onRun, onDelete, onOpenHistory, running, toggling }: WorkflowCardProps) {
  return (
    <motion.div
      variants={itemVariants}
      className="group bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] transition-all relative overflow-hidden"
    >
      <div className={`absolute top-0 left-0 h-1.5 w-full ${workflow.enabled ? 'bg-rag-green' : 'bg-silver/20'}`} />

      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <h3 className="text-xl font-black text-silver-bright uppercase tracking-tight truncate">{workflow.name}</h3>
            <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest">{formatSchedule(workflow.schedule_seconds)}</p>
          </div>
          <span className={`shrink-0 px-2 py-1 text-[9px] font-black uppercase tracking-widest border-2 border-black ${workflow.enabled ? 'bg-rag-green text-black' : 'bg-charcoal-dark text-silver/40'}`}>
            {workflow.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 py-4 border-y-2 border-black border-dashed text-[10px] font-black uppercase tracking-widest">
          <div className="space-y-1">
            <span className="text-silver/30 block">Steps</span>
            <span className="text-silver-bright">{workflow.steps?.length ?? 0}</span>
          </div>
          <div className="space-y-1">
            <span className="text-silver/30 block">Last Run</span>
            <span className="text-silver-bright">{timeAgo(workflow.last_run_at) ?? 'Never'}</span>
          </div>
        </div>

        {workflow.queued_task_ids && workflow.queued_task_ids.length > 0 && (
          <div className="space-y-1">
            <p className="text-[9px] font-black text-silver/30 uppercase tracking-widest">Queued Tasks</p>
            <div className="flex flex-wrap gap-1">
              {workflow.queued_task_ids.map(id => (
                <span key={id} className="text-[9px] font-mono text-silver/50 bg-charcoal-dark px-2 py-0.5 border border-black">
                  {id.slice(0, 8)}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={onRun}
            disabled={running}
            title="Run now"
            className="bg-rag-blue border-4 border-black p-2.5 text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all disabled:opacity-40"
          >
            <span className="material-symbols-outlined text-[18px]">{running ? 'hourglass_empty' : 'play_arrow'}</span>
          </button>

          <button
            onClick={onToggle}
            disabled={toggling}
            title={workflow.enabled ? 'Disable' : 'Enable'}
            className="border-4 border-black p-2.5 text-silver/50 hover:text-silver-bright hover:bg-charcoal-dark transition-all disabled:opacity-40"
          >
            <span className="material-symbols-outlined text-[18px]">{workflow.enabled ? 'pause' : 'play_circle'}</span>
          </button>

          <button
            onClick={onOpenHistory}
            title="History & Versions"
            className="border-4 border-black p-2.5 text-silver/50 hover:text-silver-bright hover:bg-charcoal-dark transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">history</span>
          </button>

          <button
            onClick={onDelete}
            title="Delete"
            className="ml-auto border-4 border-black p-2.5 text-silver/30 hover:text-rag-red hover:bg-rag-red/10 transition-all"
          >
            <span className="material-symbols-outlined text-[18px]">delete</span>
          </button>
        </div>
      </div>
    </motion.div>
  )
}

interface HistoryVersionsDrawerProps {
  workflow: Workflow
  onClose: () => void
  onRollbackSuccess: (updatedWorkflow: Workflow) => void
}

function HistoryVersionsDrawer({ workflow, onClose, onRollbackSuccess }: HistoryVersionsDrawerProps) {
  const [activeTab, setActiveTab] = useState<'history' | 'versions'>('history')
  const [runs, setRuns] = useState<WorkflowRun[]>([])
  const [versions, setVersions] = useState<WorkflowVersion[]>([])
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [loadingVersions, setLoadingVersions] = useState(false)
  const [runsError, setRunsError] = useState<string | null>(null)
  const [versionsError, setVersionsError] = useState<string | null>(null)
  const [restoringVersion, setRestoringVersion] = useState<number | null>(null)
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null)
  const { addToast } = useToast()

  async function fetchRuns() {
    setLoadingRuns(true)
    setRunsError(null)
    try {
      const data = await getWorkflowRuns(workflow.id)
      setRuns(data.runs)
    } catch {
      setRunsError('Failed to load execution history')
    } finally {
      setLoadingRuns(false)
    }
  }

  async function fetchVersions() {
    setLoadingVersions(true)
    setVersionsError(null)
    try {
      const data = await getWorkflowVersions(workflow.id)
      setVersions(data.versions)
    } catch {
      setVersionsError('Failed to load version snapshots')
    } finally {
      setLoadingVersions(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'history') {
      fetchRuns()
    } else {
      fetchVersions()
    }
  }, [workflow.id, activeTab])

  async function handleRestore(versionNumber: number) {
    setRestoringVersion(versionNumber)
    try {
      const res = await rollbackWorkflow(workflow.id, versionNumber)
      addToast(`Workflow rolled back to version ${versionNumber} successfully`, 'success')
      onRollbackSuccess(res.workflow)
      fetchVersions()
    } catch {
      addToast(`Failed to restore version ${versionNumber}`, 'error')
    } finally {
      setRestoringVersion(null)
    }
  }

  function getDuration(started: string, completed?: string | null): string {
    const start = parseDateSafe(started)
    const end = completed ? parseDateSafe(completed) : null
    if (!start) return '-'
    if (!end) return 'Running'
    const seconds = Math.max(0, Math.floor((end.getTime() - start.getTime()) / 1000))
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="slideover-backdrop"
        onClick={onClose}
      />

      {/* Drawer Container */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="slideover w-full max-w-lg md:max-w-xl"
        style={{ animation: 'none' }}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-black bg-[#0c0c0f]">
          <div>
            <h2 className="text-lg font-black text-silver-bright uppercase tracking-tight truncate max-w-[320px]">{workflow.name}</h2>
            <p className="text-[9px] font-mono text-silver/40 uppercase tracking-widest mt-0.5">Configuration & History</p>
          </div>
          <button onClick={onClose} className="text-silver/45 hover:text-silver-bright transition-colors">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="flex border-b border-black bg-charcoal/20 px-6">
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-4 text-[10px] uppercase tracking-[0.2em] font-black transition-all border-b-4 text-center ${
              activeTab === 'history'
                ? 'text-silver-bright border-rag-blue bg-white/[0.02]'
                : 'text-silver/40 border-transparent hover:text-silver/70'
            }`}
          >
            Execution History
          </button>
          <button
            onClick={() => setActiveTab('versions')}
            className={`flex-1 py-4 text-[10px] uppercase tracking-[0.2em] font-black transition-all border-b-4 text-center ${
              activeTab === 'versions'
                ? 'text-silver-bright border-rag-blue bg-white/[0.02]'
                : 'text-silver/40 border-transparent hover:text-silver/70'
            }`}
          >
            Versions
          </button>
        </div>

        <div className="slideover-content p-6 space-y-6 custom-scrollbar overflow-y-auto flex-1">
          {activeTab === 'history' ? (
            loadingRuns ? (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <span className="material-symbols-outlined text-silver/20 text-3xl animate-spin">progress_activity</span>
                <p className="text-[9px] font-black text-silver/20 uppercase tracking-[0.3em] italic animate-pulse">Loading runs...</p>
              </div>
            ) : runsError ? (
              <div className="border-4 border-rag-red bg-rag-red/10 p-5 text-center space-y-3">
                <p className="text-[10px] font-black text-rag-red uppercase tracking-widest">Error</p>
                <p className="text-xs text-silver/60">{runsError}</p>
                <button onClick={fetchRuns} className="bg-rag-red border-4 border-black px-4 py-2 text-[9px] font-black uppercase text-black hover:translate-x-0.5 hover:translate-y-0.5 transition-all">
                  Retry
                </button>
              </div>
            ) : runs.length === 0 ? (
              <div className="py-20 text-center space-y-3 opacity-40">
                <span className="material-symbols-outlined text-silver/10 text-5xl">history_toggle_off</span>
                <p className="text-[10px] font-black text-silver-bright uppercase tracking-widest">No runs recorded</p>
                <p className="text-[9px] font-mono text-silver/60">This workflow hasn't executed yet.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {runs.map(run => (
                  <div key={run.id} className="border-4 border-black bg-charcoal p-5 relative overflow-hidden shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    <div className={`absolute top-0 left-0 h-1.5 w-full ${
                      run.status === 'completed' ? 'bg-rag-green' :
                      run.status === 'failed' ? 'bg-rag-red' :
                      run.status === 'running' ? 'bg-rag-blue animate-pulse' :
                      run.status === 'cancelled' ? 'bg-rag-amber' : 'bg-silver/20'
                    }`} />

                    <div className="space-y-4 pt-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-widest border-2 border-black ${
                          run.status === 'completed' ? 'bg-rag-green text-black' :
                          run.status === 'failed' ? 'bg-rag-red text-black' :
                          run.status === 'running' ? 'bg-rag-blue text-black animate-pulse' :
                          run.status === 'cancelled' ? 'bg-rag-amber text-black' :
                          'bg-charcoal-dark text-silver/40 border-black/50'
                        }`}>
                          {run.status}
                        </span>

                        <span className="text-[9px] font-mono text-silver/40 uppercase tracking-wider">
                          {run.version_number ? `Version ${run.version_number}` : 'v1'}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-[9px] font-mono text-silver/60 py-3 border-y border-black border-dashed">
                        <div>
                          <span className="text-silver/30 uppercase block">Started</span>
                          <span className="text-silver-bright">{run.started_at ? formatDateLong(run.started_at) : 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-silver/30 uppercase block">Duration</span>
                          <span className="text-silver-bright">{getDuration(run.started_at, run.completed_at)}</span>
                        </div>
                      </div>

                      {run.error_message && (
                        <div className="bg-rag-red/5 border-l-4 border-rag-red p-3 font-mono text-[9px] text-rag-red leading-relaxed break-words">
                          {run.error_message}
                        </div>
                      )}

                      {run.task_ids && run.task_ids.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-[9px] font-black text-silver/30 uppercase tracking-widest block">Associated Tasks</span>
                          <div className="flex flex-wrap gap-2">
                            {run.task_ids.map(tid => (
                              <Link
                                key={tid}
                                to={`/task/${tid}`}
                                className="text-[9px] font-mono text-rag-blue hover:text-rag-blue/80 bg-charcoal-dark border-2 border-black px-2 py-1 shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
                              >
                                {tid.slice(0, 8)} →
                              </Link>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            loadingVersions ? (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <span className="material-symbols-outlined text-silver/20 text-3xl animate-spin">progress_activity</span>
                <p className="text-[9px] font-black text-silver/20 uppercase tracking-[0.3em] italic animate-pulse">Loading versions...</p>
              </div>
            ) : versionsError ? (
              <div className="border-4 border-rag-red bg-rag-red/10 p-5 text-center space-y-3">
                <p className="text-[10px] font-black text-rag-red uppercase tracking-widest">Error</p>
                <p className="text-xs text-silver/60">{versionsError}</p>
                <button onClick={fetchVersions} className="bg-rag-red border-4 border-black px-4 py-2 text-[9px] font-black uppercase text-black hover:translate-x-0.5 hover:translate-y-0.5 transition-all">
                  Retry
                </button>
              </div>
            ) : versions.length === 0 ? (
              <div className="py-20 text-center space-y-3 opacity-40">
                <span className="material-symbols-outlined text-silver/10 text-5xl">history_toggle_off</span>
                <p className="text-[10px] font-black text-silver-bright uppercase tracking-widest">No versions found</p>
              </div>
            ) : (
              <div className="space-y-4">
                {versions.map(v => {
                  const isExpanded = expandedVersionId === v.id
                  return (
                    <div key={v.id} className="border-4 border-black bg-charcoal p-5 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] relative">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h4 className="text-sm font-black text-silver-bright uppercase tracking-tight">Version {v.version_number}</h4>
                            <p className="text-[9px] font-mono text-silver/40 uppercase tracking-widest mt-0.5">
                              {v.created_at ? formatDateLong(v.created_at) : 'N/A'}
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setExpandedVersionId(isExpanded ? null : v.id)}
                              className="border-4 border-black hover:bg-charcoal-dark text-silver/70 hover:text-silver-bright font-black uppercase text-[9px] tracking-widest px-3 py-1.5 transition-all"
                            >
                              {isExpanded ? 'Hide Steps' : 'View Steps'}
                            </button>
                            <button
                              onClick={() => handleRestore(v.version_number)}
                              disabled={restoringVersion !== null}
                              className="bg-silver-bright hover:bg-white text-black border-4 border-black font-black uppercase text-[9px] tracking-widest px-3 py-1.5 shadow-[2px_2px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all disabled:opacity-40"
                            >
                              {restoringVersion === v.version_number ? 'Restoring...' : 'Restore'}
                            </button>
                          </div>
                        </div>

                        <div className="grid grid-cols-3 gap-2 text-[9px] font-mono text-silver/60 pt-3 border-t border-black border-dashed">
                          <div>
                            <span className="text-silver/30 uppercase block">Created By</span>
                            <span className="text-silver-bright truncate block" title={v.created_by}>{v.created_by}</span>
                          </div>
                          <div>
                            <span className="text-silver/30 uppercase block">Schedule</span>
                            <span className="text-silver-bright">{formatSchedule(v.definition?.schedule_seconds)}</span>
                          </div>
                          <div>
                            <span className="text-silver/30 uppercase block">Steps</span>
                            <span className="text-silver-bright">{v.definition?.steps?.length ?? 0}</span>
                          </div>
                        </div>

                        {isExpanded && (
                          <pre className="bg-black/40 border-4 border-black p-3 text-[10px] font-mono text-silver/70 max-h-48 overflow-y-auto whitespace-pre-wrap mt-3 custom-scrollbar">
                            {JSON.stringify(v.definition?.steps, null, 2)}
                          </pre>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          )}
        </div>
      </motion.div>
    </>
  )
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Workflow | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [togglingId, setTogglingId] = useState<string | null>(null)
  const [historyWorkflow, setHistoryWorkflow] = useState<Workflow | null>(null)
  const { addToast } = useToast()

  async function fetchWorkflows() {
    setLoading(true)
    setError(null)
    try {
      const data = await getWorkflows()
      setWorkflows(data)
    } catch {
      setError('Failed to load workflows')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchWorkflows() }, [])

  async function handleRun(id: string) {
    setRunningId(id)
    try {
      await runWorkflow(id)
      addToast('Workflow execution queued successfully', 'success')
      await fetchWorkflows()
    } catch {
      addToast('Failed to queue workflow execution', 'error')
    } finally {
      setRunningId(null)
    }
  }

  async function handleToggle(workflow: Workflow) {
    setTogglingId(workflow.id)
    try {
      const updated = await updateWorkflow(workflow.id, { enabled: !workflow.enabled })
      setWorkflows(prev => prev.map(w => w.id === updated.id ? updated : w))
      addToast(`Workflow ${!workflow.enabled ? 'enabled' : 'disabled'} successfully`, 'success')
    } catch {
      addToast('Failed to update workflow status', 'error')
    } finally {
      setTogglingId(null)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteWorkflow(deleteTarget.id)
      setWorkflows(prev => prev.filter(w => w.id !== deleteTarget.id))
      addToast('Workflow deleted successfully', 'success')
      setDeleteTarget(null)
    } catch {
      addToast('Failed to delete workflow', 'error')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
            Automation
          </div>
          <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
            Workflows
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic">
            Scheduled scan workflows
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={fetchWorkflows}
            className="bg-charcoal border-4 border-black p-4 text-silver-bright shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            title="Refresh"
          >
            <span className="material-symbols-outlined">sync</span>
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="bg-silver-bright border-4 border-black px-6 py-4 text-[10px] font-black uppercase tracking-widest text-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            + New Workflow
          </button>
        </div>
      </header>

      {loading && (
        <div className="flex items-center justify-center py-40 gap-6">
          <span className="material-symbols-outlined text-silver/20 text-5xl animate-spin">progress_activity</span>
          <p className="text-[10px] font-black text-silver/20 uppercase tracking-[0.4em] italic animate-pulse">
            Loading Workflows...
          </p>
        </div>
      )}

      {!loading && error && (
        <div className="border-4 border-rag-red bg-rag-red/10 p-8 flex items-center gap-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
          <span className="material-symbols-outlined text-rag-red text-3xl">error</span>
          <div className="space-y-1">
            <p className="text-xs font-black text-rag-red uppercase tracking-widest">Failed to load</p>
            <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest">{error}</p>
          </div>
          <button
            onClick={fetchWorkflows}
            className="ml-auto bg-rag-red border-4 border-black px-6 py-3 text-[9px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && workflows.length === 0 && (
        <div className="py-40 border-4 border-dashed border-black/5 text-center flex flex-col items-center gap-8 bg-charcoal/30">
          <span className="material-symbols-outlined text-silver/5 text-9xl">account_tree</span>
          <div className="space-y-2">
            <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">No Workflows</p>
            <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">Create a workflow to automate recurring scans</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="bg-silver-bright border-4 border-black px-6 py-3 text-[10px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            + New Workflow
          </button>
        </div>
      )}

      {!loading && !error && workflows.length > 0 && (
        <AnimatePresence mode="popLayout">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8"
          >
            {workflows.map(workflow => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                onRun={() => handleRun(workflow.id)}
                onToggle={() => handleToggle(workflow)}
                onOpenHistory={() => setHistoryWorkflow(workflow)}
                onDelete={() => setDeleteTarget(workflow)}
                running={runningId === workflow.id}
                toggling={togglingId === workflow.id}
              />
            ))}
          </motion.div>
        </AnimatePresence>
      )}

      {showCreate && (
        <CreateSheet
          onClose={() => setShowCreate(false)}
          onCreated={w => {
            setWorkflows(prev => [w, ...prev])
            setShowCreate(false)
          }}
        />
      )}

      {deleteTarget && (
        <DeleteDialog
          name={deleteTarget.name}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}

      <AnimatePresence>
        {historyWorkflow && (
          <HistoryVersionsDrawer
            workflow={historyWorkflow}
            onClose={() => setHistoryWorkflow(null)}
            onRollbackSuccess={updated => {
              setWorkflows(prev => prev.map(w => w.id === updated.id ? updated : w))
              setHistoryWorkflow(updated)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
