"""Compile a repeatable Swing Confluence research plan, never trading outcomes.

This is a leaf consumer recipe, not a new registry, evaluator or admission gate.
No market input, network, dynamic import, TrialLedger write or outcome-run API is
provided. Owner references remain unverified assertions. See the adjacent TOI
research protocol for the source, registration and execution prerequisites.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA = "toi.swing_research_recipe.v1"
MAX_INPUT_BYTES = 65536
MAX_CONFIGURATIONS = 10000
KEYS = frozenset({
    "schema", "study_id", "families", "clock_pairs", "session_example_minutes",
    "memory_modes", "signal_bundles", "holding_sessions", "exit_rules",
    "cost_bps_one_way", "primary_cost_bps_one_way", "baselines", "random_seed",
    "max_planned_comparisons", "dependencies",
})
DEPENDENCIES = frozenset({
    "source_admission", "evidence_census", "clock_memory", "pit_universe",
    "setup_species", "trial_registration", "intraday_evaluator",
    "event_availability", "chart_replay",
})
MEMORY_MODES = frozenset({"fixed_bar_count", "fixed_elapsed_kernel"})
STATES = frozenset({"HOLD", "MISSING", "UNVERIFIED", "REFERENCED"})
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,95}$")
AUTHORITY = ("may_rank", "may_gate", "may_size", "may_trade", "may_modify_prophet", "can_open_entry")


class RecipeError(ValueError):
    """The proposed research recipe is ambiguous, invalid or over budget."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _keys(value: Any, expected: frozenset[str] | set[str], name: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise RecipeError(f"{name}: exact fields required: {', '.join(sorted(expected))}")


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise RecipeError(f"{name}: integer required in {minimum}..{maximum}; booleans are not integers")
    return value


def _text(value: Any, name: str, *, identifier: bool = False, limit: int = 256) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise RecipeError(f"{name}: nonempty bounded text without control characters required")
    if identifier and not IDENTIFIER.fullmatch(value):
        raise RecipeError(f"{name}: lower-case identifier required")
    return value


def _axis(value: Any, name: str, validator: Any, *, max_items: int = 32) -> list[Any]:
    if not isinstance(value, list) or not 1 <= len(value) <= max_items:
        raise RecipeError(f"{name}: nonempty list of at most {max_items} values required")
    normalized = [validator(item) for item in value]
    if len({_canonical(item) for item in normalized}) != len(normalized):
        raise RecipeError(f"{name}: duplicate values are not allowed")
    return sorted(normalized)


def _cost(value: Any) -> float:
    if type(value) not in (int, float):
        raise RecipeError("cost: a finite real number, not a boolean, is required")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise RecipeError("cost: finite value required") from exc
    if not math.isfinite(number) or not 0 <= number <= 1000:
        raise RecipeError("cost: finite one-way basis points in 0..1000 required")
    return number


def _normalize(recipe: dict[str, Any]) -> dict[str, Any]:
    _keys(recipe, KEYS, "recipe")
    if recipe["schema"] != SCHEMA:
        raise RecipeError(f"schema must be {SCHEMA}")
    r: dict[str, Any] = {"schema": SCHEMA, "study_id": _text(recipe["study_id"], "study_id", identifier=True)}
    for key in ("families", "memory_modes", "signal_bundles", "exit_rules", "baselines"):
        r[key] = _axis(recipe[key], key, lambda v: _text(v, key, identifier=True), max_items=8)
    if not set(r["memory_modes"]) <= MEMORY_MODES:
        raise RecipeError("memory_modes: use the declared Temporal Grain controls")
    r["holding_sessions"] = _axis(recipe["holding_sessions"], "holding_sessions", lambda v: _integer(v, "holding_sessions", 1, 252), max_items=12)
    r["cost_bps_one_way"] = _axis(recipe["cost_bps_one_way"], "cost_bps_one_way", _cost, max_items=8)
    primary = _cost(recipe["primary_cost_bps_one_way"])
    if primary <= 0 or primary not in r["cost_bps_one_way"]:
        raise RecipeError("primary cost must be positive and included in cost_bps_one_way")
    r["primary_cost_bps_one_way"] = primary
    for key, lower, upper in (("random_seed", 0, 2**32 - 1), ("session_example_minutes", 1, 1440), ("max_planned_comparisons", 1, 1000000)):
        r[key] = _integer(recipe[key], key, lower, upper)
    pairs = recipe["clock_pairs"]
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= 16:
        raise RecipeError("clock_pairs: provide 1..16 explicit trigger/setup pairs")
    normalized_pairs = []
    for pair in pairs:
        _keys(pair, {"trigger_minutes", "setup_minutes"}, "clock pair")
        trigger = _integer(pair["trigger_minutes"], "trigger_minutes", 1, 1440)
        setup = _integer(pair["setup_minutes"], "setup_minutes", 1, 1440)
        if trigger >= setup:
            raise RecipeError("trigger_minutes must be smaller than setup_minutes")
        normalized_pairs.append((trigger, setup))
    if len(set(normalized_pairs)) != len(normalized_pairs):
        raise RecipeError("clock_pairs: duplicates are not allowed")
    r["clock_pairs"] = [{"trigger_minutes": t, "setup_minutes": s} for t, s in sorted(normalized_pairs)]
    dependencies = recipe["dependencies"]
    _keys(dependencies, DEPENDENCIES, "dependencies")
    r["dependencies"] = {}
    for name, dep in sorted(dependencies.items()):
        _keys(dep, {"owner", "reference", "status"}, f"dependency {name}")
        owner = _text(dep["owner"], f"{name}.owner", limit=128)
        state = dep["status"]
        if not isinstance(state, str) or state not in STATES:
            raise RecipeError(f"{name}.status: an evidence pointer cannot self-admit or authorize execution")
        reference = None if dep["reference"] is None else _text(dep["reference"], f"{name}.reference")
        if state == "REFERENCED" and reference is None:
            raise RecipeError(f"{name}: REFERENCED requires a nonempty reference")
        r["dependencies"][name] = {"owner": owner, "reference": reference, "status": state}
    return r


def compile_recipe(recipe: dict[str, Any], *, include_cases: bool = False) -> dict[str, Any]:
    """Return a deterministic *plan*, without evaluating or registering a trial.

    Counts are conservative proposed comparisons, not completed experiments or
    statistically independent trials. The canonical TrialLedger owner must later
    reconcile all actual looks, including refinements and chart-guided changes.
    """
    if type(include_cases) is not bool:
        raise RecipeError("include_cases must be a boolean")
    r = _normalize(recipe)
    axes = ("families", "clock_pairs", "memory_modes", "signal_bundles", "holding_sessions", "exit_rules")
    count = math.prod(len(r[name]) for name in axes)
    cost_count = count * len(r["cost_bps_one_way"])
    comparisons = cost_count * len(r["baselines"])
    if count > MAX_CONFIGURATIONS or comparisons > r["max_planned_comparisons"]:
        raise RecipeError(f"planned matrix exceeds budget: {count} configurations / {comparisons} comparisons; no cases allocated")
    fingerprint = _digest(r)
    example = r["session_example_minutes"]
    grains = sorted({minutes for pair in r["clock_pairs"] for minutes in pair.values()})
    arithmetic = []
    for grain in grains:
        whole, tail = divmod(example, grain)
        arithmetic.append({"nominal_minutes": grain, "declared_session_minutes": example, "full_buckets": whole, "terminal_minutes": tail, "total_buckets": whole + bool(tail)})
    result: dict[str, Any] = {
        "study_id": r["study_id"], "status": "DRAFT_NOT_REGISTERED",
        "recipe_sha256": fingerprint, "configuration_count": count,
        "cost_scenario_count": cost_count, "planned_comparison_upper_bound": comparisons,
        "planned_look_count_is_realized_ledger_count": False,
        "primary_cost_bps_one_way": r["primary_cost_bps_one_way"],
        "source_admission_claim": r["dependencies"]["source_admission"]["status"],
        "owner_requirements": {name: {**dep, "owner_verification_required": True} for name, dep in r["dependencies"].items()},
        "clock_arithmetic": arithmetic, "clock_arithmetic_is_calendar_proof": False,
        "outcome_execution_available": False, "trial_ledger_written": False,
        "network_used": False, "authority": {key: False for key in AUTHORITY},
        "scope_note": "Planner only. No returns, fitted parameters, data admission, native clock parity, strategy proof or product installation.",
    }
    if include_cases:
        cases = []
        for family, pair, memory, bundle, horizon, exit_rule in itertools.product(*(r[name] for name in axes)):
            case = {"family": family, **pair, "memory_mode": memory, "signal_bundle": bundle, "holding_sessions": horizon, "exit_rule": exit_rule}
            case["case_id"] = _digest({"recipe_sha256": fingerprint, **case})
            cases.append(case)
        result["cases"] = cases
    return result


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecipeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> Any:
    raise RecipeError(f"nonfinite JSON value is not allowed: {value}")


def load_recipe(path: Path | str) -> dict[str, Any]:
    """Read bounded strict JSON; no permissive duplicate-key or NaN handling."""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise RecipeError(f"recipe exceeds {MAX_INPUT_BYTES} bytes")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_pairs, parse_constant=_constant)
        if not isinstance(value, dict):
            raise RecipeError("recipe must be a JSON object")
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError(f"cannot read recipe: {type(exc).__name__}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Explicit plan-artifact destination, never a trial ledger")
    parser.add_argument("--include-cases", action="store_true", help="Include all cases in --output; stdout stays bounded")
    args = parser.parse_args(argv)
    try:
        if args.include_cases and args.output is None:
            raise RecipeError("--include-cases requires --output to keep stdout bounded")
        report = compile_recipe(load_recipe(args.recipe), include_cases=args.include_cases)
        if args.output is not None:
            # Refuse overwriting inputs; output is a disposable report, not source truth.
            if args.output.resolve() == args.recipe.resolve():
                raise RecipeError("output must not overwrite the input recipe")
            if args.output.suffix.lower() != ".json" or args.output.name.lower() == "trial_ledger.json":
                raise RecipeError("output must be a new .json plan artifact, never a trial ledger")
            # Exclusive creation preserves existing evidence and refuses symlinks.
            # No force/overwrite option: a new recipe run gets a new artifact path.
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
        summary = {key: value for key, value in report.items() if key != "cases"}
        print(json.dumps(summary, sort_keys=True, allow_nan=False))
        return 0
    except (RecipeError, OSError) as exc:
        print(f"swing-plan: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
