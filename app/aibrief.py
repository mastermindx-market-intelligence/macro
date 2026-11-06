"""Private, read-only AI Brief fragment from the existing atomic publication.

Uses the same Jinja body as the static dashboard and the site's existing auth
dependency. GET never starts a model, chooses a route, or mutates a publication.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from lib.aibrief_live import FILES, read_publication, view

PRIVATE_HEADERS = {"Cache-Control": "private, no-store, max-age=0", "Pragma": "no-cache",
                   "Vary": "Cookie, Authorization", "X-Content-Type-Options": "nosniff"}


def create_router(require_site_full_user, *, root: Path, state_dir: Path | None = None):
    router = APIRouter()
    state_dir = state_dir or Path(os.environ.get("MACRO_LIVE_STATE_DIR", "/var/lib/macro-live/state"))
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True,
                      undefined=StrictUndefined)

    @router.get("/api/aibrief/v1/{lens}")
    def read_brief(lens: str, request: Request, _user=Depends(require_site_full_user)):
        if lens not in FILES or request.query_params:
            return JSONResponse({"error": "INVALID_BRIEF_REQUEST"}, status_code=400, headers=PRIVATE_HEADERS)
        try:
            publication, fallback = read_publication(root, state_dir, lens)
            projection = view(publication, fallback, lens=lens)
            body = env.get_template("_aibrief_body.html.j2").module.aibrief_body(
                projection["brief"], lens, show_catalysts=lens == "macro", live=projection)
            return JSONResponse({key: projection[key] for key in (
                "schema", "lens", "sequence", "revision", "server_time", "status", "valid_until"
            )} | {"html": str(body)}, headers=PRIVATE_HEADERS)
        except Exception:
            # Neither raw provider errors nor server paths cross the read boundary.
            return JSONResponse({"error": "BRIEF_READ_UNAVAILABLE"}, status_code=503, headers=PRIVATE_HEADERS)

    return router
