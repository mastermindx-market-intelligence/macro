"""SPEC_I1 §5-§6: share supply and cash consequences of a financing scenario.

Every acceptance row this lane owns (A19, A23, A24, A25) is asserted with exact
Decimal strings, never approximately, and every L172 reference case has its own
named test.  Fixtures are built in-file: no network, no ``data/`` read, and no
digest is hard-coded (every digest is derived with :func:`stable_id` or
:func:`sha256_of`).  The only float literals in this file are inside the
float-refusal tests.

Two laws shape every assertion here:

* the four ``SupplyEnvelope`` components answer four different questions and are
  never summed — no test helper adds two of them, and no test looks for a total;
* unknown is never 0 and never unbounded — a missing, unreadable, contradicted,
  formula-only or pre-split term, an unselected share basis, an unresolved holder
  position, an unpriced horizon and a missing fee rate each produce a named
  ``Unknown`` and an ``unknown``-status Quantity.
"""
from __future__ import annotations

import dataclasses
import inspect
import random
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

import tests.test_capital_structure_instrument_economics as IE
import tests.test_capital_structure_issuer_state_contracts as T
from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure import supply_scenarios as supply_module
from engine.capital_structure.instrument_economics import attach_economic_terms
from engine.capital_structure.instrument_resolution import instrument_id_for
from engine.capital_structure.supply_scenarios import (
    IMPLEMENTATION,
    SETTLEMENT_RULES,
    TRACE_SCHEMA,
    evaluate_supply,
    supply_trace,
)

ISSUER = T.ISSUER
CLASS = T.CLASS
AS_OF = T.AS_OF
OUTSTANDING = "10000000"
EFFECTIVE = "2026-06-01T00:00:00Z"
PRE_SPLIT = "2025-01-02T00:00:00Z"
POST_SPLIT = "2026-06-01T00:00:00Z"
AVAILABLE = "2026-06-02T00:00:00Z"
SPLIT_DATE = "2026-06-01"
HORIZON_START = "2026-10-13"
HORIZON_END = "2027-10-13"
PRICE = "2.50"
STRIKE = "1.00"
RESIDUAL = "0.001"
CONVERSION_PRICE = "0.50"
PRINCIPAL = "2000000"
FEE = "0.03"
CAP = "9.99"
#: The A25 cap as an exact fraction: percentage POINTS, so "9.99" is 0.0999.
CAP_FRACTION = Fraction(Decimal(CAP)) / 100
#: floor(cap * E / (1 - cap)) with E = 10_000_000 and position 0, derived exactly.
CAP_CEILING = str((CAP_FRACTION * Fraction(Decimal(OUTSTANDING))) // (1 - CAP_FRACTION))

ROW_KEYS = (
    "route_id",
    "instrument_id",
    "action",
    "settlement",
    "underlying_shares",
    "incremental_shares",
    "gross_cash",
    "net_cash",
    "guards",
    "unknowns",
    "fraction",
)
TRACE_KEYS = (
    "schema",
    "implementation",
    "state_id",
    "scenario_id",
    "price",
    "horizon_days",
    "rows",
    "claims",
    "resale",
    "unknowns",
    "guards",
)
COMPONENT_NAMES = (
    "existing_outstanding",
    "incremental_issuance",
    "as_converted_claims",
    "resalable_existing",
)
STRUCTURAL_GUARDS = (
    "components_never_summed",
    "resale_mints_no_shares_or_issuer_cash",
    "one_decrement_per_action",
)
MODULE = Path("engine/capital_structure/supply_scenarios.py")


# ---------------------------------------------------------------------------
# Builders — exact terms, exact instruments, exact scenarios
# ---------------------------------------------------------------------------


def economic_term(instrument_id: str, name: str, value: str | None = None, *, status: str = "admitted",
                  flag: bool | None = None, expression: str | None = None, date_value: str | None = None,
                  effective_at: str | None = None, term_id: str | None = None,
                  fact_origin: str = "canonical_extraction", interpretation_version: str = "1.0.0",
                  evidence=(T.ev(3),)) -> c.EconomicTerm:
    """One EconomicTerm; the id is derived, never invented, and never hard-coded."""
    unit, basis = c.ECONOMIC_TERM_UNITS.get(name, (None, None))
    if effective_at is None and status == "admitted" and name in c.ECONOMIC_TERM_EFFECTIVE_NAMES:
        effective_at = EFFECTIVE
    quantity: c.Quantity | None = None
    if unit is not None:
        if status == "admitted" and value is not None:
            quantity = c.Quantity.known(value, unit, share_basis=basis)
        elif status == "contradicted":
            quantity = c.Quantity(unit=unit, status="contradicted", share_basis=basis)
        else:
            quantity = c.Quantity.unknown(unit, share_basis=basis)
    return c.EconomicTerm(
        term_id=term_id or c.stable_id(
            "econterm",
            {
                "instrument_id": instrument_id,
                "name": name,
                "value": value,
                "status": status,
                "expression": expression,
                "flag": flag,
                "date_value": date_value,
                "effective_at": effective_at,
            },
        ),
        instrument_id=instrument_id,
        name=name,
        status=status,
        value=quantity,
        flag=flag,
        expression=expression,
        date_value=date_value,
        evidence=tuple(evidence),
        fact_origin=fact_origin,
        interpretation_version=interpretation_version,
        available_at=AVAILABLE,
        effective_at=effective_at,
    )


def make_instrument(series_key: str, kind: str = "warrant", status: str = "outstanding", **terms):
    """A resolved instrument carrying admitted terms named by keyword.

    A ``bool`` builds a permission flag, a string builds an admitted quantity, and
    an :class:`EconomicTerm` is used as given (that is how an unknown, a
    contradicted or a formula-only term is injected).
    """
    instrument_id = instrument_id_for(ISSUER, series_key)
    built = []
    for name, value in terms.items():
        if value is None:
            continue  # an omitted term: the instrument simply does not carry it
        if isinstance(value, c.EconomicTerm):
            built.append(value)
        elif isinstance(value, bool):
            built.append(economic_term(instrument_id, name, flag=value))
        elif isinstance(value, tuple):
            built.append(economic_term(instrument_id, name, *value[0], **value[1]))
        else:
            built.append(economic_term(instrument_id, name, value))
    ordered = tuple(sorted(built, key=lambda item: (item.name, item.term_id)))
    resolved, instrument = IE.instrument_for(series_key, kind=kind, status=status, economic_terms=ordered)
    assert resolved == instrument_id
    return instrument_id, instrument


def instrument_set(*pairs) -> c.InstrumentSet:
    return IE.set_for(*pairs)


def series_id(series_key: str) -> str:
    """The derived identity of a series; never invented and never re-derived by hand."""
    return instrument_id_for(ISSUER, series_key)


def plain_warrant(series_key: str = "series_u_cash_warrants", **terms):
    """A cash-exercisable warrant with a 1,000,000 share claim; ``name=None`` omits a term."""
    defaults = dict(instruments_outstanding="1000000", shares_per_instrument="1", exercise_price=STRIKE)
    defaults.update(terms)
    return make_instrument(series_key, **defaults)


def basis(selected: str = OUTSTANDING, status: str = "selected", **over) -> c.ShareBasisResult:
    if status == "selected":
        return T.share_basis(status=status, selected=T.shares(selected, "issued_and_outstanding"), **over)
    return T.share_basis(status=status, **over)


def split_basis(ratio: str = "0.1", **over) -> c.ShareBasisResult:
    return basis(
        corporate_action=c.CorporateActionBasis(
            kind="reverse_split",
            ratio=ratio,
            effective_date=SPLIT_DATE,
            contract_adjustment_evidence=(T.ev(5),),
        ),
        **over,
    )


def selection(route_id: str, action: str, settlement: str, quantity: c.Quantity | None = None) -> c.ActionSelection:
    return c.ActionSelection(route_id, action, settlement, quantity=quantity)


def scenario(actions=(), **over) -> c.FinancingScenario:
    defaults = dict(
        view="counterfactual",
        as_of=AS_OF,
        horizon_start=HORIZON_START,
        horizon_end=HORIZON_END,
        price=c.PriceAssumption("fixed", "USD", fixed_price=PRICE),
        actions=tuple(actions),
        fee_rate=FEE,
        discount_rate=None,
        other_assumptions=(),
        unknown_resolutions=(),
        label="i1a fixture",
    )
    defaults.update(over)
    return c.FinancingScenario(**defaults)


def evaluate(instruments, share_basis, selected_scenario) -> tuple[c.SupplyEnvelope, dict]:
    """Run both entry points; every envelope this suite builds is schema-checked."""
    envelope = evaluate_supply(instruments, share_basis, selected_scenario)
    record = IE.check_supply_envelope(envelope)
    trace = supply_trace(instruments, share_basis, selected_scenario)
    assert tuple(trace) == TRACE_KEYS
    assert trace["schema"] == TRACE_SCHEMA
    assert trace["implementation"] == IMPLEMENTATION
    assert trace["state_id"] == envelope.state_id
    assert trace["scenario_id"] == envelope.scenario_id == selected_scenario.scenario_id
    for row in trace["rows"]:
        assert tuple(row) == ROW_KEYS
    assert c.sha256_of(record) == c.sha256_of(envelope.as_record())
    assert_no_float(record, "supply_envelope")
    assert_no_float(trace, "supply_trace")
    return envelope, trace


def rows_by_route(trace: dict) -> dict:
    return {row["route_id"]: row for row in trace["rows"]}


def cash_by_route(envelope: c.SupplyEnvelope) -> dict:
    return {item.route_id: item for item in envelope.cash_effects}


def unknown_ids(envelope: c.SupplyEnvelope) -> list:
    return [item.unknown_id for item in envelope.unknowns]


def component(envelope: c.SupplyEnvelope, name: str) -> c.Quantity:
    return envelope.components()[name]


def a24_instruments():
    """The A24 fixture: one instrument per settlement kind, 1,000,000 underlying each."""
    cash_id, cash = make_instrument(
        "series_a24_cash_warrants",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        exercise_price=STRIKE,
    )
    cashless_id, cashless = make_instrument(
        "series_a24_cashless_warrants",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        exercise_price=STRIKE,
        cashless_exercise_permitted=True,
    )
    prefunded_id, prefunded = make_instrument(
        "series_a24_prefunded_warrants",
        kind="pre_funded_warrant",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        prefunded_residual_price=RESIDUAL,
    )
    note_id, note = make_instrument(
        "series_a24_convertible_notes",
        kind="convertible_note",
        principal_outstanding=PRINCIPAL,
        conversion_price=CONVERSION_PRICE,
        cashless_exercise_permitted=True,
    )
    instruments = instrument_set((cash_id, cash), (cashless_id, cashless), (prefunded_id, prefunded), (note_id, note))
    selected_scenario = scenario(
        [
            selection(cash_id, "warrant_exercise", "cash"),
            selection(cashless_id, "warrant_exercise", "cashless"),
            selection(prefunded_id, "warrant_exercise", "pre_funded"),
            selection(note_id, "conversion", "cashless"),
        ]
    )
    return instruments, basis(), selected_scenario, {
        "cash": cash_id,
        "cashless": cashless_id,
        "prefunded": prefunded_id,
        "conversion": note_id,
    }


# ---------------------------------------------------------------------------
# A24 — the four settlement kinds have distinct share and cash consequences
# ---------------------------------------------------------------------------


def test_a24_cash_exercise_mints_the_selected_shares_and_pays_the_strike():
    instruments, share_basis, selected_scenario, ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    row = rows_by_route(trace)[ids["cash"]]
    assert row["action"] == "warrant_exercise"
    assert row["settlement"] == "cash"
    assert row["underlying_shares"] == "1000000"
    assert row["incremental_shares"] == "1000000"
    assert row["fraction"] == "0"
    effect = cash_by_route(envelope)[ids["cash"]]
    assert effect.kind == "proceeds"
    assert row["gross_cash"] == effect.gross.value == "1000000"
    assert row["net_cash"] == "970000"
    assert effect.net.decimal == Decimal("1000000") * (Decimal(1) - Decimal(FEE))
    assert effect.net.decimal <= effect.gross.decimal


def test_a24_cashless_exercise_nets_the_spread_and_pays_the_issuer_nothing():
    instruments, share_basis, selected_scenario, ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    row = rows_by_route(trace)[ids["cashless"]]
    assert row["incremental_shares"] == "600000"
    # n*(P-K)/P = 1_000_000 * (2.50 - 1.00) / 2.50, exactly.
    assert Fraction(600000) == Fraction(1000000) * (Fraction(Decimal(PRICE)) - Fraction(Decimal(STRIKE))) / Fraction(Decimal(PRICE))
    assert row["fraction"] == "0"
    assert row["gross_cash"] == "0" and row["net_cash"] == "0"
    effect = cash_by_route(envelope)[ids["cashless"]]
    assert effect.kind == "no_cash"
    assert effect.gross.decimal == Decimal(0) and effect.net.decimal == Decimal(0)


def test_a24_pre_funded_exercise_pays_only_the_residual():
    instruments, share_basis, selected_scenario, ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    row = rows_by_route(trace)[ids["prefunded"]]
    assert row["settlement"] == "pre_funded"
    assert row["incremental_shares"] == "1000000"
    assert row["gross_cash"] == "1000"
    assert row["net_cash"] == "970"
    effect = cash_by_route(envelope)[ids["prefunded"]]
    assert effect.kind == "proceeds"
    assert effect.gross.decimal == Decimal(1000000) * Decimal(RESIDUAL)
    # L100: the prepaid part is never counted again, so the gross is the residual only.
    assert effect.gross.decimal < Decimal(1000000) * Decimal(STRIKE)
    assert "prefunded_paid_economics_not_recounted" in envelope.double_count_guards


def test_a24_conversion_issues_the_contractual_shares_and_pays_nothing():
    instruments, share_basis, selected_scenario, ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    row = rows_by_route(trace)[ids["conversion"]]
    assert row["action"] == "conversion"
    assert row["incremental_shares"] == "4000000"
    assert Decimal(row["incremental_shares"]) == Decimal(PRINCIPAL) / Decimal(CONVERSION_PRICE)
    assert row["fraction"] == "0"
    effect = cash_by_route(envelope)[ids["conversion"]]
    assert effect.kind == "no_cash"
    assert effect.gross.decimal == Decimal(0) and effect.net.decimal == Decimal(0)


def test_a24_the_four_settlements_are_pairwise_distinct():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    kinds = {effect.kind for effect in envelope.cash_effects}
    observed = tuple(
        (row["incremental_shares"], cash_by_route(envelope)[row["route_id"]].kind, row["gross_cash"])
        for row in trace["rows"]
    )
    assert len(observed) == 4
    assert len(set(observed)) == 4, observed
    assert kinds == {"proceeds", "no_cash"}
    assert component(envelope, "incremental_issuance").value == "6600000"
    assert component(envelope, "as_converted_claims").value == "7000000"
    assert component(envelope, "existing_outstanding").value == OUTSTANDING
    assert component(envelope, "resalable_existing").status == "not_applicable"
    assert len(envelope.cash_effects) == len(set(item.route_id for item in envelope.cash_effects)) == 4


def test_a24_components_keep_their_own_share_basis():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    envelope, _trace = evaluate(instruments, share_basis, selected_scenario)
    assert component(envelope, "existing_outstanding").share_basis == "issued_and_outstanding"
    assert component(envelope, "incremental_issuance").share_basis == "scenario_incremental_issuance"
    assert component(envelope, "as_converted_claims").share_basis == "assumed_as_converted"
    assert component(envelope, "resalable_existing").share_basis == "potentially_resalable_existing"
    for name in COMPONENT_NAMES:
        quantity = component(envelope, name)
        assert quantity.unit == "shares"
        assert quantity.security_class_id is None or quantity.security_class_id == CLASS


# ---------------------------------------------------------------------------
# A23 — a resale of already outstanding shares mints nothing
# ---------------------------------------------------------------------------


def resale_instruments(registered: str = "5000000", **over):
    common_id, common = make_instrument("series_a23_resale_common", kind="common",
                                        resale_registered_shares=registered, **over)
    return instrument_set((common_id, common)), common_id


def test_a23_a_resale_mints_no_new_shares_and_no_issuer_cash():
    instruments, common_id = resale_instruments()
    selected_scenario = scenario([])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert component(envelope, "resalable_existing").value == "5000000"
    assert component(envelope, "resalable_existing").status == "known"
    assert component(envelope, "incremental_issuance").value == "0"
    assert component(envelope, "existing_outstanding").value == OUTSTANDING
    assert component(envelope, "as_converted_claims").status == "not_applicable"
    assert trace["rows"] == []
    assert len(envelope.cash_effects) == 1
    effect = envelope.cash_effects[0]
    assert effect.route_id == f"resale_{common_id}"
    assert effect.kind == "no_cash"
    assert effect.gross.decimal == Decimal(0) and effect.net.decimal == Decimal(0)
    assert trace["resale"] == [
        {
            "instrument_id": common_id,
            "kind": "common",
            "registered_shares": "5000000",
            "whole_shares": "5000000",
            "cash_route_id": f"resale_{common_id}",
        }
    ]
    assert "resale_mints_no_shares_or_issuer_cash" in envelope.double_count_guards
    assert unknown_ids(envelope) == []


def test_a23_a_resale_stays_out_of_incremental_beside_a_real_issuance():
    resale_set, common_id = resale_instruments()
    warrant_id, warrant = make_instrument(
        "series_a23_cash_warrants",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        exercise_price=STRIKE,
    )
    instruments = instrument_set(*[(item.instrument_id, item) for item in resale_set.instruments], (warrant_id, warrant))
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    # The resale is a separate component: it neither adds to nor subtracts from
    # the issuance, and the issuer receives cash only for the new shares.
    assert component(envelope, "incremental_issuance").value == "1000000"
    assert component(envelope, "resalable_existing").value == "5000000"
    assert component(envelope, "existing_outstanding").value == OUTSTANDING
    effects = cash_by_route(envelope)
    assert effects[f"resale_{common_id}"].kind == "no_cash"
    assert effects[warrant_id].kind == "proceeds"
    assert effects[warrant_id].gross.decimal == Decimal(1000000)
    assert Decimal(sum(1 for _ in trace["rows"])) == Decimal(1)


def test_a23_a_contradicted_resale_count_is_unknown_never_zero():
    common_id = instrument_id_for(ISSUER, "series_a23_resale_common")
    _resolved, common = IE.instrument_for(
        "series_a23_resale_common",
        kind="common",
        economic_terms=(economic_term(common_id, "resale_registered_shares", status="contradicted"),),
    )
    instruments = instrument_set((common_id, common))
    envelope, trace = evaluate(instruments, basis(), scenario([]))
    assert component(envelope, "resalable_existing").status == "unknown"
    assert component(envelope, "resalable_existing").value is None
    assert f"term_{common_id}_resale_registered_shares" in unknown_ids(envelope)
    assert trace["resale"][0]["whole_shares"] == "unknown"
    # A23 holds whatever the count turns out to be: still no shares, still no cash.
    assert envelope.cash_effects[0].kind == "no_cash"
    assert component(envelope, "incremental_issuance").value == "0"


# ---------------------------------------------------------------------------
# A25 — a cap or a notice period limits the scenario, never the claim
# ---------------------------------------------------------------------------


def notice_instruments(notice_days: str = "61"):
    warrant_id, warrant = make_instrument(
        "series_a25_notice_warrants",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        exercise_price=STRIKE,
        notice_days=notice_days,
    )
    return instrument_set((warrant_id, warrant)), warrant_id


def capped_instruments(cap: str = CAP, count: str = "2000000", kind: str = "warrant", **over):
    terms = dict(
        instruments_outstanding=count,
        shares_per_instrument="1",
        beneficial_ownership_cap=cap,
    )
    if kind == "pre_funded_warrant":
        terms["prefunded_residual_price"] = RESIDUAL
    else:
        terms["exercise_price"] = STRIKE
    terms.update(over)
    warrant_id, warrant = make_instrument("series_a25_capped_warrants", kind=kind, **terms)
    return instrument_set((warrant_id, warrant)), warrant_id


def holder_position(instrument_id: str, position: str) -> c.UnknownResolution:
    return c.UnknownResolution(
        unknown_id=f"holder_position_{instrument_id}",
        assumed=c.Quantity.known(position, "shares", share_basis="issued_and_outstanding"),
        rationale="the holder's position per the scenario's stated assumption",
    )


def test_a25_notice_longer_than_the_horizon_issues_nothing_and_keeps_the_claim():
    instruments, warrant_id = notice_instruments("61")
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")],
                                 horizon_start=HORIZON_START, horizon_end="2026-11-12")
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert trace["horizon_days"] == "30"
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == "0"
    assert row["underlying_shares"] == "1000000"
    assert row["gross_cash"] == "0" and row["net_cash"] == "0"
    assert cash_by_route(envelope)[warrant_id].kind == "proceeds"
    assert "notice_period_limits_execution" in row["guards"]
    assert "claim_survives_execution_limit" in row["guards"]
    assert "notice_period_limits_execution" in envelope.double_count_guards
    assert component(envelope, "incremental_issuance").value == "0"
    # The claim is untouched: a notice period limits THIS scenario only.
    assert component(envelope, "as_converted_claims").value == "1000000"
    assert trace["claims"] == [
        {"instrument_id": warrant_id, "kind": "warrant", "claim": "1000000", "remainder": "0"}
    ]
    assert unknown_ids(envelope) == []


def test_a25_notice_shorter_than_the_horizon_limits_nothing():
    instruments, warrant_id = notice_instruments("30")
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert trace["horizon_days"] == "365"
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == "1000000"
    assert row["guards"] == []
    assert "notice_period_limits_execution" not in envelope.double_count_guards
    assert unknown_ids(envelope) == []


def test_a25_cap_without_a_holder_position_is_unknown_and_never_unbounded():
    instruments, warrant_id = capped_instruments()
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == "unknown"
    assert row["underlying_shares"] == "unknown"
    assert row["gross_cash"] == "unknown" and row["net_cash"] == "unknown"
    assert f"holder_position_{warrant_id}" in row["unknowns"]
    assert f"holder_position_{warrant_id}" in unknown_ids(envelope)
    assert component(envelope, "incremental_issuance").status == "unknown"
    assert component(envelope, "incremental_issuance").value is None
    # The claim survives: it is a contractual fact, not a scenario quantity.
    assert component(envelope, "as_converted_claims").value == "2000000"
    assert cash_by_route(envelope)[warrant_id].kind == "proceeds"
    assert cash_by_route(envelope)[warrant_id].gross.status == "unknown"


def test_a25_cap_with_a_zero_position_limits_the_row_exactly():
    instruments, warrant_id = capped_instruments()
    selected_scenario = scenario(
        [selection(warrant_id, "warrant_exercise", "cash")],
        unknown_resolutions=[holder_position(warrant_id, "0")],
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert CAP_CEILING == "1109876"
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == CAP_CEILING
    assert row["underlying_shares"] == "2000000"
    assert "holder_cap_limits_execution" in row["guards"]
    assert "claim_survives_execution_limit" in row["guards"]
    assert row["gross_cash"] == CAP_CEILING
    assert Decimal(row["net_cash"]) == Decimal(CAP_CEILING) * (Decimal(1) - Decimal(FEE))
    assert "holder_cap_limits_execution" in envelope.double_count_guards
    assert component(envelope, "incremental_issuance").value == CAP_CEILING
    assert component(envelope, "as_converted_claims").value == "2000000"
    assert unknown_ids(envelope) == []


def test_a25_a_held_position_leaves_exactly_less_room():
    instruments, warrant_id = capped_instruments()
    position = "500000"
    expected = (CAP_FRACTION * Fraction(Decimal(OUTSTANDING)) - Fraction(Decimal(position))) // (1 - CAP_FRACTION)
    selected_scenario = scenario(
        [selection(warrant_id, "warrant_exercise", "cash")],
        unknown_resolutions=[holder_position(warrant_id, position)],
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == str(expected)
    assert Decimal(row["incremental_shares"]) < Decimal(CAP_CEILING)
    assert "holder_cap_limits_execution" in row["guards"]
    assert component(envelope, "as_converted_claims").value == "2000000"


def test_a25_a_cap_of_one_hundred_never_binds():
    instruments, warrant_id = capped_instruments(cap="100")
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == "2000000"
    assert row["guards"] == []
    assert f"holder_position_{warrant_id}" not in unknown_ids(envelope)
    assert "holder_cap_limits_execution" not in envelope.double_count_guards
    assert component(envelope, "incremental_issuance").value == "2000000"


def test_a25_a_cap_that_would_not_bind_still_needs_the_position():
    instruments, warrant_id = capped_instruments(count="100000")
    # Whether a cap binds is unknowable without the holder's position, so the
    # position is required even here: unknown is never read as "no limit".
    envelope, trace = evaluate(instruments, basis(), scenario([selection(warrant_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[warrant_id]["incremental_shares"] == "unknown"
    assert f"holder_position_{warrant_id}" in unknown_ids(envelope)
    resolved = scenario(
        [selection(warrant_id, "warrant_exercise", "cash")],
        unknown_resolutions=[holder_position(warrant_id, "0")],
    )
    envelope, trace = evaluate(instruments, basis(), resolved)
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == "100000"
    assert "holder_cap_limits_execution" not in row["guards"]
    assert "claim_survives_execution_limit" not in row["guards"]
    assert unknown_ids(envelope) == []


def test_a25_a_cap_recomputes_cash_on_the_limited_shares_for_a_pre_funded_row():
    instruments, warrant_id = capped_instruments(kind="pre_funded_warrant")
    selected_scenario = scenario(
        [selection(warrant_id, "warrant_exercise", "pre_funded")],
        unknown_resolutions=[holder_position(warrant_id, "0")],
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[warrant_id]
    assert row["settlement"] == "pre_funded"
    assert row["incremental_shares"] == CAP_CEILING
    assert Decimal(row["gross_cash"]) == Decimal(CAP_CEILING) * Decimal(RESIDUAL)
    assert cash_by_route(envelope)[warrant_id].kind == "proceeds"
    assert "prefunded_paid_economics_not_recounted" in envelope.double_count_guards


def test_a25_an_unreadable_cap_is_never_read_as_no_cap():
    instruments, warrant_id = capped_instruments()
    replaced = dataclasses.replace(
        instruments.instruments[0],
        economic_terms=tuple(
            economic_term(warrant_id, term.name, status="unknown") if term.name == "beneficial_ownership_cap" else term
            for term in instruments.instruments[0].economic_terms
        ),
    )
    instruments = dataclasses.replace(instruments, instruments=(replaced,))
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[warrant_id]
    assert row["incremental_shares"] == "unknown"
    assert f"term_{warrant_id}_beneficial_ownership_cap" in row["unknowns"]
    assert component(envelope, "incremental_issuance").status == "unknown"
    assert component(envelope, "as_converted_claims").value == "2000000"


def test_a25_a_contradicted_notice_period_is_never_read_as_no_notice():
    instruments, warrant_id = notice_instruments()
    replaced = dataclasses.replace(
        instruments.instruments[0],
        economic_terms=tuple(
            economic_term(warrant_id, term.name, status="contradicted") if term.name == "notice_days" else term
            for term in instruments.instruments[0].economic_terms
        ),
    )
    instruments = dataclasses.replace(instruments, instruments=(replaced,))
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")], horizon_end="2026-11-12")
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[warrant_id]["incremental_shares"] == "unknown"
    assert f"term_{warrant_id}_notice_days" in unknown_ids(envelope)
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_a25_the_claim_survives_every_execution_limit():
    notice_set, notice_id = notice_instruments("61")
    cap_set, cap_id = capped_instruments()
    instruments = instrument_set(
        (notice_id, notice_set.instruments[0]), (cap_id, cap_set.instruments[0])
    )
    selected_scenario = scenario(
        [
            selection(notice_id, "warrant_exercise", "cash"),
            selection(cap_id, "warrant_exercise", "cash"),
        ],
        horizon_end="2026-11-12",
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert all(row["incremental_shares"] in ("0", "unknown") for row in trace["rows"])
    assert component(envelope, "incremental_issuance").status == "unknown"
    # Both full claims stay in as_converted_claims whatever the scenario did.
    assert component(envelope, "as_converted_claims").value == "3000000"
    assert {entry["instrument_id"]: entry["claim"] for entry in trace["claims"]} == {
        notice_id: "1000000",
        cap_id: "2000000",
    }
    assert "claim_survives_execution_limit" in envelope.double_count_guards


def test_a25_a_holder_position_must_be_a_known_share_quantity():
    instruments, warrant_id = capped_instruments()
    with pytest.raises(c.ContractViolation, match="shares quantity"):
        evaluate(
            instruments,
            basis(),
            scenario(
                [selection(warrant_id, "warrant_exercise", "cash")],
                unknown_resolutions=[
                    c.UnknownResolution(
                        unknown_id=f"holder_position_{warrant_id}",
                        assumed=c.Quantity.known("0", "usd"),
                        rationale="the wrong unit",
                    )
                ],
            ),
        )


# ---------------------------------------------------------------------------
# A19 — no universal split factor: a pre-split term is stale, not convertible
# ---------------------------------------------------------------------------

SPLIT_SERIES = "series_a19_split_warrants"


def split_warrant(price_effective_at: str = POST_SPLIT, count_effective_at: str = POST_SPLIT,
                  price: str = STRIKE, count: str = "100000", per_instrument: str = "10"):
    """A post-split warrant: 100,000 instruments x 10 shares = a 1,000,000 claim."""
    instrument_id = instrument_id_for(ISSUER, SPLIT_SERIES)
    terms = (
        economic_term(instrument_id, "instruments_outstanding", count, effective_at=count_effective_at),
        economic_term(instrument_id, "shares_per_instrument", per_instrument, effective_at=count_effective_at),
        economic_term(instrument_id, "exercise_price", price, effective_at=price_effective_at),
    )
    _resolved, warrant = IE.instrument_for(SPLIT_SERIES, kind="warrant", economic_terms=terms)
    return instrument_id, instrument_set((instrument_id, warrant))


def test_a19_a_pre_split_exercise_price_is_stale_and_unknown():
    instrument_id, instruments = split_warrant(price_effective_at=PRE_SPLIT)
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, split_basis(), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "unknown"
    assert row["gross_cash"] == "unknown" and row["net_cash"] == "unknown"
    assert f"stale_presplit_{instrument_id}_exercise_price" in row["unknowns"]
    assert f"stale_presplit_{instrument_id}_exercise_price" in unknown_ids(envelope)
    assert f"term_{instrument_id}_exercise_price" not in unknown_ids(envelope)
    assert component(envelope, "incremental_issuance").status == "unknown"
    # The claim terms are post-split, so the claim itself stays known.
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_a19_an_admitted_post_split_price_computes_exactly():
    instrument_id, instruments = split_warrant()
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, split_basis(), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "1000000"
    assert row["gross_cash"] == "1000000"
    assert row["net_cash"] == "970000"
    assert unknown_ids(envelope) == []
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_a19_a_forward_split_makes_the_same_term_stale():
    instrument_id, instruments = split_warrant(price_effective_at=PRE_SPLIT)
    forward = basis(
        corporate_action=c.CorporateActionBasis(
            kind="forward_split",
            ratio="2",
            effective_date=SPLIT_DATE,
            contract_adjustment_evidence=(T.ev(5),),
        )
    )
    envelope, trace = evaluate(instruments, forward, scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"stale_presplit_{instrument_id}_exercise_price" in unknown_ids(envelope)


def test_a19_an_undated_term_is_stale_under_a_split():
    instrument_id, instruments = split_warrant(count_effective_at=None)
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, split_basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"stale_presplit_{instrument_id}_instruments_outstanding" in unknown_ids(envelope)
    # A ratio term cannot be admitted undated at all (C0 dates every admitted
    # price and ratio), so this one stays post-split and is not stale.
    assert f"stale_presplit_{instrument_id}_shares_per_instrument" not in unknown_ids(envelope)
    with pytest.raises(c.ContractViolation, match="is dated"):
        c.EconomicTerm(
            term_id="econterm:cs:undated",
            instrument_id=instrument_id,
            name="shares_per_instrument",
            status="admitted",
            value=c.Quantity.known("10", "ratio"),
            flag=None,
            expression=None,
            date_value=None,
            evidence=(T.ev(3),),
            fact_origin="canonical_extraction",
            interpretation_version="1.0.0",
            available_at=AVAILABLE,
            effective_at=None,
        )
    # The claim is built from the stale term, so it is unknown too — never 0.
    assert component(envelope, "as_converted_claims").status == "unknown"


def test_a19_the_split_factor_is_never_read_by_any_arithmetic():
    instrument_id, instruments = split_warrant()
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    first, first_trace = evaluate(instruments, split_basis(ratio="0.1"), selected_scenario)
    second, second_trace = evaluate(instruments, split_basis(ratio="0.5"), selected_scenario)
    # Two bases differing ONLY in the split factor give identical consequences.
    assert first_trace["rows"] == second_trace["rows"]
    assert first_trace["claims"] == second_trace["claims"]
    assert first_trace["unknowns"] == second_trace["unknowns"] == []
    assert first_trace["guards"] == second_trace["guards"]
    for name in COMPONENT_NAMES:
        assert component(first, name) == component(second, name)
    assert first.cash_effects == second.cash_effects
    # The factor is an input, so the identity legitimately differs; the answer does not.
    assert first.state_id != second.state_id
    assert rows_by_route(first_trace)[instrument_id]["incremental_shares"] == "1000000"
    source = MODULE.read_text()
    assert ".ratio" not in source
    assert "corporate_action.ratio" not in source


def test_a19_without_a_split_a_pre_split_dated_term_is_not_stale():
    instrument_id, instruments = split_warrant(price_effective_at=PRE_SPLIT)
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "1000000"
    assert unknown_ids(envelope) == []


def test_a19_a_stale_price_is_never_multiplied_into_an_answer():
    instrument_id, instruments = split_warrant(price_effective_at=PRE_SPLIT, price="10.00")
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, split_basis(ratio="0.1"), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "unknown"
    # Neither 1.00 nor 10.00 nor any factor-adjusted reading of them is emitted.
    for forbidden in ("1000000", "100000", "10000000"):
        assert row["gross_cash"] != forbidden
    assert cash_by_route(envelope)[instrument_id].gross.status == "unknown"


# ---------------------------------------------------------------------------
# Unknown discipline — a missing term is never 0 and never unbounded
# ---------------------------------------------------------------------------


def test_unknown_missing_k_leaves_the_cash_row_unknown_never_zero():
    instrument_id, warrant = plain_warrant(exercise_price=None)
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "unknown"
    assert row["underlying_shares"] == "unknown"
    assert row["gross_cash"] == "unknown" and row["net_cash"] == "unknown"
    assert row["unknowns"] == [f"term_{instrument_id}_exercise_price"]
    assert unknown_ids(envelope) == [f"term_{instrument_id}_exercise_price"]
    assert component(envelope, "incremental_issuance").status == "unknown"
    assert component(envelope, "incremental_issuance").value is None
    effect = cash_by_route(envelope)[instrument_id]
    assert effect.kind == "proceeds"
    assert effect.gross.status == "unknown" and effect.net.status == "unknown"
    # The claim needs no price, so it stays known: unknown is per-fact, never global.
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_unknown_missing_claim_terms_leave_the_row_and_the_claim_unknown():
    instrument_id, warrant = plain_warrant(shares_per_instrument=None)
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"term_{instrument_id}_shares_per_instrument" in unknown_ids(envelope)
    assert component(envelope, "as_converted_claims").status == "unknown"
    assert trace["claims"] == [
        {"instrument_id": instrument_id, "kind": "warrant", "claim": "unknown", "remainder": "0"}
    ]


def test_unknown_expression_price_is_never_a_number():
    instrument_id = series_id("series_u_formula_warrants")
    formula = economic_term(
        instrument_id,
        "exercise_price",
        expression="the greater of $1.00 and 90% of the ten trading day VWAP",
    )
    assert formula.status == "admitted" and formula.value.status == "unknown"
    _resolved, warrant = plain_warrant("series_u_formula_warrants", exercise_price=formula)
    instruments = instrument_set((instrument_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert unknown_ids(envelope) == [f"term_{instrument_id}_exercise_price"]
    # A26 (resets, floors and caps) is I2's: I1a names the gap and computes nothing.
    assert component(envelope, "incremental_issuance").status == "unknown"


def test_unknown_contradicted_price_is_never_a_number():
    instrument_id = series_id("series_u_conflicted_warrants")
    contradicted = economic_term(instrument_id, "exercise_price", status="contradicted")
    _resolved, warrant = plain_warrant("series_u_conflicted_warrants", exercise_price=contradicted)
    instruments = instrument_set((instrument_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert unknown_ids(envelope) == [f"term_{instrument_id}_exercise_price"]


def test_unknown_deferred_price_is_never_a_number():
    instrument_id = series_id("series_u_deferred_warrants")
    deferred = economic_term(instrument_id, "exercise_price", status="unknown")
    _resolved, warrant = plain_warrant("series_u_deferred_warrants", exercise_price=deferred)
    instruments = instrument_set((instrument_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert unknown_ids(envelope) == [f"term_{instrument_id}_exercise_price"]


def test_unknown_unselected_basis_leaves_existing_outstanding_unknown():
    instrument_id, warrant = plain_warrant()
    instruments = instrument_set((instrument_id, warrant))
    conflicted = basis(status="conflict", conflicts=("two candidate observations disagree on the count",))
    envelope, _trace = evaluate(instruments, conflicted, scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    existing = component(envelope, "existing_outstanding")
    assert existing.status == "unknown"
    assert existing.value is None
    assert existing.share_basis == "issued_and_outstanding"
    assert "share_basis_conflict" in unknown_ids(envelope)
    # The other three components answer their own questions and stay known.
    assert component(envelope, "incremental_issuance").value == "1000000"
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_unknown_unselected_basis_leaves_a_capped_row_unknown():
    instruments, warrant_id = capped_instruments()
    conflicted = basis(status="conflict", conflicts=("two candidate observations disagree on the count",))
    selected_scenario = scenario(
        [selection(warrant_id, "warrant_exercise", "cash")],
        unknown_resolutions=[holder_position(warrant_id, "0")],
    )
    envelope, trace = evaluate(instruments, conflicted, selected_scenario)
    assert rows_by_route(trace)[warrant_id]["incremental_shares"] == "unknown"
    assert "share_basis_conflict" in unknown_ids(envelope)
    assert component(envelope, "existing_outstanding").status == "unknown"
    assert component(envelope, "as_converted_claims").value == "2000000"


def test_unknown_path_with_no_point_on_or_before_the_horizon():
    instrument_id, warrant = plain_warrant("series_u_path_warrants", cashless_exercise_permitted=True)
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario(
        [selection(instrument_id, "warrant_exercise", "cashless")],
        price=c.PriceAssumption("path", "USD", path=(("2028-01-04", "2.50"), ("2029-01-03", "3.00"))),
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert "price_at_horizon" in unknown_ids(envelope)
    assert trace["price"]["kind"] == "path"
    assert trace["price"]["value"] == "unknown"
    assert trace["price"]["required"] is True
    assert trace["price"]["unknowns"] == ["price_at_horizon"]
    assert component(envelope, "incremental_issuance").status == "unknown"


def test_unknown_path_price_is_the_last_point_on_or_before_the_horizon():
    instrument_id, warrant = plain_warrant("series_u_path_warrants", cashless_exercise_permitted=True)
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario(
        [selection(instrument_id, "warrant_exercise", "cashless")],
        price=c.PriceAssumption(
            "path", "USD", path=(("2026-11-02", "1.00"), ("2027-01-04", PRICE), ("2028-01-03", "9.00"))
        ),
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert trace["price"]["value"] == PRICE
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "600000"
    assert unknown_ids(envelope) == []


def test_unknown_price_currency_other_than_usd():
    instrument_id, warrant = plain_warrant("series_u_fx_warrants", cashless_exercise_permitted=True)
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario(
        [selection(instrument_id, "warrant_exercise", "cashless")],
        price=c.PriceAssumption("fixed", "CAD", fixed_price=PRICE),
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert "price_currency" in unknown_ids(envelope)
    assert trace["price"]["currency"] == "CAD"


def test_unknown_price_is_required_only_by_a_cashless_or_net_share_row():
    instrument_id, warrant = plain_warrant()
    instruments = instrument_set((instrument_id, warrant))
    unpriced = c.PriceAssumption("path", "USD", path=(("2028-01-04", PRICE),))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "cash")],
                                                              price=unpriced))
    # A cash row never needs P, so no price Unknown is emitted for one (D8).
    assert unknown_ids(envelope) == []
    assert trace["price"]["required"] is False
    assert trace["price"]["unknowns"] == []
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "1000000"


def test_unknown_fee_rate_leaves_net_proceeds_unknown_never_zero():
    instrument_id, warrant = plain_warrant()
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")], fee_rate=None)
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "1000000"
    assert row["gross_cash"] == "1000000"
    assert row["net_cash"] == "unknown"
    assert "fee_rate" in unknown_ids(envelope)
    effect = cash_by_route(envelope)[instrument_id]
    assert effect.gross.decimal == Decimal(1000000)
    assert effect.net.status == "unknown"


def test_unknown_fee_rate_is_not_needed_for_a_zero_gross_row():
    instrument_id, warrant = plain_warrant("series_u_notice_free_warrants", notice_days="61")
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")],
                                 fee_rate=None, horizon_end="2026-11-12")
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "0"
    assert row["gross_cash"] == "0" and row["net_cash"] == "0"
    assert "fee_rate" not in unknown_ids(envelope)


def test_unknown_settlement_is_never_guessed():
    instrument_id, warrant = plain_warrant()
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "unknown")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"settlement_unknown_{instrument_id}" in unknown_ids(envelope)
    assert component(envelope, "incremental_issuance").status == "unknown"


def test_unknown_route_not_supply_contributes_nothing_but_its_unknown():
    instrument_id, warrant = plain_warrant()
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario(
        [
            selection(instrument_id, "warrant_exercise", "cash"),
            selection("route:atm", "at_the_market", "cash", quantity=c.Quantity.known("8000000", "usd")),
        ]
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)["route:atm"]
    assert row["instrument_id"] is None
    assert row["action"] == "at_the_market"
    assert row["underlying_shares"] == "unknown"
    assert row["incremental_shares"] == "unknown"
    assert row["gross_cash"] == "unknown" and row["net_cash"] == "unknown"
    assert row["unknowns"] == ["route_not_supply_route:atm"]
    # No cash effect is invented for a capacity route (C1/C2 own it).
    assert "route:atm" not in cash_by_route(envelope)
    assert len(envelope.cash_effects) == 1
    # A selected action whose issuance is unknown makes the component unknown — never 0.
    assert component(envelope, "incremental_issuance").status == "unknown"
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_unknown_a_route_the_set_cannot_identify_contributes_nothing():
    instrument_id, warrant = plain_warrant()
    instruments = instrument_set((instrument_id, warrant))
    absent = "instrument:cs:00000000000000000000000000000000"
    selected_scenario = scenario([selection(absent, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[absent]
    assert row["incremental_shares"] == "unknown"
    assert row["unknowns"] == [f"instrument_{absent}"]
    assert absent not in cash_by_route(envelope)
    assert component(envelope, "incremental_issuance").status == "unknown"


def test_unknown_cashless_requires_an_admitted_permission_flag():
    instrument_id, warrant = plain_warrant("series_u_unflagged_warrants")
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cashless")])
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert unknown_ids(envelope) == [f"term_{instrument_id}_cashless_exercise_permitted"]
    # Admitted false is a refusal, not an unknown: never silently re-routed.
    refused_id, refused = plain_warrant("series_u_refused_warrants", cashless_exercise_permitted=False)
    envelope, trace = evaluate(instrument_set((refused_id, refused)), basis(),
                               scenario([selection(refused_id, "warrant_exercise", "cashless")]))
    assert rows_by_route(trace)[refused_id]["incremental_shares"] == "unknown"
    assert f"settlement_not_permitted_{refused_id}" in unknown_ids(envelope)
    # Admitted true computes.
    permitted_id, permitted = plain_warrant("series_u_permitted_warrants", cashless_exercise_permitted=True)
    envelope, trace = evaluate(instrument_set((permitted_id, permitted)), basis(),
                               scenario([selection(permitted_id, "warrant_exercise", "cashless")]))
    assert rows_by_route(trace)[permitted_id]["incremental_shares"] == "600000"
    assert unknown_ids(envelope) == []


def test_unknown_a_contradicted_permission_flag_is_unknown_not_permitted():
    instrument_id = series_id("series_u_contradicted_flag_warrants")
    flag = economic_term(instrument_id, "cash_exercise_permitted", status="contradicted")
    _resolved, warrant = plain_warrant("series_u_contradicted_flag_warrants", cash_exercise_permitted=flag)
    instruments = instrument_set((instrument_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert unknown_ids(envelope) == [f"term_{instrument_id}_cash_exercise_permitted"]


def test_unknown_cash_exercise_admitted_false_is_refused_not_rerouted():
    instrument_id, warrant = plain_warrant("series_u_no_cash_warrants", cash_exercise_permitted=False)
    instruments = instrument_set((instrument_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    row = rows_by_route(trace)[instrument_id]
    assert row["settlement"] == "cash"
    assert row["incremental_shares"] == "unknown"
    assert f"settlement_not_permitted_{instrument_id}" in unknown_ids(envelope)
    effect = cash_by_route(envelope)[instrument_id]
    assert effect.kind == "proceeds"
    assert effect.gross.status == "unknown"
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_unknown_a_price_at_or_below_the_strike_issues_a_known_zero():
    instrument_id, warrant = plain_warrant("series_u_underwater_warrants", cashless_exercise_permitted=True)
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cashless")],
                                 price=c.PriceAssumption("fixed", "USD", fixed_price="0.50"))
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    row = rows_by_route(trace)[instrument_id]
    # The frozen table states 0 shares when P is not above K: a KNOWN zero.
    assert row["incremental_shares"] == "0"
    assert row["fraction"] == "0"
    assert component(envelope, "incremental_issuance").value == "0"
    assert component(envelope, "incremental_issuance").status == "known"
    assert unknown_ids(envelope) == []
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_unknown_a_zero_conversion_price_is_unknown_not_infinite():
    instrument_id, note = make_instrument(
        "series_u_zero_price_notes",
        kind="convertible_note",
        principal_outstanding=PRINCIPAL,
        conversion_price="0",
        cashless_exercise_permitted=True,
    )
    instruments = instrument_set((instrument_id, note))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "conversion", "cashless")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"term_{instrument_id}_conversion_price" in unknown_ids(envelope)
    assert component(envelope, "as_converted_claims").status == "unknown"


# ---------------------------------------------------------------------------
# §5.4 / D2 — action, kind and settlement compatibility
# ---------------------------------------------------------------------------


def convertible_note(series_key="series_c_notes", principal=PRINCIPAL, price=CONVERSION_PRICE, **over):
    return make_instrument(
        series_key,
        kind="convertible_note",
        principal_outstanding=principal,
        conversion_price=price,
        cashless_exercise_permitted=True,
        **over,
    )


def test_contract_a_conversion_of_a_warrant_is_not_permitted():
    instrument_id, warrant = plain_warrant("series_x_warrant_as_note")
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "conversion", "cashless")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"settlement_not_permitted_{instrument_id}" in unknown_ids(envelope)


def test_contract_a_warrant_exercise_of_a_convertible_note_is_not_permitted():
    instrument_id, note = convertible_note("series_x_note_as_warrant")
    envelope, trace = evaluate(instrument_set((instrument_id, note)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "cashless")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"settlement_not_permitted_{instrument_id}" in unknown_ids(envelope)


def test_contract_a_cash_settled_conversion_is_i2s_not_i1as():
    instrument_id, note = convertible_note("series_x_cash_conversion")
    envelope, trace = evaluate(instrument_set((instrument_id, note)), basis(),
                               scenario([selection(instrument_id, "conversion", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"settlement_not_permitted_{instrument_id}" in unknown_ids(envelope)
    assert component(envelope, "incremental_issuance").status == "unknown"


def test_contract_a_pre_funded_warrant_settles_only_pre_funded():
    instrument_id, warrant = make_instrument(
        "series_x_prefunded",
        kind="pre_funded_warrant",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        prefunded_residual_price=RESIDUAL,
    )
    instruments = instrument_set((instrument_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(instrument_id, "warrant_exercise", "pre_funded")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "1000000"
    assert rows_by_route(trace)[instrument_id]["gross_cash"] == "1000"
    for settlement in ("cash", "cashless", "net_share"):
        refused, refused_trace = evaluate(instruments, basis(),
                                          scenario([selection(instrument_id, "warrant_exercise", settlement)]))
        assert rows_by_route(refused_trace)[instrument_id]["incremental_shares"] == "unknown"
        assert f"settlement_not_permitted_{instrument_id}" in unknown_ids(refused)


def test_contract_a_plain_warrant_may_not_settle_pre_funded():
    instrument_id, warrant = plain_warrant("series_x_plain_prefunded")
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "pre_funded")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"settlement_not_permitted_{instrument_id}" in unknown_ids(envelope)


def test_contract_net_share_settlement_nets_the_spread_like_cashless():
    instrument_id, warrant = plain_warrant("series_x_net_share", cashless_exercise_permitted=True)
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "net_share")]))
    row = rows_by_route(trace)[instrument_id]
    assert row["settlement"] == "net_share"
    assert row["incremental_shares"] == "600000"
    assert cash_by_route(envelope)[instrument_id].kind == "no_cash"


def test_contract_a_convertible_preferred_converts_on_the_same_rule():
    instrument_id, preferred = make_instrument(
        "series_x_preferred",
        kind="convertible_preferred",
        principal_outstanding=PRINCIPAL,
        conversion_price=CONVERSION_PRICE,
        cashless_exercise_permitted=True,
    )
    envelope, trace = evaluate(instrument_set((instrument_id, preferred)), basis(),
                               scenario([selection(instrument_id, "conversion", "net_share")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "4000000"
    assert component(envelope, "as_converted_claims").value == "4000000"
    assert cash_by_route(envelope)[instrument_id].kind == "no_cash"


def test_contract_every_non_supply_route_kind_contributes_only_its_unknown():
    instrument_id, warrant = plain_warrant("series_x_capacity")
    instruments = instrument_set((instrument_id, warrant))
    for action in ("shelf_takedown", "at_the_market", "equity_line", "registered_direct", "pipe",
                   "debt_draw", "repurchase", "redemption", "exchange", "other"):
        route_id = f"route:{action}"
        envelope, trace = evaluate(instruments, basis(), scenario([selection(route_id, action, "cash")]))
        row = rows_by_route(trace)[route_id]
        assert row["instrument_id"] is None
        assert row["incremental_shares"] == "unknown"
        assert row["unknowns"] == [f"route_not_supply_{route_id}"]
        assert envelope.cash_effects == ()
        assert component(envelope, "incremental_issuance").status == "unknown"


# ---------------------------------------------------------------------------
# D5 — the selected quantity is underlying shares, capped at the claim
# ---------------------------------------------------------------------------


def selected_shares(value: str, share_basis: str = "reserved_for_issuance") -> c.Quantity:
    return c.Quantity.known(value, "shares", share_basis=share_basis)


def test_contract_a_partial_selection_issues_exactly_the_selected_shares():
    instrument_id, warrant = plain_warrant("series_q_partial")
    envelope, trace = evaluate(
        instrument_set((instrument_id, warrant)),
        basis(),
        scenario([selection(instrument_id, "warrant_exercise", "cash", quantity=selected_shares("250000"))]),
    )
    row = rows_by_route(trace)[instrument_id]
    assert row["underlying_shares"] == "250000"
    assert row["incremental_shares"] == "250000"
    assert row["gross_cash"] == "250000"
    assert row["net_cash"] == "242500"
    assert row["guards"] == []
    assert component(envelope, "incremental_issuance").value == "250000"
    # The claim is the contractual one, not the selected slice of it.
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_contract_a_selection_above_the_claim_is_capped_at_the_claim():
    instrument_id, warrant = plain_warrant("series_q_capped")
    envelope, trace = evaluate(
        instrument_set((instrument_id, warrant)),
        basis(),
        scenario([selection(instrument_id, "warrant_exercise", "cash", quantity=selected_shares("5000000"))]),
    )
    row = rows_by_route(trace)[instrument_id]
    assert row["underlying_shares"] == "1000000"
    assert row["incremental_shares"] == "1000000"
    assert "selection_capped_at_claim" in row["guards"]
    assert "claim_survives_execution_limit" in row["guards"]
    assert row["gross_cash"] == "1000000"
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_contract_a_cashless_selection_nets_the_spread_on_the_selected_shares():
    instrument_id, warrant = plain_warrant("series_q_cashless", cashless_exercise_permitted=True)
    envelope, trace = evaluate(
        instrument_set((instrument_id, warrant)),
        basis(),
        scenario([selection(instrument_id, "warrant_exercise", "cashless", quantity=selected_shares("500000"))]),
    )
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "300000"
    assert unknown_ids(envelope) == []


def test_contract_a_conversion_selection_is_capped_at_principal_over_conversion_price():
    instrument_id, note = convertible_note("series_q_conversion")
    envelope, trace = evaluate(
        instrument_set((instrument_id, note)),
        basis(),
        scenario([selection(instrument_id, "conversion", "cashless", quantity=selected_shares("9000000"))]),
    )
    row = rows_by_route(trace)[instrument_id]
    assert row["underlying_shares"] == "4000000"
    assert row["incremental_shares"] == "4000000"
    assert "selection_capped_at_claim" in row["guards"]


def test_contract_an_unknown_selection_quantity_leaves_the_row_unknown():
    instrument_id, warrant = plain_warrant("series_q_unknown_quantity")
    unknown_quantity = c.Quantity.unknown("shares", share_basis="reserved_for_issuance")
    envelope, trace = evaluate(
        instrument_set((instrument_id, warrant)),
        basis(),
        scenario([selection(instrument_id, "warrant_exercise", "cash", quantity=unknown_quantity)]),
    )
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"quantity_{instrument_id}" in unknown_ids(envelope)
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_contract_a_non_shares_selection_unit_is_refused():
    instrument_id, warrant = plain_warrant("series_q_wrong_unit")
    with pytest.raises(c.ContractViolation, match="underlying share count"):
        evaluate(
            instrument_set((instrument_id, warrant)),
            basis(),
            scenario([selection(instrument_id, "warrant_exercise", "cash", quantity=c.Quantity.known("1000", "usd"))]),
        )


# ---------------------------------------------------------------------------
# D7 — exact arithmetic: floored shares, recorded remainders, unrounded money
# ---------------------------------------------------------------------------


def test_contract_fractional_shares_are_floored_and_the_remainder_is_recorded():
    instrument_id, warrant = plain_warrant(
        "series_f_fractional", instruments_outstanding="1000001", cashless_exercise_permitted=True
    )
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "cashless")]))
    row = rows_by_route(trace)[instrument_id]
    assert row["underlying_shares"] == "1000001"
    assert row["incremental_shares"] == "600000"
    assert row["fraction"] == "3/5"
    assert Fraction(1000001) * (Fraction(Decimal(PRICE)) - Fraction(Decimal(STRIKE))) / Fraction(Decimal(PRICE)) == Fraction(3000003, 5)
    assert component(envelope, "incremental_issuance").value == "600000"
    assert trace["claims"][0]["remainder"] == "0"


def test_contract_a_non_terminating_claim_is_exact_and_never_rounded():
    instrument_id, note = convertible_note("series_f_thirds", principal="10000000", price="3")
    envelope, trace = evaluate(instrument_set((instrument_id, note)), basis(),
                               scenario([selection(instrument_id, "conversion", "cashless")]))
    row = rows_by_route(trace)[instrument_id]
    assert row["incremental_shares"] == "3333333"
    assert row["fraction"] == "1/3"
    assert trace["claims"][0]["claim"] == "3333333"
    assert trace["claims"][0]["remainder"] == "1/3"
    assert component(envelope, "as_converted_claims").value == "3333333"


def test_contract_money_is_exact_to_the_last_decimal_place():
    instrument_id, warrant = make_instrument(
        "series_f_mils",
        kind="pre_funded_warrant",
        instruments_outstanding="1000001",
        shares_per_instrument="1",
        prefunded_residual_price="0.001",
    )
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "pre_funded")]))
    row = rows_by_route(trace)[instrument_id]
    assert row["gross_cash"] == "1000.001"
    assert row["net_cash"] == "970.00097"
    assert Decimal(row["net_cash"]) == Decimal(row["gross_cash"]) * (Decimal(1) - Decimal(FEE))
    assert cash_by_route(envelope)[instrument_id].net.decimal == Decimal("970.00097")


def test_contract_a_whole_share_row_records_a_zero_remainder():
    instrument_id, warrant = plain_warrant("series_f_whole")
    _envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                                scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["fraction"] == "0"


# ---------------------------------------------------------------------------
# D17 — expiry is attached but not evaluated in I1a
# ---------------------------------------------------------------------------


def test_contract_expiry_is_attached_but_not_evaluated():
    instrument_id, warrant = plain_warrant(
        "series_e_expired", expiry=economic_term(instrument_id_for(ISSUER, "series_e_expired"), "expiry",
                                                 date_value="2020-01-01")
    )
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    # I1a applies no expiry cut-off: the row computes and no Unknown names expiry.
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "1000000"
    assert unknown_ids(envelope) == []
    assert not [item for item in envelope.unknowns if "expiry" in item.unknown_id]
    assert "expiry" not in trace


# ---------------------------------------------------------------------------
# §5.10 / D15 — guards, sorting and determinism
# ---------------------------------------------------------------------------


def test_contract_structural_guards_are_always_named():
    instrument_id, warrant = plain_warrant("series_g_warrant")
    resale_set, _common_id = resale_instruments()
    cases = (
        (instrument_set((instrument_id, warrant)), basis(), scenario([])),
        (instrument_set((instrument_id, warrant)), basis(),
         scenario([selection(instrument_id, "warrant_exercise", "cash")])),
        (resale_set, basis(), scenario([])),
        (instrument_set((instrument_id, warrant)), basis(status="conflict", conflicts=("candidates disagree",)),
         scenario([selection(instrument_id, "warrant_exercise", "cash")])),
    )
    for instruments, share_basis, selected_scenario in cases:
        envelope, trace = evaluate(instruments, share_basis, selected_scenario)
        for guard in STRUCTURAL_GUARDS:
            assert guard in envelope.double_count_guards
        assert trace["guards"] == list(envelope.double_count_guards)


def test_contract_the_prefunded_guard_appears_only_with_a_prefunded_row():
    prefunded_id, prefunded = make_instrument(
        "series_g_prefunded",
        kind="pre_funded_warrant",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        prefunded_residual_price=RESIDUAL,
    )
    cash_id, cash = plain_warrant("series_g_cash")
    with_prefunded, _trace = evaluate(
        instrument_set((prefunded_id, prefunded)),
        basis(),
        scenario([selection(prefunded_id, "warrant_exercise", "pre_funded")]),
    )
    assert "prefunded_paid_economics_not_recounted" in with_prefunded.double_count_guards
    without, _trace = evaluate(instrument_set((cash_id, cash)), basis(),
                               scenario([selection(cash_id, "warrant_exercise", "cash")]))
    assert "prefunded_paid_economics_not_recounted" not in without.double_count_guards


def test_contract_guards_and_unknowns_are_deduplicated_and_sorted():
    instruments, warrant_id = capped_instruments()
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash"),
                                  selection("route:atm", "at_the_market", "cash")])
    conflicted = basis(status="conflict", conflicts=("candidates disagree",))
    envelope, trace = evaluate(instruments, conflicted, selected_scenario)
    assert len(envelope.unknowns) > 1
    assert list(envelope.double_count_guards) == sorted(set(envelope.double_count_guards))
    assert unknown_ids(envelope) == sorted(set(unknown_ids(envelope)))
    assert trace["guards"] == sorted(set(trace["guards"]))
    assert trace["unknowns"] == unknown_ids(envelope)
    for row in trace["rows"]:
        assert row["guards"] == sorted(set(row["guards"]))
        assert row["unknowns"] == sorted(set(row["unknowns"]))
        assert set(row["unknowns"]) <= set(unknown_ids(envelope))


def test_contract_trace_rows_and_cash_effects_are_sorted_by_route_id():
    pairs, actions = [], []
    for series_key in ("series_s_zulu", "series_s_alpha", "series_s_mike"):
        instrument_id, warrant = plain_warrant(series_key)
        pairs.append((instrument_id, warrant))
        actions.append(selection(instrument_id, "warrant_exercise", "cash"))
    common_id, common = make_instrument("series_s_common", kind="common", resale_registered_shares="1000")
    pairs.append((common_id, common))
    instruments = instrument_set(*pairs)
    envelope, trace = evaluate(instruments, basis(), scenario(list(reversed(actions))))
    route_ids = [row["route_id"] for row in trace["rows"]]
    assert route_ids == sorted(route_ids)
    effect_ids = [item.route_id for item in envelope.cash_effects]
    assert effect_ids == sorted(effect_ids)
    assert len(effect_ids) == len(set(effect_ids)) == 4
    assert f"resale_{common_id}" in effect_ids


def test_contract_unknowns_are_well_formed_and_match_the_identifier_rule():
    instrument_id, warrant = plain_warrant("series_w_broken", exercise_price=None)
    instruments = instrument_set((instrument_id, warrant))
    conflicted = basis(status="conflict", conflicts=("candidates disagree",))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash"),
                                  selection("route:atm", "at_the_market", "cash")])
    envelope, _trace = evaluate(instruments, conflicted, selected_scenario)
    assert len(envelope.unknowns) >= 3
    for item in envelope.unknowns:
        assert c._ID.match(item.unknown_id), item.unknown_id
        assert item.description.strip()
        assert item.resolving_fact.strip()
        assert item.affects
        assert set(item.affects) <= set(COMPONENT_NAMES) | {"cash_effects"}


def test_contract_an_amended_instrument_is_eligible():
    instrument_id, warrant = plain_warrant("series_a_amended", status="amended")
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "1000000"
    assert component(envelope, "as_converted_claims").value == "1000000"
    assert unknown_ids(envelope) == []


# ---------------------------------------------------------------------------
# §0 item 5 / L78 — the four components are never summed
# ---------------------------------------------------------------------------


def numeric_strings(value, found=None) -> list:
    """Every plain decimal string in a record or trace; digests and ids are skipped."""
    found = [] if found is None else found
    if isinstance(value, str):
        if len(value) <= 32:
            try:
                found.append(Decimal(value))
            except Exception:
                pass
    elif isinstance(value, dict):
        for item in value.values():
            numeric_strings(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            numeric_strings(item, found)
    return found


def never_summed_fixture():
    """A fixture where all four components are known and pairwise sums collide with nothing."""
    common_id, common = make_instrument("series_n_common", kind="common", resale_registered_shares="3000000")
    warrant_id, warrant = plain_warrant("series_n_warrant")
    note_id, note = convertible_note("series_n_note")
    instruments = instrument_set((common_id, common), (warrant_id, warrant), (note_id, note))
    selected_scenario = scenario([selection(warrant_id, "warrant_exercise", "cash")])
    return instruments, basis(), selected_scenario


def test_never_summed_no_envelope_field_is_the_sum_of_two_components():
    instruments, share_basis, selected_scenario = never_summed_fixture()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    values = {}
    for name in COMPONENT_NAMES:
        quantity = component(envelope, name)
        assert quantity.status == "known", name
        values[name] = Decimal(quantity.value)
    assert values == {
        "existing_outstanding": Decimal(OUTSTANDING),
        "incremental_issuance": Decimal("1000000"),
        "as_converted_claims": Decimal("5000000"),
        "resalable_existing": Decimal("3000000"),
    }
    pairwise = {
        values[first] + values[second]
        for index, first in enumerate(COMPONENT_NAMES)
        for second in COMPONENT_NAMES[index + 1:]
    }
    assert len(pairwise) == 6
    assert not (set(values.values()) & pairwise)
    for number in numeric_strings(envelope.as_record()):
        assert number not in pairwise, number
    # The trace keeps the same discipline: its rows are per-action, never a component sum.
    for row in trace["rows"]:
        for number in numeric_strings(row):
            assert number not in pairwise


def test_never_summed_the_envelope_and_trace_have_no_total_field():
    instruments, share_basis, selected_scenario = never_summed_fixture()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    record = envelope.as_record()
    assert tuple(record) == (
        "schema",
        "state_id",
        "scenario_id",
        "existing_outstanding",
        "incremental_issuance",
        "as_converted_claims",
        "resalable_existing",
        "receipt",
        "cash_effects",
        "double_count_guards",
        "unknowns",
    )
    for forbidden in ("total", "fully_diluted", "sum", "pro_forma", "combined"):
        assert forbidden not in record
        assert forbidden not in trace
        assert not [key for key in trace if forbidden in key]
    assert "fully_diluted" not in c.SHARE_BASES
    with pytest.raises(c.ContractViolation):
        c.Quantity.known("1", "shares", share_basis="fully_diluted")
    assert not [name for name in dir(supply_module) if "total" in name.lower() or "diluted" in name.lower()]


def test_never_summed_a_component_stays_unknown_while_the_others_are_known():
    instruments, share_basis, selected_scenario = never_summed_fixture()
    conflicted = basis(status="conflict", conflicts=("candidates disagree",))
    envelope, _trace = evaluate(instruments, conflicted, selected_scenario)
    assert component(envelope, "existing_outstanding").status == "unknown"
    for name in ("incremental_issuance", "as_converted_claims", "resalable_existing"):
        assert component(envelope, name).status == "known", name
    # An unknown component is never filled in from the others.
    assert component(envelope, "existing_outstanding").value is None


# ---------------------------------------------------------------------------
# D15 — determinism
# ---------------------------------------------------------------------------


def test_determinism_permuted_actions_give_identical_rows_and_components():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    actions = list(selected_scenario.actions)
    generator = random.Random(20261014)
    for _attempt in range(12):
        generator.shuffle(actions)
        permuted_scenario = scenario(actions)
        permuted, permuted_trace = evaluate(instruments, share_basis, permuted_scenario)
        assert permuted_trace["rows"] == trace["rows"]
        assert permuted_trace["claims"] == trace["claims"]
        assert permuted_trace["guards"] == trace["guards"]
        assert permuted_trace["unknowns"] == trace["unknowns"]
        assert permuted.cash_effects == envelope.cash_effects
        assert permuted.double_count_guards == envelope.double_count_guards
        assert unknown_ids(permuted) == unknown_ids(envelope)
        for name in COMPONENT_NAMES:
            assert component(permuted, name) == component(envelope, name)
        # C0 digests the action order, so identity legitimately follows it (D15).
        if permuted_scenario.scenario_id == selected_scenario.scenario_id:
            assert permuted.state_id == envelope.state_id
        else:
            assert permuted.state_id != envelope.state_id


def test_determinism_repeated_evaluation_is_byte_identical():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    first = evaluate_supply(instruments, share_basis, selected_scenario)
    second = evaluate_supply(instruments, share_basis, selected_scenario)
    assert first.as_record() == second.as_record()
    assert c.sha256_of(first.as_record()) == c.sha256_of(second.as_record())
    assert first.state_id == second.state_id
    assert first.receipt == second.receipt
    assert supply_trace(instruments, share_basis, selected_scenario) == supply_trace(
        instruments, share_basis, selected_scenario
    )


def test_determinism_shuffled_term_records_and_bindings_give_a_byte_identical_envelope():
    warrant_series, common_series, other_series = "series_d_warrants", "series_d_common", "series_d_prefunded"
    warrant_id, warrant = IE.instrument_for(warrant_series)
    common_id, common = IE.instrument_for(common_series, kind="common")
    other_id, other = IE.instrument_for(other_series, kind="pre_funded_warrant")
    base = IE.set_for((warrant_id, warrant), (common_id, common), (other_id, other))
    records, bindings = [], []

    def add(record: dict, series_key: str = warrant_series, **over) -> None:
        records.append(record)
        bindings.append(IE.binding(record["occurrence_id"], series_key=series_key, **over))

    # A price restated in June: the newer binding supersedes the older one, so the
    # older occurrence stays visible but attaches nothing (binding-level history).
    new_price = IE.term_record("exercise_price", value=STRIKE, span="span:price-new")
    old_price = IE.term_record("exercise_price", value="2.00", span="span:price-old",
                               event_time="2025-01-02T00:00:00Z")
    records.extend([new_price, old_price])
    old_binding = IE.binding(old_price["occurrence_id"], series_key=warrant_series)
    new_binding = IE.binding(new_price["occurrence_id"], series_key=warrant_series,
                             supersedes=[old_binding["binding_id"]])
    bindings.extend([old_binding, new_binding])
    add(IE.term_record("shares_per_instrument", value="1", span="span:ratio"))
    add(IE.term_record("instruments_outstanding", value="1000000", span="span:count"))
    add(IE.term_record("resale_registered_shares", value="5000000", span="span:resale"), series_key=common_series)
    add(IE.term_record("prefunded_residual_price", value=RESIDUAL, span="span:residual"), series_key=other_series)
    add(IE.term_record("instruments_outstanding", value="250000", span="span:prefunded-count"),
        series_key=other_series)
    add(IE.term_record("shares_per_instrument", value="1", span="span:prefunded-ratio"), series_key=other_series)
    # Deferred bytes on an instrument no action selects: they attach as an unknown
    # term and change no row, which is the point — an unreadable term is not a 0.
    add(IE.term_record("notice_days", status="deferred", span="span:deferred"), series_key=common_series)

    selected_scenario = scenario(
        [
            selection(warrant_id, "warrant_exercise", "cash"),
            selection(other_id, "warrant_exercise", "pre_funded"),
        ]
    )
    attached = attach_economic_terms(base, records, bindings, AS_OF)
    IE.check_instrument_set(attached)
    reference, reference_trace = evaluate(attached, basis(), selected_scenario)
    reference_record = reference.as_record()
    reference_digest = c.sha256_of(reference_record)
    assert component(reference, "incremental_issuance").value == "1250000"
    assert component(reference, "as_converted_claims").value == "1250000"
    assert component(reference, "resalable_existing").value == "5000000"
    assert unknown_ids(reference) == []
    assert rows_by_route(reference_trace)[warrant_id]["gross_cash"] == "1000000"
    assert rows_by_route(reference_trace)[other_id]["gross_cash"] == "250"
    attached_terms = {
        item.instrument_id: {term.name: term for term in item.economic_terms} for item in attached.instruments
    }
    assert attached_terms[common_id]["notice_days"].status == "unknown"
    assert attached_terms[common_id]["resale_registered_shares"].status == "admitted"
    assert attached_terms[warrant_id]["exercise_price"].value.decimal == Decimal(STRIKE)

    shuffled_records = list(records)
    shuffled_bindings = list(bindings)
    generator = random.Random(20261014)
    for _attempt in range(24):
        generator.shuffle(shuffled_records)
        generator.shuffle(shuffled_bindings)
        permuted_set = attach_economic_terms(base, shuffled_records, shuffled_bindings, AS_OF)
        assert permuted_set.as_record() == attached.as_record()
        permuted, permuted_trace = evaluate(permuted_set, basis(), selected_scenario)
        assert permuted.as_record() == reference_record
        assert c.sha256_of(permuted.as_record()) == reference_digest
        assert permuted_trace == reference_trace


# ---------------------------------------------------------------------------
# §0 item 3 — no float is accepted or produced anywhere on the I1 path
# ---------------------------------------------------------------------------


def assert_no_float(value, path: str = "<root>") -> None:
    if isinstance(value, float):
        raise AssertionError(f"{path}: a float was produced ({value!r})")
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str), f"{path}: a non-string key was produced"
            assert_no_float(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_float(item, f"{path}[{index}]")


def test_float_refusal_scenario_fee_rate():
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        scenario([], fee_rate=0.03)


def test_float_refusal_scenario_price():
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        c.PriceAssumption("fixed", "USD", fixed_price=2.5)
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        c.PriceAssumption("path", "USD", path=(("2027-01-04", 2.5),))


def test_float_refusal_scenario_selection_quantity():
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        selection("route:x", "warrant_exercise", "cash",
                  quantity=c.Quantity.known(1000000.0, "shares", share_basis="reserved_for_issuance"))
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        holder_position("instrument:cs:x", 0.0)


def test_float_refusal_record_term_value():
    instrument_id, warrant = plain_warrant("series_fl_warrant")
    instruments = instrument_set((instrument_id, warrant))
    record = IE.term_record("exercise_price", value="1.00")
    record["value"] = 1.0
    with pytest.raises(c.ContractViolation, match="decimal strings only"):
        attach_economic_terms(instruments, [record], [], AS_OF)
    term = economic_term(instrument_id, "exercise_price", "1.00")
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        dataclasses.replace(term, value=c.Quantity.known(1.0, "usd"))


def test_float_refusal_record_share_basis_value():
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        T.shares(10000000.0, "issued_and_outstanding")
    with pytest.raises(c.ContractViolation, match="decimal string required"):
        c.Quantity.known(5000000.0, "shares", share_basis="potentially_resalable_existing")


def test_contract_no_float_is_produced_anywhere_on_the_supply_path():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    envelope, trace = evaluate(instruments, share_basis, selected_scenario)
    assert_no_float(envelope.as_record(), "supply_envelope")
    assert_no_float(trace, "supply_trace")
    assert_no_float(envelope.receipt.as_record(), "receipt")
    for item in envelope.unknowns:
        assert_no_float(item.as_record(), "unknown")
    # Every number the trace states is exact text: a decimal string, num/den, or "unknown".
    for row in trace["rows"]:
        for key in ("underlying_shares", "incremental_shares", "gross_cash", "net_cash", "fraction"):
            text = row[key]
            assert text == "unknown" or text == "0" or Decimal(text) >= 0 or "/" in text, text
    assert trace["horizon_days"] == "365"


# ---------------------------------------------------------------------------
# Contracts — identity, receipt and the frozen projection
# ---------------------------------------------------------------------------


def test_contract_arity_of_evaluate_supply_is_three():
    assert list(inspect.signature(evaluate_supply).parameters) == ["instruments", "basis", "scenario"]
    assert list(inspect.signature(supply_trace).parameters) == ["instruments", "basis", "scenario"]
    assert [row[1] for row in c.INTERFACE_OWNERSHIP if row[0].endswith("supply_scenarios.py")] == ["evaluate_supply"]


def test_contract_state_id_and_receipt_follow_the_spec_pattern():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    envelope, _trace = evaluate(instruments, share_basis, selected_scenario)
    inputs = {
        "supply_inputs": {"instruments": instruments.as_record(), "basis": share_basis.as_record()},
        "scenario_id": selected_scenario.scenario_id,
    }
    assert envelope.state_id == c.stable_id("state", inputs)
    expected = c.CalculationReceipt.build(
        inputs=inputs,
        rule_digest=c.sha256_of(SETTLEMENT_RULES),
        implementation=IMPLEMENTATION,
        computed_at=selected_scenario.as_of,
        scenario_id=selected_scenario.scenario_id,
    )
    assert envelope.receipt == expected
    assert envelope.receipt.receipt_id == expected.receipt_id
    assert envelope.receipt.rule_digest == c.sha256_of(SETTLEMENT_RULES)
    assert envelope.receipt.scenario_id == envelope.scenario_id
    assert envelope.scenario_id == selected_scenario.scenario_id


def test_contract_settlement_rules_transcribe_the_spec_table():
    assert isinstance(SETTLEMENT_RULES, tuple)
    for row in SETTLEMENT_RULES:
        assert isinstance(row, tuple) and len(row) == 3
        assert all(isinstance(cell, str) and cell for cell in row)
    cases = [row[0] for row in SETTLEMENT_RULES]
    assert len(cases) == len(set(cases))
    assert set(cases) == {
        "warrant_exercise|cash",
        "warrant_exercise|cashless",
        "warrant_exercise|net_share",
        "warrant_exercise|pre_funded",
        "conversion|cashless",
        "conversion|net_share",
        "resalable_existing|fact_not_an_action",
    }
    by_case = {row[0]: row for row in SETTLEMENT_RULES}
    # L100 and A23 are stated in the rule text the receipt digests.
    assert "never counted again" in by_case["warrant_exercise|pre_funded"][2]
    assert "never issuer funding" in by_case["resalable_existing|fact_not_an_action"][2]
    assert by_case["resalable_existing|fact_not_an_action"][1].startswith("incremental shares = 0")
    assert c.sha256_of(SETTLEMENT_RULES) != c.sha256_of(SETTLEMENT_RULES[:-1])


def test_contract_the_envelope_record_is_the_frozen_c0_projection():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    envelope, _trace = evaluate(instruments, share_basis, selected_scenario)
    record = envelope.as_record()
    assert record["schema"] == c.RECORD_SCHEMAS["supply_envelope"]
    assert c.validate_state_record("supply_envelope", record) is None
    assert set(envelope.components()) == set(COMPONENT_NAMES)


def test_contract_issuer_mismatch_is_refused():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    foreign = dataclasses.replace(share_basis, issuer_id="cik:0009999999")
    with pytest.raises(c.ContractViolation, match="differs from the share basis issuer"):
        evaluate_supply(instruments, foreign, selected_scenario)
    with pytest.raises(c.ContractViolation, match="differs from the share basis issuer"):
        supply_trace(instruments, foreign, selected_scenario)


def test_contract_input_types_are_required():
    instruments, share_basis, selected_scenario, _ids = a24_instruments()
    with pytest.raises(c.ContractViolation, match="InstrumentSet is required"):
        evaluate_supply({}, share_basis, selected_scenario)
    with pytest.raises(c.ContractViolation, match="ShareBasisResult is required"):
        evaluate_supply(instruments, {}, selected_scenario)
    with pytest.raises(c.ContractViolation, match="FinancingScenario is required"):
        evaluate_supply(instruments, share_basis, {})


def test_contract_one_decrement_per_action_is_enforced_by_the_scenario_identity():
    instrument_id, warrant = plain_warrant("series_o_double")
    # C0 makes a second selection of the same route impossible, so one action can
    # never decrement one claim twice.
    with pytest.raises(c.ContractViolation, match="duplicate"):
        scenario([selection(instrument_id, "warrant_exercise", "cash"),
                  selection(instrument_id, "warrant_exercise", "cashless")])
    envelope, _trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                                scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    assert "one_decrement_per_action" in envelope.double_count_guards
    assert component(envelope, "incremental_issuance").value == "1000000"
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_contract_a_scenario_with_no_actions_has_a_known_zero_incremental():
    instruments, _common_id = resale_instruments()
    envelope, trace = evaluate(instruments, basis(), scenario([]))
    assert trace["rows"] == []
    assert component(envelope, "incremental_issuance").status == "known"
    assert component(envelope, "incremental_issuance").value == "0"


# ---------------------------------------------------------------------------
# L172 reference cases
# ---------------------------------------------------------------------------


def test_l172_primary_issuance_and_resale_are_two_different_questions():
    common_id, common = make_instrument("series_l172_common", kind="common", resale_registered_shares="3000000")
    warrant_id, warrant = plain_warrant("series_l172_warrant")
    instruments = instrument_set((common_id, common), (warrant_id, warrant))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(warrant_id, "warrant_exercise", "cash")]))
    # A primary issuance mints new shares and pays the issuer; a resale does neither.
    assert component(envelope, "incremental_issuance").value == "1000000"
    assert component(envelope, "resalable_existing").value == "3000000"
    assert component(envelope, "existing_outstanding").value == OUTSTANDING
    effects = cash_by_route(envelope)
    assert effects[warrant_id].kind == "proceeds"
    assert effects[warrant_id].gross.decimal == Decimal(1000000)
    assert effects[f"resale_{common_id}"].kind == "no_cash"
    assert effects[f"resale_{common_id}"].gross.decimal == Decimal(0)
    assert [row["route_id"] for row in trace["rows"]] == [warrant_id]


def test_l172_fixed_warrant_terms_drive_the_cash_row_exactly():
    instrument_id, warrant = plain_warrant(
        "series_l172_fixed", instruments_outstanding="250000", shares_per_instrument="4", exercise_price="0.75"
    )
    envelope, trace = evaluate(instrument_set((instrument_id, warrant)), basis(),
                               scenario([selection(instrument_id, "warrant_exercise", "cash")]))
    row = rows_by_route(trace)[instrument_id]
    assert row["underlying_shares"] == "1000000"
    assert row["incremental_shares"] == "1000000"
    assert row["gross_cash"] == "750000"
    assert row["net_cash"] == "727500"
    assert Decimal(row["gross_cash"]) == Decimal(250000) * Decimal(4) * Decimal("0.75")
    assert component(envelope, "as_converted_claims").value == "1000000"


def test_l172_pre_funded_and_cashless_warrants_never_recount_paid_economics():
    prefunded_id, prefunded = make_instrument(
        "series_l172_prefunded",
        kind="pre_funded_warrant",
        instruments_outstanding="1000000",
        shares_per_instrument="1",
        prefunded_residual_price="0.001",
        cash_exercise_permitted=True,
    )
    cashless_id, cashless = plain_warrant("series_l172_cashless", cashless_exercise_permitted=True)
    instruments = instrument_set((prefunded_id, prefunded), (cashless_id, cashless))
    selected_scenario = scenario(
        [
            selection(prefunded_id, "warrant_exercise", "pre_funded"),
            selection(cashless_id, "warrant_exercise", "cashless"),
        ]
    )
    envelope, trace = evaluate(instruments, basis(), selected_scenario)
    effects = cash_by_route(envelope)
    # The pre-funded holder already paid: only the residual is proceeds (L100).
    assert effects[prefunded_id].gross.decimal == Decimal(1000)
    assert rows_by_route(trace)[prefunded_id]["incremental_shares"] == "1000000"
    # The cashless holder pays nothing and receives only the spread in shares.
    assert effects[cashless_id].kind == "no_cash"
    assert rows_by_route(trace)[cashless_id]["incremental_shares"] == "600000"
    assert component(envelope, "incremental_issuance").value == "1600000"
    assert component(envelope, "as_converted_claims").value == "2000000"
    assert "prefunded_paid_economics_not_recounted" in envelope.double_count_guards


def test_l172_share_basis_correction_conflict_leaves_existing_unknown():
    instrument_id, warrant = plain_warrant("series_l172_basis")
    instruments = instrument_set((instrument_id, warrant))
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    for status in ("conflict", "refused", "unavailable"):
        over = {"conflicts": ("two corrected observations disagree on the count",)} if status == "conflict" else {}
        share_basis = basis(status=status, **over)
        envelope, _trace = evaluate(instruments, share_basis, selected_scenario)
        existing = component(envelope, "existing_outstanding")
        assert existing.status == "unknown", status
        assert existing.share_basis == "issued_and_outstanding"
        assert f"share_basis_{status}" in unknown_ids(envelope)
        # A correction changes the basis, never the contractual claim.
        assert component(envelope, "as_converted_claims").value == "1000000"
    # A conflict still SHOWS its candidates and selects nothing (never the largest).
    conflicted = basis(status="conflict", conflicts=("two corrected observations disagree on the count",))
    assert conflicted.selected is None
    assert len(conflicted.candidates) == 2


def test_l172_corporate_action_leaves_a_pre_split_term_stale():
    instrument_id, instruments = split_warrant(price_effective_at=PRE_SPLIT)
    selected_scenario = scenario([selection(instrument_id, "warrant_exercise", "cash")])
    envelope, trace = evaluate(instruments, split_basis(), selected_scenario)
    assert rows_by_route(trace)[instrument_id]["incremental_shares"] == "unknown"
    assert f"stale_presplit_{instrument_id}_exercise_price" in unknown_ids(envelope)
    restated_id, restated = split_warrant()
    restated_envelope, restated_trace = evaluate(restated, split_basis(),
                                                 scenario([selection(restated_id, "warrant_exercise", "cash")]))
    assert rows_by_route(restated_trace)[restated_id]["incremental_shares"] == "1000000"
    assert unknown_ids(restated_envelope) == []


def test_l172_retired_overhang_contributes_nothing():
    retired_id, retired = plain_warrant("series_l172_retired", status="retired")
    retired_common_id, retired_common = make_instrument(
        "series_l172_retired_common", kind="common", status="retired", resale_registered_shares="9000000"
    )
    instruments = instrument_set((retired_id, retired), (retired_common_id, retired_common))
    envelope, trace = evaluate(instruments, basis(), scenario([selection(retired_id, "warrant_exercise", "cash")]))
    # A retired instrument is no overhang: no claim, no resale, no shares, no cash.
    assert component(envelope, "as_converted_claims").status == "not_applicable"
    assert component(envelope, "resalable_existing").status == "not_applicable"
    assert component(envelope, "incremental_issuance").status == "unknown"
    assert rows_by_route(trace)[retired_id]["incremental_shares"] == "unknown"
    assert f"instrument_{retired_id}" in unknown_ids(envelope)
    assert envelope.cash_effects == ()
    assert trace["claims"] == []
    assert trace["resale"] == []
    # Beside a live instrument only the live one counts.
    live_id, live = plain_warrant("series_l172_live")
    mixed = instrument_set((retired_id, retired), (live_id, live), (retired_common_id, retired_common))
    mixed_envelope, mixed_trace = evaluate(mixed, basis(), scenario([selection(live_id, "warrant_exercise", "cash")]))
    assert component(mixed_envelope, "as_converted_claims").value == "1000000"
    assert component(mixed_envelope, "incremental_issuance").value == "1000000"
    assert component(mixed_envelope, "resalable_existing").status == "not_applicable"
    assert [row["route_id"] for row in mixed_trace["rows"]] == [live_id]
