import React from 'react'
import { render, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useDebouncedValue } from '../../../src/hooks/useDebouncedValue'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

interface HarnessProps {
  value: string
  delay: number
  captured: { current: string }
}

function Harness({ value, delay, captured }: HarnessProps) {
  const debounced = useDebouncedValue(value, delay)

  captured.current = debounced

  return <div data-testid="value">{debounced}</div>
}

describe('useDebouncedValue', () => {
  it('keeps the previous value until the delay expires', () => {
    const captured = {
        current: 'A',
    }

    const { rerender } = render(
    <Harness
        value="A"
        delay={300}
        captured={captured}
    />,
    )

    expect(captured.current).toBe('A')

    rerender(
    <Harness
        value="B"
        delay={300}
        captured={captured}
    />,
    )

    expect(captured.current).toBe('A')

    act(() => {
    vi.advanceTimersByTime(299)
    })

    act(() => {
    vi.advanceTimersByTime(1)
    })

    expect(captured.current).toBe('B')

  })
  it('returns only the final value after rapid changes', () => {
    // We'll implement this next.
    const captured = {
        current: 'A',
    }

    const { rerender } = render(
    <Harness
        value="A"
        delay={300}
        captured={captured}
    />,
    )

    expect(captured.current).toBe('A')

    rerender(
    <Harness
        value="AB"
        delay={300}
        captured={captured}
    />,
    )

    rerender(
    <Harness
        value="ABC"
        delay={300}
        captured={captured}
    />,
    )

    rerender(
    <Harness
        value="ABCD"
        delay={300}
        captured={captured}
    />,
    )

    expect(captured.current).toBe('A')

    act(() => {
    vi.advanceTimersByTime(300)
    })

    expect(captured.current).toBe('ABCD')

  })
  it('cleans up the timeout on unmount', () => {
  // 1. Create a spy on clearTimeout
  const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')

  const captured = {
    current: 'A',
  }

  // 2. Render harness and destructure `unmount` instead of `rerender`
  const { unmount } = render(
    <Harness
      value="A"
      delay={300}
      captured={captured}
    />,
  )

  // 3. Unmount the component before the timer fires
  unmount()

  // 4. Assert that the cleanup function called clearTimeout
  expect(clearTimeoutSpy).toHaveBeenCalledTimes(1)

  // Restore the original clearTimeout to prevent test pollution
  clearTimeoutSpy.mockRestore()
})
})