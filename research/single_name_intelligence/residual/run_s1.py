#!/usr/bin/env python3
"""run_s1.py — the S1 residual baseline runner (C2) and evidence run (C3).

HISTORICAL-DESCRIPTIVE ONLY. REG §2 is not met: nothing here registers, ranks,
gates, sizes, signals, escalates or trades. Every output carries the D1 labels.

One command reproduces everything from a clean checkout:

  python3 research/single_name_intelligence/residual/run_s1.py \
      --input-ref <BASE> \
      --out-dir <dir> \
      --trial-ledger-path <dir>/trial_ledger.jsonl

`--check` re-runs into a temp dir and byte-compares every output against the
committed runs/ tree (the ledger compared after dropping the wall-clock 'ts'),
exit 0 iff identical. Invoke it with the SAME --trial-ledger-path string as the
evidence run so receipts compare byte-for-byte.

Sequence: verify pins -> verify seal (prereg digest, membership digests, manifest
bytes; exit non-zero on any mismatch) -> detect the sealed INFO-LEAK predicate
-> register trial budgets -> per protocol, one log_trial per config then the
evaluation -> write observations/, results/, REPORT.md, LANE_MANIFEST.json.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from engine.grading_stats import wilson_ci  # noqa: E402
from engine.qledger import resolve_horizon_window  # noqa: E402
from engine.trial_ledger import TrialLedger, register_trials  # noqa: E402
from s1_challenger import (characteristics_at, estimability, fit_gamma,  # noqa: E402
                           rank_standardise)
from s1_data import GitBlobStore, closes_from_frame  # noqa: E402
from s1_decomposition import (daily_log_returns, decompose_unit, factors_for,  # noqa: E402
                              spec_hash, window_log_ret)
from s1_direction import direction_trailing63, sign_of  # noqa: E402
from s1_infoleak import detect as leak_detect  # noqa: E402
from s1_infoleak import vintage_series  # noqa: E402
from s1_manifest import (TRAIN_END, build_rows, is_session_fn,  # noqa: E402
                         last_session_before, manifest_bytes, split_digests, time_split)
from s1_prereg import (BASE, BRANCH, BENCHES, D1_LABELS, HORIZONS, INPUT_PINS,  # noqa: E402
                       LANE, RUNS_REL, SUBJECTS, VERSION, prereg_digest)
from s1_report import block_key, make_block, render_report_md  # noqa: E402
from s1_stats import (ALPHA, binom_p_one_sided_greater, mirror_mean_ci,  # noqa: E402
                      sign_test_two_sided)

RESIDUAL_REL = "research/single_name_intelligence/residual"
PROTOCOL_SUBJECTS = {
    "P01": SUBJECTS["P01"],
    "P02": SUBJECTS["P02"],
    "P03": SUBJECTS["P01"] + SUBJECTS["P02"],
}
BASELINES = ("always_long", "trail63")
NOMINAL_95 = 0.95
NOMINAL_6827 = 0.6827
LABEL_TUNE_RETIRED = "NON-CONFIRMATORY — TUNE RETIRED (A23 INFO-LEAK)"
LABEL_IN_SAMPLE = "IN-SAMPLE for Gamma"
LABEL_DESCRIPTIVE_HK = "DESCRIPTIVE — outside the P03 cohort (V0 row 14 / X7)"

# per-run deterministic stamps (BASE commit date / last input bar), set in main()
DETECTED_AT: str | None = None
INFO_CUTOFF: str | None = None


class SealMismatch(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# small deterministic helpers
# --------------------------------------------------------------------------- #
def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def doc_json(obj) -> str:
    """Order-preserving canonical serialization for REG §5 documents: the ten
    fields must keep their frozen order in results/<Pxx>.json (D12). Insertion
    order is fully deterministic — no wall-clock, no set iteration."""
    return json.dumps(obj, sort_keys=False, separators=(",", ":"), ensure_ascii=False)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc_json(obj) + "\n", encoding="utf-8")


def git_out(repo_root: Path, args: list[str]) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo_root), *args],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def code_tree_sha(repo_root: Path) -> str:
    """Content address of the runner code at HEAD. A receipt pinned to a moving
    HEAD sha would not byte-reproduce across later commits; the residual/ tree
    id is stable from C2 onward."""
    return git_out(repo_root, ["rev-parse", f"HEAD:{RESIDUAL_REL}"]) or "UNAVAILABLE"


def seal_commit_sha(repo_root: Path) -> str:
    """The commit that introduced the seal file (deterministic at/after C3)."""
    return git_out(repo_root, ["log", "--format=%H", "-n", "1", "--",
                               f"{RUNS_REL}/SEAL_AND_BUDGET.json"]) or "UNAVAILABLE"


# --------------------------------------------------------------------------- #
# seal verification (D14: exit non-zero on any mismatch)
# --------------------------------------------------------------------------- #
def rebuild_manifests(store) -> dict:
    """Outcome-free manifest rebuild — index dates only."""
    out: dict[tuple, dict] = {}
    for pid in ("P01", "P02", "P03"):
        for subj in PROTOCOL_SUBJECTS[pid]:
            dates = store.index_dates(subj["data_path"])
            for h in HORIZONS:
                rows = build_rows(pid, subj["issuer_key"], subj["counter"],
                                  subj["security_id"], subj["market"], h, dates, dates[-1])
                out[(pid, subj["counter"], h)] = {
                    "rows": rows, "bytes": manifest_bytes(rows),
                    "digests": split_digests(rows), "subject": subj,
                }
    return out


def verify_seal(store, repo_root: Path, input_ref: str) -> tuple[dict, dict]:
    seal_path = repo_root / RUNS_REL / "SEAL_AND_BUDGET.json"
    if not seal_path.exists():
        raise SealMismatch(f"seal file missing: {seal_path}")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("prereg_digest_sha256") != prereg_digest():
        raise SealMismatch("prereg digest mismatch: the working PREREG_SPEC is not the "
                           "sealed spec")
    if seal.get("input_ref") != input_ref:
        raise SealMismatch(f"seal was cut for input_ref {seal.get('input_ref')!r}, "
                           f"not {input_ref!r}")
    rebuilt = rebuild_manifests(store)
    table = {(r["protocol_id"], r["subject"], r["h"], r["split"]): r
             for r in seal["membership_table"]}
    sealed_rows = 0
    for (pid, counter, h), entry in rebuilt.items():
        for sp, info in entry["digests"].items():
            row = table.get((pid, counter, h, sp))
            if row is None:
                raise SealMismatch(f"membership row missing from the seal: "
                                   f"{(pid, counter, h, sp)}")
            if row["count"] != info["count"] or \
                    row["membership_sha256"] != info["membership_sha256"]:
                raise SealMismatch(f"membership mismatch for {(pid, counter, h, sp)}")
            sealed_rows += info["count"]
        committed = repo_root / RUNS_REL / "manifests" / f"{pid}_{counter}_{h}.jsonl"
        if not committed.exists():
            raise SealMismatch(f"sealed manifest missing from the tree: {committed.name}")
        if committed.read_bytes() != entry["bytes"]:
            raise SealMismatch(f"manifest bytes changed since the seal: {committed.name}")
    if sealed_rows != sum(r["count"] for r in seal["membership_table"]):
        raise SealMismatch("membership row counts do not reconcile with the seal table")
    return seal, rebuilt


# --------------------------------------------------------------------------- #
# leg returns — reproduces engine/qledger.py _leg_ret_in_window (L2540)
# --------------------------------------------------------------------------- #
def leg_simple_ret(closes: dict, fill: date, coverage: date) -> float | None:
    """close(coverage)/close(fill) - 1 with both endpoint bars on EXACTLY the
    resolved sessions (rounded to 6 dp, the qledger convention); else None."""
    a, b = closes.get(fill), closes.get(coverage)
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return round(b / a - 1.0, 6)


def load_close_maps(store, path: str, columns: list[str]) -> tuple[list, dict]:
    d, c = store.frame(path, columns)
    maps = {col: closes_from_frame(d, c[col])[1] for col in columns}
    return d, maps


# --------------------------------------------------------------------------- #
# P01 / P02 directional evaluation
# --------------------------------------------------------------------------- #
def evaluate_directional(pid: str, store, rebuilt: dict) -> dict:
    bench = BENCHES[pid]
    _, bench_maps = load_close_maps(store, bench["data_path"], ["close"])
    bench_map = bench_maps["close"]
    is_session = is_session_fn(bench["market"])
    observations: dict[str, list[dict]] = {}
    for subj in PROTOCOL_SUBJECTS[pid]:
        _, subj_maps = load_close_maps(store, subj["data_path"], ["close"])
        subj_map = subj_maps["close"]
        for h in HORIZONS:
            rows = []
            for m in rebuilt[(pid, subj["counter"], h)]["rows"]:
                s = date.fromisoformat(m["anchor_session_date"])
                obs = {
                    "episode_key": m["episode_key"],
                    "anchor_session_date": m["anchor_session_date"],
                    "coverage_date": m["coverage_date"],
                    "manifest_split": m["split"],
                    "split": m["split"],
                    "time_split": time_split(s),
                    "abstention": "OK",
                    "excess": None,
                    "tie": False,
                    "always_long_direction": 1,
                    "trail63_direction": None,
                }
                if m["split"] in ("TRAIN", "TUNE"):
                    w = resolve_horizon_window(s - timedelta(days=1), h,
                                               "trading_days", subj["market"])
                    if w is None:
                        obs["abstention"] = "ABSTAIN_RESOLVER_NONE"
                    elif w.fill_date != s:
                        obs["abstention"] = "ABSTAIN_FILL_MISMATCH"
                    else:
                        sr = leg_simple_ret(subj_map, w.fill_date, w.coverage_date)
                        br = leg_simple_ret(bench_map, w.fill_date, w.coverage_date)
                        if sr is None or br is None:
                            obs["abstention"] = "ABSTAIN_MISSING_ENDPOINT"
                        else:
                            obs["excess"] = round(sr - br, 6)   # grade_claim L2812
                            obs["trail63_direction"] = direction_trailing63(
                                subj_map, bench_map, s, is_session, 63)
                rows.append(obs)
            observations[f"{pid}_{subj['counter']}_{h}"] = rows
    return {"observations": observations}


def directional_blocks(pid: str, evaluation: dict, rebuilt: dict, leak_retired: set,
                       trial_accounting: dict, receipt_base: dict) -> tuple[dict, list]:
    """Config-grid blocks in REG §5 order: 2 baselines x 3 h x {H0_1, H0_2} x split."""
    blocks: dict = {}
    order: list = []
    for subj in PROTOCOL_SUBJECTS[pid]:
        for h in HORIZONS:
            obs_rows = evaluation["observations"][f"{pid}_{subj['counter']}_{h}"]
            mem = {sp: info["membership_sha256"]
                   for sp, info in rebuilt[(pid, subj["counter"], h)]["digests"].items()}
            purged = sum(1 for o in obs_rows if o["manifest_split"].startswith("PURGED_"))
            quar = sum(1 for o in obs_rows if o["manifest_split"] == "QUARANTINE")
            abstain_by_time = {"TRAIN": [0, 0], "TUNE": [0, 0]}
            for o in obs_rows:
                if o["manifest_split"] in ("ABSTAIN_RESOLVER_NONE", "ABSTAIN_FILL_MISMATCH"):
                    idx = {"ABSTAIN_RESOLVER_NONE": 0, "ABSTAIN_FILL_MISMATCH": 1}[o["manifest_split"]]
                    abstain_by_time[o["time_split"]][idx] += 1
            missing = {sp: 0 for sp in ("TRAIN", "TUNE")}
            for o in obs_rows:
                if o["manifest_split"] in ("TRAIN", "TUNE") and \
                        o["abstention"] == "ABSTAIN_MISSING_ENDPOINT":
                    missing[o["split"]] += 1
            for baseline in BASELINES:
                for split in ("TRAIN", "TUNE"):
                    retired = pid in leak_retired and split == "TUNE"
                    usable, dir0, ties = [], 0, 0
                    for o in obs_rows:
                        if o["manifest_split"] != split:
                            continue
                        if o["abstention"] != "OK":
                            continue
                        d = o["always_long_direction"] if baseline == "always_long" \
                            else o["trail63_direction"]
                        if d == 0:
                            dir0 += 1
                            continue
                        usable.append(o)
                    n = len(usable)
                    k = sum(1 for o in usable
                            if sign_of(o["excess"]) == (1 if baseline == "always_long"
                                                        else o["trail63_direction"]))
                    ties = sum(1 for o in usable if o["excess"] == 0)
                    pos = sum(1 for o in usable if o["excess"] > 0)
                    neg = sum(1 for o in usable if o["excess"] < 0)
                    cluster = [o["anchor_session_date"] for o in usable]
                    xs = [o["excess"] for o in usable]
                    p_hit = binom_p_one_sided_greater(k, n) if n else None
                    hit_null = ("direction at horizon h; accuracy indistinguishable from a "
                                "coin flip at the 0.05 level"
                                if (p_hit is None or p_hit >= ALPHA) else
                                "direction at horizon h; the hit rate departs from 0.50 "
                                "(descriptive, non-confirmatory)")
                    p_sign = sign_test_two_sided(pos, neg) if (pos + neg) else None
                    ex_null = ("median excess indistinguishable from zero at the 0.05 level"
                               if (p_sign is None or p_sign >= ALPHA) else
                               "median excess departs from zero (descriptive, "
                               "non-confirmatory)")
                    split_name = f"{split} ({LABEL_TUNE_RETIRED})" if retired else split
                    res_a, mism_a = abstain_by_time[split]
                    exclusions = {"excluded_listed": res_a + mism_a + missing[split],
                                  "confounded": 0, "absorbed": 0, "purged": purged,
                                  "quarantine": quar,
                                  "detail": {"abstain_resolver_none": res_a,
                                             "abstain_fill_mismatch": mism_a,
                                             "abstain_missing_endpoint": missing[split],
                                             "direction_0_abstain": dir0,
                                             "ties_non_hit": ties}}
                    receipt = dict(receipt_base)
                    receipt["seal_row"] = {
                        "path": f"{RUNS_REL}/SEAL_AND_BUDGET.json",
                        "membership_sha256": mem.get(split, ""),
                        **({"retirement_note": LABEL_TUNE_RETIRED} if retired else {}),
                    }
                    for test_id, null_txt, test_def in (
                        ("H0_1", hit_null,
                         {"name": "exact binomial (math.comb), one-sided greater",
                          "sidedness": "one-sided (greater)", "alpha": ALPHA,
                          "statistic": {"hits": k, "n": n,
                                        "hit_rate": round(k / n, 6) if n else None},
                          "p_value": p_hit,
                          "wilson_ci_95": wilson_ci(k, n) if n else None}),
                        ("H0_2", ex_null,
                         {"name": "exact sign test on excess", "sidedness": "two-sided",
                          "alpha": ALPHA,
                          "statistic": {"pos": pos, "neg": neg, "zeros_excluded": ties},
                          "p_value": p_sign}),
                    ):
                        ci = {"method": "mirror-trick block_bootstrap_ci (grading_stats "
                                        "L121, default draws 800 seed 7)",
                              "block": "one non-overlapping anchor unit (h+1 sessions >= h)",
                              "cluster_variable": "trade date of the anchor s",
                              "mean": round(sum(xs) / len(xs), 6) if xs else None,
                              "ci95": mirror_mean_ci(xs, cluster)}
                        if ci["ci95"] is None:
                            ci["note"] = "CI NOT ESTIMABLE (cluster-N < 2)"
                        key = block_key(pid, subj["counter"], h, split_name,
                                        f"{baseline}|{test_id}")
                        blocks[key] = make_block(
                            null=null_txt, split=split_name, honest_n=n,
                            cluster_n=len(set(cluster)), literal_rows=len(obs_rows),
                            exclusions=exclusions, test=test_def, ci=ci,
                            trial_accounting=trial_accounting, receipt=receipt)
                        order.append(key)
    return blocks, order


# --------------------------------------------------------------------------- #
# P03 decomposition evaluation
# --------------------------------------------------------------------------- #
FACTOR_PATHS = {
    "SPY": "data/yahoo/SPY.parquet", "KWEB": "data/yahoo/KWEB.parquet",
    "2800.HK": "data/hk/2800.HK.parquet", "3033.HK": "data/hk/3033.HK.parquet",
}
ALL_SERIES = [  # (name, path, close columns)
    ("BABA", "data/yahoo/BABA.parquet", ["close", "close_price"]),
    ("SPY", "data/yahoo/SPY.parquet", ["close", "close_price"]),
    ("KWEB", "data/yahoo/KWEB.parquet", ["close", "close_price"]),
    ("9988", "data/hk_stocks/9988.HK.parquet", ["close"]),
    ("0700", "data/hk_stocks/0700.HK.parquet", ["close"]),
    ("2800.HK", "data/hk/2800.HK.parquet", ["close"]),
    ("3033.HK", "data/hk/3033.HK.parquet", ["close"]),
]


def load_frames(store) -> tuple[dict, dict]:
    """frames[name] = (dates, close_map, close_price_map|None); last input bar."""
    frames, last_bar = {}, None
    for name, path, cols in ALL_SERIES:
        d, maps = load_close_maps(store, path, cols)
        frames[name] = (d, maps.get("close", {}), maps.get("close_price"))
        last_bar = d[-1] if last_bar is None else max(last_bar, d[-1])
    return frames, last_bar


def evaluate_p03(store, rebuilt: dict, frames: dict, challenger_ctx: dict | None) -> dict:
    out: dict = {}
    for subj in SUBJECTS["P01"] + SUBJECTS["P02"]:
        market = subj["market"]
        subj_name = {"adr_baba": "BABA", "hkd_9988": "9988", "hkd_0700": "0700"}[subj["counter"]]
        subj_dates, subj_close, _ = frames[subj_name]
        factors = set()
        for model in ("M1", "M2"):
            factors.update(factors_for(model, market))
        factor_frames = {f: frames[f] for f in factors}
        is_session = is_session_fn(market)
        for h in HORIZONS:
            rows = []
            for m in rebuilt[("P03", subj["counter"], h)]["rows"]:
                if m["split"] not in ("TRAIN", "TUNE"):
                    continue
                s = date.fromisoformat(m["anchor_session_date"])
                base = {"episode_key": m["episode_key"],
                        "anchor_session_date": m["anchor_session_date"],
                        "coverage_date": m["coverage_date"], "split": m["split"]}
                w = resolve_horizon_window(s - timedelta(days=1), h,
                                           "trading_days", market)
                if w is None or w.fill_date != s:
                    state = "ABSTAIN_RESOLVER_NONE" if w is None else "ABSTAIN_FILL_MISMATCH"
                    for model in ("M0", "M1", "M2"):
                        r = dict(base)
                        r.update(model=model, abstention=state)
                        rows.append(r)
                    continue
                d_s = last_session_before(is_session, s)
                for model in ("M0", "M1", "M2"):
                    row = decompose_unit(model, market, h, s, d_s, w.fill_date,
                                         w.coverage_date, subj_close, subj_dates,
                                         {f: factor_frames[f][1] for f in factors},
                                         {f: factor_frames[f][0] for f in factors})
                    row.update(base)
                    row["spec_hash"] = spec_hash(model, subj["security_id"],
                                                 factors_for(model, market), h)
                    if subj["counter"] == "adr_baba" and challenger_ctx is not None \
                            and model == "M1":
                        row["challenger"] = challenger_apply(
                            challenger_ctx, subj_dates, subj_close, s,
                            w.fill_date, w.coverage_date)
                    rows.append(row)
            out[f"P03_{subj['counter']}_{h}"] = rows
    return out


# --------------------------------------------------------------------------- #
# challenger (D13)
# --------------------------------------------------------------------------- #
def build_challenger_context(store, universe: dict) -> dict:
    """Load the admitted panel, fit Gamma on TRAIN, report estimability."""
    names = [a["path"] for a in universe["admitted"]]
    panel_dates, panel_close, panel_aligned = {}, {}, {}
    for p in names:
        d, maps = load_close_maps(store, p, ["close"])
        panel_dates[p] = d
        panel_close[p] = maps["close"]
        panel_aligned[p] = [maps["close"][x] for x in d]
    spy_dates, spy_maps = load_close_maps(store, FACTOR_PATHS["SPY"], ["close"])
    spy_close = spy_maps["close"]
    spy_ret = daily_log_returns(spy_close, spy_dates)

    rows: list = []
    months: set = set()
    for t in sorted(spy_ret):
        if t >= TRAIN_END or t < date(2012, 1, 4):
            continue
        chars: dict = {}
        for p in names:
            ch = characteristics_at(panel_dates[p], panel_aligned[p], t)
            if ch is not None:
                chars[p] = ch
        if len(chars) < 30:
            continue
        months.add(f"{t.year:04d}-{t.month:02d}")
        zm = rank_standardise({k: v["mom_12_1"] for k, v in chars.items()})
        zv = rank_standardise({k: v["vol_63"] for k, v in chars.items()})
        zr = rank_standardise({k: v["rev_21"] for k, v in chars.items()})
        f = spy_ret[t]
        for p, ch in chars.items():
            j = bisect.bisect_left(panel_dates[p], t)
            if j >= len(panel_dates[p]) or panel_dates[p][j] != t or j == 0:
                continue
            prev_d = panel_dates[p][j - 1]
            prev = panel_close[p][prev_d]
            if prev is None or prev <= 0:
                continue
            y = float(np.log(panel_close[p][t] / prev))
            rows.append({"y": y, "f": f,
                         "z": {"mom_12_1": zm[p], "vol_63": zv[p], "rev_21": zr[p]}})
    est = estimability(universe, {m: 1 for m in months})
    ctx = {"estimability": est, "universe_paths": names,
           "train_months": len(months), "gamma_rows": len(rows)}
    if not est["estimable"]:
        ctx["gamma"] = None
        return ctx
    ctx["gamma"] = [float(g) for g in fit_gamma(rows)]
    ctx["panel_dates"] = panel_dates
    ctx["panel_aligned"] = panel_aligned
    ctx["spy_close"] = spy_close
    return ctx


def challenger_apply(ctx: dict, subj_dates: list, subj_close: dict, s: date,
                     fill: date, coverage: date) -> dict:
    """common_IPCA = beta_BABA(s) * F_SPY(window); BABA's z is standardised
    against the panel cross-section at the anchor (panel + BABA), same < 30
    valid-name threshold as the fit."""
    out = {"state": "OK", "beta_ipca__dc": None, "common_ipca__oc": None}
    if ctx.get("gamma") is None:
        out["state"] = "NOT_ESTIMABLE"
        return out
    aligned = [subj_close[d] for d in subj_dates if d in subj_close]
    ch = characteristics_at(subj_dates, aligned, s)
    combined: dict = {}
    for p in ctx["universe_paths"]:
        c = characteristics_at(ctx["panel_dates"][p], ctx["panel_aligned"][p], s)
        if c is not None:
            combined[p] = c
    if ch is not None:
        combined["BABA"] = ch
    out["cross_section_n"] = len(combined)
    if ch is None or len(combined) < 30:
        out["state"] = "ABSTAIN_CROSSSECTION_BELOW_THRESHOLD"
        return out
    zm = rank_standardise({k: v["mom_12_1"] for k, v in combined.items()})
    zv = rank_standardise({k: v["vol_63"] for k, v in combined.items()})
    zr = rank_standardise({k: v["rev_21"] for k, v in combined.items()})
    g = ctx["gamma"]
    beta = g[0] + g[1] * zm["BABA"] + g[2] * zv["BABA"] + g[3] * zr["BABA"]
    f_win = window_log_ret(ctx["spy_close"], fill, coverage)
    if f_win is None:
        out["state"] = "ABSTAIN_MISSING_ENDPOINT"
        return out
    out["beta_ipca__dc"] = float(beta)
    out["common_ipca__oc"] = float(beta) * f_win
    return out


# --------------------------------------------------------------------------- #
# P03 comparison blocks + calibration diagnostics
# --------------------------------------------------------------------------- #
def p03_blocks(p03_obs: dict, rebuilt: dict, leak_retired: set, trial_accounting: dict,
               receipt_base: dict) -> tuple[dict, list, dict]:
    blocks: dict = {}
    order: list = []
    diagnostics: dict = {}
    pairs = [("M0", "M1"), ("M1", "M2")]
    for subj in SUBJECTS["P01"] + SUBJECTS["P02"]:
        counter = subj["counter"]
        cohort = counter == "adr_baba"
        for h in HORIZONS:
            rows = p03_obs[f"P03_{counter}_{h}"]
            by_model: dict = {}
            for r in rows:
                by_model.setdefault(r["model"], {})[r["episode_key"]] = r
            if cohort:
                ipca = {}
                for ek, r in by_model["M1"].items():
                    ch = r.get("challenger") or {}
                    ipca[ek] = {
                        "episode_key": ek, "split": r["split"],
                        "anchor_session_date": r["anchor_session_date"],
                        "abstention": "OK" if ch.get("state") == "OK" else ch.get("state"),
                        "r__oc": r["r__oc"], "common__oc": ch.get("common_ipca__oc"),
                    }
                by_model["IPCA"] = ipca
            models = ["M0", "M1", "M2"] + (["IPCA"] if cohort else [])
            for model in models:
                for split in ("TRAIN", "TUNE"):
                    diagnostics[f"{counter}|{model}|h={h}|{split}"] = _calibration(
                        by_model, model, split)
            mem = {sp: info["membership_sha256"]
                   for sp, info in rebuilt[("P03", counter, h)]["digests"].items()}
            comparisons = pairs + ([("M1", "IPCA")] if cohort else [])
            for prev, nxt in comparisons:
                for split in ("TRAIN", "TUNE"):
                    label = ""
                    if not cohort:
                        label = LABEL_DESCRIPTIVE_HK
                    elif nxt == "IPCA" and split == "TRAIN":
                        label = LABEL_IN_SAMPLE
                    if split == "TUNE" and "P03" in leak_retired:
                        label = (label + "; " if label else "") + LABEL_TUNE_RETIRED
                    key = block_key("P03", counter, h, split, f"{nxt}_vs_{prev}")
                    blocks[key] = _comparison_block(
                        by_model[prev], by_model[nxt], prev, nxt, split,
                        label=label, receipt_base=receipt_base, membership=mem,
                        trial_accounting=trial_accounting, rows_total=len(rows))
                    order.append(key)
    return blocks, order, diagnostics


def _comparison_block(prev_rows: dict, next_rows: dict, prev: str, nxt: str, split: str,
                      *, label: str, receipt_base: dict, membership: dict,
                      trial_accounting: dict, rows_total: int) -> dict:
    paired = []
    pair_incomplete = challenger_not_ok = 0
    for ek, p in prev_rows.items():
        if p["split"] != split or p["abstention"] != "OK" or p.get("r__oc") is None:
            continue
        n = next_rows.get(ek)
        if n is None or n["abstention"] != "OK" or n.get("common__oc") is None:
            pair_incomplete += 1
            continue
        paired.append((ek, p, n))
    ds = [(p["r__oc"] - p["common__oc"]) ** 2 - (p["r__oc"] - n["common__oc"]) ** 2
          for _, p, n in paired]
    r2s = [p["r__oc"] ** 2 for _, p, n in paired]
    cluster = [n["anchor_session_date"] for _, p, n in paired]
    sum_d, sum_r2 = sum(ds) if ds else 0.0, sum(r2s) if r2s else 0.0
    delta_r2 = (sum_d / sum_r2) if sum_r2 > 0 else None
    ci = mirror_mean_ci(ds, cluster) if ds else None
    if delta_r2 is None:
        verdict = "NOT ESTIMABLE (no paired units on this split)"
    elif delta_r2 > 0 and ci is not None and ci[0] > 0:
        verdict = (f"{nxt} beats {prev} on this split (S0 criterion met; descriptive, "
                   "non-confirmatory)")
    else:
        verdict = (f"KILL/HOLD-AS-RESEARCH — {nxt} shows no incremental explanation "
                   f"over {prev} on this split")
    met = verdict.startswith(f"{nxt} beats")
    null_txt = (f"incremental explanation of {nxt} over {prev} is zero on this split; "
                + ("the pre-registered S0 criterion is met (descriptive, "
                   "non-confirmatory)" if met else
                   "the pre-registered S0 criterion is not met"))
    ci_block = {"method": "mirror-trick block_bootstrap_ci (grading_stats L121, default "
                          "draws 800 seed 7) on mean(d)",
                "block": "one non-overlapping anchor unit (h+1 sessions >= h)",
                "cluster_variable": "trade date of the anchor s",
                "mean_d": round(sum_d / len(ds), 12) if ds else None,
                "ci95": ci,
                "delta_R2": None if delta_r2 is None else round(delta_r2, 8)}
    if ci is None:
        ci_block["note"] = "CI NOT ESTIMABLE (cluster-N < 2)"
    test_def = {"name": "S0 pre-registered incremental-explanation criterion",
                "sidedness": "one-sided via the pre-registered rule delta_R2 > 0 AND CI "
                             "lower bound > 0 (approximately one-sided alpha 0.025)",
                "alpha": 0.025,
                "statistic": {"delta_R2": ci_block["delta_R2"], "paired_units": len(ds)},
                "verdict": verdict}
    exclusions = {"excluded_listed": pair_incomplete + challenger_not_ok,
                  "confounded": 0, "absorbed": 0,
                  "purged": sum(1 for r in prev_rows.values()
                                if r["split"].startswith("PURGED_")),
                  "quarantine": sum(1 for r in prev_rows.values()
                                    if r["split"] == "QUARANTINE"),
                  "detail": {"pair_incomplete": pair_incomplete,
                             "challenger_not_ok": challenger_not_ok}}
    receipt = dict(receipt_base)
    receipt["seal_row"] = {"path": f"{RUNS_REL}/SEAL_AND_BUDGET.json",
                           "membership_sha256": membership.get(split, "")}
    b = make_block(null=null_txt, split=split, honest_n=len(ds),
                   cluster_n=len(set(cluster)), literal_rows=rows_total,
                   exclusions=exclusions, test=test_def, ci=ci_block,
                   trial_accounting=trial_accounting, receipt=receipt)
    if label:
        b["analysis_set"] = b["analysis_set"] + f"; {label}"
    return b


def _calibration(by_model: dict, model: str, split: str) -> dict:
    rows = [r for r in by_model.get(model, {}).values()
            if r["split"] == split and r["abstention"] == "OK"]
    z = [r["z__oc"] for r in rows if r.get("z__oc") is not None]
    n = len(z)
    cov95 = sum(1 for v in z if abs(v) <= 1.96)
    cov68 = sum(1 for v in z if abs(v) <= 1.0)
    out = {"model": model, "split": split, "n": n,
           "coverage_1.96": {"k": cov95, "n": n, "nominal": NOMINAL_95,
                             "wilson_ci_95": wilson_ci(cov95, n) if n else None},
           "coverage_1.0": {"k": cov68, "n": n, "nominal": NOMINAL_6827,
                            "wilson_ci_95": wilson_ci(cov68, n) if n else None},
           "beta_stability": {}}
    for key in ("beta_SPY__dc", "beta_KWEB__dc", "beta_2800.HK__dc", "beta_3033.HK__dc"):
        vals = [r[key] for r in rows if r.get(key) is not None]
        if vals:
            out["beta_stability"][key] = {"mean": float(np.mean(vals)),
                                          "std": float(np.std(vals, ddof=1)),
                                          "count": len(vals)}
    return out


# --------------------------------------------------------------------------- #
# trial ledger helpers
# --------------------------------------------------------------------------- #
def _trial_accounting(ledger: TrialLedger, family: str) -> dict:
    return {"family": family,
            "literal_n": ledger.literal_n(family),
            "effective_n": ledger.effective_n(family),
            "declared_budget": ledger.declared_budget(family)}


def retirement_membership(rebuilt: dict, pid: str, counter: str) -> str:
    parts = []
    for h in HORIZONS:
        info = rebuilt[(pid, counter, h)]["digests"].get("TUNE")
        if info:
            parts.append(f"h={h}:{info['membership_sha256']}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def log_retirement(ledger: TrialLedger, family: str, pid: str, counter: str,
                   rebuilt: dict, leak: dict) -> None:
    evidence = {name: {"first_offending_date": leak[name]["detection"]["first_offending_date"],
                       "count_of_steps_in_window":
                           leak[name]["detection"]["count_of_steps_in_window"],
                       "count_of_steps_total": leak[name]["steps_total"]}
                for name in ("BABA", "SPY", "KWEB") if leak[name]["detection"]}
    ledger.log_trial(
        config={"event": "holdout_retired", "protocol_id": pid, "version": VERSION,
                "split": "TUNE", "membership_sha256": retirement_membership(rebuilt, pid, counter),
                "contamination_class": "information_leak",
                "detected_at": DETECTED_AT, "evidence": evidence},
        family=family, info_cutoff=INFO_CUTOFF,
        source="sni_s0_holdout_retirement",
        note=("TUNE retired for this protocol: the adjustment vintage post-dates the "
              "earliest TUNE anchor. A window return is invariant to a multiplicative "
              "adjustment constant across the window; the leak is the vintage, not "
              "necessarily the value."))


def log_directional_configs(ledger: TrialLedger, pid: str, subjects: list) -> None:
    fam = f"sni.s1_residual.{pid}"
    for subj in subjects:
        for baseline in BASELINES:
            for h in HORIZONS:
                ledger.log_trial(config={"protocol_id": pid, "subject": subj["counter"],
                                         "baseline": baseline, "h": h},
                                 family=fam, info_cutoff=INFO_CUTOFF,
                                 source="sni_s1_historical_descriptive")


def log_p03_configs(ledger: TrialLedger, challenger_ctx: dict | None) -> None:
    fam = "sni.s1_residual.P03"
    est = (challenger_ctx or {}).get("estimability", {})
    challenger_note = None
    if challenger_ctx is not None and not est.get("estimable", False):
        e = est
        challenger_note = (f"CHALLENGER NOT ESTIMABLE (admitted_names="
                           f"{e['admitted_names']}, characteristics={e['characteristics']}, "
                           f"train_months={e['train_months_with_valid_cross_section']})")
    for h in HORIZONS:
        ledger.log_trial(config={"protocol_id": "P03", "kind": "cohort_comparison",
                                 "subject": "adr_baba", "pair": "M1_vs_M0", "h": h},
                         family=fam, info_cutoff=INFO_CUTOFF,
                         source="sni_s1_historical_descriptive")
        ledger.log_trial(config={"protocol_id": "P03", "kind": "cohort_comparison",
                                 "subject": "adr_baba", "pair": "M2_vs_M1", "h": h},
                         family=fam, info_cutoff=INFO_CUTOFF,
                         source="sni_s1_historical_descriptive")
        ledger.log_trial(config={"protocol_id": "P03", "kind": "challenger_comparison",
                                 "subject": "adr_baba", "pair": "ipca_vs_M1", "h": h},
                         family=fam, info_cutoff=INFO_CUTOFF,
                         source="sni_s1_historical_descriptive", note=challenger_note)
        for subj in ("hkd_9988", "hkd_0700"):
            for pair in ("M1_vs_M0", "M2_vs_M1"):
                ledger.log_trial(config={"protocol_id": "P03", "kind": "descriptive_comparison",
                                         "subject": subj, "pair": pair, "h": h},
                                 family=fam, info_cutoff=INFO_CUTOFF,
                                 source="sni_s1_historical_descriptive")


# --------------------------------------------------------------------------- #
# main pipeline
# --------------------------------------------------------------------------- #
def run_pipeline(store, repo_root: Path, out_dir: Path, ledger_path_arg: str) -> dict:
    repo_root = repo_root.resolve()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seal, rebuilt = verify_seal(store, repo_root, store.input_ref)

    frames, last_bar = load_frames(store)
    global INFO_CUTOFF
    INFO_CUTOFF = last_bar.isoformat()

    # -- D10 INFO-LEAK predicate -------------------------------------------- #
    earliest_tune = _earliest_tune_anchor(rebuilt, ("P01", "P03"), "adr_baba")
    leak: dict = {}
    leak_retired: set = set()
    for name in ("BABA", "SPY", "KWEB"):
        d, close, close_price = frames[name]
        steps, state = vintage_series(d, [close.get(x) for x in d],
                                      [close_price.get(x) if close_price else None
                                       for x in d])
        hit = leak_detect(steps, state, earliest_tune, last_bar)
        leak[name] = {"state": state, "detection": hit, "steps_total": len(steps)}
        if hit:
            leak_retired.update(("P01", "P03") if name in ("BABA", "SPY") else ("P03",))
    for name in ("9988", "0700", "2800.HK", "3033.HK"):
        leak[name] = {"state": "VINTAGE_UNVERIFIABLE", "detection": None, "steps_total": 0}

    # -- challenger context --------------------------------------------------- #
    universe = json.loads((repo_root / RUNS_REL / "CHALLENGER_UNIVERSE.json").read_text("utf-8"))
    challenger_ctx = build_challenger_context(store, universe)

    receipt_base = {
        "code_tree_sha": code_tree_sha(repo_root),
        "base": BASE,
        "prereg_digest_sha256": seal["prereg_digest_sha256"],
        "ledger_path": ledger_path_arg,
        "prior_looks": "none for v1",
    }

    ledger = TrialLedger(path=_resolve_ledger(repo_root, ledger_path_arg))
    results: dict = {}
    observations_out: dict = {}

    # -- P01 ------------------------------------------------------------------ #
    with register_trials("sni.s1_residual.P01", budget=6,
                         reason="baseline(always_long, trail63) x h(5,21,63) "
                                "x subject(adr_baba)",
                         ledger=ledger):
        if "P01" in leak_retired:
            log_retirement(ledger, "sni.s1_residual.P01", "P01", "adr_baba", rebuilt, leak)
        log_directional_configs(ledger, "P01", PROTOCOL_SUBJECTS["P01"])
        evaluation = evaluate_directional("P01", store, rebuilt)
        observations_out.update(evaluation["observations"])
        blocks, order = directional_blocks(
            "P01", evaluation, rebuilt, leak_retired,
            trial_accounting=_trial_accounting(ledger, "sni.s1_residual.P01"),
            receipt_base=receipt_base)
        results["P01"] = {"family": "sni.s1_residual.P01", "blocks": blocks,
                          "block_order": order}

    # -- P02 ------------------------------------------------------------------ #
    with register_trials("sni.s1_residual.P02", budget=4,
                         reason="subject(hkd_9988, hkd_0700) x baseline(always_long, "
                                "trail63) x h(5,21,63)",
                         ledger=ledger):
        log_directional_configs(ledger, "P02", PROTOCOL_SUBJECTS["P02"])
        evaluation = evaluate_directional("P02", store, rebuilt)
        observations_out.update(evaluation["observations"])
        blocks, order = directional_blocks(
            "P02", evaluation, rebuilt, leak_retired,
            trial_accounting=_trial_accounting(ledger, "sni.s1_residual.P02"),
            receipt_base=receipt_base)
        results["P02"] = {"family": "sni.s1_residual.P02", "blocks": blocks,
                          "block_order": order}

    # -- P03 ------------------------------------------------------------------ #
    with register_trials("sni.s1_residual.P03", budget=4,
                         reason="BABA cohort (M1_vs_M0, M2_vs_M1) x h = 6; challenger "
                                "ipca_vs_M1 x h = 3; HK descriptive 2 subjects x 2 pairs "
                                "x h = 12",
                         ledger=ledger):
        if "P03" in leak_retired:
            log_retirement(ledger, "sni.s1_residual.P03", "P03", "adr_baba", rebuilt, leak)
        log_p03_configs(ledger, challenger_ctx)
        p03_obs = evaluate_p03(store, rebuilt, frames, challenger_ctx)
        observations_out.update(p03_obs)
        blocks, order, diagnostics = p03_blocks(
            p03_obs, rebuilt, leak_retired,
            trial_accounting=_trial_accounting(ledger, "sni.s1_residual.P03"),
            receipt_base=receipt_base)
        results["P03"] = {"family": "sni.s1_residual.P03", "blocks": blocks,
                          "block_order": order, "diagnostics": diagnostics}

    # -- write outputs ---------------------------------------------------------- #
    for key, rows in sorted(observations_out.items()):
        write_json(out_dir / "observations" / f"{key}.json", rows)
    for pid in ("P01", "P02", "P03"):
        r = results[pid]
        doc = {"protocol_id": pid, "family": r["family"],
               "prereg_digest_sha256": seal["prereg_digest_sha256"],
               "labels": D1_LABELS,
               "blocks": {k: r["blocks"][k] for k in r["block_order"]}}
        if "diagnostics" in r:
            doc["diagnostics"] = r["diagnostics"]
        write_json(out_dir / "results" / f"{pid}.json", doc)
    lane = _lane_manifest(store, repo_root, seal, leak, leak_retired, rebuilt, ledger,
                          challenger_ctx)
    write_json(out_dir / "LANE_MANIFEST.json", lane)
    (out_dir / "REPORT.md").write_text(
        render_report_md({"title": "SNI S1 residual baseline — P01/P02/P03 "
                                   "(historical-descriptive)",
                          "labels": D1_LABELS, "base": BASE, "branch": BRANCH,
                          "prereg_digest_sha256": seal["prereg_digest_sha256"]},
                         results), encoding="utf-8")
    return {"results": results, "lane": lane, "challenger": challenger_ctx,
            "leak": leak, "rebuilt": rebuilt}


def _resolve_ledger(repo_root: Path, ledger_arg: str) -> Path:
    p = Path(ledger_arg)
    return p if p.is_absolute() else (repo_root / p)


def _earliest_tune_anchor(rebuilt: dict, pids: tuple, counter: str) -> date:
    best = None
    for pid in pids:
        for h in HORIZONS:
            for r in rebuilt[(pid, counter, h)]["rows"]:
                if r["split"] in ("TUNE", "PURGED_TUNE"):
                    d = date.fromisoformat(r["anchor_session_date"])
                    best = d if best is None or d < best else best
    if best is None:
        raise RuntimeError(f"no TUNE anchor found for {pids}/{counter}")
    return best


def _lane_manifest(store, repo_root, seal, leak, leak_retired, rebuilt, ledger,
                   challenger_ctx) -> dict:
    ret_rows = []
    for pid in sorted(leak_retired):
        names = [n for n in ("BABA", "SPY", "KWEB") if leak[n]["detection"]]
        ret_rows.append({
            "protocol_id": pid, "version": VERSION, "split": "TUNE",
            "membership_sha256": retirement_membership(rebuilt, pid, "adr_baba"),
            "contamination_class": "information_leak",
            "detected_at": DETECTED_AT,
            "evidence": {"series": {n: leak[n]["detection"] for n in names}},
            "successor": f"{pid} v2 — not drafted; owner = seat/S0",
            "ledger_row": True,
        })
    return {
        "lane": LANE, "version": VERSION, "base": BASE, "branch": BRANCH,
        "input_ref": store.input_ref,
        "seal_commit_sha": seal_commit_sha(repo_root),
        "prereg_digest_sha256": seal["prereg_digest_sha256"],
        "labels": D1_LABELS,
        "authority_flags": {"rank": False, "gate": False, "size": False,
                            "signal": False, "escalation": False, "trade": False},
        "prior_looks": "none for v1",
        "info_cutoff": INFO_CUTOFF,
        "families": {pid: _trial_accounting(ledger, f"sni.s1_residual.{pid}")
                     for pid in ("P01", "P02", "P03")},
        "a23_retirement_visible": True,
        "retirements": ret_rows,
        "vintage_states": {n: leak[n]["state"] for n in
                           ("BABA", "SPY", "KWEB", "9988", "0700", "2800.HK", "3033.HK")},
        "vintage_note_hk": "HK series carry no raw close_price column: VINTAGE_UNVERIFIABLE "
                           "— disclosed, not retired; TRAIN is never retired",
        "challenger_estimability": (challenger_ctx or {}).get("estimability"),
        "splits_evaluated": {f"{pid}/{counter}/h={h}":
                             {sp: info["count"] for sp, info in
                              sorted(rebuilt[(pid, counter, h)]["digests"].items())}
                             for pid in ("P01", "P02", "P03")
                             for counter in sorted({s["counter"]
                                                    for s in PROTOCOL_SUBJECTS[pid]})
                             for h in HORIZONS},
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-ref", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--trial-ledger-path", required=True,
                    help="run-local trial ledger JSONL (REQUIRED, no default)")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--check", action="store_true",
                    help="run into a temp dir and byte-compare against the committed runs/")
    return ap.parse_args(argv)


def _byte_compare(committed: Path, produced: Path) -> bool:
    for rel in (Path("REPORT.md"), Path("LANE_MANIFEST.json"), Path("results"),
                Path("observations")):
        if not _tree_equal(committed / rel, produced / rel):
            print(f"check: differs under {rel}", file=sys.stderr)
            return False
    return _ledger_equal(committed / "trial_ledger.jsonl", produced / "trial_ledger.jsonl")


def _tree_equal(a: Path, b: Path) -> bool:
    if a.is_file() or b.is_file():
        return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()
    if not a.exists() and not b.exists():
        return True
    if a.exists() != b.exists():
        return False
    na = sorted(x.name for x in a.iterdir())
    nb = sorted(x.name for x in b.iterdir())
    if na != nb:
        return False
    return all(_tree_equal(a / n, b / n) for n in na)


def _ledger_equal(a: Path, b: Path) -> bool:
    def rows(p: Path):
        if not p.exists():
            return None
        out = []
        for line in p.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            r.pop("ts", None)
            out.append(canon(r))
        return out
    return rows(a) == rows(b)


def main(argv=None, store=None) -> int:
    global DETECTED_AT
    args = parse_args(argv if argv is not None else sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()

    data_root = repo_root / "data"
    ledger_arg = args.trial_ledger_path
    lp = Path(ledger_arg)
    resolved = lp if lp.is_absolute() else (repo_root / lp)
    try:
        resolved = resolved.resolve()
        bad = resolved == data_root.resolve() or data_root.resolve() in resolved.parents
    except OSError:
        bad = False
    if bad:
        print("REFUSED: --trial-ledger-path resolves inside <repo>/data/", file=sys.stderr)
        return 2

    if store is None:
        store = GitBlobStore(repo_root, args.input_ref, dict(INPUT_PINS))
        try:
            store.verify_all()
        except Exception as e:
            print(f"REFUSED: input pin verification failed: {e}", file=sys.stderr)
            return 2

    DETECTED_AT = store.commit_date_iso(BASE)   # deterministic: BASE commit date

    try:
        if args.check:
            with tempfile.TemporaryDirectory(prefix="sni_s1_check_") as td:
                out_dir = Path(td) / "out"
                run_pipeline(store, repo_root, out_dir, ledger_arg)
                ok = _byte_compare(repo_root / RUNS_REL, out_dir)
                print("check:", "IDENTICAL" if ok else "DIFFERS")
                return 0 if ok else 1

        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = repo_root / out_dir
        run_pipeline(store, repo_root, out_dir, ledger_arg)
        return 0
    except SealMismatch as e:
        print(f"SEAL MISMATCH — refusing to run: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
