#!/usr/bin/env python3
"""Risk Radar follow-up rev1: the frozen k=3 set, rule 2b and rates_realrate on PRE.

Bounded research worker. Paper-only: nothing sizes, ranks or executes.

Three runs, rows already written in the desk ledger (ledger_rows_rev1.py):
  (a) rr-roff-confluence-k3-followup-rev1-repro   DECISIVE reproduction through bm_ref rev1
  (b) rr-roff-confluence-k3-followup-rule2b-desc  rule clarified after its result was seen;
                                                  description only, NEVER a nomination
  (c) rr-roff-leg-rates-realrate-pre-desc         description only; forward candidate only

Usage:
    python3 run_rev1.py --desk <path-to-desk-v4>
    ROTATION_DESK=<path> python3 run_rev1.py
    RR_DRY=1 python3 run_rev1.py --desk <desk>     # 50 draws, pipeline check only

Two-phase import (kept from followup_pre/run_pre.py):
  1. build the alerts from Macro's engine (its inputs carry the point-in-time FRED replay);
  2. purge `engine*` from sys.modules and drop the Macro root + cwd from sys.path;
  3. load the desk kit; 4. assert `pivots.__file__` is under the desk.

Writes ONLY into this directory: result.json, SUMMARY.md, RUN_LOG.txt.
The desk is imported read-only; trials.jsonl is never touched.
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
K = 3
DRY = bool(os.environ.get("RR_DRY"))
N_DRAWS = 50 if DRY else 2000
NPROC = 20

PIN_BM = "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"
PIN_AD = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"

ID_A = "rr-roff-confluence-k3-followup-rev1-repro"
SHA_A = "a1cddaf8c097211ad2cc7b32e5a8d051aa6b997e69b7fe6d83beb2fbe827d32d"
ID_B = "rr-roff-confluence-k3-followup-rule2b-desc"
SHA_B = "48d2afc9eeb13d9d2e0a75956db0e36d4afb79a77e94b6bf831b3cb74d114d17"
ID_C = "rr-roff-leg-rates-realrate-pre-desc"
SHA_C = "3f450f59f575834d8fc72308f96089b48a506f2e4ede849933f677f12c2739cc"

# ledger_rows.py LEGS: leg -> 'on' threshold (the engine's own thr_pct as coded, not fitted)
LEGS = {
    "credit_oas_roc": 0.90, "credit_hyg_tlt": 0.90, "rates_move": 0.90, "rates_realrate": 0.90,
    "bubble_ext": 0.90, "bubble_leadership": 0.90, "growth_defensives": 0.90,
    "growth_cyc_def": 0.90, "vol_term": 0.90, "global_breadth": 0.70, "jpy_carry": 0.85,
    "corr_floor_break": 0.85,
}


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


# ------------------------------------------------------------------ phase 1: Macro alerts
def build_alert_full():
    """The k=3 confluence alert on the engine calendar, full history, shifted t+1.

    n_on = number of the 12 legs with percentiles >= their coded threshold (NaN off);
    alert = n_on >= 3, then shift(1, fill_value=False) on the FULL series before any windowing.
    """
    from engine import risk_radar as rr
    from engine.risk_radar_eval import availability as AV

    t0 = time.time()
    sigs = rr.leading_signals()
    missing = set(LEGS) - set(sigs.columns)
    if missing:
        raise SystemExit(f"legs absent from leading_signals: {sorted(missing)}")
    pit = AV.pit_signals(sigs, start=str(START.date()))
    missing = set(LEGS) - set(pit.columns)
    if missing:
        raise SystemExit(f"legs absent after pit_signals: {sorted(missing)}")
    log(f"  leading_signals + pit_signals: {time.time()-t0:.1f}s; "
        f"calendar {pit.index.min().date()} .. {pit.index.max().date()}")

    n_on = pd.Series(0, index=pit.index, dtype=int)
    avail = pd.Series(0, index=pit.index, dtype=int)
    for leg, thr in LEGS.items():
        n_on = n_on + (pit[leg] >= thr).fillna(False).astype(int)
        avail = avail + pit[leg].notna().astype(int)
    alert = n_on >= K
    return alert.shift(1, fill_value=False).astype(bool), avail, pit


def window_index(levels: dict, n: str) -> pd.DatetimeIndex:
    idx = levels[n].index
    sp = int(idx.searchsorted(START))
    lo = max(0, sp - PRE)
    ai = idx[lo:]
    return ai[ai <= END]


def window_alert(full: pd.Series, levels: dict, series: list) -> tuple[dict, dict]:
    """One alert copy per series on that series' own sessions (r1g/v2 windowing)."""
    out, px = {}, {}
    for n in series:
        ai = window_index(levels, n)
        if len(ai) == 0:
            raise SystemExit(f"empty window for {n}")
        a = full.reindex(ai, method="ffill")
        if a.isna().any():
            raise SystemExit(f"alert has NaN after reindex for {n}")
        out[n] = a.astype(bool)
        px[n] = levels[n].reindex(ai)
        assert out[n].index.max() <= END and px[n].index.max() <= END, n
    return out, px


def window_score(full: pd.Series, levels: dict, series: list) -> dict:
    """A percentile score series windowed like the alert, ffill only (leading NaN kept)."""
    out = {}
    for n in series:
        ai = window_index(levels, n)
        s = full.reindex(ai, method="ffill").astype(float)
        out[n] = s
        assert s.index.max() <= END, n
    return out


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


# ------------------------------------------------------------------ derived shares
def pooled_share(alerts: dict) -> float:
    num = sum(int(pd.Series(a).sum()) for a in alerts.values())
    den = sum(len(pd.Series(a)) for a in alerts.values())
    return float(num / den) if den else None


def share_by_year(full: pd.Series) -> dict:
    win = (full.index >= START) & (full.index <= END)
    w = full[win]
    return {int(y): round(float(v), 4) for y, v in w.groupby(w.index.year).mean().items()}


# ------------------------------------------------------------------ parallel p90
_P90: dict = {}


def _p90_chunk(di_list: list) -> list:
    """Exactly bm_ref.cluster_placebo_p90's inner loop, for a chunk of draw indices."""
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
    """cluster_placebo_p90, identical draws and scoring, with the draw loop across processes."""
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


# ------------------------------------------------------------------ scoring job
_G: dict = {}


def _job(spec: dict) -> dict:
    BM = _G["BM"]
    t0 = time.time()
    row = BM.score_alerts(spec["turns"], spec["alerts"], spec["episodes"], spec["px"],
                          direction="top", post=POST, n_draws=N_DRAWS, seed=SEED, tol=TOL,
                          pre=PRE, min_off=MIN_OFF, include_passes=False,
                          outcomes_through=END)
    row["_runtime_s"] = round(time.time() - t0, 1)
    return row


# ------------------------------------------------------------------ hand-built PRE context (diff)
def hand_built_turns(A, BM, specs: dict, series: list):
    """followup_pre/run_pre.py's build_pre_context, verbatim in substance."""
    df = A.load_pivots()
    df_pre = df[df["date"] <= END].copy()
    rows = A.select(df_pre, type="risk_off", tier="major", block="PRE")
    rows_dir = rows[[BM._direction_of(r) == "top" for _, r in rows.iterrows()]].copy()
    levels = {}
    for n in series:
        s = BM.level_series(specs[n])
        levels[n] = s[s.index <= END]
    episodes = A.build_episodes_for_series(df_pre, series, tier="major", calendar=None,
                                           levels=levels, episode_rule="swing")
    return BM.turns_in_window(BM.build_turns(rows_dir, episodes), START, END)


def turn_key(t) -> tuple:
    return (str(t.asset), pd.Timestamp(t.date), str(t.kind),
            None if t.depth is None else round(float(t.depth), 10),
            None if t.cluster_id is None else str(t.cluster_id),
            None if t.episode_onset is None else pd.Timestamp(t.episode_onset))


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=os.environ.get("ROTATION_DESK"))
    ns = ap.parse_args()
    if not ns.desk:
        raise SystemExit("desk path required: --desk <path> or ROTATION_DESK")
    desk = Path(ns.desk).resolve()

    RUN_LOG.write_text("")
    log("# Risk Radar follow-up rev1 (bm_ref rev1 pin)")
    log(f"# dry={DRY} n_draws={N_DRAWS} window={START.date()}..{END.date()} procs={NPROC}")
    p_start = check_pins(desk, "start")
    t_all = time.time()

    # --- phase 1
    log("building alerts (leading_signals + pit_signals start 2006-01-03)")
    alert_full, avail, pit = build_alert_full()

    # --- phase 2
    A, BM, pv, pv_path = load_desk_kit(desk)
    log(f"# scorer module: {str(pv_path).replace(str(desk), '<desk>')}")
    assert str(pv_path).startswith(str(desk))
    from catalogue import build as B

    # --- rev1 context
    ctx = BM.build_context("R-off", "top", start_d=START, end_d=END)
    series, turns, levels, episodes = ctx["series"], ctx["turns"], ctx["levels"], ctx["episodes"]
    t_min = min(pd.Timestamp(t.date) for t in turns)
    t_max = max(pd.Timestamp(t.date) for t in turns)
    log(f"# series: {len(series)}; turns in window: {len(turns)}  {t_min.date()} .. {t_max.date()}")

    alerts, px = window_alert(alert_full, levels, series)
    log(f"# alert window per series: {len(alerts[series[0]])} sessions, "
        f"{alerts[series[0]].index.min().date()} .. {alerts[series[0]].index.max().date()}")

    # ---- date guard: nothing after 2019-12-31 anywhere
    def date_guard() -> dict:
        worst = {"turns": max(pd.Timestamp(t.date) for t in turns),
                 "alert_index": max(s.index.max() for s in alerts.values()),
                 "px_index": max(s.index.max() for s in px.values()),
                 "levels": max(s.index.max() for s in levels.values()),
                 "outcomes_through": END}
        ep = []
        for eps in episodes.values():
            for e in eps:
                ep += [d for d in (e.peak, e.onset, e.trough, e.recovery) if d is not None]
        worst["episodes"] = max(pd.Timestamp(d) for d in ep)
        ok = all(pd.Timestamp(v) <= END for v in worst.values())
        if not ok:
            raise SystemExit(f"DATE GUARD FAILED: {worst}")
        return {"all_le_2019_12_31": True,
                "max": {k: str(pd.Timestamp(v).date()) for k, v in worst.items()}}

    guard = date_guard()
    log(f"# date guard ok: {json.dumps(guard['max'])}")

    # ---- fixed-threshold leg alerts (a)(c) and shifted windowed scores (b)
    leg_alerts, leg_px, leg_scores = {}, {}, {}
    for leg, thr in LEGS.items():
        leg_full = (pit[leg] >= thr).fillna(False).astype(bool).shift(1, fill_value=False)
        la, lpx = window_alert(leg_full, levels, series)
        leg_alerts[leg], leg_px[leg] = la, lpx
        # (b) same shift convention as the candidate: shift the FULL score series, then window
        leg_scores[leg] = window_score(pit[leg].shift(1), levels, series)

    # ---- (a) scoring: candidate + 12 fixed-threshold legs
    _G["BM"] = BM
    log(f"# scoring candidate + {len(LEGS)} legs, {NPROC} processes")
    jobs = [("candidate", {"turns": turns, "alerts": alerts, "episodes": episodes, "px": px})]
    jobs += [(f"leg_{leg}", {"turns": turns, "alerts": leg_alerts[leg], "episodes": episodes,
                             "px": leg_px[leg]}) for leg in LEGS]
    results = {}
    with ProcessPoolExecutor(max_workers=min(NPROC, len(jobs))) as ex:
        futs = {ex.submit(_job, spec): key for key, spec in jobs}
        for fut, key in futs.items():
            results[key] = fut.result()
            log(f"  {key:22s} share {results[key]['cluster_share']} false "
                f"{results[key]['false_per_asset_year']} ({results[key]['_runtime_s']}s)")
    cand = results["candidate"]
    singles = {leg: results[f"leg_{leg}"] for leg in LEGS}

    refs = {f: BM.reference_result(ctx, alerts, form=f, post=POST, n_draws=N_DRAWS,
                                   seed=SEED, tol=TOL, include_passes=False,
                                   start_d=START, end_d=END) for f in ("dd", "near")}
    bm = BM.better_reference(refs["dd"], refs["near"])
    bm_form = bm["match"]["form"]
    best_leg = sorted(singles, key=lambda k: (-(singles[k]["cluster_share"] or 0.0),
                                              singles[k]["false_per_asset_year"] or 0.0))[0]
    best_single = singles[best_leg]

    log("# p90 (k3 candidate) via parallel draw loop")
    t_p = time.time()
    p90 = parallel_p90(BM, pv, turns, alerts, episodes, px, post=POST)
    # equivalence check against the desk's own implementation, 50 draws
    ref50 = BM.cluster_placebo_p90(turns, alerts, episodes, px, kind="top",
                                   outcomes_through=END, n_draws=50, seed=SEED, tol=TOL,
                                   pre=PRE, post=POST, min_off=MIN_OFF)
    par50 = parallel_p90(BM, pv, turns, alerts, episodes, px, post=POST, n_draws=50)
    eq = (ref50["p90"] == par50["p90"] and ref50["n_valid_draws"] == par50["n_valid_draws"]
          and ref50["observed_cluster_share"] == par50["observed_cluster_share"])
    if not eq:
        raise SystemExit(f"parallel p90 disagrees with bm_ref at 50 draws: {ref50} vs {par50}")
    p90["_runtime_s"] = round(time.time() - t_p, 1)
    p90["_equivalence_50_draws"] = {"matches_bm_ref": True, "p90": ref50["p90"],
                                    "n_valid_draws": ref50["n_valid_draws"]}
    log(f"  p90 {p90['p90']} observed {p90['observed_cluster_share']} ({p90['_runtime_s']}s)")

    verdict = BM.set_level_pass(cand, bm, p90["p90"], best_single, is_confluence=True)
    log(f"# better reference: {bm_form}; best single: {best_leg}")
    log(f"# (a) verdict {json.dumps(verdict)}")

    # ---- (b) rule 2b: every leg matched to the k3 set's realised alert share
    target = pooled_share(alerts)
    log(f"# (b) target alert share (pooled k3, windowed) {target:.6f}; "
        f"alert_budget(mean of per-series) {cand['alert_budget']:.6f}")
    parts = {}
    for leg in LEGS:
        m = BM.part_at_matched_share(leg_scores[leg], target, start_d=START, end_d=END,
                                     higher_is_alert=True)
        thr = m["threshold"]
        part_alerts = {}
        for a, s in leg_scores[leg].items():
            part_alerts[a] = (s >= thr).fillna(False).astype(bool)
            own = m["alerts"].get(a)
            if own is not None:
                j = own.index
                assert bool((part_alerts[a].reindex(j) == own).all()), (leg, a)
            assert part_alerts[a].index.max() <= END
        n_sess = sum(len(s) for s in leg_scores[leg].values())
        n_nonfin = sum(int(pd.Series(s).isna().sum()) for s in leg_scores[leg].values())
        parts[leg] = {"threshold": thr, "target_share": m["target_share"],
                      "achieved_share_finite_sessions": m["achieved_share"],
                      "achieved_share_all_sessions": pooled_share(part_alerts),
                      "n_observations": m["n_observations"],
                      "n_window_sessions": n_sess, "n_nonfinite_sessions": n_nonfin,
                      "alerts": part_alerts, "row": None}
    log(f"# (b) scoring {len(LEGS)} matched parts")
    with ProcessPoolExecutor(max_workers=min(NPROC, len(LEGS))) as ex:
        futs = {ex.submit(_job, {"turns": turns, "alerts": parts[leg]["alerts"],
                                 "episodes": episodes, "px": leg_px[leg]}): leg
                for leg in LEGS}
        for fut, leg in futs.items():
            parts[leg]["row"] = fut.result()
    b_verdict = BM.set_level_pass_matched(cand, bm, p90["p90"],
                                          [parts[l]["row"] for l in LEGS])
    log(f"# (b) verdict {json.dumps(b_verdict)} (nomination forced False)")

    # ---- (c) rates_realrate alone at its fixed threshold
    rr = "rates_realrate"
    c_row = singles[rr]
    c_p90 = parallel_p90(BM, pv, turns, leg_alerts[rr], episodes, leg_px[rr], post=POST)
    c_refs = {f: BM.reference_result(ctx, leg_alerts[rr], form=f, post=POST, n_draws=N_DRAWS,
                                     seed=SEED, tol=TOL, include_passes=False,
                                     start_d=START, end_d=END) for f in ("dd", "near")}
    c_bm = BM.better_reference(c_refs["dd"], c_refs["near"])
    c_verdict = BM.set_level_pass(c_row, c_bm, c_p90["p90"], None, is_confluence=False)
    rr_full = (pit[rr] >= LEGS[rr]).fillna(False).astype(bool).shift(1, fill_value=False)
    c_shares = share_by_year(rr_full)
    log(f"# (c) rates_realrate share {c_row['cluster_share']} false "
        f"{c_row['false_per_asset_year']} p90 {c_p90['p90']}")

    # ---- turns vs the hand-built PRE context
    specs = {s.name: s for s in B.build_specs(B.CUTOFF)[0]}
    hand = hand_built_turns(A, BM, specs, series)
    hk = {turn_key(t): t for t in hand}
    rk = {turn_key(t): t for t in turns}
    only_hand = sorted(set(hk) - set(rk))
    only_rev1 = sorted(set(rk) - set(hk))
    log(f"# turns: hand-built {len(hand)}, rev1 {len(turns)}, "
        f"only-hand {len(only_hand)}, only-rev1 {len(only_rev1)}")

    # ---- alert share / available legs by year (engine calendar)
    share_by_y = share_by_year(alert_full)
    win = (avail.index >= START) & (avail.index <= END)
    av_w = avail[win]
    avail_by_y = {int(y): round(float(v), 2)
                  for y, v in av_w.groupby(av_w.index.year).mean().items()}

    # ---- cluster date range (deterministic scorer, same key scheme as pv.summarise)
    det = pv.score_pivots_multi(turns, alerts, episodes, outcomes_through=END,
                                posts=(POST,), pre=PRE, min_off=MIN_OFF)
    pooled_rows = [r for _a, v in sorted(det["by_post"][f"post{POST}"]["by_asset"].items())
                   for r in v["turns"]]
    scored = [r for r in pooled_rows if r["kind"] == "top" and r["status"] == "scored"]
    cl_dates: dict = {}
    for i, r in enumerate(scored):
        key = r.get("cluster_id") or f"__{r.get('asset')}_{r['date']}_{i}"
        cl_dates.setdefault(key, []).append(pd.Timestamp(r["date"]))
    assert len(cl_dates) == cand["clusters_scored"], (len(cl_dates), cand["clusters_scored"])
    cl_min = min(min(v) for v in cl_dates.values())
    cl_max = max(max(v) for v in cl_dates.values())
    assert cl_max <= END

    # ---- PRE comparison
    PRE_NUM = {"cluster_share": 0.4488, "false_per_asset_year": 2.9264, "p90": 0.3701,
               "near_share": 0.3228, "near_false": 2.9507, "dd_share": 0.2205,
               "dd_false": 0.7116, "rr_share": 0.7953, "rr_false": 4.9745,
               "turns_scored": 471, "clusters": 127,
               # PRE's own recorded float, not a rounded restatement
               "alert_budget": 0.18373387954269568}
    REV1_NUM = {"cluster_share": cand["cluster_share"],
                "false_per_asset_year": cand["false_per_asset_year"],
                "p90": p90["p90"], "near_share": refs["near"]["cluster_share"],
                "near_false": refs["near"]["false_per_asset_year"],
                "dd_share": refs["dd"]["cluster_share"],
                "dd_false": refs["dd"]["false_per_asset_year"],
                "rr_share": c_row["cluster_share"],
                "rr_false": c_row["false_per_asset_year"],
                "turns_scored": cand["turns_scored"],
                "clusters": cand["clusters_scored"],
                "alert_budget": cand["alert_budget"]}
    comparison = {k: {"pre": PRE_NUM[k], "rev1": REV1_NUM[k],
                      "delta": None if REV1_NUM[k] is None
                      else round(REV1_NUM[k] - PRE_NUM[k], 4) + 0.0}
                  for k in PRE_NUM}
    log(f"# comparison to PRE: {json.dumps(comparison)}")

    def slim(r: dict) -> dict:
        return {k: r.get(k) for k in
                ("turns_scored", "turns_flagged", "turn_share", "turn_share_ci90",
                 "clusters_scored", "clusters_flagged", "cluster_share",
                 "cluster_share_ci90", "median_delay", "censored", "false_per_asset_year",
                 "alert_budget", "_runtime_s")}

    deviations = [
        "bm_ref rev1 build_context(..., start_d=2006-01-03, end_d=2019-12-31) is used for rows, "
        "series, level series, swing episodes and turns; it selects block='PRE' because end_d < "
        "START_D. The PRE run hand-built the same context from a df truncated at 2019-12-31. The "
        "two turn sets are diffed in a.turns_vs_hand_built.",
        "bm_ref rev1 reference_result forwards start_d/end_d and passes outcomes_through=end_d to "
        "score_alerts; the PRE run called build_reference + score_alerts directly and left "
        "outcomes_through at the adapter default (2023-12-29). The bound is inert in both runs: "
        "every alert, price and turn index already ends at 2019-12-31, so the cut shortens nothing.",
        "score_alerts bounds outcomes_through at 2019-12-31 and cuts every alert and price series "
        "at it before scoring; the candidate alerts are also cut at 2019-12-31 before the call.",
        "The alert is built on the engine's SPY-session calendar and reindexed onto each series' "
        "own level index with method='ffill' (r1g/v2 windowing).",
        "Two-phase import: Macro's `engine` is purged and the Macro root + cwd are dropped from "
        "sys.path before the desk kit loads, so pivots resolves under the desk.",
        "The window's first 21 sessions precede 2006-01-03; the FRED legs there are the engine's "
        "pre-start values, not the PIT replay, which begins 2006-01-03.",
        "(b) shift order: the t+1 shift is applied to the FULL leg percentile series "
        "(score.shift(1)) and the window is taken afterwards, exactly the candidate's convention; "
        "part_at_matched_share then takes its threshold on the shifted windowed scores. The "
        "alternative order (threshold, then shift) would differ only at the window edges.",
        "(b) part_at_matched_share measures its achieved share over finite pooled observations "
        "only, and returns its alerts on that finite index. For scoring, each part's alert is "
        "rebuilt on the FULL windowed index as (shifted score >= returned threshold), with a "
        "non-finite session counting as not-alerting; this reproduces the function's own alert "
        "exactly where both are defined (asserted per asset). Two consequences, both reported "
        "rather than smoothed: (i) the passed-in target share is pooled over all windowed "
        "sessions while the function measures over finite sessions, so the finite achieved share "
        "is the rule's own number and the all-sessions share is the alert the scorer actually "
        "saw; (ii) a leg with in-window non-finite sessions (the ~21-session lead-in before its "
        "score exists, plus any data gap) alerts on fewer sessions than the target, so its "
        "effective budget is below the k3 set's. The per-leg non-finite counts are tabled.",
        "(b) the matched target is the k3 set's realised pooled windowed alert share; the "
        "per-series mean alert_budget is reported beside it (they differ only through rounding "
        "of per-series window lengths).",
        "(b) is a rule clarified AFTER the candidate's result was seen; nomination is forced "
        "False regardless of the verdict.",
        "The parallel p90 reproduces bm_ref.cluster_placebo_p90's draws, scoring and pooling "
        "exactly, only distributing the 2000-draw loop across processes; equivalence is asserted "
        "against the desk's own function at 50 draws and recorded in a.placebo_p90.",
        "(c) is description only: rates_realrate was seen on D and as k3's best PRE leg, so it "
        "cannot be a nomination.",
    ]

    result = {
        "runs": [
            {"id": ID_A, "spec_sha256": SHA_A,
             "role": "DECISIVE reproduction through bm_ref rev1"},
            {"id": ID_B, "spec_sha256": SHA_B,
             "role": "rule clarified after its result was seen — description, cannot be a nomination"},
            {"id": ID_C, "spec_sha256": SHA_C,
             "role": "description only; forward candidate only"},
        ],
        "pins": {"start": p_start, "end": None},
        "scorer_module": str(pv_path).replace(str(desk), "<desk>"),
        "window": {"start": str(START.date()), "end": str(END.date()), "pre": PRE, "post": POST,
                   "k": K, "n_draws": N_DRAWS, "seed": SEED, "tol": TOL, "min_off": MIN_OFF,
                   "dry": DRY},
        "series": series,
        "date_guard": guard,
        "a": {
            "id": ID_A, "spec_sha256": SHA_A,
            "label": "decisive PRE read through bm_ref rev1; forward candidate only (no hold-out)",
            "turns": {"n": len(turns), "min": str(t_min.date()), "max": str(t_max.date())},
            "clusters": {"n": cand["clusters_scored"], "flagged": cand["clusters_flagged"],
                         "min_turn_date": str(cl_min.date()),
                         "max_turn_date": str(cl_max.date())},
            "candidate": slim(cand),
            "references": {f: slim(refs[f]) for f in refs},
            "reference_match": {f: {"x": refs[f]["match"]["x"],
                                    "achieved_share": refs[f]["match"]["achieved_share"],
                                    "target_budget": refs[f]["match"]["target_budget"]}
                                for f in refs},
            "better_reference": bm_form,
            "placebo_p90": p90,
            "singles": {leg: slim(singles[leg]) for leg in LEGS},
            "best_single": best_leg,
            "verdict": verdict,
            "alert_share_pooled": target,
            "alert_share_by_year": share_by_y,
            "available_legs_by_year": avail_by_y,
            "turns_vs_hand_built": {"n_hand": len(hand), "n_rev1": len(turns),
                                    "n_only_hand": len(only_hand),
                                    "n_only_rev1": len(only_rev1),
                                    "only_hand": [list(map(str, k)) for k in only_hand[:10]],
                                    "only_rev1": [list(map(str, k)) for k in only_rev1[:10]]},
        },
        "b": {
            "id": ID_B, "spec_sha256": SHA_B,
            "label": "rule clarified after its result was seen — description, cannot be a nomination",
            "target_alert_share": target,
            "target_alert_budget_per_series_mean": cand["alert_budget"],
            "shift_order": "shift(1) on the full leg percentile series, then window; threshold "
                           "taken on the shifted windowed scores",
            "parts": {leg: {"threshold": parts[leg]["threshold"],
                            "target_share": parts[leg]["target_share"],
                            "achieved_share_finite_sessions":
                                parts[leg]["achieved_share_finite_sessions"],
                            "achieved_share_all_sessions":
                                parts[leg]["achieved_share_all_sessions"],
                            "n_observations": parts[leg]["n_observations"],
                            "n_window_sessions": parts[leg]["n_window_sessions"],
                            "n_nonfinite_sessions": parts[leg]["n_nonfinite_sessions"],
                            "row": slim(parts[leg]["row"])} for leg in LEGS},
            "verdict": b_verdict,
            "nomination": False,
            "nomination_note": "forced False: the rule was clarified after the candidate's result "
                               "was seen; this run is a description, never a nomination.",
        },
        "c": {
            "id": ID_C, "spec_sha256": SHA_C,
            "label": "description only; forward candidate only (no hold-out); NOT a nomination",
            "leg": rr, "threshold": LEGS[rr],
            "row": slim(c_row),
            "alert_share_pooled": pooled_share(leg_alerts[rr]),
            "alert_share_by_year": c_shares,
            "placebo_p90_own": c_p90,
            "references_own": {f: slim(c_refs[f]) for f in c_refs},
            "reference_match_own": {f: {"x": c_refs[f]["match"]["x"],
                                        "achieved_share": c_refs[f]["match"]["achieved_share"],
                                        "target_budget": c_refs[f]["match"]["target_budget"]}
                                    for f in c_refs},
            "better_reference_own": c_bm["match"]["form"],
            "ab_description": {"a": c_verdict["a"], "b": c_verdict["b"],
                               "criteria_met": c_verdict["criteria_met"]},
            "nomination": False,
        },
        "comparison_to_pre": comparison,
        "deviations": deviations,
        "runtime_s": None,
    }

    # ------------------------------------------------------------------ SUMMARY.md
    def f(v, nd=3):
        return "—" if v is None else f"{v:.{nd}f}"

    def ci(v):
        return "—" if not v else f"[{v[0]:.3f}, {v[1]:.3f}]"

    L = []
    L.append("# Risk Radar follow-up rev1 — frozen k=3, rule 2b, rates_realrate (PRE)\n")
    L.append(f"Window {START.date()}..{END.date()}, pre {PRE}, post {POST}, seed {SEED}, "
             f"{N_DRAWS} draws, tol {TOL}, min_off {MIN_OFF}. bm_ref rev1 pin. "
             f"Scorer `<desk>/pivot/radar_eval/`." + ("  **DRY RUN (50 draws).**" if DRY else "")
             + "\n")
    L.append("## Pins\n")
    L.append(f"- `bm_ref.py` `{p_start['bm_ref.py']}`")
    L.append(f"- `adapter.py` `{p_start['adapter.py']}`")
    L.append(f"- scorer module: `{str(pv_path).replace(str(desk), '<desk>')}`\n")
    L.append("## Date guard\n")
    L.append("Every date in turns, alerts, levels, episodes and `outcomes_through` is "
             "≤ 2019-12-31 (asserted; max values below).\n")
    L.append("| surface | max date |")
    L.append("|---|---|")
    for k, v in guard["max"].items():
        L.append(f"| {k} | {v} |")
    L.append("")

    # --- (a)
    L.append(f"## (a) `{ID_A}` — DECISIVE\n")
    L.append("| criterion | met |")
    L.append("|---|---|")
    L.append(f"| (a) cluster share > near-turn placebo p90 at cluster level ({f(p90['p90'])}) "
             f"| {verdict['a']} |")
    L.append(f"| (b) > better reference ({bm_form}) at <= false rate | {verdict['b']} |")
    L.append(f"| (c) > best single leg ({best_leg}) at <= false rate | {verdict['c']} |")
    L.append("")
    L.append(f"**criteria_met:** {verdict['criteria_met']}  ")
    L.append(f"**nomination:** {verdict['nomination']}\n")
    L.append("| set | cluster share | 90% CI | median delay | false/asset-yr | alert share |")
    L.append("|---|---|---|---|---|---|")
    L.append(f"| **candidate k={K}** | {f(cand['cluster_share'])} "
             f"| {ci(cand['cluster_share_ci90'])} | {f(cand['median_delay'], 1)} "
             f"| {f(cand['false_per_asset_year'])} | {f(cand['alert_budget'])} |")
    for form in ("dd", "near"):
        r = refs[form]
        mark = " **(better)**" if form == bm_form else ""
        L.append(f"| ref {form}{mark} | {f(r['cluster_share'])} | {ci(r['cluster_share_ci90'])} "
                 f"| {f(r['median_delay'], 1)} | {f(r['false_per_asset_year'])} "
                 f"| {f(r['alert_budget'])} |")
    for leg in sorted(singles, key=lambda k: -(singles[k]["cluster_share"] or 0.0)):
        r = singles[leg]
        L.append(f"| leg {leg} | {f(r['cluster_share'])} | {ci(r['cluster_share_ci90'])} "
                 f"| {f(r['median_delay'], 1)} | {f(r['false_per_asset_year'])} "
                 f"| {f(r['alert_budget'])} |")
    L.append("")
    L.append(f"- turns scored: {cand['turns_scored']} (flagged {cand['turns_flagged']}), "
             f"dates {t_min.date()} .. {t_max.date()}")
    L.append(f"- clusters scored: {cand['clusters_scored']} (flagged {cand['clusters_flagged']}), "
             f"turn dates {cl_min.date()} .. {cl_max.date()}")
    L.append(f"- censored turns: {cand['censored']}")
    L.append(f"- near-turn placebo p90 (cluster): {f(p90['p90'])}; observed "
             f"{f(p90['observed_cluster_share'])}; {p90['n_valid_draws']} valid draws")
    L.append(f"- best single leg: `{best_leg}` (share {f(best_single['cluster_share'])}, "
             f"false {f(best_single['false_per_asset_year'])})\n")
    L.append("### Matched threshold x per series (reference match)\n")
    L.append("| series | dd x | near x |")
    L.append("|---|---|---|")
    for n in series:
        L.append(f"| {n} | {refs['dd']['match']['x'][n]:.4f} "
                 f"| {refs['near']['match']['x'][n]:.4f} |")
    L.append("")
    L.append("### Alert share and available legs by year (description)\n")
    L.append("| year | alert share | mean legs available |")
    L.append("|---|---|---|")
    for y in sorted(share_by_y):
        L.append(f"| {y} | {share_by_y[y]:.4f} | {avail_by_y.get(y, 0):.2f} |")
    L.append("")

    # --- (b)
    L.append(f"## (b) `{ID_B}` — rule clarified after its result was seen; description, "
             f"cannot be a nomination\n")
    L.append(f"Target alert share (pooled k3, windowed): {target:.6f}. Shift order: shift(1) on "
             f"the full leg percentile series, then window; threshold on the shifted windowed "
             f"scores.\n")
    L.append("| leg | threshold | achieved (finite) | achieved (all) | non-finite sess. "
             "| cluster share | 90% CI | false/asset-yr | set beats it |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for leg in sorted(LEGS, key=lambda k: -(parts[k]["row"]["cluster_share"] or 0.0)):
        p = parts[leg]
        r = p["row"]
        beats = (cand["cluster_share"] > (r["cluster_share"] or 0)
                 and (cand["false_per_asset_year"] <= (r["false_per_asset_year"] or 0)))
        L.append(f"| {leg} | {p['threshold']:.6f} | {p['achieved_share_finite_sessions']:.6f} "
                 f"| {p['achieved_share_all_sessions']:.6f} "
                 f"| {p['n_nonfinite_sessions']}/{p['n_window_sessions']} "
                 f"| {f(r['cluster_share'])} "
                 f"| {ci(r['cluster_share_ci90'])} | {f(r['false_per_asset_year'])} "
                 f"| {'yes' if beats else 'no'} |")
    L.append("")
    L.append(f"**verdict:** a={b_verdict['a']}, b={b_verdict['b']}, c={b_verdict['c']}, "
             f"criteria_met={b_verdict['criteria_met']}, "
             f"parts_checked={b_verdict['parts_checked']}")
    L.append("**nomination: False** — forced; the rule was clarified after the candidate's result "
             "was seen.\n")

    # --- (c)
    L.append(f"## (c) `{ID_C}` — description only; forward candidate only; NOT a nomination\n")
    L.append("| metric | value |")
    L.append("|---|---|")
    L.append(f"| cluster share | {f(c_row['cluster_share'])} |")
    L.append(f"| 90% CI | {ci(c_row['cluster_share_ci90'])} |")
    L.append(f"| false/asset-yr | {f(c_row['false_per_asset_year'])} |")
    L.append(f"| median delay | {f(c_row['median_delay'], 1)} |")
    L.append(f"| alert share (pooled) | {f(pooled_share(leg_alerts[rr]))} |")
    L.append(f"| turns scored / flagged | {c_row['turns_scored']} / {c_row['turns_flagged']} |")
    L.append(f"| clusters / flagged | {c_row['clusters_scored']} / {c_row['clusters_flagged']} |")
    L.append(f"| own placebo p90 | {f(c_p90['p90'])} |")
    for form in ("dd", "near"):
        r = c_refs[form]
        L.append(f"| own ref {form} share / false | {f(r['cluster_share'])} / "
                 f"{f(r['false_per_asset_year'])} |")
    L.append(f"| better own reference | {c_bm['match']['form']} |")
    L.append(f"| (a) share > own p90 | {c_verdict['a']} |")
    L.append(f"| (b) > better own ref at <= false | {c_verdict['b']} |")
    L.append("")
    L.append("Alert share by year: "
             + ", ".join(f"{y} {v:.4f}" for y, v in sorted(c_shares.items())))
    L.append("\n**This is a description, not a nomination.**\n")

    # --- difference table
    L.append("## Difference table vs `followup_pre/result.json`\n")
    def num(v):
        if v is None:
            return "—"
        return f"{v:.4f}" if isinstance(v, float) else str(v)

    L.append("| quantity | PRE | rev1 | delta |")
    L.append("|---|---|---|---|")
    for k, v in comparison.items():
        L.append(f"| {k} | {num(v['pre'])} | {num(v['rev1'])} | {num(v['delta'])} |")
    L.append("")
    diff = result["a"]["turns_vs_hand_built"]
    L.append(f"- turns: hand-built {diff['n_hand']}, rev1 {diff['n_rev1']}; "
             f"only-hand {diff['n_only_hand']}, only-rev1 {diff['n_only_rev1']} "
             f"(diff on asset/date/kind/depth/cluster_id/episode_onset).")
    L.append("")
    L.append("### Explanations\n")
    L.append("- **`outcomes_through`.** rev1 passes `outcomes_through=2019-12-31` into "
             "`score_alerts` and `reference_result`; PRE left the default (adapter `END_D`, "
             "2023-12-29). The bound is inert in both runs: every alert, price and turn index "
             "already ends at 2019-12-31, so the cut shortens nothing. Any delta above therefore "
             "cannot come from this.")
    L.append("- **rev1 turn set vs the hand-built turns.** `build_context(..., end_d=2019-12-31)` "
             "does the same three things `build_pre_context` did by hand: block='PRE' rows, level "
             "series truncated at the end, episode rows cut before any onset/peak/trough. The "
             "turn-set diff above is the measured result of that substitution.")
    L.append("- **level truncation.** Both truncate each level series at 2019-12-31, so the "
             "running peak/low, the percentile inputs and the reference `dd`/`near` thresholds "
             "use the same sessions; no in-window value can move.")
    L.append("- **alert windowing.** Identical in both: full-series t+1 shift, then each series' "
             "own sessions from `searchsorted(start) - pre` through the end, `ffill`.")
    L.append("- Nothing was adjusted to match PRE. The PRE numbers are reproduced here as the "
             "record, and the deltas (including zero) are reported as they came out.")
    L.append("")

    L.append("## Deviations\n")
    for d in deviations:
        L.append(f"- {d}")
    L.append("")
    (HERE / "SUMMARY.md").write_text("\n".join(L))

    p_end = check_pins(desk, "end")
    result["pins"]["end"] = p_end
    result["runtime_s"] = round(time.time() - t_all, 1)
    (HERE / "result.json").write_text(json.dumps(result, indent=1, default=str))
    log(f"# total runtime {result['runtime_s']}s")
    log(f"# pins match at start and end: "
        f"{p_start == p_end == {'bm_ref.py': PIN_BM, 'adapter.py': PIN_AD}}")


if __name__ == "__main__":
    main()
