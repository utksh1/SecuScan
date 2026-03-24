import { useState } from 'react'
import LoginScreen from '../components/LoginScreen'
import SessionStatus from '../components/SessionStatus'

export default function AuthDemo() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  const handleLogin = () => {
    // Simulate successful login
    setTimeout(() => setIsLoggedIn(true), 2000)
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
  }

  const handleLock = () => {
    alert('Session locked - would show login screen again')
  }

  if (!isLoggedIn) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <div className="auth-demo-container">
      {/* Session Status Bar */}
      <SessionStatus onLogout={handleLogout} onLock={handleLock} />
      
      {/* Main Content */}
      <div className="demo-content">
        <div className="welcome-panel">
          <h1 className="welcome-title">CONSOLE UNLOCKED</h1>
          <p className="welcome-subtitle">
            Welcome to the SecuScan Security Console
          </p>
          
          <div className="feature-grid">
            <div className="feature-card">
              <div className="feature-icon">🔍</div>
              <h3 className="feature-title">SCAN MODULES</h3>
              <p className="feature-description">
                Access and configure security scanning tools
              </p>
            </div>
            
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3 className="feature-title">TASK MONITOR</h3>
              <p className="feature-description">
                Monitor running scans and view results
              </p>
            </div>
            
            <div className="feature-card">
              <div className="feature-icon">⚙️</div>
              <h3 className="feature-title">SYSTEM CONFIG</h3>
              <p className="feature-description">
                Configure system settings and preferences
              </p>
            </div>
            
            <div className="feature-card">
              <div className="feature-icon">🛡️</div>
              <h3 className="feature-title">SECURITY LOGS</h3>
              <p className="feature-description">
                View system security logs and audit trails
              </p>
            </div>
          </div>
          
          <div className="demo-actions">
            <button className="demo-button primary" onClick={() => window.location.href = '/scanner'}>
              LAUNCH SCANNER
            </button>
            <button className="demo-button secondary" onClick={handleLock}>
              LOCK SESSION
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        .auth-demo-container {
          min-height: 100vh;
          background: #0a0a0a;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
        }

        .demo-content {
          padding: 40px 20px;
          max-width: 1200px;
          margin: 0 auto;
        }

        .welcome-panel {
          text-align: center;
          margin-bottom: 60px;
        }

        .welcome-title {
          font-size: 32px;
          color: #00ff41;
          text-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
          margin: 0 0 16px 0;
          text-transform: uppercase;
          letter-spacing: 3px;
        }

        .welcome-subtitle {
          font-size: 16px;
          color: #888;
          margin: 0 0 60px 0;
        }

        .feature-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 24px;
          margin-bottom: 60px;
        }

        .feature-card {
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 1px solid #333;
          border-radius: 8px;
          padding: 32px 24px;
          text-align: center;
          transition: all 0.3s ease;
        }

        .feature-card:hover {
          border-color: #00ff41;
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.2);
          transform: translateY(-4px);
        }

        .feature-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }

        .feature-title {
          font-size: 16px;
          color: #00ff41;
          margin: 0 0 12px 0;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .feature-description {
          font-size: 12px;
          color: #888;
          line-height: 1.4;
          margin: 0;
        }

        .demo-actions {
          display: flex;
          justify-content: center;
          gap: 16px;
          flex-wrap: wrap;
        }

        .demo-button {
          padding: 12px 32px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 2px solid #333;
          border-radius: 6px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 2px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .demo-button.primary {
          border-color: #00ff41;
          color: #00ff41;
        }

        .demo-button.primary:hover {
          background: #0f4c0f;
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
        }

        .demo-button.secondary {
          border-color: #f59e0b;
          color: #f59e0b;
        }

        .demo-button.secondary:hover {
          background: #2a1f0f;
          box-shadow: 0 0 20px rgba(243, 156, 18, 0.3);
        }

        @media (max-width: 768px) {
          .welcome-title {
            font-size: 24px;
          }

          .feature-grid {
            grid-template-columns: 1fr;
          }

          .demo-actions {
            flex-direction: column;
            align-items: center;
          }

          .demo-button {
            width: 200px;
          }
        }
      `}</style>
    </div>
  )
}
