from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from .database import get_db

saved_views_router = APIRouter(prefix="/api/v1/saved-views", tags=["saved-views"])

_VALID_SORT_MODES = {"severity", "newest", "oldest", "target"}
_VALID_SEVERITIES = {"all", "critical", "high", "medium", "low", "info"}


class FilterPreset(BaseModel):
    """Validated representation of the frontend filter state."""
    severity:    str = "all"
    target:      str = "all"
    scanner:     str = "all"
    sortMode:    str = "severity"
    dateFrom:    str = ""
    dateTo:      str = ""
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
    name:        str = Field(..., min_length=1, max_length=60)
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
    name:        Optional[str] = Field(None, min_length=1, max_length=60)
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





@saved_views_router.get("")
async def list_saved_views() -> Dict[str, Any]:
    """Return all saved views ordered by creation date."""
    db = await get_db()
    rows: List[Dict] = await db.fetchall(
        "SELECT id, name, filter_json, created_at, updated_at "
        "FROM saved_views ORDER BY created_at ASC"
    )
    return {"views": rows, "total": len(rows)}


@saved_views_router.post("", status_code=201)
async def create_saved_view(body: SavedViewCreate) -> Dict[str, Any]:
    """
    Create a new saved view.
    Returns 409 if a view with the same name already exists.
    """
    db = await get_db()


    existing = await db.fetchone(
        "SELECT id FROM saved_views WHERE LOWER(name) = LOWER(?)", (body.name,)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A saved view named '{body.name}' already exists. "
                   "Use PUT to overwrite it.",
        )

    view_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO saved_views (id, name, filter_json)
        VALUES (?, ?, ?)
        """,
        (view_id, body.name, body.filter_json),
    )
    return {"id": view_id, "name": body.name, "created": True}


@saved_views_router.put("/{view_id}")
async def update_saved_view(view_id: str, body: SavedViewUpdate) -> Dict[str, Any]:
    """
    Overwrite name and/or filter_json for an existing view.
    Also accepts PATCH semantics — only supplied fields are updated.
    """
    db = await get_db()

    row = await db.fetchone("SELECT id FROM saved_views WHERE id = ?", (view_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Saved view not found")

    updates: List[str] = []
    params: List[Any] = []

    if body.name is not None:
        # Check for name collision with a *different* record
        collision = await db.fetchone(
            "SELECT id FROM saved_views WHERE LOWER(name) = LOWER(?) AND id != ?",
            (body.name, view_id),
        )
        if collision:
            raise HTTPException(
                status_code=409,
                detail=f"Another saved view named '{body.name}' already exists.",
            )
        updates.append("name = ?")
        params.append(body.name)

    if body.filter_json is not None:
        updates.append("filter_json = ?")
        params.append(body.filter_json)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = datetime('now')")
    params.append(view_id)

    await db.execute(
        f"UPDATE saved_views SET {', '.join(updates)} WHERE id = ?",
        tuple(params),
    )
    return {"id": view_id, "updated": True}


@saved_views_router.delete("/{view_id}")
async def delete_saved_view(view_id: str) -> Dict[str, Any]:
    """Delete a saved view by id. Idempotent — returns 200 even if not found."""
    db = await get_db()
    await db.execute("DELETE FROM saved_views WHERE id = ?", (view_id,))
    return {"id": view_id, "deleted": True}