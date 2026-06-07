import React, { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { routes } from '../routes'

interface NavItemProps {
  to: string
  icon: string
  label: string
  isExpanded: boolean
  highlight?: boolean
}

const NavItem = ({
  to,
  icon,
  label,
  isExpanded,
  highlight = false,
}: NavItemProps) => {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `
        relative flex items-center transition-all duration-300
        ${isExpanded ? 'gap-3 px-5 py-2.5 mx-2 rounded-lg' : 'justify-center py-3 px-2 mx-2 rounded-lg'}
        ${
          isActive
            ? 'bg-accent-silver/10 text-primary'
            : highlight
            ? 'bg-rag-blue/15 border border-rag-blue/30 text-silver-bright'
            : 'text-secondary hover:text-primary hover:bg-accent-silver/5'
        }
      `
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.div
              layoutId="activeBar"
              className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-rag-red rounded-r-full"
            />
          )}

          <span
            className={`material-symbols-outlined text-[20px] shrink-0 ${
              isActive ? 'text-rag-red' : ''
            }`}
          >
            {icon}
          </span>

          <AnimatePresence>
            {isExpanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[11px] font-bold tracking-[0.15em] uppercase"
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

const NavSection = ({
  label,
  isExpanded,
}: {
  label: string
  isExpanded: boolean
}) => (
  <AnimatePresence>
    {isExpanded ? (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="px-6 mt-6 mb-2"
      >
        <span className="text-[9px] font-black tracking-[0.2em] text-muted uppercase">
          {label}
        </span>
      </motion.div>
    ) : null}
  </AnimatePresence>
)

export default function Sidebar() {
  const [isExpanded, setIsExpanded] = useState(() => {
    const saved = localStorage.getItem('sidebar-expanded')
    return saved ? JSON.parse(saved) : true
  })

  useEffect(() => {
    localStorage.setItem('sidebar-expanded', JSON.stringify(isExpanded))
  }, [isExpanded])

  return (
    <motion.aside
      animate={{ width: isExpanded ? 220 : 64 }}
      className="hidden lg:flex flex-col h-screen fixed left-0 top-0 bg-secondary border-r border-accent-silver/10 z-50"
    >
      <div className="pt-8 pb-4 px-6">
        <span className="text-[16px] font-black text-primary italic">
          SECUSCAN
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">

        <NavItem
          to={routes.toolkit}
          icon="add_circle"
          label="Toolkit"
          isExpanded={isExpanded}
          highlight
        />

        <NavSection label="Monitor" isExpanded={isExpanded} />

        <NavItem
          to={routes.dashboard}
          icon="monitoring"
          label="Dashboard"
          isExpanded={isExpanded}
        />

        <NavItem
          to={routes.scans}
          icon="history"
          label="Registry"
          isExpanded={isExpanded}
        />

        <NavSection label="Analyze" isExpanded={isExpanded} />

        <NavItem
          to={routes.findings}
          icon="emergency_home"
          label="Findings"
          isExpanded={isExpanded}
        />

        <NavItem
          to={routes.reports}
          icon="summarize"
          label="Reports"
          isExpanded={isExpanded}
        />

        <NavItem
          to={routes.analytics}
          icon="analytics"
          label="Analytics"
          isExpanded={isExpanded}
        />

        <NavItem
          to={routes.workflows}
          icon="account_tree"
          label="Workflows"
          isExpanded={isExpanded}
        />
      </div>

      <div className="p-4 border-t border-accent-silver/10">
        <NavItem
          to={routes.settings}
          icon="settings"
          label="Settings"
          isExpanded={isExpanded}
        />

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full mt-4"
        >
          <span className="material-symbols-outlined">
            {isExpanded
              ? 'keyboard_double_arrow_left'
              : 'keyboard_double_arrow_right'}
          </span>
        </button>
      </div>
    </motion.aside>
  )
}