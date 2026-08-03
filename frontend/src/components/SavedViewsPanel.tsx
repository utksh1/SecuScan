import React, { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { FilterPreset, SavedView, UseSavedViewsReturn } from '../hooks/useSavedViews'


interface Props extends UseSavedViewsReturn {
  currentPreset: FilterPreset
  onApply: (preset: FilterPreset) => void
}


function formatRelative(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const minutes = Math.floor(diff / 60_000)
    if (minutes < 1) return 'just now'
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  } catch {
    return ''
  }
}

function presetSummary(p: FilterPreset): string {
  const parts: string[] = []
  if (p.severity !== 'all') parts.push(p.severity.toUpperCase())
  if (p.target !== 'all') parts.push(p.target)
  if (p.scanner !== 'all') parts.push(p.scanner)
  if (p.sortMode !== 'severity') parts.push(`sort:${p.sortMode}`)
  if (p.dateFrom) parts.push(`from:${p.dateFrom}`)
  if (p.dateTo) parts.push(`to:${p.dateTo}`)
  if (p.searchQuery) parts.push(`"${p.searchQuery}"`)
  return parts.length ? parts.join(' · ') : 'All findings'
}


interface ViewRowProps {
  view: SavedView
  onApply: () => void
  onRename: (name: string) => void
  onDelete: () => void
}

function ViewRow({ view, onApply, onRename, onDelete }: ViewRowProps) {
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(view.name)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function commitRename() {
    const trimmed = editName.trim()
    if (trimmed && trimmed !== view.name) {
      onRename(trimmed)
    } else {
      setEditName(view.name)
    }
    setEditing(false)
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="group border-b border-silver-bright/6 last:border-0"
    >
      <div className="flex items-start gap-3 px-4 py-3">
        {/* Apply button + name */}
        <button
          type="button"
          onClick={onApply}
          title="Apply this preset"
          className="min-w-0 flex-1 text-left"
          aria-label={`Apply saved view: ${view.name}`}
        >
          {editing ? (
            <input
              ref={inputRef}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                if (e.key === 'Enter') commitRename()
                if (e.key === 'Escape') {
                  setEditName(view.name)
                  setEditing(false)
                }
              }}
              onClick={(e) => e.stopPropagation()}
              autoFocus
              maxLength={60}
              className="w-full border-0 border-b-2 border-rag-blue bg-transparent text-[11px] font-black uppercase tracking-widest text-silver-bright outline-none"
              aria-label="Rename saved view"
            />
          ) : (
            <p className="truncate text-[11px] font-black uppercase tracking-[0.18em] text-silver-bright transition-colors group-hover:text-white">
              {view.name}
            </p>
          )}
          <p className="mt-1 truncate text-[9px] font-mono uppercase tracking-[0.12em] text-silver/35">
            {presetSummary(view.preset)}
          </p>
          <p className="mt-0.5 text-[8px] font-mono text-silver/20">
            {formatRelative(view.updatedAt)}
          </p>
        </button>

        {/* Action icons — visible on hover */}
        {!editing && (
          <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            {/* Rename */}
            <button
              type="button"
              aria-label="Rename view"
              onClick={() => {
                setEditing(true)
                setTimeout(() => inputRef.current?.select(), 0)
              }}
              className="flex h-6 w-6 items-center justify-center text-silver/40 transition-colors hover:text-rag-blue"
            >
              <span className="material-symbols-outlined text-sm">edit</span>
            </button>


            {confirmDelete ? (
              <button
                type="button"
                aria-label="Confirm delete"
                onClick={() => {
                  setConfirmDelete(false)
                  onDelete()
                }}
                className="flex h-6 items-center gap-1 border border-rag-red/40 bg-rag-red/10 px-2 text-[9px] font-black uppercase tracking-widest text-rag-red transition-all hover:bg-rag-red hover:text-black"
              >
                Confirm
              </button>
            ) : (
              <button
                type="button"
                aria-label="Delete view"
                onClick={() => setConfirmDelete(true)}
                className="flex h-6 w-6 items-center justify-center text-silver/40 transition-colors hover:text-rag-red"
              >
                <span className="material-symbols-outlined text-sm">delete</span>
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}


export default function SavedViewsPanel({
  views,
  loading,
  saveView,
  deleteView,
  renameView,
  currentPreset,
  onApply,
}: Props) {
  const [open, setOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  async function handleSave() {
    const trimmed = saveName.trim()
    if (!trimmed) {
      setError('Enter a name for this view')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const saved = await saveView(trimmed, currentPreset)
      const isOverwrite = views.some(
        (v) => v.name.toLowerCase() === trimmed.toLowerCase(),
      )
      setSuccessMsg(
        isOverwrite ? `Updated "${saved.name}"` : `Saved "${saved.name}"`,
      )
      setSaveName('')
      setTimeout(() => setSuccessMsg(null), 2000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save view')
    } finally {
      setSaving(false)
    }
  }

  const panelVariants = {
    hidden: { opacity: 0, y: -8, scaleY: 0.96 },
    visible: { opacity: 1, y: 0, scaleY: 1, transition: { duration: 0.18, ease: 'easeOut' as const } },
    exit: { opacity: 0, y: -6, scaleY: 0.97, transition: { duration: 0.12, ease: 'easeOut' as const } },
  }

  return (
    <div className="relative shrink-0">

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label="Saved filter views"
        className={`flex items-center gap-2 border-2 px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] transition-all whitespace-nowrap ${
          open
            ? 'border-black bg-silver-bright text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
            : 'border-silver-bright/10 bg-charcoal-dark text-silver/65 hover:border-silver-bright/30 hover:text-silver-bright'
        }`}
      >
        <span className="material-symbols-outlined text-sm">bookmarks</span>
        Saved_Views
        {views.length > 0 && (
          <span
            className={`flex h-4 min-w-4 items-center justify-center px-1 text-[8px] font-black ${
              open ? 'bg-black text-silver-bright' : 'bg-rag-blue text-black'
            }`}
          >
            {views.length}
          </span>
        )}
      </button>


      <AnimatePresence>
        {open && (
          <motion.div
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            style={{ transformOrigin: 'top right' }}
            className="absolute right-0 top-full z-[60] mt-2 w-[min(22rem,calc(100vw-2rem))] border-4 border-black bg-charcoal shadow-[10px_10px_0px_0px_rgba(0,0,0,1)]"
            role="dialog"
            aria-label="Saved filter views panel"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b-2 border-black px-4 py-3">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-silver-bright">
                Filter_Presets
              </p>
              <button
                type="button"
                aria-label="Close panel"
                onClick={() => setOpen(false)}
                className="text-silver/40 transition-colors hover:text-silver-bright"
              >
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            <div className="border-b border-silver-bright/10 px-4 py-4 space-y-3">
              <p className="text-[9px] font-black uppercase tracking-[0.25em] text-silver/40">
                Save Current Filters
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => {
                    setSaveName(e.target.value)
                    setError(null)
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                  placeholder="Name this view…"
                  maxLength={60}
                  aria-label="Saved view name"
                  className="flex-1 border-2 border-silver-bright/10 bg-charcoal-dark px-3 py-2 text-[10px] font-mono text-silver-bright placeholder:text-silver/25 focus:border-rag-blue focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  aria-label="Save current filters"
                  className="border-2 border-rag-blue bg-rag-blue px-3 py-2 text-[10px] font-black uppercase tracking-widest text-black shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] transition-all hover:shadow-none hover:translate-x-px hover:translate-y-px disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <span className="material-symbols-outlined text-sm animate-spin">
                      progress_activity
                    </span>
                  ) : (
                    <span className="material-symbols-outlined text-sm">save</span>
                  )}
                </button>
              </div>

              <AnimatePresence mode="wait">
                {error && (
                  <motion.p
                    key="error"
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    role="alert"
                    className="text-[9px] font-mono uppercase tracking-widest text-rag-red"
                  >
                    ⚠ {error}
                  </motion.p>
                )}
                {successMsg && (
                  <motion.p
                    key="success"
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    role="status"
                    className="text-[9px] font-mono uppercase tracking-widest text-rag-green"
                  >
                    ✓ {successMsg}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>

            <div className="max-h-72 overflow-y-auto">
              {loading ? (
                <p className="px-4 py-6 text-center text-[9px] font-mono uppercase tracking-widest text-silver/30">
                  Loading presets…
                </p>
              ) : views.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-silver/20 italic">
                    No Saved Views
                  </p>
                  <p className="mt-1 text-[8px] font-mono uppercase tracking-widest text-silver/15">
                    Configure filters then save above.
                  </p>
                </div>
              ) : (
                <AnimatePresence initial={false}>
                  {views.map((view) => (
                    <ViewRow
                      key={view.id}
                      view={view}
                      onApply={() => {
                        onApply(view.preset)
                        setOpen(false)
                      }}
                      onRename={(name) => renameView(view.id, name)}
                      onDelete={() => deleteView(view.id)}
                    />
                  ))}
                </AnimatePresence>
              )}
            </div>

            {views.length > 0 && (
              <div className="border-t border-silver-bright/6 px-4 py-2">
                <p className="text-[8px] font-mono uppercase tracking-widest text-silver/20">
                  Click a preset to apply · Hover to rename or delete
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
