"""GLT T22 views composer — display-only projection of qualified records.

Turns already-qualified upstream records (T08 conditional accounting outlook,
T09 statistical forecast package, cross-repo science blocks, replay history)
into a display-only ``views`` block. The module is a pure composer: no file
or network input/output, no clock read, no computation — every number is
copied from an upstream record together with the estimate type that record
declared; a disposition that is not ``supported`` carries a word and no
number; a missing field is named with a reason key, never invented. Every
refusal raises :class:`ViewsContractError` (nothing is coerced and no number
is ever defaulted).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from engine.global_liquidity_knowledge_time import availability_start_utc
from engine import global_liquidity_outlook

VIEW_VERSION = "glt_views_v1"
AUTHORITY = "display_only"
REPLAY_MAX = 8
CROSS_REPO_OWNER = "Mastermind brain/liquidity_lab"
VIEW_NAMES = (
    "conditional_outlook",
    "statistical_forecast",
    "transmission",
    "repricing_evidence",
    "replay",
)
ESTIMATE_TYPES = (
    "announced_scenario",
    "conditional_accounting",
    "statistical_forecast",
    "unavailable",
)
EVIDENCE_LABELS = ("observed_association", "identified_effect")
PRODUCT_DISPOSITIONS = (
    "supported",
    "rejected",
    "insufficient",
    "narrowed",
    "not_identified",
)
SOURCE_DISPOSITION_MAP = {
    "issued": "supported",
    "withheld_no_gain": "rejected",
    "withheld_miscalibrated": "rejected",
    "withheld_insufficient_sample": "insufficient",
    "unavailable": "unavailable",
}
TARGET_KEYS = {"reserves_wresbal_bn": "reserves", "tga_bn": "tga", "rrp_bn": "rrp"}
TARGET_ORDER = ("reserves", "tga", "rrp")
REPLAY_COMPONENTS = ("reserves", "tga", "rrp")
REPLAY_ESTIMATE_TYPES = (
    "observed",
    "announced_scenario",
    "conditional_accounting",
    "unavailable",
)
CORRECTION_NOTE_KEYS = ("source_revised",)
OUTLOOK_UNITS = ("USD_bn",)
CONDITIONING_KEYS = (
    "glt_cond_announced_schedule",
    "glt_cond_hold_level",
    "glt_cond_weekly_change",
)
VIEW_STATUSES = (
    "available",
    "partial",
    "data_degraded",
    "unavailable",
    "no_history",
    "warmup",
)
REASON_KEYS = (
    "science_results_not_published_to_product_plane",
    "outlook_inputs_not_supplied",
    "outlook_unit_not_declared",
    "outlook_anchor_after_as_of",
    "h41_table5_owner_loader_missing",
    "component_unavailable",
    "forecast_package_missing",
    "forecast_package_unreadable",
    "forecast_package_after_as_of",
    "issue_history_not_recorded",
    "issue_history_warming_up",
    "views_compose_failed",
    "views_contract_refused",
    "as_of_mismatch",
)
REFUSED_INPUT_KEYS = (
    "interval",
    "lower",
    "upper",
    "quantiles",
    "quantile",
    "total",
    "probability",
    "probability_interpretation",
    "confidence",
    "glt_confidence",
    "path_claim_allowed",
)

_NUMERIC_VALUE_KEYS = frozenset(
    {
        "level",
        "change_from_anchor",
        "announced_change",
        "assumed_change",
        "point",
        "value",
    }
)
_NUMERIC_ESTIMATE_TYPES = frozenset(
    {
        "announced_scenario",
        "conditional_accounting",
        "statistical_forecast",
        "observed_association",
        "identified_effect",
    }
)
_FORBIDDEN_VIEW_KEYS = frozenset(
    {"total", "glt_confidence", "confidence", "path_claim_allowed", "probability"}
)
_BOOL_NUMBER_KEYS = _NUMERIC_VALUE_KEYS | frozenset({"low", "high", "nominal"})
_OUTLOOK_INPUT_KEYS = frozenset(
    {"anchor", "announcements", "assumptions", "unit", "scenario_bounds"}
)
_EVIDENCE_BLOCK_KEYS = frozenset(
    {
        "status",
        "disposition",
        "label",
        "rows",
        "regions",
        "targets",
        "baseline_comparison",
        "coverage",
        "uncertainty",
        "withholding_reasons",
    }
)
_REPLAY_RECORD_KEYS = frozenset(
    {"known_at", "components_as_known", "estimate_types_as_known", "corrections"}
)
_REPLAY_CORRECTION_KEYS = frozenset({"field", "corrected_at", "note_key"})
_TOP_LEVEL_KEYS = frozenset({"view_version", "as_of", "authority"}) | frozenset(VIEW_NAMES)


class ViewsContractError(ValueError):
    """A display contract was violated; nothing may be coerced past this."""


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------

def _as_day(value: Any) -> date:
    """A datetime.date that is not a datetime, or a 10-char YYYY-MM-DD str."""
    if isinstance(value, datetime):
        raise ViewsContractError("as_of must be a date, not a datetime")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) == 10:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ViewsContractError(f"as_of is not YYYY-MM-DD: {value!r}") from exc
    raise ViewsContractError(f"as_of must be a date or YYYY-MM-DD str: {value!r}")


def _day_str(value: Any, what: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ViewsContractError(f"{what} must be a YYYY-MM-DD str: {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ViewsContractError(f"{what} is not a date: {value!r}") from exc


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scan_refused_keys(node: Any) -> None:
    """Refuse any dict KEY (whole key, never a substring) from the refused set."""
    if isinstance(node, Mapping):
        for key in node:
            if key in REFUSED_INPUT_KEYS:
                raise ViewsContractError(
                    f"outlook input carries refused key {key!r}"
                )
        for value in node.values():
            _scan_refused_keys(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _scan_refused_keys(item)


def _walk_numbers(node: Any) -> list:
    found: list = []

    def _walk(inner: Any) -> None:
        if isinstance(inner, bool):
            return
        if isinstance(inner, (int, float)):
            found.append(inner)
        elif isinstance(inner, Mapping):
            for value in inner.values():
                _walk(value)
        elif isinstance(inner, (list, tuple)):
            for value in inner:
                _walk(value)

    _walk(node)
    return found


# ---------------------------------------------------------------------------
# V3 conditional outlook
# ---------------------------------------------------------------------------

def _announced_published_at(path: Mapping, admitted: list) -> str:
    announcement_ids = set(path.get("support", {}).get("announcement_ids") or [])
    starts = []
    for announcement in admitted:
        if not isinstance(announcement, Mapping):
            continue
        if announcement.get("id") not in announcement_ids:
            continue
        try:
            start = availability_start_utc(
                announcement.get("published_at"),
                announcement.get("publication_tz", global_liquidity_outlook.DEFAULT_PUBLICATION_TZ),
            )
        except (ValueError, TypeError) as exc:
            raise ViewsContractError(
                f"admitted announcement {announcement.get('id')!r} has no availability start"
            ) from exc
        starts.append(start)
    if not starts:
        raise ViewsContractError(
            "announced path cites no admitted announcement for published_at"
        )
    return max(starts).isoformat()


def _conditional_outlook(outlook_inputs: Any, day: date, as_of_str: str) -> dict:
    if outlook_inputs is None:
        return {"status": "unavailable", "reason_key": "outlook_inputs_not_supplied"}
    if not isinstance(outlook_inputs, Mapping):
        raise ViewsContractError("outlook_inputs must be a mapping")
    keys = set(outlook_inputs)
    if keys == {"probe"}:
        snap = outlook_inputs["probe"]
        if not isinstance(snap, Mapping):
            raise ViewsContractError("probe must be a mapping")
        headline = snap.get("headline")
        if not isinstance(headline, Mapping) or headline.get("state") != "data_degraded":
            raise ViewsContractError("probe headline state must be data_degraded")
        if snap.get("as_of") != as_of_str:
            raise ViewsContractError("probe as_of does not match views as_of")
        return {"status": "data_degraded", "reason_key": "h41_table5_owner_loader_missing"}

    required = {"anchor", "announcements", "assumptions"}
    if not required <= keys or not keys <= _OUTLOOK_INPUT_KEYS:
        raise ViewsContractError(
            "outlook_inputs keys must include anchor/announcements/assumptions and be "
            f"a subset of {sorted(_OUTLOOK_INPUT_KEYS)}"
        )
    for key in sorted(keys):
        _scan_refused_keys(outlook_inputs[key])

    unit = outlook_inputs.get("unit")
    if unit not in OUTLOOK_UNITS:
        return {"status": "unavailable", "reason_key": "outlook_unit_not_declared"}

    anchor = outlook_inputs["anchor"]
    announcements = outlook_inputs["announcements"]
    assumptions = outlook_inputs["assumptions"]
    try:
        doc = global_liquidity_outlook.compose_component_paths(
            anchor, announcements, assumptions, as_of=day
        )
        admitted = global_liquidity_outlook.admissible_announcements(
            announcements, as_of=day
        )["admitted"]
    except ViewsContractError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ViewsContractError(f"upstream outlook compose refused: {exc}") from exc

    lineage = doc.get("anchor_lineage") or {}
    if lineage.get("admissible") is False:
        return {"status": "unavailable", "reason_key": "outlook_anchor_after_as_of"}

    paths = doc.get("paths") or {}
    bounds_by_point: dict = {}
    raw_bounds = outlook_inputs.get("scenario_bounds")
    if raw_bounds is not None:
        if not isinstance(raw_bounds, list):
            raise ViewsContractError("scenario_bounds must be a list")
        for entry in raw_bounds:
            if not isinstance(entry, Mapping):
                raise ViewsContractError("a scenario bound must be a mapping")
            if set(entry) != {"component", "horizon_weeks", "low", "high"}:
                raise ViewsContractError(
                    "a scenario bound is exactly component/horizon_weeks/low/high"
                )
            component = entry["component"]
            horizon = entry["horizon_weeks"]
            low, high = entry["low"], entry["high"]
            if not isinstance(horizon, int) or isinstance(horizon, bool):
                raise ViewsContractError("bound horizon_weeks must be an int")
            for bound in (low, high):
                if not _is_number(bound):
                    raise ViewsContractError("bound low/high must be numbers")
            if component == "reserves" or component not in paths:
                raise ViewsContractError(
                    f"scenario bound names unknown component {component!r}"
                )
            path = paths[component]
            if path.get("estimate_type") == "unavailable":
                raise ViewsContractError(
                    f"scenario bound names unavailable component {component!r}"
                )
            horizons = {p["horizon_weeks"] for p in path.get("points") or []}
            if horizon not in horizons:
                raise ViewsContractError(
                    f"scenario bound names unknown horizon {horizon!r}"
                )
            if low > high:
                raise ViewsContractError("bound low exceeds high")
            point_key = (component, horizon)
            if point_key in bounds_by_point:
                raise ViewsContractError("duplicate scenario bound")
            bounds_by_point[point_key] = {"low": low, "high": high}

    assumptions_by_id = {
        a.get("id"): a for a in assumptions if isinstance(a, Mapping)
    }
    assumptions_by_component: dict = {}
    for assumption in assumptions:
        if isinstance(assumption, Mapping):
            assumptions_by_component.setdefault(assumption.get("component"), assumption)

    def _conditioning_key(path: Mapping) -> str:
        estimate_type = path.get("estimate_type")
        if estimate_type == "announced_scenario":
            return "glt_cond_announced_schedule"
        support = path.get("support") or {}
        assumption = assumptions_by_id.get(support.get("assumption_id"))
        if assumption is None:
            assumption = assumptions_by_component.get(path.get("component"))
        if not isinstance(assumption, Mapping):
            raise ViewsContractError(
                "conditional path names no caller assumption for its key"
            )
        kind = assumption.get("kind")
        if kind == "hold_level":
            return "glt_cond_hold_level"
        if kind == "weekly_delta":
            return "glt_cond_weekly_change"
        raise ViewsContractError(f"unsupported assumption kind for conditioning key: {kind!r}")

    components: dict = {}
    conditioning_by_component: dict = {}
    published_by_component: dict = {}
    for name, path in paths.items():
        if not isinstance(path, Mapping):
            raise ViewsContractError("upstream path is not a mapping")
        estimate_type = path.get("estimate_type")
        if estimate_type == "unavailable":
            components[name] = {"component": name, "estimate_type": "unavailable"}
            continue
        if estimate_type not in ("announced_scenario", "conditional_accounting"):
            raise ViewsContractError(
                f"upstream path carries unknown estimate type {estimate_type!r}"
            )
        conditioning_key = _conditioning_key(path)
        if estimate_type == "announced_scenario":
            published = _announced_published_at(path, admitted)
        else:
            published = lineage.get("published_at_utc")
            if not isinstance(published, str):
                raise ViewsContractError("anchor lineage carries no published_at_utc")
        conditioning_by_component[name] = conditioning_key
        published_by_component[name] = published
        points = []
        for point in path.get("points") or []:
            scenario_bounds = bounds_by_point.get((name, point.get("horizon_weeks")))
            points.append(
                {
                    "horizon_weeks": point["horizon_weeks"],
                    "target_date": point["target_date"],
                    "level": point["level"],
                    "change_from_anchor": point["change_from_anchor"],
                    "estimate_type": estimate_type,
                    "conditioning_assumption_key": conditioning_key,
                    "published_at": published,
                    "scenario_bounds": copy.deepcopy(scenario_bounds)
                    if scenario_bounds is not None
                    else None,
                }
            )
        components[name] = {
            "component": name,
            "sign": path["sign"],
            "estimate_type": estimate_type,
            "points": points,
        }

    conditioning_keys = sorted(set(conditioning_by_component.values()))
    reserves_doc = doc.get("reserves") or {}
    if reserves_doc.get("estimate_type") != "unavailable" and reserves_doc.get("points"):
        reserves_points = []
        for point in reserves_doc["points"]:
            horizon = point["horizon_weeks"]
            horizon_published = [
                published_by_component[name]
                for name in conditioning_by_component
                if any(
                    p["horizon_weeks"] == horizon
                    for p in components[name]["points"]
                )
            ]
            reserves_points.append(
                {
                    "horizon_weeks": horizon,
                    "target_date": point["target_date"],
                    "level": point["level"],
                    "announced_change": point["announced_change"],
                    "assumed_change": point["assumed_change"],
                    "estimate_type": reserves_doc["estimate_type"],
                    "conditioning_assumption_keys": list(conditioning_keys),
                    "published_at": max(horizon_published) if horizon_published else None,
                }
            )
        reserves_block = {
            "estimate_type": reserves_doc["estimate_type"],
            "points": reserves_points,
        }
    else:
        reserves_block = {"estimate_type": "unavailable"}

    unavailable_components = [
        name
        for name, block in components.items()
        if block["estimate_type"] == "unavailable"
    ]
    if not unavailable_components:
        view = {"status": "available"}
    elif len(unavailable_components) < len(components):
        view = {
            "status": "partial",
            "reason_key": "component_unavailable",
            "unavailable_components": unavailable_components,
        }
    else:
        view = {
            "status": "unavailable",
            "reason_key": "component_unavailable",
            "unavailable_components": unavailable_components,
        }

    view.update(
        {
            "unit": unit,
            "anchor_observed_on": lineage.get("observed_on"),
            "anchor_published_at": lineage.get("published_at_utc"),
            "admitted_announcement_ids": list(doc.get("admitted_announcement_ids") or []),
            "excluded_announcements": [
                {
                    "id": entry.get("id"),
                    "reason_code": str(entry.get("reason")).split(":")[0],
                }
                for entry in doc.get("excluded_announcements") or []
            ],
            "components": components,
            "reserves": reserves_block,
            "statistical_residual": {"estimate_type": "unavailable"},
        }
    )
    return view


# ---------------------------------------------------------------------------
# V4 statistical forecast
# ---------------------------------------------------------------------------

def _statistical_forecast(t09_package: Any, day: date) -> dict:
    if t09_package is None:
        return {"status": "unavailable", "reason_key": "forecast_package_missing"}
    if not isinstance(t09_package, Mapping):
        raise ViewsContractError("t09_package must be a mapping")
    cells = t09_package.get("cells")
    run = t09_package.get("run")
    if not isinstance(cells, list):
        raise ViewsContractError("t09_package has no cells list")
    if not isinstance(run, Mapping) or not isinstance(run.get("as_of"), str):
        raise ViewsContractError("t09_package has no run.as_of")
    package_day = _day_str(run["as_of"][:10], "run.as_of")
    if package_day > day:
        return {"status": "unavailable", "reason_key": "forecast_package_after_as_of"}

    groups: dict = {}
    for cell in cells:
        if not isinstance(cell, Mapping):
            raise ViewsContractError("a t09 cell must be a mapping")
        target = cell.get("target")
        if target not in TARGET_KEYS:
            raise ViewsContractError(f"unknown t09 target {target!r}")
        horizon = cell.get("horizon_weeks")
        if not isinstance(horizon, int) or isinstance(horizon, bool):
            raise ViewsContractError("t09 horizon_weeks must be an int")
        disposition = cell.get("disposition")
        if disposition not in SOURCE_DISPOSITION_MAP:
            raise ViewsContractError(f"unknown t09 disposition {disposition!r}")
        groups.setdefault((TARGET_KEYS[target], horizon), []).append(cell)

    out_cells = []
    for key in sorted(groups, key=lambda k: (TARGET_ORDER.index(k[0]), k[1])):
        entries = groups[key]
        words = sorted({entry["disposition"] for entry in entries})
        mapped = {SOURCE_DISPOSITION_MAP[word] for word in words}
        supported = [
            entry
            for entry in entries
            if SOURCE_DISPOSITION_MAP[entry["disposition"]] == "supported"
        ]
        if mapped == {"unavailable"}:
            disposition = "unavailable"
        elif len(supported) == 1:
            disposition = "supported"
        elif len(supported) > 1:
            raise ViewsContractError(
                f"group {key} has more than one issued cell"
            )
        elif "insufficient" in mapped:
            disposition = "insufficient"
        else:
            disposition = "rejected"
        out_cell = {
            "target": key[0],
            "horizon_weeks": key[1],
            "disposition": disposition,
            "source_dispositions": words,
            "estimate_type": "statistical_forecast"
            if disposition == "supported"
            else "unavailable",
        }
        if disposition == "supported":
            source = supported[0]
            missing = [
                field
                for field in ("point", "interval", "probability_interpretation", "calibration_ref")
                if source.get(field) is None
            ]
            if missing:
                raise ViewsContractError(
                    f"issued cell for {key} lacks {missing}"
                )
            point = source["point"]
            interval = source["interval"]
            if not _is_number(point):
                raise ViewsContractError("issued point must be a number")
            if not isinstance(interval, Mapping):
                raise ViewsContractError("issued interval must be a mapping")
            for field in ("low", "high", "nominal"):
                if not _is_number(interval.get(field)):
                    raise ViewsContractError(f"issued interval {field} must be a number")
            if not (interval["low"] <= point <= interval["high"]):
                raise ViewsContractError("issued point sits outside its interval")
            for field in ("probability_interpretation", "calibration_ref"):
                value = source[field]
                if not isinstance(value, str) or not value:
                    raise ViewsContractError(f"issued {field} must be a non-empty str")
            out_cell["point"] = point
            out_cell["interval"] = {
                "low": interval["low"],
                "high": interval["high"],
                "nominal": interval["nominal"],
            }
            out_cell["probability_interpretation"] = source["probability_interpretation"]
            out_cell["calibration_ref"] = source["calibration_ref"]
        out_cells.append(out_cell)

    # ``status`` reports package availability (the T09 package is readable and
    # not after as_of). ``disposition`` is the section's own display word, the
    # same vocabulary the sibling sections use: "unavailable" with basis
    # "no_issued_cell" when no cell is supported, so a JSON consumer never reads
    # an all-rejected package as an available forecast (T25 obligation O1).
    issued = sum(1 for cell in out_cells if cell["disposition"] == "supported")
    section = {
        "status": "available",
        "disposition": "available" if issued else "unavailable",
        "package_as_of": package_day.isoformat(),
        "horizons_weeks": sorted({cell["horizon_weeks"] for cell in out_cells}),
        "cells": out_cells,
    }
    if not issued:
        section["disposition_basis"] = "no_issued_cell"
    return section


# ---------------------------------------------------------------------------
# V5 transmission / repricing evidence (shared helper)
# ---------------------------------------------------------------------------

def _copy_text_or_list(value: Any, disposition: str, field: str) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        copied = []
        for item in value:
            if isinstance(item, str):
                copied.append(item)
            elif _is_number(item) and disposition == "supported":
                copied.append(item)
            else:
                raise ViewsContractError(
                    f"{field} may carry str, or a number only when supported"
                )
        return copied
    raise ViewsContractError(f"{field} must be a str or a list of str")


def _evidence_view(name: str, cross_repo: Any) -> dict:
    block = None
    if isinstance(cross_repo, Mapping):
        block = cross_repo.get(name)
    if block is None:
        return {
            "status": "unavailable",
            "reason_key": "science_results_not_published_to_product_plane",
            "owner": CROSS_REPO_OWNER,
        }
    if not isinstance(block, Mapping):
        raise ViewsContractError(f"{name} block must be a mapping")
    extra = set(block) - _EVIDENCE_BLOCK_KEYS
    if extra:
        raise ViewsContractError(f"{name} block carries unallowed keys {sorted(extra)}")
    if block.get("status") != "available":
        raise ViewsContractError(f"{name} block status must be available")
    disposition = block.get("disposition")
    if disposition not in PRODUCT_DISPOSITIONS:
        raise ViewsContractError(f"{name} disposition {disposition!r} is not a product word")
    label = block.get("label")
    if label not in EVIDENCE_LABELS:
        raise ViewsContractError(f"{name} label {label!r} is not an evidence label")
    if label == "identified_effect" and disposition != "supported":
        raise ViewsContractError(
            "an identified_effect label requires a supported disposition"
        )

    rows = block.get("rows")
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise ViewsContractError(f"{name} rows must be a list")
    checked_rows = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"key", "value", "estimate_type"}:
            raise ViewsContractError(
                f"{name} row is exactly key/value/estimate_type"
            )
        if row["estimate_type"] not in EVIDENCE_LABELS:
            raise ViewsContractError(
                f"{name} row estimate_type {row['estimate_type']!r} is not an evidence label"
            )
        value = row["value"]
        if value is not None and not _is_number(value):
            raise ViewsContractError(f"{name} row value must be a number or None")
        checked_rows.append(
            {"key": row["key"], "value": value, "estimate_type": row["estimate_type"]}
        )
    out_rows = copy.deepcopy(checked_rows) if disposition == "supported" else []

    regions = block.get("regions")
    if regions is None:
        regions = []
    if not isinstance(regions, list):
        raise ViewsContractError(f"{name} regions must be a list")
    out_regions = []
    for region in regions:
        if not isinstance(region, Mapping) or set(region) != {"region", "state", "owner"}:
            raise ViewsContractError(f"{name} region is exactly region/state/owner")
        state = region["state"]
        if state not in ("available", "blocked", "missing_input"):
            raise ViewsContractError(f"{name} region state {state!r} is unknown")
        owner = region["owner"]
        if state in ("blocked", "missing_input") and (not isinstance(owner, str) or not owner):
            raise ViewsContractError(
                f"{name} region {region['region']!r} names no owner for its state"
            )
        out_state = "missing_input" if state == "blocked" else state
        out_regions.append(
            {"region": region["region"], "state": out_state, "owner": owner}
        )

    targets = block.get("targets")
    if targets is None:
        targets = []
    if not isinstance(targets, list):
        raise ViewsContractError(f"{name} targets must be a list")
    out_targets = []
    for target in targets:
        if not isinstance(target, Mapping) or set(target) != {"target", "has_card"}:
            raise ViewsContractError(f"{name} target is exactly target/has_card")
        if not isinstance(target["has_card"], bool):
            raise ViewsContractError(f"{name} target has_card must be a bool")
        out_targets.append(
            {
                "target": target["target"],
                "state": "available" if target["has_card"] else "missing",
            }
        )

    baseline_comparison = block.get("baseline_comparison")
    if baseline_comparison is not None:
        if not isinstance(baseline_comparison, Mapping):
            raise ViewsContractError(f"{name} baseline_comparison must be a mapping")
        comparator = baseline_comparison.get("comparator")
        if not isinstance(comparator, str) or not comparator:
            raise ViewsContractError(f"{name} baseline_comparison names no comparator")
        if comparator == "announced_only":
            raise ViewsContractError(
                "announced_only is never an independent comparator"
            )

    view = {
        "status": "available",
        "disposition": disposition,
        "label": label,
        "rows": out_rows,
        "regions": out_regions,
        "targets": out_targets,
    }
    if baseline_comparison is not None:
        view["baseline_comparison"] = copy.deepcopy(baseline_comparison)
    for field in ("coverage", "uncertainty", "withholding_reasons"):
        if field in block:
            view[field] = _copy_text_or_list(block[field], disposition, f"{name}.{field}")
    return view


# ---------------------------------------------------------------------------
# V6 replay (source-known history)
# ---------------------------------------------------------------------------

def _checked_replay_record(record: Any, day: date) -> tuple:
    if not isinstance(record, Mapping) or set(record) != _REPLAY_RECORD_KEYS:
        raise ViewsContractError(
            "a replay record is exactly known_at/components_as_known/"
            "estimate_types_as_known/corrections"
        )
    known_at = record["known_at"]
    known_day = _day_str(known_at, "known_at")
    if known_day > day:
        raise ViewsContractError(
            f"replay known_at {known_at} is after as_of"
        )
    components = record["components_as_known"]
    types = record["estimate_types_as_known"]
    if not isinstance(components, Mapping) or not isinstance(types, Mapping):
        raise ViewsContractError("replay maps must be mappings")
    if not components or set(components) != set(types):
        raise ViewsContractError("replay maps must share one non-empty key set")
    if not set(components) <= set(REPLAY_COMPONENTS):
        raise ViewsContractError("replay components must be reserves/tga/rrp")
    for component in sorted(components):
        value = components[component]
        estimate_type = types[component]
        if estimate_type not in REPLAY_ESTIMATE_TYPES:
            raise ViewsContractError(
                f"replay estimate type {estimate_type!r} is not source-known"
            )
        if value is None:
            if estimate_type != "unavailable":
                raise ViewsContractError("a None replay value must be typed unavailable")
        elif isinstance(value, bool):
            raise ViewsContractError("a bool is never a replay value")
        elif isinstance(value, (int, float)):
            if estimate_type == "unavailable":
                raise ViewsContractError(
                    "a replay number may not be typed unavailable"
                )
        else:
            raise ViewsContractError("a replay value is a number or None")

    corrections = record["corrections"]
    if not isinstance(corrections, list):
        raise ViewsContractError("corrections must be a list")
    checked = []
    for correction in corrections:
        if not isinstance(correction, Mapping) or set(correction) != _REPLAY_CORRECTION_KEYS:
            raise ViewsContractError(
                "a correction is exactly field/corrected_at/note_key"
            )
        if correction["field"] not in components:
            raise ViewsContractError(
                f"a correction names unknown field {correction['field']!r}"
            )
        corrected_day = _day_str(correction["corrected_at"], "corrected_at")
        if not (known_day <= corrected_day <= day):
            raise ViewsContractError(
                "corrected_at must sit between known_at and as_of"
            )
        if correction["note_key"] not in CORRECTION_NOTE_KEYS:
            raise ViewsContractError(
                f"unknown correction note_key {correction['note_key']!r}"
            )
        checked.append(dict(correction))
    return known_day, record, checked


def _replay(history_records: Any, day: date) -> dict:
    if history_records is None:
        return {
            "status": "no_history",
            "reason_key": "issue_history_not_recorded",
            "rows": [],
        }
    if not isinstance(history_records, list):
        raise ViewsContractError("history_records must be a list")
    if not history_records:
        return {"status": "warmup", "reason_key": "issue_history_warming_up", "rows": []}

    seen: set = set()
    parsed = []
    for record in history_records:
        known_day, checked_record, checked_corrections = _checked_replay_record(record, day)
        if checked_record["known_at"] in seen:
            raise ViewsContractError("duplicate replay known_at")
        seen.add(checked_record["known_at"])
        parsed.append((known_day, checked_record, checked_corrections))
    parsed.sort(key=lambda item: item[0], reverse=True)

    rows = []
    for _known_day, record, corrections in parsed[:REPLAY_MAX]:
        corrections = sorted(corrections, key=lambda c: c["corrected_at"])
        rows.append(
            {
                "known_at": record["known_at"],
                "components_as_known": copy.deepcopy(record["components_as_known"]),
                "estimate_types_as_known": copy.deepcopy(record["estimate_types_as_known"]),
                "corrections": corrections,
                "row_state": "corrected" if corrections else "as_known",
            }
        )
    return {"status": "available", "rows": rows}


# ---------------------------------------------------------------------------
# V2 public entry points
# ---------------------------------------------------------------------------

def compose_views(
    envelope,
    history_records,
    t09_package,
    cross_repo=None,
    *,
    as_of,
    outlook_inputs=None,
) -> dict:
    """Compose the five display views from already-qualified records."""
    day = _as_day(as_of)
    as_of_str = day.isoformat()
    if isinstance(envelope, Mapping):
        state = envelope.get("state")
        if isinstance(state, Mapping) and "asof" in state:
            if state["asof"] != as_of_str:
                raise ViewsContractError(
                    f"envelope state.asof {state['asof']!r} != as_of {as_of_str!r}"
                )
    views = {
        "view_version": VIEW_VERSION,
        "as_of": as_of_str,
        "authority": AUTHORITY,
        "conditional_outlook": _conditional_outlook(outlook_inputs, day, as_of_str),
        "statistical_forecast": _statistical_forecast(t09_package, day),
        "transmission": _evidence_view("transmission", cross_repo),
        "repricing_evidence": _evidence_view("repricing_evidence", cross_repo),
        "replay": _replay(history_records, day),
    }
    validate_views(views)
    return views


def failed_views(as_of) -> dict:
    """The never-failing fallback: every view says views_compose_failed."""
    try:
        as_of_str = _as_day(as_of).isoformat()
    except ViewsContractError:
        as_of_str = None
    views = {
        "view_version": VIEW_VERSION,
        "as_of": as_of_str,
        "authority": AUTHORITY,
    }
    for name in VIEW_NAMES:
        views[name] = {"status": "unavailable", "reason_key": "views_compose_failed"}
    return views


# ---------------------------------------------------------------------------
# V7 validation
# ---------------------------------------------------------------------------

def _walk_view_contract(node: Any) -> None:
    if isinstance(node, Mapping):
        carries_number = False
        for key, value in node.items():
            if key in _FORBIDDEN_VIEW_KEYS:
                raise ViewsContractError(f"forbidden view key {key!r}")
            if isinstance(value, bool) and key in _BOOL_NUMBER_KEYS:
                raise ViewsContractError(f"a bool never sits in numeric key {key!r}")
            if (
                _is_number(value)
                and key in _NUMERIC_VALUE_KEYS
            ):
                carries_number = True
        if carries_number and node.get("estimate_type") not in _NUMERIC_ESTIMATE_TYPES:
            raise ViewsContractError(
                "a number under a numeric key carries no declared estimate type"
            )
        for value in node.values():
            if isinstance(value, (Mapping, list, tuple)):
                _walk_view_contract(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            if isinstance(item, (Mapping, list, tuple)):
                _walk_view_contract(item)


def _revalidate_replay_rows(rows: Any) -> None:
    if not isinstance(rows, list):
        raise ViewsContractError("replay rows must be a list")
    previous: str = ""
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != _REPLAY_RECORD_KEYS | {"row_state"}:
            raise ViewsContractError("a replay row carries exactly the recorded keys")
        known_at = row["known_at"]
        _day_str(known_at, "known_at")
        if previous != "" and not (previous > known_at):
            raise ViewsContractError("replay rows must be newest first")
        previous = known_at
        _checked_replay_record(
            {
                "known_at": known_at,
                "components_as_known": row["components_as_known"],
                "estimate_types_as_known": row["estimate_types_as_known"],
                "corrections": row["corrections"],
            },
            date.max,  # corrected_at <= as_of was checked at compose time
        )
        corrections = row["corrections"]
        ordered = sorted(corrections, key=lambda c: c["corrected_at"])
        if corrections != ordered:
            raise ViewsContractError("replay corrections must be sorted by corrected_at")
        if row["row_state"] != ("corrected" if corrections else "as_known"):
            raise ViewsContractError("row_state disagrees with the corrections")


def validate_view(name, block) -> None:
    """Validate one view block; raise ViewsContractError on any violation."""
    if not isinstance(block, Mapping):
        raise ViewsContractError(f"{name} block must be a mapping")
    status = block.get("status")
    if status not in VIEW_STATUSES:
        raise ViewsContractError(f"{name} status {status!r} is not a view status")
    if status != "available" and block.get("reason_key") not in REASON_KEYS:
        raise ViewsContractError(f"{name} status carries no reason key")
    if status in ("unavailable", "no_history", "warmup", "data_degraded"):
        if _walk_numbers(block):
            raise ViewsContractError(f"{name} is degraded yet carries a number")
        if name == "replay" and block.get("rows"):
            raise ViewsContractError(f"{name} degraded replay must carry no rows")
    _walk_view_contract(block)
    if name == "replay" and status == "available":
        _revalidate_replay_rows(block.get("rows"))


def validate_views(views) -> None:
    """Validate the whole views document; raise ViewsContractError on any violation."""
    if not isinstance(views, Mapping) or set(views) != _TOP_LEVEL_KEYS:
        raise ViewsContractError(
            "views carries exactly view_version/as_of/authority and the five names"
        )
    if views["view_version"] != VIEW_VERSION or views["authority"] != AUTHORITY:
        raise ViewsContractError("views version or authority is not this contract")
    as_of = views["as_of"]
    if as_of is None:
        for name in VIEW_NAMES:
            block = views[name]
            if not isinstance(block, Mapping) or block.get("reason_key") != "views_compose_failed":
                raise ViewsContractError(
                    "a null as_of is admissible only for an all-failed views block"
                )
    else:
        _day_str(as_of, "views as_of")
    try:
        json.dumps(views, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ViewsContractError(f"views are not JSON-safe: {exc}") from exc
    for name in VIEW_NAMES:
        validate_view(name, views[name])
