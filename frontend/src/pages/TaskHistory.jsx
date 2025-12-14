import { useState, useEffect } from 'react'
import { api } from '../services/api'
import TaskCard from '../components/TaskCard'

export default function TaskHistory() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    loadTasks()
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(loadTasks, 5000)
    return () => clearInterval(interval)
  }, [filter])

  async function loadTasks() {
    try {
      const params = {}
      if (filter !== 'all') {
        params.status = filter
      }
      
      const data = await api.getTasks(params)
      setTasks(data.tasks || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ margin: 0 }}>Task History</h1>
        <button className="btn" onClick={loadTasks}>
          🔄 Refresh
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ marginRight: '12px' }}>Filter by status:</label>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {loading && tasks.length === 0 && <p>Loading tasks...</p>}
      
      {error && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fca5a5',
          borderRadius: '6px',
          padding: '12px',
          color: '#991b1b',
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && tasks.length === 0 && (
        <p style={{ color: '#6b7280' }}>No tasks found. Start a scan to see results here.</p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '16px' }}>
        {tasks.map(task => (
          <TaskCard key={task.task_id} task={task} />
        ))}
      </div>
    </div>
  )
}
