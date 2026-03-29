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
