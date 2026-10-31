"""SPEC_C2 §4-§5 — the joint-capacity fixtures and acceptance cases for the C2 adapter.

Every number here is exact: money is compared as ``Decimal``, kernel values as
``Fraction``.  Nothing is compared approximately and nothing is compared as
formatted text.  There is no float literal in this file.  Helpers come from
``tests.test_capital_structure_capacity`` (the C1 file) and are never copied.

Case map: §4.1 A21 -> ``test_a21_*``; §4.2 price paths -> ``test_path_*``;
§4.3 programme usage -> ``test_usage_*``; §5.2 A20 -> ``test_a20_*``; §5.3 A22 ->
``test_a22_*``; §5.4 L258 concurrency -> ``test_l258_<letter>_*``.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from fractions import Fraction
from typing import Any, Sequence

import pytest

import tests.test_capital_structure_capacity as C1
from engine.capital_structure import capacity as c2
from engine.capital_structure import capacity_joint
from engine.capital_structure.capacity import CapacityInputError, explain_capacity
from engine.capital_structure.capacity_joint import JointPool, JointRoute, solve_joint
from engine.capital_structure.issuer_state_contracts import (
    ActionSelection,
    PriceAssumption,
    Quantity,
    _record,
    sha256_of,
    validate_state_record,
)
from tests.test_capital_structure_capacity import (
    ACC_A,
    ACC_B,
    BABY_POOL,
    NASDAQ_ASSUMPTIONS,
    NASDAQ_POOL,
    PATH_A,
    PATH_B,
    SALE,
    build,
    pools_by_id,
    routes_by_id,
    standard_registration,
    strip_identity,
    unknown_ids,
    usd,
)

TAKE_A = f"shelf_takedown:{PATH_A}"
TAKE_B = f"shelf_takedown:{PATH_B}"
ATM_A = f"at_the_market:{PATH_A}"
REGISTERED_A = f"registered:{PATH_A}"
REGISTERED_B = f"registered:{PATH_B}"
SCHEDULE_A = f"price_path_sale_schedule:{ATM_A}"
USAGE_A = f"programme_usage:{PATH_A}"
RESERVATION_A = f"programme_reservation:{PATH_A}"

#: §4.2: a $2.00 price in effect at the horizon start, $3.00 inside the window.
PRICE_PATH = (("2026-10-14", "2.00"), ("2026-11-14", "3.00"))
HORIZON_END = "2026-12-31"

#: §4.2: a 2,000,000 reservation whose programme has sold nothing yet.
ATM_PROGRAMME = (usd(RESERVATION_A, "2000000"), usd(USAGE_A, "0"))

#: §4.3: the c10_02 basis (R 20,000,000, U 3,000,000, C 1,000,000, S 2,000,000).
C10_02 = (
    usd(f"shelf_usage:{PATH_A}", "3000000"),
    usd(f"continuing_offering:{PATH_A}", "1000000"),
    usd(RESERVATION_A, "2000000"),
)


# ---------------------------------------------------------------------------
# The one shared receipt / contract helper every test in this file calls
# ---------------------------------------------------------------------------


def check(evaluation: Any) -> None:
    """§0 item 5: validate, walk for forbidden keys and re-derive the input digest."""
    envelope = evaluation.envelope
    record = envelope.as_record()
    validate_state_record("capacity_envelope", record)
    C1.walk_forbidden_keys(record)
    C1.walk_forbidden_keys(evaluation.inputs)
    C1.walk_quantities(record)
    C1.walk_quantities(evaluation.inputs)
    assert sha256_of(_record(evaluation.inputs)) == envelope.receipt.input_digest


def evaluate(**kwargs: Any):
    """``C1.evaluate`` plus the shared helper, so every envelope is checked twice."""
    evaluation, state, scenario = C1.evaluate(**kwargs)
    check(evaluation)
    return evaluation, state, scenario


def evaluate_with_actions(actions: Sequence[ActionSelection], **kwargs: Any):
    """``evaluate`` with asserted actions, mirroring its checks exactly (§5)."""
    state, scenario, rules = build(**kwargs)
    scenario = dataclasses.replace(scenario, actions=tuple(actions))
    evaluation = explain_capacity(state, scenario, rules, pack=C1.PACK)
    check(evaluation)
    return evaluation, state, scenario


def explain_with_actions(actions: Sequence[ActionSelection], **kwargs: Any):
    """The raw call behind ``evaluate_with_actions``, for the input-error cases."""
    state, scenario, rules = build(**kwargs)
    scenario = dataclasses.replace(scenario, actions=tuple(actions))
    return explain_capacity(state, scenario, rules, pack=C1.PACK)


def cash(route_id: str, action: str, value: str) -> ActionSelection:
    return ActionSelection(route_id, action, "cash", Quantity.known(value, "usd"))


def shares(route_id: str, action: str, value: str) -> ActionSelection:
    return ActionSelection(
        route_id,
        action,
        "cash",
        Quantity.known(value, "shares", share_basis="scenario_incremental_issuance"),
    )


def money(quantity: Quantity) -> Decimal:
    assert quantity.status == "known" and quantity.value is not None, quantity
    return Decimal(quantity.value)


def witness_of(evaluation: Any) -> dict[str, Decimal]:
    return {
        item.route_id: Decimal(item.quantity.value)
        for item in evaluation.envelope.feasible_witness or ()
    }


def exclusivity(*groups: str) -> tuple[tuple[str, str], ...]:
    return tuple(NASDAQ_ASSUMPTIONS) + (("route_exclusivity", ";".join(groups)),)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def a21_kwargs(
    *,
    outstanding: str | None = "30000005",
    float_value: str = "30000000",
    registered_a: str = "8000000",
    registered_b: str = "7000000",
    sold: str = "0",
    other: Sequence[tuple[str, str]] = (),
) -> dict[str, Any]:
    """§4.1: PATH_A 8,000,000 with a 30,000,000 float, PATH_B 7,000,000, both at $2."""
    reg_a, shares_records = standard_registration(
        path_id=PATH_A,
        accession=ACC_A,
        registered=registered_a,
        float_value=float_value,
        outstanding=outstanding,
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B,
        accession=ACC_B,
        registered=registered_b,
        float_value=None,
        outstanding=None,
    )
    return {
        "registration": reg_a + reg_b,
        "share_basis": shares_records,
        "other": tuple(NASDAQ_ASSUMPTIONS) + tuple(other),
        "resolutions": [
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", sold),
        ],
    }


def path_kwargs(
    *,
    path: Sequence[tuple[str, str]] = PRICE_PATH,
    programme: Sequence[Any] = (),
    registered: str = "20000000",
    float_value: str = "300000000",
    horizon_end: str = HORIZON_END,
    other: Sequence[tuple[str, str]] = NASDAQ_ASSUMPTIONS,
) -> dict[str, Any]:
    """§4.2: one path, a 300,000,000 float (no baby shelf) and 15,000,005 shares out."""
    reg, shares_records = standard_registration(registered=registered, float_value=float_value)
    return {
        "registration": reg,
        "share_basis": shares_records,
        "other": tuple(other),
        "price": PriceAssumption(kind="path", path=tuple(path)),
        "horizon_end": horizon_end,
        "resolutions": [
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            *programme,
        ],
    }


def usage_kwargs(resolutions: Sequence[Any], *, registered: str = "20000000") -> dict[str, Any]:
    """§4.3: the c10_02 basis with a 300,000,000 float and no Nasdaq assumptions."""
    reg, shares_records = standard_registration(registered=registered, float_value="300000000")
    return {
        "registration": reg,
        "share_basis": shares_records,
        "resolutions": list(resolutions),
    }


# ---------------------------------------------------------------------------
# §4.1 / §5.1 — A21: the worked joint example, and maxima that are never added
# ---------------------------------------------------------------------------


def test_a21_row_slack_binds_the_baby_shelf_pool() -> None:
    """30,000,005 shares out: the 20% pool is $12M and slack, the one-third pool binds."""
    evaluation, _, _ = evaluate(**a21_kwargs(outstanding="30000005"))
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    assert money(envelope.aggregate_bound) == Decimal("10000000")
    assert envelope.aggregate_bound.status == "known"
    # 1/3 x 30,000,000 = 10,000,000 of headroom, shared by both takedowns.
    assert money(pools[BABY_POOL].bound) == Decimal("10000000.00")
    # 20% of 30,000,005 is 6,000,001 shares, so 6,000,000 below it: $12M at $2, slack.
    assert pools[NASDAQ_POOL].bound.unit == "shares"
    assert Fraction(pools[NASDAQ_POOL].bound.value) == Fraction(6_000_000)
    assert envelope.binding_constraints == (BABY_POOL,)
    assert pools[BABY_POOL].status == "binding"
    assert pools[NASDAQ_POOL].status == "slack"
    assert envelope.unknown_constraints == ()
    assert witness_of(evaluation) == {TAKE_A: Decimal("8000000.00"), TAKE_B: Decimal("2000000.00")}
    assert evaluation.kernel["evidence"]["value"] == "10000000/1"
    assert evaluation.inputs["branches"] == []
    assert evaluation.inputs["price"]["branching"] is False


def test_a21_row_nasdaq_binding_binds_the_share_pool() -> None:
    """15,000,005 shares out: only 3,000,000 shares ($6M) may be sold, and A takes it all."""
    evaluation, _, _ = evaluate(**a21_kwargs(outstanding="15000005"))
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    assert money(envelope.aggregate_bound) == Decimal("6000000")
    assert Fraction(pools[NASDAQ_POOL].bound.value) == Fraction(3_000_000)
    assert envelope.binding_constraints == (NASDAQ_POOL,)
    assert pools[NASDAQ_POOL].status == "binding"
    assert pools[BABY_POOL].status == "slack"
    assert witness_of(evaluation) == {TAKE_A: Decimal("6000000.00"), TAKE_B: Decimal("0.00")}
    assert evaluation.kernel["evidence"]["value"] == "6000000/1"


def test_a21_row_unknown_outstanding_leaves_the_aggregate_unknown() -> None:
    """No share count: the 20% pool is unknown, so no number is claimed -- only a ceiling."""
    evaluation, _, _ = evaluate(**a21_kwargs(outstanding=None))
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert pools[NASDAQ_POOL].bound.status == "unknown"
    assert pools[NASDAQ_POOL].bound.value is None
    assert NASDAQ_POOL in envelope.unknown_constraints
    assert envelope.binding_constraints == ()
    assert envelope.aggregate_bound.note == "floor 0.00 / ceiling 10000000.00 under stated unknowns"
    assert f"shares_outstanding:{SALE}" in unknown_ids(evaluation)
    # The witness is the kernel's floor witness: feasible for every value of the unknown.
    assert witness_of(evaluation) == {TAKE_A: Decimal("0.00"), TAKE_B: Decimal("0.00")}
    assert evaluation.kernel["evidence"]["determined"] is False
    assert evaluation.kernel["evidence"]["ceiling_when_unknowns_relaxed"] == "10000000/1"


def test_a21_maxima_never_added() -> None:
    """A21: 8,000,000 + 7,000,000 is not the answer; the shared pool is."""
    evaluation, _, _ = evaluate(**a21_kwargs(outstanding="30000005"))
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    route_sum = money(routes[TAKE_A].limit) + money(routes[TAKE_B].limit)
    assert route_sum == Decimal("15000000")
    assert money(envelope.aggregate_bound) == Decimal("10000000")
    assert money(envelope.aggregate_bound) < route_sum
    total = sum(witness_of(evaluation).values())
    assert total == money(envelope.aggregate_bound)
    assert money(pools_by_id(evaluation)[BABY_POOL].bound) == Decimal("10000000.00")


# ---------------------------------------------------------------------------
# §4.2 — price paths: the price in effect, the ATM window and an uncovered path
# ---------------------------------------------------------------------------


def test_path_takedown_only_prices_at_the_horizon_start() -> None:
    """A takedown is a sale already scheduled at the horizon start, so it is priced at $2.00."""
    evaluation, _, _ = evaluate(**path_kwargs(path=PRICE_PATH))
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    price = evaluation.inputs["price"]
    assert price["kind"] == "path" and price["p_start"] == "2/1"
    assert price["low"] == "2/1" and price["high"] == "3/1"
    assert price["window_dates"] == ["2026-10-14", "2026-11-14"]
    assert price["branching"] is False
    assert evaluation.inputs["branches"] == []
    # The 20% threshold is in shares and does not depend on price.
    assert pools[NASDAQ_POOL].bound.unit == "shares"
    assert Fraction(pools[NASDAQ_POOL].bound.value) == Fraction(3_000_000)
    assert evaluation.inputs["nasdaq"]["coefficient"] == "1/2"
    assert "price_path_branching_deferred_to_c2" not in envelope.blockers
    assert money(envelope.aggregate_bound) == Decimal("6000000")
    assert envelope.aggregate_bound.status == "known"
    assert envelope.binding_constraints == (NASDAQ_POOL,)
    assert witness_of(evaluation) == {TAKE_A: Decimal("6000000.00")}
    assert "optimistic" not in evaluation.kernel


def test_path_atm_branching_floors_and_ceilings_the_window() -> None:
    """$2.00 pessimistic against $3.00 optimistic: 6,000,000.00 to 6,666,666.66."""
    evaluation, _, _ = evaluate(**path_kwargs(path=PRICE_PATH, programme=ATM_PROGRAMME))
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    assert evaluation.inputs["price"]["branching"] is True
    assert evaluation.inputs["branches"] == ["price_path"]
    assert money(routes[TAKE_A].limit) == Decimal("18000000")
    assert money(routes[ATM_A].limit) == Decimal("2000000")
    assert evaluation.inputs["nasdaq"]["route_coefficients"] == [
        [ATM_A, "pessimistic", "1/2"],
        [ATM_A, "optimistic", "1/3"],
    ]
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == (
        "floor 6000000.00 / ceiling 6666666.66 under stated unknowns"
    )
    assert SCHEDULE_A in unknown_ids(evaluation)
    # The pessimistic branch: x + y <= 6,000,000 with y <= 2,000,000.
    assert evaluation.kernel["evidence"]["value"] == "6000000/1"
    # The optimistic branch: x/2 + y/3 <= 3,000,000 with y <= 2,000,000 -> 20,000,000/3.
    assert evaluation.kernel["optimistic"]["value"] == "20000000/3"
    assert evaluation.kernel["ceiling"]["value"] == "20000000/3"
    assert Fraction("20000000/3") == Fraction(20_000_000, 3)
    assert c2.decimal_floor(Fraction(20_000_000, 3)) == Decimal("6666666.66")
    # The witness is the pessimistic one: the at-the-market route fills first by
    # the kernel's lexicographic tie-break, then the takedown takes the rest.
    assert witness_of(evaluation) == {ATM_A: Decimal("2000000.00"), TAKE_A: Decimal("4000000.00")}


def test_path_point_before_horizon_does_not_branch() -> None:
    """One point before the horizon start and none in the window: low == high, no branch."""
    evaluation, _, _ = evaluate(
        **path_kwargs(path=(("2026-10-13", "2.00"),), programme=ATM_PROGRAMME)
    )
    envelope = evaluation.envelope
    price = evaluation.inputs["price"]
    assert price["p_start"] == "2/1" and price["low"] == "2/1" and price["high"] == "2/1"
    assert price["window_dates"] == ["2026-10-13"]
    assert price["branching"] is False
    assert evaluation.inputs["branches"] == []
    assert "optimistic" not in evaluation.kernel
    assert money(envelope.aggregate_bound) == Decimal("6000000")
    assert envelope.aggregate_bound.status == "known"
    assert SCHEDULE_A not in unknown_ids(evaluation)


def test_path_starts_after_horizon_is_uncovered() -> None:
    """A path with no point on or before the horizon start prices nothing: unknown."""
    evaluation, _, _ = evaluate(**path_kwargs(path=(("2026-10-20", "2.00"),)))
    envelope = evaluation.envelope
    pools = pools_by_id(evaluation)
    price = evaluation.inputs["price"]
    assert price["uncovered"] is True
    assert price["p_start"] is None and price["low"] is None and price["high"] is None
    assert price["window_dates"] == []
    assert price["branching"] is False
    assert f"price_path_uncovered:{SALE}" in unknown_ids(evaluation)
    assert evaluation.inputs["nasdaq"]["reason"] == "price_path_uncovered"
    assert pools[NASDAQ_POOL].bound.status == "unknown"
    assert pools[NASDAQ_POOL].bound.value is None
    assert pools[NASDAQ_POOL].bound.unit == "shares"
    assert NASDAQ_POOL in envelope.unknown_constraints
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None


# ---------------------------------------------------------------------------
# §4.3 / §5.5 — programme usage closes the C1 A15 gap
# ---------------------------------------------------------------------------


def test_usage_zero_leaves_the_c1_numbers_unchanged() -> None:
    """P = 0 reproduces the c10_02 fixture exactly: pool 16M, takedown 14M, ATM 2M."""
    evaluation, _, _ = evaluate(**usage_kwargs([*C10_02, usd(USAGE_A, "0")]))
    envelope = evaluation.envelope
    pools, routes = pools_by_id(evaluation), routes_by_id(evaluation)
    assert money(pools[REGISTERED_A].bound) == Decimal("16000000")
    assert money(routes[TAKE_A].limit) == Decimal("14000000")
    assert money(routes[ATM_A].limit) == Decimal("2000000")
    assert money(envelope.aggregate_bound) == Decimal("16000000")
    assert envelope.aggregate_bound.status == "known"
    assert evaluation.inputs["programme_usage"][PATH_A] == {
        "status": "known",
        "value": "0",
        "pessimistic": "0",
        "optimistic": "0",
    }
    assert USAGE_A not in unknown_ids(evaluation)


def test_usage_500k_is_deducted_once() -> None:
    """A15: P comes off the pool and the ATM limit, never off the takedown a second time."""
    zero, _, _ = evaluate(**usage_kwargs([*C10_02, usd(USAGE_A, "0")]))
    evaluation, _, _ = evaluate(**usage_kwargs([*C10_02, usd(USAGE_A, "500000")]))
    envelope = evaluation.envelope
    pools, routes = pools_by_id(evaluation), routes_by_id(evaluation)
    assert money(routes[ATM_A].limit) == Decimal("1500000")
    assert money(pools[REGISTERED_A].bound) == Decimal("15500000")
    assert money(routes[TAKE_A].limit) == Decimal("14000000")
    # The takedown limit is invariant to P: that is exactly A15.
    assert routes[TAKE_A].limit.value == routes_by_id(zero)[TAKE_A].limit.value
    assert money(envelope.aggregate_bound) == Decimal("15500000")
    assert envelope.aggregate_bound.status == "known"
    # 20,000,000 - 3,000,000 - 1,000,000 - 500,000, deducted exactly once.
    assert money(pools[REGISTERED_A].bound) == Decimal("20000000") - Decimal("3000000") - Decimal(
        "1000000"
    ) - Decimal("500000")


def test_usage_exceeds_reservation_contradicts_the_atm_limit() -> None:
    """P > S is a contradiction, never a negative limit and never zero."""
    evaluation, _, _ = evaluate(**usage_kwargs([*C10_02, usd(USAGE_A, "2500000")]))
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    assert f"programme_usage_exceeds_reservation:{PATH_A}" in envelope.blockers
    assert routes[ATM_A].limit.status == "contradicted"
    assert routes[ATM_A].limit.value is None
    # The takedown is untouched and the pool carries the sale that already happened.
    assert money(routes[TAKE_A].limit) == Decimal("14000000")
    assert money(pools_by_id(evaluation)[REGISTERED_A].bound) == Decimal("13500000")
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None


def test_usage_exceeds_reservation_with_a_fixed_action_contradicts() -> None:
    """§2.7: committing against an oversold programme is a contradiction, not a capacity."""
    resolutions = [*C10_02, usd(USAGE_A, "2500000")]
    plain, _, _ = evaluate(**usage_kwargs(resolutions))
    assert plain.envelope.aggregate_bound.status == "unknown"
    evaluation, _, _ = evaluate_with_actions(
        [cash(ATM_A, "at_the_market", "1000000")], **usage_kwargs(resolutions)
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "contradicted"
    assert envelope.aggregate_bound.value is None
    assert f"programme_usage_exceeds_reservation:{PATH_A}" in envelope.blockers
    # Recorded only (no quantity) commits nothing, so it stays unknown.
    recorded, _, _ = evaluate_with_actions(
        [ActionSelection(ATM_A, "at_the_market", "cash")], **usage_kwargs(resolutions)
    )
    assert recorded.envelope.aggregate_bound.status == "unknown"
    assert recorded.envelope.aggregate_bound.note == plain.envelope.aggregate_bound.note


def test_usage_unresolved_is_never_zero() -> None:
    """An unevidenced programme sale is an unknown with a P=S floor and a P=0 ceiling."""
    evaluation, _, _ = evaluate(**usage_kwargs(C10_02))
    envelope = evaluation.envelope
    pools, routes = pools_by_id(evaluation), routes_by_id(evaluation)
    assert USAGE_A in unknown_ids(evaluation)
    assert routes[ATM_A].limit.status == "unknown" and routes[ATM_A].limit.value is None
    assert pools[REGISTERED_A].bound.status == "unknown"
    assert pools[REGISTERED_A].bound.value is None
    assert REGISTERED_A in envelope.unknown_constraints
    # The takedown limit (R-U-C-S) never carries P, resolved or not.
    assert money(routes[TAKE_A].limit) == Decimal("14000000")
    assert evaluation.inputs["programme_usage"][PATH_A] == {
        "status": "unresolved",
        "value": None,
        "pessimistic": "2000000",
        "optimistic": "0",
    }
    assert evaluation.inputs["branches"] == [f"programme_usage:{PATH_A}"]
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.note == (
        "floor 14000000.00 / ceiling 16000000.00 under stated unknowns"
    )
    remaining = evaluation.inputs["remaining_capacity"]
    assert dict(remaining["pessimistic"]["routes"])[ATM_A] == "0/1"
    assert dict(remaining["optimistic"]["routes"])[ATM_A] == "2000000/1"
    assert dict(remaining["pessimistic"]["pools"])[REGISTERED_A] == "14000000/1"
    assert dict(remaining["optimistic"]["pools"])[REGISTERED_A] == "16000000/1"
    assert SCHEDULE_A not in unknown_ids(evaluation)


def test_usage_reservation_unknown_deducts_from_pool_and_takedown() -> None:
    """No reservation evaluated: a resolved P comes off the pool AND the takedown."""
    evaluation, _, _ = evaluate(
        **usage_kwargs(
            [
                usd(f"shelf_usage:{PATH_A}", "3000000"),
                usd(f"continuing_offering:{PATH_A}", "1000000"),
                usd(USAGE_A, "500000"),
            ]
        )
    )
    pools, routes = pools_by_id(evaluation), routes_by_id(evaluation)
    assert ATM_A not in routes
    assert RESERVATION_A in unknown_ids(evaluation)
    assert money(pools[REGISTERED_A].bound) == Decimal("15500000")
    assert money(routes[TAKE_A].limit) == Decimal("15500000")
    assert money(routes[TAKE_A].limit) == money(pools[REGISTERED_A].bound)
    assert evaluation.inputs["branches"] == []


# ---------------------------------------------------------------------------
# §5.2 — A20: units, price basis, the window interval, and unknowns
# ---------------------------------------------------------------------------


def test_a20_unit_mismatch_share_action_needs_a_price_in_effect() -> None:
    """A share quantity on a takedown with no price at the horizon start is refused."""
    kwargs = path_kwargs(path=(("2026-10-20", "2.00"),))
    with pytest.raises(CapacityInputError):
        explain_with_actions([shares(TAKE_A, "shelf_takedown", "1000000")], **kwargs)
    # The same fixture without a share quantity is not refused: it is unknown.
    evaluation, _, _ = evaluate(**kwargs)
    assert evaluation.envelope.aggregate_bound.status == "unknown"


def test_a20_price_basis_two_and_two_point_zero_agree() -> None:
    """`"2"` and `"2.00"` are the same price: identical economics, different digest."""
    plain = PriceAssumption(kind="fixed", fixed_price="2")
    scaled = PriceAssumption(kind="fixed", fixed_price="2.00")
    left, _, left_scenario = evaluate(**a21_kwargs(outstanding="15000005"), price=plain)
    right, _, right_scenario = evaluate(**a21_kwargs(outstanding="15000005"), price=scaled)
    assert left_scenario.scenario_id != right_scenario.scenario_id
    assert money(left.envelope.aggregate_bound) == money(right.envelope.aggregate_bound)
    assert money(left.envelope.aggregate_bound) == Decimal("6000000")
    assert left.envelope.binding_constraints == right.envelope.binding_constraints == (NASDAQ_POOL,)
    assert witness_of(left) == witness_of(right)
    left_routes, right_routes = routes_by_id(left), routes_by_id(right)
    assert {key: left_routes[key].limit.value for key in left_routes} == {
        key: right_routes[key].limit.value for key in right_routes
    }
    left_pools, right_pools = pools_by_id(left), pools_by_id(right)
    assert {key: left_pools[key].bound.value for key in left_pools} == {
        key: right_pools[key].bound.value for key in right_pools
    }
    assert left.kernel["evidence"]["value"] == right.kernel["evidence"]["value"] == "6000000/1"


def test_a20_interval_never_reads_beyond_the_horizon_end() -> None:
    """A point after ``he`` changes nothing; a point exactly at ``he`` is read."""
    base, _, _ = evaluate(**path_kwargs(path=PRICE_PATH, programme=ATM_PROGRAMME))
    beyond, _, _ = evaluate(
        **path_kwargs(path=(*PRICE_PATH, ("2027-06-01", "9.00")), programme=ATM_PROGRAMME)
    )
    assert beyond.inputs["price"]["window_dates"] == ["2026-10-14", "2026-11-14"]
    assert beyond.inputs["price"]["high"] == "3/1"
    assert beyond.envelope.aggregate_bound.note == base.envelope.aggregate_bound.note
    assert beyond.kernel == base.kernel
    assert witness_of(beyond) == witness_of(base)
    at_end, _, _ = evaluate(
        **path_kwargs(path=(*PRICE_PATH, (HORIZON_END, "5.00")), programme=ATM_PROGRAMME)
    )
    assert at_end.inputs["price"]["window_dates"] == ["2026-10-14", "2026-11-14", HORIZON_END]
    assert at_end.inputs["price"]["high"] == "5/1"
    assert at_end.inputs["price"]["low"] == "2/1"
    # x/2 + y/5 <= 3,000,000 with y <= 2,000,000 -> 7,200,000.
    assert at_end.kernel["optimistic"]["value"] == "7200000/1"
    assert at_end.envelope.aggregate_bound.note == (
        "floor 6000000.00 / ceiling 7200000.00 under stated unknowns"
    )


def test_a20_unknown_never_zero_or_infinity() -> None:
    """Every unresolved input is a named Unknown; nothing unknown reads as 0 or as unlimited."""
    reg_a, shares_records = standard_registration(
        path_id=PATH_A,
        accession=ACC_A,
        registered="8000000",
        float_value="30000000",
        outstanding=None,
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="7000000", float_value=None, outstanding=None
    )
    evaluation, _, _ = evaluate(
        registration=reg_a + reg_b,
        share_basis=shares_records,
        other=NASDAQ_ASSUMPTIONS,
        resolutions=[usd(f"baby_shelf_sold_trailing:{SALE}", "0")],
    )
    envelope = evaluation.envelope
    names = unknown_ids(evaluation)
    for unknown_id in (
        f"shelf_usage:{PATH_A}",
        f"shelf_usage:{PATH_B}",
        f"continuing_offering:{PATH_A}",
        f"continuing_offering:{PATH_B}",
        RESERVATION_A,
        f"programme_reservation:{PATH_B}",
        f"shares_outstanding:{SALE}",
    ):
        assert unknown_id in names
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    for route in envelope.routes:
        assert route.limit.status == "unknown" and route.limit.value is None
    pools = pools_by_id(evaluation)
    # The one-third pool IS decided (a measured float and a resolved sold figure),
    # so it is known; every pool that is not known carries no value at all.
    assert money(pools[BABY_POOL].bound) == Decimal("10000000.00")
    for pool in envelope.shared_pools:
        if pool.bound.status != "known":
            assert pool.bound.value is None
            assert pool.constraint_id in envelope.unknown_constraints
    assert pools[NASDAQ_POOL].bound.status == "unknown"
    assert pools[REGISTERED_A].bound.status == "unknown"
    assert pools[REGISTERED_B].bound.status == "unknown"
    # A20: an unknown is never infinity either -- the ceiling stays a finite number.
    assert envelope.aggregate_bound.note == "floor 0.00 / ceiling 10000000.00 under stated unknowns"
    assert evaluation.kernel["evidence"]["ceiling_when_unknowns_relaxed"] == "10000000/1"
    assert evaluation.kernel["evidence"]["floor_when_unknowns_zero"] == "0/1"
    for record in (envelope.as_record(), evaluation.inputs):
        C1.walk_quantities(record)


# ---------------------------------------------------------------------------
# §5.3 — A22: monotonicity, row order, unit rescaling and exclusive groups
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tightening,expected",
    [
        ({"outstanding": "15000005"}, Decimal("6000000")),
        ({"float_value": "15000000"}, Decimal("5000000")),
        ({"sold": "4000000"}, Decimal("6000000")),
        ({"registered_a": "2000000"}, Decimal("9000000")),
        ({"registered_b": "1000000"}, Decimal("9000000")),
    ],
)
def test_a22_monotone_tightening_never_raises_the_aggregate(
    tightening: dict[str, Any], expected: Decimal
) -> None:
    base, _, _ = evaluate(**a21_kwargs())
    tight, _, _ = evaluate(**a21_kwargs(**tightening))
    base_value = money(base.envelope.aggregate_bound)
    tight_value = money(tight.envelope.aggregate_bound)
    assert base_value == Decimal("10000000")
    assert tight_value == expected
    assert tight_value <= base_value
    assert sum(witness_of(tight).values()) <= tight_value


def test_a22_row_order_reversal_is_identity_stripped() -> None:
    """Reversing the state's record order changes only the state's own identity."""
    forward, _, _ = evaluate(**a21_kwargs())
    reversed_evaluation, _, _ = evaluate(**a21_kwargs(), reverse_records=True)
    assert strip_identity(reversed_evaluation.envelope.as_record()) == strip_identity(
        forward.envelope.as_record()
    )
    # The receipt digests the state's own identity, which is what record order
    # changes; strip_identity removes exactly that, and nothing else moves.
    assert reversed_evaluation.envelope.state_id != forward.envelope.state_id
    assert reversed_evaluation.envelope.receipt.input_digest != (
        forward.envelope.receipt.input_digest
    )
    assert reversed_evaluation.inputs["remaining_capacity"] == forward.inputs["remaining_capacity"]
    assert reversed_evaluation.inputs["actions_applied"] == forward.inputs["actions_applied"]
    assert witness_of(reversed_evaluation) == witness_of(forward)
    assert reversed_evaluation.kernel == forward.kernel


@pytest.mark.parametrize("scale", [Fraction(1, 1000), Fraction(7), Fraction(10**6)])
def test_a22_unit_rescaling_leaves_the_kernel_answer_unchanged(scale: Fraction) -> None:
    """Scaling one pool's coefficients and its bound by k changes neither value nor witness."""
    routes = [JointRoute(TAKE_A, Fraction(8_000_000)), JointRoute(TAKE_B, Fraction(7_000_000))]
    plain = JointPool(BABY_POOL, ((TAKE_A, Fraction(1)), (TAKE_B, Fraction(1))), Fraction(10_000_000))
    scaled = JointPool(BABY_POOL, ((TAKE_A, scale), (TAKE_B, scale)), scale * Fraction(10_000_000))
    left = solve_joint(routes, [plain])
    right = solve_joint(routes, [scaled])
    assert left.determined and right.determined
    assert left.value == right.value == Fraction(10_000_000)
    assert left.witness == right.witness
    assert dict(left.witness) == {TAKE_A: Fraction(8_000_000), TAKE_B: Fraction(2_000_000)}
    assert left.binding == right.binding == (BABY_POOL,)
    assert left.slack == right.slack == ()


def test_a22_exclusive_group_never_raises_the_aggregate() -> None:
    """Declaring A|B can only remove feasible combinations, never add capacity."""
    open_evaluation, _, _ = evaluate(**a21_kwargs())
    closed, _, _ = evaluate(**a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)))
    assert money(open_evaluation.envelope.aggregate_bound) == Decimal("10000000")
    assert money(closed.envelope.aggregate_bound) == Decimal("8000000")
    assert money(closed.envelope.aggregate_bound) <= money(open_evaluation.envelope.aggregate_bound)
    assert closed.envelope.mutually_exclusive == ((TAKE_A, TAKE_B),)


def test_exclusive_group_drops_an_ineligible_member_and_is_not_passed_on() -> None:
    """§2.4: an ineligible member is dropped and recorded; a singleton is never passed on."""
    reg_a, shares_records = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="8000000", float_value="30000000"
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B,
        accession=ACC_B,
        registered="7000000",
        float_value=None,
        outstanding=None,
        withdrawn="observed",
    )
    evaluation, _, _ = evaluate(
        registration=reg_a + reg_b,
        share_basis=shares_records,
        other=exclusivity(f"{TAKE_A}|{TAKE_B}"),
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "0"),
        ],
    )
    envelope = evaluation.envelope
    record = evaluation.inputs["exclusive_groups"]
    assert record["declared"] == [[TAKE_A, TAKE_B]]
    assert record["dropped"] == [TAKE_B]
    assert record["groups"] == []
    assert record["recorded_not_passed"] == [[TAKE_A, TAKE_B]]
    # A singleton is not a group: nothing is passed to the kernel or the envelope.
    assert envelope.mutually_exclusive == ()
    assert evaluation.kernel["evidence"]["branches_evaluated"] == 1
    assert routes_by_id(evaluation)[TAKE_B].status == "ineligible"


@pytest.mark.parametrize("bad", ["nope:route", "duplicated", "two-groups"])
def test_exclusive_group_input_errors(bad: str) -> None:
    value = {
        "nope:route": f"{TAKE_A}|shelf_takedown:ghost",
        "duplicated": f"{TAKE_A}|{TAKE_A}",
        "two-groups": f"{TAKE_A}|{TAKE_B};{TAKE_B}|{TAKE_A}",
    }[bad]
    with pytest.raises(CapacityInputError):
        evaluate(**a21_kwargs(other=(("route_exclusivity", value),)))


# ---------------------------------------------------------------------------
# §5.4 — L258 concurrency: exclusivity and asserted actions at once
# ---------------------------------------------------------------------------


def test_l258_a_exclusive_takedowns_choose_one() -> None:
    """A|B: at most one positive witness member, and the aggregate is the best single route."""
    evaluation, _, _ = evaluate(**a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)))
    envelope = evaluation.envelope
    witness = witness_of(evaluation)
    positive = [route_id for route_id, value in witness.items() if value > 0]
    assert len(positive) <= 1
    assert positive == [TAKE_A]
    assert witness == {TAKE_A: Decimal("8000000.00"), TAKE_B: Decimal("0.00")}
    # The aggregate is the maximum of the two single-route optima, never their sum.
    alone_a, _, _ = evaluate(**a21_kwargs(registered_b="0"))
    alone_b, _, _ = evaluate(**a21_kwargs(registered_a="0"))
    assert money(alone_a.envelope.aggregate_bound) == Decimal("8000000")
    assert money(alone_b.envelope.aggregate_bound) == Decimal("7000000")
    assert money(envelope.aggregate_bound) == max(
        money(alone_a.envelope.aggregate_bound), money(alone_b.envelope.aggregate_bound)
    )
    assert envelope.mutually_exclusive == ((TAKE_A, TAKE_B),)
    assert evaluation.kernel["evidence"]["allowed_exclusive"] == [TAKE_A]


def test_l258_b_fixed_action_is_a_use_not_a_cap() -> None:
    """A committed 3,000,000 inside a 6,000,000 optimum leaves the aggregate at 6,000,000."""
    action = cash(TAKE_A, "shelf_takedown", "3000000")
    evaluation, _, _ = evaluate_with_actions([action], **path_kwargs(path=PRICE_PATH))
    envelope = evaluation.envelope
    routes = routes_by_id(evaluation)
    open_evaluation, _, _ = evaluate(**path_kwargs(path=PRICE_PATH))
    assert money(envelope.aggregate_bound) == Decimal("6000000")
    assert money(envelope.aggregate_bound) == money(open_evaluation.envelope.aggregate_bound)
    # A committed use is not a cap: the route still reports its FULL limit.
    assert money(routes[TAKE_A].limit) == Decimal("20000000")
    assert routes[TAKE_A].limit.value == routes_by_id(open_evaluation)[TAKE_A].limit.value
    assert witness_of(evaluation)[TAKE_A] >= Decimal("3000000")
    assert witness_of(evaluation)[TAKE_A] == Decimal("6000000.00")
    remaining = evaluation.inputs["remaining_capacity"]["pessimistic"]
    assert dict(remaining["routes"])[TAKE_A] == "17000000/1"
    assert dict(remaining["pools"])[NASDAQ_POOL] == "1500000/1"
    assert dict(remaining["pools"])[REGISTERED_A] == "17000000/1"
    assert remaining["fixed_total"] == "3000000"
    assert evaluation.inputs["actions_applied"] == [
        {
            "route_id": TAKE_A,
            "action": "shelf_takedown",
            "settlement": "cash",
            "fixed": True,
            "applied": True,
            "usd_pessimistic": "3000000",
            "usd_optimistic": "3000000",
            "conditions_assumed_met": [],
        }
    ]
    assert "actions_recorded_not_applied" not in evaluation.inputs
    assert envelope.binding_constraints == (NASDAQ_POOL,)


def test_l258_c_fixed_action_over_the_residual_contradicts() -> None:
    """7,000,000 of shares at $2.00 is 3,500,000 shares: above the 3,000,000 threshold."""
    evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "7000000")], **path_kwargs(path=PRICE_PATH)
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "contradicted"
    assert envelope.aggregate_bound.value is None
    assert f"asserted_actions_infeasible:{NASDAQ_POOL}" in envelope.blockers
    # The negative residual is reported, never solved and never clamped into a claim.
    remaining = evaluation.inputs["remaining_capacity"]["pessimistic"]
    assert Fraction(dict(remaining["pools"])[NASDAQ_POOL]) == Fraction(-500_000)
    assert money(routes_by_id(evaluation)[TAKE_A].limit) == Decimal("20000000")


def test_l258_d_fixed_atm_share_action_branches() -> None:
    """800,000 shares are $1,600,000 at $2.00 and $2,400,000 at $3.00: infeasible only there."""
    evaluation, _, _ = evaluate_with_actions(
        [shares(ATM_A, "at_the_market", "800000")],
        **path_kwargs(path=PRICE_PATH, programme=ATM_PROGRAMME),
    )
    envelope = evaluation.envelope
    applied = evaluation.inputs["actions_applied"]
    assert applied[0]["route_id"] == ATM_A and applied[0]["fixed"] is True
    assert Decimal(applied[0]["usd_pessimistic"]) == Decimal("1600000")
    assert Decimal(applied[0]["usd_optimistic"]) == Decimal("2400000")
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert f"asserted_actions_infeasible_on_price_branch:optimistic:{ATM_A}" in envelope.blockers
    assert f"asserted_actions_infeasible:{ATM_A}" not in envelope.blockers
    assert SCHEDULE_A in unknown_ids(evaluation)
    remaining = evaluation.inputs["remaining_capacity"]
    assert Fraction(dict(remaining["pessimistic"]["routes"])[ATM_A]) == Fraction(400_000)
    assert Fraction(dict(remaining["optimistic"]["routes"])[ATM_A]) == Fraction(-400_000)
    # Both branches spend the same 800,000 SHARES of the 20% threshold.
    assert dict(remaining["pessimistic"]["pools"])[NASDAQ_POOL] == "2200000/1"
    assert dict(remaining["optimistic"]["pools"])[NASDAQ_POOL] == "2200000/1"
    assert Fraction(dict(remaining["pessimistic"]["pools"])[REGISTERED_A]) == Fraction(18_400_000)
    assert Fraction(dict(remaining["optimistic"]["pools"])[REGISTERED_A]) == Fraction(17_600_000)
    # No allocation honouring 800,000 shares fits the optimistic branch, so no witness.
    assert witness_of(evaluation) == {}


def test_review_fixed_takedown_over_the_route_limit_is_contradicted_without_a_witness() -> None:
    """25,000,000 committed against a 20,000,000 registration fails in every branch."""
    evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "25000000")], **path_kwargs(path=PRICE_PATH)
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "contradicted"
    assert envelope.aggregate_bound.value is None
    assert f"asserted_actions_infeasible:{TAKE_A}" in envelope.blockers
    assert f"asserted_actions_infeasible:{REGISTERED_A}" in envelope.blockers
    assert f"asserted_actions_infeasible:{NASDAQ_POOL}" in envelope.blockers
    assert witness_of(evaluation) == {}


def test_review_two_fixed_takedowns_over_the_shared_pool_are_contradicted() -> None:
    """A21: committing 8,000,000 + 7,000,000 is infeasible, never capped to 10,000,000."""
    evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "8000000"), cash(TAKE_B, "shelf_takedown", "7000000")],
        **a21_kwargs(outstanding="30000005"),
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "contradicted"
    assert envelope.aggregate_bound.value is None
    assert f"asserted_actions_infeasible:{BABY_POOL}" in envelope.blockers
    assert f"asserted_actions_infeasible:{NASDAQ_POOL}" in envelope.blockers
    assert witness_of(evaluation) == {}


def test_review_unknown_atm_limit_with_agreeing_branches_stays_unknown() -> None:
    """One price point and unresolved usage: the branches agree but the ATM limit is unknown."""
    evaluation, _, _ = evaluate(
        **path_kwargs(path=(("2026-10-14", "2.00"),), programme=(usd(RESERVATION_A, "2000000"),))
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == (
        "floor 6000000.00 / ceiling 6000000.00 under stated unknowns"
    )
    assert USAGE_A in unknown_ids(evaluation)
    assert REGISTERED_A in envelope.unknown_constraints


def test_review_action_infeasible_on_one_price_branch_never_gives_a_number() -> None:
    """R = S = 7,000,000, nothing sold, 7,000,000 committed to the programme at $2 to $3.

    At $2.00 the sale is 3,500,000 shares, over the 3,000,000-share threshold; at $3.00 it
    fits. Both branch optima are 7,000,000, but the answer stays open on the sale schedule.
    """
    evaluation, _, _ = evaluate_with_actions(
        [cash(ATM_A, "at_the_market", "7000000")],
        **path_kwargs(
            path=PRICE_PATH,
            registered="7000000",
            programme=(usd(RESERVATION_A, "7000000"), usd(USAGE_A, "0")),
        ),
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == (
        "floor unstated / ceiling 7000000.00 under stated unknowns"
    )
    assert (
        f"asserted_actions_infeasible_on_price_branch:pessimistic:{NASDAQ_POOL}"
        in envelope.blockers
    )
    assert f"asserted_actions_infeasible:{NASDAQ_POOL}" not in envelope.blockers
    assert SCHEDULE_A in unknown_ids(evaluation)
    assert witness_of(evaluation) == {}


def test_review_usage_branch_infeasibility_is_not_labelled_a_price_branch() -> None:
    """No price path: an action failing only at P = S is named on the usage branch."""
    evaluation, _, _ = evaluate_with_actions(
        [cash(ATM_A, "at_the_market", "1000000")], **usage_kwargs(C10_02)
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == (
        "floor unstated / ceiling 16000000.00 under stated unknowns"
    )
    assert f"asserted_actions_infeasible_on_branch:pessimistic:{ATM_A}" in envelope.blockers
    assert not any("on_price_branch" in blocker for blocker in envelope.blockers)
    assert witness_of(evaluation) == {}


def test_l258_e_two_fixed_actions_in_one_group_raise() -> None:
    with pytest.raises(CapacityInputError):
        explain_with_actions(
            [
                cash(TAKE_A, "shelf_takedown", "1000000"),
                cash(TAKE_B, "shelf_takedown", "1000000"),
            ],
            **a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)),
        )
    # One fixed member is allowed, and it closes the group for the other route.
    evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "3000000")],
        **a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)),
    )
    envelope = evaluation.envelope
    assert envelope.mutually_exclusive == ((TAKE_A, TAKE_B),)
    assert money(envelope.aggregate_bound) == Decimal("8000000")
    assert witness_of(evaluation) == {TAKE_A: Decimal("8000000.00"), TAKE_B: Decimal("0.00")}
    remaining = evaluation.inputs["remaining_capacity"]["pessimistic"]
    assert Fraction(dict(remaining["routes"])[TAKE_B]) == Fraction(0)
    assert Fraction(dict(remaining["routes"])[TAKE_A]) == Fraction(5_000_000)


def test_l258_f_action_on_an_ineligible_route_is_blocked() -> None:
    reg, shares_records = standard_registration(withdrawn="observed")
    kwargs = {"registration": reg, "share_basis": shares_records}
    plain, _, _ = evaluate(**kwargs)
    evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "1000000")], **kwargs
    )
    envelope = evaluation.envelope
    assert f"asserted_action_on_ineligible_route:{TAKE_A}" in envelope.blockers
    assert routes_by_id(evaluation)[TAKE_A].status == "ineligible"
    # Excluded: it changes no number at all.
    assert evaluation.envelope.aggregate_bound.status == plain.envelope.aggregate_bound.status
    assert evaluation.envelope.aggregate_bound.value == plain.envelope.aggregate_bound.value
    assert witness_of(evaluation) == witness_of(plain)
    assert evaluation.inputs["actions_applied"][0]["applied"] is False
    assert evaluation.inputs["remaining_capacity"]["pessimistic"]["routes"] == []


@pytest.mark.parametrize(
    "kind,action",
    [
        ("route_kind", ActionSelection(TAKE_A, "at_the_market", "cash", Quantity.known("1", "usd"))),
        ("settlement", ActionSelection(TAKE_A, "shelf_takedown", "cashless", Quantity.known("1", "usd"))),
        (
            "conditions",
            ActionSelection(
                TAKE_A,
                "shelf_takedown",
                "cash",
                Quantity.known("1", "usd"),
                ("a_condition_this_route_does_not_carry",),
            ),
        ),
        ("quantity_status", ActionSelection(TAKE_A, "shelf_takedown", "cash", Quantity.unknown("usd"))),
        (
            "quantity_unit",
            ActionSelection(TAKE_A, "shelf_takedown", "cash", Quantity.known("1", "votes")),
        ),
        (
            "unknown_route",
            ActionSelection("shelf_takedown:ghost", "shelf_takedown", "cash", Quantity.known("1", "usd")),
        ),
    ],
)
def test_l258_g_mismatched_action_inputs_raise(kind: str, action: ActionSelection) -> None:
    with pytest.raises(CapacityInputError):
        explain_with_actions([action], **path_kwargs(path=PRICE_PATH))


def test_l258_h_recorded_only_action_changes_no_number() -> None:
    """An ActionSelection without a quantity is recorded, never applied (A48)."""
    plain, _, _ = evaluate(**path_kwargs(path=PRICE_PATH))
    evaluation, _, _ = evaluate_with_actions(
        [ActionSelection(TAKE_A, "shelf_takedown", "cash")], **path_kwargs(path=PRICE_PATH)
    )
    envelope = evaluation.envelope
    assert money(envelope.aggregate_bound) == money(plain.envelope.aggregate_bound)
    assert envelope.binding_constraints == plain.envelope.binding_constraints
    assert witness_of(evaluation) == witness_of(plain)
    assert envelope.blockers == plain.envelope.blockers
    assert unknown_ids(evaluation) == unknown_ids(plain)
    assert evaluation.kernel["evidence"] == plain.kernel["evidence"]
    applied = evaluation.inputs["actions_applied"]
    assert applied == [
        {
            "route_id": TAKE_A,
            "action": "shelf_takedown",
            "settlement": "cash",
            "fixed": False,
            "applied": False,
            "usd_pessimistic": None,
            "usd_optimistic": None,
            "conditions_assumed_met": [],
        }
    ]
    remaining = evaluation.inputs["remaining_capacity"]["pessimistic"]
    assert remaining == plain.inputs["remaining_capacity"]["pessimistic"]


# ---------------------------------------------------------------------------
# §2.0 / §3 — identity, receipt and envelope deltas
# ---------------------------------------------------------------------------


def test_c2_identity_and_receipt_cover_the_new_inputs() -> None:
    evaluation, state, scenario = evaluate(**path_kwargs(path=PRICE_PATH, programme=ATM_PROGRAMME))
    envelope = evaluation.envelope
    assert c2.IMPLEMENTATION == (
        "capital_structure.capacity.c2_adapter.v2+" + capacity_joint.IMPLEMENTATION
    )
    assert evaluation.inputs["adapter"] == "capital_structure.capacity.c2_adapter.v2"
    assert evaluation.inputs["implementation"] == c2.IMPLEMENTATION
    assert envelope.receipt.implementation_digest == sha256_of(
        {"contract": C1.STATE_CONTRACT_VERSION, "implementation": c2.IMPLEMENTATION}
    )
    assert envelope.receipt.scenario_id == scenario.scenario_id == envelope.scenario_id
    assert envelope.state_id == state.state_id
    for key in (
        "price",
        "branches",
        "exclusive_groups",
        "programme_usage",
        "actions_applied",
        "remaining_capacity",
    ):
        assert key in evaluation.inputs
    assert "actions_recorded_not_applied" not in evaluation.inputs
    assert evaluation.inputs["kernel"]["optimistic"] == sha256_of(evaluation.kernel["optimistic"])
    assert sha256_of(_record(evaluation.inputs)) == envelope.receipt.input_digest


def test_c2_envelope_deltas_survive_record_reversal() -> None:
    """§0 item 6 with every C2 delta populated: exclusivity, actions and branches."""
    forward, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "3000000")],
        **a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)),
    )
    reversed_evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "3000000")],
        **a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)),
        reverse_records=True,
    )
    assert strip_identity(reversed_evaluation.envelope.as_record()) == strip_identity(
        forward.envelope.as_record()
    )
    assert reversed_evaluation.inputs["remaining_capacity"] == forward.inputs["remaining_capacity"]
    assert reversed_evaluation.kernel == forward.kernel
