"""Read-only, authenticated transport for the incumbent Intelligence Desk artifact.

The marketing IntelligenceStore remains the only aggregate story owner. Every
connection begins with a complete snapshot, including after reconnect: this API
does not claim delta replay and owns no database, cursor, scheduler or ingestion.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import threading
from typing import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.routing import APIRoute
from fastapi import Depends

SCHEMA = "intelligence.desk/v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_STORIES = 1000
POLL_SECONDS = 1.0
HEARTBEAT_SECONDS = 15.0
CONNECTION_SECONDS = 60.0
PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Cookie, Authorization",
    "X-Robots-Tag": "noindex, noarchive",
    "X-Content-Type-Options": "nosniff",
}


class _PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await original(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers={**(exc.headers or {}), **PRIVATE_HEADERS},
                )
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": jsonable_encoder(exc.errors())},
                    headers=dict(PRIVATE_HEADERS),
                )
        return handler


router = APIRouter(route_class=_PrivateRoute)
_cache_lock = threading.RLock()
_cache_key = None
_cache_payload = None
_cache_revision = None


def require_desk_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    # Same cookie/Bearer identity and launch-switch policy as the incumbent
    # aggregate desk. Licensed ticker-news keeps its separate paid/rights gate.
    from app.main import require_user
    from app.paywall import enforce_site_full
    return enforce_site_full(require_user(authorization, request=request))


def _snapshot_path() -> Path:
    return Path(os.environ.get(
        "MM_NEWS_DESK_SNAPSHOT",
        "/var/lib/macro-live/public/live/intelligence.json",
    ))


def _unavailable() -> HTTPException:
    return HTTPException(503, "news desk temporarily unavailable", headers=PRIVATE_HEADERS)


def _load_snapshot_file(path: Path) -> dict:
    """Bound the read itself, validate before serving, never fetch or repair."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("oversized desk artifact")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
            raise ValueError("desk schema")
        stories = payload.get("stories")
        if not isinstance(stories, list) or len(stories) > MAX_STORIES:
            raise ValueError("story collection")
        seen = set()
        for row in stories:
            if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                    or not row["id"].strip() or row["id"] in seen):
                raise ValueError("story identity")
            seen.add(row["id"])
        # JSON numeric constants NaN/Infinity are accepted by Python's decoder
        # but are not valid browser JSON. Fail at this boundary, not mid-stream.
        json.dumps(payload, allow_nan=False)
        return payload
    except (OSError, ValueError, TypeError, UnicodeError):
        raise _unavailable() from None


def _file_key(path: Path) -> tuple:
    info = path.stat()
    return (str(path), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_snapshot() -> dict:
    """Share one validated immutable read per atomic artifact revision/process.

    Authentication still precedes every request. This is a transient read cache,
    not an alternate story store; deletion or invalid replacement fails closed.
    """
    global _cache_key, _cache_payload, _cache_revision
    path = _snapshot_path()
    with _cache_lock:
        try:
            key = _file_key(path)
            if key == _cache_key:
                return _cache_payload
            payload = _load_snapshot_file(path)
            # An atomic replace while reading must never bind old bytes to the
            # new file identity. Return this coherent read; retry next poll.
            if _file_key(path) == key:
                revision = _revision(payload)
                _cache_key, _cache_payload, _cache_revision = key, payload, revision
            return payload
        except OSError:
            raise _unavailable() from None


def _revision(payload: dict) -> str:
    # The export clock advances even when no news arrives. Keep it out of the
    # change identity; story corrections/removals and health transitions count.
    if payload is _cache_payload and _cache_revision:
        return _cache_revision
    semantic = {key: value for key, value in payload.items() if key != "updated_at"}
    wire = json.dumps(semantic, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


def _event(name: str, payload: dict, revision: str | None = None) -> str:
    wire = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    prefix = f"id: {revision}\n" if revision else ""
    return f"{prefix}event: {name}\ndata: {wire}\n\n"


async def _events(
    request: Request,
    initial: dict,
    *,
    poll_seconds: float = POLL_SECONDS,
    heartbeat_seconds: float = HEARTBEAT_SECONDS,
    connection_seconds: float = CONNECTION_SECONDS,
) -> AsyncIterator[str]:
    """A full replacement protocol: no ambiguous snapshot-to-delta handoff."""
    started = time.monotonic()
    heartbeat_at = started
    revision = _revision(initial)
    # Last-Event-ID is intentionally not a skip condition. The atomic artifact
    # is authoritative; a reconnect always recovers corrections and removals.
    yield "retry: 1500\n" + _event("snapshot", initial, revision)
    while True:
        if await request.is_disconnected():
            return
        if time.monotonic() - started >= connection_seconds:
            # A finite connection re-enters canonical authentication frequently,
            # observing sign-out, expired sessions and changed access policy.
            yield _event("reconnect", {"reason": "refresh_session"})
            return
        await asyncio.sleep(poll_seconds)
        try:
            current = await asyncio.to_thread(_read_snapshot)
        except HTTPException:
            yield _event("unavailable", {"detail": "news desk temporarily unavailable"})
            return
        next_revision = _revision(current)
        if next_revision != revision:
            yield _event("snapshot", current, next_revision)
            revision = next_revision
        now = time.monotonic()
        if now - heartbeat_at >= heartbeat_seconds:
            # Connection proof only. Never a last-news or source-health stamp.
            yield _event("heartbeat", {
                "at": datetime.now(timezone.utc).isoformat(),
            })
            heartbeat_at = now


@router.get("/api/news-desk/snapshot")
async def news_desk_snapshot(user: dict = Depends(require_desk_user)) -> JSONResponse:
    del user
    payload = await asyncio.to_thread(_read_snapshot)
    return JSONResponse(payload, headers=dict(PRIVATE_HEADERS))


@router.get("/api/news-desk/stream")
async def news_desk_stream(
    request: Request,
    user: dict = Depends(require_desk_user),
) -> StreamingResponse:
    del user
    # Preflight happens after auth and before 200/event-stream has been sent.
    initial = await asyncio.to_thread(_read_snapshot)
    return StreamingResponse(
        _events(request, initial),
        media_type="text/event-stream",
        headers={**PRIVATE_HEADERS, "X-Accel-Buffering": "no"},
    )

