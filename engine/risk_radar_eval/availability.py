"""Point-in-time replay of the FRED-sourced Radar legs (prereg addendum 3, 2026-11-12).

Research-only. For each session d this rebuilds a leg exactly as the production engine would at
d's nightly run (engine/risk_radar.leading_signals: obs-dated transform, reindex onto SPY
sessions, ffill, 504-session causal percentile) from only the observations FRED had released by
d. Release dates (evidence: /tmp/rr_fred_lags/REPORT.md, worker report 2026-11-12):

- DEXJPUS (Fed H.10): weekly, Monday 4:15 pm ET for the prior business week (next business day
  when Monday is a federal holiday). Observed ALFRED first-release dates are used where present
  (`FRED_FIRST_RELEASE_DATES_v1.csv`, 2019+, includes the one 2021-03-12 anomaly); the rule
  otherwise. Rule matched 1,711 / 1,712 observed 2020+ values.
- DFII10 (H.15): next business day. Observed first-release dates where present; rule otherwise.
- BAMLH0A0HYM2 (ICE BofA via FRED): next business day (production store evidence; ALFRED's
  date-level stamp is same-day but the 18:30 ET store held only the prior session).

A value released on session R is usable at R's close (the nightly run is after the 4:15 pm ET
release). The transforms are causal, so each leg value at d needs only a trailing slice.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from engine.indicators import pct_rank_window

PCT_WIN = 504
RELEASE_CSV = Path(__file__).resolve().parents[2] / "research" / "risk_radar" / "walkforward" / \
    "FRED_FIRST_RELEASE_DATES_v1.csv"
_BD = CustomBusinessDay(calendar=USFederalHolidayCalendar())


@lru_cache(maxsize=1)
def _observed() -> pd.DataFrame:
    if not RELEASE_CSV.exists():
        return pd.DataFrame(columns=["series", "obs_date", "first_release_date"])
    d = pd.read_csv(RELEASE_CSV, comment="#", parse_dates=["obs_date", "first_release_date"])
    return d


def release_dates(series: str, obs: pd.DatetimeIndex) -> pd.Series:
    obs = pd.DatetimeIndex(obs)
    if series == "DEXJPUS":
        monday_next = obs - pd.to_timedelta(obs.weekday, unit="D") + pd.Timedelta(days=7)
        rule = pd.DatetimeIndex([_BD.rollforward(m) for m in monday_next])
    elif series in ("DFII10", "BAMLH0A0HYM2"):
        rule = pd.DatetimeIndex([o + _BD for o in obs])
    else:
        raise ValueError(series)
    out = pd.Series(rule, index=obs)
    od = _observed()
    od = od[od["series"] == series].set_index("obs_date")["first_release_date"]
    hit = out.index.intersection(od.index)
    out.loc[hit] = od.loc[hit].values
    return out


def known_at(raw: pd.Series, series: str, sessions: pd.DatetimeIndex) -> pd.Series:
    """For each session d, the last observation date released by d (NaT if none)."""
    rel = release_dates(series, raw.index)
    order = np.argsort(rel.values, kind="stable")
    rel_sorted = rel.values[order]
    obs_sorted = raw.index.values[order]
    # running max of obs date over the release order: latest obs known once its release passed
    run_max = np.maximum.accumulate(obs_sorted.astype("datetime64[ns]").astype(np.int64))
    pos = np.searchsorted(rel_sorted, sessions.values, side="right") - 1
    vals = np.where(pos >= 0, run_max[np.clip(pos, 0, None)], np.iinfo(np.int64).min)
    return pd.Series(pd.to_datetime(np.where(pos >= 0, vals, 0)).where(pos >= 0), index=sessions)


def _known_subset(raw: pd.Series, series: str, d: pd.Timestamp) -> pd.Series:
    rel = release_dates(series, raw.index)
    return raw[rel.values <= np.datetime64(d)]


def replay_leg(raw: pd.Series, series: str, idx: pd.DatetimeIndex, start, *, kind: str,
               tail: int = 900) -> pd.Series:
    """Leg value at each session d >= start, rebuilt from data released by d.

    kind: 'diff21' (credit_oas_roc), 'diff5' (rates_realrate), 'jpy' (jpy_carry).
    Sessions sharing one known set reuse a single rebuild (exact: transforms are causal)."""
    raw = raw.dropna().sort_index()
    rel = release_dates(series, raw.index)
    days = idx[idx >= pd.Timestamp(start)]
    out = pd.Series(np.nan, index=days, dtype=float)
    # group sessions by the number of released observations
    n_known = np.searchsorted(np.sort(rel.values), days.values, side="right")
    groups: dict[int, list] = {}
    for d, k in zip(days, n_known):
        groups.setdefault(int(k), []).append(d)
    rel_sorted_idx = np.argsort(rel.values, kind="stable")
    for k, ds in groups.items():
        if k == 0:
            continue
        known = raw.iloc[np.sort(rel_sorted_idx[:k])]
        last = ds[-1]
        lo_pos = max(0, idx.get_loc(ds[0]) - tail)
        sidx = idx[lo_pos: idx.get_loc(last) + 1]
        known = known[known.index >= sidx[0] - pd.Timedelta(days=int(tail * 1.6) + 120)]
        if kind == "diff21":
            leg = pct_rank_window(known.diff(21).reindex(sidx).ffill(), PCT_WIN)
        elif kind == "diff5":
            leg = pct_rank_window(known.diff(5).reindex(sidx).ffill(), PCT_WIN)
        elif kind == "jpy":
            x = known.reindex(sidx).ffill()
            ma50 = x.rolling(50, min_periods=25).mean()
            roc10 = x / x.shift(10) - 1.0
            stress = (-roc10).where(x < ma50, other=0.0)
            leg = pct_rank_window(stress, PCT_WIN)
        else:
            raise ValueError(kind)
        out.loc[ds] = leg.reindex(ds).values
    return out


LEGS = {"credit_oas_roc": ("BAMLH0A0HYM2", "hy_oas", "diff21"),
        "rates_realrate": ("DFII10", "us10y_real", "diff5"),
        "jpy_carry": ("DEXJPUS", None, "jpy")}


def pit_signals(sigs: pd.DataFrame, start="2019-06-03") -> pd.DataFrame:
    """Replace the FRED legs from `start` on with their point-in-time replay. Rows before
    `start` keep a one-session shift (they only feed nothing scored; fit starts 2020-01-02)."""
    from lib import store
    out = sigs.copy()
    idx = out.index
    for col, (name, c, kind) in LEGS.items():
        if col not in out:
            continue
        df = store.read("fred", name)
        if df is None:
            continue
        s = df[c if c in df.columns else df.columns[0]].astype(float).dropna()
        s.index = pd.to_datetime(s.index)
        early = out[col].shift(1)
        rep = replay_leg(s, name, idx, start, kind=kind)
        out[col] = early.where(idx < pd.Timestamp(start), rep.reindex(idx))
    return out
