import React, { useEffect, useMemo, useState } from 'react'
import { getAuditEvents, getAuditExportUrl, type AuditEvent } from '../api'
import AuditTable from '../components/AuditTable'
import Pagination from '../components/Pagination'

const eventTypes = [
  'all',
  'scan_created',
  'scan_running',
  'scan_completed',
  'scan_failed',
  'scan_cancelled',
  'scan_deleted',
  'report_downloaded',
]

function useDebouncedValue<T>(value: T, delayMs = 350) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(timeout)
  }, [value, delayMs])

  return debounced
}

export default function AuditLog() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [eventType, setEventType] = useState('all')
  const [pluginId, setPluginId] = useState('')
  const [date, setDate] = useState('')
  const PAGE_LIMIT = 20

  const debouncedFilters = useDebouncedValue({ eventType, pluginId, date })

  const params = useMemo(() => {
    const next = new URLSearchParams()
    next.set('page', String(page))
    next.set('per_page', String(PAGE_LIMIT))
    if (debouncedFilters.eventType !== 'all') next.set('event_type', debouncedFilters.eventType)
    if (debouncedFilters.pluginId.trim()) next.set('plugin_id', debouncedFilters.pluginId.trim())
    if (debouncedFilters.date) next.set('date', debouncedFilters.date)
    return next
  }, [page, debouncedFilters])

  useEffect(() => {
    setPage(1)
  }, [debouncedFilters.eventType, debouncedFilters.pluginId, debouncedFilters.date])

  useEffect(() => {
    let cancelled = false

    async function loadAudit() {
      setLoading(true)
      try {
        const data = await getAuditEvents(params)
        if (cancelled) return
        setEvents(data.events || [])
        setTotal(data.pagination?.total_items || 0)
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load audit log:', error)
          setEvents([])
          setTotal(0)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadAudit()
    return () => {
      cancelled = true
    }
  }, [params])

  const exportParams = useMemo(() => {
    const next = new URLSearchParams(params)
    next.delete('page')
    next.delete('per_page')
    return next
  }, [params])

  return (
    <div className="min-h-screen bg-charcoal-dark p-6 text-silver md:p-12">
      <header className="mb-10 flex flex-col gap-6 border-b-4 border-silver-bright/10 pb-10 xl:flex-row xl:items-end xl:justify-between">
        <div className="space-y-4">
          <div className="inline-block bg-rag-blue px-4 py-1 text-xs font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Append_Only_Audit_v1
          </div>
          <h1 className="text-5xl font-black uppercase italic leading-none tracking-tighter text-silver-bright md:text-7xl">
            Audit Log
          </h1>
          <p className="font-mono text-xs uppercase tracking-widest text-silver/40">
            Total_Events: {total} // {loading ? 'STREAM_SYNCING' : 'INDEXED'}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <a
            href={getAuditExportUrl(exportParams, 'csv')}
            className="flex items-center gap-2 border-2 border-black bg-silver-bright px-5 py-3 text-[10px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all hover:translate-x-1 hover:translate-y-1 hover:shadow-none"
          >
            Export_CSV
            <span className="material-symbols-outlined text-sm">download</span>
          </a>
          <a
            href={getAuditExportUrl(exportParams, 'json')}
            className="flex items-center gap-2 border-2 border-rag-blue/40 bg-rag-blue/10 px-5 py-3 text-[10px] font-black uppercase tracking-widest text-rag-blue transition-colors hover:bg-rag-blue hover:text-black"
          >
            Export_JSON
            <span className="material-symbols-outlined text-sm">data_object</span>
          </a>
        </div>
      </header>

      <section className="mb-10 grid gap-4 border-4 border-black bg-charcoal p-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] md:grid-cols-3">
        <label className="space-y-2">
          <span className="block text-[10px] font-black uppercase tracking-[0.25em] text-silver/35">Event_Type</span>
          <select
            value={eventType}
            onChange={(event) => setEventType(event.target.value)}
            className="w-full border-2 border-black bg-charcoal-dark px-4 py-3 font-mono text-xs uppercase text-silver-bright outline-none focus:border-rag-blue"
          >
            {eventTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2">
          <span className="block text-[10px] font-black uppercase tracking-[0.25em] text-silver/35">Plugin_ID</span>
          <input
            value={pluginId}
            onChange={(event) => setPluginId(event.target.value)}
            placeholder="http_inspector"
            className="w-full border-2 border-black bg-charcoal-dark px-4 py-3 font-mono text-xs text-silver-bright outline-none placeholder:text-silver/20 focus:border-rag-blue"
          />
        </label>

        <label className="space-y-2">
          <span className="block text-[10px] font-black uppercase tracking-[0.25em] text-silver/35">Date</span>
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            className="w-full border-2 border-black bg-charcoal-dark px-4 py-3 font-mono text-xs text-silver-bright outline-none focus:border-rag-blue"
          />
        </label>
      </section>

      <AuditTable events={events} loading={loading} />

      {total > PAGE_LIMIT && (
        <Pagination
          page={page}
          total={total}
          limit={PAGE_LIMIT}
          loading={loading}
          onPrev={() => setPage((current) => Math.max(1, current - 1))}
          onNext={() => setPage((current) => current + 1)}
        />
      )}
    </div>
  )
}
