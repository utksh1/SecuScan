import React, { useState } from 'react'
import { setStoredApiKey } from '../api'

interface Props {
  onSaved: () => void
}

export default function ApiKeySetupModal({ onSaved }: Props) {
  const [key, setKey] = useState('')
  const [visible, setVisible] = useState(false)
  const [error, setError] = useState('')

  function handleSave() {
    const trimmed = key.trim()
    if (!trimmed) {
      setError('Please enter the API key.')
      return
    }
    setStoredApiKey(trimmed)
    setKey('')
    setError('')
    onSaved()
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="API key required"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          background: '#1e2130',
          borderRadius: 8,
          padding: '2rem',
          maxWidth: 480,
          width: '100%',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
      >
        <h2 style={{ marginTop: 0, color: '#e2e8f0' }}>API Key Required</h2>
        <p style={{ color: '#94a3b8', fontSize: 14 }}>
          SecuScan requires an API key to communicate with the backend. Read the key
          from the key file on the server and paste it below:
        </p>
        <pre
          style={{
            background: '#0f1117',
            color: '#7dd3fc',
            padding: '0.5rem 0.75rem',
            borderRadius: 4,
            fontSize: 12,
            overflowX: 'auto',
          }}
        >
          cat backend/data/.api_key
        </pre>
        <label style={{ display: 'block', marginTop: '1rem', color: '#cbd5e1', fontSize: 13 }}>
          Backend API Key
          <input
            type="password"
            value={key}
            onChange={(e) => { setKey(e.target.value); setError('') }}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            placeholder="Paste API key here"
            aria-label="Backend API Key"
            style={{
              display: 'block',
              width: '100%',
              marginTop: 6,
              padding: '0.5rem 0.75rem',
              borderRadius: 4,
              border: '1px solid #334155',
              background: '#0f1117',
              color: '#e2e8f0',
              fontSize: 14,
              boxSizing: 'border-box',
            }}
          />
        </label>
        {error && (
          <p role="alert" style={{ color: '#f87171', fontSize: 13, marginTop: 6 }}>
            {error}
          </p>
        )}
        <button
          onClick={handleSave}
          style={{
            marginTop: '1.25rem',
            padding: '0.5rem 1.25rem',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          Save and connect
        </button>
        <p style={{ marginTop: '1rem', color: '#64748b', fontSize: 12 }}>
          The key is stored only in your browser's localStorage and sent exclusively
          as the <code>X-Api-Key</code> request header — it is never stored server-side.
        </p>
      </div>
    </div>
  )
}
