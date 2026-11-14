"""Site-full calendar BFF owner: authenticated private artifact reads, no network."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.prophet_lab import _PRIVATE_HEADERS, require_site_full_user
from app.market_calendar_contracts import MAX_BYTES
from app.market_calendar_contracts import day
from app.market_calendar_projection import public_view, read_json

router = APIRouter()
_READS = BoundedSemaphore(2)


@router.get("/api/market-calendar/v1")
def market_calendar_v1(request: Request, _user: dict = Depends(require_site_full_user)) -> JSONResponse:
    query = request.query_params
    start, end = day(query.get("from")), day(query.get("to"))
    cursor = query.get("cursor", "0")
    revision = query.get("revision")
    if (set(query) - {"from", "to", "cursor", "revision"} or any(len(query.getlist(k)) != 1 for k in query)
            or not start or not end or query.get("from") != start or query.get("to") != end
            or not 0 <= (date.fromisoformat(end) - date.fromisoformat(start)).days <= 30
            or not cursor.isdecimal() or len(cursor) > 5 or int(cursor) > 20000
            or int(cursor) > 0 and not re.fullmatch(r"[a-f0-9]{64}", revision or "")):
        return JSONResponse({"error": "INVALID_QUERY"}, status_code=400, headers=_PRIVATE_HEADERS)
    if not _READS.acquire(blocking=False):
        return JSONResponse({"error": "CALENDAR_BUSY"}, status_code=503, headers=_PRIVATE_HEADERS)
    try:
        private = Path(os.environ.get("MACRO_LIVE_STATE_DIR", "/var/lib/macro-live/state")) / "market_calendar.json"
        live = Path(os.environ.get("MACRO_LIVE_DIR", "/var/lib/macro-live/public/live")) / "release_publications.json"
        view = public_view(read_json(private), datetime.now(timezone.utc), read_json(live, 2 * 1024 * 1024),
                           start, end, int(cursor), revision)
        if len(json.dumps(view, ensure_ascii=False).encode()) > MAX_BYTES:
            raise ValueError("calendar response exceeds budget")
        return JSONResponse(view, headers=_PRIVATE_HEADERS)
    except (OSError, ValueError, KeyError, TypeError):
        return JSONResponse({"error": "CALENDAR_UNAVAILABLE"}, status_code=503, headers=_PRIVATE_HEADERS)
    finally:
        _READS.release()
