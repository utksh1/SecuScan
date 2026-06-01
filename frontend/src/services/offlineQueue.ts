const STORAGE_KEY = 'offline-queue'
const MAX_QUEUE_SIZE = 50
const ACTION_TTL_MS = 86_400_000 // 24 hours

export const SAFE_ACTION_TYPES: ActionType[] = ['startTask', 'createWorkflow', 'updateWorkflow']

export type ActionType = 'startTask' | 'createWorkflow' | 'updateWorkflow'

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
  actionType?: ActionType
}

type Listener = () => void

let queue: QueuedAction[] = []
let listeners: Set<Listener> = new Set()
let autoReplayEnabled = false
let storageAvailable = true

function load(): QueuedAction[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed: QueuedAction[] = raw ? JSON.parse(raw) : []
    const now = Date.now()
    const fresh = parsed.filter((a) => now - a.timestamp < ACTION_TTL_MS)
    if (fresh.length !== parsed.length) {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(fresh)) } catch {}
    }
    return fresh
  } catch {
    return []
  }
}

function persist(): void {
  if (!storageAvailable) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(queue))
  } catch {
    storageAvailable = false
    // continue with in-memory queue only
  }
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
  if (queue.length >= MAX_QUEUE_SIZE) throw new Error('Queue is full')
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

type ReplayResult = 'ok' | 'gone' | 'fail' | 'conflict'

export function retry(id: string): Promise<boolean> {
  const idx = queue.findIndex((a) => a.id === id)
  if (idx === -1) return Promise.resolve(false)
  const action = queue[idx]
  return replayAction(action).then((result) => {
    if (result === 'ok') {
      remove(id)
      return true
    }
    if (result === 'gone' || result === 'conflict' || action.retryCount >= action.maxRetries) {
      remove(id)
      return false
    }
    queue[idx] = { ...action, retryCount: action.retryCount + 1 }
    persist()
    notify()
    return false
  })
}

function isSafeActionType(actionType?: ActionType): boolean {
  return actionType ? SAFE_ACTION_TYPES.includes(actionType) : false
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

/**
 * Called when the browser comes back online.
 * Does NOT auto-replay unless autoReplayEnabled is explicitly set.
 * Even then, only actions with a safe actionType are replayed.
 */
export function onReconnect(): Promise<number> {
  if (!autoReplayEnabled) return Promise.resolve(0)
  const safeIds = queue.filter((a) => isSafeActionType(a.actionType)).map((a) => a.id)
  if (safeIds.length === 0) return Promise.resolve(0)
  return retryAllFiltered(safeIds)
}

async function retryAllFiltered(ids: string[]): Promise<number> {
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

export function getAutoReplay(): boolean {
  return autoReplayEnabled
}

async function conflictCheck(action: QueuedAction): Promise<'no-conflict' | 'conflict' | 'gone'> {
  if (!action.actionType) return 'no-conflict'

  try {
    switch (action.actionType) {
      case 'updateWorkflow': {
        const res = await fetch(action.url, { method: 'GET' })
        if (res.status === 404 || res.status === 410) return 'gone'
        return 'no-conflict'
      }
      case 'createWorkflow': {
        const listUrl = action.url.replace(/\/workflows(\/.*)?$/, '/workflows')
        const res = await fetch(listUrl, { method: 'GET' })
        if (!res.ok) return 'no-conflict'
        const body = action.body ? JSON.parse(action.body) : null
        if (!body?.name) return 'no-conflict'
        const data = await res.json()
        const workflows = Array.isArray(data) ? data : data.workflows
        const exists = Array.isArray(workflows) && workflows.some((w: any) => w.name === body.name)
        return exists ? 'conflict' : 'no-conflict'
      }
      case 'startTask': {
        const tasksUrl = action.url.replace('/task/start', '/tasks')
        const res = await fetch(tasksUrl, { method: 'GET' })
        if (!res.ok) return 'no-conflict'
        const body = action.body ? JSON.parse(action.body) : null
        if (!body?.plugin_id) return 'no-conflict'
        const data = await res.json()
        const tasks = Array.isArray(data) ? data : data.tasks
        const running = Array.isArray(tasks) && tasks.some((t: any) =>
          t.plugin_id === body.plugin_id && (t.status === 'running' || t.status === 'queued')
        )
        return running ? 'conflict' : 'no-conflict'
      }
      default:
        return 'no-conflict'
    }
  } catch {
    return 'no-conflict'
  }
}

function replayAction(action: QueuedAction): Promise<ReplayResult> {
  if (action.actionType && !isSafeActionType(action.actionType)) {
    return Promise.resolve('gone' as const)
  }
  if (action.actionType) {
    return conflictCheck(action).then((check) => {
      if (check !== 'no-conflict') return check
      return doFetch(action)
    })
  }
  return doFetch(action)
}

function doFetch(action: QueuedAction): Promise<ReplayResult> {
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

queue = load()
