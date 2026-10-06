"""Private, rights-gated ticker news read API.

This router is a consumer of the qbus live-news store. It owns neither provider
ingestion nor source rights. Authentication/entitlement is the incumbent site-full
boundary; source-display rights are a separate gate and fail closed until a current
feed-specific receipt is bound.

The SQLite store is opened read-only after auth, entitlement, rights, and identity
checks. Request handlers never start the ingestion service and never mutate qbus.
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
import time
from typing import Any, AsyncIterator, Mapping

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from engine.company_intelligence.contracts import ContractError, safe_ticker
from engine.qbus_news_receipts import load_health_receipt, load_rights_receipt
from engine.qbus_news_store import (
    ChangePage,
    NewsReadRights,
    NewsSnapshot,
    NewsStore,
    StoreSchemaError,
    StoreUnavailable,
)
from engine.qbus_news_universe import qualify_universe
from lib import config

router = APIRouter()

_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}
_STREAM_HEADERS = {
    **_PRIVATE_HEADERS,
    "X-Accel-Buffering": "no",
}

_RATE_LIMIT_REQUESTS = 120
_RATE_LIMIT_WINDOW_SECONDS = 60.0
_RATE_LIMIT_MAX_KEYS = 8192
_rate_limit_lock = Lock()
_rate_limit_buckets: dict[str, deque[float]] = {}


class UniverseUnavailable(RuntimeError):
    pass


def _private_error(
    status_code: int,
    detail: str,
    inherited: Mapping[str, str] | None = None,
) -> HTTPException:
    safe = {
        str(k): str(v)
        for k, v in dict(inherited or {}).items()
        if str(k).lower() not in {"authorization", "set-cookie"}
    }
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={**safe, **_PRIVATE_HEADERS},
    )


def require_site_full_user(
    authorization: str | None = Header(default=None),
) -> dict:
    """Authenticate first, then enforce incumbent paid site access."""
    from app.main import require_user as _require_user  # noqa: PLC0415
    from app.paywall import enforce_site_full  # noqa: PLC0415

    try:
        return enforce_site_full(_require_user(authorization), always=True)
    except HTTPException as exc:
        raise _private_error(
            exc.status_code,
            str(exc.detail),
            exc.headers,
        ) from None


def _user_key(user: Mapping[str, Any]) -> str:
    for name in ("id", "user_id", "sub"):
        value = user.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise _private_error(401, "authentication required")


def _allow_request(user: Mapping[str, Any], *, now: float | None = None) -> bool:
    current = time.monotonic() if now is None else float(now)
    cutoff = current - _RATE_LIMIT_WINDOW_SECONDS
    key = _user_key(user)
    with _rate_limit_lock:
        bucket = _rate_limit_buckets.get(key)
        if bucket is None:
            if len(_rate_limit_buckets) >= _RATE_LIMIT_MAX_KEYS:
                oldest = min(
                    _rate_limit_buckets,
                    key=lambda item: _rate_limit_buckets[item][-1],
                )
                del _rate_limit_buckets[oldest]
            bucket = deque()
            _rate_limit_buckets[key] = bucket
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT_REQUESTS:
            return False
        bucket.append(current)
        return True


def _reset_rate_limit_for_tests() -> None:
    with _rate_limit_lock:
        _rate_limit_buckets.clear()


def _rate_or_429(user: Mapping[str, Any]) -> None:
    if not _allow_request(user):
        raise _private_error(
            429,
            "ticker news rate limit reached",
            {"Retry-After": str(int(_RATE_LIMIT_WINDOW_SECONDS))},
        )


def _news_db_path() -> Path:
    raw = os.environ.get("MM_TICKER_NEWS_DB", "").strip()
    if raw:
        return Path(raw)
    return config.data_dir() / "qbus" / "qbus.sqlite3"


def _open_store() -> NewsStore:
    try:
        return NewsStore.open_readonly(
            _news_db_path(),
            source_key="benzinga-rest",
        )
    except (StoreUnavailable, StoreSchemaError):
        raise _private_error(503, "ticker news temporarily unavailable") from None


def _safe_ticker_or_422(ticker: str) -> str:
    try:
        return safe_ticker(ticker)
    except ContractError:
        raise _private_error(422, "invalid ticker") from None


def _universe_path() -> Path | None:
    raw = os.environ.get("MM_TICKER_NEWS_UNIVERSE", "").strip()
    return Path(raw) if raw else None


def _security_for_ticker(ticker: str, now: datetime) -> str | None:
    """Resolve via the exact owner-supplied qualified universe, never by syntax."""
    path = _universe_path()
    if path is None or not path.is_file():
        raise UniverseUnavailable("ticker-news universe unavailable")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise UniverseUnavailable("ticker-news universe unreadable") from None
    if not isinstance(payload, Mapping):
        raise UniverseUnavailable("ticker-news universe invalid")
    qualified = qualify_universe(payload, asof=now)
    if qualified.status != "qualified":
        raise UniverseUnavailable("ticker-news universe unqualified")

    normalized = _safe_ticker_or_422(ticker)
    hits = {
        binding.security_id
        for binding in qualified.alias_bindings
        if binding.alias.upper() == normalized.upper()
    }
    if len(hits) > 1:
        raise UniverseUnavailable("ticker-news alias ambiguous")
    return next(iter(hits)) if hits else None


def _rights_receipt_path() -> Path | None:
    raw = os.environ.get("MM_TICKER_NEWS_RIGHTS", "").strip()
    return Path(raw) if raw else None


def _health_receipt_path() -> Path | None:
    raw = os.environ.get("MM_TICKER_NEWS_HEALTH", "").strip()
    return Path(raw) if raw else None


def _rights_for_user(user: Mapping[str, Any]) -> NewsReadRights | None:
    """Map only an owner-backed, current site-full receipt into display rights.

    Authentication and vendor API possession are deliberately insufficient.  The
    current store persists provider history, so the receipt contract also requires
    explicit ingestion + historical-retention capability before display can arm.
    """
    del user  # site-full audience was already authenticated by the route dependency
    path = _rights_receipt_path()
    if path is None:
        return None
    qualified = load_rights_receipt(
        path,
        now=datetime.now(timezone.utc),
        audience="site_full",
    )
    return None if qualified is None else qualified.rights


def _source_health() -> dict[str, Any]:
    """Read runtime evidence; absent or stale receipts never imply live."""
    path = _health_receipt_path()
    if path is None:
        return {
            "schema": "qbus.news_health.v1",
            "source": "benzinga",
            "state": "unavailable",
            "last_successful_catchup": None,
            "last_stream_event_at": None,
            "gap_unresolved": False,
            "reason": "receipt_path_unset",
        }
    return dict(
        load_health_receipt(
            path,
            now=datetime.now(timezone.utc),
            max_observation_age_seconds=120.0,
            max_catchup_age_seconds=120.0,
        )
    )


def _state_from_health(health: Mapping[str, Any], *, row_count: int) -> str:
    raw = str(health.get("state") or "").strip().lower()
    if raw == "live" and row_count == 0:
        return "quiet"
    if raw in {"live", "catching_up", "degraded", "restricted", "unavailable"}:
        return raw
    if raw == "quiet":
        return "quiet"
    return "degraded"


def _rights_or_503(user: Mapping[str, Any]) -> NewsReadRights:
    rights = _rights_for_user(user)
    if rights is None or not rights.allowed_sources:
        raise _private_error(503, "ticker news rights unavailable")
    return rights


def _security_or_404(ticker: str, *, now: datetime) -> tuple[str, str]:
    normalized = _safe_ticker_or_422(ticker)
    try:
        security_id = _security_for_ticker(normalized, now)
    except UniverseUnavailable:
        raise _private_error(503, "ticker news universe unavailable") from None
    if security_id is None:
        raise _private_error(404, "ticker not in qualified news universe")
    return normalized, security_id


def _story_row(row) -> dict[str, Any]:
    return jsonable_encoder(asdict(row))


def _snapshot_payload(
    *,
    ticker: str,
    security_id: str,
    snapshot: NewsSnapshot,
    health: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "ticker_news.snapshot.v1",
        "ticker": ticker,
        "security_id": security_id,
        "state": _state_from_health(health, row_count=len(snapshot.rows)),
        "rows": [_story_row(row) for row in snapshot.rows],
        "next_cursor": snapshot.next_cursor,
        "has_more": snapshot.has_more,
        "source_health": dict(health),
    }


def _changes_payload(
    *,
    ticker: str,
    security_id: str,
    page: ChangePage,
) -> dict[str, Any]:
    return {
        "schema": "ticker_news.changes.v1",
        "ticker": ticker,
        "security_id": security_id,
        "rows": [jsonable_encoder(asdict(row)) for row in page.rows],
        "next_sequence": page.next_sequence,
        "has_more": page.has_more,
    }


@router.get("/api/ticker-news/stories/{story_id}")
def ticker_news_story(
    story_id: str,
    user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    _rate_or_429(user)
    rights = _rights_or_503(user)
    try:
        with _open_store() as store:
            detail = store.story(story_id, rights=rights)
    except HTTPException:
        raise
    except Exception:
        raise _private_error(503, "ticker news temporarily unavailable") from None
    if detail is None:
        raise _private_error(404, "ticker news story not found")
    payload = jsonable_encoder(asdict(detail))
    payload["schema"] = "ticker_news.story.v1"
    return JSONResponse(
        payload,
        headers=dict(_PRIVATE_HEADERS),
    )


@router.get("/api/ticker-news/{ticker}/changes")
def ticker_news_changes(
    ticker: str,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    _rate_or_429(user)
    rights = _rights_or_503(user)
    normalized, security_id = _security_or_404(
        ticker,
        now=datetime.now(timezone.utc),
    )
    try:
        with _open_store() as store:
            page = store.changes_for_security(
                security_id,
                after_sequence=after_sequence,
                limit=limit,
                rights=rights,
            )
    except HTTPException:
        raise
    except Exception:
        raise _private_error(503, "ticker news temporarily unavailable") from None
    return JSONResponse(
        _changes_payload(
            ticker=normalized,
            security_id=security_id,
            page=page,
        ),
        headers=dict(_PRIVATE_HEADERS),
    )


@router.get("/api/ticker-news/{ticker}")
def ticker_news_snapshot(
    ticker: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: int | None = Query(default=None, ge=1),
    user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    _rate_or_429(user)
    rights = _rights_or_503(user)
    normalized, security_id = _security_or_404(
        ticker,
        now=datetime.now(timezone.utc),
    )
    try:
        with _open_store() as store:
            snapshot = store.snapshot(
                security_id,
                limit=limit,
                cursor=cursor,
                rights=rights,
            )
    except HTTPException:
        raise
    except Exception:
        raise _private_error(503, "ticker news temporarily unavailable") from None
    return JSONResponse(
        _snapshot_payload(
            ticker=normalized,
            security_id=security_id,
            snapshot=snapshot,
            health=_source_health(),
        ),
        headers=dict(_PRIVATE_HEADERS),
    )


def _sse_encode(event: str, payload: Mapping[str, Any]) -> str:
    body = json.dumps(
        jsonable_encoder(dict(payload)),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event}\ndata: {body}\n\n"


async def _sse_events(
    *,
    ticker: str,
    user: Mapping[str, Any],
    after_sequence: int,
    poll_seconds: float = 1.0,
    max_cycles: int | None = None,
) -> AsyncIterator[str]:
    normalized, security_id = _security_or_404(
        ticker,
        now=datetime.now(timezone.utc),
    )
    sequence = int(after_sequence)
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        rights = _rights_for_user(user)
        if rights is None or not rights.allowed_sources:
            yield _sse_encode(
                "restricted",
                {
                    "schema": "ticker_news.restricted.v1",
                    "ticker": normalized,
                    "detail": "ticker news rights unavailable",
                },
            )
            return
        try:
            with _open_store() as store:
                page = store.changes_for_security(
                    security_id,
                    after_sequence=sequence,
                    limit=200,
                    rights=rights,
                )
        except HTTPException:
            yield _sse_encode(
                "unavailable",
                {
                    "schema": "ticker_news.unavailable.v1",
                    "ticker": normalized,
                    "detail": "ticker news temporarily unavailable",
                },
            )
            return

        for row in page.rows:
            sequence = max(sequence, row.sequence)
            yield _sse_encode(row.kind, jsonable_encoder(asdict(row)))
        if not page.rows:
            yield ": heartbeat\n\n"
        if poll_seconds > 0:
            await asyncio.sleep(poll_seconds)


@router.get("/api/ticker-news/{ticker}/stream")
def ticker_news_stream(
    ticker: str,
    after_sequence: int = Query(default=0, ge=0),
    user: dict = Depends(require_site_full_user),
) -> StreamingResponse:
    _rate_or_429(user)
    # Preflight rights before the streaming response is established; the generator
    # checks the same owner again on every cycle to observe revocation.
    _rights_or_503(user)
    _security_or_404(ticker, now=datetime.now(timezone.utc))
    return StreamingResponse(
        _sse_events(
            ticker=ticker,
            user=user,
            after_sequence=after_sequence,
        ),
        media_type="text/event-stream",
        headers=dict(_STREAM_HEADERS),
    )
