"""Authenticated, paid read-only transport for the semiconductor theme research surface.

T09 of operation gmi-semiconductors-fable-cee-20260923-chairman-001
(carrier PR #7870). The boundary this router enforces:

* the caller has been verified by ``require_user`` and is entitled to
  ``site_full``; the same dependency the existing ``app.earnings`` router owns —
  no second gate, no second copy. If this turns into a deny, the 401/403 must
  carry the four private headers below and nothing else;
* the body is validated manually inside the handler, AFTER auth resolves. The
  FastAPI dependency runs first (a 401/403 fires before any body parsing),
  then we parse with the same closed pydantic model and return a 400 with the
  private headers on a malformed payload. This keeps the two-line mount in
  ``main.py`` honest: a :class:`RequestValidationError` handler would need a
  third touchpoint;
* no reader, bundle, locator or filesystem path is constructed or read before
  auth resolves. The default :func:`load_authorized_owner_bundle` raises
  :class:`PrivateStoreUnavailable`; tests inject a bundle via the seam;
* rights filtering is done against a FRESH :func:`load_registry_snapshot` — no
  process cache, so a rights decision that moves between two same-process
  requests reaches the route without a watcher or a restart (the
  ``revoked_rights_warm`` regression) — and the permit/refuse verdict itself
  is ASKED of the rights owner (``engine.theme_graph.rights``), never
  re-derived here: this transport carries no second opinion about licensing;
* no writes. ``engine.theme_graph.store.write_evidence`` is never imported; no
  subprocess, no cache layer, no cursor table. The endpoint is a closed read.

The composition module does NOT see rights: this route strips assertions whose
family is known-and-refused BEFORE handing the bundle to
:func:`compose_semiconductor_research` and adds
``rights_refused_families_hidden`` to ``limitations`` without naming the
families — what was refused is never disclosed.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from engine.market_ontology.semiconductor_theme_research import (
    OwnerBundle,
    ResearchQuery,
    ResearchRefusal,
    compose_semiconductor_research,
    select_authorized_evidence,
)
from engine.theme_graph.rights import (
    RightsRefusal,
    assert_current_emission_allowed,
    family_for_source_ref,
    load_registry_snapshot,
)

# Reuse the existing paid dependency; no second auth gate, no second copy.
from app.earnings import require_site_full_user


router = APIRouter()


# The four private headers every response on these paths MUST carry — identical
# to app/earnings._PRIVATE_HEADERS so a Caddy / privacy interceptor see one
# policy. Re-declared rather than imported because earnings.py keeps its own
# module-private copy; the two must move together if either changes (commented
# here so a divergence is loud).
_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}
_PRIVATE_HEADER_NAMES = frozenset(name.lower() for name in _PRIVATE_HEADERS)


class PrivateStoreUnavailable(Exception):
    """The native readers are not bound yet (R4 ruling pending).

    Tests inject a bundle via :func:`load_authorized_owner_bundle`; production
    must never reach a real reader until that ruling lands. The body shape is
    fixed by the route's ``service_unavailable`` envelope.
    """


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def _private(response: Response) -> None:
    response.headers.update(_PRIVATE_HEADERS)


def _private_error(
    status_code: int,
    detail: Any,
    inherited: Mapping[str, str] | None = None,
) -> HTTPException:
    safe = {
        str(name): str(value)
        for name, value in dict(inherited or {}).items()
        if str(name).lower() not in _PRIVATE_HEADER_NAMES
    }
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={**safe, **_PRIVATE_HEADERS},
    )


def _private_json(status_code: int, payload: Mapping[str, Any]) -> JSONResponse:
    return JSONResponse(content=payload, headers=_PRIVATE_HEADERS)


#: Reusable mapping from ResearchRefusal.code -> (HTTP status, error envelope).
_RESEARCH_REFUSAL_MAP: dict[str, tuple[int, dict[str, str]]] = {
    "generation_changed": (409, {"code": "refresh_required", "action": "reset_to_first_page"}),
    "limit_out_of_range": (400, {"code": "invalid_request", "action": "fix_request"}),
    "offset_negative": (400, {"code": "invalid_request", "action": "fix_request"}),
    "expected_generation_required": (
        400, {"code": "invalid_request", "action": "fix_request"},
    ),
    "replay_cutoffs_required": (
        400, {"code": "invalid_request", "action": "fix_request"},
    ),
}


def _map_research_refusal(exc: ResearchRefusal) -> HTTPException:
    code = str(exc.code)
    if code == "not_available":
        return _private_error(404, {"error": {"code": "not_available", "action": "none"}})
    if code in _RESEARCH_REFUSAL_MAP:
        status, envelope = _RESEARCH_REFUSAL_MAP[code]
        return _private_error(status, {"error": envelope})
    return _private_error(
        503, {"error": {"code": "service_unavailable", "action": "retry_later"}},
    )


# ---------------------------------------------------------------------------
# Body models — closed; extra="forbid"
# ---------------------------------------------------------------------------

class _QueryBody(BaseModel):
    """The shape shared by both endpoints. ``extra="forbid"`` so a typo is loud."""

    model_config = ConfigDict(extra="forbid")

    anchor_theme_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    slice_key: Literal["hbm_packaging", "sic_gan_specialty"]
    view: Literal["composition", "manufacturing", "commercial", "capacity", "economics"]
    time_mode: Literal["latest", "source_history", "system_replay"]
    source_cutoff: str | None = Field(default=None, max_length=32)
    recorded_cutoff: str | None = Field(default=None, max_length=32)
    offset: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=50, ge=1, le=100)
    expected_generation: str | None = Field(default=None, pattern=r"^gen_[0-9a-f]{32}$")


class _EvidenceBody(_QueryBody):
    assertion_ref: str = Field(
        min_length=1, max_length=256,
        pattern=r"^gmi-curation://[a-z0-9_]+/gmirca_[0-9a-f]{32}$",
    )
    expected_generation: str = Field(pattern=r"^gen_[0-9a-f]{32}$")


def _body_to_query(body: _QueryBody | _EvidenceBody) -> ResearchQuery:
    return ResearchQuery(
        anchor_theme_id=body.anchor_theme_id,
        slice_key=body.slice_key,
        view=body.view,
        time_mode=body.time_mode,
        source_cutoff=body.source_cutoff,
        recorded_cutoff=body.recorded_cutoff,
        offset=body.offset,
        limit=body.limit,
        expected_generation=body.expected_generation,
    )


# ---------------------------------------------------------------------------
# Rights filter — owner verdict on a fresh snapshot, family-keyed drop, no
# family disclosure
# ---------------------------------------------------------------------------

def _filter_bundle_for_rights(bundle: OwnerBundle) -> tuple[OwnerBundle, bool]:
    """Strip assertions whose source-ref family is REFUSED by the rights
    OWNER's verdict on a FRESH snapshot. The verdict is asked of
    :func:`engine.theme_graph.rights.assert_current_emission_allowed` — the
    single veto — so tightening the owner's rule reaches this route without a
    transport change. Unknown families (``family_for_source_ref`` returns
    None) pass through: the registry has no opinion, so we have none either.

    Returns the rewritten bundle and a flag telling the caller whether any
    assertions were dropped — the route turns that into the
    ``rights_refused_families_hidden`` limitation string without naming which
    families were refused.
    """
    snapshot = load_registry_snapshot()
    verdicts: dict[str, bool] = {}  # per-request memo: one owner call per distinct family
    kept: list[Mapping[str, Any]] = []
    dropped = False
    for assertion in bundle.assertions:
        source = assertion.get("source") or {}
        source_ref = source.get("source_uri") or source.get("locator") or ""
        family = family_for_source_ref(source_ref)
        if family is None:
            kept.append(assertion)
            continue
        if family not in verdicts:
            try:
                assert_current_emission_allowed([family], snapshot=snapshot)
            except RightsRefusal:
                verdicts[family] = False
            else:
                verdicts[family] = True
        if verdicts[family]:
            kept.append(assertion)
        else:
            dropped = True
    if not dropped:
        return bundle, False
    new_bundle = OwnerBundle(
        revision_tuple=bundle.revision_tuple,
        rights_revision=bundle.rights_revision,
        assertions=tuple(kept),
        identity_results=bundle.identity_results,
        event_workspaces=bundle.event_workspaces,
        financial_packets=bundle.financial_packets,
        interpretation_blocks=bundle.interpretation_blocks,
        native_refs=bundle.native_refs,
        omissions=bundle.omissions,
    )
    return new_bundle, True


def _post_process_rights_limitation(
    payload: dict[str, Any], dropped: bool
) -> dict[str, Any]:
    """Append ``rights_refused_families_hidden`` to the composed response's
    limitations when the filter actually refused anything."""
    if not dropped:
        return payload
    existing = list(payload.get("limitations") or [])
    if "rights_refused_families_hidden" not in existing:
        existing.append("rights_refused_families_hidden")
        payload["limitations"] = sorted(existing)
    return payload


# ---------------------------------------------------------------------------
# Bundle adapter — production default unbound; tests inject a synthetic bundle
# ---------------------------------------------------------------------------

def load_authorized_owner_bundle(
    query: ResearchQuery, *, principal: Mapping[str, Any]
) -> OwnerBundle:
    """The thin adapter the route calls to fetch a bundle for ``query``.

    Production MUST call only the approved native readers; TODAY those readers
    are NOT bound (private binding R4 is an open DECISION_REQUEST), so this
    default raises :class:`PrivateStoreUnavailable` -> 503. Tests monkeypatch
    this symbol with a synthetic bundle.

    Never reads file paths, URLs or locators from request JSON: the caller
    supplies the bundle shape from its own private store.
    """
    del query, principal
    raise PrivateStoreUnavailable(
        "private native readers are not bound (R4 ruling pending)"
    )


# ---------------------------------------------------------------------------
# Body parsing — manual, AFTER auth, so a 401/403 fires before a 422
# ---------------------------------------------------------------------------

_MAX_BODY_BYTES = 8 * 1024


def _reject_oversized(request: Request) -> None:
    """Reject bodies larger than 8 KiB before any parsing."""
    cl = request.headers.get("content-length")
    if cl is None:
        return
    try:
        size = int(cl)
    except ValueError:
        raise _private_error(400, "invalid content-length") from None
    if size > _MAX_BODY_BYTES:
        raise _private_error(413, "request body too large") from None


async def _parse_body(model: type[BaseModel], request: Request) -> BaseModel:
    """Read the request body, parse JSON, validate against ``model``.

    Validation failures map to 400 with the private headers (not the framework's
    bare 422). The route's auth dependency has already resolved by the time we
    get here — a 401/403 will have fired above us if the caller is anonymous.
    """
    _reject_oversized(request)
    raw = await request.body()
    if len(raw) > _MAX_BODY_BYTES:
        raise _private_error(413, "request body too large") from None
    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "malformed JSON"}},
        ) from None
    if not isinstance(payload, dict):
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "body must be a JSON object"}},
        ) from None
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": exc.errors()}},
        ) from None


def _call_compose(body: _QueryBody, principal: Mapping[str, Any]) -> JSONResponse:
    query = _body_to_query(body)
    bundle = load_authorized_owner_bundle(query, principal=principal)
    bundle, dropped = _filter_bundle_for_rights(bundle)
    payload = compose_semiconductor_research(query, bundle)
    payload = _post_process_rights_limitation(payload, dropped)
    return _private_json(200, payload)


def _call_evidence(
    body: _EvidenceBody, principal: Mapping[str, Any]
) -> JSONResponse:
    query = _body_to_query(body)
    bundle = load_authorized_owner_bundle(query, principal=principal)
    bundle, dropped = _filter_bundle_for_rights(bundle)
    payload = select_authorized_evidence(query, bundle, body.assertion_ref)
    payload = _post_process_rights_limitation(payload, dropped)
    return _private_json(200, payload)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/themes/v1/research/query")
async def research_query(
    request: Request,
    response: Response,
    user: Mapping[str, Any] = Depends(require_site_full_user),
) -> JSONResponse:
    """Paid read-only snapshot of the bounded F04 composition.

    Order (LAW): auth (the dependency) runs FIRST — a 401/403 fires before any
    body parsing. Then we read the body manually and return a 400 (with the
    four private headers) on a malformed payload. Auth precedence is
    proven by ``test_unauthorized_request_never_constructs_private_reader``.
    """
    _private(response)
    body = await _parse_body(_QueryBody, request)
    try:
        return _call_compose(body, user)
    except ResearchRefusal as exc:
        raise _map_research_refusal(exc) from None
    except PrivateStoreUnavailable:
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except RightsRefusal:
        # The rights registry itself is missing or corrupt: no verdict can be
        # asked, so nothing is emitted. Fail closed behind the same headers.
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except Exception:  # noqa: BLE001 — internal detail must never cross the wire
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None


@router.post("/api/themes/v1/research/evidence")
async def research_evidence(
    request: Request,
    response: Response,
    user: Mapping[str, Any] = Depends(require_site_full_user),
) -> JSONResponse:
    """Paid read-only projection of ONE authorized assertion's evidence."""
    _private(response)
    body = await _parse_body(_EvidenceBody, request)
    try:
        return _call_evidence(body, user)
    except ResearchRefusal as exc:
        raise _map_research_refusal(exc) from None
    except PrivateStoreUnavailable:
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except RightsRefusal:
        # The rights registry itself is missing or corrupt: no verdict can be
        # asked, so nothing is emitted. Fail closed behind the same headers.
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except Exception:  # noqa: BLE001 — internal detail must never cross the wire
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None


# Catch-all behind the same dependency: malformed/encoded-slash probes stay
# behind the paywall, mirror app/earnings's private remainder route.
@router.post(
    "/api/themes/v1/research/{remainder:path}",
    include_in_schema=False,
)
def research_private_not_found(
    remainder: str,
    response: Response,
    _user: Mapping[str, Any] = Depends(require_site_full_user),
) -> None:
    del remainder, _user
    _private(response)
    raise _private_error(404, {"error": {"code": "not_available", "action": "none"}})


# 405 on the wrong method, scoped to these two paths. The handler does NOT
# require auth — a 405 is a method-mismatch signal that must be honest, not a
# second auth gate — but it still carries the private headers because the path
# is a paid product contract.
@router.api_route(
    "/api/themes/v1/research/query",
    methods=["GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
def research_query_method_not_allowed() -> None:
    raise _private_error(405, {"error": {"code": "method_not_allowed", "action": "use_post"}})


@router.api_route(
    "/api/themes/v1/research/evidence",
    methods=["GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
def research_evidence_method_not_allowed() -> None:
    raise _private_error(405, {"error": {"code": "method_not_allowed", "action": "use_post"}})


__all__ = ["PrivateStoreUnavailable", "router", "load_authorized_owner_bundle"]