import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function TaskDetails() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [liveLogs, setLiveLogs] = useState([])
  const logContainerRef = useRef(null)

  useEffect(() => {
    loadTask()
    
    // Auto-refresh while task is running
    const interval = setInterval(() => {
      if (task?.status === 'running' || task?.status === 'queued') {
        loadTask()
      }
    }, 2000)
    
    return () => clearInterval(interval)
  }, [taskId, task?.status])

  useEffect(() => {
    // Auto-scroll logs to bottom
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [liveLogs])

  async function loadTask() {
    try {
      const [statusData, resultData] = await Promise.all([
        api.getTaskStatus(taskId),
        api.getTaskResult(taskId).catch(() => ({ output: '', result: null })),
      ])
      
      const updatedTask = {
        ...statusData,
        output: resultData.output || '',
        result: resultData.result,
      }
      
      setTask(updatedTask)
      
      // Update live logs if new output
      if (resultData.output && resultData.output !== (task?.output || '')) {
        const newLines = resultData.output.split('\n').slice(liveLogs.length)
        if (newLines.length > 0) {
          setLiveLogs(prev => [...prev, ...newLines])
        }
      }
      
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleCancel() {
    if (!confirm('Are you sure you want to cancel this task?')) return
    
    try {
      await api.cancelTask(taskId)
      loadTask()
    } catch (err) {
      alert(`Failed to cancel task: ${err.message}`)
    }
  }

  async function handleDelete() {
    if (!confirm('Are you sure you want to delete this task? This cannot be undone.')) return
    
    try {
      await api.deleteTask(taskId)
      navigate('/history')
    } catch (err) {
      alert(`Failed to delete task: ${err.message}`)
    }
  }

  const getStatusInfo = (status) => {
    switch(status) {
      case 'queued': return { color: '#6b7280', label: 'QUEUED', icon: '⏳' }
      case 'running': return { color: '#3b82f6', label: 'RUNNING', icon: '▶️' }
      case 'completed': return { color: '#10b981', label: 'COMPLETED', icon: '✅' }
      case 'failed': return { color: '#ef4444', label: 'FAILED', icon: '❌' }
      case 'cancelled': return { color: '#f59e0b', label: 'CANCELLED', icon: '⏹️' }
      default: return { color: '#6b7280', label: 'UNKNOWN', icon: '❓' }
    }
  }

  const formatDuration = (started, finished) => {
    if (!started) return 'N/A'
    const start = new Date(started)
    const end = finished ? new Date(finished) : new Date()
    const duration = Math.floor((end - start) / 1000)
    
    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`
  }

  if (loading) {
    return (
      <div className="task-execution-container">
        <div className="loading-panel">
          <div className="loading-header">
            <h1 className="loading-title">INITIALIZING TASK MONITOR</h1>
            <div className="status-indicator loading">LOADING</div>
          </div>
          <div className="loading-content">
            <div className="loading-bars">
              <div></div>
              <div></div>
              <div></div>
            </div>
            <p>Retrieving task data...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="task-execution-container">
        <div className="error-panel">
          <div className="error-header">
            <h1 className="error-title">TASK ERROR</h1>
            <div className="status-indicator error">ERROR</div>
          </div>
          <div className="error-content">
            <div className="error-code">TASK_ERR_001</div>
            <div className="error-message">{error}</div>
            <button className="system-button" onClick={() => navigate('/history')}>
              RETURN TO HISTORY
            </button>
          </div>
        </div>
      </div>
    )
  }

  const statusInfo = getStatusInfo(task.status)

  return (
    <div className="task-execution-container">
      {/* Main Task Panel */}
      <div className="task-main-panel">
        {/* Task Header */}
        <div className="task-header">
          <div className="task-info">
            <h1 className="task-title">{task.plugin_name || 'UNKNOWN TASK'}</h1>
            <div className="task-meta">
              <span className="task-id">ID: {taskId}</span>
              <span className="task-preset">PRESET: {task.preset || 'DEFAULT'}</span>
            </div>
          </div>
          
          <div className="task-controls">
            <div className={`status-indicator ${task.status}`}>
              <span className="status-icon">{statusInfo.icon}</span>
              <span className="status-text">{statusInfo.label}</span>
            </div>
            
            <div className="control-buttons">
              {(task.status === 'running' || task.status === 'queued') && (
                <button className="control-button cancel" onClick={handleCancel}>
                  CANCEL
                </button>
              )}
              {(task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') && (
                <button className="control-button delete" onClick={handleDelete}>
                  DELETE
                </button>
              )}
              <button className="control-button details" onClick={() => setIsPanelOpen(true)}>
                DETAILS
              </button>
              <button className="control-button back" onClick={() => navigate('/history')}>
                BACK
              </button>
            </div>
          </div>
        </div>

        {/* Execution Timeline */}
        <div className="execution-timeline">
          <h3 className="timeline-title">EXECUTION TIMELINE</h3>
          <div className="timeline-events">
            <div className="timeline-event created">
              <div className="event-dot"></div>
              <div className="event-content">
                <span className="event-time">{new Date(task.created_at).toLocaleTimeString()}</span>
                <span className="event-label">Task Created</span>
              </div>
            </div>
            
            {task.started_at && (
              <div className="timeline-event started">
                <div className="event-dot"></div>
                <div className="event-content">
                  <span className="event-time">{new Date(task.started_at).toLocaleTimeString()}</span>
                  <span className="event-label">Execution Started</span>
                </div>
              </div>
            )}
            
            {task.finished_at && (
              <div className="timeline-event finished">
                <div className="event-dot"></div>
                <div className="event-content">
                  <span className="event-time">{new Date(task.finished_at).toLocaleTimeString()}</span>
                  <span className="event-label">Execution {task.status === 'completed' ? 'Completed' : 'Terminated'}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Live Terminal Output */}
        <div className="terminal-panel">
          <div className="terminal-header">
            <h3 className="terminal-title">LIVE OUTPUT</h3>
            <div className="terminal-controls">
              <div className="terminal-status">
                <div className={`status-light ${task.status === 'running' ? 'active' : ''}`}></div>
                <span>{task.status === 'running' ? 'LIVE' : 'STATIC'}</span>
              </div>
              <button className="terminal-button" onClick={() => setLiveLogs([])}>
                CLEAR
              </button>
            </div>
          </div>
          
          <div className="terminal-content" ref={logContainerRef}>
            {liveLogs.length === 0 && !task.output ? (
              <div className="terminal-placeholder">
                <span className="placeholder-text">Awaiting output...</span>
              </div>
            ) : (
              <>
                {liveLogs.map((log, index) => (
                  <div key={index} className="terminal-line">
                    <span className="line-timestamp">
                      [{new Date().toLocaleTimeString()}]
                    </span>
                    <span className="line-content">{log}</span>
                  </div>
                ))}
                {task.output && liveLogs.length === 0 && task.output.split('\n').map((line, index) => (
                  <div key={index} className="terminal-line">
                    <span className="line-content">{line}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Slide-over Details Panel */}
      <div className={`slide-over-panel ${isPanelOpen ? 'open' : ''}`}>
        <div className="panel-overlay" onClick={() => setIsPanelOpen(false)}></div>
        <div className="panel-content">
          <div className="panel-header">
            <h2 className="panel-title">TASK DETAILS</h2>
            <button className="panel-close" onClick={() => setIsPanelOpen(false)}>
              ✕
            </button>
          </div>
          
          <div className="panel-body">
            {/* Task Information */}
            <div className="detail-section">
              <h3 className="section-title">TASK INFORMATION</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">TASK ID</span>
                  <span className="detail-value">{taskId}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">PLUGIN</span>
                  <span className="detail-value">{task.plugin_name}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">STATUS</span>
                  <span className="detail-value" style={{ color: statusInfo.color }}>
                    {statusInfo.label}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">PRESET</span>
                  <span className="detail-value">{task.preset || 'DEFAULT'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">DURATION</span>
                  <span className="detail-value">
                    {formatDuration(task.started_at, task.finished_at)}
                  </span>
                </div>
                {task.exit_code !== null && task.exit_code !== undefined && (
                  <div className="detail-item">
                    <span className="detail-label">EXIT CODE</span>
                    <span className="detail-value">{task.exit_code}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Timeline Details */}
            <div className="detail-section">
              <h3 className="section-title">EXECUTION DETAILS</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">CREATED</span>
                  <span className="detail-value">
                    {new Date(task.created_at).toLocaleString()}
                  </span>
                </div>
                {task.started_at && (
                  <div className="detail-item">
                    <span className="detail-label">STARTED</span>
                    <span className="detail-value">
                      {new Date(task.started_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {task.finished_at && (
                  <div className="detail-item">
                    <span className="detail-label">FINISHED</span>
                    <span className="detail-value">
                      {new Date(task.finished_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Parsed Results */}
            {task.result && (
              <div className="detail-section">
                <h3 className="section-title">PARSED RESULTS</h3>
                <div className="result-panel">
                  <pre className="result-content">
                    {JSON.stringify(task.result, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Task Inputs */}
            {task.inputs && (
              <div className="detail-section">
                <h3 className="section-title">TASK INPUTS</h3>
                <div className="result-panel">
                  <pre className="result-content">
                    {JSON.stringify(task.inputs, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        .task-execution-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #0a0a0a;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          overflow: hidden;
        }

        /* Loading Panel */
        .loading-panel, .error-panel {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #1a1a1a;
          border: 1px solid #333;
        }

        .loading-header, .error-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          background: #0d0d0d;
          border-bottom: 1px solid #333;
        }

        .loading-title, .error-title {
          margin: 0;
          font-size: 20px;
          color: #00ff41;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          font-size: 11px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          border-radius: 4px;
        }

        .status-indicator.loading {
          background: #1a1a2e;
          color: #f39c12;
          border: 1px solid #f39c12;
        }

        .status-indicator.error {
          background: #2c0f0f;
          color: #ff4444;
          border: 1px solid #ff4444;
        }

        .loading-content, .error-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          flex: 1;
          gap: 20px;
        }

        .loading-bars {
          display: flex;
          gap: 4px;
        }

        .loading-bars div {
          width: 4px;
          height: 20px;
          background: #f39c12;
          animation: loading-bars 1.5s infinite ease-in-out;
        }

        .loading-bars div:nth-child(1) { animation-delay: 0s; }
        .loading-bars div:nth-child(2) { animation-delay: 0.2s; }
        .loading-bars div:nth-child(3) { animation-delay: 0.4s; }

        .error-code {
          color: #ff4444;
          font-size: 12px;
          margin-bottom: 8px;
        }

        .error-message {
          color: #ff8888;
          margin-bottom: 20px;
          text-align: center;
        }

        /* Main Task Panel */
        .task-main-panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          overflow: hidden;
        }

        .task-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 1px solid #333;
          border-bottom: 2px solid #333;
        }

        .task-info h1 {
          margin: 0;
          font-size: 24px;
          color: #00ff41;
          text-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }

        .task-meta {
          display: flex;
          gap: 20px;
          margin-top: 4px;
        }

        .task-id, .task-preset {
          font-size: 12px;
          color: #888;
          font-family: monospace;
        }

        .task-controls {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .status-indicator.queued {
          background: #1a1a1a;
          color: #6b7280;
          border: 1px solid #6b7280;
        }

        .status-indicator.running {
          background: #1e3a8a;
          color: #3b82f6;
          border: 1px solid #3b82f6;
          box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
        }

        .status-indicator.completed {
          background: #0f4c0f;
          color: #10b981;
          border: 1px solid #10b981;
          box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
        }

        .status-indicator.failed {
          background: #2c0f0f;
          color: #ef4444;
          border: 1px solid #ef4444;
        }

        .status-indicator.cancelled {
          background: #2a1f0f;
          color: #f59e0b;
          border: 1px solid #f59e0b;
        }

        .status-icon {
          font-size: 14px;
        }

        .control-buttons {
          display: flex;
          gap: 8px;
        }

        .control-button {
          padding: 8px 16px;
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-size: 11px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .control-button:hover {
          background: #2a2a2a;
          border-color: #555;
        }

        .control-button.cancel {
          border-color: #ef4444;
          color: #ef4444;
        }

        .control-button.cancel:hover {
          background: #2c0f0f;
        }

        .control-button.delete {
          border-color: #ef4444;
          color: #ef4444;
        }

        .control-button.delete:hover {
          background: #2c0f0f;
        }

        .control-button.details {
          border-color: #00ff41;
          color: #00ff41;
        }

        .control-button.details:hover {
          background: #0f4c0f;
        }

        /* Execution Timeline */
        .execution-timeline {
          padding: 20px;
          background: #1a1a1a;
          border: 1px solid #333;
          border-top: none;
        }

        .timeline-title {
          margin: 0 0 16px 0;
          font-size: 14px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .timeline-events {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .timeline-event {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .event-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #333;
        }

        .timeline-event.created .event-dot {
          background: #6b7280;
        }

        .timeline-event.started .event-dot {
          background: #3b82f6;
          box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
        }

        .timeline-event.finished .event-dot {
          background: #10b981;
          box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
        }

        .event-content {
          display: flex;
          gap: 12px;
          font-size: 12px;
        }

        .event-time {
          color: #888;
          min-width: 80px;
        }

        .event-label {
          color: #e5e5e5;
        }

        /* Terminal Panel */
        .terminal-panel {
          flex: 1;
          display: flex;
          flex-direction: column;
          background: #0d0d0d;
          border: 1px solid #333;
          border-top: none;
          overflow: hidden;
        }

        .terminal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          background: #0a0a0a;
          border-bottom: 1px solid #333;
        }

        .terminal-title {
          margin: 0;
          font-size: 14px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .terminal-controls {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .terminal-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          color: #888;
        }

        .status-light {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #333;
          border: 1px solid #555;
        }

        .status-light.active {
          background: #00ff41;
          border-color: #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }

        .terminal-button {
          padding: 4px 12px;
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 3px;
          color: #888;
          font-size: 10px;
          text-transform: uppercase;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .terminal-button:hover {
          background: #2a2a2a;
          border-color: #555;
          color: #e5e5e5;
        }

        .terminal-content {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          font-family: 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.4;
        }

        .terminal-placeholder {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100%;
          color: #666;
          font-style: italic;
        }

        .terminal-line {
          display: flex;
          gap: 12px;
          margin-bottom: 4px;
          white-space: pre-wrap;
          word-break: break-all;
        }

        .line-timestamp {
          color: #666;
          font-size: 11px;
          min-width: 80px;
        }

        .line-content {
          color: #e5e5e5;
        }

        /* Slide-over Panel */
        .slide-over-panel {
          position: fixed;
          top: 0;
          right: 0;
          bottom: 0;
          width: 600px;
          background: #1a1a1a;
          border-left: 1px solid #333;
          transform: translateX(100%);
          transition: transform 0.3s ease;
          z-index: 1000;
        }

        .slide-over-panel.open {
          transform: translateX(0);
        }

        .panel-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          opacity: 0;
          visibility: hidden;
          transition: opacity 0.3s ease, visibility 0.3s ease;
          z-index: 999;
        }

        .slide-over-panel.open .panel-overlay {
          opacity: 1;
          visibility: visible;
        }

        .panel-content {
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          background: #0d0d0d;
          border-bottom: 1px solid #333;
        }

        .panel-title {
          margin: 0;
          font-size: 16px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .panel-close {
          background: none;
          border: none;
          color: #888;
          font-size: 20px;
          cursor: pointer;
          padding: 4px;
          transition: color 0.3s ease;
        }

        .panel-close:hover {
          color: #e5e5e5;
        }

        .panel-body {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
        }

        .detail-section {
          margin-bottom: 32px;
        }

        .section-title {
          margin: 0 0 16px 0;
          font-size: 12px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: 120px 1fr;
          gap: 12px;
        }

        .detail-item {
          display: contents;
        }

        .detail-label {
          color: #888;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .detail-value {
          color: #e5e5e5;
          font-size: 12px;
          font-family: monospace;
        }

        .result-panel {
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          overflow: hidden;
        }

        .result-content {
          margin: 0;
          padding: 16px;
          background: #0d0d0d;
          color: #e5e5e5;
          font-size: 11px;
          line-height: 1.4;
          overflow: auto;
          max-height: 300px;
        }

        .system-button {
          padding: 10px 20px;
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          text-transform: uppercase;
          letter-spacing: 1px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .system-button:hover {
          background: #2a2a2a;
          border-color: #555;
        }

        /* Animations */
        @keyframes loading-bars {
          0%, 40%, 100% { transform: scaleY(0.4); }
          20% { transform: scaleY(1); }
        }

        /* Responsive */
        @media (max-width: 768px) {
          .task-header {
            flex-direction: column;
            gap: 16px;
            text-align: center;
          }

          .slide-over-panel {
            width: 100%;
          }

          .control-buttons {
            flex-wrap: wrap;
            justify-content: center;
          }
        }
      `}</style>
    </div>
  )
}
