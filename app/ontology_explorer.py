"""Authenticated source reads and ephemeral F04 ontology evaluations.

`/ontology.html` is a public, discoverable shell that contains no current value.
Current reads and explicit private scenario requests use this router behind the
existing authority — `app.main.require_user` then
`app.paywall.enforce_site_full(always=True)` — and nothing else. There is no
second identity path or entitlement authority here; minting either is how
a paywall quietly stops being one.

`always=True` is deliberate: this surface fails closed in every environment
rather than following the staging switch, because the payload is premium in
staging too.

The private header set is applied through a route class rather than at the end
of the handler, because the outcomes most likely to leak are the ones that never
reach the handler at all — a 401 or 403 raised inside a dependency, or a 422
raised during request validation. Serving those cacheable and indexable is the
realistic failure, so they are covered first.

There is no fallback. When an owner artifact is missing or the artifacts cannot
be trusted together, the route returns a typed 503; it does not serve a
remembered answer, because a stale state read as the current one is precisely
the harm this product exists to prevent.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool

from engine.ontology_portfolio import (
    MAX_REQUEST_BYTES as MAX_PORTFOLIO_REQUEST_BYTES, PortfolioInputError,
    compose_portfolio_read, parse_request as parse_portfolio_request,
)

from engine.ontology_explorer import (
    DEFAULT_CHAIN,
    ERROR_SCHEMA_ID,
    SourceIncoherent,
    SourceUnavailable,
    compose_snapshot,
)

log = logging.getLogger(__name__)

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent

_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}

_PRIVATE_POST_PATHS = frozenset({'/api/ontology/explorer/scenario/v1',
                                 '/api/ontology/explorer/portfolio/v1',
                                 '/api/ontology/explorer/theme/v1',
                                 '/api/ontology/explorer/research/v1',
                                 '/api/ontology/explorer/radar-research/v1'})
_POST_HEADERS = {**_PRIVATE_HEADERS, 'Vary': 'Authorization, Cookie'}

_CHAIN_PARAM_RE = re.compile(r"[a-z0-9][a-z0-9_]{0,80}")

#: PRODUCT ADMISSION, not syntax. The composer is chain-generic on purpose — it
#: is a library — but a slug the composer can parse is not thereby a product X1
#: has been built and proven for. Only chains admitted here are served; anything
#: else is refused even when it exists and composes cleanly.
ACCEPTED_CHAINS = frozenset({"oil_inflation_duration_derate", "dollar_spike_em_multinational"})


class _PrivateOntologyRoute(APIRoute):
    """Stamp the private header set on every outcome, not just on success."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        original = super().get_route_handler()

        async def private_handler(request: Request) -> Response:
            headers_for_request = _POST_HEADERS if request.url.path in _PRIVATE_POST_PATHS else _PRIVATE_HEADERS
            try:
                response = await original(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    {'detail': {'schema': ERROR_SCHEMA_ID, 'code':'invalid_request'}}
                    if request.url.path in _PRIVATE_POST_PATHS else {'detail': jsonable_encoder(exc.errors())},
                    status_code=422,
                    headers=headers_for_request,
                )
            except HTTPException as exc:
                headers = dict(exc.headers or {})
                headers.update(headers_for_request)
                raise HTTPException(status_code=exc.status_code, detail=exc.detail,
                                    headers=headers) from exc
            except Exception:  # noqa: BLE001 - see below
                # Anything not caught here escapes to Starlette's ServerErrorMiddleware,
                # which is the OUTERMOST layer — so it bypasses this route class AND
                # app.main's no-store middleware, and the 500 goes out with none of the
                # private header set. Measured on the real app, not just a bare one.
                # The exception string never travels: that is where internal paths leak.
                if request.url.path in _PRIVATE_POST_PATHS:
                    log.error('ontology private request failed unexpectedly')
                else:
                    log.exception('ontology explorer failed unexpectedly')
                return JSONResponse(
                    {"detail": {"schema": ERROR_SCHEMA_ID, "code": "internal_error",
                                "reason": "unhandled"}},
                    status_code=500, headers=headers_for_request)
            response.headers.update(headers_for_request)
            return response

        return private_handler


router = APIRouter(
    prefix="/api/ontology/explorer",
    tags=["ontology-explorer"],
    route_class=_PrivateOntologyRoute,
)


def require_site_full_user(authorization: str | None = Header(default=None)) -> dict:
    """Resolve the existing site-full entitlement lazily to avoid an import cycle."""
    from app.main import require_user  # noqa: PLC0415 — shared authority, not a second one
    from app.paywall import enforce_site_full  # noqa: PLC0415

    return enforce_site_full(require_user(authorization), always=True)


def _repo_root() -> Path:
    return Path(os.environ.get("MACRO_REPO", str(_DEFAULT_ROOT))).resolve()


def _unavailable(code: str, reason: str) -> HTTPException:
    """A typed failure the client can branch on — and nothing else.

    The reason is a stable machine token. No owner reading, no partial path and
    no remembered snapshot travels in an error body.
    """
    return HTTPException(
        503,
        detail={"schema": ERROR_SCHEMA_ID, "code": code, "reason": reason},
        headers=_PRIVATE_HEADERS,
    )


@router.get("/v1")
def read_snapshot(
    request: Request,
    _user: dict = Depends(require_site_full_user),
    chain: str | None = Query(default=None, max_length=81),
) -> JSONResponse:
    """Return the current tenant-neutral `ontology_explorer_snapshot.v1`."""
    # `chain=` asked for something specific and empty. Every other malformed
    # value is refused; silently serving the default for this one was the odd
    # case out, not a convenience.
    slug = DEFAULT_CHAIN if chain is None else chain
    # fullmatch, not match: Python's `$` also matches before a trailing newline,
    # so `^...$` accepted a slug with a line break appended — which reached the
    # composer and split one log call across two lines.
    if len(request.query_params.getlist('chain')) > 1 or not _CHAIN_PARAM_RE.fullmatch(slug):
        raise HTTPException(
            400,
            detail={"schema": ERROR_SCHEMA_ID, "code": "unknown_chain",
                    "reason": "chain_slug_rejected"},
            headers=_PRIVATE_HEADERS,
        )
    if slug not in ACCEPTED_CHAINS:
        raise HTTPException(
            404,
            detail={"schema": ERROR_SCHEMA_ID, "code": "chain_not_admitted",
                    "reason": "not_an_accepted_x1_product"},
            headers=_PRIVATE_HEADERS,
        )
    try:
        snapshot: dict[str, Any] = compose_snapshot(_repo_root(), chain=slug)
    except SourceUnavailable as exc:
        log.warning("ontology explorer source unavailable (%s)", exc)
        raise _unavailable("source_unavailable", str(exc).split(":", 1)[0]) from exc
    except SourceIncoherent as exc:
        log.warning("ontology explorer source incoherent (%s)", exc)
        raise _unavailable("source_incoherent", str(exc).split(":", 1)[0]) from exc
    return JSONResponse(snapshot, headers=_PRIVATE_HEADERS)


# HEAD and a method mismatch are both decided by Starlette's router BEFORE the
# route class above is entered, so neither could ever be stamped by it. Both are
# registered here instead: HEAD reuses the read path (the body is dropped by the
# protocol, the headers are not), and every other verb gets an explicit, headered
# 405. Both are hidden from the schema so this snapshot path stays GET-only.
router.add_api_route("/v1", read_snapshot, methods=["HEAD"], include_in_schema=False)


@router.api_route("/v1", methods=["POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                  include_in_schema=False)
def _method_not_allowed(_user: dict = Depends(require_site_full_user)) -> Response:
    """A read-only route says so with the same privacy guarantees as a read.

    Carries the same auth dependency as GET/HEAD so an unauthenticated caller
    learns they are unauthorized, not that the route exists for anonymous
    callers via a disallowed verb.
    """
    raise HTTPException(
        405,
        detail={"schema": ERROR_SCHEMA_ID, "code": "method_not_allowed",
                "reason": "read_only_route"},
        headers={**_PRIVATE_HEADERS, "Allow": "GET, HEAD"},
    )


# Explicit, ephemeral evaluation is POSTed privately; the GET snapshot contract
# stays tenant-neutral. Shared with X4 so neither feature invents another parser.
def _post_error(status: int, code: str) -> HTTPException:
    return HTTPException(status, detail={'schema':ERROR_SCHEMA_ID,'code':code},
                         headers=_POST_HEADERS)


async def _private_post_bytes(request: Request, *, max_bytes: int = 4096) -> bytes:
    if request.query_params: raise _post_error(400, 'query_parameters_forbidden')
    if request.headers.get('content-type','').split(';',1)[0].strip().lower() != 'application/json':
        raise _post_error(415, 'json_required')
    if request.headers.get('content-encoding','identity').lower() != 'identity':
        raise _post_error(415, 'content_encoding_forbidden')
    length = request.headers.get('content-length')
    if length is not None:
        if not re.fullmatch(r'[0-9]+',length): raise _post_error(400, 'invalid_length')
        if len(length) > 10 or int(length) > max_bytes: raise _post_error(413, 'body_too_large')
    async def bounded():
        raw = bytearray()
        async for chunk in request.stream():
            if len(chunk) > max_bytes - len(raw): raise _post_error(413, 'body_too_large')
            raw.extend(chunk)
        return bytes(raw)
    try:
        raw = await asyncio.wait_for(bounded(), timeout=3.0)
    except TimeoutError:
        raise _post_error(408, 'body_deadline_exceeded') from None
    return raw


async def _private_post_body(request: Request, *, max_bytes: int = 4096) -> dict:
    raw = await _private_post_bytes(request, max_bytes=max_bytes)
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate parameter')
            result[key] = value
        return result
    try:
        payload = json.loads(raw,object_pairs_hook=unique)
        if not isinstance(payload,dict): raise ValueError('object required')
    except (TypeError,ValueError,UnicodeError,RecursionError):
        raise _post_error(400,'invalid_json_object') from None
    return payload


def evaluate_current_scenario(*args, **kwargs):
    # Keep numeric owner dependencies out of API startup. This seam executes
    # only after the route's existing authentication and entitlement dependency.
    from engine.ontology_scenario_runtime import evaluate_current_scenario as evaluate
    return evaluate(*args, **kwargs)


@router.post('/scenario/v1')
async def evaluate_private_scenario(request: Request,
                                    _user: dict = Depends(require_site_full_user)) -> Response:
    payload = await _private_post_body(request)
    if set(payload) != {'schema','source_manifest_hash','assumption'} or payload.get('schema') != 'ontology_scenario_request.v1':
        raise _post_error(400,'invalid_scenario_request')
    manifest = payload.get('source_manifest_hash')
    if not isinstance(manifest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',manifest):
        raise _post_error(400,'invalid_source_identity')
    from engine.ontology_scenario import ScenarioInputError, parse_assumption
    from engine.ontology_scenario_runtime import ScenarioSnapshotChanged
    try:
        assumption = parse_assumption(json.dumps(payload['assumption']).encode())
    except (ScenarioInputError,TypeError,ValueError,RecursionError):
        raise _post_error(400,'invalid_assumption') from None
    try:
        result = await run_in_threadpool(evaluate_current_scenario,_repo_root(),assumption,manifest)
    except ScenarioSnapshotChanged:
        raise _post_error(409,'source_changed') from None
    except (SourceUnavailable,SourceIncoherent,OSError):
        raise _post_error(503,'source_unavailable') from None
    except ScenarioInputError:
        raise _post_error(400,'invalid_assumption') from None
    except Exception:
        # No exception message/traceback: owner failures can contain private
        # inputs. The code is observable; the request/exception is never logged.
        log.error('ontology scenario failed unexpectedly')
        raise _post_error(500,'internal_error') from None
    return _bounded_post_response(result)


@router.api_route('/scenario/v1',methods=['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'],include_in_schema=False)
def _scenario_method_not_allowed(_user: dict = Depends(require_site_full_user)) -> Response:
    error = _post_error(405,'method_not_allowed')
    error.headers['Allow'] = 'POST'
    raise error


def _bounded_post_response(result: dict) -> Response:
    # Stream the encoder into a bounded buffer, never truncate a complete owner
    # response or allocate an unbounded serialized private book first.
    body = bytearray()
    try:
        pieces = json.JSONEncoder(ensure_ascii=False,allow_nan=False,separators=(',',':')).iterencode(result)
        for piece in pieces:
            encoded = piece.encode('utf-8')
            if len(encoded) > 262144 - len(body): raise _post_error(503,'response_too_large')
            body.extend(encoded)
    except HTTPException:
        raise
    except (TypeError,ValueError,UnicodeError,RecursionError):
        raise _post_error(500,'internal_error') from None
    return Response(content=bytes(body),media_type='application/json',headers=_POST_HEADERS)


@router.post('/portfolio/v1')
async def read_private_portfolio(request: Request,
                                 _user: dict = Depends(require_site_full_user)) -> Response:
    raw = await _private_post_bytes(request,max_bytes=MAX_PORTFOLIO_REQUEST_BYTES)
    try:
        payload = parse_portfolio_request(raw)
    except (PortfolioInputError,RecursionError):
        raise _post_error(400,'invalid_portfolio_request') from None
    try:
        result = await run_in_threadpool(compose_portfolio_read,_repo_root(),payload)
    except PortfolioInputError as exc:
        if str(exc) == 'snapshot_changed': raise _post_error(409,'source_changed') from None
        if str(exc) == 'owner_clock_unavailable': raise _post_error(503,'owner_clock_unavailable') from None
        raise _post_error(400,'invalid_portfolio_request') from None
    except (SourceUnavailable,SourceIncoherent,OSError):
        raise _post_error(503,'source_unavailable') from None
    except Exception:
        log.error('ontology portfolio failed unexpectedly')
        raise _post_error(500,'internal_error') from None
    return _bounded_post_response(result)


@router.api_route('/portfolio/v1',methods=['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'],include_in_schema=False)
def _portfolio_method_not_allowed(_user: dict = Depends(require_site_full_user)) -> Response:
    error = _post_error(405,'method_not_allowed')
    error.headers['Allow'] = 'POST'
    raise error


def compose_theme_continuation(*args, **kwargs):
    from engine.ontology_theme import compose_theme_continuation as compose
    return compose(*args, **kwargs)


@router.post('/theme/v1')
async def read_private_theme(request: Request,
                             _user: dict = Depends(require_site_full_user)) -> Response:
    payload = await _private_post_body(request)
    from engine.ontology_theme import ThemeInputError, validate_request as validate_theme_request
    try:
        payload = validate_theme_request(payload)
        if payload['chain'] not in ACCEPTED_CHAINS:
            raise _post_error(404, 'chain_not_admitted')
        result = await run_in_threadpool(compose_theme_continuation, _repo_root(), payload)
    except ThemeInputError as exc:
        if str(exc) == 'snapshot_changed': raise _post_error(409, 'source_changed') from None
        raise _post_error(400, 'invalid_theme_request') from None
    except (SourceUnavailable, SourceIncoherent, OSError):
        raise _post_error(503, 'source_unavailable') from None
    except HTTPException:
        raise
    except Exception:
        log.error('ontology theme failed unexpectedly')
        raise _post_error(500, 'internal_error') from None
    return _bounded_post_response(result)


@router.api_route('/theme/v1', methods=['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'], include_in_schema=False)
def _theme_method_not_allowed(_user: dict = Depends(require_site_full_user)) -> Response:
    error = _post_error(405, 'method_not_allowed')
    error.headers['Allow'] = 'POST'
    raise error


def read_drl_research(root: Path, selection: dict) -> dict:
    """Capture once through the native reader, then compose without another read."""
    from engine.price_pressure.research import capture_event, compose_captured_evidence
    from lib.opportunity_case import compose_case
    captured = capture_event(root, event_date=selection['date'],
                             ticker=selection['ticker'], side=selection['side'])
    case = compose_case(**compose_captured_evidence(captured))
    return {'schema': 'ontology_drl_research.v1', 'capture': captured, 'case': case}


@router.post('/research/v1')
async def read_private_drl_research(request: Request,
                                   _user: dict = Depends(require_site_full_user)) -> Response:
    payload = await _private_post_body(request)
    from datetime import date
    try:
        if (set(payload) != {'schema', 'date', 'ticker', 'side'}
                or payload['schema'] != 'ontology_drl_research_request.v1'
                or type(payload['date']) is not str
                or date.fromisoformat(payload['date']).isoformat() != payload['date']
                or type(payload['ticker']) is not str
                or re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,14}', payload['ticker']) is None
                or type(payload['side']) is not str or payload['side'] not in {'up', 'down'}):
            raise ValueError
    except (TypeError, ValueError, KeyError):
        raise _post_error(400, 'invalid_event_selection') from None
    from engine.price_pressure.research import CaptureUnavailable
    try:
        result = await run_in_threadpool(read_drl_research, _repo_root(),
            {k: payload[k] for k in ('date', 'ticker', 'side')})
    except CaptureUnavailable as exc:
        if str(exc) == 'event_not_found':
            raise _post_error(404, 'event_not_found') from None
        raise _post_error(503, 'research_unavailable') from None
    except Exception:
        log.error('ontology research failed unexpectedly')
        raise _post_error(503, 'research_unavailable') from None
    return _bounded_post_response(result)


@router.api_route('/research/v1', methods=['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'], include_in_schema=False)
def _research_method_not_allowed(_user: dict = Depends(require_site_full_user)) -> Response:
    error = _post_error(405, 'method_not_allowed')
    error.headers['Allow'] = 'POST'
    raise error


def read_radar_research(episode_id: str | None) -> dict:
    from engine.entry_radar.research_read import read_published_research
    # The same provisioned live root used by app.main and the native publisher.
    # Never fall back to a checkout artifact when the live source is absent.
    from app.main import LIVE
    return read_published_research(LIVE, episode_id=episode_id)


@router.post('/radar-research/v1')
async def read_private_radar_research(request: Request,
                                     _user: dict = Depends(require_site_full_user)) -> Response:
    payload = await _private_post_body(request)
    if (set(payload) != {'schema', 'episode_id'}
            or payload['schema'] != 'ontology_radar_research_request.v1'
            or payload['episode_id'] is not None and (
                type(payload['episode_id']) is not str
                or re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', payload['episode_id']) is None)):
        raise _post_error(400, 'invalid_episode_selection')
    from engine.entry_radar.research_read import ResearchReadUnavailable
    try:
        result = await run_in_threadpool(read_radar_research, payload['episode_id'])
    except ResearchReadUnavailable as exc:
        raise _post_error(404 if str(exc) == 'candidate_not_found' else 503,
                          'candidate_not_found' if str(exc) == 'candidate_not_found' else 'research_unavailable') from None
    except Exception:
        log.error('ontology Radar research failed unexpectedly')
        raise _post_error(503, 'research_unavailable') from None
    return _bounded_post_response(result)


@router.api_route('/radar-research/v1', methods=['GET','HEAD','PUT','PATCH','DELETE','OPTIONS'], include_in_schema=False)
def _radar_research_method_not_allowed(_user: dict = Depends(require_site_full_user)) -> Response:
    error = _post_error(405, 'method_not_allowed')
    error.headers['Allow'] = 'POST'
    raise error
