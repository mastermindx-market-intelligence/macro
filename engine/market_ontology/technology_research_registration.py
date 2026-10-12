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
  lazily imports the shell and, when it appears, attempts the construction
  FIRST and unconditionally; a shell refusal is reported as the shell's own
  exception type (``vertical_registration_refused:<ExcType>``) and a
  constructor ``TypeError`` — §8 signature drift — propagates uncaught, so the
  pinned round-trip test errors loudly instead of xfailing stale. Nothing here
  pretends the discriminator is delivered.

Duck typing: the query and bundle are read only through ``getattr``/mapping
access on the fields §8 names, so the shell's frozen dataclasses and the
synthetic fixtures are accepted equally. Every shape this adapter EXPECTS from
the bundle beyond the OwnerBundle field set is a PLACEHOLDER pinned to the §8
adjudication and named in place: the ``as_known`` mapping on an identity
result, the ``theme_ref`` key inside an assertion's ``scope`` section, the
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

__all__ = [
    "PROFILE_ID",
    "EVIDENCE_SCHEMA_ID",
    "DEFINITION_VERSION",
    "VIEWS",
    "TechnologyRegistrationRefusal",
    "TECHNOLOGY_REGISTRATION_FACTS",
    "compose",
    "select_evidence",
    "validate_evidence_envelope",
    "registration_entry_or_refusal",
]

#: The §8 profile id and the dossier schema id are the same string; one alias,
#: so the shell's ``payload["schema"] == registration.schema_id`` check and the
#: profile routing can never drift apart.
PROFILE_ID = SCHEMA_ID
EVIDENCE_SCHEMA_ID = "technology_economic_change.evidence.v1"

#: The evidence envelope's own contract, the mirror of the composer's
#: ``CONTRACT_PATH``: :func:`validate_evidence_envelope` reads this file so the
#: runtime check and the shipped contract can never drift apart.
EVIDENCE_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts/market_ontology/technology_economic_change.evidence.v1.schema.json"
)

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


# --- the shared shell, imported lazily (NOT on this carrier base) ---------------

_SHELL_REGISTRY_MODULE = "engine.market_ontology.theme_research_registry"
_SHELL_SIBLING_MODULE = "engine.market_ontology.semiconductor_theme_research"
#: The two module names whose OWN absence means "shell not on this carrier" —
#: a ``ModuleNotFoundError`` naming anything else is a missing dependency of a
#: PRESENT shell and propagates (see :func:`_import_shell_module`).
_SHELL_MODULE_NAMES = frozenset({_SHELL_REGISTRY_MODULE, _SHELL_SIBLING_MODULE})


def _import_shell_module(name: str) -> Any:
    """Import one shared-shell module, treating ``ModuleNotFoundError`` as
    absence ONLY when the missing module IS ``name`` (``exc.name`` matches one
    of the two shell module names): a ``ModuleNotFoundError`` raised from
    INSIDE a present shell — a missing third-party dependency of the shell
    itself — carries a different ``exc.name`` and propagates, so a broken
    shell can never masquerade as ``shared_shell_unavailable``. A genuine
    non-module ``ImportError`` from a present-but-broken shell propagates too."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name in _SHELL_MODULE_NAMES:
            return None
        raise


def _resolve_vertical_registration() -> Any:
    """The REGISTRATION-ONLY resolver: the ``VerticalRegistration`` symbol from
    the registry module, or ``None`` when the module or the symbol is absent.
    The registration path (:func:`registration_entry_or_refusal`) depends on
    VerticalRegistration alone — gating it on the sibling module's
    ``OwnerBundle``/``ResearchQuery`` symbols would type
    ``shared_shell_unavailable`` for a shell whose registry ACCEPTS the §8
    entry, losing exactly the XPASS signal the pinned round-trip exists to
    detect. The full three-symbol resolver below is NOT kept for production
    consumers — it has none today, only the tests call it; it is kept as the
    pinned three-symbol shape of the §8 binding."""
    registry = _import_shell_module(_SHELL_REGISTRY_MODULE)
    if registry is None:
        return None
    return getattr(registry, "VerticalRegistration", None)


def _load_shared_shell() -> tuple[Any, Any, Any] | None:
    """Lazily import the #7870 shared shell and return
    ``(VerticalRegistration, OwnerBundle, ResearchQuery)``, or ``None`` when
    either module or any of the three symbols is absent — this carrier base
    carries neither module, and a partially-present shell is typed unavailable,
    never a silent half-binding. No shell type is copied into this branch.
    Absence means ONLY the two shell module names themselves
    (:func:`_import_shell_module`); a missing dependency of a present shell
    and any other import failure propagate. No production consumer exists —
    only the tests call it; it stays as the pinned three-symbol shape for the
    §8 binding, and the registration path does NOT use it (it needs only
    VerticalRegistration and resolves it through
    :func:`_resolve_vertical_registration` so sibling-symbol drift cannot
    drown the acceptance signal)."""
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
    consulted and no name-similarity join is ever attempted."""
    if company_ref.startswith("cik:"):
        for entry in identity_results:
            if isinstance(entry, Mapping) and entry.get("cik") == company_ref:
                return entry
        return None
    for entry in identity_results:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("entity_id") == company_ref or entry.get("node_id") == company_ref:
            return entry
    return None


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
    if getattr(query, "time_mode", None) == "system_replay":
        # PLACEHOLDER pinned to the reader owner's future contract: an identity
        # result is "as known at replay time" iff it carries a truthy
        # ``as_known`` mapping. Absent means absent — never guessed past.
        if not any(
            isinstance(entry, Mapping)
            and isinstance(entry.get("as_known"), Mapping)
            and bool(entry["as_known"])
            for entry in identity_results
        ):
            _refuse("replay_identity_unavailable")
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
    sections (PLACEHOLDER key ``theme_ref``, pinned to the §8 adjudication).
    Zero or conflicting ids are both "no accepted theme id" — never a pick."""
    theme_ids: set[str] = set()
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            continue
        scope = assertion.get("scope")
        if not isinstance(scope, Mapping):
            continue
        theme_ref = scope.get("theme_ref")
        if isinstance(theme_ref, str) and theme_ref:
            theme_ids.add(theme_ref)
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
    return compose_technology_economic_change(
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


def _cited_source_object_ids(payload: Mapping[str, Any]) -> set[str]:
    """object_ids cited by a rendered row/card/counter of THIS composed
    dossier. A refused business section renders nothing, so it cites nothing."""
    cited: set[str] = set()

    def _add(ref: Any) -> None:
        if isinstance(ref, Mapping) and isinstance(ref.get("object_id"), str) and ref["object_id"]:
            cited.add(ref["object_id"])

    business = payload.get("business")
    if isinstance(business, Mapping) and business.get("refused") is not True:
        for row in business.get("rows") or ():
            if isinstance(row, Mapping):
                _add(row.get("source_ref"))
        for card in business.get("cards") or ():
            if isinstance(card, Mapping):
                for ref in card.get("source_refs") or ():
                    _add(ref)
    for observation in payload.get("counter_observations") or ():
        if isinstance(observation, Mapping):
            _add(observation.get("source_ref"))
    return cited


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
    ``contracts/market_ontology/technology_economic_change.evidence.v1.schema.json``,
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
    """Return the closed evidence envelope for ONE authorized assertion.

    The ref is authorized iff it equals a source_ref object_id cited by a
    rendered row/card/counter of THAT composed dossier AND EXACTLY ONE
    assertion in the bundle carries that source object_id — two or more
    carrying it share the same refusal as zero, so no pick by tuple order and
    the envelope can never hand out an assertion the dossier never rendered.
    Unknown, not-selected and ambiguous refs share the ONE code
    ``not_available`` — no existence disclosure. Never fetches, never
    dereferences a locator, never widens beyond the bundle.

    That exactly-one gate is fail-closed and deliberate, but the ambiguity it
    guards against is NOT inherent to the evidence: ``source.object_id`` is
    DOCUMENT-grained while the evidence unit is assertion-grained, so two
    legitimately distinct, both-rendered assertions from ONE filing (same
    object_id, different ``selector``) both refuse ``not_available`` today.
    The durable fix — authorizing on the full source ref including the
    ``selector``, or naming an assertion-level id — is owed to §8 and
    deliberately NOT taken here; the behaviour is pinned by test so the day
    §8 names the finer key, the pin fails loudly instead of silently
    re-passing.

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
        and isinstance(assertion.get("source"), Mapping)
        and assertion["source"].get("object_id") == assertion_ref
    ]
    if len(matches) != 1 or assertion_ref not in _cited_source_object_ids(payload):
        _refuse("not_available")
    authorized = copy.deepcopy(dict(matches[0]))
    envelope = {
        "schema": EVIDENCE_SCHEMA_ID,
        "definition_version": DEFINITION_VERSION,
        "generation": payload["dossier_id"],
        "assertion": authorized,
        "limitations": sorted(_dossier_limitation_texts(payload)),
        "authority": dict(_FALSE_AUTHORITY),
    }
    validate_evidence_envelope(envelope)
    return envelope


# --- the §8 facts (what the foundation owner copies on adjudication) --------------


@dataclasses.dataclass(frozen=True, slots=True)
class TechnologyRegistrationFacts:
    """The PROPOSED §8 field set for the Technology company-first profile —
    exactly the fields §8 names, plus the two shell callables. ``anchor_theme_id``
    is ``None`` and ``slice_keys`` is empty BY PROPOSAL: under hook 1 as
    integrated these are exactly what a ``VerticalRegistration`` refuses, which
    is why nothing is registered on this branch. ``views`` is the closed view
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


def registration_entry_or_refusal() -> Any:
    """Attempt the shared-shell registration this lane deliberately does NOT
    perform, documenting the §8 dependency by execution.

    Shell absent (this carrier base) -> ``shared_shell_unavailable``. Shell
    present -> the ``VerticalRegistration`` is constructed from the facts
    FIRST and unconditionally, with no precondition against the facts: when
    hook 1 as integrated refuses the company-profile entry (anchor ``None``,
    empty slice set), the typed reason carries the shell's OWN exception type
    — ``vertical_registration_refused:<ExcType>`` — because the concrete
    reason belongs to the shell and this adapter never guesses it. A
    ``TypeError`` from the constructor is §8 signature drift and propagates
    UNCAUGHT, so the pinned strict-xfail round-trip turns into a hard error
    rather than a quietly stale xfail. If the shell ever ACCEPTS the entry
    (the §8 mount change, adjudicated), the entry is returned — and that same
    test XPASSes loudly, which is the designed signal that re-pinning is due.

    Only ``VerticalRegistration`` is resolved here
    (:func:`_resolve_vertical_registration`): the sibling module's
    ``OwnerBundle``/``ResearchQuery`` symbols are the bundle/query consumers'
    concern, and a shell that accepts the entry while those symbols drift
    must not be typed ``shared_shell_unavailable``."""
    vertical_registration = _resolve_vertical_registration()
    if vertical_registration is None:
        _refuse("shared_shell_unavailable")
    kwargs = {
        name: getattr(TECHNOLOGY_REGISTRATION_FACTS, name)
        for name in _VERTICAL_REGISTRATION_FIELDS
    }
    try:
        return vertical_registration(**kwargs)
    except TypeError:
        # Signature drift between the §8 facts and the shell's constructor:
        # never relabelled, never swallowed — the pin must hear it.
        raise
    except Exception as exc:
        _refuse("vertical_registration_refused:" + type(exc).__name__)
