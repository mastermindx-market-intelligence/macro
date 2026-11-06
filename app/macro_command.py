"""Registered-user read composition over the existing served Macro Command owners.

The static /macrodata/ payload is free_registered. This API keeps that same
verified-user boundary; it does not create a score, producer, cache or publication.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

router = APIRouter()
MANIFEST_MAX_BYTES = 256 * 1024
BODY_MAX_BYTES = 2 * 1024 * 1024
TOTAL_MAX_BYTES = 16 * 1024 * 1024


class _ReadBudgetExceeded(Exception):
    pass


def require_user(authorization: str | None = Header(default=None)) -> dict:
    # Lazy import keeps mounting after app.main.require_user free of cycles.
    from app.main import require_user as verify_user
    return verify_user(authorization)


def _served_root() -> Path:
    # Caddy serves this exact directory, not the Git checkout's unserved site/.
    # Tests monkeypatch this function; no request or environment selects a path.
    return Path("/opt/macro/site.served")


def _bounded_bytes(path: Path, root: Path, maximum: int) -> bytes:
    # Reject symlinks/escapes before opening and cap the read on the opened inode.
    if path.resolve(strict=True) != path or not path.is_relative_to(root):
        raise ValueError("unqualified published path")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError("unqualified published file")
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("published file exceeds bound")
    return raw


@router.get("/api/macro/command")
def macro_command(_user: dict = Depends(require_user)) -> JSONResponse:
    headers = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, noarchive"}
    try:
        # Composition dependencies are request-scoped; auth and unrelated APIs
        # remain available while this artifact reader is unavailable.
        from lib import macro_suite_view
        from scripts import build_macro_suite_pages as builder

        root = _served_root()
        if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
            raise ValueError("unqualified served root")
        data_root = root / "macrodata"
        manifest_path = data_root / "workspaces" / "manifest.json"
        manifest_raw = _bounded_bytes(manifest_path, root, MANIFEST_MAX_BYTES)
        manifest = json.loads(manifest_raw.decode("utf-8"))
        if (not isinstance(manifest, dict)
                or manifest.get("schema") != "mastermind.macro_workspace_manifest.v1"
                or manifest.get("min_client_contract") != builder.MIN_CLIENT_CONTRACT
                or not isinstance(manifest.get("workspaces"), dict)):
            raise ValueError("unqualified manifest")
        generated_at = manifest.get("generated_at")
        if not isinstance(generated_at, str) or datetime.fromisoformat(generated_at).tzinfo is None:
            raise ValueError("manifest clock unavailable")

        total = len(manifest_raw)

        def read_json(path: Path):
            nonlocal total
            if path == manifest_path:
                return manifest, len(manifest_raw)
            if total + BODY_MAX_BYTES > TOTAL_MAX_BYTES:
                raise _ReadBudgetExceeded()
            try:
                raw = _bounded_bytes(path, data_root, BODY_MAX_BYTES)
                total += len(raw)
                if total > TOTAL_MAX_BYTES:
                    raise _ReadBudgetExceeded()
                return json.loads(raw.decode("utf-8")), len(raw)
            except (OSError, ValueError) as exc:
                raise builder.SnapshotRefused("SOURCE_FAILED", "published body unavailable") from exc

        entries = []
        for page in builder.SUITE_PAGES:
            entry = {
                "workspace_id": page.workspace_id,
                "region": page.region,
                "output": page.output,
                "title": builder._identity(page)["title"],
                "subtitle": builder._identity(page)["subtitle"],
                "snapshot": None,
                "failure": None,
            }
            try:
                entry["snapshot"], _ = builder.read_workspace(data_root, page, read_json=read_json)
            except builder.SnapshotRefused as exc:
                entry["failure"] = {"kind": exc.kind, "detail": "Published workspace could not be verified."}
            entries.append(entry)

        composed_at = datetime.now(timezone.utc).isoformat()
        header = macro_suite_view.build_command_header(entries, page_built_at=composed_at)
        sections = builder._macro_command_sections(entries, page_built_at=composed_at)
        builder._restrict_header_to_populated(header, entries, {section["id"] for section in sections})
        # A producer move invalidates this aggregate; never mix two manifest generations.
        if _bounded_bytes(manifest_path, root, MANIFEST_MAX_BYTES) != manifest_raw:
            raise ValueError("manifest changed during read")
        workspaces = []
        for entry in entries:
            snapshot = entry["snapshot"] or {}
            workspaces.append({
                "workspace_id": entry["workspace_id"], "region": entry["region"],
                "href": "/" + entry["output"], "title": entry["title"],
                "state": (snapshot.get("availability") or {}).get("state"),
                "availability": snapshot.get("availability"),
                "effective_date": (snapshot.get("headline") or {}).get("effective_date"),
                "calculation_as_of": (snapshot.get("generation") or {}).get("calculation_as_of"),
                "content_sha256": (snapshot.get("generation") or {}).get("content_sha256"),
                "generation_id": (snapshot.get("generation") or {}).get("generation_id"),
                "failure": entry["failure"],
            })
        healthy = sum(entry["snapshot"] is not None for entry in entries)
        body = {
            "schema": "mastermind.macro_command_read.v1",
            "state": "ready" if healthy == len(entries) else "partial" if healthy else "unavailable",
            "source": {
                "served_root_qualified": True,
                "manifest_generated_at": generated_at,
                "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                "composed_at": composed_at,
                "min_client_contract": builder.MIN_CLIENT_CONTRACT,
            },
            **header,
            "sections": [{
                "id": section["id"], "label": section["label"],
                "href": "/macro_monetary.html#" + section["id"],
                "deep_href": section.get("deep_href"),
                "detail_links": section.get("detail_links"),
                "subtabs": [{key: tab.get(key) for key in ("id", "label", "deep_href")}
                            for tab in section.get("subtabs") or []],
            } for section in sections],
            "workspaces": workspaces,
        }
        return JSONResponse(body, headers=headers)
    except Exception:
        return JSONResponse({"error": "macro command unavailable"}, status_code=503, headers=headers)
