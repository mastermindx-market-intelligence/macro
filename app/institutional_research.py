"""Entitled, read-only institutional holding research over the native owner."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.forensics import require_site_full_user

router = APIRouter()
_PATH = "/api/forensics/v1/institutional/reported-holding"
_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}
_MAX_BODY_BYTES = 4096
_MAX_RESPONSE_BYTES = 64 * 1024
_FIELDS = {"filer_cik", "report_period", "accession", "infotable_sk", "decision_cutoff", "generation_id"}


def _error(status, detail, headers=None):
    return HTTPException(status, detail, headers={**(headers or {}), **_HEADERS})


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON field")
        out[key] = value
    return out


def _nonfinite(value):
    raise ValueError("non-finite JSON")


def _selection(raw):
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_nonfinite)
    if type(value) is not dict or set(value) - _FIELDS or _FIELDS - {"generation_id"} - set(value):
        raise ValueError("unexpected selection fields")
    def matches(key, pattern):
        item = value[key]
        if type(item) is not str or re.fullmatch(pattern, item) is None:
            raise ValueError("invalid selection")
        return item
    matches("filer_cik", r"[0-9]{10}")
    matches("accession", r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
    period = matches("report_period", r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
    date.fromisoformat(period)
    # Native row keys exceed JavaScript's exact-number range. Accept canonical
    # decimal text only; conversion to the owner's Python integer is lossless.
    row_key = matches("infotable_sk", r"0|[1-9][0-9]{0,18}")
    if int(row_key) > 2**63 - 1:
        raise ValueError("row key outside owner range")
    cutoff = matches("decision_cutoff", r"[0-9]{4}-[0-9]{2}-[0-9]{2}T.{1,45}(?:Z|\+00:00)")
    parsed = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("UTC cutoff required")
    generation = value.get("generation_id")
    if generation is not None and (type(generation) is not str or re.fullmatch(r"i13fgen_[0-9a-f]{64}", generation) is None):
        raise ValueError("invalid generation")
    return {**value, "infotable_sk": int(row_key), "generation_id": generation}


def _read_holding_context(**selection):
    from engine.institutional_census.research_context import read_reported_holding_context
    return read_reported_holding_context(**selection)


@router.post(_PATH)
async def reported_holding(request: Request, _user: dict = Depends(require_site_full_user)):
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise _error(415, "JSON selection required")
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > _MAX_BODY_BYTES:
                raise _error(413, "institutional selection too large")
            body.extend(chunk)
    except HTTPException:
        raise
    except Exception:
        raise _error(400, "institutional selection could not be read") from None
    try:
        selection = _selection(bytes(body))
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise _error(400, "invalid institutional selection") from None
    try:
        payload = await run_in_threadpool(_read_holding_context, **selection)
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ValueError("response bound")
    except Exception:
        raise _error(503, "institutional research temporarily unavailable") from None
    return Response(raw, media_type="application/json", headers=_HEADERS)


@router.api_route(_PATH, methods=["GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"])
def unsupported_method(_user: dict = Depends(require_site_full_user)):
    raise _error(405, "read-only POST selection required", {"Allow": "POST"})
