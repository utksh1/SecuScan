"""Helpers for target policies, profiles, crawl runs, and asset persistence."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from .database import Database
from .execution_context import normalize_execution_context
from .models import ExecutionContext


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _stable_asset_id(target: str, host: Any, port: Any, protocol: Any) -> str:
    material = "||".join(
        [
            str(target or "").strip().lower(),
            str(host or "").strip().lower(),
            str(port or "").strip().lower(),
            str(protocol or "").strip().lower(),
        ]
    )
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"asset:{digest}"


async def get_target_policy(db: Database, owner_id: str, policy_id: str | None) -> Optional[Dict[str, Any]]:
    if not policy_id:
        return None
    row = await db.fetchone(
        "SELECT * FROM target_policies WHERE id = ? AND owner_id = ?",
        (policy_id, owner_id),
    )
    return _deserialize_resource_row(row)


async def get_credential_profile(db: Database, owner_id: str, profile_id: str | None) -> Optional[Dict[str, Any]]:
    if not profile_id:
        return None
    row = await db.fetchone(
        "SELECT * FROM credential_profiles WHERE id = ? AND owner_id = ?",
        (profile_id, owner_id),
    )
    return _deserialize_resource_row(row)


async def get_session_profile(db: Database, owner_id: str, profile_id: str | None) -> Optional[Dict[str, Any]]:
    if not profile_id:
        return None
    row = await db.fetchone(
        "SELECT * FROM session_profiles WHERE id = ? AND owner_id = ?",
        (profile_id, owner_id),
    )
    return _deserialize_resource_row(row)


async def persist_crawl_run(
    db: Database,
    *,
    owner_id: str,
    task_id: str,
    plugin_id: str,
    target: str,
    crawl: Dict[str, Any],
    status: str = "completed",
) -> str:
    crawl_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO crawl_runs (
            id, owner_id, task_id, plugin_id, target, seed_url, status,
            summary_json, pages_json, forms_json, scripts_json, params_json, api_hints_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            crawl_id,
            owner_id,
            task_id,
            plugin_id,
            target,
            crawl.get("seed_url") or target,
            status,
            json.dumps(
                {
                    "final_url": crawl.get("final_url"),
                    "status_code": crawl.get("status_code"),
                    "page_count": len(crawl.get("pages", [])),
                    "form_count": len(crawl.get("forms", [])),
                    "api_hint_count": len(crawl.get("api_hints", [])),
                }
            ),
            json.dumps(crawl.get("pages", [])),
            json.dumps(crawl.get("forms", [])),
            json.dumps(crawl.get("scripts", [])),
            json.dumps(crawl.get("params", [])),
            json.dumps(crawl.get("api_hints", [])),
        ),
    )
    return crawl_id


async def replace_asset_services(
    db: Database,
    *,
    owner_id: str,
    task_id: str,
    plugin_id: str,
    target: str,
    services: Iterable[Dict[str, Any]],
) -> None:
    await db.execute("DELETE FROM asset_services WHERE task_id = ?", (task_id,))
    for item in services:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        host = str(item.get("host") or target)
        port = item.get("port")
        protocol = item.get("protocol")
        asset_id = str(item.get("asset_id") or _stable_asset_id(target, host, port, protocol))
        cert_sans = item.get("cert_san") or item.get("cert_sans") or metadata.get("cert_san") or metadata.get("cert_sans") or []
        if not isinstance(cert_sans, list):
            cert_sans = [cert_sans]
        service_fingerprint = item.get("service_fingerprint")
        if not service_fingerprint:
            service_fingerprint = " ".join(
                str(part).strip()
                for part in (
                    item.get("product"),
                    item.get("version"),
                    item.get("service"),
                    item.get("title"),
                )
                if str(part or "").strip()
            ) or None
        await db.execute(
            """
            INSERT INTO asset_services (
                id, owner_id, task_id, plugin_id, target, asset_id, host, ip, port, protocol,
                service, product, version, cpe, confidence, title, banner, cert_subject,
                cert_san_json, cert_expiry, service_fingerprint, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                owner_id,
                task_id,
                plugin_id,
                target,
                asset_id,
                host,
                item.get("ip"),
                item.get("port"),
                item.get("protocol"),
                item.get("service"),
                item.get("product"),
                item.get("version"),
                item.get("cpe"),
                item.get("confidence"),
                item.get("title"),
                item.get("banner"),
                item.get("cert_subject"),
                json.dumps(cert_sans),
                item.get("cert_expiry"),
                service_fingerprint,
                json.dumps(metadata),
            ),
        )


def serialize_execution_context(context: ExecutionContext | Dict[str, Any] | None) -> str:
    return json.dumps(normalize_execution_context(context or {}))


def _deserialize_resource_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    item = dict(row)
    for key in list(item.keys()):
        if key.endswith("_json") and isinstance(item[key], str):
            try:
                item[key[:-5]] = json.loads(item[key])
            except json.JSONDecodeError:
                item[key[:-5]] = item[key]
    return item


def deserialize_resource_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for row in rows:
        parsed = _deserialize_resource_row(row)
        if parsed is not None:
            results.append(parsed)
    return results
