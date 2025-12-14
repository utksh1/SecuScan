export const API_BASE = (import.meta as any).env.VITE_API_BASE || '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 10000)

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    signal: controller.signal,
  })
  window.clearTimeout(timeoutId)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

export function getHealth() {
  return request('/health')
}

export function listPlugins() {
  return request('/plugins')
}

export function getPluginSchema(id: string) {
  return request(`/plugin/${id}/schema`)
}

export function getDashboardSummary() {
  return request('/dashboard/summary')
}

export function getAssets() {
  return request('/assets')
}

export function getFindings() {
  return request('/findings')
}

export function getAttackSurface() {
  return request('/attack-surface')
}

export function getReports() {
  return request('/reports')
}

export function getTasks(params?: URLSearchParams) {
  const suffix = params ? `?${params.toString()}` : ''
  return request(`/tasks${suffix}`)
}

export function getTaskStatus(taskId: string) {
  return request(`/task/${taskId}/status`)
}

export function getTaskResult(taskId: string) {
  return request(`/task/${taskId}/result`)
}

export function startTask(plugin_id: string, inputs: Record<string, unknown>, consent_granted: boolean, preset?: string) {
  return request('/task/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plugin_id, inputs, consent_granted, preset }),
  })
}

export function streamTask(taskId: string, onEvent: (ev: MessageEvent) => void) {
  const url = `${API_BASE}/task/${taskId}/stream`
  const es = new EventSource(url)
  es.onmessage = onEvent
  es.onerror = () => {}
  return es
}
