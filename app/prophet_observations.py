"""Paid, read-only access to the existing lossless US Turn Watch sidecar.

No detection, backfill, B1 mutation or entry admission occurs here. Each request
reads the producer's published bytes, independent of static render order.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user
from engine.prophet_early_observations import (
    ObservationQueryError, load_observations, query_observations, unavailable_observations,
)
from engine.us_candidate_episode_intake import load_identity_spine
from lib.us_cash_calendar import expected_last_session

router = APIRouter()
log = logging.getLogger("macro.prophet_observations")
_DATA_ROOT = Path(os.environ.get("MACRO_REPO") or Path(__file__).resolve().parents[1]) / "data"
_SESSION_FILE = re.compile(r"\d{4}-\d{2}-\d{2}\.json\Z", re.ASCII)
_QUERIES = frozenset({"ticker", "security_id", "offset", "limit", "snapshot"})


def read_current_observations() -> dict:
    """Select the newest completed-session input, then validate that exact file.

    Missing or corrupt latest bytes do not fall back to an older successful
    result. Future-session files cannot change the current-session population.
    """
    reference = expected_last_session().isoformat()
    source_dir = _DATA_ROOT / "us_prophet_rank/episode_inputs/turn_watch"
    projection = unavailable_observations("SOURCE_UNREADABLE")
    paths = []
    try:
        for path in source_dir.iterdir():
            if not _SESSION_FILE.fullmatch(path.name):
                continue
            try:
                session = date.fromisoformat(path.stem).isoformat()
            except ValueError:
                continue
            if session <= reference:
                paths.append(path)
    except OSError:
        pass
    if paths:
        source = max(paths, key=lambda p: p.stem)
        try:
            spine = load_identity_spine(_DATA_ROOT)
        except (OSError, ValueError, TypeError, KeyError, ImportError):
            spine = None
        projection = load_observations(
            source, spine=spine, reference_session=reference,
            episode_root=_DATA_ROOT / "us_prophet_rank/episodes",
            public_artifact_path=_DATA_ROOT.parent / "site/turn_watch/turn_watch.json",
        )
        if (projection["status"] != "UNAVAILABLE"
                and projection["clocks"]["source_session"] != source.stem):
            projection = unavailable_observations("SOURCE_SESSION_MISMATCH")
    return {**projection, "market": "US", "reference_session": reference}


def _query(request: Request) -> dict:
    """Parse only after authentication; keep all errors within private framing."""
    params = request.query_params
    if any(key not in _QUERIES or len(params.getlist(key)) != 1 for key in params):
        raise ObservationQueryError("INVALID_QUERY")
    result = {}
    for key, default in (("offset", "0"), ("limit", "50")):
        value = params.get(key, default)
        if not re.fullmatch(r"[0-9]{1,9}", value):
            raise ObservationQueryError("INVALID_PAGE")
        result[key] = int(value)
    for key in ("ticker", "security_id"):
        if key in params:
            result[key] = params[key]
    if "snapshot" in params:
        if not re.fullmatch(r"early:[0-9a-f]{64}", params["snapshot"]):
            raise ObservationQueryError("INVALID_SNAPSHOT")
        result["expected_snapshot"] = params["snapshot"]
    # Validate exact filters/bounds before reading any source. Snapshot matching
    # belongs after the current source read.
    query_observations(unavailable_observations("VALIDATION_ONLY"),
                       **{k: v for k, v in result.items() if k != "expected_snapshot"})
    return result


@router.get("/api/prophet/observations/v1")
def observations_v1(request: Request, _user: dict = Depends(require_site_full_user)) -> JSONResponse:
    try:
        query = _query(request)
    except ObservationQueryError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400, headers=_PRIVATE_HEADERS)
    try:
        projection = read_current_observations()
        if projection["status"] == "UNAVAILABLE":
            # An outage is not a page conflict or an empty successful search.
            result = query_observations(projection, **{k: v for k, v in query.items()
                                                     if k != "expected_snapshot"})
            return JSONResponse(result, status_code=503, headers=_PRIVATE_HEADERS)
        result = query_observations(projection, **query)
    except ObservationQueryError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409, headers=_PRIVATE_HEADERS)
    except Exception as exc:  # noqa: BLE001 — private transport boundary, no path/row disclosure
        log.warning("early observation read failed (%s)", type(exc).__name__)
        return JSONResponse({"error": "OBSERVATIONS_UNAVAILABLE"}, status_code=503,
                            headers=_PRIVATE_HEADERS)
    return JSONResponse(result, headers=_PRIVATE_HEADERS)
