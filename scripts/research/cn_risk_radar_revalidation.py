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
    floors_met = len(matured) >= 30 and len(loud) >= 8
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
        "authority_floors_met": floors_met,
        "can_force": False,
        "authority_interpretation": (
            "not eligible: fewer than 30 matured rows or 8 matured loud alerts"
            if not floors_met
            else "floor eligible but no authority inferred without the live constitution gate"
        ),
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
        record.update(
            {
                "crisis": name,
                "crisis_start": start,
                "crisis_end": end,
                "excluded_rows": int((~keep).sum()),
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
