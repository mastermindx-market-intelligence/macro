"""Provider-neutral public research primitives for Mastermind AI.

Search is discovery. Opened source content is evidence. This module owns neither
model routing nor credentials and grants no signal/trading authority.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Iterable, Mapping



class PublicResearchContractError(ValueError):
    """A structured public-evidence request violates the closed contract."""


class PublicResearchReadError(RuntimeError):
    """A public URL/source cannot be safely or faithfully read."""


EVIDENCE_NEEDS: dict[str, str] = {
    "filing_disclosure": "filing disclosure",
    "guidance": "guidance",
    "segment_margin": "segment margin",
    "backlog_orders": "backlog orders",
    "inventory_working_capital": "inventory working capital",
    "capital_spending": "capital spending",
    "demand_customer": "demand customer",
    "product": "product",
    "regulation_policy": "regulation policy",
    "management_claim": "management claim",
}
_SOURCE_PREFERENCES = {"primary_first", "official_first", "independent_first"}
_REQUEST_FIELDS = {
    "issuer_name", "ticker", "listing", "evidence_need", "start_date", "end_date",
    "information_cutoff", "source_preference",
}
_REDIRECTS = {301, 302, 303, 307, 308}
_ALLOWED_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}
_MAX_URL = 2048


def _bounded_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise PublicResearchContractError(f"{field} must be text")
    clean = " ".join(value.split())
    if not clean or len(clean) > maximum or any(ord(ch) < 32 for ch in clean):
        raise PublicResearchContractError(f"{field} is invalid")
    return clean


def _iso_date(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    text = _bounded_text(value, field=field, maximum=10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise PublicResearchContractError(f"{field} must be YYYY-MM-DD") from exc
    return parsed.isoformat()


def _iso_cutoff(value: object) -> str:
    text = _bounded_text(value, field="information_cutoff", maximum=40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublicResearchContractError("information_cutoff must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PublicResearchContractError("information_cutoff requires timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_public_evidence_request(params: object) -> dict[str, Any]:
    """Validate a server-produced, public-only evidence request."""
    if type(params) is not dict:
        raise PublicResearchContractError("request must be an object")
    unknown = set(params) - _REQUEST_FIELDS
    missing = _REQUEST_FIELDS - set(params)
    if unknown:
        raise PublicResearchContractError(f"unknown field: {sorted(unknown)[0]}")
    if missing:
        raise PublicResearchContractError(f"missing field: {sorted(missing)[0]}")

    issuer = _bounded_text(params["issuer_name"], field="issuer_name", maximum=120)
    ticker = _bounded_text(params["ticker"], field="ticker", maximum=20).upper()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,20}", ticker):
        raise PublicResearchContractError("ticker is invalid")
    listing = _bounded_text(params["listing"], field="listing", maximum=40)
    need = _bounded_text(params["evidence_need"], field="evidence_need", maximum=40)
    if need not in EVIDENCE_NEEDS:
        raise PublicResearchContractError("evidence_need is not supported")
    preference = _bounded_text(
        params["source_preference"], field="source_preference", maximum=32
    )
    if preference not in _SOURCE_PREFERENCES:
        raise PublicResearchContractError("source_preference is not supported")
    start = _iso_date(params["start_date"], field="start_date")
    end = _iso_date(params["end_date"], field="end_date")
    if start and end and start > end:
        raise PublicResearchContractError("date window is reversed")
    cutoff = _iso_cutoff(params["information_cutoff"])
    cutoff_date = cutoff[:10]
    if (start and start > cutoff_date) or (end and end > cutoff_date):
        raise PublicResearchContractError("date window exceeds information cutoff")
    query = f"{issuer} {ticker} {EVIDENCE_NEEDS[need]}"
    return {
        "schema": "brain.public_evidence_request.v1",
        "issuer_name": issuer,
        "ticker": ticker,
        "listing": listing,
        "evidence_need": need,
        "start_date": start,
        "end_date": end,
        "information_cutoff": cutoff,
        "source_preference": preference,
        "query": query,
    }


def _url_shape(raw: object) -> tuple[str, urllib.parse.SplitResult]:
    if not isinstance(raw, str) or not raw or len(raw) > _MAX_URL:
        raise PublicResearchReadError("public URL is invalid")
    if any(ord(ch) < 32 or ch.isspace() for ch in raw):
        raise PublicResearchReadError("public URL is invalid")
    parsed = urllib.parse.urlsplit(raw)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        raise PublicResearchReadError("public URL must be safe HTTPS without credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise PublicResearchReadError("public URL has invalid port") from exc
    if port not in (None, 443):
        raise PublicResearchReadError("public URL must use HTTPS port 443")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise PublicResearchReadError("public URL has no host")
    clean = urllib.parse.urlunsplit(
        ("https", parsed.netloc, parsed.path or "/", parsed.query, "")
    )
    return clean, parsed


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def _public_url_details(
    raw: object,
    *,
    resolver: Callable[..., list] = socket.getaddrinfo,
) -> tuple[str, tuple[str, ...]]:
    """Admit one public URL and return the exact public DNS addresses."""
    clean, parsed = _url_shape(raw)
    host = (parsed.hostname or "").rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise PublicResearchReadError("public URL must not use a private host")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise PublicResearchReadError("public URL must not use a private host")
        return clean, (str(literal),)
    try:
        records = resolver(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise PublicResearchReadError("public host cannot be resolved") from exc
    addresses = tuple(sorted({
        str(row[4][0])
        for row in records
        if len(row) >= 5 and isinstance(row[4], tuple) and row[4]
    }))
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise PublicResearchReadError("public URL must resolve only to public hosts")
    return clean, addresses


def validate_public_url(
    raw: object,
    *,
    resolver: Callable[..., list] = socket.getaddrinfo,
) -> str:
    """Admit one public HTTPS URL after literal/DNS public-address checks."""
    return _public_url_details(raw, resolver=resolver)[0]


def _candidate_url(raw: object) -> str:
    """Reject structurally unsafe/literal-private candidates; DNS waits for open."""
    clean, parsed = _url_shape(raw)
    host = (parsed.hostname or "").rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise PublicResearchReadError("search candidate uses a private host")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        raise PublicResearchReadError("search candidate uses a private host")
    return clean


def _candidate_text(value: object, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def search_public_sources(
    request: Mapping[str, Any],
    *,
    backend: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute one injected search backend and normalize discovery candidates."""
    if request.get("schema") != "brain.public_evidence_request.v1":
        raise PublicResearchContractError("public evidence request is not normalized")
    try:
        raw = backend(dict(request))
    except Exception:
        return {
            "status": "unavailable", "reason": "search_backend_error",
            "search_executed": False, "candidates": [],
        }
    if not isinstance(raw, Mapping) or raw.get("executed") is not True:
        return {
            "status": "unavailable", "reason": "search_not_executed",
            "search_executed": False, "candidates": [],
        }

    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for row in raw.get("candidates") or []:
        if not isinstance(row, Mapping):
            continue
        try:
            url = _candidate_url(row.get("url"))
        except PublicResearchReadError:
            continue
        if url in seen:
            continue
        seen.add(url)
        parsed = urllib.parse.urlsplit(url)
        candidates.append({
            "url": url,
            "source_family": (parsed.hostname or "").lower(),
            "title": _candidate_text(row.get("title"), 300),
            "snippet": _candidate_text(row.get("snippet"), 1200),
            "published_at": _candidate_text(row.get("published_at"), 64) or None,
            "opened": False,
            "content_is_untrusted": True,
        })
        if len(candidates) >= 20:
            break
    execution_id = _candidate_text(raw.get("execution_id"), 160) or None
    backend_name = _candidate_text(raw.get("backend"), 80) or "unknown"
    return {
        "status": "available" if candidates else "empty",
        "reason": None if candidates else "no_candidates",
        "search_executed": True,
        "backend": backend_name,
        "execution_id": execution_id,
        "query": request["query"],
        "candidates": candidates,
        "is_context_only": True,
        "authority": "discovery_only",
    }


@dataclass
class PublicHttpResponse:
    status_code: int
    url: str
    headers: Mapping[str, str]
    chunks: Iterable[bytes]
    close: Callable[[], None] | None = None


# Network transport is intentionally not implemented here. A separately
# qualified transport must consume the prevalidated address set supplied by
# open_public_source; this prevents this module from silently re-resolving DNS.


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        low = tag.lower()
        if low in {"script", "style", "noscript", "template"}:
            self._skip += 1
        elif low == "title" and not self._skip:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        low = tag.lower()
        if low in {"script", "style", "noscript", "template"}:
            self._skip = max(0, self._skip - 1)
        elif low == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        clean = " ".join(data.split())
        if not clean:
            return
        if self._in_title:
            self.title_parts.append(clean)
        self.text_parts.append(clean)

    def result(self) -> tuple[str | None, str]:
        title = " ".join(self.title_parts).strip() or None
        return title, " ".join(self.text_parts).strip()


def _decode_source(body: bytes, content_type: str) -> tuple[str | None, str]:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        text = body.decode("utf-8", errors="replace")
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = _TextExtractor()
        parser.feed(text)
        parser.close()
        return parser.result()
    return None, " ".join(text.split())


def _default_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return None


def open_public_source(
    raw_url: object,
    *,
    transport: Callable[..., PublicHttpResponse],
    resolver: Callable[..., list] = socket.getaddrinfo,
    now: Callable[[], str] = _default_now,
    max_redirects: int = 3,
    max_bytes: int = 1_000_000,
    max_text_chars: int = 160_000,
    timeout: tuple[float, float] = (3.0, 7.0),
) -> dict[str, Any]:
    """Open one public text/HTML source with bounded, revalidated redirects."""
    if type(max_redirects) is not int or not 0 <= max_redirects <= 5:
        raise PublicResearchReadError("redirect bound is invalid")
    if type(max_bytes) is not int or not 1 <= max_bytes <= 5_000_000:
        raise PublicResearchReadError("size bound is invalid")
    requested, resolved_addresses = _public_url_details(raw_url, resolver=resolver)
    current = requested
    redirects = 0
    visited = {requested}

    while True:
        response: PublicHttpResponse | None = None
        try:
            response = transport(
                current, timeout=timeout, resolved_addresses=resolved_addresses
            )
            if not isinstance(response, PublicHttpResponse):
                raise PublicResearchReadError("public transport returned invalid response")
            response_url, _ = _url_shape(response.url)
            if response_url != current:
                raise PublicResearchReadError("public response changed URL unexpectedly")

            status = int(response.status_code)
            if status in _REDIRECTS:
                location = _header(response.headers, "Location")
                if not location:
                    raise PublicResearchReadError("public redirect has no location")
                if redirects >= max_redirects:
                    raise PublicResearchReadError("public redirect limit exceeded")
                redirects += 1
                next_url, next_addresses = _public_url_details(
                    urllib.parse.urljoin(current, location), resolver=resolver
                )
                if next_url in visited:
                    raise PublicResearchReadError("public redirect cycle detected")
                visited.add(next_url)
                current = next_url
                resolved_addresses = next_addresses
                continue

            if status < 200 or status >= 300:
                raise PublicResearchReadError(f"public source returned HTTP {status}")

            raw_type = (_header(response.headers, "Content-Type") or "").lower()
            content_type = raw_type.split(";", 1)[0].strip()
            if content_type not in _ALLOWED_TYPES:
                raise PublicResearchReadError("public source content type is not supported")

            content_length = _header(response.headers, "Content-Length")
            if content_length is not None:
                try:
                    if int(content_length) > max_bytes:
                        raise PublicResearchReadError("public source exceeds safe size bound")
                except ValueError:
                    raise PublicResearchReadError("public source has invalid size header") from None

            chunks: list[bytes] = []
            used = 0
            for chunk in response.chunks:
                if not isinstance(chunk, (bytes, bytearray)):
                    raise PublicResearchReadError("public source returned invalid bytes")
                if not chunk:
                    continue
                used += len(chunk)
                if used > max_bytes:
                    raise PublicResearchReadError("public source exceeds safe size bound")
                chunks.append(bytes(chunk))
            body = b"".join(chunks)
            if content_length is not None and _header(response.headers, "Content-Encoding") is None:
                if int(content_length) != len(body):
                    raise PublicResearchReadError("public source size header does not match body")
            title, text = _decode_source(body, content_type)
            if not body or not text.strip():
                raise PublicResearchReadError("public source is empty")
            truncated = len(text) > max_text_chars
            if truncated:
                text = text[:max_text_chars].rstrip()
            return {
                "schema": "brain.opened_public_source.v1",
                "status": "opened",
                "requested_url": requested,
                "final_url": current,
                "redirect_count": redirects,
                "fetched_at": now(),
                "content_type": content_type,
                "byte_length": len(body),
                "content_sha256": hashlib.sha256(body).hexdigest(),
                "title": title,
                "text": text,
                "text_truncated": truncated,
                "content_is_untrusted": True,
                "is_context_only": True,
                "authority": "opened_public_evidence",
            }
        finally:
            if response is not None and response.close is not None:
                response.close()
