import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import {
  ESCAPE_EVENT,
  useEscapeToClose,
} from '../../../src/hooks/useEscapeToClose'

function pressEscape() {
  window.dispatchEvent(new CustomEvent(ESCAPE_EVENT))
}

describe('useEscapeToClose', () => {
  it('closes when escape is broadcast while open', () => {
    const onClose = vi.fn()
    renderHook(() => useEscapeToClose(true, onClose))

    pressEscape()

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does nothing while closed', () => {
    const onClose = vi.fn()
    renderHook(() => useEscapeToClose(false, onClose))

    pressEscape()

    expect(onClose).not.toHaveBeenCalled()
  })

  it('stops listening once closed', () => {
    const onClose = vi.fn()
    const { rerender } = renderHook(
      ({ isOpen }) => useEscapeToClose(isOpen, onClose),
      { initialProps: { isOpen: true } },
    )

    rerender({ isOpen: false })
    pressEscape()

    expect(onClose).not.toHaveBeenCalled()
  })

  it('removes its listener on unmount', () => {
    const onClose = vi.fn()
    const { unmount } = renderHook(() => useEscapeToClose(true, onClose))

    unmount()
    pressEscape()

    expect(onClose).not.toHaveBeenCalled()
  })

  it('closes on each subsequent escape while it stays open', () => {
    const onClose = vi.fn()
    renderHook(() => useEscapeToClose(true, onClose))

    pressEscape()
    pressEscape()

    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('only the open overlay reacts when several are mounted', () => {
    const openClose = vi.fn()
    const closedClose = vi.fn()
    renderHook(() => useEscapeToClose(true, openClose))
    renderHook(() => useEscapeToClose(false, closedClose))

    pressEscape()

    expect(openClose).toHaveBeenCalledTimes(1)
    expect(closedClose).not.toHaveBeenCalled()
  })
})
