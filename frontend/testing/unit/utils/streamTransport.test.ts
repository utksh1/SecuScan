import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  buildTaskStreamUrl,
  createReconnectBackoff,
  createReconnectingEventSource,
  createReconnectingWebSocket,
  resolveSseUrl,
  resolveWsBase,
  resolveWsUrl,
} from '../../../src/utils/streamTransport'

describe('streamTransport URL resolution', () => {
  const originalLocation = window.location

  beforeEach(() => {
    vi.stubGlobal('location', {
      ...originalLocation,
      protocol: 'http:',
      host: 'localhost:5173',
      origin: 'http://localhost:5173',
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('resolves relative SSE task stream URLs from a proxied API base', () => {
    expect(buildTaskStreamUrl('/api/v1', 'task-1')).toBe('/api/v1/task/task-1/stream')
  })

  it('resolves absolute SSE task stream URLs from an explicit API base', () => {
    expect(buildTaskStreamUrl('http://127.0.0.1:8000/api/v1', 'task-1')).toBe(
      'http://127.0.0.1:8000/api/v1/task/task-1/stream',
    )
  })

  it('resolves backend-provided stream_url values consistently', () => {
    expect(resolveSseUrl('/api/v1', '/api/v1/task/task-1/stream')).toBe('/api/v1/task/task-1/stream')
    expect(resolveSseUrl('http://127.0.0.1:8000/api/v1', '/api/v1/task/task-1/stream')).toBe(
      'http://127.0.0.1:8000/api/v1/task/task-1/stream',
    )
  })

  it('resolves WebSocket feed URLs under the same API base', () => {
    expect(resolveWsUrl('/api/v1')).toBe('ws://localhost:5173/api/v1/ws/feed')
    expect(resolveWsUrl('http://127.0.0.1:8000/api/v1')).toBe('ws://127.0.0.1:8000/api/v1/ws/feed')
    expect(resolveWsUrl('https://secuscan.example/api/v1')).toBe('wss://secuscan.example/api/v1/ws/feed')
  })

  it('exposes the WebSocket base without the feed suffix', () => {
    expect(resolveWsBase('/api/v1')).toBe('ws://localhost:5173/api/v1')
    expect(resolveWsBase('http://127.0.0.1:8000/api/v1')).toBe('ws://127.0.0.1:8000/api/v1')
  })
})

describe('createReconnectBackoff', () => {
  it('returns exponential delays until max attempts are exhausted', () => {
    const backoff = createReconnectBackoff({ baseDelay: 1000, maxAttempts: 3 })

    expect(backoff.canRetry()).toBe(true)
    expect(backoff.nextDelay()).toBe(1000)
    expect(backoff.canRetry()).toBe(true)
    expect(backoff.nextDelay()).toBe(2000)
    expect(backoff.canRetry()).toBe(true)
    expect(backoff.nextDelay()).toBe(4000)
    expect(backoff.canRetry()).toBe(false)
  })

  it('resets attempt count after a successful connection', () => {
    const backoff = createReconnectBackoff({ baseDelay: 500, maxAttempts: 2 })
    backoff.nextDelay()
    backoff.reset()

    expect(backoff.canRetry()).toBe(true)
    expect(backoff.nextDelay()).toBe(500)
  })
})

class MockEventSource {
  static instances: MockEventSource[] = []
  onopen: (() => void) | null = null
  onerror: ((err: Event) => void) | null = null
  readyState = 0
  closeCount = 0

  constructor(public url: string) {
    MockEventSource.instances.push(this)
  }

  close() {
    this.closeCount++
    const idx = MockEventSource.instances.indexOf(this)
    if (idx !== -1) MockEventSource.instances.splice(idx, 1)
  }

  triggerOpen() {
    this.readyState = 1
    this.onopen?.()
  }

  triggerError() {
    this.onerror?.(new Event('error'))
  }

  static reset() {
    MockEventSource.instances = []
  }
}

class MockWebSocket {
  static instances: MockWebSocket[] = []
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((err: Event) => void) | null = null
  readyState = 0
  closeCount = 0

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  close() {
    this.closeCount++
    const idx = MockWebSocket.instances.indexOf(this)
    if (idx !== -1) MockWebSocket.instances.splice(idx, 1)
    this.onclose?.()
  }

  triggerOpen() {
    this.readyState = 1
    this.onopen?.()
  }

  triggerClose() {
    this.onclose?.()
  }

  static reset() {
    MockWebSocket.instances = []
  }
}

describe('reconnecting transports', () => {
  beforeEach(() => {
    MockEventSource.reset()
    MockWebSocket.reset()
    vi.stubGlobal('EventSource', MockEventSource as unknown as typeof EventSource)
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('reconnects SSE with exponential backoff', () => {
    const onReconnect = vi.fn()
    const connection = createReconnectingEventSource('http://localhost/stream', {
      maxReconnectAttempts: 2,
      reconnectBaseDelay: 1000,
      onReconnect,
    })

    const first = MockEventSource.instances[0]
    first.triggerError()

    expect(onReconnect).toHaveBeenCalledWith(1, 1000)
    vi.advanceTimersByTime(1000)
    expect(MockEventSource.instances).toHaveLength(1)

    MockEventSource.instances[0].triggerError()
    expect(onReconnect).toHaveBeenCalledWith(2, 2000)

    connection.close()
  })

  it('reconnects WebSocket with exponential backoff', () => {
    const onReconnect = vi.fn()
    const connection = createReconnectingWebSocket('ws://localhost/api/v1/ws/feed', {
      maxReconnectAttempts: 2,
      reconnectBaseDelay: 500,
      onReconnect,
    })

    MockWebSocket.instances[0].triggerClose()
    expect(onReconnect).toHaveBeenCalledWith(1, 500)

    vi.advanceTimersByTime(500)
    expect(MockWebSocket.instances[MockWebSocket.instances.length - 1]?.url).toBe('ws://localhost/api/v1/ws/feed')

    connection.close()
  })
})
