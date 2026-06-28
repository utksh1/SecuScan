import React, { useState } from 'react'
import { authenticateWithApiKey } from '../api'

interface Props {
  onSaved: () => void
}

/**
 * Full-page first-run / 401 gate.
 *
 * Replaces the entire app until the operator provides the API key.
 * Because this component renders instead of the normal route tree, no page
 * component mounts and no protected API call fires before the key is saved.
 *
 * The operator reads the key from the server key file and pastes it here.
 * The key is sent to the backend which validates it and sets an HttpOnly
 * session cookie; the raw key is never persisted in the browser.
 */
export default function ApiKeySetupScreen({ onSaved }: Props) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')

  async function handleSave() {
    const trimmed = key.trim()
    if (!trimmed) {
      setError('Please enter the API key.')
      return
    }
    try {
      await authenticateWithApiKey(trimmed)
      setKey('')
      setError('')
      onSaved()
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Check the API key.')
    }
  }

  return (
    <div
      role="main"
      aria-label="API key setup"
      style={{
        minHeight: '100vh',
        background: '#0f1117',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        style={{
          background: '#1e2130',
          borderRadius: 8,
          padding: '2rem',
          maxWidth: 500,
          width: '100%',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
      >
        <h1 style={{ marginTop: 0, fontSize: 22, color: '#e2e8f0' }}>
          Connect to SecuScan
        </h1>
        <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6 }}>
          The backend requires an API key. Read the key from the server key
          file and paste it below to get started:
        </p>
        <pre
          style={{
            background: '#0a0d14',
            color: '#7dd3fc',
            padding: '0.6rem 0.85rem',
            borderRadius: 4,
            fontSize: 12,
            overflowX: 'auto',
            margin: '0.75rem 0',
          }}
        >
          cat backend/data/.api_key
        </pre>
        <label
          htmlFor="api-key-input"
          style={{ display: 'block', color: '#cbd5e1', fontSize: 13, marginTop: '1rem' }}
        >
          Backend API Key
        </label>
        <input
          id="api-key-input"
          type="password"
          value={key}
          onChange={(e) => { setKey(e.target.value); setError('') }}
          onKeyDown={(e) => e.key === 'Enter' && handleSave()}
          placeholder="Paste API key here"
          aria-label="Backend API Key"
          autoFocus
          style={{
            display: 'block',
            width: '100%',
            marginTop: 6,
            padding: '0.5rem 0.75rem',
            borderRadius: 4,
            border: error ? '1px solid #f87171' : '1px solid #334155',
            background: '#0a0d14',
            color: '#e2e8f0',
            fontSize: 14,
            boxSizing: 'border-box',
            outline: 'none',
          }}
        />
        {error && (
          <p role="alert" style={{ color: '#f87171', fontSize: 13, margin: '6px 0 0' }}>
            {error}
          </p>
        )}
        <button
          onClick={handleSave}
          style={{
            marginTop: '1.25rem',
            padding: '0.55rem 1.4rem',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          Save and connect
        </button>
        <p style={{ marginTop: '1.25rem', color: '#475569', fontSize: 12, lineHeight: 1.5 }}>
          The key is sent to the backend which validates it and sets an HttpOnly
          session cookie. The raw key is never persisted in the browser and is held
          only in memory for the duration of the page session.
        </p>
      </div>
    </div>
  )
}
