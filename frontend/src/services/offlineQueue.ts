const STORAGE_KEY = 'offline-queue'

export interface QueuedAction {
  id: string
  url: string
  method: string
  headers?: Record<string, string>
  body?: string
  timestamp: number
  retryCount: number
  maxRetries: number
  label?: string
}

type Listener = () => void

let queue: QueuedAction[] = []
let listeners: Set<Listener> = new Set()
let autoReplayEnabled = true

function load(): QueuedAction[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function persist(): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queue))
}

function notify(): void {
  listeners.forEach((fn) => fn())
}

function addUniqueId(): string {
  return Math.random().toString(36).substring(2, 11)
}

export function getQueue(): QueuedAction[] {
  return queue
}

export function enqueue(action: Omit<QueuedAction, 'id' | 'timestamp' | 'retryCount'>): QueuedAction {
  const item: QueuedAction = {
    ...action,
    id: addUniqueId(),
    timestamp: Date.now(),
    retryCount: 0,
  }
  queue.push(item)
  persist()
  notify()
  return item
}

export function remove(id: string): void {
  queue = queue.filter((a) => a.id !== id)
  persist()
  notify()
}

export function clear(): void {
  queue = []
  persist()
  notify()
}

type ReplayResult = 'ok' | 'gone' | 'fail'

export function retry(id: string): Promise<boolean> {
  const idx = queue.findIndex((a) => a.id === id)
  if (idx === -1) return Promise.resolve(false)
  const action = queue[idx]
  return replayAction(action).then((result) => {
    if (result === 'ok') {
      remove(id)
      return true
    }
    if (result === 'gone' || action.retryCount >= action.maxRetries) {
      remove(id)
      return false
    }
    queue[idx] = { ...action, retryCount: action.retryCount + 1 }
    persist()
    notify()
    return false
  })
}

export async function retryAll(): Promise<number> {
  const ids = [...queue.map((a) => a.id)]
  let success = 0
  for (const id of ids) {
    const ok = await retry(id).catch(() => false)
    if (ok) success++
  }
  return success
}

export function isRetryable(method: string): boolean {
  return ['POST', 'PATCH', 'PUT', 'DELETE'].includes(method.toUpperCase())
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn)
  return () => {
    listeners.delete(fn)
  }
}

export function setAutoReplay(enabled: boolean): void {
  autoReplayEnabled = enabled
}

export function isOnline(): boolean {
  return typeof navigator !== 'undefined' ? navigator.onLine : true
}

function replayAction(action: QueuedAction): Promise<ReplayResult> {
  const { url, method, headers, body } = action
  return fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...headers },
    body,
  })
    .then((res) => {
      if (res.ok) return 'ok' as const
      if (res.status === 404 || res.status === 410) return 'gone' as const
      return 'fail' as const
    })
    .catch(() => 'fail' as const)
}

function onReconnect(): void {
  if (autoReplayEnabled && getQueue().length > 0) {
    retryAll()
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('online', onReconnect)
}

queue = load()
