import React, { useEffect, useState } from 'react'
import { API_BASE } from '../api'
import { useTheme } from './ThemeContext'

export default function TopBar() {
    const [status, setStatus] = useState<'online' | 'offline' | 'checking'>('checking')
    const [sessionUser, setSessionUser] = useState<string | null>(null)
    const { theme, toggleTheme } = useTheme()

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const res = await fetch(`${API_BASE}/health`)
                if (res.ok) {
                    setStatus('online')
                } else {
                    setStatus('offline')
                }
            } catch {
                setStatus('offline')
            }
        }

        checkHealth()
        const interval = setInterval(checkHealth, 30000)
        return () => clearInterval(interval)
    }, [])

    return (
        <header className="topbar">
            <div className="topbar-content">
                <div className="topbar-status">
                    <div className={`status-dot status-dot--${status}`} />
                    <span className="text-sm text-secondary">
                        {status === 'online' ? 'Connected' : status === 'offline' ? 'Disconnected' : 'Checking...'}
                    </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                    <button
                        onClick={toggleTheme}
                        className="btn btn--ghost"
                        style={{ padding: 'var(--space-1) var(--space-2)' }}
                        title="Toggle Theme"
                    >
                        {theme === 'dark' ? '☀️' : '🌙'}
                    </button>
                    <div className="session-indicator">
                        <div className={`session-dot ${sessionUser ? 'session-dot--authenticated' : 'session-dot--guest'}`} />
                        <span className="text-sm text-secondary">
                            {sessionUser || 'Guest'}
                        </span>
                    </div>
                </div>
            </div>
        </header>
    )
}
