import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  getTaskStatus, 
  getTaskResult, 
  getPluginSchema,
  startTask,
  cancelTask 
} from '../api'
import { useTaskSubscription } from '../hooks/useTaskSubscription'
import { useToast } from '../components/ToastContext'
import { ConfirmModal } from '../components/ConfirmModal'
import { routePath } from '../routes'

interface Task {
  task_id: string
  plugin_id: string
  tool: string
  target: string
  status: string
  scan_phase?: string
  created_at: string
  started_at?: string
  completed_at?: string
  duration_seconds?: number
  inputs?: any
  preset?: string
}

interface TaskResult {
  findings?: any[]
  raw_output?: string
  summary?: any
}

interface PluginSchemaResponse {
  id: string
  name: string
  description: string
  fields: any[]
}

interface Finding {
  id: string
  title: string
  severity: string
  description: string
  remediation?: string
}

export default function TaskDetails() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const { addToast } = useToast()
  
  // Mounted ref to prevent state updates after unmount
  const isMounted = useRef(true)
  const loadTaskSeqRef = useRef(0)
  
  const [task, setTask] = useState<Task | null>(null)
  const [result, setResult] = useState<TaskResult | null>(null)
  const [schema, setSchema] = useState<PluginSchemaResponse | null>(null)
  const [rawOutput, setRawOutput] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scanPhase, setScanPhase] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'summary' | 'results' | 'parameters' | 'raw'>('summary')
  const [expandedFindingRows, setExpandedFindingRows] = useState<Record<number, boolean>>({})
  const [expandedDiscoveryRows, setExpandedDiscoveryRows] = useState<Record<number, boolean>>({})
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [rawSearch, setRawSearch] = useState('')
  const [wrapRawOutput, setWrapRawOutput] = useState(true)
  const [copiedRawOutput, setCopiedRawOutput] = useState(false)
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [showRescanModal, setShowRescanModal] = useState(false)
  const [rescanning, setRescanning] = useState(false)

  useEffect(() => {
    return () => {
      isMounted.current = false
    }
  }, [])

  useTaskSubscription({
    taskId: taskId!,
    onStatus: (status) => {
      if (!isMounted.current) return
      setTask((prev: Task | null) => prev ? { ...prev, status } : null)
      if (['completed', 'failed', 'cancelled'].includes(status)) {
        loadTask()
      }
    },
    onPhase: (phase) => {
      if (!isMounted.current) return
      setScanPhase(phase)
    },
    onOutput: (chunk) => {
      if (!isMounted.current) return
      setRawOutput((prev) => prev + chunk)
    },
  })

  async function loadTask() {
    const seq = ++loadTaskSeqRef.current
    if (!isMounted.current) return
    
    try {
      setError(null)
      const [statusData, resultData] = await Promise.all([
        getTaskStatus(taskId!) as Promise<Task>,
        getTaskResult(taskId!).catch(() => null) as Promise<TaskResult | null>
      ])
      
      if (seq !== loadTaskSeqRef.current || !isMounted.current) return
      
      setTask(statusData)
      if (statusData.scan_phase) {
        setScanPhase(statusData.scan_phase)
      }
      
      getPluginSchema(statusData.plugin_id)
        .then(schema => isMounted.current && setSchema(schema))
        .catch(() => isMounted.current && setSchema(null))
      
      if (resultData && isMounted.current) {
        setResult(resultData)
        if (resultData.raw_output) {
          setRawOutput(resultData.raw_output)
        }
      }
    } catch (err) {
      if (isMounted.current && seq === loadTaskSeqRef.current) {
        console.error('Failed to load task:', err)
        setError(err instanceof Error ? err.message : 'Failed to load task')
      }
    } finally {
      if (isMounted.current && seq === loadTaskSeqRef.current) {
        setLoading(false)
      }
    }
  }

  const handleCopyTaskId = async () => {
    if (!task) return
    try {
      await navigator.clipboard.writeText(task.task_id)
      addToast('Task ID copied successfully', 'success')
    } catch (err) {
      console.error('Failed to copy task ID:', err)
      addToast('Unable to copy Task ID', 'error')
    }
  }

  const handleRescan = async () => {
    if (!task) return
    try {
      setRescanning(true)
      const res = await startTask(
        task.plugin_id,
        task.inputs || {},
        true,
        task.preset
      )
      if (res.task_id) {
        addToast('Scan started successfully', 'success')
        navigate(routePath.task(res.task_id))
      }
    } catch (err) {
      console.error('Rescan failed:', err)
      addToast('Failed to start scan', 'error')
    } finally {
      setRescanning(false)
      setShowRescanModal(false)
    }
  }

  const handleCancel = async () => {
    if (!task) return
    try {
      await cancelTask(task.task_id)
      addToast('Task cancelled successfully', 'success')
      loadTask()
    } catch (err) {
      console.error('Failed to cancel task:', err)
      addToast('Failed to cancel task', 'error')
    } finally {
      setShowCancelModal(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-12">
        <div className="space-y-4 text-center">
          <div className="w-20 h-20 border-8 border-silver-bright/10 border-t-rag-blue animate-spin mx-auto shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"></div>
          <p className="text-xs font-black text-silver-bright/40 uppercase tracking-[0.4em] italic">Loading_Operation</p>
        </div>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-12">
        <div className="max-w-md w-full bg-charcoal border-4 border-black p-8 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] text-center space-y-6">
          <div className="w-16 h-16 mx-auto bg-rag-red/20 flex items-center justify-center border-2 border-rag-red">
            <span className="material-symbols-outlined text-4xl text-rag-red">error</span>
          </div>
          <p className="text-xs font-black text-rag-red uppercase tracking-[0.4em] italic">Task_Load_Failed</p>
          <p className="text-sm text-silver-bright font-mono break-words">{error || 'Task not found'}</p>
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
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      {/* Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <div className="bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Task_Deep_Inspection
          </div>
          <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
            Task_{task.task_id.split('-')[0].toUpperCase()}
          </h1>
          <div className="flex flex-wrap items-center gap-4">
            <span className={`px-2 py-0.5 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
              task.status === 'completed' ? 'bg-rag-green text-black' :
              task.status === 'failed' ? 'bg-rag-red text-black' :
              task.status === 'running' ? 'bg-rag-amber text-black' :
              'bg-charcoal-dark text-silver-bright/50'
            }`}>
              {task.status}
            </span>
            {task.scan_phase && (
              <span className="text-[9px] font-mono text-rag-blue/80 uppercase tracking-widest">
                Phase: {task.scan_phase.replace(/_/g, ' ')}
              </span>
            )}
            <button
              onClick={handleCopyTaskId}
              className="text-[10px] font-mono text-silver/40 hover:text-silver-bright transition-colors flex items-center gap-2"
            >
              ID: {task.task_id.slice(0, 8)}...
              <span className="material-symbols-outlined text-sm">content_copy</span>
            </button>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {task.status === 'running' && (
            <button
              onClick={() => setShowCancelModal(true)}
              className="bg-rag-red/20 text-rag-red border-2 border-rag-red/20 hover:bg-rag-red hover:text-black hover:border-black px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2 italic"
            >
              Cancel_Operation
              <span className="material-symbols-outlined text-sm">stop</span>
            </button>
          )}
          {(task.status === 'completed' || task.status === 'failed') && (
            <button
              onClick={() => setShowRescanModal(true)}
              className="bg-rag-blue text-black px-6 py-3 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-2 italic"
            >
              Rescan_Signal
              <span className="material-symbols-outlined text-sm">replay</span>
            </button>
          )}
          <button
            onClick={() => navigate(routePath.scans)}
            className="bg-silver-bright text-black px-6 py-3 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-2 italic"
          >
            Back_To_Registry
            <span className="material-symbols-outlined text-sm">arrow_back</span>
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b-4 border-silver-bright/10 pb-4">
        {(['summary', 'results', 'parameters', 'raw'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 ${
              activeTab === tab
                ? 'bg-silver-bright text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] -translate-x-0.5 -translate-y-0.5'
                : 'bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20'
            }`}
          >
            {tab === 'summary' && 'Summary_Report'}
            {tab === 'results' && 'Finding_Logs'}
            {tab === 'parameters' && 'Config_Parameters'}
            {tab === 'raw' && 'Raw_Stream'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
        {activeTab === 'summary' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div>
                <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-2 italic">Target</p>
                <p className="text-sm font-mono text-silver-bright">{task.target}</p>
              </div>
              <div>
                <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-2 italic">Plugin</p>
                <p className="text-sm font-mono text-silver-bright">{task.plugin_id}</p>
              </div>
              <div>
                <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-2 italic">Tool</p>
                <p className="text-sm font-mono text-silver-bright">{task.tool}</p>
              </div>
            </div>
            {result?.summary && (
              <div className="border-t-4 border-black pt-8">
                <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] mb-4 italic">Execution_Summary</p>
                <pre className="text-xs font-mono text-silver-bright/70 whitespace-pre-wrap">
                  {JSON.stringify(result.summary, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div className="space-y-4">
            {result?.findings && result.findings.length > 0 ? (
              result.findings.map((finding: any, idx: number) => (
                <div key={idx} className="border-2 border-silver-bright/10 p-4 hover:border-rag-blue/40 transition-all">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-xs font-black uppercase">{finding.title || 'Finding'}</p>
                      <p className="text-[10px] font-mono text-silver/40 mt-1">{finding.description}</p>
                    </div>
                    <span className={`px-2 py-0.5 text-[8px] font-black uppercase border border-black ${
                      finding.severity === 'critical' ? 'bg-rag-red text-black' :
                      finding.severity === 'high' ? 'bg-rag-red/80 text-black' :
                      finding.severity === 'medium' ? 'bg-rag-amber text-black' :
                      'bg-silver-bright text-black'
                    }`}>
                      {finding.severity || 'info'}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-12">
                <span className="material-symbols-outlined text-5xl text-silver/10">verified</span>
                <p className="text-xs font-mono text-silver/20 uppercase tracking-widest mt-4">No findings detected</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'parameters' && (
          <div className="space-y-4">
            <pre className="text-xs font-mono text-silver-bright/70 whitespace-pre-wrap bg-charcoal-dark p-4 border-2 border-silver-bright/10">
              {JSON.stringify(task.inputs || {}, null, 2)}
            </pre>
          </div>
        )}

        {activeTab === 'raw' && (
          <div className="space-y-4">
            <div className="flex justify-end gap-4 mb-4">
              <button
                onClick={() => setWrapRawOutput(!wrapRawOutput)}
                className="text-[8px] font-black uppercase tracking-widest text-silver/40 hover:text-silver-bright transition-colors"
              >
                {wrapRawOutput ? 'Wrap: ON' : 'Wrap: OFF'}
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(rawOutput)
                  setCopiedRawOutput(true)
                  setTimeout(() => setCopiedRawOutput(false), 2000)
                }}
                className="text-[8px] font-black uppercase tracking-widest text-silver/40 hover:text-silver-bright transition-colors"
              >
                {copiedRawOutput ? 'Copied!' : 'Copy_All'}
              </button>
            </div>
            <div className="relative">
              <input
                type="text"
                placeholder="Filter raw output..."
                value={rawSearch}
                onChange={(e) => setRawSearch(e.target.value)}
                className="w-full bg-charcoal-dark border-2 border-silver-bright/10 px-4 py-2 text-xs font-mono text-silver-bright placeholder:text-silver/20 focus:border-rag-blue focus:outline-none mb-4"
              />
              <pre className={`text-xs font-mono text-silver-bright/70 bg-charcoal-dark p-4 border-2 border-silver-bright/10 overflow-auto max-h-[600px] ${wrapRawOutput ? 'whitespace-pre-wrap' : 'whitespace-pre'}`}>
                {rawSearch ? rawOutput.split('\n').filter(line => line.includes(rawSearch)).join('\n') : rawOutput || 'No output yet...'}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Cancel Modal */}
      <ConfirmModal
        isOpen={showCancelModal}
        title="Cancel Operation"
        message="Are you sure you want to cancel this running scan? This action cannot be undone."
        onConfirm={handleCancel}
        onCancel={() => setShowCancelModal(false)}
        confirmText="Yes, Cancel"
        cancelText="No, Keep Running"
        type="danger"
      />

      {/* Rescan Modal */}
      <ConfirmModal
        isOpen={showRescanModal}
        title="Rescan Confirmation"
        message="Are you sure you want to run this scan again with the same parameters?"
        onConfirm={handleRescan}
        onCancel={() => setShowRescanModal(false)}
        confirmText="Yes, Rescan"
        cancelText="No, Cancel"
        type="warning"
      />
    </div>
  )
}
