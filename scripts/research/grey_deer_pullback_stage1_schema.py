"""Stdlib checker for ``grey_deer_pullback_stage1/v1`` result payloads.

The payload shape is the one ``assemble_payload`` writes in
``scripts/research/grey_deer_pullback_stage1.py`` (prereg SS12 key tree,
SS11's twelve claims, SS12 verdict words the runner actually emits).

This module imports nothing outside the Python standard library and does
not read prices or recompute outcomes. ``validate_payload`` reports
structural problems. Non-finite JSON tokens (``NaN``, ``Infinity``,
``-Infinity``) are legal in the runner's ``json.dumps`` output; they are
reported by ``find_nonfinite_tokens`` and fail the CLI only under
``--strict-json``.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = "grey_deer_pullback_stage1/v1"
TRIAL_FAMILY = "grey_deer_pullback_v1"
TRIAL_BUDGET = 69
HORIZONS = (5, 10, 21)
HORIZON_KEYS = frozenset(f"h{h}" for h in HORIZONS)
POPULATIONS = ("P-all", "P-active")
CLAIMS = ("binary", "quantile")
FAMILIES = frozenset(CLAIMS)
OBSERVER_FLAG = "OBSERVER_NOT_ON_MAIN"

# Prereg §11 verdict table, restricted to the four words the runner emits.
# "separately admitted live promotion, never produced by this protocol" is
# named in the table and is never produced by the stage-1 runner.
VERDICT_DESCRIPTIVE = "accepted descriptive measurement"
VERDICT_REJECTED = "rejected candidate"
VERDICT_BLOCKED = "underpowered/blocked claim"
VERDICT_QUALIFIED = "qualified research evidence (development, reconstructed)"
VERDICTS = frozenset(
    {
        VERDICT_DESCRIPTIVE,
        VERDICT_REJECTED,
        VERDICT_BLOCKED,
        VERDICT_QUALIFIED,
    }
)

# Top-level key tree from the runner module docstring and assemble_payload.
TOP_LEVEL_TYPES: dict[str, type] = {
    "schema": str,
    "prereg": dict,
    "manifest": dict,
    "run": dict,
    "sample": dict,
    "trial_budget": dict,
    "census": list,
    "folds": dict,
    "configs": list,
    "comparison_sets": dict,
    "episodes": dict,
    "gates": list,
    "loeo": dict,
    "early_warning": dict,
    "abstention": dict,
    "negative_control": dict,
    "inc": dict,
    "deviations": list,
    "blocked": list,
}

# Horizon-keyed objects assemble_payload always fills for h in (5, 10, 21).
HORIZON_OBJECTS = (
    "folds",
    "comparison_sets",
    "episodes",
    "loeo",
    "early_warning",
    "abstention",
    "negative_control",
)

GATE_KEYS = (
    "id",
    "h",
    "pop",
    "claim",
    "statistic",
    "point",
    "lb",
    "threshold",
    "flags",
    "verdict",
)

HONEST_N_COUNTS = ("origins", "events", "clusters", "episodes", "event_months")

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

_TYPE_NAMES = {
    str: "str",
    dict: "object",
    list: "array",
    int: "int",
    bool: "bool",
    float: "float",
}


class _NonFinite:
    """Sentinel ``parse_constant`` returns so a later walk can name a path."""

    __slots__ = ("token",)

    def __init__(self, token: str) -> None:
        self.token = token


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    return _TYPE_NAMES.get(type(value), type(value).__name__)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_payload(payload: dict) -> list[str]:
    """Return human-readable errors. An empty list means the payload conforms."""
    if not isinstance(payload, dict):
        return ["payload must be an object"]
    errors: list[str] = []
    _check_top_level(payload, errors)
    _check_schema(payload, errors)
    _check_prereg(payload, errors)
    _check_manifest(payload, errors)
    _check_run(payload, errors)
    _check_sample(payload, errors)
    _check_trial_budget(payload, errors)
    _check_census(payload, errors)
    _check_horizon_objects(payload, errors)
    _check_configs(payload, errors)
    _check_comparison_verdicts(payload, errors)
    _check_episodes(payload, errors)
    _check_gates(payload, errors)
    _check_inc(payload, errors)
    _check_string_records(payload, "deviations", ("code", "detail"), errors)
    _check_string_records(payload, "blocked", ("type", "detail"), errors)
    _check_bounds(payload, "", errors)
    return errors


def find_nonfinite_tokens(text: str) -> list[str]:
    """Report every ``NaN`` / ``Infinity`` / ``-Infinity`` token and its JSON path.

    Parsing uses ``json.loads(..., parse_constant=...)``. Each hit is
    ``"<path>: <token>"`` (for example ``gates[0].lb: -Infinity``).
    Invalid JSON raises ``json.JSONDecodeError``.
    """

    def parse_constant(token: str) -> _NonFinite:
        return _NonFinite(token)

    parsed = json.loads(text, parse_constant=parse_constant)
    found: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, _NonFinite):
            found.append(f"{path or '$'}: {node.token}")
            return
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{path}.{key}" if path else str(key)
                walk(value, child)
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(parsed, "")
    return found


def main(argv: list[str] | None = None) -> int:
    """CLI: exit 0 when the file conforms, 1 otherwise."""
    parser = argparse.ArgumentParser(
        prog="grey_deer_pullback_stage1_schema",
        description="Check a grey_deer_pullback_stage1/v1 results payload.",
    )
    parser.add_argument("--path", required=True, help="JSON results file")
    parser.add_argument(
        "--strict-json",
        action="store_true",
        help="also fail when the file contains NaN, Infinity, or -Infinity",
    )
    args = parser.parse_args(argv)
    path = Path(args.path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {path}: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    if args.strict_json:
        try:
            errors.extend(find_nonfinite_tokens(text))
        except json.JSONDecodeError as exc:
            print(f"invalid JSON: {exc}", file=sys.stderr)
            return 1
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        errors.append("payload must be an object")
    else:
        errors.extend(validate_payload(payload))
    for err in errors:
        print(err)
    return 1 if errors else 0


def _check_top_level(payload: dict, errors: list[str]) -> None:
    for key, expected in TOP_LEVEL_TYPES.items():
        if key not in payload:
            errors.append(f"missing required key: {key}")
            continue
        value = payload[key]
        if not isinstance(value, expected):
            errors.append(
                f"{key} must be a {_TYPE_NAMES[expected]}, found {_type_name(value)}"
            )


def _check_schema(payload: dict, errors: list[str]) -> None:
    schema = payload.get("schema")
    if not isinstance(schema, str):
        return
    if schema != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}, found {schema!r}")


def _check_blob_sha(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or _HEX40.fullmatch(value) is None:
        errors.append(f"{path} must be 40 lowercase hex characters, found {value!r}")


def _check_sha256(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        errors.append(f"{path} must be 64 lowercase hex characters, found {value!r}")


def _check_prereg(payload: dict, errors: list[str]) -> None:
    prereg = payload.get("prereg")
    if not isinstance(prereg, dict):
        return
    path = prereg.get("path")
    if not isinstance(path, str) or not path:
        errors.append(f"prereg.path must be a non-empty str, found {path!r}")
    if "blob_sha" not in prereg:
        errors.append("missing required key: prereg.blob_sha")
    else:
        _check_blob_sha(prereg.get("blob_sha"), "prereg.blob_sha", errors)
    if "sha256" not in prereg:
        errors.append("missing required key: prereg.sha256")
    else:
        _check_sha256(prereg.get("sha256"), "prereg.sha256", errors)


def _check_manifest(payload: dict, errors: list[str]) -> None:
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        return
    path = manifest.get("path")
    if not isinstance(path, str) or not path:
        errors.append(f"manifest.path must be a non-empty str, found {path!r}")
    if "blob_sha" not in manifest:
        errors.append("missing required key: manifest.blob_sha")
    else:
        _check_blob_sha(manifest.get("blob_sha"), "manifest.blob_sha", errors)
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        errors.append(f"manifest.version must be a non-empty str, found {version!r}")


def _check_run(payload: dict, errors: list[str]) -> None:
    run = payload.get("run")
    if not isinstance(run, dict):
        return
    for key in ("utc", "python", "numpy", "pandas", "scipy"):
        value = run.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"run.{key} must be a non-empty str, found {value!r}")
    for key in ("commit_sha", "script_blob_sha", "test_blob_sha"):
        if key not in run:
            errors.append(f"missing required key: run.{key}")
        else:
            _check_blob_sha(run.get(key), f"run.{key}", errors)
    hydrate = run.get("hydrate")
    if not isinstance(hydrate, dict):
        errors.append(f"run.hydrate must be an object, found {_type_name(hydrate)}")
        return
    performed = hydrate.get("performed")
    if not isinstance(performed, bool):
        errors.append(f"run.hydrate.performed must be a bool, found {_type_name(performed)}")
    rc = hydrate.get("rc", None) if "rc" in hydrate else None
    if "rc" not in hydrate:
        errors.append("missing required key: run.hydrate.rc")
    elif rc is not None and not _is_int(rc):
        errors.append(f"run.hydrate.rc must be an int or null, found {rc!r}")


def _check_sample(payload: dict, errors: list[str]) -> None:
    sample = payload.get("sample")
    if not isinstance(sample, dict):
        return
    if "subframe_content_sha256" not in sample:
        errors.append("missing required key: sample.subframe_content_sha256")
    else:
        _check_sha256(sample.get("subframe_content_sha256"), "sample.subframe_content_sha256", errors)
    rows = sample.get("rows")
    if not _is_int(rows) or rows < 0:
        errors.append(f"sample.rows must be an integer >= 0, found {rows!r}")
    for key in ("first_date", "last_date"):
        value = sample.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"sample.{key} must be a non-empty str, found {value!r}")
    integrity = sample.get("integrity")
    if not isinstance(integrity, list):
        errors.append(f"sample.integrity must be an array, found {_type_name(integrity)}")


def _check_trial_budget(payload: dict, errors: list[str]) -> None:
    budget = payload.get("trial_budget")
    if not isinstance(budget, dict):
        return
    family = budget.get("family")
    if family != TRIAL_FAMILY:
        errors.append(f"trial_budget.family must be {TRIAL_FAMILY!r}, found {family!r}")
    amount = budget.get("budget")
    if not _is_int(amount) or amount != TRIAL_BUDGET:
        errors.append(f"trial_budget.budget must be {TRIAL_BUDGET}, found {amount!r}")
    basis = budget.get("basis")
    if not isinstance(basis, str) or not basis:
        errors.append(f"trial_budget.basis must be a non-empty str, found {basis!r}")


def _check_census(payload: dict, errors: list[str]) -> None:
    census = payload.get("census")
    if not isinstance(census, list):
        return
    horizons: set[int] = set()
    for index, row in enumerate(census):
        if not isinstance(row, dict):
            errors.append(f"census[{index}] must be an object, found {_type_name(row)}")
            continue
        horizon = row.get("horizon")
        population = row.get("population")
        if horizon not in HORIZONS:
            errors.append(
                f"census[{index}].horizon must be one of {list(HORIZONS)}, found {horizon!r}"
            )
        else:
            horizons.add(horizon)
        if population not in POPULATIONS:
            errors.append(
                f"census[{index}].population must be one of {list(POPULATIONS)}, found {population!r}"
            )
    if horizons != set(HORIZONS):
        errors.append(f"census horizons must be exactly {{5, 10, 21}}, found {sorted(horizons)}")


def _check_horizon_objects(payload: dict, errors: list[str]) -> None:
    for key in HORIZON_OBJECTS:
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        found = set(value)
        if found != HORIZON_KEYS:
            errors.append(
                f"{key}: horizons must be exactly {{h5, h10, h21}}, found {sorted(found)}"
            )


def _check_configs(payload: dict, errors: list[str]) -> None:
    configs = payload.get("configs")
    if not isinstance(configs, list):
        return
    for index, row in enumerate(configs):
        if not isinstance(row, dict):
            errors.append(f"configs[{index}] must be an object, found {_type_name(row)}")


def _check_comparison_verdicts(payload: dict, errors: list[str]) -> None:
    comparison_sets = payload.get("comparison_sets")
    if not isinstance(comparison_sets, dict):
        return
    for hkey, fams in comparison_sets.items():
        if not isinstance(fams, dict):
            errors.append(f"comparison_sets.{hkey} must be an object, found {_type_name(fams)}")
            continue
        if set(fams) != FAMILIES:
            errors.append(
                f"comparison_sets.{hkey}: families must be exactly {{binary, quantile}}, "
                f"found {sorted(fams)}"
            )
        for fam, cell in fams.items():
            if not isinstance(cell, dict):
                errors.append(
                    f"comparison_sets.{hkey}.{fam} must be an object, found {_type_name(cell)}"
                )
                continue
            verdict = cell.get("descriptive_verdict")
            if verdict not in VERDICTS:
                errors.append(
                    f"comparison_sets.{hkey}.{fam}.descriptive_verdict {verdict!r} "
                    "is not in the prereg §11 verdict set"
                )


def _check_episodes(payload: dict, errors: list[str]) -> None:
    episodes = payload.get("episodes")
    if not isinstance(episodes, dict):
        return
    for hkey, fams in episodes.items():
        if not isinstance(fams, dict):
            errors.append(f"episodes.{hkey} must be an object, found {_type_name(fams)}")
            continue
        if set(fams) != FAMILIES:
            errors.append(
                f"episodes.{hkey}: families must be exactly {{binary, quantile}}, found {sorted(fams)}"
            )
        for fam, row in fams.items():
            path = f"episodes.{hkey}.{fam}"
            if not isinstance(row, dict):
                errors.append(f"{path} must be an object, found {_type_name(row)}")
                continue
            honest = row.get("honest_n")
            if not isinstance(honest, dict):
                errors.append(f"{path}.honest_n must be an object, found {_type_name(honest)}")
                continue
            _check_honest_n(honest, f"{path}.honest_n", errors)


def _check_honest_n(honest: dict, path: str, errors: list[str]) -> None:
    counts: dict[str, int] = {}
    for name in HONEST_N_COUNTS:
        if name not in honest:
            errors.append(f"{path}: missing count {name}")
            continue
        value = honest[name]
        if not _is_int(value) or value < 0:
            errors.append(f"{path}.{name} must be an integer >= 0, found {value!r}")
            continue
        counts[name] = value
    episodes = counts.get("episodes")
    clusters = counts.get("clusters")
    events = counts.get("events")
    if episodes is None or clusters is None or events is None:
        return
    if episodes > clusters:
        errors.append(
            f"{path}: episodes ({episodes}) > clusters ({clusters}); "
            "require episodes <= clusters <= events"
        )
    if clusters > events:
        errors.append(
            f"{path}: clusters ({clusters}) > events ({events}); "
            "require episodes <= clusters <= events"
        )


def _check_gates(payload: dict, errors: list[str]) -> None:
    gates = payload.get("gates")
    if not isinstance(gates, list):
        return
    if len(gates) != 12:
        errors.append(f"gates: expected 12 claims, found {len(gates)}")
    seen: dict[tuple[object, object, object], int] = {}
    found: set[tuple[int, str, str]] = set()
    for index, row in enumerate(gates):
        path = f"gates[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{path} must be an object, found {_type_name(row)}")
            continue
        for key in GATE_KEYS:
            if key not in row:
                errors.append(f"{path}: missing key {key}")
        horizon = row.get("h")
        pop = row.get("pop")
        claim = row.get("claim")
        if horizon not in HORIZONS:
            errors.append(f"{path}.h must be one of {list(HORIZONS)}, found {horizon!r}")
        if pop not in POPULATIONS:
            errors.append(f"{path}.pop must be one of {list(POPULATIONS)}, found {pop!r}")
        if claim not in CLAIMS:
            errors.append(f"{path}.claim must be one of {list(CLAIMS)}, found {claim!r}")
        triple = (horizon, pop, claim)
        if triple in seen:
            errors.append(
                f"gates: duplicate claim h{horizon}/{pop}/{claim} "
                f"(gates[{seen[triple]}] and {path})"
            )
        else:
            seen[triple] = index
        if horizon in HORIZONS and pop in POPULATIONS and claim in CLAIMS:
            found.add((horizon, pop, claim))
            expected_id = f"h{horizon}/{pop}/{claim}"
            if row.get("id") != expected_id:
                errors.append(f"{path}.id must be {expected_id!r}, found {row.get('id')!r}")
        _check_gate_verdict_and_block(row, path, errors)
        _check_gate_numbers(row, path, errors)
        honest = row.get("honest_n")
        if isinstance(honest, dict):
            _check_honest_n(honest, f"{path}.honest_n", errors)
    expected = {
        (h, pop, claim) for h in HORIZONS for pop in POPULATIONS for claim in CLAIMS
    }
    missing = sorted(expected - found)
    if missing:
        rendered = ", ".join(f"h{h}/{pop}/{claim}" for h, pop, claim in missing)
        errors.append(f"gates: missing claim {rendered}")
    horizons_found = {h for h, _pop, _claim in found}
    if horizons_found != set(HORIZONS):
        errors.append(
            f"gates: horizons must be exactly {{5, 10, 21}}, found {sorted(horizons_found)}"
        )


def _check_gate_verdict_and_block(row: dict, path: str, errors: list[str]) -> None:
    verdict = row.get("verdict")
    if verdict not in VERDICTS:
        errors.append(f"{path}.verdict {verdict!r} is not in the prereg §11 verdict set")
    flags = row.get("flags")
    if not isinstance(flags, list) or not all(isinstance(flag, str) for flag in flags):
        errors.append(f"{path}.flags must be an array of strings, found {_type_name(flags)}")
        flags = []
    if row.get("pop") != "P-active":
        return
    blocked_type = row.get("blocked_type")
    if verdict != VERDICT_BLOCKED or OBSERVER_FLAG not in flags or blocked_type != OBSERVER_FLAG:
        errors.append(f"{path}: P-active claim must be blocked with flag {OBSERVER_FLAG}")


def _check_gate_numbers(row: dict, path: str, errors: list[str]) -> None:
    for key in ("point", "lb", "threshold"):
        if key not in row:
            continue
        value = row[key]
        if value is not None and not _is_number(value):
            errors.append(f"{path}.{key} must be a number or null, found {_type_name(value)}")


def _check_inc(payload: dict, errors: list[str]) -> None:
    inc = payload.get("inc")
    if not isinstance(inc, dict):
        return
    if "descriptive_verdict" in inc and inc.get("descriptive_verdict") not in VERDICTS:
        errors.append(
            f"inc.descriptive_verdict {inc.get('descriptive_verdict')!r} "
            "is not in the prereg §11 verdict set"
        )
    if "blocked" in inc and not isinstance(inc.get("blocked"), str):
        errors.append(f"inc.blocked must be a str, found {_type_name(inc.get('blocked'))}")


def _check_string_records(
    payload: dict,
    key: str,
    fields: tuple[str, str],
    errors: list[str],
) -> None:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{key}[{index}] must be an object, found {_type_name(row)}")
            continue
        for field in fields:
            value = row.get(field)
            if not isinstance(value, str) or not value:
                errors.append(f"{key}[{index}].{field} must be a non-empty str, found {value!r}")


def _check_bounds(node: object, path: str, errors: list[str]) -> None:
    """Lower bound must be <= point wherever both are finite numbers."""
    if isinstance(node, dict):
        if "lb" in node and "point" in node:
            _check_lb_point(node.get("lb"), node.get("point"), path or "$", errors)
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            _check_bounds(value, child, errors)
        return
    if isinstance(node, list):
        for index, value in enumerate(node):
            _check_bounds(value, f"{path}[{index}]", errors)


def _check_lb_point(lb: object, point: object, path: str, errors: list[str]) -> None:
    # Condition rows store a structured point (calibration, abstention, power).
    # The inequality applies only when both sides are scalars.
    if isinstance(point, dict):
        return
    if lb is None or point is None:
        return
    if not _is_number(lb) or not _is_number(point):
        return
    if math.isfinite(lb) and math.isfinite(point) and lb > point:
        errors.append(f"{path}: lower bound {lb!r} > point {point!r}")


if __name__ == "__main__":
    raise SystemExit(main())
