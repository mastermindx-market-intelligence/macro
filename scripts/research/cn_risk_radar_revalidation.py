"""Preregistered research-only revalidation of the China external-driver Risk Radar.

The module exposes pure statistical helpers for tests and a CLI added incrementally under
``research/cn_risk_revalidation/PREREGISTRATION.md``. It never mutates production state.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


STATE_ORDER = ("calm", "watch", "caution", "elevated", "risk-off")


def forward_max_drawdown(close: pd.Series, horizon: int) -> pd.Series:
    """Return close-to-minimum future-close drawdown over exactly ``horizon`` sessions.

    Date ``t`` is excluded from the future window. Rows lacking a complete future window
    remain immature (NaN).
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    values = pd.to_numeric(close, errors="coerce").to_numpy(dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    for pos in range(max(0, len(values) - horizon)):
        current = values[pos]
        future = values[pos + 1 : pos + horizon + 1]
        if np.isfinite(current) and current != 0.0 and np.isfinite(future).all():
            result[pos] = float(min(0.0, np.min(future) / current - 1.0))
    return pd.Series(result, index=close.index, name=f"forward_max_drawdown_h{horizon}")


def binary_outcome(drawdown: pd.Series, threshold: float) -> pd.Series:
    """Map mature drawdowns to 0/1 while preserving immature rows as NaN."""
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    values = pd.to_numeric(drawdown, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float, name="outcome")
    mature = values.notna()
    result.loc[mature] = (values.loc[mature] <= -float(threshold)).astype(float)
    return result


def _band(score: float, bands: Mapping[str, float]) -> str:
    if not np.isfinite(score):
        return "calm"
    if score >= float(bands["risk_off"]):
        return "risk-off"
    if score >= float(bands["elevated"]):
        return "elevated"
    if score >= float(bands["caution"]):
        return "caution"
    if score >= float(bands["watch"]):
        return "watch"
    return "calm"


def reconstruct_states(
    composite: pd.Series,
    gate: pd.Series,
    bands: Mapping[str, float],
) -> pd.DataFrame:
    """Reconstruct exact production ungated and context-capped states."""
    aligned = pd.concat(
        [pd.to_numeric(composite, errors="coerce").rename("composite"), gate.rename("gate")],
        axis=1,
        join="inner",
    )
    score = aligned["composite"] * 100.0
    ungated = score.map(lambda value: _band(float(value), bands))
    emitted = ungated.copy()
    gate_open = aligned["gate"].fillna(False).astype(bool)
    capped = (~gate_open) & emitted.isin(("elevated", "risk-off"))
    emitted.loc[capped] = "caution"
    return pd.DataFrame(
        {"score": score.astype(float), "state_ungated": ungated, "state": emitted},
        index=aligned.index,
    )


def episode_ids(qualifying: pd.Series, max_gap_sessions: int) -> pd.Series:
    """Assign episode IDs using positions on the supplied benchmark-session index."""
    if max_gap_sessions < 0:
        raise ValueError("max_gap_sessions must be nonnegative")
    flags = qualifying.fillna(False).astype(bool).to_numpy()
    result = np.full(len(flags), np.nan, dtype=float)
    episode = -1
    previous_position: int | None = None
    for position in np.flatnonzero(flags):
        if previous_position is None or position - previous_position > max_gap_sessions:
            episode += 1
        result[position] = float(episode)
        previous_position = int(position)
    return pd.Series(result, index=qualifying.index, name="episode_id")


def episode_summary(
    *,
    condition: pd.Series,
    outcome: pd.Series,
    horizon: int,
    episode_gap: int,
) -> dict[str, int]:
    """Report row and episode counts plus the preregistered effective-N ceiling."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    aligned = pd.concat(
        [condition.rename("condition"), pd.to_numeric(outcome, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    )
    mature = aligned["outcome"].notna()
    qualified = aligned["condition"].fillna(False).astype(bool) & mature
    ids = episode_ids(qualified, max_gap_sessions=episode_gap)
    episode_values: list[float] = []
    for episode in ids.dropna().astype(int).unique():
        mask = ids == episode
        episode_values.append(float(aligned.loc[mask, "outcome"].max()))
    episodes = len(episode_values)
    hit_episodes = sum(value >= 1.0 for value in episode_values)
    nonoverlap_ceiling = int(mature.sum() // horizon)
    return {
        "rows": int(qualified.sum()),
        "episodes": episodes,
        "hit_episodes": int(hit_episodes),
        "nonhit_episodes": int(episodes - hit_episodes),
        "nonoverlap_ceiling": nonoverlap_ceiling,
        "effective_n_ceiling": int(min(episodes, nonoverlap_ceiling)),
    }


def _aligned_numeric(*series: pd.Series) -> pd.DataFrame:
    frame = pd.concat(
        [pd.to_numeric(item, errors="coerce").rename(f"v{position}") for position, item in enumerate(series)],
        axis=1,
        join="inner",
    )
    return frame.dropna()


def brier_score(probability: pd.Series, outcome: pd.Series) -> float:
    frame = _aligned_numeric(probability, outcome)
    if frame.empty:
        return float("nan")
    return float(np.mean(np.square(frame["v0"].to_numpy() - frame["v1"].to_numpy())))


def brier_skill(
    probability: pd.Series,
    outcome: pd.Series,
    *,
    baseline_probability: float | pd.Series,
) -> float:
    current = brier_score(probability, outcome)
    baseline = (
        pd.Series(float(baseline_probability), index=outcome.index)
        if np.isscalar(baseline_probability)
        else baseline_probability
    )
    reference = brier_score(baseline, outcome)
    if not np.isfinite(current) or not np.isfinite(reference) or reference <= 0.0:
        return float("nan")
    return float(1.0 - current / reference)


def roc_auc(score: pd.Series, outcome: pd.Series) -> float:
    frame = _aligned_numeric(score, outcome)
    if frame.empty:
        return float("nan")
    y = frame["v1"].to_numpy(dtype=float)
    positives = y >= 0.5
    n_pos = int(positives.sum())
    n_neg = int((~positives).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = frame["v0"].rank(method="average").to_numpy(dtype=float)
    rank_sum = float(ranks[positives].sum())
    return float((rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def average_precision(score: pd.Series, outcome: pd.Series) -> float:
    frame = _aligned_numeric(score, outcome)
    if frame.empty:
        return float("nan")
    ordered = frame.sort_values("v0", ascending=False, kind="mergesort")
    y = (ordered["v1"].to_numpy(dtype=float) >= 0.5).astype(float)
    positives = int(y.sum())
    if positives == 0:
        return float("nan")
    precision = np.cumsum(y) / np.arange(1, len(y) + 1, dtype=float)
    return float(np.sum(precision * y) / positives)


def lift_summary(condition: pd.Series, outcome: pd.Series) -> dict[str, float | int]:
    frame = pd.concat(
        [condition.rename("condition"), pd.to_numeric(outcome, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna(subset=["outcome"])
    if frame.empty:
        return {
            "rows": 0,
            "hits": 0,
            "conditional_rate": float("nan"),
            "base_rate": float("nan"),
            "lift": float("nan"),
        }
    selected = frame["condition"].fillna(False).astype(bool)
    rows = int(selected.sum())
    hits = int(frame.loc[selected, "outcome"].sum()) if rows else 0
    conditional_rate = float(hits / rows) if rows else float("nan")
    base_rate = float(frame["outcome"].mean())
    lift = (
        float(conditional_rate / base_rate)
        if rows and np.isfinite(conditional_rate) and base_rate > 0.0
        else float("nan")
    )
    return {
        "rows": rows,
        "hits": hits,
        "conditional_rate": conditional_rate,
        "base_rate": base_rate,
        "lift": lift,
    }


def circular_moving_block_indices(
    *,
    n: int,
    block_length: int,
    seed: int | np.random.Generator,
) -> np.ndarray:
    if n <= 0:
        raise ValueError("n must be positive")
    if block_length <= 0:
        raise ValueError("block_length must be positive")
    rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
    block_count = int(np.ceil(n / block_length))
    starts = rng.integers(0, n, size=block_count)
    blocks = [(start + np.arange(block_length, dtype=int)) % n for start in starts]
    return np.concatenate(blocks)[:n]


def moving_block_bootstrap(
    frame: pd.DataFrame,
    *,
    statistic,
    block_length: int,
    reps: int,
    seed: int,
) -> dict[str, float | int]:
    if reps <= 0:
        raise ValueError("reps must be positive")
    if frame.empty:
        return {
            "estimate": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "valid_reps": 0,
            "invalid_reps": reps,
        }
    estimate = float(statistic(frame))
    rng = np.random.default_rng(seed)
    values: list[float] = []
    invalid = 0
    for _ in range(reps):
        indices = circular_moving_block_indices(
            n=len(frame), block_length=block_length, seed=rng
        )
        try:
            value = float(statistic(frame.iloc[indices]))
        except (ArithmeticError, IndexError, KeyError, TypeError, ValueError):
            invalid += 1
            continue
        if np.isfinite(value):
            values.append(value)
        else:
            invalid += 1
    if values:
        ci_low, ci_high = np.quantile(np.asarray(values), [0.025, 0.975])
    else:
        ci_low = ci_high = float("nan")
    return {
        "estimate": estimate,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "valid_reps": len(values),
        "invalid_reps": invalid,
    }


def circular_shift_permutation(
    condition: pd.Series,
    outcome: pd.Series,
    *,
    reps: int,
    min_shift: int,
    seed: int,
) -> dict[str, float | int]:
    frame = pd.concat(
        [condition.rename("condition"), pd.to_numeric(outcome, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna(subset=["outcome"])
    n = len(frame)
    if n <= 2 * min_shift:
        return {
            "observed": float("nan"),
            "p_value": float("nan"),
            "valid_reps": 0,
            "invalid_reps": reps,
        }
    observed = float(lift_summary(frame["condition"], frame["outcome"])["lift"])
    allowed = np.arange(min_shift, n - min_shift + 1, dtype=int)
    rng = np.random.default_rng(seed)
    null_values: list[float] = []
    invalid = 0
    outcome_values = frame["outcome"].to_numpy(dtype=float)
    for shift in rng.choice(allowed, size=reps, replace=True):
        shifted = pd.Series(np.roll(outcome_values, int(shift)), index=frame.index)
        value = float(lift_summary(frame["condition"], shifted)["lift"])
        if np.isfinite(value):
            null_values.append(value)
        else:
            invalid += 1
    exceed = sum(value >= observed for value in null_values)
    p_value = float((1 + exceed) / (1 + len(null_values))) if null_values else float("nan")
    return {
        "observed": observed,
        "p_value": p_value,
        "valid_reps": len(null_values),
        "invalid_reps": invalid,
    }


def state_calibration_table(
    states: pd.Series,
    probability: pd.Series,
    outcome: pd.Series,
    *,
    horizon: int,
    episode_gap: int,
) -> list[dict[str, float | int | str]]:
    frame = pd.concat(
        [
            states.rename("state"),
            pd.to_numeric(probability, errors="coerce").rename("probability"),
            pd.to_numeric(outcome, errors="coerce").rename("outcome"),
        ],
        axis=1,
        join="inner",
    ).dropna()
    rows: list[dict[str, float | int | str]] = []
    for state in STATE_ORDER:
        condition = frame["state"] == state
        selected = frame.loc[condition]
        if selected.empty:
            continue
        episodes = episode_summary(
            condition=condition,
            outcome=frame["outcome"],
            horizon=horizon,
            episode_gap=episode_gap,
        )
        rows.append(
            {
                "state": state,
                "forecast": float(selected["probability"].mean()),
                "observed": float(selected["outcome"].mean()),
                "rows": int(len(selected)),
                **episodes,
            }
        )
    return rows


def detect_probability_inversions(
    table: list[dict[str, object]],
    *,
    material_delta: float,
) -> list[dict[str, object]]:
    populated = [row for row in table if row.get("observed") is not None and np.isfinite(float(row["observed"]))]
    inversions: list[dict[str, object]] = []
    for lower, higher in zip(populated, populated[1:]):
        difference = float(higher["observed"]) - float(lower["observed"])
        if difference <= -material_delta:
            inversions.append(
                {
                    "lower_state": str(lower["state"]),
                    "higher_state": str(higher["state"]),
                    "difference": difference,
                    "material": True,
                }
            )
    return inversions


def calibration_intercept_slope(
    probability: pd.Series,
    outcome: pd.Series,
) -> dict[str, object]:
    frame = _aligned_numeric(probability, outcome)
    if len(frame) < 20:
        return {"qualified": False, "reason": "fewer_than_20_rows"}
    p = np.clip(frame["v0"].to_numpy(dtype=float), 1e-6, 1.0 - 1e-6)
    y = frame["v1"].to_numpy(dtype=float)
    if len(np.unique(p)) < 3 or y.sum() < 5 or (len(y) - y.sum()) < 5:
        return {"qualified": False, "reason": "insufficient_bins_or_classes"}
    x = np.column_stack([np.ones(len(p)), np.log(p / (1.0 - p))])
    beta = np.array([0.0, 1.0], dtype=float)
    converged = False
    for _ in range(100):
        eta = np.clip(x @ beta, -35.0, 35.0)
        mu = 1.0 / (1.0 + np.exp(-eta))
        weights = np.clip(mu * (1.0 - mu), 1e-9, None)
        gradient = x.T @ (y - mu)
        hessian = x.T @ (weights[:, None] * x)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            return {"qualified": False, "reason": "singular_information"}
        beta = beta + step
        if float(np.max(np.abs(step))) < 1e-10:
            converged = True
            break
    return {
        "qualified": bool(converged),
        "intercept": float(beta[0]),
        "slope": float(beta[1]),
        "rows": int(len(y)),
        "hits": int(y.sum()),
    }


def crisis_exclusion_mask(
    index: pd.DatetimeIndex,
    *,
    crisis_start: pd.Timestamp,
    crisis_end: pd.Timestamp,
    horizon: int,
) -> pd.Series:
    dates = pd.DatetimeIndex(index)
    keep = np.ones(len(dates), dtype=bool)
    crisis_start = pd.Timestamp(crisis_start)
    crisis_end = pd.Timestamp(crisis_end)
    for position, date in enumerate(dates):
        forward = dates[position + 1 : position + horizon + 1]
        intersects = bool(((forward >= crisis_start) & (forward <= crisis_end)).any())
        inside = crisis_start <= date <= crisis_end
        keep[position] = not (inside or intersects)
    return pd.Series(keep, index=dates, name="keep")


def chronological_split_half(index: pd.DatetimeIndex) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    dates = pd.DatetimeIndex(index).sort_values()
    split = len(dates) // 2
    return dates[:split], dates[split:]
