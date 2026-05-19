import React from 'react'
import { motion } from 'framer-motion'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Archive02Icon,
  File01Icon,
  Inbox01Icon,
  ZapOffIcon,
  AlertCircleIcon,
} from '@hugeicons/core-free-icons'

interface EmptyStateProps {
  type?: 'scans' | 'reports' | 'findings' | 'assets' | 'generic'
  title?: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

function EmptyIcon({
  icon,
  size = 48,
  className = '',
}: {
  icon: any
  size?: number
  className?: string
}) {
  return <HugeiconsIcon icon={icon} size={size} strokeWidth={1.9} className={className} />
}

const emptyStateConfigs = {
  scans: {
    icon: Inbox01Icon,
    title: 'No Scans Available',
    description: 'Start a new scan to begin analyzing your targets and identifying vulnerabilities.',
    defaultAction: 'Start Scan'
  },
  reports: {
    icon: File01Icon,
    title: 'No Reports Generated',
    description: 'Complete a scan first to generate detailed security reports and findings.',
    defaultAction: 'Run Scan'
  },
  findings: {
    icon: AlertCircleIcon,
    title: 'No Findings Detected',
    description: 'Great news! No security issues were found in this scan.',
    defaultAction: 'View Scans'
  },
  assets: {
    icon: Archive02Icon,
    title: 'No Assets Discovered',
    description: 'Assets will appear here once scans complete and targets are identified.',
    defaultAction: 'Start Discovery'
  },
  generic: {
    icon: ZapOffIcon,
    title: 'No Data Available',
    description: 'There is currently no data to display.',
    defaultAction: 'Refresh'
  }
}

const containerVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.4, type: 'spring', stiffness: 200, damping: 20 }
  }
}

export default function EmptyState({
  type = 'generic',
  title,
  description,
  action,
  className = ''
}: EmptyStateProps) {
  const config = emptyStateConfigs[type]
  const displayTitle = title || config.title
  const displayDescription = description || config.description

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={`py-20 px-8 text-center ${className}`}
    >
      <div className="flex flex-col items-center gap-8 max-w-2xl mx-auto">
        {/* Icon Container */}
        <div className="p-6 border-4 border-dashed border-silver-bright/20 bg-charcoal/50">
          <EmptyIcon icon={config.icon} size={64} className="text-silver/30" />
        </div>

        {/* Text Content */}
        <div className="space-y-4">
          <h3 className="text-3xl md:text-4xl font-black text-silver-bright uppercase tracking-tighter italic">
            {displayTitle}
          </h3>
          <p className="text-sm md:text-base font-mono text-silver/50 uppercase tracking-widest leading-relaxed italic">
            {displayDescription}
          </p>
        </div>

        {/* Action Button */}
        {action && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={action.onClick}
            className="mt-8 px-8 py-4 bg-rag-blue text-black font-black uppercase text-xs tracking-widest border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transition-all"
          >
            {action.label}
          </motion.button>
        )}

        {/* Decorative Elements */}
        <div className="pt-8 border-t-4 border-dashed border-silver-bright/10 w-full">
          <p className="text-[10px] font-black text-silver/20 uppercase tracking-[0.3em] italic">
            STATUS: IDLE // NO_ACTIVE_OPERATIONS
          </p>
        </div>
      </div>
    </motion.div>
  )
}

export function EmptyStateInline({
  type = 'generic',
  title,
  description,
  className = ''
}: Omit<EmptyStateProps, 'action'>) {
  const config = emptyStateConfigs[type]
  const displayTitle = title || config.title
  const displayDescription = description || config.description

  return (
    <div className={`py-12 px-6 text-center border-4 border-dashed border-silver-bright/10 bg-charcoal-dark/30 ${className}`}>
      <div className="flex flex-col items-center gap-6">
        <EmptyIcon icon={config.icon} size={40} className="text-silver/20" />
        <div className="space-y-2">
          <p className="text-sm font-black text-silver/40 uppercase tracking-widest">{displayTitle}</p>
          <p className="text-xs font-mono text-silver/30 uppercase tracking-widest">{displayDescription}</p>
        </div>
      </div>
    </div>
  )
}
