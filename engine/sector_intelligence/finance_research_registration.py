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
  All eight caps are False — matching the Finance projection's caps exactly.
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

import dataclasses
import hashlib
import importlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Constants — the six frozen §8 / projection-coupling values
# ---------------------------------------------------------------------------


SCHEMA_ID: str = "finance_intelligence_research.v1"
PROFILE_ID: str = SCHEMA_ID  # §8 dispatches on profile_id (entry_kind=sector_profile)
EVIDENCE_SCHEMA_ID: str = "finance_intelligence_research.evidence.v1"
DEFINITION_VERSION: str = "2026-09-25.1"
ENTRY_KIND: str = "sector_profile"
RUN_CONTEXT_KIND: str = "finance_run_context"
VIEWS: tuple[str, ...] = ("dossier",)
TIME_MODES: tuple[str, ...] = ("latest",)

# Mirror the closure of the projection's authority caps (read at import so
# the two surfaces cannot disagree; Finance projection is the canonical
# source of these eight names).
_PROJECTION_AUTHORITY_CAPS: dict[str, bool] = {
    "rank": False,
    "gate": False,
    "size": False,
    "trade": False,
    "create_theme": False,
    "change_membership": False,
    "write_graph": False,
    "admit_source": False,
}
AUTHORITY: Mapping[str, bool] = dict(_PROJECTION_AUTHORITY_CAPS)  # type: ignore[assignment]

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
_ISO_8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$"
)

# Page-bound limits (page cursor is offset+limit; the API is scalar — offset<0
# refuses, limit outside [1, 100] refuses).
_LIMIT_MIN: int = 1
_LIMIT_MAX: int = 100


# ---------------------------------------------------------------------------
# Refusal surface — adapter codes always raise FinanceRegistrationRefusal.
# ---------------------------------------------------------------------------


class FinanceRegistrationRefusal(ValueError):
    """Codes raised by the finance registration adapter; ``str(exc) == exc.code``.

    The shell's :class:`ResearchRefusal` exists for the wider research
    system; this adapter owns its own refusal surface so a §8 draft stub
    cannot collide with a real Finance registration.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __str__(self) -> str:
        return self.code


# ---------------------------------------------------------------------------
# Lazy module resolvers — every external surface this adapter may need
# ---------------------------------------------------------------------------


def _import_shell_research_refusal() -> type[ValueError] | None:
    """The shell's :class:`ResearchRefusal` is preferred when present (it
    matches the wider research system's contract); otherwise the adapter's
    own :class:`FinanceRegistrationRefusal` is used.
    """
    try:
        module = importlib.import_module(
            "engine.market_ontology.semiconductor_theme_research"
        )
    except Exception:
        return None
    refusal_type = getattr(module, "ResearchRefusal", None)
    if isinstance(refusal_type, type) and issubclass(refusal_type, ValueError):
        return refusal_type
    return None


def _refuse(code: str) -> None:
    """Adapter codes ALWAYS raise :class:`FinanceRegistrationRefusal`. This
    helper exists for symmetry with the shell — the spec uses ``_refuse`` as
    the single failure site."""
    raise FinanceRegistrationRefusal(code)


def _import_resolver():
    """Lazily load ``source_ref_for`` from the curation_assertion module.

    Returns the callable when available, or ``None`` when the shell is
    absent (the fixture-only contract). The caller picks: ``compose`` is
    allowed to swallow a missing resolver (it just emits an empty
    ``assertion_refs`` list); ``select_evidence`` strictly refuses it.
    """
    try:
        module = importlib.import_module("engine.theme_graph.curation_assertion")
    except Exception:
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
    """Parse an ISO-8601 instant into a NAIVE :class:`datetime` so the
    projection's ``_to_iso`` (which adds ``Z`` when ``tzinfo`` is None)
    preserves the round-trip shape the sealed-in wire uses.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not _ISO_8601_RE.match(text):
        return None
    body = text[:-1] if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(body)
    except ValueError:
        return None


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
        raise FinanceRegistrationRefusal("not_available")
    if not isinstance(sector_ref, str) or sector_ref != SECTOR_REF:
        raise FinanceRegistrationRefusal("not_available")
    if view not in VIEWS:
        raise FinanceRegistrationRefusal("not_available")
    if time_mode not in TIME_MODES:
        if time_mode == "system_replay":
            raise FinanceRegistrationRefusal("identity_vintage_unsupported")
        raise FinanceRegistrationRefusal("not_available")
    if time_mode == "latest":
        if source_cutoff is not None:
            raise FinanceRegistrationRefusal("not_available")
        if recorded_cutoff is not None:
            raise FinanceRegistrationRefusal("not_available")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise FinanceRegistrationRefusal("offset_negative")
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < _LIMIT_MIN
        or limit > _LIMIT_MAX
    ):
        raise FinanceRegistrationRefusal("limit_out_of_range")

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
    ordering of revision_tuple pairs (sorted on read)."""
    rights_revision = getattr(bundle, "rights_revision", "")
    revision_pairs: list[tuple[str, str]] = []
    raw_revision_tuple = getattr(bundle, "revision_tuple", ()) or ()
    for entry in raw_revision_tuple:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            continue
        key, value = entry[0], entry[1]
        key_text = key if isinstance(key, str) else json.dumps(
            key, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        value_text = value if isinstance(value, str) else json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
        revision_pairs.append((key_text, value_text))
    revision_pairs.sort()

    canonical = {
        "definition_version": DEFINITION_VERSION,
        "rights_revision": rights_revision,
        "revision_tuple": revision_pairs,
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
)

# Owner-bundle fields that the adapter deliberately does NOT map to a
# FinanceOwnerInputs field. When the bundle carries a non-empty entry in
# any of these, the limitations list records an ``owner_field_unmapped``
# marker for the field (once each).
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
      is absent, present more than once, or has unparseable seal clocks.

    Every :class:`FinanceOwnerInputs` field other than ``theme_evidence`` is
    DECLARED ABSENT (R4 fixture-only contract). The projection is allowed
    to receive those as empty / ``None`` and renders them as such.
    """
    fp_module = importlib.import_module(
        "engine.sector_intelligence.finance_projection"
    )
    inputs_cls = getattr(fp_module, "FinanceOwnerInputs", None)
    if not isinstance(inputs_cls, type):
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    theme_evidence = [
        dict(a) for a in (getattr(bundle, "assertions", ()) or ())
        if isinstance(a, Mapping)
    ]

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
      (once per field per compose).
    * Each non-empty :attr:`bundle.omissions` entry produces an
      ``owner_omission:<reason>`` marker.

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
        for omission in bundle_value:
            if isinstance(omission, str) and omission:
                limitations.add(f"owner_omission:{omission}")
    for bundle_field in _OWNER_BUNDLE_UNMAPPED_FIELDS:
        value = getattr(bundle, bundle_field, None)
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


def _compose_assertion_refs(
    resolver, assertions: tuple[Mapping[str, Any], ...]
) -> list[dict[str, str]]:
    """Build the closed ``assertion_refs`` list. Skips any assertion whose
    resolver call raises or returns a non-conforming ref.
    """
    out: list[dict[str, str]] = []
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            continue
        curation_revision = assertion.get("curation_revision")
        if not isinstance(curation_revision, str):
            continue
        ref = _try_resolve_assertion(resolver, assertion)
        if ref is None:
            continue
        out.append(
            {"curation_revision": curation_revision, "assertion_ref": ref}
        )
    return out


def _validate_envelope(envelope: dict[str, Any]) -> None:
    """Re-validate the envelope against the on-disk contract. The project's
    :func:`validate_contract` resolves ``$ref`` through an in-memory
    registry of owned contracts (the absolute ``$id`` URIs are stable
    identifiers, never network endpoints) — direct ``Draft202012Validator``
    use would attempt HTTP for those URIs and is intentionally avoided.
    """
    from engine.sector_intelligence.contracts import validate_contract

    validate_contract(
        envelope,
        contract_id=SCHEMA_ID,
        repo_root=Path(__file__).resolve().parents[2],
    )
    validate_contract(
        envelope["dossier"],
        contract_id="finance_intelligence_read_model.v1",
        repo_root=Path(__file__).resolve().parents[2],
    )


def compose(query: Any, bundle: Any) -> dict[str, Any]:
    """Build the dossier envelope from a request and bundle.

    Refusals mirror :func:`_validate_query` plus:

    * ``generation_changed`` — ``expected_generation`` was supplied and does
      not match the recomputed fingerprint.
    * ``sealed_input_unavailable:run_context`` — see
      :func:`_owner_inputs_from_bundle`.
    * ``shared_shell_unavailable`` — projection or its ``FinanceOwnerInputs``
      dtype is missing.
    """
    request = _validate_query(query)
    inputs, generated_at, knowledge_cutoff = _owner_inputs_from_bundle(bundle)
    dossier = _dossier(inputs, generated_at, knowledge_cutoff)
    gen = _generation(request, bundle)
    if request["expected_generation"] is not None and request["expected_generation"] != gen:
        raise FinanceRegistrationRefusal("generation_changed")
    resolver = _import_resolver()
    assertion_refs = _compose_assertion_refs(
        resolver, tuple(getattr(bundle, "assertions", ()) or ())
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
) -> Mapping[str, Any] | None:
    """Walk ``assertions`` in order; the first one whose resolver call
    matches ``target_ref`` is returned. Resolver failures are skipped.

    Returns ``None`` if nothing matches (caller raises ``not_available``).
    """
    for assertion in assertions:
        if not isinstance(assertion, Mapping):
            continue
        ref = _try_resolve_assertion(resolver, assertion)
        if ref is None:
            continue
        if ref == target_ref:
            return assertion
    return None


def _collect_source_records(dossier: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The T1 dossier's ``source_records`` is already a list of closed
    source_record objects; pass them through with a defensive copy.
    """
    out: list[dict[str, Any]] = []
    for value in dossier.get("source_records", ()) or ():
        if isinstance(value, Mapping):
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
        "assertion": dict(assertion),
        "source_records": list(source_records),
        "limitations": list(limitations),
        "authority": dict(AUTHORITY),
    }
    from engine.sector_intelligence.contracts import validate_contract

    validate_contract(
        envelope,
        contract_id=EVIDENCE_SCHEMA_ID,
        repo_root=Path(__file__).resolve().parents[2],
    )
    return envelope


def select_evidence(query: Any, bundle: Any, assertion_ref: str) -> dict[str, Any]:
    """Resolve ``assertion_ref`` to its underlying assertion + the source
    records visible from the same generation.

    Refusals:

    * ``expected_generation_required`` — the caller did not pin a
      ``expected_generation``; the evidence route is generation-bound and
      we will not guess.
    * ``generation_changed`` — ``expected_generation`` mismatches.
    * ``shared_shell_unavailable`` — the resolver or projection module is
      absent (fixture-only: nothing to query against).
    * ``not_available`` — the ref is not a well-formed ``assertion_ref`` or
      no assertion in the bundle resolves to it.
    * ``sealed_input_unavailable:run_context`` — see compose.
    """
    request = _validate_query(query)
    if request["expected_generation"] is None:
        raise FinanceRegistrationRefusal("expected_generation_required")
    if not isinstance(assertion_ref, str) or not _ASSERTION_REF_PATTERN.match(assertion_ref):
        raise FinanceRegistrationRefusal("not_available")
    inputs, generated_at, knowledge_cutoff = _owner_inputs_from_bundle(bundle)
    dossier = _dossier(inputs, generated_at, knowledge_cutoff)
    gen = _generation(request, bundle)
    if request["expected_generation"] != gen:
        raise FinanceRegistrationRefusal("generation_changed")

    resolver = _import_resolver()
    if resolver is None:
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    assertions = tuple(getattr(bundle, "assertions", ()) or ())
    matched = _find_assertion_by_ref(resolver, assertions, assertion_ref)
    if matched is None:
        raise FinanceRegistrationRefusal("not_available")

    source_records = _collect_source_records(dossier)
    limitations = _build_limitations(inputs, bundle)
    return _evidence_envelope(
        request, gen, assertion_ref, matched, source_records, limitations
    )


def load_bundle(query: Any, *, rights_snapshot: Mapping[str, str] | None = None) -> Any:
    """Load the owner inputs bundle for a request.

    Refusals (per point (a) of PR #7780 comment 5828668393 + R4):

    * ``shared_shell_unavailable`` — the binding module
      ``engine.market_ontology.theme_research_binding`` is not on the
      carrier (fixture-only contract; §8 has not been merged yet).
    * ``finance_owner_loader_pending`` — when the binding IS present, raise
      the binding's :class:`BundleUnavailable` for a still-not-landed owner
      loader. The message MUST start with the refusal prefix so the carrier
      can classify it.
    """
    try:
        binding_module = importlib.import_module(
            "engine.market_ontology.theme_research_binding"
        )
    except Exception:
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    unavailable_type = getattr(binding_module, "BundleUnavailable", None)
    if not (isinstance(unavailable_type, type) and issubclass(unavailable_type, Exception)):
        raise FinanceRegistrationRefusal("shared_shell_unavailable")

    try:
        raise unavailable_type(
            "finance_owner_loader_pending: Finance owner loader not wired into "
            "the shared shell yet (T10 fixture-only contract). The §8 "
            "sector_profile dispatcher must land before this returns a bundle."
        )
    except unavailable_type as exc:
        msg = str(exc)
        if not msg.startswith("finance_owner_loader_pending"):
            raise FinanceRegistrationRefusal("shared_shell_unavailable") from exc
        raise


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
    try:
        module = importlib.import_module(
            "engine.market_ontology.theme_research_registry"
        )
    except Exception:
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
