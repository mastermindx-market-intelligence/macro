"""Authenticated, read-only transport for the frozen Prophet beta evaluation.

``GET /api/prophet/beta-evaluation/v1`` serves the evaluation artifact
``site/prophet/beta_evaluation.json`` (schema ``prophet.beta_evaluation/v1``,
produced by ``scripts/run_prophet_beta_evaluation.py`` under the frozen
protocol header) to entitled callers, exactly as stored.

This file is a transport boundary only — a deliberate sibling of
``app/prophet_daily_brief.py``:

* Auth is the one canonical site-full dependency
  (``app.prophet_lab.require_site_full_user``): ``require_user`` authenticates,
  then ``enforce_site_full(..., always=True)`` gates on the paid entitlement,
  and every denial inherits the mandatory private headers. Only that
  dependency and ``_PRIVATE_HEADERS`` are imported from ``app.prophet_lab``.
* Authorization strictly precedes any file read: the dependency resolves
  before the handler body runs, so an anonymous or under-entitled request
  never touches the artifact or the protocol header on disk.
* The caller chooses nothing. There is no query parameter at all — any query
  string is rejected with 400 before any read. The repository root is this
  module's own constant (``MACRO_REPO`` environment override else the package
  parent — the established API runtime convention) and a request can never
  change which artifact is served.
* The artifact is returned byte-for-byte as stored — no recomputation, no
  reshaping, no receipt added, no timestamps assigned. The heavy evaluation
  runtime (numpy/pandas) is never imported here; the nightly regeneration
  owns all computation.
* Before serving, the stored bytes are validated: they must parse as JSON,
  carry ``schema == "prophet.beta_evaluation/v1"``, and bind the exact frozen
  protocol header (``protocol.header_sha256`` equal to the sha256 of the
  committed ``research/prophet_v4/beta_first_evaluation/protocol_header_v1.json``).
  A missing, unparsable, wrong-schema or hash-mismatched artifact is a private
  outage — ``503 {"error": "evaluation_unavailable", "reason": ...}`` — never
  a partial or stale-looking 200. Reasons are coarse codes only; no path,
  source or exception is disclosed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user

router = APIRouter()
log = logging.getLogger("macro.prophet_beta_evaluation")

# One module constant owns the repository path (same convention as
# app/prophet_daily_brief.py); requests carry nothing that can change it.
_REPO_ROOT = Path(os.environ.get("MACRO_REPO") or Path(__file__).resolve().parents[1])

_ARTIFACT_REL = "site/prophet/beta_evaluation.json"
_HEADER_REL = "research/prophet_v4/beta_first_evaluation/protocol_header_v1.json"
#: The only schema this route will ever serve. Kept as a literal so the app
#: never imports the evaluation engine (numpy/pandas) to learn it.
_EXPECTED_SCHEMA = "prophet.beta_evaluation/v1"


def _unavailable(reason: str) -> JSONResponse:
    log.warning("beta evaluation unavailable: %s", reason)
    return JSONResponse(
        {"error": "evaluation_unavailable", "reason": reason},
        status_code=503,
        headers=_PRIVATE_HEADERS,
    )


def _bad_query() -> JSONResponse:
    return JSONResponse(
        {"error": "INVALID_QUERY"}, status_code=400, headers=_PRIVATE_HEADERS
    )


@router.get("/api/prophet/beta-evaluation/v1")
def beta_evaluation_v1(
    request: Request, _user: dict = Depends(require_site_full_user)
) -> Response:
    # The caller chooses nothing: any query string is refused before any read.
    if request.query_params:
        return _bad_query()

    try:
        raw = (_REPO_ROOT / _ARTIFACT_REL).read_bytes()
    except OSError:
        return _unavailable("artifact_unavailable")
    try:
        parsed = json.loads(raw)
    except ValueError:
        return _unavailable("artifact_unparsable")
    if not isinstance(parsed, dict) or parsed.get("schema") != _EXPECTED_SCHEMA:
        return _unavailable("schema_mismatch")
    protocol = parsed.get("protocol")
    bound_hash = (
        protocol.get("header_sha256") if isinstance(protocol, dict) else None
    )
    try:
        committed_hash = hashlib.sha256(
            (_REPO_ROOT / _HEADER_REL).read_bytes()
        ).hexdigest()
    except OSError:
        return _unavailable("protocol_header_unavailable")
    if not isinstance(bound_hash, str) or bound_hash != committed_hash:
        # The artifact on disk was not produced under the header this
        # repository has frozen — serving it would misrepresent the science.
        return _unavailable("protocol_header_mismatch")

    return Response(content=raw, media_type="application/json",
                    headers=_PRIVATE_HEADERS)
