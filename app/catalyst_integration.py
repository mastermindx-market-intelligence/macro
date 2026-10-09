"""Anonymous Catalyst scan HTTP bridge. No event, consent, mail or analytics writes.

Session 00 owns this public serialization/route seam. Source/consent owners remain
engine.marketing.catalyst_scan and app.catalyst_optin respectively. Default OFF.
"""
from __future__ import annotations

import html
import ipaddress
import json
import os
import re
import time
from collections import deque
from threading import Lock
from datetime import datetime, timedelta, timezone
from importlib import import_module
from typing import Any, Callable
from urllib.parse import parse_qsl, unquote, urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app import edge_client

router = APIRouter()
_TICKER = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}\Z")
_EVENT = re.compile(r"[A-Za-z0-9_.:\-]{1,128}\Z")
_SOURCE_URL_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.IGNORECASE)
_STATUSES = {"SUPPORTED", "NOT_COVERED", "TEMPORARILY_UNAVAILABLE", "RIGHTS_BLOCKED"}
_PUBLIC_COVERAGE = {
    "SUPPORTED": "Only rights-qualified public evidence is displayed; other sources may be excluded.",
    "NOT_COVERED": "This ticker is not covered by the currently qualified public event.",
    "TEMPORARILY_UNAVAILABLE": "Current source evidence is unavailable; please try again later.",
    "RIGHTS_BLOCKED": "Source-display permission is not confirmed, so no event details can be shown.",
}
_LIMIT = 10
_FRESHNESS = timedelta(days=7)
_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
_HTML_HEADERS = {**_HEADERS, "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"}
# Process-local guard only. The canonical edge/server remains responsible for
# distributed anti-abuse; this protects worker resources before that gate.
_RATE_LIMITS = {"scan": (30, 60.0)}
# A looser trusted-Caddy-peer key bounds direct-origin spoofed visitor headers,
# without turning legitimate CDN visitors into one tiny quota bucket.
_PEER_LIMITS = {"scan": 2400}
_MAX_RATE_KEYS = 8192
_RATE_LOCK = Lock()
_RATE_BUCKETS: dict[tuple[str, str], deque[float]] = {}


def _allow_request(request: Request, lane: str, *, now: float | None = None) -> bool:
    limit, window = _RATE_LIMITS[lane]
    current = time.monotonic() if now is None else float(now)
    # Both claimed visitor and trusted TCP peer buckets book the attempt. An
    # attacker hitting the origin directly cannot evade the peer bucket simply
    # by rotating forged EO-Connecting-IP headers.
    claimed = edge_client.client_ip(request.headers)
    peer = edge_client.trusted_peer(request.headers)
    keys = [((lane, "ip:" + claimed), limit)]
    if peer:
        keys.append(((lane, "peer:" + peer), _PEER_LIMITS[lane]))
    with _RATE_LOCK:
        new_keys = sum(k not in _RATE_BUCKETS for k, _ in keys)
        while len(_RATE_BUCKETS) + new_keys > _MAX_RATE_KEYS:
            oldest = min(_RATE_BUCKETS, key=lambda k: _RATE_BUCKETS[k][-1])
            del _RATE_BUCKETS[oldest]
        cutoff = current - window
        permitted = True
        for key, cap in keys:
            bucket = _RATE_BUCKETS.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= cap:
                permitted = False
            else:
                bucket.append(current)
        return permitted


def _rate_or_429(request: Request, lane: str) -> None:
    if not _allow_request(request, lane):
        raise HTTPException(429, "Request limit exceeded", headers={"Retry-After": "60"})


async def _read_json(request: Request, *, max_bytes: int = 8192) -> Any:
    # Reject oversized bodies while streaming, before JSON parsing or owner calls.
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > max_bytes:
            raise HTTPException(413, "Request too large")
        chunks.extend(chunk)
    try:
        return json.loads(chunks)
    except (ValueError, UnicodeError, TypeError):
        raise HTTPException(400, "Invalid JSON") from None


def _reset_rate_limits_for_tests() -> None:
    with _RATE_LOCK:
        _RATE_BUCKETS.clear()



def _enabled(name: str) -> bool:
    # No implicit staging/prod publication. An explicit operational admission is required.
    return os.environ.get(name, "").strip() == "1"


def _require_enabled(name: str) -> None:
    if not _enabled(name):
        raise HTTPException(503, "Catalyst scan is not publicly enabled")


def normalize_tickers(raw: Any) -> list[str]:
    """Validate BEFORE contacting a producer; dedupe preserving order."""
    parts = raw.split(",") if isinstance(raw, str) else raw
    if not isinstance(parts, list) or not 1 <= len(parts) <= _LIMIT:
        raise HTTPException(400, "Provide 1 to 10 tickers")
    out: list[str] = []
    for value in parts:
        if not isinstance(value, str):
            raise HTTPException(400, "Invalid ticker")
        ticker = value.strip().upper()
        if not _TICKER.fullmatch(ticker):
            raise HTTPException(400, "Invalid ticker")
        if ticker not in out:
            out.append(ticker)
    return out


def _event_id(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str) or not _EVENT.fullmatch(raw):
        raise HTTPException(400, "Invalid event reference")
    return raw


def _utc(raw: Any, now: datetime, *, fresh: bool = True) -> str:
    if not isinstance(raw, str) or len(raw) > 40:
        raise ValueError("missing UTC clock")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("bad UTC clock") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError("non-UTC clock")
    dt = dt.astimezone(timezone.utc)
    if dt > now + timedelta(minutes=5) or (fresh and now - dt > _FRESHNESS):
        raise ValueError("outdated or future clock")
    return dt.isoformat().replace("+00:00", "Z")


def _public_url(raw: Any) -> str:
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ValueError("invalid source URL")
    u = urlsplit(raw)
    if (u.scheme != "https" or not u.hostname or u.username or u.password
            or u.port not in (None, 443) or u.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
            or u.hostname.endswith(".internal") or u.hostname.endswith(".local")
            or any(ord(c) < 32 for c in raw)):
        raise ValueError("non-public source URL")
    # A public "source" link must never contain authentication or subscriber PII.
    forbidden_keys = {"email", "e_mail", "phone", "ip", "token", "access_token",
                      "auth", "authorization", "api_key", "apikey", "secret",
                      "session", "user_id", "session_id", "signature", "password",
                      "credential", "client_secret", "jwt", "bearer"}
    # Source links may be forwarded to a third party by the browser. Inspect
    # decoded path/query/fragment as well as the original spelling; a private
    # parameter hidden under #token= or ?ref=ok%26token%3D... is still private.
    # Never rewrite a safe provider URL; only accept the original or deny it.
    decoded_url = raw
    for _ in range(4):
        try:
            decoded_parts = urlsplit(decoded_url)
        except ValueError:
            raise ValueError("invalid encoded source URL") from None
        fields = (parse_qsl(decoded_parts.query, keep_blank_values=True) +
                  parse_qsl(decoded_parts.fragment, keep_blank_values=True))
        if any(key.lower() in forbidden_keys for key, _ in fields):
            raise ValueError("private source URL parameter")
        if (_SOURCE_URL_EMAIL.search(decoded_url) or
                any(ord(ch) < 32 or ord(ch) == 127 for ch in decoded_url)):
            raise ValueError("identity or control in public source URL")
        expanded = unquote(decoded_url)
        if expanded == decoded_url:
            break
        decoded_url = expanded
    else:
        # Reject unbounded decoding rather than leave a fifth layer hiding
        # private keys, recipient identifiers, or control characters.
        if unquote(decoded_url) != decoded_url:
            raise ValueError("excessive source URL encoding")
    if (_SOURCE_URL_EMAIL.search(decoded_url) or
            any(ord(ch) < 32 or ord(ch) == 127 for ch in decoded_url)):
        raise ValueError("identity or control in public source URL")
    try:
        ipaddress.ip_address(u.hostname)
    except ValueError:
        return raw
    raise ValueError("literal source IP not allowed")


def _claims(raw: Any, text_key: str, sources: set[str], allowed_cases: bool = False) -> list[dict]:
    if not isinstance(raw, list) or len(raw) > 10:
        raise ValueError("invalid evidence list")
    out = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("invalid claim")
        ids = item.get("evidence_ids")
        txt = item.get(text_key)
        if (not isinstance(ids, list) or not ids or len(ids) > 8
                or any(not isinstance(x, str) or x not in sources for x in ids)
                or not isinstance(txt, str) or not txt.strip() or len(txt) > 400):
            raise ValueError("unsupported claim")
        claim = {text_key: txt.strip(), "evidence_ids": list(dict.fromkeys(ids))}
        if allowed_cases:
            case = item.get("case")
            if case not in ("BULL", "BASE", "BEAR"):
                raise ValueError("invalid scenario")
            claim["case"] = case
        out.append(claim)
    return out


def sanitize_public_scan(raw: Any, tickers: list[str], now_utc: datetime | None = None) -> dict:
    """Second deny-by-default serialization boundary over the 01 producer result.

    Do not forward arbitrary producer fields, including private bodies/scores/PII.
    Any malformed SUPPORTED material aborts the whole response, not a partial leak.
    """
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(raw, dict) or raw.get("schema") != "catalyst.scan/v1" or raw.get("schema_version") != 1:
        raise ValueError("unsupported scan schema")
    if raw.get("requested_tickers") != tickers:
        raise ValueError("ticker identity mismatch")
    publication = raw.get("publication_state")
    if publication not in ("PUBLIC_QUALIFIED", "PARTIAL", "UNAVAILABLE"):
        raise ValueError("invalid publication state")
    if publication == "UNAVAILABLE":
        raise ValueError("source unavailable")
    as_of = _utc(raw.get("as_of_utc"), now)
    generation = raw.get("generation")
    if generation is not None and (type(generation) is not int or generation < 0):
        raise ValueError("invalid generation")
    event_id = _event_id(raw.get("event_id"))
    results = raw.get("results")
    if not isinstance(results, list) or len(results) != len(tickers):
        raise ValueError("result mismatch")
    public_results = []
    for ticker, item in zip(tickers, results):
        if not isinstance(item, dict) or item.get("ticker") != ticker:
            raise ValueError("result identity mismatch")
        status = item.get("status")
        if status not in _STATUSES:
            raise ValueError("invalid status")
        # Never forward an upstream coverage_note on a blocked or supported path:
        # it may contain unqualified proprietary text, PII, or a score.
        coverage = _PUBLIC_COVERAGE[status]
        # Denial cases never carry hidden field content even if a producer supplies it.
        if status != "SUPPORTED":
            public_results.append({"ticker": ticker, "status": status, "coverage_note": coverage,
                                   "what_changed": [], "scenarios": [], "invalidators": [], "sources": []})
            continue
        if not event_id or generation is None or item.get("correction_state") not in ("CURRENT", "CORRECTED"):
            raise ValueError("unqualified event generation")
        relation = item.get("relationship")
        if relation not in ("DIRECT", "EVIDENCED_INDIRECT"):
            raise ValueError("unproven relationship")
        if item.get("public_safe") is not True:
            raise ValueError("not approved for public display")
        item_as_of = _utc(item.get("as_of_utc"), now)
        src_raw = item.get("sources")
        if not isinstance(src_raw, list) or not 1 <= len(src_raw) <= 12:
            raise ValueError("no public sources")
        sources = []
        seen_source_ids: set[str] = set()
        for s in src_raw:
            if not isinstance(s, dict) or s.get("display_rights") != "ALLOWED":
                raise ValueError("source rights missing")
            sid, receipt, title = s.get("source_id"), s.get("rights_receipt_id"), s.get("title")
            if (not isinstance(sid, str) or not _EVENT.fullmatch(sid)
                    or not isinstance(receipt, str) or not receipt.strip() or len(receipt) > 128
                    or not isinstance(title, str) or not title.strip() or len(title) > 150):
                raise ValueError("invalid source receipt")
            if sid in seen_source_ids:
                raise ValueError("ambiguous duplicate source ID")
            seen_source_ids.add(sid)
            sources.append({"source_id": sid, "rights_receipt_id": receipt,
                            "display_rights": "ALLOWED", "title": title.strip(),
                            "url": _public_url(s.get("url")),
                            "published_at_utc": _utc(s.get("published_at_utc"), now, fresh=False)})
        ids = {s["source_id"] for s in sources}
        relation_ids = item.get("relationship_evidence_ids", [])
        if (not isinstance(relation_ids, list) or any(x not in ids for x in relation_ids)
                or (relation == "EVIDENCED_INDIRECT" and not relation_ids)):
            raise ValueError("unsubstantiated relationship")
        dossier = item.get("dossier_path")
        if dossier is not None and dossier != f"/stocks/{ticker}/":
            raise ValueError("unsafe dossier path")
        headline = item.get("headline")
        if not isinstance(headline, str) or not headline.strip() or len(headline) > 180:
            raise ValueError("invalid headline")
        headline_ids = item.get("headline_evidence_ids")
        if (not isinstance(headline_ids, list) or not headline_ids
                or any(x not in ids for x in headline_ids)):
            raise ValueError("unsupported headline")
        changed = _claims(item.get("what_changed", []), "text", ids)
        if not changed:
            raise ValueError("unsupported empty coverage")
        public_results.append({"ticker": ticker, "status": "SUPPORTED", "headline": headline.strip(),
                               "relationship": relation, "relationship_evidence_ids": relation_ids,
                               "headline_evidence_ids": list(dict.fromkeys(headline_ids)),
                               "correction_state": item["correction_state"], "as_of_utc": item_as_of,
                               "what_changed": changed,
                               "scenarios": _claims(item.get("scenarios", []), "trigger", ids, True),
                               "invalidators": _claims(item.get("invalidators", []), "text", ids),
                               "sources": sources, "dossier_path": dossier, "coverage_note": coverage})
    note = "Limited coverage from rights-qualified public sources; source times are shown."
    return {"schema": "catalyst.scan/v1", "schema_version": 1, "event_id": event_id,
            "generation": generation, "as_of_utc": as_of, "publication_state": publication,
            "requested_tickers": tickers, "coverage_note": note,
            "results": public_results}


def scan_with_reader(tickers: Any, event_id: Any = None, *,
                     reader: Callable[..., dict] | None = None,
                     now_utc: datetime | None = None) -> dict:
    normalized = normalize_tickers(tickers)
    event = _event_id(event_id)
    if reader is None:
        try:
            reader = import_module("engine.marketing.catalyst_scan").scan_tickers
        except (ImportError, AttributeError) as exc:
            raise HTTPException(503, "Qualified event source unavailable") from exc
    try:
        result = reader(normalized, event_id=event, now_utc=now_utc)
        return sanitize_public_scan(result, normalized, now_utc=now_utc)
    except HTTPException:
        raise
    except Exception as exc:
        # No raw upstream exceptions/PII/scores/sources can enter public responses.
        raise HTTPException(503, "Qualified event source unavailable") from exc


def public_scan_with_receipt(tickers: Any, event_id: Any = None) -> dict:
    """Display facts come first; a receipt is optional and never proves consent.

    The 02 opt-in router alone accepts consent and verification. An unsigned
    or unconfigured scan still returns its public value, without a proof token.
    """
    scan = scan_with_reader(tickers, event_id)
    try:
        from app.catalyst_scan_authority import ScanReceiptAuthority
        receipt = ScanReceiptAuthority().issue(scan)
    except Exception:
        receipt = None
    return {**scan, "scan_receipt": receipt} if receipt else scan


@router.post("/api/catalyst/scan")
async def scan_post(request: Request):
    _require_enabled("CATALYST_PUBLIC_ENABLED")
    _rate_or_429(request, "scan")
    body = await _read_json(request)
    if not isinstance(body, dict) or set(body) - {"tickers", "event_id"}:
        raise HTTPException(400, "Invalid scan request")
    return JSONResponse(public_scan_with_receipt(body.get("tickers"), body.get("event_id")), headers=_HEADERS)


@router.post("/api/catalyst/optin/request")
async def optin_request(request: Request):
    """Delegate only to Session 02's secure owner; never grant consent here."""
    _require_enabled("CATALYST_PUBLIC_ENABLED")
    _require_enabled("CATALYST_OPTIN_ENABLED")
    _rate_or_429(request, "scan")
    # Public consent requests must not be accepted as browser-simple form/text
    # cross-origin POSTs. The verified sender/identity owners remain downstream.
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(415, "application/json required")
    body = await _read_json(request, max_bytes=4096)
    if not isinstance(body, dict):
        raise HTTPException(400, "Invalid opt-in request")
    # The *only* supported identity/OTP/consent implementation is Session 02.
    # No fallback: a missing module, owner RPC, or configured service yields 503.
    try:
        from app.catalyst_optin import request_optin, _abuse_guard
        from engine.marketing.catalyst_lifecycle import FunnelGate
    except ImportError:
        raise HTTPException(503, "Verification service unavailable") from None
    try:
        # Account-affecting OTP requests must use the SAME shared abuse owner
        # as Session 02's verify route, not just the anonymous scan limiter.
        # A missing shared guard is 503, never an unthrottled identity effect.
        _abuse_guard(request)
        result = request_optin(body)
    except FunnelGate as exc:
        raise HTTPException(exc.status, exc.code) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Verification service unavailable") from None
    if (not isinstance(result, dict) or result.get("status") != "VERIFICATION_REQUIRED"
            or not isinstance(result.get("public_ref"), str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", result["public_ref"])):
        raise HTTPException(503, "Verification service unavailable")
    return JSONResponse({"status": "VERIFICATION_REQUIRED",
                         "public_ref": result["public_ref"]}, status_code=202, headers=_HEADERS)


@router.get("/api/catalyst/scan")
def scan_get(request: Request, tickers: str, event_id: str | None = None):
    _require_enabled("CATALYST_PUBLIC_ENABLED")
    _rate_or_429(request, "scan")
    return JSONResponse(public_scan_with_receipt(tickers, event_id), headers=_HEADERS)


def render_first_value(data: dict | None, value: str = "", error: str = "") -> str:
    """Accessible no-JS first-value fallback until sibling 03 shell is accepted."""
    e = html.escape
    content = "<p>Enter up to ten tickers to see dated, source-backed earnings coverage. No account required.</p>"
    if error:
        content += f'<p role="alert">{e(error)}</p>'
    if data:
        content += f'<p>As of {e(data["as_of_utc"])} · {e(data["coverage_note"])}</p>'
        for item in data["results"]:
            content += f'<section aria-label="{e(item["ticker"])}"><h2>{e(item["ticker"])} · {e(item["status"])}</h2>'
            if item["status"] == "SUPPORTED":
                content += f'<h3>{e(item["headline"])}</h3>'
                content += (
                    f'<p>Evidence checked <time datetime="{e(item["as_of_utc"], quote=True)}">'
                    f'{e(item["as_of_utc"])}</time>. '
                    f'Relationship: {e(item["relationship"])}. '
                    f'Correction state: {e(item["correction_state"])}.</p>'
                )
                content += '<h4>What changed</h4><ul>'
                for claim in item["what_changed"]:
                    content += f'<li>{e(claim["text"])}</li>'
                content += '</ul>'
                if item["scenarios"]:
                    content += '<h4>Conditional scenarios, not predictions</h4><ul>'
                    for scenario in item["scenarios"]:
                        content += f'<li>{e(scenario["case"])}: {e(scenario["trigger"])}</li>'
                    content += '</ul>'
                if item["invalidators"]:
                    content += '<h4>What could invalidate this reading</h4><ul>'
                    for invalidator in item["invalidators"]:
                        content += f'<li>{e(invalidator["text"])}</li>'
                    content += '</ul>'
                content += '<h4>Public source references</h4><ul>'
                for src in item["sources"]:
                    content += (
                        f'<li><a rel="noopener noreferrer" href="{e(src["url"], quote=True)}">'
                        f'{e(src["title"])}</a> · published '
                        f'<time datetime="{e(src["published_at_utc"], quote=True)}">'
                        f'{e(src["published_at_utc"])}</time></li>'
                    )
                content += '</ul>'
                if item["dossier_path"]:
                    content += f'<a href="{e(item["dossier_path"], quote=True)}">Public company dossier</a>'
                content += '<p>Want a meaningful correction/update? Opt-in is optional and requires separate email verification.</p>'
            else:
                content += f'<p>{e(item["coverage_note"])}</p>'
            content += '</section>'
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Earnings Risk Scan — Mastermind</title>"
            "<style>body{font:16px/1.6 system-ui;color:#edf2fd;background:#101928;max-width:760px;"
            "margin:auto;padding:24px}a{color:#a2d9ff}input,button{font:inherit;padding:10px;"
            "max-width:100%;box-sizing:border-box}section{border-top:1px solid #536277;padding:12px 0}"
            "</style><main><h1>Earnings Risk Scan</h1>"
            "<form action='/api/catalyst' method='get'><label for='t'>Tickers (comma-separated)</label>"
            f"<p><input id='t' name='tickers' required maxlength='119' value='{e(value, quote=True)}' "
            "placeholder='NVDA, AMD' autocomplete='off'> <button type='submit'>Scan</button></p></form>"
            + content + "<footer><p>Limited coverage, delayed source times. Information only; not investment advice.</p>"
            "</footer></main></html>")


@router.get("/api/catalyst", response_class=HTMLResponse)
def first_value(request: Request, tickers: str = "", event_id: str | None = None):
    _require_enabled("CATALYST_PUBLIC_ENABLED")
    _rate_or_429(request, "scan")
    if not tickers:
        return HTMLResponse(render_first_value(None), headers=_HTML_HEADERS)
    try:
        data = public_scan_with_receipt(tickers, event_id)
    except HTTPException as exc:
        # Never echo private producer details or unsupported claims in the HTML fallback.
        return HTMLResponse(render_first_value(None, tickers[:119], str(exc.detail)),
                            status_code=exc.status_code, headers=_HTML_HEADERS)
    return HTMLResponse(render_first_value(data, tickers[:119]), headers=_HTML_HEADERS)
