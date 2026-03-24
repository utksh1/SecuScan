import { useState } from 'react'

export default function WebsiteScanner() {
  const [scanConfig, setScanConfig] = useState({
    targetUrl: '',
    followRedirects: true,
    scanType: 'light',
    crawlDepth: 1,
    maxUrls: 50,
    stayWithinDomain: true,
    includeSubdomains: false,
    includeQueryParams: false,
    securityHeaders: true,
    tlsConfig: true,
    serverMisconfig: true,
    techFingerprinting: true,
    cmsDetection: true,
    sqliDetection: false,
    xssDetection: false,
    openRedirectDetection: false,
    fileInclusionChecks: false,
    userAgent: 'default',
    requestRate: 'normal',
    timeout: '30s',
    authType: 'none',
    authCookie: '',
    authHeader: '',
    expertMode: false,
    rawArgs: '',
    consent: false
  })

  const [validationErrors, setValidationErrors] = useState({})

  const handleConfigChange = (field, value) => {
    setScanConfig(prev => ({ ...prev, [field]: value }))
    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: '' }))
    }
  }

  const validateUrl = (url) => {
    if (!url.trim()) return 'Target URL is required'
    
    // Basic URL validation
    const urlRegex = /^https?:\/\/.+/
    if (!urlRegex.test(url)) {
      return 'URL must start with http:// or https://'
    }
    
    // Additional validation for common patterns
    try {
      const parsed = new URL(url)
      if (!parsed.hostname) {
        return 'Invalid URL format'
      }
    } catch (e) {
      return 'Invalid URL format'
    }
    
    return ''
  }

  const handleUrlBlur = () => {
    const error = validateUrl(scanConfig.targetUrl)
    setValidationErrors(prev => ({ ...prev, targetUrl: error }))
  }

  const getRiskLevel = () => {
    if (scanConfig.scanType === 'light') return { level: 'LOW', color: '#10b981' }
    if (scanConfig.scanType === 'deep') return { level: 'MEDIUM', color: '#f59e0b' }
    if (scanConfig.expertMode) return { level: 'HIGH', color: '#ef4444' }
    return { level: 'MEDIUM', color: '#f59e0b' }
  }

  const getScanImpact = () => {
    let impact = 'Low'
    if (scanConfig.scanType === 'deep') impact = 'Medium'
    if (scanConfig.maxUrls > 100) impact = 'High'
    if (scanConfig.sqliDetection || scanConfig.xssDetection) impact = 'Medium'
    if (scanConfig.expertMode) impact = 'High'
    return impact
  }

  const isCustomMode = scanConfig.scanType === 'custom'

  return (
    <div className="scanner-container">
      {/* Header */}
      <div className="scanner-header">
        <div className="header-content">
          <h1 className="scanner-title">Website Scanner</h1>
          <p className="scanner-subtitle">Web application vulnerability & misconfiguration analysis</p>
        </div>
        <div className="risk-badge" style={{ borderColor: getRiskLevel().color }}>
          <span className="risk-text" style={{ color: getRiskLevel().color }}>
            {getRiskLevel().level} RISK
          </span>
        </div>
      </div>

      {/* Main Configuration */}
      <div className="config-panel">
        {/* Target Section */}
        <div className="config-section">
          <h3 className="section-title">TARGET</h3>
          <div className="target-input-wrapper">
            <input
              type="text"
              value={scanConfig.targetUrl}
              onChange={(e) => handleConfigChange('targetUrl', e.target.value)}
              onBlur={handleUrlBlur}
              placeholder="https://example.com"
              className="target-input"
            />
            {validationErrors.targetUrl && (
              <div className="validation-error">
                <span className="error-icon">⚠️</span>
                <span className="error-text">{validationErrors.targetUrl}</span>
              </div>
            )}
          </div>
          
          <div className="target-options">
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.followRedirects}
                onChange={(e) => handleConfigChange('followRedirects', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Follow redirects</span>
            </label>
          </div>
        </div>

        {/* Scan Type */}
        <div className="config-section">
          <h3 className="section-title">SCAN TYPE</h3>
          <div className="scan-type-selector">
            <label className="scan-type-option">
              <input
                type="radio"
                name="scanType"
                value="light"
                checked={scanConfig.scanType === 'light'}
                onChange={(e) => handleConfigChange('scanType', e.target.value)}
                className="scan-type-radio"
              />
              <div className="option-content">
                <span className="option-title">Light</span>
                <span className="option-description">Quick visibility, safe checks, minimal requests</span>
              </div>
            </label>
            
            <label className="scan-type-option">
              <input
                type="radio"
                name="scanType"
                value="deep"
                checked={scanConfig.scanType === 'deep'}
                onChange={(e) => handleConfigChange('scanType', e.target.value)}
                className="scan-type-radio"
              />
              <div className="option-content">
                <span className="option-title">Deep</span>
                <span className="option-description">Broader coverage, more requests, still safe</span>
              </div>
            </label>
            
            <label className="scan-type-option">
              <input
                type="radio"
                name="scanType"
                value="custom"
                checked={scanConfig.scanType === 'custom'}
                onChange={(e) => handleConfigChange('scanType', e.target.value)}
                className="scan-type-radio"
              />
              <div className="option-content">
                <span className="option-title">Custom</span>
                <span className="option-description">Full control, advanced options</span>
              </div>
            </label>
          </div>
        </div>

        {/* Crawling & Scope */}
        <div className="config-section">
          <h3 className="section-title">CRAWLING & SCOPE</h3>
          
          <div className="crawl-controls">
            <div className="control-row">
              <label className="control-label">Crawl Depth</label>
              <select
                value={scanConfig.crawlDepth}
                onChange={(e) => handleConfigChange('crawlDepth', parseInt(e.target.value))}
                className="control-select"
              >
                <option value={0}>0 - No crawling (single page)</option>
                <option value={1}>1 - Shallow crawl</option>
                <option value={2}>2 - Medium crawl</option>
                <option value={3}>3 - Deep crawl</option>
              </select>
            </div>
            
            <div className="control-row">
              <label className="control-label">Max URLs</label>
              <select
                value={scanConfig.maxUrls}
                onChange={(e) => handleConfigChange('maxUrls', parseInt(e.target.value))}
                className="control-select"
              >
                <option value={25}>25 URLs</option>
                <option value={50}>50 URLs</option>
                <option value={100}>100 URLs</option>
                <option value={250}>250 URLs</option>
                <option value={500}>500 URLs</option>
              </select>
            </div>
          </div>
          
          <div className="scope-options">
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.stayWithinDomain}
                onChange={(e) => handleConfigChange('stayWithinDomain', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Stay within domain</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.includeSubdomains}
                onChange={(e) => handleConfigChange('includeSubdomains', e.target.checked)}
                className="toggle-checkbox"
                disabled={scanConfig.stayWithinDomain}
              />
              <span className="toggle-label">Include subdomains</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.includeQueryParams}
                onChange={(e) => handleConfigChange('includeQueryParams', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Include query parameters</span>
            </label>
          </div>
        </div>

        {/* Core Web Checks */}
        <div className="config-section">
          <h3 className="section-title">CORE WEB CHECKS</h3>
          <div className="options-grid">
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.securityHeaders}
                onChange={(e) => handleConfigChange('securityHeaders', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Security headers analysis</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.tlsConfig}
                onChange={(e) => handleConfigChange('tlsConfig', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">TLS/SSL configuration</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.serverMisconfig}
                onChange={(e) => handleConfigChange('serverMisconfig', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Server misconfiguration</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.techFingerprinting}
                onChange={(e) => handleConfigChange('techFingerprinting', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Technology fingerprinting</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.cmsDetection}
                onChange={(e) => handleConfigChange('cmsDetection', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">CMS detection</span>
            </label>
          </div>
        </div>

        {/* Vulnerability Detection */}
        <div className="config-section">
          <h3 className="section-title">VULNERABILITY DETECTION</h3>
          <div className="detection-notice">
            <span className="notice-icon">ℹ️</span>
            <span className="notice-text">Detection only - No exploitation or data extraction</span>
          </div>
          
          <div className="options-grid">
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.sqliDetection}
                onChange={(e) => handleConfigChange('sqliDetection', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">SQL injection detection</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.xssDetection}
                onChange={(e) => handleConfigChange('xssDetection', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">XSS reflection detection</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.openRedirectDetection}
                onChange={(e) => handleConfigChange('openRedirectDetection', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">Open redirect detection</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.fileInclusionChecks}
                onChange={(e) => handleConfigChange('fileInclusionChecks', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">File inclusion checks</span>
            </label>
          </div>
        </div>

        {/* Advanced Options (Custom Mode Only) */}
        {isCustomMode && (
          <div className="config-section">
            <h3 className="section-title">ADVANCED OPTIONS</h3>
            
            {/* Level 1 - Structured */}
            <div className="advanced-options">
              <div className="control-row">
                <label className="control-label">User-Agent</label>
                <select
                  value={scanConfig.userAgent}
                  onChange={(e) => handleConfigChange('userAgent', e.target.value)}
                  className="control-select"
                >
                  <option value="default">Default (SecuScan)</option>
                  <option value="chrome">Chrome Browser</option>
                  <option value="firefox">Firefox Browser</option>
                  <option value="safari">Safari Browser</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              
              <div className="control-row">
                <label className="control-label">Request Rate</label>
                <select
                  value={scanConfig.requestRate}
                  onChange={(e) => handleConfigChange('requestRate', e.target.value)}
                  className="control-select"
                >
                  <option value="slow">Slow (1 req/sec)</option>
                  <option value="normal">Normal (5 req/sec)</option>
                  <option value="fast">Fast (10 req/sec)</option>
                  <option value="aggressive">Aggressive (20 req/sec)</option>
                </select>
              </div>
              
              <div className="control-row">
                <label className="control-label">Timeout</label>
                <select
                  value={scanConfig.timeout}
                  onChange={(e) => handleConfigChange('timeout', e.target.value)}
                  className="control-select"
                >
                  <option value="10s">10 seconds</option>
                  <option value="30s">30 seconds</option>
                  <option value="60s">60 seconds</option>
                  <option value="120s">120 seconds</option>
                </select>
              </div>
              
              {/* Authentication */}
              <div className="auth-section">
                <h4 className="auth-title">Authentication</h4>
                <div className="control-row">
                  <label className="control-label">Auth Type</label>
                  <select
                    value={scanConfig.authType}
                    onChange={(e) => handleConfigChange('authType', e.target.value)}
                    className="control-select"
                  >
                    <option value="none">None</option>
                    <option value="cookie">Cookie-based</option>
                    <option value="header">Header-based</option>
                  </select>
                </div>
                
                {scanConfig.authType === 'cookie' && (
                  <div className="control-row">
                    <label className="control-label">Cookie</label>
                    <input
                      type="text"
                      value={scanConfig.authCookie}
                      onChange={(e) => handleConfigChange('authCookie', e.target.value)}
                      placeholder="session=abc123"
                      className="control-input"
                    />
                  </div>
                )}
                
                {scanConfig.authType === 'header' && (
                  <div className="control-row">
                    <label className="control-label">Header</label>
                    <input
                      type="text"
                      value={scanConfig.authHeader}
                      onChange={(e) => handleConfigChange('authHeader', e.target.value)}
                      placeholder="Authorization: Bearer token"
                      className="control-input"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Level 2 - Expert Mode */}
            <div className="expert-section">
              <div className="expert-header">
                <label className="expert-toggle">
                  <input
                    type="checkbox"
                    checked={scanConfig.expertMode}
                    onChange={(e) => handleConfigChange('expertMode', e.target.checked)}
                    className="expert-checkbox"
                  />
                  <span className="expert-label">Expert Mode</span>
                </label>
              </div>
              
              {scanConfig.expertMode && (
                <div className="expert-content">
                  <div className="expert-warning">
                    <span className="warning-icon">⚠️</span>
                    <span className="warning-text">Expert mode overrides UI selections</span>
                  </div>
                  <textarea
                    value={scanConfig.rawArgs}
                    onChange={(e) => handleConfigChange('rawArgs', e.target.value)}
                    placeholder="--timeout=30 --max-redirects=5 --user-agent=custom"
                    className="expert-input"
                    rows={3}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Risk & Safety Summary */}
        <div className="config-section">
          <h3 className="section-title">RISK & SAFETY SUMMARY</h3>
          <div className="risk-summary">
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-label">Risk Level:</span>
                <span className="summary-value" style={{ color: getRiskLevel().color }}>
                  {getRiskLevel().level}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Scan Impact:</span>
                <span className="summary-value">{getScanImpact()}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Max Requests:</span>
                <span className="summary-value">{scanConfig.maxUrls} URLs</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Detection Mode:</span>
                <span className="summary-value">Safe (no exploitation)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Consent & Actions */}
        <div className="config-section">
          <div className="consent-section">
            <label className="consent-checkbox">
              <input
                type="checkbox"
                checked={scanConfig.consent}
                onChange={(e) => handleConfigChange('consent', e.target.checked)}
                className="consent-input"
              />
              <span className="consent-label">
                I confirm I am authorized to test this target
              </span>
            </label>
          </div>
          
          <div className="action-buttons">
            <button className="action-button schedule">
              <span className="button-icon">📅</span>
              <span className="button-text">Schedule Scan</span>
            </button>
            
            <button 
              className={`action-button start ${!scanConfig.consent || !scanConfig.targetUrl || validationErrors.targetUrl ? 'disabled' : ''}`}
              disabled={!scanConfig.consent || !scanConfig.targetUrl || validationErrors.targetUrl}
            >
              <span className="button-icon">▶️</span>
              <span className="button-text">Start Scan</span>
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        .scanner-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #0a0a0a;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          overflow-y: auto;
        }

        /* Header */
        .scanner-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 24px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 1px solid #333;
          border-bottom: 2px solid #333;
        }

        .scanner-title {
          margin: 0;
          font-size: 24px;
          color: #00ff41;
          text-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }

        .scanner-subtitle {
          margin: 4px 0 0 0;
          color: #888;
          font-size: 14px;
        }

        .risk-badge {
          padding: 8px 16px;
          border: 2px solid;
          border-radius: 6px;
          background: rgba(0, 0, 0, 0.3);
        }

        .risk-text {
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        /* Configuration Panel */
        .config-panel {
          flex: 1;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 32px;
        }

        .config-section {
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 1px solid #333;
          border-radius: 8px;
          padding: 20px;
        }

        .section-title {
          margin: 0 0 16px 0;
          font-size: 14px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        /* Target Input */
        .target-input-wrapper {
          position: relative;
          margin-bottom: 16px;
        }

        .target-input {
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

        .target-input:focus {
          outline: none;
          border-color: #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
        }

        .target-input::placeholder {
          color: #666;
          font-style: italic;
        }

        .validation-error {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          padding: 8px 12px;
          background: #2c0f0f;
          border: 1px solid #ef4444;
          border-radius: 4px;
        }

        .error-icon {
          font-size: 14px;
        }

        .error-text {
          font-size: 12px;
          color: #ff8888;
        }

        .target-options {
          display: flex;
          gap: 16px;
        }

        /* Scan Type Selector */
        .scan-type-selector {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .scan-type-option {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .scan-type-option:hover {
          border-color: #555;
          background: #1a1a1a;
        }

        .scan-type-option:has(input:checked) {
          border-color: #00ff41;
          background: #0f4c0f;
        }

        .scan-type-radio {
          width: 16px;
          height: 16px;
        }

        .option-content {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .option-title {
          font-weight: bold;
          color: #e5e5e5;
        }

        .option-description {
          font-size: 12px;
          color: #888;
        }

        /* Crawl Controls */
        .crawl-controls {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 20px;
        }

        .control-row {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .control-label {
          min-width: 100px;
          font-size: 12px;
          color: #888;
          text-transform: uppercase;
        }

        .control-select, .control-input {
          flex: 1;
          padding: 6px 12px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
        }

        .control-select:focus, .control-input:focus {
          outline: none;
          border-color: #00ff41;
        }

        .scope-options {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        /* Options Grid */
        .options-grid {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .toggle-option {
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
        }

        .toggle-checkbox {
          width: 16px;
          height: 16px;
        }

        .toggle-label {
          font-size: 13px;
          color: #e5e5e5;
        }

        .toggle-option:has(input:disabled) {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Detection Notice */
        .detection-notice {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          background: #1a2e1a;
          border: 1px solid #10b981;
          border-radius: 4px;
          margin-bottom: 16px;
        }

        .notice-icon {
          font-size: 14px;
          color: #10b981;
        }

        .notice-text {
          font-size: 12px;
          color: #10b981;
        }

        /* Advanced Options */
        .advanced-options {
          display: flex;
          flex-direction: column;
          gap: 16px;
          margin-bottom: 24px;
        }

        .auth-section {
          border-top: 1px solid #333;
          padding-top: 16px;
          margin-top: 16px;
        }

        .auth-title {
          margin: 0 0 12px 0;
          font-size: 12px;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        /* Expert Mode */
        .expert-section {
          border-top: 1px solid #333;
          padding-top: 16px;
        }

        .expert-header {
          margin-bottom: 16px;
        }

        .expert-toggle {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }

        .expert-checkbox {
          width: 16px;
          height: 16px;
        }

        .expert-label {
          font-size: 13px;
          font-weight: bold;
          color: #f59e0b;
        }

        .expert-content {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .expert-warning {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: #2a1f0f;
          border: 1px solid #f59e0b;
          border-radius: 4px;
        }

        .warning-icon {
          font-size: 14px;
        }

        .warning-text {
          font-size: 12px;
          color: #f59e0b;
        }

        .expert-input {
          padding: 8px 12px;
          background: #0a0a0a;
          border: 1px solid #f59e0b;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          resize: vertical;
        }

        .expert-input:focus {
          outline: none;
          border-color: #f59e0b;
          box-shadow: 0 0 10px rgba(243, 156, 18, 0.2);
        }

        /* Risk Summary */
        .risk-summary {
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 6px;
          padding: 16px;
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 12px;
        }

        .summary-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .summary-label {
          font-size: 12px;
          color: #888;
          text-transform: uppercase;
        }

        .summary-value {
          font-size: 12px;
          font-weight: bold;
          color: #e5e5e5;
        }

        /* Consent & Actions */
        .consent-section {
          margin-bottom: 20px;
        }

        .consent-checkbox {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }

        .consent-input {
          width: 16px;
          height: 16px;
        }

        .consent-label {
          font-size: 13px;
          color: #e5e5e5;
        }

        .action-buttons {
          display: flex;
          gap: 16px;
          justify-content: flex-end;
        }

        .action-button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 24px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 2px solid #333;
          border-radius: 6px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
          letter-spacing: 1px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .action-button:hover:not(.disabled) {
          transform: translateY(-2px);
        }

        .action-button.schedule:hover {
          border-color: #f59e0b;
          box-shadow: 0 0 20px rgba(243, 156, 18, 0.3);
        }

        .action-button.start:hover:not(.disabled) {
          border-color: #00ff41;
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
        }

        .action-button.disabled {
          opacity: 0.5;
          cursor: not-allowed;
          border-color: #222;
        }

        .button-icon {
          font-size: 14px;
        }

        .button-text {
          font-size: 12px;
        }

        /* Responsive */
        @media (max-width: 768px) {
          .scanner-header {
            flex-direction: column;
            gap: 16px;
            text-align: center;
          }

          .crawl-controls {
            grid-template-columns: 1fr;
          }

          .summary-grid {
            grid-template-columns: 1fr;
          }

          .action-buttons {
            flex-direction: column;
          }

          .action-button {
            justify-content: center;
          }
        }
      `}</style>
    </div>
  )
}
