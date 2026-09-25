"""Finance Intelligence research registration adapter (T10).

Fixture-only — nothing registers here. The §8 sector_profile entry_kind is
pending adjudication in PR #7780 (comment 5828668393); point (a) of that
comment asks for a registration adapter that conforms to the shared
research shell (PR #7870 head 6cd958e92b259f7221690547e7076f4a0de4ed33).

This module is the Finance side of that contract: every name here is frozen
to the §8 dispatch values, and every callable is a placeholder. Once §8 is
adjudicated, switching from fixture-only to a real registration is a copy of
ONE frozen constant — :data:`FINANCE_REGISTRATION_FACTS`.

Constraints:

* The evidence route is INERT until owner assertions reach the bundle (R4).
  ``select_evidence`` requires a working
  ``engine.theme_graph.curation_assertion.source_ref_for`` AND a present
  ``expected_generation``; missing either yields a typed refusal.
* Authority law: this module NEVER ranks, gates, sizes, or times anything.
  Every cap is False — matching the Finance projection's caps exactly.
* No clock reads: generation is derived from frozen fields only
  (``definition_version``, ``rights_revision``, ``revision_tuple``,
  ``profile_id``, ``sector_ref``, ``view``, ``time_mode``, ``source_cutoff``,
  ``recorded_cutoff``). The seal clock is read from the SEALED run-context
  native ref, never from this module's own clock.
* No IO, no network, no environment reads, no heavy third-party imports.

Names other modules are referenced by their dotted import path (the
contract-delta gate turns literal paths in code/comments into dependency
edges); the only literal paths this file reads are the three contract files
under :mod:`contracts.sector_intelligence` for the closed request and the
external ``engine.sector_intelligence.finance_projection`` composer.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Constants — the six frozen §8 / projection-coupling values
# ---------------------------------------------------------------------------


SCHEMA_ID: str = "finance_intelligence_research.v1"
PROFILE_ID: str = SCHEMA_ID  # §8 dispatches on profile_id (entry_kind=sector_profile)
EVIDENCE_SCHEMA_ID: str = "finance_intelligence_research.evidence.v1"
DEFINITION_VERSION: str = "2026-09-25.1"
# PROPOSED — §8 sector_profile, pending adjudication (#7780 5828668393)
ENTRY_KIND: str = "sector_profile"
# PLACEHOLDER — point (a), pending the owner's loader seam
RUN_CONTEXT_KIND: str = "finance_run_context"
VIEWS: tuple[str, ...] = ("dossier",)
TIME_MODES: tuple[str, ...] = ("latest",)

# Mirror the closure of the projection's authority caps. The registry is
# built at import time (the projection is one of this adapter's imports so
# it is always available on the carrier). Frozen as a MappingProxyType so
# call sites cannot mutate the caps without modifying the projection's
# source of truth.
def _build_authority() -> Mapping[str, bool]:
    import engine.sector_intelligence.finance_projection as fp
    return MappingProxyType({cap: False for cap in fp._AUTHORITY_CAPS})


AUTHORITY: Mapping[str, bool] = _build_authority()

# Resolve the sector_ref from the T1 read-model contract so the two contracts
# can never disagree.
_CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts" / "sector_intelligence"
_T1_SCHEMA_PATH = _CONTRACTS_ROOT / "finance_intelligence_read_model.v1.schema.json"
RESEARCH_SCHEMA_PATH = _CONTRACTS_ROOT / "finance_intelligence_research.v1.schema.json"
EVIDENCE_SCHEMA_PATH = _CONTRACTS_ROOT / "finance_intelligence_research.evidence.v1.schema.json"

SECTOR_REF: str = json.loads(_T1_SCHEMA_PATH.read_text(encoding="utf-8"))[
    "properties"
]["sector_ref"]["const"]

# The closed request fields shared between research.v1 and evidence.v1.
_REQUEST_FIELDS: tuple[str, ...] = ("profile_id", "sector_ref", "view", "time_mode")

# Evidence ``assertion_ref`` shell pattern (see contracts AND app/theme_research._EvidenceBody).
_ASSERTION_REF_PATTERN = re.compile(
    r"^gmi-curation://[a-z0-9_]+/gmirca_[0-9a-f]{32}$"
)

# Strict ISO-8601 (with time part) matching either ``Z`` or a numeric offset.
# Hours are 00..23; minutes/seconds 00..59; fractional seconds capped at six
# digits; offset REQUIRES a colon (``+HH:MM``). ``24:00`` is rejected because
# the wall-clock form is non-ISO-8601 even though several lenient libraries
# accept it — the sealed wire never carries it.
_ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)

# Page-bound limits (page cursor is offset+limit; the API is scalar — offset<0
# refuses, limit outside [1, 100] refuses).
_LIMIT_MIN: int = 1
_LIMIT_MAX: int = 100


# ---------------------------------------------------------------------------
# Refusal surface — adapter codes always raise FinanceRegistrationRefusal.
# ---------------------------------------------------------------------------


class FinanceRegistrationRefusal(ValueError):
    """Codes raised by the finance registration adapter; ``str(exc) == exc.code``."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# Lazy module resolvers — every external surface this adapter may need
# ---------------------------------------------------------------------------


#: The module names whose OWN absence means "shell not on this carrier" — a
#: ``ModuleNotFoundError`` naming anything else is a missing dependency of a
#: PRESENT shell and propagates (see :func:`_import_shell_module`).
_SHELL_REGISTRY_MODULE = "engine.market_ontology.theme_research_registry"
_SHELL_SIBLING_MODULE = "engine.market_ontology.semiconductor_theme_research"
_SHELL_BINDING_MODULE = "engine.market_ontology.theme_research_binding"
_SHELL_RESOLVER_MODULE = "engine.theme_graph.curation_assertion"
_SHELL_MODULE_NAMES = frozenset({
    _SHELL_REGISTRY_MODULE,
    _SHELL_SIBLING_MODULE,
    _SHELL_BINDING_MODULE,
    _SHELL_RESOLVER_MODULE,
})


def _import_shell_module(name: str) -> Any:
    """Import one shared-shell module, treating ``ModuleNotFoundError`` as
    absence ONLY when the missing module IS ``name`` (``exc.name`` matches
    one of the four shell module names in :data:`_SHELL_MODULE_NAMES`). A
    ``ModuleNotFoundError`` raised from INSIDE a present shell — a missing
    third-party dependency of the shell itself — carries a different
    ``exc.name`` and propagates, so a broken shell can never masquerade as
    ``shared_shell_unavailable``. A genuine non-module ``ImportError`` from
    a present-but-broken shell propagates too.
    """
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name in _SHELL_MODULE_NAMES:
            return None
        raise


def _import_shell_research_refusal() -> type[ValueError] | None:
    """The shell's :class:`ResearchRefusal` is preferred when present (it
    matches the wider research system's contract); otherwise the adapter's
    own :class:`FinanceRegistrationRefusal` is used.
    """
    module = _import_shell_module(_SHELL_SIBLING_MODULE)
    if module is None:
        return None
    refusal_type = getattr(module, "ResearchRefusal", None)
    if isinstance(refusal_type, type) and issubclass(refusal_type, ValueError):
        return refusal_type
    return None


#: Codes the shared shell categorizes as research contracts (see
#: app/theme_research._RESEARCH_REFUSAL_MAP and "not_available" handler).
#: Every code on this set raises the shell's :class:`ResearchRefusal` when
#: the shell is importable, and the adapter's :class:`FinanceRegistrationRefusal`
#: otherwise. Codes absent from this set — ``shared_shell_unavailable``,
#: ``sealed_input_unavailable:*``, ``vertical_registration_refused:*``,
#: ``finance_owner_loader_pending`` — stay typed as the adapter refusal.
_SHELL_SHARED_REFUSAL_CODES: frozenset[str] = frozenset({
    "generation_changed",
    "not_available",
    "identity_vintage_unsupported",
    "offset_negative",
    "limit_out_of_range",
    "expected_generation_required",
    "replay_cutoffs_required",
})


def _refuse(code: str) -> None:
    """The single refusal site used by every shared code in
    :data:`_SHELL_SHARED_REFUSAL_CODES`. When the shell's
    :class:`ResearchRefusal` resolves, raise it as the carrier-compatible
    type; otherwise raise the adapter's own typed refusal. The single site
    is the one place the registry can swap refs without re-architecting the
    raise sites scattered through query, generation and composition."""
    shell_type = _import_shell_research_refusal()
    if shell_type is not None and code in _SHELL_SHARED_REFUSAL_CODES:
        raise shell_type(code)
    raise FinanceRegistrationRefusal(code)


def _import_resolver():
    """Lazily load ``source_ref_for`` from the curation_assertion module.

    Returns the callable when available, or ``None`` when the shell is
    absent (the fixture-only contract). The caller picks: ``compose`` is
    allowed to swallow a missing resolver only when the bundle carries no
    assertions (see :data:`_SHELL_SHARED_REFUSAL_CODES` and the compose
    locus in :func:`compose`); ``select_evidence`` strictly refuses it.
    """
    module = _import_shell_module(_SHELL_RESOLVER_MODULE)
    if module is None:
        return None
    resolver = getattr(module, "source_ref_for", None)
    if not callable(resolver):
        return None
    return resolver


def _try_resolve_assertion(resolver, assertion: Mapping[str, Any]) -> str | None:
    """Call the resolver, swallow any failure. The ref is returned only if it
    matches the shell ``assertion_ref`` pattern.
    """
    if resolver is None:
        return None
    try:
        ref = resolver(dict(assertion))
    except Exception:
        return None
    if not isinstance(ref, str):
        return None
    if not _ASSERTION_REF_PATTERN.match(ref):
        return None
    return ref


# ---------------------------------------------------------------------------
# ISO-8601 helpers (seal clock)
# ---------------------------------------------------------------------------


def _parse_seal_clock(value: Any) -> datetime | None:
    """Parse an ISO-8601 instant STRICTLY into one timezone-aware
    :class:`datetime` so both ``Z`` and ``+HH:MM`` forms normalise to the
    same UTC-instant comparison surface. NO whitespace stripping (the
    sealed wire never carries stray spaces; whitespace would be contract
    drift). One representation — the parsed UTC instant — for both shapes
    so the interval check below can never disagree on a round-trip.
    """
    if not isinstance(value, str):
        return None
    if not _ISO_8601_RE.match(value):
        return None
    body = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        moment = datetime.fromisoformat(body)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc)


def _seal_clock_interval(generated_at: datetime, knowledge_cutoff: datetime) -> None:
    """Refuse when ``knowledge_cutoff`` is later than ``generated_at`` so the
    typed ``sealed_input_unavailable:run_context`` carries the inconsistency
    instead of letting it escape as a generic ``ContractValidationError`` once
    the envelope lands in the registry. The interval check is the same one
    :func:`engine.sector_intelligence.contracts._interval_issues` performs
    recursively across nested objects."""
    if knowledge_cutoff > generated_at:
        raise FinanceRegistrationRefusal("sealed_input_unavailable:run_context")


def _is_seal_clock(value: Any) -> bool:
    return _parse_seal_clock(value) is not None


# ---------------------------------------------------------------------------
# Query validation
# ---------------------------------------------------------------------------


def _validate_query(query: Any) -> dict[str, Any]:
    """Validate a request and return the frozen request dict. Refusals:

    * ``not_available`` — profile_id/sector_ref/view mismatch, or
      ``time_mode`` is neither ``latest`` nor ``system_replay``, or
      ``latest`` carries a non-null source/recorded cutoff.
    * ``identity_vintage_unsupported`` — ``time_mode == "system_replay"``.
    * ``offset_negative`` — ``offset < 0``.
    * ``limit_out_of_range`` — ``limit`` outside ``[1, 100]``.

    No clock, no IO, no globals; the request shape is closed by the schema.
    """
    profile_id = getattr(query, "profile_id", None)
    sector_ref = getattr(query, "sector_ref", None)
    view = getattr(query, "view", None)
    time_mode = getattr(query, "time_mode", None)
    source_cutoff = getattr(query, "source_cutoff", None)
    recorded_cutoff = getattr(query, "recorded_cutoff", None)
    offset = getattr(query, "offset", 0)
    limit = getattr(query, "limit", 50)
    expected_generation = getattr(query, "expected_generation", None)

    if not isinstance(profile_id, str) or profile_id != PROFILE_ID:
        _refuse("not_available")
    if not isinstance(sector_ref, str) or sector_ref != SECTOR_REF:
        _refuse("not_available")
    if view not in VIEWS:
        _refuse("not_available")
    if time_mode not in TIME_MODES:
        if time_mode == "system_replay":
            _refuse("identity_vintage_unsupported")
        _refuse("not_available")
    if time_mode == "latest":
        if source_cutoff is not None:
            _refuse("not_available")
        if recorded_cutoff is not None:
            _refuse("not_available")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        _refuse("offset_negative")
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < _LIMIT_MIN
        or limit > _LIMIT_MAX
    ):
        _refuse("limit_out_of_range")

    return {
        "profile_id": profile_id,
        "sector_ref": sector_ref,
        "view": view,
        "time_mode": time_mode,
        "source_cutoff": source_cutoff,
        "recorded_cutoff": recorded_cutoff,
        "offset": offset,
        "limit": limit,
        "expected_generation": expected_generation,
    }


# ---------------------------------------------------------------------------
# Generation — frozen-field fingerprint
# ---------------------------------------------------------------------------


def _generation(request: Mapping[str, Any], bundle: Any) -> str:
    """Compute the gen_ fingerprint. Insensitive to the seal clock
    (generated_at/knowledge_cutoff live on the dossier, not the identity),
    the assertion list (routed through the resolver), and the bundle's
    ordering of revision_tuple pairs (sorted via :func:`list` on read).

    The shell's recipe is verbatim — ``sorted(list(pair) for pair in
    bundle.revision_tuple)`` — and that recipe is the source of truth here:
    a malformed entry propagates as the underlying ``TypeError``/struct
    error rather than being silently swallowed. Two revisions that round-
    trip identically under :func:`json.dumps` (e.g. ``("k", 1)`` vs.
    ``("k", "1")``) deliberately differ.
    """
    rights_revision = getattr(bundle, "rights_revision", "")
    raw_revision_tuple = getattr(bundle, "revision_tuple", ()) or ()

    canonical = {
        "definition_version": DEFINITION_VERSION,
        "rights_revision": rights_revision,
        "revision_tuple": sorted(list(pair) for pair in raw_revision_tuple),
        "profile_id": request["profile_id"],
        "sector_ref": request["sector_ref"],
        "view": request["view"],
        "time_mode": request["time_mode"],
        "source_cutoff": request["source_cutoff"],
        "recorded_cutoff": request["recorded_cutoff"],
    }
    text = json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    return f"gen_{digest}"


# ---------------------------------------------------------------------------
# Owner inputs — projection-coupling with a sealed run-context ref
# ---------------------------------------------------------------------------


# Field-name list, in the projection's declaration order. Used for limitations.
_OWNER_INPUT_FIELDS: tuple[str, ...] = (
    "sector_dossier",
    "theme_evidence",
    "financial_packets",
    "expectation_observations",
    "market_observations",
    "basket_context",
    "macro_context",
    "identity_bindings",
    "source_records",
    "regime_breaks",
    "slice_catalog",
    "rights_snapshot",
)

# Owner-bundle fields that the adapter deliberately does NOT map to a
# FinanceOwnerInputs field. When the bundle carries a non-empty entry in
# any of these, the limitations list records an ``owner_field_unmapped``
# marker for the field (once each).
#
# ``native_refs`` is counted ONLY when at least one entry has kind !=
# :data:`RUN_CONTEXT_KIND` — the run-context ref is the lawful home for
# it on every carrier, so a foreign entry is the only thing actually
# unmapped to Finance.
_OWNER_BUNDLE_UNMAPPED_FIELDS: tuple[str, ...] = (
    "identity_results",
    "event_workspaces",
    "financial_packets",
    "interpretation_blocks",
    "native_refs",
)


def _owner_inputs_from_bundle(bundle: Any) -> tuple[Any, datetime, datetime]:
    """Build a :class:`FinanceOwnerInputs` and the seal clock from the bundle.

    Returns ``(inputs, generated_at, knowledge_cutoff)``. Refusals:

    * ``sealed_input_unavailable:run_context`` — the run-context native ref
      is absent, present more than once, has unparseable seal clocks, or
      carries an interval inconsistency (knowledge_cutoff later than
      generated_at — see :func:`_seal_clock_interval`).

    ``theme_evidence`` is the bundle's ``assertions`` LIST VERBATIM
    (M6) — the composer's ``_curation_revisions`` already withholds any
    non-:class:`Mapping` row when extracting the revision set, so the
    adapter does not pre-filter. Every :class:`FinanceOwnerInputs` field
    other than ``theme_evidence`` is DECLARED ABSENT (R4 fixture-only
    contract); the projection is allowed to receive those as empty /
    ``None`` and renders them as such.
    """
    fp_module = importlib.import_module(
        "engine.sector_intelligence.finance_projection"
    )
    inputs_cls = getattr(fp_module, "FinanceOwnerInputs", None)
    if not isinstance(inputs_cls, type):
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    theme_evidence = list(getattr(bundle, "assertions", ()) or ())

    rc_entries: list[dict] = []
    for entry in getattr(bundle, "native_refs", ()) or ():
        if isinstance(entry, Mapping) and entry.get("kind") == RUN_CONTEXT_KIND:
            rc_entries.append(dict(entry))
    if len(rc_entries) != 1:
        raise FinanceRegistrationRefusal("sealed_input_unavailable:run_context")
    generated_at_dt = _parse_seal_clock(rc_entries[0].get("generated_at"))
    knowledge_cutoff_dt = _parse_seal_clock(rc_entries[0].get("knowledge_cutoff"))
    if generated_at_dt is None or knowledge_cutoff_dt is None:
        raise FinanceRegistrationRefusal("sealed_input_unavailable:run_context")
    _seal_clock_interval(generated_at_dt, knowledge_cutoff_dt)

    inputs = inputs_cls(
        sector_dossier=None,
        theme_evidence=theme_evidence,
        financial_packets={},
        expectation_observations={},
        market_observations={},
        basket_context={},
        macro_context={},
        identity_bindings={},
        source_records=[],
        regime_breaks=[],
        slice_catalog=[],
        rights_snapshot={},
    )
    return inputs, generated_at_dt, knowledge_cutoff_dt


# ---------------------------------------------------------------------------
# Limitations
# ---------------------------------------------------------------------------


def _build_limitations(inputs: Any, bundle: Any) -> list[str]:
    """Build the limitations list. Three sources of truth:

    * Each :class:`FinanceOwnerInputs` field that is empty / None after
      fixture mapping gets an ``owner_input_absent:<field>`` marker.
    * Each owner-bundle field this adapter explicitly does NOT map, when
      present in the bundle, gets an ``owner_field_unmapped:<field>`` marker
      (once per field per compose). ``native_refs`` is special — see
      :data:`_OWNER_BUNDLE_UNMAPPED_FIELDS`; it counts only when at least
      one entry has kind != :data:`RUN_CONTEXT_KIND`.
    * Each :attr:`bundle.omissions` entry produces an
      ``owner_omission:<reason>`` marker. A blank string or a non-string
      omission is NEVER silently dropped (M7): it surfaces as the single
      limitation ``owner_omission:unnamed`` — deduplicated across any
      number of such entries — when that string satisfies the envelope
      contract's limitations pattern (``type: string, minLength: 1``).
      ``owner_omission:unnamed`` is exactly such a string, so the
      fallback is always valid; no sealed-input refusal is ever raised
      from the omissions source alone.

    The result is sorted and de-duplicated — same source produces the same
    bytes regardless of build order.
    """
    limitations: set[str] = set()
    for field_name in _OWNER_INPUT_FIELDS:
        value = getattr(inputs, field_name, None)
        if not value:
            limitations.add(f"owner_input_absent:{field_name}")
    bundle_value = getattr(bundle, "omissions", ()) or ()
    if bundle_value:
        unnamed_present = False
        for omission in bundle_value:
            # R8 (M7 amendment): a whitespace-only string (``.strip() == ""``)
            # is blank — it cannot carry an omission reason, so it collapses
            # to the single deduplicated ``owner_omission:unnamed`` marker.
            if isinstance(omission, str) and omission.strip():
                limitations.add(f"owner_omission:{omission}")
            else:
                unnamed_present = True
        if unnamed_present:
            limitations.add("owner_omission:unnamed")
    for bundle_field in _OWNER_BUNDLE_UNMAPPED_FIELDS:
        value = getattr(bundle, bundle_field, None)
        if bundle_field == "native_refs":
            if isinstance(value, (list, tuple)) and len(value) > 0:
                if any(
                    not (isinstance(entry, Mapping) and entry.get("kind") == RUN_CONTEXT_KIND)
                    for entry in value
                ):
                    limitations.add(f"owner_field_unmapped:{bundle_field}")
            elif isinstance(value, Mapping) and len(value) > 0:
                limitations.add(f"owner_field_unmapped:{bundle_field}")
            continue
        if isinstance(value, (list, tuple)) and len(value) > 0:
            limitations.add(f"owner_field_unmapped:{bundle_field}")
        elif isinstance(value, Mapping) and len(value) > 0:
            limitations.add(f"owner_field_unmapped:{bundle_field}")
    return sorted(limitations)


# ---------------------------------------------------------------------------
# Compose / select_evidence
# ---------------------------------------------------------------------------


def _dossier(inputs: Any, generated_at: datetime, knowledge_cutoff: datetime) -> dict[str, Any]:
    """Call the projection composer. The composer is PURE: it never reads its
    own clock, takes generated_at / knowledge_cutoff as params, and never
    touches IO or env.
    """
    fp_module = importlib.import_module(
        "engine.sector_intelligence.finance_projection"
    )
    composer = getattr(fp_module, "compose_finance_projection", None)
    if not callable(composer):
        raise FinanceRegistrationRefusal("shared_shell_unavailable")
    return composer(
        inputs,
        generated_at=generated_at,
        knowledge_cutoff=knowledge_cutoff,
    )


def _consumed_revision_set(dossier: Mapping[str, Any]) -> set[str]:
    """Extract the dossier's consumed ``curation_revision`` set verbatim.

    The composer emits this set under ``dossier.snapshot_identity`` and it
    is the ONLY authority on which revisions the dossier consumed. The
    adapter never infers or rebuilds it.
    """
    snapshot = dossier.get("snapshot_identity") if isinstance(dossier, Mapping) else None
    if not isinstance(snapshot, Mapping):
        return set()
    raw = snapshot.get("curation_revision_set")
    if not isinstance(raw, (list, tuple)):
        return set()
    return {str(item) for item in raw if isinstance(item, str) and item}


def _compose_assertion_refs(
    resolver,
    assertions: tuple[Mapping[str, Any], ...],
    consumed: set[str] | None = None,
) -> list[dict[str, str]]:
    """Build the closed ``assertion_refs`` list, restricted to revisions the
    dossier actually consumed.

    Behaviour:

    * Keep only assertions whose ``curation_revision`` is a STR AND appears
      in the consumed set (``dossier.snapshot_identity.curation_revision_set``).
      An assertion whose revision is non-string (e.g. an integer) is
      dropped here — it could never have reached the dossier.
    * Skip any assertion whose resolver call raises or returns a non-
      conforming ref.
    * When the bundle carries any assertion AND the resolver is absent,
      ``shared_shell_unavailable`` is raised — a present assertion list
      with no resolver is the documented "the dossier could be wrong"
      case; a silent empty list is forbidden.
    * Return the result SORTED by ``curation_revision`` so the bytes are
      byte-identical across compose calls on the same inputs.
    """
    if resolver is None and assertions:
        raise FinanceRegistrationRefusal("shared_shell_unavailable")
    out: list[dict[str, str]] = []
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            continue
        curation_revision = assertion.get("curation_revision")
        if not isinstance(curation_revision, str):
            continue
        if consumed is not None and curation_revision not in consumed:
            continue
        ref = _try_resolve_assertion(resolver, assertion)
        if ref is None:
            continue
        out.append(
            {"curation_revision": curation_revision, "assertion_ref": ref}
        )
    out.sort(key=lambda r: r["curation_revision"])
    return out


#: A lazily-built, module-level :class:`ContractRegistry` reused across
#: every compose/select_evidence call — :func:`validate_contract` mints a
#: fresh registry per call and re-discovers every owned schema, which is
#: wasted on this adapter's tight loop. The registry is built on first use
#: and never rebuilt.
_contract_registry: Any | None = None


def _registry() -> Any:
    global _contract_registry
    if _contract_registry is None:
        from engine.sector_intelligence.contracts import ContractRegistry

        _contract_registry = ContractRegistry(Path(__file__).resolve().parents[2])
    return _contract_registry


def _validate_envelope(envelope: dict[str, Any]) -> None:
    """Re-validate the envelope against the on-disk contract. The cached
    :class:`ContractRegistry` is the ONE source of ``$ref`` truth for
    every compose/select_evidence call.

    A nested-body interval check (``knowledge_cutoff`` later than
    ``generated_at`` in any sub-object) is reached by the registry's
    recursive :func:`_interval_issues` pass — that single envelope
    validation is therefore sufficient and the legacy separate dossier
    re-validation is dropped (B8 seat ruling; see
    ``tests/test_finance_research_registration.py::test_envelope_validation_rejects_late_knowledge_cutoff_in_nested_body``).
    """
    _registry().validate(SCHEMA_ID, envelope)


def compose(query: Any, bundle: Any) -> dict[str, Any]:
    """Build the dossier envelope from a request and bundle.

    Refusals mirror :func:`_validate_query` plus:

    * ``generation_changed`` — ``expected_generation`` was supplied and does
      not match the recomputed fingerprint. The check runs BEFORE building
      owner inputs (M1) so a stale generation with a missing run-context
      refuses here rather than after the projection runs.
    * ``sealed_input_unavailable:run_context`` — see
      :func:`_owner_inputs_from_bundle`.
    * ``shared_shell_unavailable`` — projection or its ``FinanceOwnerInputs``
      dtype is missing, OR the bundle carries assertions but the resolver
      is absent (B3 (c)).
    """
    request = _validate_query(query)
    gen = _generation(request, bundle)
    if request["expected_generation"] is not None and request["expected_generation"] != gen:
        _refuse("generation_changed")
    inputs, generated_at, knowledge_cutoff = _owner_inputs_from_bundle(bundle)
    dossier = _dossier(inputs, generated_at, knowledge_cutoff)
    resolver = _import_resolver()
    consumed = _consumed_revision_set(dossier)
    assertion_refs = _compose_assertion_refs(
        resolver, tuple(getattr(bundle, "assertions", ()) or ()), consumed
    )
    limitations = _build_limitations(inputs, bundle)

    envelope = {
        "contract_id": SCHEMA_ID,
        "schema": SCHEMA_ID,
        "definition_version": DEFINITION_VERSION,
        "generation": gen,
        "request": {field: request[field] for field in _REQUEST_FIELDS},
        "dossier": dossier,
        "assertion_refs": assertion_refs,
        "limitations": limitations,
        "authority": dict(AUTHORITY),
    }
    _validate_envelope(envelope)
    return envelope


def _find_assertion_by_ref(
    resolver,
    assertions: tuple[Mapping[str, Any], ...],
    target_ref: str,
    consumed: set[str],
) -> Mapping[str, Any] | None:
    """Walk ``assertions`` in order; the first one whose resolver call
    matches ``target_ref`` is returned. Resolver failures are skipped.

    The selection rule (B2):

    * The assertion is selected only when ``curation_revision`` is a STR
      AND ``curation_revision in consumed`` (the dossier's published
      ``curation_revision_set``). A non-string revision is never
      selectable, even when the resolver would echo a ref for it.
    * Returns ``None`` if nothing matches (caller raises ``not_available``).
    """
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            continue
        curation_revision = assertion.get("curation_revision")
        if not isinstance(curation_revision, str):
            continue
        if curation_revision not in consumed:
            continue
        ref = _try_resolve_assertion(resolver, assertion)
        if ref is None:
            continue
        if ref == target_ref:
            return assertion
    return None


def _collect_source_records(
    dossier: Mapping[str, Any], selected_curation_revision: str
) -> list[dict[str, Any]]:
    """The evidence envelope's ``source_records`` is filtered to entries
    whose ``evidence_ref`` equals the SELECTED ASSERTION's
    ``curation_revision`` string (B4, seat ruling). Finance-owned source
    records reference the curation revision id, NOT the shell's
    ``gmi-curation://`` URI addressing form — so the comparison key here is
    the matched assertion's ``curation_revision``, not the
    ``assertion_ref`` URI. When no source record names that revision, the
    list is EMPTY — never the full dossier's records. Comparison is
    ``str(exc) == exc.code``-exact (no coercion).
    """
    out: list[dict[str, Any]] = []
    for value in dossier.get("source_records", ()) or ():
        if isinstance(value, Mapping) and value.get("evidence_ref") == selected_curation_revision:
            out.append(dict(value))
    return out


def _evidence_envelope(
    query_dict: Mapping[str, Any],
    gen: str,
    assertion_ref: str,
    assertion: Mapping[str, Any],
    source_records: list[dict[str, Any]],
    limitations: list[str],
) -> dict[str, Any]:
    envelope = {
        "contract_id": EVIDENCE_SCHEMA_ID,
        "schema": EVIDENCE_SCHEMA_ID,
        "definition_version": DEFINITION_VERSION,
        "generation": gen,
        "request": {field: query_dict[field] for field in _REQUEST_FIELDS},
        "assertion_ref": assertion_ref,
        "assertion": copy.deepcopy(dict(assertion)),
        "source_records": list(source_records),
        "limitations": list(limitations),
        "authority": dict(AUTHORITY),
    }
    _registry().validate(EVIDENCE_SCHEMA_ID, envelope)
    return envelope


def select_evidence(query: Any, bundle: Any, assertion_ref: str) -> dict[str, Any]:
    """Resolve ``assertion_ref`` to its underlying assertion + the source
    records visible from the same generation.

    Refusals (R4 packet order — generation check runs BEFORE the assertion
    ref pattern check):

    * ``expected_generation_required`` — the caller did not pin a
      ``expected_generation``; the evidence route is generation-bound and
      we will not guess.
    * ``generation_changed`` — ``expected_generation`` mismatches. The
      check runs BEFORE the ``assertion_ref`` pattern check (R4).
    * ``shared_shell_unavailable`` — the resolver or projection module is
      absent (fixture-only: nothing to query against).
    * ``not_available`` — the ref is not a well-formed ``assertion_ref`` or
      no assertion in the bundle resolves to it AFTER the consumed-set
      filter (B2).
    * ``sealed_input_unavailable:run_context`` — see compose.
    """
    request = _validate_query(query)
    if request["expected_generation"] is None:
        _refuse("expected_generation_required")
    gen = _generation(request, bundle)
    if request["expected_generation"] != gen:
        _refuse("generation_changed")
    if not isinstance(assertion_ref, str) or not _ASSERTION_REF_PATTERN.fullmatch(assertion_ref):
        _refuse("not_available")
    inputs, generated_at, knowledge_cutoff = _owner_inputs_from_bundle(bundle)
    dossier = _dossier(inputs, generated_at, knowledge_cutoff)

    resolver = _import_resolver()
    if resolver is None:
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    consumed = _consumed_revision_set(dossier)
    assertions = tuple(getattr(bundle, "assertions", ()) or ())
    matched = _find_assertion_by_ref(resolver, assertions, assertion_ref, consumed)
    if matched is None:
        _refuse("not_available")

    source_records = _collect_source_records(dossier, matched["curation_revision"])
    limitations = _build_limitations(inputs, bundle)
    return _evidence_envelope(
        request, gen, assertion_ref, matched, source_records, limitations
    )


def load_bundle(query: Any, *, rights_snapshot: Mapping[str, str] | None = None) -> Any:
    """Load the owner inputs bundle for a request.

    Behaviour (R5, the round-1 M3 instruction is SUPERSEDED — the packet and
    the shell's own contract govern):

    * If the binding module ``engine.market_ontology.theme_research_binding``
      resolves AND it exposes a usable ``BundleUnavailable`` Exception
      subclass, raise that class DIRECTLY with a message that starts
      ``finance_owner_loader_pending`` and names point (a) of PR #7780
      comment 5828668393 and R4. The shell maps ``BundleUnavailable`` to
      its fixed private 503; the carrier classifies the hold by the prefix
      and the comment/ruling ids inside the message.
    * Otherwise (the binding is absent, OR the module is present but
      exposes no usable ``BundleUnavailable`` type) raise
      :class:`FinanceRegistrationRefusal` with the bare code
      ``shared_shell_unavailable``. The class contract requires
      ``str(exc) == exc.code`` and no whitespace in ``.code`` (mirrors
      :class:`ResearchRefusal`); no call site passes a sentence as the
      code.
    """
    binding_module = _import_shell_module(_SHELL_BINDING_MODULE)
    if binding_module is None:
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    unavailable_type = getattr(binding_module, "BundleUnavailable", None)
    if not (isinstance(unavailable_type, type) and issubclass(unavailable_type, Exception)):
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    # Direct raise — the shell maps BundleUnavailable to its fixed private
    # 503 envelope. The message prefix classifies the hold; the body names
    # the source comment + R4 so the carrier can route the hold without
    # needing repo state.
    raise unavailable_type(
        "finance_owner_loader_pending: Finance owner loader not wired into "
        "the shared shell yet (T10 fixture-only contract, PR #7780 "
        "comment 5828668393 point (a), R4). The §8 sector_profile "
        "dispatcher must land before this returns a bundle."
    )


# ---------------------------------------------------------------------------
# Registration facts + the §8 wire entry
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class FinanceRegistrationFacts:
    """The frozen field set the §8 dispatcher will eventually see."""

    entry_kind: str
    profile_id: str
    sector_ref: str
    anchor_theme_id: None  # sector_profile entry_kind replaces the shell's anchor_theme_id
    slice_keys: tuple[str, ...]
    views: tuple[str, ...]
    schema_id: str
    evidence_schema_id: str
    definition_version: str
    title_en: str
    title_zh: str
    note_en: str
    note_zh: str
    compose: Any
    select_evidence: Any
    load_bundle: Any


FINANCE_REGISTRATION_FACTS = FinanceRegistrationFacts(
    entry_kind=ENTRY_KIND,
    profile_id=PROFILE_ID,
    sector_ref=SECTOR_REF,
    anchor_theme_id=None,
    slice_keys=(),
    views=VIEWS,
    schema_id=PROFILE_ID,
    evidence_schema_id=EVIDENCE_SCHEMA_ID,
    definition_version=DEFINITION_VERSION,
    title_en="Finance Intelligence",
    title_zh="金融情报",
    note_en=(
        "A rerating-first read of the financial system for members. "
        "Nothing here ranks, gates, sizes or times anything."
    ),
    note_zh=(
        "面向会员的金融体系重估研究。此处内容不构成排序、准入、仓位或时机判断。"
    ),
    compose=compose,
    select_evidence=select_evidence,
    load_bundle=load_bundle,
)


# VerticalRegistration field set (12), in the shell's exact order. The facts
# table above carries additional §8 columns (entry_kind, profile_id,
# sector_ref, anchor_theme_id, slice_keys, views); the share with the shell
# is exactly this tuple.
_VERTICAL_REGISTRATION_FIELDS: tuple[str, ...] = (
    "anchor_theme_id",
    "slice_keys",
    "schema_id",
    "evidence_schema_id",
    "definition_version",
    "compose",
    "select_evidence",
    "load_bundle",
    "title_en",
    "title_zh",
    "note_en",
    "note_zh",
)


def _resolve_vertical_registration_class() -> Any:
    """Resolve ``VerticalRegistration`` from the shared shell module. Returns
    ``None`` when the shell is absent (the fixture-only contract)."""
    module = _import_shell_module(_SHELL_REGISTRY_MODULE)
    if module is None:
        return None
    cls = getattr(module, "VerticalRegistration", None)
    if not isinstance(cls, type):
        return None
    return cls


def registration_entry_or_refusal() -> Any:
    """Return the entry the shared shell expects. Refusals (all adapter
    codes — neither the shell's refusal nor a bare ``ValueError`` leak
    through):

    * ``shared_shell_unavailable`` — the shell is not on the carrier. This
      is the EXPECTED state on this worktree (§8 is pending adjudication).
    * ``vertical_registration_refused:<ExcType>`` — the shell is present but
      construction raised a non-``TypeError`` exception.
    * ``TypeError`` — propagate the shell's structural error so the carrier
      diagnoses the signature gap, exactly as the shell's design
      requires. The adapter never silently coerces.

    The structural construction is performed BEFORE any IO so a TypeError
    surfaces immediately and the carrier classifies it.
    """
    cls = _resolve_vertical_registration_class()
    if cls is None:
        raise FinanceRegistrationRefusal("shared_shell_unavailable")
    kwargs = {
        "anchor_theme_id": FINANCE_REGISTRATION_FACTS.anchor_theme_id,
        "slice_keys": FINANCE_REGISTRATION_FACTS.slice_keys,
        "schema_id": FINANCE_REGISTRATION_FACTS.schema_id,
        "evidence_schema_id": FINANCE_REGISTRATION_FACTS.evidence_schema_id,
        "definition_version": FINANCE_REGISTRATION_FACTS.definition_version,
        "compose": FINANCE_REGISTRATION_FACTS.compose,
        "select_evidence": FINANCE_REGISTRATION_FACTS.select_evidence,
        "load_bundle": FINANCE_REGISTRATION_FACTS.load_bundle,
        "title_en": FINANCE_REGISTRATION_FACTS.title_en,
        "title_zh": FINANCE_REGISTRATION_FACTS.title_zh,
        "note_en": FINANCE_REGISTRATION_FACTS.note_en,
        "note_zh": FINANCE_REGISTRATION_FACTS.note_zh,
    }
    try:
        return cls(**kwargs)
    except TypeError:
        raise
    except Exception as exc:
        raise FinanceRegistrationRefusal(
            f"vertical_registration_refused:{type(exc).__name__}"
        ) from exc


# ---------------------------------------------------------------------------
# __all__ — public surface for the carrier
# ---------------------------------------------------------------------------


__all__ = (
    "SCHEMA_ID",
    "PROFILE_ID",
    "EVIDENCE_SCHEMA_ID",
    "DEFINITION_VERSION",
    "ENTRY_KIND",
    "RUN_CONTEXT_KIND",
    "SECTOR_REF",
    "VIEWS",
    "TIME_MODES",
    "AUTHORITY",
    "RESEARCH_SCHEMA_PATH",
    "EVIDENCE_SCHEMA_PATH",
    "FinanceRegistrationRefusal",
    "FinanceRegistrationFacts",
    "FINANCE_REGISTRATION_FACTS",
    "_VERTICAL_REGISTRATION_FIELDS",
    "compose",
    "select_evidence",
    "load_bundle",
    "registration_entry_or_refusal",
)
