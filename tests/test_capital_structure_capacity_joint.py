"""Joint financing-constraint kernel (masterplan §5; A20, A21, A22, A48)."""

from __future__ import annotations

import random
from decimal import Decimal
from fractions import Fraction
from itertools import combinations

import pytest

from engine.capital_structure.capacity_joint import (
    JointModelError,
    JointPool,
    JointRoute,
    decimal_floor,
    exact,
    solve_joint,
)
from engine.capital_structure.issuer_state_contracts import FORBIDDEN_PROPERTY_PATTERN

M = 1_000_000


def _witness(solution):
    return dict(solution.witness)


def test_worked_example_shared_pool_gives_joint_ten_not_fifteen():
    solution = solve_joint(
        [JointRoute("a", 8 * M), JointRoute("b", 7 * M)],
        [JointPool("pool", {"a": 1, "b": 1}, 10 * M)],
    )
    assert solution.determined
    assert solution.value == 10 * M
    assert _witness(solution) == {"a": 8 * M, "b": 2 * M}
    assert solution.binding == ("pool",)
    assert solution.slack == ()


def test_share_pool_at_fixed_price_binds_below_the_dollar_pool():
    price = Fraction(2)
    solution = solve_joint(
        [JointRoute("a", 8 * M), JointRoute("b", 7 * M)],
        [
            JointPool("dollars", {"a": 1, "b": 1}, 10 * M),
            JointPool("shares", {"a": 1 / price, "b": 1 / price}, 3 * M),
        ],
    )
    assert solution.value == 6 * M
    assert solution.binding == ("shares",)
    assert solution.slack == ("dollars",)


def test_unknown_share_count_is_indeterminate_never_zero_or_unlimited():
    solution = solve_joint(
        [JointRoute("a", 8 * M), JointRoute("b", 7 * M)],
        [
            JointPool("dollars", {"a": 1, "b": 1}, 10 * M),
            JointPool("shares", {"a": Fraction(1, 2), "b": Fraction(1, 2)}, None),
        ],
    )
    assert not solution.determined
    assert solution.value is None and solution.witness is None
    assert solution.unknown_pools == ("shares",)
    assert solution.floor_when_unknowns_zero == 0
    assert solution.ceiling_when_unknowns_relaxed == 10 * M
    record = solution.as_record()
    assert record["value"] is None and record["determined"] is False


def test_unknown_route_limit_gives_a_safe_floor_and_an_open_ceiling():
    solution = solve_joint(
        [JointRoute("a", 4 * M), JointRoute("b", None)],
        [JointPool("pool", {"a": 1}, 3 * M)],
    )
    assert not solution.determined
    assert solution.unknown_routes == ("b",)
    assert solution.floor_when_unknowns_zero == 3 * M
    assert dict(solution.floor_witness) == {"a": 3 * M, "b": 0}
    assert solution.ceiling_when_unknowns_relaxed is None


def test_tight_pool_that_does_not_bind_is_slack():
    solution = solve_joint([JointRoute("a", 5)], [JointPool("pool", {"a": 1}, 5)])
    assert solution.value == 5
    assert solution.binding == ()
    assert solution.slack == ("pool",)


def test_mutually_exclusive_routes_branch_instead_of_summing():
    solution = solve_joint(
        [JointRoute("a", 8), JointRoute("b", 7), JointRoute("c", 5)],
        exclusive=[("b", "a")],
    )
    assert solution.value == 13
    assert _witness(solution) == {"a": 8, "b": 0, "c": 5}
    assert solution.allowed_exclusive == ("a",)
    assert solution.branches_evaluated == 2


def test_preference_orders_the_witness_but_never_the_value():
    routes = [JointRoute("a", 8), JointRoute("b", 7)]
    pools = [JointPool("pool", {"a": 1, "b": 1}, 10)]
    default = solve_joint(routes, pools)
    preferred = solve_joint(routes, pools, preference=["b"])
    assert default.value == preferred.value == 10
    assert _witness(preferred) == {"a": 3, "b": 7}


def test_degenerate_zero_headroom_terminates_and_binds():
    solution = solve_joint(
        [JointRoute("a", 3), JointRoute("b", 3), JointRoute("c", 3)],
        [
            JointPool("p1", {"a": 1, "b": 1}, 0),
            JointPool("p2", {"b": 1, "c": 1}, 0),
            JointPool("p3", {"a": 1, "c": 1}, 2),
        ],
    )
    assert solution.value == 0
    assert set(solution.binding) == {"p1", "p2"}


@pytest.mark.parametrize("value", [1.5, True, float("nan")])
def test_floats_and_booleans_are_refused(value):
    with pytest.raises(JointModelError):
        exact(value, "x")


def test_negative_headroom_and_unknown_references_are_refused():
    with pytest.raises(JointModelError):
        JointPool("pool", {"a": 1}, -1)
    with pytest.raises(JointModelError):
        JointPool("pool", {"a": 0}, 1)
    with pytest.raises(JointModelError):
        solve_joint([JointRoute("a", 1)], [JointPool("pool", {"b": 1}, 1)])
    with pytest.raises(JointModelError):
        solve_joint([JointRoute("a", 1), JointRoute("a", 2)])
    with pytest.raises(JointModelError):
        solve_joint([JointRoute("a", 1)], exclusive=[("a",)])


def test_decimal_inputs_and_conservative_rounding():
    solution = solve_joint([JointRoute("a", Decimal("10.005"))], [JointPool("pool", {"a": "3"}, "10")])
    assert solution.value == Fraction(10, 3)
    assert decimal_floor(solution.value) == Decimal("3.33")


def test_record_carries_no_forbidden_property():
    record = solve_joint([JointRoute("a", 1)], [JointPool("pool", {"a": 1}, 1)]).as_record()
    assert not [key for key in record if FORBIDDEN_PROPERTY_PATTERN.search(key)]


# --- independent oracle: vertex enumeration over small instances ---------------------


def _solve_square(matrix, rhs):
    size = len(matrix)
    rows = [list(row) + [value] for row, value in zip(matrix, rhs)]
    for column in range(size):
        pivot = next((r for r in range(column, size) if rows[r][column] != 0), None)
        if pivot is None:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for r in range(size):
            if r != column and rows[r][column] != 0:
                factor = rows[r][column] / rows[column][column]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[column])]
    return [rows[r][size] / rows[r][r] for r in range(size)]


def _oracle(limits, pools):
    """Max of sum(x) by enumerating every vertex of the polytope."""
    n = len(limits)
    constraints = []
    for i, limit in enumerate(limits):
        row = [Fraction(0)] * n
        row[i] = Fraction(1)
        constraints.append((row, limit))
    for uses, bound in pools:
        constraints.append(([Fraction(uses.get(i, 0)) for i in range(n)], bound))
    for i in range(n):
        row = [Fraction(0)] * n
        row[i] = Fraction(-1)
        constraints.append((row, Fraction(0)))
    best = None
    for chosen in combinations(constraints, n):
        point = _solve_square([c[0] for c in chosen], [c[1] for c in chosen])
        if point is None:
            continue
        if all(sum(a * x for a, x in zip(row, point)) <= bound for row, bound in constraints):
            total = sum(point)
            best = total if best is None or total > best else best
    return best


def _random_instance(rng):
    n = rng.randint(1, 3)
    limits = [Fraction(rng.randint(0, 12)) for _ in range(n)]
    pools = []
    for _ in range(rng.randint(0, 3)):
        members = [i for i in range(n) if rng.random() < 0.7] or [0]
        uses = {i: Fraction(rng.randint(1, 4), rng.randint(1, 3)) for i in members}
        pools.append((uses, Fraction(rng.randint(0, 15))))
    return limits, pools


def _build(limits, pools, names):
    routes = [JointRoute(names[i], limit) for i, limit in enumerate(limits)]
    joint = [JointPool(f"p{k}", {names[i]: c for i, c in uses.items()}, bound) for k, (uses, bound) in enumerate(pools)]
    return routes, joint


def test_simplex_matches_vertex_enumeration_on_random_instances():
    rng = random.Random(20261014)
    for _ in range(300):
        limits, pools = _random_instance(rng)
        names = [f"r{i}" for i in range(len(limits))]
        solution = solve_joint(*_build(limits, pools, names))
        assert solution.value == _oracle(limits, pools)
        witness = _witness(solution)
        assert sum(witness.values()) == solution.value
        for i, limit in enumerate(limits):
            assert 0 <= witness[names[i]] <= limit
        for uses, bound in pools:
            assert sum(c * witness[names[i]] for i, c in uses.items()) <= bound


def test_tighter_constraint_never_raises_and_order_and_scale_are_invariant():
    rng = random.Random(7)
    for _ in range(150):
        limits, pools = _random_instance(rng)
        names = [f"r{i}" for i in range(len(limits))]
        base = solve_joint(*_build(limits, pools, names))
        extra_uses = {i: Fraction(1) for i in range(len(limits)) if rng.random() < 0.6} or {0: Fraction(1)}
        tighter = solve_joint(*_build(limits, pools + [(extra_uses, Fraction(rng.randint(0, 10)))], names))
        assert tighter.value <= base.value
        routes, joint = _build(limits, pools, names)
        shuffled = solve_joint(list(reversed(routes)), list(reversed(joint)))
        assert shuffled.value == base.value and shuffled.witness == base.witness
        assert shuffled.binding == base.binding
        k = Fraction(rng.randint(2, 9), rng.randint(1, 4))
        scaled = solve_joint(*_build([limit * k for limit in limits], [(uses, bound * k) for uses, bound in pools], names))
        assert scaled.value == base.value * k
        assert dict(scaled.witness) == {name: amount * k for name, amount in base.witness}
        assert scaled.binding == base.binding


def test_shared_pool_maxima_are_never_summed():
    rng = random.Random(11)
    for _ in range(150):
        limits, pools = _random_instance(rng)
        names = [f"r{i}" for i in range(len(limits))]
        solution = solve_joint(*_build(limits, pools, names))
        assert solution.value <= sum(limits)
        if solution.binding:
            assert solution.value < sum(limits)
