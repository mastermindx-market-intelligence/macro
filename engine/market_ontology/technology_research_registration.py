"""Technology company-first research registration adapter (T8A, fixture-only).

Technology's side of the shared research shell only. The foundation owner
(macro#7870, hook 1 integrated at e2f4d4909156: 231c9645dff3 + nits
4733b7fa84d5/31d776705b9e) owns ``theme_research_registry.VerticalRegistration``
and the ``OwnerBundle``/``ResearchQuery`` shapes; the company-first request
shape for Technology exists only as the PROPOSED §8 profile mapping
(research/theme_graph/CURATION_ASSERTION_V1_1_PROPOSAL_2026-09-24.md @
382c0b399d5c on #7870, under Sol adjudication). This module therefore:

* performs NO registration — it exports ``TECHNOLOGY_REGISTRATION_FACTS``, the
  exact §8 field set the foundation owner copies when §8 is adjudicated;
* binds ``compose``/``select_evidence`` to the sealed Technology composer
  (``technology_economic_change.compose_technology_economic_change``) so the
  shell's checks — ``payload["schema"] == registration.schema_id`` and
  ``payload["definition_version"] == registration.definition_version`` — hold
  by construction;
* documents the §8 dependency by execution: ``registration_entry_or_refusal``
  lazily imports the shell pair (``theme_research_registry.VerticalRegistration``
  and ``theme_research_binding.ResearchRefusal``) and, when both appear, holds
  a ``company_profile`` entry that has no theme anchor and no slices
  (``vertical_registration_held:company_profile``) BEFORE constructing
  ``VerticalRegistration``. A theme-registrable entry the shell refuses is
  reported as the shell's own exception type
  (``vertical_registration_refused:<ExcType>``). A constructor ``TypeError``
  on theme-registrable facts — signature drift — propagates uncaught. The
  real Technology facts are not theme-registrable, so they never reach
  construction. Nothing here pretends the discriminator is delivered.

Duck typing: the query and bundle are read only through ``getattr``/mapping
access on the fields §8 names, so the shell's frozen dataclasses and the
synthetic fixtures are accepted equally. Every shape this adapter EXPECTS from
the bundle beyond the OwnerBundle field set is a PLACEHOLDER pinned to the §8
adjudication and named in place: the ``as_known`` mapping on an identity
result, the ``theme_ref`` key inside an assertion's ``scope`` section
(or ``canonical_theme_id`` when ``theme_ref`` is absent; differing values
conflict), the
native-ref entry carrying the run context, and the ``omissions`` -> coverage
mapping. None is ever guessed past, defaulted or repaired.

Authority law: nothing this module returns may rank, gate, size, veto,
originate or open an entry — the six authority flags are literally false on
every emitted object, and no probability, confidence, consensus, beat/miss,
forecast distribution, price, valuation or trade language appears anywhere.

Sealed-translation rules (documented, tested, never silent):

* ``scope_mode`` — §8 requests are company-first (``entry_kind="company_profile"``);
  the sealed dossier contract's closed grammar admits exactly
  ``theme_first``/``company_first``, so the adapter passes ``company_first``.
* ``company_ref`` — passed verbatim when it already matches the sealed scope
  grammar (``co:<region>:<id>``). The §8 grammar families ``theme_graph_node``
  (with a ``#revision`` pin) and ``cik`` resolve through the bundle's own
  identity results, never through this adapter: for those requests the sealed
  scope carries the RESOLVED identity result's ``entity_id`` (which must itself
  match the sealed grammar), or the compose is refused
  (``sealed_input_unavailable:company_ref``). Tickers are never consulted.
* ``comparison`` — the one ``management_outlook_comparison.v1`` packet in the
  bundle's financial packets, verbatim. With no packet the adapter builds the
  typed refused comparison the composer itself accepts — ``result`` null,
  ineligible eligibility, EMPTY limitations — so the composer renders its own
  ``comparison_limitations_absent`` typed refusal; no figure, digest or
  admission is ever fabricated. Two packets refuse
  (``sealed_input_unavailable:comparison``): the bundle cannot supply THE one.
* ``input_vector`` — the vector BOUND to the comparison: the composer's own
  ``identity_receipts_digest`` over the same receipt sequence, the native
  context generation from the bundle, and the comparison's id. The composer
  recomputes and enforces every binding.
* ``coverage`` — from the bundle's ``omissions``: no omissions attested ->
  complete within the accepted scope; any omission -> not complete; population
  unknown (the bundle carries no population total); every count unknown rather
  than guessed; family labels are labels, never baskets (the only lawful value).
"""
from __future__ import annotations

import copy
import dataclasses
import importlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, NoReturn

from engine.market_ontology.technology_economic_change import (
    COMPARISON_KIND,
    COMPARISON_SCHEMA_ID,
    DEFINITION_VERSION,
    ENGINE_VERSION,
    SCHEMA_ID,
    compose_technology_economic_change,
    identity_receipts_digest,
)
# The composer's OWN closed six-field source projection, imported under alias
# so the v2 evidence selector recomputes the native tuple through the ONE
# grammar owner instead of forking it here. A private name by deliberate
# choice: re-implementing the projection in this adapter would be a second
# grammar that can drift from the rendered rows; the sealed composer module is
# already a hard import of this adapter, so this adds no new coupling.
from engine.market_ontology.technology_economic_change import (  # noqa: E501
    _assertion_source_ref as _native_assertion_source_ref,
)

__all__ = [
    "PROFILE_ID",
    "EVIDENCE_SCHEMA_ID",
    "EVIDENCE_SCHEMA_ID_V1",
    "DEFINITION_VERSION",
    "VIEWS",
    "TIME_MODES",
    "TechnologyRegistrationRefusal",
    "TechnologyResearchQuery",
    "TECHNOLOGY_REGISTRATION_FACTS",
    "VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE",
    "build_query",
    "compose",
    "select_evidence",
    "validate_evidence_envelope",
    "load_bundle",
    "registration_entry_or_refusal",
]

#: The §8 profile id and the dossier schema id are the same string; one alias,
#: so the shell's ``payload["schema"] == registration.schema_id`` check and the
#: profile routing can never drift apart.
PROFILE_ID = SCHEMA_ID

#: The assertion-grained evidence contract (lane 5, packet §3.5): selection
#: keys on the owner-minted ``gmi-curation://`` assertion ref AND the full
#: native source tuple including the selector, so two rendered assertions
#: from ONE document are independently selectable when their selectors or
#: curation revisions differ. The superseded document-grained v1 contract
#: stays on disk under its own name; nothing emits it anymore.
EVIDENCE_SCHEMA_ID = "technology_economic_change.evidence.v2"
EVIDENCE_SCHEMA_ID_V1 = "technology_economic_change.evidence.v1"

#: The evidence envelope's own contract, the mirror of the composer's
#: ``CONTRACT_PATH``: :func:`validate_evidence_envelope` reads this file so the
#: runtime check and the shipped contract can never drift apart.
EVIDENCE_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts/market_ontology/technology_economic_change.evidence.v2.schema.json"
)

#: The closed time-mode set this profile serves today. ``system_replay`` is
#: handled by its own typed refusal (``replay_identity_unavailable``) after
#: identity resolution; every other non-latest mode refuses ``not_available``.
#: Never silently serve a foreign mode as latest.
TIME_MODES: tuple[str, ...] = ("latest",)

#: Closed view tuple, derived by construction from THIS vertical's frozen
#: contract (contracts/market_ontology/technology_economic_change.v1.schema.json):
#: the five top-level required sections that carry member-facing display
#: content. Every other top-level section of that contract is identifier,
#: provenance or bounds plumbing (schema, definition_version, dossier_id, kind,
#: engine_version, authority, authority_ceiling, display_only, owner, mode,
#: freshness, scope, navigation, classification, selected,
#: source_version_vector, bounds) — not a selectable projection. Not copied
#: from any semiconductor view list: whatever the shared five turns out to be,
#: this tuple is what THIS contract's display sections are.
VIEWS: tuple[str, ...] = (
    "business",
    "comparison",
    "counter_observations",
    "identity",
    "coverage",
)

#: The §8 grammar FAMILY names for the request body (the executable check is
#: the closed grammar below; a ``co:`` node id is a theme_graph_node, a
#: ``cik:`` id is a cik).
COMPANY_REF_GRAMMAR: tuple[str, ...] = ("theme_graph_node", "cik")

_COMPANY_REF_REQUEST_RE = re.compile(r"^co:(?:us|cn|hk|ca|intl):[A-Za-z0-9.\-]+(?:#[0-9]+)?$")
_CIK_REF_REQUEST_RE = re.compile(r"^cik:[0-9]{10}$")
#: The sealed dossier scope's own company grammar (no revision pin, no cik form).
_SEALED_COMPANY_REF_RE = re.compile(r"^co:(?:us|cn|hk|ca|intl):[A-Za-z0-9.\-]+$")

#: comparison_id for the no-packet refused comparison: a self-describing
#: marker, never shaped like a real comparison id, so it can never be mistaken
#: for a sealed figure.
REFUSED_COMPARISON_ID = "no_sealed_comparison"

#: The six authority flags, literally false (ECD-48); the composer re-checks
#: every authority section it emits.
_FALSE_AUTHORITY: dict[str, bool] = {
    "rank": False, "gate": False, "size": False,
    "veto": False, "originate": False, "open_entry": False,
}

_COVERAGE_COUNT_KEYS: tuple[str, ...] = (
    "included", "missing", "stale", "rights_blocked", "unresolved",
)


class TechnologyRegistrationRefusal(ValueError):
    """Typed adapter refusal, mirroring the shell's ``ResearchRefusal``:
    ``str(exc)`` is exactly the snake_case code (``exc.code``)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _refuse(code: str) -> NoReturn:
    raise TechnologyRegistrationRefusal(code)


# --- the shared shell, imported lazily ------------------------------------------

_SHELL_REGISTRY_MODULE = "engine.market_ontology.theme_research_registry"
_SHELL_BINDING_MODULE = "engine.market_ontology.theme_research_binding"
#: Vertical query owner for ``OwnerBundle`` / ``ResearchQuery``. Not the shell.
_SHELL_SIBLING_MODULE = "engine.market_ontology.semiconductor_theme_research"
#: Registration "shell present" is this pair, never the semiconductor module.
SHARED_SHELL_MODULES: tuple[str, str] = (
    _SHELL_REGISTRY_MODULE,
    _SHELL_BINDING_MODULE,
)
#: Module names whose OWN absence is typed unavailable rather than raised.
#: A ``ModuleNotFoundError`` naming anything else is a missing dependency of a
#: present module and propagates (see :func:`_import_shell_module`).
_SHELL_MODULE_NAMES = frozenset({
    _SHELL_REGISTRY_MODULE,
    _SHELL_BINDING_MODULE,
    _SHELL_SIBLING_MODULE,
})


def _import_shell_module(name: str) -> Any:
    """Import one named module, treating ``ModuleNotFoundError`` as absence
    ONLY when the missing module IS ``name`` (``exc.name`` matches one of
    :data:`_SHELL_MODULE_NAMES`): a ``ModuleNotFoundError`` raised from INSIDE
    a present module — a missing third-party dependency — carries a different
    ``exc.name`` and propagates, so a broken module can never masquerade as
    ``shared_shell_unavailable``. A genuine non-module ``ImportError`` from a
    present-but-broken module propagates too."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name in _SHELL_MODULE_NAMES:
            return None
        raise


def _resolve_vertical_registration() -> Any:
    """Registration gate. Returns ``VerticalRegistration`` only when both
    modules in :data:`SHARED_SHELL_MODULES` import and expose their symbols:
    ``VerticalRegistration`` on the registry and ``ResearchRefusal`` on the
    binding. Either module or either symbol absent returns ``None`` (the
    caller raises ``shared_shell_unavailable``). The semiconductor module is
    not consulted here. The company_profile hold
    (``vertical_registration_held:company_profile``) runs only after this
    returns a class, and it runs before construction when the facts lack a
    string ``anchor_theme_id`` or have empty ``slice_keys``."""
    registry = _import_shell_module(SHARED_SHELL_MODULES[0])
    binding = _import_shell_module(SHARED_SHELL_MODULES[1])
    if registry is None or binding is None:
        return None
    vertical_registration = getattr(registry, "VerticalRegistration", None)
    research_refusal = getattr(binding, "ResearchRefusal", None)
    if vertical_registration is None or research_refusal is None:
        return None
    return vertical_registration


def _load_shared_shell() -> tuple[Any, Any, Any] | None:
    """Return ``(VerticalRegistration, OwnerBundle, ResearchQuery)``, or
    ``None`` when either module or any of the three symbols is absent.

    ``OwnerBundle`` and ``ResearchQuery`` come from
    ``engine.market_ontology.semiconductor_theme_research``, the vertical query owner,
    not the shell. The registration shell is
    :data:`SHARED_SHELL_MODULES`, resolved by
    :func:`_resolve_vertical_registration`. No production consumer exists —
    only the tests call this three-symbol shape. Absence means ONLY the
    named module names themselves (:func:`_import_shell_module`); a missing
    dependency of a present module and any other import failure propagate.
    Sibling-symbol drift here does not skip the company_profile hold: the
    registration path does not call this function."""
    registry = _import_shell_module(_SHELL_REGISTRY_MODULE)
    semiconductor = _import_shell_module(_SHELL_SIBLING_MODULE)
    if registry is None or semiconductor is None:
        return None
    vertical_registration = getattr(registry, "VerticalRegistration", None)
    owner_bundle = getattr(semiconductor, "OwnerBundle", None)
    research_query = getattr(semiconductor, "ResearchQuery", None)
    if vertical_registration is None or owner_bundle is None or research_query is None:
        return None
    return vertical_registration, owner_bundle, research_query


# --- request validation (shared by compose and select_evidence) ------------------


def _identity_results(bundle: Any) -> list[Any]:
    results = getattr(bundle, "identity_results", None)
    return list(results) if results is not None else []


def _resolve_company_ref(company_ref: str, identity_results: list[Any]) -> Mapping | None:
    """Resolution is the bundle's, never this adapter's: the request ref must
    be carried VERBATIM by an identity result — its ``entity_id`` or
    ``node_id`` for a ``co:`` request, its ``cik`` field for a ``cik:`` request
    (field names pinned to the §8 bundle contract). Ticker strings are never
    consulted and no name-similarity join is ever attempted. More than one
    matching identity row, duplicates included, is ``company_ref_ambiguous``:
    the adapter never picks one."""
    if company_ref.startswith("cik:"):
        matches = [
            entry for entry in identity_results
            if isinstance(entry, Mapping) and entry.get("cik") == company_ref
        ]
    else:
        matches = [
            entry for entry in identity_results
            if isinstance(entry, Mapping)
            and (entry.get("entity_id") == company_ref or entry.get("node_id") == company_ref)
        ]
    if len(matches) > 1:
        _refuse("company_ref_ambiguous")
    return matches[0] if matches else None


def _validate_query_and_resolve(query: Any, bundle: Any) -> str:
    """Run the closed §8 request checks in order and return the SEALED
    ``company_ref`` for the dossier scope. Raises
    :class:`TechnologyRegistrationRefusal` on the first violation."""
    if getattr(query, "profile_id", None) != PROFILE_ID:
        _refuse("profile_mismatch")
    if getattr(query, "slice_key", None) not in (None, ""):
        _refuse("slice_key_forbidden")
    if getattr(query, "view", None) not in VIEWS:
        _refuse("view_not_registered")
    identity_results = _identity_results(bundle)
    if getattr(query, "offset", 0) not in (0, None):
        _refuse("pagination_unsupported")
    if getattr(query, "cursor", None) is not None:
        # cursor is as much a paging attempt as offset; the sealed scope is
        # composed cursor-less and the dossier declares pagination_supported
        # false, so a cursor-carrying request must refuse, never silently
        # answer page 1.
        _refuse("pagination_unsupported")
    company_ref = getattr(query, "company_ref", None)
    if not company_ref:
        _refuse("company_ref_required")
    if not isinstance(company_ref, str) or not (
        _COMPANY_REF_REQUEST_RE.match(company_ref)
        or _CIK_REF_REQUEST_RE.match(company_ref)
    ):
        _refuse("company_ref_grammar")
    matched = _resolve_company_ref(company_ref, identity_results)
    if matched is None:
        _refuse("company_ref_unresolved")
    if getattr(query, "time_mode", None) == "system_replay":
        # PLACEHOLDER pinned to the reader owner's future contract: the RESOLVED
        # identity result is "as known at replay time" iff it carries a truthy
        # ``as_known`` mapping. Another row's mapping says nothing about this
        # company. Absent means absent — never guessed past.
        as_known = matched.get("as_known")
        if not (isinstance(as_known, Mapping) and as_known):
            _refuse("replay_identity_unavailable")
    elif getattr(query, "time_mode", "latest") != "latest":
        # :data:`TIME_MODES` is closed: ``latest`` is the only mode this
        # profile serves today. A foreign mode — ``source_history`` included —
        # refuses ``not_available``; it is never silently served as latest.
        _refuse("not_available")
    if _SEALED_COMPANY_REF_RE.match(company_ref):
        return company_ref
    # cik: / revision-pinned requests: the sealed scope carries the RESOLVED
    # identity result's own native entity id — the bundle's resolution, not ours.
    entity_id = matched.get("entity_id")
    if isinstance(entity_id, str) and _SEALED_COMPANY_REF_RE.match(entity_id):
        return entity_id
    _refuse("sealed_input_unavailable:company_ref")


# --- bundle -> sealed input mapping ----------------------------------------------


def _theme_ref_from_assertions(assertions: list[Any]) -> str | None:
    """The ONE accepted theme id carried by the bundle's assertions' scope
    sections. ``theme_ref`` or, when that key is absent, ``canonical_theme_id``.
    Zero ids, a within-scope disagreement, or two different ids are all
    "no accepted theme id" — never a pick by tuple order."""
    theme_ids: set[str] = set()
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            continue
        scope = assertion.get("scope")
        if not isinstance(scope, Mapping):
            continue
        theme_ref = scope.get("theme_ref")
        canonical = scope.get("canonical_theme_id")
        theme_ok = isinstance(theme_ref, str) and bool(theme_ref)
        canonical_ok = isinstance(canonical, str) and bool(canonical)
        if theme_ok and canonical_ok and theme_ref != canonical:
            return None
        chosen = theme_ref if theme_ok else canonical if canonical_ok else None
        if isinstance(chosen, str) and chosen:
            theme_ids.add(chosen)
    if len(theme_ids) != 1:
        return None
    return next(iter(theme_ids))


def _native_context_from_bundle(bundle: Any) -> Mapping | None:
    """The run-context native ref (PLACEHOLDER shape: the native_refs entry
    carrying the full NativeContext field set — mode/as_of/cutoff/generation/
    owner_program). The composer validates every value; nothing is defaulted.
    More than one full-field-set ref is a CONFLICT — the refs could carry
    different ``generation`` values and therefore different dossier ids — and
    refuses, exactly as a conflicting comparison packet or theme_ref does;
    tuple order never picks the winner."""
    native_refs = getattr(bundle, "native_refs", None) or ()
    required = {"mode", "as_of", "cutoff", "generation", "owner_program"}
    matches = [
        ref for ref in native_refs
        if isinstance(ref, Mapping) and required <= set(ref)
    ]
    if len(matches) > 1:
        _refuse("sealed_input_unavailable:native_context")
    if len(matches) == 1:
        return matches[0]
    return None


def _refused_comparison_packet() -> dict[str, Any]:
    """The typed refused comparison the composer itself accepts and renders as
    a refusal section: result null, ineligible eligibility with a plain
    explanation, EMPTY limitations (so the composer emits its own
    ``comparison_limitations_absent`` typed refusal). No figure, digest or
    admission is fabricated by this adapter."""
    return {
        "schema": COMPARISON_SCHEMA_ID,
        "comparison_id": REFUSED_COMPARISON_ID,
        "kind": COMPARISON_KIND,
        "subject": {"entity_id": None, "product_id": None},
        "fiscal_partition": {},
        "input_roles": {},
        "input_vector": {},
        "eligibility": {
            "eligible": False,
            "explanation": (
                "no sealed management_outlook_comparison.v1 packet is present in "
                "the owner bundle, so the comparison section is refused"
            ),
        },
        "result": None,
        "limitations": [],
        "correction": None,
        "authority": dict(_FALSE_AUTHORITY),
    }


def _comparison_from_bundle(bundle: Any) -> Mapping[str, Any]:
    packets = getattr(bundle, "financial_packets", None) or ()
    matches = [
        packet for packet in packets
        if isinstance(packet, Mapping) and packet.get("schema") == COMPARISON_SCHEMA_ID
    ]
    if len(matches) > 1:
        _refuse("sealed_input_unavailable:comparison")
    if len(matches) == 1:
        return matches[0]
    return _refused_comparison_packet()


def _coverage_from_omissions(bundle: Any) -> dict[str, Any] | None:
    """Coverage from the bundle's omissions (PLACEHOLDER mapping, pinned to the
    §8 bundle contract): no omissions -> complete within the accepted scope;
    any omission -> not complete; population unknown; counts unknown; family
    labels never baskets (the only lawful value)."""
    omissions = getattr(bundle, "omissions", None)
    if omissions is None:
        return None
    return {
        "population_mode": "unknown_scope",
        "known_population_total": None,
        "counts": {key: None for key in _COVERAGE_COUNT_KEYS},
        "complete_attested": len(omissions) == 0,
        "family_labels_treated_as_baskets": False,
    }


def _input_vector_bound_to(
    comparison: Mapping[str, Any], native_context: Mapping[str, Any], receipts: list[Any]
) -> dict[str, Any]:
    """The sealed input vector BOUND to the comparison: the composer's own
    digest over the same receipt sequence, the native context generation, and
    the comparison's id. The composer recomputes and enforces every binding;
    this adapter invents no generation and no digest."""
    return {
        "engine_version": ENGINE_VERSION,
        "native_context_generation": native_context["generation"],
        "identity_receipts_digest": identity_receipts_digest(receipts),
        "comparison_id": comparison["comparison_id"],
    }


# --- the shell callables ----------------------------------------------------------


def compose(query: Any, bundle: Any) -> dict[str, Any]:
    """Map one §8 company-first request + owner bundle onto the sealed
    Technology composer and return its dossier unchanged.

    ``query.view`` is VALIDATION-ONLY here: it must name a registered view, but
    the composed payload is view-invariant — every registered view of the same
    request + bundle composes the byte-identical dossier. Projection is the
    shared shell's responsibility pending the §8 adjudication, so the day the
    payload must stop being view-invariant is a §8 event, pinned loudly by
    test, not a silent drift.

    The returned payload carries ``schema == PROFILE_ID`` and
    ``definition_version == DEFINITION_VERSION`` (emitted by the composer), so
    the shell's exact identity checks hold. Refusals at the request boundary
    raise :class:`TechnologyRegistrationRefusal`; refusals the SEALED contract
    itself raises (its own ``ValueError`` subclass, snake_case code first —
    bounds, shapes, bindings) propagate as-is: this adapter never repairs,
    truncates or retries a sealed refusal."""
    scope_company_ref = _validate_query_and_resolve(query, bundle)
    assertions = list(getattr(bundle, "assertions", None) or ())
    theme_ref = _theme_ref_from_assertions(assertions)
    if theme_ref is None:
        _refuse("theme_ref_unavailable")
    native_context = _native_context_from_bundle(bundle)
    if native_context is None:
        _refuse("sealed_input_unavailable:native_context")
    receipts = _identity_results(bundle)
    comparison = _comparison_from_bundle(bundle)
    coverage = _coverage_from_omissions(bundle)
    if coverage is None:
        _refuse("sealed_input_unavailable:coverage")
    payload = compose_technology_economic_change(
        scope={
            "scope_mode": "company_first",
            "theme_ref": theme_ref,
            "company_ref": scope_company_ref,
            "offset": None,
            "cursor": None,
        },
        business_assertions=assertions,
        comparison=comparison,
        native_context=native_context,
        identity_receipts=receipts,
        input_vector=_input_vector_bound_to(comparison, native_context, receipts),
        coverage=coverage,
    )
    expected_generation = getattr(query, "expected_generation", None)
    if expected_generation is not None and expected_generation != payload["dossier_id"]:
        # Continuation contract (lane 5): the caller's NATIVE expectation is
        # compared against the composed dossier's own generation — the shell
        # re-checks after composition; this is the owner-side half, so a
        # stale expectation refreshes (``generation_changed``) instead of
        # being silently answered from a different dossier. The dossier id is
        # NOT renamed to ``gen_``: the native generation keeps the sealed
        # composer's own ``tecd_`` grammar.
        _refuse("generation_changed")
    return payload


def _rendered_source_evidence(payload: Mapping[str, Any]) -> list[tuple[str | None, dict[str, Any]]]:
    """``(curation_revision, source_ref)`` for every rendered row/card/counter
    citation of THIS composed dossier. Rows carry their producing
    assertion's own ``curation_revision`` — the dossier's exact attribution;
    cards and counter observations publish the closed tuple only (their
    producing rows' revisions are already carried by those rows). A refused
    business section renders nothing, so it cites nothing. Ref-grained, not
    document-grained: two rendered rows from ONE document appear as two
    DISTINCT refs whenever their selectors differ, which is what makes an
    assertion from a shared document independently selectable under
    evidence.v2."""
    rendered: list[tuple[str | None, dict[str, Any]]] = []

    def _add(ref: Any, revision: Any = None) -> None:
        if isinstance(ref, Mapping):
            rendered.append((
                revision if isinstance(revision, str) else None,
                dict(ref),
            ))

    business = payload.get("business")
    if isinstance(business, Mapping) and business.get("refused") is not True:
        for row in business.get("rows") or ():
            if isinstance(row, Mapping):
                _add(row.get("source_ref"), row.get("curation_revision"))
        for card in business.get("cards") or ():
            if isinstance(card, Mapping):
                for ref in card.get("source_refs") or ():
                    _add(ref)
    for observation in payload.get("counter_observations") or ():
        if isinstance(observation, Mapping):
            _add(observation.get("source_ref"))
    return rendered


def _curation_ref_text(assertion: Mapping[str, Any]) -> str | None:
    """The owner-minted ``gmi-curation://`` ref text for one bundle
    assertion — the same text ``theme_graph.curation_assertion.source_ref_for``
    emits for a payload that validates, read from the row's own
    ``scope.canonical_theme_id`` and ``curation_revision``. The mint is the
    shell binding's own text builder (ONE grammar owner, imported lazily so
    this adapter keeps working when the shared shell is absent); by the time
    selection consults it, :func:`compose` has already validated every
    rendered assertion through the composer's installed contract, so the text
    here IS the owner's ref, not a re-implementation. A payload whose fields
    are absent mints no usable ref — a ``None``-scoped or revision-less text
    never equals a shell-validated request ref, so it matches nothing."""
    binding = _import_shell_module(_SHELL_BINDING_MODULE)
    if binding is None:
        return None
    mint = getattr(binding, "curation_source_ref", None)
    if mint is None:
        return None
    ref = mint(assertion)
    return ref if isinstance(ref, str) and ref else None


def _dossier_limitation_texts(payload: Mapping[str, Any]) -> set[str]:
    """The dossier's own limitation texts (the comparison primary limitation —
    the only limitation string the first-unit contract carries; per-ref
    limitation strings do not exist, so the list may be empty)."""
    texts: set[str] = set()
    comparison = payload.get("comparison")
    if isinstance(comparison, Mapping) and comparison.get("refused") is not True:
        primary = comparison.get("primary_limitation")
        if isinstance(primary, Mapping) and isinstance(primary.get("text"), str) and primary["text"]:
            texts.add(primary["text"])
    return texts


_EVIDENCE_VALIDATOR: Any = None


def _evidence_validator() -> Any:
    global _EVIDENCE_VALIDATOR
    if _EVIDENCE_VALIDATOR is None:
        import jsonschema  # lazy: the contract check is a select_evidence-time concern only

        try:
            schema = json.loads(EVIDENCE_CONTRACT_PATH.read_text(encoding="utf-8"))
        except OSError as exc:
            # typed, content-free: any unreadable contract file (absent,
            # permission-denied, a directory, ...) surfacing raw out of this
            # lazy loader would be a failure mode of THIS module's refusal
            # vocabulary, so every OSError is typed here
            raise TechnologyRegistrationRefusal("evidence_contract_unavailable") from exc
        except UnicodeDecodeError as exc:
            # bytes that are not valid UTF-8: still "cannot be read as a
            # contract", typed corrupt (UnicodeDecodeError is a ValueError,
            # NOT an OSError, so the catch above provably does not cover it)
            raise TechnologyRegistrationRefusal("evidence_contract_corrupt") from exc
        except json.JSONDecodeError as exc:
            raise TechnologyRegistrationRefusal("evidence_contract_corrupt") from exc
        _EVIDENCE_VALIDATOR = jsonschema.Draft202012Validator(schema)
    return _EVIDENCE_VALIDATOR


def validate_evidence_envelope(payload: Mapping[str, Any]) -> None:
    """Validate an evidence envelope against
    ``contracts/market_ontology/technology_economic_change.evidence.v2.schema.json``,
    the mirror of the composer's ``validate_dossier``.

    Raises :class:`TechnologyRegistrationRefusal` (code
    ``evidence_schema_violation: <path>``) naming the first violating PATH
    only — never the validator's message, which renders the offending
    instance and would embed assertion content inside a typed refusal code.
    Every failure mode of the check itself is likewise typed and content-free:
    a contract file that cannot be READ — any ``OSError`` (absent,
    permission-denied, a directory) — refuses ``evidence_contract_unavailable``,
    and a file that cannot be DECODED — invalid UTF-8 bytes or bytes that are
    not JSON — refuses ``evidence_contract_corrupt``; an absent jsonschema
    refuses ``contract_validator_unavailable: …``. Pure; reads the contract
    file only.
    """
    try:
        errors = sorted(
            _evidence_validator().iter_errors(payload),
            key=lambda err: [str(p) for p in err.absolute_path],
        )
    except ImportError as exc:  # pragma: no cover - venv always carries jsonschema
        raise TechnologyRegistrationRefusal(
            "contract_validator_unavailable: jsonschema is required to validate an evidence envelope"
        ) from exc
    if errors:
        first = errors[0]
        path = "/".join(str(p) for p in first.absolute_path) or "<root>"
        _refuse(f"evidence_schema_violation: {path}")


def select_evidence(query: Any, bundle: Any, assertion_ref: Any) -> dict[str, Any]:
    """Return the closed v2 evidence envelope for ONE authorized assertion.

    Selection is ASSERTION-grained (``technology_economic_change.evidence.v2``,
    lane 5): the request ref must equal the owner-minted ``gmi-curation://``
    curation ref (:func:`_curation_ref_text`) of EXACTLY ONE bundle assertion,
    AND that assertion's own closed six-field native source tuple — owner,
    object_id, schema, generation, sha256, selector, the SELECTOR included —
    must be cited by a rendered row/card/counter of THAT composed dossier,
    AND a rendered item citing that tuple must carry the assertion's own
    ``curation_revision`` (rows do) — the dossier's exact attribution. The
    tuple is recomputed through the composer's own projection
    (``_assertion_source_ref``) and compared by exact equality against the
    rendered refs, never guessed from a document id and never fallen back to
    the first matching row. Two assertions from ONE document (same object_id,
    different ``selector`` or curation revision) are therefore INDEPENDENTLY
    selectable when each actually produced a rendered item; a duplicate-span
    sibling (same document AND same selector) that did not render cannot
    borrow the rendered row — exactly-one authorized assertion cannot be
    established, so the private unavailable outcome stands. Unknown,
    not-cited, unattributed and ambiguous refs share the ONE code
    ``not_available`` — no existence disclosure. Never fetches, never
    dereferences a locator, never widens beyond the bundle.

    The envelope carries the assertion ref verbatim and the FULL native source
    tuple under ``source``, so a consumer can re-derive exactly which sealed
    row the assertion produced. The document-grained v1 selector (keyed on
    ``source.object_id`` alone) is superseded by this grain; its contract
    stays on disk under the v1 name and nothing emits it anymore.

    The assertion is deep-copied VERBATIM, its assertion-internal ``authority``
    block included, unchanged. Nothing here pops, filters or normalises any
    part of it: the assertion's internal shape — authority vocabulary included —
    is owned and validated by ``theme_graph.curation_assertion.v1``, whose
    ``authority_not_all_false`` code rule runs on every render, BEFORE anything
    can be cited, and refuses any assertion whose authority flags are not all
    literally false. The evidence contract deliberately asserts nothing about
    the assertion's internals; restating them here would fork the owner's
    contract with a stale-by-design clock.

    ``query.view`` is VALIDATION-ONLY here, exactly as in :func:`compose`: the
    envelope is selected from the same view-invariant dossier, and projection
    stays the shared shell's responsibility pending §8.

    The envelope is validated against the evidence contract immediately before
    it is returned (:func:`validate_evidence_envelope`), so no envelope that
    violates its own contract can ever leave this function."""
    payload = compose(query, bundle)
    matches = [
        assertion for assertion in getattr(bundle, "assertions", None) or ()
        if isinstance(assertion, Mapping)
        and _curation_ref_text(assertion) == assertion_ref
    ]
    if len(matches) != 1:
        _refuse("not_available")
    chosen = matches[0]
    schema_id = chosen.get("schema")
    native = _native_assertion_source_ref(
        chosen.get("source"),
        schema_id=schema_id if isinstance(schema_id, str) else None,
    )
    rendered = _rendered_source_evidence(payload)
    if native is None or not any(ref == native for _, ref in rendered):
        _refuse("not_available")
    chosen_revision = chosen.get("curation_revision")
    if not any(
        revision == chosen_revision and ref == native
        for revision, ref in rendered
    ):
        # The span rendered, but NO rendered item carries THIS assertion's
        # curation revision: a duplicate-span sibling (same document AND
        # same selector) produced the row, so exactly-one authorized
        # assertion cannot be established — the private unavailable
        # outcome, never a pick between indistinguishable twins.
        _refuse("not_available")
    envelope = {
        "schema": EVIDENCE_SCHEMA_ID,
        "definition_version": DEFINITION_VERSION,
        "generation": payload["dossier_id"],
        "assertion_ref": assertion_ref,
        "source": dict(native),
        "assertion": copy.deepcopy(dict(chosen)),
        "limitations": sorted(_dossier_limitation_texts(payload)),
        "authority": dict(_FALSE_AUTHORITY),
    }
    validate_evidence_envelope(envelope)
    return envelope


# --- the shell's query carrier and the registered loader (lane 5) -----------------


@dataclasses.dataclass(frozen=True, slots=True)
class TechnologyResearchQuery:
    """The frozen request carrier the shared shell builds for the
    ``company_profile`` entry kind: the §8 company-first request body with
    the cutoffs and the native continuation expectation.

    ``profile_id`` + ``company_ref`` + ``view`` + ``time_mode``; no anchor, no
    slice (``slice_key`` stays ``None``); single-document — ``offset``/``cursor``
    exist so a paging attempt is a typed refusal, never a silent page 1.
    ``expected_generation`` is the caller's NATIVE expectation (the sealed
    dossier id, ``tecd_`` grammar); the SHELL-level context expectation never
    reaches the vertical."""

    profile_id: str
    company_ref: str | None
    view: str
    time_mode: str = "latest"
    slice_key: str | None = None
    source_cutoff: str | None = None
    recorded_cutoff: str | None = None
    offset: int = 0
    cursor: str | None = None
    expected_generation: str | None = None


#: Exactly the frozen carrier's field set — the closed contract between the
#: shell's parsed body and this vertical's callables.
_QUERY_FIELDS: frozenset[str] = frozenset({
    "profile_id", "company_ref", "view", "time_mode", "slice_key",
    "source_cutoff", "recorded_cutoff", "offset", "cursor",
    "expected_generation",
})


def build_query(**fields: Any) -> TechnologyResearchQuery:
    """Construct :class:`TechnologyResearchQuery` from EXACTLY its frozen
    field set — the registry-facing query constructor the shared shell calls.
    An unknown key raises ``TypeError`` (shell-contract drift must be loud,
    never silently dropped), and a missing required key raises the
    dataclass's own ``TypeError``."""
    unknown = set(fields) - _QUERY_FIELDS
    if unknown:
        raise TypeError(
            "technology build_query: unknown query fields: " + ", ".join(sorted(unknown))
        )
    return TechnologyResearchQuery(**fields)


#: The §8 bundle's private half (assertions, identity results, native run
#: context, comparison packets) is unbound — private binding is the open
#: R4/R5 ruling, exactly as it is for the semiconductor and Robotics
#: verticals.
PRIVATE_ASSERTIONS_UNBOUND = "private_assertions_unbound"

#: No declared owner surface produces the §8 company-first bundle today (no
#: technology cohort owns ``event_workspaces`` either). Declaring one is a
#: Theme Graph / Data OS owner's ruling, not this adapter's. Both tokens are
#: bundle diagnostics for tests and operators — NOT a wire vocabulary; no
#: consumer may branch on them.
PUBLIC_COHORT_UNOWNED = "public_cohort_unowned"


def _rights_revision(rights_snapshot: object, bundle_unavailable: Any) -> str:
    """The enforced rights revision for this request — the ONE rights
    registry read the shell performs per request and also enforces with, so
    the fingerprinted revision equals the enforced one. A direct caller may
    omit it and this reads the snapshot itself; a snapshot that carries no
    revision is the one genuine "cannot serve" (``bundle_unavailable`` — the
    shell's :class:`BundleUnavailable`, passed in by the already-resolved
    caller), because ``rights_revision`` feeds the context generation and
    serving without it would fingerprint a response against nothing."""
    snapshot: object = rights_snapshot
    if snapshot is None:
        try:
            from engine.theme_graph.rights import (  # noqa: PLC0415 — lazy by design
                load_registry_snapshot,
            )
        except ImportError as exc:  # pragma: no cover - carrier base fallback
            raise bundle_unavailable(
                "rights registry snapshot reader unavailable on this base"
            ) from exc
    if not (isinstance(snapshot, tuple) and len(snapshot) == 2
            and isinstance(snapshot[0], str) and snapshot[0]):
        raise bundle_unavailable("rights snapshot carries no revision")
    return snapshot[0]


def load_bundle(query: Any, *, rights_snapshot: Any = None) -> Any:
    """Technology's registered owner-bundle loader: the REAL shell callable,
    serving exactly what exists and declaring what does not — on the bundle,
    in the Robotics loader's own honest-empty shape (a registered loader that
    reads the enforced rights revision, resolves no unowned cohort, invents
    no store, and never raises for coverage absence).

    What exists today: the rights snapshot (the one real read). What does
    NOT: every §8 bundle half — no admitted owner surface binds curated
    assertions to a company request, no declared technology cohort owns the
    public workspaces, and ``identity_results``/``native_refs``/
    ``financial_packets`` have no producer. The loader therefore reads
    NOTHING from ``query`` (not a company ref, path, URL, locator, ticker or
    CIK) and returns the honest empty bundle; the two omission tokens name
    WHICH half is absent for the bundle's own readers.

    The honest consequence through the REAL composer: a company request
    resolves no identity row, so :func:`compose` refuses before any dossier
    is minted — the profile is UNAVAILABLE end-to-end today, stated by the
    vertical's own typed refusal, never papered over with a synthetic
    narrative. Binding a real surface (the census' named producer, when one
    is admitted) replaces the empty halves here and ONLY here."""
    binding = _import_shell_module(_SHELL_BINDING_MODULE)
    owner_bundle = getattr(binding, "OwnerBundle", None) if binding else None
    bundle_unavailable = getattr(binding, "BundleUnavailable", None) if binding else None
    if owner_bundle is None or bundle_unavailable is None:
        # The registered loader is a SHELL callable: its carrier types are
        # the shell binding's, resolved lazily with the adapter's usual
        # absent-shell refusal — typed, not crashed.
        _refuse("shared_shell_unavailable")
    return owner_bundle(
        revision_tuple=(),
        rights_revision=_rights_revision(rights_snapshot, bundle_unavailable),
        assertions=(),
        identity_results=(),
        event_workspaces=(),
        financial_packets=(),
        interpretation_blocks=(),
        native_refs=(),
        omissions=(PRIVATE_ASSERTIONS_UNBOUND, PUBLIC_COHORT_UNOWNED),
    )


# --- the §8 facts (what the foundation owner copies on adjudication) --------------


@dataclasses.dataclass(frozen=True, slots=True)
class TechnologyRegistrationFacts:
    """The PROPOSED §8 field set for the Technology company-first profile —
    exactly the fields §8 names, plus the two shell callables. ``anchor_theme_id``
    is ``None`` and ``slice_keys`` is empty BY PROPOSAL: the theme-keyed shell
    requires a string anchor and a non-empty slice tuple, so
    :func:`registration_entry_or_refusal` holds ``company_profile`` before
    construction and nothing is registered on this branch. ``views`` is the closed view
    tuple the request gate validates against; ``view`` is VALIDATION-ONLY on
    this carrier — both callables compose a view-invariant payload, and
    projection is the shared shell's responsibility pending the §8
    adjudication."""

    entry_kind: str
    profile_id: str
    anchor_theme_id: str | None
    slice_keys: tuple[str, ...]
    views: tuple[str, ...]
    company_ref_grammar: tuple[str, ...]
    schema_id: str
    evidence_schema_id: str
    definition_version: str
    title_en: str
    title_zh: str
    note_en: str
    note_zh: str
    compose: Callable[..., Mapping]
    select_evidence: Callable[..., Mapping]


TECHNOLOGY_REGISTRATION_FACTS = TechnologyRegistrationFacts(
    entry_kind="company_profile",
    profile_id=PROFILE_ID,
    anchor_theme_id=None,
    slice_keys=(),
    views=VIEWS,
    company_ref_grammar=COMPANY_REF_GRAMMAR,
    schema_id=PROFILE_ID,
    evidence_schema_id=EVIDENCE_SCHEMA_ID,
    # imported from the composer so the facts can never drift from the version
    # the dossier actually emits (the shell compares the two for identity).
    definition_version=DEFINITION_VERSION,
    title_en="Technology economic-change research",
    title_zh="科技产业经济变化研究",
    note_en="Paid research context for members. Nothing here ranks, gates, sizes or times anything.",
    note_zh="会员研究内容。此处内容不构成排序、准入、仓位或时机判断。",
    compose=compose,
    select_evidence=select_evidence,
)

#: The VerticalRegistration field names, in the shell's own order (hook 1 @
#: e2f4d4909156): the §8 facts carry a SUPERSET (entry_kind, profile_id, views,
#: company_ref_grammar), so the registration is built from exactly these.
_VERTICAL_REGISTRATION_FIELDS: tuple[str, ...] = (
    "anchor_theme_id", "slice_keys", "schema_id", "evidence_schema_id",
    "definition_version", "compose", "select_evidence",
    "title_en", "title_zh", "note_en", "note_zh",
)

#: Typed HOLD code this adapter implements. The shell keys every registration
#: on a canonical ``anchor_theme_id`` plus a non-empty ``slice_keys`` tuple.
#: Technology's facts are a ``company_profile`` with neither, so
#: :func:`registration_entry_or_refusal` raises
#: ``vertical_registration_held:company_profile`` BEFORE constructing
#: ``VerticalRegistration``. The hold names that entry_kind gap rather than
#: whatever structural gap the constructor would report. Retired only by a
#: company_profile migration that supplies accepted anchor and slice semantics.
VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE: str = (
    "vertical_registration_held:company_profile"
)


def _facts_are_theme_registrable(facts: TechnologyRegistrationFacts) -> bool:
    """True only when the facts carry what the theme-keyed shell requires:
    a string ``anchor_theme_id`` and a non-empty ``slice_keys`` tuple. The
    shell's own grammar guards still run on construction; this only decides
    whether construction is attempted at all."""
    return isinstance(facts.anchor_theme_id, str) and bool(facts.slice_keys)


def registration_entry_or_refusal(
    facts: TechnologyRegistrationFacts = TECHNOLOGY_REGISTRATION_FACTS,
) -> Any:
    """Return the entry the shared shell expects. Refusals (all adapter
    codes — neither the shell's refusal nor a bare ``ValueError`` leak
    through), in precedence order:

    * ``shared_shell_unavailable`` — ``VerticalRegistration`` and
      ``ResearchRefusal`` are not both importable
      (:data:`SHARED_SHELL_MODULES`). The semiconductor module is not this
      check.
    * ``vertical_registration_held:company_profile`` — both symbols import
      but ``facts`` carry no theme anchor / slices (the §8 ``company_profile``
      entry_kind is pending). Raised before any construction, so the hold
      is independent of the shell's field count.
    * ``vertical_registration_refused:<ExcType>`` — the shell is present,
      the facts are theme-registrable, and construction raised a
      non-``TypeError`` exception.
    * ``TypeError`` — propagated uncaught when theme-registrable facts reach
      a shell whose signature the adapter does not satisfy, so the carrier
      sees the structural gap. The real Technology facts never reach this
      branch (they are held first). The adapter never silently coerces.

    ``facts`` defaults to :data:`TECHNOLOGY_REGISTRATION_FACTS`; tests inject
    a theme-registrable double to exercise the construction branches.

    The gate is :func:`_resolve_vertical_registration`: both shell symbols
    must import. The vertical query owner's ``OwnerBundle``/``ResearchQuery``
    symbols are not this check, so drift there must not be typed
    ``shared_shell_unavailable``.
    """
    vertical_registration = _resolve_vertical_registration()
    if vertical_registration is None:
        _refuse("shared_shell_unavailable")
    if not _facts_are_theme_registrable(facts):
        _refuse(VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE)
    kwargs = {
        name: getattr(facts, name)
        for name in _VERTICAL_REGISTRATION_FIELDS
    }
    try:
        return vertical_registration(**kwargs)
    except TypeError:
        # Signature drift on theme-registrable facts: never relabelled,
        # never swallowed — the pin must hear it. The real company_profile
        # facts are held above and never reach this branch.
        raise
    except Exception as exc:
        _refuse("vertical_registration_refused:" + type(exc).__name__)
