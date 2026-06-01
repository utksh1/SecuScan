import React, { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  getAuditLogs,
  exportAuditLogs,
  type AuditEntry,
  type AuditQueryParams,
} from '../api'
import { formatDateLong } from '../utils/date'

const EVENT_TYPES = [
  'task_created', 'task_started', 'task_completed', 'task_failed',
  'task_cancelled', 'task_deleted', 'report_downloaded',
]

const SEVERITY_COLORS: Record<string, string> = {
  info: 'text-cyan',
  warning: 'text-amber',
  error: 'text-rag-red',
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.03 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.25 } },
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [filters, setFilters] = useState<AuditQueryParams>({ per_page: 50 })
  const [exporting, setExporting] = useState(false)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getAuditLogs({ ...filters, page })
      setEntries(data.entries)
      setTotalPages(data.total_pages)
      setTotal(data.total)
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const handleExport = async (format: 'csv' | 'json') => {
    setExporting(true)
    try {
      const blob = await exportAuditLogs(filters, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `secuscan-audit-log.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExporting(false)
    }
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-primary uppercase tracking-tight">Audit Log</h1>
          <p className="text-[11px] text-muted font-bold tracking-widest uppercase mt-1">
            {total} event{total !== 1 ? 's' : ''} recorded
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting || loading}
            className="border-4 border-black px-4 py-2 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors disabled:opacity-40"
          >
            {exporting ? 'Exporting...' : 'CSV'}
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting || loading}
            className="border-4 border-black px-4 py-2 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors disabled:opacity-40"
          >
            JSON
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end">
        <div className="space-y-1">
          <label className="text-[9px] font-black uppercase tracking-widest text-muted">Event Type</label>
          <select
            value={filters.event_type || ''}
            onChange={(e) => { setFilters(f => ({ ...f, event_type: e.target.value || undefined })); setPage(1) }}
            className="bg-bg-tertiary border-4 border-black px-3 py-2 text-[11px] font-bold text-primary uppercase tracking-wider outline-none"
          >
            <option value="">All</option>
            {EVENT_TYPES.map(et => (
              <option key={et} value={et}>{et.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[9px] font-black uppercase tracking-widest text-muted">Date From</label>
          <input
            type="date"
            value={filters.date_from || ''}
            onChange={(e) => { setFilters(f => ({ ...f, date_from: e.target.value || undefined })); setPage(1) }}
            className="bg-bg-tertiary border-4 border-black px-3 py-2 text-[11px] font-bold text-primary outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-[9px] font-black uppercase tracking-widest text-muted">Date To</label>
          <input
            type="date"
            value={filters.date_to || ''}
            onChange={(e) => { setFilters(f => ({ ...f, date_to: e.target.value || undefined })); setPage(1) }}
            className="bg-bg-tertiary border-4 border-black px-3 py-2 text-[11px] font-bold text-primary outline-none"
          />
        </div>
        {(filters.event_type || filters.date_from || filters.date_to) && (
          <button
            onClick={() => { setFilters({ per_page: 50 }); setPage(1) }}
            className="border-4 border-black px-3 py-2 text-[10px] font-black uppercase tracking-widest text-rag-red/60 hover:text-rag-red transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-[9px] font-black uppercase tracking-widest text-muted border-b-4 border-black">
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Event</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4">Message</th>
              <th className="py-3 px-4">Task</th>
              <th className="py-3 px-4">Plugin</th>
              <th className="py-3 px-4 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-[11px] font-bold text-muted uppercase tracking-widest">
                  Loading...
                </td>
              </tr>
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-[11px] font-bold text-muted uppercase tracking-widest">
                  No audit events found
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <React.Fragment key={entry.id}>
                  <motion.tr
                    variants={itemVariants}
                    className="border-b border-accent-silver/10 hover:bg-accent-silver/5 transition-colors cursor-pointer"
                    onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                  >
                    <td className="py-3 px-4 text-[11px] font-bold text-primary whitespace-nowrap">
                      {formatDateLong(entry.timestamp)}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-[10px] font-black uppercase tracking-wider bg-bg-tertiary border-2 border-black px-2 py-1">
                        {entry.event_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`text-[10px] font-black uppercase tracking-wider ${SEVERITY_COLORS[entry.severity] || 'text-silver'}`}>
                        {entry.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-[11px] text-secondary max-w-xs truncate">
                      {entry.message}
                    </td>
                    <td className="py-3 px-4 text-[10px] font-mono text-muted">
                      {entry.task_id ? entry.task_id.slice(0, 8) + '...' : '-'}
                    </td>
                    <td className="py-3 px-4 text-[10px] font-mono text-muted">
                      {entry.plugin_id || '-'}
                    </td>
                    <td className="py-3 px-4">
                      <span className="material-symbols-outlined text-[16px] text-muted">
                        {expandedId === entry.id ? 'expand_less' : 'expand_more'}
                      </span>
                    </td>
                  </motion.tr>
                  {expandedId === entry.id && (
                    <tr className="bg-bg-tertiary/50">
                      <td colSpan={7} className="p-4">
                        <pre className="text-[10px] text-secondary font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
                          {JSON.stringify(entry.context_json, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="border-4 border-black px-3 py-2 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors disabled:opacity-30"
          >
            Prev
          </button>
          <span className="text-[11px] font-bold text-muted">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="border-4 border-black px-3 py-2 text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright transition-colors disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}
    </motion.div>
  )
}
