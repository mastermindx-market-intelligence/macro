"""Authenticated transport for the published International policy comparison.

One bounded route: it authenticates the caller with the existing Macro Command
auth owner, validates the request envelope, and republishes the typed result of
the separately-owned publication helper unchanged. It selects no source, reads no
published file, computes no arithmetic, translates no selector and caches
nothing.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app import macro_command

router = APIRouter()

BODY_MAX_BYTES = 16384
TEXT_MAX_CHARS = 4096
MAX_NODES = 10000
PREVIEW_SCHEMA = "intl.policy_preview.v1"

_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Robots-Tag": "noindex, noarchive",
}
_REQUEST_KEYS = frozenset({"generation", "fingerprint", "settings"})
_SETTINGS_KEYS = frozenset({
    "economy_a",
    "economy_b",
    "lens",
    "definition",
    "method_version",
    "period",
    "instrument_a_ref",
    "instrument_b_ref",
    "revision_policy",
})
_GENERATION_RE = re.compile(r"im-workspace-generation:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")
_ECONOMY_RE = re.compile(r"[A-Z]{2}")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_LENS = "nominal_policy_point_gap"
_DEFINITION = "absolute_gap_change_bp"
_REVISION_POLICIES = frozenset({"latest_vintage", "original_known"})
_PREVIEW_STATES = frozenset({"qualified", "unavailable", "invalid"})


def _bad_request() -> HTTPException:
    return HTTPException(
        status_code=400,
        detail="invalid policy preview request",
        headers=_PRIVATE_HEADERS,
    )


def _too_large() -> HTTPException:
    return HTTPException(
        status_code=413,
        detail="policy preview request too large",
        headers=_PRIVATE_HEADERS,
    )


def _unavailable() -> JSONResponse:
    # One fixed body: no exception text, no source detail.
    return JSONResponse(
        {"error": "policy preview unavailable"},
        status_code=503,
        headers=_PRIVATE_HEADERS,
    )


def _require_user(authorization: str | None = Header(default=None)) -> dict:
    """Authenticate with the canonical Macro Command auth owner.

    The owner is resolved per request so the shared identity cache stays the one
    and only auth path. Its 401/502 answers keep their canonical status and
    detail; only the private cache headers are added, without touching any
    global handler.
    """
    try:
        return macro_command.require_user(authorization)
    except HTTPException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={**{key: value for key, value in (exc.headers or {}).items()
                        if key.lower() not in {"cache-control", "x-robots-tag"}},
                     **_PRIVATE_HEADERS},
        ) from None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    # A repeated key is a malformed body, never a last-wins merge.
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> None:
    # NaN and the infinities are not JSON numbers.
    raise ValueError(f"nonstandard JSON constant: {value}")


def _numbers_are_finite(value: Any) -> bool:
    # 1e999 parses to infinity without ever reaching the constant hook.
    stack = [value]
    nodes = 0
    while stack:
        node = stack.pop()
        nodes += 1
        if nodes > MAX_NODES:
            return False
        if isinstance(node, float):
            if not math.isfinite(node):
                return False
        elif isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return True


def _is_text(value: Any) -> bool:
    # Nonempty, already trimmed, bounded selector text.
    return (
        type(value) is str
        and 0 < len(value) <= TEXT_MAX_CHARS
        and value.strip() == value
    )


def _is_economy(value: Any) -> bool:
    return type(value) is str and _ECONOMY_RE.fullmatch(value) is not None


def _is_date(value: Any) -> bool:
    if type(value) is not str or _DATE_RE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_period(value: Any) -> bool:
    if type(value) is not dict:
        return False
    mode = value.get("mode")
    if mode == "fixed_dates":
        if set(value) != {"mode", "start", "end"}:
            return False
        if not _is_date(value["start"]) or not _is_date(value["end"]):
            return False
        return value["end"] >= value["start"]
    if mode == "owner_horizon":
        if set(value) != {"mode", "key"}:
            return False
        return _is_text(value["key"])
    return False


def _is_settings(value: Any) -> bool:
    if type(value) is not dict or set(value) != _SETTINGS_KEYS:
        return False
    if not _is_economy(value["economy_a"]) or not _is_economy(value["economy_b"]):
        return False
    if value["economy_a"] == value["economy_b"]:
        return False
    if value["lens"] != _LENS or value["definition"] != _DEFINITION:
        return False
    if type(value["revision_policy"]) is not str or value["revision_policy"] not in _REVISION_POLICIES:
        return False
    if not _is_text(value["method_version"]):
        return False
    for key in ("instrument_a_ref", "instrument_b_ref"):
        if value[key] is not None and not _is_text(value[key]):
            return False
    return _is_period(value["period"])


def _is_generation(value: Any) -> bool:
    return type(value) is str and _GENERATION_RE.fullmatch(value) is not None


def _is_fingerprint(value: Any) -> bool:
    return type(value) is str and _FINGERPRINT_RE.fullmatch(value) is not None


async def _read_body(request: Request) -> bytes:
    """Read at most BODY_MAX_BYTES of actual bytes.

    The declared Content-Length is not authoritative: a client may understate
    it, so the cap is applied to the bytes that actually arrive.
    """
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > BODY_MAX_BYTES:
            raise _too_large()
        body.extend(chunk)
    return bytes(body)


def _parse_body(raw: bytes) -> dict:
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except (ValueError, RecursionError):
        # A decode error is a ValueError, and so is a rejected duplicate key.
        raise _bad_request() from None
    if type(payload) is not dict or set(payload) != _REQUEST_KEYS:
        raise _bad_request()
    if not _numbers_are_finite(payload):
        raise _bad_request()
    return payload


def _envelope(raw: Any, generation: str, fingerprint: str) -> dict:
    """Republish the helper's typed result unchanged, or refuse it."""
    if type(raw) is not dict or set(raw) != {
        "schema", "state", "source_generation", "artifact_sha256",
        "mapping_identity", "qualification_identity", "result",
    } or raw["schema"] != PREVIEW_SCHEMA:
        raise ValueError("helper result")
    state = raw.get("state")
    if type(state) is not str or state not in _PREVIEW_STATES:
        raise ValueError("helper state")
    source_generation = raw.get("source_generation")
    if type(source_generation) is not str or source_generation != generation:
        raise ValueError("helper generation")
    artifact_sha256 = raw.get("artifact_sha256")
    if type(artifact_sha256) is not str or artifact_sha256 != fingerprint:
        raise ValueError("helper artifact")
    mapping_identity = raw.get("mapping_identity")
    if mapping_identity is not None and not _is_text(mapping_identity):
        raise ValueError("helper mapping identity")
    qualification_identity = raw.get("qualification_identity")
    if qualification_identity is not None and not _is_text(qualification_identity):
        raise ValueError("helper qualification identity")
    result = raw.get("result")
    if type(result) is not dict or result.get("state") != state:
        raise ValueError("helper comparator result")
    if state == "qualified" and (mapping_identity is None or qualification_identity is None):
        raise ValueError("qualified identities unavailable")
    return {
        "schema": PREVIEW_SCHEMA,
        "state": state,
        "source_generation": source_generation,
        "artifact_sha256": artifact_sha256,
        "mapping_identity": mapping_identity,
        "qualification_identity": qualification_identity,
        "result": result,
    }


def _feed_base():
    # Existing deployment-owned R2 origin; request selectors cannot choose it.
    from app.main import _flow_r2_base
    return _flow_r2_base()


@router.post("/api/macro/policy-preview")
async def macro_policy_preview(request: Request, _user: dict = Depends(_require_user)):
    # The auth owner has already answered before any body byte is read.
    try:
        payload = _parse_body(await _read_body(request))
        generation = payload["generation"]
        fingerprint = payload["fingerprint"]
        settings = payload["settings"]
        if not _is_generation(generation) or not _is_fingerprint(fingerprint):
            raise _bad_request()
        if not _is_settings(settings):
            raise _bad_request()
    except HTTPException:
        raise
    except Exception:
        return _unavailable()

    try:
        # The existing configured feed origin is fixed by deployment.
        feed_base = _feed_base()
        evaluated_at = datetime.now(timezone.utc).isoformat()
        # Lazy import: the publication owner is a separate module and may be absent.
        from lib.intl_policy_publication import preview_published_policy_points

        raw_result = await run_in_threadpool(
            preview_published_policy_points,
            feed_base=feed_base,
            source_generation=generation,
            artifact_sha256=fingerprint,
            settings=settings,
            evaluated_at=evaluated_at,
        )
        envelope = _envelope(raw_result, generation, fingerprint)
        # Refuses any non-JSON number the helper may have produced.
        json.dumps(envelope, allow_nan=False)
        return JSONResponse(envelope, headers=_PRIVATE_HEADERS)
    except Exception:
        return _unavailable()
