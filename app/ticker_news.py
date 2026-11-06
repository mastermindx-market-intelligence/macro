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
import copy
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import hashlib
import logging
import math
import os
from pathlib import Path
import re
from threading import Lock
import time
from typing import Any, AsyncIterator, Literal, Mapping

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from engine.company_intelligence.contracts import ContractError, safe_ticker
from engine.qbus_news_annotate import (
    ANNOTATOR_VERSION,
    annotate_row,
    derivative_permitted,
)
from engine.qbus_news_receipts import (
    QualifiedNewsRights,
    load_health_receipt,
    load_rights_receipt,
)
from engine.qbus_news_store import (
    ChangePage,
    NewsReadRights,
    NewsSnapshot,
    NewsStore,
    StoreSchemaError,
    StoreUnavailable,
)
from engine.qbus_news_universe import QualifiedSecurity, qualify_universe
from engine.qbus_news_receipts import additional_rights_paths, combine_news_rights, load_rights_set
from engine.qbus_news_quality import EDITORIAL_POLICY_VERSION, curated_source, publisher_identity, story_quality
from engine.qkernel import publisher_category
from engine.news_common import company_reference_names
from engine.qbus_news_editorial import NewsEditorialView, company_reference_context
from lib import config
from app.ticker_news_stream import BlockingReadPool, SharedChangeReader

logger = logging.getLogger(__name__)

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


class _PrivateValidationRoute(APIRoute):
    """Give this router's query-validation 422s the private error headers.

    Out-of-range Query constraints are rejected by FastAPI's default
    RequestValidationError handling before the route body runs; re-issue that
    same 422 body with the private headers instead of the bare default.
    """

    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            try:
                return await original(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": jsonable_encoder(exc.errors())},
                    headers=dict(_PRIVATE_HEADERS),
                )

        return handler


router = APIRouter(route_class=_PrivateValidationRoute)
_STREAM_CHANGE_READER = SharedChangeReader()
_STREAM_BLOCKING_READER = BlockingReadPool()


# W11-07 additive snapshot provenance.  The snapshot route installs a fresh
# holder per request; the REAL gating reads populate it as a side effect, so
# provenance adds no file read.  Deliberately mutable: mutation is visible
# regardless of thread or context copying.
@dataclass
class _SnapshotProvenance:
    rights: QualifiedNewsRights | None = None
    receipts: tuple[QualifiedNewsRights, ...] = ()
    security: QualifiedSecurity | None = None
    universe_revision: str | None = None


_SNAPSHOT_PROVENANCE: ContextVar[_SnapshotProvenance | None] = ContextVar(
    "ticker_news_snapshot_provenance", default=None
)

# Wave B news-flow rail (ticker_news.flow.v1).  The store method is owned by
# lane B1; this layer only computes, validates, and applies feed-health
# coverage.  It never derives counts itself.
FLOW_SCHEMA = "ticker_news.flow.v1"
FLOW_PARTIAL_STATES = frozenset({"catching_up", "degraded"})

_FLOW_KEYS = frozenset(
    {
        "schema",
        "state",
        "reason",
        "coverage",
        "as_of",
        "reports_24h",
        "reports_7d",
        "stories_24h",
        "median_daily_28d",
        "daily_counts_28d",
        "history_days_observed",
        "comparison",
        "provenance",
    }
)
_FLOW_PROVENANCE_KEYS = frozenset(
    {
        "velocity_schema",
        "sources_counted",
        "status_counted",
        "distinct_by",
        "story_grouping",
        "cluster_policy_version",
        "windows",
        "calculation",
        "time_basis_counts_24h",
    }
)
_FLOW_DAILY_WINDOW_KEYS = frozenset(
    {"start_date", "end_date", "unit", "excludes", "order"}
)
_FLOW_AS_OF_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

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


def _open_store(*, editorial_view: NewsEditorialView | None = None) -> NewsStore:
    try:
        return NewsStore.open_readonly(
            _news_db_path(),
            source_key="benzinga-rest",
            curated=True,
            editorial_view=editorial_view,
        )
    except (StoreUnavailable, StoreSchemaError):
        raise _private_error(503, "ticker news temporarily unavailable") from None


def _safe_ticker_or_422(ticker: str) -> str:
    try:
        return safe_ticker(ticker)
    except ContractError:
        raise _private_error(422, "invalid ticker") from None


def _universe_path() -> Path:
    raw = os.environ.get("MM_TICKER_NEWS_UNIVERSE", "").strip()
    return Path(raw) if raw else config.data_dir() / "qbus" / "news_universe.json"


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
    if not hits:
        return None
    security_id = next(iter(hits))
    holder = _SNAPSHOT_PROVENANCE.get()
    if holder is not None:
        for security in qualified.securities:
            if security.security_id == security_id:
                holder.security = security
                holder.universe_revision = qualified.revision
                break
    return security_id


def _rights_receipt_path() -> Path | None:
    raw = os.environ.get("MM_TICKER_NEWS_RIGHTS", "").strip()
    return Path(raw) if raw else None


def _health_receipt_path() -> Path | None:
    raw = os.environ.get("MM_TICKER_NEWS_HEALTH", "").strip()
    return Path(raw) if raw else None


def _additional_rights_paths() -> tuple[Path, ...]:
    return additional_rights_paths()


def _current_rights_receipts() -> tuple[QualifiedNewsRights, ...]:
    path = _rights_receipt_path()
    paths = ((path,) if path is not None else ()) + _additional_rights_paths()
    return load_rights_set(paths, now=datetime.now(timezone.utc), audience="site_full")


def _rights_for_user(user: Mapping[str, Any]) -> NewsReadRights | None:
    """Compose current owner-issued policies without sharing fields across sources."""
    del user  # authenticated site-full audience was enforced by the route dependency
    receipts = _current_rights_receipts()
    if not receipts:
        return None
    holder = _SNAPSHOT_PROVENANCE.get()
    if holder is not None:
        holder.rights = receipts[0] if len(receipts) == 1 else None
        holder.receipts = receipts
    return receipts[0].rights if len(receipts) == 1 else combine_news_rights(receipts)


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


def _curated_health(health: Mapping[str, Any], rights: NewsReadRights) -> dict[str, Any]:
    """Scope delivery evidence to publishers this reader can actually see."""
    eligible = frozenset(
        source for source in rights.allowed_sources
        if rights.allows(source, "title") and curated_source(source)
    )
    result = dict(health)
    if "benzinga" not in eligible:
        result.update(state="unavailable", last_successful_catchup=None,
                      last_stream_event_at=None, reason="no_curated_primary_source")
    if "additional_sources" in health:
        extras = []
        for item in health.get("additional_sources") or []:
            if not isinstance(item, Mapping) or item.get("provider") != "massive":
                continue
            publishers = [publisher for publisher in item.get("configured_publishers", [])
                          if isinstance(publisher, str) and "massive:" + publisher in eligible]
            if not publishers:
                continue
            entry = dict(item, configured_publishers=publishers)
            # The writer count includes rejected articles and cannot describe
            # this curated population. Keep its untouched receipt at the writer.
            entry.pop("accepted_reports_since_start", None)
            extras.append(entry)
        result["additional_sources"] = extras
    return result


def _state_from_health(health: Mapping[str, Any], *, row_count: int) -> str:
    raw = str(health.get("state") or "").strip().lower()
    extras = health.get("additional_sources") or []
    if raw == "unavailable" and any(item.get("state") == "available" for item in extras):
        return "degraded" if row_count else "quiet"
    if raw == "live" and any(item.get("state") != "available" for item in extras):
        return "degraded"
    if raw == "live" and row_count == 0:
        return "quiet"
    if raw in {"live", "catching_up", "degraded", "restricted", "unavailable"}:
        return raw
    if raw == "quiet":
        return "quiet"
    return "degraded"


def _flow_now() -> datetime:
    return datetime.now(timezone.utc)


def _flow_unavailable(reason: str) -> dict:
    """The exact ticker_news.flow.v1 unavailable shape, keys in serving order."""
    return {
        "schema": FLOW_SCHEMA,
        "state": "unavailable",
        "reason": reason,
        "coverage": "complete",
        "as_of": None,
        "reports_24h": None,
        "reports_7d": None,
        "stories_24h": None,
        "median_daily_28d": None,
        "daily_counts_28d": None,
        "history_days_observed": None,
        "comparison": None,
        "provenance": None,
    }


def _flow_payload_valid(flow: object) -> bool:
    """Wave B contract section 4; total — any failure is simply False."""

    def count(value: object) -> bool:
        return (
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
        )

    def no_empty_strings(value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value != ""
        if isinstance(value, dict):
            return all(value) and all(
                no_empty_strings(item) for item in value.values()
            )
        if isinstance(value, (list, tuple)):
            return all(no_empty_strings(item) for item in value)
        return True

    try:
        if not isinstance(flow, dict) or set(flow) != _FLOW_KEYS:
            return False
        if flow["schema"] != FLOW_SCHEMA:
            return False
        if flow["state"] not in ("ok", "thin_history", "unavailable"):
            return False
        if flow["reason"] not in (None, "no_accessible_sources", "calculation_failed"):
            return False
        if flow["coverage"] not in ("complete", "partial"):
            return False
        if flow["state"] == "unavailable":
            if flow["reason"] is None or flow["coverage"] != "complete":
                return False
            return all(
                flow[key] is None
                for key in _FLOW_KEYS
                if key not in ("schema", "state", "reason", "coverage")
            )
        if flow["reason"] is not None:
            return False
        if not isinstance(flow["as_of"], str):
            return False
        if _FLOW_AS_OF_PATTERN.match(flow["as_of"]) is None:
            return False
        if not all(
            count(flow[key])
            for key in ("reports_24h", "reports_7d", "stories_24h")
        ):
            return False
        daily = flow["daily_counts_28d"]
        if (
            not isinstance(daily, list)
            or len(daily) != 28
            or not all(count(value) for value in daily)
        ):
            return False
        history = flow["history_days_observed"]
        if not count(history) or not 0 <= history <= 28:
            return False
        if (
            flow["stories_24h"] > flow["reports_24h"]
            or flow["reports_24h"] > flow["reports_7d"]
        ):
            return False
        provenance = flow["provenance"]
        if not isinstance(provenance, dict):
            return False
        if not _FLOW_PROVENANCE_KEYS <= set(provenance):
            return False
        if not no_empty_strings(provenance):
            return False
        sources = provenance["sources_counted"]
        if (
            not isinstance(sources, list)
            or not sources
            or not all(isinstance(item, str) and item for item in sources)
        ):
            return False
        windows = provenance["windows"]
        if not isinstance(windows, dict):
            return False
        if not {"reports_24h", "reports_7d", "daily_28d"} <= set(windows):
            return False
        daily_window = windows["daily_28d"]
        if not isinstance(daily_window, dict):
            return False
        if not _FLOW_DAILY_WINDOW_KEYS <= set(daily_window):
            return False
        calculation = provenance["calculation"]
        if not isinstance(calculation, dict):
            return False
        if not {"method", "comparison_rule"} <= set(calculation):
            return False
        basis = provenance["time_basis_counts_24h"]
        if not isinstance(basis, dict):
            return False
        if (
            not count(basis.get("published_at"))
            or not count(basis.get("received_at"))
        ):
            return False
        if basis["published_at"] + basis["received_at"] != flow["reports_24h"]:
            return False
        median = flow["median_daily_28d"]
        comparison = flow["comparison"]
        if flow["state"] == "ok":
            if history < 20:
                return False
            if isinstance(median, bool) or not isinstance(median, (int, float)):
                return False
            if not math.isfinite(median) or median < 0:
                return False
            if flow["coverage"] == "complete":
                return comparison in ("busier", "typical", "quieter")
            return comparison is None
        if history > 19 or median is not None:
            return False
        if flow["coverage"] == "complete":
            return comparison == "insufficient_history"
        return comparison is None
    except Exception:
        return False


def _compute_flow(store, security_id: str, *, rights: NewsReadRights) -> dict:
    """Ask the store for the flow; never raise and never leak a partial dict.

    A flow failure must not take the rows down (G3): any exception or any
    payload that fails the contract validator degrades to the unavailable
    flow.  Empty rights answer without touching the store method at all.
    """
    if not rights.allowed_sources:
        return _flow_unavailable("no_accessible_sources")
    try:
        result = store.news_flow(security_id, now=_flow_now(), rights=rights)
    except Exception:
        logger.exception("ticker_news flow calculation failed")
        return _flow_unavailable("calculation_failed")
    if not _flow_payload_valid(result):
        logger.error("ticker_news flow payload failed validation")
        return _flow_unavailable("calculation_failed")
    try:
        return copy.deepcopy(result)
    except Exception:
        logger.exception("ticker_news flow calculation failed")
        return _flow_unavailable("calculation_failed")


def _apply_flow_coverage(flow: dict, *, snapshot_state: str) -> dict:
    """Rule row 1 of flow_compare.v1, applied by the only layer that knows health.

    An unavailable flow is returned unchanged; any other flow under a partial
    snapshot state keeps its counts but carries coverage "partial" and no
    comparison.
    """
    if flow.get("state") == "unavailable":
        return flow
    if snapshot_state in FLOW_PARTIAL_STATES:
        partial = copy.deepcopy(flow)
        partial["coverage"] = "partial"
        partial["comparison"] = None
        return partial
    return flow


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



def _resolve_reader_view(
    ticker: str, mode: str | None, *, now: datetime, rights: NewsReadRights | None = None,
) -> tuple[str, str, NewsEditorialView | None]:
    """Attach display evidence only after the incumbent identity owner resolves it."""
    holder = _SNAPSHOT_PROVENANCE.get() or _SnapshotProvenance()
    token = _SNAPSHOT_PROVENANCE.set(holder)
    try:
        normalized, security_id = _security_or_404(ticker, now=now)
    finally:
        _SNAPSHOT_PROVENANCE.reset(token)
    if mode is None:
        return normalized, security_id, None
    security = holder.security
    if security is None or security.security_id != security_id or not holder.universe_revision:
        raise _private_error(503, "ticker news company context unavailable")
    context = company_reference_context(
        security_id=security_id, ticker=security.ticker,
        universe_revision=holder.universe_revision,
        names=company_reference_names(security.ticker),
        symbols=(security.ticker, *security.aliases),
    )
    if rights is None:
        raise _private_error(503, "ticker news rights unavailable")
    permitted = _derivative_permitted_after_rights()
    scope = [
        (source, *(rights.allows(source, field) for field in ("title", "url", "teaser")),
         source in permitted if isinstance(permitted, frozenset) else permitted is True)
        for source in sorted(rights.allowed_sources)
    ]
    rights_revision = hashlib.sha256(json.dumps(scope).encode()).hexdigest()
    return normalized, security_id, NewsEditorialView(
        mode=mode, company=context, rights_revision=rights_revision,
    )


def _open_reader(view: NewsEditorialView | None):
    return _open_store() if view is None else _open_store(editorial_view=view)


def _check_view_revision(
    view: NewsEditorialView | None, expected: str | None, *, resuming: bool = False,
) -> None:
    if view is None:
        if expected is not None:
            raise _private_error(422, "editorial view required")
        return
    if resuming and expected is None:
        raise _private_error(422, "editorial view revision required")
    if expected is not None and expected != view.revision:
        raise _private_error(409, "ticker news view changed; refresh required")


def _view_payload(view: NewsEditorialView | None) -> dict[str, Any]:
    return {"editorial_view": view.metadata()} if view is not None else {}


def _derivative_permitted_after_rights() -> bool | frozenset[str]:
    """Derivative flag for this request. Caller already holds qualified rights."""
    if _additional_rights_paths():
        receipts = _current_rights_receipts()
        rights = combine_news_rights(receipts)
        return frozenset(
            receipt.source for receipt in receipts
            if receipt.derivative_processing and receipt.source in rights.allowed_sources
        )
    path = _rights_receipt_path()
    if path is None:
        return False
    return derivative_permitted(path)


def _annotations_payload(permitted: bool) -> dict[str, str]:
    return {
        "state": "on" if permitted else "not_permitted",
        "annotator_version": ANNOTATOR_VERSION,
    }


def _attach_annotation(
    payload: dict[str, Any],
    *,
    title: str | None,
    teaser: str | None,
    permitted: bool,
    editorial_view: NewsEditorialView | None = None,
) -> dict[str, Any]:
    allowed = payload.get("source") in permitted if isinstance(permitted, frozenset) else permitted
    payload["annotation"] = annotate_row(title, teaser) if allowed else None
    if editorial_view is not None:
        payload["editorial"] = (
            editorial_view.decision(source=str(payload.get("source") or ""),
                                    title=title or "", teaser=teaser or "",
                                    url=str(payload.get("url") or ""))
            if allowed and title and payload.get("kind") != "remove" else None
        )
        payload.update(_view_payload(editorial_view))
    compared_sources = frozenset(payload.pop("reporting_sources", ()))
    comparison_allowed = (
        bool(compared_sources) and compared_sources.issubset(permitted)
        if isinstance(permitted, frozenset) else permitted is True
    )
    if not comparison_allowed:
        payload["reporting_state"] = "not_compared"
    source = str(payload.get("source") or "")
    url = str(payload.get("url") or "")
    payload["publisher"] = publisher_identity(source, url)
    payload["content_kind"] = publisher_category(payload["publisher"])
    payload["provider"] = "massive" if source.startswith("massive:") else None
    if title:
        score, reason = story_quality(title=title, url=url, source=source)
        # A material difference must remain discoverable in the signal view.
        low_value = reason is not None and payload.get("reporting_state") not in {
            "reports_differ", "comparison_limited",
        }
        payload["quality"] = {"score": score, "low_value": low_value, "reason": reason}
    else:
        payload["quality"] = None
    return payload


def _story_row(row, *, permitted: bool, editorial_view: NewsEditorialView | None = None) -> dict[str, Any]:
    payload = jsonable_encoder(asdict(row))
    return _attach_annotation(
        payload,
        title=row.title,
        teaser=row.teaser,
        permitted=permitted,
        editorial_view=editorial_view,
    )


def _rights_basis(provenance: _SnapshotProvenance | None) -> dict[str, Any] | None:
    """The shareable receipt identity; owner_ref/product_id/audience stay out."""
    if provenance is None:
        return None
    receipts = provenance.receipts or ((provenance.rights,) if provenance.rights else ())
    basis = [{
        "receipt_id": receipt.receipt_id,
        "source": receipt.source,
        "provider": receipt.provider,
        "effective_at": receipt.effective_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": receipt.expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    } for receipt in receipts]
    return basis[0] if len(basis) == 1 else ({"receipts": basis} if basis else None)


def _snapshot_payload(
    *,
    ticker: str,
    security_id: str,
    snapshot: NewsSnapshot,
    health: Mapping[str, Any],
    permitted: bool,
    flow: dict | None = None,
    provenance: _SnapshotProvenance | None = None,
    editorial_view: NewsEditorialView | None = None,
) -> dict[str, Any]:
    state = _state_from_health(health, row_count=len(snapshot.rows))
    payload: dict[str, Any] = {
        "schema": "ticker_news.snapshot.v1",
        "editorial_policy": EDITORIAL_POLICY_VERSION,
        "ticker": ticker,
        "security_id": security_id,
        "state": state,
        "rows": [_story_row(row, permitted=permitted, editorial_view=editorial_view) for row in snapshot.rows],
        **_view_payload(editorial_view),
        "change_sequence": snapshot.change_sequence,
        "next_cursor": snapshot.next_cursor,
        "has_more": snapshot.has_more,
        "source_health": dict(health),
        "annotations": _annotations_payload(permitted),
        "universe_known_at": (
            None
            if provenance is None or provenance.security is None
            else provenance.security.known_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        ),
        "rights_basis": _rights_basis(provenance),
    }
    if flow is not None:
        payload["flow"] = _apply_flow_coverage(flow, snapshot_state=state)
    return payload


def _changes_payload(
    *,
    ticker: str,
    security_id: str,
    page: ChangePage,
    permitted: bool,
    editorial_view: NewsEditorialView | None = None,
) -> dict[str, Any]:
    rows = [
        _attach_annotation(
            jsonable_encoder(asdict(row)),
            title=row.title,
            teaser=row.teaser,
            permitted=permitted,
            editorial_view=editorial_view,
        )
        for row in page.rows
    ]
    return {
        "schema": "ticker_news.changes.v1",
        "editorial_policy": EDITORIAL_POLICY_VERSION,
        **_view_payload(editorial_view),
        "ticker": ticker,
        "security_id": security_id,
        "rows": rows,
        "next_sequence": page.next_sequence,
        "has_more": page.has_more,
        "annotations": _annotations_payload(permitted),
    }


@router.get("/api/ticker-news/stories/{story_id}")
def ticker_news_story(
    story_id: str,
    ticker: str | None = Query(default=None),
    view: Literal["all", "news", "company"] | None = Query(default=None),
    view_revision: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    _rate_or_429(user)
    rights = _rights_or_503(user)
    editorial = None
    security_id = None
    if view is not None and ticker is None:
        raise _private_error(422, "ticker required for editorial view")
    if ticker is not None:
        _normalized, security_id, editorial = _resolve_reader_view(
            ticker, view, now=datetime.now(timezone.utc), rights=rights,
        )
    _check_view_revision(editorial, view_revision)
    try:
        with _open_reader(editorial) as store:
            detail = (
                store.story(story_id, rights=rights, security_id=security_id)
                if security_id is not None else store.story(story_id, rights=rights)
            )
    except HTTPException:
        raise
    except Exception:
        raise _private_error(503, "ticker news temporarily unavailable") from None
    if detail is None:
        raise _private_error(404, "ticker news story not found")
    permitted = _derivative_permitted_after_rights()
    payload = jsonable_encoder(asdict(detail))
    payload.update(schema="ticker_news.story.v1", editorial_policy=EDITORIAL_POLICY_VERSION,
                   **_view_payload(editorial))
    for encoded, member in zip(payload["members"], detail.members, strict=True):
        _attach_annotation(
            encoded, title=member.title, teaser=member.teaser,
            permitted=permitted, editorial_view=editorial,
        )
    payload["reporting_state"] = (
        payload["members"][0].get("reporting_state", "not_compared")
        if payload["members"] else "not_compared"
    )
    payload["annotations"] = _annotations_payload(permitted)
    return JSONResponse(payload, headers=dict(_PRIVATE_HEADERS))


@router.get("/api/ticker-news/{ticker}/changes")
def ticker_news_changes(
    ticker: str,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    view: Literal["all", "news", "company"] | None = Query(default=None),
    view_revision: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    _rate_or_429(user)
    rights = _rights_or_503(user)
    normalized, security_id, editorial = _resolve_reader_view(
        ticker, view, now=datetime.now(timezone.utc), rights=rights,
    )
    _check_view_revision(editorial, view_revision, resuming=after_sequence > 0)
    try:
        with _open_reader(editorial) as store:
            page = store.projected_changes_for_security(
                security_id, after_sequence=after_sequence, limit=limit, rights=rights,
            )
    except HTTPException:
        raise
    except Exception:
        raise _private_error(503, "ticker news temporarily unavailable") from None
    return JSONResponse(
        _changes_payload(
            ticker=normalized, security_id=security_id, page=page,
            permitted=_derivative_permitted_after_rights(), editorial_view=editorial,
        ),
        headers=dict(_PRIVATE_HEADERS),
    )


@router.get("/api/ticker-news/{ticker}")
def ticker_news_snapshot(
    ticker: str,
    limit: int = Query(default=20, ge=1, le=200),
    cursor: int | None = Query(default=None, ge=1),
    view: Literal["all", "news", "company"] | None = Query(default=None),
    view_revision: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    provenance = _SnapshotProvenance()
    token = _SNAPSHOT_PROVENANCE.set(provenance)
    try:
        _rate_or_429(user)
        rights = _rights_or_503(user)
        normalized, security_id, editorial = _resolve_reader_view(
            ticker, view, now=datetime.now(timezone.utc), rights=rights,
        )
        _check_view_revision(editorial, view_revision, resuming=cursor is not None)
        try:
            with _open_reader(editorial) as store:
                snapshot = store.snapshot(
                    security_id, limit=limit, cursor=cursor, rights=rights,
                )
                flow = _compute_flow(store, security_id, rights=rights) if cursor is None else None
        except HTTPException:
            raise
        except Exception:
            raise _private_error(503, "ticker news temporarily unavailable") from None
        return JSONResponse(
            _snapshot_payload(
                ticker=normalized, security_id=security_id, snapshot=snapshot,
                health=_curated_health(_source_health(), rights),
                permitted=_derivative_permitted_after_rights(),
                flow=flow, provenance=provenance, editorial_view=editorial,
            ),
            headers=dict(_PRIVATE_HEADERS),
        )
    finally:
        _SNAPSHOT_PROVENANCE.reset(token)


def _sse_encode(event: str, payload: Mapping[str, Any]) -> str:
    body = json.dumps(
        jsonable_encoder(dict(payload)),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event}\ndata: {body}\n\n"


def _stream_scope(user: Mapping[str, Any]) -> tuple[NewsReadRights | None, bool | frozenset[str]]:
    """Read display and derivative scope together in one worker context."""
    rights = _rights_for_user(user)
    permitted = _derivative_permitted_after_rights() if rights and rights.allowed_sources else False
    return rights, permitted


async def _sse_events(
    *,
    ticker: str,
    user: Mapping[str, Any],
    after_sequence: int,
    view: str | None = None,
    view_revision: str | None = None,
    poll_seconds: float = 0.1,
    max_cycles: int | None = None,
) -> AsyncIterator[str]:
    initial_rights = (
        await _STREAM_BLOCKING_READER.read(lambda: _rights_or_503(user))
        if view is not None else None
    )
    normalized, security_id, editorial = await _STREAM_BLOCKING_READER.read(
        lambda: _resolve_reader_view(ticker, view, now=datetime.now(timezone.utc), rights=initial_rights),
    )

    def reset(current: NewsEditorialView) -> str:
        return _sse_encode("reset", {
            "schema": "ticker_news.reset.v1", "ticker": normalized,
            **_view_payload(current), "detail": "ticker news view changed; refresh required",
        })

    if editorial is not None and view_revision is not None and editorial.revision != view_revision:
        yield reset(editorial)
        return
    sequence = int(after_sequence)
    cycles = 0
    permitted = False
    next_heartbeat = 0.0
    next_context_check = time.monotonic() + 5.0
    previous_scope = None
    previous_rights = None
    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        scope = await _STREAM_BLOCKING_READER.read(lambda: _stream_scope(user))
        rights = scope[0]
        if (rights is None or not rights.allowed_sources
                or (previous_rights is not None and rights != previous_rights)):
            yield _sse_encode(
                "restricted",
                {"schema": "ticker_news.restricted.v1", "ticker": normalized,
                 "detail": "ticker news rights unavailable"},
            )
            return
        previous_rights = rights
        if previous_scope is not None and scope != previous_scope:
            yield _sse_encode(
                "restricted",
                {"schema": "ticker_news.restricted.v1", "ticker": normalized,
                 "detail": "ticker news permissions changed; refresh required"},
            )
            return
        previous_scope = scope
        permitted = scope[1]

        def read_page():
            with _open_reader(editorial) as store:
                return store.projected_changes_for_security(
                    security_id, after_sequence=sequence, limit=200, rights=rights,
                )
        try:
            page = await _STREAM_CHANGE_READER.read(
                (str(_news_db_path().resolve()), security_id, sequence, rights,
                 editorial.revision if editorial is not None else None), read_page,
            )
            # Re-resolve before delivering a changed batch and at least every five
            # seconds while quiet. No name/profile update is itself a qbus event.
            if editorial is not None and (page.rows or time.monotonic() >= next_context_check):
                _ticker, _security_id, current = await _STREAM_BLOCKING_READER.read(
                    lambda: _resolve_reader_view(ticker, view, now=datetime.now(timezone.utc), rights=rights),
                )
                next_context_check = time.monotonic() + 5.0
                if current is None or current.revision != editorial.revision:
                    yield reset(current or editorial)
                    return
        except HTTPException:
            yield _sse_encode(
                "unavailable",
                {"schema": "ticker_news.unavailable.v1", "ticker": normalized,
                 "detail": "ticker news temporarily unavailable"},
            )
            return
        for row in page.rows:
            if await _STREAM_BLOCKING_READER.read(lambda: _stream_scope(user)) != scope:
                yield _sse_encode(
                    "restricted",
                    {"schema": "ticker_news.restricted.v1", "ticker": normalized,
                     "detail": "ticker news permissions changed; refresh required"},
                )
                return
            sequence = max(sequence, row.sequence)
            payload = _attach_annotation(
                jsonable_encoder(asdict(row)), title=row.title, teaser=row.teaser,
                permitted=permitted, editorial_view=editorial,
            )
            yield _sse_encode(row.kind, payload)
        if not page.rows and time.monotonic() >= next_heartbeat:
            yield ": heartbeat\n\n"
            # Keep quiet streams inside the edge's 15-second idle deadline.
            next_heartbeat = time.monotonic() + 5.0
        sequence = max(sequence, page.next_sequence)
        if poll_seconds > 0 and not page.has_more:
            await asyncio.sleep(poll_seconds)


@router.get("/api/ticker-news/{ticker}/stream")
def ticker_news_stream(
    ticker: str,
    after_sequence: int = Query(default=0, ge=0),
    view: Literal["all", "news", "company"] | None = Query(default=None),
    view_revision: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    user: dict = Depends(require_site_full_user),
) -> StreamingResponse:
    _rate_or_429(user)
    # Preflight access; the generator checks fresh scope on every cycle.
    rights = _rights_or_503(user)
    _normalized, _security_id, editorial = _resolve_reader_view(
        ticker, view, now=datetime.now(timezone.utc), rights=rights,
    )
    if editorial is None and view_revision is not None:
        raise _private_error(422, "editorial view required")
    if editorial is not None and after_sequence > 0 and view_revision is None:
        raise _private_error(422, "editorial view revision required")
    # A revision mismatch is an explicit SSE reset, not an opaque EventSource
    # HTTP failure that could leave the old snapshot indefinitely on screen.
    return StreamingResponse(
        _sse_events(
            ticker=ticker, user=user, after_sequence=after_sequence,
            view=view, view_revision=view_revision,
        ),
        media_type="text/event-stream",
        headers=dict(_STREAM_HEADERS),
    )

_UNKNOWN_PATH_METHODS = ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
_CATCH_ALL_PATHS = frozenset(
    {"/api/ticker-news", "/api/ticker-news/{rest:path}"}
)


@router.get("/api/ticker-news", include_in_schema=False)
def ticker_news_root(
    user: dict = Depends(require_site_full_user),
) -> None:
    """Private terminal answer for the bare ticker-news root.

    Without an exact route here redirect_slashes answers the rootless path
    with a 307 towards /api/ticker-news/, leaking the route family.
    """
    _rate_or_429(user)
    raise _private_error(404, "not found")


@router.get("/api/ticker-news/{rest:path}", include_in_schema=False)
def ticker_news_unmatched(
    rest: str,
    user: dict = Depends(require_site_full_user),
) -> None:
    """Private terminal answer for decoded-slash and other unmatched paths.

    Starlette decodes %2F, so paths like /api/ticker-news/..%2Fx or any
    trailing/multi-segment shape never match a single-segment route; without
    this catch-all the framework default 404 leaks without private headers.
    W12: an empty rest (the bare /api/ticker-news/ root) skips ticker
    validation and answers the private 404 directly instead of a 422.
    W13: an empty leading segment (the /api/ticker-news//x shape) is an
    unknown-path shape too, so only a non-empty head is ticker-validated.
    """
    _rate_or_429(user)
    head = rest.split("/", 1)[0]
    if head != "":
        _safe_ticker_or_422(head)
    raise _private_error(404, "not found")


def _real_route_method_not_allowed(rest: str) -> None:
    """Preserve the router 405 for a non-GET method on a real GET path.

    A non-GET catch-all at the same path would otherwise FULL-match and
    shadow the router's 405+Allow on the real routes; this re-raises the
    same Starlette 405 the router would have raised.  It matches the
    module router's own (prefix-free) route paths, so it also holds when
    the router is included under a prefix.
    """
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in _CATCH_ALL_PATHS:
            continue
        if route.path_regex.match("/api/ticker-news/" + rest):
            raise StarletteHTTPException(
                status_code=405,
                headers={"Allow": ", ".join(route.methods)},
            )
    return None


@router.api_route(
    "/api/ticker-news",
    methods=_UNKNOWN_PATH_METHODS,
    include_in_schema=False,
)
def ticker_news_root_other_methods(
    user: dict = Depends(require_site_full_user),
) -> None:
    """Private terminal answer for non-GET methods on the bare root."""
    _rate_or_429(user)
    raise _private_error(404, "not found")


@router.api_route(
    "/api/ticker-news/{rest:path}",
    methods=_UNKNOWN_PATH_METHODS,
    include_in_schema=False,
)
def ticker_news_unmatched_other_methods(
    rest: str,
    user: dict = Depends(require_site_full_user),
) -> None:
    """Private terminal answer for non-GET methods on unmatched paths.

    W13: the parameter dependency authenticates before the real-route 405
    re-raise (see _real_route_method_not_allowed), so unauthenticated
    callers get the private 401 on every path instead of a 405 that leaks
    which paths are real routes; the 405 re-raise runs before the rate
    limiter, then the chain follows the GET catch-all.
    """
    _real_route_method_not_allowed(rest)
    _rate_or_429(user)
    head = rest.split("/", 1)[0]
    if head != "":
        _safe_ticker_or_422(head)
    raise _private_error(404, "not found")
