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
    }, [isExpanded])

    useEffect(() => {
        const handleStorageChange = (e: StorageEvent) => {
            if (e.key === 'sidebar-expanded' && e.newValue !== null) {
                setIsExpanded(JSON.parse(e.newValue))
            }
        }

        window.addEventListener('storage', handleStorageChange)
        return () => window.removeEventListener('storage', handleStorageChange)
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
