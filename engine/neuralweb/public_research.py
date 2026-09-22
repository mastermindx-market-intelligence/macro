"""Provider-qualified public research evidence boundary.

This module is deliberately NOT wired into Brain yet. It normalizes one external
search/open provider behind an injected transport so qualification can be tested
without credentials or live effects. Retrieved text is untrusted evidence, never
authority, and nothing here persists, ranks, sizes, signals, or trades.
"""
from __future__ import annotations

import hashlib
import ipaddress
import math
import os
import re
from datetime import date
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

SEARCH_ENDPOINT = "https://api.tavily.com/search"
EXTRACT_ENDPOINT = "https://api.tavily.com/extract"
PROVIDER = "tavily"
SEARCH_SCHEMA = "mastermind.public_research_search.v1"
PUBLIC_QUERY_SCOPE = "public_minimal"
PUBLIC_QUERY_SCOPE_BASIS = "caller_attested_unverified"

_MAX_QUERY_CHARS = 400
_MAX_URL_CHARS = 2048
_MAX_RESULTS = 8
_MAX_DOMAINS = 20
_MAX_SNIPPET_CHARS = 4000
_SAFE_TOPIC = frozenset({"general", "news", "finance"})
_SAFE_DEPTH = frozenset({"advanced", "basic", "fast", "ultra-fast"})
_SAFE_TIME_RANGE = frozenset({"day", "week", "month", "year", "d", "w", "m", "y"})
_PRIVATE_SUFFIXES = (
    ".localhost", ".local", ".localdomain", ".internal", ".lan", ".home", ".home.arpa",
)
_TOKEN_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_NUMERIC_HOST_LABEL = re.compile(r"(?:0[xX][0-9A-Fa-f]+|0[0-7]+|[0-9]+)\Z")
_MAX_PROVIDER_ROWS = 64


class PublicResearchTransportError(RuntimeError):
    """Opaque provider transport refusal. Caller responses never relay its message."""


def _query(value: object, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_public_search_request")
    cleaned = value.strip()
    if not cleaned and required:
        raise ValueError("invalid_public_search_request")
    if len(cleaned) > _MAX_QUERY_CHARS:
        raise ValueError("invalid_public_search_request")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ValueError("invalid_public_search_request")
    return cleaned or None


def _ascii_host(host: str) -> str:
    try:
        normalized = host.rstrip(".").encode("idna").decode("ascii").lower()
    except (UnicodeError, AttributeError):
        raise ValueError("unsafe_public_source") from None
    if not normalized or len(normalized) > 253 or "." not in normalized:
        raise ValueError("unsafe_public_source")
    if normalized == "localhost" or normalized.endswith(_PRIVATE_SUFFIXES):
        raise ValueError("unsafe_public_source")
    labels = normalized.split(".")
    # Catch abbreviated / hexadecimal / octal IPv4 spellings before the
    # provider sees them. DNS resolution itself is intentionally NOT performed
    # here; Tavily remains responsible for its remote-fetch network boundary.
    if labels and all(_NUMERIC_HOST_LABEL.fullmatch(label) for label in labels):
        raise ValueError("unsafe_public_source")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise ValueError("unsafe_public_source")
    return normalized


def _domain(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_public_search_request")
    raw = value.strip()
    if (
        not raw
        or len(raw) > 253
        or any(ch in raw for ch in "/:@?#")
        or any(ord(ch) < 33 or ord(ch) == 127 for ch in raw)
    ):
        raise ValueError("invalid_public_search_request")
    try:
        return _ascii_host(raw)
    except ValueError:
        raise ValueError("invalid_public_search_request") from None


def _domains(values: object) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)) or len(values) > _MAX_DOMAINS:
        raise ValueError("invalid_public_search_request")
    normalized: list[str] = []
    for value in values:
        item = _domain(value)
        if item not in normalized:
            normalized.append(item)
    return normalized


def _date(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("invalid_public_search_request")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid_public_search_request") from None
    if parsed.isoformat() != value:
        raise ValueError("invalid_public_search_request")
    return value


def _canonical_public_url(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_URL_CHARS:
        raise ValueError("unsafe_public_source")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("unsafe_public_source")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"}:
            raise ValueError("unsafe_public_source")
        if parts.username is not None or parts.password is not None:
            raise ValueError("unsafe_public_source")
        host = _ascii_host(parts.hostname or "")
        port = parts.port
    except (ValueError, UnicodeError):
        raise ValueError("unsafe_public_source") from None
    scheme = parts.scheme.lower()
    if port is not None:
        expected_port = 80 if scheme == "http" else 443
        if port != expected_port:
            raise ValueError("unsafe_public_source")
    netloc = host
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return value[:limit]


def _request_id(value: object) -> str | None:
    return value if isinstance(value, str) and _TOKEN_RE.fullmatch(value) else None


def _credits(payload: object) -> int | float | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("credits")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return int(number) if number.is_integer() else number


def _default_post_json(
    url: str, *, headers: dict[str, str], payload: dict[str, Any], timeout: float,
) -> dict:
    try:
        import requests

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
            allow_redirects=False,
        )
        if not 200 <= int(response.status_code) < 300:
            raise PublicResearchTransportError("provider_http_error")
        decoded = response.json()
        if not isinstance(decoded, dict):
            raise PublicResearchTransportError("provider_json_invalid")
        return decoded
    except PublicResearchTransportError:
        raise
    except Exception:
        raise PublicResearchTransportError("provider_unavailable") from None


def _search_unavailable(error: str) -> dict:
    return {
        "schema": SEARCH_SCHEMA,
        "provider": PROVIDER,
        "status": "unavailable",
        "error": error,
        "search_executed": False,
        "results": [],
    }


def search_public(
    query: object,
    *,
    api_key: str | None = None,
    post_json: Callable[..., dict] | None = None,
    topic: str = "finance",
    search_depth: str = "advanced",
    max_results: int = 6,
    time_range: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_domains: object = (),
    exclude_domains: object = (),
    filter_by_published_date: bool = False,
) -> dict:
    """Search public sources; returned snippets are never full-source evidence."""
    key = api_key if api_key is not None else os.environ.get("TAVILY_API_KEY")
    if not isinstance(key, str) or not key.strip():
        return _search_unavailable("public_search_not_configured")
    try:
        public_query = _query(query)
        if topic not in _SAFE_TOPIC or search_depth not in _SAFE_DEPTH:
            raise ValueError("invalid_public_search_request")
        if type(max_results) is not int or not 1 <= max_results <= _MAX_RESULTS:
            raise ValueError("invalid_public_search_request")
        if time_range is not None and time_range not in _SAFE_TIME_RANGE:
            raise ValueError("invalid_public_search_request")
        start = _date(start_date)
        end = _date(end_date)
        if start and end and start > end:
            raise ValueError("invalid_public_search_request")
        if type(filter_by_published_date) is not bool:
            raise ValueError("invalid_public_search_request")
        allowed_domains = _domains(include_domains)
        denied_domains = _domains(exclude_domains)
        if set(allowed_domains).intersection(denied_domains):
            raise ValueError("invalid_public_search_request")
    except ValueError:
        return _search_unavailable("invalid_public_search_request")

    payload = {
        "query": public_query,
        "search_depth": search_depth,
        "max_results": max_results,
        "topic": topic,
        "time_range": time_range,
        "start_date": start,
        "end_date": end,
        "include_published_date": True,
        "filter_by_published_date": filter_by_published_date,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_image_descriptions": False,
        "include_favicon": False,
        "include_domains": allowed_domains,
        "exclude_domains": denied_domains,
        "auto_parameters": False,
        "include_usage": True,
    }
    if search_depth != "ultra-fast":
        payload["chunks_per_source"] = 3
    transport = post_json or _default_post_json
    try:
        response = transport(
            SEARCH_ENDPOINT,
            headers={
                "Authorization": f"Bearer {key.strip()}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=30.0,
        )
        if not isinstance(response, dict):
            raise PublicResearchTransportError("provider_json_invalid")
    except Exception:
        return _search_unavailable("public_search_unavailable")

    normalized: list[dict] = []
    seen_urls: set[str] = set()
    rejected = 0
    unselected = 0
    rows = response.get("results")
    if not isinstance(rows, list):
        rows = []
    provider_result_count = len(rows)
    bounded_rows = rows[:_MAX_PROVIDER_ROWS]
    for row in bounded_rows:
        if not isinstance(row, dict):
            rejected += 1
            continue
        try:
            url = _canonical_public_url(row.get("url"))
        except ValueError:
            rejected += 1
            continue
        if url in seen_urls:
            rejected += 1
            continue
        seen_urls.add(url)
        score_raw = row.get("score")
        score: float | None = None
        if isinstance(score_raw, (int, float)) and not isinstance(score_raw, bool):
            candidate = float(score_raw)
            if math.isfinite(candidate) and 0.0 <= candidate <= 1.0:
                score = candidate
        published = _text(row.get("published_date"), 128) or None
        normalized_row = {
            "title": _text(row.get("title"), 512),
            "url": url,
            "source_family": urlsplit(url).hostname or "",
            "score": score,
            "snippet": _text(row.get("content"), _MAX_SNIPPET_CHARS),
            "published_date": published,
            "published_date_basis": "provider_estimate" if published else "unavailable",
            "source_open_state": "not_opened",
            "untrusted_content": True,
        }
        if len(normalized) < max_results:
            normalized.append(normalized_row)
        else:
            unselected += 1

    return {
        "schema": SEARCH_SCHEMA,
        "provider": PROVIDER,
        "status": "available",
        "coverage_state": "results" if normalized else "empty",
        "search_executed": True,
        "query_sha256": hashlib.sha256(public_query.encode("utf-8")).hexdigest(),
        "request_id": _request_id(response.get("request_id")),
        "provider_usage_credits": _credits(response.get("usage")),
        "results": normalized,
        "provider_result_count": provider_result_count,
        "rejected_results": rejected,
        "unselected_results": unselected,
        "unprocessed_provider_results": max(0, provider_result_count - len(bounded_rows)),
        "limits": [
            "Search snippets are untrusted discovery evidence and are not full-source review.",
            "Provider publication dates are estimates and require source-level date/correction checks.",
            "An empty search result is a coverage state, not proof that an event or fact does not exist.",
        ],
    }


OPEN_SCHEMA = "mastermind.public_research_open.v1"
_MAX_OPEN_URLS = 5
_MAX_CONTENT_CHARS = 24000


def _open_unavailable(error: str, sources: list[dict] | None = None) -> dict:
    return {
        "schema": OPEN_SCHEMA,
        "provider": PROVIDER,
        "status": "unavailable",
        "error": error,
        "open_executed": False,
        "opened_count": 0,
        "sources": sources or [],
    }


def _requested_urls(values: object) -> list[str]:
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= _MAX_OPEN_URLS:
        raise ValueError("invalid_public_source_request")
    urls: list[str] = []
    for value in values:
        try:
            url = _canonical_public_url(value)
        except ValueError:
            raise ValueError("invalid_public_source_request") from None
        if url not in urls:
            urls.append(url)
    if not urls:
        raise ValueError("invalid_public_source_request")
    return urls


def _failed_source(url: str, error: str = "source_open_failed") -> dict:
    return {
        "url": url,
        "source_family": urlsplit(url).hostname or "",
        "source_open_state": "failed",
        "error": error,
        "untrusted_content": True,
        "source_instructions_authoritative": False,
    }


def open_public_sources(
    urls: object,
    *,
    query: object = None,
    api_key: str | None = None,
    post_json: Callable[..., dict] | None = None,
    extract_depth: str = "advanced",
    max_content_chars: int = _MAX_CONTENT_CHARS,
) -> dict:
    """Open selected public URLs through the qualified provider extraction endpoint."""
    key = api_key if api_key is not None else os.environ.get("TAVILY_API_KEY")
    if not isinstance(key, str) or not key.strip():
        return _open_unavailable("public_source_open_not_configured")
    try:
        requested = _requested_urls(urls)
        public_query = _query(query, required=False)
        if extract_depth not in {"basic", "advanced"}:
            raise ValueError("invalid_public_source_request")
        if type(max_content_chars) is not int or not 1000 <= max_content_chars <= 50000:
            raise ValueError("invalid_public_source_request")
    except ValueError:
        return _open_unavailable("invalid_public_source_request")

    payload: dict[str, Any] = {
        "urls": requested,
        "extract_depth": extract_depth,
        "include_images": False,
        "include_favicon": False,
        "format": "markdown",
        "include_usage": True,
    }
    if public_query:
        payload["query"] = public_query
        payload["chunks_per_source"] = 3

    transport = post_json or _default_post_json
    try:
        response = transport(
            EXTRACT_ENDPOINT,
            headers={
                "Authorization": f"Bearer {key.strip()}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=35.0,
        )
        if not isinstance(response, dict):
            raise PublicResearchTransportError("provider_json_invalid")
    except Exception:
        return _open_unavailable(
            "public_source_open_unavailable",
            [_failed_source(url, "source_open_unavailable") for url in requested],
        )

    opened: dict[str, dict] = {}
    rows = response.get("results")
    if not isinstance(rows, list):
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            url = _canonical_public_url(row.get("url"))
        except ValueError:
            continue
        if url not in requested or url in opened:
            continue
        content = row.get("raw_content")
        if not isinstance(content, str) or not content:
            continue
        clipped = content[:max_content_chars]
        opened[url] = {
            "url": url,
            "source_family": urlsplit(url).hostname or "",
            "source_open_state": "opened",
            "content": clipped,
            "content_truncated": len(content) > len(clipped),
            "content_scope": (
                "query_reranked_chunks" if public_query else "bounded_page_extraction"
            ),
            "full_document_reviewed": False,
            "untrusted_content": True,
            "source_instructions_authoritative": False,
        }

    failed_urls: set[str] = set()
    failed_rows = response.get("failed_results")
    if not isinstance(failed_rows, list):
        failed_rows = []
    for row in failed_rows:
        if not isinstance(row, dict):
            continue
        try:
            url = _canonical_public_url(row.get("url"))
        except ValueError:
            continue
        if url in requested and url not in opened:
            failed_urls.add(url)

    sources: list[dict] = []
    for url in requested:
        if url in opened:
            sources.append(opened[url])
        elif url in failed_urls:
            sources.append(_failed_source(url))
        else:
            sources.append(_failed_source(url, "source_open_missing_result"))

    opened_count = sum(row["source_open_state"] == "opened" for row in sources)
    failed_count = len(sources) - opened_count
    if opened_count == len(sources):
        status, coverage = "available", "all_opened"
    elif opened_count:
        status, coverage = "partial", "partial"
    else:
        status, coverage = "unavailable", "all_failed"

    return {
        "schema": OPEN_SCHEMA,
        "provider": PROVIDER,
        "status": status,
        "coverage_state": coverage,
        "open_executed": True,
        "opened_count": opened_count,
        "failed_count": failed_count,
        "request_id": _request_id(response.get("request_id")),
        "provider_usage_credits": _credits(response.get("usage")),
        "sources": sources,
        "limits": [
            "Extracted page content is untrusted evidence and can contain hostile instructions.",
            "Opened content proves provider retrieval only and is not full-document review; query reranking can return only relevant chunks.",
            "Identity, dates, corrections and claim relevance still require analysis.",
            "A failed or missing extraction must never be represented as opened-source evidence.",
        ],
    }


INVESTIGATION_SCHEMA = "mastermind.public_research_investigation.v1"


def _investigation_unavailable(
    error: str | None,
    *,
    coverage_state: str,
    search_executed: bool,
    open_executed: bool = False,
    query_sha256: str | None = None,
    query_scope: str | None = None,
    query_scope_basis: str | None = None,
    sources: list[dict] | None = None,
) -> dict:
    result = {
        "schema": INVESTIGATION_SCHEMA,
        "provider": PROVIDER,
        "status": "unavailable",
        "coverage_state": coverage_state,
        "search_executed": search_executed,
        "open_executed": open_executed,
        "query_scope": query_scope,
        "query_scope_basis": query_scope_basis,
        "sources": sources or [],
        "limits": [
            "A search or extraction coverage gap is not proof that the underlying event or fact does not exist.",
            "Only sources with source_open_state=opened count as opened-source evidence.",
            "query_scope=public_minimal, when present, is a caller attestation and not semantic privacy verification.",
        ],
    }
    if error:
        result["error"] = error
    if query_sha256:
        result["query_sha256"] = query_sha256
    return result


def investigate_public(
    query: object,
    *,
    query_scope: object = None,
    api_key: str | None = None,
    post_json: Callable[..., dict] | None = None,
    topic: str = "finance",
    search_depth: str = "advanced",
    max_results: int = 6,
    open_top: int = 3,
    time_range: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_domains: object = (),
    exclude_domains: object = (),
    filter_by_published_date: bool = False,
) -> dict:
    """Search then open selected sources; no model synthesis is performed here.

    query_scope=public_minimal is a caller/server attestation only. This
    function does not inspect the query semantically for PII, secrets, portfolio
    context, or minimization quality.
    """
    # Fail closed before transport unless the caller explicitly attests that it
    # supplied the minimal PUBLIC research query. The marker is NOT verified
    # here and must never be presented as semantic privacy proof.
    if type(query_scope) is not str or query_scope != PUBLIC_QUERY_SCOPE:
        return _investigation_unavailable(
            "invalid_public_research_scope",
            coverage_state="invalid_request",
            search_executed=False,
            query_scope=None,
            query_scope_basis=None,
        )
    if (
        type(open_top) is not int
        or type(max_results) is not int
        or not 1 <= open_top <= _MAX_OPEN_URLS
        or not 1 <= max_results <= _MAX_RESULTS
        or open_top > max_results
    ):
        return _investigation_unavailable(
            "invalid_public_research_request",
            coverage_state="invalid_request",
            search_executed=False,
            query_scope=PUBLIC_QUERY_SCOPE,
            query_scope_basis=PUBLIC_QUERY_SCOPE_BASIS,
        )

    search = search_public(
        query,
        api_key=api_key,
        post_json=post_json,
        topic=topic,
        search_depth=search_depth,
        max_results=max_results,
        time_range=time_range,
        start_date=start_date,
        end_date=end_date,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        filter_by_published_date=filter_by_published_date,
    )
    query_hash = search.get("query_sha256")
    if search.get("status") != "available":
        return _investigation_unavailable(
            str(search.get("error") or "public_search_unavailable"),
            coverage_state="search_unavailable",
            search_executed=bool(search.get("search_executed")),
            query_sha256=query_hash if isinstance(query_hash, str) else None,
            query_scope=PUBLIC_QUERY_SCOPE,
            query_scope_basis=PUBLIC_QUERY_SCOPE_BASIS,
        )

    candidates = search.get("results") or []
    if not candidates:
        return _investigation_unavailable(
            None,
            coverage_state="search_empty",
            search_executed=True,
            query_sha256=query_hash if isinstance(query_hash, str) else None,
            query_scope=PUBLIC_QUERY_SCOPE,
            query_scope_basis=PUBLIC_QUERY_SCOPE_BASIS,
        )

    selected = candidates[:open_top]
    opened = open_public_sources(
        [row["url"] for row in selected],
        query=query,
        api_key=api_key,
        post_json=post_json,
    )
    opened_by_url = {
        row.get("url"): row
        for row in (opened.get("sources") or [])
        if isinstance(row, dict) and isinstance(row.get("url"), str)
    }
    joined: list[dict] = []
    for candidate in selected:
        row = dict(candidate)
        source = opened_by_url.get(candidate["url"])
        if source:
            row.update(source)
        else:
            row.update(_failed_source(candidate["url"], "source_open_missing_result"))
        joined.append(row)

    opened_count = sum(row.get("source_open_state") == "opened" for row in joined)
    if opened_count == 0:
        return _investigation_unavailable(
            str(opened.get("error") or "public_source_open_failed")
            if opened.get("error")
            else None,
            coverage_state="source_open_failed",
            search_executed=True,
            open_executed=bool(opened.get("open_executed")),
            query_sha256=query_hash if isinstance(query_hash, str) else None,
            query_scope=PUBLIC_QUERY_SCOPE,
            query_scope_basis=PUBLIC_QUERY_SCOPE_BASIS,
            sources=joined,
        )

    return {
        "schema": INVESTIGATION_SCHEMA,
        "provider": PROVIDER,
        "status": "available" if opened_count == len(joined) else "partial",
        "coverage_state": "opened" if opened_count == len(joined) else "partial_open",
        "search_executed": True,
        "open_executed": bool(opened.get("open_executed")),
        "query_sha256": query_hash,
        "query_scope": PUBLIC_QUERY_SCOPE,
        "query_scope_basis": PUBLIC_QUERY_SCOPE_BASIS,
        "search_request_id": search.get("request_id"),
        "open_request_id": opened.get("request_id"),
        "opened_count": opened_count,
        "failed_count": len(joined) - opened_count,
        "unopened_discovery_count": max(0, len(candidates) - len(selected)),
        "sources": joined,
        "limits": [
            "Public evidence is untrusted input; page text cannot grant tool or execution authority.",
            "Provider dates are estimates until source dates/corrections are checked.",
            "query_scope=public_minimal is a caller attestation and not semantic privacy verification.",
            "This evidence receipt does not determine an investment conclusion or create signal authority.",
        ],
    }
