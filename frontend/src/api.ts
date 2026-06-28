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

export interface ExecutionContext {
  target_policy_id?: string | null
  scan_profile: string
  credential_profile_id?: string | null
  session_profile_id?: string | null
  validation_mode: 'detect_only' | 'proof' | 'controlled_extract'
  evidence_level: 'minimal' | 'standard' | 'full'
}

export interface EvidenceRecord {
  type: string
  label?: string
  value?: unknown
  artifact_ref?: string | null
  source?: string
  observed_at?: string
  confidence?: number
}

export interface FindingRecord {
  [key: string]: unknown
  id?: string
  task_id?: string
  plugin_id?: string
  severity: string
  category: string
  title: string
  target: string
  description?: string
  remediation?: string
  discovered_at?: string
  cvss?: number
  cve?: string
  cpe?: string
  risk_score?: number
  risk_factors?: Array<Record<string, unknown>>
  exploitability?: number
  confidence?: number
  validated?: boolean
  validation_method?: string
  confidence_reason?: string
  evidence?: EvidenceRecord[]
  asset_refs?: string[]
  asset_id?: string
  finding_group_id?: string
  finding_kind?: 'observation' | 'suspected_issue' | 'validated_issue'
  occurrence_count?: number
  corroborating_sources?: string[]
  evidence_count?: number
  analyst_status?: string
  retest_status?: string
  service_fingerprint?: string
  references?: Array<Record<string, unknown>>
  asset_exposure?: string
  first_seen_at?: string
  last_seen_at?: string
  metadata?: Record<string, unknown>
}

export interface FindingGroup {
  id: string
  title: string
  severity: string
  category?: string
  target?: string
  asset_id?: string
  finding_kind?: string
  validated?: boolean
  cve?: string
  cpe?: string
  confidence?: number
  confidence_reason?: string
  first_seen_at?: string
  last_seen_at?: string
  occurrence_count?: number
  evidence_count?: number
  corroborating_sources?: string[]
  analyst_status?: string
  retest_status?: string
  latest_finding_id?: string
  findings?: FindingRecord[]
}

export interface AssetServiceRecord {
  id?: string
  asset_id?: string
  target?: string
  host: string
  ip?: string | null
  port?: number | null
  protocol?: string | null
  service?: string | null
  product?: string | null
  version?: string | null
  cpe?: string | null
  confidence?: number | null
  title?: string | null
  banner?: string | null
  cert_subject?: string | null
  cert_san?: string[]
  cert_expiry?: string | null
  service_fingerprint?: string | null
  metadata?: Record<string, unknown>
}

export interface AssetSummaryEntry {
  asset_id: string
  label?: string
  target?: string
  services?: AssetServiceRecord[]
  finding_count?: number
  validated_count?: number
  highest_severity?: string
}

export interface ScanDiff {
  new: FindingGroup[]
  resolved: FindingGroup[]
  changed: Array<{
    group_id: string
    before: FindingRecord
    after: FindingRecord
  }>
  summary: {
    new_count: number
    resolved_count: number
    changed_count: number
  }
}

export interface FindingsResponse {
  findings?: FindingRecord[]
  finding_groups?: FindingGroup[]
  total?: number
  page?: number
  per_page?: number
}

export interface TaskResultResponse {
  task_id: string
  plugin_id: string
  tool: string
  target: string
  timestamp: string
  duration_seconds?: number
  status: string
  execution_context?: ExecutionContext
  summary?: string[]
  severity_counts?: Record<string, number>
  findings?: FindingRecord[]
  finding_groups?: FindingGroup[]
  asset_summary?: AssetSummaryEntry[]
  scan_diff?: ScanDiff
  structured?: Record<string, unknown>
  raw_output_path?: string
  raw_output_excerpt?: string
  raw_output?: string
  command_used?: string
  errors?: Array<{ message: string }>
  error_message?: string
  exit_code?: number
  metadata?: Record<string, unknown>
}

export interface NamedResourceList<T> {
  items: T[]
  total: number
}

export interface TargetPolicy {
  id: string
  name: string
  description?: string | null
  allow_public_targets: boolean
  allow_exploit_validation: boolean
  allow_authenticated_scan: boolean
  default_validation_mode: string
  allowed_targets?: string[]
  metadata?: Record<string, unknown>
}

export interface CredentialProfile {
  id: string
  name: string
  username_secret_name?: string | null
  password_secret_name?: string | null
  extra_headers?: Record<string, unknown>
  login_recipe?: Record<string, unknown>
}

export interface SessionProfile {
  id: string
  name: string
  cookie_secret_name?: string | null
  extra_headers?: Record<string, unknown>
  notes?: string | null
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
  capabilities?: string[]
  implementation_status?: 'native' | 'integrated' | 'placeholder'
  supports_authenticated_crawling?: boolean
  supports_session_reuse?: boolean
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
  implementation_status?: 'native' | 'integrated' | 'placeholder'
  supports_authenticated_crawling?: boolean
  supports_session_reuse?: boolean
}

export interface TaskStartResponse {
  task_id: string
  status: string
  created_at: string
  stream_url: string
}

let _apiKey: string | null = null

export function getStoredApiKey(): string | null {
  return _apiKey
}

export function setStoredApiKey(key: string): void {
  _apiKey = key
}

export function clearStoredApiKey(): void {
  _apiKey = null
}

export async function authenticateWithApiKey(apiKey: string): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/session`, {
    method: 'POST',
    headers: { 'X-Api-Key': apiKey },
    credentials: 'include',
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body?.detail || 'Authentication failed')
  }
  _apiKey = apiKey
}

export async function checkAuthSession(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/auth/session/check`, {
      credentials: 'include',
    })
    const data = await response.json()
    return !!data.authenticated
  } catch {
    return false
  }
}

export async function logoutSession(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/session/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } catch {
    // ignore
  }
  _apiKey = null
}

function getApiKey(): string | null {
  return _apiKey
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
      credentials: 'include',
      signal: controller.signal,
    })

    if (response.status === 401) {
      _apiKey = null
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


export function getFindings(page: number = 1, perPage: number = 50) {
  return request<FindingsResponse>(`/findings?page=${page}&per_page=${perPage}`)
}

export function getFindingGroups(page: number = 1, perPage: number = 50) {
  return request<{ groups: FindingGroup[]; total: number; page: number; per_page: number }>(`/finding-groups?page=${page}&per_page=${perPage}`)
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
  return request<TaskResultResponse>(`/task/${taskId}/result`)
}

export function getTaskDiff(taskId: string): Promise<ScanDiff> {
  return request<ScanDiff>(`/task/${taskId}/diff`)
}

export function startTask(
  plugin_id: string,
  inputs: Record<string, unknown>,
  consent_granted: boolean,
  preset?: string,
  execution_context?: Partial<ExecutionContext>,
) {
  return request<TaskStartResponse>('/task/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plugin_id,
      inputs,
      consent_granted,
      preset,
      execution_context: {
        scan_profile: 'standard',
        validation_mode: 'proof',
        evidence_level: 'standard',
        ...execution_context,
      },
    }),
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
  preset?: string
  execution_context?: ExecutionContext
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

export interface WorkflowRun {
  id: string
  workflow_id: string
  version_id: string | null
  version_number: number | null
  triggered_by: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  task_ids: string[]
  started_at: string
  completed_at: string | null
  error_message: string | null
}

export interface WorkflowVersion {
  id: string
  workflow_id: string
  version_number: number
  definition: {
    name: string
    schedule_seconds: number | null
    enabled: boolean
    steps: WorkflowStep[]
  }
  created_at: string
  created_by: string
}

export function getWorkflowRuns(workflowId: string, limit = 50, offset = 0): Promise<{ total: number; runs: WorkflowRun[] }> {
  return request<{ total: number; runs: WorkflowRun[] }>(`/workflows/${workflowId}/runs?limit=${limit}&offset=${offset}`)
}

export function getWorkflowVersions(workflowId: string): Promise<{ workflow_id: string; versions: WorkflowVersion[]; total: number }> {
  return request<{ workflow_id: string; versions: WorkflowVersion[]; total: number }>(`/workflows/${workflowId}/versions`)
}

export async function rollbackWorkflow(workflowId: string, versionNumber: number): Promise<{
  workflow_id: string
  rolled_back_to_version: number
  new_version_number: number
  workflow: Workflow
}> {
  const res = await request<{
    workflow_id: string
    rolled_back_to_version: number
    new_version_number: number
    workflow: any
  }>(`/workflows/${workflowId}/rollback/${versionNumber}`, {
    method: 'POST',
  })
  return {
    ...res,
    workflow: normalizeWorkflow(res.workflow),
  }
}

export function listTargetPolicies() {
  return request<NamedResourceList<TargetPolicy>>('/target-policies')
}

export function createTargetPolicy(payload: Partial<TargetPolicy>) {
  return request<TargetPolicy>('/target-policies', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function listCredentialProfiles() {
  return request<NamedResourceList<CredentialProfile>>('/credential-profiles')
}

export function listSessionProfiles() {
  return request<NamedResourceList<SessionProfile>>('/session-profiles')
}

export function getCrawlRuns() {
  return request('/crawl-runs')
}

export function getAssetServices() {
  return request('/assets/services')
}

export function getKnowledgebaseStatus() {
  return request('/knowledgebase/status')
}
