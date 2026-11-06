"""The capacity inputs bundle: typed per-family support bound to a generation.

SPEC_U1B §2.  S0 (``scenario_composition``) composes a joint
financing-constraint answer from five input families, and nothing in production
constructed them: this module owns the published ``capital_structure.capacity_inputs.v1``
bundle that binds instruments, share basis, financials, commitments and rules to
the served state generation, with TYPED per-family support.

The law this module enforces (SPEC_U1B §0, §2):

* per-family support is a first-class fact: ``supported`` / ``partial`` /
  ``unavailable`` with a CLOSED reason vocabulary — an unavailable family is
  never an empty contract object, never a zero, never a fixture default;
* ``record`` is null iff the family is unavailable, and a supported or partial
  record MUST reconstruct through its frozen contract class byte-identically
  (the readers here are module-local; the frozen classes gain no new methods);
* the bundle names the served state generation it binds and the verified
  projection generation it was compiled from, so a stale bundle is a typed
  mismatch, never a silently composed number.

Offline contract module: no I/O beyond reading this bundle's own JSON schema,
no network, no model call, and no score, rank, sizing, probability or
recommendation.  Money is exact ``Decimal`` text and kernel values exact
rationals, as everywhere in the state family.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from engine.capital_structure.issuer_state_contracts import (
    AUTHORITY,
    INHERITED_UNAVAILABLE_CAPABILITIES,
    STATE_CONTRACT_VERSION,
    CalculationReceipt,
    CommitmentInputs,
    ContractViolation,
    CorporateActionBasis,
    EconomicTerm,
    EvidenceRef,
    FamilyProvenance,
    FinancialInputs,
    GenerationBinding,
    Instrument,
    InstrumentSet,
    Provenance,
    Quantity,
    Resolution,
    RulePack,
    RuleRef,
    ShareBasisResult,
    ShareObservationRef,
    Unknown,
    sha256_of,
    stable_id,
    structure_from_record,
)
from engine.capital_structure.listing_facts import ListingFact, listing_fact_from_record

CAPACITY_INPUTS_SCHEMA = "capital_structure.capacity_inputs.v1"
CAPACITY_INPUTS_FILENAME = "capacity_inputs.json"
CAPACITY_INPUTS_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "capital_structure_capacity_inputs.v1.schema.json"
)

#: The five input families a bundle carries.  The first four are per issuer;
#: ``rules`` is bundle-level (one rule applicability answer per generation).
INSTRUMENTS_FAMILY = "instruments"
SHARE_BASIS_FAMILY = "share_basis"
FINANCIALS_FAMILY = "financials"
COMMITMENTS_FAMILY = "commitments"
RULES_FAMILY = "rules"
ISSUER_FAMILIES = (INSTRUMENTS_FAMILY, SHARE_BASIS_FAMILY, FINANCIALS_FAMILY, COMMITMENTS_FAMILY)
BUNDLE_FAMILIES = (INSTRUMENTS_FAMILY, SHARE_BASIS_FAMILY, FINANCIALS_FAMILY, COMMITMENTS_FAMILY, RULES_FAMILY)

#: SPEC_U1B §2: the closed reason vocabulary.  On an unavailable family the
#: codes say why nothing is bound; on a partial family they name its support
#: limits.  No other string may appear in any ``reason_codes`` list.
INPUT_UNAVAILABLE_REASONS = (
    "candidate_terms_not_materialized",
    "decisions_ledger_absent",
    "share_observations_not_admitted",
    "corporate_actions_absent",
    "companyfacts_snapshot_unavailable",
    "commitment_rows_absent",
    "binding_config_refuses_schema",
    "no_rule_governs_as_of",
)

SUPPORT_STATES = ("supported", "partial", "unavailable")


class ScenarioInputsError(ContractViolation):
    """A capacity inputs bundle could not be read or bound under the contract."""


class ScenarioInputsUnavailable(ScenarioInputsError):
    """One or more requested input families are unavailable.

    Returned by :func:`assemble_scenario_inputs` as a VALUE (and usable as an
    exception): ``components`` lists EVERY unavailable family with its support
    and reason codes, and ``available`` names the families that would have
    assembled.  It never carries a number, a default or a best-effort record.
    """

    def __init__(
        self,
        components: Mapping[str, Mapping[str, Any]],
        available: tuple[str, ...] = (),
    ) -> None:
        self.components: dict[str, dict[str, Any]] = {
            str(family): {"support": str(row["support"]), "reason_codes": [str(code) for code in row["reason_codes"]]}
            for family, row in components.items()
        }
        self.available: tuple[str, ...] = tuple(available)
        missing = ", ".join(sorted(self.components)) or "none"
        super().__init__(f"scenario_inputs_unavailable: {missing}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScenarioInputsError(message)


def _json_normal(value: Any) -> Any:
    """Normalize tuples to lists so an in-memory record compares like parsed JSON."""
    if isinstance(value, Mapping):
        return {str(key): _json_normal(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_normal(item) for item in value]
    return value


def _closed_mapping(value: Any, allowed: tuple[str, ...], label: str) -> dict[str, Any]:
    _require(isinstance(value, Mapping), f"{label}: an object is required, got {type(value).__name__}")
    body = dict(value)
    unexpected = sorted(str(key) for key in body if key not in allowed)
    _require(not unexpected, f"{label}: unexpected keys {unexpected}")
    return body


def _timestamp(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value), f"{label}: ISO-8601 timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScenarioInputsError(f"{label}: {value!r} is not an ISO-8601 timestamp") from exc
    _require(parsed.tzinfo is not None, f"{label}: timestamp must carry a timezone")
    return value


# ---------------------------------------------------------------------------
# Module-local record readers (the frozen classes gain no new methods)
# ---------------------------------------------------------------------------


def _evidence_refs_from_record(value: Any, label: str) -> tuple[EvidenceRef, ...]:
    if value is None:
        return ()
    _require(isinstance(value, (list, tuple)), f"{label}: a list is required")
    out = []
    for index, item in enumerate(value):
        body = _closed_mapping(item, ("manifest_id", "span_id", "text_sha256"), f"{label}[{index}]")
        out.append(EvidenceRef(body.get("manifest_id"), body.get("span_id"), body.get("text_sha256")))
    return tuple(out)


def _provenance_from_record(value: Any, label: str) -> Provenance | None:
    if value is None:
        return None
    body = _closed_mapping(
        value, ("input_family", "generation_id", "evidence", "available_at"), label
    )
    return Provenance(
        input_family=body.get("input_family"),
        generation_id=body.get("generation_id"),
        evidence=_evidence_refs_from_record(body.get("evidence"), f"{label}.evidence"),
        available_at=body.get("available_at"),
    )


def _quantity_from_record(value: Any, label: str) -> Quantity | None:
    if value is None:
        return None
    body = _closed_mapping(
        value,
        ("unit", "status", "value", "share_basis", "security_class_id", "applicability", "provenance", "note"),
        label,
    )
    return Quantity(
        unit=body.get("unit"),
        status=body.get("status"),
        value=body.get("value"),
        share_basis=body.get("share_basis"),
        security_class_id=body.get("security_class_id"),
        applicability=body.get("applicability"),
        provenance=_provenance_from_record(body.get("provenance"), f"{label}.provenance"),
        note=body.get("note"),
    )


def generation_binding_from_record(record: Any, label: str = "binding") -> GenerationBinding:
    body = _closed_mapping(
        record,
        ("input_family", "schema", "support", "generation_id", "artifact_sha256", "as_of"),
        label,
    )
    return GenerationBinding(
        input_family=body.get("input_family"),
        schema=body.get("schema"),
        support=body.get("support"),
        generation_id=body.get("generation_id"),
        artifact_sha256=body.get("artifact_sha256"),
        as_of=body.get("as_of"),
    )


def calculation_receipt_from_record(record: Any, label: str = "receipt") -> CalculationReceipt:
    body = _closed_mapping(
        record,
        ("schema", "receipt_id", "input_digest", "rule_digest", "implementation_digest", "computed_at", "scenario_id"),
        label,
    )
    return CalculationReceipt(
        input_digest=body.get("input_digest"),
        rule_digest=body.get("rule_digest"),
        implementation_digest=body.get("implementation_digest"),
        computed_at=body.get("computed_at"),
        scenario_id=body.get("scenario_id"),
    )


def family_provenance_from_record(record: Any, label: str = "provenance") -> FamilyProvenance:
    body = _closed_mapping(
        record,
        (
            "family", "input_family", "input_schema", "support", "compiler_version",
            "generation_id", "artifact_sha256", "support_limits", "as_of", "available_at",
        ),
        label,
    )
    return FamilyProvenance(
        family=body.get("family"),
        input_family=body.get("input_family"),
        input_schema=body.get("input_schema"),
        support=body.get("support"),
        compiler_version=body.get("compiler_version"),
        generation_id=body.get("generation_id"),
        artifact_sha256=body.get("artifact_sha256"),
        support_limits=tuple(body.get("support_limits") or ()),
        as_of=body.get("as_of"),
        available_at=body.get("available_at"),
    )


def economic_term_from_record(record: Any, label: str = "economic_term") -> EconomicTerm:
    body = _closed_mapping(
        record,
        (
            "term_id", "instrument_id", "name", "status", "value", "flag", "expression",
            "date_value", "evidence", "fact_origin", "interpretation_version", "available_at",
            "effective_at", "structure",
        ),
        label,
    )
    structure = body.get("structure")
    return EconomicTerm(
        term_id=body.get("term_id"),
        instrument_id=body.get("instrument_id"),
        name=body.get("name"),
        status=body.get("status"),
        value=_quantity_from_record(body.get("value"), f"{label}.value"),
        flag=body.get("flag"),
        expression=body.get("expression"),
        date_value=body.get("date_value"),
        evidence=_evidence_refs_from_record(body.get("evidence"), f"{label}.evidence"),
        fact_origin=body.get("fact_origin"),
        interpretation_version=body.get("interpretation_version"),
        available_at=body.get("available_at"),
        effective_at=body.get("effective_at"),
        structure=None if structure is None else structure_from_record(structure, f"{label}.structure"),
    )


def instrument_from_record(record: Any, label: str = "instrument") -> Instrument:
    body = _closed_mapping(
        record,
        (
            "instrument_id", "security_class_id", "kind", "status", "candidate_term_ids",
            "resolution", "amendments", "outstanding", "provenance", "economic_terms",
        ),
        label,
    )
    resolution_body = _closed_mapping(
        body.get("resolution"),
        ("method", "decision_id", "evidence", "decided_at"),
        f"{label}.resolution",
    )
    terms = body.get("economic_terms") or ()
    _require(isinstance(terms, (list, tuple)), f"{label}.economic_terms: a list is required")
    return Instrument(
        instrument_id=body.get("instrument_id"),
        security_class_id=body.get("security_class_id"),
        kind=body.get("kind"),
        status=body.get("status"),
        candidate_term_ids=tuple(body.get("candidate_term_ids") or ()),
        resolution=Resolution(
            method=resolution_body.get("method"),
            decision_id=resolution_body.get("decision_id"),
            evidence=_evidence_refs_from_record(resolution_body.get("evidence"), f"{label}.resolution.evidence"),
            decided_at=resolution_body.get("decided_at"),
        ),
        amendments=tuple(body.get("amendments") or ()),
        outstanding=_quantity_from_record(body.get("outstanding"), f"{label}.outstanding"),
        provenance=_provenance_from_record(body.get("provenance"), f"{label}.provenance"),
        economic_terms=tuple(
            economic_term_from_record(item, f"{label}.economic_terms[{index}]")
            for index, item in enumerate(terms)
        ),
    )


def instrument_set_from_record(record: Any) -> InstrumentSet:
    """Rebuild an :class:`InstrumentSet` from its published record, byte-identically."""
    body = _closed_mapping(
        record,
        (
            "schema", "issuer_id", "as_of", "instruments", "provenance", "receipt",
            "unresolved_candidate_ids",
        ),
        "instrument_set",
    )
    instruments = body.get("instruments") or ()
    _require(isinstance(instruments, (list, tuple)), "instrument_set.instruments: a list is required")
    built = InstrumentSet(
        issuer_id=body.get("issuer_id"),
        as_of=body.get("as_of"),
        instruments=tuple(
            instrument_from_record(item, f"instrument_set.instruments[{index}]")
            for index, item in enumerate(instruments)
        ),
        provenance=family_provenance_from_record(body.get("provenance"), "instrument_set.provenance"),
        receipt=calculation_receipt_from_record(body.get("receipt"), "instrument_set.receipt"),
        unresolved_candidate_ids=tuple(body.get("unresolved_candidate_ids") or ()),
    )
    _assert_round_trip(built, body, "instrument_set")
    return built


def share_basis_result_from_record(record: Any) -> ShareBasisResult:
    """Rebuild a :class:`ShareBasisResult` from its published record, byte-identically."""
    body = _closed_mapping(
        record,
        (
            "schema", "issuer_id", "security_class_id", "as_of", "status", "provenance",
            "receipt", "selected", "candidates", "conflicts", "corporate_action",
        ),
        "share_basis_result",
    )
    candidates = body.get("candidates") or ()
    _require(isinstance(candidates, (list, tuple)), "share_basis_result.candidates: a list is required")
    rebuilt_candidates = []
    for index, item in enumerate(candidates):
        row = _closed_mapping(
            item,
            ("observation_id", "basis", "as_of_date", "security_class_id", "value", "source"),
            f"share_basis_result.candidates[{index}]",
        )
        rebuilt_candidates.append(
            ShareObservationRef(
                observation_id=row.get("observation_id"),
                basis=row.get("basis"),
                as_of_date=row.get("as_of_date"),
                security_class_id=row.get("security_class_id"),
                value=row.get("value"),
                source=_provenance_from_record(row.get("source"), f"share_basis_result.candidates[{index}].source"),
            )
        )
    action = body.get("corporate_action")
    action_body = _closed_mapping(
        action,
        ("kind", "ratio", "effective_date", "contract_adjustment_evidence"),
        "share_basis_result.corporate_action",
    )
    built = ShareBasisResult(
        issuer_id=body.get("issuer_id"),
        security_class_id=body.get("security_class_id"),
        as_of=body.get("as_of"),
        status=body.get("status"),
        provenance=family_provenance_from_record(body.get("provenance"), "share_basis_result.provenance"),
        receipt=calculation_receipt_from_record(body.get("receipt"), "share_basis_result.receipt"),
        selected=_quantity_from_record(body.get("selected"), "share_basis_result.selected"),
        candidates=tuple(rebuilt_candidates),
        conflicts=tuple(body.get("conflicts") or ()),
        corporate_action=CorporateActionBasis(
            kind=action_body.get("kind"),
            ratio=action_body.get("ratio"),
            effective_date=action_body.get("effective_date"),
            contract_adjustment_evidence=_evidence_refs_from_record(
                action_body.get("contract_adjustment_evidence"),
                "share_basis_result.corporate_action.contract_adjustment_evidence",
            ),
        ),
    )
    _assert_round_trip(built, body, "share_basis_result")
    return built


def financial_inputs_from_record(record: Any) -> FinancialInputs:
    """Rebuild :class:`FinancialInputs` from its published record, byte-identically."""
    body = _closed_mapping(record, ("binding", "facts", "cash_basis"), "financial_inputs")
    facts = body.get("facts") or ()
    _require(isinstance(facts, (list, tuple)), "financial_inputs.facts: a list is required")
    built = FinancialInputs(
        binding=generation_binding_from_record(body.get("binding"), "financial_inputs.binding"),
        facts=tuple(dict(item) for item in facts),
        cash_basis=body.get("cash_basis"),
    )
    _assert_round_trip(built, body, "financial_inputs")
    return built


def commitment_inputs_from_record(record: Any) -> CommitmentInputs:
    """Rebuild :class:`CommitmentInputs` from its published record, byte-identically."""
    body = _closed_mapping(record, ("binding", "commitments"), "commitment_inputs")
    commitments = body.get("commitments") or ()
    _require(isinstance(commitments, (list, tuple)), "commitment_inputs.commitments: a list is required")
    built = CommitmentInputs(
        binding=generation_binding_from_record(body.get("binding"), "commitment_inputs.binding"),
        commitments=tuple(dict(item) for item in commitments),
    )
    _assert_round_trip(built, body, "commitment_inputs")
    return built


def rule_pack_from_record(record: Any) -> RulePack:
    """Rebuild a :class:`RulePack` from its published record, digest re-proved."""
    body = _closed_mapping(
        record,
        (
            "schema", "rule_pack_id", "version", "source_edition", "jurisdiction",
            "effective_date", "interpretation_date", "rules", "venues", "forms", "digest",
        ),
        "rule_pack",
    )
    rules = body.get("rules") or ()
    _require(isinstance(rules, (list, tuple)), "rule_pack.rules: a list is required")
    built = RulePack(
        rule_pack_id=body.get("rule_pack_id"),
        version=body.get("version"),
        source_edition=body.get("source_edition"),
        jurisdiction=body.get("jurisdiction"),
        effective_date=body.get("effective_date"),
        interpretation_date=body.get("interpretation_date"),
        rules=tuple(
            RuleRef(
                rule_id=item.get("rule_id"),
                binding_class=item.get("binding_class"),
                citation=item.get("citation"),
                enforceable=item.get("enforceable"),
                effective_from=item.get("effective_from"),
                effective_to=item.get("effective_to"),
                required_issuer_facts=tuple(item.get("required_issuer_facts") or ()),
            )
            for item in rules
        ),
        venues=tuple(body.get("venues") or ()),
        forms=tuple(body.get("forms") or ()),
    )
    _require(
        built.digest == body.get("digest"),
        "rule_pack.digest: the published digest is not the digest of the published rules",
    )
    _assert_round_trip(built, body, "rule_pack")
    return built


def _assert_round_trip(built: Any, record: Mapping[str, Any], label: str) -> None:
    """A supported/partial record must survive contract re-construction exactly."""
    rebuilt = _json_normal(built.as_record())
    if rebuilt != _json_normal(record):
        raise ScenarioInputsError(
            f"{label}: the published record does not survive contract re-construction"
        )


#: The reader of each per-issuer family's published record.
ISSUER_FAMILY_READERS = {
    INSTRUMENTS_FAMILY: instrument_set_from_record,
    SHARE_BASIS_FAMILY: share_basis_result_from_record,
    FINANCIALS_FAMILY: financial_inputs_from_record,
    COMMITMENTS_FAMILY: commitment_inputs_from_record,
}


# ---------------------------------------------------------------------------
# Bundle construction
# ---------------------------------------------------------------------------


def _check_support(support: Any, label: str) -> str:
    _require(support in SUPPORT_STATES, f"{label}: support {support!r} not in {list(SUPPORT_STATES)}")
    return str(support)


def _check_reason_codes(reason_codes: Any, support: str, label: str) -> tuple[str, ...]:
    codes = tuple(reason_codes or ())
    for code in codes:
        _require(code in INPUT_UNAVAILABLE_REASONS, f"{label}: reason {code!r} is outside the closed vocabulary")
    _require(len(set(codes)) == len(codes), f"{label}: duplicate reason codes")
    if support == "unavailable":
        _require(len(codes) > 0, f"{label}: an unavailable family names why")
    if support == "supported":
        _require(len(codes) == 0, f"{label}: a supported family carries no reason codes")
    return codes


@dataclass(frozen=True)
class FamilyEntry:
    """One issuer family: support, reasons, binding and the record itself.

    ``record`` is the contract OBJECT (it serialises through ``as_record()``);
    it is null exactly when the family is unavailable — never a default, never
    a zero, never a hand-written dict.
    """

    family: str
    support: str
    reason_codes: tuple[str, ...] = ()
    binding: GenerationBinding | None = None
    record: Any | None = None

    def __post_init__(self) -> None:
        _require(self.family in ISSUER_FAMILIES, f"family_entry: unknown family {self.family!r}")
        object.__setattr__(self, "support", _check_support(self.support, f"{self.family}.support"))
        object.__setattr__(
            self, "reason_codes", _check_reason_codes(self.reason_codes, self.support, f"{self.family}.reason_codes")
        )
        if self.support == "unavailable":
            _require(self.record is None, f"{self.family}: an unavailable family carries no record")
            _require(self.binding is None, f"{self.family}: an unavailable family carries no binding")
        else:
            _require(
                self.record is not None and hasattr(self.record, "as_record"),
                f"{self.family}: a {self.support} family carries its contract record",
            )
            if self.binding is not None:
                _require(
                    isinstance(self.binding, GenerationBinding)
                    and self.binding.support == self.support,
                    f"{self.family}: the binding must carry the family's own support",
                )

    def as_record(self) -> dict[str, Any]:
        return {
            "support": self.support,
            "reason_codes": list(self.reason_codes),
            "binding": None if self.binding is None else self.binding.as_record(),
            "record": None if self.record is None else self.record.as_record(),
        }


@dataclass(frozen=True)
class RulesEntry:
    """The bundle-level rules family: one L0 rule-pack answer per generation."""

    support: str
    reason_codes: tuple[str, ...] = ()
    unknowns: tuple[Unknown, ...] = ()
    record: RulePack | None = None

    def __post_init__(self) -> None:
        _require(self.support in SUPPORT_STATES, f"rules.support: {self.support!r} outside the support states")
        object.__setattr__(
            self, "reason_codes", _check_reason_codes(self.reason_codes, self.support, "rules.reason_codes")
        )
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        for item in self.unknowns:
            _require(isinstance(item, Unknown), "rules.unknowns: Unknown required")
        if self.support == "unavailable":
            _require(self.record is None, "rules: an unavailable rules family carries no record")
        else:
            _require(isinstance(self.record, RulePack), "rules: a bound rules family carries its RulePack")

    def as_record(self) -> dict[str, Any]:
        return {
            "support": self.support,
            "reason_codes": list(self.reason_codes),
            "unknowns": [item.as_record() for item in self.unknowns],
            "record": None if self.record is None else self.record.as_record(),
        }


def _coverage_tallies(issuers: Mapping[str, Mapping[str, FamilyEntry]]) -> dict[str, dict[str, int]]:
    tallies = {
        family: {"supported": 0, "partial": 0, "unavailable": 0}
        for family in ISSUER_FAMILIES
    }
    for entries in issuers.values():
        for family in ISSUER_FAMILIES:
            tallies[family][entries[family].support] += 1
    return tallies


@dataclass(frozen=True)
class CapacityInputsBundle:
    """The published inputs bundle: one generation, five families, typed support.

    ``generation_id`` digests every family body, so a tampered reason code, a
    swapped record or a re-stamped generation is a different bundle identity
    rather than a mutation.
    """

    as_of: str
    generated_at: str
    state_generation_id: str
    source_generation_id: str
    rules: RulesEntry
    issuers: Mapping[str, Mapping[str, FamilyEntry]]
    #: SPEC_G0 §2.4: the OPTIONAL per-issuer listing facts.  Outside
    #: ``ISSUER_FAMILIES`` entirely, so coverage tallies and support states do
    #: not change; the key is omitted from the record when the map is empty, so
    #: a bundle without listings round-trips byte-identically.
    listings: Mapping[str, ListingFact] | None = None

    def __post_init__(self) -> None:
        _timestamp(self.as_of, "capacity_inputs.as_of")
        _timestamp(self.generated_at, "capacity_inputs.generated_at")
        for label, value in (
            ("state_generation_id", self.state_generation_id),
            ("source_generation_id", self.source_generation_id),
        ):
            _require(isinstance(value, str) and bool(value), f"capacity_inputs.{label}: identifier required")
        _require(isinstance(self.rules, RulesEntry), "capacity_inputs.rules: RulesEntry required")
        object.__setattr__(self, "issuers", {
            str(issuer_id): dict(entries) for issuer_id, entries in self.issuers.items()
        })
        for issuer_id, entries in self.issuers.items():
            _require(
                sorted(entries) == sorted(ISSUER_FAMILIES),
                f"capacity_inputs.issuers[{issuer_id}]: exactly the four issuer families are required",
            )
            for family, entry in entries.items():
                _require(isinstance(entry, FamilyEntry), f"issuers[{issuer_id}].{family}: FamilyEntry required")
        object.__setattr__(self, "listings", {
            str(issuer_id): fact for issuer_id, fact in (self.listings or {}).items()
        })
        for issuer_id, fact in self.listings.items():
            _require(
                isinstance(fact, ListingFact),
                f"capacity_inputs.listings[{issuer_id}]: ListingFact required",
            )
            _require(
                issuer_id in self.issuers,
                f"capacity_inputs.listings[{issuer_id}]: no such issuer in the bundle",
            )

    def _record_without_identity(self) -> dict[str, Any]:
        """The full record body except the identity and stamp fields."""
        rules_record = self.rules.as_record()
        rule_record = rules_record["record"]
        rule_pack = {
            "rule_pack_id": rule_record["rule_pack_id"] if rule_record else None,
            "rule_pack_version": rule_record["version"] if rule_record else None,
            "rule_pack_digest": rule_record["digest"] if rule_record else None,
            "source": "L0",
        }
        return {
            "schema": CAPACITY_INPUTS_SCHEMA,
            "contract_version": STATE_CONTRACT_VERSION,
            "as_of": self.as_of,
            "state_generation_id": self.state_generation_id,
            "source_generation_id": self.source_generation_id,
            "rule_pack": rule_pack,
            "rules": rules_record,
            "issuers": {
                issuer_id: {family: entry.as_record() for family, entry in entries.items()}
                for issuer_id, entries in self.issuers.items()
            },
            "coverage": {
                "issuer_count": len(self.issuers),
                "families": _coverage_tallies(self.issuers),
            },
            "unavailable": list(INHERITED_UNAVAILABLE_CAPABILITIES),
            "capabilities_proven": [],
            "authority": dict(AUTHORITY),
            **(
                {"listings": {issuer_id: fact.as_record() for issuer_id, fact in self.listings.items()}}
                if self.listings
                else {}
            ),
        }

    @property
    def generation_id(self) -> str:
        """The bundle identity over everything but its own id and stamp."""
        body = {
            key: value
            for key, value in self._record_without_identity().items()
            if key not in ("schema", "contract_version", "generated_at")
        }
        return stable_id("capacity_inputs", body)

    def as_record(self) -> dict[str, Any]:
        body = self._record_without_identity()
        return {
            "schema": body["schema"],
            "contract_version": body["contract_version"],
            "generation_id": self.generation_id,
            "as_of": body["as_of"],
            "generated_at": self.generated_at,
            "state_generation_id": body["state_generation_id"],
            "source_generation_id": body["source_generation_id"],
            "rule_pack": body["rule_pack"],
            "rules": body["rules"],
            "issuers": body["issuers"],
            "coverage": body["coverage"],
            "unavailable": body["unavailable"],
            "capabilities_proven": body["capabilities_proven"],
            "authority": body["authority"],
            **({"listings": body["listings"]} if "listings" in body else {}),
        }


# ---------------------------------------------------------------------------
# Bundle validation
# ---------------------------------------------------------------------------


def load_capacity_inputs_schema() -> dict[str, Any]:
    return json.loads(CAPACITY_INPUTS_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_capacity_inputs_bundle(record: Any) -> None:
    """Validate a serialized bundle, or refuse it (SPEC §3: one generation or nothing).

    Layers, in order: this bundle's JSON schema, the frozen envelope constants,
    the per-family support law (``record`` null iff unavailable, closed reason
    vocabulary), byte-identical contract re-construction of every bound record,
    the L0 rule-pack digest, and the coverage tallies.
    """
    from jsonschema import Draft202012Validator, FormatChecker

    if not isinstance(record, Mapping):
        raise ScenarioInputsError("capacity inputs bundle must be an object")
    normal = _json_normal(record)
    schema = load_capacity_inputs_schema()
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(dict(normal)),
        key=lambda error: list(error.path),
    )
    if errors:
        messages = [
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors[:10]
        ]
        raise ScenarioInputsError("capacity inputs contract violation: " + "; ".join(messages))

    _require(
        normal.get("contract_version") == STATE_CONTRACT_VERSION,
        f"capacity inputs contract_version {normal.get('contract_version')!r} is not {STATE_CONTRACT_VERSION!r}",
    )
    body = {key: value for key, value in normal.items() if key not in ("schema", "contract_version", "generation_id", "generated_at")}
    expected_generation_id = stable_id("capacity_inputs", body)
    _require(
        normal.get("generation_id") == expected_generation_id,
        "capacity inputs generation_id does not match its content",
    )
    _require(
        normal.get("authority") == dict(AUTHORITY),
        "capacity inputs authority differs from the context-only contract",
    )
    _require(
        list(normal.get("unavailable") or ()) == sorted(INHERITED_UNAVAILABLE_CAPABILITIES),
        "capacity inputs must inherit every projection-era unavailable capability",
    )
    _require(normal.get("capabilities_proven") == [], "capacity inputs carries no capability proof yet")

    tallies = {family: {"supported": 0, "partial": 0, "unavailable": 0} for family in ISSUER_FAMILIES}
    issuers = normal.get("issuers") or {}
    for issuer_id, entries in sorted(issuers.items()):
        _require(
            sorted(entries) == sorted(ISSUER_FAMILIES),
            f"issuers[{issuer_id}]: exactly the four issuer families are required",
        )
        for family in ISSUER_FAMILIES:
            entry = entries[family]
            support = _check_support(entry.get("support"), f"issuers[{issuer_id}].{family}.support")
            codes = _check_reason_codes(
                entry.get("reason_codes") or (), support, f"issuers[{issuer_id}].{family}.reason_codes"
            )
            family_record = entry.get("record")
            binding_record = entry.get("binding")
            if support == "unavailable":
                _require(family_record is None, f"issuers[{issuer_id}].{family}: an unavailable family carries no record")
                _require(binding_record is None, f"issuers[{issuer_id}].{family}: an unavailable family carries no binding")
            else:
                _require(
                    family_record is not None,
                    f"issuers[{issuer_id}].{family}: a {support} family carries its record",
                )
                # The record MUST reconstruct through its contract class.
                ISSUER_FAMILY_READERS[family](family_record)
                if binding_record is not None:
                    binding = generation_binding_from_record(binding_record, f"issuers[{issuer_id}].{family}.binding")
                    _require(
                        binding.support == support,
                        f"issuers[{issuer_id}].{family}: binding support {binding.support!r} differs from {support!r}",
                    )
                    if binding.as_of is not None:
                        _timestamp(binding.as_of, f"issuers[{issuer_id}].{family}.binding.as_of")
            tallies[family][support] += 1

    rules = normal.get("rules") or {}
    rules_support = _check_support(rules.get("support"), "rules.support")
    _check_reason_codes(rules.get("reason_codes") or (), rules_support, "rules.reason_codes")
    rules_record = rules.get("record")
    rule_pack = normal.get("rule_pack") or {}
    if rules_support == "unavailable":
        _require(rules_record is None, "rules: an unavailable rules family carries no record")
    else:
        built_rules = rule_pack_from_record(rules_record)
        _require(
            rule_pack.get("rule_pack_digest") == built_rules.digest,
            "rule_pack.rule_pack_digest is not the digest of the published rule pack",
        )
        _require(
            rule_pack.get("rule_pack_id") == built_rules.rule_pack_id
            and rule_pack.get("rule_pack_version") == built_rules.version,
            "rule_pack identity differs from the published rule pack",
        )
    for unknown in rules.get("unknowns") or ():
        _closed_mapping(unknown, ("unknown_id", "description", "resolving_fact", "affects"), "rules.unknowns[]")

    _require(
        normal.get("coverage", {}).get("issuer_count") == len(issuers),
        "coverage.issuer_count differs from the issuer map",
    )
    _require(
        normal.get("coverage", {}).get("families") == tallies,
        "coverage.families differs from the per-issuer tallies",
    )

    listings = normal.get("listings")
    if listings is not None:
        _require(isinstance(listings, Mapping), "listings: an object keyed by issuer is required")
        for issuer_id, listing_record in sorted(listings.items()):
            _require(
                issuer_id in issuers,
                f"listings[{issuer_id}]: no such issuer in the bundle",
            )
            # The record MUST reconstruct through its contract class.
            listing_fact_from_record(listing_record)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioInputs:
    """The five assembled families, in ``compose_scenario`` argument order.

    ``bindings`` carries every family's :class:`GenerationBinding` (the ones
    that named one), in canonical family order, so a route can echo exactly
    what each family was bound to.
    """

    instruments: InstrumentSet
    basis: ShareBasisResult
    financials: FinancialInputs
    commitments: CommitmentInputs
    rules: RulePack
    bindings: tuple[GenerationBinding, ...] = ()
    #: SPEC_G0 §2.4: the issuer's listing fact when the bundle carries one;
    #: ``None`` keeps production in the venue-unknown branch.
    listing: ListingFact | None = None

    def __post_init__(self) -> None:
        for name, expected in (
            ("instruments", InstrumentSet),
            ("basis", ShareBasisResult),
            ("financials", FinancialInputs),
            ("commitments", CommitmentInputs),
            ("rules", RulePack),
        ):
            _require(isinstance(getattr(self, name), expected), f"scenario_inputs.{name}: {expected.__name__} required")
        object.__setattr__(self, "bindings", tuple(self.bindings))
        for binding in self.bindings:
            _require(isinstance(binding, GenerationBinding), "scenario_inputs.bindings: GenerationBinding required")
        if self.listing is not None:
            _require(isinstance(self.listing, ListingFact), "scenario_inputs.listing: ListingFact or None required")


def _entry_for(entries: Mapping[str, Any], family: str, issuer_id: str) -> dict[str, Any]:
    entry = entries.get(family)
    if not isinstance(entry, Mapping):
        raise ScenarioInputsError(f"issuers[{issuer_id}].{family}: family entry missing")
    return dict(entry)


def assemble_scenario_inputs(
    bundle: Mapping[str, Any],
    issuer_id: str,
    as_of: str,
    *,
    served_state_generation_id: str | None = None,
) -> "ScenarioInputs | ScenarioInputsUnavailable":
    """Bind one issuer's five families for one request, or refuse typed.

    Returns :class:`ScenarioInputsUnavailable` when ANY family is unavailable
    (with every unavailable family and its reason codes in ``components``), and
    raises :class:`ScenarioInputsError` when the bundle cannot bind the request:
    another served state generation (``inputs_generation_mismatch``), another
    as_of anywhere in the bundle or its bound records (``inputs_as_of_mismatch``),
    an unknown issuer, or a record that no longer reconstructs.
    """
    _timestamp(as_of, "as_of")
    _require(isinstance(bundle, Mapping), "bundle: a capacity inputs record is required")
    _require(
        bundle.get("schema") == CAPACITY_INPUTS_SCHEMA,
        f"bundle schema {bundle.get('schema')!r} is not {CAPACITY_INPUTS_SCHEMA!r}",
    )
    if served_state_generation_id is not None:
        bound = bundle.get("state_generation_id")
        if bound != served_state_generation_id:
            raise ScenarioInputsError(
                f"inputs_generation_mismatch: capacity inputs bind state generation {bound!r}, "
                f"the served state generation is {served_state_generation_id!r}"
            )
    bundle_as_of = bundle.get("as_of")
    if bundle_as_of != as_of:
        raise ScenarioInputsError(
            f"inputs_as_of_mismatch: capacity inputs are cut at {bundle_as_of!r}, the request asks for {as_of!r}"
        )

    issuers = bundle.get("issuers") or {}
    entries = issuers.get(issuer_id)
    if not isinstance(entries, Mapping):
        raise ScenarioInputsError(f"unknown_issuer: {issuer_id!r} is not in the capacity inputs bundle")

    components: dict[str, dict[str, Any]] = {}
    available: list[str] = []
    for family in BUNDLE_FAMILIES:
        if family == RULES_FAMILY:
            entry = dict(bundle.get("rules") or {})
        else:
            entry = _entry_for(entries, family, issuer_id)
        support = entry.get("support")
        if support == "unavailable":
            components[family] = {
                "support": "unavailable",
                "reason_codes": [str(code) for code in entry.get("reason_codes") or ()],
            }
        else:
            available.append(family)

    if components:
        return ScenarioInputsUnavailable(components, tuple(available))

    # Every as_of the bound records name must be the request's as_of.
    for family in ISSUER_FAMILIES:
        entry = _entry_for(entries, family, issuer_id)
        binding_record = entry.get("binding")
        if isinstance(binding_record, Mapping) and binding_record.get("as_of") not in (None, as_of):
            raise ScenarioInputsError(
                f"inputs_as_of_mismatch: {family} binding is cut at {binding_record.get('as_of')!r}, "
                f"the request asks for {as_of!r}"
            )
        record = entry.get("record")
        if family == INSTRUMENTS_FAMILY and record is not None and record.get("as_of") not in (None, as_of):
            raise ScenarioInputsError(
                f"inputs_as_of_mismatch: instruments are cut at {record.get('as_of')!r}, "
                f"the request asks for {as_of!r}"
            )
        if family == SHARE_BASIS_FAMILY and record is not None and record.get("as_of") not in (None, as_of):
            raise ScenarioInputsError(
                f"inputs_as_of_mismatch: share basis is cut at {record.get('as_of')!r}, "
                f"the request asks for {as_of!r}"
            )
        if record is not None and record.get("issuer_id") not in (None, issuer_id):
            raise ScenarioInputsError(
                f"issuer_mismatch: {family} record names {record.get('issuer_id')!r}, "
                f"the request names {issuer_id!r}"
            )

    instruments = instrument_set_from_record(_entry_for(entries, INSTRUMENTS_FAMILY, issuer_id)["record"])
    basis = share_basis_result_from_record(_entry_for(entries, SHARE_BASIS_FAMILY, issuer_id)["record"])
    financials = financial_inputs_from_record(_entry_for(entries, FINANCIALS_FAMILY, issuer_id)["record"])
    commitments = commitment_inputs_from_record(_entry_for(entries, COMMITMENTS_FAMILY, issuer_id)["record"])
    rules = rule_pack_from_record(bundle["rules"]["record"])

    bindings = []
    for family in ISSUER_FAMILIES:
        binding_record = _entry_for(entries, family, issuer_id).get("binding")
        if isinstance(binding_record, Mapping):
            bindings.append(generation_binding_from_record(binding_record, f"{family}.binding"))
    listing_record = (bundle.get("listings") or {}).get(issuer_id)
    return ScenarioInputs(
        instruments=instruments,
        basis=basis,
        financials=financials,
        commitments=commitments,
        rules=rules,
        bindings=tuple(bindings),
        listing=listing_fact_from_record(listing_record) if listing_record is not None else None,
    )


__all__ = [
    "BUNDLE_FAMILIES",
    "CAPACITY_INPUTS_FILENAME",
    "CAPACITY_INPUTS_SCHEMA",
    "CAPACITY_INPUTS_SCHEMA_PATH",
    "COMMITMENTS_FAMILY",
    "FINANCIALS_FAMILY",
    "INSTRUMENTS_FAMILY",
    "INPUT_UNAVAILABLE_REASONS",
    "ISSUER_FAMILIES",
    "RULES_FAMILY",
    "SHARE_BASIS_FAMILY",
    "SUPPORT_STATES",
    "CapacityInputsBundle",
    "FamilyEntry",
    "RulesEntry",
    "ScenarioInputs",
    "ScenarioInputsError",
    "ScenarioInputsUnavailable",
    "assemble_scenario_inputs",
    "calculation_receipt_from_record",
    "commitment_inputs_from_record",
    "economic_term_from_record",
    "family_provenance_from_record",
    "financial_inputs_from_record",
    "generation_binding_from_record",
    "instrument_from_record",
    "instrument_set_from_record",
    "load_capacity_inputs_schema",
    "rule_pack_from_record",
    "share_basis_result_from_record",
    "validate_capacity_inputs_bundle",
]
