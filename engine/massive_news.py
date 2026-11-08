"""Massive general-news HTTP adapter (NEW, isolated).

Pull-only polling of Massive's reference news endpoint into
``engine.qbus_news_contract.NewsRevision`` objects. Read-only with respect to
company repos; no provider calls happen unless ``poll`` is invoked with a
non-empty ``allowed_publishers``.

Hard rules enforced here:

* Bearer token travels only in the ``Authorization`` header -- never in a URL,
  query parameter, or error message.
* Fixed endpoint ``https://api.massive.com/v2/reference/news``; pagination via
  provider ``next_url`` is validated strictly (https, allow-listed host,
  port 443/None, exact path, no credentials/fragment/auth query params) and is
  never followed through redirects (``allow_redirects=False``).
* Publisher identity comes from ``publisher.homepage_url``: lowercased
  hostname, leading ``www.`` stripped, never any port or userinfo. Allow-list
  membership is exact on that hostname (no suffix/wildcard matching); rows
  whose publisher is not allowed are skipped.
* Fail closed: any malformed response or row raises :class:`MassivePollError`
  with a fixed ``code``; a watermark is only safe to advance when ``complete``
  is True. Exception text is never stringified into error messages (it can
  carry the token).
* ``through`` is the request clock captured before the first call -- a safe
  upper bound -- never the latest observed publication timestamp.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import parse_qsl, urlsplit

from engine.qbus_news_contract import NewsRevision, normalize_massive_news

__all__ = ["MassiveNewsClient", "MassivePollError", "PollBatch"]

_UTC = _dt.timezone.utc

_ENDPOINT = "https://api.massive.com/v2/reference/news"
_NEXT_HOSTS = frozenset({"api.massive.com", "api.polygon.io"})
_NEXT_PATH = "/v2/reference/news"
_PAGE_LIMIT = 1000
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024

# Query parameter names that must never appear on a followed next_url
# (case-insensitive).
_AUTH_QUERY_KEYS = frozenset(
    {"apikey", "api_key", "key", "token", "access_token", "auth", "bearer", "password"}
)

# Fixed, sanitized failure codes. Never include provider text, exception text,
# URLs, or the token in these.
CODE_TRANSPORT = "MASSIVE_TRANSPORT_ERROR"
CODE_HTTP = "MASSIVE_HTTP_ERROR"
CODE_AUTH = "MASSIVE_AUTH_REJECTED"
CODE_RATE_LIMITED = "MASSIVE_RATE_LIMITED"
CODE_MALFORMED_RESPONSE = "MASSIVE_MALFORMED_RESPONSE"
CODE_PAYLOAD_TOO_LARGE = "MASSIVE_PAYLOAD_TOO_LARGE"
CODE_ROWS_TOO_MANY = "MASSIVE_ROWS_TOO_MANY"
CODE_INVALID_NEXT_URL = "MASSIVE_INVALID_NEXT_URL"
CODE_PAGINATION_LOOP = "MASSIVE_PAGINATION_LOOP"
CODE_ROW_MALFORMED = "MASSIVE_ROW_MALFORMED"


class MassivePollError(Exception):
    """Fail-closed poll failure with a fixed, sanitized ``code``."""

    def __init__(self, code: str, detail: str = "") -> None:
        # ``detail`` must be caller-supplied static text; provider/exception
        # text is never interpolated here.
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class PollBatch:
    revisions: tuple[NewsRevision, ...]
    through: _dt.datetime
    complete: bool
    pages: int
    next_url: str | None = None


def _utc_clock() -> _dt.datetime:
    return _dt.datetime.now(_UTC)


def _require_aware(value: _dt.datetime, name: str) -> _dt.datetime:
    if not isinstance(value, _dt.datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(_UTC)


def _iso_utc(value: _dt.datetime) -> str:
    return _require_aware(value, "since").astimezone(_UTC).isoformat()


def _publisher_identity(homepage_url: Any, allowed: frozenset[str]) -> str | None:
    """Exact-match hostname identity for a publisher, or None to skip.

    Normalization is lowercase + leading ``www.`` strip; port and userinfo are
    never part of the identity (``urlsplit.hostname`` drops both). Membership
    is exact against the allow-list.
    """
    if not isinstance(homepage_url, str) or not homepage_url.strip():
        return None
    try:
        hostname = urlsplit(homepage_url).hostname
    except ValueError:
        return None
    if not hostname:
        return None
    raw = hostname.lower()
    candidates = (raw[4:] if raw.startswith("www.") else raw, raw)
    for candidate in candidates:
        if candidate in allowed:
            return candidate
    return None


def _validate_next_url(next_url: str) -> str:
    """Strict gate for a provider-supplied pagination URL. Fails closed."""
    try:
        parts = urlsplit(next_url)
    except ValueError:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "unparsable next_url") from None

    if parts.scheme != "https":
        raise MassivePollError(CODE_INVALID_NEXT_URL, "scheme must be https")
    if parts.username is not None or parts.password is not None:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "userinfo not allowed")
    if parts.fragment:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "fragment not allowed")

    hostname = parts.hostname  # lowercased by urlsplit; None when absent
    if hostname not in _NEXT_HOSTS:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "host not allowed")

    try:
        port = parts.port  # raises ValueError for out-of-range ports
    except ValueError:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "invalid port") from None
    if port is not None and port != 443:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "port must be 443 or default")

    if parts.path != _NEXT_PATH:
        raise MassivePollError(CODE_INVALID_NEXT_URL, "path not allowed")

    query = parts.query
    if query:
        try:
            pairs = [(k.lower(), v) for k, v in parse_qsl(query, keep_blank_values=True, max_num_fields=32)]
        except ValueError:
            raise MassivePollError(CODE_INVALID_NEXT_URL, "unparsable query") from None
        if any(name in _AUTH_QUERY_KEYS for name, _ in pairs):
            raise MassivePollError(CODE_INVALID_NEXT_URL, "auth query parameter present")
    # Rebuild without any normalization surprises; only scheme://netloc/path?query survive.
    host_part = hostname if port in (None, 443) else f"{hostname}:{port}"
    return f"https://{host_part}{parts.path}" + (f"?{query}" if query else "")


def _classify_status(status: int) -> str:
    if status in (401, 403):
        return CODE_AUTH
    if status == 429:
        return CODE_RATE_LIMITED
    return CODE_HTTP


class MassiveNewsClient:
    """Pull-only Massive reference-news client with an injected session/clock."""

    def __init__(
        self,
        token: str,
        session: Any = None,
        clock: Callable[[], _dt.datetime] = _utc_clock,
    ) -> None:
        if not isinstance(token, str) or not token.strip():
            raise ValueError("token must be a non-empty string")
        self._token = token
        self._session = session
        self._clock = clock

    def _session_or_default(self) -> Any:
        if self._session is None:
            import requests  # imported lazily; no import-time IO / hard dependency

            self._session = requests.Session()
        return self._session

    def _fetch(self, url: str, params: Mapping[str, Any] | None, timeout_seconds: float) -> tuple[int, bytes]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        try:
            response = self._session_or_default().get(
                url,
                params=dict(params) if params else None,
                headers=headers,
                timeout=timeout_seconds,
                allow_redirects=False, stream=True,
            )
        except Exception:
            # Never stringify: requests exceptions can embed the authenticated URL.
            raise MassivePollError(CODE_TRANSPORT, "request failed") from None

        status = getattr(response, "status_code", None)
        if not isinstance(status, int):
            raise MassivePollError(CODE_MALFORMED_RESPONSE, "missing status code")
        try:
            content = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > _MAX_RESPONSE_BYTES:
                    raise MassivePollError(CODE_PAYLOAD_TOO_LARGE, "response exceeds size bound")
            return status, bytes(content)
        except MassivePollError:
            raise
        except Exception:
            raise MassivePollError(CODE_TRANSPORT, "response read failed") from None
        finally:
            response.close()

    def poll(
        self,
        *,
        since: _dt.datetime,
        allowed_publishers: frozenset[str],
        max_pages: int = 10,
        timeout_seconds: float = 5,
        next_url: str | None = None,
        through: _dt.datetime | None = None,
    ) -> PollBatch:
        _require_aware(since, "since")
        if not isinstance(allowed_publishers, frozenset):
            allowed_publishers = frozenset(allowed_publishers)
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 100:
            raise ValueError("max_pages must be between 1 and 100")
        if not 0 < timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0 and 30")

        # Safe upper bound captured BEFORE the first request; never a
        # publication timestamp projected into the future.
        now = _require_aware(self._clock(), "clock")
        through = now if through is None else _require_aware(through, "through")
        if through > now or since > through:
            raise ValueError("invalid polling window")

        if not allowed_publishers:
            # Empty allow-list: no network call, nothing to admit.
            return PollBatch(revisions=(), through=through, complete=True, pages=0)

        revisions: list[NewsRevision] = []
        seen_urls: set[str] = set()
        url: str | None = _validate_next_url(next_url) if next_url is not None else _ENDPOINT
        params: dict[str, Any] | None = {
            "published_utc.gte": _iso_utc(since),
            "published_utc.lte": _iso_utc(through),
            "sort": "published_utc",
            "order": "asc",
            "limit": _PAGE_LIMIT,
        }
        if next_url is not None:
            params = None
        pages = 0
        complete = False

        while url is not None:
            if pages >= max_pages:
                # Saturated page cap with more data advertised: incomplete.
                complete = False
                break

            url = _validate_next_url(url)
            if url in seen_urls:
                raise MassivePollError(CODE_PAGINATION_LOOP, "repeated next_url")
            seen_urls.add(url)

            status, content = self._fetch(url, params, timeout_seconds)
            received_at = _require_aware(self._clock(), "clock")
            params = None  # query params only on the fixed first-page endpoint
            pages += 1

            if status != 200:
                raise MassivePollError(_classify_status(status), "non-200 status")
            if len(content) > _MAX_RESPONSE_BYTES:
                raise MassivePollError(CODE_PAYLOAD_TOO_LARGE, "response exceeds size bound")

            try:
                payload = json.loads(content)
            except (ValueError, UnicodeDecodeError):
                raise MassivePollError(CODE_MALFORMED_RESPONSE, "unparsable JSON") from None
            if not isinstance(payload, dict):
                raise MassivePollError(CODE_MALFORMED_RESPONSE, "top level is not an object")

            results = payload.get("results")
            if not isinstance(results, list):
                raise MassivePollError(CODE_MALFORMED_RESPONSE, "results is not a list")
            if len(results) > _PAGE_LIMIT:
                raise MassivePollError(CODE_ROWS_TOO_MANY, "page exceeds row bound")

            for row in results:
                if not isinstance(row, dict):
                    raise MassivePollError(CODE_MALFORMED_RESPONSE, "row is not an object")
                publisher = row.get("publisher")
                homepage_url = publisher.get("homepage_url") if isinstance(publisher, dict) else None
                if _publisher_identity(homepage_url, allowed_publishers) is None:
                    continue  # not an allowed publisher: skip, do not normalize

                # Approved fields only; insights/body/image and anything else
                # are dropped here before the parent normalizer sees them.
                approved: dict[str, Any] = {}
                for field in ("id", "title", "article_url", "description", "published_utc", "keywords"):
                    if field in row:
                        approved[field] = row[field]
                if isinstance(publisher, dict):
                    approved_publisher: dict[str, Any] = {}
                    for field in ("name", "homepage_url"):
                        if field in publisher:
                            approved_publisher[field] = publisher[field]
                    if approved_publisher:
                        approved["publisher"] = approved_publisher
                if "tickers" in row:
                    approved["tickers"] = row["tickers"]

                try:
                    revisions.append(normalize_massive_news(approved, received_at=received_at))
                except Exception:
                    # Fail closed: no silent cursor advancement past bad rows.
                    raise MassivePollError(CODE_ROW_MALFORMED, "row failed normalization") from None

            next_url = payload.get("next_url")
            if next_url is None or (isinstance(next_url, str) and not next_url.strip()):
                complete = True
                break
            if not isinstance(next_url, str):
                raise MassivePollError(CODE_MALFORMED_RESPONSE, "next_url is not a string")
            url = _validate_next_url(next_url)

        return PollBatch(revisions=tuple(revisions), through=through, complete=complete, pages=pages,
                         next_url=None if complete else url)
