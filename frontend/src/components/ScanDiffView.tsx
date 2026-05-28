import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ScanDiffResponse } from '../api'
import DiffFindingCard from './DiffFindingCard'

interface ScanDiffViewProps {
  diff: ScanDiffResponse | null
  isLoading: boolean
  error: string | null
  onRetry?: () => void
}

interface SectionConfig {
  key: 'new' | 'fixed' | 'severity-changed' | 'unchanged'
  label: string
  icon: string
  countKey: keyof ScanDiffResponse['summary']
  accentText: string
  accentBg: string
}

const SECTIONS: SectionConfig[] = [
  {
    key: 'new',
    label: 'New_Issues',
    icon: 'add_circle',
    countKey: 'total_new',
    accentText: 'text-rag-red',
    accentBg: 'bg-rag-red/10 border-rag-red/30',
  },
  {
    key: 'fixed',
    label: 'Fixed_Issues',
    icon: 'check_circle',
    countKey: 'total_fixed',
    accentText: 'text-rag-green',
    accentBg: 'bg-rag-green/10 border-rag-green/30',
  },
  {
    key: 'severity-changed',
    label: 'Severity_Changed',
    icon: 'trending_up',
    countKey: 'total_severity_changed',
    accentText: 'text-rag-amber',
    accentBg: 'bg-rag-amber/10 border-rag-amber/30',
  },
  {
    key: 'unchanged',
    label: 'Unchanged',
    icon: 'remove_circle',
    countKey: 'total_unchanged',
    accentText: 'text-silver',
    accentBg: 'bg-silver/5 border-silver/10',
  },
]

interface SectionPanelProps {
  section: SectionConfig
  count: number
  isOpen: boolean
  onToggle: () => void
  children: React.ReactNode
}

function SectionPanel({ section, count, isOpen, onToggle, children }: SectionPanelProps) {
  return (
    <div className="border-4 border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
      <button
        aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${section.label} section`}
        aria-expanded={isOpen}
        onClick={onToggle}
        className={`w-full flex items-center justify-between p-6 border-b-4 border-black ${section.accentBg} hover:opacity-90 transition-opacity`}
      >
        <div className="flex items-center gap-4">
          <span className={`material-symbols-outlined text-base ${section.accentText}`} aria-hidden="true">
            {section.icon}
          </span>
          <span className={`text-xs font-black uppercase tracking-widest ${section.accentText}`}>
            {section.label}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`px-3 py-1 text-[10px] font-black border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] bg-black/20 ${section.accentText}`}
            aria-label={`${count} findings`}
          >
            {count}
          </span>
          <span className="material-symbols-outlined text-sm text-silver/40" aria-hidden="true">
            {isOpen ? 'expand_less' : 'expand_more'}
          </span>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.19, 1, 0.22, 1] }}
            className="overflow-hidden"
          >
            {count > 0 ? (
              <div className="p-6 bg-charcoal space-y-3">{children}</div>
            ) : (
              <div className="p-6 bg-charcoal text-center">
                <p className="text-[10px] font-mono text-silver/30 uppercase tracking-widest italic">
                  No_Findings_In_Category
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function ScanDiffView({ diff, isLoading, error, onRetry }: ScanDiffViewProps) {
  const [openSections, setOpenSections] = useState<Set<string>>(
    new Set(['new', 'fixed', 'severity-changed'])
  )

  function toggleSection(key: string) {
    setOpenSections((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] space-y-6">
        <div className="space-y-2">
          <div className="h-4 w-48 bg-silver/10 animate-pulse" />
          <div className="h-3 w-32 bg-silver/5 animate-pulse" />
        </div>
        {([1, 2, 3] as const).map((i) => (
          <div key={i} className="h-16 border-4 border-black bg-silver/5 animate-pulse" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-rag-red/10 border-4 border-rag-red/30 p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
        <div className="flex items-start justify-between gap-6">
          <div className="space-y-2">
            <p className="text-xs font-black text-rag-red uppercase tracking-widest flex items-center gap-2">
              <span className="material-symbols-outlined text-sm" aria-hidden="true">error</span>
              Diff_Analysis_Failed
            </p>
            <p className="text-[10px] font-mono text-silver/50 uppercase">{error}</p>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              aria-label="Retry diff analysis"
              className="shrink-0 bg-rag-red text-black px-6 py-3 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all flex items-center gap-2 italic"
            >
              Retry
              <span className="material-symbols-outlined text-sm" aria-hidden="true">refresh</span>
            </button>
          )}
        </div>
      </div>
    )
  }

  if (!diff) return null

  const isEmpty =
    diff.summary.total_new === 0 &&
    diff.summary.total_fixed === 0 &&
    diff.summary.total_unchanged === 0 &&
    diff.summary.total_severity_changed === 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.19, 1, 0.22, 1] }}
      className="space-y-8"
    >
      {/* Scan meta */}
      <div className="bg-charcoal border-4 border-black p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] grid grid-cols-1 md:grid-cols-2 gap-8">
        {([diff.scan_a, diff.scan_b] as const).map((scan, i) => (
          <div key={scan.task_id} className="space-y-2">
            <span className="text-[9px] font-black uppercase text-silver/30 tracking-[0.3em] italic block">
              Scan_{String.fromCharCode(65 + i)}
            </span>
            <p className="text-sm font-black text-silver-bright uppercase tracking-tight">{scan.tool}</p>
            <p className="text-[10px] font-mono text-silver/40 uppercase">{scan.target}</p>
            <p className="text-[10px] font-mono text-silver/30">
              {new Date(scan.timestamp).toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {/* Summary bar */}
      <div className="bg-charcoal-dark border-4 border-black p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
        <p className="text-[9px] font-black uppercase tracking-[0.3em] text-silver/30 mb-4 italic">
          Diff_Summary
        </p>
        <div
          className="flex flex-wrap gap-6 text-xs font-black uppercase tracking-widest"
          aria-label="Diff summary"
        >
          <span className="text-rag-red" aria-label={`${diff.summary.total_new} new findings`}>
            {diff.summary.total_new} New
          </span>
          <span className="text-silver/20" aria-hidden="true">·</span>
          <span className="text-rag-green" aria-label={`${diff.summary.total_fixed} fixed findings`}>
            {diff.summary.total_fixed} Fixed
          </span>
          <span className="text-silver/20" aria-hidden="true">·</span>
          <span className="text-silver" aria-label={`${diff.summary.total_unchanged} unchanged findings`}>
            {diff.summary.total_unchanged} Unchanged
          </span>
          <span className="text-silver/20" aria-hidden="true">·</span>
          <span className="text-rag-amber" aria-label={`${diff.summary.total_severity_changed} severity changes`}>
            {diff.summary.total_severity_changed} Severity_Changed
          </span>
        </div>
      </div>

      {isEmpty ? (
        <div className="py-24 bg-charcoal/30 border-4 border-dashed border-silver-bright/5 text-center flex flex-col items-center gap-6">
          <span className="material-symbols-outlined text-silver/10 text-7xl" aria-hidden="true">
            compare_arrows
          </span>
          <div className="space-y-2">
            <p className="text-sm font-black text-silver/20 uppercase tracking-[0.4em] italic">
              Identical_Scans
            </p>
            <p className="text-[10px] font-mono text-silver/10 uppercase tracking-widest">
              No differences found between these scans
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {SECTIONS.map((section) => (
            <SectionPanel
              key={section.key}
              section={section}
              count={diff.summary[section.countKey]}
              isOpen={openSections.has(section.key)}
              onToggle={() => toggleSection(section.key)}
            >
              {section.key === 'new' &&
                diff.diff.new_findings.map((f, i) => (
                  <DiffFindingCard key={f.id ?? `new-${i}`} finding={f} variant="new" />
                ))}
              {section.key === 'fixed' &&
                diff.diff.fixed_findings.map((f, i) => (
                  <DiffFindingCard key={f.id ?? `fixed-${i}`} finding={f} variant="fixed" />
                ))}
              {section.key === 'unchanged' &&
                diff.diff.unchanged_findings.map((f, i) => (
                  <DiffFindingCard key={f.id ?? `unchanged-${i}`} finding={f} variant="unchanged" />
                ))}
              {section.key === 'severity-changed' &&
                diff.diff.severity_changed.map((sc, i) => (
                  <DiffFindingCard
                    key={sc.after.id ?? `sc-${i}`}
                    finding={sc.after}
                    variant="severity-changed"
                    severityBefore={sc.before.severity}
                  />
                ))}
            </SectionPanel>
          ))}
        </div>
      )}
    </motion.div>
  )
}
