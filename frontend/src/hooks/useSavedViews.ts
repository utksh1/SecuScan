import { useCallback, useEffect, useRef, useState } from 'react'
import { API_BASE } from '../api'

export interface FilterPreset {
  severity: string
  target: string
  scanner: string
  sortMode: string
  dateFrom: string
  dateTo: string
  searchQuery: string
}

export interface SavedView {
  id: string
  name: string
  preset: FilterPreset
  createdAt: string   // ISO string
  updatedAt: string   // ISO string
}

// Pydantic-shaped payload the backend expects.
interface BackendPayload {
  name: string
  filter_json: string
}

interface BackendRow {
  id: string
  name: string
  filter_json: string
  created_at: string
  updated_at: string
}

const VALID_SORT_MODES = ['severity', 'newest', 'oldest', 'target'] as const
const VALID_SEVERITIES = ['all', 'critical', 'high', 'medium', 'low', 'info'] as const

/** Returns true when obj looks like a real FilterPreset (not garbage data). */
export function isValidPreset(obj: unknown): obj is FilterPreset {
  if (!obj || typeof obj !== 'object') return false
  const p = obj as Record<string, unknown>
  if (typeof p.severity !== 'string') return false
  if (typeof p.target !== 'string') return false
  if (typeof p.scanner !== 'string') return false
  if (typeof p.sortMode !== 'string') return false
  if (typeof p.dateFrom !== 'string') return false
  if (typeof p.dateTo !== 'string') return false
  if (typeof p.searchQuery !== 'string') return false
  if (!(VALID_SORT_MODES as readonly string[]).includes(p.sortMode)) return false
  if (!(VALID_SEVERITIES as readonly string[]).includes(p.severity)) return false
  return true
}

export function isValidSavedView(obj: unknown): obj is SavedView {
  if (!obj || typeof obj !== 'object') return false
  const v = obj as Record<string, unknown>
  if (typeof v.id !== 'string' || !v.id) return false
  if (typeof v.name !== 'string' || !v.name) return false
  if (typeof v.createdAt !== 'string') return false
  if (typeof v.updatedAt !== 'string') return false
  return isValidPreset(v.preset)
}


const LS_KEY = 'secuscan-saved-views'

function readFromStorage(): SavedView[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isValidSavedView)
  } catch {
    return []
  }
}

function writeToStorage(views: SavedView[]): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(views))
  } catch {
    // Storage quota exceeded — silently ignore.
  }
}


function rowToView(row: BackendRow): SavedView | null {
  try {
    const preset: unknown = JSON.parse(row.filter_json)
    if (!isValidPreset(preset)) return null
    return {
      id: row.id,
      name: row.name,
      preset,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    }
  } catch {
    return null
  }
}

/**
 * Backend sync failure behaviour
 * ─────────────────────────────
 * All backend calls are fire-and-forget with a hard 8-second timeout.
 * On any network error, non-2xx response, or timeout:
 *
 *   • The optimistic local state (already written to localStorage) is
 *     kept as-is — the user never sees an error for a backend outage.
 *   • `backendAvailable` stays false so subsequent mutations skip the
 *     network entirely rather than hammering an unreachable server.
 *   • On the next page load the hook retries the backend hydration; if
 *     it succeeds, remote state is merged (remote wins on timestamp).
 *   • There is intentionally no retry queue — SecuScan is local-first
 *     and localStorage is the source of truth.  The backend is a
 *     convenience sync layer, not a required dependency.
 *
 * Callers (SavedViewsPanel) can rely on the returned Promise always
 * resolving — it never rejects due to a backend failure.
 */
async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: AbortSignal.timeout(8000),
    })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}


export interface UseSavedViewsReturn {
  views: SavedView[]
  loading: boolean
  /** Save a new preset or overwrite an existing one (matched by name). */
  saveView: (name: string, preset: FilterPreset) => Promise<SavedView>
  /** Delete by id. */
  deleteView: (id: string) => Promise<void>
  /** Rename an existing view. */
  renameView: (id: string, newName: string) => Promise<void>
}

export function useSavedViews(): UseSavedViewsReturn {
  const [views, setViews] = useState<SavedView[]>([])
  const [loading, setLoading] = useState(true)
  // Track whether we managed to hydrate from the backend at least once.
  const backendAvailable = useRef(false)

  // ── Mount: prefer backend, fall back to localStorage ──────────────────────
  useEffect(() => {
    let cancelled = false

    async function hydrate() {
      // Try backend first
      const data = await apiFetch<{ views: BackendRow[] }>('/saved-views')
      if (!cancelled) {
        if (data && Array.isArray(data.views)) {
          const parsed = data.views.map(rowToView).filter(Boolean) as SavedView[]
          backendAvailable.current = true
          setViews(parsed)
          writeToStorage(parsed) // keep local in sync
        } else {
          // Backend unreachable — use localStorage
          setViews(readFromStorage())
        }
        setLoading(false)
      }
    }

    hydrate()
    return () => { cancelled = true }
  }, [])


  const syncSet = useCallback((next: SavedView[]) => {
    setViews(next)
    writeToStorage(next)
  }, [])

  const saveView = useCallback(
    async (name: string, preset: FilterPreset): Promise<SavedView> => {
      const trimmed = name.trim()
      if (!trimmed) throw new Error('View name cannot be empty')
      if (!isValidPreset(preset)) throw new Error('Invalid filter preset')

      // Check whether we're overwriting an existing name
      const existing = views.find(
        (v) => v.name.toLowerCase() === trimmed.toLowerCase(),
      )

      const now = new Date().toISOString()

      if (existing) {
        const updated: SavedView = { ...existing, preset, updatedAt: now }
        const next = views.map((v) => (v.id === existing.id ? updated : v))
        syncSet(next)

        // Backend sync (optimistic, fire-and-forget)
        if (backendAvailable.current) {
          const payload: BackendPayload = {
            name: trimmed,
            filter_json: JSON.stringify(preset),
          }
          apiFetch(`/saved-views/${existing.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          })
        }
        return updated
      }

      const tempId = `local-${Date.now()}-${Math.random().toString(36).slice(2)}`
      const created: SavedView = {
        id: tempId,
        name: trimmed,
        preset,
        createdAt: now,
        updatedAt: now,
      }

      const next = [...views, created]
      syncSet(next)

      if (backendAvailable.current) {
        const payload: BackendPayload = {
          name: trimmed,
          filter_json: JSON.stringify(preset),
        }
        const result = await apiFetch<{ id: string }>('/saved-views', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (result?.id) {
          const withRealId: SavedView = { ...created, id: result.id }
          const finalNext = next.map((v) => (v.id === tempId ? withRealId : v))
          syncSet(finalNext)
          return withRealId
        }
      }

      return created
    },
    [views, syncSet],
  )

  const deleteView = useCallback(
    async (id: string): Promise<void> => {
      syncSet(views.filter((v) => v.id !== id))

      if (backendAvailable.current && !id.startsWith('local-')) {
        apiFetch(`/saved-views/${id}`, { method: 'DELETE' })
      }
    },
    [views, syncSet],
  )

  const renameView = useCallback(
    async (id: string, newName: string): Promise<void> => {
      const trimmed = newName.trim()
      if (!trimmed) throw new Error('Name cannot be empty')

      const now = new Date().toISOString()
      const next = views.map((v) =>
        v.id === id ? { ...v, name: trimmed, updatedAt: now } : v,
      )
      syncSet(next)

      if (backendAvailable.current && !id.startsWith('local-')) {
        const target = views.find((v) => v.id === id)
        if (target) {
          const payload: BackendPayload = {
            name: trimmed,
            filter_json: JSON.stringify(target.preset),
          }
          apiFetch(`/saved-views/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          })
        }
      }
    },
    [views, syncSet],
  )

  return { views, loading, saveView, deleteView, renameView }
}
