from __future__ import annotations

import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from fastapi import FastAPI
from backend.secuscan.saved_views import saved_views_router
from backend.secuscan.database import Database, get_db
import backend.secuscan.database as _db_module


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def app_client():
    """
    Spin up an isolated FastAPI app with an in-memory SQLite database
    and the saved_views_router registered.
    """
    # In-memory DB — isolated per test function
    test_db = Database(":memory:")
    await test_db.connect()
    _db_module.db = test_db

    # Minimal app
    _app = FastAPI()
    _app.include_router(saved_views_router)

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await test_db.disconnect()
    _db_module.db = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

VALID_PRESET = {
    "severity":    "critical",
    "target":      "example.com",
    "scanner":     "nmap",
    "sortMode":    "newest",
    "dateFrom":    "2025-01-01",
    "dateTo":      "2025-12-31",
    "searchQuery": "open port",
}

ALL_FILTER_PRESET = {
    "severity":    "all",
    "target":      "all",
    "scanner":     "all",
    "sortMode":    "severity",
    "dateFrom":    "",
    "dateTo":      "",
    "searchQuery": "",
}


def make_body(name: str, preset: dict = VALID_PRESET) -> dict:
    return {"name": name, "filter_json": json.dumps(preset)}


# ─── LIST (GET /saved-views) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_empty(app_client: AsyncClient):
    """Initially no saved views exist."""
    res = await app_client.get("/api/v1/saved-views")
    assert res.status_code == 200
    body = res.json()
    assert body["views"] == []
    assert body["total"] == 0


# ─── CREATE (POST /saved-views) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_success(app_client: AsyncClient):
    """Creating a new view returns 201 with an id."""
    res = await app_client.post("/api/v1/saved-views", json=make_body("Critical Web Scan"))
    assert res.status_code == 201
    body = res.json()
    assert body["created"] is True
    assert isinstance(body["id"], str) and len(body["id"]) > 0
    assert body["name"] == "Critical Web Scan"


@pytest.mark.asyncio
async def test_create_appears_in_list(app_client: AsyncClient):
    """A created view is returned by the list endpoint."""
    await app_client.post("/api/v1/saved-views", json=make_body("My View"))
    res = await app_client.get("/api/v1/saved-views")
    body = res.json()
    assert body["total"] == 1
    assert body["views"][0]["name"] == "My View"
    stored_preset = json.loads(body["views"][0]["filter_json"])
    assert stored_preset["severity"] == "critical"


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_409(app_client: AsyncClient):
    """POSTing the same name twice returns 409."""
    await app_client.post("/api/v1/saved-views", json=make_body("Dupe"))
    res = await app_client.post("/api/v1/saved-views", json=make_body("Dupe"))
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_case_insensitive_duplicate(app_client: AsyncClient):
    """Name collision check is case-insensitive."""
    await app_client.post("/api/v1/saved-views", json=make_body("MyView"))
    res = await app_client.post("/api/v1/saved-views", json=make_body("myview"))
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_empty_name_rejected(app_client: AsyncClient):
    """Blank name is rejected with 422."""
    res = await app_client.post("/api/v1/saved-views", json={"name": "   ", "filter_json": json.dumps(VALID_PRESET)})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_json_rejected(app_client: AsyncClient):
    """Non-JSON filter_json is rejected with 422."""
    res = await app_client.post("/api/v1/saved-views", json={"name": "Bad", "filter_json": "not json at all"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_sort_mode_rejected(app_client: AsyncClient):
    """filter_json with an invalid sortMode is rejected."""
    bad_preset = {**VALID_PRESET, "sortMode": "by_moon_phase"}
    res = await app_client.post("/api/v1/saved-views", json=make_body("Bad Sort", bad_preset))
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_severity_rejected(app_client: AsyncClient):
    """filter_json with an invalid severity is rejected."""
    bad_preset = {**VALID_PRESET, "severity": "apocalyptic"}
    res = await app_client.post("/api/v1/saved-views", json=make_body("Bad Sev", bad_preset))
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_missing_filter_json_rejected(app_client: AsyncClient):
    """Request missing filter_json is rejected."""
    res = await app_client.post("/api/v1/saved-views", json={"name": "No Preset"})
    assert res.status_code == 422


# ─── APPLY — list then cherry-pick (simulates frontend restore) ───────────────

@pytest.mark.asyncio
async def test_apply_restores_correct_preset(app_client: AsyncClient):
    """
    'Applying' a view means the frontend reads filter_json and restores state.
    We verify the stored preset round-trips correctly.
    """
    await app_client.post("/api/v1/saved-views", json=make_body("Pentest View", VALID_PRESET))
    list_res = await app_client.get("/api/v1/saved-views")
    views = list_res.json()["views"]
    assert len(views) == 1
    restored = json.loads(views[0]["filter_json"])
    assert restored == VALID_PRESET


# ─── OVERWRITE / UPDATE (PUT /saved-views/{id}) ───────────────────────────────

@pytest.mark.asyncio
async def test_overwrite_filter_json(app_client: AsyncClient):
    """PUT updates filter_json for an existing view."""
    create_res = await app_client.post("/api/v1/saved-views", json=make_body("Overwrite Me"))
    view_id = create_res.json()["id"]

    new_preset = {**VALID_PRESET, "severity": "high", "sortMode": "oldest"}
    put_res = await app_client.put(
        f"/api/v1/saved-views/{view_id}",
        json={"filter_json": json.dumps(new_preset)},
    )
    assert put_res.status_code == 200
    assert put_res.json()["updated"] is True

    # Verify persisted
    list_res = await app_client.get("/api/v1/saved-views")
    stored = json.loads(list_res.json()["views"][0]["filter_json"])
    assert stored["severity"] == "high"
    assert stored["sortMode"] == "oldest"


@pytest.mark.asyncio
async def test_rename_view(app_client: AsyncClient):
    """PUT with only a new name renames the view."""
    create_res = await app_client.post("/api/v1/saved-views", json=make_body("Old Name"))
    view_id = create_res.json()["id"]

    put_res = await app_client.put(
        f"/api/v1/saved-views/{view_id}",
        json={"name": "New Name"},
    )
    assert put_res.status_code == 200

    list_res = await app_client.get("/api/v1/saved-views")
    assert list_res.json()["views"][0]["name"] == "New Name"


@pytest.mark.asyncio
async def test_rename_to_existing_name_returns_409(app_client: AsyncClient):
    """Renaming to another view's name returns 409."""
    await app_client.post("/api/v1/saved-views", json=make_body("Alpha"))
    beta_res = await app_client.post("/api/v1/saved-views", json=make_body("Beta"))
    beta_id = beta_res.json()["id"]

    res = await app_client.put(f"/api/v1/saved-views/{beta_id}", json={"name": "Alpha"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_update_nonexistent_view_returns_404(app_client: AsyncClient):
    """PUT on a missing id returns 404."""
    res = await app_client.put(
        "/api/v1/saved-views/nonexistent-uuid",
        json={"name": "Whatever"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_with_no_fields_returns_400(app_client: AsyncClient):
    """PUT with an empty body returns 400."""
    create_res = await app_client.post("/api/v1/saved-views", json=make_body("Empty Update"))
    view_id = create_res.json()["id"]
    res = await app_client.put(f"/api/v1/saved-views/{view_id}", json={})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_update_invalid_filter_json_rejected(app_client: AsyncClient):
    """PUT with malformed filter_json returns 422."""
    create_res = await app_client.post("/api/v1/saved-views", json=make_body("Will Fail"))
    view_id = create_res.json()["id"]
    res = await app_client.put(
        f"/api/v1/saved-views/{view_id}",
        json={"filter_json": "{not: valid json}"},
    )
    assert res.status_code == 422


# ─── DELETE (DELETE /saved-views/{id}) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_removes_view(app_client: AsyncClient):
    """Deleted view no longer appears in the list."""
    create_res = await app_client.post("/api/v1/saved-views", json=make_body("Delete Me"))
    view_id = create_res.json()["id"]

    del_res = await app_client.delete(f"/api/v1/saved-views/{view_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    list_res = await app_client.get("/api/v1/saved-views")
    assert list_res.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_is_idempotent(app_client: AsyncClient):
    """Deleting a non-existent id returns 200 (idempotent)."""
    res = await app_client.delete("/api/v1/saved-views/does-not-exist")
    assert res.status_code == 200
    assert res.json()["deleted"] is True


@pytest.mark.asyncio
async def test_delete_only_removes_target(app_client: AsyncClient):
    """Deleting one view leaves others intact."""
    await app_client.post("/api/v1/saved-views", json=make_body("Keep Me"))
    del_res = await app_client.post("/api/v1/saved-views", json=make_body("Remove Me"))
    del_id = del_res.json()["id"]

    await app_client.delete(f"/api/v1/saved-views/{del_id}")

    list_res = await app_client.get("/api/v1/saved-views")
    assert list_res.json()["total"] == 1
    assert list_res.json()["views"][0]["name"] == "Keep Me"


# ─── Security / negative path edge-cases ─────────────────────────────────────

@pytest.mark.asyncio
async def test_name_too_long_rejected(app_client: AsyncClient):
    """Names over 60 chars are rejected."""
    long_name = "x" * 61
    res = await app_client.post("/api/v1/saved-views", json=make_body(long_name))
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_filter_json_extra_fields_ignored(app_client: AsyncClient):
    """Extra unknown fields in filter_json don't cause a 422 (Pydantic extra='ignore')."""
    preset_with_extra = {**VALID_PRESET, "injected_field": "'; DROP TABLE saved_views; --"}
    res = await app_client.post("/api/v1/saved-views", json=make_body("Extra Fields", preset_with_extra))
    # Should succeed; FilterPreset ignores unknown fields by default
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_filter_json_with_null_values_rejected(app_client: AsyncClient):
    """filter_json with null where string expected is rejected."""
    bad_preset = {**VALID_PRESET, "severity": None}
    res = await app_client.post("/api/v1/saved-views", json=make_body("Null Sev", bad_preset))
    assert res.status_code == 422

# ── File-backed DB migration path ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_saved_views_migration_runs_for_file_db(tmp_path):
    """
    Test coverage ensuring migrations resolve and execute successfully
    when the database is backed by a real file path instead of ':memory:'.
    """
    db_file = tmp_path / "secuscan.db"
    db = Database(str(db_file))

    try:
        await db.connect()

        row = await db.fetchone(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='saved_views'
            """
        )

        assert row is not None
        assert row["name"] == "saved_views"

    finally:
        await db.disconnect()

@pytest.mark.asyncio
async def test_migration_failure_raises_runtime_error(tmp_path):
    """A corrupted migration file must abort startup with RuntimeError."""
    from pathlib import Path
    import backend.secuscan.database as _db_mod

    migrations_dir = Path(_db_mod.__file__).parent / "migrations"
    broken = migrations_dir / "999_broken_test.sql"
    broken.write_text("THIS IS NOT VALID SQL !!!")

    db = None
    try:
        db = Database(str(tmp_path / "test_fail.db"))
        with pytest.raises(RuntimeError, match="startup aborted"):
            await db.connect()
    finally:
        if db and db._connection:
            await db.disconnect()
        broken.unlink(missing_ok=True)


# ─── FilterPreset model validators ─────────────────────────────────────────────

from backend.secuscan.saved_views import FilterPreset, SavedViewCreate
from pydantic import ValidationError


class TestFilterPresetDefaults:
    def test_default_severity_is_all(self):
        preset = FilterPreset()
        assert preset.severity == "all"

    def test_default_sort_mode_is_severity(self):
        preset = FilterPreset()
        assert preset.sortMode == "severity"

    def test_default_scanner_is_all(self):
        preset = FilterPreset()
        assert preset.scanner == "all"


class TestFilterPresetValidateSortMode:
    def test_valid_sort_modes(self):
        for mode in ("severity", "newest", "oldest", "target"):
            preset = FilterPreset(sortMode=mode)
            assert preset.sortMode == mode

    def test_invalid_sort_mode_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            FilterPreset(sortMode="invalid_mode")
        assert "sortMode must be one of" in str(exc_info.value)


class TestFilterPresetValidateSeverity:
    def test_valid_severities(self):
        for sev in ("all", "critical", "high", "medium", "low", "info"):
            preset = FilterPreset(severity=sev)
            assert preset.severity == sev

    def test_invalid_severity_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            FilterPreset(severity="dangerous")
        assert "severity must be one of" in str(exc_info.value)


# ─── SavedViewCreate model validators ──────────────────────────────────────────

class TestSavedViewCreateStripName:
    def test_valid_name_passes(self):
        sv = SavedViewCreate(name="My View", filter_json='{"severity":"all"}')
        assert sv.name == "My View"

    def test_strips_leading_trailing_whitespace(self):
        sv = SavedViewCreate(name="  trimmed  ", filter_json='{"severity":"all"}')
        assert sv.name == "trimmed"

    def test_blank_name_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SavedViewCreate(name="   ", filter_json='{"severity":"all"}')
        assert "name cannot be blank" in str(exc_info.value)

    def test_empty_string_name_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SavedViewCreate(name="", filter_json='{"severity":"all"}')
        # Pydantic's min_length=1 constraint fires before field_validator,
        # raising string_too_short.
        assert "string_too_short" in str(exc_info.value)


class TestSavedViewCreateValidateFilterJson:
    def test_valid_json_passes(self):
        sv = SavedViewCreate(name="v", filter_json='{"severity":"critical"}')
        assert sv.filter_json == '{"severity":"critical"}'

    def test_malformed_json_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SavedViewCreate(name="v", filter_json="not json")
        # pydantic raises an error for invalid JSON in field_validator
        assert "validation error" in str(exc_info.value).lower()
