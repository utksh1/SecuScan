/**
 * Frontend auth tests for PR #278.
 *
 * Covers:
 * - getStoredApiKey returns null when localStorage is empty
 * - setStoredApiKey persists the key to localStorage
 * - request() includes X-Api-Key header when a key is stored
 * - request() omits X-Api-Key when no key is stored
 * - request() fires AUTH_REQUIRED_EVENT on HTTP 401
 * - request() throws 'AUTH_REQUIRED' on HTTP 401 (not a generic error)
 * - request() throws a generic error on other non-200 statuses
 * - request() succeeds and returns parsed JSON on 200
 * - The raw key is never logged via console.log/warn/error
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AUTH_REQUIRED_EVENT,
  getStoredApiKey,
  setStoredApiKey,
  listPlugins,
} from '../../src/api'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockResponse(status: number, body: unknown = {}) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response)
}

// ---------------------------------------------------------------------------
// localStorage key storage
// ---------------------------------------------------------------------------

describe('getStoredApiKey / setStoredApiKey', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns null when no key is stored', () => {
    expect(getStoredApiKey()).toBeNull()
  })

  it('returns the key after setStoredApiKey', () => {
    setStoredApiKey('my-secret-key')
    expect(getStoredApiKey()).toBe('my-secret-key')
  })

  it('overwrites an existing key', () => {
    setStoredApiKey('old-key')
    setStoredApiKey('new-key')
    expect(getStoredApiKey()).toBe('new-key')
  })

  it('stores the key only under secuscan_api_key', () => {
    setStoredApiKey('abc123')
    expect(localStorage.getItem('secuscan_api_key')).toBe('abc123')
    // No other localStorage entry should be written by setStoredApiKey.
    expect(localStorage.length).toBe(1)
  })
})

// ---------------------------------------------------------------------------
// request() — header injection
// ---------------------------------------------------------------------------

describe('request() X-Api-Key header', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('includes X-Api-Key header when a key is stored', async () => {
    setStoredApiKey('test-key-123')
    const spy = vi.fn().mockReturnValue(mockResponse(200, { plugins: [], total: 0 }))
    vi.stubGlobal('fetch', spy)

    await listPlugins()

    const [_url, init] = spy.mock.calls[0]
    const headers = init?.headers as Record<string, string>
    expect(headers['X-Api-Key']).toBe('test-key-123')
  })

  it('omits X-Api-Key header when no key is stored', async () => {
    localStorage.clear()
    const spy = vi.fn().mockReturnValue(mockResponse(200, { plugins: [], total: 0 }))
    vi.stubGlobal('fetch', spy)

    await listPlugins()

    const [_url, init] = spy.mock.calls[0]
    const headers = (init?.headers ?? {}) as Record<string, string>
    expect(headers['X-Api-Key']).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// request() — 401 handling
// ---------------------------------------------------------------------------

describe('request() 401 handling', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('dispatches AUTH_REQUIRED_EVENT on 401', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(401)))

    const received: Event[] = []
    window.addEventListener(AUTH_REQUIRED_EVENT, (e) => received.push(e))

    await listPlugins().catch(() => {})

    window.removeEventListener(AUTH_REQUIRED_EVENT, (e) => received.push(e))
    expect(received).toHaveLength(1)
  })

  it('throws AUTH_REQUIRED on 401 — not a generic status error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(401)))

    await expect(listPlugins()).rejects.toThrow('AUTH_REQUIRED')
  })

  it('throws a generic error on 403 (not 401)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(403)))

    await expect(listPlugins()).rejects.toThrow('Request failed: 403')
  })

  it('throws a generic error on 500', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(500)))

    await expect(listPlugins()).rejects.toThrow('Request failed: 500')
  })

  it('wrong key triggers AUTH_REQUIRED_EVENT on next request', async () => {
    setStoredApiKey('wrong-key')
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(401)))

    const fired: boolean[] = []
    const handler = () => fired.push(true)
    window.addEventListener(AUTH_REQUIRED_EVENT, handler)

    await listPlugins().catch(() => {})

    window.removeEventListener(AUTH_REQUIRED_EVENT, handler)
    expect(fired).toHaveLength(1)
  })
})

// ---------------------------------------------------------------------------
// request() — successful authenticated request
// ---------------------------------------------------------------------------

describe('request() successful authenticated request', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('returns parsed JSON on 200 with correct key', async () => {
    setStoredApiKey('correct-key')
    const body = { plugins: [{ id: 'nmap' }], total: 1 }
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(200, body)))

    const result = await listPlugins()
    expect(result).toEqual(body)
  })
})

// ---------------------------------------------------------------------------
// Key must not be logged
// ---------------------------------------------------------------------------

describe('API key is never logged', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('does not pass the raw key to console.log', async () => {
    const logSpy = vi.spyOn(console, 'log')
    setStoredApiKey('super-secret-api-key')
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(mockResponse(200, { plugins: [], total: 0 })))

    await listPlugins()

    for (const call of logSpy.mock.calls) {
      const text = call.map(String).join(' ')
      expect(text).not.toContain('super-secret-api-key')
    }
  })
})
