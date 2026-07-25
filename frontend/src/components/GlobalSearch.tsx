import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { search, SearchFindingResult, SearchReportResult } from '../api'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { routes } from '../routes'

interface GlobalSearchProps {
  className?: string
  onNavigate?: () => void
}

export default function GlobalSearch({ className = '', onNavigate }: GlobalSearchProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [findings, setFindings] = useState<SearchFindingResult[]>([])
  const [reports, setReports] = useState<SearchReportResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const debouncedQuery = useDebouncedValue(query.trim(), 300)

  useEffect(() => {
    if (!debouncedQuery) {
      setFindings([])
      setReports([])
      setError(null)
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    search(debouncedQuery)
      .then((data) => {
        if (cancelled) return
        setFindings(data.findings)
        setReports(data.reports)
      })
      .catch(() => {
        if (cancelled) return
        setError('Search failed. Try again.')
        setFindings([])
        setReports([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedQuery])

  useEffect(() => {
    if (!open) return
    function onPointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  function goTo(path: string) {
    setOpen(false)
    setQuery('')
    onNavigate?.()
    navigate(path)
  }

  const hasResults = findings.length > 0 || reports.length > 0
  const showDropdown = open && debouncedQuery.length > 0

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[16px] text-silver/40 pointer-events-none">
          search
        </span>
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search findings, reports..."
          aria-label="Global search"
          className="h-9 w-full border border-accent-silver/20 bg-charcoal-dark pl-9 pr-3 text-xs font-mono text-silver-bright placeholder:text-silver/30 focus:border-rag-red focus:outline-none"
        />
      </div>

      {showDropdown && (
        <div
          role="listbox"
          aria-label="Search results"
          className="absolute left-0 right-0 top-full z-[70] mt-2 max-h-96 overflow-y-auto border-2 border-black bg-charcoal shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
        >
          {loading ? (
            <p className="px-4 py-4 text-[11px] font-mono uppercase tracking-[0.16em] text-silver/45">
              Searching...
            </p>
          ) : error ? (
            <p className="px-4 py-4 text-[11px] font-mono uppercase tracking-[0.16em] text-rag-red">
              {error}
            </p>
          ) : !hasResults ? (
            <p className="px-4 py-4 text-[11px] font-mono uppercase tracking-[0.16em] text-silver/45">
              No results for "{debouncedQuery}"
            </p>
          ) : (
            <>
              {findings.length > 0 && (
                <div className="border-b border-silver-bright/8">
                  <p className="px-4 pt-3 pb-1 text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">
                    Findings
                  </p>
                  {findings.map((finding) => (
                    <button
                      key={finding.id}
                      type="button"
                      role="option"
                      aria-selected={false}
                      onClick={() => goTo(routes.findings)}
                      className="block w-full px-4 py-2 text-left hover:bg-silver-bright/5"
                    >
                      <p className="text-xs font-bold text-silver-bright truncate">{finding.title}</p>
                      <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-silver/40">
                        {finding.severity} // {finding.target}
                      </p>
                    </button>
                  ))}
                </div>
              )}

              {reports.length > 0 && (
                <div>
                  <p className="px-4 pt-3 pb-1 text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">
                    Reports
                  </p>
                  {reports.map((report) => (
                    <button
                      key={report.id}
                      type="button"
                      role="option"
                      aria-selected={false}
                      onClick={() => goTo(routes.reports)}
                      className="block w-full px-4 py-2 text-left hover:bg-silver-bright/5"
                    >
                      <p className="text-xs font-bold text-silver-bright truncate">{report.name}</p>
                      <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-silver/40">
                        {report.type}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}