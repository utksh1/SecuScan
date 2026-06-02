import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('minimal polling test', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('setInterval fires with fake timers', async () => {
    const fn = vi.fn()
    setInterval(fn, 50)

    vi.advanceTimersByTime(50)
    expect(fn).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(50)
    expect(fn).toHaveBeenCalledTimes(2)
  })
})
