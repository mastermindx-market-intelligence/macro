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
