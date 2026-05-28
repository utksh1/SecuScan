import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getAuditLog, exportAuditLog, AuditEntry } from '../api'
import { formatDateLong } from '../utils/date'

const EVENT_TYPES = [
  'scan_created', 'scan_cancelled',
  'report_downloaded', 'task_deleted',
]

const severityTone = (severity: string) => {
  switch (severity) {
    case 'critical': return 'text-rag-red border-rag-red/30 bg-rag-red/10'
    case 'high':     return 'text-rag-amber border-rag-amber/30 bg-rag-amber/10'
    case 'warning':  return 'text-rag-amber border-rag-amber/30 bg-rag-amber/10'
    case 'info':     return 'text-rag-blue border-rag-blue/30 bg-rag-blue/10'
    default:         return 'text-silver/60 border-white/10 bg-white/[0.02]'
  }
}

const eventTone = (event_type: string) => {
  if (event_type.includes('cancel') || event_type.includes('delete') || event_type.includes('clear'))
    return 'text-rag-red'
  if (event_type.includes('created') || event_type.includes('completed'))
    return 'text-rag-green'
  if (event_type.includes('download') || event_type.includes('report'))
    return 'text-rag-blue'
  return 'text-silver/60'
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalItems, setTotalItems] = useState(0)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  // Filters
  const [filterEvent, setFilterEvent] = useState('')
  const [filterPlugin, setFilterPlugin] = useState('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')

  const buildParams = useCallback((overridePage?: number) => {
    const p = new URLSearchParams()
    p.set('page', String(overridePage ?? page))
    p.set('per_page', '50')
    if (filterEvent)    p.set('event_type', filterEvent)
    if (filterPlugin)   p.set('plugin_id', filterPlugin)
    if (filterDateFrom) p.set('date_from', filterDateFrom)
    if (filterDateTo)   p.set('date_to', filterDateTo)
    return p
  }, [page, filterEvent, filterPlugin, filterDateFrom, filterDateTo])

  const load = useCallback(async (overridePage?: number) => {
    setLoading(true)
    try {
      const data = await getAuditLog(buildParams(overridePage))
      setEntries(data.entries)
      setTotalPages(data.pagination.total_pages)
      setTotalItems(data.pagination.total_items)
    } catch (err) {
      console.error('Failed to load audit log', err)
    } finally {
      setLoading(false)
    }
  }, [buildParams])

  useEffect(() => { load() }, [page])

  const handleFilter = () => {
    setPage(1)
    load(1)
  }

  const handleReset = () => {
    setFilterEvent('')
    setFilterPlugin('')
    setFilterDateFrom('')
    setFilterDateTo('')
    setPage(1)
    setTimeout(() => load(1), 0)
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver px-3 py-6 md:px-4 xl:px-5 md:py-8 space-y-8">

      {/* Header */}
      <header className="border-b border-white/8 pb-6">
        <div className="space-y-3">
          <span className="bg-rag-blue text-black px-3 py-1 text-[10px] uppercase tracking-[0.3em] inline-block font-black">
            System_Audit_Trail
          </span>
          <h1 className="text-4xl md:text-6xl text-silver-bright uppercase tracking-tight leading-none italic font-black">
            Audit <span className="text-transparent" style={{ WebkitTextStroke: '1.5px var(--accent-silver-bright)' }}>Log</span>
          </h1>
          <p className="text-sm text-silver/50 font-mono">
            Append-only record of all scan lifecycle events
          </p>
        </div>
      </header>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Events', value: totalItems },
          { label: 'Current Page', value: page },
          { label: 'Total Pages', value: totalPages },
          { label: 'Per Page', value: 50 },
        ].map(({ label, value }) => (
          <div key={label} className="bg-charcoal border border-white/5 p-4">
            <p className="text-[10px] font-black text-silver/30 uppercase tracking-[0.28em] mb-2">{label}</p>
            <p className="text-2xl font-black text-silver-bright italic">{value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="border border-white/8 bg-charcoal p-5 space-y-4">
        <div className="flex items-center gap-4">
          <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Filters</h3>
          <div className="h-px flex-1 bg-white/8" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          <select
            value={filterEvent}
            onChange={e => setFilterEvent(e.target.value)}
            className="bg-black/30 border border-white/10 px-3 py-2 text-sm text-silver-bright outline-none"
          >
            <option value="">All Event Types</option>
            {EVENT_TYPES.map(e => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
          <input
            value={filterPlugin}
            onChange={e => setFilterPlugin(e.target.value)}
            placeholder="Filter by plugin ID..."
            className="bg-black/30 border border-white/10 px-3 py-2 text-sm text-silver-bright outline-none placeholder:text-silver/30"
          />
          <input
            type="date"
            value={filterDateFrom}
            onChange={e => setFilterDateFrom(e.target.value)}
            className="bg-black/30 border border-white/10 px-3 py-2 text-sm text-silver-bright outline-none"
          />
          <input
            type="date"
            value={filterDateTo}
            onChange={e => setFilterDateTo(e.target.value)}
            className="bg-black/30 border border-white/10 px-3 py-2 text-sm text-silver-bright outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleFilter}
            className="bg-rag-blue text-black px-5 py-2 text-[10px] font-black uppercase tracking-[0.26em] italic hover:brightness-110 transition-all"
          >
            Apply_Filters
          </button>
          <button
            onClick={handleReset}
            className="border border-white/10 text-silver/75 px-5 py-2 text-[10px] font-black uppercase tracking-[0.26em] italic hover:bg-white/[0.04] transition-all"
          >
            Reset
          </button>
          <div className="ml-auto flex gap-2">
            <button
              onClick={() => exportAuditLog('csv', buildParams())}
              className="border border-white/10 text-silver/75 px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-white/[0.04] transition-all"
            >
              Export CSV
            </button>
            <button
              onClick={() => exportAuditLog('json', buildParams())}
              className="border border-white/10 text-silver/75 px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-white/[0.04] transition-all"
            >
              Export JSON
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="border border-white/8 bg-charcoal p-5 space-y-4">
        <div className="flex items-center gap-4">
          <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Events</h3>
          <div className="h-px flex-1 bg-white/8" />
          <span className="text-[10px] uppercase tracking-[0.24em] text-silver/40">{entries.length} shown</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-silver-bright/10 border-t-rag-blue animate-spin" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-silver/40 italic py-12 text-center">No audit events found for the selected filters.</p>
        ) : (
          <div className="relative overflow-x-auto border border-white/6 bg-black/20">
            <table className="w-full text-left text-[11px] font-mono border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-silver/40 uppercase tracking-[0.22em] bg-[#0c0c0f]">
                  <th className="px-4 py-3 font-black w-[180px]">Timestamp</th>
                  <th className="px-4 py-3 font-black w-[160px]">Event</th>
                  <th className="px-4 py-3 font-black w-[80px]">Severity</th>
                  <th className="px-4 py-3 font-black">Message</th>
                  <th className="px-4 py-3 font-black w-[120px]">Task ID</th>
                  <th className="px-4 py-3 font-black w-[40px]" />
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {entries.map((entry) => (
                    <React.Fragment key={entry.id}>
                      <motion.tr
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="border-b border-white/5 last:border-0 hover:bg-white/[0.03] transition-colors cursor-pointer"
                        onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                      >
                        <td className="px-4 py-3 text-silver/50 whitespace-nowrap">
                          {formatDateLong(entry.timestamp)}
                        </td>
                        <td className={`px-4 py-3 font-black uppercase tracking-wider ${eventTone(entry.event_type)}`}>
                          {entry.event_type}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 text-[9px] font-black uppercase border ${severityTone(entry.severity)}`}>
                            {entry.severity}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-silver/75 max-w-xs truncate">
                          {entry.message}
                        </td>
                        <td className="px-4 py-3 text-rag-blue/70 font-mono text-[10px] truncate">
                          {entry.task_id ? entry.task_id.split('-')[0].toUpperCase() : '—'}
                        </td>
                        <td className="px-4 py-3 text-silver/30 text-center">
                          {expandedId === entry.id ? '▲' : '▼'}
                        </td>
                      </motion.tr>

                      {/* Expanded context row */}
                      <AnimatePresence>
                        {expandedId === entry.id && (
                          <motion.tr
                            key={`expanded-${entry.id}`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                          >
                            <td colSpan={6} className="px-6 py-4 bg-black/30 border-b border-white/5">
                              <div className="space-y-2">
                                <p className="text-[10px] font-black text-silver/30 uppercase tracking-[0.3em]">Context</p>
                                <pre className="text-[11px] font-mono text-rag-blue/80 whitespace-pre-wrap break-words leading-6">
                                  {JSON.stringify(entry.context, null, 2)}
                                </pre>
                                {entry.plugin_id && (
                                  <p className="text-[10px] text-silver/40 font-mono">
                                    Plugin: <span className="text-silver/70">{entry.plugin_id}</span>
                                  </p>
                                )}
                                {entry.task_id && (
                                  <p className="text-[10px] text-silver/40 font-mono">
                                    Task ID: <span className="text-rag-blue/70">{entry.task_id}</span>
                                  </p>
                                )}
                              </div>
                            </td>
                          </motion.tr>
                        )}
                      </AnimatePresence>
                    </React.Fragment>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className="border border-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/75 disabled:opacity-30 hover:bg-white/[0.04] transition-all"
            >
              ← Prev
            </button>
            <span className="text-[10px] text-silver/40 uppercase tracking-[0.2em]">
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(p => p + 1)}
              className="border border-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] text-silver/75 disabled:opacity-30 hover:bg-white/[0.04] transition-all"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
