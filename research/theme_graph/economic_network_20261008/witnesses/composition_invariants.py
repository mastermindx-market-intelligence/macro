#!/usr/bin/env python3
"""Research-only executable counterexamples. No production imports or market data.

All coefficients and capacities below are synthetic. This tests logical claims
about composition, units, bottlenecks and accounting. It does not fit a model,
validate extraction quality, establish causality or demonstrate predictive gain.
Run: python witnesses/composition_invariants.py
"""
from dataclasses import dataclass, replace
from pathlib import Path
import hashlib
import json
import math


@dataclass(frozen=True)
class Parameter:
    kind: str
    input_variable: str
    output_variable: str
    input_unit: str
    output_unit: str
    period: str
    state: str
    scope: str
    coefficient: float | None


def compose(first: Parameter, second: Parameter):
    """A deliberately narrow algebraic witness, not a propagation compiler."""
    if first.kind != "scenario_derivative" or second.kind != "scenario_derivative":
        return None, "OBSERVED_SHARE_IS_NOT_DERIVATIVE"
    for field in ("period", "state", "scope"):
        if getattr(first, field) != getattr(second, field):
            return None, f"INCOMPATIBLE_{field.upper()}"
    if first.output_variable != second.input_variable:
        return None, "INTERMEDIATE_VARIABLE_MISMATCH"
    if first.output_unit != second.input_unit:
        return None, "INTERMEDIATE_UNIT_MISMATCH"
    if first.coefficient is None or second.coefficient is None:
        return None, "PARAMETER_UNKNOWN"
    return first.coefficient * second.coefficient, "SCENARIO_ONLY"


def systems(demand, gpu, memory, power):
    # Inputs already normalized by an assumed bill of materials into
    # feasible complete systems per period. Raw MW and bits are not comparable.
    values = {"demand": demand, "gpu": gpu, "memory": memory, "power": power}
    if any(v is None for v in values.values()):
        return None, ["CAPACITY_UNKNOWN"]
    if any(not math.isfinite(v) or v < 0 for v in values.values()):
        raise ValueError("Synthetic capacities must be finite and nonnegative")
    output = min(values.values())
    return output, [k for k, v in values.items() if v == output]


def run():
    cases = []

    def check(name, actual, expected, establishes):
        cases.append({"name": name, "actual": actual, "expected": expected,
                      "passed": actual == expected, "establishes": establishes})

    first = Parameter("scenario_derivative", "C.input_available", "B.delivered",
                      "input_units", "B_units", "one_period", "s0", "program_x", 2.0)
    second = Parameter("scenario_derivative", "B.delivered", "A.output",
                       "B_units", "A_units", "one_period", "s0", "program_x", 0.5)
    check("compatible_conditional_derivatives", compose(first, second),
          (1.0, "SCENARIO_ONLY"), "Unit-linked algebra under declared assumptions")
    check("observed_sales_share_not_a_derivative",
          compose(replace(first, kind="observed_revenue_share", coefficient=0.2), second),
          (None, "OBSERVED_SHARE_IS_NOT_DERIVATIVE"), "True shares need not compose")
    check("ownership_share_not_a_derivative",
          compose(replace(first, kind="observed_equity_interest", coefficient=0.49), second),
          (None, "OBSERVED_SHARE_IS_NOT_DERIVATIVE"), "Equity interest is not revenue sensitivity")
    check("wrong_intermediate_variable", compose(first, replace(second, input_variable="B.revenue")),
          (None, "INTERMEDIATE_VARIABLE_MISMATCH"), "Same company is not same variable")
    check("wrong_intermediate_unit", compose(first, replace(second, input_unit="USD")),
          (None, "INTERMEDIATE_UNIT_MISMATCH"), "Unprovided physical-to-currency conversion blocks")
    for field, value in [("period", "one_year"), ("state", "s1"), ("scope", "program_y")]:
        check(f"mismatched_{field}", compose(first, replace(second, **{field: value})),
              (None, f"INCOMPATIBLE_{field.upper()}"), "Context is part of the parameter")
    check("unknown_parameter", compose(replace(first, coefficient=None), second),
          (None, "PARAMETER_UNKNOWN"), "Unknown is never zero or one")
    base = systems(120, 100, 80, 110)
    gpu = systems(120, 140, 80, 110)
    memory = systems(120, 100, 120, 110)
    both = systems(120, 140, 120, 110)
    check("baseline_memory_constraint", base, (80, ["memory"]), "Assumed minimum technology")
    check("nonlimiting_gpu_expansion", gpu, (80, ["memory"]), "More input may have zero marginal output")
    check("bottleneck_migrates_to_gpu", memory, (100, ["gpu"]), "Constraint depends on state")
    check("bottleneck_migrates_to_power", both, (110, ["power"]), "Joint expansion changes limiting input")
    check("positive_complement_interaction", both[0] - gpu[0] - memory[0] + base[0],
          10, "Nonadditivity of this synthetic production function")
    check("unknown_capacity_abstains", systems(120, 100, None, 110),
          (None, ["CAPACITY_UNKNOWN"]), "No guessed capacity")
    demand, original_available, outage, substitute_spare = 100, 100, 30, 30
    unqualified = min(demand, original_available - outage)
    qualified = min(demand, original_available - outage + substitute_spare)
    check("substitution_depends_on_qualification", (unqualified, qualified), (70, 100),
          "Same nominal spare input differs if qualification is unavailable within horizon")
    disruption_need, usable_inventory = 30, 30
    check("inventory_can_buffer_transmission", max(0, disruption_need - usable_inventory), 0,
          "Supply loss need not equal current output loss")
    # Two views of one transaction carry the SAME event and allocation set.
    paths = [
        {"event": "synthetic_E", "allocation": "whole_order", "value": 120},
        {"event": "synthetic_E", "allocation": "whole_order", "value": 120},
    ]
    unique_allocations = {(p["event"], p["allocation"]): p["value"] for p in paths}
    check("same_allocation_seen_twice", (sum(p["value"] for p in paths), sum(unique_allocations.values())),
          (240, 120), "Path sum double-counts; real allocations require explicit reconciliation")
    result = {
        "schema": "research.composition_witness/v0",
        "status": "RESEARCH_FIXTURE_ONLY",
        "empirical_market_validation": False,
        "production_changes": False,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "assumptions": [
            "All values synthetic; no issuer capacity, elasticity or revenue allocation estimated",
            "Capacities preconverted into feasible complete systems per identical period",
            "Minimum-input technology is an illustrative assumption, not an estimated model",
            "Derivative composition is a local algebraic witness, not a causal identification procedure",
            "Allocation dedup example assumes exact duplicate views; distinct flows cannot be deduped by origin alone",
        ],
        "passed": sum(c["passed"] for c in cases),
        "failed": sum(not c["passed"] for c in cases),
        "cases": cases,
    }
    target = Path(__file__).with_name("composition_invariants_results.json")
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": str(target), "passed": result["passed"], "failed": result["failed"],
                      "empirical_market_validation": False}))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
