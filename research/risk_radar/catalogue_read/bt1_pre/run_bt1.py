#!/usr/bin/env python3
"""Risk Radar BREAKTHROUGH-1 approach #1: BT1-RATE-RESPONSE on PRE, description only.

Bounded research worker. Paper-only: nothing sizes, ranks or executes.

Two already-written ledger rows (rows written before any read):
  rr-bt1-rate-response-pre-desc        spec d80306439c57cdc945d27055551647b329bce5e1987ea6e623d7b1effc4f276a
  rr-bt1-rate-response-pre-dgs10-desc  spec 63a0ce44d5df9fa85ea83d88c3d4468e7fbc5c94be0090f3120f624daa876235
Both are DESCRIPTION only, never a nomination, one set read in the chance account.

Frozen rule (BREAKTHROUGH_1_ANSWER.md sections 1 / Displaced-clock / Fragmentation):
  B20_X(t) = log(min(X[t-20..t-1]) / X[t])
  Rplus(t) = max qR(s), s in {t-5..t-1}, dy5(s) > 0; 0 if all five valid and none positive;
             undefined (not alerting) otherwise
  A_R(t)   = Rplus(t) >= .90 AND B20_SPY(t) > 0 AND B20_QQQ(t) > 0, published t+1
Nothing is tuned. The DGS10 block is the same frozen rule with qR/dy5 built from FRED DGS10.

Usage:
    python3 run_bt1.py --desk <path-to-desk-v4>
    ROTATION_DESK=<path> python3 run_bt1.py
    RR_DRY=1 python3 run_bt1.py --desk <desk>     # 50 placebo / 200 control draws

Two-phase import (kept from followup_rev1/run_rev1.py):
  1. build the rate legs from Macro's engine PIT replay;
  2. purge `engine*` from sys.modules and drop the Macro root + cwd from sys.path;
  3. load the desk kit; 4. assert `pivots.__file__` is under the desk.

Writes ONLY into this directory: result.json, SUMMARY.md, RUN_LOG.txt.
The desk is imported read-only; trials.jsonl is read only for the row/spec check.
Nothing after 2019-12-31 enters any alert, turn, level or outcome; asserted and recorded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
RUN_LOG = HERE / "RUN_LOG.txt"

START = pd.Timestamp("2006-01-03")
END = pd.Timestamp("2019-12-31")
PRE = 21
POST = 5
SEED = 20261112
TOL = 0.01
MIN_OFF = 10
DRY = bool(os.environ.get("RR_DRY"))
N_DRAWS = 50 if DRY else 2000
NPROC = 20

CTRL_SEED = 20261113
CTRL_MAX = 20000 if DRY else 200000
CTRL_KEEP = 200 if DRY else 2000
CTRL_EDGE = 27

PIN_BM = "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"
PIN_AD = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"

ID_RATE = "rr-bt1-rate-response-pre-desc"
SHA_RATE = "d80306439c57cdc945d27055551647b329bce5e1987ea6e623d7b1effc4f276a"
ID_DGS = "rr-bt1-rate-response-pre-dgs10-desc"
SHA_DGS = "63a0ce44d5df9fa85ea83d88c3d4468e7fbc5c94be0090f3120f624daa876235"

PARTS = ("Rplus", "B20_SPY", "B20_QQQ", "response_only")
ADVERSARIES = ("Q5", "D5")


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log(msg: str) -> None:
    with open(RUN_LOG, "a") as fh:
        fh.write(msg + "\n")
    print(msg, flush=True)


def check_pins(desk: Path, when: str) -> dict:
    p = {"bm_ref.py": sha256(desk / "catalogue" / "bm_ref.py"),
         "adapter.py": sha256(desk / "catalogue" / "adapter.py")}
    log(f"[{when}] bm_ref.py {p['bm_ref.py']}")
    log(f"[{when}] adapter.py {p['adapter.py']}")
    if p["bm_ref.py"] != PIN_BM:
        raise SystemExit(f"PIN MISMATCH bm_ref.py {p['bm_ref.py']} != {PIN_BM}; STOP")
    if p["adapter.py"] != PIN_AD:
        raise SystemExit(f"PIN MISMATCH adapter.py {p['adapter.py']} != {PIN_AD}; STOP")
    return p


def check_rows(desk: Path) -> dict:
    """The two rows must already exist with exactly the commissioned spec sha."""
    found = {}
    with (desk / "trials.jsonl").open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("id") in (ID_RATE, ID_DGS):
                found[r["id"]] = r.get("spec_sha256")
    for rid, want in ((ID_RATE, SHA_RATE), (ID_DGS, SHA_DGS)):
        if rid not in found:
            raise SystemExit(f"ledger row absent: {rid}; STOP")
        if found[rid] != want:
            raise SystemExit(f"ledger row {rid} spec sha {found[rid]} != {want}; STOP")
    log(f"# ledger rows present with the commissioned spec shas: {ID_RATE}, {ID_DGS}")
    return found


# ------------------------------------------------------------------ phase 1: Macro rate legs
def replay_diff5(raw: pd.Series, idx: pd.DatetimeIndex, start, release_fn, tail: int = 900
                 ) -> tuple[pd.Series, pd.Series]:
    """availability.replay_leg's kind='diff5' path, verbatim, returning (percentile, dy5).

    Observation obs is released on release_fn(obs); a session d uses only observations released
    by d. The transform is causal, so sessions sharing one known set reuse one rebuild.
    """
    from engine.indicators import pct_rank_window
    raw = raw.dropna().sort_index()
    rel = release_fn(raw.index)
    days = idx[idx >= pd.Timestamp(start)]
    out_q = pd.Series(np.nan, index=days, dtype=float)
    out_d = pd.Series(np.nan, index=days, dtype=float)
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
        dy = known.diff(5).reindex(sidx).ffill()
        leg = pct_rank_window(dy, 504)
        out_q.loc[ds] = leg.reindex(ds).values
        out_d.loc[ds] = dy.reindex(ds).values
    return out_q, out_d


def build_rate_inputs(replay_start="2004-01-01") -> dict:
    """qR and dy5 for DFII10 (the engine's PIT series) and for DGS10 (same rule, nominal)."""
    from engine import risk_radar as rr
    from engine.risk_radar_eval import availability as AV
    from lib import store
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from pandas.tseries.offsets import CustomBusinessDay

    t0 = time.time()
    sigs = rr.leading_signals()
    idx = sigs.index
    pit = AV.pit_signals(sigs, start=str(START.date()))
    log(f"  leading_signals + pit_signals: {time.time()-t0:.1f}s; "
        f"calendar {idx.min().date()} .. {idx.max().date()}")
    q_dfii = pit["rates_realrate"]

    q_rep, d_rep = replay_diff5(store.read("fred", "DFII10")["us10y_real"], idx, replay_start,
                                lambda obs: AV.release_dates("DFII10", obs))
    dy_dfii = d_rep

    # my replay must reproduce the engine's PIT leg exactly from the pit start onward (before it,
    # pit_signals keeps the production leg shifted one session, so those rows are not comparable)
    common = q_rep[(q_rep.index >= START)].dropna().index.intersection(
        q_dfii.dropna().index)
    diff = float(np.max(np.abs(q_rep.loc[common] - q_dfii.loc[common]))) if len(common) else None
    nan_mismatch = int((q_rep.reindex(common).isna() != q_dfii.reindex(common).isna()).sum())
    log(f"  DFII10 replay vs pit_signals: {len(common)} common finite sessions from "
        f"{START.date()}, max |diff| {diff}, nan mismatches {nan_mismatch}")
    if diff is None or diff > 1e-12 or nan_mismatch:
        raise SystemExit(f"DFII10 replay disagrees with the engine PIT leg: {diff}; STOP")

    # DGS10: the PIT helper has NO DGS10 rule (its release_dates accepts DEXJPUS / DFII10 /
    # BAMLH0A0HYM2 only, and the ALFRED first-release CSV has no DGS10 rows). Use the DFII10
    # branch's documented rule: observation t usable from the next business day.
    bd = CustomBusinessDay(calendar=USFederalHolidayCalendar())

    def dgs10_release(obs):
        return pd.Series(pd.DatetimeIndex([o + bd for o in obs]), index=obs)

    q_dgs, dy_dgs = replay_diff5(store.read("fred", "DGS10")["us10y"], idx, replay_start,
                                 dgs10_release)
    log(f"  DGS10 PIT leg: next-business-day rule (no ALFRED overrides); "
        f"{int(q_dgs.notna().sum())} finite sessions from {q_dgs.first_valid_index().date()}")
    return {"idx": idx, "q_dfii": q_dfii, "dy_dfii": dy_dfii,
            "q_dgs": q_dgs, "dy_dgs": dy_dgs,
            "dgs10_rule": "next-business-day (obs t usable from t+1 business day, "
                          "US federal holiday calendar); no ALFRED first-release overrides "
                          "exist for DGS10 in FRED_FIRST_RELEASE_DATES_v1.csv",
            "dfii10_rule": "engine availability.release_dates('DFII10') + ALFRED overrides "
                           "(pit_signals)"}


# ------------------------------------------------------------------ phase 2: desk kit
def purge_engine() -> None:
    for m in [m for m in sys.modules if m == "engine" or m.startswith("engine.")]:
        del sys.modules[m]


def load_desk_kit(desk: Path):
    sys.path[:] = [p for p in sys.path
                   if p not in ("", ".", str(_ROOT), str(_ROOT.resolve()), os.getcwd())]
    purge_engine()
    for p in (desk, desk / "catalogue", desk / "pivot"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from catalogue import adapter as A
    from catalogue import bm_ref as BM
    pv, _L = A.load_radar_kit()
    resolved = Path(pv.__file__).resolve()
    if desk.resolve() not in resolved.parents:
        raise SystemExit(f"scorer resolved outside the desk: {resolved}")
    if not hasattr(pv, "score_pivots_multi"):
        raise SystemExit(f"scorer lacks score_pivots_multi: {resolved}")
    return A, BM, pv, resolved


# ------------------------------------------------------------------ rule construction
def b20(level: pd.Series) -> pd.Series:
    """log(min(X[t-20..t-1]) / X[t]); > 0 means a new closing low vs the prior 20 sessions."""
    x = pd.Series(level, dtype=float).sort_index()
    roll_min = x.rolling(20, min_periods=20).min().shift(1)
    return np.log(roll_min / x)


def _window5(s: pd.Series) -> pd.DataFrame:
    """Columns are s[t-1] .. s[t-5] (neutral names: duplicate labels corrupt frame ops)."""
    return pd.concat([s.shift(k) for k in range(1, 6)], axis=1,
                     keys=[f"lag{k}" for k in range(1, 6)])


def build_rule(qR: pd.Series, dy5: pd.Series, bp: np.ndarray | pd.Series,
               b20s: pd.Series, b20q: pd.Series) -> dict:
    q = pd.Series(qR, dtype=float).sort_index()
    d = pd.Series(dy5, dtype=float).sort_index()
    qw, dw = _window5(q), _window5(d)
    valid = (qw.notna() & dw.notna())
    all_valid = valid.all(axis=1)
    pos = dw > 0
    any_pos = (pos & qw.notna()).any(axis=1)
    rplus = (qw.where(pos).max(axis=1)).where(any_pos)
    rplus = rplus.where(~(all_valid & ~any_pos), 0.0)
    q5 = qw.max(axis=1, skipna=True)
    d5 = dw.max(axis=1, skipna=True)
    price = pd.Series(bp, index=b20s.index, dtype=bool)
    a_r = ((rplus >= 0.90) & price).fillna(False).astype(bool)
    resp = pd.concat([b20s, b20q], axis=1).min(axis=1)
    return {"Rplus": rplus, "Q5": q5, "D5": d5, "A": a_r, "B20_SPY": b20s,
            "B20_QQQ": b20q, "response_only": resp,
            "n_rplus_undefined": int(rplus.isna().sum())}


def window_index(levels: dict, n: str) -> pd.DatetimeIndex:
    idx = levels[n].index
    sp = int(idx.searchsorted(START))
    lo = max(0, sp - PRE)
    ai = idx[lo:]
    return ai[ai <= END]


def window_alert(full: pd.Series, levels: dict, series: list) -> dict:
    out = {}
    for n in series:
        ai = window_index(levels, n)
        if len(ai) == 0:
            raise SystemExit(f"empty window for {n}")
        a = full.reindex(ai, method="ffill")
        if a.isna().any():
            raise SystemExit(f"alert has NaN after reindex for {n}")
        out[n] = a.astype(bool)
        assert out[n].index.max() <= END, n
    return out


def window_score(full: pd.Series, levels: dict, series: list) -> dict:
    out = {}
    for n in series:
        ai = window_index(levels, n)
        s = full.reindex(ai, method="ffill").astype(float)
        out[n] = s
        assert s.index.max() <= END, n
    return out


def pooled_share(alerts: dict) -> float:
    num = sum(int(pd.Series(a).sum()) for a in alerts.values())
    den = sum(len(pd.Series(a)) for a in alerts.values())
    return float(num / den) if den else None


def share_by_year(full: pd.Series) -> dict:
    win = (full.index >= START) & (full.index <= END)
    w = full[win]
    return {int(y): round(float(v), 4) for y, v in w.groupby(w.index.year).mean().items()}


def starts_of(a: np.ndarray) -> int:
    if len(a) == 0:
        return 0
    return int(np.sum(a & ~np.r_[False, a[:-1]]))


# ------------------------------------------------------------------ scoring helpers
_G: dict = {}


def _score_job(alerts: dict) -> dict:
    BM = _G["BM"]
    return BM.score_alerts(_G["turns"], alerts, _G["episodes"], _G["px"], direction="top",
                           post=POST, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                           min_off=MIN_OFF, include_passes=False, outcomes_through=END)


def _ctrl_chunk(items: list) -> list:
    BM, levels, series = _G["BM"], _G["levels"], _G["series"]
    out = []
    for i, full in items:
        alerts = window_alert(full, levels, series)
        r = BM.score_alerts(_G["turns"], alerts, _G["episodes"], _G["px"], direction="top",
                            post=POST, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                            min_off=MIN_OFF, include_passes=False, outcomes_through=END)
        out.append((i, r["cluster_share"], r["false_per_asset_year"]))
    return out


_P90: dict = {}


def _p90_chunk(di_list: list) -> list:
    P = _P90
    pv = P["pv"]
    out = []
    for di in di_list:
        pooled: list[dict] = []
        for a in P["assets"]:
            r = pv.score_pivots(pd.Series(P["draws"][a][di], index=P["idxs"][a]),
                                turns=P["by_asset"][a], episodes=P["episodes"].get(a, []),
                                outcomes_through=P["ot"], pre=P["pre"], post=P["post"],
                                min_off=P["min_off"])
            pooled += r["turns"]
        sh = pv.summarise(pooled, "top")["cluster_share_flagged"]
        if sh is not None:
            out.append(float(sh))
    return out


def parallel_p90(BM, pv, turns, alerts, episodes, px, *, post=POST, n_draws=N_DRAWS) -> dict:
    by_asset: dict[str, list] = {}
    for t in turns:
        by_asset.setdefault(t.asset, []).append(t)
    assets = [a for a in sorted(by_asset) if a in alerts]
    draws, idxs = {}, {}
    for a in assets:
        d, i = BM._placebo_draw_arrays(alerts[a], px[a], "high", TOL, n_draws, SEED)
        draws[a], idxs[a] = d, i
    shares: list[float] = []
    if assets:
        chunk = 50
        chunks = [list(range(lo, min(n_draws, lo + chunk))) for lo in range(0, n_draws, chunk)]
        _P90.clear()
        _P90.update(pv=pv, assets=assets, by_asset=by_asset, draws=draws, idxs=idxs,
                    episodes=episodes, ot=END, pre=PRE, post=post, min_off=MIN_OFF)
        with ProcessPoolExecutor(max_workers=min(NPROC, len(chunks))) as ex:
            for res in ex.map(_p90_chunk, chunks):
                shares += res
        _P90.clear()
    obs = pv.summarise([row for a in assets
                        for row in pv.score_pivots(alerts[a], turns=by_asset[a],
                                                   episodes=episodes.get(a, []),
                                                   outcomes_through=END, pre=PRE, post=post,
                                                   min_off=MIN_OFF)["turns"]], "top")
    v = np.asarray(shares, dtype=float)
    return {"kind": "top", "near": "high", "post": post, "n_draws": int(n_draws),
            "n_valid_draws": int(len(v)),
            "observed_cluster_share": obs["cluster_share_flagged"],
            "placebo_mean": float(v.mean()) if len(v) else None,
            "placebo_median": float(np.median(v)) if len(v) else None,
            "p90": float(np.quantile(v, 0.9)) if len(v) else None}


def cluster_rows(pv, turns, alerts, episodes) -> tuple[list, dict]:
    """The scorer's own scored top rows and the cluster catch map (summarise's key scheme)."""
    det = pv.score_pivots_multi(turns, alerts, episodes, outcomes_through=END, posts=(POST,),
                                pre=PRE, min_off=MIN_OFF)
    pooled = [r for _a, v in sorted(det["by_post"][f"post{POST}"]["by_asset"].items())
              for r in v["turns"]]
    sc = [r for r in pooled if r["kind"] == "top" and r["status"] == "scored"]
    cl: dict = {}
    for i, r in enumerate(sc):
        key = r.get("cluster_id") or f"__{r.get('asset')}_{r['date']}_{i}"
        r["_key"] = key
        cl[key] = cl.get(key, False) or bool(r["flagged"])
    return sc, cl


def caught(cl: dict) -> set:
    return {k for k, v in cl.items() if v}


def packed(row: dict | None) -> dict:
    if row is None:
        return {}
    return {k: row.get(k) for k in
            ("turns_scored", "turns_flagged", "turn_share", "turn_share_ci90",
             "clusters_scored", "clusters_flagged", "cluster_share", "cluster_share_ci90",
             "median_delay", "censored", "false_per_asset_year", "alert_budget")}


# ------------------------------------------------------------------ the displaced-clock control
def displaced_control(BM, pv, levels, series, A, Rplus, b20s, b20q, turns, episodes, px,
                      cand_row, observed_alert) -> dict:
    """Within each PRE calendar year circularly shift the constructed Rplus; re-form A_R with the
    unchanged price predicates. Keep draws whose windowed ON-day and start counts match the
    observed within one on the engine-calendar fixed support."""
    eng = Rplus.index
    years = {}
    yr = np.asarray(eng.year)
    for y in range(2006, 2020):
        pos = np.flatnonzero(yr == y)
        if len(pos) > 2 * CTRL_EDGE:
            years[y] = pos
    if not years:
        return {"status": "NOT_ESTIMABLE", "reason": "no eligible year blocks"}
    bp = ((pd.Series(b20s) > 0) & (pd.Series(b20q) > 0)).reindex(eng).fillna(False).to_numpy()
    rp = Rplus.reindex(eng).to_numpy(dtype=float)

    sp = int(eng.searchsorted(START))
    lo = max(0, sp - PRE)
    sup = eng[lo:]
    sup = sup[sup <= END]
    obs_a = pd.Series(observed_alert).reindex(sup).fillna(False).to_numpy(dtype=bool)
    obs_on, obs_starts = int(obs_a.sum()), starts_of(obs_a)
    assert sup.max() <= END

    rng = np.random.default_rng(CTRL_SEED)
    n_y = {y: len(pos) for y, pos in years.items()}
    generated, accepted, runs, on_counts = 0, [], [], []
    gen_start_hist: dict[int, int] = {}
    gen_on_hist: dict[int, int] = {}
    acc_run_hist: dict[int, int] = {}
    while generated < CTRL_MAX and len(accepted) < CTRL_KEEP:
        shift = {y: int(rng.integers(CTRL_EDGE, n_y[y] - CTRL_EDGE + 1)) for y in years}
        generated += 1
        shifted = rp.copy()
        for y, pos in years.items():
            shifted[pos] = np.roll(rp[pos], shift[y])
        a2 = pd.Series((shifted >= 0.90) & bp, index=eng, dtype=bool)
        full = a2.shift(1, fill_value=False)
        av = full.reindex(sup).to_numpy(dtype=bool)
        n_on, n_st = int(av.sum()), starts_of(av)
        gen_start_hist[n_st] = gen_start_hist.get(n_st, 0) + 1
        gen_on_hist[n_on] = gen_on_hist.get(n_on, 0) + 1
        if abs(n_on - obs_on) > 1 or abs(n_st - obs_starts) > 1:
            continue
        accepted.append(full.astype(bool))
        runs.append(n_st)
        on_counts.append(n_on)
        for ln in _run_lengths(av)["lengths"]:
            acc_run_hist[int(ln)] = acc_run_hist.get(int(ln), 0) + 1

    would_score = len(accepted)
    shares, falses = [], []
    if accepted:
        _G.update(BM=BM, turns=turns, episodes=episodes, px=px, levels=levels, series=series)
        items = list(enumerate(accepted))
        chunk = 25
        chunks = [items[i:i + chunk] for i in range(0, len(items), chunk)]
        with ProcessPoolExecutor(max_workers=min(NPROC, len(chunks))) as ex:
            for res in ex.map(_ctrl_chunk, chunks):
                for _i, cs, fp in res:
                    if cs is not None:
                        shares.append(cs)
                    if fp is not None:
                        falses.append(fp)
    s = np.asarray(shares, dtype=float)
    f = np.asarray(falses, dtype=float)
    est = would_score >= CTRL_KEEP
    dcatch = float(cand_row["cluster_share"]) - s if len(s) else np.array([])
    dfalse = float(cand_row["false_per_asset_year"]) - f if len(f) else np.array([])
    return {
        "status": "ESTIMABLE" if est else "NOT_ESTIMABLE",
        "reason": None if est else f"only {would_score} qualifying draws in {generated} "
                                   f"offset vectors (need {CTRL_KEEP})",
        "seed": CTRL_SEED, "offset_vectors_generated": int(generated),
        "draws_generated": int(generated), "draws_accepted": int(would_score),
        "draws_required": CTRL_KEEP, "max_offset_vectors": CTRL_MAX,
        "shift_bounds_per_year": {int(y): [CTRL_EDGE, int(n_y[y] - CTRL_EDGE)] for y in years},
        "acceptance_rate": round(would_score / generated, 6) if generated else None,
        "observed_on_days": obs_on, "observed_starts": obs_starts,
        "observed_run_lengths": _run_lengths(obs_a),
        "count_matching": {
            "observed_on_days": obs_on, "observed_starts": obs_starts,
            "tolerance": 1,
            "generated_start_count_histogram": {int(k): int(v) for k, v in
                                                sorted(gen_start_hist.items())},
            "generated_on_day_histogram": {int(k): int(v) for k, v in
                                           sorted(gen_on_hist.items())},
            "accepted_run_length_histogram": {int(k): int(v) for k, v in
                                              sorted(acc_run_hist.items())},
            "accepted_on_day_range": [int(min(on_counts)), int(max(on_counts))]
            if on_counts else None,
            "accepted_start_range": [int(min(runs)), int(max(runs))] if runs else None,
        },
        "displaced_starts": {"min": int(min(runs)) if runs else None,
                             "median": float(np.median(runs)) if runs else None,
                             "max": int(max(runs)) if runs else None,
                             "mean": float(np.mean(runs)) if runs else None},
        "displaced_on_days": {"min": int(min(on_counts)) if on_counts else None,
                              "max": int(max(on_counts)) if on_counts else None},
        "catch_share_observed": cand_row["cluster_share"],
        "catch_share_displaced_mean": float(s.mean()) if len(s) else None,
        "catch_share_displaced_median": float(np.median(s)) if len(s) else None,
        "catch_difference_p10": float(np.quantile(dcatch, 0.10)) if len(dcatch) else None,
        "catch_difference_p50": float(np.quantile(dcatch, 0.50)) if len(dcatch) else None,
        "false_rate_observed": cand_row["false_per_asset_year"],
        "false_rate_displaced_mean": float(f.mean()) if len(f) else None,
        "false_rate_displaced_median": float(np.median(f)) if len(f) else None,
        "false_difference_p90": float(np.quantile(dfalse, 0.90)) if len(dfalse) else None,
        "false_difference_p50": float(np.quantile(dfalse, 0.50)) if len(dfalse) else None,
        "n_scored_draws": int(len(s)),
        "note": "description line, not a gate on this read",
    }


def _run_lengths(a: np.ndarray) -> dict:
    runs, i, n = [], 0, len(a)
    while i < n:
        if a[i]:
            j = i
            while j + 1 < n and a[j + 1]:
                j += 1
            runs.append(j - i + 1)
            i = j + 1
        else:
            i += 1
    if not runs:
        return {"n": 0, "lengths": [], "median": None, "max": None}
    return {"n": len(runs), "lengths": runs,
            "median": float(np.median(runs)), "max": int(max(runs))}


# ------------------------------------------------------------------ fragmentation diagnostic
def fragmentation(j: pd.Series, a_dec: pd.Series, b20s: pd.Series, b20q: pd.Series,
                  sc_rows: list, alerts: dict, episodes: dict, pv) -> dict:
    """First start per parent shock episode (J = qR>=.90 AND dy5>0), evaluated against the same
    top windows and episode exemptions; the daily candidate stays frozen."""
    eng = j.index
    jv = j.reindex(eng).fillna(False).to_numpy(dtype=bool)
    # parent episodes: maximal contiguous ON runs of J
    eps = []
    i, n = 0, len(jv)
    while i < n:
        if jv[i]:
            k = i
            while k + 1 < n and jv[k + 1]:
                k += 1
            eps.append((i, k))
            i = k + 1
        else:
            i += 1
    ep_of = np.full(n, -1, dtype=int)
    for eid, (s, e) in enumerate(eps):
        ep_of[s:e + 1] = eid
    jpos = np.flatnonzero(jv)

    # candidate ON starts at decision time within the scored support
    dec = a_dec.reindex(eng).fillna(False).to_numpy(dtype=bool)
    sp = int(eng.searchsorted(START))
    lo = max(0, sp - PRE)
    decision_lo = int(eng.searchsorted(eng[lo]))
    sup_end = int(np.searchsorted(eng.values, np.datetime64(END), side="right"))
    starts = [p for p in np.flatnonzero(dec)
              if p >= decision_lo and p < sup_end
              and (p == 0 or not dec[p - 1])]
    assigned, unassigned = {}, []
    for p in starts:
        win = jpos[(jpos >= p - 5) & (jpos <= p - 1)]
        if len(win) == 0:
            unassigned.append(p)
        else:
            assigned.setdefault(int(ep_of[win[-1]]), []).append(p)
    retained_dec, removed = [], 0
    for eid in sorted(assigned):
        ps = assigned[eid]
        retained_dec.append(ps[0])
        removed += len(ps) - 1
    retained_dec += unassigned
    retained_dec = sorted(retained_dec)
    # published date = next engine session (the t+1 shift)
    retained_pub = []
    for p in retained_dec:
        if p + 1 < len(eng):
            retained_pub.append(eng[p + 1])

    # evaluate the retained start list against the same top windows and episode exemptions
    caught_keys, false_total, used_positions = set(), 0, set()
    yrs = 0.0
    per_asset = {}
    for asset, al in alerts.items():
        idx = al.index
        pos = [int(idx.searchsorted(d)) for d in retained_pub]
        pos = [q for q in pos if 0 <= q < len(idx)]
        # scorer top positions
        tops = [(r, int(idx.searchsorted(pd.Timestamp(r["date"])))) for r in sc_rows
                if r["asset"] == asset and r["kind"] == "top" and r["status"] == "scored"]
        used = set()
        for r, p in tops:
            if not (0 <= p < len(idx)):
                continue
            hit = [c for c in pos if p - PRE <= c <= p + POST]
            if hit:
                used.update(hit)
                caught_keys.add(r["_key"])
        spans = episodes.get(asset, [])
        fcount = 0
        for c in pos:
            if c in used:
                continue
            d = idx[c]
            in_ep = any((e.onset is not None and e.onset <= d
                         and (e.recovery if e.recovery is not None else idx.max()) >= d)
                        for e in spans)
            if not in_ep:
                fcount += 1
        false_total += fcount
        yrs += len(idx) / pv.SESSIONS_PER_YEAR
        per_asset[asset] = {"starts": len(pos), "false": fcount}
    n_clusters = len({r["_key"] for r in sc_rows
                      if r["kind"] == "top" and r["status"] == "scored"})
    catch = len(caught_keys) / n_clusters if n_clusters else None
    false_rate = false_total / yrs if yrs else None

    # pre-shock equity-break: was either price predicate already ON in the 5 sessions before?
    pre_break = []
    for eid, (s0, _e0) in enumerate(eps):
        if not (eng[s0] >= START and eng[s0] <= END):
            continue
        w = [p for p in range(max(0, s0 - 5), s0)]
        sp_b = bool(any(b20s.reindex(eng[[p]]).iloc[0] > 0 for p in w))
        qq_b = bool(any(b20q.reindex(eng[[p]]).iloc[0] > 0 for p in w))
        pre_break.append({"episode": eid, "episode_start": str(eng[s0].date()),
                          "B20_SPY_already": sp_b, "B20_QQQ_already": qq_b,
                          "either_already": bool(sp_b or qq_b)})
    return {
        "n_parent_episodes": len(eps),
        "n_parent_episodes_in_window": len(pre_break),
        "n_candidate_decision_starts": len(starts),
        "n_retained_starts": len(retained_dec),
        "n_removed_fragmented_starts": int(removed),
        "n_unassigned_starts": len(unassigned),
        "retained_first_starts": [str(eng[p].date()) for p in retained_dec],
        "cluster_share_retained": catch,
        "false_per_asset_year_retained": false_rate,
        "n_clusters": n_clusters,
        "per_asset": per_asset,
        "pre_shock_equity_break": {
            "n_episodes": len(pre_break),
            "n_either_already": sum(1 for r in pre_break if r["either_already"]),
            "n_spy_already": sum(1 for r in pre_break if r["B20_SPY_already"]),
            "n_qqq_already": sum(1 for r in pre_break if r["B20_QQQ_already"]),
            "episodes": pre_break,
        },
        "note": "retained event list only; the daily candidate remains frozen",
    }


# ------------------------------------------------------------------ one full block
def run_block(tag: str, qR: pd.Series, dy5: pd.Series, b20s: pd.Series, b20q: pd.Series,
              ctx: dict, A, BM, pv, levels: dict, series: list, turns: list,
              episodes: dict, levels_all: dict) -> dict:
    t0 = time.time()
    b20s = b20s.reindex(qR.index)
    b20q = b20q.reindex(qR.index)
    bp = ((b20s > 0) & (b20q > 0)).fillna(False)
    rule = build_rule(qR, dy5, bp.to_numpy(), b20s, b20q)
    log(f"[{tag}] rule built: Rplus undefined {rule['n_rplus_undefined']}, "
        f"A_R ON days {int(rule['A'].sum())}")

    alert_full = rule["A"].shift(1, fill_value=False).astype(bool)
    alerts = window_alert(alert_full, levels, series)
    px = {a: levels_all[a].reindex(alerts[a].index) for a in series}

    # canonical engine-calendar window (fixed full support for the control match)
    eng = qR.index
    sp = int(eng.searchsorted(START))
    lo = max(0, sp - PRE)
    canon = pd.Series(alert_full).reindex(eng[lo:])
    canon = canon[canon.index <= END].astype(bool)

    _G.update(BM=BM, turns=turns, episodes=episodes, px=px)
    cand = _score_job(alerts)
    log(f"[{tag}] candidate share {cand['cluster_share']} false "
        f"{cand['false_per_asset_year']} ({time.time()-t0:.1f}s)")

    refs = {f: BM.reference_result(ctx, alerts, form=f, post=POST, n_draws=N_DRAWS,
                                   seed=SEED, tol=TOL, include_passes=False,
                                   start_d=START, end_d=END) for f in ("dd", "near")}
    bm = BM.better_reference(refs["dd"], refs["near"])
    bm_form = bm["match"]["form"]

    t_p = time.time()
    p90 = parallel_p90(BM, pv, turns, alerts, episodes, px, post=POST)
    ref50 = BM.cluster_placebo_p90(turns, alerts, episodes, px, kind="top",
                                   outcomes_through=END, n_draws=50, seed=SEED, tol=TOL,
                                   pre=PRE, post=POST, min_off=MIN_OFF)
    par50 = parallel_p90(BM, pv, turns, alerts, episodes, px, post=POST, n_draws=50)
    eq = (ref50["p90"] == par50["p90"] and ref50["n_valid_draws"] == par50["n_valid_draws"]
          and ref50["observed_cluster_share"] == par50["observed_cluster_share"])
    if not eq:
        raise SystemExit(f"[{tag}] parallel p90 disagrees with bm_ref at 50 draws")
    p90["_runtime_s"] = round(time.time() - t_p, 1)
    p90["_equivalence_50_draws"] = {"matches_bm_ref": True, "p90": ref50["p90"],
                                    "n_valid_draws": ref50["n_valid_draws"]}
    log(f"[{tag}] p90 {p90['p90']} observed {p90['observed_cluster_share']} "
        f"({p90['_runtime_s']}s)")

    # ---- rule 2b: every part matched to this candidate's realised alert share
    target = pooled_share(alerts)
    score_full = {"Rplus": rule["Rplus"], "Q5": rule["Q5"], "D5": rule["D5"],
                  "B20_SPY": rule["B20_SPY"], "B20_QQQ": rule["B20_QQQ"],
                  "response_only": rule["response_only"]}
    matched, part_rows = {}, {}
    for name in PARTS + ADVERSARIES:
        sc = window_score(score_full[name].shift(1), levels, series)
        m = BM.part_at_matched_share(sc, target, start_d=START, end_d=END,
                                     higher_is_alert=True)
        thr = m["threshold"]
        part_alerts = {}
        for a, s in sc.items():
            part_alerts[a] = (s >= thr).fillna(False).astype(bool)
            own = m["alerts"].get(a)
            if own is not None:
                assert bool((part_alerts[a].reindex(own.index) == own).all()), (name, a)
            assert part_alerts[a].index.max() <= END
        n_sess = sum(len(s) for s in sc.values())
        n_nonfin = sum(int(pd.Series(s).isna().sum()) for s in sc.values())
        matched[name] = {"threshold": thr, "target_share": m["target_share"],
                         "achieved_share_finite_sessions": m["achieved_share"],
                         "achieved_share_all_sessions": pooled_share(part_alerts),
                         "n_observations": m["n_observations"],
                         "n_window_sessions": n_sess, "n_nonfinite_sessions": n_nonfin,
                         "alerts": part_alerts}
    log(f"[{tag}] target share {target:.6f}; scoring {len(PARTS)+len(ADVERSARIES)} matched "
        f"parts")
    ppx = {a: levels_all[a].reindex(alerts[a].index) for a in series}
    with ProcessPoolExecutor(max_workers=min(NPROC, len(PARTS) + len(ADVERSARIES))) as ex:
        futs = {ex.submit(_score_job, matched[name]["alerts"]): name
                for name in PARTS + ADVERSARIES}
        for fut, name in futs.items():
            part_rows[name] = fut.result()
    verdict = BM.set_level_pass_matched(cand, bm, p90["p90"],
                                        [part_rows[n] for n in PARTS])
    log(f"[{tag}] rule 2b verdict {json.dumps(verdict)} (DESCRIPTION; nomination forced False)")

    # ---- cluster ids and the paired tables
    sc_rows, cl = cluster_rows(pv, turns, alerts, episodes)
    assert len(cl) == cand["clusters_scored"], (len(cl), cand["clusters_scored"])
    cand_catch = caught(cl)
    for name in PARTS + ADVERSARIES:
        _, clx = cluster_rows(pv, turns, matched[name]["alerts"], episodes)
        part_rows[name]["caught_cluster_ids"] = sorted(caught(clx))

    native = None
    if tag == "dfii10":
        native_alert = (qR >= 0.90).fillna(False).astype(bool).shift(1, fill_value=False)
        nalerts = window_alert(native_alert, levels, series)
        _, ncl = cluster_rows(pv, turns, nalerts, episodes)
        native_catch = caught(ncl)
        native = {
            "recorded_aggregate": ".795 / 4.97 (not re-read)",
            "n_caught_clusters": len(native_catch),
            "n_clusters": len(ncl),
            "retained_by_candidate": sorted(cand_catch & native_catch),
            "lost_by_candidate": sorted(native_catch - cand_catch),
            "new_by_candidate": sorted(cand_catch - native_catch),
            "counts": {"native": len(native_catch), "candidate": len(cand_catch),
                       "retained": len(cand_catch & native_catch),
                       "lost": len(native_catch - cand_catch),
                       "new": len(cand_catch - native_catch)},
        }

    ctrl = displaced_control(BM, pv, levels, series, rule["A"], rule["Rplus"],
                             rule["B20_SPY"], rule["B20_QQQ"], turns, episodes, px,
                             cand, canon)
    log(f"[{tag}] control {ctrl['status']}: generated {ctrl['draws_generated']}, "
        f"accepted {ctrl['draws_accepted']}; catch p10 {ctrl['catch_difference_p10']} "
        f"false p90 {ctrl['false_difference_p90']}")

    frag = fragmentation((qR >= 0.90) & (dy5 > 0), rule["A"], rule["B20_SPY"],
                         rule["B20_QQQ"], sc_rows, alerts, episodes, pv)
    log(f"[{tag}] fragmentation: {frag['n_candidate_decision_starts']} starts -> "
        f"{frag['n_retained_starts']} retained; catch {frag['cluster_share_retained']} "
        f"false {frag['false_per_asset_year_retained']}")

    return {
        "tag": tag,
        "label": "DESCRIPTION only; never a nomination; one set read in the chance account",
        "candidate": {**packed(cand), "caught_cluster_ids": sorted(cand_catch)},
        "p90": p90,
        "references": {f: packed(refs[f]) for f in refs},
        "reference_match": {f: {"x": refs[f]["match"]["x"],
                                "achieved_share": refs[f]["match"]["achieved_share"],
                                "target_budget": refs[f]["match"]["target_budget"]}
                            for f in refs},
        "better_reference": bm_form,
        "alert_share_pooled": target,
        "alert_share_by_year": share_by_year(pd.Series(alert_full)),
        "on_starts_canonical": starts_of(canon.to_numpy(dtype=bool)),
        "on_days_canonical": int(canon.sum()),
        "rule_2b": {
            "target_alert_share": target,
            "parts": {n: {k: matched[n][k] for k in
                          ("threshold", "target_share", "achieved_share_finite_sessions",
                           "achieved_share_all_sessions", "n_observations",
                           "n_window_sessions", "n_nonfinite_sessions")}
                      for n in PARTS + ADVERSARIES},
            "rows": {n: {**packed(part_rows[n]),
                         "caught_cluster_ids": part_rows[n]["caught_cluster_ids"]}
                     for n in PARTS + ADVERSARIES},
            "verdict_mandatory_parts": verdict,
            "nomination": False,
            "nomination_note": "forced False: fixed rule read as a description after earlier "
                               "reads; never a nomination",
        },
        "diagnosis": {
            "sign_gate_Rplus_vs_Q5": _cmp(part_rows["Rplus"], part_rows["Q5"], cand),
            "response_condition_A_R_vs_Rplus": _cmp(cand, part_rows["Rplus"], None),
            "A_R_vs_response_only": _cmp(cand, part_rows["response_only"], None),
            "rows": {"A_R": packed(cand), "Rplus": packed(part_rows["Rplus"]),
                     "Q5": packed(part_rows["Q5"]), "D5": packed(part_rows["D5"]),
                     "response_only": packed(part_rows["response_only"])},
        },
        "native_leg": native,
        "control": ctrl,
        "fragmentation": frag,
        "runtime_s": round(time.time() - t0, 1),
    }


def _cmp(candidate: dict, other: dict, _cand: dict | None) -> dict:
    """Is the false rate lower, and how does catch compare (both at equal alert share)?"""
    cf, of = candidate["false_per_asset_year"], other["false_per_asset_year"]
    cc, oc = candidate["cluster_share"], other["cluster_share"]
    return {"candidate_cluster_share": cc, "other_cluster_share": oc,
            "candidate_false": cf, "other_false": of,
            "false_lower": bool(cf is not None and of is not None and cf < of),
            "catch_higher": bool(cc is not None and oc is not None and cc > oc),
            "catch_delta": None if cc is None or oc is None else round(cc - oc, 4),
            "false_delta": None if cf is None or of is None else round(cf - of, 4)}


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=os.environ.get("ROTATION_DESK"))
    ns = ap.parse_args()
    if not ns.desk:
        raise SystemExit("desk path required: --desk <path> or ROTATION_DESK")
    desk = Path(ns.desk).resolve()

    RUN_LOG.write_text("")
    log("# Risk Radar BT1-RATE-RESPONSE on PRE (description only) + DGS10 substitute line")
    log(f"# dry={DRY} p90 draws={N_DRAWS} control keeps={CTRL_KEEP} "
        f"window={START.date()}..{END.date()} procs={NPROC}")
    p_start = check_pins(desk, "start")
    rows = check_rows(desk)
    t_all = time.time()

    log("phase 1: rate legs (DFII10 via pit_signals; DGS10 next-business-day rule)")
    rate = build_rate_inputs()

    log("phase 2: desk kit")
    A, BM, pv, pv_path = load_desk_kit(desk)
    log(f"# scorer module: {str(pv_path).replace(str(desk), '<desk>')}")
    assert str(pv_path).startswith(str(desk))

    ctx = BM.build_context("R-off", "top", start_d=START, end_d=END)
    series, turns, levels, episodes = ctx["series"], ctx["turns"], ctx["levels"], ctx["episodes"]
    log(f"# series {len(series)}; turns {len(turns)}")

    # --- date guard: inputs and scored turns
    def date_guard() -> dict:
        worst = {"turns": max(pd.Timestamp(t.date) for t in turns),
                 "levels": max(s.index.max() for s in levels.values()),
                 "outcomes_through": END,
                 "engine_calendar_used": rate["idx"][rate["idx"] <= END].max()}
        ep = []
        for eps in episodes.values():
            for e in eps:
                ep += [d for d in (e.peak, e.onset, e.trough, e.recovery) if d is not None]
        worst["episodes"] = max(pd.Timestamp(d) for d in ep)
        ok = all(pd.Timestamp(v) <= END for v in worst.values())
        if not ok:
            raise SystemExit(f"DATE GUARD FAILED: {worst}")
        tmin = min(pd.Timestamp(t.date) for t in turns)
        if tmin < START:
            raise SystemExit(f"SCORED TURN BEFORE 2006-01-03: {tmin}")
        return {"all_le_2019_12_31": True,
                "all_scored_turns_ge_2006_01_03": True,
                "min_scored_turn": str(tmin.date()),
                "max": {k: str(pd.Timestamp(v).date()) for k, v in worst.items()}}

    guard = date_guard()
    log(f"# date guard ok: {json.dumps(guard['max'])}; min scored turn "
        f"{guard['min_scored_turn']}")

    # --- desk level series for the price predicates (adjusted closes, truncated at END)
    spy = levels["SPY"]
    qqq = levels["QQQ"]
    log(f"# desk levels SPY {spy.index.min().date()}..{spy.index.max().date()}; "
        f"QQQ {qqq.index.min().date()}..{qqq.index.max().date()}")
    align = rate["idx"].intersection(spy.index)
    log(f"# engine calendar vs desk SPY: {len(align)} common sessions "
        f"(engine {len(rate['idx'])}, desk {len(spy)})")
    b20s = b20(spy).reindex(rate["idx"]).ffill()
    b20q = b20(qqq).reindex(rate["idx"]).ffill()
    # never carry a post-window input into the rule
    b20s = b20s[b20s.index <= END]
    b20q = b20q[b20q.index <= END]
    if b20s.index.max() > END or b20q.index.max() > END:
        raise SystemExit("price predicate extends past 2019-12-31; STOP")
    if b20s.isna().all() or b20q.isna().all():
        raise SystemExit("empty price predicate; STOP")

    idx = rate["idx"][rate["idx"] <= END]

    def clip(s):
        return pd.Series(s).reindex(idx)

    blocks = {}
    for tag, qk, dk in (("dfii10", "q_dfii", "dy_dfii"), ("dgs10", "q_dgs", "dy_dgs")):
        q = clip(rate[qk])
        d = clip(rate[dk])
        if q.index.max() > END or d.index.max() > END:
            raise SystemExit(f"[{tag}] rate input past 2019-12-31; STOP")
        blocks[tag] = run_block(tag, q, d, b20s, b20q, ctx, A, BM, pv, levels, series,
                                turns, episodes, levels)

    # --- cluster-id overlap between the two candidates
    a_catch = set(blocks["dfii10"]["candidate"]["caught_cluster_ids"])
    b_catch = set(blocks["dgs10"]["candidate"]["caught_cluster_ids"])
    overlap = {"n_dfii10": len(a_catch), "n_dgs10": len(b_catch),
               "both": sorted(a_catch & b_catch), "only_dfii10": sorted(a_catch - b_catch),
               "only_dgs10": sorted(b_catch - a_catch),
               "counts": {"both": len(a_catch & b_catch), "only_dfii10": len(a_catch - b_catch),
                          "only_dgs10": len(b_catch - a_catch)}}
    log(f"# candidate cluster-id overlap: {json.dumps(overlap['counts'])}")

    p_end = check_pins(desk, "end")
    result = {
        "runs": [
            {"id": ID_RATE, "spec_sha256": rows[ID_RATE], "role": "DESCRIPTION only",
             "family": "R-off", "direction": "top", "post": POST},
            {"id": ID_DGS, "spec_sha256": rows[ID_DGS],
             "role": "DESCRIPTION only (DGS10 substitute line)"},
        ],
        "pins": {"start": p_start, "end": p_end},
        "scorer_module": str(pv_path).replace(str(desk), "<desk>"),
        "window": {"start": str(START.date()), "end": str(END.date()), "pre": PRE,
                   "post": POST, "n_draws": N_DRAWS, "seed": SEED, "tol": TOL,
                   "min_off": MIN_OFF, "control_seed": CTRL_SEED,
                   "control_keep": CTRL_KEEP, "control_max": CTRL_MAX, "dry": DRY},
        "rate_rules": {"dfii10": rate["dfii10_rule"], "dgs10": rate["dgs10_rule"]},
        "date_guard": guard,
        "dfii10": blocks["dfii10"],
        "dgs10": blocks["dgs10"],
        "cluster_overlap_dfii10_vs_dgs10": overlap,
        "deviations": DEVIATIONS,
        "runtime_s": None,
    }
    result["runtime_s"] = round(time.time() - t_all, 1)

    write_summary(result)
    (HERE / "result.json").write_text(json.dumps(result, indent=1, default=str))
    log(f"# total runtime {result['runtime_s']}s")
    log(f"# pins match at start and end: "
        f"{p_start == p_end == {'bm_ref.py': PIN_BM, 'adapter.py': PIN_AD}}")


DEVIATIONS = [
    "The two rate legs: DFII10 qR is the engine's own pit_signals('rates_realrate') series; "
    "dy5 is the same PIT replay's DFII10.diff(5) (released observations only, ffilled onto the "
    "engine sessions), verified to reproduce qR to 1e-12 on 2004+ replay vs the engine leg.",
    "The PIT helper has no DGS10 rule: availability.release_dates accepts DEXJPUS / DFII10 / "
    "BAMLH0A0HYM2 only, and FRED_FIRST_RELEASE_DATES_v1.csv contains no DGS10 rows. The DGS10 "
    "line therefore uses the DFII10 branch's documented rule verbatim: observation t is usable "
    "from the next business day (US federal holiday calendar), with the same trailing-504 "
    "pct_rank_window of diff(5) applied to released observations only.",
    "Price predicates: B20 is computed on the desk level series (bm_ref.level_series of the "
    "catalogue specs SPY and QQQ, adjusted closes truncated at 2019-12-31), reindexed onto the "
    "engine SPY-session calendar with ffill so the three operands share one clock.",
    "Market-level alert broadcast: A_R is one series built on the engine calendar, shifted t+1 "
    "on the full series, then reindexed onto every panel series with ffill (the k3 follow-up "
    "convention).",
    "Rplus validity: an observation is valid when qR and dy5 are both present at s; Rplus is 0 "
    "when all five are valid and none has dy5>0, and undefined (NaN, not alerting) otherwise.",
    "Parts at matched share follow the rev1 shift order: the t+1 shift is applied to the full "
    "part score series and the window taken afterwards; part_at_matched_share then takes one "
    "pooled threshold per part. For scoring, each part's alert is rebuilt on the full windowed "
    "index with a non-finite session counting as not alerting (asserted equal to the function's "
    "own alert where both are defined).",
    "Criterion (c) uses the four mandatory parts (Rplus, B20_SPY, B20_QQQ, response-only "
    "min(B20_SPY,B20_QQQ)); Q5 and D5 are reported as adversaries in the diagnosis table and "
    "are not part of the pass call.",
    "Displaced-clock control: one market-level Rplus exists, so each year's single drawn shift "
    "is trivially the same for every target asset; the price predicates are unchanged.",
    "Displaced-clock control: the ON-day/start-count match is evaluated on the engine-calendar "
    "windowed candidate alert (the fixed scored support), not on the pooled 21-series panel "
    "support; the two differ only by ffill edge sessions. Rplus outside PRE years 2006-2019 is "
    "left genuine (only PRE calendar years are circularly shifted), so the first sessions of "
    "2006 can read unshifted 2005 values; declared, not smoothed.",
    "Displaced-clock control: a draw is scored only after the within-one count filter; catch "
    "differences are observed cluster share minus displaced, false differences observed "
    "false/asset-yr minus displaced. Fewer than 2,000 qualifying draws = NOT_ESTIMABLE.",
    "Fragmentation: starts are taken from the unshifted decision series A_R inside the scored "
    "support, assigned to the parent J episode containing the most recent qualifying session in "
    "t-5..t-1, first start per episode retained at its original published (t+1) date, "
    "unassigned starts retained. The retained list is evaluated against the same top windows "
    "and episode exemptions; no daily alert array is rebuilt.",
    "Native comparator cluster ids come from a scoring call on the same window; its aggregate is "
    "reported only as the recorded .795 / 4.97 and is NOT re-read or re-verdict.",
    "Both blocks are DESCRIPTION only: nomination is forced False regardless of any figure.",
]


def write_summary(r: dict) -> None:
    def f(v, nd=3):
        return "—" if v is None else f"{v:.{nd}f}"

    def ci(v):
        return "—" if not v else f"[{v[0]:.3f}, {v[1]:.3f}]"

    L = []
    L.append("# Risk Radar BT1-RATE-RESPONSE on PRE — description only\n")
    L.append(f"Window {START.date()}..{END.date()}, pre {PRE}, post {POST}, seed {SEED}, "
             f"{N_DRAWS} draws, tol {TOL}, min_off {MIN_OFF}; control seed {CTRL_SEED}, "
             f"{CTRL_KEEP} accepted draws. bm_ref rev1 pin."
             + ("  **DRY RUN.**" if DRY else "") + "\n")
    L.append("**Nothing is tuned.** The rule is frozen as written in BREAKTHROUGH_1_ANSWER.md "
             "and repeated in ledger rows `" + ID_RATE + "` / `" + ID_DGS + "`. Both are "
             "DESCRIPTION only, never a nomination.\n")
    L.append("## Pins and rows\n")
    L.append(f"- `bm_ref.py` `{r['pins']['start']['bm_ref.py']}` (end `{r['pins']['end']['bm_ref.py']}`)")
    L.append(f"- `adapter.py` `{r['pins']['start']['adapter.py']}` (end `{r['pins']['end']['adapter.py']}`)")
    L.append(f"- `{ID_RATE}` spec `{r['runs'][0]['spec_sha256']}`")
    L.append(f"- `{ID_DGS}` spec `{r['runs'][1]['spec_sha256']}`")
    L.append(f"- scorer `{r['scorer_module']}`\n")
    L.append("## Date guard\n")
    L.append("Every turn, alert, level, episode and `outcomes_through` date is ≤ 2019-12-31; "
             "every scored turn is ≥ 2006-01-03 (asserted).\n")
    L.append("| surface | max date |")
    L.append("|---|---|")
    for k, v in r["date_guard"]["max"].items():
        L.append(f"| {k} | {v} |")
    L.append(f"\nMin scored turn: {r['date_guard']['min_scored_turn']}.\n")

    for key, title in (("dfii10", "DFII10 (the frozen rule)"),
                       ("dgs10", "DGS10 substitute line (description)")):
        b = r[key]
        c = b["candidate"]
        L.append(f"## {title}\n")
        L.append("| metric | value |")
        L.append("|---|---|")
        L.append(f"| cluster share | {f(c['cluster_share'])} |")
        L.append(f"| 90% CI | {ci(c['cluster_share_ci90'])} |")
        L.append(f"| false/asset-yr | {f(c['false_per_asset_year'])} |")
        L.append(f"| median delay | {f(c['median_delay'], 1)} |")
        L.append(f"| alert share (pooled) | {f(b['alert_share_pooled'])} |")
        L.append(f"| ON days / ON starts (window) | {b['on_days_canonical']} / "
                 f"{b['on_starts_canonical']} |")
        L.append(f"| turns scored / flagged | {c['turns_scored']} / {c['turns_flagged']} |")
        L.append(f"| clusters / flagged | {c['clusters_scored']} / {c['clusters_flagged']} |")
        L.append(f"| placebo p90 (cluster) | {f(b['p90']['p90'])} |")
        for form in ("dd", "near"):
            rr_ = b["references"][form]
            mark = " **(better)**" if form == b["better_reference"] else ""
            L.append(f"| ref {form}{mark} share / false | {f(rr_['cluster_share'])} / "
                     f"{f(rr_['false_per_asset_year'])} |")
        L.append("")
        L.append("Alert share by year: "
                 + ", ".join(f"{y} {v:.4f}"
                             for y, v in sorted(b["alert_share_by_year"].items())))
        L.append("")
        L.append("### Rule 2b — parts at the candidate's realised share\n")
        L.append("| part | threshold | achieved (finite) | achieved (all) | non-finite | "
                 "cluster share | false/asset-yr |")
        L.append("|---|---|---|---|---|---|---|")
        for n in PARTS + ADVERSARIES:
            p = b["rule_2b"]["parts"][n]
            rw = b["rule_2b"]["rows"][n]
            L.append(f"| {n} | {p['threshold']:.6f} | "
                     f"{p['achieved_share_finite_sessions']:.6f} | "
                     f"{p['achieved_share_all_sessions']:.6f} | "
                     f"{p['n_nonfinite_sessions']}/{p['n_window_sessions']} | "
                     f"{f(rw['cluster_share'])} | {f(rw['false_per_asset_year'])} |")
        v = b["rule_2b"]["verdict_mandatory_parts"]
        L.append("")
        L.append(f"**a/b/c:** a={v['a']}, b={v['b']}, c={v['c']}; "
                 f"criteria_met={v['criteria_met']}; parts_checked={v['parts_checked']}. "
                 f"**DESCRIPTION — nomination False (forced).**\n")
        L.append("### Principal's diagnosis (equal alert share)\n")
        L.append("| comparison | candidate share / false | other share / false | false lower? "
                 "| catch higher? |")
        L.append("|---|---|---|---|---|")
        dg = b["diagnosis"]
        for name, key in (("sign gate: Rplus vs Q5", "sign_gate_Rplus_vs_Q5"),
                          ("response: A_R vs Rplus", "response_condition_A_R_vs_Rplus"),
                          ("A_R vs response-only", "A_R_vs_response_only")):
            d = dg[key]
            L.append(f"| {name} | {f(d['candidate_cluster_share'])} / "
                     f"{f(d['candidate_false'])} | {f(d['other_cluster_share'])} / "
                     f"{f(d['other_false'])} | {d['false_lower']} | {d['catch_higher']} |")
        L.append("")
        if "native_leg" in b and b["native_leg"]:
            nl = b["native_leg"]
            L.append("### Native comparator (rates_realrate at .90) — recorded aggregate only\n")
            L.append(f"Recorded aggregate `.795 / 4.97` (not re-read). Cluster ids on this "
                     f"window are used only for the paired table.\n")
            L.append("| set | clusters caught |")
            L.append("|---|---|")
            L.append(f"| native rate leg | {nl['counts']['native']} |")
            L.append(f"| candidate A_R | {nl['counts']['candidate']} |")
            L.append(f"| retained by A_R | {nl['counts']['retained']} |")
            L.append(f"| lost by A_R | {nl['counts']['lost']} |")
            L.append(f"| newly caught by A_R | {nl['counts']['new']} |")
            L.append("")
        ct = b["control"]
        L.append("### Displaced-clock control (description line)\n")
        L.append(f"Status **{ct['status']}**; seed {ct['seed']}, "
                 f"{ct['draws_generated']} offset vectors generated (max "
                 f"{ct['max_offset_vectors']}), {ct['draws_accepted']} accepted "
                 f"(required {ct['draws_required']}).\n")
        L.append(f"- observed ON days / starts: {ct['observed_on_days']} / "
                 f"{ct['observed_starts']}")
        L.append(f"- catch difference p10 / p50: {f(ct['catch_difference_p10'])} / "
                 f"{f(ct['catch_difference_p50'])}")
        L.append(f"- false-rate difference p50 / p90: {f(ct['false_difference_p50'])} / "
                 f"{f(ct['false_difference_p90'])}")
        L.append(f"- displaced catch median {f(ct['catch_share_displaced_median'])}, "
                 f"false median {f(ct['false_rate_displaced_median'])}")
        L.append(f"- observed run lengths: {ct['observed_run_lengths']['n']} runs, "
                 f"median {f(ct['observed_run_lengths']['median'], 1)}, "
                 f"max {ct['observed_run_lengths']['max']}; displaced starts median "
                 f"{f(ct['displaced_starts']['median'], 1)}, max "
                 f"{ct['displaced_starts']['max']}")
        cm = ct["count_matching"]
        L.append(f"- count-matching (observed {cm['observed_on_days']} ON days / "
                 f"{cm['observed_starts']} starts, tolerance ±{cm['tolerance']}): accepted "
                 f"ON-day range {cm['accepted_on_day_range']}, start range "
                 f"{cm['accepted_start_range']}; acceptance "
                 f"{ct['draws_accepted']}/{ct['draws_generated']} = "
                 f"{f(ct['acceptance_rate'], 4)}")
        L.append("- accepted run-length histogram (length: runs across accepted draws): "
                 + (", ".join(f"{k}: {v}"
                              for k, v in cm["accepted_run_length_histogram"].items())
                    or "—") + "\n")
        fr = b["fragmentation"]
        L.append("### Fragmentation diagnostic (first start per shock episode)\n")
        L.append(f"- parent shock episodes (J = qR≥.90 AND dy5>0): "
                 f"{fr['n_parent_episodes']} ({fr['n_parent_episodes_in_window']} in window)")
        L.append(f"- candidate decision starts {fr['n_candidate_decision_starts']}; retained "
                 f"{fr['n_retained_starts']}; removed as later repeats "
                 f"{fr['n_removed_fragmented_starts']}; unassigned {fr['n_unassigned_starts']}")
        L.append(f"- retained event-list catch share {f(fr['cluster_share_retained'])}; "
                 f"false/asset-yr {f(fr['false_per_asset_year_retained'])}")
        ps = fr["pre_shock_equity_break"]
        L.append(f"- pre-shock equity break already true before the episode: either "
                 f"{ps['n_either_already']}/{ps['n_episodes']} (SPY {ps['n_spy_already']}, "
                 f"QQQ {ps['n_qqq_already']})\n")
        L.append(f"Runtime this block: {b['runtime_s']}s.\n")

    ov = r["cluster_overlap_dfii10_vs_dgs10"]
    L.append("## Candidate cluster-id overlap, DFII10 vs DGS10\n")
    L.append("| set | clusters |")
    L.append("|---|---|")
    L.append(f"| DFII10 candidate | {ov['n_dfii10']} |")
    L.append(f"| DGS10 candidate | {ov['n_dgs10']} |")
    L.append(f"| caught by both | {ov['counts']['both']} |")
    L.append(f"| only DFII10 | {ov['counts']['only_dfii10']} |")
    L.append(f"| only DGS10 | {ov['counts']['only_dgs10']} |")
    L.append("")
    L.append("## Deviations\n")
    for d in DEVIATIONS:
        L.append(f"- {d}")
    L.append("")
    (HERE / "SUMMARY.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
