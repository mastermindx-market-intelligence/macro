"""Alpaca (Benzinga content) news source adapter for qbus.

Alpaca's news REST API and WebSocket re-distribute Benzinga news, so the
CONTENT SOURCE stays "benzinga" everywhere downstream (store, rights, API,
Terminal); only the TRANSPORT/PROVIDER changes. Items whose publisher is not
Benzinga are dropped before normalization.

Alpaca publishes no removal feed: every item is an article observation and
removals are never delivered on this provider.

This module owns no credentials beyond the injected constructor arguments, no
rights decision, scheduler, runtime lifecycle, or UI. Tests inject HTTP/WS/
clock functions; production activation remains separately gated.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Callable, Mapping

import requests

from collectors.benzinga_news import DeltaBatch
from engine.qbus_news_contract import (
    NewsContractError,
    NewsRevision,
    normalize_news,
)

REST_URL = "https://data.alpaca.markets/v1beta1/news"
STREAM_URL = "wss://stream.data.alpaca.markets/v1beta1/news"
PROVIDER = "alpaca"
CONTENT_SOURCE = "benzinga"
LIMIT_MAX = 50
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
BACKOFF_CAP_SECONDS = 900
_BACKOFF_FLOOR_SECONDS = 60


class AlpacaNewsError(Exception):
    """Sanitized error carrying a stable reason code and nothing else."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"alpaca_news:{code}")


class AlpacaTransportError(AlpacaNewsError):
    def __init__(
        self, code: str, *, retry_after_seconds: int | None = None
    ) -> None:
        self.code = code
        self.retry_after_seconds = retry_after_seconds
        super(AlpacaNewsError, self).__init__(f"alpaca_news:{code}")


class AlpacaProtocolError(AlpacaNewsError):
    pass


class AlpacaStreamError(AlpacaNewsError):
    pass


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


def _rfc3339(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class AlpacaNewsClient:
    """Bounded REST delta client with injected transport for deterministic tests.

    Duck-types the Benzinga delta contract (``fetch_delta`` -> DeltaBatch) so
    ``benzinga_news.catch_up_once`` can drive it unchanged.
    """

    def __init__(
        self,
        *,
        key_id: str,
        secret_key: str,
        http_get: Callable[..., object] = requests.get,
        page_size: int = 50,
        max_pages: int = 100,
        overlap_seconds: int = 3,
        initial_lookback_seconds: int = 300,
        timeout_seconds: int = 20,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not isinstance(key_id, str) or not key_id:
            raise AlpacaProtocolError("missing_key_id")
        if not isinstance(secret_key, str) or not secret_key:
            raise AlpacaProtocolError("missing_secret_key")
        if (
            not isinstance(page_size, int)
            or isinstance(page_size, bool)
            or not 1 <= page_size <= LIMIT_MAX
        ):
            raise AlpacaProtocolError("invalid_page_size")
        if (
            not isinstance(max_pages, int)
            or isinstance(max_pages, bool)
            or not 1 <= max_pages <= 100_001
        ):
            raise AlpacaProtocolError("invalid_max_pages")
        if not isinstance(overlap_seconds, int) or overlap_seconds < 0:
            raise AlpacaProtocolError("invalid_overlap")
        if (
            not isinstance(initial_lookback_seconds, int)
            or initial_lookback_seconds < 0
        ):
            raise AlpacaProtocolError("invalid_initial_lookback")
        # Credentials live ONLY in these private attributes and in request
        # headers; never in params, URLs, exceptions, logs, or repr.
        self._key_id = key_id
        self._secret_key = secret_key
        self.http_get = http_get
        self.page_size = page_size
        self.max_pages = max_pages
        self.overlap_seconds = overlap_seconds
        self.initial_lookback_seconds = initial_lookback_seconds
        self.timeout_seconds = timeout_seconds
        self.sleep = sleep
        self.clock = clock
        self._backoff_step = 0.0
        self._backoff_until: datetime | None = None

    def __repr__(self) -> str:  # never a credential
        return f"AlpacaNewsClient(page_size={self.page_size})"

    def _arm_backoff(self, retry_after_header: int | None) -> int:
        step = min(
            max(self._backoff_step * 2.0, float(_BACKOFF_FLOOR_SECONDS)),
            float(BACKOFF_CAP_SECONDS),
        )
        self._backoff_step = step
        delay = retry_after_header if retry_after_header is not None else step
        delay = min(delay, BACKOFF_CAP_SECONDS)
        self._backoff_until = self.clock() + timedelta(seconds=delay)
        return int(delay)

    def _get(self, params: dict) -> object:
        try:
            response = self.http_get(
                REST_URL,
                params=params,
                headers={
                    "accept": "application/json",
                    "APCA-API-KEY-ID": self._key_id,
                    "APCA-API-SECRET-KEY": self._secret_key,
                },
                timeout=self.timeout_seconds,
            )
            status = int(getattr(response, "status_code", 0) or 0)
            if status == 429:
                delay = self._arm_backoff(
                    _retry_after(getattr(response, "headers", None))
                )
                raise AlpacaTransportError(
                    "http_429", retry_after_seconds=delay
                )
            if status >= 400:
                raise AlpacaTransportError(
                    f"http_{status}",
                    retry_after_seconds=_retry_after(
                        getattr(response, "headers", None)
                    ),
                )
            raiser = getattr(response, "raise_for_status", None)
            if callable(raiser):
                raiser()
            # A successful page resets the 429 ladder.
            self._backoff_step = 0.0
            self._backoff_until = None
            return response
        except AlpacaTransportError:
            raise
        except Exception as exc:  # noqa: BLE001
            # No exception text escapes: the raised error carries only the
            # exception class name, and `from None` drops the chained
            # original (whose message could hold a header secret).
            raise AlpacaTransportError(
                f"transport_{type(exc).__name__.lower()}"
            ) from None

    def _news_page(
        self, *, start_iso: str, end_iso: str, page_token: str | None
    ) -> tuple[tuple[NewsRevision, ...], str | None]:
        params: dict[str, object] = {
            "start": start_iso,
            "end": end_iso,
            "sort": "asc",
            "limit": self.page_size,
            "include_content": "false",
        }
        if page_token is not None:
            params["page_token"] = page_token
        response = self._get(params)

        headers = getattr(response, "headers", None) or {}
        try:
            content_length = int(str(headers.get("Content-Length", "")))
        except (TypeError, ValueError):
            content_length = -1
        if content_length > MAX_RESPONSE_BYTES:
            raise AlpacaProtocolError("response_too_large")
        body = getattr(response, "content", None)
        if body is not None and len(body) > MAX_RESPONSE_BYTES:
            raise AlpacaProtocolError("response_too_large")

        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            raise AlpacaProtocolError("news_page_invalid_json") from None
        if not isinstance(payload, Mapping):
            raise AlpacaProtocolError("news_page_not_object")
        news = payload.get("news")
        if not isinstance(news, list):
            raise AlpacaProtocolError("news_not_list")
        next_token = payload.get("next_page_token")
        if next_token is not None and not isinstance(next_token, str):
            raise AlpacaProtocolError("next_page_token_invalid")

        received_at = self.clock()
        out: list[NewsRevision] = []
        for item in news:
            if not isinstance(item, Mapping):
                raise AlpacaProtocolError("news_item_invalid")
            if str(item.get("source", "")).strip().lower() != CONTENT_SOURCE:
                continue  # Alpaca also serves other publishers; only Benzinga flows
            try:
                out.append(
                    normalize_news(
                        item,
                        transport="alpaca_rest",
                        received_at=received_at,
                    )
                )
            except NewsContractError as exc:
                raise AlpacaProtocolError(f"news_item_{exc.code}") from None
        return tuple(out), (next_token if next_token else None)

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
            raise AlpacaProtocolError("observed_at_not_aware")
        observed = observed_at.astimezone(timezone.utc)
        if cursor_epoch is not None and (
            not isinstance(cursor_epoch, int)
            or isinstance(cursor_epoch, bool)
            or cursor_epoch < 0
        ):
            raise AlpacaProtocolError("invalid_cursor")

        now = self.clock()
        if self._backoff_until is not None and now < self._backoff_until:
            raise AlpacaTransportError("backoff_active")

        base = (
            cursor_epoch
            if cursor_epoch is not None
            else max(
                0, int(observed.timestamp()) - self.initial_lookback_seconds
            )
        )
        query_since = max(0, base - self.overlap_seconds)
        start_iso = _rfc3339(query_since)
        end_iso = _rfc3339(int(observed.timestamp()))

        all_rows: list[NewsRevision] = []
        pages = 0
        exhausted_budget = False
        token: str | None = None
        for page in range(self.max_pages):
            rows, next_token = self._news_page(
                start_iso=start_iso,
                end_iso=end_iso,
                page_token=token,
            )
            pages += 1
            all_rows.extend(rows)
            token = next_token
            if token is None:
                break
            if page + 1 == self.max_pages:
                exhausted_budget = True
        gap = exhausted_budget and token is not None
        reasons: list[str] = []
        if gap:
            reasons.append("news_page_budget_exhausted")
        next_cursor = base if gap else int(observed.timestamp())
        return DeltaBatch(
            revisions=tuple(all_rows),
            query_since_epoch=query_since,
            next_cursor_epoch=next_cursor,
            gap_unresolved=gap,
            hold_reasons=tuple(reasons),
            news_pages=pages,
            removed_pages=0,
        )


def _decode_frame_text(raw: str | bytes) -> str:
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise AlpacaStreamError("stream_non_utf8") from None
    if not isinstance(raw, str):
        raise AlpacaStreamError("stream_invalid_type")
    return raw


def normalize_stream_frames(
    raw: str | bytes,
    *,
    received_at: datetime,
) -> list[NewsRevision]:
    """Normalize one Alpaca WS frame (a JSON ARRAY of messages) into revisions."""
    text = _decode_frame_text(raw)
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        raise AlpacaStreamError("stream_invalid_json") from None
    if not isinstance(payload, list):
        raise AlpacaStreamError("stream_not_array")
    out: list[NewsRevision] = []
    for element in payload:
        if not isinstance(element, Mapping):
            raise AlpacaStreamError("stream_item_not_object")
        kind = element.get("T")
        if kind == "n":
            if (
                str(element.get("source", "")).strip().lower()
                != CONTENT_SOURCE
            ):
                continue
            try:
                out.append(
                    normalize_news(
                        element,
                        transport="alpaca_ws",
                        received_at=received_at,
                    )
                )
            except NewsContractError as exc:
                raise AlpacaStreamError(f"stream_{exc.code}") from None
        elif kind == "error":
            code = element.get("code")
            if isinstance(code, bool) or not isinstance(code, int):
                code = "unknown"
            # Never the msg: server text is untrusted and may echo input.
            raise AlpacaStreamError(f"stream_error_{code}")
        # "success", "subscription" and any other T are ignored.
    return out


def _handshake_messages(raw: str | bytes) -> list[Mapping[str, object]]:
    text = _decode_frame_text(raw)
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        raise AlpacaStreamError("stream_invalid_json") from None
    if not isinstance(payload, list):
        raise AlpacaStreamError("stream_not_array")
    for element in payload:
        if not isinstance(element, Mapping):
            raise AlpacaStreamError("stream_item_not_object")
    return payload


def stream_handshake(
    ws,
    *,
    key_id: str,
    secret_key: str,
    recv: Callable[[], str | bytes] | None = None,
    max_frames: int = 8,
) -> None:
    """Drive the Alpaca WS auth dance: connected -> auth -> subscribe.

    Credentials appear ONLY inside the two ws.send JSON payloads; never in an
    exception, log, or return value.
    """
    if recv is None:
        def _default_recv() -> str | bytes:
            return ws.recv(timeout=10.0)

        recv = _default_recv

    connected = False
    authenticated = False
    for _ in range(max_frames):
        try:
            frame = recv()
        except TimeoutError:
            raise AlpacaStreamError("stream_handshake_timeout") from None
        subscribed = False
        for message in _handshake_messages(frame):
            if message.get("T") == "error":
                code = message.get("code")
                if isinstance(code, bool) or not isinstance(code, int):
                    code = "unknown"
                raise AlpacaStreamError(f"stream_auth_error_{code}")
            if not connected:
                if (
                    message.get("T") == "success"
                    and message.get("msg") == "connected"
                ):
                    connected = True
                    ws.send(
                        json.dumps(
                            {
                                "action": "auth",
                                "key": key_id,
                                "secret": secret_key,
                            }
                        )
                    )
            elif not authenticated:
                if (
                    message.get("T") == "success"
                    and message.get("msg") == "authenticated"
                ):
                    authenticated = True
                    ws.send(
                        json.dumps({"action": "subscribe", "news": ["*"]})
                    )
            elif message.get("T") == "subscription":
                subscribed = True
        if subscribed:
            return
    raise AlpacaStreamError("stream_handshake_budget")
