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

import dataclasses
import json
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from engine.market_ontology.theme_research_binding import (
    BundleUnavailable,
    ResearchRefusal,
    V2_REQUEST_SCHEMA,
    V2_RESPONSE_SCHEMA,
    context_generation,
    validate_cutoff_format,
)
from engine.market_ontology.theme_research_registry import (
    VerticalRegistration,
    profile_registration_for,
    registration_for,
)

if TYPE_CHECKING:  # pragma: no cover — annotations only (PEP 563 is on)
    # This SHARED transport used to import ``OwnerBundle``, ``ResearchQuery``
    # and ``ResearchRefusal`` from the semiconductor composer at module level,
    # so loading the shell loaded ONE vertical's entire closure and the shell
    # could not serve a second vertical without it (Sol #7870
    # issuecomment-5895067178). The refusal class moved to the shared
    # foundation above, because an ``except`` clause must resolve at runtime.
    # The two dataclasses are only ever ANNOTATED here: the shell builds a
    # query through ``registration.build_query`` and derives a filtered bundle
    # with ``dataclasses.replace``, so it needs neither type at runtime and
    # names no vertical.
    from engine.market_ontology.semiconductor_theme_research import (
        OwnerBundle,
        ResearchQuery,
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
    # A supplied cutoff the engine cannot read. It is a PERMANENT fault in the
    # request, so it belongs with the other 400s: before this row existed the
    # first parse happened inside a time gate, `_le` raised a bare ValueError,
    # and the catch-all below answered 503 `retry_later` — telling the caller
    # to try again with a string that can never work. Where no gate read it,
    # the request answered a silent 200 that echoed the unreadable value back
    # with no limitation marking it. Measured by the Energy seat over
    # nuclear's route (#7870 issuecomment-5868018569 / 5869344590 / 5870740225).
    "cutoff_unreadable": (
        400, {"code": "invalid_request", "action": "fix_request"},
    ),
    # A registered loader refuses a research mode it cannot serve (Sol
    # 5813801605: system_replay without a supported as-known identity). The
    # existing not_available refusal, with the mode named so the caller can
    # request `latest`; no new status code or error family. Because the loader
    # runs before BOTH the composer and the shell's `_refuse_unreadable_cutoff`,
    # `replay_cutoffs_required` above — and `cutoff_unreadable` in system_replay
    # — are unreachable for a vertical whose loader refuses that mode outright
    # (today: the only registered one). They stay for verticals that serve
    # replay, and `cutoff_unreadable` is reachable in every SERVED mode. An
    # independent audit caught the opposite order silently converting this 404
    # into a 400; `test_system_replay_unsupported_mode_outranks_bad_cutoff`
    # pins it against the real registration.
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


#: v2 (lane 5): the profile adapters refuse through their OWN ValueError
#: subclasses carrying a ``.code`` — duck-typed, never imported here (the
#: shell names no vertical's refusal class). ``code`` bases only; an adapter
#: code with a ``:suffix`` (``sealed_input_unavailable:run_context``) maps by
#: its base. Unknown bases fall through to the fixed private 503 — the shell
#: never guesses a severity for a code it was not told about.
_PRIVATE_UNAVAILABLE = {"code": "not_available", "action": "none"}
_V2_VERTICAL_REFUSAL_MAP: dict[str, tuple[int, dict[str, str]]] = {
    # The profile's own private unavailable verdicts: an unresolvable subject
    # or a sealed input half that no admitted producer supplies today. Same
    # bytes as ``not_available`` — no existence disclosure, no source/rights
    # detail, 404-class.
    "company_ref_unresolved": (404, _PRIVATE_UNAVAILABLE),
    "theme_ref_unavailable": (404, _PRIVATE_UNAVAILABLE),
    "sealed_input_unavailable": (404, _PRIVATE_UNAVAILABLE),
    "replay_identity_unavailable": (404, _PRIVATE_UNAVAILABLE),
    # A registry-declared view the registration's own guard also refuses;
    # the shell pre-checks ``view_keys`` so this is normally unreachable.
    "view_not_registered": (
        400, {"code": "invalid_request", "action": "fix_request"},
    ),
    # Contract/carrier drift on the vertical's side: fixed private 503s.
    "shared_shell_unavailable": (
        503, {"code": "service_unavailable", "action": "retry_later"},
    ),
    "evidence_schema_violation": (
        503, {"code": "service_unavailable", "action": "retry_later"},
    ),
}


def _map_typed_vertical_refusal(exc: ValueError) -> HTTPException | None:
    """Map a duck-typed vertical refusal (``ValueError`` carrying ``.code``)
    to its private envelope. ``None`` means "not a refusal this shell knows" —
    the caller answers the fixed private 503, never a bare 500."""
    code = getattr(exc, "code", None)
    if not isinstance(code, str) or not code:
        return None
    base = code.split(":", 1)[0]
    if base == "not_available":
        return _private_error(404, {"error": dict(_PRIVATE_UNAVAILABLE)})
    # A code the SHARED map already knows (``generation_changed`` → 409
    # refresh, the pagination/cutoff 400s) gets the shared envelope whatever
    # class carried it — the verticals refuse through their own ValueError
    # subclasses with the same code vocabulary the foundation defines.
    entry = _V2_VERTICAL_REFUSAL_MAP.get(base) or _RESEARCH_REFUSAL_MAP.get(base)
    if entry is None:
        return None
    status, envelope = entry
    return _private_error(status, {"error": dict(envelope)})


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
    # Grammar only, for the same reason and by the same rule as ``slice_key``:
    # these five views were the SEMICONDUCTOR vocabulary pinned in a shared
    # transport, which is a membership decision the shell is not entitled to
    # make for any other vertical (Sol #7870 issuecomment-5923155205). An
    # unregistered view is refused by ``_resolve_registration`` with the same
    # private 400 an unregistered slice gets.
    view: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    time_mode: Literal["latest", "source_history", "system_replay"]
    source_cutoff: str | None = Field(default=None, max_length=32)
    recorded_cutoff: str | None = Field(default=None, max_length=32)
    offset: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=50, ge=1, le=100)
    expected_generation: str | None = Field(default=None, pattern=r"^gen_[0-9a-f]{32}$")


class _EvidenceBody(_QueryBody):
    # The theme segment is the assertion's OWN `scope.canonical_theme_id`,
    # because `source_ref_for` builds the ref from that field. Two forms are
    # in use: the crosswalk SLUG the semiconductor corpus carries, and the
    # identity owner's canonical NODE id `theme:<slug>` that the canonical-id
    # law (#7870 issuecomment-5812295091) tells every vertical to mint. This
    # pattern admitted only the first, so a ref minted by this repo's own
    # `source_ref_for` from a law-conforming assertion was refused 400
    # `string_pattern_mismatch` at the door — reported by the Energy seat as
    # the one thing nuclear needs from this carrier (#7870
    # issuecomment-5866433049 item 1). `ltheme:` stays refused: the identity
    # owner declares it deliberately non-canonical.
    assertion_ref: str = Field(
        min_length=1, max_length=256,
        pattern=r"^gmi-curation://(?:theme:)?[a-z0-9_]+/gmirca_[0-9a-f]{32}$",
    )
    expected_generation: str = Field(pattern=r"^gen_[0-9a-f]{32}$")


def _body_to_query(
    body: _QueryBody | _EvidenceBody, registration: VerticalRegistration,
) -> ResearchQuery:
    """Build the resolved vertical's own query object from the parsed body.

    The field NAMES are the shared query contract every registered vertical
    accepts; the vertical owns the type and its literals, so a value this
    shell admitted by grammar but the vertical does not accept fails in the
    vertical. The shell constructs no vertical type itself.

    Construction only: the shared-grammar cutoff check deliberately does NOT
    live here, because this runs before the loader and would preempt a
    loader's own `not_available` verdict. See `_refuse_unreadable_cutoff`.
    """
    return registration.build_query(
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
# v2 body models — the closed ``theme_research.request/v2`` union (lane 5)
# ---------------------------------------------------------------------------

#: The context expectation is the SHELL's own surface: always ``gen_`` width
#: 32 (:func:`engine.market_ontology.theme_research_binding.context_generation`).
_V2_CONTEXT_PATTERN = r"^gen_[0-9a-f]{32}$"
#: Parse-time grammar for the NATIVE expectation: a prefix hex-width token
#: (``gen_…``/``tecd_…``). The per-entry EXACT grammar (registration
#: ``native_generation_prefix``/``native_generation_width``) is enforced
#: AFTER the registration resolves — the shell cannot know the entry's
#: grammar before it knows the entry.
_V2_NATIVE_PATTERN = r"^[a-z0-9_]{1,16}_[0-9a-f]{8,64}$"
#: The v2 assertion-ref grammar: any owner-minted ``gmi-curation://`` ref,
#: canonical ``theme:``-prefixed or slug theme segment, hyphen/dot included
#: (canonical ids like ``theme:technology-ex-semis`` are legal).
_V2_ASSERTION_REF_PATTERN = (
    r"^gmi-curation://(?:theme:)?[a-z0-9_.\-]+/gmirca_[0-9a-f]{32}$"
)


class _V2Body(BaseModel):
    """Fields every v2 entry kind shares. ``extra="forbid"``: a field from
    another entry kind (``anchor_theme_id`` on a profile, ``company_ref`` on
    the theme kind, a ``cursor`` on a single-document profile) is a private
    400 at parse, never silently ignored."""

    model_config = ConfigDict(extra="forbid")

    request_schema: Literal["theme_research.request/v2"]
    view: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    time_mode: Literal["latest", "source_history", "system_replay"]
    source_cutoff: str | None = Field(default=None, max_length=32)
    recorded_cutoff: str | None = Field(default=None, max_length=32)
    expected_generation: str | None = Field(
        default=None, max_length=80, pattern=_V2_NATIVE_PATTERN,
    )
    expected_context_generation: str | None = Field(
        default=None, pattern=_V2_CONTEXT_PATTERN,
    )


class _V2ThemeBody(_V2Body):
    """``entry_kind="theme"`` — the anchored, paginated collection (the v1
    shape plus the discriminator and the context expectation)."""

    entry_kind: Literal["theme"]
    anchor_theme_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    slice_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    offset: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=50, ge=1, le=100)


class _V2CompanyProfileBody(_V2Body):
    """``entry_kind="company_profile"`` — single-document: NO ``limit`` field
    exists (supplying one is the private 400 ``extra="forbid"`` gives), and a
    nonzero ``offset`` is refused after the profile resolves rather than
    silently ignored."""

    entry_kind: Literal["company_profile"]
    profile_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9_.\-]+$")
    company_ref: str = Field(
        min_length=1, max_length=128,
        pattern=r"^(?:[A-Za-z0-9:._\-]+|co:(?:us|cn|hk|ca|intl):[A-Za-z0-9.\-]+#[0-9]+)$",
    )
    offset: int = Field(default=0, ge=0)


class _V2SectorProfileBody(_V2Body):
    """``entry_kind="sector_profile"`` — single-document, same pagination
    law as the company profile."""

    entry_kind: Literal["sector_profile"]
    profile_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9_.\-]+$")
    sector_ref: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9:._\-]+$")
    offset: int = Field(default=0, ge=0)


_V2_QUERY_MODELS: Mapping[str, type[_V2Body]] = {
    "theme": _V2ThemeBody,
    "company_profile": _V2CompanyProfileBody,
    "sector_profile": _V2SectorProfileBody,
}


def _evidence_body(query_model: type[_V2Body]) -> type[_V2Body]:
    """The evidence twin of one query model: same entry kind and fields, plus
    the assertion ref and BOTH expectations REQUIRED (packet §3.6: every
    evidence request carries the paired ``expected_generation`` +
    ``expected_context_generation`` — a missing one is a private 400 at
    parse, not a silent first-page serve)."""

    class _Body(query_model):
        assertion_ref: str = Field(
            min_length=1, max_length=256, pattern=_V2_ASSERTION_REF_PATTERN,
        )
        expected_generation: str = Field(
            min_length=8, max_length=80, pattern=_V2_NATIVE_PATTERN,
        )
        expected_context_generation: str = Field(pattern=_V2_CONTEXT_PATTERN)

    return _Body


_V2_EVIDENCE_MODELS: Mapping[str, type[_V2Body]] = {
    kind: _evidence_body(model) for kind, model in _V2_QUERY_MODELS.items()
}


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
    # ``replace`` on the bundle INSTANCE, not a constructor call on a named
    # vertical class: every other field was copied through verbatim, so this
    # is the same object by construction, and the shell no longer has to know
    # which dataclass a vertical's loader returned or how many fields it has.
    # A field added to a vertical's bundle is carried here automatically
    # instead of being silently dropped by a nine-field copy.
    new_bundle = dataclasses.replace(
        bundle, assertions=tuple(kept), interpretation_blocks=tuple(blocks),
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


async def _read_json_object(request: Request) -> dict[str, Any]:
    """Read the request body and parse it as a JSON object (size-capped).

    Failures map to the same private 400/413 envelopes ``_parse_body`` always
    gave. Split out of it (lane 5) so a route can read the body ONCE and
    dispatch on the v2 ``request_schema`` discriminator before choosing the
    validation model — v1 bodies are then validated bytewise as before.
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
    return payload


def _validate_body(model: type[BaseModel], payload: Mapping[str, Any]) -> BaseModel:
    """Validate an already-parsed JSON object against ``model``.

    Validation failures map to 400 with the private headers (not the
    framework's bare 422). The route's auth dependency has already resolved
    by the time we get here — a 401/403 will have fired above us if the
    caller is anonymous.
    """
    try:
        return model.model_validate(dict(payload))
    except ValidationError as exc:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": exc.errors()}},
        ) from None


async def _parse_body(model: type[BaseModel], request: Request) -> BaseModel:
    """Read the request body, parse JSON, validate against ``model``.

    Validation failures map to 400 with the private headers (not the framework's
    bare 422). The route's auth dependency has already resolved by the time we
    get here — a 401/403 will have fired above us if the caller is anonymous.
    """
    return _validate_body(model, await _read_json_object(request))


# ---------------------------------------------------------------------------
# Vertical resolution — closed registration, after auth + parse, before any
# reader; unknown anchor / foreign slice fail closed with the existing shapes
# ---------------------------------------------------------------------------

def _resolve_registration(body: _QueryBody) -> VerticalRegistration:
    """Resolve the vertical for ``body.anchor_theme_id`` from the closed
    registration. Unregistered anchor → the route's private 404
    ``not_available`` (the same body the evidence route gives an unknown ref;
    the anchor is not echoed and the registry is not listed). Registered anchor
    with a slice or a view outside its closed sets → the private 400
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
    if body.view not in registration.view_keys:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "view is not registered for this anchor"}},
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


def _refuse_unreadable_cutoff(
    body: _QueryBody | _EvidenceBody | _V2Body,
) -> None:
    """Refuse a supplied cutoff the engine cannot read.

    Scope, stated exactly: this closes the silent-200 half for every vertical
    whose LOADER does not itself parse a cutoff. Because of the ORDER LAW
    below the loader runs first, so a loader that parses one can still raise
    a bare ValueError into the catch-all's 503 before this check is reached.
    That residue is the loader author's to close, not this shell's — a
    registering vertical that reads cutoffs inside its loader must refuse an
    unreadable one there.

    The Energy seat measured both faults this prevents over nuclear's route
    (#7870 issuecomment-5868018569 / 5869344590 / 5870740225): a bare
    ValueError raised inside a time gate, answered 503 `retry_later` by the
    catch-all, telling the caller to retry a string that can never work; and,
    where no gate read the value at all, a silent 200 that echoed the
    unreadable cutoff back with no limitation marking it. `cutoff_unreadable`
    already mapped to 400, but only the DETECTION lived in a vertical
    composer, so a vertical that omitted the call inherited the silent 200.

    ORDER LAW — this runs AFTER `load_authorized_owner_bundle`, never before.
    A loader may refuse the requested mode outright (`identity_vintage_
    unsupported`, 404 `not_available` + `action: none`; today the only
    registered loader refuses `system_replay` on the mode token alone). That
    verdict is the more actionable truth: no cutoff the caller could supply
    would make an unserved mode work, so answering 400 `fix_request` first
    would send them to fix a field that is not the obstacle. An independent
    READ_ONLY audit of the first placement — inside `_body_to_query`, ahead
    of the loader — found exactly that silent 404 -> 400 conversion, which is
    why the check sits here and is pinned by a route test on the real
    registration (`test_system_replay_unsupported_mode_outranks_bad_cutoff`).

    FORMAT only: `validate_replay_cutoffs` stays vertical-owned, because which
    modes a vertical serves differs per vertical (see the
    `identity_vintage_unsupported` note on the refusal map). The two
    validators are NOT disjoint, and an earlier revision of this docstring
    claimed they were: there are two cutoff FIELDS, so one request can carry
    a missing one and an unreadable one at once. `system_replay` with
    `source_cutoff="not-a-date"` and `recorded_cutoff=None` raises
    `replay_cutoffs_required` from one and `cutoff_unreadable` from the other,
    so this placement DOES reorder them for that input. It is unobservable
    rather than harmless: both codes land in the same byte-identical 400
    (`invalid_request` / `fix_request`, no `detail`), which is also why the
    earlier claim that the reorder was externally visible was withdrawn. If
    that envelope is ever differentiated, this pair needs a declared
    precedence and a test. Idempotent for a vertical that validates too: the
    check is pure and raises only on a cutoff `le` could not compare.
    """
    validate_cutoff_format(body.source_cutoff, body.recorded_cutoff)


def _call_compose(
    body: _QueryBody, principal: Mapping[str, Any], registration: VerticalRegistration,
) -> JSONResponse:
    query = _body_to_query(body, registration)
    snapshot = load_registry_snapshot()  # ONE rights read per request (T03 owner)
    bundle = load_authorized_owner_bundle(
        query, principal=principal, registration=registration, rights_snapshot=snapshot,
    )
    _refuse_unreadable_cutoff(body)  # AFTER the loader: see ORDER LAW there
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
    query = _body_to_query(body, registration)
    snapshot = load_registry_snapshot()  # ONE rights read per request (T03 owner)
    bundle = load_authorized_owner_bundle(
        query, principal=principal, registration=registration, rights_snapshot=snapshot,
    )
    _refuse_unreadable_cutoff(body)  # AFTER the loader: see ORDER LAW there
    bundle, dropped = _filter_bundle_for_rights(bundle, snapshot=snapshot)
    payload = _require_registered_contract(
        registration.select_evidence(query, bundle, body.assertion_ref),
        registration.evidence_schema_id,
    )
    payload = _post_process_rights_limitation(payload, dropped)
    return _private_json(200, payload)


# ---------------------------------------------------------------------------
# v2 dispatch — the closed ``theme_research.request/v2`` union through the
# SAME router, registries, seam and rights filter (lane 5)
# ---------------------------------------------------------------------------

def _parse_v2_body(
    models: Mapping[str, type[_V2Body]], payload: Mapping[str, Any],
) -> _V2Body:
    """Validate one raw v2 payload against the closed per-kind model. An
    ``entry_kind`` outside the three closed kinds (absent, foreign, non-string)
    is the private 400 ``invalid_request`` — the union is closed at the door,
    never normalised. A body carrying ``request_schema`` with any value other
    than the v2 constant fails the model's ``Literal`` the same way."""
    kind = payload.get("entry_kind")
    model = models.get(kind) if isinstance(kind, str) else None
    if model is None:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "entry_kind must be one of the closed v2 entry kinds"}},
        )
    validated = _validate_body(model, payload)
    assert isinstance(validated, _V2Body)  # models map holds only _V2Body subclasses
    return validated


def _resolve_v2_registration(body: _V2Body) -> VerticalRegistration:
    """Resolve the registration for one parsed v2 union member.

    ``theme`` → the closed anchor REGISTRY, exactly as v1 (unknown anchor →
    the same private 404 ``not_available``). ``company_profile`` /
    ``sector_profile`` → the closed PROFILE_REGISTRY (unknown profile → the
    same private 404 — never an echo, never a list). Then the registered-set
    checks in the v1 order: the SUBJECT first (a subject the entry does not
    carry is an existence question → 404), then view and time_mode (a field
    value a registered entry refuses → 400 ``fix_request``). The subject is
    read off the registration's OWN ``subject_field`` column — the shell
    hardcodes no per-vertical field name."""
    if isinstance(body, _V2ThemeBody):
        try:
            registration = registration_for(body.anchor_theme_id)
        except Exception:  # noqa: BLE001 — registry fault is a private 503, never a bare 500
            raise _private_error(
                503,
                {"error": {"code": "service_unavailable", "action": "retry_later"}},
            ) from None
        if registration is None:
            raise _private_error(
                404, {"error": {"code": "not_available", "action": "none"}},
            )
        if not isinstance(registration, VerticalRegistration):
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
    else:
        try:
            registration = profile_registration_for(body.profile_id)
        except Exception:  # noqa: BLE001 — registry fault is a private 503, never a bare 500
            raise _private_error(
                503,
                {"error": {"code": "service_unavailable", "action": "retry_later"}},
            ) from None
        if (registration is None or not isinstance(registration, VerticalRegistration)
                or registration.entry_kind != body.entry_kind):
            raise _private_error(
                404, {"error": {"code": "not_available", "action": "none"}},
            )
        subject = getattr(body, registration.subject_field, None)
        if registration.subject_values and subject not in registration.subject_values:
            # A closed subject set that does not carry the request's subject:
            # the entry does not exist FOR THAT SUBJECT — the same private
            # 404 an unknown profile id gets, never a 400 naming the set.
            raise _private_error(
                404, {"error": {"code": "not_available", "action": "none"}},
            )
    if body.view not in registration.view_keys:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "view is not registered for this entry kind"}},
        )
    if body.time_mode not in registration.time_modes:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "time_mode is not registered for this entry kind"}},
        )
    return registration


def _v2_native_generation_well_formed(
    value: Any, registration: VerticalRegistration,
) -> bool:
    """Exact string test against the native-generation grammar the
    registration declares: the entry's own ``native_generation_prefix``
    followed by exactly ``native_generation_width`` lowercase hex chars.
    Plain string arithmetic, no pattern engine — the transport's
    no-regex law (pinned by the source-scan test) is older than v2 and
    still holds."""
    if not isinstance(value, str):
        return False
    prefix = registration.native_generation_prefix
    width = registration.native_generation_width
    return (
        value.startswith(prefix)
        and len(value) == len(prefix) + width
        and all(char in "0123456789abcdef" for char in value[len(prefix):])
    )


def _check_v2_query_semantics(
    body: _V2Body, registration: VerticalRegistration,
) -> None:
    """The shell-owned v2 request laws a body must satisfy AFTER the entry
    resolves: single-document pagination, expectation pairing, and the
    entry's exact native grammar. All private 400 ``fix_request`` — the
    refusal names the rule broken, never any source or rights state."""
    if registration.single_document and body.offset != 0:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "pagination is not supported for a "
                                  "single-document entry kind"}},
        )
    supplied_native = body.expected_generation is not None
    supplied_context = body.expected_context_generation is not None
    if supplied_native != supplied_context:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "expected_generation and "
                                  "expected_context_generation must be "
                                  "supplied together"}},
        )
    is_continuation = (
        not registration.single_document and body.offset > 0
    )
    if is_continuation and not supplied_native:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "a continuation request (offset > 0) "
                                  "requires the paired expected_generation "
                                  "and expected_context_generation"}},
        )
    if supplied_native and not _v2_native_generation_well_formed(
            body.expected_generation, registration,
    ):
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "expected_generation does not match this "
                                  "entry's generation grammar"}},
        )


def _check_v2_evidence_semantics(
    body: _V2Body, registration: VerticalRegistration,
) -> None:
    """The evidence twins of the query laws. The expectation PAIR is required
    by the evidence body models themselves (a missing one is a parse-level
    400); here the single-document offset law and the native grammar apply.
    The context grammar is the shell's own and already strict at parse."""
    if registration.single_document and body.offset != 0:
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "pagination is not supported for a "
                                  "single-document entry kind"}},
        )
    if not _v2_native_generation_well_formed(
            body.expected_generation, registration,
    ):
        raise _private_error(
            400,
            {"error": {"code": "invalid_request", "action": "fix_request",
                        "detail": "expected_generation does not match this "
                                  "entry's generation grammar"}},
        )


def _v2_query_kwargs(
    body: _V2Body, registration: VerticalRegistration,
) -> dict[str, Any]:
    """The semantic fields the registration's own ``build_query`` accepts,
    per entry kind — the NATIVE expectation forwarded, the SHELL-level
    context expectation NEVER (it is compared here and dropped)."""
    del registration  # the closed union, not a per-registration column
    common = {
        "view": body.view,
        "time_mode": body.time_mode,
        "source_cutoff": body.source_cutoff,
        "recorded_cutoff": body.recorded_cutoff,
        "expected_generation": body.expected_generation,
    }
    if isinstance(body, _V2ThemeBody):
        return {
            "anchor_theme_id": body.anchor_theme_id,
            "slice_key": body.slice_key,
            "offset": body.offset,
            "limit": body.limit,
            **common,
        }
    if isinstance(body, _V2CompanyProfileBody):
        return {
            "profile_id": body.profile_id,
            "company_ref": body.company_ref,
            "offset": body.offset,
            **common,
        }
    return {
        "profile_id": body.profile_id,
        "sector_ref": body.sector_ref,
        "offset": body.offset,
        **common,
    }


def _v2_semantic_request(body: _V2Body) -> dict[str, Any]:
    """The validated semantic query echoed in the v2 response envelope —
    exactly the fields the entry resolved on, in a deterministic order."""
    if isinstance(body, _V2ThemeBody):
        return {
            "entry_kind": "theme",
            "anchor_theme_id": body.anchor_theme_id,
            "slice_key": body.slice_key,
            "view": body.view,
            "time_mode": body.time_mode,
            "source_cutoff": body.source_cutoff,
            "recorded_cutoff": body.recorded_cutoff,
            "offset": body.offset,
            "limit": body.limit,
        }
    if isinstance(body, _V2CompanyProfileBody):
        return {
            "entry_kind": "company_profile",
            "profile_id": body.profile_id,
            "company_ref": body.company_ref,
            "view": body.view,
            "time_mode": body.time_mode,
            "source_cutoff": body.source_cutoff,
            "recorded_cutoff": body.recorded_cutoff,
        }
    return {
        "entry_kind": "sector_profile",
        "profile_id": body.profile_id,
        "sector_ref": body.sector_ref,
        "view": body.view,
        "time_mode": body.time_mode,
        "source_cutoff": body.source_cutoff,
        "recorded_cutoff": body.recorded_cutoff,
    }


def _v2_entry_key(body: _V2Body) -> str:
    """anchor for ``theme``, profile id for the profile kinds (packet §3.5)."""
    return body.anchor_theme_id if isinstance(body, _V2ThemeBody) else body.profile_id


def _v2_native_generation(
    payload: Any, registration: VerticalRegistration, *, evidence: bool,
) -> str:
    """The composed payload's OWN native generation, read from the field the
    registration declares (``dossier_id`` for Technology, ``generation`` for
    the gen_-fingerprinted verticals; the evidence envelopes carry it under
    their contract's own ``generation`` key). A payload whose native
    generation is absent or off-grammar is a composer/registration mismatch —
    the fixed private 503, never a serve."""
    field = "generation" if evidence else registration.native_generation_field
    native = payload.get(field) if isinstance(payload, Mapping) else None
    if not _v2_native_generation_well_formed(native, registration):
        raise RegisteredContractMismatch(
            "composed payload does not carry the registered native generation",
        )
    return native


def _v2_context_generation(
    body: _V2Body,
    registration: VerticalRegistration,
    bundle: Any,
    snapshot: tuple[str, dict],
    *,
    native_generation: str,
) -> str:
    """The shell's own ``gen_`` continuation fingerprint over packet §3.5's
    field set. ``rights_revision`` is the revision the bundle was SERVED
    under — the loader stamps the enforced snapshot revision, and an injected
    bundle keeps its own — so the fingerprint binds what the owner actually
    served, not a second read."""
    rights_revision = getattr(bundle, "rights_revision", None)
    if not isinstance(rights_revision, str) or not rights_revision:
        rights_revision = snapshot[0]
    return context_generation(
        entry_kind=body.entry_kind,
        entry_key=_v2_entry_key(body),
        subject=str(getattr(body, registration.subject_field)),
        view=body.view,
        time_mode=body.time_mode,
        source_cutoff=body.source_cutoff,
        recorded_cutoff=body.recorded_cutoff,
        native_generation=native_generation,
        definition_version=registration.definition_version,
        rights_revision=rights_revision,
        revision_tuple=getattr(bundle, "revision_tuple", ()),
    )


def _v2_check_expectations(
    body: _V2Body, native_generation: str, context_gen: str,
) -> None:
    """The shell-level refresh gate. A mismatch on EITHER the native
    generation or the context fingerprint is the SAME 409
    ``refresh_required``/``reset_to_first_page`` envelope — without leaking
    WHICH expectation failed, let alone any source/rights detail. The
    vertical's own compose re-checks the native expectation through the
    query it was handed; this is the shell's backstop after composition."""
    if body.expected_generation is not None and body.expected_generation != native_generation:
        raise _private_error(
            409, {"error": {"code": "refresh_required", "action": "reset_to_first_page"}},
        )
    if body.expected_context_generation is not None \
            and body.expected_context_generation != context_gen:
        raise _private_error(
            409, {"error": {"code": "refresh_required", "action": "reset_to_first_page"}},
        )


def _call_v2_query(
    body: _V2Body, principal: Mapping[str, Any], registration: VerticalRegistration,
) -> JSONResponse:
    _check_v2_query_semantics(body, registration)
    query = registration.build_query(**_v2_query_kwargs(body, registration))
    snapshot = load_registry_snapshot()  # ONE rights read per request (T03 owner)
    bundle = load_authorized_owner_bundle(
        query, principal=principal, registration=registration, rights_snapshot=snapshot,
    )
    _refuse_unreadable_cutoff(body)  # AFTER the loader: the ORDER LAW above
    bundle, dropped = _filter_bundle_for_rights(bundle, snapshot=snapshot)
    payload = _require_registered_contract(
        registration.compose(query, bundle),
        registration.schema_id,
        registration.definition_version,
    )
    native = _v2_native_generation(payload, registration, evidence=False)
    context_gen = _v2_context_generation(
        body, registration, bundle, snapshot, native_generation=native,
    )
    _v2_check_expectations(body, native, context_gen)
    payload = _post_process_rights_limitation(payload, dropped)
    evidence_refs: Any = None
    if registration.evidence_refs_field is not None:
        evidence_refs = payload.get(registration.evidence_refs_field)
    envelope = {
        "schema": V2_RESPONSE_SCHEMA,
        "entry_kind": body.entry_kind,
        "request": _v2_semantic_request(body),
        "generation": native,
        "context_generation": context_gen,
        "data": payload,
        "evidence_refs": (
            list(evidence_refs) if isinstance(evidence_refs, (list, tuple)) else []
        ),
    }
    return _private_json(200, envelope)


def _call_v2_evidence(
    body: _V2Body, principal: Mapping[str, Any], registration: VerticalRegistration,
) -> JSONResponse:
    _check_v2_evidence_semantics(body, registration)
    query = registration.build_query(**_v2_query_kwargs(body, registration))
    snapshot = load_registry_snapshot()  # ONE rights read per request (T03 owner)
    bundle = load_authorized_owner_bundle(
        query, principal=principal, registration=registration, rights_snapshot=snapshot,
    )
    _refuse_unreadable_cutoff(body)  # AFTER the loader: the ORDER LAW above
    bundle, dropped = _filter_bundle_for_rights(bundle, snapshot=snapshot)
    payload = _require_registered_contract(
        registration.select_evidence(query, bundle, body.assertion_ref),
        registration.evidence_schema_id,
    )
    native = _v2_native_generation(payload, registration, evidence=True)
    context_gen = _v2_context_generation(
        body, registration, bundle, snapshot, native_generation=native,
    )
    _v2_check_expectations(body, native, context_gen)
    payload = _post_process_rights_limitation(payload, dropped)
    # The v2 evidence response is the vertical's OWN evidence envelope — the
    # shell wraps the QUERY response, never the evidence one (packet §3.5).
    return _private_json(200, payload)


def _invoke_v2(call, *args: Any) -> JSONResponse:
    """Run one v2 pipeline with the v1 error discipline plus the duck-typed
    vertical-refusal catch: the profile adapters refuse through their OWN
    ``ValueError`` subclasses carrying ``.code`` — the shell imports none of
    them and maps by the code's base token. An unrecognised ``ValueError``,
    a bundle that cannot serve, a contract mismatch, a rights-registry fault
    and any internal fault all land in the same fixed private 503; nothing
    internal ever crosses the wire."""
    try:
        return call(*args)
    except HTTPException:
        raise
    except ResearchRefusal as exc:
        raise _map_research_refusal(exc) from None
    except ValueError as exc:  # duck-typed vertical refusal (.code)
        mapped = _map_typed_vertical_refusal(exc)
        if mapped is not None:
            raise mapped from None
        raise _private_error(
            503, {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except (BundleUnavailable, RegisteredContractMismatch):
        raise _private_error(
            503, {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except RightsRefusal:
        # The rights registry itself is missing or corrupt: no verdict can be
        # asked, so nothing is emitted. Fail closed behind the same headers.
        raise _private_error(
            503, {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None
    except Exception:  # noqa: BLE001 — internal detail must never cross the wire
        raise _private_error(
            503, {"error": {"code": "service_unavailable", "action": "retry_later"}},
        ) from None


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

    v2 (lane 5): a body carrying ``request_schema`` selects the closed
    ``theme_research.request/v2`` union; a body WITHOUT the key keeps
    byte-compatible v1 parsing and the v1 response envelope. No other value
    of the discriminator is admitted (private 400 at parse).
    """
    _private(response)
    payload = await _read_json_object(request)
    if "request_schema" in payload:
        body = _parse_v2_body(_V2_QUERY_MODELS, payload)
        # Registration AFTER auth + parse, BEFORE any reader; its private
        # 404/400 must reach the wire as-is, so it resolves outside the
        # catch-all.
        registration = _resolve_v2_registration(body)
        return _invoke_v2(_call_v2_query, body, user, registration)
    body = _validate_body(_QueryBody, payload)
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
    """Paid read-only projection of ONE authorized assertion's evidence.

    v2 (lane 5): same discriminator law as the query route — a
    ``request_schema``-carrying body selects the v2 evidence union (the
    paired expectations REQUIRED), anything without the key keeps v1."""
    _private(response)
    payload = await _read_json_object(request)
    if "request_schema" in payload:
        body = _parse_v2_body(_V2_EVIDENCE_MODELS, payload)
        registration = _resolve_v2_registration(body)
        return _invoke_v2(_call_v2_evidence, body, user, registration)
    body = _validate_body(_EvidenceBody, payload)
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
