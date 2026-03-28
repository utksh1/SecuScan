import React, { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Background from './Background'
import { useShortcuts } from '../hooks/useShortcuts'
import { routes } from '../routes'

interface AppShellProps {
    children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
    const { pathname } = useLocation()

    useShortcuts()
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

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

    useEffect(() => {
        setMobileMenuOpen(false)
    }, [pathname])

    const desktopSidebarWidth = sidebarExpanded ? 220 : 64
    const mobilePrimaryNav = [
        { to: routes.dashboard, icon: 'monitoring', label: 'Dashboard' },
        { to: routes.scans, icon: 'add_circle', label: 'Scans' },
        { to: routes.findings, icon: 'emergency_home', label: 'Findings' },
        { to: routes.reports, icon: 'summarize', label: 'Reports' },
        { to: routes.history, icon: 'history', label: 'History' },
    ]
    const mobileDrawerNav = [
        { to: routes.dashboard, label: 'Dashboard' },
        { to: routes.scans, label: 'New Scan' },
        { to: routes.findings, label: 'Findings' },
        { to: routes.reports, label: 'Reports' },
        { to: routes.history, label: 'Activity' },
        { to: routes.assets, label: 'Assets' },
        { to: routes.attackSurface, label: 'Attack Surface' },
        { to: routes.settings, label: 'Settings' },
    ]


    return (
        <>
            <Background state="idle" />
            <div className="flex bg-charcoal-dark min-h-screen">
                <Sidebar />
                <div className="lg:hidden fixed inset-x-0 top-0 z-40 bg-secondary border-b border-accent-silver/10 h-14 px-4 flex items-center justify-between">
                    <button
                        onClick={() => setMobileMenuOpen((prev) => !prev)}
                        className="w-9 h-9 border border-accent-silver/20 flex items-center justify-center text-silver-bright bg-charcoal-dark"
                        aria-label="Toggle navigation menu"
                    >
                        <span className="material-symbols-outlined text-[20px]">
                            {mobileMenuOpen ? 'close' : 'menu'}
                        </span>
                    </button>
                    <span className="text-[12px] font-black tracking-[0.2em] text-silver-bright uppercase">SecuScan</span>
                    <span className="w-9 h-9" />
                </div>

                {mobileMenuOpen && (
                    <div className="lg:hidden fixed inset-0 z-40 bg-black/60" onClick={() => setMobileMenuOpen(false)}>
                        <div
                            className="absolute top-14 left-0 right-0 bg-secondary border-b border-accent-silver/10 p-4"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <nav className="grid grid-cols-2 gap-2">
                                {mobileDrawerNav.map((item) => (
                                    <NavLink
                                        key={item.to}
                                        to={item.to}
                                        className={({ isActive }) =>
                                            `px-3 py-2 text-[11px] font-bold uppercase tracking-[0.12em] border rounded ${
                                                isActive
                                                    ? 'border-rag-red/50 bg-rag-red/10 text-silver-bright'
                                                    : 'border-accent-silver/20 text-silver/80'
                                            }`
                                        }
                                    >
                                        {item.label}
                                    </NavLink>
                                ))}
                            </nav>
                        </div>
                    </div>
                )}

                <main 
                    className="flex-1 overflow-auto transition-all duration-300 ease-in-out ml-0 lg:ml-[var(--sidebar-width)] pt-14 lg:pt-0 pb-16 lg:pb-0"
                    style={{ '--sidebar-width': `${desktopSidebarWidth}px` } as React.CSSProperties}
                >
                    {children}
                </main>

                <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 h-16 bg-secondary border-t border-accent-silver/10 grid grid-cols-5">
                    {mobilePrimaryNav.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) =>
                                `flex flex-col items-center justify-center gap-1 text-[9px] font-bold uppercase tracking-[0.08em] ${
                                    isActive ? 'text-rag-red bg-rag-red/10' : 'text-silver/70'
                                }`
                            }
                        >
                            <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                            <span>{item.label}</span>
                        </NavLink>
                    ))}
                </nav>
            </div>
        </>
    )
}
