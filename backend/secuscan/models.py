"""
Pydantic models for API requests and responses
"""

from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, RootModel
from enum import Enum


MAX_BULK_DELETE = 500

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


class SandboxConfig(BaseModel):
    """Resource constraints applied to every plugin subprocess execution"""
    timeout_seconds: int = Field(default=120, description="Max wall-clock seconds before SIGTERM")
    max_memory_mb: int = Field(default=512, description="Max virtual memory in MB (RLIMIT_AS on Linux)")
    max_output_bytes: int = Field(default=5_242_880, description="Max bytes captured from stdout/stderr")
    allow_network: bool = Field(default=True, description="Whether subprocess can make network calls")


class SandboxViolation(Exception):
    """Raised when sandbox constraints are violated."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ScanPhase(str, Enum):
    """Granular scan phase for progress display"""
    QUEUED = "queued"
    RUNNING_COMMAND = "running_command"
    PARSING = "parsing"
    REPORTING = "reporting"
    FINISHED = "finished"


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


class PluginImplementationStatus(str, Enum):
    """How production-ready a plugin integration currently is."""
    NATIVE = "native"
    INTEGRATED = "integrated"
    PLACEHOLDER = "placeholder"


class ValidationMode(str, Enum):
    """How far SecuScan is allowed to validate a suspected issue."""
    DETECT_ONLY = "detect_only"
    PROOF = "proof"
    CONTROLLED_EXTRACT = "controlled_extract"


class EvidenceLevel(str, Enum):
    """How much evidence the platform should retain per finding."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


class FindingKind(str, Enum):
    """Normalized finding classification."""
    OBSERVATION = "observation"
    SUSPECTED_ISSUE = "suspected_issue"
    VALIDATED_ISSUE = "validated_issue"


class AnalystStatus(str, Enum):
    """Analyst review state for a finding."""
    NEW = "new"
    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"
    FIXED = "fixed"


class RetestStatus(str, Enum):
    """Retest lifecycle state for a finding."""
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class ExecutionContext(BaseModel):
    """Task/workflow execution policy selected by the operator."""
    target_policy_id: Optional[str] = None
    scan_profile: str = "standard"
    credential_profile_id: Optional[str] = None
    session_profile_id: Optional[str] = None
    validation_mode: ValidationMode = ValidationMode.PROOF
    evidence_level: EvidenceLevel = EvidenceLevel.STANDARD


class WorkflowStep(BaseModel):
    """Single workflow step."""
    plugin_id: str
    inputs: Dict[str, Any]
    preset: Optional[str] = None
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)


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
    capabilities: Optional[List[str]] = None
    implementation_status: Optional[PluginImplementationStatus] = None
    supports_authenticated_crawling: bool = False
    supports_session_reuse: bool = False
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
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)


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
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)
    error_message: Optional[str] = None
    exit_code: Optional[int] = None


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
    exploitability: Optional[float] = None
    confidence: Optional[float] = None
    validated: bool = False
    validation_method: Optional[str] = None
    confidence_reason: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    asset_refs: List[str] = Field(default_factory=list)
    service_fingerprint: Optional[str] = None
    cpe: Optional[str] = None
    references: List[Dict[str, Any]] = Field(default_factory=list)
    asset_exposure: Optional[str] = None
    risk_score: Optional[float] = None
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list)
    finding_kind: FindingKind = FindingKind.OBSERVATION
    finding_group_id: Optional[str] = None
    asset_id: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    occurrence_count: int = 1
    corroborating_sources: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    analyst_status: AnalystStatus = AnalystStatus.NEW
    retest_status: RetestStatus = RetestStatus.NOT_REQUESTED


class TaskResult(BaseModel):
    """Task execution result"""
    task_id: str
    plugin_id: str
    tool: str
    target: str
    timestamp: datetime
    duration_seconds: Optional[float]
    status: TaskStatus
    execution_context: ExecutionContext = Field(default_factory=ExecutionContext)
    
    summary: List[str] = []
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    findings: List[Finding] = Field(default_factory=list)
    finding_groups: List[Dict[str, Any]] = Field(default_factory=list)
    asset_summary: List[Dict[str, Any]] = Field(default_factory=list)
    scan_diff: Dict[str, Any] = Field(default_factory=dict)
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


class NotificationChannelType(str, Enum):
    """Supported notification delivery channels."""
    WEBHOOK = "webhook"
    EMAIL = "email"


class NotificationSeverityThreshold(str, Enum):
    """Minimum finding severity that can trigger a notification rule."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NotificationDeliveryStatus(str, Enum):
    """Outcome of a notification delivery attempt."""
    SUCCESS = "success"
    FAILED = "failed"


class NotificationRuleCreate(BaseModel):
    """Request payload for creating or updating a notification rule."""
    name: str = Field(..., max_length=255)
    severity_threshold: NotificationSeverityThreshold
    channel_type: NotificationChannelType
    target_url_or_email: str = Field(..., max_length=2000)
    is_active: bool = True


class NotificationRuleUpdate(BaseModel):
    """Partial update payload for a notification rule."""
    name: Optional[str] = Field(default=None, max_length=255)
    severity_threshold: Optional[NotificationSeverityThreshold] = None
    channel_type: Optional[NotificationChannelType] = None
    target_url_or_email: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class NotificationRuleResponse(BaseModel):
    """Stored notification rule returned by the API."""
    id: str
    name: str
    severity_threshold: str
    channel_type: str
    target_url_or_email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NotificationHistoryResponse(BaseModel):
    """Record of a single notification delivery attempt."""
    id: str
    rule_id: str
    finding_id: str
    status: str
    error_message: Optional[str] = None
    sent_at: datetime


class NotificationDiagnosticsResponse(BaseModel):
    """Diagnostic configuration details for notification delivery."""
    webhook_timeout_seconds: float
    webhook_connect_timeout_seconds: float
    max_retries: int
    backoff_factor_seconds: float


class BulkDeleteRequest(RootModel[Annotated[List[str], Field(max_length=MAX_BULK_DELETE)]]):
    """Accepts a JSON array of task IDs directly. Max 500 per request."""
    pass
