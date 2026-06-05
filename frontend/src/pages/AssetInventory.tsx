import { useState, useMemo, useEffect } from 'react'
import { getAssets } from '../api'

const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, none: 4 }

const SEV_CONFIG: Record<string, { label: string; chip: string; rail: string; accent: string }> = {
  critical: { label: 'CRIT', chip: 'bg-rag-red text-black',                                    rail: 'bg-rag-red',     accent: 'text-rag-red'         },
  high:     { label: 'HIGH', chip: 'bg-rag-amber text-black',                                  rail: 'bg-rag-amber',   accent: 'text-rag-amber'       },
  medium:   { label: 'MED',  chip: 'bg-rag-blue text-black',                                   rail: 'bg-rag-blue',    accent: 'text-rag-blue'        },
  low:      { label: 'LOW',  chip: 'bg-charcoal-dark text-silver-bright border border-silver-bright/15', rail: 'bg-silver/50',   accent: 'text-silver-bright'   },
  none:     { label: '—',    chip: 'bg-charcoal-dark text-silver border border-silver/15',     rail: 'bg-silver/20',   accent: 'text-silver'          },
}

type Asset = {
  host: string
  ip: string
  ports: string[]
  tags: string[]
  scanner: string
  severity: string
  findings: number
  first: string
  last: string
}

function relTime(d: string) {
  const days = Math.floor((Date.now() - new Date(d).getTime()) / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return '1d ago'
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

function SevBadge({ severity }: { severity: string }) {
  const s = SEV_CONFIG[severity] || SEV_CONFIG.none
  return (
    <span className={`inline-flex items-center px-2 py-1 text-[9px] font-black uppercase tracking-[0.18em] ${s.chip}`}>
      {s.label}
    </span>
  )
}

function PortTag({ port }: { port: string }) {
  return (
    <span className="border border-silver-bright/15 bg-charcoal-dark px-1.5 py-0.5 text-[10px] font-mono text-silver/70">
      {port}
    </span>
  )
}

function TagPill({ tag }: { tag: string }) {
  return (
    <span className="border border-silver/10 bg-charcoal/60 px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.12em] text-silver/50">
      {tag}
    </span>
  )
}

type SortCol = 'host' | 'findings' | 'severity' | 'last_seen'

export default function AssetInventory() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [query, setQuery] = useState('')
  const [sevFilter, setSevFilter] = useState('')
  const [scannerFilter, setScannerFilter] = useState('')
  const [sortCol, setSortCol] = useState<SortCol>('host')
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    getAssets()
      .then((data: any) => setAssets(data))
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    let list = assets.filter(a => {
      const matchQ = !q || a.host.includes(q) || a.ip.includes(q)
        || a.ports.some(p => p.includes(q))
        || a.tags.some(t => t.includes(q))
        || a.scanner.includes(q)
      const matchSev = !sevFilter || a.severity === sevFilter
      const matchScanner = !scannerFilter || a.scanner === scannerFilter
      return matchQ && matchSev && matchScanner
    })
    list = [...list].sort((a, b) => {
      if (sortCol === 'findings') return b.findings - a.findings
      if (sortCol === 'severity') return SEV_ORDER[a.severity] - SEV_ORDER[b.severity]
      if (sortCol === 'last_seen') return new Date(b.last).getTime() - new Date(a.last).getTime()
      return a.host.localeCompare(b.host)
    })
    return list
  }, [query, sevFilter, scannerFilter, sortCol, assets])

  const totalFindings = assets.reduce((s, a) => s + a.findings, 0)
  const criticalCount = assets.filter(a => a.severity === 'critical').length
  const totalPorts = new Set(assets.flatMap(a => a.ports)).size

  const filterControlClass =
    'h-10 border-2 border-silver-bright/10 bg-charcoal-dark px-3 text-xs font-mono text-silver-bright focus:border-rag-red focus:outline-none'

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver px-4 py-6 md:px-8 md:py-10">
      <div className="mx-auto w-full max-w-[1200px] flex flex-col gap-8">

        {/* Header */}
        <header className="border-b-4 border-silver-bright/10 pb-8">
          <div className="mb-4 inline-block bg-rag-red px-4 py-1 text-xs font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Asset Inventory
          </div>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="space-y-3">
              <h1 className="text-5xl font-black uppercase tracking-tighter text-silver-bright italic md:text-7xl">
                Discovered{' '}
                <span className="text-transparent" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>
                  Hosts
                </span>
              </h1>
              <p className="text-xs font-mono uppercase tracking-[0.24em] text-silver/45">
                Asset registry // {assets.length} hosts // {totalFindings} findings total
              </p>
            </div>

            <div className="grid w-full gap-3 sm:grid-cols-2 xl:w-auto xl:grid-cols-4">
              {[
                { label: 'Total Hosts',  value: assets.length, tone: 'text-silver-bright' },
                { label: 'Unique Ports', value: totalPorts,    tone: 'text-rag-blue'      },
                { label: 'Findings',     value: totalFindings, tone: 'text-rag-amber'     },
                { label: 'Critical',     value: criticalCount, tone: 'text-rag-red'       },
              ].map(stat => (
                <div key={stat.label} className="border-2 border-black bg-charcoal px-4 py-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                  <p className="mb-2 text-[10px] font-black uppercase tracking-[0.25em] text-silver/55">{stat.label}</p>
                  <p className={`text-3xl font-black italic tracking-tight ${stat.tone}`}>
                    {String(stat.value).padStart(2, '0')}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </header>

        {/* Filters */}
        <section className="border-2 border-black bg-charcoal/95 p-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px] space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright">Search</label>
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Host, IP, port, tag, scanner…"
                className={`${filterControlClass} w-full placeholder:text-silver/20`}
              />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright">Severity</label>
              <select value={sevFilter} onChange={e => setSevFilter(e.target.value)} className={filterControlClass}>
                <option value="">All Severities</option>
                {['critical','high','medium','low','none'].map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright">Scanner</label>
              <select value={scannerFilter} onChange={e => setScannerFilter(e.target.value)} className={filterControlClass}>
                <option value="">All Scanners</option>
                {['nmap','nuclei','subfinder','httpx'].map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-silver-bright">Sort By</label>
              <select value={sortCol} onChange={e => setSortCol(e.target.value as SortCol)} className={filterControlClass}>
                <option value="host">Host</option>
                <option value="findings">Findings</option>
                <option value="severity">Severity</option>
                <option value="last_seen">Last Seen</option>
              </select>
            </div>

            <button
              onClick={() => { setQuery(''); setSevFilter(''); setScannerFilter(''); setSortCol('host') }}
              className="h-10 border border-silver-bright/20 bg-charcoal-dark px-4 text-[10px] font-black uppercase tracking-[0.18em] text-silver/65 hover:border-rag-red hover:text-silver-bright transition-all"
            >
              Reset
            </button>
          </div>
        </section>

        {/* Table */}
        {loading ? (
          <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 px-6 py-16 text-center">
            <p className="text-sm font-mono uppercase tracking-[0.25em] text-silver/50">Loading asset inventory…</p>
          </div>
        ) : error ? (
          <div className="border-4 border-dashed border-rag-red/30 bg-rag-red/5 px-6 py-16 text-center">
            <p className="text-sm font-mono uppercase tracking-[0.25em] text-rag-red">Failed to load assets.</p>
          </div>
        ) : (
          <div className="border-2 border-black bg-charcoal shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-silver-bright/10 bg-charcoal/80">
                  {[['Host / IP','w-1/4'],['Open Ports','w-1/5'],['Scanner','w-1/8'],['Findings','w-1/12'],['Severity','w-1/8'],['First Seen','w-1/8'],['Last Seen','w-1/8']].map(([h, w]) => (
                    <th key={h} className={`${w} px-4 py-3 text-left text-[10px] font-black uppercase tracking-[0.2em] text-silver/40`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-silver-bright/6">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-16 text-center text-silver/30 uppercase tracking-widest">
                      No assets match your filters.
                    </td>
                  </tr>
                ) : filtered.map(a => {
                  const cfg = SEV_CONFIG[a.severity] || SEV_CONFIG.none
                  const isSelected = selected === a.host
                  return (
                    <>
                      <tr
                        key={a.host}
                        onClick={() => setSelected(isSelected ? null : a.host)}
                        className={`relative cursor-pointer transition-colors ${isSelected ? 'bg-silver-bright/6' : 'hover:bg-silver-bright/3'}`}
                      >
                        <td className="px-4 py-3">
                          <span className={`absolute inset-y-0 left-0 w-1 ${cfg.rail}`} />
                          <div className="font-black text-silver-bright pl-2">{a.host}</div>
                          <div className="text-silver/40 mt-0.5 pl-2">{a.ip}</div>
                          <div className="flex flex-wrap gap-1 mt-1 pl-2">{a.tags.map(t => <TagPill key={t} tag={t} />)}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {a.ports.slice(0, 4).map(p => <PortTag key={p} port={p} />)}
                            {a.ports.length > 4 && <PortTag port={`+${a.ports.length - 4}`} />}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-silver/50">{a.scanner}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={a.findings > 0 ? 'text-silver-bright font-black' : 'text-silver/25'}>
                            {a.findings > 0 ? a.findings : '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3"><SevBadge severity={a.severity} /></td>
                        <td className="px-4 py-3 text-silver/40">{relTime(a.first)}</td>
                        <td className="px-4 py-3 text-silver/40">{relTime(a.last)}</td>
                      </tr>

                      {isSelected && (
                        <tr key={`${a.host}-detail`}>
                          <td colSpan={7} className="bg-charcoal/80 border-t border-silver-bright/10 px-6 py-5">
                            <div className="grid grid-cols-3 gap-6 text-xs">
                              <div>
                                <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35 mb-2">All Ports</p>
                                <div className="flex flex-wrap gap-1">{a.ports.map(p => <PortTag key={p} port={p} />)}</div>
                              </div>
                              <div>
                                <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35 mb-2">Tags</p>
                                <div className="flex flex-wrap gap-1">{a.tags.map(t => <TagPill key={t} tag={t} />)}</div>
                              </div>
                              <div>
                                <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35 mb-2">Timeline</p>
                                <p className="text-silver/60">First {relTime(a.first)} · Last {relTime(a.last)}</p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}