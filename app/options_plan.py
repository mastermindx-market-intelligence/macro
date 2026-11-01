"""Private Plan expiry consumer. Source observations are never accepted over HTTP."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.options_auth import resolve_entitled_options_principal
from app.options_plan_source import MAX_BYTES, PlanSourceUnavailable, prepare_retained_plan
from engine.intelligence_workspace.options_use import OptionUseRefused

router = APIRouter(prefix="/api/options/plan", tags=["options-plan"])
HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization, Cookie",
           "X-Content-Type-Options": "nosniff"}


def require_plan_access(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "unauthenticated", headers=HEADERS)
    try:
        return resolve_entitled_options_principal(authorization[7:])
    except OptionUseRefused as exc:
        status = 401 if exc.code == "authentication_unavailable" else 403
        raise HTTPException(status, exc.code, headers=HEADERS) from None


def _strict_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate_key")
        out[key] = value
    return out


async def _payload(request):
    if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise HTTPException(415, "application_json_required", headers=HEADERS)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(413, "plan_too_large", headers=HEADERS)
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks), object_pairs_hook=_strict_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    except (ValueError, UnicodeError, RecursionError):
        raise HTTPException(422, "invalid_plan_request", headers=HEADERS) from None



@router.post("/expiry")
async def plan_expiry(request: Request, _principal=Depends(require_plan_access)):
    payload = await _payload(request)
    # A qualified fixed artifact must be installed privately by its existing
    # owner. This route never acquires provider data or creates that artifact.
    if os.environ.get("OPTIONS_PLAN_REFERENCE_ENABLED") != "1":
        return JSONResponse({"status": "UNAVAILABLE", "reason": "contract_terms_unavailable"},
                            status_code=503, headers=HEADERS)
    try:
        from starlette.concurrency import run_in_threadpool
        result = await run_in_threadpool(prepare_retained_plan, payload,
            reference_path=Path(os.environ.get("OPTIONS_PLAN_REFERENCE_PATH", "")),
            expected_sha256=os.environ.get("OPTIONS_PLAN_REFERENCE_SHA256", ""))
        return JSONResponse(result, headers=HEADERS)
    except PlanSourceUnavailable:
        return JSONResponse({"status": "UNAVAILABLE", "reason": "contract_terms_unavailable"},
                            status_code=503, headers=HEADERS)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return JSONResponse({"status": "INVALID", "reason": "invalid_plan_request"},
                            status_code=422, headers=HEADERS)
    except Exception:
        return JSONResponse({"status": "UNAVAILABLE", "reason": "contract_terms_unavailable"},
                            status_code=503, headers=HEADERS)
