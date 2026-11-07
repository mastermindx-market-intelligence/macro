#!/usr/bin/env python3
"""Sharp marginal opening/closing bounds in an explicitly limited count model.

Research reference only. V counts matched unit-contract transactions ONCE, not
participant sides. All trades concern one unchanged economic option series.
The only non-trade effect admitted is a known nonnegative count of removals;
its timing is unconstrained (it may occur after trading). No additions,
corporate-action remapping, incomplete volume or missing-as-zero are admitted.
These mathematical assumptions and supplied counts are not source-certified.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path

SCHEMA = "options.oi.identification.reference.v1"
MAX_ORDERED_EVENTS = 256


class Refusal(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Refusal("COUNT_INVALID", f"{name} must be a known nonnegative integer")
    return value


def _fraction(numerator: int, denominator: int):
    if denominator == 0:
        return None
    result = Fraction(numerator, denominator)
    return {"numerator": result.numerator, "denominator": result.denominator}


def exact_bounds(volume: int, initial: int, final: int, *, removals: int,
                 subset_count: int | None = None) -> dict:
    """Exact marginal integer bounds, conditional on the stated count model.

    Let x=OO, y=CC, z=OC, w=CO in buyer/seller order. The full joint feasible
    set is x_min<=x<=x_max, y=x-d, m=V+d-2x, 0<=z<=m, w=m-z.
    Arbitrary combinations of returned marginal bounds are NOT jointly valid.
    Unknown removal counts must not be replaced by zero: use an explicit
    admissible interval or leave the observation unavailable.
    """
    v, i0, i1, e = (_count(volume, "volume"), _count(initial, "initial"),
                    _count(final, "final"), _count(removals, "removals"))
    d = i1 - i0 + e
    # Without a starting position, positive trading requires at least one OO.
    x_min = max(0, d, 1 if i0 == 0 and v > 0 else 0)
    x_max = (v + d) // 2
    if d < -v or d > v or x_min > x_max:
        raise Refusal("COUNT_MODEL_INFEASIBLE", "no lawful unit-trade sequence fits these counts")
    bounds = {
        "both_open": [x_min, x_max],
        "both_close": [x_min - d, x_max - d],
        "mixed": [v + d - 2 * x_max, v + d - 2 * x_min],
        "buyer_open": [x_min, v + d - x_min],
        "seller_open": [x_min, v + d - x_min],
        "opening_sides": [v + d, v + d],
        "closing_sides": [v - d, v - d],
    }
    subset = None
    if subset_count is not None:
        a = _count(subset_count, "subset_count")
        if a > v:
            raise Refusal("SUBSET_INVALID", "subset_count exceeds matched-contract volume")
        lo, hi = bounds["buyer_open"]
        subset = [max(0, lo + a - v), min(a, hi)]
    return {
        "schema": SCHEMA,
        "model": "single_series_unit_trades_unconstrained_removal_timing",
        "volume": v, "initial_interest": i0, "final_interest": i1,
        "nontrading_removals": e, "reported_oi_change": i1 - i0,
        "trade_oi_change": d, "bounds": bounds,
        "joint_parameterization": {"both_open_range": [x_min, x_max],
            "both_close": "both_open - trade_oi_change",
            "mixed": "volume + trade_oi_change - 2*both_open",
            "buyer_open_seller_close_range": "0..mixed",
            "buyer_close_seller_open": "mixed - buyer_open_seller_close"},
        "opening_side_fraction": _fraction(v + d, 2 * v),
        "subset_buyer_open_bounds": subset,
        "subset_basis": "count_only_unpositioned" if subset_count is not None else None,
        "opening_probability": None,
        "source_certified": False,
        "predictive_authority": False,
    }


def removal_interval_bounds(volume: int, initial: int, final: int, *,
                            removals_low: int, removals_high: int) -> dict:
    """Union marginal bounds over a stated integer interval of removal counts.

    Computes O(1) candidates, not a point estimate of the unknown removals.
    Marginal extrema are piecewise-linear/floor functions of d with breakpoints
    at zero and the empty-inventory correction. Endpoint neighbours cover both
    parity classes for the mixed-count minimum. Full joint sets remain separate.
    """
    v, i0, i1 = _count(volume, "volume"), _count(initial, "initial"), _count(final, "final")
    low, high = _count(removals_low, "removals_low"), _count(removals_high, "removals_high")
    if low > high:
        raise Refusal("REMOVAL_INTERVAL_INVALID", "lower removal bound exceeds upper bound")
    delta = i1 - i0
    feasible_low = max(low, -v - delta)
    feasible_high = min(high, v - delta)
    if i0 == 0 and v == 1 and delta + feasible_low == 0:
        feasible_low += 1
    if feasible_low > feasible_high:
        raise Refusal("COUNT_MODEL_INFEASIBLE", "no removal count in the interval is feasible")
    d_low, d_high = delta + feasible_low, delta + feasible_high
    candidates = {d_low, d_high, d_low + 1, d_high - 1, -1, 0, 1}
    evaluated = [exact_bounds(v, i0, i1, removals=d - delta)
                 for d in sorted(candidates) if d_low <= d <= d_high]
    result_bounds = {name: [min(r["bounds"][name][0] for r in evaluated),
                            max(r["bounds"][name][1] for r in evaluated)]
                     for name in evaluated[0]["bounds"]}
    return {
        "schema": SCHEMA,
        "model": "union_over_integer_removals_unconstrained_timing",
        "volume": v, "initial_interest": i0, "final_interest": i1,
        "declared_removals": [low, high],
        "feasible_removals": [feasible_low, feasible_high],
        "inconsistent_removal_endpoints_excluded": [low, high] != [feasible_low, feasible_high],
        "bounds": result_bounds,
        "joint_warning": "Marginal endpoints may require different removal counts and cannot be combined freely.",
        "opening_probability": None, "source_certified": False, "predictive_authority": False,
    }


def ordered_subset_bounds(volume: int, initial: int, final: int, selected_indices,
                          *, removals: int) -> dict:
    """Exact min/max buyer-open units at specified unit-transaction positions.

    This is a bounded O(V^2) reference, not a trade-feed reconstruction. Source
    order must be qualified elsewhere; timestamp order is not assumed correct.
    Non-trade removals have unconstrained timing, so moving them after all trades
    preserves feasibility and gives a terminal inventory of final+removals.
    """
    v, i0, i1, e = (_count(volume, "volume"), _count(initial, "initial"),
                    _count(final, "final"), _count(removals, "removals"))
    if v > MAX_ORDERED_EVENTS:
        raise Refusal("ORDERED_REFERENCE_LIMIT", "more than 256 unit events; no truncation performed")
    if isinstance(selected_indices, (str, bytes, dict)):
        raise Refusal("SUBSET_INVALID", "selected indices must be an iterable of distinct integer positions")
    try:
        selected = tuple(selected_indices)
    except TypeError as error:
        raise Refusal("SUBSET_INVALID", "selected indices are unavailable") from error
    for index in selected:
        _count(index, "selected_index")
        if index >= v:
            raise Refusal("SUBSET_INVALID", "selected index outside the unit-event sequence")
    if len(set(selected)) != len(selected):
        raise Refusal("SUBSET_INVALID", "duplicate selected indices")
    selected = set(selected)
    states = {i0: (0, 0)}
    for index in range(v):
        nxt = {}
        mark = int(index in selected)
        for interest, (lo, hi) in states.items():
            moves = [(interest + 1, mark)]  # OO
            if interest > 0:
                moves.extend([(interest - 1, 0), (interest, mark), (interest, 0)])  # CC, OC, CO
            for destination, increment in moves:
                a, b = lo + increment, hi + increment
                previous = nxt.get(destination)
                nxt[destination] = (a, b) if previous is None else (min(previous[0], a), max(previous[1], b))
        states = nxt
    target = i1 + e
    if target not in states:
        raise Refusal("COUNT_MODEL_INFEASIBLE", "no lawful sequence fits the endpoint")
    return {"schema": SCHEMA, "model": "known_unit_event_order_unconstrained_removal_timing",
            "volume": v, "selected_indices": sorted(selected),
            "buyer_open_bounds": list(states[target]),
            "opening_probability": None, "source_certified": False, "predictive_authority": False}


def examples() -> dict:
    return {
        "schema": SCHEMA, "synthetic_only": True,
        "examples": {
            "flat_oi_all_ask_unidentified": exact_bounds(100, 10, 10, removals=0, subset_count=100),
            "oi_gain_90_selected_30": exact_bounds(100, 10, 100, removals=0, subset_count=30),
            "volume_exceeds_initial_oi": exact_bounds(100, 10, 10, removals=0),
            "expiration_removes_without_a_closing_trade": exact_bounds(0, 100, 0, removals=100),
            "unobserved_removals_widen_bounds": removal_interval_bounds(100, 100, 20, removals_low=0, removals_high=80),
            "first_trade_genuinely_zero_start": ordered_subset_bounds(3, 0, 0, [0], removals=0),
            "last_trade_genuinely_zero_start": ordered_subset_bounds(3, 0, 0, [2], removals=0),
        },
        "not_established": ["customer or dealer identity", "aggressor classification", "opening probability", "predictive value", "source availability or rights"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new synthetic-example output path; never overwritten")
    args = parser.parse_args()
    text = json.dumps(examples(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
