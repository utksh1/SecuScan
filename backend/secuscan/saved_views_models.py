"""
Pure Pydantic model definitions for saved views.

These models contain no FastAPI or database dependencies.
saved_views.py re-imports them so existing call sites keep working.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


_VALID_SORT_MODES = {"severity", "newest", "oldest", "target"}
_VALID_SEVERITIES = {"all", "critical", "high", "medium", "low", "info"}


class FilterPreset(BaseModel):
    """Validated representation of the frontend filter state."""

    severity: str = "all"
    target: str = "all"
    scanner: str = "all"
    sortMode: str = "severity"
    dateFrom: str = ""
    dateTo: str = ""
    searchQuery: str = ""

    @field_validator("sortMode")
    @classmethod
    def validate_sort_mode(cls, v: str) -> str:
        if v not in _VALID_SORT_MODES:
            raise ValueError(f"sortMode must be one of {_VALID_SORT_MODES}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {_VALID_SEVERITIES}")
        return v


class SavedViewCreate(BaseModel):
    """Request body for POST /saved-views."""

    name: str = Field(..., min_length=1, max_length=60)
    filter_json: str

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("filter_json")
    @classmethod
    def validate_filter_json(cls, v: str) -> str:
        try:
            data = json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(f"filter_json is not valid JSON: {exc}") from exc
        FilterPreset(**data)
        return v


class SavedViewUpdate(BaseModel):
    """Request body for PUT /saved-views/{id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=60)
    filter_json: Optional[str] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be blank")
        return stripped

    @field_validator("filter_json")
    @classmethod
    def validate_filter_json(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            data = json.loads(v)
        except json.JSONDecodeError as exc:
            raise ValueError(f"filter_json is not valid JSON: {exc}") from exc
        FilterPreset(**data)
        return v
