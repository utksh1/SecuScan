import React from 'react'

interface BackgroundProps {
    state?: 'idle' | 'active' | 'error'
}

export default function Background({ state = 'idle' }: BackgroundProps) {
    return (
        <div className={`background background--${state}`}>
            <div className="background-grid" />
            <div className="background-scan" />
            <div className="background-lines" />
        </div>
    )
}
