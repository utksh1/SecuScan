import React, { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { routes } from '../routes'

interface NavItemProps {
    to: string;
    icon: string;
    label: string;
    isExpanded: boolean;
    highlight?: boolean;
}

const NavItem = ({ to, icon, label, isExpanded, highlight = false }: NavItemProps) => {
    return (
        <NavLink 
            to={to} 
            onClick={(e) => e.stopPropagation()}
            className={({ isActive }) => `
                relative flex items-center transition-all duration-300 group
                ${isExpanded ? 'gap-3 px-5 py-2.5 mx-2 rounded-lg' : 'justify-center py-3 px-2 mx-2 rounded-lg'}
                ${isActive 
                    ? 'bg-accent-silver/10 text-primary shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]' 
                    : highlight
                        ? 'bg-rag-blue/15 border border-rag-blue/30 text-silver-bright hover:bg-rag-blue/25'
                        : 'text-secondary hover:text-primary hover:bg-accent-silver/5'}
            `}
            title={!isExpanded ? label : undefined}
        >
            {({ isActive }) => (
                <>
                    {/* Active Indicator Glow */}
                    {isActive && (
                        <motion.div 
                            layoutId="activeGlow"
                            className="absolute inset-0 bg-rag-red/5 rounded-lg border border-rag-red/20 shadow-[0_0_15px_rgba(255,59,59,0.1)]"
                            initial={false}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        />
                    )}
                    
                    {/* Active Side bar */}
                    {isActive && (
                        <motion.div 
                            layoutId="activeBar"
                            className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-rag-red rounded-r-full shadow-[0_0_10px_rgba(255,59,59,0.5)]"
                            initial={false}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        />
                    )}
                    
                    <span className={`
                        material-symbols-outlined text-[20px] shrink-0 z-10
                        ${isActive ? 'text-rag-red font-medium fill-1' : highlight ? 'text-rag-blue font-medium' : 'font-light'}
                        group-hover:scale-110 transition-transform duration-300
                    `}>
                        {icon}
                    </span>
                    
                    <AnimatePresence mode="wait">
                        {isExpanded && (
                            <motion.span 
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className={`
                                    text-[11px] font-bold tracking-[0.15em] uppercase whitespace-nowrap z-10
                                    ${isActive ? 'text-primary' : highlight ? 'text-silver-bright' : 'text-secondary'}
                                `}
                            >
                                {label}
                            </motion.span>
                        )}
                    </AnimatePresence>
                </>
            )}
        </NavLink>
    )
}

const NavSection = ({ label, isExpanded }: { label: string, isExpanded: boolean }) => (
    <AnimatePresence>
        {isExpanded ? (
            <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="px-6 mt-6 mb-2 flex items-center gap-3"
            >
                <span className="text-[9px] font-black tracking-[0.2em] text-muted uppercase whitespace-nowrap">{label}</span>
                <div className="h-[1px] w-full bg-accent-silver/10" />
            </motion.div>
        ) : (
            <div className="flex justify-center mt-6 mb-2">
                <div className="h-[1px] w-4 bg-accent-silver/10" />
            </div>
        )}
    </AnimatePresence>
)

export default function Sidebar() {
    const [isExpanded, setIsExpanded] = useState(() => {
        const saved = localStorage.getItem('sidebar-expanded')
        return saved !== null ? JSON.parse(saved) : true
    })

    useEffect(() => {
        localStorage.setItem('sidebar-expanded', JSON.stringify(isExpanded))
    }, [isExpanded])

    return (
        <motion.aside 
            initial={false}
            animate={{ width: isExpanded ? 220 : 64 }}
            onClick={() => setIsExpanded(!isExpanded)}
            className={`
                hidden lg:flex flex-col h-screen fixed left-0 top-0 bg-secondary border-r border-accent-silver/10 z-50 
                shadow-[4px_0_24px_rgba(0,0,0,0.4)] overflow-hidden cursor-pointer
            `}
        >
            {/* Header / Logo */}
            <div className={`flex flex-col pt-8 pb-4 mb-4`}>
                <div className={`flex items-center gap-4 px-6`}>
                    <motion.div 
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={(e) => {
                            e.stopPropagation();
                            if (!isExpanded) setIsExpanded(true);
                        }}
                        className={`
                            w-12 h-12 bg-bg-tertiary flex items-center justify-center rounded-xl border border-accent-silver/20
                            shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]
                            ${!isExpanded && 'cursor-pointer'}
                        `}
                    >
                        <span className="material-symbols-outlined text-rag-red text-[24px] glow-red fill-1">shield</span>
                    </motion.div>
                    
                    <AnimatePresence>
                        {isExpanded && (
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                className="flex flex-col leading-none"
                            >
                                <span className="text-[16px] font-black tracking-tighter text-primary italic">SECUSCAN</span>
                                <span className="text-[8px] font-bold tracking-[0.3em] text-rag-red mt-1">LOCAL WORKSPACE</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Navigation Body */}
            <div className="flex-1 flex flex-col overflow-y-auto no-scrollbar py-4">
                <NavItem to={routes.scans} icon="add_circle" label="New Scan" isExpanded={isExpanded} highlight />

                <NavSection label="Monitor" isExpanded={isExpanded} />
                <NavItem to={routes.dashboard} icon="monitoring" label="Dashboard" isExpanded={isExpanded} />
                <NavItem to={routes.attackSurface} icon="radar" label="Surface" isExpanded={isExpanded} />
                <NavItem to={routes.assets} icon="database" label="Assets" isExpanded={isExpanded} />

                <NavSection label="Analyze" isExpanded={isExpanded} />
                <NavItem to={routes.findings} icon="emergency_home" label="Findings" isExpanded={isExpanded} />
                <NavItem to={routes.reports} icon="summarize" label="Reports" isExpanded={isExpanded} />

                <NavSection label="Track" isExpanded={isExpanded} />
                <NavItem to={routes.history} icon="history" label="Activity" isExpanded={isExpanded} />
            </div>

            {/* Bottom Actions */}
            <div className="p-4 mt-auto border-t border-accent-silver/5 bg-bg-primary/30 backdrop-blur-md">
                <NavItem to={routes.settings} icon="settings" label="Settings" isExpanded={isExpanded} />
                <button 
                    onClick={(e) => {
                        e.stopPropagation();
                        setIsExpanded(!isExpanded);
                    }}
                    className="w-full mt-4 py-2 flex items-center justify-center text-muted hover:text-primary transition-colors"
                >
                    <span className="material-symbols-outlined text-[18px]">
                        {isExpanded ? 'keyboard_double_arrow_left' : 'keyboard_double_arrow_right'}
                    </span>
                </button>
            </div>
        </motion.aside>
    )
}
