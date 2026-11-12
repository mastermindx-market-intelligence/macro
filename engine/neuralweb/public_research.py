"""Provider-neutral public evidence qualification boundary.

The core validates closed public fields and owns discovery/open receipts. Adapters
are explicitly injected; this module has no credential, vendor endpoint, default
network opener, Brain registration, persistence, model synthesis or trade authority.
Caller attestation and structural validation are not semantic privacy verification.
"""
from __future__ import annotations

import hashlib
import ipaddress
import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

SEARCH_SCHEMA = "mastermind.public_research_search.v1"
OPEN_SCHEMA = "mastermind.public_research_open.v1"
INVESTIGATION_SCHEMA = "mastermind.public_research_investigation.v1"
PUBLIC_QUERY_SCOPE = "public_minimal"
PUBLIC_QUERY_SCOPE_BASIS = "caller_attested_unverified"

_MAX_QUERY_CHARS = 400
_MAX_URL_CHARS = 2048
_MAX_RESULTS = 8
_MAX_OPEN_URLS = 5
_MAX_CONTENT_CHARS = 24000
_MAX_SNIPPET_CHARS = 4000
_MAX_PROVIDER_ROWS = 64
_PRIVATE_SUFFIXES = (
    ".localhost", ".local", ".localdomain", ".internal", ".lan", ".home", ".home.arpa",
)
_TOKEN_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_NUMERIC_HOST_LABEL = re.compile(r"(?:0[xX][0-9A-Fa-f]+|0[0-7]+|[0-9]+)\Z")
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_SENSITIVE_QUERY_NAMES = frozenset({
    "access_token", "oauth_token", "id_token", "refresh_token", "token",
    "api_key", "apikey", "api-key", "authorization", "auth",
    "signature", "sig", "credential", "security_token",
    "x-amz-signature", "x-amz-credential", "x-amz-security-token",
    "x-goog-signature", "x-goog-credential", "x-goog-security-token",
    "awsaccesskeyid", "googleaccessid", "key-pair-id",
})
EVIDENCE_NEEDS = {
    "filing_disclosure": "filing or public disclosure",
    "guidance": "management guidance",
    "segment_margin": "segment performance and margins",
    "backlog_orders": "backlog and orders",
    "inventory_working_capital": "inventory and working capital",
    "capital_spending": "capital spending",
    "demand_customer": "demand and customers",
    "product": "product developments",
    "regulation_policy": "regulation and policy",
    "management_claim": "verification of management claims",
}
SOURCE_PREFERENCES = {
    "primary_first": "prefer primary issuer and regulator sources",
    "independent_first": "prefer independent reporting",
    "balanced": "seek primary and independent sources",
}
_REQUEST_FIELDS = frozenset({
    "issuer", "ticker", "listing", "evidence_need", "start_date", "end_date",
    "information_cutoff", "source_preference",
})


class PublicResearchTransportError(RuntimeError):
    """Opaque transport refusal; its message is never relayed in core receipts."""


class PublicResearchNotConfigured(PublicResearchTransportError):
    """The explicitly selected adapter has no admitted configuration."""


@dataclass(frozen=True)
class PublicEvidenceRequest:
    issuer: str
    ticker: str
    listing: str
    evidence_need: str
    start_date: str
    end_date: str
    information_cutoff: str
    source_preference: str


class PublicResearchAdapter(Protocol):
    """An explicit backend returns completed action envelopes, never core receipts."""

    provider: str

    def search(self, request: PublicEvidenceRequest, *, max_results: int) -> dict: ...

    def open_sources(
        self, urls: list[str], *, request: PublicEvidenceRequest | None,
        max_content_chars: int,
    ) -> dict: ...


def _identity(value: object, limit: int) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > limit:
        raise ValueError("invalid_public_search_request")
    if any(not ch.isprintable() or ord(ch) == 127 for ch in value):
        raise ValueError("invalid_public_search_request")
    return value


def _date(value: object) -> str:
    if type(value) is not str or len(value) != 10:
        raise ValueError("invalid_public_search_request")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid_public_search_request") from None
    if parsed.isoformat() != value:
        raise ValueError("invalid_public_search_request")
    return value


def validate_public_request(value: object) -> PublicEvidenceRequest:
    """Validate only the closed public-field contract, not identity truth or PII."""
    if type(value) is PublicEvidenceRequest:
        fields = {name: getattr(value, name) for name in _REQUEST_FIELDS}
    elif type(value) is dict and set(value) == _REQUEST_FIELDS:
        fields = dict(value)
    else:
        raise ValueError("invalid_public_search_request")
    issuer = _identity(fields["issuer"], 120)
    ticker = _identity(fields["ticker"], 24)
    listing = _identity(fields["listing"], 32)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^:/-]*", ticker):
        raise ValueError("invalid_public_search_request")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .:_/-]*", listing):
        raise ValueError("invalid_public_search_request")
    need = fields["evidence_need"]
    preference = fields["source_preference"]
    if type(need) is not str or need not in EVIDENCE_NEEDS:
        raise ValueError("invalid_public_search_request")
    if type(preference) is not str or preference not in SOURCE_PREFERENCES:
        raise ValueError("invalid_public_search_request")
    start, end, cutoff = (_date(fields[name]) for name in (
        "start_date", "end_date", "information_cutoff",
    ))
    if not start <= end <= cutoff:
        raise ValueError("invalid_public_search_request")
    request = PublicEvidenceRequest(issuer, ticker, listing, need, start, end, cutoff, preference)
    if len(_request_query(request)) > _MAX_QUERY_CHARS:
        raise ValueError("invalid_public_search_request")
    return request


def _request_query(request: PublicEvidenceRequest) -> str:
    return (
        f"{request.issuer} ({request.ticker}; listing {request.listing}): "
        f"{EVIDENCE_NEEDS[request.evidence_need]}; "
        f"{request.start_date} to {request.end_date}; "
        f"information cutoff {request.information_cutoff}; "
        f"{SOURCE_PREFERENCES[request.source_preference]}"
    )


def build_public_query(value: object) -> str:
    """Build the minimal query from validated public fields; no raw-query escape."""
    return _request_query(validate_public_request(value))


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
    if any(not _DNS_LABEL.fullmatch(label) for label in labels):
        raise ValueError("unsafe_public_source")
    if all(_NUMERIC_HOST_LABEL.fullmatch(label) for label in labels):
        raise ValueError("unsafe_public_source")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise ValueError("unsafe_public_source")
    # This is lexical URL admission, not DNS proof. The injected remote extractor
    # owns its network boundary; a future direct opener needs its own qualification.
    return normalized


def _public_query_names(query: str) -> None:
    try:
        # Recognize both common delimiters for refusal; keep the original query.
        pairs = parse_qsl(query.replace(";", "&"), keep_blank_values=True, max_num_fields=64, errors="strict")
        for name, _ in pairs:
            # parse_qsl decodes once. Bound additional encodings and refuse residual
            # escapes/ambiguous delimiters instead of forwarding a disguised name.
            for _ in range(2):
                decoded = unquote(name, errors="strict")
                if decoded == name:
                    break
                name = decoded
            if (
                not name or "%" in name or any(ch in name for ch in "&=;")
                or any(not ch.isprintable() or ch.isspace() for ch in name)
                or name.casefold() in _SENSITIVE_QUERY_NAMES
            ):
                raise ValueError("unsafe_public_source")
    except (ValueError, UnicodeError):
        raise ValueError("unsafe_public_source") from None


def _canonical_public_url(value: object) -> str:
    if type(value) is not str or not value or len(value) > _MAX_URL_CHARS:
        raise ValueError("unsafe_public_source")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("unsafe_public_source")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() != "https":
            raise ValueError("unsafe_public_source")
        if parts.username is not None or parts.password is not None:
            raise ValueError("unsafe_public_source")
        host = _ascii_host(parts.hostname or "")
        if parts.port is not None and parts.port != 443:
            raise ValueError("unsafe_public_source")
        _public_query_names(parts.query)
    except (ValueError, UnicodeError):
        raise ValueError("unsafe_public_source") from None
    return urlunsplit(("https", host, parts.path or "/", parts.query, ""))


def _text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _request_id(value: object) -> str | None:
    return value if isinstance(value, str) and _TOKEN_RE.fullmatch(value) else None


def _provider(adapter: object) -> str:
    return _request_id(getattr(adapter, "provider", None)) or "unconfigured"


def _credits(payload: object) -> int | float | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("credits")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return int(number) if number.is_integer() else number


def _rows(response: dict, key: str, count_key: str) -> tuple[list, int]:
    rows = response.get(key)
    if not isinstance(rows, list):
        rows = []
    count = response.get(count_key)
    if type(count) is not int or not len(rows) <= count <= 1_000_000:
        count = len(rows)
    return rows[:_MAX_PROVIDER_ROWS], count


def _completed(response: object, action: str) -> bool:
    return (
        isinstance(response, dict) and response.get("status") == "completed"
        and response.get("action") == action
        and response.get(f"{action}_executed") is True
    )


def _search_unavailable(error: str, *, provider: str = "unconfigured") -> dict:
    return {
        "schema": SEARCH_SCHEMA, "provider": provider, "status": "unavailable",
        "error": error, "search_executed": False, "results": [],
    }


def search_public(
    request: object, *, adapter: PublicResearchAdapter | None = None, max_results: int = 6,
) -> dict:
    """Validate first; normalize completed search into discovery-only evidence."""
    provider = _provider(adapter)
    try:
        public_request = validate_public_request(request)
        if type(max_results) is not int or not 1 <= max_results <= _MAX_RESULTS:
            raise ValueError("invalid_public_search_request")
    except ValueError:
        return _search_unavailable("invalid_public_search_request", provider=provider)
    if adapter is None:
        return _search_unavailable("public_search_not_configured", provider=provider)
    try:
        response = adapter.search(public_request, max_results=max_results)
    except PublicResearchNotConfigured:
        return _search_unavailable("public_search_not_configured", provider=provider)
    except ValueError:
        return _search_unavailable("invalid_public_search_request", provider=provider)
    except Exception:
        return _search_unavailable("public_search_unavailable", provider=provider)
    if not _completed(response, "search"):
        return _search_unavailable("public_search_not_executed", provider=provider)
    if not isinstance(response.get("results"), list):
        return _search_unavailable("public_search_unavailable", provider=provider)

    normalized: list[dict] = []
    seen_urls: set[str] = set()
    rejected = unselected = 0
    rows, provider_count = _rows(response, "results", "provider_result_count")
    for row in rows:
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
        raw_score, score = row.get("score"), None
        if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool):
            try:
                candidate = float(raw_score)
            except (ValueError, OverflowError):
                candidate = math.nan
            if math.isfinite(candidate) and 0.0 <= candidate <= 1.0:
                score = candidate
        published = _text(row.get("published_date"), 128) or None
        normalized_row = {
            "title": _text(row.get("title"), 512), "url": url,
            "source_family": urlsplit(url).hostname or "", "score": score,
            "snippet": _text(row.get("snippet"), _MAX_SNIPPET_CHARS),
            "published_date": published,
            "published_date_basis": "provider_estimate" if published else "unavailable",
            "source_open_state": "not_opened", "untrusted_content": True,
        }
        if len(normalized) < max_results:
            normalized.append(normalized_row)
        else:
            unselected += 1
    return {
        "schema": SEARCH_SCHEMA, "provider": provider, "status": "available",
        "coverage_state": "results" if normalized else "empty", "search_executed": True,
        "query_sha256": hashlib.sha256(_request_query(public_request).encode("utf-8")).hexdigest(),
        "request_id": _request_id(response.get("request_id")),
        "provider_usage_credits": _credits(response.get("usage")),
        "results": normalized, "provider_result_count": provider_count,
        "rejected_results": rejected, "unselected_results": unselected,
        "unprocessed_provider_results": max(0, provider_count - len(rows)),
        "limits": [
            "Search snippets are untrusted discovery evidence and are not full-source review.",
            "Provider publication dates are estimates and require source-level date/correction checks.",
            "An empty search result is a coverage state, not proof that an event or fact does not exist.",
            "Closed public fields are structurally validated, not semantically checked for private data.",
        ],
    }


def _open_unavailable(
    error: str, sources: list[dict] | None = None, *, provider: str = "unconfigured",
) -> dict:
    return {
        "schema": OPEN_SCHEMA, "provider": provider, "status": "unavailable",
        "error": error, "open_executed": False, "opened_count": 0, "sources": sources or [],
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
    return urls


def _failed_source(url: str, error: str = "source_open_failed") -> dict:
    return {
        "url": url, "source_family": urlsplit(url).hostname or "",
        "source_open_state": "failed", "error": error,
        "untrusted_content": True, "source_instructions_authoritative": False,
    }


def open_public_sources(
    urls: object, *, adapter: PublicResearchAdapter | None = None,
    request: object = None, max_content_chars: int = _MAX_CONTENT_CHARS,
) -> dict:
    """Own open-state normalization while the explicitly selected adapter retrieves."""
    provider = _provider(adapter)
    try:
        requested = _requested_urls(urls)
        public_request = validate_public_request(request) if request is not None else None
        if type(max_content_chars) is not int or not 1000 <= max_content_chars <= 50000:
            raise ValueError("invalid_public_source_request")
    except ValueError:
        return _open_unavailable("invalid_public_source_request", provider=provider)
    if adapter is None:
        return _open_unavailable("public_source_open_not_configured", provider=provider)
    try:
        response = adapter.open_sources(
            requested, request=public_request, max_content_chars=max_content_chars,
        )
    except PublicResearchNotConfigured:
        return _open_unavailable("public_source_open_not_configured", provider=provider)
    except ValueError:
        return _open_unavailable("invalid_public_source_request", provider=provider)
    except Exception:
        return _open_unavailable(
            "public_source_open_unavailable",
            [_failed_source(url, "source_open_unavailable") for url in requested],
            provider=provider,
        )
    if not _completed(response, "open"):
        return _open_unavailable(
            "public_source_open_not_executed",
            [_failed_source(url, "source_open_unavailable") for url in requested],
            provider=provider,
        )
    opened: dict[str, dict] = {}
    rows, provider_count = _rows(response, "results", "provider_result_count")
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            url = _canonical_public_url(row.get("url"))
        except ValueError:
            continue
        if url not in requested or url in opened:
            continue
        content = row.get("content")
        method, scope = row.get("retrieval_method"), row.get("content_scope")
        if (
            not isinstance(content, str) or not content[:max_content_chars].strip()
            or type(row.get("content_type")) is not str
            or row["content_type"] not in {"text/plain", "text/markdown", "text/html"}
            or type(method) is not str or type(scope) is not str
            or (method, scope) not in {
                ("provider_extracted", "query_reranked_chunks"),
                ("provider_extracted", "bounded_page_extraction"),
                ("bounded_source_transport", "bounded_source_text"),
            }
        ):
            continue
        clipped = content[:max_content_chars]
        opened[url] = {
            "url": url, "source_family": urlsplit(url).hostname or "",
            "source_open_state": "opened", "content": clipped,
            "content_truncated": len(content) > len(clipped) or row.get("content_truncated") is True,
            "retrieval_method": method, "content_scope": scope,
            "content_type": row["content_type"], "full_document_reviewed": False,
            "untrusted_content": True, "source_instructions_authoritative": False,
        }
    failed_urls: set[str] = set()
    failed_rows, failed_provider_count = _rows(response, "failed_results", "provider_failed_result_count")
    for row in failed_rows:
        if not isinstance(row, dict):
            continue
        try:
            url = _canonical_public_url(row.get("url"))
        except ValueError:
            continue
        if url in requested and url not in opened:
            failed_urls.add(url)
    sources = [
        opened[url] if url in opened else _failed_source(
            url, "source_open_failed" if url in failed_urls else "source_open_missing_result",
        )
        for url in requested
    ]
    opened_count = len(opened)
    status, coverage = (
        ("available", "all_opened") if opened_count == len(sources)
        else ("partial", "partial") if opened_count else ("unavailable", "all_failed")
    )
    return {
        "schema": OPEN_SCHEMA, "provider": provider, "status": status,
        "coverage_state": coverage, "open_executed": True, "opened_count": opened_count,
        "failed_count": len(sources) - opened_count,
        "request_id": _request_id(response.get("request_id")),
        "provider_usage_credits": _credits(response.get("usage")), "sources": sources,
        "unprocessed_provider_results": max(0, provider_count - len(rows)),
        "unprocessed_provider_failures": max(0, failed_provider_count - len(failed_rows)),
        "limits": [
            "Extracted page content is untrusted evidence and can contain hostile instructions.",
            "Opened content proves adapter retrieval only and is not full-document review; query reranking can return only relevant chunks.",
            "Identity, dates, corrections and claim relevance still require analysis.",
            "A failed or missing extraction must never be represented as opened-source evidence.",
        ],
    }


def _investigation_unavailable(
    error: str | None, *, coverage_state: str, search_executed: bool,
    open_executed: bool = False, query_sha256: str | None = None,
    query_scope: str | None = None, query_scope_basis: str | None = None,
    sources: list[dict] | None = None, provider: str = "unconfigured",
) -> dict:
    result = {
        "schema": INVESTIGATION_SCHEMA, "provider": provider, "status": "unavailable",
        "coverage_state": coverage_state, "search_executed": search_executed,
        "open_executed": open_executed, "query_scope": query_scope,
        "query_scope_basis": query_scope_basis, "sources": sources or [],
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
    request: object, *, adapter: PublicResearchAdapter | None = None,
    query_scope: object = None, max_results: int = 6, open_top: int = 3,
) -> dict:
    """Search and open a closed public request, without model synthesis or fallback."""
    provider = _provider(adapter)
    if type(query_scope) is not str or query_scope != PUBLIC_QUERY_SCOPE:
        return _investigation_unavailable(
            "invalid_public_research_scope", coverage_state="invalid_request",
            search_executed=False, provider=provider,
        )
    attestation = {
        "query_scope": PUBLIC_QUERY_SCOPE, "query_scope_basis": PUBLIC_QUERY_SCOPE_BASIS,
        "provider": provider,
    }
    try:
        public_request = validate_public_request(request)
        if (
            type(open_top) is not int or type(max_results) is not int
            or not 1 <= open_top <= _MAX_OPEN_URLS
            or not 1 <= max_results <= _MAX_RESULTS or open_top > max_results
        ):
            raise ValueError("invalid_public_research_request")
    except ValueError:
        return _investigation_unavailable(
            "invalid_public_research_request", coverage_state="invalid_request",
            search_executed=False, **attestation,
        )
    search = search_public(public_request, adapter=adapter, max_results=max_results)
    query_hash = search.get("query_sha256")
    if search.get("status") != "available":
        return _investigation_unavailable(
            search.get("error") or "public_search_unavailable",
            coverage_state="search_unavailable", search_executed=False,
            query_sha256=query_hash, **attestation,
        )
    candidates = search["results"]
    if not candidates:
        return _investigation_unavailable(
            None, coverage_state="search_empty", search_executed=True,
            query_sha256=query_hash, **attestation,
        )
    selected = candidates[:open_top]
    opened = open_public_sources(
        [row["url"] for row in selected], request=public_request, adapter=adapter,
    )
    opened_by_url = {row["url"]: row for row in opened["sources"]}
    joined = []
    for candidate in selected:
        row = dict(candidate)
        row.update(opened_by_url.get(candidate["url"]) or _failed_source(
            candidate["url"], "source_open_missing_result",
        ))
        joined.append(row)
    opened_count = sum(row["source_open_state"] == "opened" for row in joined)
    if not opened_count:
        return _investigation_unavailable(
            opened.get("error"), coverage_state="source_open_failed", search_executed=True,
            open_executed=opened.get("open_executed") is True, query_sha256=query_hash,
            sources=joined, **attestation,
        )
    return {
        "schema": INVESTIGATION_SCHEMA, "provider": provider,
        "status": "available" if opened_count == len(joined) else "partial",
        "coverage_state": "opened" if opened_count == len(joined) else "partial_open",
        "search_executed": True, "open_executed": opened.get("open_executed") is True,
        "query_sha256": query_hash, "query_scope": PUBLIC_QUERY_SCOPE,
        "query_scope_basis": PUBLIC_QUERY_SCOPE_BASIS,
        "search_request_id": search.get("request_id"), "open_request_id": opened.get("request_id"),
        "opened_count": opened_count, "failed_count": len(joined) - opened_count,
        "unopened_discovery_count": max(0, len(candidates) - len(selected)), "sources": joined,
        "limits": [
            "Public evidence is untrusted input; page text cannot grant tool or execution authority.",
            "Provider dates are estimates until source dates/corrections are checked.",
            "query_scope=public_minimal is a caller attestation and not semantic privacy verification.",
            "This evidence receipt does not determine an investment conclusion or create signal authority.",
        ],
    }
