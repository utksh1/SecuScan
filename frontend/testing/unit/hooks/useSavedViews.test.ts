import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  FilterPreset,
  isValidPreset,
  isValidSavedView,
  useSavedViews,
} from '../../../src/hooks/useSavedViews'


const mockFetch = vi.fn(() => Promise.reject(new Error('Network offline')))
vi.stubGlobal('fetch', mockFetch)

const storage: Record<string, string> = {}
const localStorageMock = {
  getItem: (k: string) => storage[k] ?? null,
  setItem: (k: string, v: string) => {
    storage[k] = v
  },
  removeItem: (k: string) => {
    delete storage[k]
  },
  clear: () => {
    Object.keys(storage).forEach((k) => delete storage[k])
  },
}
vi.stubGlobal('localStorage', localStorageMock)


const VALID_PRESET: FilterPreset = {
  severity: 'critical',
  target: 'example.com',
  scanner: 'nmap',
  sortMode: 'newest',
  dateFrom: '2025-01-01',
  dateTo: '2025-12-31',
  searchQuery: 'port scan',
}

const ALL_PRESET: FilterPreset = {
  severity: 'all',
  target: 'all',
  scanner: 'all',
  sortMode: 'severity',
  dateFrom: '',
  dateTo: '',
  searchQuery: '',
}


beforeEach(() => {
  localStorageMock.clear()
  mockFetch.mockReset()
  mockFetch.mockRejectedValue(new Error('Network offline'))
})

afterEach(() => {
  vi.clearAllMocks()
})


describe('isValidPreset', () => {
  it('accepts a complete valid preset', () => {
    expect(isValidPreset(VALID_PRESET)).toBe(true)
  })

  it('accepts the all-defaults preset', () => {
    expect(isValidPreset(ALL_PRESET)).toBe(true)
  })

  it('rejects null', () => {
    expect(isValidPreset(null)).toBe(false)
  })

  it('rejects a non-object', () => {
    expect(isValidPreset('string')).toBe(false)
    expect(isValidPreset(42)).toBe(false)
  })

  it('rejects an object missing required fields', () => {
    expect(isValidPreset({ severity: 'all' })).toBe(false)
  })

  it('rejects invalid sortMode', () => {
    expect(isValidPreset({ ...VALID_PRESET, sortMode: 'by_moon_phase' })).toBe(false)
  })

  it('rejects invalid severity', () => {
    expect(isValidPreset({ ...VALID_PRESET, severity: 'apocalyptic' })).toBe(false)
  })
})


describe('isValidSavedView', () => {
  const view = {
    id: 'abc-123',
    name: 'My View',
    preset: VALID_PRESET,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }

  it('accepts a complete valid view', () => {
    expect(isValidSavedView(view)).toBe(true)
  })

  it('rejects a view with a missing id', () => {
    expect(isValidSavedView({ ...view, id: '' })).toBe(false)
  })

  it('rejects a view with an invalid preset', () => {
    expect(isValidSavedView({ ...view, preset: { severity: 'bad' } })).toBe(false)
  })

  it('rejects a non-object', () => {
    expect(isValidSavedView(null)).toBe(false)
  })
})


describe('useSavedViews — localStorage fallback (no backend)', () => {
  it('starts empty when localStorage is empty', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.views).toHaveLength(0)
  })

  it('creates a new view and returns it', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    let saved: Awaited<ReturnType<typeof result.current.saveView>> | undefined

    await act(async () => {
      saved = await result.current.saveView('My Scan', VALID_PRESET)
    })

    expect(saved).toBeDefined()
    expect(saved?.name).toBe('My Scan')
    expect(saved?.preset).toEqual(VALID_PRESET)
    expect(result.current.views).toHaveLength(1)
  })

  it('persists the new view to localStorage', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Persistent', VALID_PRESET)
    })

    const raw = localStorage.getItem('secuscan-saved-views')
    expect(raw).not.toBeNull()

    const parsed = JSON.parse(raw!)
    expect(parsed).toHaveLength(1)
    expect(parsed[0].name).toBe('Persistent')
  })

  it('restores a saved view correctly (apply simulation)', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Apply Me', VALID_PRESET)
    })

    const view = result.current.views[0]
    expect(view.preset).toEqual(VALID_PRESET)
    expect(view.preset.sortMode).toBe('newest')
    expect(view.preset.severity).toBe('critical')
  })

  it('overwrites a view when the same name is saved again', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Repeat', VALID_PRESET)
    })

    const firstId = result.current.views[0].id

    const updatedPreset: FilterPreset = {
      ...VALID_PRESET,
      severity: 'high',
      sortMode: 'oldest',
    }

    await act(async () => {
      await result.current.saveView('Repeat', updatedPreset)
    })

    expect(result.current.views).toHaveLength(1)
    expect(result.current.views[0].id).toBe(firstId)
    expect(result.current.views[0].preset.severity).toBe('high')
    expect(result.current.views[0].preset.sortMode).toBe('oldest')
  })

  it('overwrite is case-insensitive on name comparison', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Alpha', VALID_PRESET)
    })

    await act(async () => {
      await result.current.saveView('alpha', ALL_PRESET)
    })

    expect(result.current.views).toHaveLength(1)
    expect(result.current.views[0].preset.severity).toBe('all')
  })

  it('renames a view', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Old Name', VALID_PRESET)
    })

    const id = result.current.views[0].id

    await act(async () => {
      await result.current.renameView(id, 'New Name')
    })

    expect(result.current.views[0].name).toBe('New Name')
  })

  it('throws when renaming with an empty string', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Name', VALID_PRESET)
    })

    const id = result.current.views[0].id

    await expect(
      act(async () => {
        await result.current.renameView(id, '   ')
      }),
    ).rejects.toThrow()
  })

  it('deletes a view by id', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Delete Me', VALID_PRESET)
    })

    const id = result.current.views[0].id

    await act(async () => {
      await result.current.deleteView(id)
    })

    expect(result.current.views).toHaveLength(0)
  })

  it('deleting a non-existent id is a no-op', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Keep', VALID_PRESET)
    })

    await act(async () => {
      await result.current.deleteView('ghost-id')
    })

    expect(result.current.views).toHaveLength(1)
  })

  it('deleting one view leaves others intact', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('Keep', VALID_PRESET)
    })

    await act(async () => {
      await result.current.saveView('Remove', ALL_PRESET)
    })

    const removeId = result.current.views.find((v) => v.name === 'Remove')!.id

    await act(async () => {
      await result.current.deleteView(removeId)
    })

    expect(result.current.views).toHaveLength(1)
    expect(result.current.views[0].name).toBe('Keep')
  })

  it('throws when saving with an empty name', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await expect(
      act(async () => {
        await result.current.saveView('', VALID_PRESET)
      }),
    ).rejects.toThrow()
  })

  it('throws when saving with a whitespace-only name', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await expect(
      act(async () => {
        await result.current.saveView('   ', VALID_PRESET)
      }),
    ).rejects.toThrow()
  })

  it('throws when saving with an invalid preset (bad sortMode)', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    const badPreset = { ...VALID_PRESET, sortMode: 'random_order' } as any

    await expect(
      act(async () => {
        await result.current.saveView('Bad Preset', badPreset)
      }),
    ).rejects.toThrow()
  })

  it('ignores corrupt localStorage data on mount', async () => {
    localStorage.setItem('secuscan-saved-views', 'this is not JSON!!!!')

    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.views).toHaveLength(0)
  })

  it('filters out invalid saved-view entries from localStorage on mount', async () => {
    const mixed = [
      {
        id: 'ok',
        name: 'Good',
        preset: VALID_PRESET,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: 'bad',
        name: 'Bad',
      },
    ]

    localStorage.setItem('secuscan-saved-views', JSON.stringify(mixed))

    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.views).toHaveLength(1)
    expect(result.current.views[0].name).toBe('Good')
  })

  it('supports multiple independent saved views', async () => {
    const { result } = renderHook(() => useSavedViews())

    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.saveView('View A', VALID_PRESET)
    })

    await act(async () => {
      await result.current.saveView('View B', ALL_PRESET)
    })

    await act(async () => {
      await result.current.saveView('View C', { ...VALID_PRESET, severity: 'low' })
    })

    expect(result.current.views).toHaveLength(3)
    expect(result.current.views.map((v) => v.name)).toEqual(expect.arrayContaining(['View A', 'View B', 'View C']))
  })
})
