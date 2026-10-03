"""Frozen aggregate statistics for terminal tactical R1B prereg study (synthetic / in-memory only)."""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable, Mapping

import numpy as np

READINGS = ("L-A", "L-B", "S-A", "S-B")


def event_delta(row: Mapping[str, Any], reading: str, *, floor: int) -> float | None:
    if row["pool_availability"] != "AVAILABLE":
        return None
    if row["selected_return"] is None:
        return None
    controls = row["control_returns_a"] if reading.endswith("-A") else row["control_returns_b"]
    evidence_floor = 1 if reading.startswith("L-") else floor
    if len(controls) < evidence_floor:
        return None
    return row["selected_return"] - (math.fsum(controls) / len(controls))


def date_means(pairs: Iterable[tuple[str, float]]) -> list[tuple[str, float]]:
    buckets: dict[str, list[float]] = {}
    for d, v in pairs:
        buckets.setdefault(d, []).append(v)
    return sorted((d, math.fsum(vals) / len(vals)) for d, vals in buckets.items())


def primary_statistic(means: list[tuple[str, float]]) -> float | None:
    if not means:
        return None
    return math.fsum(m for _, m in means) / len(means)


def week_blocks(means: list[tuple[str, float]]) -> list[list[float]]:
    blocks: dict[tuple[int, int], list[tuple[str, float]]] = {}
    for d, m in means:
        key = date.fromisoformat(d).isocalendar()[:2]
        blocks.setdefault(key, []).append((d, m))
    out: list[list[float]] = []
    for key in sorted(blocks):
        ordered = sorted(blocks[key], key=lambda x: x[0])
        out.append([v for _, v in ordered])
    return out


def bootstrap_interval(
    means: list[tuple[str, float]], *, replicates: int = 4000, seed: int = 20260917
) -> tuple[float, float] | None:
    blocks = week_blocks(means)
    k = len(blocks)
    if k == 0:
        return None
    sums = np.array([math.fsum(b) for b in blocks], dtype=np.float64)
    counts = np.array([len(b) for b in blocks], dtype=np.int64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, k, size=(replicates, k))
    reps = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.quantile(reps, [0.025, 0.975])
    return (float(lo), float(hi))


def partition_of(date_string: str, cfg: Mapping[str, Any]) -> str | None:
    d = date.fromisoformat(date_string)
    early_end = date.fromisoformat(cfg["early_partition_end"])
    late_start = date.fromisoformat(cfg["late_partition_start"])
    if d <= early_end:
        return "early"
    if d >= late_start:
        return "late"
    return None


def cell_summary(
    rows: list[Mapping[str, Any]], reading: str, *, cfg: Mapping[str, Any], with_interval: bool
) -> dict[str, Any]:
    floor = cfg["matched_control_min_rows"]
    fires_raw = len(rows)
    no_control = sum(1 for r in rows if r["pool_availability"] != "AVAILABLE")
    selected_censored = sum(1 for r in rows if r["selected_return"] is None)
    no_control_and_censored = sum(
        1
        for r in rows
        if r["pool_availability"] != "AVAILABLE" and r["selected_return"] is None
    )
    ambiguous_touch = sum(1 for r in rows if r.get("selected_touch") == "same_bar_ambiguous")

    deltas_by_row: list[tuple[Mapping[str, Any], float | None]] = [
        (r, event_delta(r, reading, floor=floor)) for r in rows
    ]
    delta_pairs: list[tuple[str, float]] = []
    ticker_fires_raw: dict[str, int] = {}
    ticker_fires_delta: dict[str, int] = {}
    ticker_delta_vals: dict[str, list[float]] = {}
    candidate_bins: dict[int, int] = {}
    decision_bins: dict[int, int] = {}
    no_control_reasons: dict[str, int] = {}

    for r in rows:
        sym = r["symbol"]
        ticker_fires_raw[sym] = ticker_fires_raw.get(sym, 0) + 1
        candidate_bins[r["candidate_bin"]] = candidate_bins.get(r["candidate_bin"], 0) + 1
        decision_bins[r["decision_bin"]] = decision_bins.get(r["decision_bin"], 0) + 1
        if r["pool_availability"] != "AVAILABLE":
            reason = r.get("pool_reason") or "unknown"
            no_control_reasons[reason] = no_control_reasons.get(reason, 0) + 1

    fires_delta = 0
    for r, delta in deltas_by_row:
        if delta is None:
            continue
        fires_delta += 1
        sym = r["symbol"]
        ticker_fires_delta[sym] = ticker_fires_delta.get(sym, 0) + 1
        ticker_delta_vals.setdefault(sym, []).append(delta)
        delta_pairs.append((r["date"], delta))

    means = date_means(delta_pairs)
    dates_delta = len(means)
    tickers_delta = len(ticker_fires_delta)

    early_means = [(d, m) for d, m in means if partition_of(d, cfg) == "early"]
    late_means = [(d, m) for d, m in means if partition_of(d, cfg) == "late"]

    control_evidence_unavailable = (
        fires_raw - fires_delta - (no_control + selected_censored - no_control_and_censored)
    )

    ticker_sign: dict[str, int] = {}
    for sym, vals in ticker_delta_vals.items():
        s = math.fsum(vals) / len(vals)
        if s > 0:
            ticker_sign[sym] = 1
        elif s < 0:
            ticker_sign[sym] = -1
        else:
            ticker_sign[sym] = 0

    def _max_share(counts: dict[str, int], denom: int) -> float | None:
        if denom == 0:
            return None
        return max(counts.values()) / denom

    def _max_bin_share(bins: dict[int, int], denom: int) -> float | None:
        if denom == 0:
            return None
        return max(bins.values()) / denom

    return {
        "reading": reading,
        "fires_raw": fires_raw,
        "fires_delta": fires_delta,
        "dates_delta": dates_delta,
        "tickers_delta": tickers_delta,
        "statistic": primary_statistic(means),
        "interval": bootstrap_interval(means) if with_interval else None,
        "early_statistic": primary_statistic(early_means),
        "late_statistic": primary_statistic(late_means),
        "no_control": no_control,
        "selected_censored": selected_censored,
        "no_control_and_censored": no_control_and_censored,
        "control_evidence_unavailable": control_evidence_unavailable,
        "no_control_fraction": (no_control / fires_raw) if fires_raw else None,
        "no_control_reasons": dict(sorted(no_control_reasons.items())),
        "ambiguous_touch": ambiguous_touch,
        "ticker_fires_raw": dict(sorted(ticker_fires_raw.items())),
        "ticker_fires_delta": dict(sorted(ticker_fires_delta.items())),
        "ticker_share_raw_max": _max_share(ticker_fires_raw, fires_raw),
        "ticker_share_delta_max": _max_share(ticker_fires_delta, fires_delta),
        "ticker_sign": dict(sorted(ticker_sign.items())),
        "candidate_bin_share_max": _max_bin_share(candidate_bins, fires_raw),
        "decision_bin_share_max": _max_bin_share(decision_bins, fires_raw),
    }


def gate(rows: list[Mapping[str, Any]], *, cfg: Mapping[str, Any]) -> dict[str, Any]:
    gcfg = cfg["prospective_candidate_gate"]
    readings_out: dict[str, Any] = {}
    for r in READINGS:
        s = cell_summary(rows, r, cfg=cfg, with_interval=True)
        bullet_1_counts = (
            s["fires_delta"] >= gcfg["min_fires"]
            and s["dates_delta"] >= gcfg["min_distinct_dates"]
            and s["tickers_delta"] >= gcfg["min_tickers"]
        )
        bullet_2_interval = s["interval"] is not None and s["interval"][0] > 0
        es, ls = s["early_statistic"], s["late_statistic"]
        bullet_3_partition_sign = (
            es is not None
            and ls is not None
            and ((es > 0 and ls > 0) or (es < 0 and ls < 0))
        )
        bullet_4_concentration = (
            s["ticker_share_raw_max"] is not None
            and s["ticker_share_delta_max"] is not None
            and s["ticker_share_raw_max"] <= gcfg["max_single_ticker_fire_share"]
            and s["ticker_share_delta_max"] <= gcfg["max_single_ticker_fire_share"]
        )
        mechanical_pass = bullet_1_counts and bullet_2_interval and bullet_3_partition_sign and bullet_4_concentration
        readings_out[r] = {
            "summary": s,
            "bullet_1_counts": bullet_1_counts,
            "bullet_2_interval": bullet_2_interval,
            "bullet_3_partition_sign": bullet_3_partition_sign,
            "bullet_4_concentration": bullet_4_concentration,
            "bullet_5_admission_artifact": "REQUIRES_ADJUDICATION",
            "mechanical_pass": mechanical_pass,
        }
    mechanical_pass_all = all(readings_out[r]["mechanical_pass"] for r in READINGS)
    disposition = (
        "PROSPECTIVE_CANDIDATE_PENDING_ARTIFACT_ADJUDICATION"
        if mechanical_pass_all
        else "NO_PROMOTION"
    )
    return {
        "readings": readings_out,
        "mechanical_pass_all_readings": mechanical_pass_all,
        "disposition": disposition,
    }


def summarize(rows: list[Mapping[str, Any]], *, cfg: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        key = (row["selector"], row["horizon"], row["cost_bps"])
        grouped.setdefault(key, []).append(row)

    cells: dict[str, dict[str, dict[str, Any]]] = {}
    for selector in cfg["selectors"]:
        for horizon in cfg["horizons"]:
            for cost in cfg["round_trip_cost_bps"]:
                cell_key = f"{selector}|{horizon}|{cost}"
                cell_rows = grouped.get((selector, horizon, cost), [])
                with_interval = horizon == cfg["primary_horizon"] and cost == cfg["primary_cost_bps"]
                cells[cell_key] = {
                    r: cell_summary(cell_rows, r, cfg=cfg, with_interval=with_interval) for r in READINGS
                }

    gates: dict[str, Any] = {}
    for selector in cfg["selectors"]:
        primary_rows = grouped.get(
            (selector, cfg["primary_horizon"], cfg["primary_cost_bps"]), []
        )
        g = gate(primary_rows, cfg=cfg)
        if selector == cfg["primary_selector"]:
            g["gate_role"] = "prospective_candidate_gate"
        else:
            g["gate_role"] = "comparator_only"
            g["disposition"] = None
        gates[selector] = g

    cost_invariance: dict[str, dict[str, bool]] = {}
    for selector in cfg["selectors"]:
        for horizon in cfg["horizons"]:
            inv_key = f"{selector}|{horizon}"
            cost_invariance[inv_key] = {}
            for reading in READINGS:
                stats = [
                    cells[f"{selector}|{horizon}|{cost}"][reading]["statistic"]
                    for cost in cfg["round_trip_cost_bps"]
                ]
                non_none = [x for x in stats if x is not None]
                if not non_none:
                    cost_invariance[inv_key][reading] = True
                elif len(non_none) != len(stats):
                    cost_invariance[inv_key][reading] = False
                else:
                    cost_invariance[inv_key][reading] = all(
                        abs(a - non_none[0]) <= 1e-12 for a in non_none
                    )

    return {
        "schema": "mastermind.tti.r1b.aggregate.v4",
        "readings": list(READINGS),
        "cells": cells,
        "gates": gates,
        "cost_invariance": cost_invariance,
        "authority": "retrospective_research_only",
        "may_rank": False,
        "may_alert": False,
        "may_size": False,
        "may_trade": False,
    }
