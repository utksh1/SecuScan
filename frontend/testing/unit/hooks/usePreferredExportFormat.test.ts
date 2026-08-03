import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePreferredExportFormat } from '../../../src/hooks/usePreferredExportFormat'

const STORAGE_KEY = 'secuscan:preferred-export-format'

describe('usePreferredExportFormat', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts with no preferred format when storage is empty', () => {
    const { result } = renderHook(() => usePreferredExportFormat())

    expect(result.current.preferred).toBeNull()
  })

  it('restores a stored preferred format on first render', () => {
    localStorage.setItem(STORAGE_KEY, 'pdf')

    const { result } = renderHook(() => usePreferredExportFormat())

    expect(result.current.preferred).toBe('pdf')
  })

  it('persists a newly selected preferred format', () => {
    const { result } = renderHook(() => usePreferredExportFormat())

    act(() => {
      result.current.savePreference('csv')
    })

    expect(result.current.preferred).toBe('csv')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('csv')
  })

  it('returns null on init when localStorage.getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('Access denied', 'SecurityError')
    })

    const { result } = renderHook(() => usePreferredExportFormat())

    expect(result.current.preferred).toBeNull()
    vi.restoreAllMocks()
  })

  it('still updates React state when localStorage.setItem throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('Access denied', 'SecurityError')
    })

    const { result } = renderHook(() => usePreferredExportFormat())

    act(() => {
      result.current.savePreference('html')
    })

    expect(result.current.preferred).toBe('html')
    vi.restoreAllMocks()
  })
})
