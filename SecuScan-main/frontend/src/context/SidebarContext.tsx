import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface SidebarContextType {
    isExpanded: boolean
    toggleSidebar: () => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: ReactNode }) {
    const [isExpanded, setIsExpanded] = useState(() => {
        const saved = localStorage.getItem('sidebar-expanded')
        return saved !== null ? JSON.parse(saved) : true
    })

    useEffect(() => {
        localStorage.setItem('sidebar-expanded', JSON.stringify(isExpanded))
        window.dispatchEvent(new CustomEvent('sidebar-state-changed', { detail: isExpanded }))
    }, [isExpanded])

    useEffect(() => {
        const handleStorageChange = () => {
            const saved = localStorage.getItem('sidebar-expanded')
            if (saved !== null) setIsExpanded(JSON.parse(saved))
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
