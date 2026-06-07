import { renderHook, act } from '@testing-library/react'
import { usePreferredExportFormat } from "../../../src/hooks/usePreferredExportFormat";

const STORAGE_KEY = 'secuscan:preferred-export-format'

beforeEach(() => {
  localStorage.clear()
})

describe('usePreferredExportFormat', () => {
  it('returns null as default when no preference is stored', () => {
    const { result } = renderHook(() => usePreferredExportFormat())
    expect(result.current.preferred).toBeNull()
  })

  it('returns stored preference from localStorage on mount', () => {
    localStorage.setItem(STORAGE_KEY, 'pdf')
    const { result } = renderHook(() => usePreferredExportFormat())
    expect(result.current.preferred).toBe('pdf')
  })

  it('saves preference to localStorage when savePreference is called', () => {
    const { result } = renderHook(() => usePreferredExportFormat())
    act(() => {
      result.current.savePreference('csv')
    })
    expect(localStorage.getItem(STORAGE_KEY)).toBe('csv')
  })

  it('updates preferred state when savePreference is called', () => {
    const { result } = renderHook(() => usePreferredExportFormat())
    act(() => {
      result.current.savePreference('json')
    })
    expect(result.current.preferred).toBe('json')
  })
})