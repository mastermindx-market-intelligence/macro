"""Pure measurements for published theme-leadership persistence.

All functions are research/display only.  They consume normalized keep-first
snapshots from :mod:`archive` and never read prices, outcomes, or production
state.  Horizons are NYSE trading sessions, not positional archive rows.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from lib.nyse_calendar import is_session

PAIR_METRICS: tuple[str, ...] = (
    "rank_rho",
    "topq_overlap",
    "chance_overlap",
    "topq_overlap_lift",
    "leader_to_laggard",
    "laggard_to_leader",
    "score_continuation_ic",
    "breadth_coverage",
    "leader_breadth_delta",
    "breadth_rank_rho",
)


def _finite(value: object) -> float | None:
    if value is None or isinstance(value, (bool, np.bool_)):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _spearman(first: pd.Series, second: pd.Series) -> float | None:
    """Spearman rho without a scipy dependency; null on thin/constant vectors."""
    joined = pd.concat(
        [pd.to_numeric(first, errors="coerce"), pd.to_numeric(second, errors="coerce")],
        axis=1,
        join="inner",
    ).dropna()
    if len(joined) < 3:
        return None
    left = joined.iloc[:, 0].rank(method="average")
    right = joined.iloc[:, 1].rank(method="average")
    if float(left.std()) <= 0.0 or float(right.std()) <= 0.0:
        return None
    value = left.corr(right, method="pearson")
    return _finite(value)


def nth_session_after(anchor: date, sessions: int) -> date:
    """Return the exact *sessions*-th NYSE session strictly after *anchor*."""
    if sessions < 0:
        raise ValueError("sessions must be non-negative")
    if sessions == 0:
        return anchor
    cursor = anchor
    found = 0
    while found < sessions:
        cursor += timedelta(days=1)
        if is_session(cursor):
            found += 1
    return cursor


def _empty_pair(reason: str, n_common: int, common_fraction: float) -> dict:
    return {
        "eligible": False,
        "reason": reason,
        "n_common": n_common,
        "common_fraction": common_fraction,
        "breadth_state": None,
        **{metric: None for metric in PAIR_METRICS},
    }


def pair_metrics(
    first: pd.DataFrame,
    second: pd.DataFrame,
    *,
    min_common: int = 10,
    min_common_fraction: float = 0.80,
    min_breadth_fraction: float = 0.80,
) -> dict:
    """Measure one endpoint pair over its common published theme set."""
    first_ids = set(str(x) for x in first.index)
    second_ids = set(str(x) for x in second.index)
    common = sorted(first_ids.intersection(second_ids))
    union = first_ids.union(second_ids)
    common_fraction = len(common) / len(union) if union else 0.0
    if common_fraction < min_common_fraction:
        return _empty_pair("INSUFFICIENT_COMMON_COVERAGE", len(common), common_fraction)
    if len(common) < min_common:
        return _empty_pair("INSUFFICIENT_COMMON_COUNT", len(common), common_fraction)

    a = first.loc[common].copy()
    b = second.loc[common].copy()
    rank_a = pd.to_numeric(a["rank"], errors="coerce").rank(
        method="average", ascending=True
    )
    rank_b = pd.to_numeric(b["rank"], errors="coerce").rank(
        method="average", ascending=True
    )
    n_common = len(common)
    quartile_count = max(1, int(math.ceil(n_common / 4)))
    bottom_start = int(math.ceil(n_common / 2))
    top_a = set(rank_a[rank_a <= quartile_count].index)
    top_b = set(rank_b[rank_b <= quartile_count].index)
    bottom_a = set(rank_a[rank_a > bottom_start].index)
    bottom_b = set(rank_b[rank_b > bottom_start].index)

    topq_overlap = len(top_a.intersection(top_b)) / len(top_a) if top_a else None
    chance_overlap = len(top_b) / n_common if n_common else None
    overlap_lift = (
        topq_overlap / chance_overlap
        if topq_overlap is not None and chance_overlap not in (None, 0.0)
        else None
    )
    leader_to_laggard = (
        len(top_a.intersection(bottom_b)) / len(top_a) if top_a else None
    )
    laggard_to_leader = (
        len(bottom_a.intersection(top_b)) / len(bottom_a) if bottom_a else None
    )

    score_a = pd.to_numeric(a["score"], errors="coerce")
    score_b = pd.to_numeric(b["score"], errors="coerce")
    score_delta = score_b - score_a
    score_continuation = _spearman(-rank_a, score_delta)

    breadth_a = pd.to_numeric(a["breadth"], errors="coerce")
    breadth_b = pd.to_numeric(b["breadth"], errors="coerce")
    breadth_mask = breadth_a.notna() & breadth_b.notna()
    breadth_coverage = float(breadth_mask.mean()) if n_common else 0.0
    breadth_state = "MEASURED"
    leader_breadth_delta: float | None = None
    breadth_rank_rho: float | None = None
    if breadth_coverage >= min_breadth_fraction:
        eligible_breadth = breadth_mask[breadth_mask].index
        breadth_rank_rho = _spearman(
            breadth_a.loc[eligible_breadth], breadth_b.loc[eligible_breadth]
        )
        leader_ids = sorted(top_a.intersection(set(eligible_breadth)))
        if leader_ids:
            leader_breadth_delta = _finite(
                (breadth_b.loc[leader_ids] - breadth_a.loc[leader_ids]).mean()
            )
    else:
        breadth_state = "INSUFFICIENT_BREADTH_COVERAGE"

    return {
        "eligible": True,
        "reason": None,
        "n_common": n_common,
        "common_fraction": float(common_fraction),
        "rank_rho": _spearman(rank_a, rank_b),
        "topq_overlap": _finite(topq_overlap),
        "chance_overlap": _finite(chance_overlap),
        "topq_overlap_lift": _finite(overlap_lift),
        "leader_to_laggard": _finite(leader_to_laggard),
        "laggard_to_leader": _finite(laggard_to_leader),
        "score_continuation_ic": score_continuation,
        "breadth_coverage": breadth_coverage,
        "leader_breadth_delta": leader_breadth_delta,
        "breadth_rank_rho": breadth_rank_rho,
        "breadth_state": breadth_state,
    }


def moving_block_ci(
    values: Iterable[float],
    *,
    block_len: int,
    n_resamples: int,
    seed: int,
) -> tuple[float, float] | None:
    """Deterministic 90% circular moving-block bootstrap of the sample mean."""
    clean = np.asarray([v for value in values if (v := _finite(value)) is not None])
    if len(clean) == 0:
        return None
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")
    block_len = max(1, min(int(block_len), len(clean)))
    n_blocks = int(math.ceil(len(clean) / block_len))
    offsets = np.arange(block_len)
    rng = np.random.default_rng(int(seed))
    means = np.empty(int(n_resamples), dtype=float)
    for index in range(int(n_resamples)):
        starts = rng.integers(0, len(clean), size=n_blocks)
        positions = (starts[:, None] + offsets[None, :]) % len(clean)
        sample = clean[positions.ravel()[: len(clean)]]
        means[index] = float(sample.mean())
    low, high = np.quantile(means, [0.05, 0.95])
    return float(low), float(high)


def _recent_start(last_asof: date, sessions: int) -> date:
    if sessions <= 1:
        return last_asof
    cursor = last_asof
    remaining = sessions - 1
    while remaining:
        cursor -= timedelta(days=1)
        if is_session(cursor):
            remaining -= 1
    return cursor


def _metric_summary(
    values: Sequence[float | None],
    *,
    horizon: int,
    metric_index: int,
    min_pairs: int,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict:
    clean = [v for value in values if (v := _finite(value)) is not None]
    if len(clean) < min_pairs:
        return {
            "state": "INSUFFICIENT_HISTORY",
            "n": len(clean),
            "mean": None,
            "ci90": None,
        }
    block_len = min(max(1, int(horizon)), max(1, len(clean) // 3))
    ci = moving_block_ci(
        clean,
        block_len=block_len,
        n_resamples=bootstrap_resamples,
        seed=bootstrap_seed + 100 * int(horizon) + metric_index,
    )
    return {
        "state": "MEASURED",
        "n": len(clean),
        "mean": float(np.mean(clean)),
        "ci90": list(ci) if ci is not None else None,
    }


def build_surface(
    frames: Mapping[date, pd.DataFrame],
    *,
    horizons: Sequence[int] = (1, 2, 3, 5, 7, 10, 15, 20),
    recent_sessions: int = 20,
    min_pairs: int = 8,
    bootstrap_resamples: int = 2_000,
    bootstrap_seed: int = 20_260_910,
) -> dict[str, dict]:
    """Build exact-session pair surfaces for all/recent/prior windows."""
    dates = sorted(frames)
    if not dates:
        return {}
    recent_start = _recent_start(dates[-1], recent_sessions)
    output: dict[str, dict] = {}
    for horizon in horizons:
        pair_rows: list[dict] = []
        target_missing = 0
        ineligible = 0
        for anchor in dates:
            target = nth_session_after(anchor, int(horizon))
            target_frame = frames.get(target)
            if target_frame is None:
                target_missing += 1
                continue
            metrics = pair_metrics(frames[anchor], target_frame)
            if not metrics["eligible"]:
                ineligible += 1
                continue
            pair_rows.append(
                {
                    "anchor": anchor,
                    "target": target,
                    **metrics,
                }
            )

        windows: dict[str, dict] = {}
        for window_name in ("all", "recent", "prior"):
            if window_name == "recent":
                selected = [row for row in pair_rows if row["anchor"] >= recent_start]
            elif window_name == "prior":
                selected = [row for row in pair_rows if row["anchor"] < recent_start]
            else:
                selected = pair_rows
            windows[window_name] = {
                metric: _metric_summary(
                    [row.get(metric) for row in selected],
                    horizon=int(horizon),
                    metric_index=index,
                    min_pairs=min_pairs,
                    bootstrap_resamples=bootstrap_resamples,
                    bootstrap_seed=bootstrap_seed,
                )
                for index, metric in enumerate(PAIR_METRICS)
            }
            windows[window_name]["anchor_first"] = (
                selected[0]["anchor"].isoformat() if selected else None
            )
            windows[window_name]["anchor_last"] = (
                selected[-1]["anchor"].isoformat() if selected else None
            )

        output[str(int(horizon))] = {
            "horizon_sessions": int(horizon),
            "pairs_eligible": len(pair_rows),
            "pairs_target_missing": target_missing,
            "pairs_ineligible": ineligible,
            "recent_window_start": recent_start.isoformat(),
            "windows": windows,
        }
    return output


def _rank_correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    return _spearman(pd.Series(xs, dtype=float), pd.Series(ys, dtype=float))


def derive_half_life(curve: Mapping[int, float | None]) -> dict:
    """Apply the frozen honest-null half-life admissibility rules."""
    points = sorted(
        (int(h), value)
        for h, raw in curve.items()
        if (value := _finite(raw)) is not None
    )
    base = {
        "half_life_sessions": None,
        "start_rho": points[0][1] if points else None,
        "half_target": points[0][1] / 2.0 if points else None,
        "curve": [{"horizon": h, "value": v} for h, v in points],
    }
    if len(points) < 4:
        return {"state": "INSUFFICIENT_HORIZONS", **base}
    start = points[0][1]
    if start <= 0.0:
        return {"state": "NONPOSITIVE_START", **base}
    horizon_rho = _rank_correlation(
        [float(h) for h, _ in points], [value for _, value in points]
    )
    if horizon_rho is None or horizon_rho >= 0.0:
        return {"state": "NON_DECAYING", **base}
    if any(current > previous + 0.05 for (_, previous), (_, current) in zip(points, points[1:])):
        return {"state": "NON_MONOTONE", **base}

    target = start / 2.0
    for (left_h, left_v), (right_h, right_v) in zip(points, points[1:]):
        if right_v > target:
            continue
        if right_v == left_v:
            crossing = float(right_h)
        else:
            fraction = (target - left_v) / (right_v - left_v)
            crossing = float(left_h + fraction * (right_h - left_h))
        return {
            "state": "MEASURED",
            "half_life_sessions": crossing,
            **{k: v for k, v in base.items() if k != "half_life_sessions"},
        }
    return {"state": "NO_HALF_CROSSING", **base}


def classify_temporal_shape(curve: Mapping[int, float | None]) -> dict:
    """Classify the frozen short-vs-long published-score continuation shape."""
    clean = {int(h): value for h, raw in curve.items() if (value := _finite(raw)) is not None}
    short_values = [clean[h] for h in (1, 2, 3, 5) if h in clean]
    long_values = [clean[h] for h in (10, 15, 20) if h in clean]
    if len(short_values) < 2 or len(long_values) < 2:
        return {
            "label": "INSUFFICIENT_HISTORY",
            "short_median": None,
            "long_median": None,
            "n_short": len(short_values),
            "n_long": len(long_values),
        }
    short = float(np.median(short_values))
    long = float(np.median(long_values))
    if short <= -0.05 and long >= 0.05:
        label = "MULTI_SCALE"
    elif short <= -0.05 and long < 0.05:
        label = "REVERSAL_DOMINANT"
    elif short >= 0.05 and long >= 0.05:
        label = "CONTINUATION_DOMINANT"
    else:
        label = "TRANSITIONAL"
    return {
        "label": label,
        "short_median": short,
        "long_median": long,
        "n_short": len(short_values),
        "n_long": len(long_values),
    }
