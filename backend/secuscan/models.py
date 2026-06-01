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
    asset_exposure: Optional[str] = None
    risk_score: Optional[float] = None
    risk_factors: List[Dict[str, Any]] = Field(default_factory=list)


class TaskResult(BaseModel):
    """Task execution result"""
    task_id: str
    plugin_id: str
    tool: str
    target: str
    timestamp: datetime
    duration_seconds: Optional[float]
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
    name: str
    severity_threshold: NotificationSeverityThreshold
    channel_type: NotificationChannelType
    target_url_or_email: str
    is_active: bool = True


class NotificationRuleUpdate(BaseModel):
    """Partial update payload for a notification rule."""
    name: Optional[str] = None
    severity_threshold: Optional[NotificationSeverityThreshold] = None
    channel_type: Optional[NotificationChannelType] = None
    target_url_or_email: Optional[str] = None
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


class BulkDeleteRequest(RootModel[Annotated[List[str], Field(max_length=MAX_BULK_DELETE)]]):
    """Accepts a JSON array of task IDs directly. Max 500 per request."""
    pass
