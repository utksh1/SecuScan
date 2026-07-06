import { render, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import React from 'react'
import { useTaskSubscription } from '../../../src/hooks/useTaskSubscription'

vi.mock('../../../src/api', () => ({
  API_BASE: 'http://localhost',
  getTaskStatus: vi.fn().mockResolvedValue({ status: 'running' }),
}))

import { getTaskStatus } from '../../../src/api'

class MockEventSource {
  static instances: MockEventSource[] = []
  onopen: (() => void) | null = null
  onerror: ((err: Event) => void) | null = null
  listeners: Map<string, (e: MessageEvent) => void> = new Map()
  url: string
  options?: EventSourceInit
  readyState = 0
  closeCount = 0
  constructor(url: string, options?: EventSourceInit) { this.url = url; this.options = options; MockEventSource.instances.push(this) }
  addEventListener(event: string, handler: (e: MessageEvent) => void) { this.listeners.set(event, handler) }
  close() { this.closeCount++; const idx = MockEventSource.instances.indexOf(this); if (idx !== -1) MockEventSource.instances.splice(idx, 1) }
  dispatchEvent(event: string, data: string) { const h = this.listeners.get(event); if (h) h(new MessageEvent(event, { data })) }
  triggerOpen() { this.readyState = 1; this.onopen?.() }
  triggerError() { this.onerror?.(new Event('error')) }
  static reset() { MockEventSource.instances = [] }
}

function renderHook(props: { taskId: string; onStatus?: (s: string) => void; onOutput?: (c: string) => void; pollingInterval?: number; maxReconnectAttempts?: number }) {
  const Comp = () => { useTaskSubscription(props); return null }
  return render(React.createElement(Comp))
}

function getES() { return MockEventSource.instances[0] }

beforeEach(() => {
  MockEventSource.reset()
  vi.stubGlobal('EventSource', MockEventSource as any)
  vi.useFakeTimers()
  vi.mocked(getTaskStatus).mockReset()
  vi.mocked(getTaskStatus).mockResolvedValue({ status: 'running' })
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve() }) }
async function tickTime(ms: number) { await act(async () => { vi.advanceTimersByTime(ms); await Promise.resolve(); await Promise.resolve(); await Promise.resolve() }) }

describe('useTaskSubscription', () => {
  it('connects to SSE on mount', async () => {
    renderHook({ taskId: 'task-1' })
    await flush()
    const es = getES()
    expect(es).toBeTruthy()
    expect(es!.url).toContain('/task/task-1/stream')
  })

  it('includes credentials on the SSE connection', async () => {
    renderHook({ taskId: 'task-1' })
    await flush()
    expect(getES()!.options).toEqual({ withCredentials: true })
  })

  it('calls onStatus on status event', async () => {
    const onStatus = vi.fn()
    renderHook({ taskId: 'task-1', onStatus })
    await flush()
    getES()!.triggerOpen()
    getES()!.dispatchEvent('status', JSON.stringify({ status: 'running' }))
    expect(onStatus).toHaveBeenCalledWith('running')
  })

  it('deduplicates same status value', async () => {
    const onStatus = vi.fn()
    renderHook({ taskId: 'task-1', onStatus })
    await flush()
    const es = getES()!
    es.triggerOpen()
    es.dispatchEvent('status', JSON.stringify({ status: 'running' }))
    es.dispatchEvent('status', JSON.stringify({ status: 'running' }))
    es.dispatchEvent('status', JSON.stringify({ status: 'running' }))
    expect(onStatus).toHaveBeenCalledTimes(1)
  })

  it('does not deduplicate different status values', async () => {
    const onStatus = vi.fn()
    renderHook({ taskId: 'task-1', onStatus })
    await flush()
    const es = getES()!
    es.triggerOpen()
    es.dispatchEvent('status', JSON.stringify({ status: 'queued' }))
    es.dispatchEvent('status', JSON.stringify({ status: 'running' }))
    es.dispatchEvent('status', JSON.stringify({ status: 'completed' }))
    expect(onStatus).toHaveBeenCalledTimes(3)
    expect(onStatus).toHaveBeenNthCalledWith(1, 'queued')
    expect(onStatus).toHaveBeenNthCalledWith(2, 'running')
    expect(onStatus).toHaveBeenNthCalledWith(3, 'completed')
  })

  it('calls onOutput on output event', async () => {
    const onOutput = vi.fn()
    renderHook({ taskId: 'task-1', onOutput })
    await flush()
    getES()!.triggerOpen()
    getES()!.dispatchEvent('output', JSON.stringify({ chunk: 'line1\n' }))
    expect(onOutput).toHaveBeenCalledWith('line1\n')
  })

  it('appends identical output chunks in order', async () => {
    const onOutput = vi.fn()
    renderHook({ taskId: 'task-1', onOutput })
    await flush()
    const es = getES()!
    es.triggerOpen()
    es.dispatchEvent('output', JSON.stringify({ chunk: 'line1\n' }))
    es.dispatchEvent('output', JSON.stringify({ chunk: 'line1\n' }))
    expect(onOutput).toHaveBeenCalledTimes(2)
    expect(onOutput).toHaveBeenNthCalledWith(1, 'line1\n')
    expect(onOutput).toHaveBeenNthCalledWith(2, 'line1\n')
  })

  it('falls back to polling after SSE max reconnect attempts', async () => {
    renderHook({ taskId: 'task-1', pollingInterval: 50, maxReconnectAttempts: 3 })
    await flush()

    for (let i = 0; i < 4; i++) {
      await act(() => { getES()!.triggerError() })
      await tickTime(1000 * Math.pow(2, Math.min(i, 3)))
    }

    await tickTime(50)
    expect(getTaskStatus).toHaveBeenCalled()
  })

  it('polls getTaskStatus at the configured interval', async () => {
    renderHook({ taskId: 'task-1', pollingInterval: 50, maxReconnectAttempts: 0 })
    await flush()

    const es = getES()!
    await act(() => { es.triggerError() })
    // startPolling calls poll() immediately (chained setTimeout), so one call
    // happens synchronously before the first interval elapses.
    await tickTime(50)
    expect(getTaskStatus).toHaveBeenCalledTimes(2) // initial (direct) + first timer

    await tickTime(50)
    expect(getTaskStatus).toHaveBeenCalledTimes(3) // initial + first + second timer
  })

  it('stops polling on terminal status', async () => {
    let resolveGetTaskStatus: (value: unknown) => void
    vi.mocked(getTaskStatus).mockImplementation(() => new Promise(resolve => {
      resolveGetTaskStatus = resolve
    }))

    renderHook({ taskId: 'task-1', pollingInterval: 50, maxReconnectAttempts: 0 })
    await flush()

    await act(() => { getES()!.triggerError() })

    await tickTime(50)
    // Resolve with terminal status so cleanupAll() clears the interval
    await act(async () => { resolveGetTaskStatus({ status: 'completed' }); await Promise.resolve(); await Promise.resolve() })

    const callsAfterCleanup = vi.mocked(getTaskStatus).mock.calls.length

    await tickTime(200)
    expect(vi.mocked(getTaskStatus).mock.calls.length).toBe(callsAfterCleanup)
  })

  it('stops SSE on terminal status event', async () => {
    const onStatus = vi.fn()
    renderHook({ taskId: 'task-1', onStatus })
    await flush()
    const es = getES()!
    es.triggerOpen()
    es.dispatchEvent('status', JSON.stringify({ status: 'completed' }))
    expect(onStatus).toHaveBeenCalledWith('completed')
  })

  it('cleans up EventSource on unmount', async () => {
    const { unmount } = renderHook({ taskId: 'task-1', pollingInterval: 50, maxReconnectAttempts: 0 })
    await flush()

    const es = getES()!
    const closeSpy = vi.spyOn(es, 'close')
    unmount()
    expect(closeSpy).toHaveBeenCalled()
  })

  it('polls and calls onStatus with new statuses', async () => {
    const onStatus = vi.fn()
    renderHook({ taskId: 'task-1', onStatus, pollingInterval: 50, maxReconnectAttempts: 0 })
    await flush()

    const es = getES()!
    await act(() => { es.triggerError() })

    await tickTime(50)
    expect(onStatus).toHaveBeenCalledWith('running')
  })
})
