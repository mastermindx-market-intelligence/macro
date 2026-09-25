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
  auth resolves. :func:`load_authorized_owner_bundle` dispatches to whatever
  the resolved registration carries as its ``load_bundle`` and names no
  vertical, no owner surface and no store; a loader that cannot serve raises
  :class:`BundleUnavailable` and gets the fixed private 503, and tests inject
  a bundle through the same seam;
* rights filtering is done against a FRESH :func:`load_registry_snapshot` — no
  process cache, so a rights decision that moves between two same-process
  requests reaches the route without a watcher or a restart (the
  ``revoked_rights_warm`` regression) — and the permit/refuse verdict itself
  is ASKED of the rights owner (``engine.theme_graph.rights``), never
  re-derived here: this transport carries no second opinion about licensing;
* no writes. ``engine.theme_graph.store.write_evidence`` is never imported; no
  subprocess, no cache layer, no cursor table. The endpoint is a closed read.

* the vertical is resolved from the CLOSED registration
  (:mod:`engine.market_ontology.theme_research_registry`, shared hook 1, Sol
  ruling #7780 issuecomment-5813801605) AFTER auth and AFTER body parsing and
  BEFORE any reader is touched: an unregistered anchor is the same private
  404 ``not_available`` the evidence route gives an unknown ref; a slice
  outside the registration's closed slice set is the same private 400
  ``invalid_request`` the body model gives a malformed field. No wildcard, no
  regex, no default vertical — the composer and evidence selector are the
  registration's own callables, and a composed payload whose ``schema`` (or,
  for the query envelope, ``definition_version``) is not the registration's
  exact value is refused (503) rather than served.

The composition module does NOT see rights: this route strips assertions whose
family is known-and-refused BEFORE handing the bundle to the registered
composer and adds ``rights_refused_families_hidden`` to ``limitations``
without naming the families — what was refused is never disclosed.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from engine.market_ontology.semiconductor_theme_research import (
    OwnerBundle,
    ResearchQuery,
    ResearchRefusal,
)
from engine.market_ontology.theme_research_binding import BundleUnavailable
from engine.market_ontology.theme_research_registry import (
    VerticalRegistration,
    registration_for,
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


class PrivateStoreUnavailable(BundleUnavailable):
    """The transport's historical name for "the owner surface cannot serve".

    Registered loaders raise the base class
    :class:`~engine.market_ontology.theme_research_binding.BundleUnavailable`;
    the route catches the base, so both spell the same fixed private 503 and
    neither message ever crosses the wire.
    """


class RegisteredContractMismatch(Exception):
    """A registered vertical's composer returned a payload that is not the
    registration's accepted contract (wrong ``schema`` / ``definition_version``
    or not a mapping). Same fixed 503 envelope on the wire as
    :class:`PrivateStoreUnavailable`; a distinct class so an in-process
    observer (tests, a future log hook — this module logs nothing today) can
    tell a composer/registration drift from an unbound reader.
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
    # A registered loader refuses a research mode it cannot serve (Sol
    # 5813801605: system_replay without a supported as-known identity). The
    # existing not_available refusal, with the mode named so the caller can
    # request `latest`; no new status code or error family. Because the loader
    # runs before the composer, `replay_cutoffs_required` above is unreachable
    # for a vertical whose loader refuses system_replay outright (today: the
    # only registered one); it stays for verticals that serve replay.
    "identity_vintage_unsupported": (
        404, {"code": "not_available", "action": "none",
              "detail": "identity_vintage_unsupported"},
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
    # Grammar only; MEMBERSHIP is decided by the closed registration for the
    # anchor (``_resolve_registration``), never by a literal in this shell.
    slice_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
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

def _rows_of(collection: object) -> tuple[tuple[Any, ...], bool]:
    """``(rows, readable)`` for one owner-supplied collection.

    ``readable`` is False when the collection cannot be iterated at all, and
    the caller withholds everything rather than letting the failure become a
    503 for the whole request. Materialising also makes a one-shot iterable
    safe: iterating it twice, or returning the original bundle after consuming
    it, would silently serve nothing while reporting nothing withheld.
    """
    if isinstance(collection, (str, bytes)) or not isinstance(collection, Iterable):
        return (), False
    try:
        return tuple(collection), True
    except Exception:  # noqa: BLE001 — a hostile iterator withholds, never 503s
        return (), False


def _canonically_attributable(ref: str) -> bool:
    """False when a LITERAL-PREFIX match cannot be trusted to name where the
    ref really points.

    ``family_for_source_ref`` matches a prefix and nothing else, so
    ``data/baskets/../finviz_themes/private.json`` starts with
    ``data/baskets/``, resolves to ``mastermind_curated`` and gets SERVED
    while naming a file in another family's directory. This transport does
    not normalize the ref — normalizing would be this route forming a second
    opinion about what a path means, which it is forbidden to do — it simply
    declines to attribute a ref carrying a relative segment or a backslash.
    """
    if "\\" in ref or "%" in ref:
        # A percent-escape is EXACTLY a ref whose literal prefix cannot be
        # trusted to say where it points. RFC 3986 normalisation decodes %2E to
        # "." before dot-segment removal, so "%2e%2e" is not a directory name
        # to anything that dereferences the URI — and now that the table
        # carries https prefixes, encoded traversal is the normal spelling of
        # the attack, not an exotic one. An independent review measured
        # "https://www.sec.gov/Archives/%2e%2e/%2e%2e/vendor/private.json"
        # resolving to sec_edgar, a PERMITTED family, and being served.
        # Declining to decode is the same move this function already makes for
        # "..": the transport never resolves what a path means.
        return False
    return not any(segment in (".", "..") for segment in ref.split("/"))


def _attributable_family(source: object) -> str | None:
    """The ONE rights family this transport can attribute a row's source to.

    None means "cannot attribute", which on this EMISSION path means withhold.
    Four ways to get None, all fail-closed:

    * ``source`` is not a mapping — a row whose source this transport cannot
      even read is not a row it can publish;
    * no readable ref (missing, empty, or not a string);
    * a ref that is not canonically attributable (see
      :func:`_canonically_attributable`);
    ``source_uri`` is the ONLY field consulted. ``locator`` is not a second
    opinion about the same thing and was never a path: the corpus fills it with
    ``para-3``, ``table-1`` — a pointer INSIDE the cited document — and the
    v1.1 proposal names the rights dependency as ``family_for_source_ref(
    source_uri)``, listing ``locator`` as a sibling field with no rights role.
    Two earlier readings were both wrong in the same place. Falling back to
    ``locator`` when ``source_uri`` was absent let a paragraph pointer that
    happens to look like a repo path ("data/baskets/x.json") ATTRIBUTE a row
    the rights owner never attributed. Treating the two as co-equal vetoes then
    manufactured contradictions out of an external URL and an internal pointer,
    which withholds legitimate rows. Reading one field is strictly narrower
    than both, and it is the only reading that does not require this transport
    to hold an opinion about what a locator means.
    """
    if not isinstance(source, Mapping):
        return None
    ref = source.get("source_uri")
    # Exact str, never a subclass: a hostile ``__str__`` could hand the family
    # resolver a different string than the one this row carries on the wire.
    if type(ref) is not str or not ref.strip():
        return None
    if not _canonically_attributable(ref):
        return None
    return family_for_source_ref(ref)


def _filter_bundle_for_rights(
    bundle: OwnerBundle, *, snapshot: tuple[str, dict] | None = None,
) -> tuple[OwnerBundle, bool]:
    """Withhold assertions the rights OWNER refuses, and assertions whose
    source this transport cannot attribute at all.

    Two rules, both fail-closed:

    * a MAPPED family is withheld when
      :func:`engine.theme_graph.rights.assert_current_emission_allowed`
      refuses it on a FRESH snapshot — the single veto, so tightening the
      owner's rule reaches this route without a transport change;
    * an UNMAPPED source ref (``family_for_source_ref`` returns None, which
      includes an assertion carrying no source ref at all) is withheld too.
      This reverses the earlier "no opinion, so no opinion here" reading, on
      Sol #7780 issuecomment-5813801605: unmapped rights fail CLOSED. The
      owner's None genuinely means "no opinion" for its own guard, which
      warns on a DISAGREEMENT and must not manufacture one out of ignorance;
      but this is an EMISSION path, and emitting material no rights row
      covers is exactly the decision the registry exists to make. An
      unattributable assertion is not published;
    * a row whose ``source`` this transport cannot READ, or whose two refs
      contradict each other, or whose ref cannot be attributed by a literal
      prefix at all, is withheld — :func:`_attributable_family` is the single
      place that decides, and it never normalizes a path or resolves a
      contradiction on the owner's behalf;
    * a row that is not a mapping is withheld by itself. It used to raise
      ``AttributeError`` into the route's catch-all and return a 503 for the
      WHOLE request, which is how one malformed row from the owner denied a
      caller every row it was entitled to. A whole COLLECTION that cannot be
      iterated withholds everything for the same reason, rather than raising.

    Interpretation blocks are withheld alongside the assertions they read.
    A block names its inputs in ``input_revisions``; prose derived from a
    withheld assertion is that assertion reaching the wire in another form,
    and the composer would otherwise still emit it (marked stale, but
    emitted). A block referencing no revision present in the served
    assertions is withheld as well, and revisions are compared as the
    strings they are — never coerced, so "12" and 12 stay different
    revisions.

    Returns the rewritten bundle and a flag telling the caller whether
    anything was withheld — the route turns that into the
    ``rights_refused_families_hidden`` limitation string without naming which
    families or sources were refused.

    The private half is unbound today (R4 open), so ``assertions`` and
    ``interpretation_blocks`` are empty on every served request and both
    rules are currently inert. They are the fail-closed default the moment R4
    binds them, which is the only safe direction for a default to have.

    ``snapshot`` is the request's ONE rights read (the route loads it once and
    hands the same object to the registered loader, whose fingerprinted
    ``rights_revision`` therefore equals the revision enforced here); a direct
    caller that passes none gets a fresh read, the historical behaviour.
    """
    if snapshot is None:
        snapshot = load_registry_snapshot()
    verdicts: dict[str, bool] = {}  # per-request memo: one owner call per distinct family
    kept: list[Mapping[str, Any]] = []
    dropped = False
    # Materialised ONCE, up front, for two reasons. A collection this transport
    # cannot even iterate (None, a scalar) is withheld rather than raised into
    # the route's catch-all as a 503 for the whole request — the same rule the
    # rows follow. And a one-shot iterable would otherwise be CONSUMED here and
    # reach the composer empty while ``dropped`` stayed False, so the response
    # would drop every row and say nothing was withheld.
    assertions, assertions_readable = _rows_of(bundle.assertions)
    blocks_in, blocks_readable = _rows_of(bundle.interpretation_blocks)
    dropped = not (assertions_readable and blocks_readable)
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            # A row this transport cannot read is WITHHELD, never fatal.
            # Before this, ``assertion.get(...)`` raised AttributeError, the
            # route's catch-all turned it into a 503, and one malformed row
            # from the owner took down the entire request instead of dropping
            # itself. Withholding is the fail-closed answer; 503 is not.
            dropped = True
            continue
        family = _attributable_family(assertion.get("source"))
        if family is None:
            # Unmapped, unreadable, non-canonical or self-contradicting source
            # ref: fail closed (see :func:`_attributable_family`).
            dropped = True
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
    # Compared as the strings they are, never coerced: ``str()`` on both sides
    # made the integer 12 and the string "12" the same revision, so a block
    # naming a revision that was NOT served could survive. A curation revision
    # is a string by its own contract
    # (``engine.theme_graph.curation_assertion.curation_revision``), so a
    # non-string here is a malformed row, not a value to convert.
    served_revisions = {
        a["curation_revision"] for a in kept
        if isinstance(a.get("curation_revision"), str) and a["curation_revision"]
    }
    blocks: list[Mapping[str, Any]] = []
    for block in blocks_in:
        if not isinstance(block, Mapping):
            dropped = True
            continue
        inputs = block.get("input_revisions")
        if not isinstance(inputs, (list, tuple)) or not inputs:
            # No readable input list (absent, empty, or a bare string, which
            # would otherwise iterate as characters): withheld.
            dropped = True
            continue
        if all(isinstance(rev, str) and rev in served_revisions for rev in inputs):
            blocks.append(block)
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
        interpretation_blocks=tuple(blocks),
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
    query: ResearchQuery,
    *,
    principal: Mapping[str, Any],
    registration: VerticalRegistration,
    rights_snapshot: tuple[str, dict],
) -> OwnerBundle:
    """The seam the route calls to fetch a bundle for ``query``.

    Production dispatches to the closed registration's own loader
    (``registration.load_bundle``) — the shell names no vertical's owner
    surfaces, exactly as it names no composer. The loader receives ONLY the
    parsed query (anchor already resolved, slice already a member of the
    registration's closed set) and the request's single rights snapshot;
    never a path, URL, locator, event id, ticker or CIK from request JSON.
    ``principal`` is not forwarded: entitlement was decided by the route's
    auth dependency, and the loader must not re-decide it.

    Tests monkeypatch this symbol with a synthetic bundle. A loader that
    cannot serve raises :class:`BundleUnavailable` → 503; one that refuses a
    research mode raises the composer's ``ResearchRefusal`` → the existing
    private refusal mapping.
    """
    del principal
    return registration.load_bundle(query, rights_snapshot=rights_snapshot)


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


# ---------------------------------------------------------------------------
# Vertical resolution — closed registration, after auth + parse, before any
# reader; unknown anchor / foreign slice fail closed with the existing shapes
# ---------------------------------------------------------------------------

def _resolve_registration(body: _QueryBody) -> VerticalRegistration:
    """Resolve the vertical for ``body.anchor_theme_id`` from the closed
    registration. Unregistered anchor → the route's private 404
    ``not_available`` (the same body the evidence route gives an unknown ref;
    the anchor is not echoed and the registry is not listed). Registered anchor
    with a slice outside its closed slice set → the private 400
    ``invalid_request`` the body model gives a malformed field. Nothing here
    reads a bundle, a file or the environment."""
    try:
        registration = registration_for(body.anchor_theme_id)
    except Exception:  # noqa: BLE001 — a registry fault is a private 503, never a bare 500
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    if registration is None:
        raise _private_error(404, {"error": {"code": "not_available", "action": "none"}})
    if not isinstance(registration, VerticalRegistration):
        # A registry that hands back anything but a registration is a fault,
        # not a vertical: stay inside the private envelope (never a bare 500).
        raise _private_error(
            503,
            {"error": {"code": "service_unavailable", "action": "retry_later"}},
        )
    if body.slice_key not in registration.slice_keys:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "slice_key is not registered for this anchor"}},
        )
    return registration


def _require_registered_contract(
    payload: Any,
    expected_schema_id: str,
    expected_definition_version: str | None = None,
) -> dict[str, Any]:
    """A composed payload is served only when it is a mapping whose ``schema``
    is the registration's exact schema id and — for the query envelope, which
    carries one — whose ``definition_version`` is the registration's exact
    version; anything else is a composer / registration mismatch and fails
    closed (the caller maps it to the fixed 503 envelope)."""
    if not isinstance(payload, Mapping) or payload.get("schema") != expected_schema_id:
        raise RegisteredContractMismatch("composed payload does not carry the registered schema")
    if expected_definition_version is not None and \
            payload.get("definition_version") != expected_definition_version:
        raise RegisteredContractMismatch(
            "composed payload does not carry the registered definition_version"
        )
    return dict(payload)


def _call_compose(
    body: _QueryBody, principal: Mapping[str, Any], registration: VerticalRegistration,
) -> JSONResponse:
    query = _body_to_query(body)
    snapshot = load_registry_snapshot()  # ONE rights read per request (T03 owner)
    bundle = load_authorized_owner_bundle(
        query, principal=principal, registration=registration, rights_snapshot=snapshot,
    )
    bundle, dropped = _filter_bundle_for_rights(bundle, snapshot=snapshot)
    payload = _require_registered_contract(
        registration.compose(query, bundle),
        registration.schema_id,
        registration.definition_version,
    )
    payload = _post_process_rights_limitation(payload, dropped)
    return _private_json(200, payload)


def _call_evidence(
    body: _EvidenceBody, principal: Mapping[str, Any], registration: VerticalRegistration,
) -> JSONResponse:
    query = _body_to_query(body)
    snapshot = load_registry_snapshot()  # ONE rights read per request (T03 owner)
    bundle = load_authorized_owner_bundle(
        query, principal=principal, registration=registration, rights_snapshot=snapshot,
    )
    bundle, dropped = _filter_bundle_for_rights(bundle, snapshot=snapshot)
    payload = _require_registered_contract(
        registration.select_evidence(query, bundle, body.assertion_ref),
        registration.evidence_schema_id,
    )
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
    four private headers) on a malformed payload; then the closed registration
    resolves the vertical (private 404 on an unregistered anchor, private 400
    on a foreign slice) before any reader is touched. Auth precedence is
    proven by ``test_unauthorized_request_never_constructs_private_reader``.
    """
    _private(response)
    body = await _parse_body(_QueryBody, request)
    # Closed registration AFTER auth + parse, BEFORE any reader: its private
    # 404/400 must reach the wire as-is, so it is resolved outside the
    # catch-all below.
    registration = _resolve_registration(body)
    try:
        return _call_compose(body, user, registration)
    except ResearchRefusal as exc:
        raise _map_research_refusal(exc) from None
    except (BundleUnavailable, RegisteredContractMismatch):
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
    registration = _resolve_registration(body)
    try:
        return _call_evidence(body, user, registration)
    except ResearchRefusal as exc:
        raise _map_research_refusal(exc) from None
    except (BundleUnavailable, RegisteredContractMismatch):
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