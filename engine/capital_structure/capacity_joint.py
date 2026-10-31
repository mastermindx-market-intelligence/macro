"""Exact joint feasibility kernel for shared financing constraints (masterplan §5).

Route-use quantities are nonnegative and share one unit.  Each route may carry
its own limit; shared pools are linear rows ``sum(coefficient * use) <= bound``
with positive coefficients; mutually exclusive groups allow at most one route of
the group to be used, and are handled by enumerating branches rather than by an
integer program.  The kernel maximizes total use and returns:

* the exact optimum and a canonical witness (the lexicographic maximum of total
  use, then of each route's use in the stated preference order), so the
  witness never depends on input order;
* which shared pools are binding (removing the pool strictly raises the
  optimum) and which are slack;
* when a relevant limit or pool bound is unknown, no optimum at all, only an
  explicit bracket: the floor with every unknown at zero (with a witness that is
  feasible for every nonnegative value of the unknowns) and the ceiling with
  every unknown relaxed (``None`` when nothing else bounds it).

Arithmetic is exact (``Fraction``); floats are refused.  Shared-pool maxima are
never summed (A21), unknowns are never zero or unlimited (A20), a tighter
constraint never raises the optimum and neither input order nor a common
rescaling changes the answer beyond scaling it (A22).  No score, rank or sizing
is produced (A48).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from fractions import Fraction
from itertools import product
from typing import Any, Iterable, Mapping, Sequence

MAX_BRANCHES = 4096
IMPLEMENTATION = "capital_structure.capacity_joint.lexicographic_simplex.v1"


class JointModelError(ValueError):
    """Malformed joint-model input."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise JointModelError(message)


def exact(value: Any, name: str) -> Fraction:
    """Exact rational from an int, Decimal, Fraction or decimal string; floats are refused."""
    _require(not isinstance(value, (bool, float)), f"{name}: exact value required, got {type(value).__name__}")
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    if isinstance(value, Decimal):
        _require(value.is_finite(), f"{name}: finite value required")
        return Fraction(value)
    if isinstance(value, str):
        try:
            parsed = Decimal(value)
        except ArithmeticError as error:
            raise JointModelError(f"{name}: {value!r} is not a decimal") from error
        _require(parsed.is_finite(), f"{name}: finite value required")
        return Fraction(parsed)
    raise JointModelError(f"{name}: unsupported type {type(value).__name__}")


def decimal_floor(value: Fraction, places: int = 2) -> Decimal:
    """Round toward zero to ``places`` decimals; conservative for packing rows."""
    _require(value >= 0, "decimal_floor: nonnegative value required")
    scale = 10**places
    whole = (value.numerator * scale) // value.denominator
    return (Decimal(whole) / Decimal(scale)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_DOWN)


@dataclass(frozen=True)
class JointRoute:
    """One route's use variable; ``limit`` is ``None`` when it is not known."""

    route_id: str
    limit: Fraction | None = None

    def __post_init__(self) -> None:
        _require(isinstance(self.route_id, str) and bool(self.route_id), "route_id required")
        if self.limit is not None:
            limit = exact(self.limit, f"route[{self.route_id}].limit")
            _require(limit >= 0, f"route[{self.route_id}].limit is negative")
            object.__setattr__(self, "limit", limit)


@dataclass(frozen=True)
class JointPool:
    """A shared linear row; ``bound`` is ``None`` when it is not known."""

    pool_id: str
    uses: tuple[tuple[str, Fraction], ...]
    bound: Fraction | None = None

    def __post_init__(self) -> None:
        _require(isinstance(self.pool_id, str) and bool(self.pool_id), "pool_id required")
        if self.bound is not None:
            bound = exact(self.bound, f"pool[{self.pool_id}].bound")
            _require(bound >= 0, f"pool[{self.pool_id}].bound is negative; pass remaining headroom, never an overrun")
            object.__setattr__(self, "bound", bound)
        uses = dict(self.uses.items() if isinstance(self.uses, Mapping) else self.uses)
        _require(len(uses) == len(tuple(self.uses.items() if isinstance(self.uses, Mapping) else self.uses)), f"pool[{self.pool_id}] repeats a route")
        normalized = []
        for route_id, coefficient in sorted(uses.items()):
            value = exact(coefficient, f"pool[{self.pool_id}].uses[{route_id}]")
            _require(value > 0, f"pool[{self.pool_id}].uses[{route_id}] must be positive")
            normalized.append((route_id, value))
        object.__setattr__(self, "uses", tuple(normalized))


@dataclass(frozen=True)
class JointSolution:
    determined: bool
    value: Fraction | None
    witness: tuple[tuple[str, Fraction], ...] | None
    binding: tuple[str, ...]
    slack: tuple[str, ...]
    unknown_routes: tuple[str, ...]
    unknown_pools: tuple[str, ...]
    floor_when_unknowns_zero: Fraction
    floor_witness: tuple[tuple[str, Fraction], ...]
    ceiling_when_unknowns_relaxed: Fraction | None
    allowed_exclusive: tuple[str, ...]
    branches_evaluated: int
    blockers: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        def text(value: Fraction | None) -> str | None:
            return None if value is None else f"{value.numerator}/{value.denominator}"

        return {
            "determined": self.determined,
            "value": text(self.value),
            "witness": None if self.witness is None else [[route_id, text(amount)] for route_id, amount in self.witness],
            "binding": list(self.binding),
            "slack": list(self.slack),
            "unknown_routes": list(self.unknown_routes),
            "unknown_pools": list(self.unknown_pools),
            "floor_when_unknowns_zero": text(self.floor_when_unknowns_zero),
            "floor_witness": [[route_id, text(amount)] for route_id, amount in self.floor_witness],
            "ceiling_when_unknowns_relaxed": text(self.ceiling_when_unknowns_relaxed),
            "allowed_exclusive": list(self.allowed_exclusive),
            "branches_evaluated": self.branches_evaluated,
            "blockers": list(self.blockers),
            "implementation": IMPLEMENTATION,
        }


def _lexicographic_simplex(
    count: int,
    rows: Sequence[Sequence[Fraction]],
    rhs: Sequence[Fraction],
    objectives: Sequence[Sequence[Fraction]],
) -> list[Fraction] | None:
    """Lexicographic maximum of ``objectives`` over ``rows @ x <= rhs``, ``x >= 0``.

    ``rhs`` is nonnegative, so the origin is a feasible basis and no phase one
    is needed.  Bland's rule (smallest entering index whose reduced-cost vector
    is lexicographically positive; smallest basic index among ratio ties) is
    valid over the lexicographically ordered field and cannot cycle.  Returns
    ``None`` when the first objective is unbounded.
    """
    height = len(rows)
    width = count + height
    table = [list(row) + [Fraction(int(i == r)) for i in range(height)] for r, row in enumerate(rows)]
    values = list(rhs)
    basis = [count + r for r in range(height)]
    reduced = [list(objective) + [Fraction(0)] * height for objective in objectives]
    while True:
        entering = None
        for column in range(width):
            for row in reduced:
                if row[column] != 0:
                    if row[column] > 0:
                        entering = column
                    break
            if entering is not None:
                break
        if entering is None:
            break
        leaving = None
        best: Fraction | None = None
        for r in range(height):
            pivot = table[r][entering]
            if pivot > 0:
                ratio = values[r] / pivot
                if best is None or ratio < best or (ratio == best and basis[r] < basis[leaving]):
                    best, leaving = ratio, r
        if leaving is None:
            _require(reduced[0][entering] > 0, "joint kernel: unbounded secondary objective on a bounded face")
            return None
        pivot = table[leaving][entering]
        table[leaving] = [entry / pivot for entry in table[leaving]]
        values[leaving] = values[leaving] / pivot
        for r in range(height):
            factor = table[r][entering]
            if r != leaving and factor != 0:
                table[r] = [a - factor * b for a, b in zip(table[r], table[leaving])]
                values[r] = values[r] - factor * values[leaving]
        for row in reduced:
            factor = row[entering]
            if factor != 0:
                row[:] = [a - factor * b for a, b in zip(row, table[leaving])]
        basis[leaving] = entering
    solution = [Fraction(0)] * count
    for r, variable in enumerate(basis):
        if variable < count:
            solution[variable] = values[r]
    return solution


def _solve_branch(
    order: Sequence[str],
    limits: Mapping[str, Fraction | None],
    pools: Sequence[tuple[Fraction, Mapping[str, Fraction]]],
) -> tuple[Fraction, dict[str, Fraction]] | None:
    """Optimum and canonical witness for routes in ``order``; ``None`` limit = no row."""
    index = {route_id: position for position, route_id in enumerate(order)}
    count = len(order)
    if count == 0:
        return Fraction(0), {}
    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    for route_id in order:
        limit = limits[route_id]
        if limit is not None:
            row = [Fraction(0)] * count
            row[index[route_id]] = Fraction(1)
            rows.append(row)
            rhs.append(limit)
    for bound, uses in pools:
        row = [Fraction(0)] * count
        touched = False
        for route_id, coefficient in uses.items():
            if route_id in index:
                row[index[route_id]] = coefficient
                touched = True
        if touched:
            rows.append(row)
            rhs.append(bound)
    objectives = [[Fraction(1)] * count]
    for position in range(count):
        objective = [Fraction(0)] * count
        objective[position] = Fraction(1)
        objectives.append(objective)
    solution = _lexicographic_simplex(count, rows, rhs, objectives)
    if solution is None:
        return None
    return sum(solution, Fraction(0)), dict(zip(order, solution))


def _branches(groups: Sequence[tuple[str, ...]]) -> list[frozenset[str]]:
    """Distinct sets of routes excluded by choosing at most one route per group."""
    seen: dict[frozenset[str], None] = {}
    for choice in product(*groups):
        excluded = frozenset(route_id for group, chosen in zip(groups, choice) for route_id in group if route_id != chosen)
        seen.setdefault(excluded, None)
    return list(seen)


def solve_joint(
    routes: Iterable[JointRoute],
    pools: Iterable[JointPool] = (),
    *,
    exclusive: Iterable[Sequence[str]] = (),
    preference: Sequence[str] | None = None,
) -> JointSolution:
    """Maximize total route use under limits, shared pools and exclusive groups."""
    route_list = list(routes)
    for route in route_list:
        _require(isinstance(route, JointRoute), "routes: JointRoute required")
    route_ids = [route.route_id for route in route_list]
    _require(len(set(route_ids)) == len(route_ids), "routes: duplicate route_id")
    known_routes = set(route_ids)
    pool_list = sorted(pools, key=lambda pool: pool.pool_id)
    for pool in pool_list:
        _require(isinstance(pool, JointPool), "pools: JointPool required")
        for route_id, _ in pool.uses:
            _require(route_id in known_routes, f"pool[{pool.pool_id}] uses unknown route {route_id!r}")
    pool_ids = [pool.pool_id for pool in pool_list]
    _require(len(set(pool_ids)) == len(pool_ids), "pools: duplicate pool_id")
    groups = []
    for group in exclusive:
        members = tuple(sorted(group))
        _require(len(members) >= 2 and len(set(members)) == len(members), f"exclusive group {members} needs two or more distinct routes")
        for route_id in members:
            _require(route_id in known_routes, f"exclusive group names unknown route {route_id!r}")
        groups.append(members)
    groups.sort()
    stated = list(preference or ())
    _require(len(set(stated)) == len(stated), "preference repeats a route")
    for route_id in stated:
        _require(route_id in known_routes, f"preference names unknown route {route_id!r}")
    order = stated + sorted(known_routes - set(stated))

    limits = {route.route_id: route.limit for route in route_list}
    unknown_routes = tuple(sorted(route_id for route_id, limit in limits.items() if limit is None))
    unknown_pools = tuple(pool.pool_id for pool in pool_list if pool.bound is None and pool.uses)
    branch_sets = _branches(groups)
    exclusive_members = {route_id for group in groups for route_id in group}
    if len(branch_sets) > MAX_BRANCHES:
        return JointSolution(
            determined=False, value=None, witness=None, binding=(), slack=(),
            unknown_routes=unknown_routes, unknown_pools=unknown_pools,
            floor_when_unknowns_zero=Fraction(0), floor_witness=(), ceiling_when_unknowns_relaxed=None,
            allowed_exclusive=(), branches_evaluated=0,
            blockers=(f"exclusive choices give {len(branch_sets)} branches, above the {MAX_BRANCHES} enumeration limit",),
        )

    def best(mode: str, skip_pool: str | None = None) -> tuple[Fraction | None, dict[str, Fraction], frozenset[str]]:
        """Best branch; ``mode`` is exact, floor (unknown = 0) or ceiling (unknown relaxed)."""
        winner: tuple[tuple[Fraction, ...], dict[str, Fraction], frozenset[str]] | None = None
        for excluded in branch_sets:
            dropped = set(excluded)
            if mode == "floor":
                dropped |= set(unknown_routes)
            rows = []
            for pool in pool_list:
                if pool.pool_id == skip_pool:
                    continue
                if pool.bound is None:
                    if mode == "floor":
                        dropped |= {route_id for route_id, _ in pool.uses}
                    continue
                rows.append((pool.bound, dict(pool.uses)))
            active = [route_id for route_id in order if route_id not in dropped]
            result = _solve_branch(active, limits, rows)
            if result is None:
                return None, {}, excluded
            value, solution = result
            full = {route_id: solution.get(route_id, Fraction(0)) for route_id in order}
            key = (value, *(full[route_id] for route_id in order))
            if winner is None or key > winner[0]:
                winner = (key, full, excluded)
        assert winner is not None
        return winner[0][0], winner[1], winner[2]

    def allowed(excluded: frozenset[str]) -> tuple[str, ...]:
        return tuple(sorted(exclusive_members - excluded))

    floor_value, floor_solution, _ = best("floor")
    assert floor_value is not None
    floor_witness = tuple((route_id, floor_solution[route_id]) for route_id in sorted(floor_solution))
    if unknown_routes or unknown_pools:
        ceiling_value, _, _ = best("ceiling")
        return JointSolution(
            determined=False, value=None, witness=None, binding=(), slack=(),
            unknown_routes=unknown_routes, unknown_pools=unknown_pools,
            floor_when_unknowns_zero=floor_value, floor_witness=floor_witness,
            ceiling_when_unknowns_relaxed=ceiling_value,
            allowed_exclusive=(), branches_evaluated=len(branch_sets),
        )
    value, solution, excluded = best("exact")
    assert value is not None
    binding, slack = [], []
    for pool in pool_list:
        relaxed, _, _ = best("exact", skip_pool=pool.pool_id)
        (binding if relaxed is None or relaxed > value else slack).append(pool.pool_id)
    return JointSolution(
        determined=True, value=value,
        witness=tuple((route_id, solution[route_id]) for route_id in sorted(solution)),
        binding=tuple(binding), slack=tuple(slack),
        unknown_routes=(), unknown_pools=(),
        floor_when_unknowns_zero=value, floor_witness=floor_witness,
        ceiling_when_unknowns_relaxed=value,
        allowed_exclusive=allowed(excluded), branches_evaluated=len(branch_sets),
    )


__all__ = [
    "IMPLEMENTATION",
    "JointModelError",
    "JointPool",
    "JointRoute",
    "JointSolution",
    "MAX_BRANCHES",
    "decimal_floor",
    "exact",
    "solve_joint",
]
