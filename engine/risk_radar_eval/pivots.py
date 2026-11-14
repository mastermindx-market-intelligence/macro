"""Pivot scorecard: was each turn into risk-off, and back out to risk-on, flagged, and how late?

Research-only; nothing in the live engine imports this. Chairman steer 2026-11-12: the goal is
identifying pivots accurately, not beating SPY. This is the PRIMARY read; the paper economics in
`scorecard.py` stay as a secondary column.

Turns
-----
A turn is (kind, date): kind "top" is a turn into risk-off, kind "bottom" a turn back to risk-on.
`turns_from_episodes` derives them from the shared drawdown episodes (top = episode peak, bottom =
episode trough; an open episode has no bottom yet). Any other catalogue (e.g. the research desk's
swing rule over many assets) can be passed in as a list of `Turn` and is scored identically.

Calls
-----
- A risk-off call is an alert run START (off -> on) at session s.
- An all-clear is an alert run END that holds: the first session the alert is off again, provided
  it then stays off for at least `min_off` sessions (default 10). An off-flicker that turns back on
  sooner is not an all-clear (it is counted as premature if it falls inside a decline). An end
  too close to the last scored session to know whether it holds is censored, not counted.
A top is *flagged* if a risk-off call falls in [top - pre, top + post]; a bottom is flagged if an
all-clear falls in [bottom - pre, bottom + post]. Delay = call session - turn session, in
sessions (negative = before the turn). Several calls in one window: the first counts. A call
already running before the window opened does not flag the turn (`on_at_turn` records it).

Unmatched calls (false signals)
-------------------------------
- risk-off call matched to no top window: *in-episode* if it starts between an episode's onset and
  its recovery (a late repeat inside the same decline), else a **false risk-off signal**;
- all-clear matched to no bottom window: **premature all-clear** if it falls between an episode's
  onset and its trough (the decline was not over), else not counted (end of an unmatched run).
Rates are per year of scored sessions.

Censoring (never scored as hits or misses)
------------------------------------------
- a turn whose window starts before the first scored session (left-censored);
- a turn whose window ends after `outcomes_through` or the last scored session (right-censored);
- the bottom of an open episode does not exist yet.
Missing alert rows are not compressed: the alert must be on the full session index; NaN is
refused.

Every share is printed with its count and an exact (Clopper-Pearson) 90% interval; with 9 turns
no interval tighter than that is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.risk_radar_eval import labels as L
from engine.risk_radar_eval.scorecard import _cp, _r, SESSIONS_PER_YEAR

DEFAULT_PRE = 21
DEFAULT_POST = 10
DEFAULT_MIN_OFF = 10


@dataclass(frozen=True)
class Turn:
    kind: str                 # "top" | "bottom"
    date: pd.Timestamp
    depth: float | None = None
    asset: str = "SPY"
    episode_onset: pd.Timestamp | None = None   # links a top and its bottom
    cluster_id: str | None = None               # turns sharing a date cluster (honest N)


def turns_from_episodes(episodes: list[L.Episode]) -> list[Turn]:
    out = []
    for e in episodes:
        out.append(Turn("top", e.peak, e.depth, episode_onset=e.onset))
        # the trough is only final once the episode has recovered; an open episode's running
        # low may still be undercut, so it is not a turn yet
        if e.recovery is not None:
            out.append(Turn("bottom", e.trough, e.depth, episode_onset=e.onset))
    return out


def summarise(rows: list[dict], kind: str) -> dict:
    """Flagged share over turns and over date clusters (a cluster is flagged if any of its scored
    turns is flagged; a turn without cluster_id is its own cluster)."""
    sc = [r for r in rows if r["kind"] == kind and r["status"] == "scored"]
    k = sum(r["flagged"] for r in sc)
    d = [int(r["delay"]) for r in sc if r["flagged"]]
    lo, hi = _cp(k, len(sc)) if sc else (None, None)
    cl: dict = {}
    for i, r in enumerate(sc):
        key = r.get("cluster_id") or f"__{r.get('asset')}_{r['date']}_{i}"
        cl[key] = cl.get(key, False) or bool(r["flagged"])
    kc = sum(cl.values())
    clo, chi = _cp(kc, len(cl)) if cl else (None, None)
    return {"n_turns": len(sc), "flagged": int(k),
            "share_flagged": _r(k / len(sc)) if sc else None,
            "share_ci90": [_r(lo), _r(hi)] if sc else None,
            "n_clusters": len(cl), "clusters_flagged": int(kc),
            "cluster_share_flagged": _r(kc / len(cl)) if cl else None,
            "cluster_share_ci90": [_r(clo), _r(chi)] if cl else None,
            "median_delay": None if not d else float(np.median(d)),
            "delays": d,
            "censored": sum(1 for r in rows if r["kind"] == kind and r["status"] != "scored")}


def _calls(alert: pd.Series, min_off: int):
    a = alert.to_numpy(dtype=bool)
    n = len(a)
    starts = [i for i in range(n) if a[i] and (i == 0 or not a[i - 1])]
    ends, flickers = [], []
    for i in range(1, n):
        if (not a[i]) and a[i - 1]:                     # first off session
            if i + min_off > n:
                continue                                 # cannot tell yet whether it holds
            (flickers if a[i:i + min_off].any() else ends).append(i)
    return starts, ends, flickers


def score_pivots(alert: pd.Series, *, turns: list[Turn], episodes: list[L.Episode],
                 outcomes_through, pre: int = DEFAULT_PRE, post: int = DEFAULT_POST,
                 min_off: int = DEFAULT_MIN_OFF,
                 regime: pd.Series | None = None, sealed_from=L.SEALED_FROM,
                 seen_history_ok: bool = False, name: str = "") -> dict:
    """Score risk-off calls against tops and all-clears against bottoms."""
    if alert.isna().any():
        raise ValueError("alert has missing sessions; mark them explicitly, do not drop them")
    alert = alert.astype(bool).sort_index()
    L.check_scoring_window(alert.index, sealed_from=sealed_from, seen_history_ok=seen_history_ok)
    cut = pd.Timestamp(outcomes_through)
    if alert.index.max() > cut:
        raise L.LabelLeakError("alert window extends past outcomes_through")
    idx = alert.index
    n = len(idx)
    starts, ends, flickers = _calls(alert, min_off)
    a = alert.to_numpy(dtype=bool)

    def pos(d):
        p = idx.searchsorted(pd.Timestamp(d))
        return p if p < n and idx[p] == pd.Timestamp(d) else None

    rows, used_s, used_e = [], set(), set()
    for t in sorted(turns, key=lambda t: t.date):
        p = pos(t.date)
        row = {"kind": t.kind, "date": pd.Timestamp(t.date).date().isoformat(), "depth": t.depth,
               "asset": t.asset, "cluster_id": t.cluster_id,
               "regime": None if regime is None else regime.reindex([pd.Timestamp(t.date)]).iloc[0]}
        if p is None:
            row["status"] = "outside_window"
        elif p - pre < 0:
            row["status"] = "left_censored"
        elif p + post > n - 1:
            row["status"] = "right_censored"
        else:
            cands = starts if t.kind == "top" else ends
            hit = [c for c in cands if p - pre <= c <= p + post]
            row["status"] = "scored"
            row["flagged"] = bool(hit)
            row["delay"] = int(hit[0] - p) if hit else None
            row["on_at_turn"] = bool(a[p])
            if hit:
                (used_s if t.kind == "top" else used_e).add(hit[0])
                for c in hit[1:]:
                    (used_s if t.kind == "top" else used_e).add(c)
        rows.append(row)

    def in_span(i, lo_attr, hi_attr):
        d = idx[i]
        for e in episodes:
            lo = getattr(e, lo_attr)
            hi = getattr(e, hi_attr) if getattr(e, hi_attr) is not None else idx.max()
            if lo <= d <= hi:
                return True
        return False

    false_on = in_ep = premature = 0
    for s in starts:
        if s in used_s:
            continue
        if in_span(s, "onset", "recovery"):
            in_ep += 1
        else:
            false_on += 1
    for e_ in sorted(ends + flickers):
        if e_ in used_e:
            continue
        if in_span(e_, "onset", "trough"):
            premature += 1
    years = n / SESSIONS_PER_YEAR

    def summ(kind, subset=None):
        return summarise(rows if subset is None else subset, kind)

    by_regime = {}
    if regime is not None:
        for g in sorted({r["regime"] for r in rows if r["regime"] is not None}, key=str):
            sub = [r for r in rows if r["regime"] == g]
            by_regime[str(g)] = {"top": summ("top", sub), "bottom": summ("bottom", sub)}
    return {
        "name": name,
        "window": [idx.min().date().isoformat(), idx.max().date().isoformat()],
        "flag_window": {"pre": pre, "post": post, "min_off": min_off},
        "budget": _r(float(a.mean())),
        "n_calls": {"risk_off": len(starts), "all_clear": len(ends), "off_flickers": len(flickers)},
        "top": summ("top"),
        "bottom": summ("bottom"),
        "false_risk_off_per_year": _r(false_on / years),
        "false_risk_off": false_on,
        "in_episode_repeat_calls": in_ep,
        "premature_all_clear_per_year": _r(premature / years),
        "premature_all_clear": premature,
        "by_regime": by_regime,
        "turns": rows,
    }


def score_pivots_multi(turns: list[Turn], alerts: dict[str, pd.Series],
                       episodes: dict[str, list], *, outcomes_through, posts=(5, 10, 21),
                       pre: int = DEFAULT_PRE, min_off: int = DEFAULT_MIN_OFF,
                       sealed_from=L.SEALED_FROM, seen_history_ok: bool = False,
                       name: str = "") -> dict:
    """Score each asset's turns against that asset's own alert, at several post windows.

    `episodes[asset]` is any list of objects with onset / trough / recovery dates (e.g.
    `labels.Episode`, or swing legs peak->trough->next peak built as Episode). Turns whose asset has
    no alert are reported as `no_alert`, never as misses. Pooled summaries are over turns and over
    date clusters across assets; false/premature rates are summed over assets and divided by
    summed asset-years.
    """
    out = {"name": name, "pre": pre, "min_off": min_off, "by_post": {}}
    by_asset: dict[str, list[Turn]] = {}
    for t in turns:
        by_asset.setdefault(t.asset, []).append(t)
    out["no_alert"] = sorted(a for a in by_asset if a not in alerts)
    for post in posts:
        per, rows, fro, prem, yrs = {}, [], 0, 0, 0.0
        for asset, ts in sorted(by_asset.items()):
            if asset not in alerts:
                continue
            r = score_pivots(alerts[asset], turns=ts, episodes=episodes.get(asset, []),
                             outcomes_through=outcomes_through, pre=pre, post=post,
                             min_off=min_off, sealed_from=sealed_from,
                             seen_history_ok=seen_history_ok, name=asset)
            per[asset] = r
            rows += r["turns"]
            fro += r["false_risk_off"]
            prem += r["premature_all_clear"]
            yrs += len(alerts[asset]) / SESSIONS_PER_YEAR
        out["by_post"][f"post{post}"] = {
            "top": summarise(rows, "top"), "bottom": summarise(rows, "bottom"),
            "false_risk_off_per_asset_year": _r(fro / yrs) if yrs else None,
            "premature_all_clear_per_asset_year": _r(prem / yrs) if yrs else None,
            "by_asset": per,
        }
    return out


def placebo(alert: pd.Series, *, px: pd.Series, turns: list[Turn], episodes: list,
            outcomes_through, near: str | None = None, tol: float = 0.01, n_draws: int = 500,
            seed: int = 0, pre: int = DEFAULT_PRE, post: int = DEFAULT_POST,
            min_off: int = DEFAULT_MIN_OFF, sealed_from=L.SEALED_FROM,
            seen_history_ok: bool = False) -> dict:
    """Random-run placebo for the flagged shares (research desk falsification, 2026-11-12).

    Draws alert series with the observed alert's run lengths (hence its budget and persistence),
    placing each run's start at random among eligible sessions without overlap:
      near=None    any session;
      near="high"  sessions whose close is within `tol` of the running high (causal: closes <= t);
      near="low"   sessions whose close is within `tol` of the lowest close since the running high.
    A top-flagged share means something only above the near="high" placebo; a bottom share only
    above near="low". Returns the placebo distribution of flagged shares and the share of draws at
    or above the observed value (a permutation-style p, not a significance claim on 9 turns).
    """
    alert = alert.astype(bool).sort_index()
    idx = alert.index
    p = px.reindex(idx).ffill().to_numpy(dtype=float)
    n = len(idx)
    if near is None:
        elig = np.ones(n, dtype=bool)
    else:
        hi = np.maximum.accumulate(np.where(np.isnan(p), -np.inf, p))
        if near == "high":
            elig = p >= hi * (1 - tol)
        elif near == "low":
            lo = np.empty(n)
            for i in range(n):
                lo[i] = p[i] if (i == 0 or hi[i] != hi[i - 1] or p[i] >= hi[i]) else min(lo[i - 1], p[i])
            elig = p <= lo * (1 + tol)
        else:
            raise ValueError("near must be None, 'high' or 'low'")
    starts = np.flatnonzero(elig)
    runs = [e - s + 1 for s, e in _run_bounds(alert.to_numpy(dtype=bool))]
    obs = score_pivots(alert, turns=turns, episodes=episodes, outcomes_through=outcomes_through,
                       pre=pre, post=post, min_off=min_off, sealed_from=sealed_from,
                       seen_history_ok=seen_history_ok)
    rng = np.random.default_rng(seed)
    shares = {"top": [], "bottom": []}
    fro, prem = [], []
    for _ in range(n_draws):
        a = np.zeros(n, dtype=bool)
        for ln in rng.permutation(runs):
            for _try in range(50):
                s = int(rng.choice(starts)) if len(starts) else 0
                e = min(n, s + int(ln))
                lo_, hi_ = max(0, s - 1), min(n, e + 1)      # keep runs separate
                if not a[lo_:hi_].any():
                    a[s:e] = True
                    break
        r = score_pivots(pd.Series(a, index=idx), turns=turns, episodes=episodes,
                         outcomes_through=outcomes_through, pre=pre, post=post, min_off=min_off,
                         sealed_from=sealed_from, seen_history_ok=seen_history_ok)
        fro.append(r["false_risk_off_per_year"])
        prem.append(r["premature_all_clear_per_year"])
        for k in shares:
            if r[k]["share_flagged"] is not None:
                shares[k].append(r[k]["share_flagged"])
    out = {"near": near, "tol": tol, "n_draws": n_draws, "seed": seed,
           "eligible_share": _r(float(elig.mean())),
           "false_risk_off_per_year": {"observed": obs["false_risk_off_per_year"],
                                       "placebo_mean": _r(float(np.mean(fro))),
                                       "placebo_median": _r(float(np.median(fro)))},
           "premature_all_clear_per_year": {"observed": obs["premature_all_clear_per_year"],
                                            "placebo_mean": _r(float(np.mean(prem))),
                                            "placebo_median": _r(float(np.median(prem)))}}
    for k, v in shares.items():
        o = obs[k]["share_flagged"]
        v = np.asarray(v)
        out[k] = {"observed": o,
                  "placebo_mean": _r(float(v.mean())) if len(v) else None,
                  "placebo_median": _r(float(np.median(v))) if len(v) else None,
                  "placebo_p90": _r(float(np.quantile(v, 0.9))) if len(v) else None,
                  "share_draws_ge_observed": (_r(float((v >= o - 1e-12).mean()))
                                              if len(v) and o is not None else None)}
    return out


def beyond_reference(sig: dict, ref: dict, *, kind: str = "top") -> dict:
    """Early catches of `sig` beyond a mechanical reference (principal ruling 2026-11-12, point 4).

    `sig` and `ref` are `score_pivots` results on the same turns and window. An early catch is a
    scored, flagged turn with delay < 0. It counts as incremental unless the reference also flags
    that turn AND the reference's false risk-off rate is <= the signal's (literal rule). The strict
    column excludes every turn the reference flags, whatever its false-call rate. Secondary read.
    """
    rr = {(r["kind"], r["date"]): r for r in ref["turns"] if r.get("status") == "scored"}
    sf, rf = sig["false_risk_off_per_year"], ref["false_risk_off_per_year"]
    ref_qualifies = rf is not None and sf is not None and rf <= sf
    early = [r for r in sig["turns"] if r["kind"] == kind and r.get("status") == "scored"
             and r.get("flagged") and r["delay"] is not None and r["delay"] < 0]
    also = [r for r in early if rr.get((kind, r["date"]), {}).get("flagged")]
    n = sum(1 for r in sig["turns"] if r["kind"] == kind and r.get("status") == "scored")
    return {"kind": kind, "n_turns": n, "early_catches": len(early),
            "also_caught_by_reference": len(also),
            "incremental_literal": len(early) - (len(also) if ref_qualifies else 0),
            "incremental_strict": len(early) - len(also),
            "reference_false_per_year": rf, "signal_false_per_year": sf,
            "reference_meets_rate_condition": ref_qualifies,
            "early_dates": [r["date"] for r in early],
            "incremental_strict_dates": [r["date"] for r in early if r not in also]}


def _run_bounds(a: np.ndarray) -> list[tuple[int, int]]:
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i]:
            j = i
            while j + 1 < n and a[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out
