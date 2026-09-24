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
