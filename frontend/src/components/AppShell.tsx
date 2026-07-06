import React, { useState, useEffect, useRef, useCallback } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import Background from './Background'
import { useShortcuts } from '../hooks/useShortcuts'
import { SidebarProvider, useSidebar } from '../context/SidebarContext'
import { routes } from '../routes'

interface AppShellProps {
    children: React.ReactNode
}

function AppShellInner({ children }: AppShellProps) {
    const { pathname } = useLocation()
    const { isExpanded: sidebarExpanded, toggleSidebar } = useSidebar()
    useShortcuts(toggleSidebar)
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
    const menuButtonRef = useRef<HTMLButtonElement>(null)
    const drawerRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        setMobileMenuOpen(false)
    }, [pathname])

    useEffect(() => {
        if (!mobileMenuOpen) return
        const previousOverflow = document.body.style.overflow
        document.body.style.overflow = 'hidden'
        return () => {
            document.body.style.overflow = previousOverflow
        }
    }, [mobileMenuOpen])

    useEffect(() => {
        if (mobileMenuOpen) {
            const firstFocusable = drawerRef.current?.querySelector<HTMLElement>(
                'a, button, [tabindex]:not([tabindex="-1"])'
            )
            firstFocusable?.focus()
        } else {
            menuButtonRef.current?.focus()
        }
    }, [mobileMenuOpen])

    const handleDrawerKeyDown = useCallback(
        (e: React.KeyboardEvent<HTMLDivElement>) => {
            if (e.key === 'Escape') {
                setMobileMenuOpen(false)
                return
            }
            if (e.key !== 'Tab') return
            const focusable = Array.from(
                drawerRef.current?.querySelectorAll<HTMLElement>(
                    'a, button, [tabindex]:not([tabindex="-1"])'
                ) ?? []
            )
            if (focusable.length === 0) return
            const first = focusable[0]
            const last = focusable[focusable.length - 1]
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault()
                last.focus()
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault()
                first.focus()
            }
        },
        []
    )

    const desktopSidebarWidth = sidebarExpanded ? 220 : 64
    const mobilePrimaryNav = [
        { to: routes.dashboard, icon: 'monitoring', label: 'Dashboard' },
        { to: routes.scans, icon: 'history', label: 'Scans' },
        { to: routes.findings, icon: 'emergency_home', label: 'Findings' },
        { to: routes.reports, icon: 'summarize', label: 'Reports' },
        { to: routes.workflows, icon: 'account_tree', label: 'Workflows' },
    ]
    const mobileDrawerNav = [
        { to: routes.dashboard, label: 'Dashboard' },
        { to: routes.scans, label: 'Scans' },
        { to: routes.findings, label: 'Findings' },
        { to: routes.reports, label: 'Reports' },
        { to: routes.workflows, label: 'Workflows' },
        { to: routes.toolkit, label: 'Toolkit' },
        { to: routes.settings, label: 'Settings' },
    ]

    return (
        <>
            <Background state="idle" />
            <div className="flex bg-charcoal-dark min-h-screen">
                <Sidebar />
                <div className="lg:hidden fixed inset-x-0 top-0 z-[60] bg-[var(--bg-secondary)] border-b border-accent-silver/10 h-14 px-4 flex items-center justify-between">
                    <button
                        ref={menuButtonRef}
                        onClick={() => setMobileMenuOpen((prev) => !prev)}
                        className="w-9 h-9 border border-accent-silver/20 flex items-center justify-center text-silver-bright bg-charcoal-dark"
                        aria-label="Toggle navigation menu"
                        aria-expanded={mobileMenuOpen}
                        aria-controls="mobile-nav-drawer"
                    >
                        <span className="material-symbols-outlined text-[20px]">
                            {mobileMenuOpen ? 'close' : 'menu'}
                        </span>
                    </button>
                    <span className="text-[12px] font-black tracking-[0.2em] text-silver-bright uppercase">SecuScan</span>
                    <span className="w-9 h-9" />
                </div>

                {mobileMenuOpen && (
                    <>
                        <button
                            type="button"
                            className="lg:hidden fixed inset-0 z-50 bg-charcoal-dark/80 backdrop-blur-sm"
                            onClick={() => setMobileMenuOpen(false)}
                            aria-label="Close navigation menu"
                        />
                        <div
                            id="mobile-nav-drawer"
                            ref={drawerRef}
                            role="dialog"
                            aria-modal="true"
                            aria-label="Navigation menu"
                            className="lg:hidden fixed top-14 left-0 right-0 z-50 bg-[var(--bg-secondary)] border-b border-accent-silver/10 p-4 shadow-[0_12px_32px_rgba(0,0,0,0.6)]"
                            onKeyDown={handleDrawerKeyDown}
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
                    </>
                )}

                <main
                    className="flex-1 overflow-auto transition-all duration-300 ease-in-out ml-0 lg:ml-[var(--sidebar-width)] pt-14 lg:pt-0 pb-20 lg:pb-0"
                    style={{ '--sidebar-width': `${desktopSidebarWidth}px` } as React.CSSProperties}
                >
                    {children}
                </main>

                <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 h-16 bg-[var(--bg-secondary)] border-t border-accent-silver/10 grid grid-cols-5 px-1 pb-safe">
                    {mobilePrimaryNav.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) =>
                                `flex flex-col items-center justify-center gap-1 text-[8px] sm:text-[9px] font-bold uppercase tracking-wider overflow-hidden my-1 mx-0.5 rounded-md ${
                                    isActive ? 'text-rag-red bg-rag-red/10' : 'text-silver/70'
                                }`
                            }
                        >
                            <span className="material-symbols-outlined text-[18px]">{item.icon}</span>
                            <span className="truncate w-full text-center px-0.5">{item.label}</span>
                        </NavLink>
                    ))}
                </nav>
            </div>
        </>
    )
}

export default function AppShell({ children }: AppShellProps) {
    return (
        <SidebarProvider>
            <AppShellInner>{children}</AppShellInner>
        </SidebarProvider>
    )
}
