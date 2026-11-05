"""Authenticated, read-only transport for the Prophet daily candidate brief.

``GET /api/prophet/daily-brief/v1`` is the candidate-binding plane in front of
the Chairman's Daily Brief views: one entitled request pins the exact
generation it is looking at (source sha256, incumbent pair id, selection
receipt, optional candidate generation id) and receives the original
producer's own projection envelope back, unchanged.

This file is a transport boundary only — a deliberate sibling of
``app/prophet_observations.py`` (B03):

* Auth is the one canonical site-full dependency
  (``app.prophet_lab.require_site_full_user``): ``require_user`` authenticates,
  then ``enforce_site_full(..., always=True)`` gates on the paid entitlement,
  and every denial inherits the mandatory private headers. Only that
  dependency and ``_PRIVATE_HEADERS`` are imported from ``app.prophet_lab`` —
  no Lab projection, board or data reader is touched.
* Query parsing happens strictly AFTER authentication and accepts exactly four
  exact-bound pins (three required, one optional). Unknown names, repeated
  names, empty or malformed bindings and path-shaped values are rejected with
  400 before any owner read. There is NO server-path override query: the
  repository root is this module's own constant (``MACRO_REPO`` environment
  override else the package parent — the established API runtime convention)
  and a request can never change it.
* The projection is read by the original owner,
  ``scripts.build_stock_library.read_today_candidate_projection``, imported
  request-scoped AFTER auth and validation, so the optional heavy
  pandas/pyarrow runtime can neither break application startup nor an
  anonymous caller's authentication path. This router passes the returned
  envelope through verbatim: it issues NO candidate/provenance/owner receipt,
  computes NO selection or order, reads NO source bytes and assigns NO
  producer timestamps.
* Framing is the producer's own ``status``: AVAILABLE|PARTIAL -> 200 and
  UNAVAILABLE -> 503, except an explicit SOURCE_BINDING_MISMATCH or
  SELECTION_BINDING_MISMATCH reason, which is a stale caller pin — a 409
  conflict carrying the same envelope bytes. An optional candidate-generation
  pin mismatch stays UNAVAILABLE/503: this route never retries, refreshes or
  substitutes another generation. An unexpected import or runtime failure
  collapses to a generic ``DAILY_BRIEF_UNAVAILABLE`` 503 that discloses no
  exception, source or path.

The returned envelope is a prerequisite candidate binding only: real Daily
Brief views need genuine other-owner plan/assessment/evidence inputs, and
nothing here fabricates a plan, assessment, evidence or quote receipt. B03's
existing population and query behaviour is untouched by this router.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from threading import BoundedSemaphore
from typing import Mapping

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user

router = APIRouter()
log = logging.getLogger("macro.prophet_daily_brief")

# One module constant owns the repository path (same convention as
# app/prophet_observations.py::_DATA_ROOT); requests carry bindings, never paths.
_REPO_ROOT = Path(os.environ.get("MACRO_REPO") or Path(__file__).resolve().parents[1])

# A native read materializes large candidate snapshots. Bound this route to one
# read per API process; overlap fails privately instead of queueing thread-pool
# work. This is not a cross-process budget or a limit on one read's memory use.
_READ_ADMISSION = BoundedSemaphore(1)

_QUERIES = frozenset(
    {"source_sha256", "pair_id", "selection_receipt", "candidate_generation_id"}
)
# The restricted alphabets are themselves the injection guard: no accepted
# binding can carry a separator, dot segment or whitespace into any path.
_SOURCE_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_PAIR_ID = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)  # incumbent emits a UUID
_SELECTION_RECEIPT = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_CANDIDATE_GENERATION = re.compile(r"peg:[0-9a-f]{64}\Z", re.ASCII)

# A stale caller pin conflicts with the producer's answer; every other
# UNAVAILABLE (missing/corrupt/racing native or source inputs, including an
# optional candidate-generation pin mismatch) stays a private outage.
_PIN_CONFLICT_REASONS = frozenset(
    {"SOURCE_BINDING_MISMATCH", "SELECTION_BINDING_MISMATCH"}
)


class DailyBriefQueryError(ValueError):
    """Malformed request query — rejected before any owner or source read."""


def _pin(params, name: str, pattern) -> str:
    values = params.getlist(name)
    if len(values) != 1:
        raise DailyBriefQueryError("INVALID_QUERY")
    value = values[0]
    if not pattern.fullmatch(value):
        raise DailyBriefQueryError("INVALID_QUERY")
    return value


def _query(request: Request) -> dict:
    """Exact bindings only, parsed strictly after authentication."""
    params = request.query_params
    if any(key not in _QUERIES or len(params.getlist(key)) != 1 for key in params):
        raise DailyBriefQueryError("INVALID_QUERY")
    return {
        "expected_source_sha256": _pin(params, "source_sha256", _SOURCE_SHA256),
        "expected_pair_id": _pin(params, "pair_id", _PAIR_ID),
        "expected_selection_receipt": _pin(params, "selection_receipt", _SELECTION_RECEIPT),
        "expected_candidate_generation_id": (
            _pin(params, "candidate_generation_id", _CANDIDATE_GENERATION)
            if "candidate_generation_id" in params
            else None
        ),
    }


def _unavailable() -> JSONResponse:
    return JSONResponse({"error": "DAILY_BRIEF_UNAVAILABLE"}, status_code=503,
                        headers=_PRIVATE_HEADERS)


def _projection_response(projection: Mapping, *, status_code: int) -> JSONResponse:
    """Keep a malformed owner serialization inside the private error boundary."""
    try:
        return JSONResponse(dict(projection), status_code=status_code, headers=_PRIVATE_HEADERS)
    except (TypeError, ValueError, OverflowError) as exc:
        log.warning("daily brief owner serialization failed (%s)", type(exc).__name__)
        return _unavailable()


@router.get("/api/prophet/daily-brief/v1")
def daily_brief_v1(
    request: Request, _user: dict = Depends(require_site_full_user)
) -> JSONResponse:
    # The optional pandas/pyarrow producer runtime belongs to this entitled
    # request, not application startup or an anonymous authentication path.
    try:
        bindings = _query(request)
    except DailyBriefQueryError:
        return JSONResponse({"error": "INVALID_QUERY"}, status_code=400,
                            headers=_PRIVATE_HEADERS)
    if not _READ_ADMISSION.acquire(blocking=False):
        return _unavailable()
    try:
        try:
            from scripts.build_stock_library import (  # noqa: PLC0415 — request-scoped owner
                read_today_candidate_projection,
            )
        except Exception as exc:  # noqa: BLE001 — optional runtime missing, disclose nothing
            log.warning("daily brief owner import failed (%s)", type(exc).__name__)
            return _unavailable()
        try:
            projection = read_today_candidate_projection(_REPO_ROOT, **bindings)
        except Exception as exc:  # noqa: BLE001 — private transport boundary, no path/row disclosure
            log.warning("daily brief owner read failed (%s)", type(exc).__name__)
            return _unavailable()
        if not isinstance(projection, Mapping):
            return _unavailable()
        raw_reasons = projection.get("reason_codes")
        reasons = (
            {reason for reason in raw_reasons if isinstance(reason, str)}
            if isinstance(raw_reasons, (list, tuple, set, frozenset)) else set()
        )
        if reasons & _PIN_CONFLICT_REASONS:
            # Stale caller pin: the producer's own envelope, nothing added.
            return _projection_response(projection, status_code=409)
        status = projection.get("status")
        if status in ("AVAILABLE", "PARTIAL"):
            return _projection_response(projection, status_code=200)
        if status == "UNAVAILABLE":
            return _projection_response(projection, status_code=503)
        return _unavailable()
    finally:
        # Import, owner and response serialization all retain the permit until
        # they settle, including exceptions.
        _READ_ADMISSION.release()
