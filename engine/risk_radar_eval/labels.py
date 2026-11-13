"""Shared outcome labels for scoring Risk Radar and its challengers on identical terms.

Research-only. Nothing in the live engine imports this package.

Two label families, both on SPY dividend-adjusted closes (`store.read("yahoo","SPY")["close"]`,
i.e. total return):

1. **Day-level forward loss** (the definition behind the published state-ladder figures, e.g.
   "risk-off 2020+: 43.8% at H21"): for session d, the event is
   ``min(close[d+1..d+H]) / close[d] - 1 <= -depth``. Native observations only: no resampling,
   no forward fill; a window with any missing/invalid close is dropped.
   Source of the definition: research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_PREREG_2026-09-21.md
   and scripts/research/risk_radar_state_ladder_calibration.py:41-73.

2. **Drawdown episodes** (the target of the risk-off pivot scorecard): a peak-to-trough decline of
   at least ``depth`` from the running total-return peak.
   - ``peak``: the session of the running maximum the decline starts from.
   - ``onset``: the session after the peak (first session of the decline).
   - ``breach``: first session whose close is <= peak * (1 - depth).
   - ``trough``: lowest close between onset and recovery.
   - ``recovery``: first session after the trough whose close is >= the peak close (None while
     unrecovered).
   - Merge: if a new episode's onset falls within ``merge_gap`` sessions (default 21) after the
     previous episode's recovery, the two are one episode (the earlier peak/onset is kept, the
     trough is the lower one).

Leak control. Every public function takes ``outcomes_through``: labels are computed from closes
dated on or before it and nothing else, so a day-level label needing a close after the cutoff is
absent, and an episode whose breach happens after the cutoff does not exist. ``check_scoring_window``
enforces a sealed date (default 2024-01-02, the research desk's sealed hold-out) unless the caller
explicitly declares the scoring as the incumbent's own already-seen history.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

SEALED_FROM = pd.Timestamp("2024-01-02")
DEFAULT_DEPTHS = (0.05, 0.07, 0.10)
DEFAULT_HORIZONS = (3, 5, 10, 21)
DEFAULT_MERGE_GAP = 21


class LabelLeakError(ValueError):
    """Raised when a request would use outcomes beyond the declared cutoff or sealed date."""


def spy_total_return(store_reader=None) -> pd.Series:
    """SPY dividend-adjusted closes (native observations, sorted, finite > 0 only)."""
    if store_reader is None:
        from lib import store
        store_reader = store.read
    df = store_reader("yahoo", "SPY")
    if df is None or "close" not in df:
        raise LabelLeakError("SPY store unavailable")
    s = pd.to_numeric(df["close"], errors="coerce")
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    if not s.index.is_unique:
        raise ValueError("SPY index must be unique")
    return s[np.isfinite(s) & (s > 0)]


def _cut(px: pd.Series, outcomes_through) -> pd.Series:
    if outcomes_through is None:
        raise LabelLeakError("outcomes_through is required (pass an explicit date)")
    return px[px.index <= pd.Timestamp(outcomes_through)]


def check_scoring_window(dates, *, sealed_from=SEALED_FROM, seen_history_ok: bool = False) -> None:
    """Refuse to score dates on/after the sealed date unless explicitly declared seen history.

    The research desk's challengers keep ``seen_history_ok=False``. The incumbent's own
    walk-forward scoring of 2024+ (allowed by the 2026-11-12 direction ruling, labelled as seen
    history) passes ``seen_history_ok=True``.
    """
    if sealed_from is None or seen_history_ok:
        return
    idx = pd.DatetimeIndex(dates)
    if len(idx) and idx.max() >= pd.Timestamp(sealed_from):
        raise LabelLeakError(
            f"scoring window reaches {idx.max().date()} >= sealed {pd.Timestamp(sealed_from).date()}")


def forward_loss_labels(px: pd.Series, horizon: int, depth: float = 0.05, *,
                        outcomes_through) -> pd.DataFrame:
    """Day-level forward-loss labels. Index = session d; columns end, loss, event."""
    if type(horizon) is not int or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    if not 0 < depth < 1:
        raise ValueError("depth must be in (0, 1)")
    p = _cut(px, outcomes_through)
    v = p.to_numpy(dtype=float)
    n = len(v)
    if n <= horizon:
        return pd.DataFrame(columns=["end", "loss", "event"])
    # rolling min of the NEXT `horizon` closes
    fut = pd.Series(v[::-1]).rolling(horizon, min_periods=horizon).min().to_numpy()[::-1]
    nxt_min = np.full(n, np.nan)
    nxt_min[:-1] = fut[1:]
    loss = nxt_min / v - 1.0
    ok = np.isfinite(loss)
    ok[n - horizon:] = False
    idx = p.index[ok]
    out = pd.DataFrame({
        "end": p.index[np.nonzero(ok)[0] + horizon],
        "loss": loss[ok],
    }, index=idx)
    out["event"] = out["loss"] <= -depth
    out.index.name = "date"
    return out


@dataclass(frozen=True)
class Episode:
    depth: float
    peak: pd.Timestamp
    onset: pd.Timestamp
    breach: pd.Timestamp
    trough: pd.Timestamp
    recovery: pd.Timestamp | None
    max_loss: float

    def as_dict(self) -> dict:
        d = asdict(self)
        return {k: (v.date().isoformat() if isinstance(v, pd.Timestamp) else v) for k, v in d.items()}


def drawdown_episodes(px: pd.Series, depth: float, *, outcomes_through,
                      merge_gap: int = DEFAULT_MERGE_GAP) -> list[Episode]:
    """Peak-to-trough drawdown episodes of at least `depth`, using closes <= outcomes_through."""
    if not 0 < depth < 1:
        raise ValueError("depth must be in (0, 1)")
    p = _cut(px, outcomes_through)
    v = p.to_numpy(dtype=float)
    idx = p.index
    n = len(v)
    raw = []  # (peak_i, breach_i, trough_i, recovery_i or None)
    i = 0
    peak_i = 0
    while i < n:
        if v[i] >= v[peak_i]:
            peak_i = i
            i += 1
            continue
        if v[i] <= v[peak_i] * (1 - depth):
            breach_i = i
            trough_i = i
            j = i
            rec = None
            while j < n:
                if v[j] < v[trough_i]:
                    trough_i = j
                if v[j] >= v[peak_i]:
                    rec = j
                    break
                j += 1
            raw.append([peak_i, breach_i, trough_i, rec])
            if rec is None:
                break
            peak_i = rec
            i = rec + 1
            continue
        i += 1
    merged: list[list] = []
    for ep in raw:
        if merged and merged[-1][3] is not None and (ep[0] + 1) - merged[-1][3] <= merge_gap:
            prev = merged[-1]
            if v[ep[2]] < v[prev[2]]:
                prev[2] = ep[2]
            prev[3] = ep[3]
        else:
            merged.append(list(ep))
    out = []
    for pk, br, tr, rec in merged:
        if pk + 1 >= n:
            continue
        out.append(Episode(depth=depth, peak=idx[pk], onset=idx[pk + 1], breach=idx[br],
                           trough=idx[tr], recovery=None if rec is None else idx[rec],
                           max_loss=round(float(v[tr] / v[pk] - 1.0), 5)))
    return out


def in_episode_mask(index: pd.DatetimeIndex, episodes: list[Episode]) -> pd.Series:
    """True on sessions from an episode's onset through its recovery (or to the end if open)."""
    m = pd.Series(False, index=index)
    for e in episodes:
        hi = e.recovery if e.recovery is not None else index.max()
        m.loc[(index >= e.onset) & (index <= hi)] = True
    return m
