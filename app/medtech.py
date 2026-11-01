"""Authenticated R14 MedTech discovery and event history over published product data.

No request opens worker state, acquires source data, or starts an ingestion job.
The same Macro/Supabase identity and site_full entitlement gate this payload.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from engine.medtech.events import EVENT_ID_RE, MedTechError, PATHWAYS, instant
from engine.medtech.publication import read_attempt, read_snapshot

_HEADERS = {
    "Cache-Control": "private, no-store", "Vary": "Authorization, Cookie",
    "X-Content-Type-Options": "nosniff", "X-Robots-Tag": "noindex, noarchive",
}


def _error(status: int, code: str):
    return JSONResponse({"schema": "medtech.error/v1", "code": code},
                        status_code=status, headers=_HEADERS)


class _PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def private(request: Request):
            try:
                response = await original(request)
            except HTTPException as exc:
                code = {401: "AUTHENTICATION_REQUIRED", 403: "ENTITLEMENT_REQUIRED",
                        404: "EVENT_NOT_FOUND", 409: "SNAPSHOT_CHANGED",
                        400: "REQUEST_INVALID", 502: "AUTHENTICATION_UNAVAILABLE"}.get(
                            exc.status_code, "MEDTECH_UNAVAILABLE")
                return _error(exc.status_code, code)
            except RequestValidationError:
                return _error(400, "REQUEST_INVALID")
            except Exception:
                return _error(503, "MEDTECH_UNAVAILABLE")
            response.headers.update(_HEADERS)
            return response
        return private


router = APIRouter(prefix="/api/medtech", route_class=_PrivateRoute, tags=["medtech"])


def require_medtech_user(request: Request, authorization: str | None = Header(default=None)):
    from app.main import require_user
    from app.paywall import enforce_site_full

    # Reuse the existing token/cookie reader and entitlement owner, including outages.
    user = enforce_site_full(require_user(authorization, request), always=True)
    if not isinstance(user.get("id"), str) or not user["id"].strip():
        raise HTTPException(401)
    return {"id": user["id"]}


def public_root() -> Path:
    # Deployment-supplied path, never a query parameter; only public projections belong here.
    return Path(os.environ.get("MEDTECH_PUBLIC_ROOT", "/srv/medtech/public"))


def now() -> datetime:
    return datetime.now(timezone.utc)


def _load(snapshot_id: str | None = None):
    payload, generation = read_snapshot(public_root())
    if snapshot_id is not None and generation != snapshot_id:
        raise HTTPException(409)
    return payload, generation


def _summary(event: dict) -> dict:
    return {key: value for key, value in event.items() if key != "history"}


def _source_status(source: dict) -> dict:
    current = now()
    updated = source["dataset_updated_at"]
    age = (current.date() - datetime.fromisoformat(updated).date()).days if updated else None
    return {**source, "dataset_age_days": age,
            # A transparent reference-data policy; this is not a regulator deadline.
            "status": "stale" if age is not None and age > 45 else "available"}


@router.get("/health")
def health(_user: dict = Depends(require_medtech_user)):
    payload, generation = _load()
    attempt = read_attempt(public_root())
    failed_refresh = bool(attempt and attempt["status"] == "failed"
                          and instant(attempt["observed_at"]) >= instant(payload["generated_at"]))
    return {
        "schema": "medtech.health/v1", "snapshot_id": generation,
        "generated_at": payload["generated_at"],
        "state": "refresh_failed" if failed_refresh else "available",
        "last_attempt": attempt, "retained_snapshot_available": True,
        "sources": [_source_status(source) for source in payload["sources"]],
        "capabilities": payload["capabilities"],
    }


@router.get("/events")
def list_events(
    q: str = Query(default="", max_length=120),
    pathway: str | None = Query(default=None, max_length=40),
    decision: str | None = Query(default=None, max_length=40),
    dataset: str | None = Query(default=None, max_length=8),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    snapshot_id: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    _user: dict = Depends(require_medtech_user),
):
    if pathway is not None and pathway not in PATHWAYS:
        raise HTTPException(400)
    if dataset is not None and dataset not in {"510k", "pma"}:
        raise HTTPException(400)
    # Continuations must bind a generation; a concurrent publication cannot shift rows silently.
    if offset and snapshot_id is None:
        raise HTTPException(400)
    payload, generation = _load(snapshot_id)
    query = " ".join(q.casefold().split())
    rows = []
    for event in payload["events"]:
        if pathway and event["pathway"] != pathway:
            continue
        if decision and event["decision"]["status"] != decision:
            continue
        if dataset and event["source"]["dataset"] != dataset:
            continue
        haystack = " ".join(str(value or "") for value in (
            event["submission_id"], event["event_id"], event["device"]["name"],
            event["device"]["generic_name"], event["device"]["product_code"],
            event["applicant"]["name"],
        )).casefold()
        if query and query not in haystack:
            continue
        rows.append(event)
    end = offset + limit
    return {
        "schema": "medtech.events/v1", "snapshot_id": generation,
        "generated_at": payload["generated_at"], "total": len(rows),
        "items": [_summary(event) for event in rows[offset:end]],
        "next_offset": end if end < len(rows) else None,
        "sources": [_source_status(source) for source in payload["sources"]],
        "capabilities": payload["capabilities"],
    }


def _event(event_id: str, snapshot_id: str | None):
    if not EVENT_ID_RE.fullmatch(event_id):
        raise HTTPException(404)
    payload, generation = _load(snapshot_id)
    for event in payload["events"]:
        if event["event_id"] == event_id:
            return event, generation
    raise HTTPException(404)


@router.get("/events/{event_id}")
def event_detail(
    event_id: str,
    snapshot_id: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    _user: dict = Depends(require_medtech_user),
):
    event, generation = _event(event_id, snapshot_id)
    return {"schema": "medtech.event_detail/v1", "snapshot_id": generation,
            "event": _summary(event),
            "history_count": len(event["history"]),
            "latest_change": event["history"][-1]}


@router.get("/events/{event_id}/changes")
def event_changes(
    event_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    snapshot_id: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    _user: dict = Depends(require_medtech_user),
):
    if offset and snapshot_id is None:
        raise HTTPException(400)
    event, generation = _event(event_id, snapshot_id)
    history = list(reversed(event["history"]))
    end = offset + limit
    return {"schema": "medtech.changes/v1", "snapshot_id": generation,
            "event_id": event_id, "total": len(history), "items": history[offset:end],
            "next_offset": end if end < len(history) else None}


def _subject_events(payload: dict, subject_type: str, subject_id: str) -> list[dict]:
    import re

    if subject_type == "event" and EVENT_ID_RE.fullmatch(subject_id):
        matched = [event for event in payload["events"] if event["event_id"] == subject_id]
    elif subject_type == "pma_application" and re.fullmatch(r"fda-pma-P[0-9]{6}", subject_id):
        number = subject_id.removeprefix("fda-pma-")
        matched = [event for event in payload["events"]
                   if event["source"]["dataset"] == "pma" and event["submission_id"] == number]
    else:
        raise HTTPException(400)
    if not matched:
        raise HTTPException(404)
    return matched


@router.get("/subjects/{subject_type}/{subject_id}")
def watch_subject(
    subject_type: str, subject_id: str,
    snapshot_id: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    _user: dict = Depends(require_medtech_user),
):
    payload, generation = _load(snapshot_id)
    matched = _subject_events(payload, subject_type, subject_id)
    triggers = ["record_changed"]
    if subject_type == "pma_application":
        triggers.append("new_supplement")
    return {
        "schema": "medtech.subject/v1", "snapshot_id": generation,
        "generated_at": payload["generated_at"], "subject_type": subject_type,
        "subject_id": subject_id, "allowed_triggers": triggers,
        "baseline_revision": matched[0]["revision_id"] if subject_type == "event" else None,
        "label": matched[0]["device"]["name"] or subject_id,
    }


@router.get("/changes")
def subject_changes(
    subject_type: str = Query(max_length=24),
    subject_id: str = Query(max_length=40),
    since: str = Query(max_length=40),
    trigger: str | None = Query(default=None, pattern=r"^(record_changed|new_supplement)$"),
    revision_id: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    snapshot_id: str | None = Query(default=None, pattern=r"^[0-9a-f]{64}$"),
    _user: dict = Depends(require_medtech_user),
):
    try:
        baseline = instant(since)
    except MedTechError:
        raise HTTPException(400) from None
    if baseline > now() or (offset and snapshot_id is None):
        raise HTTPException(400)
    payload, generation = _load(snapshot_id)
    matched = _subject_events(payload, subject_type, subject_id)
    updates = []
    for event in matched:
        for revision in event["history"]:
            if instant(revision["observed_at"]) <= baseline:
                continue
            if revision["kind"] == "first_observed":
                decision_date = revision["decision_date"]
                # A later backfill of a pre-subscription decision is baseline coverage,
                # not a new-supplement alert. Day precision cannot establish same-day ordering.
                if (subject_type != "pma_application" or not event["supplement"]["number"]
                        or not decision_date or decision_date <= baseline.date().isoformat()):
                    continue
                update_trigger = "new_supplement"
            else:
                update_trigger = "record_changed"
            if ((trigger is not None and update_trigger != trigger)
                    or (revision_id is not None and revision["revision_id"] != revision_id)):
                continue
            updates.append({
                "event_id": event["event_id"], "revision_id": revision["revision_id"],
                "observed_at": revision["observed_at"], "trigger": update_trigger,
                "kind": "new_supplement_record" if update_trigger == "new_supplement" else revision["kind"],
                "decision_date": revision["decision_date"],
                "device_name": revision["device_name"],
                "changes": revision["changes"], "source_url": event["source"]["url"],
            })
    updates.sort(key=lambda item: (item["observed_at"], item["revision_id"]), reverse=True)
    end = offset + limit
    return {
        "schema": "medtech.updates/v1", "snapshot_id": generation,
        "subject_type": subject_type, "subject_id": subject_id,
        "total": len(updates), "items": updates[offset:end],
        "next_offset": end if end < len(updates) else None,
    }
