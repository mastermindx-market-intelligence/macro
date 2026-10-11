"""Private Company Intelligence transport; owner admission precedes Store creation.

The application installs a trusted PrivateDisclosureReader as a runtime capability.
HTTP callers cannot supply that capability, an Admission, a purpose or a Store path.
An absent runtime is unavailable, never permission to read a public fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence import issuer_disclosure_selection as selection

FEATURE = "company_intelligence_private_read"
PURPOSE = "private_company_intelligence_context"
AUDIENCE = "company_intelligence_entitled"
ERROR_SCHEMA = "company_intelligence.private_error/v1"
_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization, Cookie",
            "X-Content-Type-Options": "nosniff", "X-Robots-Tag": "noindex, noarchive"}
_FACT_ID = re.compile(r"integration:[0-9a-f]{64}\Z")


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse({"schema": ERROR_SCHEMA, "code": code,
                         "automatic_retry_permitted": False}, status_code=status,
                        headers=_HEADERS)


class _PrivateRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def private(request: Request):
            try:
                response = await original(request)
            except HTTPException as exc:
                # Do not serialize upstream details, tokens or owner paths.
                code = {401: "AUTHENTICATION_REQUIRED", 403: "ENTITLEMENT_REQUIRED",
                        400: "REQUEST_INVALID", 502: "AUTHENTICATION_UNAVAILABLE"}.get(
                            exc.status_code, "PRIVATE_SERVICE_UNAVAILABLE")
                return _error(exc.status_code, code)
            except RequestValidationError:
                return _error(400, "REQUEST_INVALID")
            except Exception:
                return _error(503, "PRIVATE_SERVICE_UNAVAILABLE")
            response.headers.update(_HEADERS)
            return response

        return private


router = APIRouter(prefix="/api/company-intelligence/private", route_class=_PrivateRoute)


def require_private_user(request: Request, authorization: str | None = Header(default=None)) -> dict:
    # Lazy import preserves the single incumbent authentication cache and allows
    # both the legitimate shared session cookie and Bearer machine clients.
    from app.main import require_user
    from app import billing

    user = require_user(authorization, request)
    uid = user.get("id")
    if not isinstance(uid, str) or not uid.strip():
        raise HTTPException(401)
    row = billing.read_entitlement(uid)
    if not isinstance(row, dict):
        raise HTTPException(403)
    features = row.get("features")
    tier, status = row.get("tier"), row.get("status")
    allowed = (isinstance(tier, str) and tier.strip().lower() not in {"", "free"}
               and isinstance(status, str) and status.strip().lower() in {"active", "trialing"}
               and type(features) is list and all(type(v) is str for v in features)
               and FEATURE in features)
    if not allowed:
        raise HTTPException(403)
    # Do not pass the token or personal record into the source owner.
    return {"id": uid}


@dataclass(frozen=True)
class PrivateDisclosureReader:
    """Installed server capability. store_factory must not run before admission.

    The source owner supplies the live resolver. No test resolver or serialized
    Admission is a production installation. Current selection is rechecked by
    the native reader before retrieval and again before serialization.
    """
    authority: native.DisclosureAuthority
    store_factory: Callable[[], object]
    selection_owner: selection.SelectionOwner | None = None

    def read(self, request: native.Request) -> dict:
        native.preflight(self.authority, request)
        store = self.store_factory()
        return native.read_disclosure(store, self.authority, request)


@router.get("/product-integrations/{fact_id:path}")
def product_integration(fact_id: str, request: Request,
                        _user: dict = Depends(require_private_user)) -> JSONResponse:
    # Query controls are parsed only after authentication/entitlement. Reject
    # duplicate or unknown inputs instead of silently ignoring a caller grant.
    items = list(request.query_params.multi_items())
    if (not _FACT_ID.fullmatch(fact_id)
            or any(k not in {"mode", "as_of"} for k, _ in items)
            or len({k for k, _ in items}) != len(items)):
        return _error(400, "REQUEST_INVALID")
    try:
        query = native.Request(fact_id, PURPOSE, AUDIENCE,
                               mode=request.query_params.get("mode", "current"),
                               as_of=request.query_params.get("as_of"))
    except native.DisclosureError:
        return _error(400, "REQUEST_INVALID")
    reader = getattr(request.app.state, "company_disclosure_reader", None)
    if type(reader) is not PrivateDisclosureReader:
        return _error(503, "SOURCE_RUNTIME_UNAVAILABLE")
    try:
        value = reader.read(query)
    except native.DisclosureError as exc:
        # Native error codes are owner-internal. Transport exposes only stable,
        # non-enumerating admission/unavailability classes.
        code = "SOURCE_NOT_ADMITTED" if exc.code == "SOURCE_NOT_ADMITTED" else "PRIVATE_SOURCE_UNAVAILABLE"
        return _error(503, code)
    return JSONResponse(value, headers=_HEADERS)


@router.get("/issuers/{issuer_id}/product-integrations")
def issuer_selections(issuer_id: str, request: Request,
                      _user: dict = Depends(require_private_user)) -> JSONResponse:
    if request.query_params:
        return _error(400, "REQUEST_INVALID")
    try:
        selection.issuer_identity(issuer_id)
    except native.DisclosureError:
        return _error(400, "REQUEST_INVALID")
    reader = getattr(request.app.state, "company_disclosure_reader", None)
    if type(reader) is not PrivateDisclosureReader or reader.selection_owner is None:
        return _error(503, "SOURCE_RUNTIME_UNAVAILABLE")
    try:
        value = selection.read_issuer_selection(
            reader.selection_owner, reader.authority, reader.store_factory, issuer_id,
            purpose=PURPOSE, audience=AUDIENCE)
    except native.DisclosureError:
        return _error(503, "PRIVATE_SOURCE_UNAVAILABLE")
    return JSONResponse(value, headers=_HEADERS)
