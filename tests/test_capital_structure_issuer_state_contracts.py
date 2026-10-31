"""Contract tests for the frozen ``capital_structure.state.v2`` types (masterplan C0).

Every record kind the owner modules exchange is built here through the typed
factories and validated against ``contracts/capital_structure_state.v2.schema.json``.
The negative tests pin the acceptance rows the masterplan assigns to C0:

* A06 — version compatibility with ``capital_structure.projection_bundle.v1``;
  removing an inherited unavailable label requires a capability proof.
* A20 — unknown is never zero and never infinite.
* A21 — a joint envelope never sums shared-pool maxima.
* A31 — current, then-known and scenario views stay distinct.
* A32 — an assumption change is a new scenario identity.
* A48 — no probability, score, rank, sizing, entry or Prophet authority.
"""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import re
from decimal import Decimal
from pathlib import Path

import pytest

from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure import projection

ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64
AS_OF = "2026-10-13T12:00:00Z"
GENERATED_AT = "2026-10-13T12:05:00Z"
GEN = "gen:cs:2026-10-13T12"
ISSUER = "cik:0001234567"
CLASS = "class:common:0001234567"
IMPLEMENTATION = "engine.capital_structure.issuer_state_contracts:test"


# ---------------------------------------------------------------------------
# Factories — one valid instance of every record kind
# ---------------------------------------------------------------------------


def ev(n: int = 1) -> c.EvidenceRef:
    return c.EvidenceRef(f"manifest:{n}", f"span:{n}", HASH)


def rule_pack() -> c.RulePack:
    return c.RulePack(
        rule_pack_id="rules:sec-equity-2026",
        version="2026.10",
        source_edition="17 CFR 230/239 (e-CFR 2026-04-01)",
        jurisdiction="US",
        effective_date="2026-04-01",
        interpretation_date="2026-10-13",
        rules=(
            c.RuleRef(
                "rule:form-s3-ib6",
                "binding_rule",
                "Form S-3 General Instruction I.B.6",
                True,
                effective_from="2008-01-28",
                required_issuer_facts=("non_affiliate_public_float",),
            ),
            c.RuleRef("rule:33-11418", "proposed_reform", "Release No. 33-11418 (proposed)", False),
        ),
        venues=("NASDAQ",),
        forms=("S-3",),
    )


def bindings() -> dict[str, c.GenerationBinding]:
    return {
        "event_projection": c.GenerationBinding(
            "event_projection", "capital_structure.projection_bundle.v1", "supported", generation_id=GEN, as_of=AS_OF
        ),
        "events": c.GenerationBinding("events", "capital_structure.event.v1", "supported", generation_id=GEN),
        "event_edges": c.GenerationBinding("event_edges", "capital_structure.event_edge.v1", "supported", generation_id=GEN),
        "registration_lifecycle": c.GenerationBinding(
            "registration_lifecycle", "capital_structure.registration_lifecycle_bundle.v1", "supported", generation_id=GEN
        ),
        "document_terms": c.GenerationBinding(
            "document_terms", "capital_structure.document_term_observation.v1", "partial", generation_id=GEN
        ),
        "covenant_terms": c.GenerationBinding("covenant_terms", None, "unavailable"),
        "instrument_candidate_terms": c.GenerationBinding(
            "instrument_candidate_terms", "capital_structure.instrument_candidate_term.v1", "supported", generation_id=GEN
        ),
        "share_count_observations": c.GenerationBinding(
            "share_count_observations", "capital_structure.share_count_observation.v2", "supported", generation_id=GEN
        ),
        "financials": c.GenerationBinding("financials", None, "not_built"),
        "corrections": c.GenerationBinding("corrections", None, "not_built"),
    }


def request(view_mode: str = "current", **over) -> c.StateRequest:
    pack = rule_pack()
    kw = dict(
        issuer_id=ISSUER,
        as_of=AS_OF,
        view_mode=view_mode,
        input_generations=tuple(bindings().values()),
        rule_pack_id=pack.rule_pack_id,
        rule_pack_version=pack.version,
        rule_pack_digest=pack.digest,
        security_class_id=CLASS,
    )
    kw.update(over)
    return c.StateRequest(**kw)


def inputs() -> c.CapitalInputs:
    return c.CapitalInputs(
        bindings=tuple(bindings().values()),
        events=({"schema": "capital_structure.event.v1", "event_id": "evt:1", "kind": "shelf_effective"},),
        share_observations=(
            {"schema": "capital_structure.share_count_observation.v2", "observation_id": "obs:1", "value": "10000000"},
        ),
    )


def receipt(scenario_id: str | None = None) -> c.CalculationReceipt:
    return c.CalculationReceipt.build(
        inputs=inputs(),
        rule_digest=rule_pack().digest,
        implementation=IMPLEMENTATION,
        computed_at=GENERATED_AT,
        scenario_id=scenario_id,
    )


_FAMILY_INPUTS = {
    "identity": ("event_projection", "capital_structure.projection_bundle.v1", "supported"),
    "share_basis": ("share_count_observations", "capital_structure.share_count_observation.v2", "supported"),
    "registration": ("registration_lifecycle", "capital_structure.registration_lifecycle_bundle.v1", "supported"),
    "instruments": ("instrument_candidate_terms", "capital_structure.instrument_candidate_term.v1", "partial"),
    "cash_funding": ("financials", None, "not_built"),
    "transactions": ("events", "capital_structure.event.v1", "supported"),
    "uncertainty": ("event_projection", "capital_structure.projection_bundle.v1", "supported"),
    "change_events": ("corrections", None, "not_built"),
}


def family_provenance(family: str, **over) -> c.FamilyProvenance:
    input_family, schema, support = _FAMILY_INPUTS[family]
    kw = dict(family=family, input_family=input_family, input_schema=schema, support=support, as_of=AS_OF)
    if support in ("supported", "partial"):
        kw.update(compiler_version=c.STATE_CONTRACT_VERSION, generation_id=GEN)
    if support == "partial":
        kw.update(support_limits=("unresolved candidates are not instruments",))
    kw.update(over)
    return c.FamilyProvenance(**kw)


def family_state(family: str) -> c.FamilyState:
    prov = family_provenance(family)
    if prov.support in ("unavailable", "not_built"):
        return c.FamilyState(family, prov, unavailable=(f"{family}: no compiler built",))
    return c.FamilyState(
        family, prov, records=({"schema": prov.input_schema, "family": family, "record_id": f"{family}:1"},)
    )


def families() -> tuple[c.FamilyState, ...]:
    return tuple(family_state(family) for family in c.STATE_FAMILIES)


def state(**over) -> c.CapitalState:
    kw = dict(
        request=request(), generated_at=GENERATED_AT, families=families(), receipt=receipt(), projection_generation_id=GEN
    )
    kw.update(over)
    return c.CapitalState(**kw)


def scenario(**over) -> c.FinancingScenario:
    kw = dict(
        view="counterfactual",
        as_of=AS_OF,
        horizon_start="2026-10-13",
        horizon_end="2027-10-13",
        price=c.PriceAssumption("fixed", "USD", fixed_price="2.50"),
        actions=(c.ActionSelection("route:atm", "at_the_market", "cash", quantity=c.Quantity.known("8000000", "usd")),),
        fee_rate="0.03",
        discount_rate=None,
        other_assumptions=(("warrant_exercise", "none"),),
        unknown_resolutions=(),
        label="base case",
    )
    kw.update(over)
    return c.FinancingScenario(**kw)


def route(route_id: str, limit: str, kind: str = "at_the_market", **over) -> c.RouteBound:
    kw = dict(
        route_id=route_id,
        route_kind=kind,
        limit=c.Quantity.known(limit, "usd"),
        status="eligible",
        consumes=("pool:shelf-s3",),
        applicability="Form S-3 I.B.6 baby-shelf cap applies while public float < $75M",
        evidence=(ev(1),),
    )
    kw.update(over)
    return c.RouteBound(**kw)


def pool(bound: str | None = "10000000", **over) -> c.Constraint:
    kw = dict(
        constraint_id="pool:shelf-s3",
        kind="dollars",
        bound=c.Quantity.known(bound, "usd") if bound is not None else c.Quantity.unknown("usd"),
        status="binding" if bound is not None else "unknown",
        stock_or_flow="stock",
        shared_by=("route:atm", "route:takedown"),
        applicability="remaining S-3 shelf balance",
        evidence=(ev(2),),
    )
    kw.update(over)
    return c.Constraint(**kw)


def capacity(aggregate: str | None = "10000000", **over) -> c.CapacityEnvelope:
    sc = scenario()
    kw = dict(
        state_id=state().state_id,
        scenario_id=sc.scenario_id,
        rule_pack_digest=rule_pack().digest,
        routes=(route("route:atm", "8000000"), route("route:takedown", "7000000", kind="shelf_takedown")),
        aggregate_bound=c.Quantity.known(aggregate, "usd") if aggregate is not None else c.Quantity.unknown("usd"),
        receipt=receipt(scenario_id=sc.scenario_id),
        shared_pools=(pool(),),
        binding_constraints=("pool:shelf-s3",),
        feasible_witness=(
            c.WitnessAllocation("route:atm", c.Quantity.known("8000000", "usd")),
            c.WitnessAllocation("route:takedown", c.Quantity.known("2000000", "usd")),
        ),
    )
    kw.update(over)
    return c.CapacityEnvelope(**kw)


def shares(value: str, basis: str) -> c.Quantity:
    return c.Quantity.known(value, "shares", share_basis=basis, security_class_id=CLASS)


def supply(**over) -> c.SupplyEnvelope:
    sc = scenario()
    kw = dict(
        state_id=state().state_id,
        scenario_id=sc.scenario_id,
        existing_outstanding=shares("10000000", "issued_and_outstanding"),
        incremental_issuance=shares("3200000", "scenario_incremental_issuance"),
        as_converted_claims=c.Quantity.unknown("shares", share_basis="assumed_as_converted", security_class_id=CLASS),
        resalable_existing=shares("1500000", "potentially_resalable_existing"),
        receipt=receipt(scenario_id=sc.scenario_id),
        cash_effects=(
            c.CashEffect("route:atm", "proceeds", c.Quantity.known("8000000", "usd"), c.Quantity.known("7760000", "usd")),
        ),
        double_count_guards=("pre-funded warrants carry no second cash leg",),
        unknowns=(
            c.Unknown(
                "unknown:convertible-ratio",
                "conversion price of the 2025 note is not yet disclosed",
                "an indenture exhibit or 8-K stating the conversion price",
                affects=("as_converted_claims",),
            ),
        ),
    )
    kw.update(over)
    return c.SupplyEnvelope(**kw)


def flow(flow_id: str, kind: str, amount: str, certainty: str = "contractual_dated", dated: str | None = "2026-11-15", condition: str | None = None) -> c.Flow:
    return c.Flow(flow_id, kind, f"{kind} {flow_id}", c.Quantity.known(amount, "usd"), certainty, dated=dated, condition=condition)


def period(closing: str = "9500000", sources=None, uses=None, **over) -> c.FundingPeriod:
    kw = dict(
        period_start="2026-10-01",
        period_end="2026-12-31",
        opening_balance=c.Quantity.known("5000000", "usd"),
        closing_balance=c.Quantity.known(closing, "usd"),
        minimum_liquidity=c.Quantity.known("2000000", "usd"),
        gap=c.Quantity.known("0", "usd"),
        sources=sources if sources is not None else (flow("flow:atm-proceeds", "source", "7760000"),),
        uses=uses if uses is not None else (flow("flow:opex", "use", "3260000", certainty="assumed", dated=None),),
    )
    kw.update(over)
    return c.FundingPeriod(**kw)


def funding(**over) -> c.FundingSchedule:
    sc = scenario()
    kw = dict(
        state_id=state().state_id,
        scenario_id=sc.scenario_id,
        cash_basis="unrestricted_cash",
        receipt=receipt(scenario_id=sc.scenario_id),
        periods=(period(),),
        assumptions=tuple(
            c.Assumption(key, "trailing-two-quarter average", "no issuer guidance on file")
            for key in c.REQUIRED_FUNDING_ASSUMPTIONS
        ),
        unknowns=(),
    )
    kw.update(over)
    return c.FundingSchedule(**kw)


def instrument(status: str = "outstanding", method: str = "supported_identity", **over) -> c.Instrument:
    if method == "unresolved":
        resolution = c.Resolution("unresolved")
    else:
        resolution = c.Resolution(method, decision_id="decision:1", evidence=(ev(3),), decided_at=AS_OF)
    kw = dict(
        instrument_id="inst:warrant-2025",
        security_class_id="class:warrant:2025",
        kind="warrant",
        status=status,
        candidate_term_ids=("cand:1",),
        resolution=resolution,
        outstanding=None if status == "unresolved_candidate" else shares("1200000", "reserved_for_issuance"),
        provenance=c.Provenance("instrument_candidate_terms", generation_id=GEN, evidence=(ev(3),)),
    )
    kw.update(over)
    return c.Instrument(**kw)


def instrument_set(**over) -> c.InstrumentSet:
    kw = dict(
        issuer_id=ISSUER,
        as_of=AS_OF,
        instruments=(instrument(),),
        provenance=family_provenance("instruments"),
        receipt=receipt(),
        unresolved_candidate_ids=("cand:2",),
    )
    kw.update(over)
    return c.InstrumentSet(**kw)


def observation(obs_id: str = "obs:10q-2026-08", value: str = "10000000", basis: str = "issued_and_outstanding", as_of_date: str = "2026-08-10") -> c.ShareObservationRef:
    return c.ShareObservationRef(
        obs_id, basis, as_of_date, CLASS, value=value,
        source=c.Provenance("share_count_observations", generation_id=GEN, evidence=(ev(4),)),
    )


def share_basis(status: str = "selected", **over) -> c.ShareBasisResult:
    kw = dict(
        issuer_id=ISSUER,
        security_class_id=CLASS,
        as_of=AS_OF,
        status=status,
        provenance=family_provenance("share_basis"),
        receipt=receipt(),
        selected=shares("10000000", "issued_and_outstanding") if status == "selected" else None,
        candidates=(observation(), observation("obs:8k-cover-2026-09", as_of_date="2026-09-30")),
        conflicts=(),
        corporate_action=c.CorporateActionBasis(),
    )
    kw.update(over)
    return c.ShareBasisResult(**kw)


def scenario_result(**over) -> c.ScenarioResult:
    """One valid S0 composed result, built from the three component factories above."""
    sc = scenario()
    st = state()
    usd = lambda value: c.Quantity.known(value, "usd")  # noqa: E731 - fixture shorthand
    issued = lambda value: shares(value, "scenario_incremental_issuance")  # noqa: E731
    kw = dict(
        result_id=c.stable_id(
            "scenario_result", {"scenario_id": sc.scenario_id, "state_id": st.state_id}
        ),
        scenario_id=sc.scenario_id,
        state_id=st.state_id,
        scenario_view=sc.view,
        state_view_mode=st.request.view_mode,
        as_of=sc.as_of,
        capacity_envelope=capacity(),
        supply_envelope=supply(),
        funding_schedule=funding(),
        action_checks=(
            c.ActionCheck("route:atm", "at_the_market", "cash", "within_capacity", "capacity", True),
        ),
        joint_check=c.JointCheck("feasible", "known", ("pool:shelf-s3",)),
        cash_reconciliation=(
            c.CashReconciliation(
                "route:atm", "capacity", usd("8000000"), usd("7760000"), usd("8000000"), "agree"
            ),
        ),
        issuance_rows=(c.IssuanceRow("route:atm", issued("3200000"), issued("3200000"), "fixed_price"),),
        scenario_new_shares_low=issued("3200000"),
        scenario_new_shares_high=issued("3200000"),
        price_bases=(c.PriceBasis("capacity", "fixed", "2.50", "2.50"),),
        coverage=(
            c.CoveragePeriod(
                "2026-10-01", "2026-12-31", usd("0"), c.SignedQuantity.known("7760000", "usd"),
                c.SignedQuantity.known("12760000", "usd"), usd("0"),
                "covered", c.COVERAGE_SCENARIO_ONLY_NOTE,
            ),
        ),
        authorized_headroom=c.AuthorizedHeadroomDisclosure(
            "not_evaluated", None, None,
            "charter share limit not evaluated by capacity; requested share issuance is not checked",
        ),
        receipt=receipt(scenario_id=sc.scenario_id),
        blockers=(),
        unknowns=(),
        notes=("scenario issuance rows are scenario-conditional and are never added to outstanding",),
    )
    kw.update(over)
    return c.ScenarioResult(**kw)


RECORD_FACTORIES = (
    ("state", state),
    ("state_request", request),
    ("capital_inputs", inputs),
    ("rule_pack", rule_pack),
    ("financing_scenario", scenario),
    ("capacity_envelope", capacity),
    ("supply_envelope", supply),
    ("funding_schedule", funding),
    ("instrument_set", instrument_set),
    ("share_basis_result", share_basis),
    ("calculation_receipt", receipt),
    ("scenario_result", scenario_result),
)


# ---------------------------------------------------------------------------
# Every record kind round-trips through the frozen schema
# ---------------------------------------------------------------------------


def test_record_schemas_and_factories_cover_the_same_kinds():
    assert {kind for kind, _ in RECORD_FACTORIES} == set(c.RECORD_SCHEMAS)


@pytest.mark.parametrize("kind,factory", RECORD_FACTORIES, ids=[kind for kind, _ in RECORD_FACTORIES])
def test_every_record_kind_validates_against_the_schema(kind, factory):
    record = factory().as_record()
    assert record["schema"] == c.RECORD_SCHEMAS[kind]
    c.validate_state_record(kind, record)


def test_schema_file_is_the_frozen_v2_contract():
    schema = c.load_state_schema()
    assert schema["$id"].endswith("/contracts/" + c.STATE_SCHEMA_FILE)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema"]["const"] == c.STATE_SCHEMA
    assert schema["properties"]["contract_version"]["const"] == c.STATE_CONTRACT_VERSION
    assert c.STATE_SCHEMA_PATH == ROOT / "contracts" / c.STATE_SCHEMA_FILE
    assert c.STATE_SCHEMA_PATH.exists()
    assert c.STATE_CONTRACT_VERSION.startswith("capital-structure-state-contracts/2.")


_ENUM_PINS = (
    ("input_family", tuple(c.COMPATIBLE_INPUT_SCHEMAS)),
    ("state_family", c.STATE_FAMILIES),
    ("support", c.SUPPORT_STATES),
    ("unit", c.UNIT_KINDS),
    ("quantity_status", c.QUANTITY_STATUSES),
    ("share_basis", c.SHARE_BASES),
    ("view_mode", c.VIEW_MODES),
    ("scenario_view", c.SCENARIO_VIEWS),
    ("rule_class", c.RULE_CLASSES),
    ("constraint_kind", c.CONSTRAINT_KINDS),
    ("constraint_status", c.CONSTRAINT_STATUSES),
    ("stock_or_flow", c.STOCK_OR_FLOW),
    ("route_kind", c.ROUTE_KINDS),
    ("route_status", c.ROUTE_STATUSES),
    ("settlement", c.SETTLEMENTS),
    ("instrument_kind", c.INSTRUMENT_KINDS),
    ("instrument_status", c.INSTRUMENT_STATUSES),
    ("resolution_method", c.RESOLUTION_METHODS),
    ("share_basis_status", c.SHARE_BASIS_STATUSES),
    ("corporate_action_kind", c.CORPORATE_ACTION_KINDS),
    ("flow_kind", c.FLOW_KINDS),
    ("flow_certainty", c.FLOW_CERTAINTIES),
    ("cash_basis", c.CASH_BASES),
    ("cash_effect_kind", c.CASH_EFFECT_KINDS),
    ("price_kind", c.PRICE_KINDS),
    ("economic_term_name", c.ECONOMIC_TERM_NAMES),
    ("economic_term_status", c.ECONOMIC_TERM_STATUSES),
    ("term_fact_origin", c.TERM_FACT_ORIGINS),
    ("rounding_mode", c.ROUNDING_MODES),
    ("price_component_source", c.PRICE_COMPONENT_SOURCES),
    ("price_measure", c.PRICE_MEASURES),
    ("price_aggregation", c.PRICE_AGGREGATIONS),
    ("price_window_end", c.PRICE_WINDOW_ENDS),
    ("price_combine", c.PRICE_COMBINES),
    ("floor_basis", c.FLOOR_BASES),
    ("below_floor_rule", c.BELOW_FLOOR_RULES),
    ("reset_rule", c.RESET_RULES),
    ("share_adjustment", c.SHARE_ADJUSTMENTS),
    ("price_term_name", c.PRICE_TERM_NAMES),
    ("condition_comparison", c.CONDITION_COMPARISONS),
    ("condition_threshold_kind", c.CONDITION_THRESHOLD_KINDS),
    ("settlement_branch_name", c.SETTLEMENT_BRANCH_NAMES),
    ("branch_elected_by", c.BRANCH_ELECTED_BY),
    ("anti_dilution_method", c.ANTI_DILUTION_METHODS),
    ("accrual_day_count", c.ACCRUAL_DAY_COUNTS),
    ("accrual_compounding", c.ACCRUAL_COMPOUNDING),
    ("structure_kind", c.STRUCTURE_KINDS),
    ("action_check_status", c.ACTION_CHECK_STATUSES),
    ("joint_check_status", c.JOINT_CHECK_STATUSES),
    ("reconciliation_status", c.RECONCILIATION_STATUSES),
    ("coverage_status", c.COVERAGE_STATUSES),
    ("action_owner", c.ACTION_OWNERS),
    ("authorized_headroom_status", c.AUTHORIZED_HEADROOM_STATUSES),
)


@pytest.mark.parametrize("name,values", _ENUM_PINS, ids=[name for name, _ in _ENUM_PINS])
def test_schema_enums_mirror_the_module_vocabularies(name, values):
    schema = c.load_state_schema()
    assert set(schema["$defs"][name]["enum"]) == set(values), name


#: X0 (C0 2.2.0) record vocabularies live inline in their record ``$defs``,
#: not as top-level enum ``$defs``; pin them to the module tuples the same way.
_INLINE_ENUM_PINS = (
    (("transaction_observation", "kind"), c.TRANSACTION_KINDS),
    (("transaction_observation", "reporting_basis"), c.REPORTING_BASES),
    (("transaction_observation", "origin"), c.TRANSACTION_ORIGINS),
    (("transaction_binding", "target_kind"), c.BINDING_TARGET_KINDS),
    (("transaction_binding", "usage_class"), c.USAGE_CLASSES),
    (("transaction_binding", "origin"), c.BINDING_ORIGINS),
)


@pytest.mark.parametrize("path,values", _INLINE_ENUM_PINS,
                         ids=[".".join(path) for path, _ in _INLINE_ENUM_PINS])
def test_schema_record_inline_enums_mirror_the_module_vocabularies(path, values):
    record, field = path
    schema = c.load_state_schema()
    assert set(schema["$defs"][record]["properties"][field]["enum"]) == set(values), path


def test_schema_realized_cash_kind_is_the_realized_cash_vocabulary():
    """``realized_cash_kind`` is nullable, so its enum sits in an ``anyOf`` branch."""
    schema = c.load_state_schema()
    branches = [item["enum"] for item in
                schema["$defs"]["realized_cash"]["properties"]["realized_cash_kind"]["anyOf"]
                if "enum" in item]
    assert len(branches) == 1
    assert set(branches[0]) == set(c.REALIZED_CASH_KINDS)


def test_schema_warrant_exercise_settlement_is_the_settlement_vocabulary():
    schema = c.load_state_schema()
    branches = [item["then"]["properties"]["settlement"]
                for item in schema["$defs"]["transaction_observation"].get("allOf", [])
                if "settlement" in item.get("then", {}).get("properties", {})]
    assert len(branches) == 1
    # I2 (SPEC_I2 §1.2) admits ``physical`` only for a conversion action on an
    # instrument carrying settlement_branches; a warrant exercise never settles
    # "physical", so the warrant branch is the vocabulary minus that one value.
    assert "physical" in c.SETTLEMENTS
    assert set(branches[0]["enum"]) == set(c.SETTLEMENTS) - {"physical"}


def test_schema_input_schema_enum_is_the_compatibility_table():
    schema = c.load_state_schema()
    expected = {item for schemas in c.COMPATIBLE_INPUT_SCHEMAS.values() for item in schemas}
    assert set(schema["$defs"]["input_schema"]["enum"]) == expected


def test_validate_state_record_rejects_unknown_kinds():
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("bogus", {})
    with pytest.raises(c.ContractViolation, match="contract violation"):
        c.validate_state_record("state", {"schema": c.STATE_SCHEMA})


# ---------------------------------------------------------------------------
# A06 — version compatibility and capability proofs
# ---------------------------------------------------------------------------


def test_projection_bundle_v1_is_the_only_observed_event_input():
    assert c.COMPATIBLE_INPUT_SCHEMAS["event_projection"] == (projection.PROJECTION_BUNDLE_SCHEMA,)
    assert c.PROJECTION_COMPATIBILITY["projection_bundle_schema"] == "capital_structure.projection_bundle.v1"
    assert c.PROJECTION_COMPATIBILITY["projection_version_floor"] == projection.PROJECTION_VERSION
    assert c.PROJECTION_COMPATIBILITY["observed_event_reader_status"] == "preserved"
    assert c.INHERITED_UNAVAILABLE_CAPABILITIES == tuple(projection.UNAVAILABLE_CAPABILITIES)
    assert c.AUTHORITY == projection.AUTHORITY
    with pytest.raises(c.ContractViolation):
        c.GenerationBinding("event_projection", "capital_structure.projection_bundle.v2", "supported", generation_id=GEN)


def test_projection_compatibility_verdict_names_every_mismatch():
    ok = {
        "schema": projection.PROJECTION_BUNDLE_SCHEMA,
        "projection_version": projection.PROJECTION_VERSION,
        "authority": dict(projection.AUTHORITY),
    }
    verdict = c.projection_compatibility(ok)
    assert verdict["verdict"] == "compatible" and verdict["reasons"] == []
    assert verdict["state_contract_version"] == c.STATE_CONTRACT_VERSION
    assert c.projection_compatibility({**ok, "projection_version": "capital-structure-event-projection/1.4.2"})["verdict"] == "compatible"
    for bad in (
        {**ok, "schema": "capital_structure.projection_bundle.v2"},
        {**ok, "projection_version": "capital-structure-event-projection/2.0.0"},
        {**ok, "authority": {**ok["authority"], "prophet_authority": True}},
    ):
        result = c.projection_compatibility(bad)
        assert result["verdict"] == "incompatible" and result["reasons"], bad


def test_removing_an_inherited_unavailable_label_requires_a_capability_proof():
    remaining = tuple(item for item in c.INHERITED_UNAVAILABLE_CAPABILITIES if item != "remaining_capacity")
    with pytest.raises(c.ContractViolation, match="removed without a capability proof"):
        state(unavailable=remaining)
    proof = c.CapabilityProof(
        "remaining_capacity", GEN, "tests/test_capital_structure_capacity.py::test_joint_envelope", GENERATED_AT
    )
    proven = state(unavailable=remaining, capabilities_proven=(proof,))
    assert "remaining_capacity" not in proven.unavailable
    c.validate_state_record("state", proven.as_record())
    with pytest.raises(c.ContractViolation, match="both unavailable and proven"):
        state(capabilities_proven=(proof,))
    with pytest.raises(c.ContractViolation):
        c.CapabilityProof("remaining_capacity", GEN, "tests/test_other.py::test_x", GENERATED_AT)


def test_state_is_bound_to_the_projection_generation_it_was_compiled_over():
    with pytest.raises(c.ContractViolation):
        state(projection_generation_id="gen:cs:other")
    with pytest.raises(c.ContractViolation, match="not scenario-bound"):
        state(receipt=receipt(scenario_id=scenario().scenario_id))
    compiled = state()
    assert compiled.state_id.startswith("state:cs:")
    assert compiled.as_record()["as_of"] == AS_OF
    assert compiled.as_record()["compatibility"] == c.PROJECTION_COMPATIBILITY


# ---------------------------------------------------------------------------
# A20 — unknown is never zero or infinite; every share quantity names a basis
# ---------------------------------------------------------------------------


def test_unknown_is_never_zero_or_infinite():
    unknown = c.Quantity.unknown("usd")
    assert unknown.status == "unknown" and unknown.value is None
    with pytest.raises(c.ContractViolation, match="must be null"):
        c.Quantity("usd", "unknown", value="0")
    for bad in ("inf", "-inf", "NaN", "-1", "abc"):
        with pytest.raises(c.ContractViolation):
            c.Quantity.known(bad, "usd")
    record = scenario().as_record()
    record["actions"][0]["quantity"]["value"] = "Infinity"
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("financing_scenario", record)
    record = scenario().as_record()
    record["actions"][0]["quantity"]["status"] = "unknown"
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("financing_scenario", record)


def test_unknown_closing_cash_stays_unknown_not_infinite_runway():
    open_ended = period(closing_balance=c.Quantity.unknown("usd"))
    assert open_ended.closing_balance.status == "unknown"
    schedule = funding(periods=(open_ended,))
    c.validate_state_record("funding_schedule", schedule.as_record())


def test_every_share_quantity_names_its_basis():
    with pytest.raises(c.ContractViolation, match="must name its basis"):
        c.Quantity.known("1", "shares")
    with pytest.raises(c.ContractViolation, match="only share quantities carry a basis"):
        c.Quantity.known("1", "usd", share_basis="issued_and_outstanding")
    assert not any("fully" in basis for basis in c.SHARE_BASES)
    record = state().as_record()
    record["fully_diluted_shares"] = "1"
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("state", record)
    record = supply().as_record()
    record["existing_outstanding"]["share_basis"] = None
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("supply_envelope", record)


def test_supply_components_keep_four_bases_apart():
    with pytest.raises(c.ContractViolation, match="basis must be"):
        supply(existing_outstanding=shares("1", "assumed_as_converted"))
    envelope = supply()
    bases = {name: getattr(envelope, name).share_basis for name in c.SupplyEnvelope._BASES}
    assert bases == c.SupplyEnvelope._BASES
    assert envelope.as_converted_claims.status == "unknown"


# ---------------------------------------------------------------------------
# A31 / A32 — views and scenario identity
# ---------------------------------------------------------------------------


def test_current_then_known_and_scenario_views_are_distinct():
    assert c.VIEW_MODES == ("current", "then_known", "scenario")
    assert c.SCENARIO_VIEWS == ("then_known", "counterfactual")
    assert request(view_mode="current").request_id != request(view_mode="then_known").request_id
    assert scenario(view="then_known").scenario_id != scenario(view="counterfactual").scenario_id
    with pytest.raises(c.ContractViolation):
        request(view_mode="blended")
    with pytest.raises(c.ContractViolation):
        scenario(view="current")


def test_assumption_change_is_a_new_scenario_identity():
    base = scenario()
    assert base.scenario_id.startswith("scenario:cs:")
    assert "label" not in base.assumptions
    assert scenario(label="renamed").scenario_id == base.scenario_id
    assert scenario(fee_rate="0.05").scenario_id != base.scenario_id
    assert scenario(price=c.PriceAssumption("fixed", "USD", fixed_price="2.00")).scenario_id != base.scenario_id
    assert scenario(other_assumptions=(("warrant_exercise", "full"),)).scenario_id != base.scenario_id
    assert scenario(actions=()).scenario_id != base.scenario_id
    assert scenario(horizon_end="2027-04-13").scenario_id != base.scenario_id
    with pytest.raises(c.ContractViolation):
        scenario(fee_rate="1.5")
    with pytest.raises(c.ContractViolation):
        scenario(horizon_end="2026-01-01")
    with pytest.raises(c.ContractViolation):
        scenario(other_assumptions=(("k", "a"), ("k", "b")))


def test_scenario_bound_envelopes_carry_their_own_receipt():
    other = scenario(fee_rate="0.05")
    with pytest.raises(c.ContractViolation, match="receipt scenario differs"):
        capacity(receipt=receipt(scenario_id=other.scenario_id))
    with pytest.raises(c.ContractViolation, match="receipt scenario differs"):
        supply(receipt=receipt(scenario_id=other.scenario_id))
    with pytest.raises(c.ContractViolation, match="receipt scenario differs"):
        funding(receipt=receipt(scenario_id=other.scenario_id))


# ---------------------------------------------------------------------------
# A21 — the joint financing-constraint envelope
# ---------------------------------------------------------------------------


def test_joint_envelope_never_sums_shared_pool_maxima():
    joint = capacity("10000000")
    assert joint.aggregate_bound.decimal == Decimal("10000000")
    c.validate_state_record("capacity_envelope", joint.as_record())
    with pytest.raises(c.ContractViolation, match="sums shared pool"):
        capacity("15000000")
    with pytest.raises(c.ContractViolation, match="exceeds the sum of route limits"):
        capacity("16000000")


def test_unknown_shared_pool_makes_the_aggregate_unknown():
    with pytest.raises(c.ContractViolation, match="cannot be known"):
        capacity("10000000", shared_pools=(pool(None),), binding_constraints=(), unknown_constraints=("pool:shelf-s3",), feasible_witness=None)
    with pytest.raises(c.ContractViolation, match="must name an unknown constraint"):
        capacity(None, binding_constraints=(), feasible_witness=None)
    indeterminate = capacity(
        None,
        shared_pools=(pool(None),),
        binding_constraints=(),
        unknown_constraints=("pool:shelf-s3",),
        feasible_witness=None,
        unknowns=(
            c.Unknown(
                "unknown:shelf-balance",
                "remaining S-3 balance after the 2026-09 takedown is not yet reported",
                "the 424(b) prospectus supplement stating the aggregate offering amount sold",
                affects=("pool:shelf-s3",),
            ),
        ),
    )
    assert indeterminate.aggregate_bound.status == "unknown"
    c.validate_state_record("capacity_envelope", indeterminate.as_record())


def test_feasible_witness_respects_routes_pools_and_aggregate():
    with pytest.raises(c.ContractViolation, match="over-allocates route"):
        capacity(feasible_witness=(c.WitnessAllocation("route:atm", c.Quantity.known("9000000", "usd")),))
    with pytest.raises(c.ContractViolation, match="over-allocates shared pool"):
        capacity(
            "10000000",
            feasible_witness=(
                c.WitnessAllocation("route:atm", c.Quantity.known("8000000", "usd")),
                c.WitnessAllocation("route:takedown", c.Quantity.known("7000000", "usd")),
            ),
        )
    with pytest.raises(c.ContractViolation, match="names unknown route"):
        capacity(feasible_witness=(c.WitnessAllocation("route:ghost", c.Quantity.known("1", "usd")),))


def test_known_bounds_require_evidence_and_applicability():
    with pytest.raises(c.ContractViolation, match="without evidence"):
        route("route:x", "1", evidence=())
    with pytest.raises(c.ContractViolation, match="needs evidence"):
        pool(evidence=())
    with pytest.raises(c.ContractViolation):
        route("route:x", "1", status="conditional", conditions=())
    with pytest.raises(c.ContractViolation):
        pool(kind="time_window")
    record = capacity().as_record()
    record["routes"][0]["evidence"] = []
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("capacity_envelope", record)


# ---------------------------------------------------------------------------
# Rule packs — binding rules versus proposals and assertions
# ---------------------------------------------------------------------------


def test_proposed_reforms_and_issuer_assertions_are_never_enforceable():
    with pytest.raises(c.ContractViolation, match="never enforceable"):
        c.RuleRef("rule:33-11418", "proposed_reform", "Release No. 33-11418", True)
    with pytest.raises(c.ContractViolation, match="never enforceable"):
        c.RuleRef("rule:assert", "issuer_assertion", "10-K p.44", True)
    with pytest.raises(c.ContractViolation, match="is enforceable"):
        c.RuleRef("rule:ib6", "binding_rule", "Form S-3 I.B.6", False)
    pack = rule_pack()
    record = pack.as_record()
    assert record["digest"] == pack.digest
    assert record["digest"] == c.sha256_of({key: value for key, value in record.items() if key not in ("schema", "digest")})
    record["rules"][1]["enforceable"] = True
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("rule_pack", record)
    assert request().rule_pack_digest == pack.digest


# ---------------------------------------------------------------------------
# A48 — no probability, score, rank, sizing, entry or Prophet authority
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    ["probability", "score", "rank", "sizing", "entry", "prophet_score", "runway", "capacity", "fully_diluted", "expected_dilution", "likelihood", "position_size", "overhang"],
)
def test_authority_bearing_keys_are_rejected_at_every_depth(key):
    record = state().as_record()
    record[key] = 1
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("state", record)
    record = state().as_record()
    record["families"][0]["records"][0][key] = 1
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("state", record)
    with pytest.raises(c.ContractViolation):
        c.FamilyState(
            "identity", family_provenance("identity"), records=({"schema": "capital_structure.projection_bundle.v1", key: 1},)
        )


def test_authority_is_context_only_and_frozen():
    record = state().as_record()
    assert record["authority"] == {
        "is_context_only": True,
        "rank_authority": False,
        "sizing_authority": False,
        "entry_authority": False,
        "prophet_authority": False,
    }
    record["authority"]["prophet_authority"] = True
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("state", record)
    record = state().as_record()
    record["authority"]["is_context_only"] = False
    with pytest.raises(c.ContractViolation):
        c.validate_state_record("state", record)


def test_forbidden_property_pattern_is_the_state_schema_pattern_byte_for_byte():
    schema_pattern = c.load_state_schema()["$defs"]["safe_property_name"]["not"]["pattern"]
    assert c.FORBIDDEN_PROPERTY_PATTERN.pattern == schema_pattern


@pytest.mark.parametrize(
    "key, forbidden",
    [
        ("prophet_authority", False),
        ("prophet", True),
        ("prophet_score", True),
        ("prophet_authority_override", True),
        ("prophet_authorityx", True),
        ("rank_authority", False),
        ("sizing_authority", False),
        ("entry_authority", False),
    ],
)
def test_prophet_authority_is_the_only_exempt_prophet_name(key, forbidden):
    assert bool(c.FORBIDDEN_PROPERTY_PATTERN.match(key)) is forbidden


@pytest.mark.parametrize("value", [True, 1, 0, "false", None, {"granted": False}])
def test_prophet_authority_must_be_the_literal_false_denial_at_every_depth(value):
    nested = {"schema": "capital_structure.projection_bundle.v1", "authority": {"prophet_authority": value}}
    with pytest.raises(c.ContractViolation):
        c.FamilyState("identity", family_provenance("identity"), records=(nested,))
    with pytest.raises(c.ContractViolation):
        c.ResolutionInputs(decisions=({"prophet_authority": value},), decided_by="owner", as_of=AS_OF)
    denial = {"schema": "capital_structure.projection_bundle.v1", "authority": {"prophet_authority": False}}
    assert c.FamilyState("identity", family_provenance("identity"), records=(denial,)).records == (denial,)


def test_candidate_bundle_and_capital_inputs_accept_compiled_candidate_rows():
    from engine.capital_structure.instrument_candidates import compile_candidate_term_records
    from tests.test_capital_structure_instrument_candidates import _direct_authority

    source, manifests, reader = _direct_authority()
    rows = compile_candidate_term_records(
        source, source_manifests=manifests, source_reader=reader, generated_at="2026-08-04T00:00:00Z"
    )["observations"]
    assert len(rows) == 5
    assert all(row["authority"]["prophet_authority"] is False for row in rows)
    binding = bindings()["instrument_candidate_terms"]
    bundle = c.CandidateBundle(binding=binding, candidate_terms=tuple(rows), as_of=AS_OF)
    assert len(bundle.candidate_terms) == 5
    inputs = c.CapitalInputs(bindings=(binding,), candidate_terms=tuple(rows))
    assert len(inputs.candidate_terms) == 5
    granted = [dict(row, authority=dict(row["authority"], prophet_authority=True)) for row in rows]
    with pytest.raises(c.ContractViolation):
        c.CandidateBundle(binding=binding, candidate_terms=tuple(granted), as_of=AS_OF)
    with pytest.raises(c.ContractViolation):
        c.CapitalInputs(bindings=(binding,), candidate_terms=tuple(granted))


# ---------------------------------------------------------------------------
# Receipts and interface ownership
# ---------------------------------------------------------------------------


def test_receipt_digests_bind_inputs_rules_and_implementation():
    built = receipt()
    for digest in (built.input_digest, built.rule_digest, built.implementation_digest):
        assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert built.receipt_id.startswith("receipt:cs:")
    assert built.input_digest == c.sha256_of(inputs().as_record())
    assert built.rule_digest == rule_pack().digest
    assert built.implementation_digest == c.sha256_of({"contract": c.STATE_CONTRACT_VERSION, "implementation": IMPLEMENTATION})
    other = c.CalculationReceipt.build(
        inputs=inputs(), rule_digest=rule_pack().digest, implementation="other", computed_at=GENERATED_AT
    )
    assert other.implementation_digest != built.implementation_digest
    assert other.receipt_id != built.receipt_id
    assert inputs().input_digest == inputs().input_digest


def test_inputs_are_bound_to_their_generation_schemas():
    bound = tuple(bindings().values())
    with pytest.raises(c.ContractViolation, match="differs from binding"):
        c.CapitalInputs(bindings=bound, events=({"schema": "capital_structure.event.v2", "event_id": "evt:1"},))
    with pytest.raises(c.ContractViolation, match="bound as"):
        c.CapitalInputs(bindings=bound, covenant_terms=({"schema": None, "term_id": "cov:1"},))
    with pytest.raises(c.ContractViolation):
        c.GenerationBinding("financials", None, "supported", generation_id=GEN)
    with pytest.raises(c.ContractViolation, match="must name its schema"):
        c.GenerationBinding("events", None, "supported", generation_id=GEN)
    with pytest.raises(c.ContractViolation):
        c.GenerationBinding("events", "capital_structure.event.v1", "supported")


def test_financials_bind_per_item_observations_and_corrections_stay_not_built():
    schema = "capital_structure.financial_item_observation.v1"
    assert c.COMPATIBLE_INPUT_SCHEMAS["financials"] == (schema,)
    assert c.COMPATIBLE_INPUT_SCHEMAS["corrections"] == ()
    binding = c.GenerationBinding("financials", schema, "partial", generation_id="gen:fif-cells-2026-10-14")
    fact = {
        "schema": schema,
        "item_id": "fin:unrestricted_cash:0000000001:2026-06-30",
        "item_kind": "unrestricted_cash",
        "availability": "available_now",
        "amount": {"value": "12500000", "unit": "usd", "status": "known"},
        "measured_at": "2026-06-30",
        "source": {"owner": "fundamental_forensics", "metric_id": "cash_and_cash_equivalents"},
    }
    inputs = c.FinancialInputs(binding=binding, facts=(fact,), cash_basis="unrestricted_cash")
    assert inputs.facts[0]["item_id"] == fact["item_id"]
    with pytest.raises(c.ContractViolation, match="differs from binding"):
        c.FinancialInputs(binding=binding, facts=({**fact, "schema": "capital_structure.financial_item_observation.v2"},), cash_basis="unrestricted_cash")
    with pytest.raises(c.ContractViolation, match="forbidden property name"):
        c.FinancialInputs(binding=binding, facts=({**fact, "runway": "12"},), cash_basis="unrestricted_cash")
    with pytest.raises(c.ContractViolation, match="not compatible"):
        c.GenerationBinding("financials", "capital_structure.financial_item_observation.v2", "partial", generation_id=GEN)
    with pytest.raises(c.ContractViolation, match="support must be not_built"):
        c.GenerationBinding("corrections", None, "unavailable")


def test_bound_financials_validate_against_the_state_schema():
    schema = "capital_structure.financial_item_observation.v1"
    binding = c.GenerationBinding("financials", schema, "partial", generation_id="gen:fif-cells-2026-10-14")
    c.validate_state_record("generation_binding", binding.as_record())
    fact = {"schema": schema, "item_id": "fin:unrestricted_cash:0000000001:2026-06-30", "item_kind": "unrestricted_cash"}
    c.validate_state_record("capital_inputs", c.CapitalInputs(bindings=(binding,), financials=(fact,)).as_record())
    refused = {"input_family": "corrections", "schema": schema, "support": "partial", "generation_id": GEN, "artifact_sha256": None, "as_of": None}
    with pytest.raises(c.ContractViolation, match="not_built"):
        c.validate_state_record("generation_binding", refused)


def _corporate_action(stage, **over):
    record = {
        "schema": "capital_structure.corporate_action_observation.v1",
        "observation_id": f"ca:0000000001:rs-2026-03:{stage}",
        "action_id": "ca:0000000001:rs-2026-03",
        "issuer_id": "cik:0000000001",
        "action_kind": "reverse_split",
        "stage": stage,
        "security_class_id": "sec:0000000001:common",
        "ratio": {"new_shares": "1", "old_shares": "10"},
        "effective_date": "2026-03-02",
        "state": {"disposition": "observed", "reason": None},
        "filing": {"accession": "0000000001-26-000010", "form": "8-K", "filing_date": "2026-02-27"},
        "evidence": [{"manifest_id": "manifest:0000000001-26-000010", "span_id": f"span:{stage}", "text_sha256": "a" * 64}],
        "point_in_time": {"available_at": "2026-02-27T21:05:00Z"},
        "authority": {"selects_denominator": False, "is_context_only": True},
    }
    record.update(over)
    return record


def test_corporate_action_observations_bind_as_corporate_actions():
    schema = "capital_structure.corporate_action_observation.v1"
    generation = "gen:corporate-actions-2026-10-14"
    assert c.COMPATIBLE_INPUT_SCHEMAS["corporate_actions"] == (schema,)
    binding = c.GenerationBinding("corporate_actions", schema, "partial", generation_id=generation)
    c.validate_state_record("generation_binding", binding.as_record())
    stages = ("authorization", "vote", "effective", "exchange_adjustment")
    inputs = c.CorporateActionInputs(binding=binding, actions=tuple(_corporate_action(stage) for stage in stages))
    assert [action["stage"] for action in inputs.actions] == list(stages)
    with pytest.raises(c.ContractViolation, match="differs from binding"):
        c.CorporateActionInputs(binding=binding, actions=(_corporate_action("effective", schema="capital_structure.corporate_action_observation.v2"),))
    with pytest.raises(c.ContractViolation, match="forbidden property name"):
        c.CorporateActionInputs(binding=binding, actions=(_corporate_action("effective", probability="0.9"),))
    with pytest.raises(c.ContractViolation, match="not compatible"):
        c.GenerationBinding("corporate_actions", "capital_structure.corporate_action_observation.v2", "partial", generation_id=generation)


def test_interface_ownership_matches_masterplan_section_nine():
    expected = {
        "engine/capital_structure/issuer_state.py": ("compile_issuer_state", ("StateRequest", "CapitalInputs"), "CapitalState"),
        "engine/capital_structure/instrument_resolution.py": ("resolve_instruments", ("CandidateBundle", "ResolutionInputs", "as_of"), "InstrumentSet"),
        "engine/capital_structure/share_basis.py": ("select_share_basis", ("ShareInputs", "CorporateActionInputs", "as_of"), "ShareBasisResult"),
        "engine/capital_structure/capacity.py": ("evaluate_capacity", ("CapitalState", "FinancingScenario", "RulePack"), "CapacityEnvelope"),
        "engine/capital_structure/supply_scenarios.py": ("evaluate_supply", ("InstrumentSet", "ShareBasisResult", "FinancingScenario"), "SupplyEnvelope"),
        "engine/capital_structure/funding.py": ("project_funding", ("FinancialInputs", "CommitmentInputs", "FinancingScenario"), "FundingSchedule"),
        "engine/capital_structure/scenario_composition.py": (
            "compose_scenario",
            ("CapitalState", "InstrumentSet", "ShareBasisResult", "FinancialInputs",
             "CommitmentInputs", "FinancingScenario", "RulePack", "pack", "listing"),
            "ScenarioResult",
        ),
    }
    assert {row[0]: tuple(row[1:]) for row in c.INTERFACE_OWNERSHIP} == expected
    assert c.INTERFACE_OWNER == "capital-structure-intelligence"
    assert c.INTERFACE_READER == "app/capital_structure.py"
    assert (ROOT / c.INTERFACE_READER).exists()
    for path, function_name, parameters, result_type in c.INTERFACE_OWNERSHIP:
        assert hasattr(c, result_type), result_type
        for parameter in parameters:
            assert parameter in ("as_of", "pack", "listing") or hasattr(c, parameter), parameter
        if not (ROOT / path).exists():
            continue
        module = importlib.import_module(path[:-3].replace("/", "."))
        target = getattr(module, function_name)
        assert len(inspect.signature(target).parameters) == len(parameters), path


def test_contract_records_are_frozen():
    quantity = c.Quantity.known("1", "usd")
    with pytest.raises(dataclasses.FrozenInstanceError):
        quantity.value = "2"  # type: ignore[misc]
    for name in c.__all__:
        obj = getattr(c, name)
        if dataclasses.is_dataclass(obj) and isinstance(obj, type):
            assert obj.__dataclass_params__.frozen, name


# ---------------------------------------------------------------------------
# Funding, instruments and share basis
# ---------------------------------------------------------------------------


def test_conditional_commitment_is_not_money_now():
    conditional = flow(
        "flow:eln-draw", "source", "2000000", certainty="conditional", dated=None,
        condition="equity line registration statement declared effective",
    )
    with_option = period(sources=(flow("flow:atm-proceeds", "source", "7760000"), conditional))
    assert with_option.closing_balance.decimal == Decimal("9500000")
    with pytest.raises(c.ContractViolation):
        period(closing="11500000", sources=(flow("flow:atm-proceeds", "source", "7760000"), conditional))
    with pytest.raises(c.ContractViolation, match="names its condition"):
        flow("flow:x", "source", "1", certainty="conditional", dated=None)
    with pytest.raises(c.ContractViolation, match="contractual flow is dated"):
        flow("flow:y", "source", "1", certainty="contractual_dated", dated=None)
    with pytest.raises(c.ContractViolation, match="freezes"):
        funding(assumptions=())
    with pytest.raises(c.ContractViolation):
        period(sources=(flow("flow:z", "use", "1"),))


def test_instrument_identity_is_a_resolution_not_a_filing_form():
    with pytest.raises(c.ContractViolation, match="status and resolution disagree"):
        instrument(status="unresolved_candidate", method="supported_identity")
    with pytest.raises(c.ContractViolation, match="status and resolution disagree"):
        instrument(status="outstanding", method="unresolved")
    candidate = instrument(status="unresolved_candidate", method="unresolved", instrument_id="inst:cand-2", candidate_term_ids=("cand:2",))
    assert candidate.outstanding is None
    with pytest.raises(c.ContractViolation):
        instrument(status="unresolved_candidate", method="unresolved", outstanding=shares("1", "reserved_for_issuance"))
    with pytest.raises(c.ContractViolation):
        c.Resolution("supported_identity")
    with pytest.raises(c.ContractViolation):
        instrument(candidate_term_ids=())
    resolved = instrument_set(instruments=(instrument(), candidate))
    c.validate_state_record("instrument_set", resolved.as_record())
    with pytest.raises(c.ContractViolation):
        instrument_set(provenance=family_provenance("identity"))


def test_cashless_routes_carry_no_cash_economics():
    with pytest.raises(c.ContractViolation):
        c.CashEffect("route:cashless", "no_cash", c.Quantity.known("1", "usd"), c.Quantity.known("1", "usd"))
    none = c.CashEffect("route:cashless", "no_cash", c.Quantity("usd", "not_applicable"), c.Quantity("usd", "not_applicable"))
    assert none.gross.status == "not_applicable"
    with pytest.raises(c.ContractViolation, match="net exceeds gross"):
        c.CashEffect("route:atm", "proceeds", c.Quantity.known("1", "usd"), c.Quantity.known("2", "usd"))


def test_share_basis_conflicts_are_displayed_never_resolved_by_size():
    with pytest.raises(c.ContractViolation):
        share_basis(status="conflict")
    conflict = share_basis(
        status="conflict",
        candidates=(observation(), observation("obs:8k-cover-2026-09", value="10400000", as_of_date="2026-09-30")),
        conflicts=("10-Q cover 10,000,000 (2026-08-10) vs 8-K cover 10,400,000 (2026-09-30)",),
    )
    assert conflict.selected is None
    c.validate_state_record("share_basis_result", conflict.as_record())
    with pytest.raises(c.ContractViolation):
        share_basis(selected=shares("99", "issued_and_outstanding"))
    with pytest.raises(c.ContractViolation):
        share_basis(selected=shares("10000000", "weighted_average_eps"))
    with pytest.raises(c.ContractViolation):
        share_basis(status="conflict", candidates=(observation(),), conflicts=("lone observation",))
    with pytest.raises(c.ContractViolation):
        share_basis(provenance=family_provenance("identity"))


def test_reverse_split_needs_effective_date_and_contract_adjustment_evidence():
    with pytest.raises(c.ContractViolation, match="contract-adjustment evidence"):
        c.CorporateActionBasis("reverse_split", ratio="0.1", effective_date="2026-09-01")
    with pytest.raises(c.ContractViolation):
        c.CorporateActionBasis("reverse_split", ratio="0.1", contract_adjustment_evidence=(ev(),))
    with pytest.raises(c.ContractViolation):
        c.CorporateActionBasis("none", ratio="0.1")
    split = c.CorporateActionBasis("reverse_split", ratio="0.1", effective_date="2026-09-01", contract_adjustment_evidence=(ev(5),))
    adjusted = share_basis(corporate_action=split)
    c.validate_state_record("share_basis_result", adjusted.as_record())
