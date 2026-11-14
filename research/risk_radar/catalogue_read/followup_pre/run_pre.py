#!/usr/bin/env python3
"""Risk Radar follow-up PRE read: R-off confluence k=3 (rr-roff-confluence-k3-followup).

_ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(_ROOT))

Bounded research worker. Paper-only: nothing sizes, ranks or executes.

Decisive PRE read of the frozen follow-up set (FOLLOWUP_DECLARATION.md, 2026-11-12 10:22Z;
ledger row rr-roff-confluence-k3-followup). Selected after seeing D. No hold-out.

Usage:
    python3 run_pre.py --desk <path-to-desk-v4>
    ROTATION_DESK=<path> python3 run_pre.py
    RR_DRY=1 python3 run_pre.py --desk <desk>     # 50 draws, pipeline check only

Two-phase import (the fix; mirrors catalogue_read/v2/run_read_v2.py):
  1. build the alerts from Macro's engine (its inputs carry the point-in-time FRED replay);
  2. purge `engine*` from sys.modules and drop the Macro root + cwd from sys.path;
  3. load the desk kit;
  4. assert `pivots.__file__` really is under the desk path.
Both trees expose a top-level `engine`, so without the purge the scorer silently resolves to
the worktree copy.

Writes ONLY into this directory: result.json, SUMMARY.md, RUN_LOG.txt.
The desk is read-only (import only); trials.jsonl is never appended.
Nothing after 2019-12-31 enters any alert, turn or outcome; asserted below.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
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

PIN_BM = "c5130e9e2f80c9da3ff85d66a9f3070367f02e71c10d3e411205a97f12a9f066"
PIN_AD = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"

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


def pins(desk: Path) -> dict:
    return {"bm_ref.py": sha256(desk / "catalogue" / "bm_ref.py"),
            "adapter.py": sha256(desk / "catalogue" / "adapter.py")}


def check_pins(desk: Path, when: str) -> dict:
    p = pins(desk)
    log(f"[{when}] bm_ref.py {p['bm_ref.py']}")
    log(f"[{when}] adapter.py {p['adapter.py']}")
    if p["bm_ref.py"] != PIN_BM:
        raise SystemExit(f"PIN MISMATCH bm_ref.py {p['bm_ref.py']} != {PIN_BM}; STOP")
    if p["adapter.py"] != PIN_AD:
        raise SystemExit(f"PIN MISMATCH adapter.py {p['adapter.py']} != {PIN_AD}; STOP")
    return p


# ------------------------------------------------------------------ phase 1: Macro alerts
def build_alert_full():
    """The k=3 confluence alert on the engine's own calendar, full history, shifted t+1.

    sigs = engine.risk_radar.leading_signals() (trailing 504-session causal percentiles), then
    availability.pit_signals(sigs, start='2006-01-03') (point-in-time FRED replay). n_on = number
    of the 12 legs with sigs[leg] >= thr (a NaN leg counts off); alert = n_on >= 3. The shift is
    applied on the FULL series, then the caller windows it.
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
        on = (pit[leg] >= thr).fillna(False).astype(bool)
        n_on = n_on + on.astype(int)
        avail = avail + pit[leg].notna().astype(int)
    alert = n_on >= K
    full = alert.shift(1, fill_value=False).astype(bool)
    return full, n_on, avail, pit


def window_alert(full: pd.Series, levels: dict, series: list) -> tuple[dict, dict]:
    """One copy per series, reindexed to that series' own sessions as r1g/v2 window.

    lo = max(0, searchsorted(START) - PRE); take that series' sessions up to 2019-12-31 and carry
    the last known alert state forward (method='ffill'). The alert lives on the SPY calendar; a
    series' own session not on it inherits the prior state.
    """
    out, px = {}, {}
    for n in series:
        idx = levels[n].index
        sp = int(idx.searchsorted(START))
        lo = max(0, sp - PRE)
        ai = idx[lo:]
        ai = ai[ai <= END]
        if len(ai) == 0:
            raise SystemExit(f"empty window for {n}")
        a = full.reindex(ai, method="ffill")
        if a.isna().any():
            raise SystemExit(f"alert has NaN after reindex for {n}")
        out[n] = a.astype(bool)
        px[n] = levels[n].reindex(ai)
        assert out[n].index.max() <= END and px[n].index.max() <= END, n
    return out, px


# ------------------------------------------------------------------ phase 2: desk kit
def purge_engine() -> None:
    for m in [m for m in sys.modules if m == "engine" or m.startswith("engine.")]:
        del sys.modules[m]


def load_desk_kit(desk: Path):
    """Drop the Macro root/cwd, purge `engine`, then let the desk's vendored kit resolve."""
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


# ------------------------------------------------------------------ PRE context
def build_pre_context(A, BM, specs: dict, series: list):
    """PRE context built directly: bm_ref.build_context hard-codes block='D'.

    The catalogue is truncated at 2019-12-31 first, so no post-2019 trough or recovery can
    define an in-episode span (no leak). Turns are then restricted to [START, END].
    """
    df = A.load_pivots()
    df_pre = df[df["date"] <= END].copy()
    assert pd.to_datetime(df_pre["date"]).max() <= END
    rows = A.select(df_pre, type="risk_off", tier="major", block="PRE")
    rows_dir = rows[[BM._direction_of(r) == "top" for _, r in rows.iterrows()]].copy()
    # Truncate the LEVEL series at END too: a peak on 2019-12-31 would otherwise take its
    # episode onset (next session) from 2020-01-02. This is the PRE analogue of the desk's own
    # 2023-12-29 spec cutoff, and leaves every windowed session identical.
    levels = {}
    for n in series:
        s = BM.level_series(specs[n])
        levels[n] = s[s.index <= END]
        if len(levels[n]) == 0:
            raise SystemExit(f"empty level series for {n}")
    episodes = A.build_episodes_for_series(df_pre, series, tier="major", calendar=None,
                                           levels=levels, episode_rule="swing")
    turns_all = BM.build_turns(rows_dir, episodes)
    turns = BM.turns_in_window(turns_all, START, END)
    # leak guards
    assert turns, "no PRE turns in window"
    assert max(pd.Timestamp(t.date) for t in turns) <= END
    for a, eps in episodes.items():
        for e in eps:
            for d in (e.onset, e.trough, e.recovery):
                assert d is None or pd.Timestamp(d) <= END, (a, d)
    return rows_dir, levels, episodes, turns


# ------------------------------------------------------------------ scoring jobs (parallel)
_G: dict = {}


def _job(spec: dict) -> dict:
    BM = _G["BM"]
    A = _G["A"]
    kind = spec["kind"]
    t0 = time.time()
    if kind == "p90":
        out = BM.cluster_placebo_p90(_G["turns"], _G["alerts"], _G["episodes"], _G["px"],
                                     kind="top", outcomes_through=END, n_draws=N_DRAWS,
                                     seed=SEED, tol=TOL, pre=PRE, post=POST, min_off=MIN_OFF)
        out["_runtime_s"] = round(time.time() - t0, 1)
        return out

    # include_passes=False: the per-asset near-turn placebo is not part of the set-level
    # criteria, and every table field comes from the deterministic scorer.
    if kind == "candidate":
        alerts, px = _G["alerts"], _G["px"]
        row = BM.score_alerts(_G["turns"], alerts, _G["episodes"], px, direction="top",
                              post=POST, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                              min_off=MIN_OFF, include_passes=False)
    elif kind == "ref":
        levels = _G["levels"]
        ref = BM.build_reference(levels, _G["alerts"], direction="top", form=spec["form"],
                                 start_d=START, pre=PRE, shift=1, end_d=END)
        for a, s in ref["alerts"].items():
            assert s.index.max() <= END, (a, s.index.max())
        px = {a: levels[a].reindex(ref["alerts"][a].index) for a in ref["alerts"]}
        row = BM.score_alerts(_G["turns"], ref["alerts"], _G["episodes"], px, direction="top",
                              post=POST, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                              min_off=MIN_OFF, include_passes=False)
        row["match"] = {"form": spec["form"], "x": ref["x"],
                        "target_budget": ref["target_budget"],
                        "achieved_share": ref["achieved_share"], "budget": ref["budget"]}
    elif kind == "leg":
        alerts = _G["leg_alerts"][spec["leg"]]
        px = _G["leg_px"][spec["leg"]]
        row = BM.score_alerts(_G["turns"], alerts, _G["episodes"], px, direction="top",
                              post=POST, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                              min_off=MIN_OFF, include_passes=False)
    else:
        raise SystemExit(f"bad job kind {kind!r}")
    row["_runtime_s"] = round(time.time() - t0, 1)
    return row


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=os.environ.get("ROTATION_DESK"))
    ns = ap.parse_args()
    if not ns.desk:
        raise SystemExit("desk path required: --desk <path> or ROTATION_DESK")
    desk = Path(ns.desk).resolve()

    RUN_LOG.write_text("")
    log(f"# Risk Radar follow-up PRE read (R-off confluence k={K})")
    log(f"# desk: {desk}")
    log(f"# dry={DRY} n_draws={N_DRAWS} window={START.date()}..{END.date()}")
    p_start = check_pins(desk, "start")

    t_all = time.time()

    # --- phase 1: alerts from Macro's engine (before the desk inserts its own paths)
    log("building alerts (leading_signals + pit_signals start 2006-01-03)")
    alert_full, n_on, avail, pit = build_alert_full()

    # --- phase 2: the desk's vendored scorer must win (purge `engine`, drop Macro paths)
    A, BM, pv, pv_path = load_desk_kit(desk)
    log(f"# scorer module: {pv_path}")
    assert str(pv_path).startswith(str(desk))

    # --- PRE context
    from catalogue import build as B
    specs = {s.name: s for s in B.build_specs(B.CUTOFF)[0]}
    df = A.load_pivots()
    pre_rows = A.select(df[df["date"] <= END], type="risk_off", tier="major", block="PRE")
    series = sorted(pre_rows["series"].unique())
    rows_dir, levels, episodes, turns = build_pre_context(A, BM, specs, series)

    t_min = min(pd.Timestamp(t.date) for t in turns)
    t_max = max(pd.Timestamp(t.date) for t in turns)
    log(f"# series: {len(series)}")
    log(f"# turns in window: {len(turns)}  {t_min.date()} .. {t_max.date()}")

    alerts, px = window_alert(alert_full, levels, series)
    log(f"# alert window per series: {len(alerts[series[0]])} sessions, "
        f"{alerts[series[0]].index.min().date()} .. {alerts[series[0]].index.max().date()}")

    # one shifted full series per leg, then the same windowing
    leg_alerts, leg_px = {}, {}
    for leg, thr in LEGS.items():
        leg_full = (pit[leg] >= thr).fillna(False).astype(bool).shift(1, fill_value=False)
        la, lpx = window_alert(leg_full, levels, series)
        leg_alerts[leg], leg_px[leg] = la, lpx

    # --- shared globals for the forked workers
    _G.update(A=A, BM=BM, turns=turns, alerts=alerts, px=px, episodes=episodes,
              levels=levels, leg_alerts=leg_alerts, leg_px=leg_px)

    jobs = [{"kind": "candidate"}]
    jobs += [{"kind": "ref", "form": f} for f in ("dd", "near")]
    jobs += [{"kind": "leg", "leg": leg} for leg in LEGS]
    jobs += [{"kind": "p90"}]

    log(f"# {len(jobs)} jobs, {min(16, len(jobs))} processes, {N_DRAWS} draws")
    results = {}
    with ProcessPoolExecutor(max_workers=min(16, len(jobs))) as ex:
        futs = {ex.submit(_job, j): j for j in jobs}
        for fut in as_completed(futs):
            j = futs[fut]
            key = ("p90" if j["kind"] == "p90" else
                   "candidate" if j["kind"] == "candidate" else
                   f"ref_{j['form']}" if j["kind"] == "ref" else f"leg_{j['leg']}")
            r = fut.result()
            results[key] = r
            if key == "p90":
                log(f"  p90 {r['p90']} observed {r['observed_cluster_share']} "
                    f"({r['_runtime_s']}s)")
            else:
                log(f"  {key:22s} share {r['cluster_share']} false "
                    f"{r['false_per_asset_year']} ({r['_runtime_s']}s)")

    cand = results["candidate"]
    refs = {f: results[f"ref_{f}"] for f in ("dd", "near")}
    singles = {leg: results[f"leg_{leg}"] for leg in LEGS}
    p90 = results["p90"]
    bm = BM.better_reference(refs["dd"], refs["near"])
    bm_form = bm["match"]["form"]
    best_leg = sorted(singles, key=lambda k: (-(singles[k]["cluster_share"] or 0.0),
                                              singles[k]["false_per_asset_year"] or 0.0))[0]
    best_single = singles[best_leg]
    verdict = BM.set_level_pass(cand, bm, p90["p90"], best_single, is_confluence=True)
    log(f"# better reference: {bm_form}; best single: {best_leg}")
    log(f"# verdict {json.dumps(verdict)}")

    # --- cluster date range: replicate pv.summarise's exact key scheme (deterministic, no draws)
    det = pv.score_pivots_multi(turns, alerts, episodes, outcomes_through=END,
                                posts=(POST,), pre=PRE, min_off=MIN_OFF)
    pooled = [r for _a, v in sorted(det["by_post"][f"post{POST}"]["by_asset"].items())
              for r in v["turns"]]
    scored = [r for r in pooled if r["kind"] == "top" and r["status"] == "scored"]
    cl_dates: dict = {}
    for i, r in enumerate(scored):
        key = r.get("cluster_id") or f"__{r.get('asset')}_{r['date']}_{i}"
        cl_dates.setdefault(key, []).append(pd.Timestamp(r["date"]))
    assert len(cl_dates) == cand["clusters_scored"], (len(cl_dates), cand["clusters_scored"])
    cl_min = min(min(v) for v in cl_dates.values())
    cl_max = max(max(v) for v in cl_dates.values())
    assert cl_max <= END and t_max <= END

    # --- alert share and available legs by year (description; engine calendar)
    win = (alert_full.index >= START) & (alert_full.index <= END)
    a_w = alert_full[win]
    share_by_year = {int(y): round(float(v), 4) for y, v in a_w.groupby(a_w.index.year).mean().items()}
    av_w = avail[win]
    legs_by_year = {int(y): round(float(v), 2)
                    for y, v in av_w.groupby(av_w.index.year).mean().items()}

    def slim(r: dict) -> dict:
        return {k: r.get(k) for k in
                ("turns_scored", "turns_flagged", "turn_share", "turn_share_ci90",
                 "clusters_scored", "clusters_flagged", "cluster_share",
                 "cluster_share_ci90", "median_delay", "censored", "false_per_asset_year",
                 "alert_budget", "_runtime_s")}

    result = {
        "id": "rr-roff-confluence-k3-followup",
        "label": "selected after seeing D; decisive PRE read; next: desk attack seat; "
                 "forward candidate only (no hold-out)",
        "pins": {"start": p_start, "end": None},
        "scorer_module": str(pv_path),
        "window": {"start": str(START.date()), "end": str(END.date()), "pre": PRE, "post": POST,
                   "k": K, "n_draws": N_DRAWS, "seed": SEED, "tol": TOL, "min_off": MIN_OFF,
                   "dry": DRY},
        "series": series,
        "turns": {"n": len(turns), "min": str(t_min.date()), "max": str(t_max.date())},
        "clusters": {"n": cand["clusters_scored"], "flagged": cand["clusters_flagged"],
                     "min_turn_date": str(cl_min.date()), "max_turn_date": str(cl_max.date())},
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
        "alert_share_by_year": share_by_year,
        "available_legs_by_year": legs_by_year,
        "deviations": [
            "bm_ref.build_context hard-codes block='D' via _family_rows, so "
            "turns_in_window(build_context(...)['turns'], 2006, 2019) would be empty. The PRE "
            "context is built directly: A.select(..., block='PRE') on the catalogue truncated at "
            "2019-12-31, swing episodes from the same truncated rows, bm_ref.build_turns + "
            "turns_in_window.",
            "bm_ref.reference_result does not forward start_d/end_d; build_reference + "
            "score_alerts are called directly with start_d=2006-01-03, end_d=2019-12-31.",
            "Episodes are built from catalogue rows truncated at 2019-12-31, so no post-2019 "
            "trough or recovery can define an in-episode span (the PRE analogue of the "
            "catalogue's own 2023-12-29 truncation).",
            "The alert is built on the engine's SPY-session calendar and reindexed onto each "
            "series' own level index with method='ffill' (r1g/v2 windowing).",
            "score_alerts bounds outcomes_through at the adapter's END_D (2023-12-29); the bound "
            "is inert here because every scored alert, turn, price and episode date is "
            "<= 2019-12-31 (asserted).",
            "Two-phase import fix: Macro's `engine` is purged and the Macro root + cwd are dropped "
            "from sys.path before the desk kit loads, so pivots resolves under the desk (the dead "
            "worker's run had it resolving to the worktree copy).",
            "The window's first 21 sessions precede 2006-01-03, so the FRED legs there are the "
            "engine's pre-start (one-session-shifted) values, not the PIT replay, which begins "
            "2006-01-03 per the ledger row.",
        ],
        "runtime_s": None,
    }

    # ------------------------------------------------------------------ SUMMARY.md
    def f(v, nd=3):
        return "—" if v is None else f"{v:.{nd}f}"

    def ci(v):
        return "—" if not v else f"[{v[0]:.3f}, {v[1]:.3f}]"

    L = []
    L.append("# Risk Radar follow-up — R-off confluence k=3 (PRE)\n")
    L.append(f"Ledger row `rr-roff-confluence-k3-followup`. Window {START.date()}..{END.date()}, "
             f"pre {PRE}, post {POST}, seed {SEED}, {N_DRAWS} draws, tol {TOL}, "
             f"min_off {MIN_OFF}." + ("  **DRY RUN (50 draws).**" if DRY else "") + "\n")
    L.append("## Pins\n")
    L.append(f"- `bm_ref.py` `{p_start['bm_ref.py']}`")
    L.append(f"- `adapter.py` `{p_start['adapter.py']}`")
    L.append(f"- scorer module: `{pv_path}`\n")
    L.append("## Verdict\n")
    L.append("**selected after seeing D; decisive PRE read; next: desk attack seat; "
             "forward candidate only (no hold-out)**\n")
    L.append("| criterion | met |")
    L.append("|---|---|")
    L.append(f"| (a) cluster share > near-turn placebo p90 at cluster level ({f(p90['p90'])}) "
             f"| {verdict['a']} |")
    L.append(f"| (b) > better reference ({bm_form}) at <= false rate | {verdict['b']} |")
    L.append(f"| (c) > best single leg ({best_leg}) at <= false rate | {verdict['c']} |")
    L.append("")
    L.append(f"**criteria_met:** {verdict['criteria_met']}  ")
    L.append(f"**nomination:** {verdict['nomination']}\n")

    L.append("## Table — candidate, better reference, 12 single legs\n")
    L.append("| set | cluster share | 90% CI | median delay | false/asset-yr | alert share |")
    L.append("|---|---|---|---|---|---|")
    L.append(f"| **candidate k={K}** | {f(cand['cluster_share'])} "
             f"| {ci(cand['cluster_share_ci90'])} | {f(cand['median_delay'], 1)} "
             f"| {f(cand['false_per_asset_year'])} | {f(cand['alert_budget'])} |")
    for form in ("dd", "near"):
        r = refs[form]
        mark = " **(better)**" if form == bm_form else ""
        L.append(f"| ref {form}{mark} | {f(r['cluster_share'])} "
                 f"| {ci(r['cluster_share_ci90'])} | {f(r['median_delay'], 1)} "
                 f"| {f(r['false_per_asset_year'])} | {f(r['alert_budget'])} |")
    for leg in sorted(singles, key=lambda k: -(singles[k]["cluster_share"] or 0.0)):
        r = singles[leg]
        L.append(f"| leg {leg} | {f(r['cluster_share'])} | {ci(r['cluster_share_ci90'])} "
                 f"| {f(r['median_delay'], 1)} | {f(r['false_per_asset_year'])} "
                 f"| {f(r['alert_budget'])} |")
    L.append("")

    L.append("## Turns and clusters\n")
    L.append(f"- turns scored: {cand['turns_scored']} (flagged {cand['turns_flagged']}), "
             f"dates {t_min.date()} .. {t_max.date()}")
    L.append(f"- clusters scored: {cand['clusters_scored']} "
             f"(flagged {cand['clusters_flagged']}), turn dates {cl_min.date()} .. {cl_max.date()}")
    L.append(f"- censored turns: {cand['censored']}")
    L.append(f"- near-turn placebo p90 (cluster): {f(p90['p90'])}; observed {f(p90['observed_cluster_share'])}; "
             f"{p90['n_valid_draws']} valid draws\n")

    L.append("## Alert share and available legs by year (description)\n")
    L.append("| year | alert share | mean legs available |")
    L.append("|---|---|---|")
    for y in sorted(share_by_year):
        L.append(f"| {y} | {share_by_year[y]:.4f} | {legs_by_year[y]:.2f} |")
    L.append("")

    L.append("## Matched threshold x per series\n")
    L.append("| series | dd x | near x |")
    L.append("|---|---|---|")
    for n in series:
        L.append(f"| {n} | {refs['dd']['match']['x'][n]:.4f} "
                 f"| {refs['near']['match']['x'][n]:.4f} |")
    L.append("")

    L.append("## Deviations\n")
    for d in result["deviations"]:
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
