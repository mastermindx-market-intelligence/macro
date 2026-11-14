"""Private, exact-publication native detail under the existing Prophet reader.

The Daily Brief router includes this child once. Request-scoped access to its
source reader and shared permit preserves the incumbent read lifecycle without
a circular module import or a second cache, source path or semaphore.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user

router = APIRouter()
log = logging.getLogger("macro.prophet_board_detail")
_TICKER = re.compile(r"[A-Z][A-Z0-9.-]{0,31}\Z", re.ASCII)
_SHA = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)


def _error(code: str, status: int) -> JSONResponse:
    return JSONResponse({"error": code}, status_code=status, headers=_PRIVATE_HEADERS)


@router.get("/api/prophet/board-detail/v1")
def board_detail_v1(request: Request, _user: dict = Depends(require_site_full_user)) -> JSONResponse:
    params = request.query_params
    if (set(params) != {"ticker", "source_sha256"}
            or len(params.getlist("ticker")) != 1 or len(params.getlist("source_sha256")) != 1
            or not _TICKER.fullmatch(params["ticker"]) or not _SHA.fullmatch(params["source_sha256"])):
        return _error("INVALID_QUERY", 400)

    from app import prophet_daily_brief as owner  # noqa: PLC0415 — original source/admission owner
    if not owner._READ_ADMISSION.acquire(blocking=False):
        return _error("BOARD_DETAIL_UNAVAILABLE", 503)
    try:
        try:
            from engine.us_prophet_board_view import project_board_detail  # noqa: PLC0415
            raw = owner._read_candidate_source()
            source_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
            if source_sha != params["source_sha256"]:
                return _error("SOURCE_BINDING_MISMATCH", 409)
            board = json.loads(raw.decode("utf-8"), object_pairs_hook=owner._candidate_object,
                               parse_constant=owner._candidate_constant, parse_float=owner._candidate_float)
            detail = project_board_detail(board, params["ticker"])
            response = JSONResponse({
                "schema": "mastermind.prophet_board_detail_read.v1", "market": "US", "display_only": True,
                "source": {"path": owner._CANDIDATE_SOURCE_PATH, "sha256": source_sha, "bytes": len(raw)},
                **detail,
            }, headers=_PRIVATE_HEADERS)
            # The response is serialized before the final raw identity check.
            # An unrelated source-field change is still a publication change.
            if owner._read_candidate_source() != raw:
                return _error("BOARD_DETAIL_UNAVAILABLE", 503)
            return response
        except Exception as exc:  # noqa: BLE001 — private bounded read/parse/projection/serialization boundary
            log.warning("board detail read failed (%s)", type(exc).__name__)
            return _error("BOARD_DETAIL_UNAVAILABLE", 503)
    finally:
        owner._READ_ADMISSION.release()
