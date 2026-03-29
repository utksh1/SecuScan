import React from 'react'
import { motion } from 'framer-motion'

interface ExecutiveStatsBarProps {
  riskLabel: string
  criticalVulns: number
  totalAssets: number
  attackSurface: number
  compliancePercent: number
  riskNote?: string
}

export const ExecutiveStatsBar: React.FC<ExecutiveStatsBarProps> = ({
  riskLabel,
  criticalVulns,
  totalAssets,
  attackSurface,
  compliancePercent,
  riskNote = 'Risk exposure has increased by 12% following recent network expansion.'
}) => {
  const hasCritical = criticalVulns > 0

  return (
    <div className="w-full bg-[var(--bg-secondary)] border-y border-white/5 py-16 grid grid-cols-1 md:grid-cols-4 divide-x divide-white/5">
      {/* 1. Risk Profile */}
      <div className="px-6 first:pl-8">
        <span className="text-xs font-bold text-white/70 uppercase tracking-[0.3em] block mb-6">Status Profile</span>
        <div className="space-y-6">
          <span 
            className="text-7xl font-light text-[var(--rag-amber)] leading-none block" 
            style={{ fontFamily: "'Libre Baskerville', Georgia, serif" }}
          >
            {riskLabel || 'Moderate'}
          </span>
          <p className="text-sm text-white/80 leading-relaxed font-light tracking-wide">
            {riskNote}
          </p>
        </div>
      </div>

      {/* 2. Critical Vulns */}
      <div className="px-6">
        <span className="text-xs font-bold text-white/70 uppercase tracking-[0.3em] block mb-6">Critical Vulns</span>
        <div className="space-y-8">
          <span
            className={`text-8xl font-normal leading-[0.8] block ${hasCritical ? 'text-[var(--rag-red)]' : 'text-white'}`}
            style={{ fontFamily: 'var(--font-display)' }}
          >
            {criticalVulns}
          </span>
          <span className={`text-xs font-bold uppercase tracking-[0.25em] block ${hasCritical ? 'text-[var(--rag-red)]' : 'text-[var(--rag-green)]'}`}>
            {hasCritical ? 'ATTENTION REQUIRED' : 'NO CRITICAL FINDINGS'}
          </span>
        </div>
      </div>

      {/* 3. Total Assets */}
      <div className="px-6">
        <span className="text-xs font-bold text-white/70 uppercase tracking-[0.3em] block mb-6">Total Assets</span>
        <div className="space-y-8">
          <span className="text-8xl font-normal text-white leading-[0.8]" style={{ fontFamily: 'var(--font-display)' }}>
            {totalAssets.toLocaleString()}
          </span>
          <span className="text-xs text-[var(--rag-green)] font-bold uppercase tracking-[0.25em] block">
            {compliancePercent}% COMPLIANT
          </span>
        </div>
      </div>

      {/* 4. Live Attack Surface */}
      <div className="px-6 last:pr-8">
        <span className="text-xs font-bold text-white/70 uppercase tracking-[0.3em] block mb-6">Surface Ledger</span>
        <div className="space-y-8">
          <span className="text-8xl font-normal text-white leading-[0.8]" style={{ fontFamily: 'var(--font-display)' }}>
            {attackSurface.toLocaleString()}
          </span>
          <span className="text-xs text-[var(--rag-blue)] font-bold uppercase tracking-[0.25em] block">
            MONITORING ACTIVE
          </span>
        </div>
      </div>
    </div>
  )
}
