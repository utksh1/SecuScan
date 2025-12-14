import React, { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'

export default function Sidebar() {
    const [isExpanded, setIsExpanded] = useState(() => {
        const saved = localStorage.getItem('sidebar-expanded')
        return saved !== null ? JSON.parse(saved) : true
    })

    useEffect(() => {
        localStorage.setItem('sidebar-expanded', JSON.stringify(isExpanded))
    }, [isExpanded])

    const navItem = (to: string, icon: string, label: string) => (
        <NavLink 
            to={to} 
            className={({ isActive }) => `
                relative flex items-center transition-all duration-200 group
                ${isExpanded ? 'gap-4 px-6 py-3 rounded-sm' : 'justify-center py-3.5 w-full'}
                ${isActive ? 'bg-silver/5 text-silver-bright' : 'text-silver/40 hover:text-silver-bright hover:bg-silver/5'}
            `}
            title={!isExpanded ? label : undefined}
        >
            {({ isActive }) => (
                <>
                    {/* Active Indicator */}
                    {isActive && (
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-rag-red rounded-r-full shadow-[0_0_12px_rgba(239,68,68,0.4)]" />
                    )}
                    
                    <span className="material-symbols-outlined text-[20px] shrink-0 font-light">{icon}</span>
                    {isExpanded && <span className="text-[11px] font-bold tracking-[0.1em] uppercase whitespace-nowrap">{label}</span>}
                </>
            )}
        </NavLink>
    )

    return (
        <aside 
            className={`
                hidden lg:flex flex-col h-screen fixed left-0 top-0 bg-charcoal border-r border-accent-silver/20 z-50 
                transition-all duration-300 ease-in-out
                ${isExpanded ? 'w-64' : 'w-20'}
                py-8
            `}
        >
            {/* Header / Logo */}
            <div className={`flex ${isExpanded ? 'flex-row items-center justify-between px-6' : 'flex-col items-center gap-8'} mb-14 w-full`}>
                <div className="flex items-center gap-4">
                    <div 
                        onClick={() => !isExpanded && setIsExpanded(true)}
                        className={`
                            w-10 h-10 bg-silver/10 flex items-center justify-center rounded-sm border border-silver/5 
                            ${!isExpanded && 'cursor-pointer hover:bg-silver/15 transition-colors'}
                        `}
                    >
                        <span className="material-symbols-outlined text-silver-bright text-[22px]">shield</span>
                    </div>
                    {isExpanded && (
                        <div className="flex flex-col leading-none">
                            <span className="text-[13px] font-black tracking-tight text-silver-bright">SECUSCAN</span>
                            <span className="text-[9px] font-medium tracking-[0.15em] text-silver/40">EXECUTIVE SUITE</span>
                        </div>
                    )}
                </div>
                
                <button 
                    onClick={() => setIsExpanded(!isExpanded)}
                    className={`
                        p-1 hover:bg-silver/10 rounded transition-colors text-silver/30 group
                        ${isExpanded ? '' : 'opacity-40 hover:opacity-100'}
                    `}
                >
                    <span className={`material-symbols-outlined text-[18px] transition-transform duration-300 ${isExpanded ? 'rotate-0' : 'rotate-180'}`}>
                        {isExpanded ? 'menu_open' : 'menu'}
                    </span>
                </button>
            </div>

            {/* Navigation Body */}
            <div className="flex-1 flex flex-col gap-10 overflow-y-auto no-scrollbar w-full translate-z-0">
                {/* Monitoring Section */}
                <div className="flex flex-col gap-1 w-full">
                    {isExpanded && <h3 className="px-6 text-[9px] font-black text-silver/20 tracking-[0.2em] mb-3">MONITORING</h3>}
                    {navItem("/", "dashboard", "Center")}
                    {navItem("/attack-surface", "radar", "Surface")}
                    {navItem("/assets", "lan", "Assets")}
                </div>

                {/* Analysis Section */}
                <div className="flex flex-col gap-1 w-full">
                    {isExpanded && <h3 className="px-6 text-[9px] font-black text-silver/20 tracking-[0.2em] mb-3">ANALYSIS</h3>}
                    {navItem("/scans", "search", "Scanner")}
                    {navItem("/findings", "warning", "Findings")}
                    {navItem("/history", "history", "Log")}
                    {navItem("/compare", "compare_arrows", "Diff")}
                </div>

                {/* System Section */}
                <div className="flex flex-col gap-1 w-full">
                    {isExpanded && <h3 className="px-6 text-[9px] font-black text-silver/20 tracking-[0.2em] mb-3">SYSTEM</h3>}
                    {navItem("/reports", "description", "Reports")}
                    {navItem("/settings", "settings", "Settings")}
                </div>
            </div>

            {/* Footer */}
            <div className="pt-6 border-t border-silver/5 flex flex-col gap-4 mt-auto w-full">
                <button className={`
                    flex items-center gap-4 transition-colors text-silver/40 hover:text-silver-bright group w-full
                    ${isExpanded ? 'px-6 py-3 hover:bg-silver/5 rounded' : 'justify-center py-4'}
                `}>
                    <span className="material-symbols-outlined text-[20px] shrink-0">account_circle</span>
                    {isExpanded && (
                        <div className="flex flex-col items-start leading-none overflow-hidden">
                            <span className="text-[11px] font-bold truncate w-full">AGENT_0x772</span>
                            <span className="text-[9px] opacity-40 truncate w-full italic">clearance_alpha</span>
                        </div>
                    )}
                </button>
                <Link to="/login" className={`
                    flex items-center gap-4 transition-colors text-silver/40 hover:text-rag-red group w-full
                    ${isExpanded ? 'px-6 py-3 hover:bg-rag-red/10 rounded' : 'justify-center py-4'}
                `}>
                    <span className="material-symbols-outlined text-[20px] shrink-0">logout</span>
                    {isExpanded && <span className="text-[11px] font-bold tracking-[0.1em] uppercase">Terminate</span>}
                </Link>
            </div>
        </aside>
    )
}
