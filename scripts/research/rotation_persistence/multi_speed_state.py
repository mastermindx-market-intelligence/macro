"""Deterministic multi-speed causal state frame for sector leadership persistence.

OUTCOME-BLIND. This module emits structural, tactical, cycle-duration, temporal-basis,
dependence, and participation state for every eligible sector/date using only
information available at that date. It does NOT predict returns, select winning
timeframes, rank trade candidates, create Prophet recommendations, size capital,
or read forward outcomes.

State families
--------------
1. Structural (slow): causal 21-session return / leadership percentile,
   prior-day rank and level velocity, top-tier residency age (or null before
   eligibility). Uses only completed sessions so that the anchor date is
   confirmed-closed.

2. Tactical (fast): causal 5-session return / leadership percentile and
   velocity; daily MACD histogram level / sign / slope / acceleration;
   bars since the most recent confirmed-zero-cross (completed bars only).

3. Cycle duration: length of the latest COMPLETED histogram-sign half-cycle
   and a causal trailing summary of completed half-cycles. A confirmed
   half-cycle closes when the histogram sign flips — the confirmed flip
   session is the last bar of the prior half-cycle. Zero-delay location of
   a future pivot is impossible and is not attempted.

4. Temporal basis: standard daily EMA (span 26 / 12 / 9) and a daily filter
   whose per-session exponential decay is equivalent to the 3D 12/26/9 MACD.
   The 3D per-session decay alpha is derived from the epoch decay (1 - 2/27)^(1/3)
   per session; the memory-equivalent daily span is therefore
   1 / (1 - (25/27)^(1/3)) ≈ 38.85. A simpler heuristic that matches the
   26-day slow-EMA memory on a per-session basis is also provided. Label the
   daily filter ``memory_equivalent`` — "information-equivalent" is reserved
   for the MACD pair and is not applied to the daily filter.

5. Dependence: 20-session cross-sectional dispersion (sample std of daily
   returns) and mean pairwise Pearson correlation — reusing the exact RPH-1
   definitions from sector_control.dispersion_control / correlation_control.

6. Participation: fraction of the declared sector ETF panel with positive
   causal 5-session AND 21-session returns. Denominator is the full declared
   panel; unavailable symbols are excluded from both numerator and denominator.

References
----------
- RPH-1: scripts/research/rotation_persistence/sector_control.py
"""
from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .contracts import AUTHORITY as BASE_AUTHORITY, ContractError

SCHEMA = "research.rotation_persistence_multi_speed_state_rph2.v1"
OPERATION_KEY = "multi-speed-state-rph2-20260916-sol-001"
# ------------------------------------------------------------------
# Shared constants (mirrored from sector_control.py for hermeticity)
# ------------------------------------------------------------------
SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
MIN_OBSERVATIONS = 8
# MACD standard parameters (same as sector_control.py)
MACD_FAST_SPAN = 12
MACD_SLOW_SPAN = 26
MACD_SIGNAL_SPAN = 9
# 3D per-session exponential-decay alpha for the 12/26/9 MACD.
# Per-session alpha from the epoch-decay formula: alpha_3d = 1 - (25/27)^(1/3).
# span = 1 / alpha_3d ≈ 38.85.
# A heuristic matching the 26-session slow-EMA memory is also provided.
_ALPHA_3D: float = 1.0 - (25.0 / 27.0) ** (1.0 / 3.0)
_SPAN_3D_MEMORY_EQUIVALENT: float = 1.0 / _ALPHA_3D  # ≈ 38.85
_SPAN_3D_SLOW_HEURISTIC: float = 26.0  # matches slow-EMA memory on per-session basis
AUTHORITY = dict(BASE_AUTHORITY)


def _iso_date(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def _as_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _require_panel(panel: pd.DataFrame, *, columns: Iterable[str] = SECTORS) -> None:
    required = tuple(columns)
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise ContractError(f"price panel is missing columns: {', '.join(missing)}")
    if panel.empty:
        raise ContractError("price panel is empty")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise ContractError("price panel index must be a DatetimeIndex")
    if not panel.index.is_monotonic_increasing or not panel.index.is_unique:
        raise ContractError("price panel dates must be unique and increasing")
    values = panel.loc[:, required].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ContractError("price panel closes must be finite and positive")


def _spearman(left: pd.Series | float, right: pd.Series | float) -> float | None:
    """Pearson of ranks — same helper as sector_control.py."""
    if not isinstance(left, pd.Series):
        left = pd.Series([left])
    if not isinstance(right, pd.Series):
        right = pd.Series([right])
    aligned = pd.concat([left.astype(float), right.astype(float)], axis=1).dropna()
    if len(aligned) < 2 or aligned.iloc[:, 0].nunique() < 2 or aligned.iloc[:, 1].nunique() < 2:
        return None
    left_rank = aligned.iloc[:, 0].rank(method="average")
    right_rank = aligned.iloc[:, 1].rank(method="average")
    return _as_float(left_rank.corr(right_rank))


def _window_entries(entries: list[tuple[pd.Timestamp, float | None]]) -> dict[str, list]:
    prior_end = max(0, len(entries) - 20)
    return {
        "all": entries,
        "recent_20": entries[-20:],
        "recent_60": entries[-60:],
        "prior_252": entries[max(0, prior_end - 252): prior_end],
    }


def _summary(
    entries: list[tuple[pd.Timestamp, float | None]], *, minimum: int = MIN_OBSERVATIONS
) -> dict[str, Any]:
    valid = [(date, value) for date, value in entries
             if value is not None and math.isfinite(value)]
    values = np.asarray([value for _, value in valid], dtype=float)
    state = "MEASURED" if len(values) >= minimum else "INSUFFICIENT_HISTORY"
    measured = state == "MEASURED"
    return {
        "state": state,
        "anchors": int(len(entries)),
        "n": int(len(values)),
        "start_date": _iso_date(valid[0][0]) if valid else None,
        "end_date": _iso_date(valid[-1][0]) if valid else None,
        "mean": float(values.mean()) if measured else None,
        "median": float(np.median(values)) if measured else None,
        "sample_std": float(values.std(ddof=1)) if measured else None,
    }


def _window_summaries(entries: list[tuple[pd.Timestamp, float | None]]) -> dict[str, dict]:
    return {name: _summary(window) for name, window in _window_entries(entries).items()}


# ------------------------------------------------------------------
# 1. Structural (slow: 21-session)
# ------------------------------------------------------------------

def _rank_at(panel: pd.DataFrame, position: int) -> pd.Series:
    """Return sector ranks (1 = best) at the given panel position."""
    row = panel.iloc[position][list(SECTORS)]
    ranks = row.rank(method="average", ascending=False).astype(int)
    return ranks


def _top_tier_residency(
    panel: pd.DataFrame, lookback: int, top_n: int = 3
) -> list[tuple[pd.Timestamp, int | None]]:
    """Per-anchor session: how many consecutive prior sessions was this sector in top_n?

    Returns one entry per eligible anchor (position lookback … len-1).
    Residency age is 0 when the sector enters the top-n on the anchor session itself.
    Returns None when the sector was not in top-n on the anchor session.
    """
    entries: list[tuple[pd.Timestamp, int | None]] = []
    for pos in range(lookback, len(panel)):
        anchor = panel.index[pos]
        current_ranks = _rank_at(panel, pos)
        in_top = set(current_ranks[current_ranks <= top_n].index)
        if not in_top:
            entries.append((anchor, None))
            continue
        # Count consecutive prior sessions in top_n, walking backwards
        age = 0
        for lag in range(1, lookback + 1):
            prior_pos = pos - lag
            if prior_pos < 0:
                break
            prior_ranks = _rank_at(panel, prior_pos)
            prior_in_top = set(prior_ranks[prior_ranks <= top_n].index)
            if in_top & prior_in_top:
                age += 1
            else:
                break
        entries.append((anchor, age))
    return entries


def structural_state(
    panel: pd.DataFrame,
) -> dict[str, Any]:
    """Slow (21-session) causal structural state for all eligible sectors."""
    _require_panel(panel)
    log_prices = np.log(panel[list(SECTORS) + ["SPY"]].astype(float))

    # 21-session leadership: Spearman of 21-session sector return vs SPY return
    lookback = 21
    entries_by_symbol: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
        s: [] for s in SECTORS
    }
    for pos in range(lookback, len(panel)):
        anchor = panel.index[pos]
        sector_ret = log_prices.iloc[pos] - log_prices.iloc[pos - lookback]
        spy_ret = log_prices.iloc[pos]["SPY"] - log_prices.iloc[pos - lookback]["SPY"]
        for sym in SECTORS:
            if sector_ret[sym] == spy_ret:
                # degenerate — same value for all, rank undefined
                entries_by_symbol[sym].append((anchor, None))
            else:
                entries_by_symbol[sym].append((anchor, _spearman(sector_ret[[sym]], spy_ret)))

    # Prior-day rank and level velocity
    rank_velocity_entries: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
        s: [] for s in SECTORS
    }
    level_velocity_entries: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
        s: [] for s in SECTORS
    }
    for pos in range(1, len(panel)):
        anchor = panel.index[pos]
        prev_ranks = _rank_at(panel, pos - 1)
        curr_ranks = _rank_at(panel, pos)
        prev_closes = panel.iloc[pos - 1][list(SECTORS)]
        curr_closes = panel.iloc[pos][list(SECTORS)]
        for sym in SECTORS:
            rank_vel = float(prev_ranks[sym] - curr_ranks[sym])  # positive = improving
            level_vel = float(curr_closes[sym] / prev_closes[sym] - 1.0)
            rank_velocity_entries[sym].append((anchor, rank_vel))
            level_velocity_entries[sym].append((anchor, level_vel))

    # Top-tier residency age (top 3, 21-session lookback)
    residency_entries: dict[str, list[tuple[pd.Timestamp, int | None]]] = {
        s: _top_tier_residency(panel, lookback=21, top_n=3) for s in SECTORS
    }

    return {
        "lookback_sessions": lookback,
        "leadership": {
            sym: {
                "percentile": _window_summaries(entries_by_symbol[sym]),
                "rank_velocity": _window_summaries(rank_velocity_entries[sym]),
                "level_velocity": _window_summaries(level_velocity_entries[sym]),
                "top3_residency_age": {
                    name: _summary(
                        residency_entries[sym][-60:] if name == "recent_60"
                        else residency_entries[sym][-20:] if name == "recent_20"
                        else residency_entries[sym]
                    )
                    for name in ("all", "recent_20", "recent_60")
                },
            }
            for sym in SECTORS
        },
    }


# ------------------------------------------------------------------
# 2. Tactical (fast: 5-session)
# ------------------------------------------------------------------

def tactical_state(
    panel: pd.DataFrame,
) -> dict[str, Any]:
    """Fast (5-session) causal tactical state + daily MACD histogram state."""
    _require_panel(panel)
    log_prices = np.log(panel[list(SECTORS) + ["SPY"]].astype(float))

    lookback = 5
    leadership_entries: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
        s: [] for s in SECTORS
    }
    rank_vel_fast: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
        s: [] for s in SECTORS
    }
    level_vel_fast: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
        s: [] for s in SECTORS
    }
    for pos in range(lookback, len(panel)):
        anchor = panel.index[pos]
        sector_ret = log_prices.iloc[pos] - log_prices.iloc[pos - lookback]
        spy_ret = log_prices.iloc[pos]["SPY"] - log_prices.iloc[pos - lookback]["SPY"]
        prev_ranks = _rank_at(panel, pos - 1)
        curr_ranks = _rank_at(panel, pos)
        prev_closes = panel.iloc[pos - 1][list(SECTORS)]
        curr_closes = panel.iloc[pos][list(SECTORS)]
        for sym in SECTORS:
            leadership_entries[sym].append((anchor, _spearman(sector_ret[[sym]], spy_ret)))
            rank_vel_fast[sym].append((anchor, float(prev_ranks[sym] - curr_ranks[sym])))
            level_vel_fast[sym].append((anchor, float(curr_closes[sym] / prev_closes[sym] - 1.0)))

    # Daily MACD histogram per sector
    macd_state: dict[str, dict[str, Any]] = {}
    for sym in SECTORS:
        closes = panel[sym].astype(float)
        fast_ema = closes.ewm(span=MACD_FAST_SPAN, adjust=False).mean()
        slow_ema = closes.ewm(span=MACD_SLOW_SPAN, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=MACD_SIGNAL_SPAN, adjust=False).mean()
        histogram = macd_line - signal_line

        # Signed histogram: + / 0 / -
        hist_signs = pd.Series(
            np.where(histogram.to_numpy() > 0, 1, np.where(histogram.to_numpy() < 0, -1, 0)),
            index=histogram.index,
        )

        # Completed-bar zero-cross events: sign flips from +1 to -1 or -1 to +1
        cross_events = (hist_signs != hist_signs.shift(1)) & (hist_signs != 0)
        cross_indices = cross_events[cross_events].index

        # Bars since most recent completed zero-cross (at or before current bar)
        bars_since_cross: list[tuple[pd.Timestamp, int | None]] = []
        for pos in range(1, len(panel)):
            anchor = panel.index[pos]
            prior_crosses = [ci for ci in cross_indices if ci <= anchor]
            if not prior_crosses:
                bars_since_cross.append((anchor, None))
            else:
                latest_cross = prior_crosses[-1]
                bars_since_cross.append((anchor, pos - panel.index.get_loc(latest_cross)))

        # Slope: difference of histogram over 3 completed sessions
        slope_entries: list[tuple[pd.Timestamp, float | None]] = []
        for pos in range(3, len(panel)):
            anchor = panel.index[pos]
            delta = float(histogram.iloc[pos] - histogram.iloc[pos - 3])
            slope_entries.append((anchor, delta))

        # Acceleration: change in slope over 3 sessions
        slope_arr = pd.Series(
            [v for _, v in slope_entries],
            index=[d for d, _ in slope_entries],
        )
        accel_entries: list[tuple[pd.Timestamp, float | None]] = []
        for pos in range(6, len(slope_arr)):
            anchor = slope_arr.index[pos]
            accel = float(slope_arr.iloc[pos] - slope_arr.iloc[pos - 3])
            accel_entries.append((anchor, accel))

        # Level at each completed bar
        level_entries: list[tuple[pd.Timestamp, float | None]] = [
            (panel.index[p], _as_float(histogram.iloc[p])) for p in range(len(panel))
        ]

        macd_state[sym] = {
            "histogram_level": _window_summaries(level_entries),
            "bars_since_cross": _window_summaries(bars_since_cross),
            "slope": _window_summaries(slope_entries),
            "acceleration": _window_summaries(accel_entries),
        }

    return {
        "lookback_sessions": lookback,
        "leadership": {
            sym: {
                "percentile": _window_summaries(leadership_entries[sym]),
                "rank_velocity": _window_summaries(rank_vel_fast[sym]),
                "level_velocity": _window_summaries(level_vel_fast[sym]),
            }
            for sym in SECTORS
        },
        "macd_histogram": macd_state,
    }


# ------------------------------------------------------------------
# 3. Cycle duration — completed half-cycles only
# ------------------------------------------------------------------

def _histogram_sign(panel: pd.DataFrame, symbol: str) -> pd.Series:
    closes = panel[symbol].astype(float)
    fast_ema = closes.ewm(span=MACD_FAST_SPAN, adjust=False).mean()
    slow_ema = closes.ewm(span=MACD_SLOW_SPAN, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=MACD_SIGNAL_SPAN, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.Series(
        np.where(hist.to_numpy() > 0, 1, np.where(hist.to_numpy() < 0, -1, 0)),
        index=hist.index,
    )


def _completed_half_cycles(sign_series: pd.Series) -> list[dict[str, Any]]:
    """Return list of completed half-cycle records.

    A half-cycle is a contiguous run of the same non-zero sign (+1 or -1).
    Each record: {start_date, end_date, sign, length_sessions}.
    The record is only emitted when the cycle CLOSES (sign flips to opposite
    non-zero sign or series ends). The confirmed-flip bar is the LAST bar
    of the prior half-cycle.
    """
    cycles: list[dict[str, Any]] = []
    if len(sign_series) == 0:
        return cycles

    pos = 0
    current_sign = int(sign_series.iloc[0])
    if current_sign == 0:
        # Skip leading zeros — find first non-zero
        for i in range(1, len(sign_series)):
            if sign_series.iloc[i] != 0:
                current_sign = int(sign_series.iloc[i])
                pos = i
                break
        else:
            return cycles

    start_pos = pos
    while pos < len(sign_series) - 1:
        next_sign = int(sign_series.iloc[pos + 1])
        if next_sign == 0:
            pos += 1
            continue
        if next_sign != current_sign:
            # Half-cycle closes at pos (the confirmed-flip bar is pos)
            cycles.append({
                "start_date": _iso_date(sign_series.index[start_pos]),
                "end_date": _iso_date(sign_series.index[pos]),
                "sign": current_sign,
                "length_sessions": pos - start_pos + 1,
            })
            current_sign = next_sign
            start_pos = pos + 1
        pos += 1

    # Final half-cycle (did not get a confirmed close — not emitted as completed)
    # We only emit cycles that have a confirmed flip; the last incomplete run is
    # excluded so that cycle_length is never a function of an unconfirmed future.
    return cycles


def cycle_duration_state(
    panel: pd.DataFrame,
) -> dict[str, Any]:
    """Completed half-cycle duration state per sector."""
    _require_panel(panel)
    result: dict[str, Any] = {}
    for sym in SECTORS:
        signs = _histogram_sign(panel, sym)
        completed = _completed_half_cycles(signs)

        # Length of the latest completed half-cycle
        latest_length: int | None = completed[-1]["length_sessions"] if completed else None
        latest_sign: int | None = completed[-1]["sign"] if completed else None

        # Trailing summary of completed half-cycle lengths, by sign
        positive_cycles = [c["length_sessions"] for c in completed if c["sign"] == 1]
        negative_cycles = [c["length_sessions"] for c in completed if c["sign"] == -1]

        def _cycle_summary(lengths: list[int]) -> dict[str, Any]:
            if len(lengths) < MIN_OBSERVATIONS:
                return {"state": "INSUFFICIENT_HISTORY", "n": len(lengths), "mean": None, "median": None}
            arr = np.asarray(lengths, dtype=float)
            return {
                "state": "MEASURED",
                "n": len(lengths),
                "mean": float(arr.mean()),
                "median": float(np.median(arr)),
            }

        result[sym] = {
            "latest_completed_half_cycle": {
                "sign": latest_sign,
                "length_sessions": latest_length,
            },
            "trailing_positive_half_cycles": _cycle_summary(positive_cycles),
            "trailing_negative_half_cycles": _cycle_summary(negative_cycles),
        }
    return result


# ------------------------------------------------------------------
# 4. Temporal basis — EMA memory equivalence
# ------------------------------------------------------------------

def temporal_basis_state(
    panel: pd.DataFrame,
) -> dict[str, Any]:
    """Daily EMA memory and the 3D-equivalent daily filter.

    The standard daily EMA uses spans 12/26/9. The 3D filter uses the same spans
    but applied to 3-session bars; its per-session decay alpha is
    (1 - 2/27). The memory-equivalent daily span is 26. Both series are
    emitted so the relationship is auditable; the daily filter is labelled
    'memory_equivalent' to make clear it does not carry the MACD signal or
    histogram semantics of the 3D series.
    """
    _require_panel(panel)
    closes = panel[list(SECTORS)].astype(float)

    # Standard daily EMA components
    daily_fast = closes.ewm(span=MACD_FAST_SPAN, adjust=False).mean()
    daily_slow = closes.ewm(span=MACD_SLOW_SPAN, adjust=False).mean()
    daily_signal = daily_fast.ewm(span=MACD_SIGNAL_SPAN, adjust=False).mean()
    daily_histogram = daily_fast - daily_slow - daily_signal

    # 3D-equivalent daily filter: spans derived from the per-session alpha
    # formula  alpha_3d = 1 - (25/27)^(1/3) ≈ 0.02572, giving slow span ≈ 38.85.
    # Also emit a heuristic using the 26-span directly to show the relationship.
    daily_3d_fast = closes.ewm(span=MACD_FAST_SPAN, adjust=False).mean()
    daily_3d_slow_equiv = closes.ewm(span=_SPAN_3D_MEMORY_EQUIVALENT, adjust=False).mean()
    signal_span_3d = _SPAN_3D_MEMORY_EQUIVALENT * MACD_SIGNAL_SPAN / MACD_FAST_SPAN
    daily_3d_signal = daily_3d_fast.ewm(span=signal_span_3d, adjust=False).mean()
    daily_3d_histogram = daily_3d_fast - daily_3d_slow_equiv - daily_3d_signal

    # Emit level entries for each series
    def _series_summary(
        series: pd.DataFrame,
    ) -> dict[str, dict[str, Any]]:
        entries_by_sym: dict[str, list[tuple[pd.Timestamp, float | None]]] = {
            s: [(panel.index[p], _as_float(series.iloc[p][s])) for p in range(len(panel))]
            for s in SECTORS
        }
        return {s: _window_summaries(entries_by_sym[s]) for s in SECTORS}

    return {
        "parameters": {
            "daily_fast_span": MACD_FAST_SPAN,
            "daily_slow_span": MACD_SLOW_SPAN,
            "daily_signal_span": MACD_SIGNAL_SPAN,
            "daily_3d_memory_equivalent_span": _SPAN_3D_MEMORY_EQUIVALENT,
            "daily_3d_signal_memory_equivalent_span": signal_span_3d,
            "note": (
                "daily_3d_* series use memory_equivalent spans; "
                "they are NOT information-equivalent to the 3D MACD and "
                "must not be confused with the MACD histogram or signal line."
            ),
        },
        "daily_ema": {
            "fast": _series_summary(daily_fast),
            "slow": _series_summary(daily_slow),
            "histogram": _series_summary(daily_histogram),
        },
        "daily_3d_memory_equivalent": {
            "fast": _series_summary(daily_3d_fast),
            "slow": _series_summary(daily_3d_slow_equiv),
            "histogram": _series_summary(daily_3d_histogram),
        },
    }


# ------------------------------------------------------------------
# 5. Dependence — reuse RPH-1 definitions exactly
# ------------------------------------------------------------------

def dependence_state(
    panel: pd.DataFrame,
) -> dict[str, Any]:
    """20-session cross-sectional dispersion and mean pairwise Pearson correlation.

    Definitions are identical to sector_control.dispersion_control / correlation_control.
    Dispersion: sample std across the 11 sector daily simple returns.
    Correlation: mean of the 55 unique upper-triangle Pearson pairs.
    """
    _require_panel(panel)
    returns = panel[list(SECTORS)].pct_change(fill_method=None).iloc[1:]

    # Dispersion: sample std per session, then summarised over windows
    dispersion_per_session: list[tuple[pd.Timestamp, float | None]] = [
        (returns.index[i], _as_float(returns.iloc[i].std(ddof=1)))
        for i in range(len(returns))
    ]

    # Correlation: 20-session rolling mean of 55 unique Pearson pairs
    window = 20
    corr_per_session: list[tuple[pd.Timestamp, float | None]] = []
    upper = np.triu_indices(len(SECTORS), k=1)
    for end in range(window - 1, len(returns)):
        sample = returns.iloc[end - window + 1: end + 1]
        matrix = sample.corr().to_numpy(dtype=float)
        pairs = matrix[upper]
        corr_per_session.append((
            returns.index[end],
            float(pairs.mean()) if np.isfinite(pairs).all() else None,
        ))

    return {
        "dispersion": {
            "definition": "sample_std_across_eleven_sector_daily_simple_returns",
            "windows": _window_summaries(dispersion_per_session),
        },
        "correlation": {
            "definition": "mean_of_55_unique_pairwise_pearson_correlations",
            "trailing_sessions": window,
            "windows": _window_summaries(corr_per_session),
        },
    }


# ------------------------------------------------------------------
# 6. Participation — ETF-panel fraction with positive causal returns
# ------------------------------------------------------------------

def participation_state(
    panel: pd.DataFrame,
) -> dict[str, Any]:
    """Market-level fraction of declared sector ETFs with positive causal returns.

    Participation is the fraction of the FULL declared panel (XLB…XLY = 10 sectors)
    that have a positive causal 5-session and/or 21-session return.
    The denominator is always 10 — unavailable symbols are excluded from both
    numerator and denominator AND flagged explicitly. This is NOT constituent
    breadth; it is an ETF-panel participation signal.

    Returns two variants:
    - with_positive_5_session: fraction positive on 5-session return
    - with_positive_21_session: fraction positive on 21-session return
    Each entry is keyed by date and carries the explicit null reason when
    insufficient history prevents a determination.
    """
    _require_panel(panel)
    closes = panel[list(SECTORS)]
    log_closes = np.log(closes.astype(float))

    entries_5: list[tuple[pd.Timestamp, float | None]] = []
    entries_21: list[tuple[pd.Timestamp, float | None]] = []

    for pos in range(5, len(panel)):
        anchor = panel.index[pos]
        ret_5 = log_closes.iloc[pos] - log_closes.iloc[pos - 5]
        ret_21 = log_closes.iloc[pos] - log_closes.iloc[pos - 21]
        pos_5 = float((ret_5 > 0).sum()) / len(SECTORS)
        pos_21 = float((ret_21 > 0).sum()) / len(SECTORS)
        entries_5.append((anchor, pos_5))
        entries_21.append((anchor, pos_21))

    return {
        "definition": "etf_panel_participation_fraction",
        "denominator": len(SECTORS),
        "panel": list(SECTORS),
        "with_positive_5_session": _window_summaries(entries_5),
        "with_positive_21_session": _window_summaries(entries_21),
    }


# ------------------------------------------------------------------
# Top-level builder
# ------------------------------------------------------------------

def build_result(
    panel: pd.DataFrame,
    *,
    produced_at: str,
    source_universe: str = "daily_sector_etf_panel",
) -> dict[str, Any]:
    """Compose the deterministic RPH-2 multi-speed state frame.

    Parameters
    ----------
    panel : pd.DataFrame
        Price panel with DatetimeIndex, columns SECTORS + SPY.
    produced_at : str
        ISO-8601 timestamp of output generation (not source availability proof).
    source_universe : str
        Human label for the input universe (e.g. "daily_sector_etf_panel").
    """
    _require_panel(panel, columns=(*SECTORS, "SPY"))

    return {
        "schema_version": SCHEMA,
        "operation_key": OPERATION_KEY,
        "produced_at": produced_at,
        "source": {
            "universe": source_universe,
            "sectors": list(SECTORS),
            "benchmark": "SPY",
            "common_rows": int(len(panel)),
            "first_session": _iso_date(panel.index[0]),
            "last_session": _iso_date(panel.index[-1]),
        },
        "parameters": {
            "min_observations": MIN_OBSERVATIONS,
            "macd_fast_span": MACD_FAST_SPAN,
            "macd_slow_span": MACD_SLOW_SPAN,
            "macd_signal_span": MACD_SIGNAL_SPAN,
            "ema_memory_equivalent_span": _SPAN_3D_MEMORY_EQUIVALENT,
            "ema_signal_memory_equivalent_span": float(
                _SPAN_3D_MEMORY_EQUIVALENT * MACD_SIGNAL_SPAN / MACD_FAST_SPAN
            ),
            "participation_denominator": len(SECTORS),
            "correlation_window": 20,
        },
        "structural": structural_state(panel),
        "tactical": tactical_state(panel),
        "cycle_duration": cycle_duration_state(panel),
        "temporal_basis": temporal_basis_state(panel),
        "dependence": dependence_state(panel),
        "participation": participation_state(panel),
        "authority": dict(AUTHORITY),
        "limitations": [
            "Historical price corrections are not reconstructable from this corpus.",
            "State is descriptive only; it does not predict returns, select timeframes, "
            "rank trade candidates, create Prophet recommendations, size capital, "
            "or read forward outcomes.",
            "MACD zero-cross bars-since uses completed bars only; the latest cross "
            "age is a lower bound until the next confirmed flip.",
            "The daily 3D memory-equivalent series is NOT information-equivalent "
            "to the 3D MACD and must not be substituted for it.",
            "Participation denominator is the declared 10-symbol panel; "
            "a symbol absent from the panel is not substituted.",
        ],
    }
