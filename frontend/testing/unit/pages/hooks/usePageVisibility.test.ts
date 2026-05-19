import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { usePageVisibility } from '../../../../src/hooks/usePageVisibility'

function setVisibility(state: 'visible' | 'hidden') {
    Object.defineProperty(document, 'visibilityState', {
        configurable: true,
        get: () => state,
    })
    document.dispatchEvent(new Event('visibilitychange'))
}

describe('usePageVisibility', () => {
    it('returns true when tab is visible', () => {
        setVisibility('visible')
        const { result } = renderHook(() => usePageVisibility())
        expect(result.current).toBe(true)
    })

    it('returns false when tab is hidden', () => {
        setVisibility('hidden')
        const { result } = renderHook(() => usePageVisibility())
        expect(result.current).toBe(false)
    })

    it('updates when tab becomes hidden', () => {
        setVisibility('visible')
        const { result } = renderHook(() => usePageVisibility())
        act(() => setVisibility('hidden'))
        expect(result.current).toBe(false)
    })

    it('updates when tab becomes visible again', () => {
        setVisibility('hidden')
        const { result } = renderHook(() => usePageVisibility())
        act(() => setVisibility('visible'))
        expect(result.current).toBe(true)
    })

    it('cleans up event listener on unmount', () => {
        const spy = vi.spyOn(document, 'removeEventListener')
        const { unmount } = renderHook(() => usePageVisibility())
        unmount()
        expect(spy).toHaveBeenCalledWith('visibilitychange', expect.any(Function))
        spy.mockRestore()
    })
})