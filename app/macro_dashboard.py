"""Authenticated, bounded read of the native Macro display publication.

Uses the existing served-directory and runtime-live owners. No engines execute
in the request; missing live state never falls back to the repository's site/live.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.macro_command import _bounded_bytes, _served_root, require_user
from lib.macro_dashboard_view import LIVE, MAX_BYTES, RELEASE_FEED, SCHEMA, project

router = APIRouter()
HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization",
           "X-Robots-Tag": "noindex, noarchive", "X-Content-Type-Options": "nosniff"}


def _live_root() -> Path:
    from app.main import LIVE as runtime_live
    return runtime_live


def _read(path: Path, root: Path) -> tuple[dict, bytes]:
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError("unqualified publication root")
    raw = _bounded_bytes(path, root, MAX_BYTES)
    value = json.loads(raw.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    if not isinstance(value, dict):
        raise ValueError("unqualified publication")
    return value, raw


@router.get("/api/macro/dashboard")
def macro_dashboard(request: Request, _user: dict = Depends(require_user)) -> JSONResponse:
    if request.query_params:
        return JSONResponse({"error": "bad_request"}, status_code=400, headers=HEADERS)
    try:
        root = _served_root()
        payload, raw = _read(root / "macrodata" / "dashboard.json", root)
        if payload.get("schema") != SCHEMA or payload.get("market") != "US" or payload.get("display_only") is not True:
            raise ValueError("unqualified dashboard contract")
        clock = datetime.fromisoformat(payload["published_at"])
        if clock.tzinfo is None or clock > datetime.now(timezone.utc):
            raise ValueError("unqualified publication clock")
    except (OSError, ValueError, TypeError, KeyError):
        return JSONResponse({"error": "dashboard_unavailable"}, status_code=503, headers=HEADERS)
    live = None
    try:
        live_root = _live_root()
        candidate, _ = _read(live_root / "risk_state.json", live_root)
        if candidate.get("schema") == "risk_state.v1":
            live = project(candidate, LIVE)
    except (OSError, ValueError, TypeError):
        pass  # Settled evidence remains usable; current assessment stays unavailable.
    releases = None
    try:
        live_root = _live_root()
        candidate, _ = _read(live_root / "release_publications.json", live_root)
        if candidate.get("schema") == "release_publications.v2" and candidate.get("is_context_only") is True:
            releases = project(candidate, RELEASE_FEED)
    except (OSError, ValueError, TypeError):
        pass
    return JSONResponse({**payload, "current_risk": live, "release_feed": releases, "publication_sha256": hashlib.sha256(raw).hexdigest(),
                         "read_at": datetime.now(timezone.utc).isoformat()}, headers=HEADERS)
