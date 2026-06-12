import React, { useState } from 'react'
import { motion } from 'framer-motion'

export interface ScanSummary {
  task_id: string
  plugin_id: string
  // The API returns the tool column as `tool_name` (DB column name).
  // `tool` is kept optional for compatibility with the Task interface in Scans.tsx.
  tool_name?: string
  tool?: string
  target: string
  created_at?: string | null
  status: string
}

interface ScanComparePickerProps {
  scans: ScanSummary[]
  onCompare: (scanAId: string, scanBId: string) => void
}

function formatScanLabel(scan: ScanSummary): string {
  const toolLabel = (scan.tool_name ?? scan.tool ?? scan.plugin_id ?? 'unknown').toUpperCase()
  const rawDate = scan.created_at
  let dateStr: string
  if (!rawDate) {
    dateStr = 'Unknown Date'
  } else {
    const date = new Date(rawDate)
    dateStr = isNaN(date.getTime())
      ? rawDate
      : date.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  }
  return `${toolLabel} — ${dateStr} [${scan.task_id.slice(0, 8).toUpperCase()}]`
}

export default function ScanComparePicker({ scans, onCompare }: ScanComparePickerProps) {
  const [scanA, setScanA] = useState('')
  const [scanB, setScanB] = useState('')

  const sameSelected = Boolean(scanA && scanB && scanA === scanB)
  const isDisabled = !scanA || !scanB || sameSelected

  function handleCompare() {
    if (!isDisabled) {
      onCompare(scanA, scanB)
    }
  }

  if (scans.length < 2) {
    return (
      <div className="bg-charcoal border-4 border-dashed border-silver-bright/5 p-8 text-center">
        <p className="text-[10px] font-mono text-silver/30 uppercase tracking-widest italic">
          Requires_2+_Completed_Scans_For_Comparison
        </p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.19, 1, 0.22, 1] }}
      className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
    >
      <p className="text-[9px] font-black uppercase tracking-[0.3em] text-silver/40 mb-8 italic">
        Select_Two_Scans_To_Compare
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="space-y-3">
          <label
            htmlFor="scan-a-select"
            className="text-[9px] font-black uppercase tracking-[0.3em] text-silver/40 block italic"
          >
            Baseline_Scan_A
          </label>
          <select
            id="scan-a-select"
            value={scanA}
            onChange={(e) => setScanA(e.target.value)}
            aria-label="Select baseline scan A"
            className="w-full bg-charcoal-dark border-4 border-black text-silver-bright text-[10px] font-mono uppercase p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] focus:outline-none focus:border-rag-blue cursor-pointer"
          >
            <option value="">-- Select_Scan_A --</option>
            {scans.map((scan) => (
              <option key={scan.task_id} value={scan.task_id}>
                {formatScanLabel(scan)}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-3">
          <label
            htmlFor="scan-b-select"
            className="text-[9px] font-black uppercase tracking-[0.3em] text-silver/40 block italic"
          >
            Comparison_Scan_B
          </label>
          <select
            id="scan-b-select"
            value={scanB}
            onChange={(e) => setScanB(e.target.value)}
            aria-label="Select comparison scan B"
            className="w-full bg-charcoal-dark border-4 border-black text-silver-bright text-[10px] font-mono uppercase p-4 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] focus:outline-none focus:border-rag-blue cursor-pointer"
          >
            <option value="">-- Select_Scan_B --</option>
            {scans.map((scan) => (
              <option key={scan.task_id} value={scan.task_id}>
                {formatScanLabel(scan)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {sameSelected && (
        <p className="text-[10px] font-mono text-rag-amber/70 uppercase tracking-widest mb-6 italic">
          Warning: Identical_Scans_Selected
        </p>
      )}

      <button
        onClick={handleCompare}
        disabled={isDisabled}
        aria-label="Run scan diff analysis"
        aria-disabled={isDisabled}
        className={`px-8 py-4 text-[10px] font-black uppercase tracking-widest flex items-center gap-3 transition-all italic ${
          isDisabled
            ? 'bg-charcoal-dark text-silver/20 border-4 border-silver-bright/5 cursor-not-allowed'
            : 'bg-rag-blue text-black border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5'
        }`}
      >
        Run_Diff_Analysis
        <span className="material-symbols-outlined text-sm" aria-hidden="true">
          compare_arrows
        </span>
      </button>
    </motion.div>
  )
}
