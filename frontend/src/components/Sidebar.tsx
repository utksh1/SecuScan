import React, { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { routes } from '../routes'
import ThemeToggle from './ThemeToggle'
import { useOfflineQueue } from './OfflineQueueContext'

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
            end
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
                <NavItem to={routes.toolkit} icon="add_circle" label="Toolkit" isExpanded={isExpanded} highlight />

                <NavSection label="Monitor" isExpanded={isExpanded} />
                <NavItem to={routes.dashboard} icon="monitoring" label="Dashboard" isExpanded={isExpanded} />
                <NavItem to={routes.scans} icon="history" label="Registry" isExpanded={isExpanded} />

                <NavSection label="Analyze" isExpanded={isExpanded} />
                <NavItem to={routes.findings} icon="emergency_home" label="Findings" isExpanded={isExpanded} />

                <NavItem to={routes.reports} icon="summarize" label="Reports" isExpanded={isExpanded} />
                <NavItem to={routes.workflows} icon="account_tree" label="Workflows" isExpanded={isExpanded} />

            </div>

            {/* Bottom Actions */}
            <div className="p-4 mt-auto border-t border-accent-silver/5 bg-bg-primary/30 backdrop-blur-md space-y-3">
                <OfflineQueueIndicator isExpanded={isExpanded} />
                <NavItem to={routes.settings} icon="settings" label="Settings" isExpanded={isExpanded} />
                <div className="flex items-center gap-2">
                    <ThemeToggle size="sm" />
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            setIsExpanded(!isExpanded);
                        }}
                        className="flex-1 py-2 flex items-center justify-center text-muted hover:text-primary transition-colors"
                    >
                        <span className="material-symbols-outlined text-[18px]">
                            {isExpanded ? 'keyboard_double_arrow_left' : 'keyboard_double_arrow_right'}
                        </span>
                    </button>
                </div>
            </div>
        </motion.aside>
    )
}

function OfflineQueueIndicator({ isExpanded }: { isExpanded: boolean }) {
  const { isOnline, pendingCount, queue, retry, retryAll, remove } = useOfflineQueue()
  const [showDropdown, setShowDropdown] = useState(false)

  if (isOnline && pendingCount === 0) return null

  const handleRetryAll = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`Replay ${pendingCount} pending action(s)? This may create duplicate tasks or workflows.`)) {
      retryAll()
    }
  }

  const handleRetry = (e: React.MouseEvent, id: string, label?: string) => {
    e.stopPropagation()
    if (window.confirm(`Replay "${label || 'action'}"? This may create a duplicate task or workflow.`)) {
      retry(id)
    }
  }

  return (
    <div className="relative mb-2">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setShowDropdown(!showDropdown) }}
        className={`flex items-center w-full transition-all duration-300 group ${
          isExpanded ? 'gap-3 px-5 py-2.5 mx-2 rounded-lg' : 'justify-center py-3 px-2 mx-2 rounded-lg'
        } ${!isOnline ? 'text-rag-amber' : 'text-rag-blue'}`}
        title={!isExpanded ? `${pendingCount} pending` : undefined}
      >
        <span className="material-symbols-outlined text-[20px] shrink-0 z-10 relative">
          {!isOnline ? 'cloud_off' : 'cloud_sync'}
          {pendingCount > 0 && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-rag-amber rounded-full animate-pulse" />
          )}
        </span>
        <AnimatePresence>
          {isExpanded && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="text-[11px] font-bold tracking-[0.15em] uppercase whitespace-nowrap z-10 flex-1 text-left"
            >
              {!isOnline ? 'Offline' : `${pendingCount} Pending`}
            </motion.span>
          )}
        </AnimatePresence>
        {isExpanded && pendingCount > 0 && (
          <span className="text-[9px] font-black text-rag-amber bg-rag-amber/10 px-1.5 py-0.5 rounded z-10">
            {pendingCount}
          </span>
        )}
      </button>

      {showDropdown && pendingCount > 0 && (
        <div
          className="absolute bottom-full left-0 right-0 mb-1 mx-2 bg-secondary border border-accent-silver/10 rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="p-2 space-y-1">
            {queue.map((action) => (
              <div key={action.id} className="flex items-center justify-between gap-2 px-2 py-1 text-[10px] text-silver/80">
                <span className="truncate flex-1">{action.label || action.url}</span>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={(e) => handleRetry(e, action.id, action.label)}
                    className="text-rag-blue/60 hover:text-rag-blue"
                    aria-label={`Replay ${action.label || 'action'}`}
                  >
                    <span className="material-symbols-outlined text-[14px]">replay</span>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); remove(action.id) }}
                    className="text-silver/40 hover:text-rag-red"
                    aria-label={`Remove ${action.label || 'action'} from queue`}
                  >
                    <span className="material-symbols-outlined text-[14px]">close</span>
                  </button>
                </div>
              </div>
            ))}
            <button
              type="button"
              onClick={handleRetryAll}
              className="w-full mt-1 px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider bg-rag-blue/20 text-rag-blue hover:bg-rag-blue/30 rounded"
            >
              Retry All
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
