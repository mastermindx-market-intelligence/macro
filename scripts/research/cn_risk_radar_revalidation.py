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
    """Threshold-based average precision with deterministic, tie-honest grouping."""
    frame = _aligned_numeric(score, outcome)
    if frame.empty:
        return float("nan")
    positives = float((frame["v1"] >= 0.5).sum())
    if positives <= 0.0:
        return float("nan")
    grouped = (
        frame.assign(_positive=(frame["v1"] >= 0.5).astype(float))
        .groupby("v0", sort=True)["_positive"]
        .agg(["sum", "count"])
        .sort_index(ascending=False)
    )
    true_positives = grouped["sum"].cumsum().to_numpy(dtype=float)
    observations = grouped["count"].cumsum().to_numpy(dtype=float)
    recall = true_positives / positives
    precision = true_positives / observations
    previous_recall = np.concatenate(([0.0], recall[:-1]))
    return float(np.sum((recall - previous_recall) * precision))

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
    p_value = float((1 + exceed) / (1 + reps)) if null_values else float("nan")
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


def sha256_file(path) -> str:
    import hashlib
    from pathlib import Path

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_sources(repo_root, expected: Mapping[str, str]) -> dict[str, dict[str, object]]:
    from pathlib import Path

    root = Path(repo_root)
    manifest: dict[str, dict[str, object]] = {}
    for relative, expected_hash in expected.items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"frozen source missing: {relative}")
        actual = sha256_file(path)
        if actual != expected_hash:
            raise RuntimeError(
                f"source hash drift for {relative}: expected {expected_hash}, got {actual}"
            )
        manifest[relative] = {
            "sha256": actual,
            "bytes": int(path.stat().st_size),
        }
    return manifest


def verify_no_cn_overlay(repo_root) -> None:
    from pathlib import Path

    overlay = Path(repo_root) / "data" / "risk_radar_intl" / "cn_calibration.json"
    if overlay.exists():
        raise RuntimeError(f"unexpected CN calibration overlay: {overlay}")


def dataframe_file_manifest(path, *, role: str, provider: str) -> dict[str, object]:
    from pathlib import Path

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix == ".parquet":
        frame = pd.read_parquet(source)
    elif suffix in {".csv", ".txt"}:
        frame = pd.read_csv(source, index_col=0, parse_dates=True)
    else:
        raise ValueError(f"unsupported tabular source: {source}")
    dates = pd.to_datetime(frame.index)
    return {
        "path": str(source),
        "role": role,
        "provider": provider,
        "sha256": sha256_file(source),
        "bytes": int(source.stat().st_size),
        "rows": int(len(frame)),
        "first_date": str(dates.min().date()) if len(dates) else None,
        "last_date": str(dates.max().date()) if len(dates) else None,
        "columns": [str(column) for column in frame.columns],
    }


def delayed_expanding_base(
    outcome: pd.Series,
    *,
    horizon: int,
    min_history: int = 252,
) -> pd.Series:
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    values = pd.to_numeric(outcome, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype=float, name="delayed_expanding_base")
    for position in range(len(values)):
        cutoff = position - horizon
        if cutoff < 0:
            continue
        history = values.iloc[: cutoff + 1].dropna()
        if len(history) < min_history:
            continue
        result.iloc[position] = float((history.sum() + 0.5) / (len(history) + 1.0))
    return result


def build_baseline_scores(
    *,
    sublegs: Mapping[str, pd.Series],
    composite: pd.Series,
    gate: pd.Series,
    percentile_window: int = 504,
) -> pd.DataFrame:
    if percentile_window <= 1:
        raise ValueError("percentile_window must exceed one")
    rate_names = ("us_rate_2y", "us_real_rate", "us_rate_10y")
    rate_members = [pd.to_numeric(sublegs[name], errors="coerce") for name in rate_names if name in sublegs]
    if not rate_members:
        rates_only = pd.Series(np.nan, index=composite.index, dtype=float)
    else:
        rates_raw = pd.concat(rate_members, axis=1).mean(axis=1)
        rates_only = rates_raw.rolling(
            percentile_window,
            min_periods=percentile_window // 2,
        ).rank(pct=True)
    breadth = pd.to_numeric(
        sublegs.get("cn_breadth", pd.Series(np.nan, index=composite.index)),
        errors="coerce",
    )
    return pd.concat(
        [
            breadth.rename("breadth_only"),
            rates_only.rename("rates_only"),
            gate.fillna(False).astype(float).rename("trend_context"),
            pd.to_numeric(composite, errors="coerce").rename("ungated_composite"),
        ],
        axis=1,
        join="outer",
    ).sort_index()


def align_replication_outcome(
    canonical_signal: pd.DataFrame,
    replication_close: pd.Series,
    *,
    horizon: int,
    threshold: float,
    outcome_name: str,
) -> pd.DataFrame:
    close = pd.to_numeric(replication_close, errors="coerce").sort_index()
    drawdown = forward_max_drawdown(close, horizon=horizon)
    outcome = binary_outcome(drawdown, threshold=threshold).rename(outcome_name)
    return canonical_signal.join(outcome, how="inner")


def fixed_threshold_conditions(
    score: pd.Series,
    *,
    elevated_threshold: float = 0.83,
    risk_off_threshold: float = 0.91,
) -> tuple[pd.Series, pd.Series]:
    numeric = pd.to_numeric(score, errors="coerce")
    elevated = (numeric >= elevated_threshold).fillna(False)
    risk_off = (numeric >= risk_off_threshold).fillna(False)
    return elevated.astype(bool), risk_off.astype(bool)


_CLAIM_KEYS = (
    "extreme China external-driver hazard",
    "98th-percentile intensity semantics",
    ">=5%/21d risk-off probability = 50%",
    ">=10%/42d historical lift ~2.07x",
    "elevated vs risk-off separation",
    "5d / 10d / 21d ladder",
    "context gate value-add",
)

_ALLOWED_VERDICTS = {
    "KEEP",
    "KEEP_BUT_RELABEL",
    "RECALIBRATION_CANDIDATE",
    "FAIL / REMOVE",
    "INSUFFICIENT_EVIDENCE",
}


def claim_keys() -> tuple[str, ...]:
    return _CLAIM_KEYS


def adjudicate_probability(
    *,
    forecast: float,
    observed: float,
    block_ci: tuple[float, float],
    episode_ci: tuple[float, float],
    brier_skill_value: float,
    effective_n: int,
    hit_episodes: int,
    nonhit_episodes: int,
    material_inversion: bool,
) -> dict[str, object]:
    reasons: list[str] = []
    if effective_n < 20 or hit_episodes < 5 or nonhit_episodes < 5:
        return {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "reasons": [
                f"effective episodes {effective_n}; hits/non-hits {hit_episodes}/{nonhit_episodes}"
            ],
        }
    error = abs(float(observed) - float(forecast))
    block_contains = float(block_ci[0]) <= forecast <= float(block_ci[1])
    episode_contains = float(episode_ci[0]) <= forecast <= float(episode_ci[1])
    if error > 0.20 and not block_contains and not episode_contains and brier_skill_value < 0.0:
        reasons.append(f"absolute calibration error {error:.3f} exceeds 0.20")
        if material_inversion:
            reasons.append("material state-bin inversion")
        return {"verdict": "FAIL / REMOVE", "reasons": reasons}
    if (
        error > 0.10
        or not block_contains
        or not episode_contains
        or brier_skill_value < 0.0
        or material_inversion
    ):
        if error > 0.10:
            reasons.append(f"absolute calibration error {error:.3f} exceeds 0.10")
        if not block_contains:
            reasons.append("forecast outside moving-block interval")
        if not episode_contains:
            reasons.append("forecast outside episode interval")
        if brier_skill_value < 0.0:
            reasons.append("negative Brier skill versus baked base")
        if material_inversion:
            reasons.append("material state-bin inversion")
        return {"verdict": "RECALIBRATION_CANDIDATE", "reasons": reasons}
    return {
        "verdict": "KEEP",
        "reasons": [
            f"error {error:.3f}; forecast inside both dependence-aware intervals; nonnegative skill"
        ],
    }


def adjudicate_historical_lift(
    *,
    lift: float,
    ci: tuple[float, float],
    split_lifts: tuple[float, float],
    modern_lift: float,
    loco_lifts: tuple[float, ...],
    permutation_p: float,
    effective_n: int,
) -> dict[str, object]:
    if effective_n < 8:
        return {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "reasons": [f"only {effective_n} effective signal episodes"],
        }
    slices = [*split_lifts, modern_lift, *loco_lifts]
    positive = sum(value > 1.0 for value in slices)
    robust = (
        lift > 1.0
        and ci[0] > 1.0
        and all(value > 1.0 for value in split_lifts)
        and modern_lift > 1.0
        and all(value > 1.0 for value in loco_lifts)
        and permutation_p <= 0.05
        and effective_n >= 20
        and abs(lift - 2.07) <= 0.25
    )
    if robust:
        return {
            "verdict": "KEEP",
            "reasons": ["robust across block CI, split halves, modern era, LOCO, and permutation"],
        }
    if lift <= 1.0:
        return {
            "verdict": "FAIL / REMOVE",
            "reasons": [f"point lift {lift:.3f} is not above one"],
        }
    if positive >= max(1, (len(slices) + 1) // 2):
        return {
            "verdict": "KEEP_BUT_RELABEL",
            "reasons": [
                "directional lift survives a majority of stability slices but misses robust promotion"
            ],
        }
    return {
        "verdict": "FAIL / REMOVE",
        "reasons": ["lift reverses across a majority of powered stability slices"],
    }


def adjudicate_state_separation(
    *,
    difference: float,
    ci: tuple[float, float],
    elevated_effective_n: int,
    risk_off_effective_n: int,
    material_inversion: bool,
) -> dict[str, object]:
    if elevated_effective_n < 12 or risk_off_effective_n < 12:
        return {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "reasons": [
                f"effective episodes elevated/risk-off {elevated_effective_n}/{risk_off_effective_n}"
            ],
        }
    if material_inversion and difference < 0.0:
        return {
            "verdict": "FAIL / REMOVE",
            "reasons": ["material risk-off versus elevated inversion"],
        }
    if difference > 0.0 and ci[0] >= 0.0:
        return {
            "verdict": "KEEP",
            "reasons": ["risk-off observed rate exceeds elevated with nonnegative lower bound"],
        }
    if difference > 0.0:
        return {
            "verdict": "KEEP_BUT_RELABEL",
            "reasons": ["positive point separation but interval overlaps zero"],
        }
    return {
        "verdict": "RECALIBRATION_CANDIDATE",
        "reasons": ["risk-off point estimate does not exceed elevated"],
    }


def _format_scalar(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if not np.isfinite(value):
            return "n/a"
        return f"{value:.4f}"
    return str(value)


def render_report(result: Mapping[str, object]) -> str:
    lines = [
        "# China Risk Radar Revalidation",
        "",
        f"- Operation: `{result.get('operation_key', 'unknown')}`",
        f"- Base SHA: `{result.get('base_sha', 'unknown')}`",
        f"- Preregistration SHA: `{result.get('prereg_sha', 'unknown')}`",
        "- Classification: research-only; production behavior unchanged",
        "",
        "## Claim-by-claim verdict",
        "",
    ]
    claims = result.get("claims", {})
    if not isinstance(claims, Mapping):
        claims = {}
    for claim in _CLAIM_KEYS:
        record = claims.get(claim, {}) if isinstance(claims, Mapping) else {}
        if not isinstance(record, Mapping):
            record = {}
        verdict = str(record.get("verdict", "INSUFFICIENT_EVIDENCE"))
        basis = record.get("basis") or record.get("reasons") or "No basis recorded."
        if isinstance(basis, (list, tuple)):
            basis = "; ".join(str(item) for item in basis)
        lines.extend([f"### {claim}", "", f"**{verdict}** — {basis}", ""])
    lines.extend(["## Primary target summaries", ""])
    targets = result.get("targets", {})
    if isinstance(targets, Mapping) and targets:
        for name in sorted(targets):
            target = targets[name]
            lines.append(f"### {name}")
            lines.append("")
            if isinstance(target, Mapping):
                for key in ("benchmark", "eligible_rows", "base_rate", "risk_off_lift", "elevated_plus_lift"):
                    if key in target:
                        lines.append(f"- {key}: {_format_scalar(target[key])}")
            lines.append("")
    else:
        lines.extend(["No target results recorded.", ""])
    lines.extend(["## Issued forward evidence", ""])
    forward = result.get("forward_ledger", {})
    if isinstance(forward, Mapping) and forward:
        for key in sorted(forward):
            lines.append(f"- {key}: {_format_scalar(forward[key])}")
    else:
        lines.append("No forward-ledger summary recorded.")
    lines.extend(["", "## Discoveries", ""])
    discoveries = result.get("discoveries", [])
    if isinstance(discoveries, list) and discoveries:
        lines.extend(f"- {item}" for item in discoveries)
    else:
        lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 -m scripts.research.cn_risk_radar_revalidation --repo-root . --output-dir research/cn_risk_revalidation --bootstrap-reps 5000 --permutation-reps 5000 --seed 20260923",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_result_artifacts(result: Mapping[str, object], output_dir) -> dict[str, str]:
    import json
    from pathlib import Path

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    clean_result = json_ready(result)
    claims = clean_result.get("claims")
    if not isinstance(claims, Mapping) or tuple(claims.keys()) != _CLAIM_KEYS:
        missing = [claim for claim in _CLAIM_KEYS if not isinstance(claims, Mapping) or claim not in claims]
        extra = [] if not isinstance(claims, Mapping) else [claim for claim in claims if claim not in _CLAIM_KEYS]
        if missing or extra:
            raise ValueError(f"claim set mismatch; missing={missing}, extra={extra}")
    for claim, record in claims.items():
        if not isinstance(record, Mapping) or record.get("verdict") not in _ALLOWED_VERDICTS:
            raise ValueError(f"invalid verdict record for {claim}: {record}")
    json_text = json.dumps(clean_result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    report_text = render_report(clean_result)
    json_path = output / "results.json"
    report_path = output / "REPORT.md"
    json_path.write_text(json_text)
    report_path.write_text(report_text)
    written = {
        "results_json": str(json_path),
        "results_sha256": sha256_file(json_path),
        "report_md": str(report_path),
        "report_sha256": sha256_file(report_path),
    }
    if "data_provenance" in clean_result:
        manifest_path = output / "data_manifest.json"
        manifest_path.write_text(
            json.dumps(clean_result["data_provenance"], indent=2, sort_keys=True, allow_nan=False) + "\n"
        )
        written.update(
            {
                "data_manifest_json": str(manifest_path),
                "data_manifest_sha256": sha256_file(manifest_path),
            }
        )
    return written


OPERATION_KEY = "cn-risk-p1-radar-revalidation-20260923-solpro-001"
BASE_SHA = "8db6896dab2199a4b7fc61a005c225380cac7cd6"
PREREG_SHA = "db5590accaa03f78396ca91b6874f04b9bcf4cf3"
FROZEN_SOURCE_SHA256 = {
    "engine/risk_radar_intl.py": "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7",
    "engine/indicators.py": "edb47847dba4e3ae011341e17c9c914b58639b0ae42a09969800044b4cd4a5b5",
    "scripts/calibrate_risk_radar_intl.py": "ec613aa8b38f317ebd4ed8a4ab9dca153db9c632898c40a5edae663e69c26458",
    "lib/store.py": "77051ae1e522e415e2b8c3be51f51187f2571d53a049472a52ca54e9ee1a3c4b",
}


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Preregistered research-only revalidation of the China Risk Radar."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="research/cn_risk_revalidation")
    parser.add_argument("--bootstrap-reps", type=int, default=5000)
    parser.add_argument("--permutation-reps", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260923)
    parser.add_argument("--check-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    import json
    from pathlib import Path

    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    source_manifest = verify_frozen_sources(repo_root, FROZEN_SOURCE_SHA256)
    verify_no_cn_overlay(repo_root)
    if args.check_only:
        print(
            json.dumps(
                {
                    "schema": "cn_risk_radar_revalidation.check.v1",
                    "operation_key": OPERATION_KEY,
                    "base_sha": BASE_SHA,
                    "prereg_sha": PREREG_SHA,
                    "overlay": "absent",
                    "sources": source_manifest,
                },
                sort_keys=True,
            )
        )
        return 0
    result = run_revalidation(
        repo_root=repo_root,
        bootstrap_reps=args.bootstrap_reps,
        permutation_reps=args.permutation_reps,
        seed=args.seed,
    )
    write_result_artifacts(result, Path(args.output_dir))
    return 0


def episode_bootstrap_rate(
    *,
    condition: pd.Series,
    outcome: pd.Series,
    episode_gap: int,
    reps: int,
    seed: int,
) -> dict[str, float | int]:
    """Bootstrap a conditional event rate by resampling complete signal episodes."""
    if reps <= 0:
        raise ValueError("reps must be positive")
    frame = pd.concat(
        [condition.rename("condition"), pd.to_numeric(outcome, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna(subset=["outcome"])
    qualified = frame["condition"].fillna(False).astype(bool)
    ids = episode_ids(qualified, max_gap_sessions=episode_gap)
    episode_hits: list[float] = []
    episode_rows: list[int] = []
    for episode in ids.dropna().astype(int).unique():
        values = frame.loc[ids == episode, "outcome"].to_numpy(dtype=float)
        if len(values):
            episode_hits.append(float(values.sum()))
            episode_rows.append(int(len(values)))
    episodes = len(episode_rows)
    total_rows = int(sum(episode_rows))
    estimate = float(sum(episode_hits) / total_rows) if total_rows else float("nan")
    if episodes == 0:
        return {
            "estimate": estimate,
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "episodes": 0,
            "valid_reps": 0,
            "invalid_reps": reps,
        }
    hit_array = np.asarray(episode_hits, dtype=float)
    row_array = np.asarray(episode_rows, dtype=float)
    rng = np.random.default_rng(seed)
    values: list[float] = []
    invalid = 0
    for _ in range(reps):
        selection = rng.integers(0, episodes, size=episodes)
        denominator = float(row_array[selection].sum())
        if denominator <= 0.0:
            invalid += 1
            continue
        values.append(float(hit_array[selection].sum() / denominator))
    if values:
        low, high = np.quantile(np.asarray(values, dtype=float), [0.025, 0.975])
    else:
        low = high = float("nan")
    return {
        "estimate": estimate,
        "ci_low": float(low),
        "ci_high": float(high),
        "episodes": episodes,
        "valid_reps": len(values),
        "invalid_reps": invalid,
    }


def summarize_forward_ledger(path) -> dict[str, object]:
    """Read the immutable issued CN ledger without grading or modifying any row."""
    import json
    from collections import Counter
    from pathlib import Path

    source = Path(path)
    rows: list[dict[str, object]] = []
    invalid_lines = 0
    for line in source.read_text().splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines += 1
            continue
        if isinstance(record, dict):
            rows.append(record)
        else:
            invalid_lines += 1
    matured = [row for row in rows if isinstance(row.get("graded"), dict)]
    pending = [row for row in rows if not isinstance(row.get("graded"), dict)]

    def is_loud(row: Mapping[str, object]) -> bool:
        return bool(row.get("alert")) or row.get("state") in {"elevated", "risk-off"}

    def is_hit(row: Mapping[str, object]) -> bool:
        graded = row.get("graded")
        return bool(graded.get("any_dd5_within_h21")) if isinstance(graded, Mapping) else False

    loud = [row for row in matured if is_loud(row)]
    risk_off = [row for row in matured if row.get("state") == "risk-off"]
    pending_dates = sorted(str(row.get("asof")) for row in pending if row.get("asof"))
    matured_dates = sorted(str(row.get("asof")) for row in matured if row.get("asof"))
    total_state_counts = Counter(str(row.get("state")) for row in rows)
    matured_state_counts = Counter(str(row.get("state")) for row in matured)

    cohort_keys = ("model", "model_version", "construction_hash", "source_sha", "profile")
    cohort_values = {
        key: sorted({str(row.get(key)) for row in rows if row.get(key) not in (None, "")})
        for key in cohort_keys
    }
    cohort_identifiers_present = any(cohort_values.values())
    episode_identifiers_present = any(
        row.get("episode_id") not in (None, "") or row.get("alert_episode_id") not in (None, "")
        for row in rows
    )
    research_count_floor_met = len(matured) >= 25
    loud_count_floor_met = len(loud) >= 8
    production_force_count_floor_met = len(matured) >= 30 and loud_count_floor_met
    research_recalibration_floor_met = bool(
        research_count_floor_met
        and loud_count_floor_met
        and cohort_identifiers_present
        and episode_identifiers_present
    )
    if not research_count_floor_met:
        authority_interpretation = "not eligible: fewer than 25 matured issued rows"
    elif not cohort_identifiers_present:
        authority_interpretation = (
            "count floor met, but exact model cohort is unverifiable from the ledger schema"
        )
    elif not episode_identifiers_present:
        authority_interpretation = (
            "count floor met, but independent loud/risk-off episodes are unverifiable from the ledger schema"
        )
    elif not loud_count_floor_met:
        authority_interpretation = "count floor met, but fewer than 8 matured loud rows"
    else:
        authority_interpretation = "research count/cohort/episode floors met; no production authority inferred"

    return {
        "evidence_class": "genuinely_issued_forward",
        "source_sha256": sha256_file(source),
        "total_rows": len(rows),
        "matured_rows": len(matured),
        "pending_rows": len(pending),
        "invalid_lines": invalid_lines,
        "matured_loud_alerts": len(loud),
        "matured_loud_hits": sum(is_hit(row) for row in loud),
        "matured_risk_off_rows": len(risk_off),
        "matured_risk_off_hits": sum(is_hit(row) for row in risk_off),
        "matured_all_hits": sum(is_hit(row) for row in matured),
        "matured_asof_range": [matured_dates[0], matured_dates[-1]] if matured_dates else None,
        "pending_asof_range": [pending_dates[0], pending_dates[-1]] if pending_dates else None,
        "september_pending_rows": sum(date.startswith("2026-09") for date in pending_dates),
        "total_state_counts": dict(sorted(total_state_counts.items())),
        "matured_state_counts": dict(sorted(matured_state_counts.items())),
        "research_count_floor_met": research_count_floor_met,
        "loud_count_floor_met": loud_count_floor_met,
        "research_recalibration_floor_met": research_recalibration_floor_met,
        "production_force_count_floor_met": production_force_count_floor_met,
        "authority_floors_met": research_recalibration_floor_met,
        "cohort_identifiers_present": cohort_identifiers_present,
        "cohort_identifiers": cohort_values,
        "cohort_qualification": (
            "identified" if cohort_identifiers_present else "unverifiable_from_ledger_schema"
        ),
        "episode_identifiers_present": episode_identifiers_present,
        "can_force": False,
        "authority_interpretation": authority_interpretation,
        "pool_with_reconstructed_history": False,
    }

def _sample_conditional_rate(sample: pd.DataFrame) -> float:
    condition = sample["condition"].fillna(False).to_numpy(dtype=bool)
    outcome = pd.to_numeric(sample["outcome"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(outcome)
    selected = condition & valid
    return float(outcome[selected].mean()) if selected.any() else float("nan")


def _sample_lift(sample: pd.DataFrame) -> float:
    condition = sample["condition"].fillna(False).to_numpy(dtype=bool)
    outcome = pd.to_numeric(sample["outcome"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(outcome)
    if not valid.any():
        return float("nan")
    selected = condition & valid
    if not selected.any():
        return float("nan")
    base = float(outcome[valid].mean())
    conditional = float(outcome[selected].mean())
    return float(conditional / base) if base > 0.0 else float("nan")

def _conditional_analysis(
    *,
    condition: pd.Series,
    outcome: pd.Series,
    horizon: int,
    bootstrap_reps: int,
    seed: int,
) -> dict[str, object]:
    point = lift_summary(condition, outcome)
    block_frame = pd.concat(
        [condition.rename("condition"), pd.to_numeric(outcome, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna(subset=["outcome"])
    block = moving_block_bootstrap(
        block_frame,
        statistic=_sample_lift,
        block_length=42,
        reps=bootstrap_reps,
        seed=seed,
    )
    episodes = episode_summary(
        condition=condition,
        outcome=outcome,
        horizon=horizon,
        episode_gap=42,
    )
    episode_rate = episode_bootstrap_rate(
        condition=condition,
        outcome=outcome,
        episode_gap=42,
        reps=bootstrap_reps,
        seed=seed + 1,
    )
    return {
        **point,
        "block_ci": [float(block["ci_low"]), float(block["ci_high"])],
        "block_valid_reps": int(block["valid_reps"]),
        "block_invalid_reps": int(block["invalid_reps"]),
        "episode_rate_ci": [
            float(episode_rate["ci_low"]),
            float(episode_rate["ci_high"]),
        ],
        "episode_valid_reps": int(episode_rate["valid_reps"]),
        "effective_n": episodes,
    }


def analyze_target(
    frame: pd.DataFrame,
    *,
    target_name: str,
    benchmark_label: str,
    horizon: int,
    bootstrap_reps: int,
    permutation_reps: int,
    seed: int,
) -> dict[str, object]:
    """Analyze one frozen target on an already aligned exact-production frame."""
    required = {"state", "state_ungated", "composite", "outcome"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"target frame missing columns: {missing}")
    eligible = frame.dropna(subset=["outcome", "composite"]).copy()
    outcome = pd.to_numeric(eligible["outcome"], errors="coerce")
    conditions = {
        "risk_off": eligible["state"].eq("risk-off"),
        "elevated_plus": eligible["state"].isin(["elevated", "risk-off"]),
        "ungated_risk_off": eligible["state_ungated"].eq("risk-off"),
        "ungated_elevated_plus": eligible["state_ungated"].isin(["elevated", "risk-off"]),
    }
    condition_results = {
        name: _conditional_analysis(
            condition=condition,
            outcome=outcome,
            horizon=horizon,
            bootstrap_reps=bootstrap_reps,
            seed=seed + position * 17,
        )
        for position, (name, condition) in enumerate(conditions.items())
    }
    base_rate = float(outcome.mean()) if len(outcome) else float("nan")
    ap = average_precision(eligible["composite"], outcome)
    auc = roc_auc(eligible["composite"], outcome)
    permutations = {
        name: circular_shift_permutation(
            condition,
            outcome,
            reps=permutation_reps,
            min_shift=42,
            seed=seed + 1000 + position * 31,
        )
        for position, (name, condition) in enumerate(
            (("risk_off", conditions["risk_off"]), ("ungated_risk_off", conditions["ungated_risk_off"]))
        )
    }
    return {
        "target": target_name,
        "benchmark": benchmark_label,
        "horizon": horizon,
        "eligible_rows": int(len(eligible)),
        "first_eligible_date": str(eligible.index.min().date()) if len(eligible) else None,
        "last_eligible_date": str(eligible.index.max().date()) if len(eligible) else None,
        "base_rate": base_rate,
        "continuous_discrimination": {
            "average_precision": ap,
            "ap_over_base": float(ap / base_rate) if np.isfinite(ap) and base_rate > 0.0 else float("nan"),
            "roc_auc": auc,
        },
        **condition_results,
        "permutation": permutations,
    }


def state_probability_series(states: pd.Series, surface: Mapping[str, float]) -> pd.Series:
    probability = states.map(surface)
    unknown = sorted(set(states.dropna().astype(str)) - set(surface))
    if unknown:
        raise ValueError(f"probability surface missing states: {unknown}")
    return pd.to_numeric(probability, errors="coerce").rename("probability")


def analyze_calibration(
    *,
    states: pd.Series,
    probabilities: pd.Series,
    outcomes: pd.Series,
    base_probability: float,
    horizon: int,
    bootstrap_reps: int,
    seed: int,
) -> dict[str, object]:
    frame = pd.concat(
        [
            states.rename("state"),
            pd.to_numeric(probabilities, errors="coerce").rename("probability"),
            pd.to_numeric(outcomes, errors="coerce").rename("outcome"),
        ],
        axis=1,
        join="inner",
    ).dropna()
    table = state_calibration_table(
        frame["state"],
        frame["probability"],
        frame["outcome"],
        horizon=horizon,
        episode_gap=42,
    )
    enriched: list[dict[str, object]] = []
    for position, row in enumerate(table):
        state = str(row["state"])
        condition = frame["state"].eq(state)
        block_frame = frame[["state", "outcome"]].copy()
        block_frame["condition"] = condition
        block = moving_block_bootstrap(
            block_frame,
            statistic=_sample_conditional_rate,
            block_length=42,
            reps=bootstrap_reps,
            seed=seed + position * 19,
        )
        episode = episode_bootstrap_rate(
            condition=condition,
            outcome=frame["outcome"],
            episode_gap=42,
            reps=bootstrap_reps,
            seed=seed + 500 + position * 19,
        )
        enriched.append(
            {
                **row,
                "block_ci": [float(block["ci_low"]), float(block["ci_high"])],
                "block_valid_reps": int(block["valid_reps"]),
                "episode_ci": [float(episode["ci_low"]), float(episode["ci_high"])],
                "episode_valid_reps": int(episode["valid_reps"]),
            }
        )
    return {
        "rows": int(len(frame)),
        "brier": brier_score(frame["probability"], frame["outcome"]),
        "brier_skill_vs_baked_base": brier_skill(
            frame["probability"],
            frame["outcome"],
            baseline_probability=base_probability,
        ),
        "base_probability": float(base_probability),
        "states": enriched,
        "point_inversions": detect_probability_inversions(
            enriched,
            material_delta=0.05,
        ),
        "intercept_slope_row_level": calibration_intercept_slope(
            frame["probability"], frame["outcome"]
        ),
    }


def _sample_state_difference(sample: pd.DataFrame) -> float:
    states = sample["state"].astype(str).to_numpy()
    outcomes = pd.to_numeric(sample["outcome"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(outcomes)
    elevated = valid & (states == "elevated")
    risk_off = valid & (states == "risk-off")
    if not elevated.any() or not risk_off.any():
        return float("nan")
    return float(outcomes[risk_off].mean() - outcomes[elevated].mean())


def state_separation_analysis(
    *,
    states: pd.Series,
    outcomes: pd.Series,
    horizon: int,
    bootstrap_reps: int,
    seed: int,
) -> dict[str, object]:
    frame = pd.concat(
        [states.rename("state"), pd.to_numeric(outcomes, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna()
    elevated = frame["state"].eq("elevated")
    risk_off = frame["state"].eq("risk-off")
    elevated_rate = float(frame.loc[elevated, "outcome"].mean()) if elevated.any() else float("nan")
    risk_off_rate = float(frame.loc[risk_off, "outcome"].mean()) if risk_off.any() else float("nan")
    difference = float(risk_off_rate - elevated_rate)
    block = moving_block_bootstrap(
        frame,
        statistic=_sample_state_difference,
        block_length=42,
        reps=bootstrap_reps,
        seed=seed,
    )
    elevated_effective = episode_summary(
        condition=elevated,
        outcome=frame["outcome"],
        horizon=horizon,
        episode_gap=42,
    )
    risk_off_effective = episode_summary(
        condition=risk_off,
        outcome=frame["outcome"],
        horizon=horizon,
        episode_gap=42,
    )
    return {
        "elevated_rate": elevated_rate,
        "risk_off_rate": risk_off_rate,
        "difference": difference,
        "block_ci": [float(block["ci_low"]), float(block["ci_high"])],
        "block_valid_reps": int(block["valid_reps"]),
        "block_invalid_reps": int(block["invalid_reps"]),
        "elevated_effective_n": elevated_effective,
        "risk_off_effective_n": risk_off_effective,
        "material_inversion": bool(
            difference <= -0.05 and np.isfinite(float(block["ci_high"])) and float(block["ci_high"]) < 0.0
        ),
    }


def _lift_record(condition: pd.Series, outcome: pd.Series) -> dict[str, object]:
    record = lift_summary(condition, outcome)
    return {
        "rows": int(record["rows"]),
        "hits": int(record["hits"]),
        "conditional_rate": float(record["conditional_rate"]),
        "base_rate": float(record["base_rate"]),
        "lift": float(record["lift"]),
    }


def stability_lifts(
    *,
    condition: pd.Series,
    outcome: pd.Series,
    horizon: int,
    crises: tuple[tuple[str, str, str], ...],
) -> dict[str, object]:
    frame = pd.concat(
        [condition.rename("condition"), pd.to_numeric(outcome, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna(subset=["outcome"])
    frame = frame.sort_index()
    first_index, second_index = chronological_split_half(pd.DatetimeIndex(frame.index))

    def subset_record(mask: pd.Series | np.ndarray) -> dict[str, object]:
        subset = frame.loc[mask]
        return {
            **_lift_record(subset["condition"], subset["outcome"]),
            "eligible_rows": int(len(subset)),
            "first_date": str(subset.index.min().date()) if len(subset) else None,
            "last_date": str(subset.index.max().date()) if len(subset) else None,
        }

    split_half = {
        "first": subset_record(frame.index.isin(first_index)),
        "second": subset_record(frame.index.isin(second_index)),
    }
    modern = frame.index >= pd.Timestamp("2016-01-01")
    era = {
        "pre_2016": subset_record(~modern),
        "post_2016": subset_record(modern),
    }
    loco: list[dict[str, object]] = []
    for name, start, end in crises:
        keep = crisis_exclusion_mask(
            pd.DatetimeIndex(frame.index),
            crisis_start=pd.Timestamp(start),
            crisis_end=pd.Timestamp(end),
            horizon=horizon,
        )
        record = subset_record(keep.to_numpy(dtype=bool))
        excluded_rows = int((~keep).sum())
        record.update(
            {
                "crisis": name,
                "crisis_start": start,
                "crisis_end": end,
                "excluded_rows": excluded_rows,
                "applicable": excluded_rows > 0,
            }
        )
        loco.append(record)
    return {"split_half": split_half, "era": era, "loco": loco}


def compare_baselines(
    baselines: pd.DataFrame,
    outcomes: pd.Series,
) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for name in baselines.columns:
        frame = pd.concat(
            [
                pd.to_numeric(baselines[name], errors="coerce").rename("score"),
                pd.to_numeric(outcomes, errors="coerce").rename("outcome"),
            ],
            axis=1,
            join="inner",
        ).dropna()
        threshold = 0.5 if name == "trend_context" else 0.91
        elevated_threshold = 0.5 if name == "trend_context" else 0.83
        risk_condition = frame["score"] >= threshold
        elevated_condition = frame["score"] >= elevated_threshold
        risk_lift = lift_summary(risk_condition, frame["outcome"])
        elevated_lift = lift_summary(elevated_condition, frame["outcome"])
        results[str(name)] = {
            "rows": int(len(frame)),
            "average_precision": average_precision(frame["score"], frame["outcome"]),
            "roc_auc": roc_auc(frame["score"], frame["outcome"]),
            "risk_off_threshold": float(threshold),
            "risk_off_rows": int(risk_lift["rows"]),
            "risk_off_lift": float(risk_lift["lift"]),
            "elevated_threshold": float(elevated_threshold),
            "elevated_plus_rows": int(elevated_lift["rows"]),
            "elevated_plus_lift": float(elevated_lift["lift"]),
        }
    return results


def json_ready(value):
    """Convert research results to strict, deterministic JSON-compatible values."""
    from pathlib import Path

    if isinstance(value, Mapping):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return json_ready(value.item())
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


PREREGISTERED_CRISES = (
    ("asian_russia_ltcm", "1997-07-01", "1999-02-28"),
    ("global_financial_crisis", "2007-10-01", "2009-06-30"),
    ("china_equity_devaluation", "2015-06-01", "2016-03-31"),
    ("us_china_trade_war", "2018-01-01", "2019-01-31"),
    ("covid_shock", "2020-01-01", "2020-06-30"),
    ("china_property_regulatory_zero_covid", "2021-02-01", "2022-11-30"),
)

TARGET_SPECS = {
    "5pct_5d": {"horizon": 5, "threshold": 0.05, "confirmatory": False},
    "5pct_10d": {"horizon": 10, "threshold": 0.05, "confirmatory": False},
    "5pct_21d": {"horizon": 21, "threshold": 0.05, "confirmatory": True},
    "10pct_42d": {"horizon": 42, "threshold": 0.10, "confirmatory": True},
}

DATA_SOURCE_SPECS = {
    "shanghai_composite": (
        "data/china/000001.SS.parquet",
        "canonical_benchmark_and_context_gate",
        "repo_store",
    ),
    "csi300_etf_proxy": (
        "data/china/510300.SS.parquet",
        "available_proxy_not_used_for_confirmatory_replication",
        "repo_store_yahoo_adjusted",
    ),
    "china_breadth": (
        "data/china_breadth/breadth.parquet",
        "breadth_subleg",
        "repo_store",
    ),
    "us_2y": ("data/fred/DGS2.parquet", "rate_subleg", "FRED_snapshot"),
    "us_10y_real": ("data/fred/DFII10.parquet", "rate_subleg", "FRED_snapshot"),
    "us_10y": ("data/fred/DGS10.parquet", "rate_and_differential_subleg", "FRED_snapshot"),
    "usd_cnh": ("data/yahoo/CNH_F.parquet", "fx_subleg", "repo_store_yahoo"),
    "dxy": ("data/yahoo/DX-Y.NYB.parquet", "pre_cnh_fx_backfill", "repo_store_yahoo"),
    "china_10y": ("data/china_property/cgb.parquet", "differential_subleg", "repo_store"),
}


def _generic_file_manifest(path, *, role: str, provider: str) -> dict[str, object]:
    from pathlib import Path

    source = Path(path)
    return {
        "path": str(source),
        "role": role,
        "provider": provider,
        "sha256": sha256_file(source),
        "bytes": int(source.stat().st_size),
    }


def _construction_contract(profile, *, source_sha256: str) -> dict[str, object]:
    import hashlib
    import json

    contract = {
        "profile_key": profile.key,
        "benchmark": list(profile.bench),
        "breadth_group": profile.breadth_group,
        "breadth_code": profile.breadth_code,
        "component_legs": json_ready(profile.comp_legs),
        "bands": dict(profile.bands),
        "probability_surface": json_ready(profile.prob_cal),
        "base_probabilities": dict(profile.prob_base),
        "percentile_window_sessions": 504,
        "rate_and_fx_change_sessions": 21,
        "dxy_backfill_change_sessions": 63,
        "context_gate": "benchmark_below_causal_200_session_mean",
        "loud_state_cap_when_gate_closed": "caution",
        "engine_source_sha256": source_sha256,
    }
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    return {
        "hash_algorithm": "sha256",
        "construction_hash": hashlib.sha256(encoded).hexdigest(),
        "contract": contract,
    }


def build_data_provenance(repo_root, profile) -> dict[str, object]:
    from pathlib import Path

    root = Path(repo_root)
    sources: dict[str, object] = {}
    for key, (relative, role, provider) in DATA_SOURCE_SPECS.items():
        path = root / relative
        manifest = dataframe_file_manifest(path, role=role, provider=provider)
        manifest["path"] = relative
        manifest["point_in_time_status"] = "causal_transform_on_latest_repository_snapshot"
        manifest["vintage_identifier_available"] = False
        sources[key] = manifest
    ledger_relative = "data/risk_radar_intl/cn_forward_log.jsonl"
    ledger_manifest = _generic_file_manifest(
        root / ledger_relative,
        role="genuinely_issued_forward_evidence",
        provider="committed_forward_ledger",
    )
    ledger_manifest["path"] = ledger_relative
    ledger_manifest["rows"] = sum(
        1 for line in (root / ledger_relative).read_text().splitlines() if line.strip()
    )
    sources["cn_forward_ledger"] = ledger_manifest
    frozen_sources = verify_frozen_sources(root, FROZEN_SOURCE_SHA256)
    for relative, record in frozen_sources.items():
        record["path"] = relative
    construction = _construction_contract(
        profile,
        source_sha256=FROZEN_SOURCE_SHA256["engine/risk_radar_intl.py"],
    )
    return {
        "evidence_class": "reconstructed_history_plus_separate_issued_forward_ledger",
        "historical_snapshot_pit_status": "causal_transform_on_snapshot_not_vintage_pit",
        "source_files": sources,
        "frozen_source_files": frozen_sources,
        "construction": construction,
        "csi300_replication_qualification": qualify_csi300_replication(root),
        "historical_claim_provenance": {
            "record": "merged PR #711 prose and production docstring",
            "claimed_composite_lift": 2.07,
            "claimed_split_half": [2.28, 2.00],
            "claimed_permutation_p": 0.01,
            "claimed_csi300_lift": 2.22,
            "research_harness_committed_with_claim": False,
            "immutable_result_artifact_committed_with_claim": False,
            "exact_original_extreme_trigger_recoverable": False,
        },
        "probability_surface_provenance": {
            "baked_surface_location": "engine/risk_radar_intl.py::CN_PROFILE",
            "current_calibrator_policy": "flat_at_base_for_prob_cal; raw state rates descriptive_only",
            "current_calibrator_generated_baked_surface": False,
            "overlay_present": False,
        },
    }


def load_exact_production_signal(repo_root):
    from pathlib import Path
    from engine import risk_radar_intl as production

    root = Path(repo_root).resolve()
    verify_frozen_sources(root, FROZEN_SOURCE_SHA256)
    verify_no_cn_overlay(root)
    benchmark, sublegs, composite, gate = production.composite_series(production.CN_PROFILE)
    if benchmark is None or sublegs is None or composite is None or gate is None:
        raise RuntimeError("exact CN production construction returned no data")
    states = reconstruct_states(composite, gate, production.CN_PROFILE.bands)
    signal = pd.concat(
        [
            pd.to_numeric(benchmark, errors="coerce").rename("close"),
            pd.to_numeric(composite, errors="coerce").rename("composite"),
            gate.fillna(False).astype(bool).rename("gate"),
            states[["score", "state_ungated", "state"]],
        ],
        axis=1,
        join="outer",
    ).sort_index()
    baselines = build_baseline_scores(
        sublegs=sublegs,
        composite=composite,
        gate=gate,
        percentile_window=504,
    )
    return production.CN_PROFILE, benchmark, sublegs, signal, baselines


def _read_close_from_parquet(path) -> pd.Series:
    frame = pd.read_parquet(path)
    column = "close" if "close" in frame.columns else frame.columns[0]
    close = pd.to_numeric(frame[column], errors="coerce").dropna()
    close.index = pd.to_datetime(close.index)
    return close.sort_index()


def _sample_brier_difference(sample: pd.DataFrame) -> float:
    gated = pd.to_numeric(sample["gated_probability"], errors="coerce").to_numpy(dtype=float)
    ungated = pd.to_numeric(sample["ungated_probability"], errors="coerce").to_numpy(dtype=float)
    outcome = pd.to_numeric(sample["outcome"], errors="coerce").to_numpy(dtype=float)
    valid = np.isfinite(gated) & np.isfinite(ungated) & np.isfinite(outcome)
    if not valid.any():
        return float("nan")
    gated_brier = float(np.mean(np.square(gated[valid] - outcome[valid])))
    ungated_brier = float(np.mean(np.square(ungated[valid] - outcome[valid])))
    return gated_brier - ungated_brier


def _sample_lift_difference(sample: pd.DataFrame) -> float:
    outcome = pd.to_numeric(sample["outcome"], errors="coerce").to_numpy(dtype=float)
    gated = sample["gated_condition"].fillna(False).to_numpy(dtype=bool)
    ungated = sample["ungated_condition"].fillna(False).to_numpy(dtype=bool)
    valid = np.isfinite(outcome)
    base = float(outcome[valid].mean()) if valid.any() else float("nan")
    if not np.isfinite(base) or base <= 0.0:
        return float("nan")
    gated_selected = valid & gated
    ungated_selected = valid & ungated
    if not gated_selected.any() or not ungated_selected.any():
        return float("nan")
    gated_lift = float(outcome[gated_selected].mean() / base)
    ungated_lift = float(outcome[ungated_selected].mean() / base)
    return gated_lift - ungated_lift


def context_gate_analysis(
    *,
    states: pd.Series,
    ungated_states: pd.Series,
    outcomes: pd.Series,
    probability_surface: Mapping[str, float],
    bootstrap_reps: int,
    seed: int,
    horizon: int = 21,
) -> dict[str, object]:
    frame = pd.concat(
        [
            states.rename("state"),
            ungated_states.rename("state_ungated"),
            pd.to_numeric(outcomes, errors="coerce").rename("outcome"),
        ],
        axis=1,
        join="inner",
    ).dropna()
    frame["gated_probability"] = state_probability_series(frame["state"], probability_surface)
    frame["ungated_probability"] = state_probability_series(
        frame["state_ungated"], probability_surface
    )
    brier_difference = _sample_brier_difference(frame)
    brier_bootstrap = moving_block_bootstrap(
        frame,
        statistic=_sample_brier_difference,
        block_length=42,
        reps=bootstrap_reps,
        seed=seed,
    )

    def lift_comparison(
        gated_condition: pd.Series,
        ungated_condition: pd.Series,
        *,
        local_seed: int,
    ) -> dict[str, object]:
        comparison = frame.copy()
        comparison["gated_condition"] = gated_condition.to_numpy(dtype=bool)
        comparison["ungated_condition"] = ungated_condition.to_numpy(dtype=bool)
        difference = _sample_lift_difference(comparison)
        bootstrap = moving_block_bootstrap(
            comparison,
            statistic=_sample_lift_difference,
            block_length=42,
            reps=bootstrap_reps,
            seed=local_seed,
        )
        gated_lift = lift_summary(comparison["gated_condition"], comparison["outcome"])
        ungated_lift = lift_summary(comparison["ungated_condition"], comparison["outcome"])
        return {
            "gated_lift": float(gated_lift["lift"]),
            "ungated_lift": float(ungated_lift["lift"]),
            "difference": difference,
            "block_ci": [float(bootstrap["ci_low"]), float(bootstrap["ci_high"])],
        }

    gated_risk_off = frame["state"].eq("risk-off")
    ungated_risk_off = frame["state_ungated"].eq("risk-off")
    gated_elevated_plus = frame["state"].isin(["elevated", "risk-off"])
    ungated_elevated_plus = frame["state_ungated"].isin(["elevated", "risk-off"])
    risk = lift_comparison(gated_risk_off, ungated_risk_off, local_seed=seed + 1)
    elevated = lift_comparison(
        gated_elevated_plus,
        ungated_elevated_plus,
        local_seed=seed + 2,
    )
    elevated_effective_n = episode_summary(
        condition=gated_elevated_plus,
        outcome=frame["outcome"],
        horizon=horizon,
        episode_gap=42,
    )
    return {
        "rows": int(len(frame)),
        "gated_brier": brier_score(frame["gated_probability"], frame["outcome"]),
        "ungated_brier": brier_score(frame["ungated_probability"], frame["outcome"]),
        "brier_difference_gated_minus_ungated": brier_difference,
        "brier_difference_block_ci": [
            float(brier_bootstrap["ci_low"]),
            float(brier_bootstrap["ci_high"]),
        ],
        "gated_risk_off_lift": risk["gated_lift"],
        "ungated_risk_off_lift": risk["ungated_lift"],
        "risk_off_lift_difference_gated_minus_ungated": risk["difference"],
        "risk_off_lift_difference_block_ci": risk["block_ci"],
        "gated_elevated_plus_lift": elevated["gated_lift"],
        "ungated_elevated_plus_lift": elevated["ungated_lift"],
        "elevated_plus_lift_difference_gated_minus_ungated": elevated["difference"],
        "elevated_plus_lift_difference_block_ci": elevated["block_ci"],
        "gated_elevated_plus_effective_n": elevated_effective_n,
        "ranking_score_unchanged": True,
        "continuous_ap_difference": 0.0,
    }

def _sample_adjacent_state_difference(
    sample: pd.DataFrame,
    *,
    lower_state: str,
    higher_state: str,
) -> float:
    outcomes = pd.to_numeric(sample["outcome"], errors="coerce").to_numpy(dtype=float)
    states = sample["state"].astype(str).to_numpy()
    valid = np.isfinite(outcomes)
    lower = valid & (states == lower_state)
    higher = valid & (states == higher_state)
    if not lower.any() or not higher.any():
        return float("nan")
    return float(outcomes[higher].mean() - outcomes[lower].mean())


def dependence_aware_inversions(
    *,
    states: pd.Series,
    outcomes: pd.Series,
    bootstrap_reps: int,
    seed: int,
) -> list[dict[str, object]]:
    frame = pd.concat(
        [states.rename("state"), pd.to_numeric(outcomes, errors="coerce").rename("outcome")],
        axis=1,
        join="inner",
    ).dropna()
    rows: list[dict[str, object]] = []
    for position, (lower, higher) in enumerate(zip(STATE_ORDER, STATE_ORDER[1:])):
        statistic = lambda sample, lo=lower, hi=higher: _sample_adjacent_state_difference(
            sample, lower_state=lo, higher_state=hi
        )
        estimate = statistic(frame)
        bootstrap = moving_block_bootstrap(
            frame,
            statistic=statistic,
            block_length=42,
            reps=bootstrap_reps,
            seed=seed + position * 43,
        )
        rows.append(
            {
                "lower_state": lower,
                "higher_state": higher,
                "difference": estimate,
                "block_ci": [float(bootstrap["ci_low"]), float(bootstrap["ci_high"])],
                "material_point_inversion": bool(np.isfinite(estimate) and estimate <= -0.05),
                "supported_material_inversion": bool(
                    np.isfinite(estimate)
                    and estimate <= -0.05
                    and np.isfinite(float(bootstrap["ci_high"]))
                    and float(bootstrap["ci_high"]) < 0.0
                ),
            }
        )
    return rows


def add_delayed_base_comparison(
    calibration: dict[str, object],
    *,
    probabilities: pd.Series,
    outcomes: pd.Series,
    horizon: int,
) -> None:
    delayed = delayed_expanding_base(outcomes, horizon=horizon, min_history=252)
    frame = pd.concat(
        [
            pd.to_numeric(probabilities, errors="coerce").rename("production"),
            pd.to_numeric(delayed, errors="coerce").rename("delayed"),
            pd.to_numeric(outcomes, errors="coerce").rename("outcome"),
        ],
        axis=1,
        join="inner",
    ).dropna()
    production_brier = brier_score(frame["production"], frame["outcome"])
    delayed_brier = brier_score(frame["delayed"], frame["outcome"])
    calibration["delayed_expanding_base"] = {
        "rows": int(len(frame)),
        "production_brier_on_overlap": production_brier,
        "delayed_base_brier": delayed_brier,
        "production_skill_vs_delayed_base": (
            float(1.0 - production_brier / delayed_brier)
            if np.isfinite(production_brier) and np.isfinite(delayed_brier) and delayed_brier > 0.0
            else float("nan")
        ),
    }


def _target_frame(signal: pd.DataFrame, outcome: pd.Series) -> pd.DataFrame:
    return signal.join(outcome.rename("outcome"), how="left")


def _finite_lifts(records: list[dict[str, object]]) -> tuple[float, ...]:
    values: list[float] = []
    for record in records:
        if int(record.get("excluded_rows", 0)) <= 0:
            continue
        value = record.get("lift")
        if value is not None and np.isfinite(float(value)):
            values.append(float(value))
    return tuple(values)


def _find_state_row(calibration: Mapping[str, object], state: str) -> dict[str, object] | None:
    rows = calibration.get("states")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("state") == state:
            return row
    return None


def _qualify_calibration_slope(calibration: dict[str, object]) -> None:
    rows = calibration.get("states")
    raw = calibration.pop("intercept_slope_row_level", {"qualified": False})
    if not isinstance(rows, list):
        calibration["intercept_slope"] = {
            "qualified": False,
            "reason": "missing_state_table",
        }
        return
    powered = [
        row for row in rows
        if isinstance(row, Mapping) and int(row.get("effective_n_ceiling", 0)) >= 8
    ]
    hit_episodes = sum(int(row.get("hit_episodes", 0)) for row in powered)
    nonhit_episodes = sum(int(row.get("nonhit_episodes", 0)) for row in powered)
    if len(powered) < 3 or hit_episodes < 20 or nonhit_episodes < 20:
        calibration["intercept_slope"] = {
            "qualified": False,
            "reason": "preregistered_episode_power_floor_not_met",
            "powered_bins": len(powered),
            "hit_episodes": hit_episodes,
            "nonhit_episodes": nonhit_episodes,
            "row_level_diagnostic": raw,
        }
        return
    calibration["intercept_slope"] = {
        **raw,
        "episode_qualification_met": True,
        "powered_bins": len(powered),
        "hit_episodes": hit_episodes,
        "nonhit_episodes": nonhit_episodes,
    }


def _claim_extreme_hazard(
    primary: Mapping[str, object],
    historical: Mapping[str, object],
) -> dict[str, object]:
    p = primary["risk_off"]
    h = historical["risk_off"]
    p_effective = int(p["effective_n"]["effective_n_ceiling"])
    h_effective = int(h["effective_n"]["effective_n_ceiling"])
    if min(p_effective, h_effective) < 8:
        return {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "basis": f"effective episodes are {p_effective} for 5%/21d and {h_effective} for 10%/42d",
        }
    p_lift = float(p["lift"])
    h_lift = float(h["lift"])
    if p_lift <= 1.0 and h_lift <= 1.0:
        return {
            "verdict": "FAIL / REMOVE",
            "basis": f"neither confirmatory target discriminates: lifts {p_lift:.2f} and {h_lift:.2f}",
        }
    robust = (
        p_effective >= 20
        and h_effective >= 20
        and float(p["block_ci"][0]) > 1.0
        and float(h["block_ci"][0]) > 1.0
    )
    return {
        "verdict": "KEEP" if robust else "KEEP_BUT_RELABEL",
        "basis": (
            f"emitted risk-off lift is {p_lift:.2f}x for 5%/21d and {h_lift:.2f}x for 10%/42d; "
            f"effective episodes {p_effective}/{h_effective}. Call this an elevated external-driver hazard, "
            "not an exact crisis probability."
        ),
    }


def _claim_context_gate(
    context: Mapping[str, object],
    *,
    effective_n: int,
) -> dict[str, object]:
    brier_delta = float(context["brier_difference_gated_minus_ungated"])
    lift_delta = float(context["elevated_plus_lift_difference_gated_minus_ungated"])
    brier_ci = context["brier_difference_block_ci"]
    lift_ci = context["elevated_plus_lift_difference_block_ci"]
    brier_supported = brier_delta < 0.0 and float(brier_ci[1]) < 0.0
    lift_supported = lift_delta > 0.0 and float(lift_ci[0]) > 0.0
    harmful_supported = (
        brier_delta > 0.0
        and float(brier_ci[0]) > 0.0
        and lift_delta < 0.0
        and float(lift_ci[1]) < 0.0
    )
    if effective_n < 8:
        verdict = "INSUFFICIENT_EVIDENCE"
    elif effective_n >= 20 and (brier_supported or lift_supported):
        verdict = "KEEP"
    elif harmful_supported:
        verdict = "FAIL / REMOVE"
    else:
        verdict = "KEEP_BUT_RELABEL"
    return {
        "verdict": verdict,
        "basis": (
            f"gate-minus-ungated Brier difference {brier_delta:.4f}; elevated-plus lift difference "
            f"{lift_delta:.2f}x; effective gated elevated-plus episodes {effective_n}; "
            "continuous ranking score unchanged."
        ),
    }


def qualify_csi300_replication(repo_root) -> dict[str, object]:
    """Apply the preregistered cash-index requirement without substituting an ETF proxy."""
    from pathlib import Path

    root = Path(repo_root)
    exact_candidates = (
        "data/china/000300.SS.parquet",
        "data/china/000300.SH.parquet",
        "data/china/CSI300.parquet",
    )
    exact_present = [relative for relative in exact_candidates if (root / relative).is_file()]
    proxy_relative = "data/china/510300.SS.parquet"
    proxy_available = (root / proxy_relative).is_file()
    if exact_present:
        basis = (
            "An exact cash-index candidate exists but was not part of this frozen source manifest; "
            "a separately frozen exact-series run is required."
        )
    else:
        basis = (
            "No exact CSI300 cash-index history is available. The 510300.SS ETF proxy is disclosed "
            "but is not used as confirmatory replication evidence."
        )
    return {
        "verdict": "INSUFFICIENT_EVIDENCE",
        "cash_index_series_available": bool(exact_present),
        "exact_candidates_checked": list(exact_candidates),
        "exact_candidates_present": exact_present,
        "proxy_available": proxy_available,
        "proxy_symbol": "510300.SS" if proxy_available else None,
        "proxy_path": proxy_relative if proxy_available else None,
        "quantitative_replication_performed": False,
        "basis": basis,
    }


def adjudicate_historical_record_claim(historical: Mapping[str, object]) -> dict[str, object]:
    """Adjudicate the historical record against the exact emitted production state."""
    metric = historical["risk_off"]
    stability = historical["stability"]["emitted_risk_off"]
    adjudication = adjudicate_historical_lift(
        lift=float(metric["lift"]),
        ci=tuple(float(value) for value in metric["block_ci"]),
        split_lifts=(
            float(stability["split_half"]["first"]["lift"]),
            float(stability["split_half"]["second"]["lift"]),
        ),
        modern_lift=float(stability["era"]["post_2016"]["lift"]),
        loco_lifts=_finite_lifts(stability["loco"]),
        permutation_p=float(historical["permutation"]["risk_off"]["p_value"]),
        effective_n=int(metric["effective_n"]["effective_n_ceiling"]),
    )
    adjudication.update(
        {
            "metric_source": "emitted_production_risk_off",
            "observed_lift": float(metric["lift"]),
            "basis": (
                f"exact emitted production risk-off lift {float(metric['lift']):.2f}x with "
                f"{int(metric['effective_n']['effective_n_ceiling'])} effective episodes; the "
                "historical record is 2.07x, and its original executable harness was not committed."
            ),
        }
    )
    return adjudication


def assess_band_cutoffs(
    calibration: Mapping[str, object],
    bands: Mapping[str, float],
) -> dict[str, object]:
    """Separate observed state ordering from untested threshold optimality."""
    supported_inversion = False
    minimum_effective_by_horizon: dict[str, int] = {}
    for horizon in ("h5", "h10", "h21"):
        record = calibration.get(horizon, {})
        inversions = record.get("dependence_aware_inversions", []) if isinstance(record, Mapping) else []
        supported_inversion = supported_inversion or any(
            bool(row.get("supported_material_inversion"))
            for row in inversions
            if isinstance(row, Mapping)
        )
        states = record.get("states", []) if isinstance(record, Mapping) else []
        effective = [
            int(row.get("effective_n_ceiling", 0))
            for row in states
            if isinstance(row, Mapping)
        ]
        minimum_effective_by_horizon[horizon] = min(effective) if effective else 0
    if supported_inversion:
        ordering_verdict = "RECALIBRATION_CANDIDATE"
    elif all(value >= 20 for value in minimum_effective_by_horizon.values()):
        ordering_verdict = "KEEP"
    else:
        ordering_verdict = "KEEP_BUT_RELABEL"
    return {
        "exact_cutoffs": {key: float(bands[key]) for key in ("watch", "caution", "elevated", "risk_off")},
        "monotonic_ordering_verdict": ordering_verdict,
        "supported_material_inversion": supported_inversion,
        "minimum_state_effective_n_by_horizon": minimum_effective_by_horizon,
        "cutoff_optimality_verdict": "INSUFFICIENT_EVIDENCE",
        "cutoff_optimality_basis": (
            "The fixed production cuts were tested as-is. No preregistered neighborhood sensitivity or "
            "threshold search was permitted, so optimality is not established."
        ),
        "post_hoc_threshold_search_performed": False,
    }

def run_revalidation(
    *,
    repo_root,
    bootstrap_reps: int,
    permutation_reps: int,
    seed: int,
) -> dict[str, object]:
    from pathlib import Path

    if bootstrap_reps <= 0 or permutation_reps <= 0:
        raise ValueError("replication counts must be positive")
    root = Path(repo_root).resolve()
    profile, benchmark, sublegs, signal, baselines = load_exact_production_signal(root)
    eligible_signal = signal.dropna(subset=["composite"]).copy()
    data_provenance = build_data_provenance(root, profile)

    outcomes: dict[str, pd.Series] = {}
    targets: dict[str, dict[str, object]] = {}
    for position, (target_name, spec) in enumerate(TARGET_SPECS.items()):
        horizon = int(spec["horizon"])
        threshold = float(spec["threshold"])
        outcome = binary_outcome(
            forward_max_drawdown(benchmark, horizon=horizon),
            threshold=threshold,
        )
        outcomes[target_name] = outcome
        frame = _target_frame(signal, outcome)
        analysis = analyze_target(
            frame,
            target_name=target_name,
            benchmark_label="Shanghai Composite (000001.SS)",
            horizon=horizon,
            bootstrap_reps=bootstrap_reps,
            permutation_reps=permutation_reps,
            seed=seed + position * 10000,
        )
        analysis["threshold"] = threshold
        analysis["confirmatory"] = bool(spec["confirmatory"])
        mature = frame.dropna(subset=["outcome", "composite"])
        analysis["stability"] = {
            "emitted_risk_off": stability_lifts(
                condition=mature["state"].eq("risk-off"),
                outcome=mature["outcome"],
                horizon=horizon,
                crises=PREREGISTERED_CRISES,
            ),
            "ungated_risk_off": stability_lifts(
                condition=mature["state_ungated"].eq("risk-off"),
                outcome=mature["outcome"],
                horizon=horizon,
                crises=PREREGISTERED_CRISES,
            ),
        }
        analysis["baseline_comparison"] = compare_baselines(
            baselines.reindex(mature.index),
            mature["outcome"],
        )
        targets[target_name] = analysis

    calibration: dict[str, dict[str, object]] = {}
    calibration_targets = {
        "h5": ("5pct_5d", 5),
        "h10": ("5pct_10d", 10),
        "h21": ("5pct_21d", 21),
    }
    for position, (horizon_key, (target_name, horizon)) in enumerate(calibration_targets.items()):
        outcome = outcomes[target_name]
        probabilities = state_probability_series(
            eligible_signal["state"], profile.prob_cal[horizon_key]
        )
        eligible_outcome = outcome.reindex(eligible_signal.index)
        cal = analyze_calibration(
            states=eligible_signal["state"],
            probabilities=probabilities,
            outcomes=eligible_outcome,
            base_probability=float(profile.prob_base[horizon_key]),
            horizon=horizon,
            bootstrap_reps=bootstrap_reps,
            seed=seed + 50000 + position * 5000,
        )
        add_delayed_base_comparison(
            cal,
            probabilities=probabilities,
            outcomes=eligible_outcome,
            horizon=horizon,
        )
        cal["dependence_aware_inversions"] = dependence_aware_inversions(
            states=eligible_signal["state"],
            outcomes=eligible_outcome,
            bootstrap_reps=bootstrap_reps,
            seed=seed + 70000 + position * 5000,
        )
        cal["state_separation"] = state_separation_analysis(
            states=eligible_signal["state"],
            outcomes=eligible_outcome,
            horizon=horizon,
            bootstrap_reps=bootstrap_reps,
            seed=seed + 90000 + position * 5000,
        )
        _qualify_calibration_slope(cal)
        calibration[horizon_key] = cal

    context_gate = context_gate_analysis(
        states=eligible_signal["state"],
        ungated_states=eligible_signal["state_ungated"],
        outcomes=outcomes["5pct_21d"].reindex(eligible_signal.index),
        probability_surface=profile.prob_cal["h21"],
        bootstrap_reps=bootstrap_reps,
        seed=seed + 120000,
    )
    context_gate["historical_10pct_42d_gated_lift"] = targets["10pct_42d"]["risk_off"]["lift"]
    context_gate["historical_10pct_42d_ungated_lift"] = targets["10pct_42d"]["ungated_risk_off"]["lift"]

    csi_replication = qualify_csi300_replication(root)

    forward_ledger = summarize_forward_ledger(
        root / "data/risk_radar_intl/cn_forward_log.jsonl"
    )
    valid_signal = eligible_signal
    latest = valid_signal.iloc[-1]
    current_snapshot = {
        "asof": str(valid_signal.index[-1].date()),
        "composite_percentile": float(latest["composite"]),
        "intensity_score_0_100": float(latest["score"]),
        "state_ungated": str(latest["state_ungated"]),
        "state": str(latest["state"]),
        "context_gate_open": bool(latest["gate"]),
        "semantics": "causal rank within the trailing 504 available sessions of the composite; not a drawdown probability or confidence level",
    }

    primary = targets["5pct_21d"]
    historical = targets["10pct_42d"]
    risk_off_h21 = _find_state_row(calibration["h21"], "risk-off")
    if risk_off_h21 is None:
        probability_claim = {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "basis": "no mature risk-off calibration row",
        }
    else:
        material_inversion = any(
            bool(row.get("supported_material_inversion"))
            for row in calibration["h21"]["dependence_aware_inversions"]
            if row.get("higher_state") == "risk-off"
        )
        adjudication = adjudicate_probability(
            forecast=0.50,
            observed=float(risk_off_h21["observed"]),
            block_ci=tuple(float(value) for value in risk_off_h21["block_ci"]),
            episode_ci=tuple(float(value) for value in risk_off_h21["episode_ci"]),
            brier_skill_value=float(calibration["h21"]["brier_skill_vs_baked_base"]),
            effective_n=int(risk_off_h21["effective_n_ceiling"]),
            hit_episodes=int(risk_off_h21["hit_episodes"]),
            nonhit_episodes=int(risk_off_h21["nonhit_episodes"]),
            material_inversion=material_inversion,
        )
        probability_claim = {
            **adjudication,
            "basis": (
                f"observed {float(risk_off_h21['observed']):.3f} versus displayed 0.500; "
                f"effective episodes {int(risk_off_h21['effective_n_ceiling'])}; "
                f"block CI {risk_off_h21['block_ci']}; episode CI {risk_off_h21['episode_ci']}."
            ),
        }

    historical_adjudication = adjudicate_historical_record_claim(historical)

    separation = calibration["h21"]["state_separation"]
    separation_adjudication = adjudicate_state_separation(
        difference=float(separation["difference"]),
        ci=tuple(float(value) for value in separation["block_ci"]),
        elevated_effective_n=int(separation["elevated_effective_n"]["effective_n_ceiling"]),
        risk_off_effective_n=int(separation["risk_off_effective_n"]["effective_n_ceiling"]),
        material_inversion=bool(separation["material_inversion"]),
    )
    separation_adjudication["basis"] = (
        f"risk-off minus elevated observed 5%/21d rate {float(separation['difference']):.3f}; "
        f"block CI {separation['block_ci']}; effective episodes "
        f"{int(separation['elevated_effective_n']['effective_n_ceiling'])}/"
        f"{int(separation['risk_off_effective_n']['effective_n_ceiling'])}."
    )

    ladder_powered = all(
        (_find_state_row(calibration[key], "risk-off") or {}).get("effective_n_ceiling", 0) >= 20
        for key in ("h5", "h10", "h21")
    )
    supported_inversion = any(
        bool(row.get("supported_material_inversion"))
        for key in ("h5", "h10", "h21")
        for row in calibration[key]["dependence_aware_inversions"]
    )
    if supported_inversion and ladder_powered:
        ladder_verdict = "RECALIBRATION_CANDIDATE"
    elif not ladder_powered:
        ladder_verdict = "INSUFFICIENT_EVIDENCE"
    else:
        ladder_verdict = "KEEP_BUT_RELABEL"

    primary_effective = int(primary["risk_off"]["effective_n"]["effective_n_ceiling"])
    band_cutoff_assessment = assess_band_cutoffs(calibration, profile.bands)

    claims = {
        "extreme China external-driver hazard": _claim_extreme_hazard(primary, historical),
        "98th-percentile intensity semantics": {
            "verdict": "KEEP_BUT_RELABEL",
            "basis": (
                f"current score is {current_snapshot['intensity_score_0_100']:.2f}; valid only as a causal "
                "trailing-504-session composite percentile, not 98% drawdown odds or all-history extremity."
            ),
        },
        ">=5%/21d risk-off probability = 50%": probability_claim,
        ">=10%/42d historical lift ~2.07x": historical_adjudication,
        "elevated vs risk-off separation": separation_adjudication,
        "5d / 10d / 21d ladder": {
            "verdict": ladder_verdict,
            "basis": (
                "The surface is mechanically monotone, but its current calibrator explicitly seeds flat-at-base "
                f"and the loud-state episode floor is not met across all horizons; supported material inversion={supported_inversion}."
            ),
        },
        "context gate value-add": _claim_context_gate(
            context_gate,
            effective_n=int(
                context_gate["gated_elevated_plus_effective_n"]["effective_n_ceiling"]
            ),
        ),
    }

    discoveries = [
        "The current production calibrator explicitly treats raw state rates as descriptive and emits a flat-at-base probability surface; it is not the provenance of the baked CN ladder.",
        "Merged PR #711 and the engine docstring preserve the 2.07x claim, but no executable research harness, immutable result artifact, or exact original extreme trigger accompanied the claim.",
        "No exact CSI300 cash-index series was found. The available 510300.SS ETF proxy is disclosed but withheld from confirmatory replication under the preregistration.",
        "Historical transforms are causal on repository snapshots, but vintage identifiers are unavailable; this is not fully vintage point-in-time evidence.",
        "Issued forward rows remain a separate evidence class and are not pooled with reconstructed history; the ledger lacks exact model-cohort and independent-episode identifiers.",
    ]
    proposed_followup = [
        "Do not retune production in this PR. Open a separately preregistered calibration candidate only after the forward authority floors and independent loud-state episode floors mature.",
        "Recover or rebuild the original PR #711 validation harness under a new provenance-only commission; do not retroactively call the present reconstruction byte-identical replication.",
        "Acquire a lawful exact CSI300 cash-index history for the canonical replication; any 510300.SS ETF-proxy study requires its own separately preregistered, explicitly proxy-labeled analysis.",
    ]
    what_must_not_be_redone = [
        f"Preregistration commit {PREREG_SHA} is immutable and must not be rewritten after outcome inspection.",
        "Do not merge reconstructed historical evidence with the issued forward ledger.",
        "Do not reinterpret the 98th-percentile intensity as a 98% drawdown probability.",
        "Do not change production bands, probabilities, gate logic, can_force, UI, Market State policy, or consumers in this research PR.",
        "Do not silently substitute FXI or label 510300.SS as the exact CSI300 cash index.",
    ]

    return {
        "schema": "cn_risk_radar_revalidation.v1",
        "operation_key": OPERATION_KEY,
        "classification": "research_only_no_production_behavior_change",
        "base_sha": BASE_SHA,
        "prereg_sha": PREREG_SHA,
        "harness_path": "scripts/research/cn_risk_radar_revalidation.py",
        "harness_sha256": sha256_file(__file__),
        "run_parameters": {
            "bootstrap_reps": bootstrap_reps,
            "permutation_reps": permutation_reps,
            "seed": seed,
            "moving_block_length_sessions": 42,
            "episode_gap_sessions": 42,
        },
        "data_provenance": data_provenance,
        "current_snapshot": current_snapshot,
        "targets": targets,
        "csi300_replication": csi_replication,
        "calibration": calibration,
        "context_gate": context_gate,
        "band_cutoff_assessment": band_cutoff_assessment,
        "forward_ledger": forward_ledger,
        "claims": claims,
        "discoveries": discoveries,
        "proposed_followup": proposed_followup,
        "what_must_not_be_redone": what_must_not_be_redone,
    }


def _report_number(value, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "n/a"
    return f"{numeric:.{digits}f}"


def _report_pct(value, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "n/a"
    return f"{numeric * 100.0:.{digits}f}%"


def _report_ci(value, *, pct: bool = False) -> str:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return "n/a"
    formatter = _report_pct if pct else _report_number
    return f"[{formatter(value[0])}, {formatter(value[1])}]"


def _render_report_v2(result: Mapping[str, object]) -> str:
    lines: list[str] = [
        "# China External-Driver Risk Radar — Preregistered Revalidation",
        "",
        f"**Operation:** `{result.get('operation_key', 'unknown')}`  ",
        f"**Base:** `{result.get('base_sha', 'unknown')}`  ",
        f"**Preregistration:** `{result.get('prereg_sha', 'unknown')}`  ",
        "**Status:** Draft/HOLD research package; production behavior unchanged.",
        "",
    ]
    snapshot = result.get("current_snapshot", {})
    if isinstance(snapshot, Mapping):
        lines.extend(
            [
                "## Executive conclusion",
                "",
                (
                    f"As of **{snapshot.get('asof', 'n/a')}**, the exact production composite is "
                    f"**{_report_number(snapshot.get('intensity_score_0_100'), 2)} / 100** and emits "
                    f"**{snapshot.get('state', 'n/a')}** with the context gate "
                    f"{'open' if snapshot.get('context_gate_open') else 'closed'}. This score is a "
                    "causal trailing-504-session rank, not a 98% drawdown probability."
                ),
                "",
                (
                    "The construction retains meaningful hazard discrimination, especially for the historical "
                    "10%/42-session target, but the independent-episode ceiling is 18 for the current loud state. "
                    "That supports directional hazard language, not certification of the exact 50% displayed odds."
                ),
                "",
            ]
        )

    lines.extend(["## Claim-by-claim adjudication", "", "| Claim | Verdict | Basis |", "|---|---|---|"])
    claims = result.get("claims", {})
    if isinstance(claims, Mapping):
        for claim in _CLAIM_KEYS:
            record = claims.get(claim, {})
            if not isinstance(record, Mapping):
                record = {}
            basis = str(record.get("basis", "No basis recorded.")).replace("|", "\\|")
            lines.append(f"| {claim} | **{record.get('verdict', 'INSUFFICIENT_EVIDENCE')}** | {basis} |")
    lines.append("")

    targets = result.get("targets", {})
    lines.extend(["## Confirmatory targets — Shanghai Composite", ""])
    if isinstance(targets, Mapping):
        lines.extend(
            [
                "| Target | Eligible | Base rate | Risk-off rate | Risk-off lift | Block 95% CI | Effective episodes | Permutation p | AP / base | AUC |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for key in ("5pct_21d", "10pct_42d"):
            target = targets.get(key, {})
            if not isinstance(target, Mapping):
                continue
            risk = target.get("risk_off", {})
            disc = target.get("continuous_discrimination", {})
            perm = target.get("permutation", {}).get("risk_off", {}) if isinstance(target.get("permutation"), Mapping) else {}
            effective = risk.get("effective_n", {}) if isinstance(risk, Mapping) else {}
            lines.append(
                "| {label} | {eligible} | {base} | {rate} | {lift}× | {ci} | {eff} | {p} | {ap}× | {auc} |".format(
                    label=">=5% / 21 sessions" if key == "5pct_21d" else ">=10% / 42 sessions",
                    eligible=target.get("eligible_rows", "n/a"),
                    base=_report_pct(target.get("base_rate")),
                    rate=_report_pct(risk.get("conditional_rate") if isinstance(risk, Mapping) else None),
                    lift=_report_number(risk.get("lift") if isinstance(risk, Mapping) else None, 2),
                    ci=_report_ci(risk.get("block_ci") if isinstance(risk, Mapping) else None),
                    eff=effective.get("effective_n_ceiling", "n/a") if isinstance(effective, Mapping) else "n/a",
                    p=_report_number(perm.get("p_value") if isinstance(perm, Mapping) else None, 4),
                    ap=_report_number(disc.get("ap_over_base") if isinstance(disc, Mapping) else None, 2),
                    auc=_report_number(disc.get("roc_auc") if isinstance(disc, Mapping) else None, 3),
                )
            )
        lines.extend(
            [
                "",
                "Both confirmatory targets use the exact **emitted production state after the context gate**. The ungated composite remains a preregistered counterfactual baseline only; it is not used to rescue or reproduce the historical claim.",
                "",
            ]
        )

    historical = targets.get("10pct_42d", {}) if isinstance(targets, Mapping) else {}
    stability = historical.get("stability", {}).get("emitted_risk_off", {}) if isinstance(historical, Mapping) else {}
    if isinstance(stability, Mapping):
        lines.extend(["## Historical 10%/42-session stability", "", "### Split-half and era", ""])
        lines.extend(["| Slice | Eligible rows | Risk-off rows | Base rate | Conditional rate | Lift |", "|---|---:|---:|---:|---:|---:|"])
        split = stability.get("split_half", {})
        era = stability.get("era", {})
        entries = []
        if isinstance(split, Mapping):
            entries.extend([("First half", split.get("first", {})), ("Second half", split.get("second", {}))])
        if isinstance(era, Mapping):
            entries.extend([("Pre-2016", era.get("pre_2016", {})), ("2016+", era.get("post_2016", {}))])
        for label, record in entries:
            if not isinstance(record, Mapping):
                continue
            lines.append(
                f"| {label} | {record.get('eligible_rows', 'n/a')} | {record.get('rows', 'n/a')} | "
                f"{_report_pct(record.get('base_rate'))} | {_report_pct(record.get('conditional_rate'))} | "
                f"{_report_number(record.get('lift'), 2)}× |"
            )
        lines.extend(["", "### Leave-one-crisis-out", ""])
        lines.extend(["| Omitted episode | Applicable | Excluded rows | Remaining lift |", "|---|---:|---:|---:|"])
        loco = stability.get("loco", [])
        if isinstance(loco, list):
            for record in loco:
                if not isinstance(record, Mapping):
                    continue
                applicable = bool(record.get("applicable", int(record.get("excluded_rows", 0)) > 0))
                lift = _report_number(record.get("lift"), 2) + "×" if applicable else "not testable; pre-sample"
                lines.append(
                    f"| {record.get('crisis', 'n/a')} | {'yes' if applicable else 'no'} | "
                    f"{record.get('excluded_rows', 0)} | {lift} |"
                )
        lines.append("")

    csi = result.get("csi300_replication", {})
    if isinstance(csi, Mapping):
        lines.extend(["## CSI300 replication", ""])
        lines.append(
            f"**{csi.get('verdict', 'INSUFFICIENT_EVIDENCE')}** — {csi.get('basis', 'No exact cash-index series available.')}"
        )
        lines.extend(
            [
                "",
                f"- Exact cash-index history available: **{str(csi.get('cash_index_series_available', False)).lower()}**.",
                f"- 510300.SS ETF proxy available: **{str(csi.get('proxy_available', False)).lower()}**.",
                f"- Quantitative proxy replication performed: **{str(csi.get('quantitative_replication_performed', False)).lower()}**.",
                "- The ETF proxy is disclosed in provenance but withheld from confirmatory evidence; no FXI or offshore substitute is used.",
                "",
            ]
        )

    calibration = result.get("calibration", {})
    if isinstance(calibration, Mapping):
        lines.extend(["## Calibration of the displayed 5d / 10d / 21d surface", ""])
        lines.extend(["| Horizon | Brier | Skill vs baked base | Skill vs delayed expanding base | Intercept | Slope | Supported inversion |", "|---|---:|---:|---:|---:|---:|---:|"])
        for key in ("h5", "h10", "h21"):
            cal = calibration.get(key, {})
            if not isinstance(cal, Mapping):
                continue
            delayed = cal.get("delayed_expanding_base", {})
            slope = cal.get("intercept_slope", {})
            inversions = cal.get("dependence_aware_inversions", [])
            supported = any(bool(row.get("supported_material_inversion")) for row in inversions if isinstance(row, Mapping)) if isinstance(inversions, list) else False
            lines.append(
                f"| {key} | {_report_number(cal.get('brier'), 4)} | {_report_pct(cal.get('brier_skill_vs_baked_base'), 2)} | "
                f"{_report_pct(delayed.get('production_skill_vs_delayed_base') if isinstance(delayed, Mapping) else None, 2)} | "
                f"{_report_number(slope.get('intercept') if isinstance(slope, Mapping) and slope.get('qualified') else None, 3)} | "
                f"{_report_number(slope.get('slope') if isinstance(slope, Mapping) and slope.get('qualified') else None, 3)} | "
                f"{'yes' if supported else 'no'} |"
            )
        lines.extend(["", "### Fixed state bins", ""])
        lines.extend(["| Horizon | State | Forecast | Observed | Block 95% CI | Episode 95% CI | Effective episodes | Hit / non-hit episodes |", "|---|---|---:|---:|---:|---:|---:|---:|"])
        for key in ("h5", "h10", "h21"):
            cal = calibration.get(key, {})
            rows = cal.get("states", []) if isinstance(cal, Mapping) else []
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                lines.append(
                    f"| {key} | {row.get('state')} | {_report_pct(row.get('forecast'))} | {_report_pct(row.get('observed'))} | "
                    f"{_report_ci(row.get('block_ci'), pct=True)} | {_report_ci(row.get('episode_ci'), pct=True)} | "
                    f"{row.get('effective_n_ceiling', 'n/a')} | {row.get('hit_episodes', 'n/a')} / {row.get('nonhit_episodes', 'n/a')} |"
                )
        lines.append("")

    band_assessment = result.get("band_cutoff_assessment", {})
    if isinstance(band_assessment, Mapping):
        lines.extend(
            [
                "## Band cutoffs and monotonic ordering",
                "",
                f"- Exact production cuts tested unchanged: **{band_assessment.get('exact_cutoffs', {})}**.",
                f"- Observed monotonic ordering: **{band_assessment.get('monotonic_ordering_verdict', 'INSUFFICIENT_EVIDENCE')}**.",
                f"- Exact cutoff optimality: **{band_assessment.get('cutoff_optimality_verdict', 'INSUFFICIENT_EVIDENCE')}** — {band_assessment.get('cutoff_optimality_basis', '')}",
                f"- Supported material probability-bin inversion: **{str(band_assessment.get('supported_material_inversion', False)).lower()}**.",
                f"- Post-hoc threshold search performed: **{str(band_assessment.get('post_hoc_threshold_search_performed', False)).lower()}**.",
                "",
            ]
        )

    lines.extend(["## Economic baseline comparison", ""])
    if isinstance(targets, Mapping):
        for key in ("5pct_21d", "10pct_42d"):
            target = targets.get(key, {})
            if not isinstance(target, Mapping):
                continue
            lines.extend([f"### {key}", "", "| Construction | AP | AUC | Risk-off lift | Elevated-plus lift |", "|---|---:|---:|---:|---:|"])
            disc = target.get("continuous_discrimination", {})
            risk = target.get("risk_off", {})
            elevated = target.get("elevated_plus", {})
            lines.append(
                f"| Current emitted radar | {_report_number(disc.get('average_precision') if isinstance(disc, Mapping) else None, 3)} | "
                f"{_report_number(disc.get('roc_auc') if isinstance(disc, Mapping) else None, 3)} | "
                f"{_report_number(risk.get('lift') if isinstance(risk, Mapping) else None, 2)}× | "
                f"{_report_number(elevated.get('lift') if isinstance(elevated, Mapping) else None, 2)}× |"
            )
            baselines = target.get("baseline_comparison", {})
            if isinstance(baselines, Mapping):
                for name in ("breadth_only", "rates_only", "trend_context", "ungated_composite"):
                    record = baselines.get(name, {})
                    if not isinstance(record, Mapping):
                        continue
                    lines.append(
                        f"| {name} | {_report_number(record.get('average_precision'), 3)} | {_report_number(record.get('roc_auc'), 3)} | "
                        f"{_report_number(record.get('risk_off_lift'), 2)}× | {_report_number(record.get('elevated_plus_lift'), 2)}× |"
                    )
            lines.append("")

    context = result.get("context_gate", {})
    if isinstance(context, Mapping):
        elevated_effective = context.get("gated_elevated_plus_effective_n", {})
        lines.extend(
            [
                "## Context-gate value-add",
                "",
                f"- 5%/21d gated elevated-plus lift: **{_report_number(context.get('gated_elevated_plus_lift'), 2)}×**; ungated: **{_report_number(context.get('ungated_elevated_plus_lift'), 2)}×**.",
                f"- Elevated-plus lift difference: **{_report_number(context.get('elevated_plus_lift_difference_gated_minus_ungated'), 2)}×**, block CI {_report_ci(context.get('elevated_plus_lift_difference_block_ci'))}.",
                f"- Elevated-plus effective episode ceiling: **{elevated_effective.get('effective_n_ceiling', 'n/a') if isinstance(elevated_effective, Mapping) else 'n/a'}**.",
                f"- Brier difference, gated minus ungated: **{_report_number(context.get('brier_difference_gated_minus_ungated'), 4)}**, block CI {_report_ci(context.get('brier_difference_block_ci'))}. Negative favors the gate.",
                f"- Continuous ranking score unchanged by the state cap: **{str(context.get('ranking_score_unchanged', True)).lower()}**; AP difference {_report_number(context.get('continuous_ap_difference'), 4)}.",
                f"- Secondary risk-off lift difference: **{_report_number(context.get('risk_off_lift_difference_gated_minus_ungated'), 2)}×**, block CI {_report_ci(context.get('risk_off_lift_difference_block_ci'))}.",
                f"- 10%/42d gated/ungated risk-off lifts: **{_report_number(context.get('historical_10pct_42d_gated_lift'), 2)}× / {_report_number(context.get('historical_10pct_42d_ungated_lift'), 2)}×**.",
                "- Preregistered promotion uses supported Brier improvement **or** supported elevated-plus lift improvement, plus the effective-episode floor.",
                "",
            ]
        )

    forward = result.get("forward_ledger", {})
    if isinstance(forward, Mapping):
        lines.extend(
            [
                "## Genuinely issued forward ledger — kept separate",
                "",
                "| Rows | Matured | Pending | Matured loud | Loud hits | Matured risk-off | Risk-off hits | can_force |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|",
                (
                    f"| {forward.get('total_rows', 'n/a')} | {forward.get('matured_rows', 'n/a')} | "
                    f"{forward.get('pending_rows', 'n/a')} | {forward.get('matured_loud_alerts', 'n/a')} | "
                    f"{forward.get('matured_loud_hits', 'n/a')} | {forward.get('matured_risk_off_rows', 'n/a')} | "
                    f"{forward.get('matured_risk_off_hits', 'n/a')} | {str(forward.get('can_force', False)).lower()} |"
                ),
                "",
                f"Pending issuance spans **{forward.get('pending_asof_range')}**; the September episode remains unresolved. `{forward.get('authority_interpretation', '')}`",
                f"Research count floor (25 matured) met: **{str(forward.get('research_count_floor_met', False)).lower()}**; research recalibration floor including cohort/episode qualification met: **{str(forward.get('research_recalibration_floor_met', False)).lower()}**.",
                f"Exact model cohort identifiers present: **{str(forward.get('cohort_identifiers_present', False)).lower()}**; independent episode identifiers present: **{str(forward.get('episode_identifiers_present', False)).lower()}**.",
                "",
            ]
        )

    provenance = result.get("data_provenance", {})
    if isinstance(provenance, Mapping):
        construction = provenance.get("construction", {})
        lines.extend(["## Provenance and reproducibility", ""])
        if isinstance(construction, Mapping):
            lines.append(f"- Exact construction hash: `{construction.get('construction_hash', 'n/a')}`")
        lines.extend(
            [
                f"- Historical PIT qualification: **{provenance.get('historical_snapshot_pit_status', 'n/a')}**.",
                "- CSI replication: **INSUFFICIENT_EVIDENCE** for the exact cash index; 510300.SS is disclosed as an ETF proxy and withheld from confirmatory results.",
                "- Historical reconstruction and issued forward evidence are distinct evidence classes and are never pooled.",
                "",
                "### Data files",
                "",
                "| Source | Role | Rows | Date range | SHA-256 |",
                "|---|---|---:|---|---|",
            ]
        )
        source_files = provenance.get("source_files", {})
        if isinstance(source_files, Mapping):
            for name, record in source_files.items():
                if not isinstance(record, Mapping):
                    continue
                date_range = (
                    f"{record.get('first_date')} → {record.get('last_date')}"
                    if record.get("first_date") else "n/a"
                )
                lines.append(
                    f"| {name} | {record.get('role', 'n/a')} | {record.get('rows', 'n/a')} | {date_range} | "
                    f"`{str(record.get('sha256', ''))[:16]}…` |"
                )
        lines.append("")

    discoveries = result.get("discoveries", [])
    lines.extend(["## Discoveries", ""])
    if isinstance(discoveries, list):
        lines.extend(f"- {item}" for item in discoveries)
    lines.append("")

    followup = result.get("proposed_followup", [])
    lines.extend(["## Proposed follow-up", ""])
    if isinstance(followup, list):
        lines.extend(f"- {item}" for item in followup)
    lines.append("")

    no_redo = result.get("what_must_not_be_redone", [])
    lines.extend(["## What must not be redone", ""])
    if isinstance(no_redo, list):
        lines.extend(f"- {item}" for item in no_redo)
    lines.extend(
        [
            "",
            "## One-command reproduction",
            "",
            "```bash",
            "python3 -m scripts.research.cn_risk_radar_revalidation \\",
            "  --repo-root . \\",
            "  --output-dir research/cn_risk_revalidation \\",
            "  --bootstrap-reps 5000 \\",
            "  --permutation-reps 5000 \\",
            "  --seed 20260923",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


render_report = _render_report_v2


if __name__ == "__main__":
    raise SystemExit(main())
