"""SPEC_C2B §3 -- scenario actions on routes the capacity model does not own.

Every number here is exact: money is compared as ``Decimal``, kernel values as
``Fraction``, and nothing is compared approximately.  There is no float literal
in this file.  The fixtures and the receipt helper come from
``tests.test_capital_structure_capacity`` (C1) and
``tests.test_capital_structure_capacity_c2`` (C2a) and are never copied.

Case map: §0 item 1 -> ``test_c2b_instrument_actions_leave_every_number_unchanged``,
``test_c2b_debt_draw_and_other_are_funding_only``; §0 item 2 ->
``test_c2b_fixed_pipe_makes_the_aggregate_unknown``,
``test_c2b_fixed_registered_direct_on_an_unknown_ceiling_keeps_the_c2a_ceiling_text``;
§0 item 3 -> ``test_c2b_takedown_on_a_missing_route_still_raises``,
``test_c2b_at_the_market_on_a_missing_route_still_raises``, ``test_c2b_owner_table``;
§0 item 4 -> ``test_c2b_inputs_record_carries_no_amount``,
``test_c2b_settlement_and_conditions_are_recorded_verbatim_and_sorted``; §0 item 5 ->
``test_c2b_actions_applied_holds_only_envelope_routes``; §0 item 6 ->
``check`` (called by every test) plus ``test_c2b_digest_and_order_determinism``;
§2.3 -> ``test_c2b_contradicted_stays_contradicted_with_an_unmodelled_action``,
``test_c2b_recorded_only_unmodelled_action_changes_nothing``; §2.4 ->
``test_c2b_exclusivity_naming_an_instrument_route_still_raises``.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from fractions import Fraction
from typing import Any, Mapping, Sequence

import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_capacity_c2 as C2
from engine.capital_structure import capacity as c2b
from engine.capital_structure.capacity import CapacityInputError
from engine.capital_structure.issuer_state_contracts import (
    ROUTE_KINDS,
    ActionSelection,
    Quantity,
    _record,
    sha256_of,
    validate_state_record,
)
from tests.test_capital_structure_capacity import (
    BABY_POOL,
    NASDAQ_POOL,
    PATH_A,
    PATH_B,
    pools_by_id,
    routes_by_id,
    standard_registration,
    strip_identity,
    unknown_ids,
    usd,
)
from tests.test_capital_structure_capacity_c2 import (
    REGISTERED_A,
    REGISTERED_B,
    TAKE_A,
    TAKE_B,
    a21_kwargs,
    cash,
    money,
)

#: Non-envelope route ids.  None of them is a route of any fixture envelope here,
#: so every action on one is partitioned off by SPEC_C2B §2.1.
WARRANT_ROUTE = "warrant_exercise:series-a-2026"
CONVERSION_ROUTE = "conversion:november-notes"
EXCHANGE_ROUTE = "exchange:preferred-series-b"
REDEMPTION_ROUTE = "redemption:note-2027"
REPURCHASE_ROUTE = "repurchase:buyback-2026"
DEBT_ROUTE = "debt_draw:revolver-2026"
OTHER_ROUTE = "other:legal-settlement-2026"
PIPE_ROUTE = "pipe:october-private-placement"
DIRECT_ROUTE = "registered_direct:october-2026"
EQUITY_LINE_ROUTE = "equity_line:forward-purchase-2026"

#: §2.2 restated as this file's own oracle.  ``None`` is the refusal: capacity
#: owns those two route kinds, so a route the envelope does not carry is an input
#: error rather than another model's action.
OWNERS: dict[str, str | None] = {
    "shelf_takedown": None,
    "at_the_market": None,
    "warrant_exercise": "supply",
    "conversion": "supply",
    "exchange": "supply",
    "redemption": "supply",
    "repurchase": "supply",
    "debt_draw": "funding_only",
    "other": "funding_only",
    "equity_line": "capacity_unmodelled",
    "registered_direct": "capacity_unmodelled",
    "pipe": "capacity_unmodelled",
}
CAPACITY_KINDS = tuple(kind for kind, owner in OWNERS.items() if owner is None)
UNMODELLED_KINDS = tuple(
    sorted(kind for kind, owner in OWNERS.items() if owner == "capacity_unmodelled")
)
#: SPEC_C2D §0.2 supersedes §2.3 for ONE shape: a fixed CASH PIPE now consumes the
#: Nasdaq and authorized share pools at ``p_start`` and is modelled.  A registered
#: direct or equity line stays unmodelled until a path is declared (C2d §0.6), and
#: a non-cash PIPE stays unmodelled exactly as before (C2d §0.11) -- so this file's
#: §2.3 unknown-path tests put ``NON_CASH`` on a PIPE.
C2D_MODELLED_CASH_KINDS = ("pipe",)
NON_CASH = "physical"

#: §0 item 4: no amount, price, share count or cash field may appear in the record.
AMOUNT_KEYS = frozenset({"quantity", "usd", "shares", "price", "gross", "net", "amount"})
QUANTITY_KEYS = frozenset({"unit", "status", "value"})
RECORD_KEYS = ["route_id", "action", "settlement", "owner", "fixed", "conditions_assumed_met"]


# ---------------------------------------------------------------------------
# The ONE shared helper every test in this file calls (§0 item 6)
# ---------------------------------------------------------------------------


def check(evaluation: Any) -> None:
    """Validate the envelope, walk it for forbidden keys and re-derive the digest."""
    envelope = evaluation.envelope
    record = envelope.as_record()
    validate_state_record("capacity_envelope", record)
    C1.walk_forbidden_keys(record)
    C1.walk_forbidden_keys(evaluation.inputs)
    C1.walk_quantities(record)
    C1.walk_quantities(evaluation.inputs)
    assert sha256_of(_record(evaluation.inputs)) == envelope.receipt.input_digest
    # §2.4: the record is ALWAYS present from C2b on, so "no such actions" and
    # "none supplied" digest the same shape.
    assert isinstance(evaluation.inputs["non_capacity_actions"], list)


def evaluate(**kwargs: Any) -> Any:
    """``C1.evaluate`` plus this file's helper."""
    evaluation, state, scenario = C1.evaluate(**kwargs)
    check(evaluation)
    return evaluation, state, scenario


def evaluate_with_actions(actions: Sequence[ActionSelection], **kwargs: Any) -> Any:
    """``C2.evaluate_with_actions`` plus this file's helper."""
    evaluation, state, scenario = C2.evaluate_with_actions(actions, **kwargs)
    check(evaluation)
    return evaluation, state, scenario


def action(
    route_id: str,
    kind: str,
    settlement: str,
    value: str | None = None,
    *,
    unit: str = "usd",
    status: str = "known",
    conditions: Sequence[str] = (),
) -> ActionSelection:
    """One action on a route the envelope does not carry.

    The adapter never reads the quantity (§2.2), so any admitted quantity states
    ``fixed``; ``status="unknown"`` proves the quantity's status is not inspected.
    """
    quantity: Quantity | None = None
    if status != "known":
        quantity = Quantity.unknown(unit, **_basis(unit))
    elif value is not None:
        quantity = Quantity.known(value, unit, **_basis(unit))
    return ActionSelection(route_id, kind, settlement, quantity, tuple(conditions))


def _basis(unit: str) -> dict[str, str]:
    return {"share_basis": "scenario_incremental_issuance"} if unit == "shares" else {}


def without_identity(evaluation: Any) -> dict[str, Any]:
    """§0 item 1: the envelope minus ``scenario_id`` and ``receipt``."""
    record = evaluation.envelope.as_record()
    record.pop("scenario_id")
    record.pop("receipt")
    return record


def without_record(evaluation: Any, *dropped: str) -> dict[str, Any]:
    """The digested inputs minus the C2b record (and the identity it digests)."""
    body = dict(evaluation.inputs)
    for key in (*dropped, "non_capacity_actions", "scenario_id"):
        body.pop(key)
    return body


def assert_every_key_equal(left: Mapping[str, Any], right: Mapping[str, Any], label: str) -> None:
    assert sorted(left) == sorted(right), f"{label}: key sets differ"
    for key in sorted(left):
        assert left[key] == right[key], f"{label}.{key}"


def assert_unchanged(evaluation: Any, baseline: Any) -> None:
    """§0 item 1: equal to the same scenario without the non-envelope actions."""
    check(evaluation)
    check(baseline)
    assert_every_key_equal(without_identity(evaluation), without_identity(baseline), "envelope")
    assert_every_key_equal(without_record(evaluation), without_record(baseline), "inputs")
    assert evaluation.kernel == baseline.kernel


def walk_no_amount(value: Any, path: str = "<root>") -> None:
    """§0 item 4: no amount key, no Quantity shape, no number object of any kind."""
    if isinstance(value, Mapping):
        assert not QUANTITY_KEYS <= set(value), f"{path}: a Quantity-shaped record"
        for key, item in value.items():
            assert key not in AMOUNT_KEYS, f"{path}.{key}: an amount field"
            walk_no_amount(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            walk_no_amount(item, f"{path}[{index}]")
    else:
        assert isinstance(value, (str, bool)), f"{path}: {type(value).__name__} is not text or a flag"


def owners_of(evaluation: Any) -> dict[str, str]:
    return {
        item["route_id"]: item["owner"]
        for item in evaluation.inputs["non_capacity_actions"]
    }


def unmodelled_unknown(evaluation: Any, route_id: str) -> Any:
    unknown_id = f"action_route_not_modelled:{route_id}"
    named = {item.unknown_id: item for item in evaluation.envelope.unknowns}
    assert unknown_id in named, sorted(named)
    return named[unknown_id]


def pool_ids(evaluation: Any) -> tuple[str, ...]:
    return tuple(sorted(pool.constraint_id for pool in evaluation.envelope.shared_pools))


def assert_pools_undetermined(evaluation: Any, baseline: Any) -> None:
    """C2b audit: once §2.3 leaves the optimum undetermined, no pool claims binding or slack.

    Each pool keeps its C2a bound and identity; only its status becomes unknown.
    """
    pools = evaluation.envelope.shared_pools
    before = baseline.envelope.shared_pools
    assert [pool.constraint_id for pool in pools] == [pool.constraint_id for pool in before]
    assert [pool.bound for pool in pools] == [pool.bound for pool in before]
    assert {pool.status for pool in pools} <= {"unknown"}, [
        (pool.constraint_id, pool.status) for pool in pools
    ]
    assert [item["status"] for item in evaluation.inputs["pools"]] == ["unknown"] * len(pools)


def refused_message(kind: str, route_id: str, **kwargs: Any) -> str:
    """§0 item 3: the refusal names the route id and the kind capacity owns."""
    with pytest.raises(CapacityInputError) as raised:
        C2.explain_with_actions([action(route_id, kind, "cash", "1000000")], **kwargs)
    message = str(raised.value)
    assert message == (
        f"scenario action on {route_id}: capacity owns {kind} routes and the envelope "
        "has no such route"
    )
    assert route_id in message and kind in message
    return message


# ---------------------------------------------------------------------------
# §0 item 1 -- instrument and funding actions change no number
# ---------------------------------------------------------------------------


def test_c2b_instrument_actions_leave_every_number_unchanged() -> None:
    """A fixed takedown plus five instrument actions: every C2a number survives."""
    kwargs = a21_kwargs(outstanding="30000005")
    remaining_fixed = "3000000"
    takedown = cash(TAKE_A, "shelf_takedown", remaining_fixed)
    baseline, _, _ = evaluate_with_actions([takedown], **kwargs)
    instruments = [
        action(WARRANT_ROUTE, "warrant_exercise", "cash", "1200000"),
        action(CONVERSION_ROUTE, "conversion", "net_share", "900000", unit="shares"),
        action(EXCHANGE_ROUTE, "exchange", "cashless", "400000"),
        action(REDEMPTION_ROUTE, "redemption", "cash", "250000"),
        action(REPURCHASE_ROUTE, "repurchase", "cash", "150000"),
    ]
    evaluation, _, _ = evaluate_with_actions([takedown, *instruments], **kwargs)
    assert_unchanged(evaluation, baseline)

    envelope = evaluation.envelope
    assert money(envelope.aggregate_bound) == Decimal("10000000")
    assert envelope.aggregate_bound.status == "known"
    assert envelope.binding_constraints == (BABY_POOL,)
    assert envelope.unknown_constraints == ()
    assert envelope.feasible_witness is not None
    assert C2.witness_of(evaluation) == {
        TAKE_A: Decimal("8000000.00"),
        TAKE_B: Decimal("2000000.00"),
    }
    assert Fraction(pools_by_id(evaluation)[BABY_POOL].bound.value) == Fraction(10_000_000)
    assert Fraction(pools_by_id(evaluation)[NASDAQ_POOL].bound.value) == Fraction(6_000_000)
    assert money(routes_by_id(evaluation)[TAKE_A].limit) == Decimal("8000000")
    # The kernel solved the residual: 3,000,000 committed plus 7,000,000 residual.
    assert Fraction(evaluation.kernel["evidence"]["value"]) == Fraction(7_000_000)
    assert Fraction(evaluation.kernel["evidence"]["value"]) + Fraction(
        remaining_fixed
    ) == Fraction(envelope.aggregate_bound.value)
    assert "unmodelled_consumption" not in evaluation.inputs
    records = evaluation.inputs["non_capacity_actions"]
    assert [item["route_id"] for item in records] == sorted(
        [WARRANT_ROUTE, CONVERSION_ROUTE, EXCHANGE_ROUTE, REDEMPTION_ROUTE, REPURCHASE_ROUTE]
    )
    assert set(owners_of(evaluation).values()) == {"supply"}
    assert [item["fixed"] for item in records] == [True] * 5
    assert {item["route_id"]: item["settlement"] for item in records} == {
        CONVERSION_ROUTE: "net_share",
        EXCHANGE_ROUTE: "cashless",
        REDEMPTION_ROUTE: "cash",
        REPURCHASE_ROUTE: "cash",
        WARRANT_ROUTE: "cash",
    }


def test_c2b_debt_draw_and_other_are_funding_only() -> None:
    """§2.2: a debt draw and an ``other`` action belong to the funding schedule."""
    kwargs = a21_kwargs(outstanding="30000005")
    takedown = cash(TAKE_A, "shelf_takedown", "3000000")
    baseline, _, _ = evaluate_with_actions([takedown], **kwargs)
    evaluation, _, _ = evaluate_with_actions(
        [
            takedown,
            action(DEBT_ROUTE, "debt_draw", "cash", "5000000"),
            action(OTHER_ROUTE, "other", "unknown", "1"),
        ],
        **kwargs,
    )
    assert_unchanged(evaluation, baseline)
    assert owners_of(evaluation) == {DEBT_ROUTE: "funding_only", OTHER_ROUTE: "funding_only"}
    assert [item["route_id"] for item in evaluation.inputs["non_capacity_actions"]] == [
        DEBT_ROUTE,
        OTHER_ROUTE,
    ]
    assert money(evaluation.envelope.aggregate_bound) == Decimal("10000000")
    assert evaluation.envelope.feasible_witness is not None
    assert "unmodelled_consumption" not in evaluation.inputs
    assert not any(
        item.unknown_id.startswith("action_route_not_modelled:")
        for item in evaluation.envelope.unknowns
    )


# ---------------------------------------------------------------------------
# §0 items 3 and 4 -- the owner table over all twelve route kinds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ROUTE_KINDS)
def test_c2b_owner_table(kind: str) -> None:
    """Every ROUTE_KINDS member on a non-envelope id: refused, or owned per §2.2."""
    # The spec table tiles the contract's twelve kinds, so no kind is unowned.
    assert set(OWNERS) == set(ROUTE_KINDS)
    assert set(c2b.CAPACITY_OWNED_ROUTE_KINDS) == set(CAPACITY_KINDS)
    assert set(c2b.NON_CAPACITY_OWNERS) == set(ROUTE_KINDS) - set(CAPACITY_KINDS)
    assert not set(c2b.CAPACITY_OWNED_ROUTE_KINDS) & set(c2b.NON_CAPACITY_OWNERS)
    route_id = f"{kind}:c2b-not-an-envelope-route"
    kwargs = a21_kwargs(outstanding="30000005")
    if OWNERS[kind] is None:
        refused_message(kind, route_id, **kwargs)
        baseline, _, _ = evaluate(**kwargs)
        assert money(baseline.envelope.aggregate_bound) == Decimal("10000000")
        return
    evaluation, _, _ = evaluate_with_actions(
        [action(route_id, kind, "cash", "1000000")], **kwargs
    )
    assert evaluation.inputs["non_capacity_actions"] == [
        {
            "route_id": route_id,
            "action": kind,
            "settlement": "cash",
            "owner": OWNERS[kind],
            "fixed": True,
            "conditions_assumed_met": [],
        }
    ]
    if kind in C2D_MODELLED_CASH_KINDS:
        # SPEC_C2D §0.2: a fixed cash PIPE is modelled -- no named unknown, the
        # aggregate stays known, a witness is offered and the consumption is
        # reported in ``outside_consumption`` (never added to the aggregate).
        assert "unmodelled_consumption" not in evaluation.inputs
        assert [row["route_id"] for row in evaluation.inputs["outside_consumption"]] == [
            route_id
        ]
        assert not any(
            item.unknown_id.startswith("action_route_not_modelled:")
            for item in evaluation.envelope.unknowns
        )
        assert evaluation.envelope.aggregate_bound.status == "known"
        assert evaluation.envelope.feasible_witness is not None
    elif kind in UNMODELLED_KINDS:
        # §2.3: a FIXED unmodelled action is a named unknown, never a number.
        assert evaluation.inputs["unmodelled_consumption"] == [route_id]
        assert unmodelled_unknown(evaluation, route_id).affects == pool_ids(evaluation)
        assert evaluation.envelope.aggregate_bound.status == "unknown"
        assert evaluation.envelope.aggregate_bound.value is None
        assert evaluation.envelope.feasible_witness is None
        assert evaluation.envelope.binding_constraints == ()
        assert_pools_undetermined(evaluation, evaluate(**kwargs)[0])
    else:
        assert "unmodelled_consumption" not in evaluation.inputs
        assert_unchanged(evaluation, evaluate(**kwargs)[0])


# ---------------------------------------------------------------------------
# §0 item 2 / §2.3 -- a fixed unmodelled action names an unknown
# ---------------------------------------------------------------------------


def test_c2b_fixed_non_cash_pipe_makes_the_aggregate_unknown() -> None:
    """The A21 known case (10,000,000) plus a fixed non-cash PIPE: a named unknown.

    A CASH PIPE is modelled from SPEC_C2D on (``test_c2d_pipe_consumes_share_pools_at_p_start``).
    """
    kwargs = a21_kwargs(outstanding="30000005")
    baseline, _, _ = evaluate(**kwargs)
    assert money(baseline.envelope.aggregate_bound) == Decimal("10000000")
    evaluation, _, _ = evaluate_with_actions(
        [action(PIPE_ROUTE, "pipe", NON_CASH, "5000000")], **kwargs
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.unit == "usd"
    assert envelope.aggregate_bound.note == (
        "floor not evaluated / ceiling 10000000.00 under stated unknowns"
    )
    # The quoted ceiling is exactly the C2a ceiling for the scenario without it.
    assert envelope.aggregate_bound.note.endswith(
        f"ceiling {baseline.envelope.aggregate_bound.value} under stated unknowns"
    )
    assert envelope.feasible_witness is None
    assert envelope.binding_constraints == ()
    assert envelope.unknown_constraints == baseline.envelope.unknown_constraints == ()
    assert envelope.blockers == baseline.envelope.blockers
    assert envelope.routes == baseline.envelope.routes
    # C2b audit: C2a's baby-shelf "binding" and Nasdaq "slack" are claims about a
    # determined optimum; with the PIPE's consumption unknown both become unknown.
    assert [(pool.constraint_id, pool.status) for pool in baseline.envelope.shared_pools] == [
        (BABY_POOL, "binding"),
        (NASDAQ_POOL, "slack"),
        (REGISTERED_A, "slack"),
        (REGISTERED_B, "slack"),
    ]
    assert_pools_undetermined(evaluation, baseline)
    named = unmodelled_unknown(evaluation, PIPE_ROUTE)
    assert named.affects == (BABY_POOL, NASDAQ_POOL, REGISTERED_A, REGISTERED_B)
    assert named.affects == pool_ids(evaluation)
    assert named.description == (
        f"pipe on {PIPE_ROUTE} may draw on shared registration and exchange-approval pools "
        "that capacity models only for shelf takedowns and at-the-market programmes"
    )
    assert named.resolving_fact == (
        "the registration path, pricing date and share or dollar consumption of "
        f"{PIPE_ROUTE} against each shared pool"
    )
    assert unknown_ids(evaluation) == unknown_ids(baseline) | {
        f"action_route_not_modelled:{PIPE_ROUTE}"
    }
    assert evaluation.inputs["unmodelled_consumption"] == [PIPE_ROUTE]
    assert evaluation.inputs["actions_applied"] == []
    assert evaluation.inputs["remaining_capacity"] == baseline.inputs["remaining_capacity"]


def test_c2b_fixed_registered_direct_on_an_unknown_ceiling_keeps_the_c2a_ceiling_text() -> None:
    """An unknown C2a ceiling is quoted verbatim, ``unbounded`` included."""
    unknown_outstanding = a21_kwargs(outstanding=None)
    baseline, _, _ = evaluate(**unknown_outstanding)
    assert baseline.envelope.aggregate_bound.status == "unknown"
    assert baseline.envelope.aggregate_bound.note == (
        "floor 0.00 / ceiling 10000000.00 under stated unknowns"
    )
    assert C2.witness_of(baseline) == {TAKE_A: Decimal("0.00"), TAKE_B: Decimal("0.00")}
    evaluation, _, _ = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")], **unknown_outstanding
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "unknown"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == (
        "floor not evaluated / ceiling 10000000.00 under stated unknowns"
    )
    assert envelope.feasible_witness is None
    assert envelope.binding_constraints == ()
    assert envelope.unknown_constraints == baseline.envelope.unknown_constraints == (NASDAQ_POOL,)
    assert_pools_undetermined(evaluation, baseline)
    assert unmodelled_unknown(evaluation, DIRECT_ROUTE).affects == pool_ids(evaluation)
    assert evaluation.inputs["unmodelled_consumption"] == [DIRECT_ROUTE]

    # A deduction above the registered amount contradicts the pool, so the C2a
    # ceiling is ``unbounded``; that text is kept, never replaced by a number.
    reg, share_records = standard_registration(registered="20000000", float_value="300000000")
    overrun = {
        "registration": reg,
        "share_basis": share_records,
        "resolutions": [
            usd(f"shelf_usage:{PATH_A}", "25000000"),
            usd(f"continuing_offering:{PATH_A}", "0"),
        ],
    }
    unbounded_baseline, _, _ = evaluate(**overrun)
    assert unbounded_baseline.envelope.aggregate_bound.note == (
        "floor 0.00 / ceiling unbounded under stated unknowns"
    )
    unbounded, _, _ = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")], **overrun
    )
    assert unbounded.envelope.aggregate_bound.status == "unknown"
    assert unbounded.envelope.aggregate_bound.value is None
    assert unbounded.envelope.aggregate_bound.note == (
        "floor not evaluated / ceiling unbounded under stated unknowns"
    )
    assert unbounded.envelope.feasible_witness is None
    assert unbounded.envelope.binding_constraints == ()
    assert unbounded.envelope.unknown_constraints == (
        unbounded_baseline.envelope.unknown_constraints
    )
    assert_pools_undetermined(unbounded, unbounded_baseline)
    assert unmodelled_unknown(unbounded, DIRECT_ROUTE).affects == (REGISTERED_A,)
    assert unbounded.inputs["unmodelled_consumption"] == [DIRECT_ROUTE]


def test_c2b_contradicted_stays_contradicted_with_an_unmodelled_action() -> None:
    """§2.3: more consumption cannot cure a contradiction; the unknown is still named."""
    kwargs = a21_kwargs(outstanding="30000005")
    committed = [
        cash(TAKE_A, "shelf_takedown", "8000000"),
        cash(TAKE_B, "shelf_takedown", "7000000"),
    ]
    baseline, _, _ = evaluate_with_actions(committed, **kwargs)
    assert baseline.envelope.aggregate_bound.status == "contradicted"
    assert baseline.envelope.feasible_witness == ()
    evaluation, _, _ = evaluate_with_actions(
        [*committed, action(EQUITY_LINE_ROUTE, "equity_line", "cash", "1000000")], **kwargs
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "contradicted"
    assert envelope.aggregate_bound.value is None
    assert envelope.aggregate_bound.note == baseline.envelope.aggregate_bound.note
    assert envelope.blockers == baseline.envelope.blockers
    assert envelope.binding_constraints == () == baseline.envelope.binding_constraints
    # §2.3: no witness at all, not even the empty one C2a returned.
    assert envelope.feasible_witness is None
    assert_pools_undetermined(evaluation, baseline)
    assert unmodelled_unknown(evaluation, EQUITY_LINE_ROUTE).affects == pool_ids(evaluation)
    assert unknown_ids(evaluation) == unknown_ids(baseline) | {
        f"action_route_not_modelled:{EQUITY_LINE_ROUTE}"
    }
    assert evaluation.inputs["unmodelled_consumption"] == [EQUITY_LINE_ROUTE]
    assert evaluation.inputs["actions_applied"] == baseline.inputs["actions_applied"]
    assert evaluation.inputs["remaining_capacity"] == baseline.inputs["remaining_capacity"]


def test_c2b_long_unmodelled_route_id_gets_a_digest_unknown_id() -> None:
    """C2b audit: a lawful 195-character route id must not overflow the unknown id."""
    kwargs = a21_kwargs(outstanding="30000005")
    long_route = "pipe:" + "x" * 190
    evaluation, _, _ = evaluate_with_actions(
        [action(long_route, "pipe", NON_CASH, "5000000")], **kwargs
    )
    digest = hashlib.sha256(long_route.encode("utf-8")).hexdigest()[:16]
    named = {item.unknown_id: item for item in evaluation.envelope.unknowns}
    assert f"action_route_not_modelled:{digest}" in named, sorted(named)
    assert long_route in named[f"action_route_not_modelled:{digest}"].description
    assert evaluation.inputs["unmodelled_consumption"] == [long_route]
    assert evaluation.envelope.aggregate_bound.status == "unknown"
    # A route id that fits keeps the readable form.
    short = evaluate_with_actions([action(PIPE_ROUTE, "pipe", NON_CASH, "5000000")], **kwargs)[0]
    assert unmodelled_unknown(short, PIPE_ROUTE).unknown_id == (
        f"action_route_not_modelled:{PIPE_ROUTE}"
    )


def test_c2b_recorded_only_unmodelled_action_changes_nothing() -> None:
    """§2.3: recorded only (no quantity), the three unmodelled kinds move nothing."""
    kwargs = a21_kwargs(outstanding="30000005")
    baseline, _, _ = evaluate(**kwargs)
    evaluation, _, _ = evaluate_with_actions(
        [
            action(PIPE_ROUTE, "pipe", "cash"),
            action(DIRECT_ROUTE, "registered_direct", "unknown"),
            action(EQUITY_LINE_ROUTE, "equity_line", "pre_funded"),
        ],
        **kwargs,
    )
    assert_unchanged(evaluation, baseline)
    assert money(evaluation.envelope.aggregate_bound) == Decimal("10000000")
    assert evaluation.envelope.feasible_witness is not None
    assert evaluation.envelope.binding_constraints == (BABY_POOL,)
    assert "unmodelled_consumption" not in evaluation.inputs
    assert not any(
        item.unknown_id.startswith("action_route_not_modelled:")
        for item in evaluation.envelope.unknowns
    )
    records = evaluation.inputs["non_capacity_actions"]
    assert [item["route_id"] for item in records] == [
        EQUITY_LINE_ROUTE,
        PIPE_ROUTE,
        DIRECT_ROUTE,
    ]
    assert [item["fixed"] for item in records] == [False, False, False]
    assert set(owners_of(evaluation).values()) == {"capacity_unmodelled"}


# ---------------------------------------------------------------------------
# §0 item 3 -- capacity still owns its two route kinds
# ---------------------------------------------------------------------------


def test_c2b_takedown_on_a_missing_route_still_raises() -> None:
    """A shelf takedown on a route the envelope does not carry is refused by name."""
    kwargs = a21_kwargs(outstanding="30000005")
    route_id = "shelf_takedown:ghost"
    message = refused_message("shelf_takedown", route_id, **kwargs)
    assert message.startswith(f"scenario action on {route_id}:")
    # The same route id under a kind capacity does not own is accepted.
    evaluation, _, _ = evaluate_with_actions(
        [action(route_id, "other", "cash", "1000000")], **kwargs
    )
    assert owners_of(evaluation) == {route_id: "funding_only"}


def test_c2b_at_the_market_on_a_missing_route_still_raises() -> None:
    """An at-the-market action on a route the envelope does not carry is refused."""
    kwargs = a21_kwargs(outstanding="30000005")
    route_id = "at_the_market:ghost"
    message = refused_message("at_the_market", route_id, **kwargs)
    assert "capacity owns at_the_market routes" in message
    # An envelope ATM route is still the C2a path, not this refusal.
    atm, _, _ = evaluate(**C2.path_kwargs(path=C2.PRICE_PATH, programme=C2.ATM_PROGRAMME))
    assert C2.ATM_A in {route.route_id for route in atm.envelope.routes}


# ---------------------------------------------------------------------------
# §0 item 4 -- the record is verbatim, sorted and amount-free
# ---------------------------------------------------------------------------


def test_c2b_settlement_and_conditions_are_recorded_verbatim_and_sorted() -> None:
    """Settlement verbatim, conditions sorted, ``fixed`` from the quantity alone."""
    kwargs = a21_kwargs(outstanding="30000005")
    baseline, _, _ = evaluate(**kwargs)
    evaluation, _, _ = evaluate_with_actions(
        [
            action(
                WARRANT_ROUTE,
                "warrant_exercise",
                "unknown",
                conditions=("zeta_second", "alpha_first", "mid_condition"),
            ),
            action(DEBT_ROUTE, "debt_draw", "pre_funded", "1"),
            action(OTHER_ROUTE, "other", "cash", status="unknown"),
        ],
        **kwargs,
    )
    records = {item["route_id"]: item for item in evaluation.inputs["non_capacity_actions"]}
    assert records[WARRANT_ROUTE]["settlement"] == "unknown"
    assert records[WARRANT_ROUTE]["conditions_assumed_met"] == [
        "alpha_first",
        "mid_condition",
        "zeta_second",
    ]
    assert records[WARRANT_ROUTE]["fixed"] is False
    assert records[DEBT_ROUTE]["settlement"] == "pre_funded"
    assert records[DEBT_ROUTE]["conditions_assumed_met"] == []
    assert records[DEBT_ROUTE]["fixed"] is True
    # An asserted action with an UNKNOWN amount is still asserted (§2.2).
    assert records[OTHER_ROUTE]["fixed"] is True
    assert [item["route_id"] for item in evaluation.inputs["non_capacity_actions"]] == [
        DEBT_ROUTE,
        OTHER_ROUTE,
        WARRANT_ROUTE,
    ]
    # The C2a cash-only rule governs envelope routes alone: nothing was refused.
    assert_unchanged(evaluation, baseline)


def test_c2b_inputs_record_carries_no_amount() -> None:
    """§0 item 4: no quantity, price, share count or cash field anywhere in it."""
    kwargs = a21_kwargs(outstanding="30000005")
    evaluation, _, _ = evaluate_with_actions(
        [
            cash(TAKE_A, "shelf_takedown", "3000000"),
            action(WARRANT_ROUTE, "warrant_exercise", "cash", "1200000"),
            action(PIPE_ROUTE, "pipe", NON_CASH, "5000000"),
            action(DEBT_ROUTE, "debt_draw", "cash", "900000", conditions=("alpha_first",)),
        ],
        **kwargs,
    )
    records = evaluation.inputs["non_capacity_actions"]
    assert len(records) == 3
    for record in records:
        assert list(record) == RECORD_KEYS
        walk_no_amount(record)
    assert evaluation.inputs["unmodelled_consumption"] == [PIPE_ROUTE]
    walk_no_amount(evaluation.inputs["unmodelled_consumption"])
    # Exactly once each, sorted by route id.
    listed = [item["route_id"] for item in records]
    assert listed == sorted(listed) == [DEBT_ROUTE, PIPE_ROUTE, WARRANT_ROUTE]
    assert len(set(listed)) == len(listed)
    # The empty record is present too, and carries no amount either.
    empty, _, _ = evaluate(**kwargs)
    assert empty.inputs["non_capacity_actions"] == []
    walk_no_amount(empty.inputs["non_capacity_actions"])
    assert "unmodelled_consumption" not in empty.inputs


# ---------------------------------------------------------------------------
# §0 item 5 -- actions_applied holds only envelope routes
# ---------------------------------------------------------------------------


def test_c2b_actions_applied_holds_only_envelope_routes() -> None:
    """The C2a record and the residual solve see envelope-route actions only."""
    kwargs = a21_kwargs(outstanding="30000005")
    takedown = cash(TAKE_A, "shelf_takedown", "3000000")
    baseline, _, _ = evaluate_with_actions([takedown], **kwargs)
    evaluation, _, _ = evaluate_with_actions(
        [
            takedown,
            action(WARRANT_ROUTE, "warrant_exercise", "cash", "1200000"),
            action(DEBT_ROUTE, "debt_draw", "cash", "900000"),
            action(CONVERSION_ROUTE, "conversion", "net_share", "500000", unit="shares"),
        ],
        **kwargs,
    )
    envelope_routes = {route.route_id for route in evaluation.envelope.routes}
    applied = evaluation.inputs["actions_applied"]
    assert [item["route_id"] for item in applied] == [TAKE_A]
    assert {item["route_id"] for item in applied} <= envelope_routes
    non_capacity = set(owners_of(evaluation))
    assert non_capacity & envelope_routes == set()
    assert non_capacity == {WARRANT_ROUTE, DEBT_ROUTE, CONVERSION_ROUTE}
    assert applied == baseline.inputs["actions_applied"]
    assert applied[0]["fixed"] is True and applied[0]["applied"] is True
    assert applied[0]["usd_pessimistic"] == "3000000"
    remaining = evaluation.inputs["remaining_capacity"]["pessimistic"]
    assert remaining == baseline.inputs["remaining_capacity"]["pessimistic"]
    assert Fraction(dict(remaining["routes"])[TAKE_A]) == Fraction(5_000_000)
    assert Fraction(remaining["fixed_total"]) == Fraction(3_000_000)
    assert money(evaluation.envelope.aggregate_bound) == Decimal("10000000")


# ---------------------------------------------------------------------------
# §0 item 6 -- digest and order determinism
# ---------------------------------------------------------------------------


def test_c2b_digest_and_order_determinism() -> None:
    """One digest for one scenario; record and action order change nothing else."""
    kwargs = a21_kwargs(outstanding="30000005")
    actions = [
        cash(TAKE_A, "shelf_takedown", "3000000"),
        action(WARRANT_ROUTE, "warrant_exercise", "cash", "1200000"),
        action(PIPE_ROUTE, "pipe", NON_CASH, "5000000"),
        action(DEBT_ROUTE, "debt_draw", "cash", "900000"),
    ]
    first, _, _ = evaluate_with_actions(actions, **kwargs)
    second, _, _ = evaluate_with_actions(actions, **kwargs)
    assert first.envelope.receipt.input_digest == second.envelope.receipt.input_digest
    assert sha256_of(_record(first.inputs)) == first.envelope.receipt.input_digest
    assert first.inputs == second.inputs

    # Reversing the STATE's record order: the C1 identity strip is enough.
    reversed_records, _, _ = evaluate_with_actions(
        actions, **{**kwargs, "reverse_records": True}
    )
    assert strip_identity(reversed_records.envelope.as_record()) == strip_identity(
        first.envelope.as_record()
    )
    assert_every_key_equal(
        without_record(reversed_records, "state_id"), without_record(first, "state_id"), "inputs"
    )
    assert sha256_of(_record(without_record(reversed_records, "state_id"))) == sha256_of(
        _record(without_record(first, "state_id"))
    )

    # Reversing the ACTION order: both records are sorted and the scenario stores
    # its actions as a keyed set, so nothing moves, the scenario id included
    # (masterplan A22: row order does not change results; SPEC_S0 section 11 item 6).
    reordered, _, _ = evaluate_with_actions(list(reversed(actions)), **kwargs)
    assert reordered.inputs["non_capacity_actions"] == first.inputs["non_capacity_actions"]
    assert reordered.inputs["actions_applied"] == first.inputs["actions_applied"]
    assert reordered.inputs["unmodelled_consumption"] == first.inputs["unmodelled_consumption"]
    assert without_identity(reordered) == without_identity(first)
    assert_every_key_equal(
        without_record(reordered), without_record(first), "inputs-minus-scenario"
    )
    assert sha256_of(_record(without_record(reordered))) == sha256_of(
        _record(without_record(first))
    )
    assert reordered.inputs["scenario_id"] == first.inputs["scenario_id"]
    assert reordered.envelope.receipt.input_digest == first.envelope.receipt.input_digest
    assert reordered.envelope.as_record() == first.envelope.as_record()


# ---------------------------------------------------------------------------
# §2.2 last bullet -- exclusivity is still an envelope-route rule
# ---------------------------------------------------------------------------


def test_c2b_exclusivity_naming_an_instrument_route_still_raises() -> None:
    """C2a §2.4 is unchanged: a group may only name routes of this envelope."""
    route_id = WARRANT_ROUTE
    with pytest.raises(CapacityInputError) as raised:
        C2.explain_with_actions(
            [action(route_id, "warrant_exercise", "cash", "1000000")],
            **a21_kwargs(
                outstanding="30000005",
                other=(("route_exclusivity", f"{TAKE_A}|{route_id}"),),
            ),
        )
    assert route_id in str(raised.value)
    assert "is not a route of this envelope" in str(raised.value)
    # The same declaration over two envelope routes is still accepted.
    evaluation, _, _ = evaluate_with_actions(
        [cash(TAKE_A, "shelf_takedown", "3000000")],
        **a21_kwargs(
            outstanding="30000005", other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),)
        ),
    )
    assert evaluation.envelope.mutually_exclusive == ((TAKE_A, TAKE_B),)
    assert money(evaluation.envelope.aggregate_bound) == Decimal("8000000")
