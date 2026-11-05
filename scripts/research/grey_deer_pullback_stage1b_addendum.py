"""Render a stage-1b results addendum from the stored results JSON.

The renderer reads one results object plus two imported constants
(``BASE_RATES`` and ``IDENTITY_PINS``). It does not re-run a claim, does not
change a verdict, and does not read a price store. Importing this module
imports ``grey_deer_pullback_stage1b``, whose top level does not open a
price file; parquet reads live inside that module's ``load_panel`` path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.research.grey_deer_pullback_stage1 import BASE_RATES
from scripts.research.grey_deer_pullback_stage1b import IDENTITY_PINS, PANEL_TICKERS

SCHEMA_EXPECTED = "grey_deer_pullback_stage1b/v1"

_REQUIRED_TOP = (
    "schema",
    "status",
    "claims",
    "negative_control",
    "bootstrap_cells",
    "bootstrap",
    "fold_block_table",
    "episodes",
    "comparison",
    "panel",
    "subframe_sha256",
    "inc",
    "blocked",
    "commit_sha",
    "run_commit",
    "script_blob_sha",
    "test_blob_sha",
    "adjust_module_blob_sha",
    "manifest_path",
    "manifest_version",
    "manifest_blob_sha",
    "prereg_path",
    "prereg_blob_sha",
    "dividend_basis",
    "dividend_disclosure",
    "trial_family",
    "trial_budget",
    "trial_counting",
    "seed_root",
    "n_draws",
)

_CLAIM_KEYS = (
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
_P_ALL_KEYS = ("conditions", "honest_n", "loeo")
_P_ACTIVE_KEYS = ("blocked_type", "detail")
_HONEST_KEYS = (
    "origins",
    "ticker_events",
    "events",
    "episodes",
    "clusters",
    "event_months",
    "event_dates",
    "event_month_list",
    "episode_windows",
    "power_floor",
    "per_ticker_episodes",
)
_LOEO_KEYS = ("fragile", "min", "n_episodes")
_POWER_KEYS = ("met", "min_episodes", "min_months")
_FOLD_KEYS = (
    "h",
    "fold",
    "start_index",
    "end_index",
    "start_date",
    "end_date",
    "after_excluded_session",
)
_FAMILIES = ("binary", "quantile")
_NC_FAMILIES = ("m3-ALL-shifted", "q3-ALL-shifted")
_BOOT_VARIANTS = ("primary", "sensitivity_L_h")
_BOOT_FIELDS = ("n_draws", "L", "N_dates", "headline")
_RESULTS_FILE_NAME = "PULLBACK_STAGE1B_RESULTS.json"
_NO_RERUN = (
    "Derived only from the stored results JSON. "
    "No claim was re-run and no verdict changed."
)
_HONEST_HEADLINE = "V(M3)@alpha=b_h"
_DELTA_V_STATISTIC = "delta_v@alpha=b_h"


def _fail(message: str) -> None:
    raise ValueError(message)


def _require(obj: dict, key: str, where: str) -> object:
    if key not in obj:
        _fail(f"missing required key {where}.{key}" if where else f"missing required key {key}")
    return obj[key]


def _expect_dict(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        _fail(f"missing required key {where}: expected an object")
    return value


def _expect_list(value: object, where: str) -> list:
    if not isinstance(value, list):
        _fail(f"missing required key {where}: expected a list")
    return value


def _reject_non_finite(obj: object, where: str) -> None:
    if isinstance(obj, float):
        if not math.isfinite(obj):
            _fail(f"non-finite number at {where}")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            _reject_non_finite(value, f"{where}.{key}")
        return
    if isinstance(obj, list):
        for index, value in enumerate(obj):
            _reject_non_finite(value, f"{where}[{index}]")


def _parse_constant(token: str) -> None:
    _fail(f"refusing non-finite JSON constant: {token}")


def _load_results(raw: bytes) -> dict:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"results JSON is not valid UTF-8: {exc}")
    try:
        data = json.loads(text, parse_constant=_parse_constant)
    except json.JSONDecodeError as exc:
        _fail(f"results JSON could not be parsed: {exc}")
    if not isinstance(data, dict):
        _fail("results JSON must be an object")
    return data


def fmt(value: object) -> str:
    """Render a stored scalar or a small nested value. Floats use ``repr``."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(fmt(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = [f"{key}={fmt(value[key])}" for key in sorted(value, key=str)]
        return "{" + ", ".join(parts) + "}"
    _fail(f"unsupported value type {type(value).__name__}")
    return ""


def _cell(value: object) -> str:
    text = value if isinstance(value, str) else fmt(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[object]]) -> list[str]:
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    lines = [head, sep]
    width = len(headers)
    for row in rows:
        if len(row) != width:
            _fail("internal table width mismatch")
        lines.append("| " + " | ".join(_cell(item) for item in row) + " |")
    return lines


def _flatten(value: object, prefix: str) -> list[tuple[str, object]]:
    if isinstance(value, dict):
        rows: list[tuple[str, object]] = []
        for key in sorted(value, key=str):
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(value[key], child))
        return rows
    if isinstance(value, list) and any(isinstance(item, (dict, list)) for item in value):
        rows = []
        for index, item in enumerate(value):
            rows.extend(_flatten(item, f"{prefix}[{index}]"))
        return rows
    return [(prefix, value)]


def _bullets(value: object, prefix: str = "") -> list[str]:
    return [f"- {path}: {fmt(item)}" for path, item in _flatten(value, prefix)]


def _is_delta_v(statistic: object) -> bool:
    if not isinstance(statistic, str):
        return False
    return statistic.strip().split(" ", 1)[0].startswith("delta_v")


def _is_v_m3_at_b(statistic: object) -> bool:
    if not isinstance(statistic, str):
        return False
    return statistic.strip().split(" ", 1)[0] == "v_m3@alpha=b"


def _horizon_key(h: object, where: str) -> str:
    if isinstance(h, bool) or not isinstance(h, int):
        _fail(f"{where} h must be an int")
    return f"h{h}"


def _horizon_sort(key: str) -> tuple:
    if key.startswith("h") and key[1:].isdigit():
        return (0, int(key[1:]))
    return (1, key)


def _as_number(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{where} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        _fail(f"{where} must be finite")
    return float(value)


def _flags(value: object, where: str) -> str:
    flags = _expect_list(value, where)
    if not flags:
        return "(empty)"
    return ", ".join(str(flag) for flag in flags)


def _index_summary(values: object, where: str) -> tuple[str, str, str]:
    rows = _expect_list(values, where)
    if not rows:
        return ("0", "null", "null")
    return (str(len(rows)), fmt(rows[0]), fmt(rows[-1]))


def _windows(values: object, where: str) -> str:
    rows = _expect_list(values, where)
    if not rows:
        return "(empty)"
    parts: list[str] = []
    for item in rows:
        if (
            isinstance(item, list)
            and len(item) == 2
            and all(isinstance(end, (int, float)) and not isinstance(end, bool) for end in item)
        ):
            parts.append(f"{fmt(item[0])}..{fmt(item[1])}")
        else:
            parts.append(fmt(item))
    return "; ".join(parts)


def _family_config(claim: str) -> str:
    if claim == "binary":
        return "M3-ALL"
    if claim == "quantile":
        return "Q3-ALL"
    _fail(f"unknown claim family {claim!r}")
    return ""


def _validate_claim(claim: object, index: int) -> dict:
    where = f"claims[{index}]"
    row = _expect_dict(claim, where)
    for key in _CLAIM_KEYS:
        _require(row, key, where)
    pop = row["pop"]
    if pop == "P-all":
        for key in _P_ALL_KEYS:
            _require(row, key, where)
        _expect_list(row["conditions"], f"{where}.conditions")
        honest = _expect_dict(row["honest_n"], f"{where}.honest_n")
        for key in _HONEST_KEYS:
            _require(honest, key, f"{where}.honest_n")
        power = _expect_dict(honest["power_floor"], f"{where}.honest_n.power_floor")
        for key in _POWER_KEYS:
            _require(power, key, f"{where}.honest_n.power_floor")
        loeo = _expect_dict(row["loeo"], f"{where}.loeo")
        for key in _LOEO_KEYS:
            _require(loeo, key, f"{where}.loeo")
        _expect_dict(loeo["min"], f"{where}.loeo.min")
    elif pop == "P-active":
        for key in _P_ACTIVE_KEYS:
            _require(row, key, where)
    else:
        _fail(f"{where}.pop is {pop!r}")
    if row["claim"] not in _FAMILIES:
        _fail(f"{where}.claim is {row['claim']!r}")
    _expect_list(row["flags"], f"{where}.flags")
    _horizon_key(row["h"], where)
    if not isinstance(row["id"], str) or not row["id"]:
        _fail(f"{where}.id must be a non-empty string")
    return row


def _collect_horizons(results: dict, claims: list[dict]) -> list[str]:
    keys: set[str] = set()
    for claim in claims:
        keys.add(_horizon_key(claim["h"], claim["id"]))
    for section in ("negative_control", "bootstrap_cells", "episodes", "comparison"):
        block = _expect_dict(results[section], section)
        for key in block:
            if not isinstance(key, str):
                _fail(f"{section} key {key!r} must be a string")
            keys.add(key)
    horizons = sorted(keys, key=_horizon_sort)
    for section, families in (
        ("negative_control", _NC_FAMILIES),
        ("bootstrap_cells", _FAMILIES),
        ("episodes", _FAMILIES),
        ("comparison", _FAMILIES),
    ):
        block = results[section]
        for horizon in horizons:
            if horizon not in block:
                _fail(f"missing required key {section}.{horizon}")
            cell = _expect_dict(block[horizon], f"{section}.{horizon}")
            for family in families:
                if family not in cell:
                    _fail(f"missing required key {section}.{horizon}.{family}")
    return horizons


def _validate_bootstrap(bootstrap_cells: dict, horizons: list[str]) -> None:
    for horizon in horizons:
        for family in _FAMILIES:
            cell = _expect_dict(
                bootstrap_cells[horizon][family],
                f"bootstrap_cells.{horizon}.{family}",
            )
            for variant in _BOOT_VARIANTS:
                if variant not in cell:
                    _fail(f"missing required key bootstrap_cells.{horizon}.{family}.{variant}")
                block = _expect_dict(cell[variant], f"bootstrap_cells.{horizon}.{family}.{variant}")
                for field in _BOOT_FIELDS:
                    _require(block, field, f"bootstrap_cells.{horizon}.{family}.{variant}")


def _validate_episodes(episodes: dict, horizons: list[str]) -> None:
    for horizon in horizons:
        for family in _FAMILIES:
            cell = _expect_dict(episodes[horizon][family], f"episodes.{horizon}.{family}")
            if "episode_windows" not in cell:
                _fail(f"missing required key episodes.{horizon}.{family}.episode_windows")
            _expect_list(cell["episode_windows"], f"episodes.{horizon}.{family}.episode_windows")


def _validate_folds(rows: object) -> list:
    table = _expect_list(rows, "fold_block_table")
    for index, row in enumerate(table):
        item = _expect_dict(row, f"fold_block_table[{index}]")
        for key in _FOLD_KEYS:
            _require(item, key, f"fold_block_table[{index}]")
    return table


def _validate_hashes(subframe: object) -> dict:
    hashes = _expect_dict(subframe, "subframe_sha256")
    got = set(hashes)
    want = set(PANEL_TICKERS)
    if got != want:
        _fail(
            "subframe_sha256 tickers "
            f"{sorted(str(item) for item in got)} != panel tickers {list(PANEL_TICKERS)}"
        )
    for ticker in PANEL_TICKERS:
        if ticker not in IDENTITY_PINS:
            _fail(f"missing required key IDENTITY_PINS.{ticker}")
        pin = IDENTITY_PINS[ticker]
        for field in ("subframe_sha256", "rows", "first_date", "last_date"):
            if field not in pin:
                _fail(f"missing required key IDENTITY_PINS.{ticker}.{field}")
        if not isinstance(hashes[ticker], str):
            _fail(f"subframe_sha256.{ticker} must be a string")
    return hashes


def _delta_v_condition(claim: dict) -> dict:
    conditions = claim["conditions"]
    found: list[dict] = []
    for index, condition in enumerate(conditions):
        row = _expect_dict(condition, f"{claim['id']}.conditions[{index}]")
        if "statistic" not in row:
            _fail(f"missing required key {claim['id']}.conditions[{index}].statistic")
        if _is_delta_v(row["statistic"]):
            found.append(row)
    if len(found) != 1:
        _fail(f"{claim['id']}: expected one delta-V condition by name, found {len(found)}")
    chosen = found[0]
    for field in ("point", "lb"):
        if field not in chosen:
            _fail(f"missing required key {claim['id']} delta-V condition.{field}")
    return chosen


def _confirm_headline_is_v_m3(claim: dict) -> None:
    found: list[dict] = []
    for index, condition in enumerate(claim["conditions"]):
        row = _expect_dict(condition, f"{claim['id']}.conditions[{index}]")
        if _is_v_m3_at_b(row.get("statistic")):
            found.append(row)
    if len(found) != 1:
        _fail(f"{claim['id']}: expected one v_m3@alpha=b condition by name, found {len(found)}")
    chosen = found[0]
    if chosen.get("point") != claim["point"] or chosen.get("lb") != claim["lb"]:
        _fail(f"{claim['id']}: stored headline point/lb differ from the v_m3@alpha=b condition")


def _blank(lines: list[str]) -> None:
    if not lines or lines[-1] != "":
        lines.append("")


def _section(lines: list[str], title: str) -> None:
    _blank(lines)
    lines.append(f"## {title}")
    lines.append("")


def _render_provenance(lines: list[str], results: dict, results_sha256: str, results_ref: str) -> None:
    lines.append("# Pullback stage-1b results addendum")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- results file: `{_RESULTS_FILE_NAME}`")
    lines.append(f"- results sha256: `{results_sha256}`")
    lines.append(f"- results_ref: `{results_ref}`")
    lines.append(f"- schema: `{results['schema']}`")
    lines.append("")
    lines.append(_NO_RERUN)
    lines.append("")
    lines.append("Stored run fields copied from the results JSON:")
    lines.append("")
    for key in (
        "status",
        "commit_sha",
        "run_commit",
        "script_blob_sha",
        "test_blob_sha",
        "adjust_module_blob_sha",
        "manifest_path",
        "manifest_version",
        "manifest_blob_sha",
        "prereg_path",
        "prereg_blob_sha",
        "dividend_basis",
        "trial_family",
        "trial_budget",
        "seed_root",
        "n_draws",
    ):
        lines.append(f"- {key}: {fmt(results[key])}")
    lines.append("- trial_counting:")
    lines.extend(f"  {line}" for line in _bullets(results["trial_counting"]))
    lines.append("- bootstrap:")
    lines.extend(f"  {line}" for line in _bullets(results["bootstrap"]))
    lines.append("- dividend_disclosure: " + fmt(results["dividend_disclosure"]))
    blocked = _expect_list(results["blocked"], "blocked")
    if blocked:
        lines.append("- blocked:")
        lines.extend(f"  {line}" for line in _bullets(blocked, "blocked"))
    else:
        lines.append("- blocked: (empty)")


def _render_claim_index(lines: list[str], claims: list[dict]) -> None:
    _section(lines, "Stored claim verdicts")
    lines.append("Claim verdicts below are copied from the stored JSON.")
    lines.append("")
    lines.append(f"Stored claim rows: {len(claims)}.")
    lines.append("")
    lines.extend(
        _table(
            [
                "id",
                "h",
                "pop",
                "claim",
                "stored_statistic",
                "stored_point",
                "stored_lb",
                "stored_threshold",
                "flags",
                "stored_verdict",
            ],
            [
                [
                    claim["id"],
                    claim["h"],
                    claim["pop"],
                    claim["claim"],
                    claim["statistic"],
                    claim["point"],
                    claim["lb"],
                    claim["threshold"],
                    _flags(claim["flags"], f"{claim['id']}.flags"),
                    claim["verdict"],
                ]
                for claim in claims
            ],
        )
    )
    active = [claim for claim in claims if claim["pop"] == "P-active"]
    if active:
        lines.append("")
        lines.append("P-active rows store null `statistic`, `point`, `lb` and `threshold`.")
        lines.append("")
        lines.extend(
            _table(
                ["id", "stored_verdict", "blocked_type", "detail", "flags"],
                [
                    [
                        claim["id"],
                        claim["verdict"],
                        claim["blocked_type"],
                        claim["detail"],
                        _flags(claim["flags"], f"{claim['id']}.flags"),
                    ]
                    for claim in active
                ],
            )
        )


def _render_f1(lines: list[str], claims: list[dict]) -> None:
    _section(lines, "F1. Stored headline label")
    lines.append(
        "For each P-all claim whose stored statistic is `delta_v@alpha=b_h`, "
        "the stored point and lb are labelled V(M3)@alpha=b_h. "
        "The frozen stage-1 helper copies `conditions[1]` into those fields. "
        "That condition's statistic is `v_m3@alpha=b`. "
        "The delta-V point and lb come from the condition whose statistic name begins with `delta_v`."
    )
    lines.append("")
    lines.append("Verdicts are computed separately and are unaffected.")
    lines.append("")
    repaired: list[list[object]] = []
    others: list[list[object]] = []
    for claim in claims:
        if claim["pop"] != "P-all":
            continue
        if claim["statistic"] == _DELTA_V_STATISTIC:
            _confirm_headline_is_v_m3(claim)
            delta = _delta_v_condition(claim)
            repaired.append(
                [
                    claim["id"],
                    claim["statistic"],
                    _HONEST_HEADLINE,
                    claim["point"],
                    claim["lb"],
                    delta["statistic"],
                    delta["point"],
                    delta["lb"],
                    claim["verdict"],
                ]
            )
        else:
            others.append(
                [
                    claim["id"],
                    claim["statistic"],
                    claim["point"],
                    claim["lb"],
                    claim["verdict"],
                ]
            )
    if repaired:
        lines.extend(
            _table(
                [
                    "id",
                    "stored_statistic",
                    "honest_label_of_stored_point_and_lb",
                    "stored_point",
                    "stored_lb",
                    "delta_v_statistic_name",
                    "delta_v_point",
                    "delta_v_lb",
                    "stored_verdict",
                ],
                repaired,
            )
        )
    else:
        lines.append("No stored claim has statistic `delta_v@alpha=b_h`.")
    lines.append("")
    lines.append(
        "P-all claims whose stored statistic is not `delta_v@alpha=b_h` "
        "are not given that label. No delta-V number is invented for them."
    )
    lines.append("")
    if others:
        lines.extend(
            _table(
                ["id", "stored_statistic", "stored_point", "stored_lb", "stored_verdict"],
                others,
            )
        )
    else:
        lines.append("No other P-all claim is stored.")


def _abstention_conditions(claim: dict) -> list[dict]:
    found: list[dict] = []
    for index, condition in enumerate(claim.get("conditions") or []):
        row = _expect_dict(condition, f"{claim['id']}.conditions[{index}]")
        point = row.get("point")
        statistic = row.get("statistic")
        named = isinstance(statistic, str) and statistic.strip().startswith("abstention")
        has_table = isinstance(point, dict) and "by_type" in point
        if named or has_table:
            if not isinstance(point, dict) or "by_type" not in point:
                _fail(f"missing required key {claim['id']}.conditions[{index}].point.by_type")
            if not isinstance(point["by_type"], dict):
                _fail(f"{claim['id']}.conditions[{index}].point.by_type must be an object")
            found.append(row)
    return found


def _render_f2(lines: list[str], claims: list[dict]) -> None:
    _section(lines, "F2. Abstention tables present; eligibility census absent")
    lines.append(
        "The D12 eligibility/maturity census is absent from the stored results JSON. "
        "It cannot be recovered without re-running on real data. "
        "This is a disclosed deviation. No census count is estimated here."
    )
    lines.append("")
    lines.append(
        "Abstention tables that do exist are `claims[].conditions[].point.by_type` "
        "on M3-ALL (binary) and Q3-ALL (quantile)."
    )
    found_any = False
    preferred = ("rate", "gap_pp", "issued", "abstained")
    for claim in claims:
        if claim["pop"] != "P-all":
            continue
        for condition in _abstention_conditions(claim):
            found_any = True
            point = condition["point"]
            lines.append("")
            lines.append(f"### {claim['id']} ({_family_config(claim['claim'])})")
            lines.append("")
            lines.append(f"- statistic: {fmt(condition.get('statistic'))}")
            seen = set()
            for key in preferred:
                if key in point:
                    lines.append(f"- {key}: {fmt(point[key])}")
                    seen.add(key)
            for key in sorted(point, key=str):
                if key in seen or key == "by_type":
                    continue
                lines.append(f"- {key}: {fmt(point[key])}")
            by_type = point["by_type"]
            lines.append("")
            if by_type:
                lines.extend(
                    _table(
                        ["abstention_type", "count"],
                        [[key, by_type[key]] for key in sorted(by_type, key=str)],
                    )
                )
            else:
                lines.append("stored by_type is empty.")
    if not found_any:
        lines.append("")
        lines.append("No `by_type` abstention table is stored on the claims.")


def _render_f3(lines: list[str], subframe: dict) -> None:
    _section(lines, "F3. Per-ticker subframe identity")
    lines.append(
        "Each row is one panel ticker. `subframe_sha256` is the stored results value. "
        "`rows`, `first_date` and `last_date` are `IDENTITY_PINS` imported from "
        "`scripts/research/grey_deer_pullback_stage1b.py` and are not copied into this module. "
        "`hash_equals_pin` is `true` when the stored hash equals the imported pin hash. "
        "This addendum does not re-read a price subframe."
    )
    lines.append("")
    rows: list[list[object]] = []
    for ticker in PANEL_TICKERS:
        pin = IDENTITY_PINS[ticker]
        stored_hash = subframe[ticker]
        rows.append(
            [
                ticker,
                stored_hash,
                pin["rows"],
                pin["first_date"],
                pin["last_date"],
                "true" if stored_hash == pin["subframe_sha256"] else "false",
            ]
        )
    lines.extend(
        _table(
            ["ticker", "subframe_sha256", "rows", "first_date", "last_date", "hash_equals_pin"],
            rows,
        )
    )


def _render_f4(lines: list[str], table: list) -> None:
    _section(lines, "F4. Fold block table")
    lines.append(f"Stored `fold_block_table` rows: {len(table)}.")
    lines.append("")
    lines.append(
        "Per-year, per-test-block and rv20-tercile breakdowns are absent from the stored JSON."
    )
    fold8 = [row["start_date"] for row in table if row.get("fold") == 8]
    unique: list[object] = []
    for item in fold8:
        if item not in unique:
            unique.append(item)
    if unique == ["2026-04-13"]:
        lines.append(
            "Block-level performance, including the latest block 8 (2026-04-13 onward), "
            "is not stored and is unreported. This addendum does not estimate it."
        )
    else:
        lines.append(
            "Block-level performance is not stored and is unreported. "
            "This addendum does not estimate it."
        )
        if unique:
            shown = ", ".join(fmt(item) for item in unique)
            lines.append(f"Stored block 8 start_date values: {shown}.")
    lines.append("")
    lines.extend(
        _table(
            [
                "h",
                "fold",
                "start_index",
                "end_index",
                "start_date",
                "end_date",
                "after_excluded_session",
            ],
            [
                [
                    row["h"],
                    row["fold"],
                    row["start_index"],
                    row["end_index"],
                    row["start_date"],
                    row["end_date"],
                    row["after_excluded_session"],
                ]
                for row in table
            ],
        )
    )


def _render_f5(lines: list[str], negative: dict, horizons: list[str]) -> None:
    _section(lines, "F5. Negative control")
    lines.append(
        "Stored `negative_control` for every horizon and both families "
        "(`m3-ALL-shifted`, `q3-ALL-shifted`)."
    )
    for horizon in horizons:
        cell = negative[horizon]
        lines.append("")
        lines.append(f"### {horizon}")
        lines.append("")
        for key in ("expectation", "shift"):
            if key in cell:
                lines.append(f"- {key}: {fmt(cell[key])}")
        extras = [key for key in sorted(cell, key=str) if key not in ("expectation", "shift", *_NC_FAMILIES)]
        for key in extras:
            lines.append(f"- {key}: {fmt(cell[key])}")
        for family in _NC_FAMILIES:
            block = _expect_dict(cell[family], f"negative_control.{horizon}.{family}")
            lines.append("")
            lines.append(f"#### {family}")
            lines.append("")
            if not block:
                lines.append("stored object is empty.")
                continue
            for key in sorted(block, key=str):
                lines.append(f"- {key}: {fmt(block[key])}")


def _render_f6(lines: list[str], claims: list[dict], episodes: dict) -> None:
    _section(lines, "F6. Leave-one-episode-out")
    lines.append(
        "`loeo` stores `min`, `fragile` and `n_episodes` only. "
        "Episode windows are the stored `episodes` windows for that horizon and family. "
        "The episode whose deletion moves the estimate most cannot be named from the stored data."
    )
    for claim in claims:
        if claim["pop"] != "P-all":
            continue
        horizon = _horizon_key(claim["h"], claim["id"])
        family = claim["claim"]
        cell = episodes[horizon][family]
        loeo = claim["loeo"]
        lines.append("")
        lines.append(f"### {claim['id']}")
        lines.append("")
        lines.append(f"- fragile: {fmt(loeo['fragile'])}")
        lines.append(f"- n_episodes: {fmt(loeo['n_episodes'])}")
        minima = loeo["min"]
        if minima:
            for key in sorted(minima, key=str):
                lines.append(f"- min.{key}: {fmt(minima[key])}")
        else:
            lines.append("- min: stored object is empty.")
        lines.append(
            f"- episode_windows (`episodes.{horizon}.{family}.episode_windows`): "
            f"{_windows(cell['episode_windows'], f'episodes.{horizon}.{family}.episode_windows')}"
        )
        honest_windows = claim["honest_n"]["episode_windows"]
        if honest_windows == cell["episode_windows"]:
            lines.append("- `honest_n.episode_windows` matches the episode windows above.")
        else:
            where = f"{claim['id']}.honest_n.episode_windows"
            lines.append(f"- `honest_n.episode_windows`: {_windows(honest_windows, where)}")


def _render_f7(lines: list[str], comparison: dict, horizons: list[str]) -> None:
    _section(lines, "F7. Comparison fields present")
    lines.append(
        "Descriptive baseline-vs-baseline intervals (B1/B2 vs B0, Q1 vs Q0) are not in the payload. "
        "`comparison.*.binary.sensitivity` metrics are not in the payload. "
        "Both are disclosed deviations and are not estimated. "
        "What is stored (`N_common`, and where present `config`, `n`, `note`) is below."
    )
    preferred = ("config", "n", "note")
    for horizon in horizons:
        for family in _FAMILIES:
            cell = _expect_dict(comparison[horizon][family], f"comparison.{horizon}.{family}")
            lines.append("")
            lines.append(f"### {horizon} {family}")
            lines.append("")
            if "N_common" not in cell:
                _fail(f"missing required key comparison.{horizon}.{family}.N_common")
            lines.append(f"- N_common: {fmt(cell['N_common'])}")
            sensitivity = cell.get("sensitivity")
            if sensitivity is None:
                lines.append("- sensitivity: absent")
            else:
                block = _expect_dict(sensitivity, f"comparison.{horizon}.{family}.sensitivity")
                seen = set()
                for key in preferred:
                    if key in block:
                        lines.append(f"- sensitivity.{key}: {fmt(block[key])}")
                        seen.add(key)
                for key in sorted(block, key=str):
                    if key in seen:
                        continue
                    lines.append(f"- sensitivity.{key}: {fmt(block[key])}")
            for key in sorted(cell, key=str):
                if key in ("N_common", "sensitivity"):
                    continue
                lines.append(f"- {key}: {fmt(cell[key])}")


def _render_bootstrap(lines: list[str], bootstrap_cells: dict, horizons: list[str]) -> None:
    _section(lines, "Bootstrap cells")
    lines.append(
        "Stored `bootstrap_cells` for every horizon and family, primary and `sensitivity_L_h`: "
        "`n_draws`, `L`, `N_dates`, and `headline`."
    )
    for horizon in horizons:
        for family in _FAMILIES:
            cell = bootstrap_cells[horizon][family]
            for variant in _BOOT_VARIANTS:
                block = cell[variant]
                lines.append("")
                lines.append(f"### {horizon} {family} {variant}")
                lines.append("")
                for field in _BOOT_FIELDS:
                    if field == "headline":
                        continue
                    lines.append(f"- {field}: {fmt(block[field])}")
                for key in sorted(block, key=str):
                    if key in _BOOT_FIELDS or key == "seed":
                        continue
                    lines.append(f"- {key}: {fmt(block[key])}")
                lines.append("- headline:")
                headline = block["headline"]
                flat = _flatten(headline, "headline")
                if not flat:
                    lines.append("  - stored object is empty.")
                else:
                    for path, value in flat:
                        lines.append(f"  - {path}: {fmt(value)}")
                if "seed" in block:
                    lines.append(f"- seed: {fmt(block['seed'])}")


def _derived_rates(claim: dict) -> tuple[float, float]:
    honest = claim["honest_n"]
    origins = _as_number(honest["origins"], f"{claim['id']}.honest_n.origins")
    ticker_events = _as_number(honest["ticker_events"], f"{claim['id']}.honest_n.ticker_events")
    if origins == 0:
        _fail(f"{claim['id']}.honest_n.origins is 0")
    if claim["h"] not in BASE_RATES:
        _fail(f"missing frozen b_h for h={claim['h']!r} in BASE_RATES")
    rate = ticker_events / origins
    return rate, rate / float(BASE_RATES[claim["h"]])


def _ticker_order(keys: list[str]) -> list[str]:
    panel = [ticker for ticker in PANEL_TICKERS if ticker in keys]
    extra = sorted(ticker for ticker in keys if ticker not in panel)
    return panel + extra


def _render_honest_n(lines: list[str], claims: list[dict]) -> None:
    _section(lines, "Honest-N and frozen base rates")
    lines.append(
        "Frozen b_h values are `BASE_RATES` imported from "
        "`scripts/research/grey_deer_pullback_stage1.py`. They are not retyped."
    )
    lines.append("")
    for horizon in sorted(BASE_RATES):
        lines.append(f"- h={horizon}: `{fmt(BASE_RATES[horizon])}`")
    lines.append("")
    lines.append(
        "`derived_row_base_rate` equals `ticker_events / origins`. "
        "`derived_rate_over_b_h` equals that rate divided by frozen b_h. "
        "Both columns are derived in this addendum. Every other column is stored."
    )
    lines.append("")
    lines.append(
        "Event-date index lists are summarised by count, first stored entry and last stored entry. "
        "They are not dumped."
    )
    lines.append("")
    rate_rows: list[list[object]] = []
    summary_rows: list[list[object]] = []
    ticker_rows: list[list[object]] = []
    for claim in claims:
        if claim["pop"] != "P-all":
            continue
        honest = claim["honest_n"]
        rate, ratio = _derived_rates(claim)
        power = honest["power_floor"]
        rate_rows.append(
            [
                claim["id"],
                honest["origins"],
                honest["ticker_events"],
                rate,
                BASE_RATES[claim["h"]],
                ratio,
                honest["events"],
                honest["clusters"],
                honest["episodes"],
                honest["event_months"],
                power["met"],
                power["min_episodes"],
                power["min_months"],
            ]
        )
        date_count, date_first, date_last = _index_summary(
            honest["event_dates"], f"{claim['id']}.honest_n.event_dates"
        )
        month_count, month_first, month_last = _index_summary(
            honest["event_month_list"], f"{claim['id']}.honest_n.event_month_list"
        )
        summary_rows.append(
            [
                claim["id"],
                date_count,
                date_first,
                date_last,
                month_count,
                month_first,
                month_last,
            ]
        )
        per_ticker = _expect_dict(
            honest["per_ticker_episodes"], f"{claim['id']}.honest_n.per_ticker_episodes"
        )
        for ticker in _ticker_order([str(key) for key in per_ticker]):
            ticker_rows.append([claim["id"], ticker, per_ticker[ticker]])
    lines.extend(
        _table(
            [
                "id",
                "origins",
                "ticker_events",
                "derived_row_base_rate",
                "frozen_b_h",
                "derived_rate_over_b_h",
                "events",
                "clusters",
                "episodes",
                "event_months",
                "power_floor_met",
                "power_min_episodes",
                "power_min_months",
            ],
            rate_rows,
        )
    )
    lines.append("")
    lines.extend(
        _table(
            [
                "id",
                "event_dates_count",
                "event_dates_first",
                "event_dates_last",
                "event_month_list_count",
                "event_month_first",
                "event_month_last",
            ],
            summary_rows,
        )
    )
    lines.append("")
    lines.append("Stored `per_ticker_episodes`:")
    lines.append("")
    if ticker_rows:
        lines.extend(_table(["id", "ticker", "per_ticker_episodes"], ticker_rows))
    else:
        lines.append("stored per_ticker_episodes objects are empty.")


def _render_panel_inc(lines: list[str], results: dict) -> None:
    _section(lines, "Stored panel and INC")
    lines.append("Stored `panel`:")
    lines.append("")
    lines.extend(_bullets(_expect_dict(results["panel"], "panel")))
    lines.append("")
    lines.append("Stored `inc`:")
    lines.append("")
    lines.extend(_bullets(_expect_dict(results["inc"], "inc")))


def render_addendum(results: dict, *, results_sha256: str, results_ref: str) -> str:
    if not isinstance(results_sha256, str) or not isinstance(results_ref, str):
        _fail("results_sha256 and results_ref must be strings")
    if not isinstance(results, dict):
        _fail("results must be a JSON object")
    _reject_non_finite(results, "results")
    for key in _REQUIRED_TOP:
        if key not in results:
            _fail(f"missing required key {key}")
    if results["schema"] != SCHEMA_EXPECTED:
        _fail(f"schema mismatch: {results['schema']!r} != {SCHEMA_EXPECTED!r}")
    raw_claims = _expect_list(results["claims"], "claims")
    claims = [_validate_claim(claim, index) for index, claim in enumerate(raw_claims)]
    horizons = _collect_horizons(results, claims)
    _validate_bootstrap(results["bootstrap_cells"], horizons)
    _validate_episodes(results["episodes"], horizons)
    folds = _validate_folds(results["fold_block_table"])
    hashes = _validate_hashes(results["subframe_sha256"])
    _expect_dict(results["negative_control"], "negative_control")
    _expect_dict(results["comparison"], "comparison")
    _expect_dict(results["panel"], "panel")
    _expect_dict(results["inc"], "inc")
    _expect_dict(results["bootstrap"], "bootstrap")
    _expect_dict(results["trial_counting"], "trial_counting")

    lines: list[str] = []
    _render_provenance(lines, results, results_sha256, results_ref)
    _render_claim_index(lines, claims)
    _render_f1(lines, claims)
    _render_f2(lines, claims)
    _render_f3(lines, hashes)
    _render_f4(lines, folds)
    _render_f5(lines, results["negative_control"], horizons)
    _render_f6(lines, claims, results["episodes"])
    _render_f7(lines, results["comparison"], horizons)
    _render_bootstrap(lines, results["bootstrap_cells"], horizons)
    _render_honest_n(lines, claims)
    _render_panel_inc(lines, results)
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the stage-1b results addendum from a stored results JSON file."
    )
    parser.add_argument("--results", required=True, help="path to the results JSON")
    parser.add_argument("--out", required=True, help="path to write the markdown addendum")
    parser.add_argument("--ref", default="", help="results ref recorded in the provenance block")
    args = parser.parse_args(argv)
    raw = Path(args.results).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    results = _load_results(raw)
    text = render_addendum(results, results_sha256=digest, results_ref=args.ref)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
