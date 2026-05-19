import React, { useCallback, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { PluginFieldSchema } from '../api'
import {
  buildCommandTokens,
  getMissingFields,
  tokensToString,
  type PreviewToken,
} from '../utils/commandPreview'

interface CommandPreviewProps {
  commandTemplate: string[]
  fields: PluginFieldSchema[]
  inputs: Record<string, unknown>
}

function TokenChip({ token }: { token: PreviewToken }) {
  const styles: Record<PreviewToken['kind'], string> = {
    command:     'text-rag-green font-black',
    flag:        'text-rag-blue',
    value:       'text-silver-bright',
    redacted:    'text-rag-amber font-mono bg-rag-amber/10 px-1 rounded',
    missing:     'text-rag-red font-mono bg-rag-red/10 px-1 rounded animate-pulse',
    placeholder: 'text-silver/40 italic',
  }

  return (
    <span className={`inline-block whitespace-nowrap ${styles[token.kind]}`}>
      {token.text}
    </span>
  )
}

export default function CommandPreview({ commandTemplate, fields, inputs }: CommandPreviewProps) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(true)

  const tokens = buildCommandTokens(commandTemplate, fields, inputs)
  const missingFields = getMissingFields(fields, inputs)
  const plainText = tokensToString(tokens)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(plainText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard not available
    }
  }, [plainText])

  return (
    <section
      className="bg-charcoal border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] overflow-hidden"
      aria-label="Command preview"
    >
      {/* ── Header bar ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-4 border-b-4 border-black bg-charcoal-dark">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-rag-blue text-lg">terminal</span>
          <span className="text-[10px] font-black uppercase tracking-[0.4em] text-silver-bright italic">
            Cmd_Preview
          </span>
          <span className="text-[9px] px-2 py-0.5 border-2 border-silver/20 text-silver/40 uppercase tracking-widest font-black">
            sanitized · local
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            title="Copy sanitized command"
            className="flex items-center gap-1.5 px-3 py-1.5 border-2 border-black text-[9px] font-black uppercase tracking-widest text-silver hover:bg-rag-blue hover:text-black transition-all shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-0.5 active:translate-y-0.5"
          >
            <span className="material-symbols-outlined text-sm">
              {copied ? 'check' : 'content_copy'}
            </span>
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={() => setExpanded((v) => !v)}
            title={expanded ? 'Collapse preview' : 'Expand preview'}
            className="w-8 h-8 flex items-center justify-center border-2 border-black text-silver hover:bg-charcoal-light transition-all"
          >
            <span className="material-symbols-outlined text-sm">
              {expanded ? 'expand_less' : 'expand_more'}
            </span>
          </button>
        </div>
      </div>

      {/* ── Token display ─────────────────────────────────────────────────── */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="preview-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-6 py-5">
              <pre
                className="font-mono text-xs leading-relaxed whitespace-pre-wrap break-all flex flex-wrap gap-x-1.5 gap-y-1"
                aria-label={`Preview command: ${plainText}`}
              >
                {tokens.map((token, i) => (
                  <TokenChip key={i} token={token} />
                ))}
              </pre>
            </div>

            {/* ── Legend ──────────────────────────────────────────────────── */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-6 pb-4 border-t-2 border-black/40 pt-3">
              <LegendItem color="text-rag-green" label="binary" />
              <LegendItem color="text-rag-blue" label="flag" />
              <LegendItem color="text-silver-bright" label="value" />
              <LegendItem color="text-rag-amber" label="redacted secret" />
              <LegendItem color="text-rag-red" label="missing required" />
            </div>

            {/* ── Missing fields warning ───────────────────────────────────── */}
            {missingFields.length > 0 && (
              <div className="mx-6 mb-5 border-2 border-rag-red/60 bg-rag-red/5 px-4 py-3 flex items-start gap-3">
                <span className="material-symbols-outlined text-rag-red text-base mt-0.5 shrink-0">
                  warning
                </span>
                <div>
                  <p className="text-[9px] font-black uppercase tracking-widest text-rag-red mb-1">
                    Missing required fields
                  </p>
                  <p className="text-[9px] text-silver/60 uppercase tracking-widest">
                    {missingFields.map((f) => f.label).join(', ')}
                  </p>
                </div>
              </div>
            )}

            {/* ── Disclaimer ──────────────────────────────────────────────── */}
            <p className="px-6 pb-4 text-[9px] text-silver/25 uppercase tracking-widest leading-relaxed">
              ⚠ This preview is locally generated and sanitized. Runtime normalisation may alter
              the final command. Secrets and credentials are always redacted here.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`text-[10px] font-mono font-black ${color}`}>■</span>
      <span className="text-[9px] uppercase tracking-widest text-silver/40">{label}</span>
    </span>
  )
}