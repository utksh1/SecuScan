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
  status?: string
  guidance?: string | null
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

const API_KEY_STORAGE_KEY = 'secuscan_api_key'

export function getStoredApiKey(): string | null {
  try {
    return localStorage.getItem(API_KEY_STORAGE_KEY) || null
  } catch {
    return null
  }
}

export function setStoredApiKey(key: string): void {
  try {
    localStorage.setItem(API_KEY_STORAGE_KEY, key)
  } catch {
    // ignore storage errors
  }
}

function getApiKey(): string | null {
  return getStoredApiKey()
}

/** Fired on the window when any API request receives HTTP 401. */
export const AUTH_REQUIRED_EVENT = 'secuscan:auth-required'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 10000)

  const apiKey = getApiKey()
  const authHeaders: Record<string, string> = apiKey ? { 'X-Api-Key': apiKey } : {}

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        ...authHeaders,
        ...(init?.headers as Record<string, string> | undefined),
      },
      signal: controller.signal,
    })

    if (response.status === 401) {
      // Notify the app so it can show the API-key setup UI without every
      // caller needing to handle auth independently.
      window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT))
      throw new Error('AUTH_REQUIRED')
    }

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`)
    }
    return response.json()
  } finally {
    window.clearTimeout(timeoutId)
  }
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

export function getSettings() {
  return request<any>(`/settings`)
}

export function getDashboardSummary() {
  return request('/dashboard/summary')
}


export function getFindings() {
  return request('/findings')
}


export function getReports() {
  return request('/reports')
}

export type NotificationChannelType = 'webhook' | 'email'
export type NotificationSeverityThreshold = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface NotificationRule {
  id: string
  name: string
  severity_threshold: NotificationSeverityThreshold | string
  channel_type: NotificationChannelType | string
  target_url_or_email: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NotificationHistoryRow {
  id: string
  rule_id: string
  finding_id: string
  status: 'success' | 'failed' | string
  error_message?: string | null
  sent_at: string
}

export interface NotificationRuleCreatePayload {
  name: string
  severity_threshold: NotificationSeverityThreshold
  channel_type: NotificationChannelType
  target_url_or_email: string
  is_active: boolean
}

export interface NotificationRuleUpdatePayload {
  name?: string
  severity_threshold?: NotificationSeverityThreshold
  channel_type?: NotificationChannelType
  target_url_or_email?: string
  is_active?: boolean
}

export async function listNotificationRules(): Promise<NotificationRule[]> {
  const data: any = await request('/notifications/rules')
  const rules = Array.isArray(data) ? data : data?.rules
  return Array.isArray(rules) ? (rules as NotificationRule[]) : []
}

export async function createNotificationRule(payload: NotificationRuleCreatePayload): Promise<NotificationRule> {
  return request<NotificationRule>('/notifications/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function updateNotificationRule(ruleId: string, payload: NotificationRuleUpdatePayload): Promise<NotificationRule> {
  return request<NotificationRule>(`/notifications/rules/${ruleId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteNotificationRule(ruleId: string): Promise<{ rule_id: string; deleted: boolean }> {
  return request<{ rule_id: string; deleted: boolean }>(`/notifications/rules/${ruleId}`, {
    method: 'DELETE',
  })
}

export async function listNotificationHistory(params?: {
  rule_id?: string
  limit?: number
  offset?: number
}): Promise<{ history: NotificationHistoryRow[]; total: number; limit: number; offset: number }> {
  const sp = new URLSearchParams()
  if (params?.rule_id) sp.set('rule_id', params.rule_id)
  if (typeof params?.limit === 'number') sp.set('limit', String(params.limit))
  if (typeof params?.offset === 'number') sp.set('offset', String(params.offset))
  const suffix = sp.toString() ? `?${sp.toString()}` : ''
  const data: any = await request(`/notifications/history${suffix}`)
  return {
    history: Array.isArray(data?.history) ? (data.history as NotificationHistoryRow[]) : [],
    total: Number(data?.total ?? 0),
    limit: Number(data?.limit ?? (params?.limit ?? 50)),
    offset: Number(data?.offset ?? (params?.offset ?? 0)),
  }
}

export function getTasks(params?: URLSearchParams) {
  const suffix = params ? `?${params.toString()}` : ''
  return request(`/tasks${suffix}`)
}

export type ScanPhase = 'queued' | 'running_command' | 'parsing' | 'reporting' | 'finished'

export function getTaskStatus(taskId: string): Promise<any> {
  return request<any>(`/task/${taskId}/status`)
}

export function getTaskResult(taskId: string): Promise<any> {
  return request<any>(`/task/${taskId}/result`)
}

export function startTask(plugin_id: string, inputs: Record<string, unknown>, consent_granted: boolean, preset?: string) {
  return request<TaskStartResponse>('/task/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plugin_id, inputs, consent_granted, preset }),
  })
}

export function deleteTask(taskId: string) {
  return request<{ task_id: string; deleted: boolean }>(`/task/${taskId}`, {
    method: 'DELETE',
  })
}

export function bulkDeleteTasks(taskIds: string[]) {
  return request<{ deleted_count: number; success: boolean }>('/tasks/bulk', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(taskIds),
  })
}

export function clearAllTasks() {
  return request<{ cleared: boolean; message: string }>('/tasks/clear', {
    method: 'DELETE',
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
export interface WorkflowStep {
  plugin_id: string
  inputs: Record<string, unknown>
}

export interface Workflow {
  id: string
  name: string
  schedule_seconds: number | null
  enabled: boolean
  steps: WorkflowStep[]
  last_run_at?: string | null
  queued_task_ids?: string[]
  created_at?: string
}

export interface WorkflowCreatePayload {
  name: string
  schedule_seconds?: number | null
  enabled: boolean
  steps: WorkflowStep[]
}

export interface WorkflowUpdatePayload {
  name?: string
  schedule_seconds?: number | null
  enabled?: boolean
  steps?: WorkflowStep[]
}

interface WorkflowListResponse {
  workflows: unknown[]
  total: number
}

function parseWorkflowSteps(value: unknown): WorkflowStep[] {
  if (Array.isArray(value)) return value as WorkflowStep[]
  if (typeof value !== 'string' || value.trim() === '') return []

  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed as WorkflowStep[] : []
  } catch {
    return []
  }
}

function parseScheduleSeconds(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeWorkflow(raw: any): Workflow {
  return {
    id: String(raw.id),
    name: String(raw.name ?? ''),
    schedule_seconds: parseScheduleSeconds(raw.schedule_seconds),
    enabled: Boolean(raw.enabled),
    steps: parseWorkflowSteps(raw.steps ?? raw.steps_json),
    last_run_at: raw.last_run_at ?? null,
    queued_task_ids: Array.isArray(raw.queued_task_ids)
      ? raw.queued_task_ids
      : Array.isArray(raw.queued_tasks)
        ? raw.queued_tasks
        : [],
    created_at: raw.created_at,
  }
}

export async function getWorkflows(): Promise<Workflow[]> {
  const data = await request<WorkflowListResponse | unknown[]>('/workflows')
  const workflows = Array.isArray(data) ? data : data.workflows
  return Array.isArray(workflows) ? workflows.map(normalizeWorkflow) : []
}

export async function createWorkflow(data: WorkflowCreatePayload): Promise<Workflow> {
  const workflow = await request<unknown>('/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return normalizeWorkflow(workflow)
}

export async function runWorkflow(workflowId: string): Promise<{ queued_task_ids: string[] }> {
  const result: any = await request(`/workflows/${workflowId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return {
    queued_task_ids: Array.isArray(result.queued_task_ids)
      ? result.queued_task_ids
      : Array.isArray(result.queued_tasks)
        ? result.queued_tasks
        : [],
  }
}

export async function updateWorkflow(workflowId: string, data: WorkflowUpdatePayload): Promise<Workflow> {
  const workflow = await request<unknown>(`/workflows/${workflowId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return normalizeWorkflow(workflow)
}

export function deleteWorkflow(workflowId: string): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/workflows/${workflowId}`, {
    method: 'DELETE',
  })
}
