from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScanMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    target: str
    timestamp: datetime
    tool: str


class FindingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeverityChange(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    before: FindingSchema
    after: FindingSchema


class DiffFindings(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    new_findings: list[FindingSchema] = Field(default_factory=list)
    fixed_findings: list[FindingSchema] = Field(default_factory=list)
    unchanged_findings: list[FindingSchema] = Field(default_factory=list)
    severity_changed: list[SeverityChange] = Field(default_factory=list)


class DiffSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_new: int = 0
    total_fixed: int = 0
    total_unchanged: int = 0
    total_severity_changed: int = 0


class ScanDiffResponse(BaseModel):
    """Top-level response for GET /api/v1/scans/diff."""

    model_config = ConfigDict(from_attributes=True)

    scan_a: ScanMeta
    scan_b: ScanMeta
    diff: DiffFindings
    summary: DiffSummary
