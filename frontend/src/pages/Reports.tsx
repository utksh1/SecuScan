import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Analytics02Icon,
  Archive02Icon,
  Download01Icon,
  File01Icon,
  KnightShieldIcon,
  Radar02Icon,
  Refresh01Icon,
  ScanEyeIcon,
  ShieldUserIcon,
  UserShield02Icon,
} from '@hugeicons/core-free-icons'
import { getDashboardSummary, getReports, API_BASE } from '../api'
import { formatDateLong, isWithinDateRange, type DateRange } from '../utils/date'
import { usePreferredExportFormat } from '../hooks/usePreferredExportFormat'

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

type ReportStatus = 'all' | 'ready' | 'generating' | 'failed'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.4 },
  },
}

const exportFormats = ['pdf', 'html', 'csv' , 'sarif'] as const

function ReportIcon({
  icon,
  size = 20,
  className = '',
}: {
  icon: any
  size?: number
  className?: string
}) {
  return <HugeiconsIcon icon={icon} size={size} strokeWidth={1.9} className={className} />
}

export default function Reports() {
  const navigate = useNavigate()
  const [reports, setReports] = useState<Report[]>([])
  const [summary, setSummary] = useState<any>({ total_findings: 0, total_assets: 0, critical_findings: 0, high_findings: 0, total_attack_surface: 0 })
  const [selectedType, setSelectedType] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState<ReportStatus>('all')
  const [selectedDateRange, setSelectedDateRange] = useState<DateRange>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { preferred, savePreference } = usePreferredExportFormat()

  const fetchReports = () => {
    setLoading(true)
    setError(null)
    Promise.all([getReports(), getDashboardSummary()])
      .then(([reportData, summaryData]: any) => {
        setReports(reportData.reports || [])
        setSummary(summaryData || {})
      })
      .catch(() => {
        setError('Failed to fetch reports')
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    fetchReports()
  }, [])

  const filteredReports = reports.filter((report) =>
    (selectedType === 'all' || report.type === selectedType) &&
    (selectedStatus === 'all' || report.status === selectedStatus) &&
    isWithinDateRange(report.generated_at, selectedDateRange)
  )

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      {/* Neo-Brutalist Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
        <div className="space-y-4">
          <div className="bg-rag-amber text-slate-800 px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
            Archive_Matrix v8.2
          </div>
          <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
            Analytics <span className="text-transparent [ -webkit-text-stroke:1px_#64748b ] opacity-90" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Archive</span>
          </h1>
          <p className="text-sm font-mono text-silver/100 uppercase tracking-widest italic leading-relaxed">
            HISTORICAL_BRIEFINGS // ENCRYPTED_DOSSIERS // AUDIT_FEED
          </p>
        </div>

        <div className="flex items-center gap-6">
          <button
            onClick={fetchReports}
            className="bg-charcoal border-4 border-slate-300  p-4 text-silver-bright shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            title="Refresh Archive"
          >
            <ReportIcon icon={Refresh01Icon} className="block" aria-hidden="true" />
          </button>
        </div>
      </header>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-40 gap-6">
          <div className="animate-spin">
            <ReportIcon icon={Refresh01Icon} size={48} className="text-silver/80" />
            <ReportIcon icon={Refresh01Icon} size={48} className="text-silver/20" aria-hidden="true" />
          </div>
          <p className="text-[10px] font-black text-silver/80 uppercase tracking-[0.4em] italic animate-pulse">
            Retrieving Archive Data...
          </p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="border-4 border-rag-red bg-rag-red/10 p-8 flex items-center gap-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
          <div className="space-y-1">
            <p className="text-xs font-black text-rag-red uppercase tracking-widest">Archive_Retrieval_Failed</p>
            <p className="text-[10px] font-mono text-silver/100 uppercase tracking-widest">{error}</p>
          </div>
          <button
            onClick={fetchReports}
            className="ml-auto bg-rag-red border-4 border-slate-300  px-6 py-3 text-[9px] font-black uppercase tracking-widest text-slate-800 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Metrics Row */}
          <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { label: 'Archived_Briefings', val: reports.length, color: 'bg-rag-blue', unit: 'FILES' },
              { label: 'Surface_Nodes', val: summary.total_assets || 0, color: 'bg-rag-green', unit: 'NODES' },
              { label: 'Aggregate_Anomalies', val: summary.total_findings || 0, color: 'bg-rag-red', unit: 'TRIGGERS' },
              { label: 'Archive_Volume', val: '12.4', color: 'bg-rag-amber', unit: 'GB' },
            ].map((m, i) => (
              <div key={i} className={`${m.color} border-4 border-slate-300  p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between h-40 group hover:-translate-y-1 transition-transform`}>
                <div className="flex justify-between items-start">
  <span className="text-[10px] font-black text-slate-800 uppercase tracking-[0.2em] italic">
    {m.label}
  </span>

  <ReportIcon
    icon={Archive02Icon}
    className="text-slate-800/80 group-hover:text-slate-800 transition-colors"
    aria-hidden="true"
  />
</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-black text-slate-800 font-mono leading-none tracking-tighter">{m.val}</span>
                  <span className="text-[10px] font-black text-slate-800/100 uppercase tracking-widest">{m.unit}</span>
                </div>
              </div>
            ))}
          </section>

          <div className="grid grid-cols-1 xl:grid-cols-4 gap-12">
            {/* Filtration Sidebar */}
            <aside className="xl:col-span-1 space-y-12">
              <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">

                {/* Type Filter */}
                <div className="space-y-4">
                  <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Classification_Isolation</label>
                  <div className="grid grid-cols-1 gap-2">
                    {['all', 'executive', 'technical', 'compliance'].map(t => (
                      <button
                        key={t}
                        onClick={() => setSelectedType(t)}
                        className={`px-6 py-4 text-left text-[10px] font-black uppercase tracking-widest border-4 transition-all flex justify-between items-center ${
                          selectedType === t
                            ? 'bg-rag-red border-slate-300  text-slate-800 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                            : 'bg-charcoal-dark border-slate-300  text-silver/100 hover:border-silver-bright/80'
                        }`}
                      >
                        {t} BRIEFINGS
                        {selectedType === t && <ReportIcon icon={Radar02Icon} size={16} className="text-slate-800" />}
                        {selectedType === t && <ReportIcon icon={Radar02Icon} size={16} className="text-black" aria-hidden="true" />}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-8 border-4 border-slate-300  border-dashed space-y-4 bg-charcoal-dark/50">
                {/* Status Filter */}
                <div className="space-y-4">
                  <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Status_Filter</label>
                  <div className="grid grid-cols-1 gap-2">
                    {([
                      { value: 'all',        label: 'All Statuses' },
                      { value: 'ready',      label: 'Ready' },
                      { value: 'generating', label: 'Generating' },
                      { value: 'failed',     label: 'Failed' },
                    ] as const).map(({ value, label }) => (
                      <button
                        key={value}
                        onClick={() => setSelectedStatus(value)}
                        aria-label={`status ${label}`}
                        className={`px-6 py-4 text-left text-[10px] font-black uppercase tracking-widest border-4 transition-all flex justify-between items-center ${
                          selectedStatus === value
                            ? 'bg-rag-amber border-black text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                            : 'bg-charcoal-dark border-black text-silver/40 hover:border-silver-bright/20'
                        }`}
                      >
                        {label}
                        {selectedStatus === value && <ReportIcon icon={Radar02Icon} size={16} className="text-black" />}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Date Range Filter */}
                <div className="space-y-4">
                  <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic">Date_Range</label>
                  <div className="grid grid-cols-1 gap-2">
                    {([
                      { value: 'all', label: 'All Time' },
                      { value: '24h', label: 'Last 24 Hours' },
                      { value: '7d',  label: 'Last 7 Days' },
                      { value: '30d', label: 'Last 30 Days' },
                    ] as const).map(({ value, label }) => (
                      <button
                        key={value}
                        onClick={() => setSelectedDateRange(value)}
                        aria-label={`date ${label}`}
                        className={`px-6 py-4 text-left text-[10px] font-black uppercase tracking-widest border-4 transition-all flex justify-between items-center ${
                          selectedDateRange === value
                            ? 'bg-rag-blue border-black text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                            : 'bg-charcoal-dark border-black text-silver/40 hover:border-silver-bright/20'
                        }`}
                      >
                        {label}
                        {selectedDateRange === value && <ReportIcon icon={Radar02Icon} size={16} className="text-black" />}
                      </button>
                    ))}
                  </div>
                </div>

                </div>

                <div className="p-8 border-4 border-black border-dashed space-y-4 bg-charcoal-dark/50">
                  <div className="flex items-center gap-3">
                    <ReportIcon icon={KnightShieldIcon} className="text-emerald-500" />
                    <ReportIcon icon={KnightShieldIcon} className="text-rag-green" aria-hidden="true" />
                    <h4 className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] italic leading-none">Integrity_Secure</h4>
                  </div>
                  <p className="text-[10px] text-silver/100 font-black uppercase tracking-widest leading-loose italic">
                    Dossiers are cryptographically hashed and recorded. Modifications are strictly detectable by the Enclave audit daemon.
                  </p>
                </div>
              </section>
            </aside>

            {/* Ledger Section */}
            <main className="xl:col-span-3 space-y-8">
              <div className="flex flex-col md:flex-row justify-between items-end gap-6 border-b-4 border-slate-300  pb-8">
                <h2 className="text-5xl font-black text-silver-bright italic uppercase tracking-tighter shrink-0">Historical_Ledger</h2>
                <div className="h-0.5 bg-slate-100 border border-slate-300 text-slate-800/10 flex-1 mb-2 hidden md:block"></div>
                <span className="text-[10px] font-mono text-silver/80 uppercase font-black mb-2 animate-pulse">{filteredReports.length} ENTRIES_LOCATED</span>
              </div>

              <AnimatePresence mode="popLayout">
                <motion.div
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  className="grid grid-cols-1 md:grid-cols-2 gap-8"
                >
                  {filteredReports.map((report) => (
                    <motion.div
                      key={report.id}
                      variants={itemVariants}
                      className="group bg-charcoal border-4 border-slate-300  p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-[14px_14px_0px_0px_rgba(0,0,0,1)] transition-all relative overflow-hidden"
                    >
                      {/* Status Top Bar */}
                      <div className={`absolute top-0 left-0 h-2 transition-all duration-500 ${
                        report.status === 'ready' ? 'bg-rag-green w-full' :
                          report.status === 'failed' ? 'bg-rag-red w-full' : 'bg-rag-amber w-1/2 animate-pulse'
                      }`}></div>

                      <div className="space-y-8 relative z-10">
                        <div className="flex justify-between items-start">
  <span className="text-[10px] font-black text-slate-800 uppercase tracking-[0.2em] italic">
  {report.type}
</span>

  <ReportIcon
    icon={Archive02Icon}
    className="text-slate-800/80 group-hover:text-slate-800 transition-colors"
  />
</div>
                        <div className="p-8 border-4 border-slate-300  border-dashed space-y-4 bg-charcoal-dark/50">
                          <div className="w-12 h-1 bg-silver-bright/10 mt-6 group-hover:w-full group-hover:bg-rag-red/90 transition-all duration-700"></div>
                        </div>

                        <div className="grid grid-cols-3 gap-6 py-6 border-y-2 border-slate-300  border-dashed">
                          <div className="space-y-1">
                            <span className="text-[8px] font-black text-silver/80 uppercase tracking-widest italic block">Findings</span>
                            <span className="text-xs font-black font-mono text-silver-bright">{report.findings.toString().padStart(3, '0')}</span>
                          </div>
                          <div className="space-y-1 text-center">
                            <span className="text-[8px] font-black text-silver/80 uppercase tracking-widest italic block">Assets</span>
                            <span className="text-xs font-black font-mono text-silver-bright">{report.assets.toString().padStart(3, '0')}</span>
                          </div>
                          <div className="space-y-1 text-right">
                            <span className="text-[8px] font-black text-silver/80 uppercase tracking-widest italic block">Pages</span>
                            <span className="text-xs font-black font-mono text-silver-bright">{report.pages.toString().padStart(3, '0')}</span>
                          </div>
                        </div>

                        <div className="flex justify-between items-end pt-2">
                          <div className="space-y-1">
                            <p className="text-[8px] font-black uppercase text-silver/80 tracking-[0.3em] italic leading-none">TIMESTAMP</p>
                            <p className="text-[10px] font-mono text-silver-bright uppercase font-black">{formatDateLong(report.generated_at)}</p>
                          </div>
                          <div className="flex gap-4">
                            <button
                              onClick={() => navigate(`/task/${report.task_id}`)}
                              className="bg-charcoal-dark border-4 border-black p-3 text-silver/20 group-hover:text-silver-bright group-hover:bg-black transition-all"
                              title="View Briefing" aria-label="View briefing"
                            >
                              <ReportIcon icon={ScanEyeIcon} size={18} aria-hidden="true"/>
                            </button>
                            {[...exportFormats].sort((a, b) =>
                              a === preferred ? -1 : b === preferred ? 1 : 0
                            ).map((format) => (
                              <button
                                key={format}
                                onClick={() => {
                                  if (report.status !== 'generating') {
                                    savePreference(format)
                                    window.open(`${API_BASE}/task/${report.task_id}/report/${format}`, '_blank')
                                  }
                                }}
                                disabled={report.status === 'generating'}
                                className={`border-4 px-3 py-2 text-[9px] font-black uppercase tracking-widest transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:group-hover:text-silver/20 disabled:group-hover:bg-charcoal-dark ${
                                  format === preferred
                                    ? 'bg-rag-amber text-black group-hover:bg-rag-amber'
                                    : 'bg-charcoal-dark text-silver/20 group-hover:text-silver-bright group-hover:bg-black border-slate-300 text-slate-800'
                                }`}
                                title={report.status === 'generating' ? 'Export unavailable while report is generating' : `Download ${format.toUpperCase()}${format === preferred ? ' (preferred)' : ''}`}
                              >
                                {format}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Background Hover Icon */}
                      <div className="absolute -right-12 -bottom-12 opacity-0 group-hover:opacity-[0.03] transition-all duration-1000 transform scale-150 rotate-12 pointer-events-none">
                        <div className="text-silver-bright">
                          <ReportIcon
                            icon={report.type === 'executive' ? Analytics02Icon : report.type === 'compliance' ? UserShield02Icon : ShieldUserIcon}
                            size={200} aria-hidden="true"
                          />
                        </div>
                      </div>
                    </motion.div>
                  ))}

                  {filteredReports.length === 0 && (
                    <div className="col-span-2 py-40 border-4 border-dashed border-black/5 text-center flex flex-col items-center gap-8 bg-charcoal/30">
                      <ReportIcon icon={Archive02Icon} size={120} className="text-silver/5" aria-hidden="true" />
                      <div className="space-y-2">
                        <p className="text-xl font-black text-silver/80 uppercase tracking-[0.4em] italic">Archive Isolated</p>
                        <p className="text-xs font-mono text-silver/10 uppercase tracking-widest leading-relaxed">System buffer awaiting briefing generation protocols</p>
                        <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">Archive Isolated</p>
                        <p className="text-xs font-mono text-silver/10 uppercase tracking-widest leading-relaxed">No entries match the selected filters</p>
                      </div>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </main>
          </div>
        </>
      )}

      {/* Tactical Footer */}
      <footer className="pt-24 border-t-4 border-slate-300 /5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
        <div className="flex items-center gap-6">
          <div className="w-12 h-1 bg-silver/80"></div>
          RESTRICTED_ACCESS_ENCLAVE // SYSTEM_ARCHIVE_DAEMON // {new Date().getFullYear()}
        </div>
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map(i => <div key={i} className="w-2 h-2 bg-silver/80 rounded-full"></div>)}
        </div>
      </footer>
    </div>
  )
}