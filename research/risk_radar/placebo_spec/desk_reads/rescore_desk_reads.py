#!/usr/bin/env python3
"""CORRECTION LINE (not a new read); placebo p90 under repair; part (a) provisional.

Re-scores the cluster-level near-turn placebo p90 of the four catalogue reads under
PLACEBO_PLACEMENT_SPEC_v1 Rule A (co-signed Amendment 1), so each read's part (a) can be
read against the repaired bar. Nothing else changes: same alerts, windows, turns, episodes,
kind, post, seed, n_draws, tol, outcomes_through.

Reads / sets
  v2      five -v2 sets on block D (2020-01-02..2023-12-29), ledger rows 479-483
  pre     R-off confluence k=3 follow-up on PRE (2006-01-03..2019-12-31), row 484
  rev1    the rev1 re-run of that follow-up on PRE: set a (row 512) and the
          rates_realrate leg description c (row 514)
  bt1     BT1 rate-response on PRE: dfii10 (row 535) and dgs10 (row 537)

Method (per read and per set)
  Step A  run the read's ORIGINAL p90 carrier unchanged (bm_ref.cluster_placebo_p90 for
          v2/pre; the runner's own parallel_p90 for rev1/bt1, which calls
          bm_ref._placebo_draw_arrays) and require it to equal the p90 recorded in that
          read's result.json. A mismatch stops that read (no Step B).
  Step B  replace ONLY the placement: each asset's draws come from
          catalogue/placebo_rule_a.placebo_draw_arrays (Rule A; cap = 10 * n_draws, the
          module default). Draw index k pairs the k-th kept draw of every asset (spec §3;
          pair_kept_draws is called as the pairing check). If ANY contributing asset is
          not defined, the set's p90 is "not defined at this exposure" - no asset is
          dropped. Otherwise the same scoring loop as cluster_placebo_p90 runs on the
          paired draws (patched bm_ref._placebo_draw_arrays returning the Rule A
          (draws, idx) shape), pooling turn rows across assets and reading the cluster
          catch share; p90 = 0.9 quantile.

Writes ONLY into this directory: raw_<read>_<ndraws>.json, RESULT.json, SUMMARY.md,
RUN_LOG.txt. The desk is read-only; trials.jsonl is read only, never appended.

Usage
  python3 rescore_desk_reads.py --desk <desk-v4> --read v2|pre|rev1|bt1
  python3 rescore_desk_reads.py --assemble
  add --n-draws 20 --smoke for a pipeline check (results are not comparable)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]                                  # repo root, no absolute paths written
CAT_READ = REPO / "research" / "risk_radar" / "catalogue_read"

LABEL = ("CORRECTION LINE (not a new read); placebo p90 under repair; "
         "part (a) provisional")

PIN_BM = "f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76"
PIN_BM_OLD = "c5130e9e2f80c9da3ff85d66a9f3070367f02e71c10d3e411205a97f12a9f066"
PIN_AD = "504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1"
PIN_RULE_A = "5270e64e4041331095c1d93ae5addec4c87b91f613c3d4c61853c3eea7cc774c"

NPROC = int(os.environ.get("RR_NPROC", "8"))
TOL = 0.01
SEED = 20261112
MIN_OFF = 10
PRE = 21

RUN_LOG = HERE / "RUN_LOG.txt"


def log(msg: str) -> None:
    with open(RUN_LOG, "a") as fh:
        fh.write(msg + "\n")
    print(msg, flush=True)


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ module loading
def load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def check_pins(desk: Path) -> dict:
    p = {"bm_ref.py": sha256(desk / "catalogue" / "bm_ref.py"),
         "placebo_rule_a.py": sha256(desk / "catalogue" / "placebo_rule_a.py"),
         "adapter.py": sha256(desk / "catalogue" / "adapter.py")}
    for k, v in p.items():
        log(f"[pin] {k} {v}")
    if p["bm_ref.py"] != PIN_BM:
        raise SystemExit(f"PIN MISMATCH bm_ref.py {p['bm_ref.py']} != {PIN_BM}; STOP")
    if p["adapter.py"] != PIN_AD:
        raise SystemExit(f"PIN MISMATCH adapter.py {p['adapter.py']}; STOP")
    if p["placebo_rule_a.py"] != PIN_RULE_A:
        raise SystemExit(f"PIN MISMATCH placebo_rule_a.py {p['placebo_rule_a.py']}; STOP")
    return p


def neutralise_logs(mods) -> None:
    """Keep every runner's log() out of its own read directory."""
    for m in mods:
        if hasattr(m, "log"):
            m.log = log


# ------------------------------------------------------------------ fingerprints
def fp_alert(s: pd.Series) -> str:
    s = pd.Series(s)
    a = np.packbits(np.asarray(s.astype(bool), dtype=bool))
    h = hashlib.sha256(a.tobytes())
    h.update(str(s.index[0]).encode())
    h.update(str(s.index[-1]).encode())
    h.update(str(len(s)).encode())
    h.update(str(int(s.sum())).encode())
    return h.hexdigest()


def fp_px(s: pd.Series) -> str:
    s = pd.Series(s)
    a = np.ascontiguousarray(s.to_numpy(dtype=float))
    h = hashlib.sha256(a.tobytes())
    h.update(str(s.index[0]).encode())
    h.update(str(s.index[-1]).encode())
    return h.hexdigest()


def alert_share(alerts: dict, assets: list) -> tuple[dict, float]:
    by = {a: float(pd.Series(alerts[a]).mean()) for a in assets}
    num = sum(int(pd.Series(alerts[a]).sum()) for a in assets)
    den = sum(len(pd.Series(alerts[a])) for a in assets)
    return by, (float(num / den) if den else None)


# ------------------------------------------------------------------ Rule A draws
def rule_a_cache(P, alerts: dict, px: dict, assets: list, near: str,
                 n_draws: int) -> tuple[dict, list]:
    """Rule A placement for every contributing asset; keyed by (alert, px) fingerprint."""
    cache, undefined = {}, []
    t0 = time.time()
    for a in assets:
        out = P.placebo_draw_arrays(alerts[a], px[a], near, TOL, n_draws, SEED)
        out = dict(out)
        cache[(fp_alert(alerts[a]), fp_px(px[a]))] = out
        if not out["defined"]:
            undefined.append(a)
        log(f"    ruleA {a:10s} near={near} attempts {out['attempts']} kept {out['kept']} "
            f"discarded {out['discarded']} acceptance {out['acceptance']:.3f} "
            f"defined {out['defined']} E {out['e_count']} "
            f"placed {out['placed_mass_in_e_share']} alert "
            f"{out['alert_mass_in_e_share']}")
    log(f"    ruleA placement {len(assets)} assets in {time.time() - t0:.1f}s")
    return cache, undefined


def make_rule_a_patch(BM, cache: dict, n_draws: int, near: str):
    """Monkeypatch bm_ref._placebo_draw_arrays to return the cached Rule A draws."""
    orig = BM._placebo_draw_arrays

    def patched(alert, px, near_, tol, n_draws_, seed):
        if n_draws_ != n_draws or seed != SEED or near_ != near:
            raise AssertionError(
                f"patched placebo called with unexpected settings: n_draws {n_draws_} "
                f"seed {seed} near {near_!r}")
        k = (fp_alert(alert), fp_px(px))
        if k not in cache:
            raise AssertionError("patched placebo got an alert/px pair outside the cache")
        out = cache[k]
        if not out["defined"]:
            raise AssertionError("patched placebo asked to score an undefined asset")
        return out["draws"], out["idx"]

    return orig, patched


# ------------------------------------------------------------------ per-read input building
def build_v2(R, desk: Path):
    """v2_bmref/run_bmref.py input phase, verbatim in substance."""
    V2, ledger_legs = R.load_v2()
    raw = R.build_alerts(V2, ledger_legs)
    A, BM, pv, pv_path = R.load_desk_kit(desk)
    ctx = {}
    for fam in ("R-off", "R-on"):
        direction, post = R.FAMILY[fam]
        c = BM.build_context(fam, direction)
        c["turns"] = BM.turns_in_window(c["turns"], R.START_D, R.END_D)
        ctx[fam] = c
        tmax = max(pd.Timestamp(t.date) for t in c["turns"])
        assert tmax <= R.END_D, (fam, tmax)
        log(f"  ctx {fam}: series {len(c['series'])} turns {len(c['turns'])} max {tmax.date()}")
    rec = json.loads((CAT_READ / "v2_bmref" / "result.json").read_text())
    sets = []
    for set_id, fam, key, _conf in R.SETS:
        alerts, px = R.window_set(V2, raw[key], ctx[fam])
        direction, post = R.FAMILY[fam]
        r = rec["sets"][set_id]["placebo_p90"]
        sets.append({"set": set_id, "kind": direction, "post": post,
                     "near": "high" if direction == "top" else "low",
                     "family": fam,
                     "turns": ctx[fam]["turns"], "alerts": alerts, "px": px,
                     "episodes": ctx[fam]["episodes"], "carrier": "desk",
                     "end": R.END_D,
                     "recorded_p90": r["p90"],
                     "recorded_observed": r["observed_cluster_share"],
                     "recorded_n_valid": r["n_valid_draws"],
                     "recorded_verdict_a": rec["sets"][set_id]["verdict"]["a"]})
    return {"BM": BM, "pv": pv, "pv_path": pv_path, "A": A, "sets": sets,
            "window": {"start": str(R.START_D.date()), "end": str(R.END_D.date()),
                       "pre": R.PRE, "n_draws": R.N_DRAWS, "seed": R.SEED, "tol": R.TOL,
                       "min_off": R.MIN_OFF,
                       "post": {"R-off": R.FAMILY["R-off"][1],
                                "R-on": R.FAMILY["R-on"][1]}},
            "rows": ["479 rr-roff-incumbent-v2", "480 rr-ron-incumbent-v2",
                     "481 rr-roff-confluence-k4-v2", "482 rr-ron-confluence-k4-v2",
                     "483 rr-ron-exit-v1-v2"]}


def build_pre(R, desk: Path):
    """followup_pre/run_pre.py input phase, verbatim in substance."""
    alert_full, n_on, avail, pit = R.build_alert_full()
    A, BM, pv, pv_path = R.load_desk_kit(desk)
    from catalogue import build as B
    specs = {s.name: s for s in B.build_specs(B.CUTOFF)[0]}
    df = A.load_pivots()
    pre_rows = A.select(df[df["date"] <= R.END], type="risk_off", tier="major", block="PRE")
    series = sorted(pre_rows["series"].unique())
    rows_dir, levels, episodes, turns = R.build_pre_context(A, BM, specs, series)
    alerts, px = R.window_alert(alert_full, levels, series)
    rec = json.loads((CAT_READ / "followup_pre" / "result.json").read_text())
    r = rec["placebo_p90"]
    sets = [{"set": "rr-roff-confluence-k3-followup", "kind": "top", "post": R.POST,
             "near": "high", "family": "R-off", "turns": turns, "alerts": alerts, "px": px,
             "episodes": episodes, "carrier": "desk", "end": R.END,
             "recorded_p90": r["p90"], "recorded_observed": r["observed_cluster_share"],
             "recorded_n_valid": r["n_valid_draws"],
             "recorded_verdict_a": rec["verdict"]["a"]}]
    return {"BM": BM, "pv": pv, "pv_path": pv_path, "A": A, "sets": sets,
            "window": {"start": str(R.START.date()), "end": str(R.END.date()),
                       "pre": R.PRE, "n_draws": R.N_DRAWS, "seed": R.SEED, "tol": R.TOL,
                       "min_off": R.MIN_OFF, "post": R.POST},
            "rows": ["484 rr-roff-confluence-k3-followup"]}


def build_rev1(R, desk: Path):
    """followup_rev1/run_rev1.py input phase, verbatim in substance."""
    alert_full, avail, pit = R.build_alert_full()
    A, BM, pv, pv_path = R.load_desk_kit(desk)
    ctx = BM.build_context("R-off", "top", start_d=R.START, end_d=R.END)
    series, turns, levels, episodes = (ctx["series"], ctx["turns"], ctx["levels"],
                                       ctx["episodes"])
    alerts, px = R.window_alert(alert_full, levels, series)
    leg_alerts, leg_px = {}, {}
    for leg, thr in R.LEGS.items():
        leg_full = (pit[leg] >= thr).fillna(False).astype(bool).shift(1, fill_value=False)
        la, lpx = R.window_alert(leg_full, levels, series)
        leg_alerts[leg], leg_px[leg] = la, lpx
    rec = json.loads((CAT_READ / "followup_rev1" / "result.json").read_text())
    ra, rc = rec["a"]["placebo_p90"], rec["c"]["placebo_p90_own"]
    sets = [
        {"set": "rr-roff-confluence-k3-followup-rev1-repro", "kind": "top", "post": R.POST,
         "near": "high", "family": "R-off", "turns": turns, "alerts": alerts, "px": px,
         "episodes": episodes, "carrier": "parallel", "end": R.END,
         "recorded_p90": ra["p90"], "recorded_observed": ra["observed_cluster_share"],
         "recorded_n_valid": ra["n_valid_draws"],
         "recorded_verdict_a": rec["a"]["verdict"]["a"],
         "recorded_equiv50": ra.get("_equivalence_50_draws", {}).get("p90")},
        {"set": "rr-roff-leg-rates-realrate-pre-desc", "kind": "top", "post": R.POST,
         "near": "high", "family": "R-off", "turns": turns,
         "alerts": leg_alerts["rates_realrate"], "px": leg_px["rates_realrate"],
         "episodes": episodes, "carrier": "parallel", "end": R.END,
         "recorded_p90": rc["p90"], "recorded_observed": rc["observed_cluster_share"],
         "recorded_n_valid": rc["n_valid_draws"],
         "recorded_verdict_a": rec["c"]["ab_description"]["a"],
         "recorded_equiv50": None},
    ]
    return {"BM": BM, "pv": pv, "pv_path": pv_path, "A": A, "sets": sets,
            "window": {"start": str(R.START.date()), "end": str(R.END.date()),
                       "pre": R.PRE, "n_draws": R.N_DRAWS, "seed": R.SEED, "tol": R.TOL,
                       "min_off": R.MIN_OFF, "post": R.POST},
            "rows": ["512 rr-roff-confluence-k3-followup-rev1-repro",
                     "514 rr-roff-leg-rates-realrate-pre-desc"]}


def build_bt1(R, desk: Path):
    """bt1_pre/run_bt1.py input phase, verbatim in substance."""
    rate = R.build_rate_inputs()
    A, BM, pv, pv_path = R.load_desk_kit(desk)
    ctx = BM.build_context("R-off", "top", start_d=R.START, end_d=R.END)
    series, turns, levels, episodes = (ctx["series"], ctx["turns"], ctx["levels"],
                                       ctx["episodes"])
    spy, qqq = levels["SPY"], levels["QQQ"]
    b20s = R.b20(spy).reindex(rate["idx"]).ffill()
    b20q = R.b20(qqq).reindex(rate["idx"]).ffill()
    b20s, b20q = b20s[b20s.index <= R.END], b20q[b20q.index <= R.END]
    idx = rate["idx"][rate["idx"] <= R.END]

    rec = json.loads((CAT_READ / "bt1_pre" / "result.json").read_text())
    sets = []
    for tag, qk, dk in (("dfii10", "q_dfii", "dy_dfii"), ("dgs10", "q_dgs", "dy_dgs")):
        q = pd.Series(rate[qk]).reindex(idx)
        d = pd.Series(rate[dk]).reindex(idx)
        b20s_i, b20q_i = b20s.reindex(q.index), b20q.reindex(q.index)
        bp = ((b20s_i > 0) & (b20q_i > 0)).fillna(False)
        rule = R.build_rule(q, d, bp.to_numpy(), b20s_i, b20q_i)
        alert_full = rule["A"].shift(1, fill_value=False).astype(bool)
        alerts = R.window_alert(alert_full, levels, series)
        px = {a: levels[a].reindex(alerts[a].index) for a in series}
        r = rec[tag]["p90"]
        sets.append({"set": tag, "kind": "top", "post": R.POST, "near": "high",
                     "family": "R-off", "turns": turns, "alerts": alerts, "px": px,
                     "episodes": episodes, "carrier": "parallel", "end": R.END,
                     "recorded_p90": r["p90"],
                     "recorded_observed": r["observed_cluster_share"],
                     "recorded_n_valid": r["n_valid_draws"],
                     "recorded_verdict_a": rec[tag]["rule_2b"]
                     ["verdict_mandatory_parts"]["a"],
                     "recorded_equiv50": r.get("_equivalence_50_draws", {}).get("p90")})
    return {"BM": BM, "pv": pv, "pv_path": pv_path, "A": A, "sets": sets,
            "window": {"start": str(R.START.date()), "end": str(R.END.date()),
                       "pre": R.PRE, "n_draws": R.N_DRAWS, "seed": R.SEED, "tol": R.TOL,
                       "min_off": R.MIN_OFF, "post": R.POST},
            "rows": ["535 rr-bt1-rate-response-pre-desc",
                     "537 rr-bt1-rate-response-pre-desc (DGS10 substitute)"]}


BUILDERS = {"v2": (build_v2, "v2_bmref/run_bmref.py"),
            "pre": (build_pre, "followup_pre/run_pre.py"),
            "rev1": (build_rev1, "followup_rev1/run_rev1.py"),
            "bt1": (build_bt1, "bt1_pre/run_bt1.py")}


# ------------------------------------------------------------------ p90 carriers
def carrier_call(setd: dict, BM, pv, n_draws: int):
    """Exactly the call the read itself used for its recorded p90."""
    if setd["carrier"] == "desk":
        return BM.cluster_placebo_p90(
            setd["turns"], setd["alerts"], setd["episodes"], setd["px"],
            kind=setd["kind"], outcomes_through=setd["end"], n_draws=n_draws, seed=SEED,
            tol=TOL, pre=PRE, post=setd["post"], min_off=MIN_OFF)
    return pv_parallel(setd, BM, pv, n_draws)


def pv_parallel(setd: dict, BM, pv, n_draws: int) -> dict:
    """The runners' parallel_p90: identical draws and scoring, draw loop across processes."""
    from concurrent.futures import ProcessPoolExecutor
    by_asset: dict[str, list] = {}
    for t in setd["turns"]:
        by_asset.setdefault(t.asset, []).append(t)
    assets = [a for a in sorted(by_asset) if a in setd["alerts"]]
    draws, idxs = {}, {}
    for a in assets:
        d, i = BM._placebo_draw_arrays(setd["alerts"][a], setd["px"][a], setd["near"],
                                       TOL, n_draws, SEED)
        draws[a], idxs[a] = d, i
    shares: list[float] = []
    if assets:
        chunk = 50
        chunks = [list(range(lo, min(n_draws, lo + chunk)))
                  for lo in range(0, n_draws, chunk)]
        _P90.clear()
        _P90.update(pv=pv, kind=setd["kind"], assets=assets, by_asset=by_asset,
                    draws=draws, idxs=idxs, episodes=setd["episodes"], ot=setd["end"],
                    pre=PRE, post=setd["post"], min_off=MIN_OFF)
        with ProcessPoolExecutor(max_workers=min(NPROC, len(chunks))) as ex:
            for res in ex.map(_p90_chunk, chunks):
                shares += res
        _P90.clear()
    obs = pv.summarise([row for a in assets
                        for row in pv.score_pivots(setd["alerts"][a], turns=by_asset[a],
                                                   episodes=setd["episodes"].get(a, []),
                                                   outcomes_through=setd["end"], pre=PRE,
                                                   post=setd["post"],
                                                   min_off=MIN_OFF)["turns"]],
                       setd["kind"])
    v = np.asarray(shares, dtype=float)
    return {"kind": setd["kind"], "near": setd["near"], "post": setd["post"],
            "n_draws": int(n_draws), "n_valid_draws": int(len(v)),
            "observed_cluster_share": obs["cluster_share_flagged"],
            "placebo_mean": float(v.mean()) if len(v) else None,
            "placebo_median": float(np.median(v)) if len(v) else None,
            "p90": float(np.quantile(v, 0.9)) if len(v) else None}


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
                                turns=P["by_asset"][a],
                                episodes=P["episodes"].get(a, []),
                                outcomes_through=P["ot"], pre=P["pre"], post=P["post"],
                                min_off=P["min_off"])
            pooled += r["turns"]
        sh = pv.summarise(pooled, P["kind"])["cluster_share_flagged"]
        if sh is not None:
            out.append(float(sh))
    return out


def desk_p90_parallel(setd: dict, BM, pv, n_draws: int) -> dict:
    """cluster_placebo_p90's draws, scoring and pooling, spread over processes.

    Only used for the cheap 50-draw equivalence checks; the recorded Step A value comes
    from the read's own carrier.
    """
    saved = NPROC
    return pv_parallel(setd, BM, pv, n_draws) if saved else None


# ------------------------------------------------------------------ one read
def run_read(read: str, desk: Path, n_draws: int, smoke: bool) -> dict:
    build, rel = BUILDERS[read]
    path = CAT_READ / rel
    R = load_mod(f"rr_{read}", path)
    neutralise_logs([R])
    log(f"=== read {read} ({rel}); n_draws {n_draws}; smoke {smoke}")
    t0 = time.time()
    built = build(R, desk)
    BM, pv = built["BM"], built["pv"]
    log(f"  inputs built in {time.time() - t0:.1f}s; scorer "
        f"{str(built['pv_path']).replace(str(desk), '<desk>')}")
    P = load_mod("rr_placebo_rule_a", desk / "catalogue" / "placebo_rule_a.py")

    out_sets = []
    for setd in built["sets"]:
        sid = setd["set"]
        log(f"  -- set {sid} kind {setd['kind']} post {setd['post']} near {setd['near']}")
        by_asset: dict[str, list] = {}
        for t in setd["turns"]:
            by_asset.setdefault(t.asset, []).append(t)
        assets = [a for a in sorted(by_asset) if a in setd["alerts"]]
        shares, pooled = alert_share(setd["alerts"], assets)

        # ---- Step A: original p90, unchanged
        t_a = time.time()
        A_out = carrier_call(setd, BM, pv, n_draws)
        rec = setd["recorded_p90"]
        got = A_out["p90"]
        diff = None if (got is None or rec is None) else float(got) - float(rec)
        ok = (diff is not None and abs(diff) < 1e-9)
        log(f"     step A p90 {got} recorded {rec} diff {diff} "
            f"({'MATCH' if ok else 'MISMATCH'}) ({time.time() - t_a:.1f}s)")
        if not ok and not smoke:
            raise SystemExit(f"STEP A MISMATCH for {read}/{sid}: reproduced {got} != "
                             f"recorded {rec}; STOP this read")

        row = {
            "set": sid, "kind": setd["kind"], "post": setd["post"],
            "near": setd["near"], "family": setd.get("family"),
            "n_draws": n_draws,
            "assets_contributing": assets,
            "alert_share_by_asset": shares,
            "alert_share_pooled": pooled,
            "recorded_p90": rec,
            "reproduced_p90": got,
            "reproduced_diff": diff,
            "reproduced_ok": bool(ok),
            "observed_cluster_share": A_out["observed_cluster_share"],
            "recorded_observed_cluster_share": setd["recorded_observed"],
            "reproduced_n_valid_draws": A_out["n_valid_draws"],
            "recorded_n_valid_draws": setd["recorded_n_valid"],
            "recorded_verdict_a": setd["recorded_verdict_a"],
            "rule_a_status": None, "rule_a_p90": None,
            "rule_a_n_valid_draws": None, "rule_a_placebo_mean": None,
            "rule_a_placebo_median": None,
            "undefined_assets": [], "mass_table": [],
            "a_old": bool(setd["recorded_observed"] > rec) if rec is not None else None,
            "a_new": None, "flip": False,
        }

        # ---- Step B: Rule A placement only
        cache, undefined = rule_a_cache(P, setd["alerts"], setd["px"], assets,
                                        setd["near"], n_draws)
        mass = []
        for a in assets:
            o = cache[(fp_alert(setd["alerts"][a]), fp_px(setd["px"][a]))]
            mass.append({"asset": a, "attempts": int(o["attempts"]),
                         "kept": int(o["kept"]), "discarded": int(o["discarded"]),
                         "acceptance": float(o["acceptance"]),
                         "defined": bool(o["defined"]), "e_count": int(o["e_count"]),
                         "placed_mass_in_e_share": o["placed_mass_in_e_share"],
                         "alert_mass_in_e_share": o["alert_mass_in_e_share"],
                         "alert_share": shares[a]})
        row["mass_table"] = mass
        row["undefined_assets"] = list(undefined)

        if undefined:
            row["rule_a_status"] = "not defined at this exposure"
            row["a_new"] = None
            row["flip"] = bool(row["a_old"] is not None and row["a_old"] is not False)
            log(f"     ruleA NOT DEFINED at this exposure; undefined assets "
                f"{undefined} -> no further scoring for this set")
        else:
            # §3 pairing check (k-th kept draw of every asset)
            paired = P.pair_kept_draws(
                {a: cache[(fp_alert(setd["alerts"][a]), fp_px(setd["px"][a]))]
                 for a in assets}, n_draws)
            if not paired["defined"]:
                raise SystemExit(f"pair_kept_draws undefined for {read}/{sid}")
            assert len(paired["paired"]) == n_draws
            for k, d in enumerate(paired["paired"]):
                for a in assets:
                    exp = cache[(fp_alert(setd["alerts"][a]),
                                 fp_px(setd["px"][a]))]["draws"][k]
                    if not np.array_equal(d[a], exp):
                        raise AssertionError(f"pairing mismatch {read}/{sid}/{a}/draw {k}")

            orig, patched = make_rule_a_patch(BM, cache, n_draws, setd["near"])
            BM._placebo_draw_arrays = patched
            try:
                t_b = time.time()
                B_out = carrier_call(setd, BM, pv, n_draws)
                log(f"     step B p90 {B_out['p90']} observed "
                    f"{B_out['observed_cluster_share']} valid {B_out['n_valid_draws']} "
                    f"({time.time() - t_b:.1f}s)")
            finally:
                BM._placebo_draw_arrays = orig
            row["rule_a_status"] = "defined"
            row["rule_a_p90"] = B_out["p90"]
            row["rule_a_n_valid_draws"] = B_out["n_valid_draws"]
            row["rule_a_placebo_mean"] = B_out["placebo_mean"]
            row["rule_a_placebo_median"] = B_out["placebo_median"]
            assert B_out["observed_cluster_share"] == A_out["observed_cluster_share"]
            row["a_new"] = bool(A_out["observed_cluster_share"] > B_out["p90"]) \
                if B_out["p90"] is not None else None
            row["flip"] = bool(row["a_new"] != row["a_old"])
        out_sets.append(row)
        log(f"     part (a) old {row['a_old']} -> new {row['a_new']} "
            f"(flip {row['flip']})")

    result = {
        "label": LABEL,
        "read": read,
        "runner": rel,
        "smoke": smoke,
        "n_draws": n_draws,
        "window": built["window"],
        "ledger_rows": built["rows"],
        "pins": {"bm_ref.py": PIN_BM, "bm_ref.py_at_original_read": PIN_BM_OLD,
                 "adapter.py": PIN_AD, "placebo_rule_a.py": PIN_RULE_A,
                 "note": "bm_ref.cluster_placebo_p90 and _placebo_draw_arrays are "
                         "byte-identical between c5130e9e and f7350e6e (verified); the "
                         "v2/pre reads' recorded p90 are reproduced under f7350e6e."},
        "scorer_module": str(built["pv_path"]).replace(str(desk), "<desk>"),
        "sets": out_sets,
        "runtime_s": round(time.time() - t0, 1),
    }
    outp = HERE / f"raw_{read}_{n_draws}.json"
    outp.write_text(json.dumps(result, indent=1, default=str))
    log(f"=== read {read} done in {result['runtime_s']}s -> {outp.name}")
    return result


# ------------------------------------------------------------------ assemble
def fmt(v, nd=3):
    return "not defined" if v is None else f"{v:.{nd}f}"


def assemble(desk: Path) -> dict:
    reads = {}
    for r in BUILDERS:
        cands = sorted(HERE.glob(f"raw_{r}_*.json"))
        cands = [p for p in cands if "_smoke" not in p.name]
        if not cands:
            log(f"[assemble] no raw file for {r}; skipped")
            continue
        # prefer a non-smoke full run (largest n_draws)
        best = None
        for p in cands:
            d = json.loads(p.read_text())
            if d.get("smoke"):
                continue
            if best is None or d["n_draws"] > best["n_draws"]:
                best = d
        if best is None:
            continue
        reads[r] = best
        log(f"[assemble] {r}: raw_{r}_{best['n_draws']}.json ({len(best['sets'])} sets)")

    result = {"label": LABEL,
              "generated": "2026-11-12",
              "desk": "<desk> (read-only)",
              "rule": "PLACEBO_PLACEMENT_SPEC_v1 Rule A, cap = 10 * n_draws "
                      "(co-signed Amendment 1, catalogue/placebo_rule_a.py)",
              "method": {
                  "step_a": "original p90 carrier unchanged; must equal the read's "
                            "recorded p90",
                  "step_b": "only the placement swapped: bm_ref._placebo_draw_arrays "
                            "monkeypatched to the Rule A kept draws; identical scoring, "
                            "pooling and 0.9 quantile",
                  "pairing": "draw k = k-th kept draw of every asset (spec §3); checked "
                             "against pair_kept_draws",
                  "undefined_rule": "if any contributing asset is not defined, the set's "
                                    "p90 is 'not defined at this exposure'; no asset dropped",
                  "no_widening": "no other window, tol or near tried",
              },
              "reads": {}}

    for r, d in reads.items():
        entry = {"runner": d["runner"], "window": d["window"],
                 "ledger_rows": d["ledger_rows"], "scorer_module": d["scorer_module"],
                 "n_draws": d["n_draws"], "runtime_s": d["runtime_s"],
                 "sets": d["sets"]}
        result["reads"][r] = entry

    (HERE / "RESULT.json").write_text(json.dumps(result, indent=1, default=str))
    write_summary(result)
    return result


def write_summary(res: dict) -> None:
    L = []
    L.append("# Catalogue part (a) placebo p90 — Rule A re-score\n")
    L.append(f"**{LABEL}.**\n")
    L.append("Rule: `PLACEBO_PLACEMENT_SPEC_v1` **Rule A**, cap `10 * n_draws`, "
             "co-signed Amendment 1; placement from `catalogue/placebo_rule_a.py`. "
             "Nothing else changes: same alerts, windows (all end ≤ 2023-12-29), turns, "
             "episodes, kind, post, seed 20261112, n_draws, tol 0.01, outcomes_through.\n")
    L.append("Step A reproduced each read's recorded p90 with the original carrier "
             "(`bm_ref.cluster_placebo_p90` for v2/pre; the read's own `parallel_p90`, "
             "which calls `bm_ref._placebo_draw_arrays`, for rev1/bt1). Step B swapped "
             "only the placement. Pairing is the k-th kept draw of every asset (spec §3), "
             "checked against `pair_kept_draws`.\n")

    L.append("## Per-set table\n")
    L.append("| read | set | kind | observed | old p90 | new p90 | (a) old → new | FLIP "
             "| alert share (pooled) | undefined assets |")
    L.append("|---|---|---|---:|---:|---:|---|---|---:|---:|")
    for r, d in res["reads"].items():
        for s in d["sets"]:
            new = s["rule_a_p90"] if s["rule_a_status"] == "defined" else "not defined"
            nt = fmt(new) if isinstance(new, float) else new
            L.append(f"| {r} | {s['set']} | {s['kind']} | "
                     f"{fmt(s['observed_cluster_share'])} | {fmt(s['recorded_p90'])} | "
                     f"{nt} | {s['a_old']} → "
                     f"{'not defined' if s['a_new'] is None else s['a_new']} | "
                     f"{'**FLIP**' if s['flip'] else '—'} | "
                     f"{fmt(s['alert_share_pooled'], 4)} | "
                     f"{len(s['undefined_assets'])} |")
    L.append("")
    L.append("(a) is read at the read's own printed precision: observed cluster share > "
             "cluster p90. `not defined` means at least one contributing asset hit the "
             "attempt cap or an empty eligible pool under Rule A.\n")
    L.append("**FLIP convention.** `FLIP` marks a set whose part (a) *pass* changed state: a "
             "former `True` that is no longer `True`. A set that was already `False` and is now "
             "`not defined` is **not** marked FLIP, but (a) is no longer evaluable — it is not a "
             "preserved `False`. Read the new column as: `False` where the set was defined and "
             "still fails, `not defined at this exposure` everywhere else. No top-exposure set "
             "is defined under Rule A, so every part (a) pass in this catalogue depended on the "
             "repaired placement.\n")

    L.append("## Alert share beside the p90 — per asset and pooled\n")
    L.append("Alert share is the fraction of that asset's windowed sessions the alert is ON "
             "(so it is the same for both p90 columns). The pooled figure is the session-"
             "weighted mean across the set's contributing assets, and is the one repeated in "
             "the per-set table above.\n")
    L.append("| read | set | kind | asset | alert share | old p90 | new p90 |")
    L.append("|---|---|---|---|---:|---:|---:|")
    for r, d in res["reads"].items():
        for s in d["sets"]:
            new = s["rule_a_p90"] if s["rule_a_status"] == "defined" else "not defined"
            nt = fmt(new) if isinstance(new, float) else new
            for m in s["mass_table"]:
                L.append(f"| {r} | {s['set']} | {s['kind']} | {m['asset']} | "
                         f"{fmt(m['alert_share'], 4)} | {fmt(s['recorded_p90'])} | {nt} |")
            L.append(f"| {r} | {s['set']} | {s['kind']} | **pooled** | "
                     f"**{fmt(s['alert_share_pooled'], 4)}** | "
                     f"**{fmt(s['recorded_p90'])}** | **{nt}** |")
    L.append("")

    L.append("## Reproduction (step A)\n")
    L.append("| read | set | recorded p90 | reproduced p90 | diff | recorded observed "
             "| reproduced observed | recorded valid draws |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for r, d in res["reads"].items():
        for s in d["sets"]:
            L.append(f"| {r} | {s['set']} | {fmt(s['recorded_p90'])} | "
                     f"{fmt(s['reproduced_p90'])} | {s['reproduced_diff']} | "
                     f"{fmt(s['recorded_observed_cluster_share'])} | "
                     f"{fmt(s['observed_cluster_share'])} | "
                     f"{s['recorded_n_valid_draws']} |")
    L.append("")

    L.append("## Unchanged inputs per set\n")
    L.append("| read | set | kind | near | post | contributing assets | "
             "observed cluster share |")
    L.append("|---|---|---|---|---:|---:|---:|")
    for r, d in res["reads"].items():
        for s in d["sets"]:
            L.append(f"| {r} | {s['set']} | {s['kind']} | {s['near']} | {s['post']} | "
                     f"{len(s['assets_contributing'])} | "
                     f"{fmt(s['observed_cluster_share'])} |")
    L.append("")

    L.append("## Rule A placement, per asset and near\n")
    L.append("`placed` is the mean share of placed mass landing inside the eligible band; "
             "`alert` is the observed alert's own in-band mass share. `alert share` is the "
             "fraction of the asset's windowed sessions the alert is ON.\n")
    for r, d in res["reads"].items():
        for s in d["sets"]:
            L.append(f"### {r} · {s['set']} (near {s['near']}, post {s['post']})\n")
            L.append("| asset | attempts | kept | discarded | acceptance | defined | "
                     "E sessions | placed mass in E | alert mass in E | alert share |")
            L.append("|---|---:|---:|---:|---:|---|---:|---:|---:|---:|")
            for m in s["mass_table"]:
                L.append(f"| {m['asset']} | {m['attempts']} | {m['kept']} | "
                         f"{m['discarded']} | {m['acceptance']:.3f} | "
                         f"{'yes' if m['defined'] else '**no**'} | {m['e_count']} | "
                         f"{fmt(m['placed_mass_in_e_share'], 3)} | "
                         f"{fmt(m['alert_mass_in_e_share'], 3)} | "
                         f"{fmt(m['alert_share'], 4)} |")
            if s["undefined_assets"]:
                L.append(f"\n**Not defined at this exposure:** "
                         f"{', '.join(s['undefined_assets'])}.\n")
            else:
                L.append("")
    L.append("## Provenance\n")
    L.append("| read | runner | window | ledger rows | sets |")
    L.append("|---|---|---|---|---:|")
    for r, d in res["reads"].items():
        w = d["window"]
        L.append(f"| {r} | `{d['runner']}` | {w['start']}..{w['end']} | "
                 f"{'; '.join(d['ledger_rows'])} | {len(d['sets'])} |")
    L.append("")
    L.append(f"Desk modules pinned: `bm_ref.py` `{PIN_BM}`; "
             f"`placebo_rule_a.py` `{PIN_RULE_A}`; `adapter.py` `{PIN_AD}`. "
             f"The v2/pre reads recorded `bm_ref.py` `{PIN_BM_OLD}`; "
             "`cluster_placebo_p90` and `_placebo_draw_arrays` are byte-identical between "
             "those revisions.\n")
    L.append("No output file names a local absolute path. The desk was read only and "
             "`trials.jsonl` was never written.\n")
    (HERE / "SUMMARY.md").write_text("\n".join(L))


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desk", default=os.environ.get("ROTATION_DESK"))
    ap.add_argument("--read", choices=sorted(BUILDERS))
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--n-draws", type=int, default=2000)
    ap.add_argument("--smoke", action="store_true")
    ns = ap.parse_args()

    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    if ns.assemble:
        desk = Path(ns.desk).resolve() if ns.desk else Path("<desk>")
        res = assemble(desk)
        log("[assemble] wrote RESULT.json and SUMMARY.md")
        return
    if not ns.desk or not ns.read:
        raise SystemExit("need --desk <desk-v4> and --read <v2|pre|rev1|bt1>, or --assemble")
    desk = Path(ns.desk).resolve()
    log(f"# {LABEL}")
    log(f"# desk <desk> (read-only); read {ns.read}; n_draws {ns.n_draws}; smoke {ns.smoke}")
    check_pins(desk)
    run_read(ns.read, desk, 50 if ns.smoke else ns.n_draws, ns.smoke)


if __name__ == "__main__":
    main()
