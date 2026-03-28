function resolveApiBase(): string {
  const configured = (import.meta as any).env.VITE_API_BASE
  if (configured) return configured

  if (typeof window !== 'undefined') {
    const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const isViteDevServer = window.location.port === '5173'

    // For localhost preview/static modes (e.g. :8080), call backend directly.
    if (isLocalHost && !isViteDevServer) return 'http://127.0.0.1:8000/api/v1'
  }

  // Default for Vite dev server where /api is proxied to backend.
  return '/api/v1'
}

export const API_BASE = resolveApiBase()

export type PluginFieldType =
  | 'string'
  | 'text'
  | 'integer'
  | 'boolean'
  | 'select'
  | 'multiselect'
  | 'file'
  | 'keyvalue'

export interface PluginFieldOption {
  value: string
  label: string
}

export interface PluginFieldSchema {
  id: string
  label: string
  type: PluginFieldType
  required?: boolean
  default?: unknown
  placeholder?: string
  help?: string
  options?: PluginFieldOption[]
  validation?: Record<string, unknown>
}

export interface PluginAvailability {
  runnable: boolean
  missing_binaries: string[]
}

export interface PluginListItem {
  id: string
  name: string
  description: string
  category: string
  safety_level: string
  enabled: boolean
  icon: string
  requires_consent: boolean
  consent_message?: string | null
  availability: PluginAvailability
}

export interface PluginListResponse {
  plugins: PluginListItem[]
  total: number
}

export interface PluginSchemaResponse {
  id: string
  name: string
  description: string
  fields: PluginFieldSchema[]
  presets: Record<string, Record<string, unknown>>
  safety: Record<string, unknown>
}

export interface TaskStartResponse {
  task_id: string
  status: string
  created_at: string
  stream_url: string
}

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
  return request<PluginListResponse>('/plugins')
}

export function getPluginSchema(id: string) {
  return request<PluginSchemaResponse>(`/plugin/${id}/schema`)
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
  return request<TaskStartResponse>('/task/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plugin_id, inputs, consent_granted, preset }),
  })
}

export function cancelTask(taskId: string) {
  return request(`/task/${taskId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
}

export function streamTask(taskId: string, onEvent: (ev: MessageEvent) => void) {
  const url = `${API_BASE}/task/${taskId}/stream`
  const es = new EventSource(url)
  es.onmessage = onEvent
  es.onerror = () => {}
  return es
}
