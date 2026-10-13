"""Frozen state/scenario contracts for Capital Structure Intelligence V2 (task C0).

Masterplan ``research/capital_structure/e2e_20261013/MASTERPLAN.md`` §9 freezes
the shared types before parallel writers start.  This module is a deterministic,
dependency-free type contract: no I/O, no HTTP, no model call and no ledger
writer.  It owns exactly four things.

1. Schema names, the contract version and the compatibility table that bind the
   new state family to the existing ``capital_structure.projection_bundle.v1``.
   The projection bundle is never renamed and its observed-event reader stays
   the consumer path until an accepted migration (acceptance row A06).
2. The frozen records every planned same-owner module exchanges:
   ``StateRequest``, ``CapitalInputs``, ``CapitalState``, ``FinancingScenario``,
   ``CapacityEnvelope``, ``SupplyEnvelope``, ``FundingSchedule``,
   ``InstrumentSet``, ``ShareBasisResult``, ``RulePack`` and
   ``CalculationReceipt``.
3. The null law and the basis law as type invariants: unknown is never ``0`` or
   infinity, every share quantity names its basis, shared-pool maxima are never
   summed, a numeric bound without applicability evidence is rejected, and a
   changed assumption is a different scenario identity rather than a mutation.
4. Interface ownership for the planned modules so a second writer collides with
   this freeze instead of silently diverging (``INTERFACE_OWNERSHIP``).

Nothing here is a truth store.  ``CapitalState`` is a derived owner artifact
compiled over accepted inputs with explicit per-family provenance and support
limits.  Authority is identical to the projection bundle: context only, no rank,
sizing, entry or Prophet authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from .projection import (
    AUTHORITY as PROJECTION_AUTHORITY,
    PROJECTION_BUNDLE_SCHEMA,
    PROJECTION_VERSION,
    UNAVAILABLE_CAPABILITIES as PROJECTION_UNAVAILABLE_CAPABILITIES,
)

# ---------------------------------------------------------------------------
# Names, versions and compatibility
# ---------------------------------------------------------------------------

STATE_SCHEMA = "capital_structure.state.v2"
STATE_CONTRACT_VERSION = "capital-structure-state-contracts/2.0.0"
STATE_SCHEMA_FILE = "capital_structure_state.v2.schema.json"
STATE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / STATE_SCHEMA_FILE

RECORD_SCHEMAS = {
    "state": STATE_SCHEMA,
    "state_request": "capital_structure.state_request.v2",
    "capital_inputs": "capital_structure.capital_inputs.v2",
    "rule_pack": "capital_structure.rule_pack.v2",
    "financing_scenario": "capital_structure.financing_scenario.v2",
    "capacity_envelope": "capital_structure.capacity_envelope.v2",
    "supply_envelope": "capital_structure.supply_envelope.v2",
    "funding_schedule": "capital_structure.funding_schedule.v2",
    "instrument_set": "capital_structure.instrument_set.v2",
    "share_basis_result": "capital_structure.share_basis_result.v2",
    "calculation_receipt": "capital_structure.calculation_receipt.v2",
}

#: The projection family this state family is compatible with.  The constant is
#: imported from the projection module so a rename there fails this contract.
PROJECTION_COMPATIBILITY = {
    "projection_bundle_schema": PROJECTION_BUNDLE_SCHEMA,
    "projection_version_floor": PROJECTION_VERSION,
    "projection_version_prefix": "capital-structure-event-projection/1.",
    "observed_event_reader": "engine.capital_structure.projection.build_projection_bundle",
    "observed_event_reader_status": "preserved",
    "state_contract_version": STATE_CONTRACT_VERSION,
}

#: Accepted input families and the schema constants each may bind.  A family with
#: no accepted schema is ``not_built``: it may be bound only as unavailable and
#: may carry no records.
COMPATIBLE_INPUT_SCHEMAS: dict[str, tuple[str, ...]] = {
    "event_projection": (PROJECTION_BUNDLE_SCHEMA,),
    "events": ("capital_structure.event.v1",),
    "event_edges": ("capital_structure.event_edge.v1",),
    "registration_lifecycle": ("capital_structure.registration_lifecycle_bundle.v1",),
    "document_terms": ("capital_structure.document_term_observation.v1",),
    "covenant_terms": ("capital_structure.covenant_term_observation.v1",),
    "instrument_candidate_terms": ("capital_structure.instrument_candidate_term.v1",),
    "share_count_observations": (
        "capital_structure.share_count_observation.v1",
        "capital_structure.share_count_observation.v2",
    ),
    "financials": (),
    "corrections": (),
}

#: Twin families of the frozen ``capital_structure_state.v2`` ontology
#: (2026-08-18 masterplan §11, DEC:CS-V2-SIX-QUESTION-ONTOLOGY).
STATE_FAMILIES = (
    "identity",
    "share_basis",
    "registration",
    "instruments",
    "cash_funding",
    "transactions",
    "uncertainty",
    "change_events",
)

#: Authority is byte-identical to the projection bundle.  The state family never
#: widens it.
AUTHORITY = dict(PROJECTION_AUTHORITY)

#: Capabilities the projection bundle lists as unavailable.  A state generation
#: must keep every one of them unavailable unless it carries a capability proof
#: naming the generation and the test that proved it (acceptance row A06).
INHERITED_UNAVAILABLE_CAPABILITIES = tuple(PROJECTION_UNAVAILABLE_CAPABILITIES)

#: Planned same-owner interfaces (masterplan §9).  Every planned module must
#: expose exactly this callable; the reader stays ``app/capital_structure.py``
#: and never implements a second calculation path.
INTERFACE_OWNER = "capital-structure-intelligence"
INTERFACE_READER = "app/capital_structure.py"
INTERFACE_OWNERSHIP: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "engine/capital_structure/issuer_state.py",
        "compile_issuer_state",
        ("StateRequest", "CapitalInputs"),
        "CapitalState",
    ),
    (
        "engine/capital_structure/instrument_resolution.py",
        "resolve_instruments",
        ("CandidateBundle", "ResolutionInputs", "as_of"),
        "InstrumentSet",
    ),
    (
        "engine/capital_structure/share_basis.py",
        "select_share_basis",
        ("ShareInputs", "CorporateActionInputs", "as_of"),
        "ShareBasisResult",
    ),
    (
        "engine/capital_structure/capacity.py",
        "evaluate_capacity",
        ("CapitalState", "FinancingScenario", "RulePack"),
        "CapacityEnvelope",
    ),
    (
        "engine/capital_structure/supply_scenarios.py",
        "evaluate_supply",
        ("InstrumentSet", "ShareBasisResult", "FinancingScenario"),
        "SupplyEnvelope",
    ),
    (
        "engine/capital_structure/funding.py",
        "project_funding",
        ("FinancialInputs", "CommitmentInputs", "FinancingScenario"),
        "FundingSchedule",
    ),
)

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

UNIT_KINDS = ("usd", "shares", "votes", "percent", "ratio", "days")
QUANTITY_STATUSES = ("known", "unknown", "not_applicable", "contradicted", "withheld")
SHARE_BASES = (
    "issued_and_outstanding",
    "assumed_as_converted",
    "scenario_incremental_issuance",
    "potentially_resalable_existing",
    "weighted_average_eps",
    "non_affiliate_public_float",
    "authorized_unissued",
    "reserved_for_issuance",
    "treasury",
    "preferred_as_converted_equivalent",
)
VIEW_MODES = ("current", "then_known", "scenario")
SCENARIO_VIEWS = ("then_known", "counterfactual")
SUPPORT_STATES = ("supported", "partial", "unavailable", "not_built")
RULE_CLASSES = ("binding_rule", "staff_interpretation", "issuer_assertion", "proposed_reform")
CONSTRAINT_KINDS = (
    "dollars",
    "shares",
    "voting_power",
    "holder_ownership",
    "registered_class",
    "programme_balance",
    "reserved_authorized_shares",
    "covenant_headroom",
    "time_window",
)
CONSTRAINT_STATUSES = ("binding", "slack", "unknown", "inapplicable")
STOCK_OR_FLOW = ("stock", "flow")
ROUTE_KINDS = (
    "shelf_takedown",
    "at_the_market",
    "equity_line",
    "registered_direct",
    "pipe",
    "warrant_exercise",
    "conversion",
    "debt_draw",
    "repurchase",
    "redemption",
    "exchange",
    "other",
)
ROUTE_STATUSES = ("eligible", "conditional", "ineligible", "unknown")
SETTLEMENTS = ("cash", "cashless", "net_share", "pre_funded", "unknown")
INSTRUMENT_KINDS = (
    "common",
    "warrant",
    "pre_funded_warrant",
    "convertible_note",
    "convertible_preferred",
    "preferred",
    "debt",
    "unit",
    "earnout",
    "option",
    "restricted_stock_unit",
    "other",
)
INSTRUMENT_STATUSES = ("outstanding", "retired", "amended", "unresolved_candidate")
RESOLUTION_METHODS = ("supported_identity", "amendment_join", "retirement", "unresolved")
SHARE_BASIS_STATUSES = ("selected", "conflict", "refused", "unavailable")
CORPORATE_ACTION_KINDS = ("none", "reverse_split", "forward_split")
FLOW_KINDS = ("source", "use")
FLOW_CERTAINTIES = ("contractual_dated", "conditional", "assumed")
CASH_BASES = (
    "unrestricted_cash",
    "unrestricted_cash_and_marketable_securities",
    "unrestricted_and_restricted_cash",
    "unknown",
)
CASH_EFFECT_KINDS = ("proceeds", "no_cash", "repayment", "fee")
PRICE_KINDS = ("fixed", "path")

#: Property names no state record may carry (acceptance row A48 plus the
#: projection's own public-safety list).  ``fully_diluted`` is a basis the
#: contract refuses by construction (masterplan §4).
FORBIDDEN_PROPERTY_PATTERN = re.compile(
    r"^(?:object_?keys?|raw_?(?:docs?|documents?)|scores?|probabilit(?:y|ies)|"
    r"capacities|capacity|runway|overhang|fully_?diluted(?:_[a-z_]+)?|ranks?|ranking|"
    r"sizing|position_?size|entry|prophet(?:_[a-z_]+)?|likelihood|expected_dilution)$"
)

_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_SHA256 = re.compile(r"^[A-Fa-f0-9]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,199}$")


class ContractViolation(ValueError):
    """A frozen contract invariant was broken."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_of(value: Any) -> str:
    """Hex digest of the canonical JSON form of ``value``."""
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def stable_id(prefix: str, body: Any) -> str:
    """``<prefix>:cs:<32 hex>`` digest identity over canonical JSON."""
    return f"{prefix}:cs:{sha256_of(body)[:32]}"


def _decimal(value: Any, field_name: str, *, nonnegative: bool = True) -> str:
    _require(isinstance(value, str) and bool(_DECIMAL.match(value)), f"{field_name}: decimal string required, got {value!r}")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - regex already excludes
        raise ContractViolation(f"{field_name}: {value!r} is not a decimal") from exc
    _require(number.is_finite(), f"{field_name}: must be finite")
    if nonnegative:
        _require(number >= 0, f"{field_name}: must be nonnegative, got {value!r}")
    return value


def _timestamp(value: Any, field_name: str) -> str:
    _require(isinstance(value, str) and value, f"{field_name}: ISO-8601 timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractViolation(f"{field_name}: {value!r} is not an ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{field_name}: timestamp must carry a timezone")
    return value


def _date(value: Any, field_name: str) -> str:
    _require(isinstance(value, str) and value, f"{field_name}: ISO date required")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ContractViolation(f"{field_name}: {value!r} is not an ISO date") from exc
    return value


def _identifier(value: Any, field_name: str) -> str:
    _require(isinstance(value, str) and bool(_ID.match(value)), f"{field_name}: identifier required, got {value!r}")
    return value


def _member(value: Any, allowed: Sequence[str], field_name: str) -> str:
    _require(value in allowed, f"{field_name}: {value!r} not in {list(allowed)}")
    return value


def _unique(values: Sequence[str], field_name: str) -> None:
    _require(len(set(values)) == len(values), f"{field_name}: duplicate entries {sorted(values)}")


def _tuple(value: Any, field_name: str) -> tuple:
    _require(isinstance(value, (tuple, list)), f"{field_name}: sequence required")
    return tuple(value)


def _records(value: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    out = []
    for index, item in enumerate(_tuple(value, field_name)):
        _require(isinstance(item, Mapping), f"{field_name}[{index}]: mapping required")
        out.append(dict(item))
    return tuple(out)


def _assert_safe_keys(value: Any, path: str = "<root>") -> None:
    """Reject forbidden property names anywhere in a record."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(isinstance(key, str), f"{path}: non-string key")
            _require(not FORBIDDEN_PROPERTY_PATTERN.match(key), f"{path}.{key}: forbidden property name")
            _assert_safe_keys(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_safe_keys(item, f"{path}[{index}]")


def _record(obj: Any) -> Any:
    """Recursive JSON-able form of a frozen record or plain value."""
    if hasattr(obj, "as_record"):
        return obj.as_record()
    if isinstance(obj, Mapping):
        return {str(key): _record(item) for key, item in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_record(item) for item in obj]
    return obj


def _plain(obj: Any) -> dict[str, Any]:
    """Field dictionary of a dataclass instance with nested records expanded."""
    return {item.name: _record(getattr(obj, item.name)) for item in fields(obj)}


# ---------------------------------------------------------------------------
# Evidence, provenance and quantities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceRef:
    """Exact retained-byte reference: manifest, span and the span's text hash."""

    manifest_id: str
    span_id: str
    text_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.manifest_id, "evidence.manifest_id")
        _identifier(self.span_id, "evidence.span_id")
        _require(bool(_SHA256.match(self.text_sha256)), "evidence.text_sha256: sha256 hex required")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class Provenance:
    """Source and version of one quantity or claim."""

    input_family: str
    generation_id: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()
    available_at: str | None = None

    def __post_init__(self) -> None:
        _member(self.input_family, tuple(COMPATIBLE_INPUT_SCHEMAS), "provenance.input_family")
        if self.generation_id is not None:
            _identifier(self.generation_id, "provenance.generation_id")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        for item in self.evidence:
            _require(isinstance(item, EvidenceRef), "provenance.evidence: EvidenceRef required")
        if self.available_at is not None:
            _timestamp(self.available_at, "provenance.available_at")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class Quantity:
    """A unit-bearing number whose absence is a first-class state.

    ``unknown``, ``not_applicable``, ``contradicted`` and ``withheld`` carry no
    value: missing is never ``0`` and never infinity.  A ``shares`` quantity
    must name its basis even when unknown; a non-share quantity may not.
    """

    unit: str
    status: str = "unknown"
    value: str | None = None
    share_basis: str | None = None
    security_class_id: str | None = None
    applicability: str | None = None
    provenance: Provenance | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        _member(self.unit, UNIT_KINDS, "quantity.unit")
        _member(self.status, QUANTITY_STATUSES, "quantity.status")
        if self.status == "known":
            _decimal(self.value, "quantity.value")
        else:
            _require(self.value is None, f"quantity.value must be null when status is {self.status!r}")
        if self.unit == "shares":
            _require(self.share_basis is not None, "quantity.share_basis: a share quantity must name its basis")
            _member(self.share_basis, SHARE_BASES, "quantity.share_basis")
        else:
            _require(self.share_basis is None, "quantity.share_basis: only share quantities carry a basis")
        if self.security_class_id is not None:
            _identifier(self.security_class_id, "quantity.security_class_id")
        if self.provenance is not None:
            _require(isinstance(self.provenance, Provenance), "quantity.provenance: Provenance required")

    @classmethod
    def known(cls, value: str, unit: str, **kwargs: Any) -> "Quantity":
        return cls(unit=unit, status="known", value=value, **kwargs)

    @classmethod
    def unknown(cls, unit: str, **kwargs: Any) -> "Quantity":
        return cls(unit=unit, status="unknown", value=None, **kwargs)

    @property
    def decimal(self) -> Decimal | None:
        return Decimal(self.value) if self.status == "known" and self.value is not None else None

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


# ---------------------------------------------------------------------------
# Bindings, rules and requests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenerationBinding:
    """Exact input generation a state generation was compiled from."""

    input_family: str
    schema: str | None
    support: str
    generation_id: str | None = None
    artifact_sha256: str | None = None
    as_of: str | None = None

    def __post_init__(self) -> None:
        _member(self.input_family, tuple(COMPATIBLE_INPUT_SCHEMAS), "binding.input_family")
        _member(self.support, SUPPORT_STATES, "binding.support")
        compatible = COMPATIBLE_INPUT_SCHEMAS[self.input_family]
        if self.schema is None:
            _require(
                self.support in ("unavailable", "not_built"),
                f"binding[{self.input_family}]: a bound family must name its schema",
            )
        else:
            _require(
                self.schema in compatible,
                f"binding[{self.input_family}]: schema {self.schema!r} is not compatible with {list(compatible)}",
            )
        if not compatible:
            _require(self.support == "not_built", f"binding[{self.input_family}]: family has no accepted schema; support must be not_built")
        if self.support in ("supported", "partial"):
            _require(
                self.generation_id is not None or self.artifact_sha256 is not None,
                f"binding[{self.input_family}]: a supported family binds a generation id or artifact digest",
            )
        if self.generation_id is not None:
            _identifier(self.generation_id, "binding.generation_id")
        if self.artifact_sha256 is not None:
            _require(bool(_SHA256.match(self.artifact_sha256)), "binding.artifact_sha256: sha256 hex required")
        if self.as_of is not None:
            _timestamp(self.as_of, "binding.as_of")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class RuleRef:
    """One rule with its class, citation and applicability window.

    A proposed reform or an issuer assertion is never enforceable; a binding rule
    always is (masterplan §6, do-not-redo: 33-11418 is proposed, not law).
    """

    rule_id: str
    binding_class: str
    citation: str
    enforceable: bool
    effective_from: str | None = None
    effective_to: str | None = None
    required_issuer_facts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.rule_id, "rule.rule_id")
        _member(self.binding_class, RULE_CLASSES, "rule.binding_class")
        _require(isinstance(self.citation, str) and bool(self.citation), "rule.citation required")
        if self.binding_class in ("proposed_reform", "issuer_assertion"):
            _require(self.enforceable is False, f"rule[{self.rule_id}]: a {self.binding_class} is never enforceable")
        if self.binding_class == "binding_rule":
            _require(self.enforceable is True, f"rule[{self.rule_id}]: a binding rule is enforceable")
        if self.effective_from is not None:
            _date(self.effective_from, "rule.effective_from")
        if self.effective_to is not None:
            _date(self.effective_to, "rule.effective_to")
            if self.effective_from is not None:
                _require(self.effective_to >= self.effective_from, "rule: effective_to precedes effective_from")
        object.__setattr__(self, "required_issuer_facts", tuple(self.required_issuer_facts))

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class RulePack:
    """Reviewed rule-applicability pack with edition and interpretation dates."""

    rule_pack_id: str
    version: str
    source_edition: str
    jurisdiction: str
    effective_date: str
    interpretation_date: str
    rules: tuple[RuleRef, ...]
    venues: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.rule_pack_id, "rule_pack.rule_pack_id")
        for name in ("version", "source_edition", "jurisdiction"):
            _require(isinstance(getattr(self, name), str) and bool(getattr(self, name)), f"rule_pack.{name} required")
        _date(self.effective_date, "rule_pack.effective_date")
        _date(self.interpretation_date, "rule_pack.interpretation_date")
        object.__setattr__(self, "rules", tuple(self.rules))
        object.__setattr__(self, "venues", tuple(self.venues))
        object.__setattr__(self, "forms", tuple(self.forms))
        _require(len(self.rules) > 0, "rule_pack.rules: at least one rule")
        for rule in self.rules:
            _require(isinstance(rule, RuleRef), "rule_pack.rules: RuleRef required")
        _unique([rule.rule_id for rule in self.rules], "rule_pack.rules")

    @property
    def digest(self) -> str:
        return sha256_of(_plain(self))

    def as_record(self) -> dict[str, Any]:
        record = {"schema": RECORD_SCHEMAS["rule_pack"], **_plain(self), "digest": self.digest}
        return record


@dataclass(frozen=True)
class StateRequest:
    """Binds issuer/security, cutoff, view mode, exact input generations and rule pack."""

    issuer_id: str
    as_of: str
    view_mode: str
    input_generations: tuple[GenerationBinding, ...]
    rule_pack_id: str
    rule_pack_version: str
    rule_pack_digest: str
    security_class_id: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.issuer_id, "request.issuer_id")
        _timestamp(self.as_of, "request.as_of")
        _member(self.view_mode, VIEW_MODES, "request.view_mode")
        object.__setattr__(self, "input_generations", tuple(self.input_generations))
        _require(len(self.input_generations) > 0, "request.input_generations: at least one binding")
        for binding in self.input_generations:
            _require(isinstance(binding, GenerationBinding), "request.input_generations: GenerationBinding required")
        _unique([binding.input_family for binding in self.input_generations], "request.input_generations")
        _identifier(self.rule_pack_id, "request.rule_pack_id")
        _require(bool(self.rule_pack_version), "request.rule_pack_version required")
        _require(bool(_SHA256.match(self.rule_pack_digest)), "request.rule_pack_digest: sha256 hex required")
        if self.security_class_id is not None:
            _identifier(self.security_class_id, "request.security_class_id")

    @property
    def request_id(self) -> str:
        return stable_id("state-request", _plain(self))

    def binding(self, input_family: str) -> GenerationBinding | None:
        for item in self.input_generations:
            if item.input_family == input_family:
                return item
        return None

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["state_request"], "request_id": self.request_id, **_plain(self)}


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

_INPUT_FIELDS = {
    "events": "events",
    "event_edges": "edges",
    "registration_lifecycle": "lifecycles",
    "document_terms": "document_terms",
    "covenant_terms": "covenant_terms",
    "instrument_candidate_terms": "candidate_terms",
    "share_count_observations": "share_observations",
    "financials": "financials",
    "corrections": "corrections",
}


def _check_bound_records(bindings: Mapping[str, GenerationBinding], family: str, records: tuple[dict[str, Any], ...], label: str) -> None:
    if not records:
        return
    binding = bindings.get(family)
    _require(binding is not None, f"{label}: records present for {family!r} without a binding")
    assert binding is not None
    _require(binding.support in ("supported", "partial"), f"{label}: {family!r} records bound as {binding.support}")
    for index, item in enumerate(records):
        schema = item.get("schema")
        _require(schema == binding.schema, f"{label}[{index}]: record schema {schema!r} differs from binding {binding.schema!r}")
    _assert_safe_keys(records, label)


@dataclass(frozen=True)
class CapitalInputs:
    """Accepted inputs by family with their native support limits.

    Every record family present must be bound to a compatible generation, and
    every record's ``schema`` must equal that binding.  Families with no accepted
    schema (financials, corrections) may carry no records.
    """

    bindings: tuple[GenerationBinding, ...]
    events: tuple[dict[str, Any], ...] = ()
    edges: tuple[dict[str, Any], ...] = ()
    lifecycles: tuple[dict[str, Any], ...] = ()
    document_terms: tuple[dict[str, Any], ...] = ()
    covenant_terms: tuple[dict[str, Any], ...] = ()
    candidate_terms: tuple[dict[str, Any], ...] = ()
    share_observations: tuple[dict[str, Any], ...] = ()
    financials: tuple[dict[str, Any], ...] = ()
    corrections: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "bindings", tuple(self.bindings))
        for binding in self.bindings:
            _require(isinstance(binding, GenerationBinding), "inputs.bindings: GenerationBinding required")
        _unique([binding.input_family for binding in self.bindings], "inputs.bindings")
        by_family = {binding.input_family: binding for binding in self.bindings}
        for family, attr in _INPUT_FIELDS.items():
            records = _records(getattr(self, attr), f"inputs.{attr}")
            object.__setattr__(self, attr, records)
            _check_bound_records(by_family, family, records, f"inputs.{attr}")

    def binding(self, input_family: str) -> GenerationBinding | None:
        for item in self.bindings:
            if item.input_family == input_family:
                return item
        return None

    @property
    def input_digest(self) -> str:
        return sha256_of(_plain(self))

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["capital_inputs"], "input_digest": self.input_digest, **_plain(self)}


@dataclass(frozen=True)
class CandidateBundle:
    """Closed candidate-term boundary handed to instrument resolution."""

    binding: GenerationBinding
    candidate_terms: tuple[dict[str, Any], ...]
    as_of: str

    def __post_init__(self) -> None:
        _require(self.binding.input_family == "instrument_candidate_terms", "candidate_bundle: binding must be instrument_candidate_terms")
        object.__setattr__(self, "candidate_terms", _records(self.candidate_terms, "candidate_bundle.candidate_terms"))
        _check_bound_records({self.binding.input_family: self.binding}, "instrument_candidate_terms", self.candidate_terms, "candidate_bundle.candidate_terms")
        _timestamp(self.as_of, "candidate_bundle.as_of")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class ResolutionInputs:
    """Owner adjudication records for instrument identity; never fuzzy joins."""

    decisions: tuple[dict[str, Any], ...]
    decided_by: str
    as_of: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "decisions", _records(self.decisions, "resolution_inputs.decisions"))
        _assert_safe_keys(self.decisions, "resolution_inputs.decisions")
        _require(bool(self.decided_by), "resolution_inputs.decided_by required")
        _timestamp(self.as_of, "resolution_inputs.as_of")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class ShareInputs:
    """Share-count observations with their binding."""

    binding: GenerationBinding
    observations: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        _require(self.binding.input_family == "share_count_observations", "share_inputs: binding must be share_count_observations")
        object.__setattr__(self, "observations", _records(self.observations, "share_inputs.observations"))
        _check_bound_records({self.binding.input_family: self.binding}, "share_count_observations", self.observations, "share_inputs.observations")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class CorporateActionInputs:
    """Evidenced corporate actions (splits, reclassifications) with their binding."""

    binding: GenerationBinding
    actions: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "actions", _records(self.actions, "corporate_action_inputs.actions"))
        _check_bound_records({self.binding.input_family: self.binding}, self.binding.input_family, self.actions, "corporate_action_inputs.actions")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class FinancialInputs:
    """Financial facts at their supported accounting basis."""

    binding: GenerationBinding
    facts: tuple[dict[str, Any], ...]
    cash_basis: str

    def __post_init__(self) -> None:
        _require(self.binding.input_family == "financials", "financial_inputs: binding must be financials")
        _member(self.cash_basis, CASH_BASES, "financial_inputs.cash_basis")
        object.__setattr__(self, "facts", _records(self.facts, "financial_inputs.facts"))
        _check_bound_records({self.binding.input_family: self.binding}, "financials", self.facts, "financial_inputs.facts")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class CommitmentInputs:
    """Dated commitments, maturities and covenants with their binding."""

    binding: GenerationBinding
    commitments: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        _require(self.binding.input_family in ("document_terms", "covenant_terms"), "commitment_inputs: binding must be document_terms or covenant_terms")
        object.__setattr__(self, "commitments", _records(self.commitments, "commitment_inputs.commitments"))
        _check_bound_records({self.binding.input_family: self.binding}, self.binding.input_family, self.commitments, "commitment_inputs.commitments")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


# ---------------------------------------------------------------------------
# Receipts and state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalculationReceipt:
    """Exact input, rule and implementation digests behind one result."""

    input_digest: str
    rule_digest: str
    implementation_digest: str
    computed_at: str
    scenario_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("input_digest", "rule_digest", "implementation_digest"):
            _require(bool(_SHA256.match(getattr(self, name))), f"receipt.{name}: sha256 hex required")
        _timestamp(self.computed_at, "receipt.computed_at")
        if self.scenario_id is not None:
            _identifier(self.scenario_id, "receipt.scenario_id")

    @classmethod
    def build(
        cls,
        *,
        inputs: Any,
        rule_digest: str,
        implementation: str,
        computed_at: str,
        scenario_id: str | None = None,
    ) -> "CalculationReceipt":
        return cls(
            input_digest=sha256_of(_record(inputs)),
            rule_digest=rule_digest,
            implementation_digest=sha256_of({"contract": STATE_CONTRACT_VERSION, "implementation": implementation}),
            computed_at=computed_at,
            scenario_id=scenario_id,
        )

    @property
    def receipt_id(self) -> str:
        return stable_id("receipt", _plain(self))

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["calculation_receipt"], "receipt_id": self.receipt_id, **_plain(self)}


@dataclass(frozen=True)
class FamilyProvenance:
    """Per-family input binding, compiler version and native support limits."""

    family: str
    input_family: str
    input_schema: str | None
    support: str
    compiler_version: str | None = None
    generation_id: str | None = None
    artifact_sha256: str | None = None
    support_limits: tuple[str, ...] = ()
    as_of: str | None = None
    available_at: str | None = None

    def __post_init__(self) -> None:
        _member(self.family, STATE_FAMILIES, "family_provenance.family")
        _member(self.input_family, tuple(COMPATIBLE_INPUT_SCHEMAS), "family_provenance.input_family")
        _member(self.support, SUPPORT_STATES, "family_provenance.support")
        compatible = COMPATIBLE_INPUT_SCHEMAS[self.input_family]
        if self.input_schema is None:
            _require(self.support in ("unavailable", "not_built"), f"family_provenance[{self.family}]: supported families name their input schema")
        else:
            _require(self.input_schema in compatible, f"family_provenance[{self.family}]: schema {self.input_schema!r} incompatible with {list(compatible)}")
        object.__setattr__(self, "support_limits", tuple(self.support_limits))
        if self.support == "partial":
            _require(len(self.support_limits) > 0, f"family_provenance[{self.family}]: partial support names its limits")
        if self.support in ("supported", "partial"):
            _require(bool(self.compiler_version), f"family_provenance[{self.family}]: compiler_version required")
            _require(self.generation_id is not None or self.artifact_sha256 is not None, f"family_provenance[{self.family}]: generation id or artifact digest required")
        if self.generation_id is not None:
            _identifier(self.generation_id, "family_provenance.generation_id")
        if self.artifact_sha256 is not None:
            _require(bool(_SHA256.match(self.artifact_sha256)), "family_provenance.artifact_sha256: sha256 hex required")
        if self.as_of is not None:
            _timestamp(self.as_of, "family_provenance.as_of")
        if self.available_at is not None:
            _timestamp(self.available_at, "family_provenance.available_at")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class FamilyState:
    """One twin family: provenance, its records and what it cannot answer."""

    family: str
    provenance: FamilyProvenance
    records: tuple[dict[str, Any], ...] = ()
    unavailable: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _member(self.family, STATE_FAMILIES, "family_state.family")
        _require(isinstance(self.provenance, FamilyProvenance), "family_state.provenance: FamilyProvenance required")
        _require(self.provenance.family == self.family, f"family_state[{self.family}]: provenance names {self.provenance.family!r}")
        object.__setattr__(self, "records", _records(self.records, f"family_state[{self.family}].records"))
        object.__setattr__(self, "unavailable", tuple(self.unavailable))
        _unique(self.unavailable, f"family_state[{self.family}].unavailable")
        _assert_safe_keys(self.records, f"family_state[{self.family}].records")
        if self.provenance.support in ("unavailable", "not_built"):
            _require(not self.records, f"family_state[{self.family}]: an unavailable family carries no records")
            _require(len(self.unavailable) > 0, f"family_state[{self.family}]: an unavailable family names what is unavailable")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class CapabilityProof:
    """Proof that a previously unavailable capability is now supported."""

    capability: str
    generation_id: str
    test_reference: str
    proven_at: str

    def __post_init__(self) -> None:
        _require(bool(self.capability), "capability_proof.capability required")
        _identifier(self.generation_id, "capability_proof.generation_id")
        _require(self.test_reference.startswith("tests/test_capital_structure_"), "capability_proof.test_reference: a tests/test_capital_structure_* reference is required")
        _timestamp(self.proven_at, "capability_proof.proven_at")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class CapitalState:
    """Derived owner artifact: supported families with cutoff, generation and authority.

    Every projection-era unavailable capability stays unavailable unless a
    ``CapabilityProof`` names the generation and test that proved it (A06).
    """

    request: StateRequest
    generated_at: str
    families: tuple[FamilyState, ...]
    receipt: CalculationReceipt
    unavailable: tuple[str, ...] = INHERITED_UNAVAILABLE_CAPABILITIES
    capabilities_proven: tuple[CapabilityProof, ...] = ()
    projection_generation_id: str | None = None

    def __post_init__(self) -> None:
        _require(isinstance(self.request, StateRequest), "state.request: StateRequest required")
        _timestamp(self.generated_at, "state.generated_at")
        object.__setattr__(self, "families", tuple(self.families))
        _require(len(self.families) > 0, "state.families: at least one family")
        for item in self.families:
            _require(isinstance(item, FamilyState), "state.families: FamilyState required")
        _unique([item.family for item in self.families], "state.families")
        _require(isinstance(self.receipt, CalculationReceipt), "state.receipt: CalculationReceipt required")
        _require(self.receipt.scenario_id is None, "state.receipt: a state generation is not scenario-bound")
        object.__setattr__(self, "unavailable", tuple(sorted(set(self.unavailable))))
        object.__setattr__(self, "capabilities_proven", tuple(self.capabilities_proven))
        proven = {}
        for proof in self.capabilities_proven:
            _require(isinstance(proof, CapabilityProof), "state.capabilities_proven: CapabilityProof required")
            proven[proof.capability] = proof
        _unique(list(proven), "state.capabilities_proven")
        for capability in INHERITED_UNAVAILABLE_CAPABILITIES:
            _require(
                capability in self.unavailable or capability in proven,
                f"state.unavailable: {capability!r} was removed without a capability proof",
            )
            _require(
                not (capability in self.unavailable and capability in proven),
                f"state.unavailable: {capability!r} is both unavailable and proven",
            )
        if self.projection_generation_id is not None:
            _identifier(self.projection_generation_id, "state.projection_generation_id")
            binding = self.request.binding("event_projection")
            _require(binding is not None and binding.generation_id == self.projection_generation_id, "state.projection_generation_id must equal the request's event_projection binding")

    @property
    def state_id(self) -> str:
        return stable_id("state", {"request": self.request.as_record(), "receipt": self.receipt.as_record(), "families": _record(self.families)})

    def family(self, name: str) -> FamilyState | None:
        for item in self.families:
            if item.family == name:
                return item
        return None

    def as_record(self) -> dict[str, Any]:
        return {
            "schema": STATE_SCHEMA,
            "contract_version": STATE_CONTRACT_VERSION,
            "state_id": self.state_id,
            "request": self.request.as_record(),
            "as_of": self.request.as_of,
            "generated_at": self.generated_at,
            "projection_generation_id": self.projection_generation_id,
            "compatibility": dict(PROJECTION_COMPATIBILITY),
            "families": _record(self.families),
            "unavailable": list(self.unavailable),
            "capabilities_proven": _record(self.capabilities_proven),
            "receipt": self.receipt.as_record(),
            "authority": dict(AUTHORITY),
        }


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceAssumption:
    """Fixed price or dated path; price-to-share conversion is a scenario input."""

    kind: str
    currency: str = "USD"
    fixed_price: str | None = None
    path: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _member(self.kind, PRICE_KINDS, "price.kind")
        _require(bool(re.match(r"^[A-Z]{3}$", self.currency)), "price.currency: ISO-4217 code required")
        object.__setattr__(self, "path", tuple(tuple(point) for point in self.path))
        if self.kind == "fixed":
            _decimal(self.fixed_price, "price.fixed_price")
            _require(not self.path, "price.path must be empty for a fixed price")
        else:
            _require(self.fixed_price is None, "price.fixed_price must be null for a path")
            _require(len(self.path) > 0, "price.path: at least one dated point")
            previous = None
            for point in self.path:
                _require(len(point) == 2, "price.path: (date, price) pairs required")
                _date(point[0], "price.path.date")
                _decimal(point[1], "price.path.price")
                _require(previous is None or point[0] > previous, "price.path: dates must strictly ascend")
                previous = point[0]

    def as_record(self) -> dict[str, Any]:
        return {"kind": self.kind, "currency": self.currency, "fixed_price": self.fixed_price, "path": [list(point) for point in self.path]}


@dataclass(frozen=True)
class ActionSelection:
    """One selected contractual action on a route under the scenario."""

    route_id: str
    action: str
    settlement: str
    quantity: Quantity | None = None
    conditions_assumed_met: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.route_id, "action.route_id")
        _member(self.action, ROUTE_KINDS, "action.action")
        _member(self.settlement, SETTLEMENTS, "action.settlement")
        if self.quantity is not None:
            _require(isinstance(self.quantity, Quantity), "action.quantity: Quantity required")
        object.__setattr__(self, "conditions_assumed_met", tuple(self.conditions_assumed_met))

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class UnknownResolution:
    """An explicitly supplied resolution of an unknown, with its rationale."""

    unknown_id: str
    assumed: Quantity
    rationale: str

    def __post_init__(self) -> None:
        _identifier(self.unknown_id, "unknown_resolution.unknown_id")
        _require(isinstance(self.assumed, Quantity), "unknown_resolution.assumed: Quantity required")
        _require(self.assumed.status == "known", "unknown_resolution.assumed: a resolution supplies a known value")
        _require(bool(self.rationale), "unknown_resolution.rationale required")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class FinancingScenario:
    """Time horizon, price assumption, selected actions, cash/fee assumptions and
    explicit unknown resolutions.  ``scenario_id`` digests every assumption:
    changing one creates a different scenario, never a mutation of facts.
    """

    view: str
    as_of: str
    horizon_start: str
    horizon_end: str
    price: PriceAssumption
    actions: tuple[ActionSelection, ...] = ()
    fee_rate: str | None = None
    discount_rate: str | None = None
    other_assumptions: tuple[tuple[str, str], ...] = ()
    unknown_resolutions: tuple[UnknownResolution, ...] = ()
    label: str | None = None

    def __post_init__(self) -> None:
        _member(self.view, SCENARIO_VIEWS, "scenario.view")
        _timestamp(self.as_of, "scenario.as_of")
        _date(self.horizon_start, "scenario.horizon_start")
        _date(self.horizon_end, "scenario.horizon_end")
        _require(self.horizon_end >= self.horizon_start, "scenario: horizon_end precedes horizon_start")
        _require(isinstance(self.price, PriceAssumption), "scenario.price: PriceAssumption required")
        object.__setattr__(self, "actions", tuple(self.actions))
        for action in self.actions:
            _require(isinstance(action, ActionSelection), "scenario.actions: ActionSelection required")
        _unique([action.route_id for action in self.actions], "scenario.actions")
        for name in ("fee_rate", "discount_rate"):
            value = getattr(self, name)
            if value is not None:
                _decimal(value, f"scenario.{name}")
                _require(Decimal(value) <= 1, f"scenario.{name}: a rate is at most 1")
        object.__setattr__(self, "other_assumptions", tuple((str(key), str(value)) for key, value in self.other_assumptions))
        _unique([key for key, _ in self.other_assumptions], "scenario.other_assumptions")
        object.__setattr__(self, "unknown_resolutions", tuple(self.unknown_resolutions))
        for item in self.unknown_resolutions:
            _require(isinstance(item, UnknownResolution), "scenario.unknown_resolutions: UnknownResolution required")
        _unique([item.unknown_id for item in self.unknown_resolutions], "scenario.unknown_resolutions")

    @property
    def assumptions(self) -> dict[str, Any]:
        body = _plain(self)
        body.pop("label", None)
        return body

    @property
    def scenario_id(self) -> str:
        return stable_id("scenario", self.assumptions)

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["financing_scenario"], "scenario_id": self.scenario_id, **_plain(self)}


# ---------------------------------------------------------------------------
# Capacity
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Constraint:
    """A shared or route-local limit on dollars, shares, votes, ownership, classes,
    programme balances, reserved shares, covenant headroom or time."""

    constraint_id: str
    kind: str
    bound: Quantity
    status: str
    stock_or_flow: str
    shared_by: tuple[str, ...] = ()
    applicability: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()
    window_start: str | None = None
    window_end: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.constraint_id, "constraint.constraint_id")
        _member(self.kind, CONSTRAINT_KINDS, "constraint.kind")
        _require(isinstance(self.bound, Quantity), "constraint.bound: Quantity required")
        _member(self.status, CONSTRAINT_STATUSES, "constraint.status")
        _member(self.stock_or_flow, STOCK_OR_FLOW, "constraint.stock_or_flow")
        object.__setattr__(self, "shared_by", tuple(self.shared_by))
        _unique(self.shared_by, f"constraint[{self.constraint_id}].shared_by")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if self.bound.status == "known":
            _require(len(self.evidence) > 0, f"constraint[{self.constraint_id}]: a known bound needs evidence")
            _require(self.applicability is not None, f"constraint[{self.constraint_id}]: a known bound needs an applicability predicate")
        if self.status in ("binding", "slack"):
            _require(self.bound.status == "known", f"constraint[{self.constraint_id}]: {self.status} requires a known bound")
        if self.kind == "time_window":
            _require(self.window_start is not None and self.window_end is not None, "constraint: a time window names both ends")
        if self.window_start is not None:
            _date(self.window_start, "constraint.window_start")
        if self.window_end is not None:
            _date(self.window_end, "constraint.window_end")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class RouteBound:
    """Conditional per-route limit with the constraints it consumes."""

    route_id: str
    route_kind: str
    limit: Quantity
    status: str
    conditions: tuple[str, ...] = ()
    consumes: tuple[str, ...] = ()
    applicability: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.route_id, "route.route_id")
        _member(self.route_kind, ROUTE_KINDS, "route.route_kind")
        _require(isinstance(self.limit, Quantity), "route.limit: Quantity required")
        _member(self.status, ROUTE_STATUSES, "route.status")
        object.__setattr__(self, "conditions", tuple(self.conditions))
        object.__setattr__(self, "consumes", tuple(self.consumes))
        _unique(self.consumes, f"route[{self.route_id}].consumes")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if self.limit.status == "known":
            _require(len(self.evidence) > 0, f"route[{self.route_id}]: a numeric limit without evidence is rejected")
            _require(self.applicability is not None, f"route[{self.route_id}]: a numeric limit without an applicability predicate is rejected")
        if self.status == "conditional":
            _require(len(self.conditions) > 0, f"route[{self.route_id}]: a conditional route names its conditions")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class Unknown:
    """What is unknown and which future fact would resolve it."""

    unknown_id: str
    description: str
    resolving_fact: str
    affects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.unknown_id, "unknown.unknown_id")
        _require(bool(self.description), "unknown.description required")
        _require(bool(self.resolving_fact), "unknown.resolving_fact required")
        object.__setattr__(self, "affects", tuple(self.affects))

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class WitnessAllocation:
    route_id: str
    quantity: Quantity

    def __post_init__(self) -> None:
        _identifier(self.route_id, "witness.route_id")
        _require(isinstance(self.quantity, Quantity) and self.quantity.status == "known", "witness.quantity: a known quantity is required")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


def _sum_known(quantities: Sequence[Quantity], unit: str) -> Decimal | None:
    total = Decimal(0)
    for quantity in quantities:
        if quantity.unit != unit:
            continue
        if quantity.status != "known" or quantity.decimal is None:
            return None
        total += quantity.decimal
    return total


@dataclass(frozen=True)
class CapacityEnvelope:
    """Per-route conditional bounds, shared pools, binding and unknown constraints,
    mutually exclusive choices, an evidence-qualified aggregate bound and a
    jointly feasible witness where evidence suffices.

    Invariants (masterplan §5, acceptance rows A20/A21): shared-pool maxima are
    never summed, an aggregate bound is known only when every eligible route and
    every shared pool it depends on is known and the aggregate respects each
    pool, and a witness never over-allocates a route, a pool or an exclusive
    group.  An unknown aggregate must name what is unknown.
    """

    state_id: str
    scenario_id: str
    rule_pack_digest: str
    routes: tuple[RouteBound, ...]
    aggregate_bound: Quantity
    receipt: CalculationReceipt
    shared_pools: tuple[Constraint, ...] = ()
    binding_constraints: tuple[str, ...] = ()
    unknown_constraints: tuple[str, ...] = ()
    mutually_exclusive: tuple[tuple[str, ...], ...] = ()
    feasible_witness: tuple[WitnessAllocation, ...] | None = None
    blockers: tuple[str, ...] = ()
    unknowns: tuple[Unknown, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.state_id, "capacity.state_id")
        _identifier(self.scenario_id, "capacity.scenario_id")
        _require(bool(_SHA256.match(self.rule_pack_digest)), "capacity.rule_pack_digest: sha256 hex required")
        object.__setattr__(self, "routes", tuple(self.routes))
        for route in self.routes:
            _require(isinstance(route, RouteBound), "capacity.routes: RouteBound required")
        route_ids = [route.route_id for route in self.routes]
        _unique(route_ids, "capacity.routes")
        object.__setattr__(self, "shared_pools", tuple(self.shared_pools))
        for pool in self.shared_pools:
            _require(isinstance(pool, Constraint), "capacity.shared_pools: Constraint required")
        pool_ids = [pool.constraint_id for pool in self.shared_pools]
        _unique(pool_ids, "capacity.shared_pools")
        pools = {pool.constraint_id: pool for pool in self.shared_pools}
        routes = {route.route_id: route for route in self.routes}
        for route in self.routes:
            for constraint_id in route.consumes:
                _require(constraint_id in pools, f"route[{route.route_id}] consumes unknown constraint {constraint_id!r}")
        for pool in self.shared_pools:
            for route_id in pool.shared_by:
                _require(route_id in routes, f"pool[{pool.constraint_id}] shared by unknown route {route_id!r}")
        object.__setattr__(self, "binding_constraints", tuple(self.binding_constraints))
        object.__setattr__(self, "unknown_constraints", tuple(self.unknown_constraints))
        for constraint_id in (*self.binding_constraints, *self.unknown_constraints):
            _require(constraint_id in pools, f"capacity: constraint {constraint_id!r} is not a declared pool")
        for constraint_id in self.unknown_constraints:
            _require(pools[constraint_id].bound.status != "known", f"capacity: {constraint_id!r} listed unknown but carries a known bound")
        object.__setattr__(self, "mutually_exclusive", tuple(tuple(group) for group in self.mutually_exclusive))
        for group in self.mutually_exclusive:
            _require(len(group) >= 2, "capacity.mutually_exclusive: a group names at least two routes")
            for route_id in group:
                _require(route_id in routes, f"capacity.mutually_exclusive names unknown route {route_id!r}")
        _require(isinstance(self.aggregate_bound, Quantity), "capacity.aggregate_bound: Quantity required")
        _require(isinstance(self.receipt, CalculationReceipt), "capacity.receipt: CalculationReceipt required")
        _require(self.receipt.scenario_id == self.scenario_id, "capacity.receipt: receipt scenario differs from envelope scenario")
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        for item in self.unknowns:
            _require(isinstance(item, Unknown), "capacity.unknowns: Unknown required")
        _unique([item.unknown_id for item in self.unknowns], "capacity.unknowns")
        self._check_aggregate(routes, pools)
        self._check_witness(routes, pools)

    def _consumers(self, routes: Mapping[str, RouteBound], pool: Constraint) -> list[RouteBound]:
        return [route for route in routes.values() if pool.constraint_id in route.consumes or route.route_id in pool.shared_by]

    def _check_aggregate(self, routes: Mapping[str, RouteBound], pools: Mapping[str, Constraint]) -> None:
        aggregate = self.aggregate_bound
        if aggregate.status != "known":
            _require(
                bool(self.unknown_constraints) or bool(self.unknowns) or bool(self.blockers),
                "capacity.aggregate_bound: an unknown aggregate must name an unknown constraint, unknown or blocker",
            )
            return
        unit = aggregate.unit
        active = [route for route in routes.values() if route.status in ("eligible", "conditional")]
        _require(len(active) > 0, "capacity.aggregate_bound: a known aggregate needs at least one eligible or conditional route")
        for route in active:
            _require(route.limit.unit == unit, f"capacity.aggregate_bound: route {route.route_id!r} is in {route.limit.unit}, aggregate in {unit}")
            _require(route.limit.status == "known", f"capacity.aggregate_bound: route {route.route_id!r} has no known limit, so the aggregate cannot be known")
        total = aggregate.decimal
        assert total is not None
        route_sum = _sum_known([route.limit for route in active], unit)
        assert route_sum is not None
        _require(total <= route_sum, "capacity.aggregate_bound exceeds the sum of route limits")
        for pool in pools.values():
            consumers = [route for route in self._consumers(routes, pool) if route.status in ("eligible", "conditional")]
            if len(consumers) < 2 or pool.bound.unit != unit:
                continue
            _require(pool.bound.status == "known", f"capacity.aggregate_bound: shared pool {pool.constraint_id!r} is unknown, so the aggregate cannot be known")
            outside = _sum_known([route.limit for route in active if route not in consumers], unit)
            assert outside is not None and pool.bound.decimal is not None
            _require(
                total <= pool.bound.decimal + outside,
                f"capacity.aggregate_bound sums shared pool {pool.constraint_id!r} maxima",
            )

    def _check_witness(self, routes: Mapping[str, RouteBound], pools: Mapping[str, Constraint]) -> None:
        if self.feasible_witness is None:
            return
        object.__setattr__(self, "feasible_witness", tuple(self.feasible_witness))
        witness = {}
        for allocation in self.feasible_witness:
            _require(isinstance(allocation, WitnessAllocation), "capacity.feasible_witness: WitnessAllocation required")
            _require(allocation.route_id in routes, f"capacity.feasible_witness names unknown route {allocation.route_id!r}")
            witness[allocation.route_id] = allocation.quantity
        _unique(list(witness), "capacity.feasible_witness")
        for route_id, quantity in witness.items():
            route = routes[route_id]
            _require(route.status in ("eligible", "conditional"), f"witness allocates to {route_id!r}, which is {route.status}")
            if route.limit.status == "known" and route.limit.unit == quantity.unit:
                assert route.limit.decimal is not None and quantity.decimal is not None
                _require(quantity.decimal <= route.limit.decimal, f"witness over-allocates route {route_id!r}")
        for pool in pools.values():
            if pool.bound.status != "known":
                continue
            consumed = [witness[route.route_id] for route in self._consumers(routes, pool) if route.route_id in witness]
            used = _sum_known(consumed, pool.bound.unit)
            if used is not None and pool.bound.decimal is not None:
                _require(used <= pool.bound.decimal, f"witness over-allocates shared pool {pool.constraint_id!r}")
        for group in self.mutually_exclusive:
            positive = [route_id for route_id in group if route_id in witness and witness[route_id].decimal and witness[route_id].decimal > 0]
            _require(len(positive) <= 1, f"witness allocates to mutually exclusive routes {positive}")
        if self.aggregate_bound.status == "known":
            used = _sum_known(list(witness.values()), self.aggregate_bound.unit)
            if used is not None and self.aggregate_bound.decimal is not None:
                _require(used <= self.aggregate_bound.decimal, "witness exceeds the aggregate bound")

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["capacity_envelope"], **_plain(self)}


# ---------------------------------------------------------------------------
# Supply
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CashEffect:
    """Gross and net cash consequence of one route; resale is never issuer funding."""

    route_id: str
    kind: str
    gross: Quantity
    net: Quantity

    def __post_init__(self) -> None:
        _identifier(self.route_id, "cash_effect.route_id")
        _member(self.kind, CASH_EFFECT_KINDS, "cash_effect.kind")
        for name in ("gross", "net"):
            quantity = getattr(self, name)
            _require(isinstance(quantity, Quantity) and quantity.unit == "usd", f"cash_effect.{name}: a usd Quantity is required")
        if self.gross.status == "known" and self.net.status == "known":
            assert self.gross.decimal is not None and self.net.decimal is not None
            _require(self.net.decimal <= self.gross.decimal, "cash_effect: net exceeds gross")
        if self.kind == "no_cash":
            for name in ("gross", "net"):
                quantity = getattr(self, name)
                _require(quantity.status == "not_applicable" or (quantity.status == "known" and quantity.decimal == 0), f"cash_effect.{name}: a no_cash route carries no proceeds")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class SupplyEnvelope:
    """Existing, incremental, as-converted and resalable shares plus cash effects.

    The components are never summed: there is no total and no fully-diluted
    figure, by construction (masterplan §4).
    """

    state_id: str
    scenario_id: str
    existing_outstanding: Quantity
    incremental_issuance: Quantity
    as_converted_claims: Quantity
    resalable_existing: Quantity
    receipt: CalculationReceipt
    cash_effects: tuple[CashEffect, ...] = ()
    double_count_guards: tuple[str, ...] = ()
    unknowns: tuple[Unknown, ...] = ()

    _BASES = {
        "existing_outstanding": "issued_and_outstanding",
        "incremental_issuance": "scenario_incremental_issuance",
        "as_converted_claims": "assumed_as_converted",
        "resalable_existing": "potentially_resalable_existing",
    }

    def __post_init__(self) -> None:
        _identifier(self.state_id, "supply.state_id")
        _identifier(self.scenario_id, "supply.scenario_id")
        for name, basis in self._BASES.items():
            quantity = getattr(self, name)
            _require(isinstance(quantity, Quantity), f"supply.{name}: Quantity required")
            _require(quantity.unit == "shares", f"supply.{name}: a share quantity is required")
            _require(quantity.share_basis == basis, f"supply.{name}: basis must be {basis!r}, got {quantity.share_basis!r}")
        _require(isinstance(self.receipt, CalculationReceipt), "supply.receipt: CalculationReceipt required")
        _require(self.receipt.scenario_id == self.scenario_id, "supply.receipt: receipt scenario differs from envelope scenario")
        object.__setattr__(self, "cash_effects", tuple(self.cash_effects))
        for item in self.cash_effects:
            _require(isinstance(item, CashEffect), "supply.cash_effects: CashEffect required")
        _unique([item.route_id for item in self.cash_effects], "supply.cash_effects")
        object.__setattr__(self, "double_count_guards", tuple(self.double_count_guards))
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        for item in self.unknowns:
            _require(isinstance(item, Unknown), "supply.unknowns: Unknown required")

    def components(self) -> dict[str, Quantity]:
        return {name: getattr(self, name) for name in self._BASES}

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["supply_envelope"], **_plain(self)}


# ---------------------------------------------------------------------------
# Funding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Flow:
    """A dated source or use of cash with its certainty class.

    A conditional flow carries its condition and never enters a balance
    identity: an undrawn commitment with conditions is not money available now.
    """

    flow_id: str
    kind: str
    label: str
    amount: Quantity
    certainty: str
    dated: str | None = None
    condition: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.flow_id, "flow.flow_id")
        _member(self.kind, FLOW_KINDS, "flow.kind")
        _require(bool(self.label), "flow.label required")
        _require(isinstance(self.amount, Quantity) and self.amount.unit == "usd", "flow.amount: a usd Quantity is required")
        _member(self.certainty, FLOW_CERTAINTIES, "flow.certainty")
        if self.certainty == "contractual_dated":
            _require(self.dated is not None, f"flow[{self.flow_id}]: a contractual flow is dated")
        if self.certainty == "conditional":
            _require(bool(self.condition), f"flow[{self.flow_id}]: a conditional flow names its condition")
        if self.dated is not None:
            _date(self.dated, "flow.dated")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class FundingPeriod:
    """Dated opening balance, sources, uses, closing balance, minimum liquidity and gap."""

    period_start: str
    period_end: str
    opening_balance: Quantity
    closing_balance: Quantity
    minimum_liquidity: Quantity
    gap: Quantity
    sources: tuple[Flow, ...] = ()
    uses: tuple[Flow, ...] = ()

    def __post_init__(self) -> None:
        _date(self.period_start, "period.period_start")
        _date(self.period_end, "period.period_end")
        _require(self.period_end > self.period_start, "period: period_end must follow period_start")
        for name in ("opening_balance", "closing_balance", "minimum_liquidity", "gap"):
            quantity = getattr(self, name)
            _require(isinstance(quantity, Quantity) and quantity.unit == "usd", f"period.{name}: a usd Quantity is required")
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "uses", tuple(self.uses))
        for flow in (*self.sources, *self.uses):
            _require(isinstance(flow, Flow), "period: Flow required")
        for flow in self.sources:
            _require(flow.kind == "source", f"period.sources: {flow.flow_id!r} is a {flow.kind}")
        for flow in self.uses:
            _require(flow.kind == "use", f"period.uses: {flow.flow_id!r} is a {flow.kind}")
        _unique([flow.flow_id for flow in (*self.sources, *self.uses)], "period.flows")
        if self.closing_balance.status == "known":
            _require(self.opening_balance.status == "known", "period: a known closing balance needs a known opening balance")
            counted_sources = _sum_known([flow.amount for flow in self.sources if flow.certainty != "conditional"], "usd")
            counted_uses = _sum_known([flow.amount for flow in self.uses if flow.certainty != "conditional"], "usd")
            _require(counted_sources is not None and counted_uses is not None, "period: a known closing balance needs known non-conditional flows")
            assert self.opening_balance.decimal is not None and self.closing_balance.decimal is not None
            expected = self.opening_balance.decimal + counted_sources - counted_uses
            _require(self.closing_balance.decimal == expected, f"period: closing balance {self.closing_balance.value} is not opening plus non-conditional flows ({expected})")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class Assumption:
    key: str
    value: str
    rationale: str

    def __post_init__(self) -> None:
        _require(bool(self.key) and bool(self.value) and bool(self.rationale), "assumption: key, value and rationale required")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


REQUIRED_FUNDING_ASSUMPTIONS = ("burn_basis", "working_capital_basis", "seasonality_basis")


@dataclass(frozen=True)
class FundingSchedule:
    """Time-indexed sources and uses at a named cash basis with frozen assumptions.

    Periods chain (closing of one is opening of the next when both are known),
    the burn/working-capital/seasonality assumptions are explicit, and a
    negative or unknown burn never implies an infinite horizon.
    """

    state_id: str
    scenario_id: str
    cash_basis: str
    receipt: CalculationReceipt
    periods: tuple[FundingPeriod, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    unknowns: tuple[Unknown, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.state_id, "funding.state_id")
        _identifier(self.scenario_id, "funding.scenario_id")
        _member(self.cash_basis, CASH_BASES, "funding.cash_basis")
        _require(isinstance(self.receipt, CalculationReceipt), "funding.receipt: CalculationReceipt required")
        _require(self.receipt.scenario_id == self.scenario_id, "funding.receipt: receipt scenario differs from schedule scenario")
        object.__setattr__(self, "periods", tuple(self.periods))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        for item in self.assumptions:
            _require(isinstance(item, Assumption), "funding.assumptions: Assumption required")
        _unique([item.key for item in self.assumptions], "funding.assumptions")
        previous: FundingPeriod | None = None
        for period in self.periods:
            _require(isinstance(period, FundingPeriod), "funding.periods: FundingPeriod required")
            if previous is not None:
                _require(period.period_start >= previous.period_end, "funding.periods must ascend without overlap")
                if previous.closing_balance.status == "known" and period.opening_balance.status == "known":
                    _require(previous.closing_balance.value == period.opening_balance.value, "funding.periods: opening balance differs from the prior closing balance")
            previous = period
        if self.periods:
            keys = {item.key for item in self.assumptions}
            missing = [key for key in REQUIRED_FUNDING_ASSUMPTIONS if key not in keys]
            _require(not missing, f"funding.assumptions: a schedule freezes {missing}")
        for item in self.unknowns:
            _require(isinstance(item, Unknown), "funding.unknowns: Unknown required")

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["funding_schedule"], **_plain(self)}


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Resolution:
    """Owner adjudication of an instrument identity; ``unresolved`` is first-class."""

    method: str
    decision_id: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()
    decided_at: str | None = None

    def __post_init__(self) -> None:
        _member(self.method, RESOLUTION_METHODS, "resolution.method")
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if self.method != "unresolved":
            _require(self.decision_id is not None, "resolution: a resolved identity carries its decision id")
            _identifier(self.decision_id, "resolution.decision_id")
            _require(len(self.evidence) > 0, "resolution: a resolved identity carries evidence")
            _require(self.decided_at is not None, "resolution: a resolved identity is dated")
        if self.decided_at is not None:
            _timestamp(self.decided_at, "resolution.decided_at")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class Instrument:
    """A supported series/tranche identity grounded in candidate terms."""

    instrument_id: str
    security_class_id: str
    kind: str
    status: str
    candidate_term_ids: tuple[str, ...]
    resolution: Resolution
    amendments: tuple[str, ...] = ()
    outstanding: Quantity | None = None
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        _identifier(self.instrument_id, "instrument.instrument_id")
        _identifier(self.security_class_id, "instrument.security_class_id")
        _member(self.kind, INSTRUMENT_KINDS, "instrument.kind")
        _member(self.status, INSTRUMENT_STATUSES, "instrument.status")
        object.__setattr__(self, "candidate_term_ids", tuple(self.candidate_term_ids))
        _require(len(self.candidate_term_ids) > 0, f"instrument[{self.instrument_id}]: grounded in at least one candidate term")
        _unique(self.candidate_term_ids, f"instrument[{self.instrument_id}].candidate_term_ids")
        _require(isinstance(self.resolution, Resolution), "instrument.resolution: Resolution required")
        unresolved = self.resolution.method == "unresolved"
        _require((self.status == "unresolved_candidate") == unresolved, f"instrument[{self.instrument_id}]: status and resolution disagree")
        object.__setattr__(self, "amendments", tuple(self.amendments))
        if self.outstanding is not None:
            _require(isinstance(self.outstanding, Quantity), "instrument.outstanding: Quantity required")
            _require(self.outstanding.unit in ("shares", "usd"), "instrument.outstanding: shares or usd")
            if unresolved:
                _require(self.outstanding.status != "known", f"instrument[{self.instrument_id}]: an unresolved candidate has no known outstanding amount")
        if self.provenance is not None:
            _require(isinstance(self.provenance, Provenance), "instrument.provenance: Provenance required")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class InstrumentSet:
    """Resolved instruments plus the candidates that stay unresolved."""

    issuer_id: str
    as_of: str
    instruments: tuple[Instrument, ...]
    provenance: FamilyProvenance
    receipt: CalculationReceipt
    unresolved_candidate_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.issuer_id, "instrument_set.issuer_id")
        _timestamp(self.as_of, "instrument_set.as_of")
        object.__setattr__(self, "instruments", tuple(self.instruments))
        for item in self.instruments:
            _require(isinstance(item, Instrument), "instrument_set.instruments: Instrument required")
        _unique([item.instrument_id for item in self.instruments], "instrument_set.instruments")
        _require(isinstance(self.provenance, FamilyProvenance) and self.provenance.family == "instruments", "instrument_set.provenance: the instruments family is required")
        _require(isinstance(self.receipt, CalculationReceipt), "instrument_set.receipt: CalculationReceipt required")
        object.__setattr__(self, "unresolved_candidate_ids", tuple(self.unresolved_candidate_ids))
        _unique(self.unresolved_candidate_ids, "instrument_set.unresolved_candidate_ids")

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["instrument_set"], **_plain(self)}


# ---------------------------------------------------------------------------
# Share basis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShareObservationRef:
    """One candidate share figure with its basis, date and source."""

    observation_id: str
    basis: str
    as_of_date: str
    security_class_id: str
    value: str | None = None
    source: Provenance | None = None

    def __post_init__(self) -> None:
        _identifier(self.observation_id, "share_observation.observation_id")
        _member(self.basis, SHARE_BASES, "share_observation.basis")
        _date(self.as_of_date, "share_observation.as_of_date")
        _identifier(self.security_class_id, "share_observation.security_class_id")
        if self.value is not None:
            _decimal(self.value, "share_observation.value")
        if self.source is not None:
            _require(isinstance(self.source, Provenance), "share_observation.source: Provenance required")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class CorporateActionBasis:
    """Split basis; a reverse split needs an effective date and contract-adjustment evidence."""

    kind: str = "none"
    ratio: str | None = None
    effective_date: str | None = None
    contract_adjustment_evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        _member(self.kind, CORPORATE_ACTION_KINDS, "corporate_action.kind")
        object.__setattr__(self, "contract_adjustment_evidence", tuple(self.contract_adjustment_evidence))
        if self.kind == "none":
            _require(self.ratio is None and self.effective_date is None and not self.contract_adjustment_evidence, "corporate_action: none carries no ratio, date or evidence")
        else:
            _decimal(self.ratio, "corporate_action.ratio")
            _require(Decimal(str(self.ratio)) > 0, "corporate_action.ratio must be positive")
            _date(self.effective_date, "corporate_action.effective_date")
            _require(len(self.contract_adjustment_evidence) > 0, "corporate_action: a split needs contract-adjustment evidence, never a universal factor")

    def as_record(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class ShareBasisResult:
    """Selected comparable share basis, or an explicit conflict/refusal.

    A selection is one of the candidate observations on the issued-and-
    outstanding basis; a conflict shows the candidates and selects nothing.
    The largest or newest-looking number is never chosen silently.
    """

    issuer_id: str
    security_class_id: str
    as_of: str
    status: str
    provenance: FamilyProvenance
    receipt: CalculationReceipt
    selected: Quantity | None = None
    candidates: tuple[ShareObservationRef, ...] = ()
    conflicts: tuple[str, ...] = ()
    corporate_action: CorporateActionBasis = field(default_factory=CorporateActionBasis)

    def __post_init__(self) -> None:
        _identifier(self.issuer_id, "share_basis.issuer_id")
        _identifier(self.security_class_id, "share_basis.security_class_id")
        _timestamp(self.as_of, "share_basis.as_of")
        _member(self.status, SHARE_BASIS_STATUSES, "share_basis.status")
        _require(isinstance(self.provenance, FamilyProvenance) and self.provenance.family == "share_basis", "share_basis.provenance: the share_basis family is required")
        _require(isinstance(self.receipt, CalculationReceipt), "share_basis.receipt: CalculationReceipt required")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        for item in self.candidates:
            _require(isinstance(item, ShareObservationRef), "share_basis.candidates: ShareObservationRef required")
        _unique([item.observation_id for item in self.candidates], "share_basis.candidates")
        object.__setattr__(self, "conflicts", tuple(self.conflicts))
        _require(isinstance(self.corporate_action, CorporateActionBasis), "share_basis.corporate_action: CorporateActionBasis required")
        if self.status == "selected":
            _require(isinstance(self.selected, Quantity) and self.selected.status == "known", "share_basis: selected requires a known quantity")
            assert self.selected is not None
            _require(self.selected.unit == "shares" and self.selected.share_basis == "issued_and_outstanding", "share_basis: the selected quantity is issued-and-outstanding shares")
            _require(
                any(
                    item.basis == "issued_and_outstanding"
                    and item.value is not None
                    and Decimal(item.value) == Decimal(str(self.selected.value))
                    for item in self.candidates
                ),
                "share_basis: the selected value must be one of the issued-and-outstanding candidates",
            )
        else:
            _require(self.selected is None, f"share_basis: {self.status} selects nothing")
        if self.status == "conflict":
            _require(len(self.candidates) >= 2, "share_basis: a conflict shows at least two candidates")
            _require(len(self.conflicts) > 0, "share_basis: a conflict names what conflicts")

    def as_record(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMAS["share_basis_result"], **_plain(self)}


# ---------------------------------------------------------------------------
# Compatibility and schema validation
# ---------------------------------------------------------------------------


def projection_compatibility(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Verdict on whether a projection bundle may feed this state family."""
    reasons: list[str] = []
    schema = bundle.get("schema")
    if schema != PROJECTION_BUNDLE_SCHEMA:
        reasons.append(f"schema {schema!r} is not {PROJECTION_BUNDLE_SCHEMA!r}")
    version = str(bundle.get("projection_version") or "")
    if not version.startswith(PROJECTION_COMPATIBILITY["projection_version_prefix"]):
        reasons.append(f"projection_version {version!r} is outside {PROJECTION_COMPATIBILITY['projection_version_prefix']!r}")
    authority = bundle.get("authority")
    if authority != AUTHORITY:
        reasons.append("authority differs from the context-only contract")
    return {
        "verdict": "compatible" if not reasons else "incompatible",
        "reasons": reasons,
        "projection_bundle_schema": PROJECTION_BUNDLE_SCHEMA,
        "state_contract_version": STATE_CONTRACT_VERSION,
    }


def load_state_schema(schema_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(schema_path) if schema_path else STATE_SCHEMA_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def validate_state_record(kind: str, record: Mapping[str, Any], schema_path: Path | str | None = None) -> None:
    """Validate a serialized record against ``capital_structure_state.v2``.

    ``kind`` is ``"state"`` for the root artifact or one of the ``$defs`` keys
    (``financing_scenario``, ``capacity_envelope``, ``supply_envelope``,
    ``funding_schedule``, ``instrument_set``, ``share_basis_result``,
    ``state_request``, ``capital_inputs``, ``rule_pack``,
    ``calculation_receipt``).
    """
    from jsonschema import Draft202012Validator, FormatChecker

    schema = load_state_schema(schema_path)
    if kind == "state":
        target: dict[str, Any] = schema
    else:
        _require(kind in schema.get("$defs", {}), f"unknown state record kind {kind!r}")
        target = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": f"#/$defs/{kind}"}
    validator = Draft202012Validator(target, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(dict(record)), key=lambda error: list(error.path))
    if errors:
        messages = [
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors[:10]
        ]
        raise ContractViolation("capital-structure state contract violation: " + "; ".join(messages))


__all__ = [
    "AUTHORITY",
    "ActionSelection",
    "Assumption",
    "COMPATIBLE_INPUT_SCHEMAS",
    "CalculationReceipt",
    "CandidateBundle",
    "CapabilityProof",
    "CapacityEnvelope",
    "CapitalInputs",
    "CapitalState",
    "CashEffect",
    "CommitmentInputs",
    "Constraint",
    "ContractViolation",
    "CorporateActionBasis",
    "CorporateActionInputs",
    "EvidenceRef",
    "FORBIDDEN_PROPERTY_PATTERN",
    "FamilyProvenance",
    "FamilyState",
    "FinancialInputs",
    "FinancingScenario",
    "Flow",
    "FundingPeriod",
    "FundingSchedule",
    "GenerationBinding",
    "INHERITED_UNAVAILABLE_CAPABILITIES",
    "INTERFACE_OWNER",
    "INTERFACE_OWNERSHIP",
    "INTERFACE_READER",
    "Instrument",
    "InstrumentSet",
    "PROJECTION_COMPATIBILITY",
    "PriceAssumption",
    "Provenance",
    "Quantity",
    "RECORD_SCHEMAS",
    "REQUIRED_FUNDING_ASSUMPTIONS",
    "Resolution",
    "ResolutionInputs",
    "RouteBound",
    "RulePack",
    "RuleRef",
    "SHARE_BASES",
    "STATE_CONTRACT_VERSION",
    "STATE_FAMILIES",
    "STATE_SCHEMA",
    "STATE_SCHEMA_FILE",
    "STATE_SCHEMA_PATH",
    "ShareBasisResult",
    "ShareInputs",
    "ShareObservationRef",
    "StateRequest",
    "SupplyEnvelope",
    "Unknown",
    "UnknownResolution",
    "WitnessAllocation",
    "load_state_schema",
    "projection_compatibility",
    "sha256_of",
    "stable_id",
    "validate_state_record",
]
