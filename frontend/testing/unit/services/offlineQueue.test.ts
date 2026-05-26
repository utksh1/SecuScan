import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as offlineQueue from '../../../src/services/offlineQueue'

function createMockLocalStorage() {
  const store = new Map<string, string>()
  return {
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => { store.set(key, value) }),
    removeItem: vi.fn((key: string) => { store.delete(key) }),
    clear: vi.fn(() => { store.clear() }),
    key: vi.fn((i: number) => Array.from(store.keys())[i] ?? null),
    get length() { return store.size },
  }
}

function mockNavigatorOnline(onLine: boolean) {
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    value: onLine,
  })
}

describe('offlineQueue', () => {
  let mockStorage: ReturnType<typeof createMockLocalStorage>

  beforeEach(() => {
    mockStorage = createMockLocalStorage()
    Object.defineProperty(window, 'localStorage', {
      value: mockStorage,
      configurable: true,
      writable: true,
    })
    mockNavigatorOnline(true)
    offlineQueue.clear()
  })

  afterEach(() => {
    offlineQueue.clear()
  })

  describe('isRetryable', () => {
    it('returns true for POST, PATCH, PUT, DELETE', () => {
      expect(offlineQueue.isRetryable('POST')).toBe(true)
      expect(offlineQueue.isRetryable('PATCH')).toBe(true)
      expect(offlineQueue.isRetryable('PUT')).toBe(true)
      expect(offlineQueue.isRetryable('DELETE')).toBe(true)
    })

    it('returns false for GET and HEAD', () => {
      expect(offlineQueue.isRetryable('GET')).toBe(false)
      expect(offlineQueue.isRetryable('HEAD')).toBe(false)
    })
  })

  describe('enqueue / getQueue', () => {
    it('adds an action to the queue', () => {
      const action = offlineQueue.enqueue({
        url: '/api/v1/task/start',
        method: 'POST',
        body: '{"foo":"bar"}',
        maxRetries: 3,
        label: 'Start Scan',
      })

      expect(action.id).toBeTruthy()
      expect(action.url).toBe('/api/v1/task/start')
      expect(action.method).toBe('POST')
      expect(action.retryCount).toBe(0)
      expect(action.timestamp).toBeGreaterThan(0)

      const queue = offlineQueue.getQueue()
      expect(queue).toHaveLength(1)
      expect(queue[0].id).toBe(action.id)
    })

    it('persists to localStorage', () => {
      offlineQueue.enqueue({
        url: '/api/v1/task/abc',
        method: 'DELETE',
        maxRetries: 3,
        label: 'Delete Task',
      })

      const saved = mockStorage.getItem('offline-queue')
      expect(saved).toBeTruthy()
      const parsed = JSON.parse(saved!)
      expect(parsed).toHaveLength(1)
      expect(parsed[0].method).toBe('DELETE')
    })

    it('queues multiple actions', () => {
      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })
      offlineQueue.enqueue({ url: '/b', method: 'DELETE', maxRetries: 3 })
      expect(offlineQueue.getQueue()).toHaveLength(2)
    })
  })

  describe('remove', () => {
    it('removes an action by id', () => {
      const a = offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })
      offlineQueue.enqueue({ url: '/b', method: 'DELETE', maxRetries: 3 })

      offlineQueue.remove(a.id)

      expect(offlineQueue.getQueue()).toHaveLength(1)
      expect(offlineQueue.getQueue()[0].url).toBe('/b')
    })

    it('does nothing for unknown id', () => {
      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })
      offlineQueue.remove('nonexistent')
      expect(offlineQueue.getQueue()).toHaveLength(1)
    })
  })

  describe('clear', () => {
    it('removes all actions', () => {
      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })
      offlineQueue.enqueue({ url: '/b', method: 'DELETE', maxRetries: 3 })
      offlineQueue.clear()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })
  })

  describe('retry', () => {
    it('replays a queued action and removes it on success', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/start',
        method: 'POST',
        body: '{}',
        maxRetries: 3,
        label: 'Start Scan',
        headers: { 'X-Custom': 'val' },
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(true)
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/task/start',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Custom': 'val' },
          body: '{}',
        }),
      )
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('increments retryCount on failure and keeps item in queue', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/abc',
        method: 'DELETE',
        maxRetries: 3,
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(false)

      const remaining = offlineQueue.getQueue()
      expect(remaining).toHaveLength(1)
      expect(remaining[0].retryCount).toBe(1)
    })

    it('returns false for unknown id', async () => {
      const result = await offlineQueue.retry('nonexistent')
      expect(result).toBe(false)
    })

    it('removes action when server returns 404 (stale resource)', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 })

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/abc',
        method: 'DELETE',
        maxRetries: 3,
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(false)
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('removes action when server returns 410 (gone)', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 410 })

      const action = offlineQueue.enqueue({
        url: '/api/v1/workflows/wf-1',
        method: 'PATCH',
        maxRetries: 3,
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(false)
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('removes action when maxRetries exceeded', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/start',
        method: 'POST',
        maxRetries: 2,
      })

      await offlineQueue.retry(action.id)
      expect(offlineQueue.getQueue()).toHaveLength(1)
      expect(offlineQueue.getQueue()[0].retryCount).toBe(1)

      await offlineQueue.retry(action.id)
      expect(offlineQueue.getQueue()).toHaveLength(1)
      expect(offlineQueue.getQueue()[0].retryCount).toBe(2)

      await offlineQueue.retry(action.id)
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })
  })

  describe('retryAll', () => {
    it('replays all queued actions', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      offlineQueue.enqueue({ url: '/a', method: 'POST', body: '{}', maxRetries: 3 })
      offlineQueue.enqueue({ url: '/b', method: 'DELETE', maxRetries: 3 })

      const successCount = await offlineQueue.retryAll()
      expect(successCount).toBe(2)
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('reports partial success on mixed results', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) return Promise.resolve({ ok: true })
        return Promise.reject(new Error('fail'))
      })

      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })
      offlineQueue.enqueue({ url: '/b', method: 'DELETE', maxRetries: 3 })

      const successCount = await offlineQueue.retryAll()
      expect(successCount).toBe(1)
      expect(offlineQueue.getQueue()).toHaveLength(1)
    })
  })

  describe('subscribe', () => {
    it('notifies listeners on queue changes', () => {
      const listener = vi.fn()
      offlineQueue.subscribe(listener)

      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })

      expect(listener).toHaveBeenCalledTimes(1)
    })

    it('returns an unsubscribe function', () => {
      const listener = vi.fn()
      const unsub = offlineQueue.subscribe(listener)

      unsub()
      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })

      expect(listener).not.toHaveBeenCalled()
    })
  })

  describe('isOnline', () => {
    it('returns navigator.onLine status', () => {
      mockNavigatorOnline(true)
      expect(offlineQueue.isOnline()).toBe(true)

      mockNavigatorOnline(false)
      expect(offlineQueue.isOnline()).toBe(false)
    })
  })

  describe('setAutoReplay', () => {
    it('toggles autoReplayEnabled', () => {
      expect(() => offlineQueue.setAutoReplay(false)).not.toThrow()
      expect(() => offlineQueue.setAutoReplay(true)).not.toThrow()
    })
  })
})
