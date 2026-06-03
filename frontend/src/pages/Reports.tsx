import React, { useEffect, useRef, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useVirtualizer } from '@tanstack/react-virtual'
import { getDashboardSummary, getReports, API_BASE } from '../api'
import { formatDateLong } from '../utils/date'

type Report = {
  id: string
  task_id: string
  name: string
  type: 'executive' | 'technical' | 'compliance'
  generated_at: string
  status: 'ready' | 'generating' | 'failed'
  findings: number
  assets: number
  pages: number
}

// Pair reports into rows of 2 for the 2-col grid
type ReportRow = [Report, Report | null]

const CARD_HEIGHT = 380 // px — estimated height per grid row

export default function Reports() {
  const navigate = useNavigate()
  const [reports, setReports] = useState<Report[]>([])
  const [summary, setSummary] = useState<any>({ total_findings: 0, total_assets: 0, critical_findings: 0, high_findings: 0, total_attack_surface: 0 })
  const [selectedType, setSelectedType] = useState('all')

  const fetchReports = () => {
    Promise.all([getReports(), getDashboardSummary()]).then(([reportData, summaryData]: any) => {
      setReports(reportData.reports || [])
      setSummary(summaryData || {})
    })
  }

  useEffect(() => {
    fetchReports()
  }, [])

  const filteredReports = reports.filter((report) => selectedType === 'all' || report.type === selectedType)

  // Chunk filtered reports into rows of 2 for the virtual grid
  const reportRows = useMemo<ReportRow[]>(() => {
    const rows: ReportRow[] = []
    for (let i = 0; i < filteredReports.length; i += 2) {
      rows.push([filteredReports[i], filteredReports[i + 1] ?? null])
    }
    return rows
  }, [filteredReports])

  // ─── Virtualizer ────────────────────────────────────────────────────────────
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: reportRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => CARD_HEIGHT,
    overscan: 3,
  })

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">

      {/* Neo-Brutalist Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
        <div className="space-y-4">
          <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
            Archive_Matrix v8.2
          </div>
          <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
            Analytics <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Archive</span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
            HISTORICAL_BRIEFINGS // ENCRYPTED_DOSSIERS // AUDIT_FEED
          </p>
        </div>

        <div className="flex items-center gap-6">
          <button
            onClick={fetchReports}
            className="bg-charcoal border-4 border-black p-4 text-silver-bright shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            title="Refresh Archive"
          >
            <span className="material-symbols-outlined">sync</span>
          </button>
          <button
            onClick={() => window.open(`${API_BASE}/task/latest/report/pdf`, '_blank')}
            className="bg-silver-bright border-4 border-black p-4 text-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            title="Download Latest Briefing"
          >
            <span className="material-symbols-outlined">cloud_download</span>
          </button>
        </div>
      </header>

      {/* Metrics Row */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {[
          { label: 'Archived_Briefings', val: reports.length, color: 'bg-rag-blue', unit: 'FILES' },
          { label: 'Surface_Nodes', val: summary.total_assets || 0, color: 'bg-rag-green', unit: 'NODES' },
          { label: 'Aggregate_Anomalies', val: summary.total_findings || 0, color: 'bg-rag-red', unit: 'TRIGGERS' },
          { label: 'Archive_Volume', val: '12.4', color: 'bg-rag-amber', unit: 'GB' },
        ].map((m, i) => (
          <div key={i} className={`${m.color} border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between h-40 group hover:-translate-y-1 transition-transform`}>
            <div className="flex justify-between items-start">
              <span className="text-[10px] font-black text-black uppercase tracking-[0.2em] italic">{m.label}</span>
              <span className="material-symbols-outlined text-black/20 group-hover:text-black transition-colors">folder_zip</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-5xl font-black text-black font-mono leading-none tracking-tighter">{m.val}</span>
              <span className="text-[10px] font-black text-black/40 uppercase tracking-widest">{m.unit}</span>
            </div>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-12">
        {/* Filtration Sidebar */}
        <aside className="xl:col-span-1 space-y-12">
          <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
            <div className="space-y-4">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Classification_Isolation</label>
              <div className="grid grid-cols-1 gap-2">
                {['all', 'executive', 'technical', 'compliance'].map(t => (
                  <button
                    key={t}
                    onClick={() => setSelectedType(t)}
                    className={`px-6 py-4 text-left text-[10px] font-black uppercase tracking-widest border-4 transition-all flex justify-between items-center ${selectedType === t
                        ? 'bg-rag-red border-black text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                        : 'bg-charcoal-dark border-black text-silver/40 hover:border-silver-bright/20'
                      }`}
                  >
                    {t} BRIEFINGS
                    {selectedType === t && <span className="material-symbols-outlined text-sm">check</span>}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3 border-t border-black/20 pt-6">
              <p className="text-[9px] font-black text-silver/20 uppercase tracking-widest italic">Enclave_Notice</p>
              <p className="text-[10px] text-silver/40 font-black uppercase tracking-widest leading-loose italic">
                Dossiers are cryptographically hashed and recorded. Modifications are strictly detectable by the Enclave audit daemon.
              </p>
            </div>
          </section>
        </aside>

        {/* Virtualized Ledger Section */}
        <main className="xl:col-span-3 space-y-8">
          <div className="flex flex-col md:flex-row justify-between items-end gap-6 border-b-4 border-black pb-8">
            <h2 className="text-5xl font-black text-silver-bright italic uppercase tracking-tighter shrink-0">Historical_Ledger</h2>
            <div className="h-0.5 bg-black/10 flex-1 mb-2 hidden md:block"></div>
            <span className="text-[10px] font-mono text-silver/20 uppercase font-black mb-2 animate-pulse">{filteredReports.length} ENTRIES_LOCATED</span>
          </div>

          {filteredReports.length === 0 ? (
            <div className="col-span-2 py-40 border-4 border-dashed border-black/5 text-center flex flex-col items-center gap-8 bg-charcoal/30">
              <span className="material-symbols-outlined text-silver/5 text-9xl">folder_off</span>
              <div className="space-y-2">
                <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">Archive Isolated</p>
                <p className="text-xs font-mono text-silver/10 uppercase tracking-widest leading-relaxed">System buffer awaiting briefing generation protocols</p>
              </div>
            </div>
          ) : (
            /* Scrollable virtual window */
            <div
              ref={parentRef}
              style={{ height: '75vh', overflowY: 'auto' }}
            >
              <div style={{ height: virtualizer.getTotalSize(), width: '100%', position: 'relative' }}>
                {virtualizer.getVirtualItems().map((virtualItem) => {
                  const [left, right] = reportRows[virtualItem.index]

                  return (
                    <div
                      key={virtualItem.key}
                      data-index={virtualItem.index}
                      ref={virtualizer.measureElement}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        transform: `translateY(${virtualItem.start}px)`,
                        paddingBottom: '2rem',
                      }}
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {[left, right].map((report, colIdx) =>
                          report ? (
                            <ReportCard
                              key={report.id}
                              report={report}
                              onNavigate={() => navigate(`/task/${report.task_id}`)}
                              onDownload={() => window.open(`${API_BASE}/task/${report.task_id}/report/pdf`, '_blank')}
                            />
                          ) : (
                            // Empty cell to keep grid alignment
                            <div key={`empty-${colIdx}`} />
                          )
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Tactical Footer */}
      <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
        <div className="flex items-center gap-6">
          <div className="w-12 h-1 bg-silver/20"></div>
          RESTRICTED_ACCESS_ENCLAVE // SYSTEM_ARCHIVE_DAEMON // {new Date().getFullYear()}
        </div>
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map(i => <div key={i} className="w-2 h-2 bg-silver/20 rounded-full"></div>)}
        </div>
      </footer>
    </div>
  )
}

// ─── Extracted ReportCard to keep virtualizer render lean ──────────────────

interface ReportCardProps {
  report: Report
  onNavigate: () => void
  onDownload: () => void
}

function ReportCard({ report, onNavigate, onDownload }: ReportCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.97, y: 12 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="group bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-[14px_14px_0px_0px_rgba(0,0,0,1)] transition-all relative overflow-hidden"
    >
      {/* Status Top Bar */}
      <div className={`absolute top-0 left-0 h-2 transition-all duration-500 ${report.status === 'ready' ? 'bg-rag-green w-full' :
          report.status === 'failed' ? 'bg-rag-red w-full' : 'bg-rag-amber w-1/2 animate-pulse'
        }`}></div>

      <div className="space-y-8 relative z-10">
        <div className="flex justify-between items-start">
          <span className={`px-2 py-0.5 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${report.type === 'executive' ? 'bg-silver-bright text-black' :
              report.type === 'compliance' ? 'bg-rag-green text-black' :
                'bg-rag-blue text-black'
            }`}>
            {report.type}_TYPE
          </span>
          <span className="material-symbols-outlined text-silver/10 group-hover:text-silver-bright transition-colors text-2xl">description</span>
        </div>

        <div>
          <h3 className="text-3xl font-black text-silver-bright uppercase tracking-tighter italic leading-tight group-hover:text-rag-red transition-colors font-mono">
            {report.name}
          </h3>
          <div className="w-12 h-1 bg-silver-bright/10 mt-6 group-hover:w-full group-hover:bg-rag-red/30 transition-all duration-700"></div>
        </div>

        <div className="grid grid-cols-3 gap-6 py-6 border-y-2 border-black border-dashed">
          <div className="space-y-1">
            <span className="text-[8px] font-black text-silver/20 uppercase tracking-widest italic block">Findings</span>
            <span className="text-xs font-black font-mono text-silver-bright">{report.findings.toString().padStart(3, '0')}</span>
          </div>
          <div className="space-y-1 text-center">
            <span className="text-[8px] font-black text-silver/20 uppercase tracking-widest italic block">Assets</span>
            <span className="text-xs font-black font-mono text-silver-bright">{report.assets.toString().padStart(3, '0')}</span>
          </div>
          <div className="space-y-1 text-right">
            <span className="text-[8px] font-black text-silver/20 uppercase tracking-widest italic block">Pages</span>
            <span className="text-xs font-black font-mono text-silver-bright">{report.pages.toString().padStart(3, '0')}</span>
          </div>
        </div>

        <div className="flex justify-between items-end pt-2">
          <div className="space-y-1">
            <p className="text-[8px] font-black uppercase text-silver/20 tracking-[0.3em] italic leading-none">TIMESTAMP</p>
            <p className="text-[10px] font-mono text-silver-bright uppercase font-black">{formatDateLong(report.generated_at)}</p>
          </div>
          <div className="flex gap-4">
            <button
              onClick={onNavigate}
              className="bg-charcoal-dark border-4 border-black p-3 text-silver/20 group-hover:text-silver-bright group-hover:bg-black transition-all"
              title="View Briefing"
            >
              <span className="material-symbols-outlined text-sm">visibility</span>
            </button>
            <button
              onClick={onDownload}
              className="bg-charcoal-dark border-4 border-black p-3 text-silver/20 group-hover:text-silver-bright group-hover:bg-black transition-all"
              title="Download PDF"
            >
              <span className="material-symbols-outlined text-sm">download</span>
            </button>
          </div>
        </div>
      </div>

      {/* Background Hover Icon */}
      <div className="absolute -right-12 -bottom-12 opacity-0 group-hover:opacity-[0.03] transition-all duration-1000 transform scale-150 rotate-12 pointer-events-none">
        <span className="material-symbols-outlined text-[200px] text-silver-bright">
          {report.type === 'executive' ? 'leaderboard' : report.type === 'compliance' ? 'verified_user' : 'terminal'}
        </span>
      </div>
    </motion.div>
  )
}