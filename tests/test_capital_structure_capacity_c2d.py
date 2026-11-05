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
values.  No float literal and no float conversion call appear in this file (§0.17).
"""

from __future__ import annotations

import ast
import hashlib
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
    CapacityInputError,
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
    routes_by_id,
    standard_registration,
    unknown_ids,
    usd,
)
from tests.test_capital_structure_capacity_c2 import (
    ATM_A,
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
    output_blob,
    residual_pool,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "engine" / "capital_structure" / "capacity.py"
THIS_FILE = Path(__file__).resolve()

#: §3: the price in effect at the horizon start of the C2a path fixture, and the
#: window low/high an at-the-market programme (so an equity line) is priced at.
#: Derived from the imported fixture path, never restated as a literal.
P_START = Fraction(PRICE_PATH[0][1])
WINDOW_LOW = min(Fraction(text) for _, text in PRICE_PATH)
WINDOW_HIGH = max(Fraction(text) for _, text in PRICE_PATH)
#: A path whose horizon-start price is $3, so Q / p_start is not a whole number.
THREE_PATH = ((SALE, "3.00"), ("2026-11-14", "4.00"))
#: A path with no point on or before the horizon start (§0.16).
UNCOVERED_PATH = (("2026-11-01", "2.00"), ("2026-11-14", "3.00"))

AUTH_UNKNOWN = f"authorized_share_headroom:{SALE}"

#: The SPEC_C2B §2.3 sentence, verbatim, and the ONE sentence §4.3 appends to it
#: for the two declared kinds only.
C2B_RESOLVES_WITH = (
    "the registration path, pricing date and share or dollar consumption of "
    "{route_id} against each shared pool"
)
C2D_SUFFIX = (
    "; a registered direct or equity line is modelled once "
    f"{ROUTE_REGISTRATION_PATHS_KEY} binds it to a registration path of this envelope"
)


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


def with_declaration(kwargs: dict[str, Any], *bindings: tuple[str, str]) -> dict[str, Any]:
    """The same fixture kwargs plus one ``route_registration_paths`` declaration.

    Threaded through ``other_assumptions`` exactly as ``route_exclusivity`` is
    (§7), so the route-to-path binding stays a SCENARIO ASSUMPTION and never an
    observed fact (masterplan §4).
    """
    out = dict(kwargs)
    text = ";".join(f"{route_id}={path_id}" for route_id, path_id in bindings)
    out["other"] = tuple(out.get("other") or ()) + ((ROUTE_REGISTRATION_PATHS_KEY, text),)
    return out


def outside_rows(evaluation: Any) -> dict[str, dict[str, Any]]:
    """``inputs["outside_consumption"]`` by route id (§5)."""
    return {row["route_id"]: row for row in evaluation.inputs["outside_consumption"]}


def residual_text(evaluation: Any, pool_id: str, branch: str = "pessimistic") -> str | None:
    """The pool residual exactly as published: ``None`` when the bound is unknown.

    ``residual_pool`` refuses an undecided pool by construction, so the fixtures
    whose bound is unknown (C2c-A ``ceiling_only``, an uncovered price path, an
    unknown effectiveness) are compared as the published text instead.
    """
    rows = dict(evaluation.inputs["remaining_capacity"][branch]["pools"])
    assert pool_id in rows, rows
    return rows[pool_id]


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
    # (c) a declaration for a RECORDED-ONLY action still publishes nothing: the
    # candidate gate is `fixed`, so §6 keeps both new keys absent and the output
    # byte-identical to the same declared scenario with the C2d path switched off.
    declared_recorded = with_declaration(kwargs, (DIRECT_ROUTE, PATH_A))
    declared_build = evaluate_with_actions(recorded, **declared_recorded)
    no_outside_views(declared_build)
    assert_identical(
        base_build(monkeypatch, lambda: evaluate_with_actions(recorded, **declared_recorded)),
        declared_build,
        "recorded-only with a declaration",
    )
    assert [ROUTE_REGISTRATION_PATHS_KEY, f"{DIRECT_ROUTE}={PATH_A}"] in [
        list(item) for item in declared_build.inputs["scenario_assumptions"]
    ]
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


# ---------------------------------------------------------------------------
# §0 item 3 -- a declared registered direct consumes its own path's pools
# ---------------------------------------------------------------------------


def test_c2d_registered_direct_consumes_declared_path_pools() -> None:
    """§0.3: every pool the declared path's takedown shares is reduced once."""
    # Derivation (§3.1/§3.3): Q = 1,000,000 usd declared on PATH_A -> each dollar
    # pool that takedown shares loses Q, and the Nasdaq share pool loses
    # Q * coefficient_for(shelf_takedown:PATH_A) = 1,000,000 / p_start = 500,000.
    # PATH_B's pool shares no route with the declaration, so it does not move.
    quantity = Fraction(1_000_000)
    kwargs = a21_kwargs(outstanding="30000005")
    baseline = evaluate(**kwargs)
    evaluation = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")],
        **with_declaration(kwargs, (DIRECT_ROUTE, PATH_A)),
    )
    coefficient = Fraction(evaluation.inputs["nasdaq"]["coefficient"])
    assert coefficient == Fraction(1) / P_START
    assert residual_pool(evaluation, BABY_POOL) == Fraction(10_000_000) - quantity
    assert residual_pool(evaluation, REGISTERED_A) == Fraction(8_000_000) - quantity
    assert residual_pool(evaluation, NASDAQ_POOL) == Fraction(6_000_000) - quantity * coefficient
    assert residual_pool(evaluation, REGISTERED_B) == residual_pool(baseline, REGISTERED_B)
    row = outside_rows(evaluation)[DIRECT_ROUTE]
    assert row["path_id"] == PATH_A
    assert row["pools"] == [BABY_POOL, NASDAQ_POOL, REGISTERED_A]
    assert row["usd"] == {"pessimistic": "1000000", "optimistic": "1000000"}
    assert row["shares"] == {
        branch: fraction_text(quantity * coefficient) for branch in c2d.BRANCHES
    }
    envelope = evaluation.envelope
    assert "unmodelled_consumption" not in evaluation.inputs
    assert envelope.aggregate_bound.status == "known"
    assert money(envelope.aggregate_bound) == Decimal("9000000.00")
    assert money(envelope.aggregate_bound) < money(baseline.envelope.aggregate_bound)
    assert envelope.feasible_witness is not None
    assert C2.witness_of(evaluation) == {
        TAKE_A: Decimal("7000000.00"),
        TAKE_B: Decimal("2000000.00"),
    }
    # On a PRICED PATH both branch residuals are published, and a registered
    # direct prices at p_start in each: the deduction is the same in both.
    branching = path_kwargs(programme=ATM_PROGRAMME)
    before = evaluate(**branching)
    both = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "600000")],
        **with_declaration(branching, (DIRECT_ROUTE, PATH_A)),
    )
    for branch in c2d.BRANCHES:
        assert residual_pool(both, NASDAQ_POOL, branch) == Fraction(
            3_000_000
        ) - Fraction(600_000) / P_START
        assert residual_pool(both, REGISTERED_A, branch) == Fraction(20_000_000) - Fraction(600_000)
        assert residual_pool(before, NASDAQ_POOL, branch) == Fraction(3_000_000)


# ---------------------------------------------------------------------------
# §0 item 4 -- an equity line prices exactly like an at-the-market programme
# ---------------------------------------------------------------------------


def test_c2d_equity_line_prices_like_an_atm() -> None:
    """§0.4: Rule 415(a)(4) at-the-market pricing, window low then window high."""
    # Derivation (§3.1): on a priced path Q = 600,000 usd costs Q / low = 300,000
    # shares pessimistically and Q / high = 200,000 optimistically, while each
    # dollar pool the path's takedown shares loses Q in BOTH branches.
    quantity = Fraction(600_000)
    branching = path_kwargs(programme=ATM_PROGRAMME)
    evaluation = evaluate_with_actions(
        [action(EQUITY_LINE_ROUTE, "equity_line", "cash", "600000")],
        **with_declaration(branching, (EQUITY_LINE_ROUTE, PATH_A)),
    )
    row = outside_rows(evaluation)[EQUITY_LINE_ROUTE]
    assert row["shares"] == {
        "pessimistic": fraction_text(quantity / WINDOW_LOW),
        "optimistic": fraction_text(quantity / WINDOW_HIGH),
    }
    assert row["usd"] == {"pessimistic": "600000", "optimistic": "600000"}
    assert residual_pool(evaluation, NASDAQ_POOL, "pessimistic") == Fraction(
        3_000_000
    ) - quantity / WINDOW_LOW
    assert residual_pool(evaluation, NASDAQ_POOL, "optimistic") == Fraction(
        3_000_000
    ) - quantity / WINDOW_HIGH
    for branch in c2d.BRANCHES:
        assert residual_pool(evaluation, REGISTERED_A, branch) == Fraction(20_000_000) - quantity
    # The SAME dollars asserted on the envelope's own at-the-market route deduct
    # the SAME shares from the SAME pool in each branch: the pricing is identical.
    atm = evaluate_with_actions([C2.cash(ATM_A, "at_the_market", "600000")], **branching)
    for branch in c2d.BRANCHES:
        assert residual_pool(evaluation, NASDAQ_POOL, branch) == residual_pool(
            atm, NASDAQ_POOL, branch
        )
    # Under FIXED pricing there is no window at all, so both branches use p_start.
    fixed = a21_kwargs(outstanding="30000005")
    unbranched = evaluate_with_actions(
        [action(EQUITY_LINE_ROUTE, "equity_line", "cash", "600000")],
        **with_declaration(fixed, (EQUITY_LINE_ROUTE, PATH_A)),
    )
    assert outside_rows(unbranched)[EQUITY_LINE_ROUTE]["shares"] == {
        branch: fraction_text(quantity / P_START) for branch in c2d.BRANCHES
    }
    assert residual_pool(unbranched, NASDAQ_POOL) == Fraction(6_000_000) - quantity / P_START


# ---------------------------------------------------------------------------
# §0 item 5 -- a shares quantity is exact, in shares and in dollars
# ---------------------------------------------------------------------------


def test_c2d_share_quantity_consumes_shares_exactly() -> None:
    """§0.5: S shares cost S shares of every share pool and S * price(branch) usd."""
    # Derivation (§3.2/§3.3): S = 250,000 shares -> each share pool -250,000 in
    # both branches, and usd = S * p_start = 500,000 (a PIPE never uses a window).
    shares = Fraction(250_000)
    kwargs = base_kwargs(
        extra_shares=capital(authorized="2000000", issued="1000000", reserved="500000")
    )
    evaluation = evaluate_authorized(
        [action(PIPE_ROUTE, "pipe", "cash", "250000", unit="shares")], **kwargs
    )
    row = outside_rows(evaluation)[PIPE_ROUTE]
    assert row["shares"] == {branch: fraction_text(shares) for branch in c2d.BRANCHES}
    dollars = shares * P_START
    assert dollars == Fraction(500_000)
    assert row["usd"] == {branch: "500000" for branch in c2d.BRANCHES}
    for branch in c2d.BRANCHES:
        assert Fraction(row["usd"][branch]) == dollars
    assert residual_pool(evaluation, NASDAQ_POOL) == Fraction(3_000_000) - shares
    assert residual_pool(evaluation, AUTH_POOL) == Fraction(500_000) - shares
    # A shares quantity on an equity line prices per branch: S * low, S * high.
    line_shares = Fraction(100_000)
    branching = path_kwargs(programme=ATM_PROGRAMME)
    line = evaluate_with_actions(
        [action(EQUITY_LINE_ROUTE, "equity_line", "cash", "100000", unit="shares")],
        **with_declaration(branching, (EQUITY_LINE_ROUTE, PATH_A)),
    )
    line_row = outside_rows(line)[EQUITY_LINE_ROUTE]
    assert line_row["shares"] == {
        branch: fraction_text(line_shares) for branch in c2d.BRANCHES
    }
    assert Fraction(line_row["usd"]["pessimistic"]) == line_shares * WINDOW_LOW
    assert Fraction(line_row["usd"]["optimistic"]) == line_shares * WINDOW_HIGH
    for branch in c2d.BRANCHES:
        assert residual_pool(line, NASDAQ_POOL, branch) == Fraction(3_000_000) - line_shares
        assert residual_pool(line, REGISTERED_A, branch) == Fraction(
            20_000_000
        ) - line_shares * (WINDOW_LOW if branch == "pessimistic" else WINDOW_HIGH)
    # Fraction exactness: at p_start = 3 a 1,000,000 usd PIPE costs 1000000/3
    # shares and leaves 3,000,000 - 1000000/3 = 8000000/3 -- never rounded.
    exact_shares = Fraction(1_000_000) / Fraction(3)
    assert exact_shares == Fraction(1_000_000, 3)
    three = evaluate_with_actions(
        [action(PIPE_ROUTE, "pipe", "cash", "1000000")],
        **path_kwargs(path=THREE_PATH, programme=ATM_PROGRAMME),
    )
    assert outside_rows(three)[PIPE_ROUTE]["shares"] == {
        branch: "1000000/3" for branch in c2d.BRANCHES
    }
    for branch in c2d.BRANCHES:
        residual = residual_pool(three, NASDAQ_POOL, branch)
        assert residual == Fraction(3_000_000) - exact_shares
        assert fraction_text(residual) == "8000000/3"


# ---------------------------------------------------------------------------
# §0 item 6 -- an undeclared path keeps the SPEC_C2B §2.3 unknown
# ---------------------------------------------------------------------------


def test_c2d_undeclared_path_stays_unmodelled(monkeypatch: Any) -> None:
    """§0.6: no declaration, no model -- plus the ONE added sentence (§4.3)."""
    kwargs = a21_kwargs(outstanding="30000005")
    for route_id, kind in (
        (DIRECT_ROUTE, "registered_direct"),
        (EQUITY_LINE_ROUTE, "equity_line"),
    ):
        def build(route_id: str = route_id, kind: str = kind) -> Any:
            return evaluate_with_actions([action(route_id, kind, "cash", "1000000")], **kwargs)

        evaluation = build()
        # Nothing is modelled, so the C2d path adds no byte at all (§6).
        assert_identical(base_build(monkeypatch, build), evaluation, kind)
        no_outside_views(evaluation)
        assert evaluation.inputs["unmodelled_consumption"] == [route_id]
        assert "asserted_action_on_ineligible_route" not in "".join(
            evaluation.envelope.blockers
        )
        named = unmodelled_unknown(evaluation, route_id)
        assert named.description == (
            f"{kind} on {route_id} may draw on shared registration and exchange-approval "
            "pools that capacity models only for shelf takedowns and at-the-market programmes"
        )
        # The SPEC_C2B sentence verbatim, then the one appended sentence.
        assert named.resolving_fact == C2B_RESOLVES_WITH.format(route_id=route_id) + C2D_SUFFIX
        assert named.resolving_fact.startswith(C2B_RESOLVES_WITH.format(route_id=route_id))
        assert named.affects == tuple(
            sorted(pool.constraint_id for pool in evaluation.envelope.shared_pools)
        )
        envelope = evaluation.envelope
        assert envelope.aggregate_bound.status == "unknown"
        assert envelope.aggregate_bound.value is None
        assert envelope.feasible_witness is None
        assert envelope.binding_constraints == ()
        assert [pool.status for pool in envelope.shared_pools] == ["unknown"] * len(
            envelope.shared_pools
        )
        for pool_id in sorted(pool.constraint_id for pool in envelope.shared_pools):
            assert residual_pool(evaluation, pool_id) == residual_pool(
                evaluate(**kwargs), pool_id
            )


# ---------------------------------------------------------------------------
# §0 item 7 -- a PIPE has no registration path to declare
# ---------------------------------------------------------------------------


def test_c2d_pipe_with_declared_path_is_input_error() -> None:
    """§0.7: declaring a path for a PIPE is a CapacityInputError."""
    assert OUTSIDE_REGISTERED_KINDS == ("registered_direct", "equity_line")
    assert "pipe" not in OUTSIDE_REGISTERED_KINDS
    kwargs = a21_kwargs(outstanding="30000005")
    with pytest.raises(CapacityInputError) as raised:
        explain_with_actions(
            [action(PIPE_ROUTE, "pipe", "cash", "5000000")],
            **with_declaration(kwargs, (PIPE_ROUTE, PATH_A)),
        )
    assert str(raised.value) == (
        f"{ROUTE_REGISTRATION_PATHS_KEY}: {PIPE_ROUTE!r} is a pipe action; a PIPE is "
        "unregistered, so it has no registration path to declare"
    )


# ---------------------------------------------------------------------------
# §0 item 8 -- every malformed declaration shape is refused by name
# ---------------------------------------------------------------------------


MALFORMED_DECLARATIONS: list[tuple[str, str, str, Any]] = [
    ("no_equals", DIRECT_ROUTE, "registered_direct", f"{DIRECT_ROUTE}"),
    ("empty_route_id", DIRECT_ROUTE, "registered_direct", f"={PATH_A}"),
    ("empty_path_id", DIRECT_ROUTE, "registered_direct", f"{DIRECT_ROUTE}="),
    (
        "repeated_route",
        DIRECT_ROUTE,
        "registered_direct",
        f"{DIRECT_ROUTE}={PATH_A};{DIRECT_ROUTE}={PATH_A}",
    ),
    (
        "route_carries_no_action",
        DIRECT_ROUTE,
        "registered_direct",
        f"registered_direct:ghost-of-this-scenario={PATH_A}",
    ),
    ("envelope_route_declared_here", DIRECT_ROUTE, "registered_direct", f"{TAKE_A}={PATH_A}"),
    ("pipe_declared", PIPE_ROUTE, "pipe", f"{PIPE_ROUTE}={PATH_A}"),
    ("supply_kind_declared", WARRANT_ROUTE, "warrant_exercise", f"{WARRANT_ROUTE}={PATH_A}"),
    (
        "funding_kind_declared",
        C2B.DEBT_ROUTE,
        "debt_draw",
        f"{C2B.DEBT_ROUTE}={PATH_A}",
    ),
    (
        "path_not_of_this_envelope",
        DIRECT_ROUTE,
        "registered_direct",
        f"{DIRECT_ROUTE}=registration-path:cs:not-carried",
    ),
    ("value_is_not_text", DIRECT_ROUTE, "registered_direct", ((DIRECT_ROUTE, PATH_A),)),
    ("path_with_no_route_separator", DIRECT_ROUTE, "registered_direct", f"{DIRECT_ROUTE}:{PATH_A}"),
]


@pytest.mark.parametrize(
    "route_id,kind,value",
    [(item[1], item[2], item[3]) for item in MALFORMED_DECLARATIONS],
    ids=[item[0] for item in MALFORMED_DECLARATIONS],
)
def test_c2d_malformed_declaration_is_input_error(
    route_id: str, kind: str, value: Any
) -> None:
    """§0.8: the declaration grammar mirrors ``route_exclusivity`` and refuses."""
    kwargs = a21_kwargs(outstanding="30000005")
    kwargs["other"] = tuple(NASDAQ_ASSUMPTIONS) + ((ROUTE_REGISTRATION_PATHS_KEY, value),)
    with pytest.raises(CapacityInputError) as raised:
        explain_with_actions([action(route_id, kind, "cash", "1000000")], **kwargs)
    message = str(raised.value)
    assert message.startswith(f"{ROUTE_REGISTRATION_PATHS_KEY}: "), message


def test_c2d_whitespace_only_declaration_models_nothing() -> None:
    """§0.8/§6: an all-whitespace declaration is empty, so nothing is modelled."""
    kwargs = a21_kwargs(outstanding="30000005")
    kwargs["other"] = tuple(NASDAQ_ASSUMPTIONS) + ((ROUTE_REGISTRATION_PATHS_KEY, "  ; ;"),)
    evaluation = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")], **kwargs
    )
    no_outside_views(evaluation)
    assert evaluation.inputs["unmodelled_consumption"] == [DIRECT_ROUTE]
    # A well-formed declaration of TWO routes parses into a sorted tuple, however
    # it was written: ``;`` separates the bindings and whitespace is stripped.
    both = evaluate_with_actions(
        [
            action(DIRECT_ROUTE, "registered_direct", "cash", "1000000"),
            action(EQUITY_LINE_ROUTE, "equity_line", "cash", "300000"),
        ],
        **with_declaration(
            a21_kwargs(outstanding="30000005"),
            (EQUITY_LINE_ROUTE, f" {PATH_A} "),
            (f" {DIRECT_ROUTE} ", PATH_A),
        ),
    )
    assert both.inputs["outside_declared"] == [
        [EQUITY_LINE_ROUTE, PATH_A],
        [DIRECT_ROUTE, PATH_A],
    ]


# ---------------------------------------------------------------------------
# §0 item 9 -- an ineligible declared path blocks and deducts nothing
# ---------------------------------------------------------------------------


def test_c2d_ineligible_declared_path_is_blocker() -> None:
    """§0.9: the existing blocker id, no deduction, and no §2.3 unknown."""
    kwargs = _ineligible_pair()
    baseline = evaluate(**kwargs)
    evaluation = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")],
        **with_declaration(kwargs, (DIRECT_ROUTE, PATH_B)),
    )
    # §4.1: the EXISTING id, and no new blocker vocabulary at all.
    assert evaluation.envelope.blockers == (
        f"asserted_action_on_ineligible_route:{DIRECT_ROUTE}",
    )
    assert "unmodelled_consumption" not in evaluation.inputs
    # §5: a blocked route is not an outside_consumption row.
    no_outside_views(evaluation)
    assert routes_by_id(evaluation)[f"shelf_takedown:{PATH_B}"].status == "ineligible"
    # NO deduction: every residual, the aggregate and the witness are unchanged.
    for pool_id in sorted(pool.constraint_id for pool in baseline.envelope.shared_pools):
        assert residual_pool(evaluation, pool_id) == residual_pool(baseline, pool_id)
    assert money(evaluation.envelope.aggregate_bound) == money(
        baseline.envelope.aggregate_bound
    ) == Decimal("6000000.00")
    assert evaluation.envelope.feasible_witness is not None
    assert C2.witness_of(evaluation) == C2.witness_of(baseline)


# ---------------------------------------------------------------------------
# §0 item 10 -- unknown effectiveness means unknown consumption
# ---------------------------------------------------------------------------


def test_c2d_unknown_path_effectiveness_stays_unmodelled() -> None:
    """§0.10: a declared path whose effectiveness is unknown is not modelled."""
    kwargs = _single(effect="not_observed")
    baseline = evaluate(**kwargs)
    assert f"registration_effectiveness:{PATH_A}" in unknown_ids(baseline)
    evaluation = evaluate_with_actions(
        [action(EQUITY_LINE_ROUTE, "equity_line", "cash", "1000000")],
        **with_declaration(kwargs, (EQUITY_LINE_ROUTE, PATH_A)),
    )
    assert evaluation.inputs["unmodelled_consumption"] == [EQUITY_LINE_ROUTE]
    no_outside_views(evaluation)
    named = unmodelled_unknown(evaluation, EQUITY_LINE_ROUTE)
    assert named.resolving_fact == (
        C2B_RESOLVES_WITH.format(route_id=EQUITY_LINE_ROUTE) + C2D_SUFFIX
    )
    assert f"registration_effectiveness:{PATH_A}" in unknown_ids(evaluation)
    assert evaluation.envelope.feasible_witness is None
    assert evaluation.envelope.aggregate_bound.status == "unknown"
    assert evaluation.inputs["remaining_capacity"] == baseline.inputs["remaining_capacity"]


# ---------------------------------------------------------------------------
# §0 item 11 -- a non-cash settlement stays unmodelled, text verbatim
# ---------------------------------------------------------------------------


def test_c2d_non_cash_outside_action_stays_unmodelled(monkeypatch: Any) -> None:
    """§0.11: only ``cash`` is modelled; every other settlement is unchanged."""
    kwargs = a21_kwargs(outstanding="30000005")
    baseline = evaluate(**kwargs)
    for route_id, kind, settlement in (
        (DIRECT_ROUTE, "registered_direct", "physical"),
        (EQUITY_LINE_ROUTE, "equity_line", "net_share"),
        (PIPE_ROUTE, "pipe", "physical"),
        (DIRECT_ROUTE, "registered_direct", "cashless"),
    ):
        def build(
            route_id: str = route_id, kind: str = kind, settlement: str = settlement
        ) -> Any:
            return evaluate_with_actions(
                [action(route_id, kind, settlement, "1000000")], **kwargs
            )

        evaluation = build()
        assert_identical(base_build(monkeypatch, build), evaluation, f"{kind}/{settlement}")
        no_outside_views(evaluation)
        assert evaluation.inputs["unmodelled_consumption"] == [route_id]
        named = unmodelled_unknown(evaluation, route_id)
        # §4.3: a non-cash action keeps the SPEC_C2B sentence VERBATIM, even for
        # the two registered kinds -- the appended sentence is for cash only.
        assert named.resolving_fact == C2B_RESOLVES_WITH.format(route_id=route_id)
        assert C2D_SUFFIX.strip("; ") not in named.resolving_fact
        assert evaluation.envelope.feasible_witness is None
        assert evaluation.envelope.aggregate_bound.status == "unknown"
        for pool_id in sorted(pool.constraint_id for pool in baseline.envelope.shared_pools):
            assert residual_pool(evaluation, pool_id) == residual_pool(baseline, pool_id)
    # A recorded-only outside action is inert too (§0.1), whatever its settlement.
    recorded = evaluate_with_actions(
        [action(EQUITY_LINE_ROUTE, "equity_line", "physical", None)], **kwargs
    )
    no_outside_views(recorded)
    assert "unmodelled_consumption" not in recorded.inputs


# ---------------------------------------------------------------------------
# §0 item 12 -- an outside deduction over a ceiling or a bound is infeasible
# ---------------------------------------------------------------------------


def test_c2d_outside_deduction_over_ceiling_is_infeasible() -> None:
    """§0.12: over a ``ceiling_only`` substitute, the existing over_ceiling path."""
    # Derivation (§3.3 + C2c-A §8): a 3,000,000 usd PIPE costs 3,000,000 / 2 =
    # 1,500,000 shares, above the authorized pool's 1,000,000-share substitute
    # (2,000,000 authorized less 1,000,000 issued), whose bound itself is unknown.
    kwargs = base_kwargs(extra_shares=capital(authorized="2000000", issued="1000000"))
    baseline = evaluate(**kwargs)
    assert baseline.envelope.aggregate_bound.status == "unknown"
    assert AUTH_UNKNOWN in unknown_ids(baseline)
    evaluation = evaluate_authorized(
        [action(PIPE_ROUTE, "pipe", "cash", "3000000")], **kwargs
    )
    shares = Fraction(3_000_000) / P_START
    assert shares == Fraction(1_500_000)
    assert shares > Fraction(1_000_000)
    # The unknown bound stays unknown -- nothing is deducted from it, and the
    # substitute is what the deduction exceeded.
    assert residual_text(evaluation, AUTH_POOL) is None
    assert AUTH_POOL in evaluation.envelope.unknown_constraints
    assert residual_pool(evaluation, NASDAQ_POOL) == Fraction(3_000_000) - shares
    assert evaluation.envelope.blockers == (
        f"asserted_actions_infeasible:{AUTH_POOL}",
    )
    assert evaluation.envelope.aggregate_bound.status == "contradicted"
    assert evaluation.envelope.aggregate_bound.value is None
    assert AUTH_POOL in evaluation.envelope.aggregate_bound.note
    assert evaluation.envelope.feasible_witness == ()
    assert AUTH_UNKNOWN in unknown_ids(evaluation)


def test_c2d_outside_deduction_over_known_bound_contradicts() -> None:
    """§0.12: over a KNOWN bound the residual goes negative, exactly as for a route."""
    # Derivation (§3.3): a 1,200,000 usd PIPE costs 600,000 shares against the
    # authorized pool's known 500,000-share headroom -> residual -100,000.
    kwargs = base_kwargs(
        extra_shares=capital(authorized="2000000", issued="1000000", reserved="500000")
    )
    outside = evaluate_authorized(
        [action(PIPE_ROUTE, "pipe", "cash", "1200000")], **kwargs
    )
    assert residual_pool(outside, AUTH_POOL) == Fraction(500_000) - Fraction(600_000)
    assert residual_pool(outside, AUTH_POOL) == Fraction(-100_000)
    assert outside.envelope.blockers == (f"asserted_actions_infeasible:{AUTH_POOL}",)
    assert outside.envelope.aggregate_bound.status == "contradicted"
    # The SAME dollars asserted on an envelope route contradict identically: the
    # outside deduction travels the existing negative-residual path and no other.
    envelope = evaluate_authorized(
        [C2.cash(TAKE_A, "shelf_takedown", "1200000")], **kwargs
    )
    assert residual_pool(envelope, AUTH_POOL) == residual_pool(outside, AUTH_POOL)
    assert envelope.envelope.blockers == outside.envelope.blockers
    assert envelope.envelope.aggregate_bound.status == "contradicted"
    assert envelope.envelope.aggregate_bound.note == outside.envelope.aggregate_bound.note


# ---------------------------------------------------------------------------
# §0 item 13 -- the conditions name the scenario declaration, and nothing else
# ---------------------------------------------------------------------------


def test_c2d_conditions_name_the_scenario_declaration() -> None:
    """§0.13: §4.2 conditions on the declared path's row, and nowhere else."""
    kwargs = a21_kwargs(outstanding="30000005")
    baseline = evaluate(**kwargs)
    direct_condition = f"registered_direct_path_declared_by_scenario:{DIRECT_ROUTE}"
    line_conditions = (
        f"equity_line_concurrent_resale_registration_not_evaluated:{EQUITY_LINE_ROUTE}",
        f"equity_line_path_declared_by_scenario:{EQUITY_LINE_ROUTE}",
    )
    evaluation = evaluate_with_actions(
        [
            action(PIPE_ROUTE, "pipe", "cash", "500000"),
            action(DIRECT_ROUTE, "registered_direct", "cash", "1000000"),
            action(EQUITY_LINE_ROUTE, "equity_line", "cash", "300000"),
        ],
        **with_declaration(
            kwargs, (DIRECT_ROUTE, PATH_A), (EQUITY_LINE_ROUTE, PATH_A)
        ),
    )
    rows = outside_rows(evaluation)
    assert rows[DIRECT_ROUTE]["conditions_assumed_met"] == [direct_condition]
    assert rows[EQUITY_LINE_ROUTE]["conditions_assumed_met"] == list(line_conditions)
    # A PIPE adds NO condition: the Nasdaq pool already carries the aggregation note.
    assert rows[PIPE_ROUTE]["conditions_assumed_met"] == []
    assert any(
        condition.startswith("nasdaq_aggregation_of_related_transactions_not_evaluated")
        or condition == "nasdaq_aggregation_of_related_transactions_not_evaluated"
        for route in evaluation.envelope.routes
        for condition in route.conditions
    )
    # "and nowhere else": no envelope route gained a condition, and each new
    # string appears exactly once in everything the call publishes.
    assert {route.route_id: route.conditions for route in evaluation.envelope.routes} == {
        route.route_id: route.conditions for route in baseline.envelope.routes
    }
    blob = output_blob(evaluation)
    for condition in (direct_condition, *line_conditions):
        assert blob.count(condition) == 1, condition
    # The declaration itself is an assumption of the scenario, recorded as one.
    assert [ROUTE_REGISTRATION_PATHS_KEY, f"{DIRECT_ROUTE}={PATH_A};{EQUITY_LINE_ROUTE}={PATH_A}"] in [
        list(item) for item in evaluation.inputs["scenario_assumptions"]
    ]


# ---------------------------------------------------------------------------
# §0 item 14 -- inputs["outside_consumption"]
# ---------------------------------------------------------------------------


def test_c2d_inputs_record_outside_consumption() -> None:
    """§0.14: one exact-text row per modelled outside action, sorted by route id."""
    kwargs = a21_kwargs(outstanding="30000005")
    evaluation = evaluate_with_actions(
        [
            action(DIRECT_ROUTE, "registered_direct", "cash", "1000000"),
            action(PIPE_ROUTE, "pipe", "cash", "500000"),
            action(EQUITY_LINE_ROUTE, "equity_line", "cash", "300000"),
        ],
        **with_declaration(
            kwargs, (DIRECT_ROUTE, PATH_A), (EQUITY_LINE_ROUTE, PATH_A)
        ),
    )
    rows = evaluation.inputs["outside_consumption"]
    assert [row["route_id"] for row in rows] == sorted(
        [EQUITY_LINE_ROUTE, PIPE_ROUTE, DIRECT_ROUTE]
    )
    assert list(rows[0]) == [
        "route_id",
        "action",
        "path_id",
        "pools",
        "usd",
        "shares",
        "conditions_assumed_met",
    ]
    assert [row["action"] for row in rows] == [
        "equity_line",
        "pipe",
        "registered_direct",
    ]
    assert [row["path_id"] for row in rows] == [PATH_A, None, PATH_A]
    # Every number is exact TEXT: money as decimal text, shares as fraction text.
    for row in rows:
        assert sorted(row["usd"]) == sorted(c2d.BRANCHES)
        for branch in c2d.BRANCHES:
            assert isinstance(row["usd"][branch], str)
            Fraction(row["usd"][branch])
            assert isinstance(row["shares"][branch], str)
            Fraction(row["shares"][branch])
        assert isinstance(row["pools"], list) and row["pools"] == sorted(row["pools"])
    assert rows[1]["usd"] == {"pessimistic": "500000", "optimistic": "500000"}
    assert rows[1]["shares"] == {
        "pessimistic": "250000/1",
        "optimistic": "250000/1",
    }
    assert evaluation.inputs["outside_declared"] == [
        [EQUITY_LINE_ROUTE, PATH_A],
        [DIRECT_ROUTE, PATH_A],
    ]
    # The gate: with nothing modelled, neither key exists at all (§0.1).
    no_outside_views(evaluate(**kwargs))
    no_outside_views(
        evaluate_with_actions(
            [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")], **kwargs
        )
    )
    # The rows are what the residuals show: the two declared routes take
    # 1,000,000 + 300,000 dollars off each dollar pool the path's takedown shares,
    # and all three take (1,800,000 / p_start) = 900,000 shares off the Nasdaq pool.
    declared_dollars = Fraction(1_000_000) + Fraction(300_000)
    all_dollars = declared_dollars + Fraction(500_000)
    assert residual_pool(evaluation, BABY_POOL) == Fraction(10_000_000) - declared_dollars
    assert residual_pool(evaluation, NASDAQ_POOL) == Fraction(6_000_000) - all_dollars / P_START
    assert residual_pool(evaluation, REGISTERED_A) == Fraction(8_000_000) - declared_dollars
    assert residual_pool(evaluation, REGISTERED_B) == Fraction(7_000_000)


# ---------------------------------------------------------------------------
# §0 item 15 -- outside cash is never added to the aggregate
# ---------------------------------------------------------------------------


def test_c2d_outside_cash_is_not_added_to_the_aggregate() -> None:
    """§0.15: the aggregate is still what the ENVELOPE routes can raise."""
    kwargs = base_kwargs(
        extra_shares=capital(authorized="2000000", issued="1000000", reserved="500000")
    )
    envelope_action = [C2.cash(TAKE_A, "shelf_takedown", "200000")]
    without_outside = evaluate_authorized(envelope_action, **kwargs)
    with_outside = evaluate_authorized(
        [*envelope_action, action(DIRECT_ROUTE, "registered_direct", "cash", "100000")],
        **with_declaration(kwargs, (DIRECT_ROUTE, PATH_A)),
    )
    # fixed_totals carries the ENVELOPE action only: outside cash is not a fixed
    # use of a route this adapter carries.
    assert (
        with_outside.inputs["remaining_capacity"]["pessimistic"]["fixed_total"]
        == without_outside.inputs["remaining_capacity"]["pessimistic"]["fixed_total"]
        == "200000"
    )
    # No witness row for an outside route: it has no limit this adapter may state.
    assert [item.route_id for item in with_outside.envelope.feasible_witness] == [
        item.route_id for item in without_outside.envelope.feasible_witness
    ] == [TAKE_A]
    assert [route.route_id for route in with_outside.envelope.routes] == [
        route.route_id for route in without_outside.envelope.routes
    ]
    # Derivation: the outside 100,000 usd costs 50,000 of the 400,000 charter
    # shares the envelope action left, so the optimum falls 800,000 -> 700,000 and
    # the aggregate is 200,000 + 700,000 = 900,000 -- never 1,000,000, which is
    # what adding the outside cash would state.
    assert Fraction(with_outside.kernel["evidence"]["value"]) == Fraction(700_000)
    assert money(with_outside.envelope.aggregate_bound) == Decimal("900000.00")
    assert money(with_outside.envelope.aggregate_bound) == Decimal(
        with_outside.inputs["remaining_capacity"]["pessimistic"]["fixed_total"]
    ) + Decimal(with_outside.kernel["evidence"]["value"].split("/")[0]) / Decimal(
        with_outside.kernel["evidence"]["value"].split("/")[1]
    )
    assert money(with_outside.envelope.aggregate_bound) != Decimal("1000000.00")
    assert money(with_outside.envelope.aggregate_bound) < money(
        without_outside.envelope.aggregate_bound
    )
    assert residual_pool(with_outside, AUTH_POOL) == Fraction(400_000) - Fraction(50_000)
    assert residual_pool(without_outside, AUTH_POOL) == Fraction(400_000)
    # The outside cash IS reported, in inputs only.
    assert outside_rows(with_outside)[DIRECT_ROUTE]["usd"] == {
        "pessimistic": "100000",
        "optimistic": "100000",
    }


# ---------------------------------------------------------------------------
# §0 item 16 -- an uncovered price path
# ---------------------------------------------------------------------------


def test_c2d_uncovered_price_path_outside_action() -> None:
    """§0.16: no price in effect -> no share deduction, and a shares quantity refuses."""
    kwargs = path_kwargs(path=UNCOVERED_PATH)
    baseline = evaluate(**kwargs)
    assert f"price_path_uncovered:{SALE}" in unknown_ids(baseline)
    # A usd PIPE is modelled, but nothing is deducted from the undecided share
    # pool: its bound is unknown with no substitute, so there is nothing to deduct.
    evaluation = evaluate_with_actions(
        [action(PIPE_ROUTE, "pipe", "cash", "1000000")], **kwargs
    )
    row = outside_rows(evaluation)[PIPE_ROUTE]
    assert row["pools"] == [NASDAQ_POOL]
    assert row["shares"] is None
    assert row["usd"] == {"pessimistic": "1000000", "optimistic": "1000000"}
    assert residual_text(evaluation, NASDAQ_POOL) is None
    assert residual_text(evaluation, NASDAQ_POOL) == residual_text(baseline, NASDAQ_POOL)
    assert residual_pool(evaluation, REGISTERED_A) == residual_pool(baseline, REGISTERED_A)
    assert Fraction(evaluation.kernel["evidence"]["floor_when_unknowns_zero"]) == Fraction(0)
    # A declared registered direct still deducts its DOLLAR pools exactly.
    declared_kwargs = with_declaration(kwargs, (DIRECT_ROUTE, PATH_A))
    direct = evaluate_with_actions(
        [action(DIRECT_ROUTE, "registered_direct", "cash", "1000000")], **declared_kwargs
    )
    direct_row = outside_rows(direct)[DIRECT_ROUTE]
    assert direct_row["shares"] is None
    assert residual_text(direct, NASDAQ_POOL) is None
    assert residual_pool(direct, REGISTERED_A) == Fraction(20_000_000) - Fraction(1_000_000)
    # A shares quantity needs a price, and refuses in _action_price's wording.
    for route_id, kind, label in (
        (PIPE_ROUTE, "pipe", "the price in effect at the horizon start"),
        (DIRECT_ROUTE, "registered_direct", "the price in effect at the horizon start"),
    ):
        target = kwargs if kind == "pipe" else declared_kwargs
        with pytest.raises(CapacityInputError) as raised:
            explain_with_actions(
                [action(route_id, kind, "cash", "100", unit="shares")], **target
            )
        assert str(raised.value) == (
            f"a share quantity on {route_id} needs {label}, and the price path carries no "
            f"price in effect on or before the horizon start {SALE}"
        )


# ---------------------------------------------------------------------------
# §0 item 17 -- exact arithmetic only
# ---------------------------------------------------------------------------


def test_c2d_no_float_in_the_adapter_or_this_file() -> None:
    """§0.17: no float literal and no float conversion call in either owned file."""

    def offenders(path: Path) -> list[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                found.append(f"{path.name}:{node.lineno}: a float literal")
            if isinstance(node, ast.Call):
                name = node.func
                if isinstance(name, ast.Name) and name.id == "float":
                    found.append(f"{path.name}:{node.lineno}: a float conversion call")
        return found

    assert offenders(ADAPTER) == []
    assert offenders(THIS_FILE) == []


# ---------------------------------------------------------------------------
# §8 -- the untouched digest path is still reachable, and still untouched
# ---------------------------------------------------------------------------


def test_c2d_long_undeclared_route_id_keeps_the_digest_unknown_id() -> None:
    """§8: a 195-character undeclared route id still gets the digest unknown id."""
    long_route = "registered_direct:" + "x" * 177
    assert len(f"action_route_not_modelled:{long_route}") > 200
    kwargs = a21_kwargs(outstanding="30000005")
    evaluation = evaluate_with_actions(
        [action(long_route, "registered_direct", "cash", "5000000")], **kwargs
    )
    digest = hashlib.sha256(long_route.encode("utf-8")).hexdigest()[:16]
    named = {item.unknown_id: item for item in evaluation.envelope.unknowns}
    assert f"action_route_not_modelled:{digest}" in named, sorted(named)
    assert long_route in named[f"action_route_not_modelled:{digest}"].description
    # The added sentence is appended to the digest-id unknown too, and only there.
    assert named[f"action_route_not_modelled:{digest}"].resolving_fact == (
        C2B_RESOLVES_WITH.format(route_id=long_route) + C2D_SUFFIX
    )
    assert evaluation.inputs["unmodelled_consumption"] == [long_route]
    no_outside_views(evaluation)
