import { Link } from 'react-router-dom'

const statusColors = {
  pending: '#f59e0b',
  running: '#3b82f6',
  completed: '#10b981',
  failed: '#ef4444',
  cancelled: '#6b7280',
}

export default function TaskCard({ task }) {
  const statusColor = statusColors[task.status] || '#6b7280'
  
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '16px' }}>{task.plugin_name}</h3>
          <p style={{ margin: 0, fontSize: '12px', color: '#6b7280' }}>
            Task ID: {task.task_id}
          </p>
        </div>
        <span style={{
          padding: '4px 8px',
          borderRadius: '12px',
          fontSize: '11px',
          fontWeight: '600',
          color: 'white',
          background: statusColor,
        }}>
          {task.status.toUpperCase()}
        </span>
      </div>
      
      <div style={{ fontSize: '14px', marginBottom: '8px' }}>
        <p style={{ margin: '4px 0' }}>
          <strong>Preset:</strong> {task.preset}
        </p>
        <p style={{ margin: '4px 0', fontSize: '12px', color: '#6b7280' }}>
          Created: {new Date(task.created_at).toLocaleString()}
        </p>
        {task.finished_at && (
          <p style={{ margin: '4px 0', fontSize: '12px', color: '#6b7280' }}>
            Finished: {new Date(task.finished_at).toLocaleString()}
          </p>
        )}
      </div>
      
      <Link to={`/task/${task.task_id}`}>
        <button className="btn" style={{ width: '100%' }}>
          View Details
        </button>
      </Link>
    </div>
  )
}
