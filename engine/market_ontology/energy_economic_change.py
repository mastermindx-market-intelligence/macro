"""Compose pure economic-change dossiers without ranking or trading authority.

The adapter accepts owner-supplied facts, normalizes them to the shared contract,
records data problems as typed unavailable states, and validates its output. It
never reads the network, calls a clock or model, mutates durable state, or derives
an unstated economic value.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPOSITORY_ROOT / "contracts" / "market_ontology" / "economic_change_dossier.v1.schema.json"

ROLE_VOCABULARY = "energy_mechanism_families.v1"
ROLE_KINDS = (
    "upstream_oil_resource_production",
    "natural_gas_production_basis",
    "gathering_processing_ngl",
    "pipelines_reserved_capacity",
    "lng_liquefaction_marketing",
    "refining_conversion",
    "oilfield_services",
    "energy_equipment_long_cycle_manufacturing",
    "merchant_generation_retail",
    "regulated_utility_investment_recovery",
    "contracted_generation_asset_ownership",
    "nuclear_resource_procurement",
    "nuclear_conversion_enrichment_fuel_services",
    "nuclear_components_services",
    "nuclear_reactor_technology_development",
    "solar_manufacturing",
    "solar_wind_development_capital_recycling",
    "renewable_contracted_asset_ownership",
    "storage_integration",
    "storage_asset_operation",
    "grid_electrical_equipment",
    "epc_construction",
    "geothermal",
    "renewable_fuels",
    "hydrogen_fuel_cells",
    "carbon_capture_transport_storage",
    "waste_to_energy_other_transition",
    "other",
)
MILESTONE_VOCABULARIES = ("core_milestone_flags.v1", "energy_milestone_flags.v1")
BOUNDS = {"subjects": 5, "roles": 12, "changes": 40, "relationships": 80, "comparisons": 20}
STEP_KINDS = (
    "demand",
    "commercial_exposure",
    "unit_economics",
    "operating_contribution",
    "capital_financing",
    "ownership_claims",
    "shareholder_cash",
)
_STEP_ORDER = {kind: order for order, kind in enumerate(STEP_KINDS)}
_BRIDGE_CHANGE_KINDS = {
    "demand": ("guidance", "contract", "reported_measure"),
    "commercial_exposure": ("contract", "reported_measure"),
    "unit_economics": ("reported_measure",),
    "operating_contribution": ("reported_measure",),
    "capital_financing": ("financing", "contract", "reported_measure"),
}
_BRIDGE_BASES = {
    "ownership_claims": ("proportionate", "common_shareholder"),
    "shareholder_cash": ("common_shareholder",),
}
_REGISTERED_VOCABULARIES = {ROLE_VOCABULARY, *MILESTONE_VOCABULARIES}
_REASONS = {
    "IDENTITY_UNRESOLVED": ("This identifier or basket relation is not fully established.", "该标识或组别关系尚未完全确立。"),
    "RIGHTS_RESTRICTED": ("The source does not permit this value to be displayed.", "来源不允许展示该数值。"),
    "SOURCE_UNAVAILABLE": ("The supporting source is unavailable.", "支持来源不可用。"),
    "PERIOD_MISMATCH": ("The requested periods do not align.", "所请求的期间不一致。"),
    "DEFINITION_INCOMPATIBLE": ("The definitions are not compatible.", "这些定义不兼容。"),
    "MILESTONE_NOT_OPERATING": ("The milestone does not establish current operation.", "该里程碑不能证明当前运营。"),
    "CONTINGENT_NOT_FUNDED": ("The contingent item has not become funded.", "该或有项目尚未落实。"),
    "EXPECTATIONS_UNAVAILABLE": ("No compatible expectation is available.", "目前没有兼容的预期值。"),
    "EVIDENCE_GRADE_INSUFFICIENT": ("The evidence grade is not strong enough for an estimate.", "证据等级不足以支持估计值。"),
    "CONFOUNDED_EVENT": ("The event window has an untreated confound.", "该事件窗口存在未处理的混杂因素。"),
    "OVERSIZE_SELECTION": ("This selection is larger than the adapter bound.", "该选择范围超过适配器上限。"),
    "SUPERSEDED": ("A newer source supersedes this item.", "较新的来源已替代该项。"),
    "CONFLICTING_SOURCES": ("The available sources conflict.", "可用来源相互冲突。"),
    "PRIVATE_BINDING_UNAVAILABLE": ("No permitted binding is available for this subject.", "该主体没有可用且被允许的绑定。"),
    "AUTHORITY_BIT_REJECTED": ("The caller requested authority this interface may never grant.", "调用方请求了此接口永远不能授予的权限。"),
    "ROLE_KIND_UNKNOWN": ("The supplied role kind is not registered for this vocabulary.", "提供的角色类型未在该词表中注册。"),
    "UNIT_INCOMPATIBLE": ("The numeric form or measurement unit is incompatible.", "数值形式或计量单位不兼容。"),
    "AFTER_KNOWLEDGE_CUTOFF": ("The item became known after the requested cutoff.", "该项目在请求的知识截止时间之后才可知。"),
    "KNOWLEDGE_TIME_UNKNOWN": ("The time the item became known is missing.", "缺少该项目变为可知的时间。"),
    "COUNTEREVIDENCE_MISSING": ("A favorable interpretation lacks explicit counterevidence.", "有利解释缺少明确的反面证据。"),
    "BRIDGE_INCOMPATIBLE": ("The referenced change cannot support this bridge state.", "被引用的变化不能支持该桥接状态。"),
    "STEP_UNAVAILABLE": ("This bridge step is unavailable.", "该桥接步骤不可用。"),
}


class EnergyProfileError(Exception):
    """A caller or programming error made a valid dossier impossible."""


@dataclasses.dataclass(frozen=True, slots=True)
class BasketMembership:
    basket_id: str
    relation: str
    receipt: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class EnergySelection:
    canonical_theme_id: str | None
    primary_basket_id: str | None
    supplemental_basket_ids: tuple[str, ...]
    subject_ids: tuple[str, ...]
    domain_profile: str = "energy"
    mode: str = "current"


@dataclasses.dataclass(frozen=True, slots=True)
class StructuralClassification:
    provider: str
    version: str
    code: str
    label_en: str
    label_zh: str


@dataclasses.dataclass(frozen=True, slots=True)
class EnergySubject:
    subject_id: str
    issuer_label_en: str
    issuer_label_zh: str
    identity_state: str
    basket_memberships: tuple[BasketMembership, ...]
    security_link_allowed: bool
    structural_classification: StructuralClassification | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class RoleExposure:
    kind: str
    value: Decimal | None = None
    unit: str | None = None
    source_ref: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class RoleFacet:
    vocabulary: str
    kind: str


@dataclasses.dataclass(frozen=True, slots=True)
class EnergyRole:
    role_id: str
    subject_id: str
    role_kind: str
    role_facets: tuple[RoleFacet, ...]
    business_label_en: str
    business_label_zh: str
    relationship_basis: str
    exposure: RoleExposure | None
    rights_state: str
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    authored_by: str = "deterministic"
    attribution: str | None = None
    role_vocabulary: str = ROLE_VOCABULARY


@dataclasses.dataclass(frozen=True, slots=True)
class ChangeClocks:
    publication: str | None = None
    observation: str | None = None
    business_valid_from: str | None = None
    business_valid_to: str | None = None
    retention: str | None = None
    review: str | None = None
    recorded: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    label_en: str
    label_zh: str
    unit: str
    currency: str | None = None
    scale: str | None = None
    basis: str = "reported"
    measure_class: str | None = None
    perimeter: str | None = None
    perimeter_change: str | None = None
    organic: bool | None = None
    period: str | None = None
    prior_period: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ContractTerms:
    index: str | None = None
    formula: str | None = None
    option_holder: str | None = None
    start: str | None = None
    expiry: str | None = None
    volume_scope: str | None = None
    fee_basis: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ChangeValue:
    kind: str = "null"
    point: Decimal | None = None
    low: Decimal | None = None
    high: Decimal | None = None
    text: str | None = None
    precision: int | None = None
    preliminary: bool | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class MilestoneAssertion:
    vocabulary: str
    flag: str
    value: bool | None


@dataclasses.dataclass(frozen=True, slots=True)
class EconomicChange:
    change_id: str
    subject_id: str
    kind: str
    status: str
    revision_kind: str | None = None
    supersedes: str | None = None
    contained_in: str | None = None
    additive_with_siblings: bool | None = None
    clocks: ChangeClocks = ChangeClocks()
    definition: MetricDefinition | None = None
    contract_terms: ContractTerms | None = None
    value: ChangeValue = ChangeValue()
    milestone_assertions: tuple[MilestoneAssertion, ...] = ()
    evidenced_by: str | None = None
    rights_state: str = "admitted"
    source_class: str = "unknown"
    source_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class EconomicBridgeStep:
    subject_id: str
    step_kind: str
    state: str
    value_ref: str | None
    narrative_en: str | None
    narrative_zh: str | None
    authored_by: str = "deterministic"
    attribution: str | None = None
    rights_state: str = "admitted"
    source_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class CapitalOwnershipItem:
    subject_id: str
    item_kind: str
    state: str
    value_refs: tuple[str, ...]
    narrative_en: str | None = None
    narrative_zh: str | None = None
    authored_by: str = "deterministic"
    attribution: str | None = None
    rights_state: str = "admitted"
    source_refs: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ExpectationEstimate:
    value: Decimal
    unit: str
    currency: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class SurpriseVector:
    metric: str
    direction: str


@dataclasses.dataclass(frozen=True, slots=True)
class ExpectationContext:
    expectation_id: str
    subject_id: str
    horizon: str | None
    status: str
    evidence_grade: str
    metric_definition: str | None = None
    fiscal_horizon: str | None = None
    ownership_basis: str | None = None
    aggregate_method: str | None = None
    contributor_count: int | None = None
    panel_turnover: str | None = None
    estimate: ExpectationEstimate | None = None
    first_known_at: str | None = None
    revision_kind: str | None = None
    surprise_vector: tuple[SurpriseVector, ...] = ()
    source_ref: str | None = None
    limitations: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class MarketContext:
    subject_id: str
    event_ref: str | None
    return_window: str
    raw_return: Decimal | None = None
    total_return: Decimal | None = None
    benchmark_residual: Decimal | None = None
    external_reported: bool = False
    commodity_context: str | None = None
    confounds: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Counterevidence:
    counter_id: str
    subject_id: str | None
    against_ref: str
    kind: str
    narrative_en: str
    narrative_zh: str
    authored_by: str = "deterministic"
    attribution: str | None = None
    rights_state: str = "admitted"
    source_refs: tuple[str, ...] = ()
    state: str = "observed"


@dataclasses.dataclass(frozen=True, slots=True)
class RelationshipMagnitude:
    value: Decimal
    unit: str
    source_ref: str


@dataclasses.dataclass(frozen=True, slots=True)
class Relationship:
    relationship_id: str
    src: str
    dst: str
    kind: str
    basis: str
    magnitude: RelationshipMagnitude | None = None
    source_refs: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class NativeContext:
    owner: str
    object: str
    clock: str | None
    label_en: str
    label_zh: str
    authority_note: str


@dataclasses.dataclass(frozen=True, slots=True)
class ComparisonInput:
    role: str
    change_id: str


@dataclasses.dataclass(frozen=True, slots=True)
class CompatibilityCheck:
    check: str
    outcome: str


@dataclasses.dataclass(frozen=True, slots=True)
class ComparisonResult:
    value: Decimal
    unit: str
    currency: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class EconomicComparison:
    comparison_id: str
    subject_id: str | None
    kind: str
    formula_id: str
    formula_version: str
    inputs: tuple[ComparisonInput, ...]
    result: ComparisonResult | None = None
    kind_vocabulary: str | None = None
    compatibility: tuple[CompatibilityCheck, ...] = ()
    rounding: str | None = None
    limitations: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class InputReceipt:
    owner: str
    object: str
    schema: str
    version: str
    digest: str
    selector: str | None = None
    role: str = "source"


@dataclasses.dataclass(frozen=True, slots=True)
class OwnerInputs:
    subjects: tuple[EnergySubject, ...]
    roles: tuple[EnergyRole, ...]
    changes: tuple[EconomicChange, ...]
    comparisons: tuple[EconomicComparison, ...]
    bridge: tuple[EconomicBridgeStep, ...]
    capital_ownership: tuple[CapitalOwnershipItem, ...]
    expectations: tuple[ExpectationContext, ...]
    market_context: tuple[MarketContext, ...]
    counterevidence: tuple[Counterevidence, ...]
    relationships: tuple[Relationship, ...]
    native_context: tuple[NativeContext, ...]
    input_receipts: tuple[InputReceipt, ...]
    authority_bits: Mapping[str, bool] | None = None


def _unavailable(code: str, *, subject_id: str | None = None, detail: str | None = None,
                 conflict_class: str | None = None, domain_code: tuple[str, str] | None = None) -> dict[str, Any]:
    en, zh = _REASONS[code]
    return {
        "code": code,
        "conflict_class": conflict_class,
        "domain_code": {"vocabulary": domain_code[0], "code": domain_code[1]} if domain_code else None,
        "reason": {"en": en, "zh": zh},
        "subject_id": subject_id,
        "detail": detail,
    }


def _decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise TypeError("numeric values must be Decimal")
    if not value.is_finite():
        raise TypeError("numeric values must be finite")
    return format(value, "f")


def _bilingual(en: str | None, zh: str | None) -> dict[str, str | None]:
    return {"en": en, "zh": zh}


def _receipt(item: InputReceipt) -> dict[str, Any]:
    return dataclasses.asdict(item)


def _load_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _generation(receipts: Sequence[dict[str, Any]], definition_version: str, as_of: str,
                knowledge_cutoff: str, selection: EnergySelection) -> str:
    material = {
        "input_receipts": sorted(receipts, key=lambda item: (item["owner"], item["object"], item["role"])),
        "definition_version": definition_version,
        "as_of": as_of,
        "knowledge_cutoff": knowledge_cutoff,
        "selection": {
            "canonical_theme_id": selection.canonical_theme_id,
            "primary_basket_id": selection.primary_basket_id,
            "supplemental_basket_ids": list(selection.supplemental_basket_ids),
            "subject_ids": list(selection.subject_ids),
        },
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _empty_refused(owner_inputs: OwnerInputs, selection: EnergySelection, as_of: str, knowledge_cutoff: str,
                   unavailable: dict[str, Any]) -> dict[str, Any]:
    receipts = [_receipt(item) for item in sorted(owner_inputs.input_receipts, key=lambda x: (x.owner, x.object, x.role))]
    return {
        "schema": "market_ontology.economic_change_dossier/v1",
        "definition_version": "1.0.0",
        "domain_profile": selection.domain_profile,
        "asof": as_of,
        "knowledge_cutoff": knowledge_cutoff,
        "authority_ceiling": "research_display_only",
        "display_only": True,
        "authority": {key: False for key in ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry", "can_veto")},
        "scope": {"canonical_theme_id": selection.canonical_theme_id, "primary_basket_id": selection.primary_basket_id,
                  "supplemental_basket_ids": list(selection.supplemental_basket_ids), "research_facet": None,
                  "geography": None, "currency": None},
        "subjects": [], "roles": [], "changes": [], "comparisons": [], "bridge": [], "capital_ownership": [],
        "expectations": [], "market_context": [], "counterevidence": [], "relationships": [], "native_context": [],
        "coverage": {"subjects_selected": len(selection.subject_ids), "subjects_ready": 0, "subjects_unavailable": len(selection.subject_ids),
                     "changes_admitted": 0, "changes_restricted": 0, "rights_blocked": 0, "unresolved_identities": len(selection.subject_ids),
                     "bounds": BOUNDS, "generation": _generation(receipts, "1.0.0", as_of, knowledge_cutoff, selection)},
        "unavailable": [unavailable], "continuation": None,
        "provenance": {"composer": "engine.market_ontology.energy_economic_change.compose_energy_profile",
                       "engine_version": "1.0.0", "mode": selection.mode, "input_receipts": receipts,
                       "model_attribution_policy": "attributed_narrative_only_never_facts"},
    }


def compose_energy_profile(selection: EnergySelection, *, owner_inputs: OwnerInputs, as_of: str,
                           knowledge_cutoff: str) -> dict[str, Any]:
    if not isinstance(selection, EnergySelection) or not isinstance(owner_inputs, OwnerInputs):
        raise EnergyProfileError("selection and owner_inputs must use the frozen dataclasses")
    if knowledge_cutoff > as_of:
        raise EnergyProfileError("knowledge_cutoff must not be later than as_of")
    if any(bool(bit) for bit in (owner_inputs.authority_bits or {}).values()):
        return _empty_refused(owner_inputs, selection, as_of, knowledge_cutoff,
                              _unavailable("AUTHORITY_BIT_REJECTED"))
    if len(selection.subject_ids) > BOUNDS["subjects"]:
        return _empty_refused(owner_inputs, selection, as_of, knowledge_cutoff,
                              _unavailable("OVERSIZE_SELECTION", detail=f"subjects={len(selection.subject_ids)}"))
    unavailable: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    admitted_change_ids: set[str] = set()
    change_inputs = {item.change_id: item for item in owner_inputs.changes}
    subject_ids = set(selection.subject_ids)

    subjects: list[dict[str, Any]] = []
    for subject in sorted(owner_inputs.subjects, key=lambda item: item.subject_id):
        if subject.subject_id not in subject_ids:
            continue
        security_allowed = subject.security_link_allowed and subject.identity_state == "resolved"
        if subject.security_link_allowed and subject.identity_state != "resolved":
            unavailable.append(_unavailable("IDENTITY_UNRESOLVED", subject_id=subject.subject_id, detail="security_link_forced_false"))
        memberships = []
        for membership in sorted(subject.basket_memberships, key=lambda item: item.basket_id):
            relation = membership.relation
            receipt_relation = None
            if membership.receipt and ":" in membership.receipt:
                receipt_relation = membership.receipt.rsplit(":", 1)[1]
            if receipt_relation in {"primary_member", "supplemental_member"} and receipt_relation != relation:
                relation = receipt_relation
                unavailable.append(_unavailable("IDENTITY_UNRESOLVED", subject_id=subject.subject_id, detail="basket_relation_conflict"))
            memberships.append({"basket_id": membership.basket_id, "relation": relation, "receipt": membership.receipt})
        structural = None
        if subject.structural_classification is not None:
            structural = dataclasses.asdict(subject.structural_classification)
            structural["label"] = _bilingual(structural.pop("label_en"), structural.pop("label_zh"))
        subjects.append({"subject_id": subject.subject_id, "issuer_label": _bilingual(subject.issuer_label_en, subject.issuer_label_zh),
                         "identity_state": subject.identity_state, "basket_memberships": memberships,
                         "security_link_allowed": security_allowed, "structural_classification": structural})
        if subject.identity_state != "resolved":
            unavailable.append(_unavailable("IDENTITY_UNRESOLVED", subject_id=subject.subject_id))

    roles: list[dict[str, Any]] = []
    for role in sorted(owner_inputs.roles, key=lambda item: item.role_id):
        label_valid = bool(role.business_label_en and role.business_label_zh)
        if role.role_vocabulary not in _REGISTERED_VOCABULARIES or role.role_kind not in ROLE_KINDS or (
                role.role_kind == "other" and (not role.limitations or not label_valid)):
            unavailable.append(_unavailable("ROLE_KIND_UNKNOWN", subject_id=role.subject_id, detail=f"role_id={role.role_id}"))
            continue
        exposure = None
        if role.exposure is not None:
            value = _decimal(role.exposure.value)
            if role.exposure.kind == "unknown":
                value = None
            if value is not None and not role.exposure.source_ref:
                unavailable.append(_unavailable("SOURCE_UNAVAILABLE", subject_id=role.subject_id, detail=f"role_id={role.role_id}"))
                value = None
            exposure = {"kind": role.exposure.kind, "value": value, "unit": role.exposure.unit,
                        "source_ref": role.exposure.source_ref}
        roles.append({"role_id": role.role_id, "subject_id": role.subject_id, "role_vocabulary": role.role_vocabulary,
                      "role_kind": role.role_kind,
                      "role_facets": [{"vocabulary": facet.vocabulary, "kind": facet.kind} for facet in role.role_facets],
                      "business_label": _bilingual(role.business_label_en, role.business_label_zh),
                      "relationship_basis": role.relationship_basis, "exposure": exposure, "rights_state": role.rights_state,
                      "source_refs": list(role.source_refs), "limitations": list(role.limitations),
                      "status": "ready" if role.rights_state == "admitted" else "degraded",
                      "authored_by": role.authored_by, "attribution": role.attribution})

    for change in sorted(owner_inputs.changes, key=lambda item: item.change_id):
        numeric = any(value is not None for value in (change.value.point, change.value.low, change.value.high))
        try:
            point, low, high = _decimal(change.value.point), _decimal(change.value.low), _decimal(change.value.high)
        except (TypeError, InvalidOperation):
            unavailable.append(_unavailable("UNIT_INCOMPATIBLE", subject_id=change.subject_id, detail="numeric_form"))
            continue
        if numeric and not change.source_refs:
            unavailable.append(_unavailable("SOURCE_UNAVAILABLE", subject_id=change.subject_id, detail=f"change_id={change.change_id}"))
            continue
        known = [change.clocks.publication, change.clocks.recorded]
        if all(value is None for value in known):
            unavailable.append(_unavailable("KNOWLEDGE_TIME_UNKNOWN", subject_id=change.subject_id, detail=f"change_id={change.change_id}"))
            continue
        if any(value and value[:10] > knowledge_cutoff for value in known):
            unavailable.append(_unavailable("AFTER_KNOWLEDGE_CUTOFF", subject_id=change.subject_id, detail=f"change_id={change.change_id}"))
            continue
        assertions = []
        assertion_failed = False
        for assertion in change.milestone_assertions:
            value = assertion.value
            if (change.kind == "milestone" and assertion.vocabulary == "core_milestone_flags.v1"
                    and assertion.flag == "establishes_current_operation" and value is True):
                evidence = change_inputs.get(change.evidenced_by)
                if evidence is None or evidence.kind != "reported_measure" or evidence.status not in {"observed", "historical"}:
                    value = None
                    assertion_failed = True
                    unavailable.append(_unavailable("MILESTONE_NOT_OPERATING", subject_id=change.subject_id, detail=f"change_id={change.change_id}"))
            assertions.append({"vocabulary": assertion.vocabulary, "flag": assertion.flag, "value": value})
        rights_restricted = change.rights_state != "admitted"
        if rights_restricted:
            unavailable.append(_unavailable("RIGHTS_RESTRICTED", subject_id=change.subject_id, detail=f"change_id={change.change_id}"))
        value_kind = None if rights_restricted or change.value.kind == "null" else change.value.kind
        value_payload = {"kind": value_kind,
                         "point": None if rights_restricted or assertion_failed else point,
                         "low": None if rights_restricted else low, "high": None if rights_restricted else high,
                         "text": None if rights_restricted else change.value.text,
                         "precision": change.value.precision, "preliminary": change.value.preliminary}
        definition = None
        if change.definition is not None:
            definition = dataclasses.asdict(change.definition)
            definition["label"] = _bilingual(definition.pop("label_en"), definition.pop("label_zh"))
        contract = dataclasses.asdict(change.contract_terms) if change.contract_terms is not None else None
        changes.append({"change_id": change.change_id, "subject_id": change.subject_id, "kind": change.kind,
                        "status": change.status, "revision_kind": change.revision_kind, "supersedes": change.supersedes,
                        "contained_in": change.contained_in, "additive_with_siblings": change.additive_with_siblings,
                        "clocks": dataclasses.asdict(change.clocks), "definition": definition, "contract_terms": contract,
                        "value": value_payload, "milestone_assertions": assertions, "evidenced_by": change.evidenced_by,
                        "rights_state": change.rights_state, "source_class": change.source_class,
                        "source_refs": list(change.source_refs), "limitations": list(change.limitations)})
        if not assertion_failed:
            admitted_change_ids.add(change.change_id)

    comparisons: list[dict[str, Any]] = []
    for comparison in sorted(owner_inputs.comparisons, key=lambda item: item.comparison_id):
        definitions = [change_inputs[item.change_id].definition for item in comparison.inputs if item.change_id in change_inputs]
        checks = [{"check": item.check, "outcome": item.outcome} for item in comparison.compatibility]
        units = [item.unit for item in definitions if item is not None]
        currencies = [item.currency for item in definitions if item is not None]
        periods = [item.period for item in definitions if item is not None]
        basises = [item.basis for item in definitions if item is not None]
        contained = [change_inputs[item.change_id].contained_in for item in comparison.inputs if item.change_id in change_inputs]
        if len(set(units)) > 1: checks.append({"check": "unit", "outcome": "failed"})
        if len(set(currencies)) > 1: checks.append({"check": "currency", "outcome": "failed"})
        if len(set(periods)) > 1: checks.append({"check": "period", "outcome": "failed"})
        if len(set(basises)) > 1: checks.append({"check": "ownership_basis", "outcome": "failed"})
        comparison_ids = [item.change_id for item in comparison.inputs]
        if any(container in comparison_ids for container in contained):
            checks.append({"check": "containment", "outcome": "failed"})
        failed = any(item["outcome"] != "passed" for item in checks) or len(comparison.inputs) < 2
        result = None
        if not failed and comparison.result is not None:
            result = {"value": _decimal(comparison.result.value), "unit": comparison.result.unit, "currency": comparison.result.currency}
        comparisons.append({"comparison_id": comparison.comparison_id, "subject_id": comparison.subject_id, "kind": comparison.kind,
                            "kind_vocabulary": comparison.kind_vocabulary,
                            "inputs": [{"role": item.role, "change_id": item.change_id} for item in comparison.inputs],
                            "compatibility": checks, "formula_id": comparison.formula_id,
                            "formula_version": comparison.formula_version, "result": result, "rounding": comparison.rounding,
                            "unavailable_code": ("DEFINITION_INCOMPATIBLE" if any(item["check"] in {"ownership_basis", "containment", "metric", "horizon"} for item in checks if item["outcome"] != "passed") else "UNIT_INCOMPATIBLE") if failed else None,
                            "authored_by": "deterministic", "limitations": list(comparison.limitations)})

    counter_refs = {item.against_ref for item in owner_inputs.counterevidence}
    bridge: list[dict[str, Any]] = []
    bridge_by_subject: dict[tuple[str, str], EconomicBridgeStep] = {
        (item.subject_id, item.step_kind): item for item in owner_inputs.bridge}
    for subject_id in sorted(subject_ids):
        for step_kind in STEP_KINDS:
            step = bridge_by_subject.get((subject_id, step_kind))
            if step is None:
                bridge.append({"subject_id": subject_id, "step_order": _STEP_ORDER[step_kind], "step_kind": step_kind,
                               "state": "unavailable", "value_ref": None, "narrative": None, "authored_by": "deterministic",
                               "attribution": None, "rights_state": "unavailable", "source_refs": [], "assumptions": []})
                continue
            state = step.state
            ref = step.value_ref
            change = change_inputs.get(step.value_ref)
            reason = None
            if change is not None:
                if state == "observed" and change.status not in {"observed", "historical"}:
                    state = "unavailable"
                    reason = "CONTINGENT_NOT_FUNDED" if change.status == "contingent" else "BRIDGE_INCOMPATIBLE"
                elif change.kind == "milestone" and any(
                    assertion.flag in {"site_operating_license", "operating_generation", "commercial_grid_generation"}
                    and assertion.value is not True
                    for assertion in change.milestone_assertions
                ):
                    state = "unavailable"; reason = "MILESTONE_NOT_OPERATING"
                elif change.kind not in _BRIDGE_CHANGE_KINDS.get(step.step_kind, (change.kind,)):
                    state = "unavailable"; reason = "BRIDGE_INCOMPATIBLE"
                elif change.definition is not None and change.definition.basis not in _BRIDGE_BASES.get(step.step_kind, (change.definition.basis,)):
                    state = "unavailable"; reason = "BRIDGE_INCOMPATIBLE"
                elif (state == "observed" and change.definition is not None
                      and change.definition.perimeter_change == "accounting_policy"):
                    state = "forward"; reason = "BRIDGE_INCOMPATIBLE"
                elif change.change_id not in admitted_change_ids:
                    state = "unavailable"; reason = "MILESTONE_NOT_OPERATING"
            bridge_ref = f"bridge:{subject_id}:{step_kind}"
            if state in {"observed", "forward"} and bridge_ref not in counter_refs:
                state = "unavailable"; reason = "COUNTEREVIDENCE_MISSING"
            if reason:
                unavailable.append(_unavailable(reason, subject_id=subject_id, detail=f"step_kind={step_kind}"))
            narrative = None if step.rights_state != "admitted" else _bilingual(step.narrative_en, step.narrative_zh)
            if step.rights_state != "admitted":
                unavailable.append(_unavailable("RIGHTS_RESTRICTED", subject_id=subject_id, detail=f"step_kind={step_kind}"))
            bridge.append({"subject_id": subject_id, "step_order": _STEP_ORDER[step_kind], "step_kind": step_kind,
                           "state": "restricted" if step.rights_state != "admitted" else state, "value_ref": ref,
                           "narrative": narrative, "authored_by": step.authored_by, "attribution": step.attribution,
                           "rights_state": step.rights_state, "source_refs": list(step.source_refs),
                           "assumptions": list(step.assumptions)})

    capital = []
    for item in sorted(owner_inputs.capital_ownership, key=lambda value: (value.subject_id, value.item_kind)):
        narrative = None if item.rights_state != "admitted" else _bilingual(item.narrative_en, item.narrative_zh)
        capital.append({"subject_id": item.subject_id, "item_kind": item.item_kind, "state": item.state,
                        "value_refs": list(item.value_refs), "narrative": narrative, "authored_by": item.authored_by,
                        "attribution": item.attribution, "rights_state": item.rights_state, "source_refs": list(item.source_refs)})

    expectation_records: dict[str, list[dict[str, Any]]] = {subject_id: [] for subject_id in subject_ids}
    expectations = []
    for item in sorted(owner_inputs.expectations, key=lambda value: value.expectation_id):
        status = item.status
        estimate = None
        grade_ok = item.evidence_grade in {"PRE_EVENT_TIMESTAMPED_VALUE", "ISSUER_PROCESS_PLUS_ARCHIVE"}
        cutoff_ok = bool(item.first_known_at and item.first_known_at[:10] <= knowledge_cutoff)
        if status == "AVAILABLE" and (not grade_ok or not cutoff_ok):
            status = "INCOMPATIBLE"
            unavailable.append(_unavailable("EVIDENCE_GRADE_INSUFFICIENT", subject_id=item.subject_id, detail=f"expectation_id={item.expectation_id}"))
        elif status == "UNAVAILABLE":
            unavailable.append(_unavailable("EXPECTATIONS_UNAVAILABLE", subject_id=item.subject_id, detail=f"expectation_id={item.expectation_id}"))
        if status == "AVAILABLE" and item.estimate is not None:
            estimate = {"value": _decimal(item.estimate.value), "unit": item.estimate.unit, "currency": item.estimate.currency}
        record = {"expectation_id": item.expectation_id, "subject_id": item.subject_id, "horizon": item.horizon,
                  "status": status, "evidence_grade": item.evidence_grade, "metric_definition": item.metric_definition,
                  "fiscal_horizon": item.fiscal_horizon, "ownership_basis": item.ownership_basis,
                  "aggregate_method": item.aggregate_method, "contributor_count": item.contributor_count,
                  "panel_turnover": item.panel_turnover, "estimate": estimate, "first_known_at": item.first_known_at,
                  "revision_kind": item.revision_kind,
                  "surprise_vector": [{"metric": vector.metric, "direction": vector.direction} for vector in item.surprise_vector],
                  "forced_beat_miss_bit": False, "source_ref": item.source_ref, "limitations": list(item.limitations)}
        expectations.append(record); expectation_records.setdefault(item.subject_id, []).append(record)
    for subject_id in sorted(subject_ids):
        if not expectation_records.get(subject_id):
            record = {"expectation_id": f"unavailable:{subject_id}:expectations", "subject_id": subject_id,
                      "horizon": None, "status": "UNAVAILABLE", "evidence_grade": "UNAVAILABLE",
                      "metric_definition": None, "fiscal_horizon": None, "ownership_basis": None, "aggregate_method": None,
                      "contributor_count": None, "panel_turnover": None, "estimate": None, "first_known_at": None,
                      "revision_kind": None, "surprise_vector": [], "forced_beat_miss_bit": False, "source_ref": None,
                      "limitations": ["No owner-supplied expectation is available."]}
            expectations.append(record)
            unavailable.append(_unavailable("EXPECTATIONS_UNAVAILABLE", subject_id=subject_id, detail="expectation_id=unavailable"))
    expectations.sort(key=lambda item: item["expectation_id"])

    market = []
    for item in sorted(owner_inputs.market_context, key=lambda value: (value.subject_id, value.event_ref or "")):
        market.append({"subject_id": item.subject_id, "event_ref": item.event_ref, "return_window": item.return_window,
                       "raw_return": _decimal(item.raw_return), "total_return": _decimal(item.total_return),
                       "benchmark_residual": _decimal(item.benchmark_residual), "residual_is_alpha": False,
                       "external_reported": item.external_reported, "commodity_context": item.commodity_context,
                       "confounds": list(item.confounds), "source_refs": list(item.source_refs)})

    counters = []
    for item in sorted(owner_inputs.counterevidence, key=lambda value: value.counter_id):
        counters.append({"counter_id": item.counter_id, "subject_id": item.subject_id, "against_ref": item.against_ref,
                         "kind": item.kind, "narrative": _bilingual(item.narrative_en, item.narrative_zh),
                         "authored_by": item.authored_by, "attribution": item.attribution, "rights_state": item.rights_state,
                         "source_refs": list(item.source_refs), "state": item.state})

    relationships = []
    for item in sorted(owner_inputs.relationships, key=lambda value: value.relationship_id):
        if item.basis == "source_backed" and not item.source_refs:
            unavailable.append(_unavailable("SOURCE_UNAVAILABLE", detail=f"relationship_id={item.relationship_id}"))
            continue
        against = item.relationship_id
        if item.basis == "hypothesis" and against not in counter_refs:
            unavailable.append(_unavailable("COUNTEREVIDENCE_MISSING", detail=f"relationship_id={item.relationship_id}"))
            continue
        magnitude = None
        if item.basis != "hypothesis" and item.magnitude is not None:
            magnitude = {"value": _decimal(item.magnitude.value), "unit": item.magnitude.unit, "source_ref": item.magnitude.source_ref}
        relationships.append({"relationship_id": item.relationship_id, "src": item.src, "dst": item.dst, "kind": item.kind,
                              "basis": item.basis, "magnitude": magnitude, "source_refs": list(item.source_refs)})

    native = []
    for item in sorted(owner_inputs.native_context, key=lambda value: (value.owner, value.object)):
        native.append({"owner": item.owner, "object": item.object, "clock": item.clock,
                       "label": _bilingual(item.label_en, item.label_zh), "authority_note": item.authority_note})

    receipts = [_receipt(item) for item in owner_inputs.input_receipts]
    payload = {
        "schema": "market_ontology.economic_change_dossier/v1", "definition_version": "1.0.0",
        "domain_profile": selection.domain_profile, "asof": as_of, "knowledge_cutoff": knowledge_cutoff,
        "authority_ceiling": "research_display_only", "display_only": True,
        "authority": {key: False for key in ("can_rank", "can_gate", "can_size", "can_originate", "can_open_entry", "can_veto")},
        "scope": {"canonical_theme_id": selection.canonical_theme_id, "primary_basket_id": selection.primary_basket_id,
                  "supplemental_basket_ids": list(selection.supplemental_basket_ids), "research_facet": None,
                  "geography": None, "currency": None},
        "subjects": subjects, "roles": roles, "changes": changes, "comparisons": comparisons, "bridge": bridge,
        "capital_ownership": capital, "expectations": expectations, "market_context": market,
        "counterevidence": counters, "relationships": relationships, "native_context": native,
        "coverage": {"subjects_selected": len(selection.subject_ids), "subjects_ready": len({role["subject_id"] for role in roles if role["status"] == "ready"}),
                     "subjects_unavailable": max(0, len(subject_ids) - len({role["subject_id"] for role in roles if role["status"] == "ready"})),
                     "changes_admitted": len(changes), "changes_restricted": sum(change["rights_state"] != "admitted" for change in changes),
                     "rights_blocked": sum(change["rights_state"] != "admitted" for change in changes),
                     "unresolved_identities": sum(subject["identity_state"] != "resolved" for subject in subjects),
                     "bounds": BOUNDS, "generation": _generation(receipts, "1.0.0", as_of, knowledge_cutoff, selection)},
        "unavailable": sorted(unavailable, key=lambda item: (item["code"], item["subject_id"] or "", item["detail"] or "")),
        "continuation": None,
        "provenance": {"composer": "engine.market_ontology.energy_economic_change.compose_energy_profile",
                       "engine_version": "1.0.0", "mode": selection.mode, "input_receipts": sorted(receipts, key=lambda item: (item["owner"], item["object"], item["role"])),
                       "model_attribution_policy": "attributed_narrative_only_never_facts"},
    }
    try:
        jsonschema.Draft202012Validator(_load_schema(), format_checker=jsonschema.FormatChecker()).validate(payload)
    except jsonschema.ValidationError as error:
        raise EnergyProfileError(f"composed dossier failed schema validation: {error.message}") from error
    return payload
