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

export interface HealthResponse {
  status: string
  version: string
  uptime_seconds?: number
  system: Record<string, unknown>
  limits?: Record<string, number>
}

export interface TaskResponse {
  task_id: string
  plugin_id: string
  tool: string
  target: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  duration_seconds?: number | null
  inputs?: Record<string, unknown> | null
  preset?: string | null
  error_message?: string | null
  exit_code?: number | null
}

export interface TaskStatusResponse extends TaskResponse {
  queue_position?: number | null
  pending_count?: number | null
}

export interface TaskPagination {
  page: number
  per_page: number
  total_pages: number
  total_items: number
  next?: string | null
  previous?: string | null
}

export interface TasksResponse {
  tasks: TaskResponse[]
  pagination?: TaskPagination | null
}

export interface Finding {
  id?: string | null
  title: string
  category: string
  severity: string
  target?: string | null
  description: string
  remediation?: string | null
  cvss?: number | null
  cve?: string | null
  proof?: string | null
  discovered_at?: string | null
  metadata?: Record<string, unknown>
  metadata_json?: Record<string, unknown> | null
}

export interface TaskResult {
  task_id: string
  plugin_id: string
  tool: string
  target: string
  timestamp: string
  duration_seconds?: number | null
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  summary?: string[]
  severity_counts?: Record<string, number>
  findings?: Finding[]
  structured?: Record<string, unknown>
  raw_output_path?: string | null
  raw_output_excerpt?: string | null
  errors?: Record<string, unknown>[]
  error_message?: string | null
  exit_code?: number | null
  metadata?: Record<string, unknown>
}

export interface ScanActivity {
  total: number
  completed: number
  running: number
}

export interface DashboardTask {
  id: string
  plugin_id: string
  tool_name: string
  target: string
  status: string
  created_at: string
  duration_seconds?: number | null
}

export interface DashboardSummaryResponse {
  total_findings: number
  critical_findings: number
  high_findings: number
  medium_findings: number
  low_findings: number
  info_findings: number
  last_scan_time?: string | null
  recent_findings: Finding[]
  scan_activity: ScanActivity
  running_tasks: DashboardTask[]
  recent_tasks: DashboardTask[]
}

export interface FindingsResponse {
  findings: Finding[]
}

export interface FindingAssetRef {
  id: string
  name: string
  type: string
}

export interface FindingDetailsResponse {
  id: string
  task_id?: string | null
  plugin_id: string
  tool: string
  title: string
  category: string
  severity: string
  target: string
  description: string
  remediation?: string | null
  cvss?: number | null
  cve?: string | null
  proof?: string | null
  discovered_at: string
  metadata?: Record<string, unknown>
  assets: FindingAssetRef[]
}

export interface ReportItem {
  id: string
  task_id?: string | null
  name: string
  type: string
  generated_at: string
  status: string
  findings: number
  pages: number
  file_path?: string | null
}

export interface ReportsResponse {
  reports: ReportItem[]
}

export interface AssetResponseItem {
  id: string
  type: string
  name: string
  host_id?: string | null
  host_name?: string | null
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
  findings_count: number
  tasks_count: number
  reports_count: number
}

export interface AssetsResponse {
  assets: AssetResponseItem[]
}

export interface GraphNode {
  id: string
  type: string
  label: string
  details?: Record<string, unknown>
}

export interface GraphLink {
  source: string
  target: string
  type: string
}

export interface GraphResponse {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface AssetDetailsResponse {
  id: string
  type: string
  name: string
  host_id?: string | null
  host_name?: string | null
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
  findings: Record<string, unknown>[]
  tasks: Record<string, unknown>[]
  reports: Record<string, unknown>[]
}

export interface WorkflowsResponse {
  workflows: Workflow[]
  total: number
}

export interface TaskCancelResponse {
  task_id: string
  status: string
  cancelled_at: string
}

export interface WorkflowRunResponse {
  workflow_id: string
  queued_tasks: string[]
}

export interface WorkflowDeleteResponse {
  workflow_id: string
  deleted: boolean
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

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

export function listPlugins(): Promise<PluginListResponse> {
  return request<PluginListResponse>('/plugins')
}

export function getPluginSchema(id: string): Promise<PluginSchemaResponse> {
  return request<PluginSchemaResponse>(`/plugin/${id}/schema`)
}

export function getDashboardSummary(): Promise<DashboardSummaryResponse> {
  return request<DashboardSummaryResponse>('/dashboard/summary')
}

export function getFindings(): Promise<FindingsResponse> {
  return request<FindingsResponse>('/findings')
}

export function getReports(): Promise<ReportsResponse> {
  return request<ReportsResponse>('/reports')
}

export function getAssets(): Promise<AssetsResponse> {
  return request<AssetsResponse>('/assets')
}

export function getAssetsGraph(): Promise<GraphResponse> {
  return request<GraphResponse>('/assets/graph')
}

export function getAssetDetails(assetId: string): Promise<AssetDetailsResponse> {
  return request<AssetDetailsResponse>(`/asset/${assetId}`)
}

export function getFindingDetails(findingId: string): Promise<FindingDetailsResponse> {
  return request<FindingDetailsResponse>(`/finding/${findingId}`)
}

export function getTasks(params?: URLSearchParams): Promise<TasksResponse> {
  const suffix = params ? `?${params.toString()}` : ''
  return request<TasksResponse>(`/tasks${suffix}`)
}

export function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return request<TaskStatusResponse>(`/task/${taskId}/status`)
}

export function getTaskResult(taskId: string): Promise<TaskResult> {
  return request<TaskResult>(`/task/${taskId}/result`)
}

export function startTask(
  plugin_id: string,
  inputs: Record<string, unknown>,
  consent_granted: boolean,
  preset?: string
): Promise<TaskStartResponse> {
  return request<TaskStartResponse>('/task/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plugin_id, inputs, consent_granted, preset }),
  })
}

export function deleteTask(taskId: string): Promise<{ task_id: string; deleted: boolean }> {
  return request<{ task_id: string; deleted: boolean }>(`/task/${taskId}`, {
    method: 'DELETE',
  })
}

export function bulkDeleteTasks(taskIds: string[]): Promise<{ deleted_count: number; success: boolean }> {
  return request<{ deleted_count: number; success: boolean }>('/tasks/bulk', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(taskIds),
  })
}

export function clearAllTasks(): Promise<{ cleared: boolean; message: string }> {
  return request<{ cleared: boolean; message: string }>('/tasks/clear', {
    method: 'DELETE',
  })
}

export function cancelTask(taskId: string): Promise<TaskCancelResponse> {
  return request<TaskCancelResponse>(`/task/${taskId}/cancel`, {
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
  schedule_interval: string
  enabled: boolean
  steps: WorkflowStep[]
  last_run_at?: string | null
  queued_task_ids?: string[]
  created_at?: string
}

export interface WorkflowCreatePayload {
  name: string
  schedule_interval: string
  enabled: boolean
  steps: WorkflowStep[]
}

export interface WorkflowUpdatePayload {
  name?: string
  schedule_interval?: string
  enabled?: boolean
  steps?: WorkflowStep[]
}

export function getWorkflows(): Promise<Workflow[]> {
  return request<WorkflowsResponse>('/workflows').then(r => r.workflows)
}

export function createWorkflow(data: WorkflowCreatePayload): Promise<Workflow> {
  return request<Workflow>('/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function runWorkflow(workflowId: string): Promise<{ queued_task_ids: string[] }> {
  return request<WorkflowRunResponse>(`/workflows/${workflowId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  }).then(r => ({ queued_task_ids: r.queued_tasks }))
}

export function updateWorkflow(workflowId: string, data: WorkflowUpdatePayload): Promise<Workflow> {
  return request<Workflow>(`/workflows/${workflowId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function deleteWorkflow(workflowId: string): Promise<WorkflowDeleteResponse> {
  return request<WorkflowDeleteResponse>(`/workflows/${workflowId}`, {
    method: 'DELETE',
  })
}