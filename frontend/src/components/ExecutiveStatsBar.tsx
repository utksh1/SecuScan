import React from 'react'
import { motion } from 'framer-motion'

interface ExecutiveStatsBarProps {
  riskLabel: string
  criticalVulns: number
  totalFindings: number
  scanActivity: number
  compliancePercent: number
  riskNote?: string
  loading?: boolean
}

function SkeletonBlock({ className = '' }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block bg-white/10 rounded animate-pulse ${className}`}
    />
  )
}

export const ExecutiveStatsBar: React.FC<ExecutiveStatsBarProps> = ({
  riskLabel = 'Moderate',
  criticalVulns = 0,
  totalFindings = 0,
  scanActivity = 0,
  compliancePercent = 100,
  riskNote = 'Risk exposure has increased by 12% following recent network expansion.',
  loading = false,
}) => {
  const criticalCount = Number.isFinite(criticalVulns) ? criticalVulns : 0
  const findingCount = Number.isFinite(totalFindings) ? totalFindings : 0
  const scanCount = Number.isFinite(scanActivity) ? scanActivity : 0
  const compliance = Number.isFinite(compliancePercent) ? compliancePercent : 100
  const hasCritical = criticalCount > 0

  return (
    <div
      className="w-full bg-[var(--bg-secondary)] border-y border-white/5 py-10 md:py-16 grid grid-cols-1 md:grid-cols-4 md:divide-x divide-white/5 gap-y-16 md:gap-y-0"
      aria-busy={loading}
    >
      {/* 1. Risk Profile */}
      <div className="px-6 md:first:pl-8 flex flex-col justify-between">
        <span className="text-xs font-bold text-silver uppercase tracking-[0.3em] block mb-1">Status Profile</span>
        <div className="space-y-2">
          {loading ? (
            <>
              <SkeletonBlock className="h-[4.5rem] w-3/4" />
              <div className="space-y-2">
                <SkeletonBlock className="h-3 w-full" />
                <SkeletonBlock className="h-3 w-5/6" />
              </div>
            </>
          ) : (
            <>
              <span
                className="text-7xl font-light text-[var(--rag-amber)] leading-none block"
                style={{ fontFamily: "'Libre Baskerville', Georgia, serif" }}
              >
                {riskLabel || 'Moderate'}
              </span>
              <p className="text-sm text-silver leading-relaxed font-light tracking-wide">
                {riskNote}
              </p>
            </>
          )}
        </div>
      </div>

      {/* 2. Critical Vulns */}
      <div className="px-6 flex flex-col justify-between">
        <span className="text-xs font-bold text-silver uppercase tracking-[0.3em] block mb-1">Critical Vulns</span>
        <div className="space-y-2">
          {loading ? (
            <>
              <SkeletonBlock className="h-[5rem] w-1/2" />
              <SkeletonBlock className="h-3 w-2/3" />
            </>
          ) : (
            <>
              <span
                className={`text-8xl font-normal leading-[0.8] block ${hasCritical ? 'text-[var(--rag-red)]' : 'text-silver-bright'}`}
                style={{ fontFamily: 'var(--font-display)' }}
              >
                {criticalCount}
              </span>
              <span className={`text-xs font-bold uppercase tracking-[0.25em] block ${hasCritical ? 'text-[var(--rag-red)]' : 'text-[var(--rag-green)]'}`}>
                {hasCritical ? 'ATTENTION REQUIRED' : 'NO CRITICAL FINDINGS'}
              </span>
            </>
          )}
        </div>
      </div>

      {/* 3. Total Findings */}
      <div className="px-6 flex flex-col justify-between">
        <span className="text-xs font-bold text-silver uppercase tracking-[0.3em] block mb-1">Total Findings</span>
        <div className="space-y-2">
          {loading ? (
            <>
              <SkeletonBlock className="h-[5rem] w-1/2" />
              <SkeletonBlock className="h-3 w-2/3" />
            </>
          ) : (
            <>
              <span className="text-8xl font-normal text-silver-bright leading-[0.8]" style={{ fontFamily: 'var(--font-display)' }}>
                {findingCount.toLocaleString()}
              </span>
              <span className="text-xs text-[var(--rag-green)] font-bold uppercase tracking-[0.25em] block">
                {compliance}% COMPLIANT
              </span>
            </>
          )}
        </div>
      </div>

      {/* 4. Scan Activity */}
      <div className="px-6 md:last:pr-8 flex flex-col justify-between">
        <span className="text-xs font-bold text-silver uppercase tracking-[0.3em] block mb-1">Scan Cycles</span>
        <div className="space-y-2">
          {loading ? (
            <>
              <SkeletonBlock className="h-[5rem] w-1/2" />
              <SkeletonBlock className="h-3 w-2/3" />
            </>
          ) : (
            <>
              <span className="text-8xl font-normal text-silver-bright leading-[0.8]" style={{ fontFamily: 'var(--font-display)' }}>
                {scanCount.toLocaleString()}
              </span>
              <span className="text-xs text-[var(--rag-blue)] font-bold uppercase tracking-[0.25em] block">
                MONITORING ACTIVE
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
