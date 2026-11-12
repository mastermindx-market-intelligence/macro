"""The shared Risk Radar scorecard: one function scores any daily alert series.

Research-only. Same terms for the incumbent and every challenger:

- **Budget** = share of scored sessions with the alert on.
- **Day level** (the published-figure definition): event rate on alert days for a >= depth SPY
  loss within the next H closes, vs the window's unconditional rate (lift).
- **Episode level** (the pivot target), per depth and horizon h:
  - an episode is *caught at onset* if the alert is on in any of the h sessions before its onset
    ([onset-h, onset-1]); lead = sessions from the first such alert day to onset;
  - an episode is *caught by breach* if the alert is on at any session from onset-h through the
    breach session; lead_to_breach = sessions from first such alert day to breach (>= 0);
  - an **alert run** is a maximal block of consecutive alert-on sessions. A run that starts inside
    an active episode (onset..recovery) is *in-episode* (confirming, not early). Otherwise it is
    *true* if an episode onset falls in [start+1, end+h], else a **false alarm**.
  - false alarms per year = false runs / (scored sessions / 252).
- **Calibration** (when a probability series is supplied): Brier vs the climatology base rate,
  Brier skill, and a fixed-bin reliability table.

All counts are printed; thin cells are flagged (n < 5 episodes or < 100 alert days).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import beta as _beta
import pandas as pd

from engine.risk_radar_eval import labels as L

DAY_HORIZONS = (5, 10, 21)
DAY_DEPTH = 0.05
PROB_BINS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 1.0001)
SESSIONS_PER_YEAR = 252


def alert_runs(alert: pd.Series) -> list[tuple[int, int]]:
    """(start_pos, end_pos) of consecutive True blocks, positions in alert.index."""
    a = alert.fillna(False).astype(bool).to_numpy()
    runs, i, n = [], 0, len(a)
    while i < n:
        if a[i]:
            j = i
            while j + 1 < n and a[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def threshold_for_budget(score: pd.Series, budget: float) -> float:
    """Threshold giving `budget` share of days at/above it on the supplied (fit-window) score."""
    s = score.dropna()
    if not len(s) or not 0 < budget < 1:
        raise ValueError("need a non-empty score and budget in (0,1)")
    return float(np.quantile(s.to_numpy(), 1.0 - budget))


def _day_level(alert: pd.Series, px: pd.Series, outcomes_through) -> dict:
    out = {}
    for h in DAY_HORIZONS:
        lab = L.forward_loss_labels(px, h, DAY_DEPTH, outcomes_through=outcomes_through)
        ev = lab["event"].reindex(alert.index)
        ok = ev.notna()
        a = alert[ok].astype(bool)
        e = ev[ok].astype(bool)
        base = float(e.mean()) if len(e) else None
        n_alert = int(a.sum())
        prec = float(e[a].mean()) if n_alert else None
        out[f"h{h}"] = {
            "n_days": int(len(e)), "n_alert_days": n_alert,
            "events": int(e.sum()), "base_rate": _r(base),
            "precision": _r(prec), "lift": _r(prec / base) if (prec is not None and base) else None,
            "thin": n_alert < 100,
        }
    return out


def _episode_level(alert: pd.Series, px: pd.Series, outcomes_through, depths, horizons,
                   merge_gap) -> dict:
    full_idx = px.index[px.index <= pd.Timestamp(outcomes_through)]
    a_full = alert.reindex(full_idx).fillna(False).astype(bool)
    a_np = a_full.to_numpy()
    pos = {d: i for i, d in enumerate(full_idx)}
    lo, hi = alert.index.min(), alert.index.max()
    years = len(alert) / SESSIONS_PER_YEAR
    runs = alert_runs(alert)
    run_bounds = [(pos[alert.index[s]], pos[alert.index[e]]) for s, e in runs]
    out = {}
    for depth in depths:
        eps = L.drawdown_episodes(px, depth, outcomes_through=outcomes_through,
                                  merge_gap=merge_gap)
        in_ep = L.in_episode_mask(full_idx, eps).to_numpy()
        scored = [e for e in eps if lo <= e.onset <= hi]
        onset_pos = [pos[e.onset] for e in eps]
        dkey = f"dd{int(round(depth * 100))}"
        out[dkey] = {"n_episodes": len(scored),
                     "episodes": [e.as_dict() for e in scored], "by_h": {}}
        for h in horizons:
            caught, leads, caught_b, leads_b = 0, [], 0, []
            for e in scored:
                o, b = pos[e.onset], pos[e.breach]
                w = np.nonzero(a_np[max(0, o - h):o])[0]
                if len(w):
                    caught += 1
                    leads.append(int(h - w[0]))
                wb = np.nonzero(a_np[max(0, o - h):b + 1])[0]
                if len(wb):
                    caught_b += 1
                    leads_b.append(int((b - max(0, o - h)) - wb[0]))
            n_true = n_false = n_in = 0
            for s, en in run_bounds:
                if in_ep[s]:
                    n_in += 1
                    continue
                if any(s + 1 <= op <= en + h for op in onset_pos):
                    n_true += 1
                else:
                    n_false += 1
            n_ep = len(scored)
            econ = _economics(a_np, px.reindex(full_idx).to_numpy(dtype=float), pos, scored,
                              lo_pos=pos[lo], hi_pos=pos[hi], h=h, years=years)
            out[dkey]["by_h"][f"h{h}"] = {
                **econ,
                "share_caught_by_breach_ci90": _cp(caught_b, n_ep),
                "caught_at_onset": caught,
                "share_caught_at_onset": _r(caught / n_ep) if n_ep else None,
                "median_lead_to_onset": _med(leads),
                "caught_by_breach": caught_b,
                "share_caught_by_breach": _r(caught_b / n_ep) if n_ep else None,
                "median_lead_to_breach": _med(leads_b),
                "alert_runs": len(run_bounds), "runs_true": n_true, "runs_in_episode": n_in,
                "false_alarms": n_false,
                "false_alarms_per_year": _r(n_false / years) if years else None,
                "thin": n_ep < 5,
            }
    return out


def _cp(k: int, n: int, level: float = 0.90):
    """Exact (Clopper-Pearson) interval for k of n. With n ~ 9 it is honestly wide."""
    if not n:
        return None
    a = (1 - level) / 2
    lo = 0.0 if k == 0 else float(_beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(_beta.ppf(1 - a, k + 1, n - k))
    return [round(lo, 3), round(hi, 3)]


EXEC_LAG = 1   # desk H19: an alert seen at d's close is acted on at d+1's close


def _economics(a_np, px, pos, episodes, *, lo_pos, hi_pos, h, years,
               exec_lag: int = EXEC_LAG) -> dict:
    """Paper accounting of an alert, descriptive only (never a trading rule).

    The alert at close d is read as "out of SPY for session d+1+exec_lag" (default exec_lag=1:
    decided at d's close, executed at d+1's close). Returns on those sessions are split by phase:
      decline  = onset..trough of a scored episode  -> loss avoided (positive is good)
      rebound  = trough+1..recovery                 -> rebound forgone (cost)
      outside  = any other session                  -> return given up outside episodes (cost)
    Per episode also: share of the peak-to-trough decline that came after the first alert
    (first alert day in [onset-h, trough]; 0 if none), lead to breach, and sessions from the
    trough until the alert is next off (all-clear delay).
    """
    n = len(px)
    r = np.full(n, np.nan)
    r[1:] = px[1:] / px[:-1] - 1.0
    phase = np.zeros(n, dtype=int)  # 0 outside, 1 decline, 2 rebound
    per_ep = []
    for e in episodes:
        o, t, b = pos[e.onset], pos[e.trough], pos[e.breach]
        rc = pos[e.recovery] if e.recovery is not None else n - 1
        phase[o:t + 1] = 1
        phase[t + 1:rc + 1] = 2
        pk = o - 1
        w = np.nonzero(a_np[max(0, o - h):t + 1])[0]
        first = max(0, o - h) + int(w[0]) if len(w) else None
        decline = px[pk] - px[t]
        share = 0.0
        if first is not None and decline > 0:
            fx = min(first + exec_lag, n - 1)
            share = float(np.clip((min(px[fx], px[pk]) - px[t]) / decline, 0.0, 1.0))
        clear = 0
        if a_np[t]:
            j = t
            while j < n and a_np[j]:
                j += 1
            clear = j - t
        per_ep.append({"onset": e.onset.date().isoformat(), "loss_avoided_share": round(share, 3),
                       "lead_to_breach": (b - first) if (first is not None and first <= b) else None,
                       "trough_to_all_clear": int(clear)})
    sel = np.zeros(n, dtype=bool)
    k = 1 + exec_lag
    sel[lo_pos + k:min(hi_pos + k + 1, n)] = True   # sessions d+k for d in window
    on_prev = np.zeros(n, dtype=bool)
    on_prev[k:] = a_np[:-k]
    m = sel & on_prev & np.isfinite(r)
    dec = float(-np.nansum(r[m & (phase == 1)]))
    reb = float(np.nansum(r[m & (phase == 2)]))
    outside = float(np.nansum(r[m & (phase == 0)]))
    shares = [p["loss_avoided_share"] for p in per_ep]
    clears = [p["trough_to_all_clear"] for p in per_ep]
    return {
        "loss_avoided_sum": _r(dec), "rebound_forgone_sum": _r(reb),
        "outside_return_forgone_sum": _r(outside),
        "net_avoided_minus_cost_sum": _r(dec - reb - outside),
        "net_per_year": _r((dec - reb - outside) / years) if years else None,
        "median_loss_avoided_share": _med(shares),
        "median_trough_to_all_clear": _med(clears),
        "exec_lag": exec_lag,
        "per_episode": per_ep,
    }


def _calibration(prob: pd.Series, px: pd.Series, outcomes_through, base_rate: float | None,
                 horizon: int = 21) -> dict:
    lab = L.forward_loss_labels(px, horizon, DAY_DEPTH, outcomes_through=outcomes_through)
    df = pd.DataFrame({"p": prob, "y": lab["event"].reindex(prob.index)}).dropna()
    if df.empty:
        return {"n": 0}
    y = df["y"].astype(float).to_numpy()
    p = df["p"].astype(float).clip(0, 1).to_numpy()
    base = float(y.mean()) if base_rate is None else float(base_rate)
    brier = float(np.mean((p - y) ** 2))
    brier_base = float(np.mean((base - y) ** 2))
    bins = []
    edges = PROB_BINS
    for lo_, hi_ in zip(edges[:-1], edges[1:]):
        m = (p >= lo_) & (p < hi_)
        if m.any():
            bins.append({"bin": [lo_, round(min(hi_, 1.0), 2)], "n": int(m.sum()),
                         "mean_p": _r(float(p[m].mean())), "observed": _r(float(y[m].mean()))})
    return {"horizon": horizon, "depth": DAY_DEPTH, "n": int(len(y)),
            "base_rate_used": _r(base), "base_rate_source": "supplied" if base_rate is not None else "window",
            "brier": _r(brier, 5), "brier_base": _r(brier_base, 5),
            "brier_skill": _r(1 - brier / brier_base) if brier_base else None,
            "reliability": bins}


def score(alert: pd.Series, *, px: pd.Series, outcomes_through, prob: pd.Series | None = None,
          prob_base_rate: float | None = None, depths=L.DEFAULT_DEPTHS,
          horizons=L.DEFAULT_HORIZONS, merge_gap: int = L.DEFAULT_MERGE_GAP,
          sealed_from=L.SEALED_FROM, seen_history_ok: bool = False, name: str = "") -> dict:
    """Score a daily boolean alert series over its own index (the scoring window)."""
    alert = alert.dropna().astype(bool).sort_index()
    if alert.empty:
        raise ValueError("empty alert series")
    L.check_scoring_window(alert.index, sealed_from=sealed_from, seen_history_ok=seen_history_ok)
    if alert.index.max() > pd.Timestamp(outcomes_through):
        raise L.LabelLeakError("alert window extends past outcomes_through")
    res = {
        "name": name,
        "window": [alert.index.min().date().isoformat(), alert.index.max().date().isoformat()],
        "outcomes_through": pd.Timestamp(outcomes_through).date().isoformat(),
        "n_sessions": int(len(alert)),
        "budget": _r(float(alert.mean())),
        "seen_history": bool(seen_history_ok),
        "day_level": _day_level(alert, px, outcomes_through),
        "episode_level": _episode_level(alert, px, outcomes_through, depths, horizons, merge_gap),
    }
    if prob is not None:
        res["calibration_h21"] = _calibration(prob.reindex(alert.index), px, outcomes_through,
                                              prob_base_rate)
    return res


def _r(x, nd: int = 4):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return round(float(x), nd)


def _med(xs):
    return None if not xs else float(np.median(xs))
