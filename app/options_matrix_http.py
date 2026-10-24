"""Narrow exact Matrix display HTTP composition, unavailable without native readers.

The incumbent handler must supply its retained raw artifact, snapshot reference,
selection and trusted native readers/configuration. There is no upstream fetch,
fixture, parsed JSON fallback or default source binding here.
This seam is usable only in the same request that performs fresh authorization.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from engine.options_matrix_retention import SnapshotReference, parse_reference
from app.options_matrix_runtime import MatrixCaptureUnavailable

if TYPE_CHECKING:
    from engine.intelligence_workspace.entity import IdentityArtifactRead
    from engine.intelligence_workspace.options_matrix_delivery import MatrixDisplaySource


def resolve_options_principal(*args, **kwargs):
    # Keep unrelated/unprovisioned app startup independent of the contract stack.
    # Real requests still use the incumbent verifier; no optional-import fallback.
    from app.options_auth import resolve_options_principal as resolve
    return resolve(*args, **kwargs)


def resolve_authenticated_matrix_display(*args, **kwargs):
    from app.options_auth import resolve_authenticated_matrix_display as resolve
    return resolve(*args, **kwargs)


_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization, Cookie"}
router = APIRouter()
_BODY_TIMEOUT = 5
_RESPONSE_TIMEOUT = 10


@dataclass(frozen=True)
class MatrixHTTPInputs:
    """Genuine server captures/configuration, never decoded from the request."""

    matrix: IdentityArtifactRead
    aliases: IdentityArtifactRead
    security_master: IdentityArtifactRead
    root_evidence: IdentityArtifactRead
    source: MatrixDisplaySource


@dataclass(frozen=True)
class MatrixHTTPRuntime:
    """Deployment-owned injection; there is deliberately no production default.

    capture reads the requested retained snapshot and its genuine native inputs.
    It receives only an artifact selector, never browser policy/source context.
    Python object types establish consistency, not provenance or enrollment.
    """

    capture: Callable[[SnapshotReference], MatrixHTTPInputs]
    clock: Callable | None = None


def _error(status=503):
    return JSONResponse({"error": "matrix_display_unavailable"}, status_code=status,
                        headers=_HEADERS)


def _serve(runtime, ref, selection, token):
    try:
        # No artifact/network capture is permitted before the actual verifier.
        resolve_options_principal(token)
        from engine.intelligence_workspace.options_matrix_delivery import MatrixDisplaySource
        if type(runtime) is not MatrixHTTPRuntime or not callable(runtime.capture):
            return _error()
        captured = runtime.capture(ref)
        if (type(captured) is not MatrixHTTPInputs
                or type(captured.source) is not MatrixDisplaySource
                or captured.source.binding is None):
            return _error()
        return matrix_display_response(
            ref, captured.matrix, selection, access_token=token,
            vendor=captured.source.binding.vendor, aliases=captured.aliases,
            security_master=captured.security_master, root_evidence=captured.root_evidence,
            source=captured.source, clock=runtime.clock,
        )
    except MatrixCaptureUnavailable as exc:
        logging.getLogger("macro.api").warning("Matrix capture unavailable: %s", exc.code)
        return _error()
    except Exception:
        return _error()


async def _selection_body(request):
    raw = bytearray()
    async for chunk in request.stream():
        if len(chunk) > 2048 - len(raw):
            raise ValueError("selection exceeds bound")
        raw.extend(chunk)
    return bytes(raw)


@router.api_route("/api/options/matrix/display/{root}",
                  methods=["GET", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"])
def display_method_unavailable(root: str):
    response = _error(405)
    response.headers["Allow"] = "POST"
    return response


@router.post("/api/options/matrix/display/{root}")
async def display_matrix(root: str, request: Request) -> Response:
    """Raw selection <=2048B plus a strict snapshot selector; display only.

    The response is the whole authorized Matrix. No browser field can supply
    vendor, dataset, policy, source context, identity readers or runtime config.
    GET/SSE/export/Save are not admitted by this endpoint.
    """
    try:
        if (set(request.query_params) != {"version_ref", "fingerprint"}
                or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params)):
            return _error(400)
        auth = request.headers.getlist("authorization")
        if (len(auth) != 1 or not auth[0].startswith("Bearer ")
                or not 1 <= len(auth[0][7:]) <= 16384 or any(c.isspace() for c in auth[0][7:])):
            return _error(401)
        if (request.headers.getlist("content-type") != ["application/octet-stream"]
                or request.headers.getlist("content-encoding")):
            return _error(415)
        lengths = request.headers.getlist("content-length")
        if lengths and (len(lengths) != 1 or len(lengths[0]) > 10 or not lengths[0].isascii()
                        or not lengths[0].isdigit() or not 0 < int(lengths[0]) <= 2048):
            return _error(400)
        try:
            ref = parse_reference(root, request.query_params["version_ref"],
                                  request.query_params["fingerprint"])
            raw = await asyncio.wait_for(_selection_body(request), _BODY_TIMEOUT)
        except (ValueError, TypeError):
            return _error(400)
        if not raw or (lengths and len(raw) != int(lengths[0])):
            return _error(400)
        runtime = getattr(request.app.state, "options_matrix_display_runtime", None)
        # A late read can finish in the worker thread, but cannot release bytes
        # into a timed-out request or authorize a later request.
        return await asyncio.wait_for(
            run_in_threadpool(_serve, runtime, ref, raw, auth[0][7:]), _RESPONSE_TIMEOUT)
    except Exception:
        return _error()


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
