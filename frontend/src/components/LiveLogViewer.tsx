import React, { useEffect, useRef, useState, useCallback } from 'react'

export interface LogLine {
  line: string
  stream: 'stdout' | 'stderr'
  ts: number
}

interface LiveLogViewerProps {
  lines: LogLine[]
  isLive: boolean
  onCopy: () => void
  copied: boolean
}

export default function LiveLogViewer({ lines, isLive, onCopy, copied }: LiveLogViewerProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [paused, setPaused] = useState(false)
  const [filter, setFilter] = useState('')

  // Auto-scroll when new lines arrive unless paused
  useEffect(() => {
    if (!paused && bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines, paused])
  const filteredLines = filter
    ? lines.filter(l => l.line.toLowerCase().includes(filter.toLowerCase()))
    : lines

  const stderrCount = lines.filter(l => l.stream === 'stderr').length

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          {/* Live indicator */}
          {isLive && (
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rag-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rag-green"></span>
              </span>
              <span className="text-[10px] font-black uppercase tracking-[0.28em] text-rag-green italic">
                Live_Stream
              </span>
            </div>
          )}
          {/* Stderr warning */}
          {stderrCount > 0 && (
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-rag-amber px-2 py-0.5 border border-rag-amber/30 bg-rag-amber/10">
              {stderrCount} Stderr
            </span>
          )}
          <span className="text-[10px] uppercase tracking-[0.2em] text-silver/40">
            {filteredLines.length} lines
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Filter output..."
            className="bg-black/30 border border-white/10 px-3 py-2 text-sm text-silver-bright outline-none min-w-[180px] placeholder:text-silver/30"
          />
          <button
            onClick={() => setPaused(p => !p)}
            className={`border px-3 py-2 text-[10px] uppercase tracking-[0.2em] font-black transition-colors ${
              paused
                ? 'border-rag-amber/40 text-rag-amber bg-rag-amber/10'
                : 'border-white/10 text-silver/75 hover:bg-white/[0.04]'
            }`}
          >
            {paused ? 'Resume_Scroll' : 'Pause_Scroll'}
          </button>
          <button
            onClick={onCopy}
            className="border border-white/10 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-silver/75 font-black hover:bg-white/[0.04] transition-colors"
          >
            {copied ? 'Copied' : 'Copy_Log'}
          </button>
        </div>
      </div>

      {/* Log window */}
      <div
        ref={containerRef}
        className="border border-white/6 bg-black/40 p-4 h-[420px] overflow-y-auto font-mono text-[11px] leading-6 custom-scrollbar"
      >
        {filteredLines.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-silver/30 uppercase tracking-[0.3em] text-[10px] italic">
              {isLive ? 'Awaiting_Output...' : 'No_Output_Available'}
            </p>
          </div>
        ) : (
          filteredLines.map((l, i) => (
            <div key={i} className="flex gap-3 group hover:bg-white/[0.02] px-1">
              {/* Line number */}
              <span className="text-silver/15 select-none w-8 text-right shrink-0 group-hover:text-silver/30 transition-colors">
                {i + 1}
              </span>
              {/* Stream badge */}
              <span className={`shrink-0 text-[9px] font-black uppercase w-10 pt-[2px] ${
                l.stream === 'stderr' ? 'text-rag-amber/70' : 'text-silver/20'
              }`}>
                {l.stream === 'stderr' ? 'ERR' : 'OUT'}
              </span>
              {/* Content */}
              <span className={`break-all whitespace-pre-wrap ${
                l.stream === 'stderr'
                  ? 'text-rag-amber/85'
                  : 'text-silver/80'
              }`}>
                {l.line}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
