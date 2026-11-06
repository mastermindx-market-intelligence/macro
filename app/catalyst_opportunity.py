"""Entitled current Catalyst attention view; no public or historical data route."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user

router = APIRouter()
log = logging.getLogger("macro.catalyst_opportunity")
_REPO_ROOT = Path(os.environ.get("MACRO_REPO") or Path(__file__).resolve().parents[1])
_READ_ADMISSION = BoundedSemaphore(2)


@router.get("/api/catalyst-opportunities/v1")
def catalyst_opportunities_v1(request: Request,
                             _user: dict = Depends(require_site_full_user)) -> JSONResponse:
    """Auth and site-full entitlement precede query validation and all file reads."""
    if request.query_params:
        return JSONResponse({"error": "INVALID_QUERY"}, status_code=400, headers=_PRIVATE_HEADERS)
    if not _READ_ADMISSION.acquire(blocking=False):
        return JSONResponse({"error": "CATALYST_BUSY"}, status_code=503, headers=_PRIVATE_HEADERS)
    try:
        from engine.catalyst_opportunity.reader import read_current_view
        view = read_current_view(_REPO_ROOT)
        status = 503 if view.get("status") == "unavailable" else 200
        return JSONResponse(view, status_code=status, headers=_PRIVATE_HEADERS)
    except Exception as exc:
        log.warning("catalyst opportunity read failed (%s)", type(exc).__name__)
        return JSONResponse({"error": "CATALYST_UNAVAILABLE"}, status_code=503,
                            headers=_PRIVATE_HEADERS)
    finally:
        _READ_ADMISSION.release()
