import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as offlineQueue from '../../src/services/offlineQueue'
import { OfflineQueueError } from '../../src/api'

// The api module uses the offlineQueue service directly.
// We test that calling retryable API functions while offline enqueues the action.
// We import the functions dynamically to avoid top-level side effects.
async function getApi() {
  return await import('../../src/api')
}

describe('API offline integration', () => {
  beforeEach(() => {
    offlineQueue.clear()
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      value: true,
    })
  })

  afterEach(() => {
    offlineQueue.clear()
  })

  describe('retryable actions (safe/idempotent mutations only)', () => {
    it('startTask enqueues when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(
        api.startTask('test_plugin', { target: 'http://example.com' }, true),
      ).rejects.toThrow(OfflineQueueError)

      const queue = offlineQueue.getQueue()
      expect(queue).toHaveLength(1)
      expect(queue[0].label).toBe('Start Scan')
      expect(queue[0].method).toBe('POST')
    })

    it('createWorkflow enqueues when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(
        api.createWorkflow({ name: 'test', schedule_interval: 'manual', enabled: true, steps: [] }),
      ).rejects.toThrow(OfflineQueueError)

      expect(offlineQueue.getQueue()).toHaveLength(1)
    })

    it('updateWorkflow enqueues when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.updateWorkflow('wf-1', { name: 'new' })).rejects.toThrow(OfflineQueueError)

      expect(offlineQueue.getQueue()).toHaveLength(1)
    })
  })

  describe('non-retryable actions (reads + destructive mutations)', () => {
    it('getHealth does not enqueue when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.getHealth()).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('listPlugins does not enqueue when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.listPlugins()).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('getFindings does not enqueue when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.getFindings()).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('getTasks does not enqueue when offline', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.getTasks()).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('deleteTask does not enqueue when offline (destructive)', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.deleteTask('task-123')).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('cancelTask does not enqueue when offline (non-idempotent)', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.cancelTask('task-123')).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('bulkDeleteTasks does not enqueue when offline (destructive)', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.bulkDeleteTasks(['a', 'b'])).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('clearAllTasks does not enqueue when offline (destructive)', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.clearAllTasks()).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('deleteWorkflow does not enqueue when offline (destructive)', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.deleteWorkflow('wf-1')).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('runWorkflow does not enqueue when offline (non-idempotent)', async () => {
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: false })
      const api = await getApi()

      await expect(api.runWorkflow('wf-1')).rejects.toThrow()
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })
  })

  describe('online behavior unchanged', () => {
    it('retryable actions still call fetch when online', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ task_id: 'abc', status: 'running', created_at: 'now', stream_url: '/stream' }),
      })
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
      const api = await getApi()

      const result = await api.startTask('test_plugin', {}, false)
      expect(result).toEqual({ task_id: 'abc', status: 'running', created_at: 'now', stream_url: '/stream' })
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })

    it('non-retryable actions call fetch when online', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' }),
      })
      Object.defineProperty(navigator, 'onLine', { configurable: true, value: true })
      const api = await getApi()

      const result = await api.getHealth()
      expect(result).toEqual({ status: 'ok' })
      expect(offlineQueue.getQueue()).toHaveLength(0)
    })
  })
})
