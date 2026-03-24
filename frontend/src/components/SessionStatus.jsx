import { useState } from 'react'

export default function SessionStatus() {
  const [sessionInfo] = useState({
    user: 'admin',
    sessionId: 'sess_2025_0103_0327_alpha',
    loginTime: new Date(),
    sessionDuration: '2h 14m',
    securityLevel: 'HIGH',
    isActive: true
  })

  const formatDuration = (loginTime) => {
    const now = new Date()
    const diff = Math.floor((now - loginTime) / 1000)
    
    if (diff < 60) return `${diff}s`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
    return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
  }

  const getSecurityLevelColor = (level) => {
    switch(level) {
      case 'HIGH': return '#ef4444'
      case 'MEDIUM': return '#f59e0b'
      case 'LOW': return '#10b981'
      default: return '#6b7280'
    }
  }

  return (
    <div className="session-status-bar">
      {/* Session Status */}
      <div className="session-info">
        <div className="user-info">
          <span className="user-label">USER:</span>
          <span className="user-name">{sessionInfo.user.toUpperCase()}</span>
        </div>
        
        <div className="session-details">
          <span className="session-id">ID: {sessionInfo.sessionId}</span>
          <span className="session-duration">
            DURATION: {formatDuration(sessionInfo.loginTime)}
          </span>
        </div>
      </div>

      {/* Security Status */}
      <div className="security-status">
        <div className="status-indicators">
          <div className="indicator-item">
            <div className={`status-light ${sessionInfo.isActive ? 'active' : 'inactive'}`}></div>
            <span className="indicator-label">
              {sessionInfo.isActive ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>
          
          <div className="indicator-item">
            <div className="security-light" style={{ backgroundColor: getSecurityLevelColor(sessionInfo.securityLevel) }}></div>
            <span className="indicator-label" style={{ color: getSecurityLevelColor(sessionInfo.securityLevel) }}>
              {sessionInfo.securityLevel} SECURITY
            </span>
          </div>
        </div>

        {/* Session Actions */}
        <div className="session-actions">
          <button className="action-button lock">
            <span className="button-icon">🔒</span>
            <span className="button-text">LOCK</span>
          </button>
          
          <button className="action-button logout">
            <span className="button-icon">🚪</span>
            <span className="button-text">LOGOUT</span>
          </button>
        </div>
      </div>

      <style jsx>{`
        .session-status-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 20px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border-bottom: 1px solid #333;
          font-family: 'Courier New', monospace;
          font-size: 11px;
        }

        /* Session Info */
        .session-info {
          display: flex;
          align-items: center;
          gap: 24px;
        }

        .user-info {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .user-label {
          color: #888;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .user-name {
          color: #00ff41;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .session-details {
          display: flex;
          gap: 16px;
          color: #666;
        }

        .session-id, .session-duration {
          font-family: monospace;
        }

        /* Security Status */
        .security-status {
          display: flex;
          align-items: center;
          gap: 24px;
        }

        .status-indicators {
          display: flex;
          gap: 16px;
        }

        .indicator-item {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .status-light {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          border: 1px solid #555;
        }

        .status-light.active {
          background: #00ff41;
          border-color: #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }

        .status-light.inactive {
          background: #333;
          border-color: #555;
        }

        .security-light {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          border: 1px solid currentColor;
          box-shadow: 0 0 10px currentColor;
        }

        .indicator-label {
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #888;
        }

        /* Session Actions */
        .session-actions {
          display: flex;
          gap: 8px;
        }

        .action-button {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #888;
          font-size: 10px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .action-button:hover {
          background: #2a2a2a;
          border-color: #555;
          color: #e5e5e5;
        }

        .action-button.lock:hover {
          border-color: #f59e0b;
          color: #f59e0b;
          box-shadow: 0 0 10px rgba(243, 156, 18, 0.2);
        }

        .action-button.logout:hover {
          border-color: #ef4444;
          color: #ef4444;
          box-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
        }

        .button-icon {
          font-size: 12px;
        }

        .button-text {
          font-size: 10px;
        }

        /* Responsive */
        @media (max-width: 768px) {
          .session-status-bar {
            flex-direction: column;
            gap: 8px;
            padding: 12px 16px;
          }

          .session-info {
            flex-wrap: wrap;
            gap: 12px;
          }

          .security-status {
            flex-wrap: wrap;
            gap: 12px;
            justify-content: space-between;
            width: 100%;
          }

          .session-details {
            flex-wrap: wrap;
            gap: 8px;
          }
        }

        @media (max-width: 480px) {
          .status-indicators {
            flex-direction: column;
            gap: 8px;
            align-items: flex-start;
          }

          .session-actions {
            width: 100%;
            justify-content: flex-end;
          }
        }
      `}</style>
    </div>
  )
}
