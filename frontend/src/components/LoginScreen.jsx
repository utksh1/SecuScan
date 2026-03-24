import { useState } from 'react'

export default function LoginScreen() {
  const [credentials, setCredentials] = useState({
    username: '',
    password: '',
    access_code: ''
  })
  const [isUnlocking, setIsUnlocking] = useState(false)
  const [authMethod, setAuthMethod] = useState('credentials')

  const handleInputChange = (field, value) => {
    setCredentials(prev => ({ ...prev, [field]: value }))
  }

  const handleUnlock = (e) => {
    e.preventDefault()
    setIsUnlocking(true)
    // Simulate authentication process
    setTimeout(() => setIsUnlocking(false), 2000)
  }

  return (
    <div className="auth-container">
      {/* Background Grid Effect */}
      <div className="grid-background">
        <div className="grid-lines horizontal"></div>
        <div className="grid-lines vertical"></div>
      </div>

      {/* Main Login Panel */}
      <div className="login-panel">
        {/* System Header */}
        <div className="system-header">
          <div className="system-info">
            <h1 className="system-title">SECUSCAN CONSOLE</h1>
            <div className="system-status">
              <span className="status-indicator online">ONLINE</span>
              <span className="system-version">v0.1.0-alpha</span>
            </div>
          </div>
          <div className="security-badge">
            <div className="badge-icon">🔒</div>
            <span className="badge-text">SECURE ACCESS</span>
          </div>
        </div>

        {/* Authentication Form */}
        <div className="auth-form">
          <div className="form-header">
            <h2 className="form-title">SYSTEM AUTHENTICATION</h2>
            <p className="form-subtitle">Enter credentials to access the security console</p>
          </div>

          {/* Auth Method Selector */}
          <div className="auth-method-selector">
            <button 
              className={`method-button ${authMethod === 'credentials' ? 'active' : ''}`}
              onClick={() => setAuthMethod('credentials')}
            >
              CREDENTIALS
            </button>
            <button 
              className={`method-button ${authMethod === 'access_code' ? 'active' : ''}`}
              onClick={() => setAuthMethod('access_code')}
            >
              ACCESS CODE
            </button>
            <button 
              className={`method-button ${authMethod === 'token' ? 'active' : ''}`}
              onClick={() => setAuthMethod('token')}
            >
              SECURITY TOKEN
            </button>
          </div>

          <form onSubmit={handleUnlock}>
            {/* Credentials Mode */}
            {authMethod === 'credentials' && (
              <div className="auth-fields">
                <div className="field-group">
                  <label className="field-label">USERNAME</label>
                  <div className="input-wrapper">
                    <input
                      type="text"
                      value={credentials.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      className="auth-input"
                      placeholder="Enter username..."
                      required
                    />
                    <div className="input-border"></div>
                  </div>
                </div>

                <div className="field-group">
                  <label className="field-label">PASSWORD</label>
                  <div className="input-wrapper">
                    <input
                      type="password"
                      value={credentials.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      className="auth-input"
                      placeholder="Enter password..."
                      required
                    />
                    <div className="input-border"></div>
                  </div>
                </div>
              </div>
            )}

            {/* Access Code Mode */}
            {authMethod === 'access_code' && (
              <div className="auth-fields">
                <div className="field-group">
                  <label className="field-label">ACCESS CODE</label>
                  <div className="input-wrapper">
                    <input
                      type="text"
                      value={credentials.access_code}
                      onChange={(e) => handleInputChange('access_code', e.target.value)}
                      className="auth-input code-input"
                      placeholder="Enter 6-digit code..."
                      maxLength={6}
                      required
                    />
                    <div className="input-border"></div>
                  </div>
                </div>
              </div>
            )}

            {/* Token Mode */}
            {authMethod === 'token' && (
              <div className="auth-fields">
                <div className="field-group">
                  <label className="field-label">SECURITY TOKEN</label>
                  <div className="input-wrapper">
                    <input
                      type="text"
                      value={credentials.access_code}
                      onChange={(e) => handleInputChange('access_code', e.target.value)}
                      className="auth-input token-input"
                      placeholder="Enter security token..."
                      required
                    />
                    <div className="input-border"></div>
                  </div>
                </div>
              </div>
            )}

            {/* Unlock Button */}
            <button 
              type="submit" 
              className={`unlock-button ${isUnlocking ? 'unlocking' : ''}`}
              disabled={isUnlocking}
            >
              <span className="button-content">
                {isUnlocking ? (
                  <>
                    <span className="unlock-spinner"></span>
                    <span>AUTHENTICATING...</span>
                  </>
                ) : (
                  <>
                    <span className="unlock-icon">🔓</span>
                    <span>UNLOCK CONSOLE</span>
                  </>
                )}
              </span>
              <div className="button-glow"></div>
            </button>
          </form>

          {/* Security Notice */}
          <div className="security-notice">
            <div className="notice-icon">⚠️</div>
            <div className="notice-content">
              <p className="notice-title">SECURITY NOTICE</p>
              <p className="notice-text">
                Unauthorized access attempts are logged and monitored. 
                This system is protected by enterprise-grade security protocols.
              </p>
            </div>
          </div>
        </div>

        {/* System Footer */}
        <div className="system-footer">
          <div className="footer-info">
            <span className="system-id">SYS-ID: SC-2025-ALPHA</span>
            <span className="last-check">LAST CHECK: {new Date().toLocaleTimeString()}</span>
          </div>
          <div className="security-level">
            <span className="level-indicator high">HIGH SECURITY</span>
          </div>
        </div>
      </div>

      {/* Scan Line Effect */}
      <div className="scan-line"></div>

      <style jsx>{`
        .auth-container {
          position: relative;
          height: 100vh;
          background: #0a0a0a;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        /* Grid Background */
        .grid-background {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          opacity: 0.1;
          pointer-events: none;
        }

        .grid-lines {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-image: 
            linear-gradient(rgba(0, 255, 65, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 65, 0.1) 1px, transparent 1px);
          background-size: 50px 50px;
        }

        /* Login Panel */
        .login-panel {
          position: relative;
          width: 500px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 2px solid #333;
          border-radius: 12px;
          box-shadow: 0 0 40px rgba(0, 255, 65, 0.1);
          overflow: hidden;
        }

        /* System Header */
        .system-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 24px;
          background: #0d0d0d;
          border-bottom: 2px solid #333;
        }

        .system-title {
          margin: 0;
          font-size: 20px;
          color: #00ff41;
          text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
          letter-spacing: 2px;
        }

        .system-status {
          display: flex;
          gap: 12px;
          align-items: center;
          margin-top: 4px;
        }

        .status-indicator {
          padding: 4px 8px;
          font-size: 10px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          border-radius: 3px;
        }

        .status-indicator.online {
          background: #0f4c0f;
          color: #00ff41;
          border: 1px solid #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }

        .system-version {
          font-size: 11px;
          color: #888;
        }

        .security-badge {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          background: #1a2e1a;
          border: 1px solid #00ff41;
          border-radius: 6px;
        }

        .badge-icon {
          font-size: 16px;
        }

        .badge-text {
          font-size: 11px;
          font-weight: bold;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        /* Auth Form */
        .auth-form {
          padding: 32px 24px;
        }

        .form-header {
          text-align: center;
          margin-bottom: 32px;
        }

        .form-title {
          margin: 0 0 8px 0;
          font-size: 18px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        .form-subtitle {
          margin: 0;
          color: #888;
          font-size: 12px;
        }

        /* Auth Method Selector */
        .auth-method-selector {
          display: flex;
          gap: 8px;
          margin-bottom: 24px;
          background: #0a0a0a;
          padding: 4px;
          border-radius: 6px;
          border: 1px solid #333;
        }

        .method-button {
          flex: 1;
          padding: 8px 12px;
          background: transparent;
          border: none;
          color: #888;
          font-size: 10px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          cursor: pointer;
          border-radius: 4px;
          transition: all 0.3s ease;
        }

        .method-button.active {
          background: #00ff41;
          color: #0a0a0a;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }

        .method-button:hover:not(.active) {
          background: #1a1a1a;
          color: #e5e5e5;
        }

        /* Form Fields */
        .auth-fields {
          display: flex;
          flex-direction: column;
          gap: 20px;
          margin-bottom: 32px;
        }

        .field-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .field-label {
          font-size: 11px;
          font-weight: bold;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .input-wrapper {
          position: relative;
        }

        .auth-input {
          width: 100%;
          padding: 12px 16px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 6px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 14px;
          transition: all 0.3s ease;
        }

        .auth-input:focus {
          outline: none;
          border-color: #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
        }

        .auth-input::placeholder {
          color: #666;
          font-style: italic;
        }

        .code-input {
          text-align: center;
          font-size: 18px;
          letter-spacing: 4px;
        }

        .token-input {
          font-family: monospace;
          font-size: 12px;
        }

        .input-border {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 2px;
          background: linear-gradient(90deg, #00ff41 0%, transparent 100%);
          transform: scaleX(0);
          transition: transform 0.3s ease;
        }

        .auth-input:focus + .input-border {
          transform: scaleX(1);
        }

        /* Unlock Button */
        .unlock-button {
          position: relative;
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 2px solid #333;
          border-radius: 8px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 14px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 2px;
          cursor: pointer;
          transition: all 0.3s ease;
          overflow: hidden;
        }

        .unlock-button:hover:not(:disabled) {
          border-color: #00ff41;
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
          transform: translateY(-2px);
        }

        .unlock-button:disabled {
          opacity: 0.7;
          cursor: not-allowed;
          border-color: #222;
        }

        .unlock-button.unlocking {
          border-color: #f39c12;
          box-shadow: 0 0 20px rgba(243, 156, 18, 0.3);
        }

        .button-content {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          position: relative;
          z-index: 1;
        }

        .unlock-icon {
          font-size: 16px;
        }

        .unlock-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #f39c12;
          border-top: 2px solid transparent;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .button-glow {
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent 0%, rgba(0, 255, 65, 0.3) 50%, transparent 100%);
          transition: left 0.5s ease;
        }

        .unlock-button:hover:not(:disabled) .button-glow {
          left: 100%;
        }

        /* Security Notice */
        .security-notice {
          display: flex;
          gap: 12px;
          padding: 16px;
          background: #1a1f1a;
          border: 1px solid #00ff41;
          border-radius: 6px;
          margin-top: 24px;
        }

        .notice-icon {
          font-size: 16px;
          color: #f39c12;
        }

        .notice-content {
          flex: 1;
        }

        .notice-title {
          margin: 0 0 4px 0;
          font-size: 11px;
          font-weight: bold;
          color: #f39c12;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .notice-text {
          margin: 0;
          font-size: 11px;
          color: #888;
          line-height: 1.4;
        }

        /* System Footer */
        .system-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 24px;
          background: #0d0d0d;
          border-top: 1px solid #333;
        }

        .footer-info {
          display: flex;
          gap: 16px;
          font-size: 10px;
          color: #666;
        }

        .security-level {
          display: flex;
          align-items: center;
        }

        .level-indicator {
          padding: 4px 8px;
          font-size: 9px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          border-radius: 3px;
        }

        .level-indicator.high {
          background: #2c0f0f;
          color: #ff4444;
          border: 1px solid #ff4444;
        }

        /* Scan Line Effect */
        .scan-line {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent 0%, #00ff41 50%, transparent 100%);
          animation: scan 3s linear infinite;
        }

        /* Animations */
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @keyframes scan {
          0% { transform: translateY(0); }
          100% { transform: translateY(100vh); }
        }

        /* Responsive */
        @media (max-width: 600px) {
          .login-panel {
            width: 90%;
            margin: 20px;
          }

          .system-header {
            flex-direction: column;
            gap: 16px;
            text-align: center;
          }

          .auth-method-selector {
            flex-direction: column;
          }

          .footer-info {
            flex-direction: column;
            gap: 4px;
          }
        }
      `}</style>
    </div>
  )
}
