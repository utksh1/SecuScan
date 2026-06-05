import React, { useState } from 'react'
import type { AuditEvent } from '../api'
import { parseDateSafe, formatLocaleDate, formatLocaleTime } from '../utils/date'

interface AuditTableProps {
  events: AuditEvent[]
  loading: boolean
}

function eventTone(eventType: string) {
  if (eventType.includes('failed')) return 'bg-rag-red text-black'
  if (eventType.includes('completed')) return 'bg-rag-green text-black'
  if (eventType.includes('running')) return 'bg-rag-amber text-black'
  if (eventType.includes('cancelled')) return 'bg-silver/20 text-silver-bright'
  return 'bg-rag-blue text-black'
}

export default function AuditTable({ events, loading }: AuditTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  if (loading && events.length === 0) {
    return (
      <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 py-24 text-center">
        <p className="text-xs font-black uppercase tracking-[0.3em] text-silver/30">Syncing audit stream</p>
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 py-24 text-center">
        <p className="text-xs font-black uppercase tracking-[0.3em] text-silver/30">No audit events matched</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
      <table className="min-w-full bg-charcoal text-left">
        <thead className="bg-black/60">
          <tr>
            {['Event', 'Plugin', 'Scan', 'Target', 'Actor', 'Timestamp', ''].map((header) => (
              <th key={header} className="px-5 py-4 text-[10px] font-black uppercase tracking-[0.25em] text-silver/40">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {events.map((event) => {
            const timestamp = parseDateSafe(event.timestamp)
            const expanded = expandedId === event.id
            return (
              <React.Fragment key={event.id}>
                <tr
                  onClick={() => setExpandedId(expanded ? null : event.id)}
                  className="cursor-pointer border-t-2 border-black/70 transition-colors hover:bg-silver-bright/5"
                >
                  <td className="px-5 py-5">
                    <span className={`inline-flex px-3 py-1 text-[9px] font-black uppercase tracking-widest ${eventTone(event.event_type)}`}>
                      {event.event_type}
                    </span>
                  </td>
                  <td className="px-5 py-5 font-mono text-xs text-silver-bright">{event.plugin_id || 'system'}</td>
                  <td className="px-5 py-5 font-mono text-[11px] text-silver/50">{event.scan_id || 'n/a'}</td>
                  <td className="max-w-xs truncate px-5 py-5 font-mono text-[11px] text-silver/60">{event.target || 'n/a'}</td>
                  <td className="px-5 py-5 font-mono text-[11px] uppercase text-silver/50">{event.actor || 'system'}</td>
                  <td className="px-5 py-5 font-mono text-[11px] text-silver/60">
                    {formatLocaleDate(timestamp)} // {formatLocaleTime(timestamp)}
                  </td>
                  <td className="px-5 py-5 text-right">
                    <span className="material-symbols-outlined text-silver/40">
                      {expanded ? 'keyboard_arrow_up' : 'keyboard_arrow_down'}
                    </span>
                  </td>
                </tr>
                {expanded && (
                  <tr className="border-t-2 border-black bg-charcoal-dark">
                    <td colSpan={7} className="p-6">
                      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words border-2 border-black bg-black/30 p-5 font-mono text-[11px] leading-relaxed text-silver/70">
                        {JSON.stringify(event.metadata || {}, null, 2)}
                      </pre>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
