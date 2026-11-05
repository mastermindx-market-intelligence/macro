"""Responsive SVG path geometry for source-bound International Compare cohorts.

Presentation mathematics only. Qualification, source witnesses, normalization,
endpoint identity and observed gaps belong to lib.intl_chart_publication.
Each missing point terminates its path; no lines bridge unobserved dates.
"""
from __future__ import annotations

from copy import deepcopy
import math

import pandas as pd


def _invalid() -> None:
    raise ValueError("invalid_chart_geometry")


def _stamp(value: object) -> int:
    if type(value) is not str:
        _invalid()
    try:
        return int(pd.Timestamp(value).value)
    except (ValueError, TypeError, OverflowError):
        _invalid()


def _line_geometry(line: dict, *, begin: int, finish: int,
                   y_min: float, y_max: float, width: int, height: int) -> dict | None:
    if type(line) is not dict or type(line.get("points")) is not list:
        return None
    count = 0
    segments, current = [], []
    gap_count = 0
    previous = None
    for item in line["points"]:
        if type(item) is not dict:
            return None
        timestamp = item.get("timestamp")
        tick = _stamp(timestamp)
        if tick < begin or tick > finish or (previous is not None and tick <= previous):
            return None
        previous = tick
        value = item.get("rebased")
        if value is None:
            gap_count += 1
            if current:
                segments.append(current)
                current = []
            continue
        if type(value) not in (float, int) or not math.isfinite(float(value)):
            return None
        y_value = float(value)
        if y_value <= 0:
            return None
        x = round((tick - begin) * width / (finish - begin), 2)
        y = round((y_max - y_value) * height / (y_max - y_min), 2)
        if not (0 <= x <= width and 0 <= y <= height):
            return None
        current.append({"x": x, "y": y, "timestamp": timestamp})
        count += 1
    if current:
        segments.append(current)
    if gap_count != line.get("gaps") or count < 2:
        return None
    paths = []
    for block in segments:
        verbs = [
            ("M" if n == 0 else "L") + f"{p['x']:.2f},{p['y']:.2f}"
            for n, p in enumerate(block)
        ]
        paths.append({"d": " ".join(verbs),
                      "first_timestamp": block[0]["timestamp"],
                      "last_timestamp": block[-1]["timestamp"],
                      "first_x": block[0]["x"], "last_x": block[-1]["x"],
                      "first_y": block[0]["y"], "last_y": block[-1]["y"],
                      "count": len(block)})
    return {"slot": line["slot"], "market_id": line["market_id"],
            "status": line["status"], "gaps": gap_count,
            "observations": count, "segments": paths}


def build_chart_geometry(publication: dict, *, width: int = 640, height: int = 220) -> dict:
    """Produce fixed-scale, data-only SVG segments for each comparable cohort.

    The native runtime renders these using governed CSS tokens. No fabricated
    benchmark, market timestamp, source label, rank or interpolate path.
    """
    if (type(width) is not int or type(height) is not int
            or not (1 <= width <= 4096) or not (1 <= height <= 2048)):
        _invalid()
    if type(publication) is not dict or publication.get("schema") != "intl-source-bound-chart.v1":
        _invalid()
    cohorts = publication.get("cohorts")
    lines = publication.get("series")
    if type(cohorts) is not list or type(lines) is not list:
        _invalid()
    result = {"schema": "intl-chart-geometry.v1", "status": "unavailable",
              "reason": "no_comparable_source_bound_cohort",
              "benchmark": deepcopy(publication["benchmark"]), "cohorts": []}
    by_slot = {line["slot"]: line for line in lines}
    if len(by_slot) != len(lines):
        _invalid()
    for group in cohorts:
        if type(group) is not dict or type(group.get("slots")) is not list:
            _invalid()
        window = group["window"]
        start = _stamp(window["start"])
        end = _stamp(window["end"])
        if start >= end:
            continue
        members = [by_slot[s] for s in group["slots"] if s in by_slot]
        if len(members) < 2:
            continue
        values = []
        for line in members:
            if any(line["window"][k] != window[k] for k in ("start", "end", "calendar_policy")):
                continue
            for p in line["points"]:
                if p["rebased"] is not None:
                    v = p["rebased"]
                    if type(v) not in (int, float) or not math.isfinite(float(v)):
                        _invalid()
                    values.append(float(v))
        if len(values) < 4:
            continue
        lo, hi = min(*values, 100.), max(*values, 100.)
        pad = max((hi - lo) * 0.08, 1.)
        lower, upper = max(0., lo - pad), hi + pad
        if upper <= lower:
            continue
        paths = []
        for line in members:
            if any(line["window"][k] != window[k] for k in ("start", "end", "calendar_policy")):
                continue
            geom = _line_geometry(line, begin=start, finish=end,
                                  y_min=lower, y_max=upper,
                                  width=width, height=height)
            if geom is not None:
                paths.append(geom)
        if len(paths) < 2:
            continue
        result["cohorts"].append({
            "id": group["id"], "width": width, "height": height,
            "window": deepcopy(window),
            "min_value": round(lower, 5),
            "max_value": round(upper, 5),
            "baseline_y": round((upper - 100.) * height / (upper - lower), 2),
            "paths": paths,
        })
    if result["cohorts"]:
        result["status"] = ("partial" if publication["status"] == "partial" else "available")
        result["reason"] = "observation_gaps" if result["status"] == "partial" else None
    return result
