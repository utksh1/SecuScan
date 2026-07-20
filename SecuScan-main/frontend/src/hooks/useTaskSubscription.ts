import { useEffect, useRef, useState, useCallback } from 'react'
import { API_BASE, getTaskStatus } from '../api'

export interface UseTaskSubscriptionOptions {
  taskId: string
  onStatus?: (status: string) => void
  onPhase?: (phase: string) => void
  onOutput?: (chunk: string) => void
  pollingInterval?: number
  maxReconnectAttempts?: number
  reconnectBaseDelay?: number
}

export interface UseTaskSubscriptionResult {
  isConnected: boolean
  isPolling: boolean
  error: string | null
}

export function useTaskSubscription({
  taskId,
  onStatus,
  onPhase,
  onOutput,
  pollingInterval = 5000,
  maxReconnectAttempts = 5,
  reconnectBaseDelay = 1000,
}: UseTaskSubscriptionOptions): UseTaskSubscriptionResult {
  const [isConnected, setIsConnected] = useState(false)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onStatusRef = useRef(onStatus)
  const onPhaseRef = useRef(onPhase)
  const onOutputRef = useRef(onOutput)
  const esRef = useRef<EventSource | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastStatusRef = useRef<string | null>(null)
  const cleanupRef = useRef(false)
  const versionRef = useRef(0)

  onStatusRef.current = onStatus
  onPhaseRef.current = onPhase
  onOutputRef.current = onOutput

  const cleanupAll = useCallback(() => {
    cleanupRef.current = true
    versionRef.current += 1
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    if (cleanupRef.current) return
    const version = versionRef.current + 1
    versionRef.current = version
    setIsPolling(true)
    setIsConnected(false)

    const poll = async () => {
      if (cleanupRef.current || versionRef.current !== version) return
      try {
        const data = await getTaskStatus(taskId) as { status?: string }
        if (cleanupRef.current || versionRef.current !== version) return
        if (data.status && data.status !== lastStatusRef.current) {
          lastStatusRef.current = data.status
          onStatusRef.current?.(data.status)
        }
        if (data.status && ['completed', 'failed', 'cancelled'].includes(data.status)) {
          cleanupAll()
          setIsPolling(false)
          return
        }
      } catch {
      }
      if (!cleanupRef.current && versionRef.current === version) {
        pollTimerRef.current = setTimeout(poll, pollingInterval)
      }
    }

    poll()
  }, [taskId, pollingInterval, cleanupAll])

  const connectSSE = useCallback(() => {
    if (cleanupRef.current) return
    const version = versionRef.current + 1
    versionRef.current = version
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    const url = `${API_BASE}/task/${taskId}/stream`
    const es = new EventSource(url, { withCredentials: true })
    esRef.current = es

    es.addEventListener('status', (e: MessageEvent) => {
      if (cleanupRef.current || versionRef.current !== version) return
      try {
        const data = JSON.parse(e.data) as { status: string; scan_phase?: string }
        if (data.scan_phase) {
          onPhaseRef.current?.(data.scan_phase)
        }
        if (data.status && data.status !== lastStatusRef.current) {
          lastStatusRef.current = data.status
          onStatusRef.current?.(data.status)
        }
        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          cleanupAll()
          setIsConnected(false)
          setIsPolling(false)
        }
      } catch {
      }
    })

    es.addEventListener('phase', (e: MessageEvent) => {
      if (cleanupRef.current || versionRef.current !== version) return
      try {
        const data = JSON.parse(e.data) as { scan_phase: string }
        if (data.scan_phase) {
          onPhaseRef.current?.(data.scan_phase)
        }
      } catch {
      }
    })

    es.addEventListener('output', (e: MessageEvent) => {
      if (cleanupRef.current || versionRef.current !== version) return
      try {
        const data = JSON.parse(e.data) as { chunk: string }
        if (data.chunk) {
          onOutputRef.current?.(data.chunk)
        }
      } catch {
      }
    })

    es.onerror = () => {
      if (cleanupRef.current || versionRef.current !== version) return
      es.close()
      esRef.current = null
      setIsConnected(false)
      setError('SSE connection lost')

      if (reconnectAttemptRef.current < maxReconnectAttempts) {
        const delay = reconnectBaseDelay * Math.pow(2, reconnectAttemptRef.current)
        reconnectAttemptRef.current++
        reconnectTimerRef.current = setTimeout(() => {
          if (!cleanupRef.current) connectSSE()
        }, delay)
      } else {
        startPolling()
      }
    }

    es.onopen = () => {
      if (cleanupRef.current || versionRef.current !== version) return
      reconnectAttemptRef.current = 0
      setIsConnected(true)
      setIsPolling(false)
      setError(null)
    }
  }, [taskId, maxReconnectAttempts, reconnectBaseDelay, cleanupAll, startPolling])

  useEffect(() => {
    cleanupRef.current = false
    lastStatusRef.current = null
    reconnectAttemptRef.current = 0

    connectSSE()

    return () => {
      cleanupAll()
    }
  }, [taskId, connectSSE, cleanupAll])

  return { isConnected, isPolling, error }
}
