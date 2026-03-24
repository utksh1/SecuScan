import { useState } from 'react'

export default function DynamicForm({ schema, preset, onSubmit, loading }) {
  const [formData, setFormData] = useState({})
  const [selectedPreset, setSelectedPreset] = useState(preset || '')

  const handleChange = (fieldName, value) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }))
  }

  const handlePresetChange = (presetId) => {
    setSelectedPreset(presetId)
    
    // Apply preset defaults
    const selectedPresetData = schema.presets.find(p => p.id === presetId)
    if (selectedPresetData?.defaults) {
      setFormData(prev => ({ ...prev, ...selectedPresetData.defaults }))
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      preset: selectedPreset,
      inputs: formData,
    })
  }

  const getVisibleFields = () => {
    if (!schema?.fields) return []
    
    return schema.fields.filter(field => {
      if (!field.show_if) return true
      
      // Simple condition evaluation
      const [fieldName, expectedValue] = field.show_if.split('=')
      return formData[fieldName?.trim()] === expectedValue?.trim()
    })
  }

  return (
    <form onSubmit={handleSubmit} className="technical-form">
      {/* Preset Selection */}
      {schema?.presets && schema.presets.length > 0 && (
        <div className="form-group">
          <label className="form-label">
            PRESET CONFIGURATION
            <span className="required">*</span>
          </label>
          <select
            value={selectedPreset}
            onChange={(e) => handlePresetChange(e.target.value)}
            required
            className="form-select"
          >
            <option value="">SELECT PRESET...</option>
            {schema.presets.map(p => (
              <option key={p.id} value={p.id}>
                [{p.id.toUpperCase()}] {p.name} - {p.description}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Dynamic Fields */}
      {getVisibleFields().map(field => (
        <div key={field.name} className="form-group">
          <label className="form-label">
            {field.label.toUpperCase()}
            {field.required && <span className="required"> *</span>}
          </label>
          
          {field.type === 'text' && (
            <div className="input-wrapper">
              <input
                type="text"
                value={formData[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value)}
                placeholder={field.placeholder || `ENTER ${field.label.toUpperCase()}`}
                required={field.required}
                className="form-input"
              />
              <div className="input-border"></div>
            </div>
          )}
          
          {field.type === 'number' && (
            <div className="input-wrapper">
              <input
                type="number"
                value={formData[field.name] || ''}
                onChange={(e) => handleChange(field.name, parseInt(e.target.value) || '')}
                placeholder={field.placeholder || `ENTER ${field.label.toUpperCase()}`}
                required={field.required}
                className="form-input"
              />
              <div className="input-border"></div>
            </div>
          )}
          
          {field.type === 'select' && (
            <div className="input-wrapper">
              <select
                value={formData[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value)}
                required={field.required}
                className="form-select"
              >
                <option value="">SELECT...</option>
                {field.options?.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <div className="input-border"></div>
            </div>
          )}
          
          {field.type === 'boolean' && (
            <div className="checkbox-wrapper">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData[field.name] || false}
                  onChange={(e) => handleChange(field.name, e.target.checked)}
                  className="form-checkbox"
                />
                <span className="checkbox-text">{field.label}</span>
                <div className="checkbox-border"></div>
              </label>
            </div>
          )}
          
          {field.help && (
            <div className="field-help">
              <span className="help-icon">ℹ</span>
              <span className="help-text">{field.help}</span>
            </div>
          )}
        </div>
      ))}

      <button type="submit" className="form-button" disabled={loading || !selectedPreset}>
        <span className="button-text">
          {loading ? 'ENGAGING SYSTEM...' : 'ARM SYSTEM'}
        </span>
        <div className="button-glow"></div>
      </button>

      <style jsx>{`
        .technical-form {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .form-label {
          font-size: 12px;
          font-weight: bold;
          color: #00ff41;
          text-transform: uppercase;
          letter-spacing: 1px;
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .required {
          color: #ff4444;
          font-size: 14px;
        }

        .input-wrapper {
          position: relative;
        }

        .form-input, .form-select {
          width: 100%;
          padding: 12px 16px;
          background: #0a0a0a;
          border: 1px solid #333;
          border-radius: 4px;
          color: #e5e5e5;
          font-family: 'Courier New', monospace;
          font-size: 14px;
          transition: all 0.3s ease;
        }

        .form-input:focus, .form-select:focus {
          outline: none;
          border-color: #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
        }

        .form-input::placeholder, .form-select::placeholder {
          color: #666;
          font-style: italic;
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

        .form-input:focus + .input-border,
        .form-select:focus + .input-border {
          transform: scaleX(1);
        }

        .checkbox-wrapper {
          position: relative;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
          position: relative;
        }

        .form-checkbox {
          width: 16px;
          height: 16px;
          background: #0a0a0a;
          border: 2px solid #333;
          border-radius: 3px;
          appearance: none;
          cursor: pointer;
          position: relative;
          transition: all 0.3s ease;
        }

        .form-checkbox:checked {
          background: #00ff41;
          border-color: #00ff41;
          box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
        }

        .form-checkbox:checked::after {
          content: '✓';
          position: absolute;
          top: -2px;
          left: 2px;
          color: #0a0a0a;
          font-size: 12px;
          font-weight: bold;
        }

        .checkbox-text {
          color: #e5e5e5;
          font-weight: normal;
          text-transform: none;
          letter-spacing: normal;
        }

        .checkbox-border {
          position: absolute;
          bottom: -2px;
          left: 0;
          width: 100%;
          height: 1px;
          background: linear-gradient(90deg, #333 0%, transparent 100%);
        }

        .field-help {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 4px;
        }

        .help-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 50%;
          color: #666;
          font-size: 10px;
          font-weight: bold;
        }

        .help-text {
          font-size: 11px;
          color: #666;
          font-style: italic;
        }

        .form-button {
          position: relative;
          padding: 16px 32px;
          background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
          border: 2px solid #333;
          border-radius: 6px;
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

        .form-button:hover:not(:disabled) {
          border-color: #00ff41;
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
          transform: translateY(-2px);
        }

        .form-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          border-color: #222;
        }

        .button-text {
          position: relative;
          z-index: 1;
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

        .form-button:hover:not(:disabled) .button-glow {
          left: 100%;
        }

        /* Select dropdown styling */
        .form-select {
          appearance: none;
          background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2300ff41' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6,9 12,15 18,9'%3e%3c/polyline%3e%3c/svg%3e");
          background-repeat: no-repeat;
          background-position: right 12px center;
          background-size: 16px;
          padding-right: 40px;
        }

        /* Focus animations */
        @keyframes input-focus {
          0% { box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.4); }
          100% { box-shadow: 0 0 0 10px rgba(0, 255, 65, 0); }
        }

        .form-input:focus, .form-select:focus {
          animation: input-focus 0.3s ease-out;
        }
      `}</style>
    </form>
  )
}
