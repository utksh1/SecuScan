"""
Pydantic models for API requests and responses
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SafetyLevel(str, Enum):
    """Plugin safety level classification"""
    SAFE = "safe"
    INTRUSIVE = "intrusive"
    EXPLOIT = "exploit"


class TaskStatus(str, Enum):
    """Task execution status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PluginFieldType(str, Enum):
    """Plugin field input types"""
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    FILE = "file"
    KEYVALUE = "keyvalue"


class PluginField(BaseModel):
    """Plugin input field definition"""
    id: str
    label: str
    type: PluginFieldType
    required: bool = False
    default: Optional[Any] = None
    placeholder: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    help: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None


class PluginMetadata(BaseModel):
    """Plugin metadata schema"""
    id: str
    name: str
    version: str
    description: str
    long_description: Optional[str] = None
    category: str
    author: Optional[Dict[str, str]] = None
    license: Optional[str] = "MIT"
    icon: Optional[str] = "🔧"
    
    engine: Dict[str, str]
    command_template: List[str]
    fields: List[PluginField]
    presets: Dict[str, Dict[str, Any]]
    
    output: Dict[str, Any]
    safety: Dict[str, Any]
    learning: Optional[Dict[str, Any]] = None
    dependencies: Optional[Dict[str, List[str]]] = None
    docker_image: Optional[str] = None

    checksum: Optional[str] = None
    signature: Optional[str] = None


class TaskCreateRequest(BaseModel):
    """Request to create a new task"""
    plugin_id: str
    preset: Optional[str] = None
    inputs: Dict[str, Any]
    consent_granted: bool = False


class TaskResponse(BaseModel):
    """Task information response"""
    task_id: str
    plugin_id: str
    tool: str
    target: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    inputs: Optional[Dict[str, Any]] = None
    preset: Optional[str] = None
    error_message: Optional[str] = None
    exit_code: Optional[int] = None


class TaskStatusResponse(TaskResponse):
    """Task status query response containing optional queue information"""
    queue_position: Optional[int] = None
    pending_count: Optional[int] = None


class Finding(BaseModel):
    """Structured security finding"""
    id: Optional[str] = None
    title: str
    category: str
    severity: str
    target: str
    description: str
    remediation: Optional[str] = ""
    cvss: Optional[float] = None
    cve: Optional[str] = None
    proof: Optional[str] = None
    discovered_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Task execution result"""
    task_id: str
    plugin_id: str
    tool: str
    target: str
    timestamp: datetime
    duration_seconds: Optional[float] = None
    status: TaskStatus
    
    summary: List[str] = []
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    findings: List[Finding] = Field(default_factory=list)
    structured: Dict[str, Any] = Field(default_factory=dict)
    raw_output_path: Optional[str] = None
    raw_output_excerpt: Optional[str] = None
    
    errors: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
    exit_code: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    uptime_seconds: Optional[int] = None
    system: Dict[str, Any]
    limits: Optional[Dict[str, int]] = None


class PluginListResponse(BaseModel):
    """List of available plugins"""
    plugins: List[Dict[str, Any]]
    total: int


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TaskStartResponse(BaseModel):
    """Response when a task starts successfully"""
    task_id: str
    status: str
    created_at: str
    stream_url: str


class TaskPagination(BaseModel):
    """Pagination details for task list"""
    page: int
    per_page: int
    total_pages: int
    total_items: int
    next: Optional[str] = None
    previous: Optional[str] = None


class TasksResponse(BaseModel):
    """List of tasks response"""
    tasks: List[TaskResponse]
    pagination: Optional[TaskPagination] = None


class FindingAssetRef(BaseModel):
    """Asset details nested inside finding details"""
    id: str
    name: str
    type: str


class FindingDetailsResponse(BaseModel):
    """Detailed finding response including associated assets"""
    id: str
    task_id: Optional[str] = None
    plugin_id: str
    tool: str
    title: str
    category: str
    severity: str
    target: str
    description: str
    remediation: Optional[str] = ""
    cvss: Optional[float] = None
    cve: Optional[str] = None
    proof: Optional[str] = None
    discovered_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    assets: List[FindingAssetRef]


class FindingsResponse(BaseModel):
    """List of findings response"""
    findings: List[Finding]


class ReportItem(BaseModel):
    """Single report item"""
    id: str
    task_id: Optional[str] = None
    name: str
    type: str
    generated_at: str
    status: str
    findings: int
    pages: int
    file_path: Optional[str] = None


class ReportsResponse(BaseModel):
    """List of reports response"""
    reports: List[ReportItem]


class AssetResponseItem(BaseModel):
    """Single asset item in assets list"""
    id: str
    type: str
    name: str
    host_id: Optional[str] = None
    host_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    findings_count: int
    tasks_count: int
    reports_count: int


class AssetsResponse(BaseModel):
    """List of assets response"""
    assets: List[AssetResponseItem]


class GraphNode(BaseModel):
    """Topology graph node"""
    id: str
    type: str
    label: str
    details: Dict[str, Any] = Field(default_factory=dict)


class GraphLink(BaseModel):
    """Topology graph link"""
    source: str
    target: str
    type: str


class GraphResponse(BaseModel):
    """Topology graph response"""
    nodes: List[GraphNode]
    links: List[GraphLink]


class AssetDetailsResponse(BaseModel):
    """Detailed asset view with linked resources"""
    id: str
    type: str
    name: str
    host_id: Optional[str] = None
    host_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    findings: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    reports: List[Dict[str, Any]]


class WorkflowStep(BaseModel):
    """Single step in a workflow"""
    plugin_id: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    preset: Optional[str] = None


class Workflow(BaseModel):
    """Workflow model with frontend-aligned schedule_interval"""
    id: str
    name: str
    schedule_interval: str
    enabled: bool
    steps: List[WorkflowStep]
    created_at: Optional[str] = None
    last_run_at: Optional[str] = None


class WorkflowsResponse(BaseModel):
    """List of workflows response"""
    workflows: List[Workflow]
    total: int


class WorkflowCreateResponse(BaseModel):
    """Workflow creation response containing the full created object"""
    id: str
    name: str
    schedule_interval: str
    enabled: bool
    steps: List[WorkflowStep]
    created_at: Optional[str] = None
    last_run_at: Optional[str] = None


class WorkflowRunResponse(BaseModel):
    """Workflow execution trigger response"""
    workflow_id: str
    queued_tasks: List[str]


class WorkflowUpdateResponse(BaseModel):
    """Workflow update response containing the full updated object"""
    id: str
    name: str
    schedule_interval: str
    enabled: bool
    steps: List[WorkflowStep]
    created_at: Optional[str] = None
    last_run_at: Optional[str] = None


class WorkflowDeleteResponse(BaseModel):
    """Workflow deletion response"""
    workflow_id: str
    deleted: bool


class ScanActivity(BaseModel):
    """Scan activity statistics for dashboard"""
    total: int
    completed: int
    running: int


class DashboardTask(BaseModel):
    """Task metadata returned in dashboard summary"""
    id: str
    plugin_id: str
    tool_name: str
    target: str
    status: str
    created_at: str
    duration_seconds: Optional[float] = None


class DashboardSummaryResponse(BaseModel):
    """Dashboard statistics summary response"""
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    info_findings: int
    last_scan_time: Optional[str] = None
    recent_findings: List[Finding]
    scan_activity: ScanActivity
    running_tasks: List[DashboardTask]
    recent_tasks: List[DashboardTask]


class PluginSchemaResponse(BaseModel):
    """Schema definition for plugin parameters"""
    id: str
    name: str
    description: str
    fields: List[PluginField]
    presets: Dict[str, Dict[str, Any]]
    safety: Dict[str, Any]
