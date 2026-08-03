/**
 * Frontend API request behavior tests.
 *
 * Covers:
 * - Successful JSON responses
 * - Non-OK HTTP responses
 * - Timeout + abort behavior
 * - Timeout cleanup
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { getHealth, listPlugins } from '../../src/api'

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function mockJsonResponse(status: number, body: unknown = {}) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response)
}

// -----------------------------------------------------------------------------
// Shared cleanup
// -----------------------------------------------------------------------------

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

// -----------------------------------------------------------------------------
// Successful responses
// -----------------------------------------------------------------------------

describe('API request — successful responses', () => {
  it('successfully parses JSON response', async () => {
    const responseBody = {
      plugins: [{ id: 'nmap', name: 'Nmap' }],
      total: 1,
    }

    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(mockJsonResponse(200, responseBody)),
    )

    const result = await listPlugins()

    expect(result).toEqual(responseBody)
  })

  it('clears timeout after successful response', async () => {
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(mockJsonResponse(200, { ok: true })),
    )

    await getHealth()

    expect(clearTimeoutSpy).toHaveBeenCalled()
  })
})

// -----------------------------------------------------------------------------
// Non-OK HTTP responses
// -----------------------------------------------------------------------------

describe('API request — non-OK responses', () => {
  it('throws on non-OK HTTP response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(mockJsonResponse(500)),
    )

    await expect(getHealth()).rejects.toThrow('Request failed: 500')
  })
})

// -----------------------------------------------------------------------------
// Timeout + abort behavior
// -----------------------------------------------------------------------------

describe('API request — timeout behavior', () => {
  it('sets a 10-second timeout', async () => {
    const setTimeoutSpy = vi.spyOn(window, 'setTimeout')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(mockJsonResponse(200, {})),
    )

    await getHealth()

    expect(setTimeoutSpy).toHaveBeenCalledWith(
      expect.any(Function),
      10000,
    )
  })

  it('passes AbortSignal to fetch', async () => {
    const fetchSpy = vi
      .fn()
      .mockReturnValue(mockJsonResponse(200, {}))

    vi.stubGlobal('fetch', fetchSpy)

    await getHealth()

    const [, init] = fetchSpy.mock.calls[0]

    expect(init?.signal).toBeInstanceOf(AbortSignal)
  })

  it('aborts request when timeout expires', async () => {
    vi.useFakeTimers()

    const fetchSpy = vi.fn().mockImplementation((_, init) => {
      const signal = (init as RequestInit)?.signal

      return new Promise((_, reject) => {
        signal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'))
        })
      })
    })

    vi.stubGlobal('fetch', fetchSpy)

    const promise = getHealth()

    vi.runAllTimers()

    await expect(promise).rejects.toThrow('Aborted')
  })

  it('cleans up timeout on fetch rejection', async () => {
    vi.useFakeTimers()

    const setTimeoutSpy = vi.spyOn(window, 'setTimeout')
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout')

    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network error')),
    )

    await getHealth().catch(() => {})

    const timeoutId = setTimeoutSpy.mock.results[0].value

    expect(clearTimeoutSpy).toHaveBeenCalledWith(timeoutId)
  })
})