"""SPEC_S0 §11: one scenario, three components, one composed answer.

Every acceptance row this lane owns is asserted with exact :class:`Decimal`
money and exact :class:`Fraction` kernel values, never approximately and never
with a float.  Fixtures are imported from the component suites that own them
(C1/C2/C2b capacity, I1/I2 supply, F1 funding) and re-used, never copied: no
new data file, no network read, and no digest is hard-coded -- every identity is
derived with :func:`stable_id` or :func:`sha256_of`.

The laws under test:

* A21 — the composed answer carries capacity's joint numbers through and never
  caps a conditional proceed to a pool bound (§0.2);
* A22 — action order and input record order change nothing but identity, a
  raised pool bound never worsens the joint check or lowers the scenario
  balance, and scaling every money input by k scales every money field by k;
* A26 — an unknown part never yields a finite total;
* A30 — coverage is scenario-only: no field and no note states or implies cash
  on hand, and every period carries the same disclosure;
* A31 — a then-known scenario runs only on then-known facts and S0 relabels
  nothing;
* A32 — an assumption change is a new identity and a new receipt with the
  evidence untouched;
* §4 — one canonical owner per cash amount, and a disagreement with F1 is a
  named blocker carrying both values rather than a silent pick;
* §7a — authorized headroom is disclosed, never assumed.
"""
from __future__ import annotations

import dataclasses
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence

import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_capacity_c2 as C2
import tests.test_capital_structure_capacity_c2b as CB
import tests.test_capital_structure_funding as F
import tests.test_capital_structure_supply_scenarios as SS
import tests.test_capital_structure_supply_variable as SV
from engine.capital_structure import capacity as capacity_module
from engine.capital_structure import issuer_state_contracts as c
from engine.capital_structure import rule_applicability as ra
from engine.capital_structure import scenario_composition as sc
from engine.capital_structure import supply_scenarios as supply_module
from engine.capital_structure.issuer_state_contracts import (
    ActionSelection,
    PriceAssumption,
    Quantity,
    SignedQuantity,
)

TAKE_A = C2.TAKE_A
TAKE_B = C2.TAKE_B
ATM_A = C2.ATM_A
BABY_POOL = C1.BABY_POOL
NASDAQ_POOL = C1.NASDAQ_POOL

#: F1's three stated bases; the horizon is one 78-day period, 2026-10-14 to
#: 2026-12-31, so the assumed burn is exactly 51,000 x 78.
FUNDING_ASSUMPTIONS = (
    ("burn_basis", "fixed_usd_per_day:51000"),
    ("working_capital_basis", "excluded"),
    ("seasonality_basis", "flat"),
)
OPENING_CASH = Decimal("5000000")
LIQUIDITY_FLOOR = Decimal("2000000")
COVENANT_AVAILABLE = "2026-10-01T00:00:00Z"
BURN_PER_DAY = Decimal("51000")
PERIOD_DAYS = Decimal(78)
ASSUMED_BURN = BURN_PER_DAY * PERIOD_DAYS
COMPUTED_CLOSING = OPENING_CASH - ASSUMED_BURN
FEE_RATE = "0.05"

#: SPEC_S0 §3: the four joint-check answers, worst first, for the A22 monotonicity
#: assertion ("never turns infeasible into something worse").
JOINT_RANK = {"infeasible": 0, "indeterminate": 1, "no_capacity_actions": 2, "feasible": 3}

FORBIDDEN_NOTE = re.compile(r"\b(?:recommend\w*|should)\b", re.IGNORECASE)
CASH_ON_HAND = "cash on hand"
NOT_CASH_ON_HAND = "not cash on hand"


# ---------------------------------------------------------------------------
# Fixtures — built from the component suites' own helpers
# ---------------------------------------------------------------------------


def explain(
    actions: Sequence[ActionSelection] = (),
    *,
    fee_rate: str | None = FEE_RATE,
    capacity_kwargs: Mapping[str, Any] | None = None,
    price: PriceAssumption | None = None,
    view: str | None = None,
    state_view_mode: str | None = None,
    cash: Decimal = OPENING_CASH,
    floor: Decimal = LIQUIDITY_FLOOR,
    burn_per_day: Decimal = BURN_PER_DAY,
    extra_facts: Sequence[Mapping[str, Any]] = (),
    instruments: Any = None,
    share_basis: Any = None,
    rules: Any = None,
    pack: Any = C1.PACK,
    reverse_records: bool = False,
    scenario_over: Mapping[str, Any] | None = None,
) -> sc.ScenarioComposition:
    """One composition: capacity + supply + funding under ONE scenario and state."""
    kwargs = dict(C2.a21_kwargs() if capacity_kwargs is None else capacity_kwargs)
    other = tuple(kwargs.pop("other", ()))
    assumptions = tuple(other) + tuple(
        (name, f"fixed_usd_per_day:{burn_per_day}" if name == "burn_basis" else value)
        for name, value in FUNDING_ASSUMPTIONS
    )
    build_kwargs: dict[str, Any] = dict(kwargs)
    if price is not None:
        build_kwargs["price"] = price
    state, scenario, built_rules = C1.build(
        other=assumptions, reverse_records=reverse_records, **build_kwargs
    )
    over: dict[str, Any] = {"actions": tuple(actions), "fee_rate": fee_rate}
    if view is not None:
        over["view"] = view
    if scenario_over:
        over.update(scenario_over)
    scenario = dataclasses.replace(scenario, **over)
    if state_view_mode is not None:
        state = dataclasses.replace(
            state, request=dataclasses.replace(state.request, view_mode=state_view_mode)
        )
    financials = F.financials(
        F.cash(str(cash), measured="2026-06-30"), *[dict(item) for item in extra_facts]
    )
    commitments = F.covenants(
        F.covenant("cov-min-1", str(floor), available_at=COVENANT_AVAILABLE)
    )
    return sc.explain_scenario(
        state,
        SS.instrument_set() if instruments is None else instruments,
        SS.basis() if share_basis is None else share_basis,
        financials,
        commitments,
        scenario,
        built_rules if rules is None else rules,
        pack=pack,
    )


def compose(**kwargs: Any) -> c.ScenarioResult:
    return explain(**kwargs).result


def money(quantity: Any) -> Decimal:
    assert quantity.status == "known" and quantity.value is not None, quantity
    return Decimal(quantity.value)


def checks_of(result: c.ScenarioResult) -> dict[str, c.ActionCheck]:
    return {item.route_id: item for item in result.action_checks}


def recon_of(result: c.ScenarioResult) -> dict[str, c.CashReconciliation]:
    return {item.route_id: item for item in result.cash_reconciliation}


def issuance_of(result: c.ScenarioResult) -> dict[str, c.IssuanceRow]:
    return {item.route_id: item for item in result.issuance_rows}


def bases_of(result: c.ScenarioResult) -> dict[str, c.PriceBasis]:
    return {item.component: item for item in result.price_bases}


def unknown_ids_of(result: c.ScenarioResult) -> list[str]:
    return [item.unknown_id for item in result.unknowns]


def cash_warrant(series_key: str = "series_s0_cash_warrants", *, exercise_price: str = "1.50",
                 count: str = "1000000"):
    """A cash-exercisable warrant: n x K is supply's canonical gross (§4 row 3)."""
    instrument_id, instrument = SS.make_instrument(
        series_key, instruments_outstanding=count, shares_per_instrument="1",
        exercise_price=exercise_price,
    )
    return SS.instrument_set((instrument_id, instrument)), instrument_id


def warrant_action(route_id: str, settlement: str, quantity: Quantity | None = None) -> ActionSelection:
    return ActionSelection(route_id, "warrant_exercise", settlement, quantity)


def branching_note(series_key: str = "series_s0_branching_note", *, conversion_price: str = "5.00"):
    """An I2 convertible note whose settlement branch the scenario elects."""
    instrument_id, instrument = SV.branching_note(
        series_key, conversion_price=conversion_price
    )
    return SS.instrument_set((instrument_id, instrument)), instrument_id


def maturity_fact(route_id: str, amount: str = "1000000", due: str = "2026-11-30") -> dict[str, Any]:
    """A debt maturity F1 books in-horizon, so a conversion can relieve it."""
    return F.obligation(route_id, "debt_maturity", amount, due)


# ---------------------------------------------------------------------------
# The ONE shared helper every test in this file calls
# ---------------------------------------------------------------------------


def string_values(value: Any, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            string_values(item, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            string_values(item, out)


#: The record fields S0 itself authored; the three component records are the
#: components' own and are never re-read as S0's numbers.
S0_OWNED_FIELDS = (
    "action_checks", "joint_check", "cash_reconciliation", "issuance_rows",
    "scenario_new_shares_low", "scenario_new_shares_high", "price_bases", "coverage",
    "authorized_headroom", "blockers", "unknowns", "notes",
)


def quantity_values(value: Any, out: list[Decimal], unit: str = "usd") -> None:
    """Every known quantity of one unit in a record, as an exact Decimal."""
    if isinstance(value, Mapping):
        if value.get("unit") == unit and value.get("status") == "known":
            out.append(Decimal(value["value"]))
        for item in value.values():
            quantity_values(item, out, unit)
    elif isinstance(value, (list, tuple)):
        for item in value:
            quantity_values(item, out, unit)


def s0_owned_money(record: Mapping[str, Any]) -> list[Decimal]:
    out: list[Decimal] = []
    for key in S0_OWNED_FIELDS:
        quantity_values(record[key], out)
    return out


def keys_of(value: Any, out: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            out.append(key)
            keys_of(item, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            keys_of(item, out)


def check(result: c.ScenarioResult) -> dict[str, Any]:
    """§0 items 5 and 6: validate, sweep, deny authority and forbid advice text."""
    record = result.as_record()
    c.validate_state_record("scenario_result", record)
    c._assert_safe_keys(record)
    keys: list[str] = []
    keys_of(record, keys)
    assert keys, "an empty record proves nothing"
    for key in keys:
        assert not c.FORBIDDEN_PROPERTY_PATTERN.match(key), key
        assert "cash_on_hand" not in key, key
    C1.walk_quantities(record)
    assert result.prophet_authority is False
    assert record["prophet_authority"] is False
    texts: list[str] = []
    string_values(record, texts)
    for text in texts:
        assert not FORBIDDEN_NOTE.search(text), text
        if CASH_ON_HAND in text.lower():
            assert NOT_CASH_ON_HAND in text.lower(), text
    for period in result.coverage:
        assert period.note.startswith(c.COVERAGE_SCENARIO_ONLY_NOTE)
    # Every component travelled inside the result carries the one identity.
    for component in (result.capacity_envelope, result.supply_envelope, result.funding_schedule):
        assert component.scenario_id == result.scenario_id
        assert component.state_id == result.state_id
        assert component.receipt.scenario_id == result.scenario_id
    assert result.receipt.scenario_id == result.scenario_id
    assert result.receipt.implementation_digest == c.sha256_of(
        {"contract": c.STATE_CONTRACT_VERSION, "implementation": sc.IMPLEMENTATION}
    )
    return record


# ---------------------------------------------------------------------------
# §0.1 — one scenario_id and one state_id, no component re-run
# ---------------------------------------------------------------------------


def test_s0_compose_runs_the_three_components_under_one_identity() -> None:
    composition = explain([C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    result = check(composition.result)
    assert result["scenario_id"] == composition.result.scenario_id
    assert result["state_id"] == composition.result.state_id
    # The three component records travel inside the result byte-identically.
    assert result["capacity_envelope"] == composition.capacity.envelope.as_record()
    assert result["funding_schedule"] == composition.funding.as_record()
    assert result["supply_envelope"]["scenario_id"] == composition.result.scenario_id
    assert result["supply_envelope"]["state_id"] == composition.result.state_id
    assert composition.supply_trace["scenario_id"] == composition.result.scenario_id
    assert composition.supply_trace["state_id"] == composition.result.state_id
    assert composition.capacity.inputs["actions_applied"], "capacity applied the requested action"
    # S0 re-stamped supply with the state identity (SPEC_I1 §5.1) and never the
    # other way round: the supply receipt still names the scenario it consumed.
    assert composition.result.supply_envelope.receipt.scenario_id == composition.result.scenario_id


# ---------------------------------------------------------------------------
# §0.2 / §11.1 — A21 carried through with requested actions
# ---------------------------------------------------------------------------


def test_s0_a21_row_one_a_six_million_request_is_within_capacity_and_feasible() -> None:
    result = compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    check(result)
    assert money(result.capacity_envelope.aggregate_bound) == Decimal("10000000.00")
    assert result.capacity_envelope.aggregate_bound.status == "known"
    assert result.joint_check.status == "feasible"
    assert result.joint_check.aggregate_status == "known"
    assert result.joint_check.binding == (BABY_POOL,)
    assert result.joint_check.blocker_ids == ()
    assert result.blockers == ()
    action = checks_of(result)[TAKE_A]
    assert (action.status, action.owner, action.fixed) == ("within_capacity", "capacity", True)
    assert action.blocker_ids == () and action.unknown_ids == ()
    # §3: S0 quotes capacity's own floor/ceiling sentence verbatim when present,
    # and this row states a determined number instead.
    assert result.joint_check.note is not None
    assert result.capacity_envelope.aggregate_bound.note in result.joint_check.note
    # §5: the new shares are a row of their own, never folded into a total.
    row = issuance_of(result)[TAKE_A]
    assert (money(row.shares_low), money(row.shares_high)) == (Decimal(3_000_000), Decimal(3_000_000))
    assert row.basis == "fixed_price" and row.unknown_id is None
    assert money(result.scenario_new_shares_low) == Decimal(3_000_000)
    # §7: covered, with the exact gross and net bases apart.
    period = result.coverage[0]
    assert period.status == "covered"
    assert money(period.gap) == Decimal("978000.00")
    assert money(period.scenario_net) == Decimal("5700000.00")
    assert money(period.scenario_balance) == COMPUTED_CLOSING + Decimal("5700000.00")
    assert money(period.shortfall) == Decimal(0)
    assert money(period.gross_basis) == Decimal("6000000")
    assert money(period.net_basis) == Decimal("5700000.00")


def test_s0_a21_share_pool_row_carries_the_six_million_bound() -> None:
    """15,000,005 shares out: the 3,000,000-share pool is $6,000,000 and binds."""
    result = compose(
        actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")],
        capacity_kwargs=C2.a21_kwargs(outstanding="15000005"),
    )
    check(result)
    assert money(result.capacity_envelope.aggregate_bound) == Decimal("6000000.00")
    assert result.joint_check.binding == (NASDAQ_POOL,)
    assert result.joint_check.status == "feasible"
    assert checks_of(result)[TAKE_A].status == "within_capacity"


def test_s0_a21_row_two_eight_plus_seven_million_is_infeasible_and_never_capped() -> None:
    """§0.2: the $15M request is infeasible, and $15M is neither reported as
    capacity nor silently capped to the $10M pool."""
    result = compose(actions=[
        C2.cash(TAKE_A, "shelf_takedown", "8000000"),
        C2.cash(TAKE_B, "shelf_takedown", "7000000"),
    ])
    check(result)
    assert result.joint_check.status == "infeasible"
    assert result.joint_check.aggregate_status == "contradicted"
    assert f"asserted_actions_infeasible:{BABY_POOL}" in result.joint_check.blocker_ids
    for route_id in (TAKE_A, TAKE_B):
        action = checks_of(result)[route_id]
        assert action.status == "infeasible" and action.owner == "capacity"
        assert f"asserted_actions_infeasible:{BABY_POOL}" in action.blocker_ids
    # The negative: no capacity number is 15,000,000 and the aggregate is not a
    # capped 10,000,000 -- a contradicted aggregate carries NO value at all.
    assert result.capacity_envelope.aggregate_bound.status == "contradicted"
    assert result.capacity_envelope.aggregate_bound.value is None
    assert money(result.capacity_envelope.routes[0].limit) + money(
        result.capacity_envelope.routes[1].limit
    ) == Decimal("15000000")
    # Nothing S0 authored is the pool bound wearing a proceed's clothes: the
    # $10M pool stays capacity's own number and is never substituted for the
    # $15M the scenario requested.
    record = result.as_record()
    assert Decimal("10000000") not in s0_owned_money(record)
    assert Decimal("15000000") not in s0_owned_money(record)
    assert money(recon_of(result)[TAKE_A].canonical_gross) == Decimal("8000000")
    assert money(recon_of(result)[TAKE_B].canonical_gross) == Decimal("7000000")
    assert money(recon_of(result)[TAKE_A].funding_amount) == Decimal("8000000")
    assert money(recon_of(result)[TAKE_B].funding_amount) == Decimal("7000000")
    # F1's conditional proceeds stay exactly what was requested: 8M and 7M.
    flows = {
        flow.flow_id: flow
        for period in result.funding_schedule.periods
        for flow in (*period.sources, *period.uses)
    }
    assert money(flows[f"source:{TAKE_A}:gross"].amount) == Decimal("8000000")
    assert money(flows[f"source:{TAKE_B}:gross"].amount) == Decimal("7000000")
    assert (
        money(flows[f"source:{TAKE_A}:gross"].amount) + money(flows[f"source:{TAKE_B}:gross"].amount)
        == Decimal("15000000")
    )
    assert all(flow.certainty == "conditional" for flow in flows.values()
               if flow.flow_id.startswith("source:"))
    # §7: coverage is not evaluated, with a blocker reference and no numbers.
    period = result.coverage[0]
    assert period.status == "not_evaluated"
    assert period.gap.status == "unknown" and period.shortfall.status == "unknown"
    assert period.scenario_balance.status == "unknown"
    assert f"asserted_actions_infeasible:{BABY_POOL}" in period.note
    # The reconciliation still reports both requested amounts as F1 booked them.
    assert money(recon_of(result)[TAKE_A].canonical_gross) == Decimal("8000000")
    assert money(recon_of(result)[TAKE_A].funding_amount) == Decimal("8000000")
    assert money(recon_of(result)[TAKE_B].canonical_net) == Decimal("6650000.00")


def test_s0_a21_row_three_unknown_outstanding_leaves_the_joint_indeterminate() -> None:
    """No share count: capacity states a floor and a ceiling and no number."""
    result = compose(
        actions=[C2.cash(TAKE_A, "shelf_takedown", "8000000")],
        capacity_kwargs=C2.a21_kwargs(outstanding=None),
    )
    check(result)
    assert result.capacity_envelope.aggregate_bound.status == "unknown"
    assert result.capacity_envelope.aggregate_bound.value is None
    assert result.joint_check.status == "indeterminate"
    assert result.joint_check.aggregate_status == "unknown"
    # §3: capacity's own sentence is quoted verbatim, and S0 reports no witness.
    assert "floor 8000000.00 / ceiling 10000000.00 under stated unknowns" in result.joint_check.note
    assert result.capacity_envelope.aggregate_bound.note in result.joint_check.note
    assert checks_of(result)[TAKE_A].status == "within_capacity"
    assert result.coverage[0].status == "indeterminate"
    assert result.coverage[0].shortfall.status == "unknown"
    # The requested proceed is still exact on both sides.
    assert money(recon_of(result)[TAKE_A].canonical_gross) == Decimal("8000000")
    assert money(recon_of(result)[TAKE_A].funding_amount) == Decimal("8000000")


# ---------------------------------------------------------------------------
# §2 / §11.2 — view pairing (A31)
# ---------------------------------------------------------------------------


def test_s0_then_known_scenario_on_a_current_state_is_refused() -> None:
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")], state_view_mode="current")
    assert str(excinfo.value) == "view_mismatch:then_known_scenario_on_current_state"


def test_s0_then_known_scenario_on_a_scenario_state_is_refused() -> None:
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")], state_view_mode="scenario")
    assert str(excinfo.value) == "view_mismatch:then_known_scenario_on_scenario_state"


def test_s0_counterfactual_on_a_then_known_state_records_both_labels() -> None:
    result = compose(
        actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")], view="counterfactual"
    )
    check(result)
    assert result.scenario_view == "counterfactual"
    assert result.state_view_mode == "then_known"
    assert result.scenario_view != result.state_view_mode
    # S0 relabels nothing: the scenario the components consumed is the same one.
    assert result.capacity_envelope.scenario_id == result.scenario_id


def test_s0_a_scenario_dated_off_the_state_cutoff_is_refused() -> None:
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(
            actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")],
            scenario_over={"as_of": "2026-10-13T00:00:00Z"},
        )
    assert str(excinfo.value).startswith("as_of_mismatch:")


# ---------------------------------------------------------------------------
# §2 / §11.3 — one identity, and a mismatch is named per component
# ---------------------------------------------------------------------------


def _tamper_scenario_id(record: Any, value: str) -> Any:
    copy = dataclasses.replace(record)
    object.__setattr__(copy, "scenario_id", value)
    return copy


def test_s0_scenario_identity_mismatch_capacity_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    real = capacity_module.explain_capacity

    def tampered(*args: Any, **kwargs: Any) -> Any:
        evaluation = real(*args, **kwargs)
        envelope = _tamper_scenario_id(evaluation.envelope, "scenario:cs:" + "f" * 32)
        return dataclasses.replace(evaluation, envelope=envelope)

    monkeypatch.setattr(capacity_module, "explain_capacity", tampered)
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    assert str(excinfo.value) == "scenario_identity_mismatch:capacity"


def test_s0_scenario_identity_mismatch_supply_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    real = supply_module.evaluate_supply

    def tampered(*args: Any, **kwargs: Any) -> Any:
        return _tamper_scenario_id(real(*args, **kwargs), "scenario:cs:" + "e" * 32)

    monkeypatch.setattr(supply_module, "evaluate_supply", tampered)
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    assert str(excinfo.value) == "scenario_identity_mismatch:supply"


def test_s0_scenario_identity_mismatch_supply_trace_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = supply_module.supply_trace

    def tampered(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {**real(*args, **kwargs), "scenario_id": "scenario:cs:" + "d" * 32}

    monkeypatch.setattr(supply_module, "supply_trace", tampered)
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    assert str(excinfo.value) == "scenario_identity_mismatch:supply"


def test_s0_scenario_identity_mismatch_funding_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    real = capacity_module.bind_funding_schedule

    def tampered(state: Any, schedule: Any) -> Any:
        bound = real(state, schedule)
        copy = dataclasses.replace(bound)
        object.__setattr__(copy, "state_id", "state:cs:" + "c" * 32)
        return copy

    monkeypatch.setattr(capacity_module, "bind_funding_schedule", tampered)
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    assert str(excinfo.value) == "scenario_identity_mismatch:funding"


def test_s0_a_component_input_error_is_wrapped_by_type_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = capacity_module.explain_capacity

    def refused(*args: Any, **kwargs: Any) -> Any:
        raise capacity_module.CapacityInputError("action on 'nope' has no route")

    monkeypatch.setattr(capacity_module, "explain_capacity", refused)
    with pytest.raises(sc.ScenarioCompositionError) as excinfo:
        compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    assert str(excinfo.value) == "action on 'nope' has no route"
    assert isinstance(excinfo.value.__cause__, capacity_module.CapacityInputError)
    assert real is not refused


# ---------------------------------------------------------------------------
# §3 / §11 — the action-check table and the joint check, read from C2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route_id,action,settlement,value,expected_status,expected_owner",
    [
        (CB.WARRANT_ROUTE, "warrant_exercise", "cash", "1500000", "not_a_capacity_route", "supply"),
        (CB.CONVERSION_ROUTE, "conversion", "cashless", None, "not_a_capacity_route", "supply"),
        (CB.EXCHANGE_ROUTE, "exchange", "cash", "500000", "not_a_capacity_route", "supply"),
        (CB.REDEMPTION_ROUTE, "redemption", "cash", "600000", "not_a_capacity_route", "supply"),
        (CB.REPURCHASE_ROUTE, "repurchase", "cash", "400000", "not_a_capacity_route", "supply"),
        (CB.DEBT_ROUTE, "debt_draw", "cash", "500000", "not_a_capacity_route", "funding_only"),
        (CB.OTHER_ROUTE, "other", "cash", "250000", "not_a_capacity_route", "funding_only"),
        (CB.EQUITY_LINE_ROUTE, "equity_line", "cash", None, "not_modelled", "capacity_unmodelled"),
        (CB.DIRECT_ROUTE, "registered_direct", "cash", "1000000", "not_modelled", "capacity_unmodelled"),
        (CB.PIPE_ROUTE, "pipe", "cash", "3000000", "not_modelled", "capacity_unmodelled"),
    ],
)
def test_s0_the_action_check_table_reads_the_owner_from_capacity(
    route_id: str, action: str, settlement: str, value: str | None,
    expected_status: str, expected_owner: str,
) -> None:
    """§3: S0 never re-derives an owner; it reads capacity's own partition."""
    result = compose(actions=[CB.action(route_id, action, settlement, value)])
    check(result)
    entry = checks_of(result)[route_id]
    assert (entry.status, entry.owner) == (expected_status, expected_owner)
    assert entry.action == action and entry.settlement == settlement
    assert entry.fixed is (value is not None)
    assert entry.blocker_ids == ()
    if expected_status == "not_modelled" and entry.fixed:
        # C2b's own unknown id, carried verbatim: capacity owns the Unknown and
        # S0 references it rather than minting a second one.
        assert entry.unknown_ids == (f"action_route_not_modelled:{route_id}",)
        assert f"action_route_not_modelled:{route_id}" in {
            item.unknown_id for item in result.capacity_envelope.unknowns
        }
    else:
        assert entry.unknown_ids == ()


def test_s0_a_recorded_only_capacity_action_is_not_applied() -> None:
    result = compose(actions=[ActionSelection(TAKE_A, "shelf_takedown", "cash")])
    check(result)
    entry = checks_of(result)[TAKE_A]
    assert (entry.status, entry.owner, entry.fixed) == ("not_applied", "capacity", False)
    assert result.joint_check.status == "no_capacity_actions"
    # An unpriced action is unknown, never zero (§5, A26).
    row = issuance_of(result)[TAKE_A]
    assert row.shares_low.status == "unknown" and row.shares_low.value is None
    assert row.unknown_id == f"scenario_shares_unpriced:{TAKE_A}"
    assert result.scenario_new_shares_low.status == "unknown"
    assert recon_of(result)[TAKE_A].status == "funding_unpriced"


def test_s0_an_action_on_an_ineligible_route_is_named() -> None:
    registration, shares = C1.standard_registration(withdrawn="observed")
    result = compose(
        actions=[C2.cash(TAKE_A, "shelf_takedown", "1000000")],
        capacity_kwargs={"registration": registration, "share_basis": shares},
    )
    check(result)
    entry = checks_of(result)[TAKE_A]
    assert entry.status == "ineligible_route" and entry.owner == "capacity"
    assert entry.blocker_ids == (f"asserted_action_on_ineligible_route:{TAKE_A}",)
    assert result.joint_check.status == "infeasible"
    assert f"asserted_action_on_ineligible_route:{TAKE_A}" in result.joint_check.blocker_ids


def test_s0_a_price_branch_infeasibility_leaves_the_joint_indeterminate() -> None:
    """§3: only a single-branch blocker is `infeasible_on_price_branch`."""
    result = compose(
        actions=[C2.shares(ATM_A, "at_the_market", "800000")],
        capacity_kwargs=C2.path_kwargs(path=C2.PRICE_PATH, programme=C2.ATM_PROGRAMME),
    )
    check(result)
    entry = checks_of(result)[ATM_A]
    assert entry.status == "infeasible_on_price_branch"
    assert entry.blocker_ids == (f"asserted_actions_infeasible_on_price_branch:optimistic:{ATM_A}",)
    assert result.joint_check.status == "indeterminate"
    assert result.joint_check.aggregate_status == "unknown"


def test_s0_the_joint_check_reports_no_witness_of_its_own() -> None:
    """§3: capacity's witness stays reachable only through the envelope."""
    result = compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    record = check(result)
    assert set(record["joint_check"]) == {
        "status", "aggregate_status", "binding", "blocker_ids", "note",
    }
    assert result.capacity_envelope.feasible_witness, "capacity's own witness is still there"
    assert result.joint_check.binding == result.capacity_envelope.binding_constraints
    assert result.joint_check.blocker_ids == tuple(sorted(result.capacity_envelope.blockers))


def test_s0_a_fixed_unmodelled_action_leaves_the_joint_indeterminate() -> None:
    result = compose(actions=[CB.action(CB.PIPE_ROUTE, "pipe", "cash", "3000000")])
    check(result)
    assert checks_of(result)[CB.PIPE_ROUTE].status == "not_modelled"
    assert result.joint_check.status == "indeterminate"
    assert result.joint_check.aggregate_status == "unknown"
    assert result.coverage[0].status == "indeterminate"


def test_s0_one_scenario_carries_capacity_and_instrument_actions_together() -> None:
    """The SPEC_C2B precondition §3 depends on: no refusal, each recorded once."""
    instruments, warrant_id = cash_warrant()
    result = compose(
        actions=[
            C2.cash(TAKE_A, "shelf_takedown", "6000000"),
            warrant_action(
                warrant_id, "cash",
                Quantity.known("1000000", "shares", share_basis="scenario_incremental_issuance"),
            ),
        ],
        instruments=instruments,
    )
    check(result)
    entries = checks_of(result)
    assert sorted(entries) == sorted([TAKE_A, warrant_id])
    assert entries[TAKE_A].status == "within_capacity"
    assert entries[warrant_id].status == "not_a_capacity_route"
    assert entries[warrant_id].owner == "supply"
    assert result.joint_check.status == "feasible"


# ---------------------------------------------------------------------------
# §4 / §11.4 — one canonical owner per cash amount, one test per table row
# ---------------------------------------------------------------------------


def test_s0_reconciles_a_fixed_usd_capacity_action_with_funding() -> None:
    """§4 row 1: gross is the asserted usd, net is gross x (1 - fee_rate)."""
    result = compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")])
    check(result)
    row = recon_of(result)[TAKE_A]
    assert (row.owner, row.status, row.conflict_id) == ("capacity", "agree", None)
    assert money(row.canonical_gross) == Decimal("6000000")
    assert money(row.canonical_net) == Decimal("6000000") * (1 - Decimal(FEE_RATE))
    assert money(row.canonical_net) == Decimal("5700000.00")
    assert money(row.funding_amount) == Decimal("6000000")
    assert result.blockers == ()


def test_s0_a_capacity_action_without_a_fee_rate_leaves_net_unknown() -> None:
    result = compose(actions=[C2.cash(TAKE_A, "shelf_takedown", "6000000")], fee_rate=None)
    check(result)
    row = recon_of(result)[TAKE_A]
    assert row.status == "agree"
    assert money(row.canonical_gross) == Decimal("6000000")
    assert row.canonical_net.status == "unknown" and row.canonical_net.value is None
    assert money(row.funding_amount) == Decimal("6000000")


def test_s0_reconciles_a_fixed_share_action_at_a_fixed_price() -> None:
    """§4 row 2: a share quantity at one price is one canonical amount."""
    result = compose(actions=[C2.shares(TAKE_A, "shelf_takedown", "1000000")])
    check(result)
    row = recon_of(result)[TAKE_A]
    assert row.status == "agree"
    assert money(row.canonical_gross) == Decimal("2000000")
    assert money(row.canonical_net) == Decimal("1900000.00")
    assert money(row.funding_amount) == Decimal("2000000.00")


def test_s0_a_path_priced_share_action_is_funding_unpriced() -> None:
    """§4: canonical known, F1 unknown -- F1 needs a fixed usd price."""
    result = compose(
        actions=[C2.shares(TAKE_A, "shelf_takedown", "1000000")],
        price=PriceAssumption(kind="path", path=C2.PRICE_PATH),
        capacity_kwargs=C2.a21_kwargs(),
    )
    check(result)
    row = recon_of(result)[TAKE_A]
    assert row.status == "funding_unpriced" and row.conflict_id is None
    assert money(row.canonical_gross) == Decimal("2000000")
    assert row.funding_amount.status == "unknown" and row.funding_amount.value is None
    assert f"scenario_cash_unpriced:{TAKE_A}" in unknown_ids_of(result)
    # S0 substituted nothing into F1's schedule: F1 still books the flow with no
    # amount and still names its own unknown.
    flows = {
        flow.flow_id: flow
        for period in result.funding_schedule.periods
        for flow in (*period.sources, *period.uses)
    }
    assert flows[f"source:{TAKE_A}:gross"].amount.status == "unknown"
    assert flows[f"source:{TAKE_A}:gross"].amount.value is None
    assert f"unknown:action_amount:{TAKE_A}" in {
        item.unknown_id for item in result.funding_schedule.unknowns
    }
    assert result.coverage[0].status == "indeterminate"


def test_s0_a_branched_share_action_has_a_range_and_picks_neither_end() -> None:
    result = compose(
        actions=[C2.shares(ATM_A, "at_the_market", "800000")],
        capacity_kwargs=C2.path_kwargs(path=C2.PRICE_PATH, programme=C2.ATM_PROGRAMME),
    )
    check(result)
    row = recon_of(result)[ATM_A]
    assert row.status == "funding_unpriced"
    assert row.canonical_gross.status == "unknown" and row.canonical_gross.value is None
    assert "pessimistic 1600000 usd" in row.canonical_gross.note
    assert "optimistic 2400000 usd" in row.canonical_gross.note
    assert f"scenario_cash_unpriced:{ATM_A}" in unknown_ids_of(result)


def test_s0_a_cash_warrant_disagrees_with_funding_and_names_both_values() -> None:
    """§4 row 3 and §0.3: I1 says n x K, F1 booked shares x the scenario price."""
    instruments, warrant_id = cash_warrant(exercise_price="1.50")
    result = compose(
        actions=[warrant_action(
            warrant_id, "cash",
            Quantity.known("1000000", "shares", share_basis="scenario_incremental_issuance"),
        )],
        instruments=instruments,
    )
    check(result)
    row = recon_of(result)[warrant_id]
    assert (row.owner, row.status) == ("supply", "disagree")
    assert money(row.canonical_gross) == Decimal("1500000")
    assert money(row.canonical_net) == Decimal("1425000")
    assert money(row.funding_amount) == Decimal("2000000.00")
    assert row.conflict_id == f"cash_effect_disagreement:{warrant_id}"
    assert row.conflict_id in result.blockers
    # S0 never substituted the canonical value into F1's schedule.
    flows = {
        flow.flow_id: flow
        for period in result.funding_schedule.periods
        for flow in (*period.sources, *period.uses)
    }
    assert money(flows[f"source:{warrant_id}:gross"].amount) == Decimal("2000000.00")


def test_s0_a_cashless_warrant_moves_no_cash_on_either_side() -> None:
    """§4 row 4: no cash, so the reconciliation is not applicable."""
    instrument_id, instrument = SS.make_instrument(
        "series_s0_cashless_warrants", instruments_outstanding="1000000",
        shares_per_instrument="1", exercise_price="1.50", cashless_exercise_permitted=True,
    )
    instruments = SS.instrument_set((instrument_id, instrument))
    result = compose(
        actions=[warrant_action(
            instrument_id, "cashless",
            Quantity.known("1000000", "shares", share_basis="scenario_incremental_issuance"),
        )],
        instruments=instruments,
    )
    check(result)
    row = recon_of(result)[instrument_id]
    assert row.status == "not_applicable" and row.conflict_id is None
    assert row.canonical_gross.status == "not_applicable"
    assert row.canonical_net.status == "not_applicable"
    assert row.funding_amount.status == "not_applicable"
    assert result.blockers == ()
    # n x (P - K) / P = 1,000,000 x (2.00 - 1.50) / 2.00, exactly.
    shares = money(issuance_of(result)[instrument_id].shares_low)
    assert shares == Decimal(250_000)
    assert Fraction(shares) == (
        Fraction(1_000_000)
        * (Fraction(Decimal("2.00")) - Fraction(Decimal("1.50")))
        / Fraction(Decimal("2.00"))
    )


def test_s0_a_pre_funded_warrant_pays_the_residual_exercise_price() -> None:
    """§4 row 5: n x R is supply's, and F1 books no cash for it."""
    instrument_id, instrument = SS.make_instrument(
        "series_s0_prefunded_warrants", kind="pre_funded_warrant",
        instruments_outstanding="1000000", shares_per_instrument="1",
        prefunded_residual_price="0.001",
    )
    instruments = SS.instrument_set((instrument_id, instrument))
    result = compose(
        actions=[warrant_action(instrument_id, "pre_funded")], instruments=instruments
    )
    check(result)
    row = recon_of(result)[instrument_id]
    assert money(row.canonical_gross) == Decimal("1000000") * Decimal("0.001")
    assert money(row.canonical_gross) == Decimal("1000")
    assert money(row.canonical_net) == Decimal("950")
    assert row.funding_amount.status == "not_applicable"
    assert row.status == "funding_unpriced"
    assert f"scenario_cash_unpriced:{instrument_id}" in unknown_ids_of(result)
    assert money(issuance_of(result)[instrument_id].shares_low) == Decimal(1_000_000)


def test_s0_a_physical_conversion_relief_is_not_a_cash_amount() -> None:
    """§4 row 6: no cash, and relieving the converted debt is valid."""
    instruments, note_id = branching_note(conversion_price="5.00")
    result = compose(
        actions=[ActionSelection(note_id, "conversion", "physical")],
        instruments=instruments,
        extra_facts=(maturity_fact(note_id),),
    )
    check(result)
    row = recon_of(result)[note_id]
    assert row.status == "not_applicable" and row.conflict_id is None
    assert row.canonical_gross.status == "not_applicable"
    assert result.blockers == ()
    # 1,000,000 principal at a 5.00 conversion price: exactly 200,000 shares.
    assert money(issuance_of(result)[note_id].shares_low) == Decimal(200_000)
    assert money(issuance_of(result)[note_id].shares_high) == Decimal(200_000)
    # The maturity F1 flipped to conditional is excluded from its own closing and
    # is never added back by S0.
    relieved = [
        flow
        for period in result.funding_schedule.periods
        for flow in (*period.sources, *period.uses)
        if flow.flow_id == f"use:{note_id}"
    ]
    assert len(relieved) == 1
    assert relieved[0].certainty == "conditional"
    assert relieved[0].condition.startswith("relieved under scenario")
    assert money(result.coverage[0].scenario_net) == Decimal(0)


def test_s0_a_cash_settled_conversion_conflicts_with_funding_relief() -> None:
    """§4 row 7 and §0.3: a cash use against a relief is a named conflict."""
    instruments, note_id = branching_note(conversion_price="5.00")
    result = compose(
        actions=[ActionSelection(note_id, "conversion", "cash")],
        instruments=instruments,
        extra_facts=(maturity_fact(note_id),),
    )
    check(result)
    row = recon_of(result)[note_id]
    assert row.status == "conflict"
    assert row.conflict_id == f"conversion_cash_settlement_vs_relief:{note_id}"
    assert row.conflict_id in result.blockers
    assert money(row.canonical_gross) == Decimal("400000")
    assert money(row.funding_amount) == Decimal("1000000")
    assert money(issuance_of(result)[note_id].shares_low) == Decimal(0)


def test_s0_a_repurchase_is_a_cash_use_owned_by_funding() -> None:
    """§4 row 8: F1 is canonical and the I-trace has no row of its own."""
    result = compose(actions=[CB.action(CB.REPURCHASE_ROUTE, "repurchase", "cash", "400000")])
    check(result)
    row = recon_of(result)[CB.REPURCHASE_ROUTE]
    assert row.status == "agree" and row.conflict_id is None
    assert money(row.canonical_gross) == Decimal("400000")
    assert money(row.funding_amount) == Decimal("400000")
    flows = {
        flow.flow_id: flow
        for period in result.funding_schedule.periods
        for flow in (*period.sources, *period.uses)
    }
    assert f"use:{CB.REPURCHASE_ROUTE}:repurchase" in flows
    # §7: an outflow is subtracted from the scenario's own net, so the balance
    # falls below the floor by exactly the floor less (computed closing - 400,000).
    assert money(result.coverage[0].scenario_net) == Decimal("-400000.00")
    assert money(result.coverage[0].scenario_balance) == COMPUTED_CLOSING - Decimal("400000.00")
    assert result.coverage[0].status == "shortfall"
    assert money(result.coverage[0].shortfall) == LIQUIDITY_FLOOR - (
        COMPUTED_CLOSING - Decimal("400000.00")
    )
    assert money(result.coverage[0].shortfall) == Decimal("1378000.00")


def test_s0_a_redemption_is_a_cash_use_owned_by_funding() -> None:
    result = compose(actions=[CB.action(CB.REDEMPTION_ROUTE, "redemption", "cash", "600000")])
    check(result)
    row = recon_of(result)[CB.REDEMPTION_ROUTE]
    assert row.status == "agree" and row.owner == "supply"
    assert money(row.canonical_gross) == Decimal("600000")
    assert money(row.funding_amount) == Decimal("600000")
    assert money(result.coverage[0].scenario_net) == Decimal("-600000.00")


def test_s0_an_other_action_stays_unknown_on_both_sides() -> None:
    """§4 row 9: F1's own `unknown:action_amount` is carried, never resolved."""
    result = compose(actions=[CB.action(CB.OTHER_ROUTE, "other", "cash", "250000")])
    check(result)
    row = recon_of(result)[CB.OTHER_ROUTE]
    assert row.status == "funding_unpriced"
    assert row.canonical_gross.status == "unknown" and row.canonical_gross.value is None
    assert row.funding_amount.status == "not_applicable"
    assert f"scenario_cash_unpriced:{CB.OTHER_ROUTE}" in unknown_ids_of(result)
    assert f"unknown:action_amount:{CB.OTHER_ROUTE}" in {
        item.unknown_id for item in result.funding_schedule.unknowns
    }


def test_s0_a_debt_draw_is_funding_only_and_agrees_with_itself() -> None:
    result = compose(actions=[CB.action(CB.DEBT_ROUTE, "debt_draw", "cash", "500000")])
    check(result)
    row = recon_of(result)[CB.DEBT_ROUTE]
    assert (row.owner, row.status) == ("funding_only", "agree")
    assert money(row.canonical_gross) == Decimal("500000")
    assert money(row.funding_amount) == Decimal("500000")
    # §7: the net side is the gross less the scenario fee, 500,000 - 25,000.
    assert money(result.coverage[0].scenario_net) == Decimal("475000.00")
    assert money(result.coverage[0].gross_basis) == Decimal("500000")
