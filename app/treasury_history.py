"""Same-box Treasury input for Terminal's existing derived risk compiler.

Raw history is refused for every edge request, including authenticated users.
The co-located server supplies the existing site-full Bearer credential; it
keeps positions and calculations in Terminal and returns only derived metrics.
This reuses the deployed loopback/X-MM-Peer boundary and site-full authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.prophet_lab import _hub_prophet_authorized, require_site_full_user
from lib.treasury_daily_history import compose_history, read_history

_ROOT = Path(__file__).resolve().parent.parent
_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization, Cookie",
            "X-Robots-Tag": "noindex, noarchive", "X-Content-Type-Options": "nosniff"}


class _PrivateRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private(request):
            try:
                response = await handler(request)
            except RequestValidationError:
                response = JSONResponse({"error": "invalid_request"}, status_code=422)
            except HTTPException as exc:
                response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            except Exception:
                response = JSONResponse({"error": "treasury_history_unavailable"}, status_code=503)
            response.headers.update(_HEADERS)
            return response
        return private


router = APIRouter(route_class=_PrivateRoute)


def _service_user(request: Request, authorization: str | None = Header(default=None)) -> dict:
    # Edge header presence (even empty) denies before any identity or file read.
    if not _hub_prophet_authorized(request):
        raise HTTPException(401, "internal_only")
    return require_site_full_user(authorization)


@router.get("/api/internal/treasury-history")
def treasury_history(start: str = Query(...), end: str = Query(...),
                     expected_through: str = Query(...), _user: dict = Depends(_service_user)):
    now = datetime.now(timezone.utc)
    args = {"start": start, "end": end, "expected_through": expected_through, "read_at": now}
    try:
        compose_history(None, **args)  # Shared strict bounds before any native read.
    except ValueError:
        raise HTTPException(422, "invalid_window") from None
    return read_history(_ROOT, **args)
