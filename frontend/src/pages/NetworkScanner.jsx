import { useState } from 'react'

export default function NetworkScanner() {
  const [scanConfig, setScanConfig] = useState({
    target: '',
    scanType: 'light',
    protocol: 'tcp',
    checkHostAlive: true,
    skipHostDiscovery: false,
    resolveHostnames: true,
    portType: 'top',
    customPorts: '',
    serviceDetection: false,
    osDetection: false,
    scriptScanning: false,
    timingTemplate: 'T3',
    retries: 3,
    scanTimeout: '10m',
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

  const validateTarget = (target) => {
    // Basic validation for IP, hostname, or CIDR
    const targets = target.split(/[\s,]+/).filter(t => t.trim())
    const errors = []
    
    targets.forEach(t => {
      // IPv4 regex
      const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
      // CIDR regex
      const cidrRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:[0-9]|[1-2][0-9]|3[0-2])$/
      // Hostname regex (simplified)
      const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/
      
      if (!ipv4Regex.test(t) && !cidrRegex.test(t) && !hostnameRegex.test(t)) {
        errors.push(`Invalid target: ${t}`)
      }
    })
    
    return errors
  }

  const handleTargetBlur = () => {
    const errors = validateTarget(scanConfig.target)
    setValidationErrors(prev => ({ ...prev, target: errors.join(', ') }))
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
    if (scanConfig.portType === 'all' || scanConfig.osDetection) impact = 'High'
    if (scanConfig.expertMode && scanConfig.rawArgs.includes('-A')) impact = 'Very High'
    return impact
  }

  const isCustomMode = scanConfig.scanType === 'custom'

  return (
    <div className="scanner-container">
      {/* Header */}
      <div className="scanner-header">
        <div className="header-content">
          <h1 className="scanner-title">Network Scanner</h1>
          <p className="scanner-subtitle">Port, service, and host discovery</p>
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
            <textarea
              value={scanConfig.target}
              onChange={(e) => handleConfigChange('target', e.target.value)}
              onBlur={handleTargetBlur}
              placeholder="Enter hostname, IP address, or CIDR block&#10;Examples:&#10;192.168.1.1&#10;example.com&#10;192.168.1.0/24&#10;&#10;Multiple targets (comma or newline separated):&#10;192.168.1.1, 192.168.1.2&#10;example.com&#10;10.0.0.0/8"
              className="target-input"
              rows={6}
            />
            {validationErrors.target && (
              <div className="validation-error">
                <span className="error-icon">⚠️</span>
                <span className="error-text">{validationErrors.target}</span>
              </div>
            )}
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
                <span className="option-description">Fast scan, top ports, minimal noise</span>
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
                <span className="option-description">Full enumeration, service detection, slower</span>
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

        {/* Protocol Selection */}
        <div className="config-section">
          <h3 className="section-title">PROTOCOL</h3>
          <div className="protocol-selector">
            <label className="protocol-option">
              <input
                type="radio"
                name="protocol"
                value="tcp"
                checked={scanConfig.protocol === 'tcp'}
                onChange={(e) => handleConfigChange('protocol', e.target.value)}
                className="protocol-radio"
              />
              <span className="protocol-label">TCP</span>
            </label>
            
            <label className="protocol-option">
              <input
                type="radio"
                name="protocol"
                value="udp"
                checked={scanConfig.protocol === 'udp'}
                onChange={(e) => handleConfigChange('protocol', e.target.value)}
                className="protocol-radio"
              />
              <span className="protocol-label">UDP</span>
            </label>
            
            <label className="protocol-option">
              <input
                type="radio"
                name="protocol"
                value="both"
                checked={scanConfig.protocol === 'both'}
                onChange={(e) => handleConfigChange('protocol', e.target.value)}
                className="protocol-radio"
              />
              <span className="protocol-label">Both</span>
            </label>
          </div>
        </div>

        {/* Common Options */}
        <div className="config-section">
          <h3 className="section-title">COMMON OPTIONS</h3>
          <div className="options-grid">
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.checkHostAlive}
                onChange={(e) => handleConfigChange('checkHostAlive', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Check if host is alive before scanning</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.skipHostDiscovery}
                onChange={(e) => handleConfigChange('skipHostDiscovery', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Skip host discovery</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.resolveHostnames}
                onChange={(e) => handleConfigChange('resolveHostnames', e.target.checked)}
                className="toggle-checkbox"
              />
              <span className="toggle-label">Resolve hostnames</span>
            </label>
          </div>
        </div>

        {/* Port Configuration */}
        <div className="config-section">
          <h3 className="section-title">PORT CONFIGURATION</h3>
          <div className="port-selector">
            <label className="port-option">
              <input
                type="radio"
                name="portType"
                value="top"
                checked={scanConfig.portType === 'top'}
                onChange={(e) => handleConfigChange('portType', e.target.value)}
                className="port-radio"
              />
              <span className="port-label">Top ports (100 most common)</span>
            </label>
            
            <label className="port-option">
              <input
                type="radio"
                name="portType"
                value="common"
                checked={scanConfig.portType === 'common'}
                onChange={(e) => handleConfigChange('portType', e.target.value)}
                className="port-radio"
              />
              <span className="port-label">Common ports (1000 most common)</span>
            </label>
            
            <label className="port-option">
              <input
                type="radio"
                name="portType"
                value="all"
                checked={scanConfig.portType === 'all'}
                onChange={(e) => handleConfigChange('portType', e.target.value)}
                className="port-radio"
              />
              <span className="port-label">All ports (1-65535)</span>
            </label>
            
            <label className="port-option">
              <input
                type="radio"
                name="portType"
                value="custom"
                checked={scanConfig.portType === 'custom'}
                onChange={(e) => handleConfigChange('portType', e.target.value)}
                className="port-radio"
              />
              <div className="custom-port-input">
                <span className="port-label">Custom range:</span>
                <input
                  type="text"
                  value={scanConfig.customPorts}
                  onChange={(e) => handleConfigChange('customPorts', e.target.value)}
                  placeholder="80,443,8080-8090"
                  className="custom-port-field"
                  disabled={scanConfig.portType !== 'custom'}
                />
              </div>
            </label>
          </div>
        </div>

        {/* Detection & Enumeration */}
        <div className="config-section">
          <h3 className="section-title">DETECTION & ENUMERATION</h3>
          <div className="options-grid">
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.serviceDetection}
                onChange={(e) => handleConfigChange('serviceDetection', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">Service version detection (-sV)</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.osDetection}
                onChange={(e) => handleConfigChange('osDetection', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">OS detection (-O)</span>
            </label>
            
            <label className="toggle-option">
              <input
                type="checkbox"
                checked={scanConfig.scriptScanning}
                onChange={(e) => handleConfigChange('scriptScanning', e.target.checked)}
                className="toggle-checkbox"
                disabled={!isCustomMode}
              />
              <span className="toggle-label">Default script scanning (safe)</span>
            </label>
          </div>
        </div>

        {/* Advanced Options (Custom Mode Only) */}
        {isCustomMode && (
          <div className="config-section">
            <h3 className="section-title">ADVANCED OPTIONS</h3>
            
            {/* Level 1 - Structured */}
            <div className="advanced-options">
              <div className="option-row">
                <label className="option-label">Timing Template</label>
                <select
                  value={scanConfig.timingTemplate}
                  onChange={(e) => handleConfigChange('timingTemplate', e.target.value)}
                  className="timing-select"
                >
                  <option value="T0">T0 - Paranoid (very slow)</option>
                  <option value="T1">T1 - Sneaky (slow)</option>
                  <option value="T2">T2 - Polite (medium)</option>
                  <option value="T3">T3 - Normal (default)</option>
                  <option value="T4">T4 - Fast (quick)</option>
                  <option value="T5">T5 - Aggressive (very fast)</option>
                </select>
              </div>
              
              <div className="option-row">
                <label className="option-label">Retries</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={scanConfig.retries}
                  onChange={(e) => handleConfigChange('retries', parseInt(e.target.value))}
                  className="number-input"
                />
              </div>
              
              <div className="option-row">
                <label className="option-label">Scan Timeout</label>
                <select
                  value={scanConfig.scanTimeout}
                  onChange={(e) => handleConfigChange('scanTimeout', e.target.value)}
                  className="timeout-select"
                >
                  <option value="5m">5 minutes</option>
                  <option value="10m">10 minutes</option>
                  <option value="30m">30 minutes</option>
                  <option value="1h">1 hour</option>
                </select>
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
                    placeholder="-sV -p- -A -T4"
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
                <span className="summary-label">Scope:</span>
                <span className="summary-value">
                  {scanConfig.target.includes('/') ? 'Network enumeration' : 'Host enumeration'}
                </span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Protocol:</span>
                <span className="summary-value">{scanConfig.protocol.toUpperCase()}</span>
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
              className={`action-button start ${!scanConfig.consent || !scanConfig.target || validationErrors.target ? 'disabled' : ''}`}
              disabled={!scanConfig.consent || !scanConfig.target || validationErrors.target}
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
        }

        .target-input {
          width: 100%;
          padding: 12px 16px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 6px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 13px;
          resize: vertical;
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

        /* Protocol Selector */
        .protocol-selector {
          display: flex;
          gap: 16px;
        }

        .protocol-option {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .protocol-option:hover {
          border-color: #555;
        }

        .protocol-option:has(input:checked) {
          border-color: #00ff41;
          background: #0f4c0f;
        }

        .protocol-label {
          font-size: 12px;
          font-weight: bold;
          text-transform: uppercase;
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

        /* Port Selector */
        .port-selector {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .port-option {
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
        }

        .port-radio {
          width: 16px;
          height: 16px;
        }

        .port-label {
          font-size: 13px;
          color: #e5e5e5;
        }

        .custom-port-input {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }

        .custom-port-field {
          flex: 1;
          padding: 4px 8px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
        }

        .custom-port-field:focus {
          outline: none;
          border-color: #00ff41;
        }

        .custom-port-field:disabled {
          opacity: 0.5;
        }

        /* Advanced Options */
        .advanced-options {
          display: flex;
          flex-direction: column;
          gap: 16px;
          margin-bottom: 24px;
        }

        .option-row {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .option-label {
          min-width: 120px;
          font-size: 12px;
          color: #888;
          text-transform: uppercase;
        }

        .timing-select, .timeout-select {
          padding: 6px 12px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
        }

        .number-input {
          width: 80px;
          padding: 6px 12px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 12px;
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

          .protocol-selector {
            flex-direction: column;
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
