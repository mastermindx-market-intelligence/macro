"""Direct Benzinga live-news source adapter.

This module is deliberately split between:
- REST delta catch-up (/api/v2/news + /api/v2/news-removed);
- WebSocket frame normalization; and
- canonical-security routing into the qbus live-news store.

It owns no credentials, rights decisions, scheduler, runtime lifecycle, or UI.
Tests inject HTTP/clock functions; production activation remains separately gated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Callable, Mapping

import requests

from collectors.base import redact_secrets
from engine.qbus_news_contract import (
    NewsContractError,
    NewsRevision,
    normalize_news,
)
from engine.qbus_news_store import CommitReceipt, NewsStore, RoutedRevision
from engine.qbus_news_universe import UniverseQualification

NEWS_URL = "https://api.benzinga.com/api/v2/news"
REMOVED_URL = "https://api.benzinga.com/api/v2/news-removed"
STREAM_URL = "wss://api.benzinga.com/api/v1/news/stream"


class BenzingaError(RuntimeError):
    pass


class BenzingaProtocolError(BenzingaError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"benzinga_news:{code}")


class BenzingaTransportError(BenzingaError):
    def __init__(self, code: str, *, retry_after_seconds: int | None = None) -> None:
        self.code = code
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"benzinga_news:{code}")


class BenzingaRoutingError(BenzingaError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"benzinga_news:{code}")


@dataclass(frozen=True, slots=True)
class DeltaBatch:
    revisions: tuple[NewsRevision, ...]
    query_since_epoch: int
    next_cursor_epoch: int
    gap_unresolved: bool
    hold_reasons: tuple[str, ...]
    news_pages: int
    removed_pages: int


@dataclass(frozen=True, slots=True)
class CatchUpResult:
    committed: bool
    gap_unresolved: bool
    hold_reasons: tuple[str, ...]
    receipt: CommitReceipt | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _retry_after(headers: Mapping[str, object] | None) -> int | None:
    if not headers:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        raw = headers.get("retry-after")
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


class BenzingaNewsClient:
    """Bounded REST delta client with injected transport for deterministic tests."""

    def __init__(
        self,
        *,
        token: str,
        http_get: Callable[..., object] = requests.get,
        page_size: int = 100,
        max_pages: int = 100,
        overlap_seconds: int = 3,
        initial_lookback_seconds: int = 300,
        timeout_seconds: int = 20,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not isinstance(token, str) or not token:
            raise BenzingaProtocolError("missing_token")
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= 100:
            raise BenzingaProtocolError("invalid_page_size")
        if not isinstance(max_pages, int) or isinstance(max_pages, bool) or not 1 <= max_pages <= 100_001:
            raise BenzingaProtocolError("invalid_max_pages")
        if not isinstance(overlap_seconds, int) or overlap_seconds < 0:
            raise BenzingaProtocolError("invalid_overlap")
        if not isinstance(initial_lookback_seconds, int) or initial_lookback_seconds < 0:
            raise BenzingaProtocolError("invalid_initial_lookback")
        self.token = token
        self.http_get = http_get
        self.page_size = page_size
        self.max_pages = max_pages
        self.overlap_seconds = overlap_seconds
        self.initial_lookback_seconds = initial_lookback_seconds
        self.timeout_seconds = timeout_seconds
        self.sleep = sleep
        self.clock = clock

    def _get(self, url: str, *, params: dict) -> object:
        try:
            response = self.http_get(
                url,
                params=params,
                headers={"accept": "application/json"},
                timeout=self.timeout_seconds,
            )
            status = int(getattr(response, "status_code", 0) or 0)
            if status >= 400:
                raise BenzingaTransportError(
                    f"http_{status}",
                    retry_after_seconds=_retry_after(
                        getattr(response, "headers", None)
                    ),
                )
            raiser = getattr(response, "raise_for_status", None)
            if callable(raiser):
                raiser()
            return response
        except BenzingaTransportError:
            raise
        except Exception as exc:  # noqa: BLE001
            # Render and discard sanitized text so query/header secrets never escape.
            redact_secrets(str(exc))
            raise BenzingaTransportError(
                f"transport_{type(exc).__name__.lower()}"
            ) from None

    def _news_page(
        self, *, updated_since: int, page: int
    ) -> tuple[NewsRevision, ...]:
        response = self._get(
            NEWS_URL,
            params={
                "token": self.token,
                "updatedSince": updated_since,
                "sort": "updated:asc",
                "page": page,
                "pageSize": self.page_size,
                "displayOutput": "headline",
            },
        )
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            raise BenzingaProtocolError("news_page_invalid_json") from None
        if not isinstance(payload, list):
            raise BenzingaProtocolError("news_page_not_array")
        if len(payload) > self.page_size:
            raise BenzingaProtocolError("news_page_oversized")

        received_at = self.clock()
        out: list[NewsRevision] = []
        for item in payload:
            if not isinstance(item, Mapping):
                raise BenzingaProtocolError("news_item_invalid")
            try:
                out.append(
                    normalize_news(
                        item,
                        transport="benzinga_rest",
                        received_at=received_at,
                    )
                )
            except NewsContractError as exc:
                raise BenzingaProtocolError(
                    f"news_item_{exc.code}"
                ) from None
        return tuple(out)

    def _removed_page(
        self, *, updated_since: int, page: int
    ) -> tuple[NewsRevision, ...]:
        response = self._get(
            REMOVED_URL,
            params={
                "token": self.token,
                "updatedSince": updated_since,
                "page": page,
                "pageSize": self.page_size,
            },
        )
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            raise BenzingaProtocolError("removed_page_invalid_json") from None
        if not isinstance(payload, Mapping):
            raise BenzingaProtocolError("removed_page_not_object")
        items = payload.get("items")
        # Older vendor examples use the "removed" container. Accept only these
        # two known shapes rather than arbitrary mappings.
        if items is None:
            items = payload.get("removed")
        if not isinstance(items, list):
            raise BenzingaProtocolError("removed_items_not_array")
        if len(items) > self.page_size:
            raise BenzingaProtocolError("removed_page_oversized")

        received_at = self.clock()
        out: list[NewsRevision] = []
        for item in items:
            if not isinstance(item, Mapping):
                raise BenzingaProtocolError("removed_item_invalid")
            if item.get("id") in (None, "") or item.get("updated") in (None, ""):
                raise BenzingaProtocolError("removed_item_invalid")
            normalized = {
                "id": item.get("id"),
                "action": "removed",
                "updated": item.get("updated"),
            }
            try:
                out.append(
                    normalize_news(
                        normalized,
                        transport="benzinga_rest",
                        received_at=received_at,
                    )
                )
            except NewsContractError:
                raise BenzingaProtocolError("removed_item_invalid") from None
        return tuple(out)

    def _page_family(
        self,
        *,
        family: str,
        updated_since: int,
    ) -> tuple[tuple[NewsRevision, ...], int, bool]:
        all_rows: list[NewsRevision] = []
        pages = 0
        exhausted_budget = False
        for page in range(self.max_pages):
            if family == "news":
                rows = self._news_page(
                    updated_since=updated_since, page=page
                )
            else:
                rows = self._removed_page(
                    updated_since=updated_since, page=page
                )
            pages += 1
            all_rows.extend(rows)
            if len(rows) < self.page_size:
                break
            if page + 1 == self.max_pages:
                exhausted_budget = True
        return tuple(all_rows), pages, exhausted_budget

    def fetch_delta(
        self,
        *,
        cursor_epoch: int | None,
        observed_at: datetime,
    ) -> DeltaBatch:
        if (
            not isinstance(observed_at, datetime)
            or observed_at.tzinfo is None
            or observed_at.utcoffset() is None
        ):
            raise BenzingaProtocolError("observed_at_not_aware")
        observed = observed_at.astimezone(timezone.utc)
        if cursor_epoch is not None and (
            not isinstance(cursor_epoch, int)
            or isinstance(cursor_epoch, bool)
            or cursor_epoch < 0
        ):
            raise BenzingaProtocolError("invalid_cursor")

        base = (
            cursor_epoch
            if cursor_epoch is not None
            else max(0, int(observed.timestamp()) - self.initial_lookback_seconds)
        )
        query_since = max(0, base - self.overlap_seconds)

        news, news_pages, news_gap = self._page_family(
            family="news", updated_since=query_since
        )
        removed, removed_pages, removed_gap = self._page_family(
            family="removed", updated_since=query_since
        )
        reasons: list[str] = []
        if news_gap:
            reasons.append("news_page_budget_exhausted")
        if removed_gap:
            reasons.append("removed_page_budget_exhausted")
        gap = bool(reasons)
        next_cursor = base if gap else int(observed.timestamp())
        return DeltaBatch(
            revisions=news + removed,
            query_since_epoch=query_since,
            next_cursor_epoch=next_cursor,
            gap_unresolved=gap,
            hold_reasons=tuple(reasons),
            news_pages=news_pages,
            removed_pages=removed_pages,
        )


def normalize_stream_frame(
    raw: str | bytes,
    *,
    received_at: datetime,
) -> NewsRevision | None:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise BenzingaProtocolError("stream_non_utf8") from None
    if not isinstance(raw, str):
        raise BenzingaProtocolError("stream_invalid_type")
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        raise BenzingaProtocolError("stream_invalid_json") from None
    if not isinstance(payload, Mapping):
        raise BenzingaProtocolError("stream_not_object")
    if payload.get("kind") != "news":
        return None
    try:
        return normalize_news(
            payload,
            transport="benzinga_ws",
            received_at=received_at,
        )
    except NewsContractError as exc:
        raise BenzingaProtocolError(f"stream_{exc.code}") from None


def route_revision(
    revision: NewsRevision,
    universe: UniverseQualification,
) -> RoutedRevision:
    if universe.status != "qualified":
        raise BenzingaRoutingError("universe_not_qualified")
    aliases = {b.alias: b.security_id for b in universe.alias_bindings}
    security_ids: list[str] = []
    seen: set[str] = set()
    for ticker in revision.provider_tickers:
        sid = aliases.get(ticker)
        if sid is not None and sid not in seen:
            seen.add(sid)
            security_ids.append(sid)
    return RoutedRevision(
        revision=revision,
        security_ids=tuple(security_ids),
        universe_revision=universe.revision,
    )


def _parse_store_cursor(cursor: str | None) -> int | None:
    if cursor is None:
        return None
    try:
        value = int(cursor)
    except (TypeError, ValueError):
        raise BenzingaProtocolError("store_cursor_invalid") from None
    if value < 0:
        raise BenzingaProtocolError("store_cursor_invalid")
    return value


def catch_up_once(
    *,
    client: BenzingaNewsClient,
    store: NewsStore,
    universe: UniverseQualification,
    observed_at: datetime,
) -> CatchUpResult:
    if universe.status != "qualified":
        raise BenzingaRoutingError("universe_not_qualified")
    current_text = store.current_cursor()
    current_epoch = _parse_store_cursor(current_text)
    batch = client.fetch_delta(
        cursor_epoch=current_epoch,
        observed_at=observed_at,
    )
    if batch.gap_unresolved:
        return CatchUpResult(
            committed=False,
            gap_unresolved=True,
            hold_reasons=batch.hold_reasons,
            receipt=None,
        )
    routed = tuple(route_revision(r, universe) for r in batch.revisions)
    receipt = store.commit(
        routed,
        expected_cursor=current_text,
        next_cursor=str(batch.next_cursor_epoch),
    )
    return CatchUpResult(
        committed=True,
        gap_unresolved=False,
        hold_reasons=(),
        receipt=receipt,
    )