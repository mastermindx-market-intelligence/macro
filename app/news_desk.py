"""Read-only, authenticated transport for the incumbent Intelligence Desk artifact.

The marketing IntelligenceStore remains the only aggregate story owner. Every
connection begins with a complete snapshot, including after reconnect: this API
does not claim delta replay and owns no database, scheduler or ingestion. Bounded
history cursors address the existing writer's private, current projection only.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
import threading
from typing import AsyncIterator
from urllib.parse import urlsplit

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.routing import APIRoute
from fastapi import Depends

from engine.marketing import intelligence_history as retained

SCHEMA = "intelligence.desk/v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_STORIES = 1000
POLL_SECONDS = 1.0
# Match the accepted company-news quiet-stream margin (Macro #9893).
# This is connection liveness only; it never advances reporting/source clocks.
HEARTBEAT_SECONDS = 5.0
CONNECTION_SECONDS = 60.0
PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Cookie, Authorization",
    "X-Robots-Tag": "noindex, noarchive",
    "X-Content-Type-Options": "nosniff",
}
COVERAGE_SCHEMA = "intelligence.coverage/v1"
_SOURCE_OUTCOMES = frozenset({
    "accepted", "unchanged", "empty", "filtered", "fetch_failed",
    "rejected", "acceptance_failed", "unknown",
})
_SOURCE_COUNTS = (
    "last_observed_item_count", "last_eligible_item_count",
    "last_filtered_item_count", "last_duplicate_item_count",
    "last_changed_item_count",
)
_PACKET_CLOCKS = (
    "published_at", "source_updated_at", "provider_indexed_at",
    "first_seen", "accepted_revision_at",
)


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
_frame_cache = None
_history_cache_lock = threading.RLock()
_history_cache_key = None
_history_cache_payload = None


def require_desk_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    # All four aggregate desk routes intentionally share the incumbent owner:
    # registered accounts while PAYWALL_ENABLED is off, site_full when armed.
    # Retained-history privacy is not an alternative entitlement policy.
    # Licensed ticker-news keeps its separate always-on paid/rights gate.
    from app.main import require_user
    from app.paywall import enforce_site_full
    return enforce_site_full(require_user(authorization, request=request))


def _snapshot_path() -> Path:
    return Path(os.environ.get(
        "MM_NEWS_DESK_SNAPSHOT",
        "/var/lib/macro-live/public/live/intelligence.json",
    ))


def _history_path() -> Path:
    # This explicit contract is paired with wire.intelligence.history_snapshot_path.
    # Never infer a SQLite or public/live history path from the aggregate file.
    return Path(os.environ.get("MM_NEWS_DESK_HISTORY_SNAPSHOT", str(retained.DEFAULT_PATH)))


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
    global _cache_key, _cache_payload, _cache_revision, _frame_cache
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
                _frame_cache = None
            return payload
        except OSError:
            raise _unavailable() from None


def _history_file_key(path: Path) -> tuple:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > retained.MAX_BYTES:
        raise retained.HistoryArtifactError("unsafe history artifact")
    return (str(path), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_history_file() -> dict:
    """Transient bounded read cache, invalidated on every atomic replacement."""
    global _history_cache_key, _history_cache_payload
    path = _history_path()
    with _history_cache_lock:
        key = _history_file_key(path)
        if key == _history_cache_key:
            return _history_cache_payload
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > retained.MAX_BYTES:
                raise retained.HistoryArtifactError("unsafe history artifact")
            payload = retained.decode(handle.read(retained.MAX_BYTES + 1))
        if _history_file_key(path) == key:
            _history_cache_key, _history_cache_payload = key, payload
        return payload


def _read_current_history(*, now: datetime | None = None) -> dict:
    """No SQLite access. Both files must agree with the current display grant."""
    now = now or datetime.now(timezone.utc)
    try:
        initial = _read_snapshot().get("retained_history")
        if not isinstance(initial, dict) or initial.get("state") != "available":
            raise retained.HistoryArtifactError("history not available")
        payload = _read_history_file()
        current = _read_snapshot()
        expected = retained.descriptor(payload)
        if initial != expected or current.get("retained_history") != expected:
            raise retained.HistoryArtifactError("history generation mismatch")
        # as_of is an export/tick clock, never measured causal latency. A fresh
        # current descriptor cannot make an older or future private export live.
        exported = retained._at(payload["as_of"])
        published = retained._at(current.get("updated_at"))
        if (published is None or exported > published or published > now
                or (now - exported).total_seconds() > retained.MAX_EXPORT_AGE_SECONDS
                or (now - published).total_seconds() > retained.MAX_EXPORT_AGE_SECONDS):
            raise retained.HistoryArtifactError("history export clock unavailable")
        scope = retained.display_scope(current.get("source_health"))
        if any(not retained.is_displayable(row, scope) for row in payload["stories"]):
            raise retained.HistoryArtifactError("history source scope changed")
        return payload
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        raise _unavailable() from None


def _revision(payload: dict) -> str:
    # The export clock advances even when no news arrives. Keep it out of the
    # change identity; story corrections/removals and health transitions count.
    # Coverage also calls this helper outside the cache owner. Keep the
    # identity check and cached revision read in the same critical section.
    with _cache_lock:
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


def _snapshot_delivery(payload: dict) -> tuple[str, bytes, bytes]:
    """One current artifact's UTF-8 frames; never cache by semantic hash alone.

    The normal and initial retry-prefixed forms have a fixed two-frame bound.
    This runs in a read worker, so concurrent readers neither repeat large JSON
    serialization nor block the event loop. Authentication still precedes I/O.
    """
    global _frame_cache
    with _cache_lock:
        revision = _revision(payload)
        if _frame_cache is not None and _frame_cache[0] is payload and _frame_cache[1] == revision:
            return _frame_cache[1:]
        frame = _event("snapshot", payload, revision).encode("utf-8")
        initial = b"retry: 1500\n" + frame
        if payload is _cache_payload and revision == _cache_revision:
            _frame_cache = (payload, revision, initial, frame)
        return revision, initial, frame


def _read_snapshot_delivery() -> tuple[str, bytes, bytes]:
    return _snapshot_delivery(_read_snapshot())


def _coverage_text(value: object, cap: int = 160) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if len(value) <= cap else ""


def _coverage_clock(value: object, now: datetime) -> tuple[datetime | None, str]:
    """Never manufacture a timezone, replace a bad clock or clamp future ages."""
    if value is None or value == "":
        return None, "missing"
    if not isinstance(value, str) or len(value) > 80:
        return None, "invalid"
    try:
        at = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if at.tzinfo is None or at.utcoffset() is None:
            return None, "invalid"
        at = at.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None, "invalid"
    return at, "future" if at > now else "valid"


def _coverage_clock_view(value: object, now: datetime) -> dict:
    at, state = _coverage_clock(value, now)
    return {
        "at": at.isoformat().replace("+00:00", "Z") if at else None,
        "state": state,
        "age_seconds": round((now - at).total_seconds(), 3) if state == "valid" else None,
    }


def _coverage_number(value: object, *, integer: bool = False) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        return None
    if value < 0 or value > 2**31 - 1 or not math.isfinite(value):
        return None
    return value if integer else round(value, 3)


def _coverage_labels(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {text for item in value if (text := _coverage_text(item))}


def _coverage_publishers(packet: dict) -> set[str]:
    labels = set()
    if name := _coverage_text(packet.get("source_name")):
        labels.add(name)
    evidence = packet.get("evidence")
    for source in (evidence if isinstance(evidence, list) else []):
        if not isinstance(source, dict):
            continue
        name = _coverage_text(source.get("name"))
        if not name:
            try:
                name = urlsplit(_coverage_text(source.get("url"), 2048)).hostname or ""
            except ValueError:
                name = ""
        if name:
            labels.add(name)
    return labels


def _coverage_distribution(groups: list[set[str]]) -> dict:
    counts = Counter(label for labels in groups for label in labels)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    # Explicit truncation keeps this diagnostic response bounded. Counts are
    # story memberships in labels, not mutually exclusive or independent sources.
    return {
        "values": [{"value": label, "stories": count} for label, count in ranked[:100]],
        "distinct_labels": len(counts),
        "missing_stories": sum(not labels for labels in groups),
        "omitted_labels": max(0, len(ranked) - 100),
        "omitted_story_memberships": sum(count for _, count in ranked[100:]),
    }


def _coverage_delay(clocks: list[dict], start: str, end: str) -> dict:
    values, excluded = [], Counter()
    for row in clocks:
        a, a_state = row[start]
        b, b_state = row[end]
        if a_state != "valid":
            excluded["start_" + a_state] += 1
        elif b_state != "valid":
            excluded["end_" + b_state] += 1
        elif b < a:
            excluded["reverse_clock_order"] += 1
        else:
            values.append((b - a).total_seconds())
    values.sort()

    def percentile(fraction: float) -> float | None:
        if not values:
            return None
        index = fraction * (len(values) - 1)
        low = math.floor(index)
        high = math.ceil(index)
        return round(values[low] + (values[high] - values[low]) * (index - low), 3)

    return {
        "from": start, "to": end, "unit": "seconds",
        "sample_count": len(values), "excluded": dict(sorted(excluded.items())),
        "p50": percentile(.5), "p95": percentile(.95), "p99": percentile(.99),
        "max": round(values[-1], 3) if values else None,
    }


def _coverage_source(row: dict, *, loaded: int, now: datetime) -> dict:
    clock_fields = (
        "last_attempt_at", "last_fetch_success_at", "last_accepted_at",
        "last_attempt_started_at", "last_attempt_completed_at",
    )
    clocks = {key: _coverage_clock_view(row.get(key), now) for key in clock_fields}
    enabled = row.get("enabled") if isinstance(row.get("enabled"), bool) else None
    outcome = row.get("last_outcome")
    outcome = outcome if isinstance(outcome, str) and outcome in _SOURCE_OUTCOMES else "unknown"
    reported = row.get("status")
    reported = reported if reported in ("held", "degraded", "observed", "unknown") else "unknown"
    if enabled is False:
        state = "held"
    elif (outcome in ("fetch_failed", "rejected", "acceptance_failed")
          or reported == "degraded" or row.get("last_error")):
        state = "degraded"
    elif any(clocks[key]["state"] == "future" for key in clock_fields):
        state = "unknown"
    elif clocks["last_fetch_success_at"]["state"] == "valid":
        success, _ = _coverage_clock(row.get("last_fetch_success_at"), now)
        attempt, attempt_state = _coverage_clock(row.get("last_attempt_at"), now)
        state = "checked" if attempt_state == "valid" and success >= attempt else "previous_success"
    elif clocks["last_attempt_at"]["state"] == "valid":
        state = "attempted"
    else:
        state = "unknown"
    status = _coverage_number(row.get("last_http_status"), integer=True)
    error = row.get("last_error_code")
    return {
        "id": row["id"], "publisher": _coverage_text(row.get("publisher")),
        "enabled": enabled, "reported_status": reported, "observation_state": state,
        "last_outcome": outcome, "loaded_stories": loaded,
        "declared_regions": sorted(_coverage_labels(row.get("coverage_regions"))),
        "configured_language": _coverage_text(row.get("language")) or None,
        "poll_eligibility_seconds": _coverage_number(row.get("poll_seconds"), integer=True),
        "clocks": clocks,
        "last_http_status": status if status is not None and 100 <= status <= 599 else None,
        **{key: _coverage_number(row.get(key), integer=True) for key in _SOURCE_COUNTS},
        "last_attempt_duration_ms": _coverage_number(row.get("last_attempt_duration_ms")),
        "last_error_code": error if isinstance(error, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", error) else None,
    }


def _build_coverage(payload: dict, *, now: datetime) -> dict:
    """Derive diagnostics solely from the same admitted display artifact.

    Source configuration tags are not a measured geographic coverage universe.
    Legacy outcomes/counts stay unknown. Acceptance/export timestamps inherit
    the collector's tick clock; their differences are not completion telemetry.
    This function does not query a database, resolve rights, fetch or persist.
    """
    now = now.astimezone(timezone.utc)
    stories = payload["stories"]
    dimensions = {name: [] for name in (
        "publisher_labels", "feed_ids", "languages", "categories",
        "declared_regions", "publisher_countries", "timestamp_quality_labels",
    )}
    feed_counts, clocks = Counter(), []
    for packet in stories:
        dimensions["publisher_labels"].append(_coverage_publishers(packet))
        for dimension, field in (("feed_ids", "feed_id"), ("languages", "language"),
                                 ("categories", "category"), ("publisher_countries", "publisher_country"),
                                 ("timestamp_quality_labels", "timestamp_quality")):
            value = _coverage_text(packet.get(field))
            dimensions[dimension].append({value} if value else set())
        dimensions["declared_regions"].append(_coverage_labels(packet.get("coverage_regions")))
        if feed := _coverage_text(packet.get("feed_id")):
            feed_counts[feed] += 1
        clocks.append({field: _coverage_clock(packet.get(field), now) for field in _PACKET_CLOCKS})

    health = payload.get("source_health")
    health = health if isinstance(health, list) else []
    source_rows, duplicate_ids, invalid_rows = {}, set(), 0
    for row in health[:1000]:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not row["id"].strip() or len(row["id"]) > 160):
            invalid_rows += 1
            continue
        if row["id"] in source_rows:
            duplicate_ids.add(row["id"])
        source_rows[row["id"]] = row
    # Conflicting source-health identities cannot select an arbitrary healthy row.
    sources = [_coverage_source(row, loaded=feed_counts[key], now=now)
               for key, row in sorted(source_rows.items()) if key not in duplicate_ids]
    clock_summary = {}
    for field in _PACKET_CLOCKS:
        states = Counter(row[field][1] for row in clocks)
        known = [row[field][0] for row in clocks if row[field][1] == "valid"]
        clock_summary[field] = {
            **{state: states[state] for state in ("valid", "missing", "invalid", "future")},
            "latest_at": max(known).isoformat().replace("+00:00", "Z") if known else None,
        }
    return {
        "schema": COVERAGE_SCHEMA,
        "observed_at": now.isoformat().replace("+00:00", "Z"),
        "artifact_revision": _revision(payload),
        "artifact_export_clock": _coverage_clock_view(payload.get("updated_at"), now),
        "scope": {
            "collection": "current_aggregate_projection",
            "history_complete": False, "geographic_completeness_measured": False,
            "publisher_independence_measured": False,
            "publisher_to_screen_latency_measured": False,
        },
        "loaded_coverage": {
            "stories": len(stories), "count_unit": "story_memberships_per_label",
            **{name: _coverage_distribution(groups) for name, groups in dimensions.items()},
        },
        "source_observations": {
            "scope": "published_feed_health_only",
            "rows": sources, "source_count": len(sources),
            "enabled_count": sum(row["enabled"] is True for row in sources),
            "held_count": sum(row["enabled"] is False for row in sources),
            "invalid_rows": invalid_rows, "duplicate_source_ids": len(duplicate_ids),
            "omitted_rows": max(0, len(health) - 1000),
            "stories_without_observed_feed": sum(
                not _coverage_text(packet.get("feed_id"))
                or _coverage_text(packet.get("feed_id")) not in source_rows
                or _coverage_text(packet.get("feed_id")) in duplicate_ids
                for packet in stories
            ),
        },
        "recorded_timing": {
            "basis": "current_packet_recorded_clocks",
            "acceptance_and_export_clock_basis": "collector_tick",
            "completion_latency_measured": False,
            "clocks": clock_summary,
            "differences": [
                _coverage_delay(clocks, "published_at", "first_seen"),
                _coverage_delay(clocks, "source_updated_at", "accepted_revision_at"),
                _coverage_delay(clocks, "provider_indexed_at", "accepted_revision_at"),
            ],
        },
    }


async def _events(
    request: Request,
    initial: dict,
    *,
    poll_seconds: float = POLL_SECONDS,
    heartbeat_seconds: float = HEARTBEAT_SECONDS,
    connection_seconds: float = CONNECTION_SECONDS,
) -> AsyncIterator[str | bytes]:
    """A full replacement protocol: no ambiguous snapshot-to-delta handoff."""
    started = time.monotonic()
    heartbeat_at = started
    revision, initial_frame, _ = await asyncio.to_thread(_snapshot_delivery, initial)
    # Last-Event-ID is intentionally not a skip condition. The atomic artifact
    # is authoritative; a reconnect always recovers corrections and removals.
    yield initial_frame
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
            next_revision, _, next_frame = await asyncio.to_thread(_read_snapshot_delivery)
        except HTTPException:
            yield _event("unavailable", {"detail": "news desk temporarily unavailable"})
            return
        if next_revision != revision:
            yield next_frame
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


@router.get("/api/news-desk/coverage")
async def news_desk_coverage(user: dict = Depends(require_desk_user)) -> JSONResponse:
    del user

    def read():
        payload = _read_snapshot()
        return _build_coverage(payload, now=datetime.now(timezone.utc))

    return JSONResponse(await asyncio.to_thread(read), headers=dict(PRIVATE_HEADERS))


@router.get("/api/news-desk/history")
async def news_desk_history(
    q: str = Query(default="", max_length=retained.QUERY_LIMITS["q"]),
    source: str = Query(default="", max_length=retained.QUERY_LIMITS["source"]),
    feed_id: str = Query(default="", max_length=retained.QUERY_LIMITS["feed_id"]),
    category: str = Query(default="", max_length=retained.QUERY_LIMITS["category"]),
    language: str = Query(default="", max_length=retained.QUERY_LIMITS["language"]),
    from_at: str | None = Query(default=None, max_length=retained.QUERY_LIMITS["from_at"]),
    to_at: str | None = Query(default=None, max_length=retained.QUERY_LIMITS["to_at"]),
    limit: int = Query(default=50, ge=1, le=retained.MAX_PAGE_SIZE),
    cursor: str | None = Query(default=None, max_length=retained.MAX_CURSOR_LENGTH),
    user: dict = Depends(require_desk_user),
) -> JSONResponse:
    del user
    try:
        query = retained.normalize_query(q=q, source=source, feed_id=feed_id, category=category,
                                        language=language, from_at=from_at, to_at=to_at, limit=limit)
    except retained.HistoryQueryError:
        raise HTTPException(400, {"code": "invalid_history_query"}) from None

    def read():
        return retained.page(_read_current_history(), query=query, cursor=cursor)

    try:
        page = await asyncio.to_thread(read)
    except retained.HistoryRevisionChanged:
        raise HTTPException(409, {"code": "history_revision_changed", "restart_required": True}) from None
    except retained.HistoryCursorError:
        raise HTTPException(400, {"code": "invalid_history_cursor"}) from None
    return JSONResponse(page, headers=dict(PRIVATE_HEADERS))
