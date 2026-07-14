from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from .database import get_db

saved_views_router = APIRouter(prefix="/api/v1/saved-views", tags=["saved-views"])

_VALID_SORT_MODES = {"severity", "newest", "oldest", "target"}
_VALID_SEVERITIES = {"all", "critical", "high", "medium", "low", "info"}

# Default owner for backward-compatible single-user deployments.
_DEFAULT_OWNER = "default"
_OWNER_HEADER = "x-user-id"


async def _get_owner(request: Request) -> str:
    """FastAPI dependency that resolves the caller's owner identity."""
    user_id = request.headers.get(_OWNER_HEADER)
    if user_id and user_id.strip():
        return f"user:{user_id.strip()}"
    return _DEFAULT_OWNER


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
    shared:      bool = False

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
    shared:      Optional[bool] = None

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
async def list_saved_views(owner: str = Depends(_get_owner)) -> Dict[str, Any]:
    """Return saved views visible to the caller: own views + shared views from others."""
    db = await get_db()
    rows: List[Dict] = await db.fetchall(
        "SELECT id, name, filter_json, owner_id, shared, created_at, updated_at "
        "FROM saved_views WHERE owner_id = ? OR shared = 1 "
        "ORDER BY created_at ASC",
        (owner,),
    )
    return {"views": rows, "total": len(rows)}


@saved_views_router.post("", status_code=201)
async def create_saved_view(body: SavedViewCreate, owner: str = Depends(_get_owner)) -> Dict[str, Any]:
    """
    Create a new saved view.
    Returns 409 if a view with the same name already exists for this owner.
    """
    db = await get_db()


    existing = await db.fetchone(
        "SELECT id FROM saved_views WHERE LOWER(name) = LOWER(?) AND owner_id = ?",
        (body.name, owner),
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
        INSERT INTO saved_views (id, name, filter_json, owner_id, shared)
        VALUES (?, ?, ?, ?, ?)
        """,
        (view_id, body.name, body.filter_json, owner, int(body.shared)),
    )
    return {"id": view_id, "name": body.name, "created": True}


@saved_views_router.put("/{view_id}")
async def update_saved_view(view_id: str, body: SavedViewUpdate, owner: str = Depends(_get_owner)) -> Dict[str, Any]:
    """
    Overwrite name and/or filter_json for an existing view.
    Also accepts PATCH semantics — only supplied fields are updated.
    Only the owner can modify a view; shared views are read-only to others.
    """
    db = await get_db()

    row = await db.fetchone(
        "SELECT id, owner_id, shared FROM saved_views WHERE id = ?", (view_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Saved view not found")

    if row["owner_id"] != owner:
        if row["shared"]:
            raise HTTPException(
                status_code=403,
                detail="Cannot modify a shared view owned by another user.",
            )
        raise HTTPException(status_code=403, detail="Not authorized to modify this view.")

    updates: List[str] = []
    params: List[Any] = []

    if body.name is not None:
        # Check for name collision with a *different* record owned by the same user
        collision = await db.fetchone(
            "SELECT id FROM saved_views WHERE LOWER(name) = LOWER(?) AND id != ? AND owner_id = ?",
            (body.name, view_id, owner),
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

    if body.shared is not None:
        updates.append("shared = ?")
        params.append(int(body.shared))

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
async def delete_saved_view(view_id: str, owner: str = Depends(_get_owner)) -> Dict[str, Any]:
    """Delete a saved view by id. Only the owner can delete their views."""
    db = await get_db()
    row = await db.fetchone(
        "SELECT id, owner_id FROM saved_views WHERE id = ?", (view_id,)
    )
    if not row:
        return {"id": view_id, "deleted": True}

    if row["owner_id"] != owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this view.")

    await db.execute("DELETE FROM saved_views WHERE id = ?", (view_id,))
    return {"id": view_id, "deleted": True}