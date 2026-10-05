"""Massive-distributed Benzinga news supplement.

Massive is another delivery route for the Benzinga editorial source, not an
independent corroborating source. The documented v2 endpoint exposes pagination
but no correction/removal cursor equivalent to direct Benzinga, so every result
from this module is explicitly supplemental and correction-incomplete.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from collectors.base import redact_secrets
from engine.qbus_news_contract import NewsContractError, NewsRevision, normalize_news

BASE_URL = "https://api.massive.com/benzinga/v2/news"
_ALLOWED_SCHEME = "https"
_ALLOWED_HOST = "api.massive.com"
_ALLOWED_PATH = "/benzinga/v2/news"


class MassiveError(RuntimeError):
    pass


class MassiveProtocolError(MassiveError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"massive_benzinga_news:{code}")


class MassiveTransportError(MassiveError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"massive_benzinga_news:{code}")


@dataclass(frozen=True, slots=True)
class MassiveBatch:
    revisions: tuple[NewsRevision, ...]
    pages: int
    request_ids: tuple[str, ...]
    next_url: str | None
    gap_unresolved: bool
    hold_reasons: tuple[str, ...]
    correction_complete: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_next_url(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise MassiveProtocolError("unsafe_next_url")
    try:
        parsed = urlsplit(raw.strip())
    except ValueError:
        raise MassiveProtocolError("unsafe_next_url") from None
    if (
        parsed.scheme.lower() != _ALLOWED_SCHEME
        or (parsed.hostname or "").lower() != _ALLOWED_HOST
        or parsed.path != _ALLOWED_PATH
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
        or parsed.port not in (None, 443)
    ):
        raise MassiveProtocolError("unsafe_next_url")
    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=False)
    except ValueError:
        raise MassiveProtocolError("unsafe_next_url") from None
    # A vendor-returned URL never gets to select the credential. The locally
    # bound apiKey is supplied separately on every request.
    kept = [(k, v) for k, v in pairs if k.lower() != "apikey"]
    query = urlencode(kept, doseq=True)
    return urlunsplit((_ALLOWED_SCHEME, _ALLOWED_HOST, _ALLOWED_PATH, query, ""))


class MassiveBenzingaNewsClient:
    def __init__(
        self,
        *,
        api_key: str,
        http_get: Callable[..., object] = requests.get,
        limit: int = 100,
        max_pages: int = 20,
        timeout_seconds: int = 20,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not isinstance(api_key, str) or not api_key:
            raise MassiveProtocolError("missing_api_key")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50_000:
            raise MassiveProtocolError("invalid_limit")
        if not isinstance(max_pages, int) or isinstance(max_pages, bool) or not 1 <= max_pages <= 10_000:
            raise MassiveProtocolError("invalid_max_pages")
        self.api_key = api_key
        self.http_get = http_get
        self.limit = limit
        self.max_pages = max_pages
        self.timeout_seconds = timeout_seconds
        self.clock = clock

    def _get(self, url: str, *, first_page: bool) -> object:
        params = {"apiKey": self.api_key}
        if first_page:
            params.update({"limit": self.limit, "sort": "published.desc"})
        try:
            response = self.http_get(
                url,
                params=params,
                headers={"accept": "application/json"},
                timeout=self.timeout_seconds,
            )
            status = int(getattr(response, "status_code", 0) or 0)
            if status >= 400:
                raise MassiveTransportError(f"http_{status}")
            raiser = getattr(response, "raise_for_status", None)
            if callable(raiser):
                raiser()
            return response
        except MassiveTransportError:
            raise
        except Exception as exc:  # noqa: BLE001
            redact_secrets(str(exc))
            raise MassiveTransportError(
                f"transport_{type(exc).__name__.lower()}"
            ) from None

    def _parse_page(
        self,
        response: object,
    ) -> tuple[tuple[NewsRevision, ...], str | None, str]:
        try:
            payload = response.json()
        except Exception:  # noqa: BLE001
            raise MassiveProtocolError("invalid_json") from None
        if not isinstance(payload, Mapping):
            raise MassiveProtocolError("page_not_object")
        if payload.get("status") != "OK":
            raise MassiveProtocolError("status_not_ok")
        results = payload.get("results")
        if not isinstance(results, list):
            raise MassiveProtocolError("results_not_array")
        received_at = self.clock()
        out: list[NewsRevision] = []
        for item in results:
            if not isinstance(item, Mapping):
                raise MassiveProtocolError("result_not_object")
            try:
                out.append(
                    normalize_news(
                        item,
                        transport="massive_benzinga_v2",
                        received_at=received_at,
                    )
                )
            except NewsContractError as exc:
                raise MassiveProtocolError(
                    f"result_{exc.code}"
                ) from None
        request_id_raw = payload.get("request_id")
        request_id = "" if request_id_raw is None else str(request_id_raw)
        next_raw = payload.get("next_url")
        next_url = None
        if next_raw not in (None, ""):
            next_url = _safe_next_url(next_raw)
        return tuple(out), next_url, request_id

    def fetch_latest(self) -> MassiveBatch:
        revisions: list[NewsRevision] = []
        request_ids: list[str] = []
        url = BASE_URL
        next_url: str | None = None
        pages = 0
        for index in range(self.max_pages):
            response = self._get(url, first_page=index == 0)
            rows, next_url, request_id = self._parse_page(response)
            revisions.extend(rows)
            request_ids.append(request_id)
            pages += 1
            if next_url is None:
                return MassiveBatch(
                    revisions=tuple(revisions),
                    pages=pages,
                    request_ids=tuple(request_ids),
                    next_url=None,
                    gap_unresolved=False,
                    hold_reasons=(),
                )
            if index + 1 == self.max_pages:
                break
            url = next_url

        return MassiveBatch(
            revisions=tuple(revisions),
            pages=pages,
            request_ids=tuple(request_ids),
            next_url=next_url,
            gap_unresolved=True,
            hold_reasons=("page_budget_exhausted",),
        )