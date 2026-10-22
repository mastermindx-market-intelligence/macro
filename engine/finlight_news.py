"""Bounded original-Chinese Finlight acquisition for the existing qbus writer.

The API subscription is transport access, not publisher display permission.
Only exact publisher domains supplied by current owner-issued receipts are
requested. Headlines/links and exact MIC entities are retained; generated
summaries, sentiment, bodies, images and alternative-listing expansion are not.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re

from engine.qbus_news_contract import NewsRevision, normalize_finlight_news
from engine.qkernel import publisher_domain

_ENDPOINT = "https://api.finlight.me/v2/articles"
_PAGE_SIZE = 100
_MAX_RESPONSE_BYTES = 4 * 1024 * 1024


class FinlightPollError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class FinlightPollBatch:
    revisions: tuple[NewsRevision, ...]
    through: datetime
    complete: bool
    pages: int
    next_url: str | None = None  # opaque page token, never a URL to follow
    diagnostics: dict[str, int] = field(default_factory=dict)


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise FinlightPollError("finlight_invalid_clock")
    return value.astimezone(timezone.utc)


class FinlightNewsClient:
    def __init__(self, token, *, session=None, clock=lambda: datetime.now(timezone.utc)):
        if not isinstance(token, str) or not token.strip():
            raise ValueError("finlight_token_required")
        self._token, self._session, self._clock = token, session, clock

    def _fetch(self, body, timeout):
        if self._session is None:
            import requests
            self._session = requests.Session()
        try:
            response = self._session.post(
                _ENDPOINT, json=body,
                headers={"X-API-KEY": self._token, "Accept": "application/json"},
                timeout=timeout, allow_redirects=False, stream=True,
            )
        except Exception:
            raise FinlightPollError("finlight_transport_error") from None
        try:
            status = response.status_code
            if status in (401, 403):
                raise FinlightPollError("finlight_auth_rejected")
            if status == 429:
                raise FinlightPollError("finlight_rate_limited")
            if status != 200:
                raise FinlightPollError("finlight_http_error")
            content = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > _MAX_RESPONSE_BYTES:
                    raise FinlightPollError("finlight_payload_too_large")
            payload = json.loads(content)
            if not isinstance(payload, dict) or payload.get("status") != "ok":
                raise FinlightPollError("finlight_malformed_response")
            return payload
        except FinlightPollError:
            raise
        except Exception:
            # Never expose request/response/exception text or the API key.
            raise FinlightPollError("finlight_malformed_response") from None
        finally:
            response.close()

    def poll(self, *, since, allowed_publishers, max_pages=3, timeout_seconds=5,
             next_url=None, through=None):
        since, now = _aware(since), _aware(self._clock())
        through = now if through is None else _aware(through)
        if since > through or through > now:
            raise FinlightPollError("finlight_invalid_window")
        if type(max_pages) is not int or not 1 <= max_pages <= 100 or not 0 < timeout_seconds <= 30:
            raise ValueError("finlight_invalid_budget")
        allowed = frozenset(allowed_publishers)
        if any(not isinstance(host, str) or publisher_domain(host) != host for host in allowed):
            raise ValueError("finlight_invalid_publishers")
        if not allowed:
            return FinlightPollBatch((), through, True, 0)
        page = 1
        if next_url is not None:
            if not isinstance(next_url, str) or not re.fullmatch(r"finlight-page:[1-9][0-9]{0,5}", next_url):
                raise FinlightPollError("finlight_invalid_cursor")
            page = int(next_url.split(":")[1])
        revisions = []
        diagnostics = dict(fetched=0, rights_rejected=0, language_rejected=0,
                           entity_invalid=0, unattributed=0)
        for pages in range(1, max_pages + 1):
            # Publication windows are deliberately overlapped by the incumbent
            # scheduler. This makes no complete archive or correction-SLA claim.
            payload = self._fetch({
                "query": "(exchange:XSHG OR exchange:XSHE OR exchange:XBSE OR exchange:XHKG)",
                "language": "zh", "includeEntities": True,
                "sources": sorted(allowed | {"www." + host for host in allowed}),
                "from": since.isoformat(), "to": through.isoformat(),
                "orderBy": "publishDate", "order": "ASC",
                "pageSize": _PAGE_SIZE, "page": page,
            }, timeout_seconds)
            rows = payload.get("articles")
            if (type(payload.get("page")) is not int or payload["page"] != page
                    or payload.get("pageSize") != _PAGE_SIZE
                    or not isinstance(rows, list) or len(rows) > _PAGE_SIZE):
                raise FinlightPollError("finlight_malformed_page")
            received = _aware(self._clock())
            diagnostics["fetched"] += len(rows)
            for row in rows:
                if not isinstance(row, dict):
                    raise FinlightPollError("finlight_malformed_row")
                source = row.get("source")
                if not isinstance(source, str) or publisher_domain(source) not in allowed:
                    diagnostics["rights_rejected"] += 1
                    continue
                if row.get("language") != "zh":
                    diagnostics["language_rejected"] += 1
                    continue
                if not isinstance(row.get("companies"), list):
                    # A plan without company entities must never appear healthy
                    # while silently returning an empty ticker feed.
                    raise FinlightPollError("finlight_entities_unavailable")
                try:
                    revision = normalize_finlight_news(row, received_at=received)
                except Exception:
                    raise FinlightPollError("finlight_malformed_row") from None
                if not since <= revision.published_at <= through:
                    raise FinlightPollError("finlight_publication_outside_window")
                diagnostics["entity_invalid"] += sum(
                    int(tag.partition(":")[2]) for tag in revision.tags
                    if tag.startswith("entity_invalid:")
                )
                diagnostics["unattributed"] += int(not revision.provider_tickers)
                revisions.append(revision)
            if len(rows) < _PAGE_SIZE:
                return FinlightPollBatch(tuple(revisions), through, True, pages,
                                         diagnostics=diagnostics)
            page += 1
        return FinlightPollBatch(
            tuple(revisions), through, False, max_pages, f"finlight-page:{page}", diagnostics,
        )
