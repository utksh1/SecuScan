import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useShortcuts } from '../../../src/hooks/useShortcuts'
import { routes } from '../../../src/routes'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}))

describe('useShortcuts', () => {
  afterEach(() => {
    mockNavigate.mockClear()
    vi.clearAllMocks()
  })

  it('navigates when a registered shortcut is pressed', () => {
    renderHook(() => useShortcuts())

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd' }))

    expect(mockNavigate).toHaveBeenCalledWith(routes.dashboard)
  })

  it('cleans up keydown listener on unmount', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    const removeSpy = vi.spyOn(window, 'removeEventListener')

    const { unmount } = renderHook(() => useShortcuts())

    expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function))

    unmount()

    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
  })

  it('toggles sidebar when g + b is pressed', () => {
    const mockToggle = vi.fn()
    renderHook(() => useShortcuts(mockToggle))

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'b' }))

    expect(mockToggle).toHaveBeenCalledTimes(1)
  })

  it('ignores shortcuts while typing in an input', () => {
    renderHook(() => useShortcuts())

    const input = document.createElement('input')
    document.body.appendChild(input)

    input.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'g',
        bubbles: true,
      })
    )

    input.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'd',
        bubbles: true,
      })
    )

    expect(mockNavigate).not.toHaveBeenCalled()

    document.body.removeChild(input)
  })

  it('blurs editable input when Escape is pressed', () => {
    renderHook(() => useShortcuts())

    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()

    input.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'Escape',
        bubbles: true,
      })
    )

    expect(document.activeElement).not.toBe(input)

    document.body.removeChild(input)
  })
})