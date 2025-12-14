import React, { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Background from './Background'

interface AppShellProps {
    children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
    const { pathname } = useLocation()
    const isLogin = pathname === '/login'

    const [sidebarExpanded, setSidebarExpanded] = useState(() => {
        const saved = localStorage.getItem('sidebar-expanded')
        return saved !== null ? JSON.parse(saved) : true
    })

    // Brief hack to sync sidebar state without a full context provider
    useEffect(() => {
        const handleStorage = () => {
            const saved = localStorage.getItem('sidebar-expanded')
            if (saved !== null) setSidebarExpanded(JSON.parse(saved))
        }
        window.addEventListener('storage', handleStorage)
        const interval = setInterval(handleStorage, 100)
        return () => {
            window.removeEventListener('storage', handleStorage)
            clearInterval(interval)
        }
    }, [])

    if (isLogin) {
        return (
            <>
                <Background state="idle" />
                {children}
            </>
        )
    }

    return (
        <>
            <Background state="idle" />
            <div className="flex bg-charcoal-dark min-h-screen">
                <Sidebar />
                <main 
                    className={`flex-1 overflow-auto transition-all duration-300 ease-in-out ${sidebarExpanded ? 'ml-64' : 'ml-20'}`}
                >
                    {children}
                </main>
            </div>
        </>
    )
}
