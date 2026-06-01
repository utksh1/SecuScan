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

  describe('conflict checks', () => {
    it('removes updateWorkflow when resource is gone (GET 404)', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) return Promise.resolve({ ok: false, status: 404 })
        return Promise.resolve({ ok: true })
      })

      const action = offlineQueue.enqueue({
        url: '/api/v1/workflows/wf-1',
        method: 'PATCH',
        body: '{"name":"new"}',
        maxRetries: 3,
        actionType: 'updateWorkflow',
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(false)
      expect(offlineQueue.getQueue()).toHaveLength(0)
      expect(callCount).toBe(1)
    })

    it('removes createWorkflow when workflow name already exists (conflict)', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            workflows: [{ name: 'test' }],
            total: 1,
          }),
        })
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
      })

      const action = offlineQueue.enqueue({
        url: '/api/v1/workflows',
        method: 'POST',
        body: JSON.stringify({ name: 'test', enabled: true, steps: [] }),
        maxRetries: 3,
        actionType: 'createWorkflow',
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(false)
      expect(offlineQueue.getQueue()).toHaveLength(0)
      expect(callCount).toBe(1)
    })

    it('proceeds with createWorkflow when workflow name is unique (no conflict)', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            workflows: [{ name: 'other' }],
            total: 1,
          }),
        })
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ id: 'wf-2' }) })
      })

      const action = offlineQueue.enqueue({
        url: '/api/v1/workflows',
        method: 'POST',
        body: JSON.stringify({ name: 'new-workflow', enabled: true, steps: [] }),
        maxRetries: 3,
        actionType: 'createWorkflow',
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(true)
      expect(offlineQueue.getQueue()).toHaveLength(0)
      expect(callCount).toBe(2)
    })

    it('removes startTask when similar task is already running (conflict)', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            tasks: [{ plugin_id: 'test_plugin', status: 'running' }],
          }),
        })
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
      })

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/start',
        method: 'POST',
        body: JSON.stringify({ plugin_id: 'test_plugin', inputs: {} }),
        maxRetries: 3,
        actionType: 'startTask',
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(false)
      expect(offlineQueue.getQueue()).toHaveLength(0)
      expect(callCount).toBe(1)
    })

    it('proceeds with startTask when no similar task is running (no conflict)', async () => {
      let callCount = 0
      global.fetch = vi.fn().mockImplementation(() => {
        callCount++
        if (callCount === 1) return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            tasks: [{ plugin_id: 'other_plugin', status: 'completed' }],
          }),
        })
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ task_id: 'task-1' }) })
      })

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/start',
        method: 'POST',
        body: JSON.stringify({ plugin_id: 'test_plugin', inputs: {} }),
        maxRetries: 3,
        actionType: 'startTask',
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(true)
      expect(offlineQueue.getQueue()).toHaveLength(0)
      expect(callCount).toBe(2)
    })

    it('skips conflict check when actionType is not set (backward compat)', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      const action = offlineQueue.enqueue({
        url: '/api/v1/task/start',
        method: 'POST',
        body: '{}',
        maxRetries: 3,
      })

      const ok = await offlineQueue.retry(action.id)
      expect(ok).toBe(true)
      expect(global.fetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('auto-replay is disabled', () => {
    it('does not auto-replay on reconnect (default is false)', () => {
      const retryAllSpy = vi.spyOn(offlineQueue, 'retryAll')
      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })

      window.dispatchEvent(new Event('online'))

      expect(retryAllSpy).not.toHaveBeenCalled()
      retryAllSpy.mockRestore()
    })

    it('setAutoReplay is preserved for backward compat', () => {
      expect(() => offlineQueue.setAutoReplay(false)).not.toThrow()
      expect(() => offlineQueue.setAutoReplay(true)).not.toThrow()
    })
  })

  describe('queue safety boundaries', () => {
    it('enforces max queue size and throws when full', () => {
      for (let i = 0; i < 50; i++) {
        offlineQueue.enqueue({ url: `/a/${i}`, method: 'POST', maxRetries: 3 })
      }
      expect(() => offlineQueue.enqueue({ url: '/overflow', method: 'POST', maxRetries: 3 })).toThrow('Queue is full')
      expect(offlineQueue.getQueue()).toHaveLength(50)
    })

    it('drops stale entries older than TTL on load', () => {
      const oldTimestamp = Date.now() - 86_400_001 // 24h + 1ms
      const stale = [{ id: 'old', url: '/stale', method: 'POST', timestamp: oldTimestamp, retryCount: 0, maxRetries: 3 }]
      mockStorage.getItem.mockReturnValue(JSON.stringify(stale))

      const fresh = offlineQueue.enqueue({ url: '/fresh', method: 'POST', maxRetries: 3 })
      expect(offlineQueue.getQueue()).toHaveLength(1)
      expect(offlineQueue.getQueue()[0].id).toBe(fresh.id)
    })

    it('falls back to in-memory when localStorage fails on persist', () => {
      mockStorage.setItem.mockImplementation(() => { throw new Error('QuotaExceeded') })
      const action = offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3 })
      expect(action).not.toBeNull()
      expect(offlineQueue.getQueue()).toHaveLength(1)
    })
  })

  describe('onReconnect guard', () => {
    it('does not replay when autoReplay is disabled', async () => {
      offlineQueue.setAutoReplay(false)
      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({ ok: true } as Response)
      offlineQueue.enqueue({ url: '/a', method: 'POST', maxRetries: 3, actionType: 'startTask' })
      offlineQueue.enqueue({ url: '/b', method: 'POST', maxRetries: 3, actionType: 'createWorkflow' })

      const count = await offlineQueue.onReconnect()
      expect(count).toBe(0)
      expect(fetchSpy).not.toHaveBeenCalled()
      fetchSpy.mockRestore()
    })

    it('only replays safe action types when autoReplay is enabled', async () => {
      offlineQueue.setAutoReplay(true)
      global.fetch = vi.fn().mockResolvedValue({ ok: true })
      offlineQueue.enqueue({ url: '/safe', method: 'POST', maxRetries: 3, actionType: 'startTask' })
      offlineQueue.enqueue({ url: '/unsafe', method: 'DELETE', maxRetries: 3, actionType: undefined })

      const count = await offlineQueue.onReconnect()
      expect(count).toBe(1)
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })

    it('returns 0 and replays nothing when autoReplay is enabled but queue has no safe action types', async () => {
      offlineQueue.setAutoReplay(true)
      global.fetch = vi.fn().mockResolvedValue({ ok: true })
      offlineQueue.enqueue({ url: '/unsafe', method: 'DELETE', maxRetries: 3, actionType: undefined })

      const count = await offlineQueue.onReconnect()
      expect(count).toBe(0)
      expect(global.fetch).not.toHaveBeenCalled()
    })

    it('replays nothing when queue is empty', async () => {
      offlineQueue.setAutoReplay(true)
      const count = await offlineQueue.onReconnect()
      expect(count).toBe(0)
    })
  })

  describe('SAFE_ACTION_TYPES', () => {
    it('only includes startTask, createWorkflow, updateWorkflow', () => {
      expect(offlineQueue.SAFE_ACTION_TYPES).toEqual(['startTask', 'createWorkflow', 'updateWorkflow'])
      expect(offlineQueue.SAFE_ACTION_TYPES).not.toContain('deleteTask')
      expect(offlineQueue.SAFE_ACTION_TYPES).not.toContain('cancelTask')
      expect(offlineQueue.SAFE_ACTION_TYPES).not.toContain('clearAllTasks')
      expect(offlineQueue.SAFE_ACTION_TYPES).not.toContain('runWorkflow')
      expect(offlineQueue.SAFE_ACTION_TYPES).not.toContain('deleteWorkflow')
      expect(offlineQueue.SAFE_ACTION_TYPES).not.toContain('bulkDeleteTasks')
    })
  })
})
