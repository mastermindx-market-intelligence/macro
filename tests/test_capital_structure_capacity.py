"""SPEC_C1 §10 — the fifteen required cases for the evidence-qualified capacity adapter.

Every digest here is derived (``build_rule_pack`` / ``sha256_of``); none is
hard-coded, because the L1b rule-pack bump moves all of them.  Registration-path
records are plain dicts in the SPEC_L1 §A.3 shape: C1 never imports L1a.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence

import pytest

from engine.capital_structure import capacity as c1
from engine.capital_structure import capacity_joint
from engine.capital_structure import rule_applicability as ra
from engine.capital_structure.capacity import (
    IMPLEMENTATION,
    CapacityInputError,
    CapacityRuleTextUnavailable,
    bind_funding_schedule,
    evaluate_capacity,
    explain_capacity,
)
from engine.capital_structure.issuer_state_contracts import (
    COMPATIBLE_INPUT_SCHEMAS,
    FORBIDDEN_PROPERTY_PATTERN,
    STATE_CONTRACT_VERSION,
    CalculationReceipt,
    CapitalState,
    FamilyProvenance,
    FamilyState,
    FinancingScenario,
    FundingSchedule,
    GenerationBinding,
    PriceAssumption,
    Quantity,
    StateRequest,
    UnknownResolution,
    _record,
    sha256_of,
    stable_id,
    validate_state_record,
)

PACK = ra.load_rule_applicability_pack()

ISSUER = "cik:0001234567"
CLASS = "common"
SALE = "2026-10-14"
AS_OF = f"{SALE}T00:00:00Z"
GENERATED_AT = f"{SALE}T01:00:00Z"
PATH_A = "registration-path:cs:" + "a" * 32
PATH_B = "registration-path:cs:" + "b" * 32
ACC_A = "0001234567-26-000001"
ACC_B = "0001234567-26-000002"
ACC_A2 = "0001234567-26-000003"
MANIFEST = "manifest:cs:" + "0" * 64
BABY_POOL = f"baby_shelf:{SALE}"
NASDAQ_POOL = f"nasdaq_20pct:{SALE}"
WINDOW_CONDITIONS = (
    "securities_registered_under_rule_415_a_1_x_or_automatic_shelf_not_verified",
    "rule_415_a_5_ii_continuation_after_new_filing_not_evaluated",
    "rule_415_a_6_carry_forward_not_evaluated",
    "effective_date_taken_from_effect_notice_acceptance",
)
AUTHORITY = {
    "is_context_only": True,
    "instrument_authority": False,
    "capacity_authority": False,
    "risk_authority": False,
    "probability_authority": False,
    "rank_authority": False,
    "sizing_authority": False,
    "entry_authority": False,
    "trade_authority": False,
    "prophet_authority": False,
}
FAMILY_INPUTS = {
    "registration": ("registration_lifecycle", "capital_structure.registration_lifecycle_bundle.v1"),
    "share_basis": ("share_count_observations", "capital_structure.share_count_observation.v2"),
}


def rules_for(sale: str):
    """The contract RulePack whose text is in force on ``sale`` — never hard-coded."""
    built = ra.build_rule_pack(PACK, sale)[0]
    assert built is not None, f"no qualified rule text on {sale}"
    return built


def shift(sale: str, days: int) -> str:
    return (date.fromisoformat(sale) - timedelta(days=days)).isoformat()


def span_ref(observation_id: str, sha: str = "1" * 64) -> dict[str, str]:
    return {
        "manifest_id": MANIFEST,
        "span_id": f"span:{observation_id}",
        "locator_type": "text_range",
        "locator": "cover page",
        "text_sha256": sha,
    }


def predicate(
    status: str,
    reason: str,
    *,
    rule_ids: Sequence[str] = (),
    value: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "status": status,
        "evidence_event_ids": [],
        "evidence_accessions": [],
        "reason": reason,
        "rule_ids": list(rule_ids),
    }
    if value is not None:
        body["value"] = value
    body.update(extra)
    return body


def registration_path(
    path_id: str,
    *,
    as_of: str = AS_OF,
    available_at: str | None = None,
    accession: str = ACC_A,
    form: str = "S-3",
    family: str = "registration_s3",
    effect: str = "observed",
    automatic_effectiveness: str = "not_applicable",
    withdrawn: str = "not_observed",
    window_status: str = "conditional",
    position: str = "inside_window",
    window_start: str | None = None,
    window_end: str | None = None,
    amendments: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """A ``capital_structure.registration_path.v1`` record (SPEC_L1 §A.3)."""
    stamp = available_at or f"{shift(as_of[:10], 30)}T21:00:00Z"
    start = window_start or shift(as_of[:10], 30)
    end = window_end or f"{int(start[:4]) + 3}{start[4:]}"
    window_extra: dict[str, Any] = {}
    if window_status != "not_applicable":
        window_extra = {
            "window_start": start,
            "window_end": end,
            "position": position,
            "conditions": list(WINDOW_CONDITIONS),
        }
    return {
        "schema": c1.REGISTRATION_PATH_SCHEMA,
        "path_id": path_id,
        "lifecycle_id": f"registration-lifecycle:{path_id[-8:]}",
        "lifecycle_generation_id": "registration-lifecycle-gen-1",
        "as_of": as_of,
        "issuer": {"issuer_id": ISSUER, "security_class_id": CLASS},
        "registration": {"form": form, "registration_family": family},
        "origin": {
            "event_id": f"evt:{path_id[-8:]}",
            "accession": accession,
            "form": form,
            "sec_accepted_at": stamp,
            "mastermind_available_at": stamp,
        },
        "amendment_chain": [dict(item) for item in amendments],
        "intervals": [],
        "observed_registration_state": "effective",
        "predicates": {
            "filed": predicate("observed", "registration_filing_visible"),
            "effect_observed": predicate(
                effect,
                "effect_notice_visible"
                if effect == "observed"
                else "no_effect_notice_visible_absence_is_not_non_effectiveness",
            ),
            "automatic_shelf_form": predicate(
                "observed" if form in c1.AUTOMATIC_SHELF_FORMS else "not_observed",
                "form_fact_only_not_wksi_status",
            ),
            "automatic_effectiveness": predicate(
                automatic_effectiveness,
                "rule_462_e_effective_on_filing_if_wksi_at_determination_date_wksi_not_evaluated"
                if automatic_effectiveness == "conditional"
                else "rule_462_e_text_not_in_rule_pack",
                rule_ids=("cfr.17.230.462.e",) if automatic_effectiveness == "conditional" else (),
            ),
            "offering_role": predicate(
                "unknown",
                "no_accepted_content_evidence_lifecycle_carries_no_primary_or_resale_classification",
                value="unknown",
            ),
            "withdrawn": predicate(
                withdrawn, "withdrawal_notice_observed" if withdrawn == "observed" else "no_withdrawal_notice"
            ),
            "replaced": predicate("unknown", "rule_415_a_6_carry_forward_rows_not_extracted"),
            "shelf_window": predicate(
                window_status,
                "inside_rule_415_a_5_window"
                if window_status == "conditional"
                else "shelf_window_not_evaluated",
                rule_ids=("cfr.17.230.415.a.5",),
                **window_extra,
            ),
        },
        "coverage": {},
        "unavailable": ["registered_amount_remaining"],
        "authority": dict(AUTHORITY),
    }


def fee_row(
    accession: str,
    value: str | None,
    *,
    available_at: str,
    observation_id: str,
    disposition: str = "observed",
    currency: str = "USD",
    scale: str = "1",
    contradiction_ids: Sequence[str] = (),
    term: str = c1.FEE_TABLE_TERM_NAME,
    spans: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": c1.DOCUMENT_TERM_SCHEMA,
        "observation_id": observation_id,
        "logical_observation_id": f"logical:{observation_id}",
        "issuer_id": ISSUER,
        "term": {"name": term},
        "state": {"disposition": disposition},
        "reported": {"raw_text": None if value is None else f"${value}"},
        "normalized": {"value": value, "unit": "USD", "currency": currency, "scale": scale},
        "filing": {
            "accession": accession,
            "form": "S-3",
            "filing_date": available_at[:10],
            "accepted_at": available_at,
        },
        "evidence": {
            "source_manifest_id": MANIFEST,
            "spans": [dict(item) for item in (spans if spans is not None else [span_ref(observation_id)])],
        },
        "relationships": {
            "amends": [],
            "supersedes": [],
            "contradiction_ids": list(contradiction_ids),
        },
        "point_in_time": {"source_available_at": available_at, "available_at": available_at},
    }


def public_float(
    value: str,
    *,
    period_end: str,
    available_at: str,
    observation_id: str = "share-count-v2:cs:" + "c" * 24,
    unit: str = "USD",
    state: str = "observed",
    kind: str = "public_float",
) -> dict[str, Any]:
    return {
        "schema": "capital_structure.share_count_observation.v2",
        "observation_id": observation_id,
        "issuer_id": ISSUER,
        "metric": {"kind": kind, "scope": "direct_sec_companyfacts_fact"},
        "period": {"period_end": period_end, "fiscal_year": int(period_end[:4]), "fiscal_period": "Q3", "frame": None},
        "filing": {"accession": ACC_A, "form": "10-Q", "filed": period_end},
        "state": {"disposition": state, "reason": "direct_sec_companyfacts_fact"},
        "normalized": {"value": value, "unit": unit, "scale": "1", "state": state},
        "evidence": {
            "source_receipt_id": "companyfacts-bridge:cs:" + "d" * 24,
            "source_manifest_id": "manifest:cs-companyfacts:" + "e" * 64,
            "fact_entries": [{"entry_sha256": "f" * 64, "value": value, "unit": unit, "period_end": period_end}],
        },
        "point_in_time": {"available_at": available_at, "public_available_at": available_at},
    }


def share_basis_result(
    outstanding: str,
    *,
    as_of: str = AS_OF,
    status: str = "selected",
) -> dict[str, Any]:
    return {
        "schema": c1.SHARE_BASIS_RESULT_SCHEMA,
        "issuer_id": ISSUER,
        "security_class_id": CLASS,
        "as_of": as_of,
        "status": status,
        "selected": {
            "unit": "shares",
            "status": "known",
            "value": outstanding,
            "share_basis": "issued_and_outstanding",
        },
        "candidates": [
            {
                "observation_id": "share-count-v2:cs:" + "9" * 24,
                "basis": "issued_and_outstanding",
                "as_of_date": as_of[:10],
                "security_class_id": CLASS,
                "value": outstanding,
                "source": {
                    "input_family": "share_count_observations",
                    "generation_id": "share_basis-gen-1",
                    "evidence": [span_ref("share-basis", "2" * 64)],
                    "available_at": as_of,
                },
            }
        ],
        "provenance": {
            "family": "share_basis",
            "input_family": "share_count_observations",
            "input_schema": "capital_structure.share_count_observation.v2",
            "support": "supported",
        },
    }


def usd(unknown_id: str, value: str, rationale: str = "operator supplied the figure") -> UnknownResolution:
    return UnknownResolution(unknown_id, Quantity.known(value, "usd"), rationale)


NASDAQ_ASSUMPTIONS = (
    ("listing_venue", "nasdaq"),
    ("exchange_offering_treatment", "non_public"),
    ("price_relative_to_minimum_price", "below"),
)


def build(
    *,
    sale: str = SALE,
    registration: Sequence[Mapping[str, Any]] = (),
    share_basis: Sequence[Mapping[str, Any]] = (),
    resolutions: Sequence[UnknownResolution] = (),
    other: Sequence[tuple[str, str]] = (),
    price: PriceAssumption | None = None,
    request_digest: str | None = None,
    rules: Any = None,
    horizon_end: str = "2026-12-31",
    families: Sequence[str] | None = None,
    reverse_records: bool = False,
) -> tuple[CapitalState, FinancingScenario, Any]:
    """A CapitalState over the given records plus a scenario whose sale date is ``sale``."""
    as_of = f"{sale}T00:00:00Z"
    rules = rules or rules_for(sale)
    grouped: dict[str, list[dict[str, Any]]] = {"registration": [], "share_basis": []}
    for record in registration:
        grouped["registration"].append(dict(record))
    for record in share_basis:
        grouped["share_basis"].append(dict(record))
    family_states = []
    bindings = []
    for name in families or sorted(grouped):
        records = grouped.get(name, [])
        if reverse_records:
            records = list(reversed(records))
        input_family, input_schema = FAMILY_INPUTS[name]
        assert input_schema in COMPATIBLE_INPUT_SCHEMAS[input_family]
        bindings.append(
            GenerationBinding(input_family, input_schema, "supported", generation_id=f"{name}-gen-1")
        )
        family_states.append(
            FamilyState(
                name,
                FamilyProvenance(
                    family=name,
                    input_family=input_family,
                    input_schema=input_schema,
                    support="supported",
                    compiler_version=STATE_CONTRACT_VERSION,
                    generation_id=f"{name}-gen-1",
                    as_of=as_of,
                ),
                records=tuple(records),
            )
        )
    state = CapitalState(
        request=StateRequest(
            issuer_id=ISSUER,
            as_of=as_of,
            view_mode="then_known",
            input_generations=tuple(bindings),
            rule_pack_id=PACK.rule_pack_id,
            rule_pack_version=PACK.version,
            rule_pack_digest=request_digest or rules.digest,
            security_class_id=CLASS,
        ),
        generated_at=GENERATED_AT.replace(SALE, sale),
        families=tuple(family_states),
        receipt=CalculationReceipt.build(
            inputs={"families": _record(family_states)},
            rule_digest=rules.digest,
            implementation="tests.test_capital_structure_capacity.fixture/1",
            computed_at=GENERATED_AT.replace(SALE, sale),
            scenario_id=None,
        ),
    )
    scenario = FinancingScenario(
        view="then_known",
        as_of=as_of,
        horizon_start=sale,
        horizon_end=horizon_end if horizon_end >= sale else sale,
        price=price or PriceAssumption(kind="fixed", fixed_price="2.00"),
        other_assumptions=tuple(other),
        unknown_resolutions=tuple(resolutions),
        fee_rate="0.01",
        discount_rate="0.02",
    )
    return state, scenario, rules


def evaluate(**kwargs: Any):
    """Build, evaluate, validate and return ``(evaluation, state, scenario)``."""
    state, scenario, rules = build(**kwargs)
    evaluation = explain_capacity(state, scenario, rules, pack=PACK)
    record = evaluation.envelope.as_record()
    validate_state_record("capacity_envelope", record)
    walk_forbidden_keys(record)
    walk_forbidden_keys(evaluation.inputs)
    walk_quantities(record)
    walk_quantities(evaluation.inputs)
    assert sha256_of(_record(evaluation.inputs)) == evaluation.envelope.receipt.input_digest
    return evaluation, state, scenario


def walk_forbidden_keys(value: Any, path: str = "<root>") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            assert isinstance(key, str), f"{path}: non-string key"
            assert not FORBIDDEN_PROPERTY_PATTERN.match(key), f"{path}.{key}: forbidden property name"
            walk_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            walk_forbidden_keys(item, f"{path}[{index}]")


def walk_quantities(value: Any, path: str = "<root>") -> None:
    """A20: a quantity that is not known carries no value -- never 0, never infinity."""
    if isinstance(value, Mapping):
        if {"unit", "status", "value"} <= set(value):
            status = value["status"]
            if status == "known":
                assert isinstance(value["value"], str) and value["value"], f"{path}: a known quantity carries a decimal string"
            else:
                assert value["value"] is None, f"{path}: a {status} quantity carries no value"
        for key, item in value.items():
            walk_quantities(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            walk_quantities(item, f"{path}[{index}]")


def routes_by_id(evaluation) -> dict[str, Any]:
    return {route.route_id: route for route in evaluation.envelope.routes}


def pools_by_id(evaluation) -> dict[str, Any]:
    return {pool.constraint_id: pool for pool in evaluation.envelope.shared_pools}


def unknown_ids(evaluation) -> set[str]:
    return {item.unknown_id for item in evaluation.envelope.unknowns}


def standard_registration(
    sale: str = SALE,
    *,
    path_id: str = PATH_A,
    accession: str = ACC_A,
    registered: str = "20000000",
    form: str = "S-3",
    family: str = "registration_s3",
    effect: str = "observed",
    automatic_effectiveness: str = "not_applicable",
    withdrawn: str = "not_observed",
    position: str = "inside_window",
    window_status: str = "conditional",
    fee_available_days: int = 30,
    float_value: str | None = "60000000",
    float_days: int = 14,
    outstanding: str | None = "15000005",
    extra_fee_rows: Sequence[Mapping[str, Any]] = (),
    amendments: Sequence[Mapping[str, Any]] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One shelf path with its fee row, public float and share-basis result."""
    as_of = f"{sale}T00:00:00Z"
    fee_stamp = f"{shift(sale, fee_available_days)}T21:00:00Z"
    registration: list[dict[str, Any]] = [
        registration_path(
            path_id,
            as_of=as_of,
            available_at=fee_stamp,
            accession=accession,
            form=form,
            family=family,
            effect=effect,
            automatic_effectiveness=automatic_effectiveness,
            withdrawn=withdrawn,
            position=position,
            window_status=window_status,
            amendments=amendments,
        ),
        fee_row(accession, registered, available_at=fee_stamp, observation_id=f"doc:{path_id[-6:]}"),
    ]
    registration.extend(dict(item) for item in extra_fee_rows)
    shares: list[dict[str, Any]] = []
    if float_value is not None:
        shares.append(
            public_float(
                float_value,
                period_end=shift(sale, float_days),
                available_at=f"{shift(sale, float_days - 1)}T00:00:00Z",
            )
        )
    if outstanding is not None:
        shares.append(share_basis_result(outstanding, as_of=as_of))
    return registration, shares


# ---------------------------------------------------------------------------
# §10 case 1 — the worked joint example
# ---------------------------------------------------------------------------


def test_c10_01_worked_joint_example_binds_shared_baby_shelf() -> None:
    """Two shelf paths share one I.B.6 headroom: the aggregate is the joint optimum."""
    reg_a, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", float_value="60000000"
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", float_value=None, outstanding=None
    )
    evaluation, _, _ = evaluate(
        registration=reg_a + reg_b,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "5000000"),
            usd(f"continuing_offering:{PATH_A}", "1000000"),
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "15000000"),
        ],
    )
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    pools = pools_by_id(evaluation)
    limit_a = routes[f"shelf_takedown:{PATH_A}"].limit
    limit_b = routes[f"shelf_takedown:{PATH_B}"].limit
    assert limit_a.value == "14000000" and limit_b.value == "10000000"
    # float 60,000,000 / 3 = 20,000,000.00 one-third limit, less 15,000,000 sold = 5,000,000.00
    assert pools[BABY_POOL].bound.value == "5000000.00"
    assert pools[BABY_POOL].kind == "dollars" and pools[BABY_POOL].stock_or_flow == "flow"
    assert evaluation.inputs["baby_shelf"]["limit"]["value"] == "20000000.00"
    assert evaluation.inputs["baby_shelf"]["float_measured_on"] == shift(SALE, 14)
    aggregate = envelope.aggregate_bound
    assert aggregate.status == "known" and aggregate.unit == "usd"
    assert aggregate.value == "5000000.00"
    assert Decimal(aggregate.value) == min(
        Decimal(limit_a.value) + Decimal(limit_b.value), Decimal(pools[BABY_POOL].bound.value)
    )
    # A21: the shared pool's maximum is never added to the route maxima.
    assert Decimal(aggregate.value) < Decimal(limit_a.value) + Decimal(limit_b.value)
    assert envelope.binding_constraints == (BABY_POOL,)
    assert pools[BABY_POOL].status == "binding"
    assert sorted(envelope.unknown_constraints) == []
    assert set(pools[BABY_POOL].shared_by) == {f"shelf_takedown:{PATH_A}", f"shelf_takedown:{PATH_B}"}
    for route_id in pools[BABY_POOL].shared_by:
        assert BABY_POOL in routes[route_id].consumes
    assert evaluation.kernel["evidence"]["value"] == "5000000/1"
    witness = {item.route_id: Decimal(item.quantity.value) for item in envelope.feasible_witness}
    assert sum(witness.values()) == Decimal("5000000.00")
    assert witness[f"shelf_takedown:{PATH_A}"] <= Decimal(limit_a.value)
    assert witness[f"shelf_takedown:{PATH_B}"] <= Decimal(limit_b.value)


# ---------------------------------------------------------------------------
# §10 case 2 — A15 usage, continuing offering and programme reservation
# ---------------------------------------------------------------------------


def test_c10_02_a15_reservation_splits_the_pool_without_reducing_it() -> None:
    registered, usage, continuing, reservation = (
        Decimal("20000000"),
        Decimal("3000000"),
        Decimal("1000000"),
        Decimal("2000000"),
    )
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "3000000"),
            usd(f"continuing_offering:{PATH_A}", "1000000"),
            usd(f"programme_reservation:{PATH_A}", "2000000"),
            usd(f"programme_usage:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    pools = pools_by_id(evaluation)
    pool_id = f"registered:{PATH_A}"
    bound = pools[pool_id].bound
    takedown = routes[f"shelf_takedown:{PATH_A}"]
    atm = routes[f"at_the_market:{PATH_A}"]
    assert pools[pool_id].kind == "registered_class" and pools[pool_id].stock_or_flow == "stock"
    assert bound.status == "known" and bound.value == "16000000"
    assert Decimal(bound.value) == registered - usage - continuing
    # The reservation SPLITS the pool; it never reduces it a second time.
    assert Decimal(bound.value) != registered - usage - continuing - reservation
    assert takedown.limit.value == "14000000" and takedown.route_kind == "shelf_takedown"
    assert atm.limit.value == "2000000" and atm.route_kind == "at_the_market"
    assert Decimal(takedown.limit.value) + Decimal(atm.limit.value) == Decimal(bound.value)
    assert envelope.aggregate_bound.status == "known"
    assert envelope.aggregate_bound.value == "16000000.00"
    assert Decimal(envelope.aggregate_bound.value) == registered - usage - continuing
    assert evaluation.kernel["evidence"]["value"] == "16000000/1"
    assert set(pools[pool_id].shared_by) == {takedown.route_id, atm.route_id}
    assert pool_id in takedown.consumes and pool_id in atm.consumes
    witness = {item.route_id: Decimal(item.quantity.value) for item in envelope.feasible_witness}
    assert witness[atm.route_id] <= Decimal(atm.limit.value)
    assert witness[takedown.route_id] <= Decimal(takedown.limit.value)
    assert sum(witness.values()) == Decimal("16000000.00")
    # A15: usage is deducted exactly once, in the pool bound, never in a route too.
    assert Decimal(takedown.limit.value) == Decimal(bound.value) - reservation
    assert "baby_shelf_not_applicable_public_float_at_or_above_75m" in takedown.conditions
    assert BABY_POOL not in pools


# ---------------------------------------------------------------------------
# §10 case 3 — A15 with an unresolved deduction
# ---------------------------------------------------------------------------


def test_c10_03_a15_unresolved_usage_leaves_the_aggregate_unknown() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[usd(f"continuing_offering:{PATH_A}", "1000000")],
    )
    envelope = evaluation.envelope
    pool_id = f"registered:{PATH_A}"
    pools = pools_by_id(evaluation)
    route = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"]
    assert pools[pool_id].bound.status == "unknown" and pools[pool_id].bound.value is None
    assert pools[pool_id].status == "unknown"
    assert route.limit.status == "unknown" and route.limit.value is None
    # Never 0, never unlimited, never the gross registered amount.
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.unit == "usd"
    assert envelope.aggregate_bound.note == (
        "floor 0.00 / ceiling 20000000.00 under stated unknowns"
    )
    assert f"shelf_usage:{PATH_A}" in unknown_ids(evaluation)
    assert f"continuing_offering:{PATH_A}" not in unknown_ids(evaluation)
    assert envelope.unknown_constraints == (pool_id,)
    # The gross registered amount appears only as the ceiling substitute.
    assert evaluation.inputs["ceiling_call"]["value"] == "20000000/1"
    assert evaluation.inputs["ceiling_call"]["reported_as"] == (
        "aggregate_note_and_inputs_only_never_the_aggregate"
    )
    assert evaluation.inputs["registration_paths"][0]["registered_amount"]["value"] == "20000000"
    assert evaluation.kernel["evidence"]["determined"] is False
    assert evaluation.kernel["evidence"]["value"] is None


# ---------------------------------------------------------------------------
# §10 case 4 — A20 units and the shape of an unknown
# ---------------------------------------------------------------------------


def test_c10_04_a20_units_are_explicit_and_an_unknown_is_never_zero() -> None:
    reg_a, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", effect="not_observed",
        float_value="300000000",
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", float_value=None, outstanding=None
    )
    evaluation, _, _ = evaluate(
        registration=reg_a + reg_b,
        share_basis=shares,
        other=NASDAQ_ASSUMPTIONS,
        resolutions=[
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
        ],
    )
    envelope = evaluation.envelope
    for route in envelope.routes:
        assert route.limit.unit == "usd", route.route_id
        assert route.limit.share_basis is None
    assert envelope.aggregate_bound.unit == "usd"
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    shares_pool = pools_by_id(evaluation)[NASDAQ_POOL]
    assert shares_pool.kind == "shares"
    assert shares_pool.bound.unit == "shares"
    assert shares_pool.bound.share_basis == "issued_and_outstanding"
    assert shares_pool.bound.value == "3000000"
    unknown_limit = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"].limit
    assert unknown_limit.status == "unknown"
    assert unknown_limit.value is None
    assert unknown_limit.unit == "usd"
    # A20 across the whole record: a quantity that is not known carries no value.
    record = envelope.as_record()
    for quantity in iter_quantities(record):
        assert (quantity["status"] == "known") == (quantity["value"] is not None)
    assert not any(
        quantity["status"] != "known" and quantity["value"] is not None
        for quantity in iter_quantities(evaluation.inputs)
    )


def iter_quantities(value: Any):
    if isinstance(value, Mapping):
        if {"unit", "status", "value"} <= set(value):
            yield value
        for item in value.values():
            yield from iter_quantities(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_quantities(item)


# ---------------------------------------------------------------------------
# §10 case 5 — A20 the share pool binds below the dollar pool
# ---------------------------------------------------------------------------


def test_c10_05_a20_nasdaq_share_pool_binds_below_the_dollar_pool() -> None:
    """15,000,005 shares outstanding -> 3,000,001 threshold -> 3,000,000 below it, at $2."""
    reg, shares = standard_registration(registered="20000000", float_value="300000000", outstanding="15000005")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        other=NASDAQ_ASSUMPTIONS,
        price=PriceAssumption(kind="fixed", fixed_price="2.00"),
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    assert pools[NASDAQ_POOL].bound.value == "3000000"
    assert pools[NASDAQ_POOL].bound.unit == "shares"
    assert evaluation.inputs["nasdaq"]["coefficient"] == "1/2"
    assert evaluation.inputs["nasdaq"]["outstanding"]["value"] == "15000005"
    assert envelope.aggregate_bound.status == "known"
    assert envelope.aggregate_bound.value == "6000000.00"
    assert Decimal(envelope.aggregate_bound.value) == Decimal("3000000") * Decimal("2.00")
    registered_bound = Decimal(pools[f"registered:{PATH_A}"].bound.value)
    assert registered_bound == Decimal("20000000")
    assert Decimal(envelope.aggregate_bound.value) < registered_bound
    assert envelope.binding_constraints == (NASDAQ_POOL,)
    assert pools[NASDAQ_POOL].status == "binding"
    assert pools[f"registered:{PATH_A}"].status == "slack"
    assert "nasdaq_aggregation_of_related_transactions_not_evaluated" in (
        routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"].conditions
    )
    assert any(ref.manifest_id == c1.REFERENCE_PACK_MANIFEST_ID for ref in pools[NASDAQ_POOL].evidence)
    witness = {item.route_id: Decimal(item.quantity.value) for item in envelope.feasible_witness}
    assert witness == {f"shelf_takedown:{PATH_A}": Decimal("6000000.00")}


# ---------------------------------------------------------------------------
# §10 case 6 — A14 offering treatment not assumed
# ---------------------------------------------------------------------------


def test_c10_06_a14_unassumed_offering_treatment_leaves_the_share_pool_out() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    route = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"]
    assert NASDAQ_POOL not in pools_by_id(evaluation)
    assert not any(pool.kind == "shares" for pool in envelope.shared_pools)
    assert f"nasdaq_offering_treatment:{route.route_id}" in unknown_ids(evaluation)
    assert "exchange_public_offering_treatment_undetermined" in route.conditions
    assert "nasdaq_aggregation_of_related_transactions_not_evaluated" not in route.conditions
    # A14: the dollar side is still answerable; only the share test is not reached.
    assert envelope.aggregate_bound.status == "known"
    assert envelope.aggregate_bound.value == "20000000.00"
    assert evaluation.inputs["nasdaq"] is None
    partial = dict(NASDAQ_ASSUMPTIONS)
    partial.pop("exchange_offering_treatment")
    evaluation_partial, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        other=tuple(sorted(partial.items())),
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    assert NASDAQ_POOL not in pools_by_id(evaluation_partial)
    assert f"nasdaq_offering_treatment:shelf_takedown:{PATH_A}" in unknown_ids(evaluation_partial)


# ---------------------------------------------------------------------------
# §10 case 7 — ineligible routes consume nothing
# ---------------------------------------------------------------------------


def test_c10_07_ineligible_paths_consume_nothing_and_never_witness() -> None:
    path_c = "registration-path:cs:" + "c" * 32
    acc_c = "0001234567-26-000009"
    withdrawn, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", withdrawn="observed",
        float_value="300000000",
    )
    expired, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", position="after_window_end",
        float_value=None, outstanding=None,
    )
    live, _ = standard_registration(
        path_id=path_c, accession=acc_c, registered="8000000", float_value=None, outstanding=None
    )
    evaluation, _, _ = evaluate(
        registration=withdrawn + expired + live,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{path_c}", "0"),
            usd(f"continuing_offering:{path_c}", "0"),
        ],
    )
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    for path_id, reason in ((PATH_A, "withdrawal_notice_observed"), (PATH_B, "inside_rule_415_a_5_window")):
        route = routes[f"shelf_takedown:{path_id}"]
        assert route.status == "ineligible"
        assert route.limit.status == "not_applicable" and route.limit.value is None
        assert route.limit.unit == "usd"
        assert route.consumes == ()
        assert route.conditions
        assert f"registered:{path_id}" not in pools_by_id(evaluation)
    assert routes[f"shelf_takedown:{PATH_A}"].conditions[0] == "withdrawal_notice_observed" or (
        "withdrawal_notice_observed" in routes[f"shelf_takedown:{PATH_A}"].conditions
    )
    live_route = routes[f"shelf_takedown:{path_c}"]
    assert live_route.status == "conditional" and live_route.limit.value == "8000000"
    assert envelope.aggregate_bound.value == "8000000.00"
    witnessed = {item.route_id for item in envelope.feasible_witness}
    assert witnessed == {f"shelf_takedown:{path_c}"}
    kernel_routes = {row[0] for row in evaluation.kernel["evidence"]["witness"]}
    assert kernel_routes == {f"shelf_takedown:{path_c}"}
    assert f"shelf_takedown:{PATH_A}" not in kernel_routes
    assert f"shelf_takedown:{PATH_B}" not in kernel_routes
    assert evaluation.kernel["evidence"]["value"] == "8000000/1"


def test_c10_07b_ineligible_only_state_has_no_known_aggregate() -> None:
    withdrawn, shares = standard_registration(withdrawn="observed")
    evaluation, _, _ = evaluate(registration=withdrawn, share_basis=shares)
    envelope = evaluation.envelope
    assert [route.status for route in envelope.routes] == ["ineligible"]
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert "no_active_route" in envelope.blockers
    assert envelope.feasible_witness == ()


# ---------------------------------------------------------------------------
# §10 case 8 — unresolved registration effectiveness
# ---------------------------------------------------------------------------


def test_c10_08_unknown_effectiveness_is_unknown_and_witnesses_only_active_routes() -> None:
    unresolved, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", effect="not_observed",
        float_value="300000000",
    )
    effective, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", float_value=None, outstanding=None
    )
    evaluation, _, _ = evaluate(
        registration=unresolved + effective,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
        ],
    )
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    unknown_route = routes[f"shelf_takedown:{PATH_A}"]
    assert unknown_route.status == "unknown"
    assert unknown_route.limit.status == "unknown" and unknown_route.limit.value is None
    assert f"registration_effectiveness:{PATH_A}" in unknown_ids(evaluation)
    resolving = next(
        item for item in envelope.unknowns if item.unknown_id == f"registration_effectiveness:{PATH_A}"
    )
    assert resolving.resolving_fact == "SEC notice of effectiveness or WKSI status at the determination date"
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == "floor 10000000.00 / ceiling 30000000.00 under stated unknowns"
    witnessed = {item.route_id: item.quantity.value for item in envelope.feasible_witness}
    assert witnessed == {f"shelf_takedown:{PATH_B}": "10000000.00"}
    assert evaluation.kernel["evidence"]["unknown_routes"] == [f"shelf_takedown:{PATH_A}"]


# ---------------------------------------------------------------------------
# §10 case 9 — then-known reading
# ---------------------------------------------------------------------------


def test_c10_09_then_known_excludes_a_fee_row_that_arrives_after_the_cutoff() -> None:
    later = f"{shift(SALE, -6)}T21:00:00Z"
    amendment = {
        "event_id": "evt:amend-1",
        "accession": ACC_A2,
        "form": "S-3",
        "sec_accepted_at": later,
        "mastermind_available_at": later,
        "correction_version": 1,
        "relationship": "amended",
    }
    with_later, shares = standard_registration(
        registered="20000000",
        float_value="300000000",
        amendments=[amendment],
        extra_fee_rows=[fee_row(ACC_A2, "30000000", available_at=later, observation_id="doc:later")],
    )
    without_later, _ = standard_registration(registered="20000000", float_value="300000000")
    resolutions = [
        usd(f"shelf_usage:{PATH_A}", "0"),
        usd(f"continuing_offering:{PATH_A}", "0"),
    ]
    later_evaluation, _, _ = evaluate(
        registration=with_later, share_basis=shares, resolutions=resolutions
    )
    plain_evaluation, _, _ = evaluate(
        registration=without_later, share_basis=shares, resolutions=resolutions
    )
    assert later_evaluation.inputs["excluded_after_as_of"] == {c1.DOCUMENT_TERM_SCHEMA: 1}
    assert plain_evaluation.inputs["excluded_after_as_of"] == {}
    path_record = later_evaluation.inputs["registration_paths"][0]
    assert path_record["fee_table_accession"] == ACC_A
    assert path_record["registered_amount"]["value"] == "20000000"
    assert later_evaluation.envelope.aggregate_bound.value == "20000000.00"
    assert later_evaluation.envelope.aggregate_bound.value == plain_evaluation.envelope.aggregate_bound.value
    assert strip_identity(later_evaluation.envelope.as_record()) == strip_identity(
        plain_evaluation.envelope.as_record()
    )
    # The exclusion is part of what was digested, so the receipts differ.
    assert later_evaluation.envelope.receipt.input_digest != plain_evaluation.envelope.receipt.input_digest


def strip_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    """The envelope minus the fields that digest the state's own record order."""
    out = dict(record)
    out.pop("state_id")
    out.pop("receipt")
    return out


# ---------------------------------------------------------------------------
# §10 case 10 — Class-4 rule transitions (every digest derived, none hard-coded)
# ---------------------------------------------------------------------------


def rule_condition(rule_id: str, sale: str) -> str:
    status = ra.rule_status_as_of(PACK, rule_id, sale)
    assert status.condition, f"{rule_id} has no condition on {sale}"
    return status.condition


def test_c10_10_sale_on_2026_10_14_is_verified_with_beyond_window_nasdaq_text() -> None:
    reg, shares = standard_registration(SALE, registered="20000000", float_value="300000000")
    resolutions = [
        usd(f"shelf_usage:{PATH_A}", "0"),
        usd(f"continuing_offering:{PATH_A}", "0"),
    ]
    assert ra.rule_status_as_of(PACK, "form_s3.I.B.6", SALE).state == "verified"
    assert ra.rule_status_as_of(PACK, "form_s3.I.B.1", SALE).state == "verified"
    assert ra.rule_status_as_of(PACK, c1.NASDAQ_RULE_ID, SALE).state == "beyond_window"
    plain, _, _ = evaluate(registration=reg, share_basis=shares, resolutions=resolutions)
    conditions = routes_by_id(plain)[f"shelf_takedown:{PATH_A}"].conditions
    assert not any("bracketed" in condition for condition in conditions)
    # The Form S-3 eligibility text is verified on the sale date, so it adds no
    # condition. Rule 415(a)(5) (rule pack 1.1.0, L1b) was last verified on
    # 2026-10-09 and therefore carries its own requalify condition; every
    # requalify condition must come from a rule that is actually beyond its window.
    for rule_id in ("form_s3.I.B.6", "form_s3.I.B.1"):
        status = ra.rule_status_as_of(PACK, rule_id, SALE)
        assert status.condition is None or status.condition not in conditions
    assert rule_condition("cfr.17.230.415.a.5", SALE) in conditions
    beyond_window = {
        ra.rule_status_as_of(PACK, rule_id, SALE).condition
        for rule_id in PACK.rules
        if ra.rule_status_as_of(PACK, rule_id, SALE).state == "beyond_window"
    }
    assert all(
        condition in beyond_window for condition in conditions if "requalify" in condition
    )
    assert not any(item.startswith("rule_text:") for item in unknown_ids(plain))
    nasdaq, _, _ = evaluate(
        registration=reg, share_basis=shares, resolutions=resolutions, other=NASDAQ_ASSUMPTIONS
    )
    nasdaq_conditions = routes_by_id(nasdaq)[f"shelf_takedown:{PATH_A}"].conditions
    assert rule_condition(c1.NASDAQ_RULE_ID, SALE) in nasdaq_conditions
    assert not any("bracketed" in condition for condition in nasdaq_conditions)
    assert NASDAQ_POOL in pools_by_id(nasdaq)


def test_c10_10_sale_on_2015_06_01_brackets_ib6_and_withholds_ib1_and_nasdaq() -> None:
    sale = "2015-06-01"
    assert ra.rule_status_as_of(PACK, "form_s3.I.B.6", sale).state == "bracketed"
    assert ra.rule_status_as_of(PACK, "form_s3.I.B.1", sale).state == "withheld"
    assert ra.rule_status_as_of(PACK, c1.NASDAQ_RULE_ID, sale).state == "withheld"
    reg, shares = standard_registration(sale, registered="20000000", float_value="60000000")
    evaluation, _, _ = evaluate(
        sale=sale,
        registration=reg,
        share_basis=shares,
        other=NASDAQ_ASSUMPTIONS,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_sold_trailing:{sale}", "1000000"),
        ],
    )
    envelope = evaluation.envelope
    conditions = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"].conditions
    assert rule_condition("form_s3.I.B.6", sale) in conditions
    assert rule_condition("form_s3.I.B.1", sale) in conditions
    assert f"rule_text:form_s3.I.B.1:{sale}" in unknown_ids(evaluation)
    assert f"rule_text:{c1.NASDAQ_RULE_ID}:{sale}" in unknown_ids(evaluation)
    assert not any(pool.kind == "shares" for pool in envelope.shared_pools)
    # I.B.1 withheld means no pool DECISION: the one-third pool stays declared with
    # an unknown bound rather than disappearing, so the aggregate cannot be known.
    baby_pool = pools_by_id(evaluation)[f"baby_shelf:{sale}"]
    assert baby_pool.bound.status == "unknown" and baby_pool.bound.value is None
    assert envelope.aggregate_bound.status == "unknown"
    assert f"baby_shelf:{sale}" in envelope.unknown_constraints
    assert evaluation.inputs["baby_shelf"]["reason"] == "eligibility_withheld"


def test_c10_10_sale_on_2004_06_01_has_no_rule_text_at_all() -> None:
    # Rule pack 1.1.0 (L1b) holds Rule 415 text in force from 2005-12-01, so the
    # first date with no qualified text at all moved from 2007 to before that.
    sale = "2004-06-01"
    assert ra.build_rule_pack(PACK, sale)[0] is None
    reg, shares = standard_registration(sale, registered="20000000")
    state, scenario, _ = build(sale=sale, registration=reg, share_basis=shares, rules=rules_for(SALE))
    with pytest.raises(CapacityRuleTextUnavailable) as refusal:
        explain_capacity(state, scenario, rules_for(SALE), pack=PACK)
    assert refusal.value.unknowns
    assert all(item.unknown_id.startswith("rule_text:") for item in refusal.value.unknowns)
    assert f"rule_text:form_s3.I.B.1:{sale}" in {item.unknown_id for item in refusal.value.unknowns}
    with pytest.raises(CapacityInputError):
        # CapacityRuleTextUnavailable IS a CapacityInputError, so the public surface stays closed.
        evaluate_capacity(state, scenario, rules_for(SALE))


def test_c10_10_sale_on_2007_06_01_refuses_rules_from_another_date() -> None:
    # On 2007-06-01 only the Rule 415 text is in force; rules compiled for the
    # 2026 sale do not match that pack, so the evaluation refuses instead of
    # silently using text that was not in force.
    sale = "2007-06-01"
    assert ra.build_rule_pack(PACK, sale)[0] is not None
    reg, shares = standard_registration(sale, registered="20000000")
    state, scenario, _ = build(sale=sale, registration=reg, share_basis=shares, rules=rules_for(SALE))
    with pytest.raises(CapacityInputError, match="does not match the rule text in force on 2007-06-01"):
        explain_capacity(state, scenario, rules_for(SALE), pack=PACK)


def test_c10_10_sale_on_2027_03_01_is_beyond_every_qualified_window() -> None:
    sale = "2027-03-01"
    for rule_id in ("form_s3.I.B.6", "form_s3.I.B.1", c1.NASDAQ_RULE_ID):
        assert ra.rule_status_as_of(PACK, rule_id, sale).state == "beyond_window"
    reg, shares = standard_registration(sale, registered="20000000", float_value="60000000")
    evaluation, _, _ = evaluate(
        sale=sale,
        registration=reg,
        share_basis=shares,
        other=NASDAQ_ASSUMPTIONS,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_sold_trailing:{sale}", "5000000"),
        ],
    )
    conditions = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"].conditions
    for rule_id in ("form_s3.I.B.6", "form_s3.I.B.1", c1.NASDAQ_RULE_ID):
        assert rule_condition(rule_id, sale) in conditions
    assert not any("bracketed" in condition for condition in conditions)
    assert not any(item.startswith("rule_text:") for item in unknown_ids(evaluation))
    # Beyond a window the text still governs until requalified, so the pools stand.
    assert pools_by_id(evaluation)[f"baby_shelf:{sale}"].bound.value == "15000000.00"
    # The share pool at $2.00 (3,000,000 shares below the threshold) binds tighter.
    assert evaluation.envelope.aggregate_bound.value == "6000000.00"
    assert evaluation.envelope.binding_constraints == (f"nasdaq_20pct:{sale}",)


def test_c10_10_a_rule_pack_from_another_date_is_refused() -> None:
    sale = "2015-06-01"
    reg, shares = standard_registration(sale, registered="20000000")
    state, scenario, _ = build(sale=sale, registration=reg, share_basis=shares)
    with pytest.raises(CapacityInputError) as refusal:
        explain_capacity(state, scenario, rules_for(SALE), pack=PACK)
    assert "rule pack does not match the rule text in force on 2015-06-01" in str(refusal.value)
    assert not isinstance(refusal.value, CapacityRuleTextUnavailable)
    # The request's own digest is recorded, never compared.
    other = sha256_of({"not": "the pack in force"})
    state2, scenario2, rules2 = build(
        sale=sale, registration=reg, share_basis=shares, request_digest=other
    )
    evaluation = explain_capacity(state2, scenario2, rules2, pack=PACK)
    assert evaluation.inputs["request_rule_pack_digest"] == other
    assert evaluation.inputs["rule_pack_digest"] == rules2.digest != other


# ---------------------------------------------------------------------------
# §10 case 11 — the baby-shelf pool
# ---------------------------------------------------------------------------


def test_c10_11_float_at_or_above_75m_has_no_baby_shelf_pool() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="75000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    assert BABY_POOL not in pools_by_id(evaluation)
    route = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"]
    assert "baby_shelf_not_applicable_public_float_at_or_above_75m" in route.conditions
    assert evaluation.inputs["baby_shelf"]["reason"] == "not_applicable"
    assert evaluation.inputs["baby_shelf"]["limit"]["status"] == "not_applicable"
    assert envelope.aggregate_bound.value == "20000000.00"


def test_c10_11_a_stale_float_leaves_the_headroom_unknown() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="60000000", float_days=90)
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "1000000"),
        ],
    )
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[BABY_POOL]
    assert pool.bound.status == "unknown" and pool.bound.value is None
    assert pool.status == "unknown"
    assert BABY_POOL in envelope.unknown_constraints
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert evaluation.inputs["baby_shelf"]["float_measured_on"] is None
    assert evaluation.inputs["baby_shelf"]["limit"]["status"] == "unknown"


def test_c10_11_a_resolved_float_is_recorded_as_an_assumption() -> None:
    reg, shares = standard_registration(registered="20000000", float_value=None)
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_public_float:{SALE}", "60000000", "10-Q cover page supplied by the operator"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "15000000"),
        ],
    )
    envelope = evaluation.envelope
    assumptions = {item["unknown_id"]: item for item in evaluation.inputs["assumptions"]}
    assert assumptions[f"baby_shelf_public_float:{SALE}"]["assumed"]["value"] == "60000000"
    assert assumptions[f"baby_shelf_public_float:{SALE}"]["rationale"] == (
        "10-Q cover page supplied by the operator"
    )
    assert evaluation.inputs["baby_shelf"]["float_measured_on"] == SALE
    assert pools_by_id(evaluation)[BABY_POOL].bound.value == "5000000.00"
    assert envelope.aggregate_bound.value == "5000000.00"
    assert envelope.binding_constraints == (BABY_POOL,)


def test_c10_11_trailing_sales_above_the_limit_zero_the_headroom() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="30000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "12000000"),
        ],
    )
    envelope = evaluation.envelope
    pool = pools_by_id(evaluation)[BABY_POOL]
    assert evaluation.inputs["baby_shelf"]["limit"]["value"] == "10000000.00"
    assert evaluation.inputs["baby_shelf"]["overrun"]["value"] == "2000000.00"
    assert pool.bound.status == "known" and pool.bound.value == "0"
    assert f"baby_shelf_overrun:{SALE}" in envelope.blockers
    assert envelope.aggregate_bound.status == "known"
    assert envelope.aggregate_bound.value == "0.00"
    assert envelope.binding_constraints == (BABY_POOL,)
    assert {item.route_id: item.quantity.value for item in envelope.feasible_witness} == {
        f"shelf_takedown:{PATH_A}": "0.00"
    }


# ---------------------------------------------------------------------------
# §10 case 12 — an automatic shelf
# ---------------------------------------------------------------------------


def test_c10_12_automatic_shelf_is_conditional_and_gets_no_baby_shelf_pool() -> None:
    reg, shares = standard_registration(
        registered="20000000",
        form="S-3ASR",
        effect="not_observed",
        automatic_effectiveness="conditional",
        float_value="60000000",
    )
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    route = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"]
    assert route.status == "conditional"
    assert route.route_kind == "shelf_takedown"
    assert "wksi_status_not_evaluated" in route.conditions
    assert BABY_POOL not in pools_by_id(evaluation)
    assert evaluation.inputs["baby_shelf"] is None
    assert "form_s3.I.B.6" not in evaluation.inputs["rule_texts"]["consulted"]
    # A small float would otherwise cap the pool at one third: it does not apply.
    assert envelope.aggregate_bound.value == "20000000.00"
    assert pools_by_id(evaluation)[f"registered:{PATH_A}"].bound.value == "20000000"


# ---------------------------------------------------------------------------
# §10 case 13 — the receipt and the owned interface
# ---------------------------------------------------------------------------


def all_keys(value: Any):
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield key
            yield from all_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from all_keys(item)


def test_c10_13_receipt_digests_the_inputs_and_the_interface_takes_three_parameters() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    evaluation, state, scenario = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    record = envelope.as_record()
    rules = rules_for(scenario.horizon_start)
    assert list(inspect.signature(evaluate_capacity).parameters) == ["state", "scenario", "rules"]
    assert sha256_of(_record(evaluation.inputs)) == envelope.receipt.input_digest
    assert envelope.receipt.rule_digest == rules.digest == envelope.rule_pack_digest
    assert envelope.receipt.scenario_id == scenario.scenario_id == envelope.scenario_id
    assert envelope.receipt.computed_at == state.generated_at
    assert envelope.receipt.implementation_digest == sha256_of(
        {"contract": STATE_CONTRACT_VERSION, "implementation": IMPLEMENTATION}
    )
    assert IMPLEMENTATION == "capital_structure.capacity.c2_adapter.v2+" + capacity_joint.IMPLEMENTATION
    assert envelope.state_id == state.state_id
    assert envelope.state_id != state.receipt.input_digest
    validate_state_record("capacity_envelope", record)
    assert [key for key in all_keys(record) if FORBIDDEN_PROPERTY_PATTERN.match(key)] == []
    assert [key for key in all_keys(evaluation.inputs) if FORBIDDEN_PROPERTY_PATTERN.match(key)] == []
    assert evaluate_capacity(state, scenario, rules).as_record() == record
    assert evaluation.kernel["evidence"]["implementation"] == capacity_joint.IMPLEMENTATION
    assert evaluation.inputs["kernel"]["evidence"] == sha256_of(evaluation.kernel["evidence"])
    assert evaluation.inputs["kernel"]["ceiling"] == sha256_of(evaluation.kernel["ceiling"])
    assert evaluation.inputs["fee_rate"] == "0.01" and evaluation.inputs["discount_rate"] == "0.02"


# ---------------------------------------------------------------------------
# §10 case 14 — joining a funding schedule
# ---------------------------------------------------------------------------


def funding_schedule(scenario: FinancingScenario, rules: Any, computed_at: str) -> FundingSchedule:
    return FundingSchedule(
        state_id=stable_id("state", {"funding_inputs": scenario.scenario_id}),
        scenario_id=scenario.scenario_id,
        cash_basis="unrestricted_cash",
        receipt=CalculationReceipt.build(
            inputs={"scenario": scenario.as_record()},
            rule_digest=rules.digest,
            implementation="tests.test_capital_structure_capacity.schedule/1",
            computed_at=computed_at,
            scenario_id=scenario.scenario_id,
        ),
    )


def test_c10_14_bind_funding_schedule_restamps_the_state_identity() -> None:
    reg, shares = standard_registration(float_value="300000000")
    state, scenario, rules = build(registration=reg, share_basis=shares)
    schedule = funding_schedule(scenario, rules, state.request.as_of)
    assert schedule.state_id != state.state_id
    joined = bind_funding_schedule(state, schedule)
    assert joined.state_id == state.state_id
    assert joined.scenario_id == schedule.scenario_id
    assert joined.receipt == schedule.receipt
    assert joined.periods == schedule.periods
    validate_state_record("funding_schedule", joined.as_record())
    validate_state_record("funding_schedule", schedule.as_record())
    # A schedule projected for another scenario/instant is refused, not joined.
    other = dataclasses.replace(scenario, horizon_start="2026-11-01", horizon_end="2027-01-31")
    assert other.scenario_id != scenario.scenario_id
    mismatched = funding_schedule(other, rules, "2026-10-13T00:00:00Z")
    with pytest.raises(CapacityInputError):
        bind_funding_schedule(state, mismatched)
    with pytest.raises(CapacityInputError):
        bind_funding_schedule(state, scenario)  # type: ignore[arg-type]
    with pytest.raises(CapacityInputError):
        bind_funding_schedule(schedule, schedule)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §10 case 15 — determinism
# ---------------------------------------------------------------------------


def test_c10_15_determinism_is_byte_identical_and_order_independent() -> None:
    reg_a, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", float_value="60000000"
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", float_value=None, outstanding=None
    )
    kwargs: dict[str, Any] = dict(
        registration=reg_a + reg_b,
        share_basis=shares,
        other=NASDAQ_ASSUMPTIONS,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "5000000"),
            usd(f"continuing_offering:{PATH_A}", "1000000"),
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "15000000"),
        ],
    )
    first, _, _ = evaluate(**kwargs)
    second, _, _ = evaluate(**kwargs)
    assert first.envelope.as_record() == second.envelope.as_record()
    assert json.dumps(first.envelope.as_record(), sort_keys=True) == json.dumps(
        second.envelope.as_record(), sort_keys=True
    )
    assert sha256_of(_record(first.inputs)) == sha256_of(_record(second.inputs))
    # The adapter's answer never depends on family or record order; only the C0
    # state identity (and so the receipt digest) does, because CapitalState.state_id
    # digests its families in the order they were supplied.
    reordered, _, _ = evaluate(families=["share_basis", "registration"], reverse_records=True, **kwargs)
    assert strip_identity(reordered.envelope.as_record()) == strip_identity(first.envelope.as_record())
    assert json.dumps(strip_identity(reordered.envelope.as_record()), sort_keys=True) == json.dumps(
        strip_identity(first.envelope.as_record()), sort_keys=True
    )
    assert reordered.kernel == first.kernel
    assert reordered.envelope.receipt.input_digest != first.envelope.receipt.input_digest


# ---------------------------------------------------------------------------
# Negative cases required by the packet
# ---------------------------------------------------------------------------


def test_c10_negative_no_registration_path_in_state_is_unknown_not_zero() -> None:
    evaluation, state, _ = evaluate(registration=[], share_basis=[])
    envelope = evaluation.envelope
    assert envelope.routes == ()
    assert envelope.shared_pools == ()
    assert envelope.binding_constraints == ()
    assert envelope.unknown_constraints == ()
    assert envelope.feasible_witness == ()
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert f"registration_paths:{state.request.issuer_id}" in unknown_ids(evaluation)
    assert "no_registration_path_in_state" in envelope.blockers
    validate_state_record("capacity_envelope", envelope.as_record())


def test_c10_negative_input_validation() -> None:
    reg, shares = standard_registration(float_value="300000000")
    state, scenario, rules = build(registration=reg, share_basis=shares)
    with pytest.raises(CapacityInputError):
        explain_capacity(scenario, state, rules, pack=PACK)  # type: ignore[arg-type]
    with pytest.raises(CapacityInputError):
        explain_capacity(state, state, rules, pack=PACK)  # type: ignore[arg-type]
    with pytest.raises(CapacityInputError):
        explain_capacity(state, scenario, scenario, pack=PACK)  # type: ignore[arg-type]
    drifted = dataclasses.replace(scenario, as_of="2026-10-13T00:00:00Z")
    with pytest.raises(CapacityInputError):
        explain_capacity(state, drifted, rules, pack=PACK)
    early = dataclasses.replace(scenario, horizon_start="2026-10-13", horizon_end="2026-12-31")
    with pytest.raises(CapacityInputError):
        explain_capacity(state, early, rules, pack=PACK)
    # A path compiled for another date is refused rather than re-dated.
    stale_registration, stale_shares = standard_registration(float_value="300000000")
    stale_registration[0] = dict(stale_registration[0], as_of="2026-10-13T00:00:00Z")
    stale_state, stale_scenario, stale_rules = build(
        registration=stale_registration, share_basis=stale_shares
    )
    with pytest.raises(CapacityInputError):
        explain_capacity(stale_state, stale_scenario, stale_rules, pack=PACK)
    # A resolution in the wrong unit is refused rather than read as dollars.
    wrong_unit, _ = standard_registration(float_value="300000000")
    wrong_state, wrong_scenario, wrong_rules = build(
        registration=wrong_unit,
        share_basis=_,
        resolutions=[
            UnknownResolution(
                f"shelf_usage:{PATH_A}",
                Quantity.known("1000", "shares", share_basis="issued_and_outstanding"),
                "wrong unit",
            )
        ],
    )
    with pytest.raises(CapacityInputError):
        explain_capacity(wrong_state, wrong_scenario, wrong_rules, pack=PACK)


def test_c10_every_envelope_shape_validates_against_the_c0_contract() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="60000000")
    resolutions = [
        usd(f"shelf_usage:{PATH_A}", "1000000"),
        usd(f"continuing_offering:{PATH_A}", "500000"),
    ]
    shapes: list[dict[str, Any]] = [
        dict(registration=[], share_basis=[]),
        dict(registration=reg, share_basis=shares, resolutions=resolutions),
        dict(registration=reg, share_basis=shares, resolutions=resolutions, other=NASDAQ_ASSUMPTIONS),
        dict(registration=reg, share_basis=shares),
        dict(
            registration=standard_registration(withdrawn="observed")[0],
            share_basis=shares,
        ),
        dict(
            registration=standard_registration(registered="20000000", float_value="30000000")[0],
            share_basis=standard_registration(float_value="30000000")[1],
            resolutions=[
                *resolutions,
                usd(f"baby_shelf_sold_trailing:{SALE}", "12000000"),
            ],
        ),
        dict(
            registration=standard_registration(effect="not_observed")[0],
            share_basis=shares,
            resolutions=resolutions,
        ),
        dict(
            registration=standard_registration(
                form="S-3ASR", effect="not_observed", automatic_effectiveness="conditional"
            )[0],
            share_basis=shares,
            resolutions=resolutions,
        ),
        dict(
            registration=reg,
            share_basis=shares,
            resolutions=resolutions,
            other=NASDAQ_ASSUMPTIONS,
            price=PriceAssumption(kind="path", path=(("2026-10-14", "2.00"), ("2026-11-14", "3.00"))),
        ),
    ]
    for shape in shapes:
        evaluation, _, _ = evaluate(**shape)
        record = evaluation.envelope.as_record()
        validate_state_record("capacity_envelope", record)
        assert [key for key in all_keys(record) if FORBIDDEN_PROPERTY_PATTERN.match(key)] == []
        assert sha256_of(_record(evaluation.inputs)) == evaluation.envelope.receipt.input_digest
        if evaluation.envelope.aggregate_bound.status != "known":
            assert (
                evaluation.envelope.unknown_constraints
                or evaluation.envelope.unknowns
                or evaluation.envelope.blockers
            )


# SPEC_C2 §5.6: test_c10_price_path_branching_is_deferred_to_c2 is gone.  C2 §2.2
# removed the C1 deferral (the blocker price_path_branching_deferred_to_c2) and
# computes the 20% share bound at the price in effect, so path pricing is no
# longer a deferred shape.  Its successors are the four §4.2 fixtures in
# tests/test_capital_structure_capacity_c2.py: test_path_takedown_only_*,
# test_path_atm_branching_*, test_path_point_before_horizon_* and
# test_path_starts_after_horizon_*.


def test_c10_mixed_shelf_forms_leave_the_one_third_pool_undecided() -> None:
    reg_a, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", form="S-3", family="registration_s3",
        float_value="60000000",
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", form="F-3", family="registration_f3",
        float_value=None, outstanding=None,
    )
    evaluation, _, _ = evaluate(
        registration=reg_a + reg_b,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "1000000"),
        ],
    )
    envelope = evaluation.envelope
    assert "baby_shelf_mixed_forms" in envelope.blockers
    assert pools_by_id(evaluation)[BABY_POOL].bound.status == "unknown"
    assert envelope.aggregate_bound.status == "unknown"
    assert evaluation.inputs["baby_shelf"]["reason"] == "mixed_forms"


# ---------------------------------------------------------------------------
# §5 the fee table — a contradicted row is contradicted, a disagreeing pair is unknown
# ---------------------------------------------------------------------------


def test_c10_a_contradicted_fee_table_is_contradicted_and_never_a_known_amount() -> None:
    stamp = f"{shift(SALE, 30)}T21:00:00Z"
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    reg[1] = fee_row(
        ACC_A,
        "20000000",
        available_at=stamp,
        observation_id="doc:contradicted",
        contradiction_ids=["contradiction:cs:" + "9" * 24],
    )
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    registered = evaluation.inputs["registration_paths"][0]["registered_amount"]
    assert registered["status"] == "contradicted"
    assert registered["value"] is None
    assert f"fee_table_contradicted:{ACC_A}" in envelope.blockers
    assert f"registered_amount:{PATH_A}" in unknown_ids(evaluation)
    assert pools_by_id(evaluation)[f"registered:{PATH_A}"].bound.status == "unknown"
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    # A contradicted gross amount is not even a ceiling substitute: nothing is claimed.
    assert "unbounded" in (envelope.aggregate_bound.note or "")
    assert evaluation.inputs["ceiling_call"]["value"] is None


def test_c10_two_disagreeing_fee_rows_in_one_filing_leave_the_amount_unknown() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    reg.append(
        fee_row(
            ACC_A,
            "30000000",
            available_at=f"{shift(SALE, 20)}T21:00:00Z",
            observation_id="doc:second-row",
        )
    )
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    registered = evaluation.inputs["registration_paths"][0]["registered_amount"]
    assert registered["status"] == "unknown"
    assert f"fee_table_multi_row:{ACC_A}" in envelope.blockers
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None


# ---------------------------------------------------------------------------
# §6 negatives — an overrun contradicts the pool; it never becomes 0 or the gross
# ---------------------------------------------------------------------------


def test_c10_deductions_above_the_registered_amount_contradict_the_pool() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "25000000"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    )
    envelope = evaluation.envelope
    pool_id = f"registered:{PATH_A}"
    pool = pools_by_id(evaluation)[pool_id]
    assert pool.bound.status == "contradicted" and pool.bound.value is None
    assert pool.status == "unknown"
    assert f"registered_overrun:{PATH_A}" in envelope.blockers
    assert envelope.unknown_constraints == (pool_id,)
    route = routes_by_id(evaluation)[f"shelf_takedown:{PATH_A}"]
    assert route.limit.status == "contradicted" and route.limit.value is None
    assert route.applicability is None and route.evidence == ()
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert {item.route_id: item.quantity.value for item in envelope.feasible_witness} == {
        f"shelf_takedown:{PATH_A}": "0.00"
    }
    # The gross registered amount is a substitute for an UNKNOWN bound only: a
    # contradicted one is never relaxed back into the amount already exceeded.
    assert evaluation.inputs["ceiling_call"]["value"] is None
    assert envelope.aggregate_bound.note == (
        "floor 0.00 / ceiling unbounded under stated unknowns"
    )


def test_c10_a_reservation_above_the_amount_remaining_contradicts_the_pool() -> None:
    reg, shares = standard_registration(registered="20000000", float_value="300000000")
    evaluation, _, _ = evaluate(
        registration=reg,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"programme_reservation:{PATH_A}", "25000000"),
        ],
    )
    envelope = evaluation.envelope
    pool_id = f"registered:{PATH_A}"
    pool = pools_by_id(evaluation)[pool_id]
    assert pool.bound.status == "contradicted" and pool.bound.value is None
    assert f"programme_reservation_overrun:{PATH_A}" in envelope.blockers
    routes = routes_by_id(evaluation)
    assert routes[f"shelf_takedown:{PATH_A}"].limit.status == "unknown"
    # An impossible split emits no at-the-market route limit: the reservation stays
    # a recorded assumption instead of a claimed 25,000,000 route.
    assert f"at_the_market:{PATH_A}" not in routes
    assert pool.shared_by == (f"shelf_takedown:{PATH_A}",)
    assert f"programme_reservation:{PATH_A}" in {
        item["unknown_id"] for item in evaluation.inputs["assumptions"]
    }
    assert evaluation.inputs["registration_paths"][0]["resolutions"]["programme_reservation"][
        "assumed"
    ]["value"] == "25000000"
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert evaluation.inputs["ceiling_call"]["value"] is None


# ---------------------------------------------------------------------------
# §3 schemas the adapter does not read are listed, sorted, unique and never used
# ---------------------------------------------------------------------------


def test_c10_unread_schemas_are_listed_and_never_used() -> None:
    plain, shares = standard_registration(registered="20000000", float_value="300000000")
    resolutions = [
        usd(f"shelf_usage:{PATH_A}", "0"),
        usd(f"continuing_offering:{PATH_A}", "0"),
    ]
    baseline, _, _ = evaluate(registration=plain, share_basis=shares, resolutions=resolutions)
    noisy = [
        *plain,
        {"schema": "capital_structure.instrument_observation.v1", "instrument_id": "instrument:cs:" + "1" * 24},
        {"schema": "capital_structure.instrument_observation.v1", "instrument_id": "instrument:cs:" + "2" * 24},
        {"schema": "capital_structure.covenant_observation.v1", "covenant_id": "covenant:cs:" + "3" * 24},
    ]
    with_noise, _, _ = evaluate(registration=noisy, share_basis=shares, resolutions=resolutions)
    assert baseline.inputs["ignored_schemas"] == []
    assert with_noise.inputs["ignored_schemas"] == [
        "capital_structure.covenant_observation.v1",
        "capital_structure.instrument_observation.v1",
    ]
    # Ignored records change nothing but the state's own identity.
    assert with_noise.envelope.aggregate_bound.value == baseline.envelope.aggregate_bound.value
    assert with_noise.envelope.aggregate_bound.value == "20000000.00"
    assert with_noise.kernel == baseline.kernel
    assert strip_identity(with_noise.envelope.as_record()) == strip_identity(
        baseline.envelope.as_record()
    )
