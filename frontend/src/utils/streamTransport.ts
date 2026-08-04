export interface ReconnectBackoffOptions {
  baseDelay?: number
  maxAttempts?: number
  maxDelay?: number
}

export interface ReconnectBackoff {
  reset: () => void
  canRetry: () => boolean
  nextDelay: () => number
  readonly attempts: number
}

export function createReconnectBackoff({
  baseDelay = 1000,
  maxAttempts = 5,
  maxDelay = 30_000,
}: ReconnectBackoffOptions = {}): ReconnectBackoff {
  let attempts = 0

  return {
    get attempts() {
      return attempts
    },
    reset() {
      attempts = 0
    },
    canRetry() {
      return attempts < maxAttempts
    },
    nextDelay() {
      const delay = Math.min(baseDelay * Math.pow(2, attempts), maxDelay)
      attempts++
      return delay
    },
  }
}

export interface StreamOrigins {
  httpOrigin: string
  wsOrigin: string
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function ensureLeadingSlash(value: string): string {
  return value.startsWith('/') ? value : `/${value}`
}

export function resolveStreamOrigins(apiBase: string): StreamOrigins {
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    const url = new URL(apiBase)
    const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return {
      httpOrigin: `${url.protocol}//${url.host}`,
      wsOrigin: `${wsProtocol}//${url.host}`,
    }
  }

  if (typeof window === 'undefined') {
    return { httpOrigin: '', wsOrigin: '' }
  }

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return {
    httpOrigin: window.location.origin,
    wsOrigin: `${wsProtocol}//${window.location.host}`,
  }
}

export function resolveSseUrl(apiBase: string, pathOrUrl: string): string {
  if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
    return pathOrUrl
  }

  const normalizedPath = ensureLeadingSlash(pathOrUrl)
  if (normalizedPath.startsWith('/api/')) {
    if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
      return `${resolveStreamOrigins(apiBase).httpOrigin}${normalizedPath}`
    }
    return normalizedPath
  }

  const base = trimTrailingSlash(apiBase)
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    return `${base}${normalizedPath}`
  }

  return `${base}${normalizedPath}`
}

export function resolveWsBase(apiBase: string): string {
  const base = trimTrailingSlash(apiBase)

  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    const url = new URL(base)
    const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProtocol}//${url.host}${url.pathname}`
  }

  const { wsOrigin } = resolveStreamOrigins(apiBase)
  return `${wsOrigin}${base}`
}

export function resolveWsUrl(apiBase: string, path = '/ws/feed'): string {
  const normalizedPath = ensureLeadingSlash(path)
  if (normalizedPath.startsWith('/api/')) {
    return `${resolveStreamOrigins(apiBase).wsOrigin}${normalizedPath}`
  }

  return `${resolveWsBase(apiBase)}${normalizedPath}`
}

export function buildTaskStreamUrl(apiBase: string, taskId: string): string {
  return resolveSseUrl(apiBase, `/task/${taskId}/stream`)
}

export interface ReconnectingTransportOptions {
  maxReconnectAttempts?: number
  reconnectBaseDelay?: number
  maxReconnectDelay?: number
  withCredentials?: boolean
  onReconnect?: (attempt: number, delayMs: number) => void
  onExhausted?: () => void
  onInstance?: (instance: EventSource | WebSocket) => void
}

export interface ReconnectingTransportHandle {
  close: () => void
}

export function createReconnectingEventSource(
  url: string,
  options: ReconnectingTransportOptions = {},
): ReconnectingTransportHandle & { get current(): EventSource | null } {
  const backoff = createReconnectBackoff({
    baseDelay: options.reconnectBaseDelay,
    maxAttempts: options.maxReconnectAttempts,
    maxDelay: options.maxReconnectDelay,
  })

  let closed = false
  let es: EventSource | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const connect = () => {
    if (closed) return
    es?.close()
    es = new EventSource(
      url,
      options.withCredentials ? { withCredentials: true } : undefined,
    )
    options.onInstance?.(es)

    es.onopen = () => {
      backoff.reset()
    }

    es.onerror = () => {
      if (closed) return
      es?.close()
      es = null

      if (backoff.canRetry()) {
        const delay = backoff.nextDelay()
        options.onReconnect?.(backoff.attempts, delay)
        reconnectTimer = setTimeout(connect, delay)
        return
      }

      options.onExhausted?.()
    }
  }

  connect()

  return {
    get current() {
      return es
    },
    close() {
      closed = true
      clearReconnectTimer()
      es?.close()
      es = null
    },
  }
}

export function createReconnectingWebSocket(
  url: string,
  options: ReconnectingTransportOptions = {},
): ReconnectingTransportHandle & { get current(): WebSocket | null } {
  const backoff = createReconnectBackoff({
    baseDelay: options.reconnectBaseDelay,
    maxAttempts: options.maxReconnectAttempts,
    maxDelay: options.maxReconnectDelay,
  })

  let closed = false
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const connect = () => {
    if (closed) return
    ws?.close()
    ws = new WebSocket(url)
    options.onInstance?.(ws)

    ws.onopen = () => {
      backoff.reset()
    }

    ws.onclose = () => {
      if (closed) return
      ws = null

      if (backoff.canRetry()) {
        const delay = backoff.nextDelay()
        options.onReconnect?.(backoff.attempts, delay)
        reconnectTimer = setTimeout(connect, delay)
        return
      }

      options.onExhausted?.()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  connect()

  return {
    get current() {
      return ws
    },
    close() {
      closed = true
      clearReconnectTimer()
      ws?.close()
      ws = null
    },
  }
}
