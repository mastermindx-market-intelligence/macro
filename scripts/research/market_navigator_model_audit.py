"""Deterministic model stress audit, NOT an alpha backtest or live inventory estimate.

Reuse the incumbent scalar Greeks. Compare local charm extrapolation with finite
repricing only BEFORE expiry. Demonstrate why an extrapolation across fixing has
no admitted settlement interpretation. Writes only when an explicit --output is given.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import statistics

import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.greeks import bs_greeks

MINUTES_PER_YEAR = 365 * 24 * 60


def audit() -> dict:
    rows = []
    bad_extrapolations = []
    fd_errors = []
    for minutes in (5, 15, 60, 390):
        tenor = minutes / MINUTES_PER_YEAR
        for strike in (770, 773, 774, 775, 776, 777, 780):
            for is_call in (True, False):
                delta, _, _, charm = bs_greeks(775, strike, tenor, 0.2, is_call)
                epsilon = tenor * 1e-4
                numeric_charm = (bs_greeks(775, strike, tenor - epsilon, 0.2, is_call)[0]
                                 - bs_greeks(775, strike, tenor + epsilon, 0.2, is_call)[0]) / (2 * epsilon)
                fd_errors.append(abs(numeric_charm - charm) / max(1.0, abs(charm)))
                # Intentionally invalid practice being tested, never admitted as a forecast.
                naive_day = charm / 365
                if abs(naive_day) > 1:
                    bad_extrapolations.append({"minutes_to_expiry": minutes,
                        "strike": strike, "right": "C" if is_call else "P",
                        "linear_one_calendar_day_delta_change": naive_day,
                        "reason": "crosses_expiry_and_exceeds_unit_delta_change_bound"})
                for fraction in (0.05, 0.25, 0.5, 0.9):
                    dt = tenor * fraction
                    target_delta = bs_greeks(775, strike, tenor - dt, 0.2, is_call)[0]
                    exact = target_delta - delta
                    linear = charm * dt
                    rows.append({"minutes_to_expiry": minutes, "strike": strike,
                        "right": "C" if is_call else "P", "fraction_elapsed": fraction,
                        "finite_delta_change": exact, "linear_delta_change": linear,
                        "absolute_delta_error": abs(exact - linear),
                        "hedge_error_units_per_long_standard_contract": 100 * abs(exact - linear)})
    errors = sorted(row["absolute_delta_error"] for row in rows)
    root = Path(__file__).resolve().parents[2]
    source = root / "engine/greeks.py"
    return {
        "schema": "market_navigator.model_audit/v1",
        "evidence_class": "SIMULATED_MODEL_AUDIT_NOT_MARKET_PERFORMANCE",
        "source_kernel": "engine/greeks.py:bs_greeks",
        "source_sha256": sha256(source.read_bytes()).hexdigest(),
        "assumptions": {"spot": 775, "iv_decimal": 0.2, "r": 0, "q": 0,
            "pricing_model": "European Black-Scholes", "time_basis": "calendar_year_365d",
            "strike_grid": [770, 773, 774, 775, 776, 777, 780],
            "expiry_minutes": [5, 15, 60, 390], "roll_fractions": [0.05, 0.25, 0.5, 0.9],
            "benchmark_position": "one hypothetical long standard 100-unit contract",
            "iv_surface": "fixed", "real_trade_costs": "not_modelled"},
        "n_pre_expiry_cases": len(rows),
        "n_one_day_cases": 56,
        "n_one_day_extrapolations_violating_delta_bound": len(bad_extrapolations),
        "max_relative_finite_difference_charm_error": max(fd_errors),
        "median_absolute_delta_error": statistics.median(errors),
        "max_absolute_delta_error": max(errors),
        "max_hedge_error_units_per_contract": 100 * max(errors),
        "finite_changes_within_unit_bound": all(abs(r["finite_delta_change"]) <= 1 for r in rows),
        "largest_pre_expiry_errors": sorted(rows, key=lambda r: -r["absolute_delta_error"])[:8],
        "invalid_day_examples": sorted(bad_extrapolations,
            key=lambda r: -abs(r["linear_one_calendar_day_delta_change"]))[:6],
        "authority": {"predictive_edge": False, "observed_dealer_inventory": False,
                      "trading": False, "production_promotion": False},
        "interpretation": "A local derivative is not a bounded finite hedge forecast. Use the incumbent finite scenario owner, preserving model applicability and fixing refusal.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(audit(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
