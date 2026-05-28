import React from 'react'
import { motion } from 'framer-motion'
import type { Finding } from '../api'
import { severityConfig } from '../pages/Findings'

export interface DiffFindingCardProps {
  finding: Finding
  variant: 'new' | 'fixed' | 'unchanged' | 'severity-changed'
  severityBefore?: string
}

const variantBorder: Record<DiffFindingCardProps['variant'], string> = {
  new: 'border-rag-red/40',
  fixed: 'border-rag-green/40',
  unchanged: 'border-silver/10',
  'severity-changed': 'border-rag-amber/40',
}

function normalizeSeverity(value: string): string {
  return value in severityConfig ? value : 'info'
}

export default function DiffFindingCard({
  finding,
  variant,
  severityBefore,
}: DiffFindingCardProps) {
  const afterSev = normalizeSeverity(finding.severity)
  const afterConfig = severityConfig[afterSev]

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.19, 1, 0.22, 1] }}
      className={`bg-charcoal border-4 ${variantBorder[variant]} p-6 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1 flex-1 min-w-0">
          <h4 className="text-sm font-black text-silver-bright uppercase tracking-tight leading-tight">
            {finding.title}
          </h4>
          <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest truncate">
            {finding.category} // {finding.target}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {variant === 'severity-changed' && severityBefore && (
            <>
              <span
                className={`px-2 py-0.5 text-[9px] font-black uppercase border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${severityConfig[normalizeSeverity(severityBefore)]?.chip ?? ''}`}
                aria-label={`Previous severity: ${severityBefore}`}
              >
                {severityBefore}
              </span>
              <span className="text-[9px] font-mono text-silver/40" aria-hidden="true">
                →
              </span>
            </>
          )}
          <span
            className={`px-2 py-0.5 text-[9px] font-black uppercase border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${afterConfig.chip}`}
            aria-label={`Severity: ${afterConfig.label}`}
          >
            {afterConfig.label}
          </span>
        </div>
      </div>
    </motion.div>
  )
}
