import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface SidebarContextType {
    isExpanded: boolean
    toggleSidebar: () => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

const SIDEBAR_EXPANDED_KEY = 'sidebar-expanded'

/**
 * Read the persisted sidebar expanded flag from localStorage.
 * Corrupted or non-boolean values must not crash the app — default to true.
 */
function readSidebarExpanded(): boolean {
    try {
        const saved = localStorage.getItem(SIDEBAR_EXPANDED_KEY)
        if (saved === null) return true
        const parsed: unknown = JSON.parse(saved)
        return typeof parsed === 'boolean' ? parsed : true
    } catch {
        return true
    }
}

export function SidebarProvider({ children }: { children: ReactNode }) {
    const [isExpanded, setIsExpanded] = useState(readSidebarExpanded)

    useEffect(() => {
        localStorage.setItem(SIDEBAR_EXPANDED_KEY, JSON.stringify(isExpanded))
        window.dispatchEvent(new CustomEvent('sidebar-state-changed', { detail: isExpanded }))
    }, [isExpanded])

    useEffect(() => {
        const handleStorageChange = () => {
            setIsExpanded(readSidebarExpanded())
        }

        const handleSidebarStateChanged = (e: Event) => {
            const detail = (e as CustomEvent).detail
            if (typeof detail === 'boolean') setIsExpanded(detail)
        }

        window.addEventListener('storage', handleStorageChange)
        window.addEventListener('sidebar-state-changed', handleSidebarStateChanged)
        return () => {
            window.removeEventListener('storage', handleStorageChange)
            window.removeEventListener('sidebar-state-changed', handleSidebarStateChanged)
        }
    }, [])

    const toggleSidebar = () => setIsExpanded((prev: boolean) => !prev)

    return (
        <SidebarContext.Provider value={{ isExpanded, toggleSidebar }}>
            {children}
        </SidebarContext.Provider>
    )
}

export function useSidebar() {
    const context = useContext(SidebarContext)
    if (!context) {
        throw new Error('useSidebar must be used within a SidebarProvider')
    }
    return context
}
