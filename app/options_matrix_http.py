"""Exact Matrix display response composition; no HTTP route is registered.

The incumbent handler must supply its retained raw artifact, snapshot reference,
selection and trusted native readers/configuration. There is no upstream fetch,
fixture, parsed JSON fallback, transport endpoint or default source binding here.
This seam is usable only in the same request that performs fresh authorization.
"""
from __future__ import annotations

from fastapi.responses import JSONResponse, Response

from app.options_auth import resolve_authenticated_matrix_display


_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization, Cookie"}


def matrix_display_response(
    ref, matrix, selection, *, access_token: str, vendor: str,
    aliases, security_master, root_evidence, source=None, clock=None,
) -> Response:
    """Authorize and emit the same retained bytes, never JSON-reserialize them.

    Inputs are server captures, not browser JSON. The existing helper verifies
    the snapshot and semantic selection, native produced contracts, exact output,
    fresh subject/session/product access and source policy. Missing source fails
    before authentication. Error responses reveal no token, identity or policy.
    A success is display-only; it grants no export or Save capability.
    """
    try:
        result = resolve_authenticated_matrix_display(
            ref, matrix, selection, release_body=matrix.body,
            access_token=access_token, vendor=vendor, aliases=aliases,
            security_master=security_master, root_evidence=root_evidence,
            source=source, clock=clock,
        )
        return Response(content=result.body, media_type="application/json",
                        headers=_HEADERS)
    except Exception:
        # No cache/stale/fixture fallback, even on an unexpected integration error.
        return JSONResponse({"error": "matrix_display_unavailable"}, status_code=503,
                            headers=_HEADERS)
