"""SPEC_C2D §7 -- PIPE / registered-direct / equity-line pool consumption (C2d).

One named test per §0 item, built ONLY from the merged C1/C2a/C2b/C2c-A/C2x
helpers (imported, never copied): :func:`build` states and :func:`action`
selections come from those files, so nothing here hand-writes an envelope, a pool
row, a Constraint or an Unknown.

§0.1 byte identity is proven three ways: the two in-test identity tests below
compare every fixture against the SAME build with the C2d path switched off (a
monkeypatched no-op ``_outside_consumption``, which is exactly the pre-C2d
adapter for a scenario with no modelled outside action), every pre-existing
capacity test still passes with no edit, and a pre/post golden ``cmp`` over the
same fixture family runs outside the suite (never committed).

Every number is exact: ``Decimal`` text for money, ``Fraction`` for kernel
values.  No float literal or ``float()`` call appears in this file (§0.17).
"""

from __future__ import annotations

import ast
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Sequence

import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_capacity_c2 as C2
import tests.test_capital_structure_capacity_c2b as C2B
import tests.test_capital_structure_capacity_c2c_a as C2CA
import tests.test_capital_structure_capacity_c2x as C2X
from engine.capital_structure import capacity as c2d
from engine.capital_structure import capacity_joint
from engine.capital_structure.capacity import (
    OUTSIDE_REGISTERED_KINDS,
    ROUTE_REGISTRATION_PATHS_KEY,
)
from engine.capital_structure.issuer_state_contracts import (
    ActionSelection,
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
    standard_registration,
    usd,
)
from tests.test_capital_structure_capacity_c2 import (
    ATM_PROGRAMME,
    C10_02,
    PRICE_PATH,
    REGISTERED_A,
    REGISTERED_B,
    TAKE_A,
    TAKE_B,
    a21_kwargs,
    money,
    path_kwargs,
    usage_kwargs,
)
from tests.test_capital_structure_capacity_c2b import (
    DIRECT_ROUTE,
    EQUITY_LINE_ROUTE,
    PIPE_ROUTE,
    WARRANT_ROUTE,
    action,
    unmodelled_unknown,
    without_identity,
)
from tests.test_capital_structure_capacity_c2c_a import (
    AUTH_POOL,
    base_kwargs,
    capital,
    residual_pool,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "engine" / "capital_structure" / "capacity.py"
THIS_FILE = Path(__file__).resolve()

#: §3: the price in effect at the horizon start of every fixture here.
P_START = Fraction(2)
#: The §0.4 window: the same path C2a prices an at-the-market programme over.
WINDOW_LOW = Fraction(2)
WINDOW_HIGH = Fraction(3)

AUTH_UNKNOWN = f"authorized_share_headroom:{SALE}"


# ---------------------------------------------------------------------------
# The ONE shared helper every test in this file calls (§7)
# ---------------------------------------------------------------------------


def check(evaluation: Any) -> Any:
    """Validate the envelope, refuse forbidden keys, re-derive the input digest.

    Delegates to the C2b helper (imported, never copied) so the C0 contract walk,
    the A20 quantity walk and the ``non_capacity_actions`` record shape all run on
    every envelope this file produces, then re-asserts the two facts §7 names and
    pins the adapter id, which SPEC_C2D does NOT bump.
    """
    C2B.check(evaluation)
    envelope = evaluation.envelope
    record = envelope.as_record()
    validate_state_record("capacity_envelope", record)
    C1.walk_forbidden_keys(record)
    C1.walk_forbidden_keys(evaluation.inputs)
    assert sha256_of(_record(evaluation.inputs)) == envelope.receipt.input_digest
    assert c2d.IMPLEMENTATION == (
        "capital_structure.capacity.c2_adapter.v2+" + capacity_joint.IMPLEMENTATION
    ), "§0: the adapter id is NOT bumped"
    return evaluation


def evaluate(**kwargs: Any) -> Any:
    """``C2B.evaluate`` plus this file's helper."""
    evaluation, _, _ = C2B.evaluate(**kwargs)
    return check(evaluation)


def evaluate_with_actions(actions: Sequence[ActionSelection], **kwargs: Any) -> Any:
    """``C2B.evaluate_with_actions`` plus this file's helper."""
    evaluation, _, _ = C2B.evaluate_with_actions(actions, **kwargs)
    return check(evaluation)


def evaluate_authorized(actions: Sequence[ActionSelection], **kwargs: Any) -> Any:
    """The C2c-A authorized-capital fixture path, through this file's helper."""
    return check(C2CA.evaluate_actions(actions, **kwargs))


def evaluate_ledger(**kwargs: Any) -> Any:
    """The C2x transaction-ledger fixture path, through this file's helper."""
    return check(C2X.explain(**kwargs))


def explain_with_actions(actions: Sequence[ActionSelection], **kwargs: Any) -> Any:
    """The raw call behind ``evaluate_with_actions``, for the refusal cases."""
    return C2.explain_with_actions(actions, **kwargs)


def declared(
    *bindings: tuple[str, str],
    base: Sequence[tuple[str, str]] = NASDAQ_ASSUMPTIONS,
) -> tuple[tuple[str, Any], ...]:
    """``other_assumptions`` carrying one ``route_registration_paths`` declaration.

    Threaded exactly as ``route_exclusivity`` is (§7): the key is a scenario
    assumption, so the binding is an ASSUMPTION and never an observed fact.
    """
    text = ";".join(f"{route_id}={path_id}" for route_id, path_id in bindings)
    return tuple(base) + ((ROUTE_REGISTRATION_PATHS_KEY, text),)


def outside_rows(evaluation: Any) -> dict[str, dict[str, Any]]:
    """``inputs["outside_consumption"]`` by route id (§5)."""
    return {row["route_id"]: row for row in evaluation.inputs["outside_consumption"]}


def fraction_text(value: Fraction) -> str:
    """The adapter's exact ``Fraction`` text: ``numerator/denominator``, never a float."""
    return f"{value.numerator}/{value.denominator}"


def no_outside_views(evaluation: Any) -> None:
    """§0.1: neither C2d key is emitted when no outside action is modelled."""
    assert "outside_consumption" not in evaluation.inputs
    assert "outside_declared" not in evaluation.inputs


# ---------------------------------------------------------------------------
# The §0.1 fixture family: >= 10 existing fixtures, none with a modelled outside
# action, spanning C1 pools, C2a actions, C2b records, C2c-A ceilings, C2x ledgers
# ---------------------------------------------------------------------------


def _two_paths(**overrides: Any) -> dict[str, Any]:
    """The C1 worked joint example: two shelf paths sharing one I.B.6 headroom."""
    reg_a, shares = standard_registration(
        path_id=PATH_A, accession=ACC_A, registered="20000000", float_value="60000000"
    )
    reg_b, _ = standard_registration(
        path_id=PATH_B, accession=ACC_B, registered="10000000", float_value=None, outstanding=None
    )
    return dict(
        registration=reg_a + reg_b,
        share_basis=shares,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "5000000"),
            usd(f"continuing_offering:{PATH_A}", "1000000"),
            usd(f"shelf_usage:{PATH_B}", "0"),
            usd(f"continuing_offering:{PATH_B}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "15000000"),
        ],
        **overrides,
    )


def _single(**overrides: Any) -> dict[str, Any]:
    reg, shares = standard_registration(**overrides)
    return {"registration": reg, "share_basis": shares}


def _ineligible_pair() -> dict[str, Any]:
    reg_a, shares = standard_registration(
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
    return dict(
        registration=reg_a + reg_b,
        share_basis=shares,
        other=NASDAQ_ASSUMPTIONS,
        resolutions=[
            usd(f"shelf_usage:{PATH_A}", "0"),
            usd(f"continuing_offering:{PATH_A}", "0"),
            usd(f"baby_shelf_sold_trailing:{SALE}", "0"),
        ],
    )


FIXTURES: list[tuple[str, Callable[[], Any]]] = [
    # C1: shelf, programme and exchange-approval pools.
    ("c1_worked_joint_example", lambda: evaluate(**_two_paths())),
    ("c1_standard_single_path", lambda: evaluate(**_single())),
    ("c1_unknown_effectiveness", lambda: evaluate(**_single(effect="not_observed"))),
    ("c1_ineligible_path", lambda: evaluate(**_single(withdrawn="observed"))),
    ("c1_ineligible_pair_with_exchange_pool", lambda: evaluate(**_ineligible_pair())),
    ("c1_no_exchange_assumptions", lambda: evaluate(**usage_kwargs(C10_02))),
    # C2a: joint solve, actions, price paths, exclusivity.
    ("c2_a21_known", lambda: evaluate(**a21_kwargs(outstanding="30000005"))),
    ("c2_a21_unknown_outstanding", lambda: evaluate(**a21_kwargs(outstanding=None))),
    (
        "c2_path_atm_branching",
        lambda: evaluate(**path_kwargs(programme=ATM_PROGRAMME)),
    ),
    (
        "c2_fixed_takedown_action",
        lambda: evaluate_with_actions(
            [C2.cash(TAKE_A, "shelf_takedown", "1000000")], **a21_kwargs()
        ),
    ),
    (
        "c2_fixed_share_quantity_action",
        lambda: evaluate_with_actions(
            [C2.shares(TAKE_A, "shelf_takedown", "250000")], **a21_kwargs()
        ),
    ),
    (
        "c2_exclusive_group",
        lambda: evaluate(
            **a21_kwargs(other=(("route_exclusivity", f"{TAKE_A}|{TAKE_B}"),))
        ),
    ),
    # C2b: outside actions that C2d leaves exactly as they are.
    (
        "c2b_recorded_only_outside_actions",
        lambda: evaluate_with_actions(
            [
                action(PIPE_ROUTE, "pipe", "cash", None),
                action(DIRECT_ROUTE, "registered_direct", "cash", None),
                action(EQUITY_LINE_ROUTE, "equity_line", "cash", None),
            ],
            **a21_kwargs(),
        ),
    ),
    (
        "c2b_fixed_supply_action",
        lambda: evaluate_with_actions(
            [action(WARRANT_ROUTE, "warrant_exercise", "cash", "1000000")],
            **a21_kwargs(),
        ),
    ),
    (
        "c2b_fixed_funding_only_action",
        lambda: evaluate_with_actions(
            [C2B.action(C2B.DEBT_ROUTE, "debt_draw", "cash", "1000000")],
            **a21_kwargs(),
        ),
    ),
    (
        "c2b_non_cash_registered_direct",
        lambda: evaluate_with_actions(
            [action(DIRECT_ROUTE, "registered_direct", "physical", "1000000")],
            **a21_kwargs(),
        ),
    ),
    # C2c-A: the authorized-unreserved pool, known and ceiling-only.
    (
        "c2ca_ceiling_only_authorized_pool",
        lambda: evaluate(
            **base_kwargs(extra_shares=capital(authorized="2000000", issued="1000000"))
        ),
    ),
    (
        "c2ca_known_headroom_applied_action",
        lambda: evaluate_authorized(
            [C2CA.cash(TAKE_A, "shelf_takedown", "200000")],
            **base_kwargs(
                extra_shares=capital(
                    authorized="2000000", issued="1000000", reserved="500000"
                )
            ),
        ),
    ),
    # C2x: the transaction ledger, shelf and programme.
    ("c2x_x1_ledger", lambda: evaluate_ledger(transactions=C2X.x1_ledger())),
    (
        "c2x_x7_programme_ledger",
        lambda: evaluate_ledger(
            sale=C2X.PROGRAMME_SALE,
            transactions=C2X.x7_ledger(),
            resolutions=C2X.programme_resolutions(),
        ),
    ),
]

#: The fixtures whose outside actions are inert, with those actions removed (§7).
#: A FIXED non-cash registered direct is deliberately absent: it is unmodelled, so
#: removing it changes the envelope (§0.11), which its own test asserts.
FIXTURES_WITHOUT_ACTIONS: dict[str, Callable[[], Any]] = {
    "c2b_recorded_only_outside_actions": lambda: evaluate(**a21_kwargs()),
    "c2b_fixed_supply_action": lambda: evaluate(**a21_kwargs()),
    "c2b_fixed_funding_only_action": lambda: evaluate(**a21_kwargs()),
}


def base_build(monkeypatch: Any, build: Callable[[], Any]) -> Any:
    """The SAME build with the C2d path switched off -- the pre-C2d adapter.

    With no modelled outside action the pre-C2d adapter builds no view, parses no
    declaration and names no unknown, which is exactly a no-op
    ``_outside_consumption``; every other line of ``_apply_actions``,
    ``_residuals`` and ``_inputs`` is gated on that empty state (§6).
    """
    monkeypatch.setattr(c2d._Builder, "_outside_consumption", lambda self, outside: None)
    try:
        return check(build())
    finally:
        monkeypatch.undo()


def assert_identical(left: Any, right: Any, label: str) -> None:
    """§0.1: byte identity for the SAME scenario -- inputs and digest included."""
    assert without_identity(left) == without_identity(right), f"{label}: envelope"
    assert left.inputs == right.inputs, f"{label}: inputs"
    assert left.kernel == right.kernel, f"{label}: kernel"
    assert (
        left.envelope.receipt.input_digest == right.envelope.receipt.input_digest
    ), f"{label}: receipt digest"


def assert_identical_modulo_record(left: Any, right: Any, label: str) -> None:
    """§0.1/§7: identical once the C2b record of the removed actions is dropped.

    ``inputs["non_capacity_actions"]`` records the outside actions verbatim and
    ``scenario_id`` digests them, so comparing a scenario WITH a recorded-only
    action to the same build without one uses the C2b helper that drops exactly
    those two keys -- every other digested input must still be equal.
    """
    assert without_identity(left) == without_identity(right), f"{label}: envelope"
    assert C2B.without_record(left) == C2B.without_record(right), f"{label}: inputs"
    assert left.kernel == right.kernel, f"{label}: kernel"


# ---------------------------------------------------------------------------
# §0 item 1 -- byte identity with no modelled outside action
# ---------------------------------------------------------------------------


def test_c2d_no_outside_actions_is_byte_identical(monkeypatch: Any) -> None:
    """§0.1: no outside action on these routes -> byte-identical to base."""
    assert len(FIXTURES) >= 10, len(FIXTURES)
    for name, build in FIXTURES:
        after = build()
        before = base_build(monkeypatch, build)
        assert_identical(before, after, name)
        no_outside_views(after)


def test_c2d_recorded_only_outside_action_is_byte_identical(monkeypatch: Any) -> None:
    """§0.1: a RECORDED-ONLY (quantity None) outside action moves nothing."""
    kwargs = a21_kwargs(outstanding="30000005")
    recorded = [
        action(PIPE_ROUTE, "pipe", "cash", None),
        action(DIRECT_ROUTE, "registered_direct", "cash", None),
        action(EQUITY_LINE_ROUTE, "equity_line", "unknown", None),
    ]
    evaluation = evaluate_with_actions(recorded, **kwargs)
    no_outside_views(evaluation)
    no_outside_views(evaluation)
    assert "unmodelled_consumption" not in evaluation.inputs
    # (a) identical to the same build with the C2d path switched off;
    assert_identical(base_build(monkeypatch, lambda: evaluate_with_actions(recorded, **kwargs)),
                     evaluation, "recorded-only")
    # (b) identical to the same build with the outside actions removed (§7).
    assert_identical_modulo_record(evaluate(**kwargs), evaluation, "actions removed")
    for name, build in FIXTURES:
        if name not in FIXTURES_WITHOUT_ACTIONS:
            continue
        assert_identical(build(), base_build(monkeypatch, build), name)
        no_outside_views(build())
        assert_identical_modulo_record(
            FIXTURES_WITHOUT_ACTIONS[name](), build(), f"{name} removed"
        )


# ---------------------------------------------------------------------------
# §0 item 2 -- a fixed cash PIPE consumes the share pools at p_start
# ---------------------------------------------------------------------------


def test_c2d_pipe_consumes_share_pools_at_p_start() -> None:
    """§0.2: a PIPE draws only on the exchange-approval and charter share pools."""
    # Derivation (§3.1/§3.3): Q = 500,000 usd at p_start = 2 -> 250,000 shares off
    # BOTH the Nasdaq pool (3,000,000) and the authorized pool (500,000); the
    # registered dollar pool is not a PIPE pool, so it does not move.
    quantity = Fraction(500_000)
    shares = quantity / P_START
    kwargs = base_kwargs(
        extra_shares=capital(authorized="2000000", issued="1000000", reserved="500000")
    )
    baseline = evaluate_authorized([], **kwargs)
    assert money(baseline.envelope.aggregate_bound) == Decimal("1000000.00")
    evaluation = evaluate_authorized(
        [action(PIPE_ROUTE, "pipe", "cash", "500000")], **kwargs
    )
    row = outside_rows(evaluation)[PIPE_ROUTE]
    assert row["path_id"] is None
    assert row["pools"] == [AUTH_POOL, NASDAQ_POOL]
    assert row["usd"] == {"pessimistic": "500000", "optimistic": "500000"}
    # §0.2: BOTH branches, at p_start -- a PIPE is never priced at the window.
    assert row["shares"] == {
        "pessimistic": fraction_text(shares),
        "optimistic": fraction_text(shares),
    }
    assert residual_pool(evaluation, NASDAQ_POOL) == Fraction(3_000_000) - shares
    assert residual_pool(evaluation, AUTH_POOL) == Fraction(500_000) - shares
    assert residual_pool(evaluation, REGISTERED_A) == residual_pool(
        baseline, REGISTERED_A
    ) == Fraction(20_000_000)
    assert "unmodelled_consumption" not in evaluation.inputs
    assert not any(
        item.unknown_id.startswith("action_route_not_modelled:")
        for item in evaluation.envelope.unknowns
    )
    envelope = evaluation.envelope
    assert envelope.aggregate_bound.status == "known"
    # The aggregate is what the ENVELOPE routes can still raise: 250,000 shares of
    # charter headroom left at $2 (§0.15 -- the PIPE's own cash is never added).
    assert money(envelope.aggregate_bound) == Decimal("500000.00")
    assert money(envelope.aggregate_bound) < money(baseline.envelope.aggregate_bound)
    assert envelope.feasible_witness is not None
    assert C2.witness_of(evaluation) == {TAKE_A: Decimal("500000.00")}
    assert envelope.binding_constraints == (AUTH_POOL,)
    assert envelope.blockers == ()

    # The same PIPE on a PRICED PATH branches for the ATM route, so both branch
    # residuals are published: a PIPE still deducts Q / p_start in each (§3.1).
    path_kwargs_branching = path_kwargs(programme=ATM_PROGRAMME)
    piped = evaluate_with_actions(
        [action(PIPE_ROUTE, "pipe", "cash", "600000")], **path_kwargs_branching
    )
    before = evaluate(**path_kwargs_branching)
    both = Fraction(600_000) / P_START
    for branch in c2d.BRANCHES:
        # Derivation: 3,000,000 - 600,000/2 = 2,700,000 shares, in BOTH branches.
        assert residual_pool(piped, NASDAQ_POOL, branch) == Fraction(3_000_000) - both
        assert residual_pool(before, NASDAQ_POOL, branch) == Fraction(3_000_000)
        assert residual_pool(piped, REGISTERED_A, branch) == Fraction(20_000_000)
    assert outside_rows(piped)[PIPE_ROUTE]["shares"] == {
        "pessimistic": fraction_text(both),
        "optimistic": fraction_text(both),
    }
