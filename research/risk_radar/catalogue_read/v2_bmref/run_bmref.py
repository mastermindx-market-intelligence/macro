#!/usr/bin/env python3
"""Risk Radar BM-REF description read: the five -v2 sets on block D, against the budget-matched
mechanical reference (desk rule H20).

_ROOT = Path(__file__).resolve().parents[4]; sys.path.insert(0, str(_ROOT))

Bounded research worker. Paper-only: nothing sizes, ranks or executes.
DESCRIPTION ONLY: every row below was seen before the set-level definition and is not a
nomination; the `nomination` boolean is reported as description, not as a verdict.

Usage:
    python3 run_bmref.py --desk <path-to-desk-v4>
    ROTATION_DESK=<path> python3 run_bmref.py

Pins are checked at start and end; any mismatch stops the run.

Alerts are reused verbatim from ../v2/run_read_v2.py (the five set builders, same
`full.shift(1, fill_value=False)` before the same windowing). Contexts, references and the
set-level pass come from the desk's pinned `catalogue/bm_ref.py`. Nothing after 2023-12-29
enters any alert, turn or outcome; asserted below.

Writes ONLY into this directory: result.json, SUMMARY.md, RUN_LOG.txt.
The desk is read-only (import only); trials.jsonl is never appended.
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

START_D = pd.Timestamp("2020-01-02")
END_D = pd.Timestamp("2023-12-29")
SEED = 20261112
DRY = bool(os.environ.get("RR_DRY"))
N_DRAWS = 20 if DRY else 2000
TOL = 0.01
PRE = 21
MIN_OFF = 10
SHIFT = 1

PIN_BM = "c5130e9e2f80c9da3ff85d66a9f3070367f02e71c10d3e411205a97f12a9f066"
PIN_AD = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"

ROW_LABEL = "seen before the set-level definition, not a nomination"

# set id -> (family, alert key, confluence?)
SETS = [
    ("rr-roff-incumbent-v2", "R-off", "incumbent", False),
    ("rr-roff-confluence-k4-v2", "R-off", "confluence_k4", True),
    ("rr-ron-incumbent-v2", "R-on", "incumbent", False),
    ("rr-ron-confluence-k4-v2", "R-on", "confluence_k4", True),
    ("rr-ron-exit-v1-v2", "R-on", "exit_v1", False),
]
FAMILY = {"R-off": ("top", 5), "R-on": ("bottom", 10)}


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


# ------------------------------------------------------------------ phase 1: v2 alerts
def purge_engine() -> None:
    for m in [m for m in sys.modules if m == "engine" or m.startswith("engine.")]:
        del sys.modules[m]


def load_v2():
    """The five set builders, reused exactly as they are (same shift, same windowing)."""
    import importlib.util as iu
    p = HERE.parent / "v2" / "run_read_v2.py"
    spec = iu.spec_from_file_location("rr_run_read_v2", str(p))
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    s = iu.spec_from_file_location("rr_ledger_rows", str(HERE.parent / "ledger_rows.py"))
    LR = iu.module_from_spec(s)
    s.loader.exec_module(LR)
    if set(mod.LEGS) != set(LR.LEGS):
        raise SystemExit("v2 LEGS and ledger_rows LEGS differ")
    return mod, dict(LR.LEGS)


def build_alerts(V2, ledger_legs: dict) -> dict:
    sys.path.insert(0, str(_ROOT))
    purge_engine()
    t0 = time.time()
    out = V2.build_alerts(ledger_legs)
    log(f"  v2 alerts built: {time.time() - t0:.1f}s; {len(out)} series; "
        f"calendar {out['incumbent'].index.min().date()} .. {out['incumbent'].index.max().date()}")
    return out


# ------------------------------------------------------------------ phase 2: desk kit
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


# ------------------------------------------------------------------ candidate alerts for one set
def window_set(V2, src: pd.Series, ctx: dict):
    """v2.window_alert per series: full-series shift-1, then the D window (r1g)."""
    alerts, px = {}, {}
    for n in ctx["series"]:
        p_, a_ = V2.window_alert(src, ctx["levels"][n], True)
        alerts[n], px[n] = a_, p_
        if a_.index.max() > END_D:
            raise SystemExit(f"alert past end for {n}: {a_.index.max()}")
        if a_.isna().any():
            raise SystemExit(f"alert has NaN for {n}")
    return alerts, px


# ------------------------------------------------------------------ scoring jobs (fork)
_G: dict = {}


def _job(spec: dict) -> dict:
    BM, A = _G["BM"], _G["A"]
    t0 = time.time()
    fam = spec["family"]
    direction, post = FAMILY[fam]
    ctx = _G["ctx"][fam]
    alerts, px = (_G["sets"][spec["set"]] if spec["kind"] in ("candidate", "p90", "ref")
                  else (None, None))
    if spec["kind"] == "candidate":
        row = BM.score_alerts(ctx["turns"], alerts, ctx["episodes"], px, direction=direction,
                              post=post, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                              min_off=MIN_OFF, include_passes=True)
        row["alert_share_by_series"] = {a: float(alerts[a].mean()) for a in alerts}
    elif spec["kind"] == "ref":
        ref = BM.build_reference(ctx["levels"], alerts, direction=direction, form=spec["form"],
                                 start_d=START_D, pre=PRE, shift=SHIFT, end_d=END_D)
        for a, s in ref["alerts"].items():
            if s.index.max() > END_D:
                raise SystemExit(f"reference past end for {a}: {s.index.max()}")
        rpx = {a: ctx["levels"][a].reindex(ref["alerts"][a].index) for a in ref["alerts"]}
        row = BM.score_alerts(ctx["turns"], ref["alerts"], ctx["episodes"], rpx,
                              direction=direction, post=post, n_draws=N_DRAWS, seed=SEED,
                              tol=TOL, pre=PRE, min_off=MIN_OFF, include_passes=True)
        row["match"] = {"form": spec["form"], "x": ref["x"],
                        "target_budget": ref["target_budget"],
                        "achieved_share": ref["achieved_share"], "budget": ref["budget"]}
    elif spec["kind"] == "leg":
        la, lpx = _G["legs"][fam][spec["leg"]]
        row = BM.score_alerts(ctx["turns"], la, ctx["episodes"], lpx, direction=direction,
                              post=post, n_draws=N_DRAWS, seed=SEED, tol=TOL, pre=PRE,
                              min_off=MIN_OFF, include_passes=True)
    elif spec["kind"] == "p90":
        row = BM.cluster_placebo_p90(ctx["turns"], alerts, ctx["episodes"], px, kind=direction,
                                     outcomes_through=END_D, n_draws=N_DRAWS, seed=SEED,
                                     tol=TOL, pre=PRE, post=post, min_off=MIN_OFF)
    else:
        raise SystemExit(f"bad job kind {spec['kind']!r}")
    row["_runtime_s"] = round(time.time() - t0, 1)
    return row


# ------------------------------------------------------------------ cross-check vs v2 results.csv
def cross_check(cands: dict, csv_path: Path) -> dict:
    tab = pd.read_csv(csv_path)
    out = {}
    for set_id, fam, key, _conf in SETS:
        r = tab[(tab["family"] == fam) & (tab["set"] == key) & (tab["role"] == "set")]
        if len(r) != 1:
            out[set_id] = {"found": False}
            continue
        r = r.iloc[0]
        c = cands[set_id]
        d_share = (None if c["cluster_share"] is None else
                   round(float(c["cluster_share"]) - float(r["cluster_share"]), 10))
        d_false = (None if c["false_per_asset_year"] is None else
                   round(float(c["false_per_asset_year"]) - float(r["false_per_asset_year"]), 10))
        out[set_id] = {"found": True,
                       "csv_cluster_share": float(r["cluster_share"]),
                       "ours_cluster_share": c["cluster_share"],
                       "csv_false_per_asset_year": float(r["false_per_asset_year"]),
                       "ours_false_per_asset_year": c["false_per_asset_year"],
                       "share_diff": d_share, "false_diff": d_false,
                       "match": bool(d_share == 0 and d_false == 0)}
    return out


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=os.environ.get("ROTATION_DESK"))
    ns = ap.parse_args()
    if not ns.desk:
        raise SystemExit("desk path required: --desk <path> or ROTATION_DESK")
    desk = Path(ns.desk).resolve()

    RUN_LOG.write_text("")
    log("# Risk Radar BM-REF description read — five -v2 sets on block D")
    log(f"# desk: {desk}")
    log(f"# window {START_D.date()}..{END_D.date()} pre={PRE} post=primary(5|10) "
        f"seed={SEED} n_draws={N_DRAWS} tol={TOL} min_off={MIN_OFF}")
    p_start = check_pins(desk, "start")
    t_all = time.time()

    # --- phase 1: the five sets, exactly as v2 built them
    V2, ledger_legs = load_v2()
    log("building v2 alerts")
    raw = build_alerts(V2, ledger_legs)

    # --- phase 2: desk kit
    A, BM, pv, pv_path = load_desk_kit(desk)
    scorer_rel = "<desk>/" + str(pv_path.relative_to(desk))
    log(f"# scorer module: {scorer_rel}")

    # --- contexts (bm_ref.build_context hard-codes block='D')
    ctx = {}
    for fam in ("R-off", "R-on"):
        direction, post = FAMILY[fam]
        c = BM.build_context(fam, direction)
        c["turns"] = BM.turns_in_window(c["turns"], START_D, END_D)
        ctx[fam] = c
        tmin = min(pd.Timestamp(t.date) for t in c["turns"])
        tmax = max(pd.Timestamp(t.date) for t in c["turns"])
        assert tmax <= END_D, (fam, tmax)
        for a, eps in c["episodes"].items():
            for e in eps:
                for d in (e.peak, e.onset, e.trough, e.recovery):
                    assert d is None or pd.Timestamp(d) <= END_D, (a, d)
        log(f"# {fam}: series {len(c['series'])}, turns {len(c['turns'])} "
            f"{tmin.date()}..{tmax.date()}")

    # --- window every set's alert onto its family's series
    sets = {}
    for set_id, fam, key, _conf in SETS:
        sets[set_id] = window_set(V2, raw[key], ctx[fam])
        a0 = ctx[fam]["series"][0]
        log(f"# {set_id}: alert ON share by series mean "
            f"{np.mean([sets[set_id][0][n].mean() for n in ctx[fam]['series']]):.4f}")

    # --- 12 legs alone, per family (used only by the confluence sets)
    legs = {}
    for fam in ("R-off", "R-on"):
        legs[fam] = {}
        for leg in V2.LEGS:
            legs[fam][leg] = window_set(V2, raw[f"leg__{leg}"], ctx[fam])

    _G.update(BM=BM, A=A, ctx=ctx, sets=sets, legs=legs)

    jobs = []
    for set_id, fam, key, _conf in SETS:
        jobs.append({"kind": "candidate", "family": fam, "set": set_id})
        for form in ("dd", "near"):
            jobs.append({"kind": "ref", "family": fam, "set": set_id, "form": form})
        jobs.append({"kind": "p90", "family": fam, "set": set_id})
    for fam in ("R-off", "R-on"):
        for leg in V2.LEGS:
            jobs.append({"kind": "leg", "family": fam, "leg": leg})

    log(f"# {len(jobs)} jobs, {min(20, len(jobs))} processes, {N_DRAWS} draws")
    results = {}
    with ProcessPoolExecutor(max_workers=min(20, len(jobs))) as ex:
        futs = {ex.submit(_job, j): j for j in jobs}
        for fut in as_completed(futs):
            j = futs[fut]
            if j["kind"] == "leg":
                k = f"{j['family']}|leg|{j['leg']}"
            elif j["kind"] == "ref":
                k = f"{j['set']}|ref|{j['form']}"
            else:
                k = f"{j['set']}|{j['kind']}"
            r = fut.result()
            results[k] = r
            if j["kind"] == "p90":
                log(f"  p90 {k:34s} {r['p90']} observed {r['observed_cluster_share']} "
                    f"({r['_runtime_s']}s)")
            else:
                log(f"  {k:34s} share {r['cluster_share']} false "
                    f"{r['false_per_asset_year']} ({r['_runtime_s']}s)")

    # ------------------------------------------------------------------ assemble
    def slim(r: dict) -> dict:
        return {kk: r.get(kk) for kk in
                ("turns_scored", "turns_flagged", "turn_share", "turn_share_ci90",
                 "clusters_scored", "clusters_flagged", "cluster_share",
                 "cluster_share_ci90", "median_delay", "censored", "false_per_asset_year",
                 "alert_budget", "_runtime_s")}

    def f(v, nd=3):
        return "—" if v is None else f"{v:.{nd}f}"

    def ci(v):
        return "—" if not v else f"[{v[0]:.3f}, {v[1]:.3f}]"

    out_sets = {}
    cands = {}
    for set_id, fam, key, is_conf in SETS:
        cand = results[f"{set_id}|candidate"]
        cands[set_id] = cand
        refs = {form: results[f"{set_id}|ref|{form}"] for form in ("dd", "near")}
        p90 = results[f"{set_id}|p90"]
        better = BM.better_reference(refs["dd"], refs["near"])
        bform = better["match"]["form"]
        singles = {leg: results[f"{fam}|leg|{leg}"] for leg in V2.LEGS} if is_conf else None
        best_leg, best_single = None, None
        if is_conf:
            best_leg = sorted(singles, key=lambda kk: (-(singles[kk]["cluster_share"] or 0.0),
                                                       singles[kk]["false_per_asset_year"] or 0.0))[0]
            best_single = singles[best_leg]
        verdict = BM.set_level_pass(cand, better, p90["p90"], best_single,
                                    is_confluence=is_conf)
        out_sets[set_id] = {
            "family": fam, "direction": FAMILY[fam][0], "primary_post": FAMILY[fam][1],
            "alert_key": key, "is_confluence": is_conf, "row_label": ROW_LABEL,
            "candidate": slim(cand),
            "references": {form: {**slim(refs[form]),
                                  "x": refs[form]["match"]["x"],
                                  "achieved_share": refs[form]["match"]["achieved_share"],
                                  "target_budget": refs[form]["match"]["target_budget"]}
                           for form in ("dd", "near")},
            "better_reference": bform,
            "placebo_p90": p90,
            "singles": ({kk: slim(singles[kk]) for kk in V2.LEGS} if is_conf else None),
            "best_single_leg": best_leg,
            "verdict": verdict,
        }
        log(f"# {set_id}: better {bform}; best single {best_leg}; "
            f"verdict {json.dumps(verdict)}")

    # --- determinism / end-bound proof on the scored turn rows
    bound = {}
    for set_id, fam, key, _conf in SETS:
        direction, post = FAMILY[fam]
        alerts, _px = sets[set_id]
        det = pv.score_pivots_multi(ctx[fam]["turns"], alerts, ctx[fam]["episodes"],
                                    outcomes_through=END_D, posts=(post,), pre=PRE,
                                    min_off=MIN_OFF)
        rows = [r for _a, v in sorted(det["by_post"][f"post{post}"]["by_asset"].items())
                for r in v["turns"]]
        assert all(pd.Timestamp(r["date"]) <= END_D for r in rows), set_id
        scored = [r for r in rows if r["kind"] == direction and r["status"] == "scored"]
        n_sum = det["by_post"][f"post{post}"][direction]["n_turns"]
        assert len(scored) == n_sum == cands[set_id]["turns_scored"], (
            set_id, len(scored), n_sum, cands[set_id]["turns_scored"])
        cl_max = max((pd.Timestamp(r["date"]) for r in scored), default=None)
        bound[set_id] = {"scored_turn_max": str(cl_max.date()) if cl_max else None,
                         "n_scored": len(scored),
                         "all_rows_end_by": str(END_D.date())}
    assert all(v["scored_turn_max"] is None or v["scored_turn_max"] <= "2023-12-29"
               for v in bound.values())

    xcheck = cross_check(cands, HERE.parent / "v2" / "results.csv")
    log("# cross-check vs v2/results.csv: "
        + json.dumps({k: v.get("match") for k, v in xcheck.items()}))

    deviations = [
        "bm_ref.reference_result does not forward start_d/end_d, so each reference is built with "
        "build_reference(..., start_d='2020-01-02', pre=21, shift=1, end_d='2023-12-29') + "
        "score_alerts directly, the same path reference_result takes with its defaults.",
        "Alerts are reused verbatim from v2/run_read_v2.py (build_alerts + window_alert): the t+1 "
        "shift is applied to the full series before the D window is cut, exactly as v2/r1g.",
        "bm_ref.build_context hard-codes block='D'; turns are restricted to "
        "turns_in_window(ctx['turns'], 2020-01-02, 2023-12-29) (a no-op here: the catalogue's rows "
        "are already block D).",
        "ns: each set has its own p90 because the placebo draws depend on that candidate's own "
        "alert run lengths.",
        "include_passes=True is used so run_pass_line's require_activity=True pass line is present; "
        "the reported cluster share and false rate come from the deterministic score_pivots_multi.",
        "DESCRIPTION ONLY: every row was seen before the set-level definition and is not a "
        "nomination; the `nomination` boolean is reported as description.",
    ]

    result = {
        "id": "rr-bmref-five-sets-D",
        "label": "description read, block D; every row is " + ROW_LABEL,
        "pins": {"start": p_start, "end": None},
        "scorer_module": scorer_rel,
        "window": {"start": str(START_D.date()), "end": str(END_D.date()), "pre": PRE,
                   "n_draws": N_DRAWS, "seed": SEED, "tol": TOL, "min_off": MIN_OFF,
                   "shift": SHIFT, "primary_post": {"R-off": 5, "R-on": 10}},
        "turns": {fam: {"n": len(ctx[fam]["turns"]),
                        "min": str(min(pd.Timestamp(t.date) for t in ctx[fam]["turns"]).date()),
                        "max": str(max(pd.Timestamp(t.date) for t in ctx[fam]["turns"]).date())}
                  for fam in ("R-off", "R-on")},
        "series": {fam: ctx[fam]["series"] for fam in ("R-off", "R-on")},
        "sets": out_sets,
        "end_bound_proof": bound,
        "cross_check": xcheck,
        "deviations": deviations,
        "runtime_s": None,
    }

    # ------------------------------------------------------------------ SUMMARY.md
    L = []
    L.append("# Risk Radar — BM-REF description read, five `-v2` sets on block D\n")
    L.append(f"Window {START_D.date()}..{END_D.date()}, pre {PRE}, primary post 5 (R-off) / "
             f"10 (R-on), seed {SEED}, {N_DRAWS} draws, tol {TOL}, min_off {MIN_OFF}. "
             f"Paper-only; nothing sizes, ranks or executes.\n")
    L.append(f"**Every row below is {ROW_LABEL}.** The `nomination` boolean is description, "
             f"not a verdict.\n")
    L.append("## Pins\n")
    L.append(f"- `bm_ref.py` `{p_start['bm_ref.py']}`")
    L.append(f"- `adapter.py` `{p_start['adapter.py']}`")
    L.append(f"- scorer module: `{scorer_rel}`\n")

    L.append("## Cross-check vs `v2/results.csv` (shifted set rows)\n")
    L.append("| set | csv cluster share | ours | csv false/yr | ours | match |")
    L.append("|---|---|---|---|---|---|")
    for set_id, _f, _k, _c in SETS:
        x = xcheck[set_id]
        if not x.get("found"):
            L.append(f"| {set_id} | — | — | — | — | not found |")
            continue
        L.append(f"| {set_id} | {x['csv_cluster_share']:.4f} | {x['ours_cluster_share']:.4f} "
                 f"| {x['csv_false_per_asset_year']:.4f} | "
                 f"{x['ours_false_per_asset_year']:.4f} | {x['match']} |")
    L.append("")

    for set_id, fam, key, is_conf in SETS:
        d = out_sets[set_id]
        c = d["candidate"]
        L.append(f"## {set_id} — {fam} ({d['direction']}), post {d['primary_post']}, "
                 f"alert `{key}`\n")
        L.append(f"*{ROW_LABEL}.*\n")
        L.append("| row | cluster share | 90% CI | median delay | false/asset-yr | "
                 "alert share |")
        L.append("|---|---|---|---|---|---|")
        L.append(f"| **candidate** | {f(c['cluster_share'])} | {ci(c['cluster_share_ci90'])} "
                 f"| {f(c['median_delay'], 1)} | {f(c['false_per_asset_year'])} "
                 f"| {f(c['alert_budget'])} |")
        for form in ("dd", "near"):
            r = d["references"][form]
            mark = " **(better)**" if form == d["better_reference"] else ""
            L.append(f"| ref {form}{mark} | {f(r['cluster_share'])} "
                     f"| {ci(r['cluster_share_ci90'])} | {f(r['median_delay'], 1)} "
                     f"| {f(r['false_per_asset_year'])} | {f(r['alert_budget'])} |")
        if is_conf:
            leg = d["best_single_leg"]
            r = d["singles"][leg]
            L.append(f"| best single leg `{leg}` | {f(r['cluster_share'])} "
                     f"| {ci(r['cluster_share_ci90'])} | {f(r['median_delay'], 1)} "
                     f"| {f(r['false_per_asset_year'])} | {f(r['alert_budget'])} |")
        L.append("")
        L.append(f"- better reference: **{d['better_reference']}**")
        for form in ("dd", "near"):
            r = d["references"][form]
            tgt = float(np.mean(list(r["target_budget"].values())))
            ach = float(np.mean(list(r["achieved_share"].values())))
            gap = ("" if abs(ach - tgt) <= 0.01 else
                   " — **budget capped: the >=5% bottom gate makes the candidate's ON share "
                   "unreachable, so this reference runs a smaller budget than the candidate**")
            L.append(f"- ref {form} budget: target {tgt:.4f}, achieved {ach:.4f}{gap}")
        dd_, nr_ = d["references"]["dd"], d["references"]["near"]
        if (dd_["cluster_share"] == nr_["cluster_share"]
                and dd_["false_per_asset_year"] == nr_["false_per_asset_year"]):
            L.append("- note: the `dd` and `near` forms scored identically here (same cluster share "
                     "and false rate); under the bottom gate `<` vs `<=` on `r` separates the two "
                     "forms only at an exact tie, which the matched thresholds did not hit")
        L.append(f"- near-turn placebo p90 (cluster): {f(d['placebo_p90']['p90'])}; observed "
                 f"{f(d['placebo_p90']['observed_cluster_share'])}; "
                 f"{d['placebo_p90']['n_valid_draws']} valid draws")
        v = d["verdict"]
        if v["c"] is None:
            cl = "n/a (not a confluence set)"
        else:
            cl = f"> best single leg `{d['best_single_leg']}` at <= false: **{v['c']}**"
        L.append(f"- (a) > p90: **{v['a']}**; (b) > better ref at <= false: **{v['b']}**; "
                 f"(c) {cl}")
        L.append(f"- criteria_met: `{v['criteria_met']}`; nomination (description only): "
                 f"**{v['nomination']}**")
        if is_conf:
            L.append("\n### 12 single legs alone (this family)\n")
            L.append("| leg | cluster share | false/asset-yr | alert share |")
            L.append("|---|---|---|---|")
            for leg in sorted(d["singles"], key=lambda kk: -(d["singles"][kk]["cluster_share"] or 0.0)):
                r = d["singles"][leg]
                star = " **(best)**" if leg == d["best_single_leg"] else ""
                L.append(f"| {leg}{star} | {f(r['cluster_share'])} "
                         f"| {f(r['false_per_asset_year'])} | {f(r['alert_budget'])} |")
        L.append("\n### Matched threshold x per series\n")
        L.append("| series | dd x | near x |")
        L.append("|---|---|---|")
        for n in ctx[fam]["series"]:
            L.append(f"| {n} | {d['references']['dd']['x'][n]:.4f} "
                     f"| {d['references']['near']['x'][n]:.4f} |")
        L.append("")

    L.append("## Turns and end bound\n")
    for fam in ("R-off", "R-on"):
        t = result["turns"][fam]
        L.append(f"- {fam}: {t['n']} turns, {t['min']} .. {t['max']}")
    L.append(f"- every scored turn row and every alert/reference date ends by {END_D.date()} "
             f"(asserted; the bar is that nothing dated 2024-01-02 or later enters any alert, "
             f"turn or outcome).\n")
    L.append("## Deviations and notes\n")
    for x in deviations:
        L.append(f"- {x}")
    L.append("")
    (HERE / "SUMMARY.md").write_text("\n".join(L))

    p_end = check_pins(desk, "end")
    result["pins"]["end"] = p_end
    result["runtime_s"] = round(time.time() - t_all, 1)
    (HERE / "result.json").write_text(json.dumps(result, indent=1, default=str))
    ok = p_start == p_end == {"bm_ref.py": PIN_BM, "adapter.py": PIN_AD}
    log(f"# total runtime {result['runtime_s']}s")
    log(f"# pins match at start and end: {ok}")
    if not ok:
        raise SystemExit("PIN MISMATCH at end; STOP")


if __name__ == "__main__":
    main()
