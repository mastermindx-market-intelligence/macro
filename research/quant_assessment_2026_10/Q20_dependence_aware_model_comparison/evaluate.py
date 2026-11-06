"""Q20 evaluator — research only. Refuses to run unless PREREG.md matches FREEZE.log.

Stages (each appends one record to RUNS.log with command, exit code, input and output
sha256s):

  baseline   reproduce the incumbent's published full-sample allocation figures
  simulate   method-control simulation (correlated nulls, true-signal control, budget)
  empirical  the single pre-registered dependence-aware comparison on the vector family
             (refuses to run twice — no repeated holdout search; the refusal holds if
             the result file exists OR RUNS.log already records an exit-0 empirical run)
  replay-baseline | replay-simulate | replay-empirical
             deterministic recomputation of a stored result under the CURRENT module and
             evaluator bytes; writes nothing to results/, fails on any byte mismatch

baseline and simulate also refuse to overwrite a stored result (use the replay stage).

Usage: python evaluate.py --stage <stage> --data-root <macro data dir> --config <config.yml>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.dont_write_bytecode = True

PREREG = HERE / "PREREG.md"
FREEZE = HERE / "FREEZE.log"
RUNS = HERE / "RUNS.log"
RESULTS = HERE / "results"

EXPECTED_INPUTS = {
    "vector/signals.parquet": "b0df9712370c4af4f5cf779512c862c0ba6e453639d2ec51b0e54a411ada1996",
    "vector/calibration.json": "1fc7b6e664d55bf6c75d39d42ae430d02f394b748af4bcc5078e6b680ba290ce",
    "trial_ledger.jsonl": "58b7feba20efafca5125faaf21330343a07141496379b4b9aea0fa8cc112380d",
}
EXPECTED_CONFIG = "b8963682e5f2fe209cee1a604f19e51bbce232992d75c0b26c60a615600a310f"
VARIANTS = ("conservative", "moderate", "aggressive", "optimal")
FAMILY, SOURCE = "vector", "alloc_variant"
PRIMARY_BLOCK, B_EMP, SEED_EMP = 21, 5000, 7
SENS_BLOCKS = (7, 14, 21, 42, 63)
ANN = 365.0
EFFECT_BAR = 0.02
SIM = {"n": 2100, "k": 20, "phi": 0.3, "B": 499, "mean_block": 21, "reps": 1000, "seed": 20}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def freeze_guard() -> str:
    text = FREEZE.read_text(encoding="utf-8")
    frozen = None
    for tok in text.split():
        if tok.startswith("sha256="):
            frozen = tok.split("=", 1)[1]
            break
    actual = sha256(PREREG)
    if frozen is None or actual != frozen:
        raise SystemExit(f"REFUSED: sha256(PREREG.md)={actual} does not match FREEZE.log ({frozen})")
    return actual


def append_run(cmd: str, code: int, inputs: dict, outputs: dict, note: str) -> None:
    rec = {"command": cmd, "exit_code": code, "inputs_sha256": inputs,
           "outputs_sha256": outputs, "note": note}
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def logged_success(stage: str) -> bool:
    """True when RUNS.log already holds an exit-0 record for exactly this stage."""
    if not RUNS.exists():
        return False
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("exit_code") == 0 and rec.get("note") == f"stage={stage} ok":
            return True
    return False


def dumps(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=float) + "\n"


def write_json(name: str, obj: dict) -> tuple[str, str]:
    RESULTS.mkdir(exist_ok=True)
    p = RESULTS / name
    p.write_text(dumps(obj), encoding="utf-8")
    return f"results/{name}", sha256(p)


def load_inputs(data_root: Path, config_path: Path) -> tuple[dict, dict]:
    hashes = {}
    for rel, exp in EXPECTED_INPUTS.items():
        p = data_root / rel
        if not p.exists():
            raise FileNotFoundError(f"INSUFFICIENT_DATA: missing input {p}")
        h = sha256(p)
        if h != exp:
            raise SystemExit(f"REFUSED: input {rel} sha256 {h} != frozen {exp}")
        hashes[str(p)] = h
    ch = sha256(config_path)
    if ch != EXPECTED_CONFIG:
        raise SystemExit(f"REFUSED: config sha256 {ch} != frozen {EXPECTED_CONFIG}")
    hashes[str(config_path)] = ch
    import yaml
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))["vector"]["calibration"]
    return hashes, cfg


def load_ledger(data_root: Path) -> list[dict]:
    rows = []
    with open(data_root / "trial_ledger.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_panel(data_root: Path, cfg: dict):
    import numpy as np
    import pandas as pd
    cols = ["close"] + [f"alloc_{v}" for v in VARIANTS]
    raw_cols = [f"alloc_{v}_raw" for v in VARIANTS]
    df_all = pd.read_parquet(data_root / "vector/signals.parquet")
    present_raw = [c for c in raw_cols if c in df_all.columns]
    df = df_all[cols].sort_index()
    n_export = len(df)
    df = df.loc[pd.Timestamp(cfg["start_date"]):]
    support = {"rows_export": n_export, "rows_from_start": len(df),
               "nan_rows_from_start": int(df.isna().any(axis=1).sum()),
               "excluded_columns": {c: "not itemized in the trial ledger (no generation-time "
                                       "trial identity) — not a candidate" for c in present_raw}}
    r = df["close"].pct_change().to_numpy()
    return df, r, support, np


def stage_baseline(data_root: Path, cfg: dict) -> dict:
    from engine import challenger_spa_comparison as q
    df, r, support, np = load_panel(data_root, cfg)
    cal = json.loads((data_root / "vector/calibration.json").read_text(encoding="utf-8"))
    pub = cal["allocation"]
    cost = float(cfg["cost_bps"]) / 1e4
    out = {"published": {}, "reproduced_lag1": {}, "reproduced_lag0_diagnostic": {},
           "support": support, "cost_one_way": cost}
    for lag, key in ((1, "reproduced_lag1"), (0, "reproduced_lag0_diagnostic")):
        for v in VARIANTS:
            net = q.strategy_net_returns(r, df[f"alloc_{v}"].to_numpy(), cost, lag=lag)
            net = net[np.isfinite(net)]
            sh = float(net.mean() / net.std(ddof=1) * math.sqrt(ANN))
            cagr = float(np.prod(1 + net) ** (ANN / net.size) - 1)
            out[key][v] = {"sharpe": round(sh, 4), "cagr_pct": round(100 * cagr, 2), "n": int(net.size)}
    rr = r[np.isfinite(r)]
    out["reproduced_hodl"] = {"sharpe": round(float(rr.mean() / rr.std(ddof=1) * math.sqrt(ANN)), 4),
                              "cagr_pct": round(100 * float(np.prod(1 + rr) ** (ANN / rr.size) - 1), 2),
                              "n": int(rr.size)}
    ok = True
    for v in VARIANTS:
        p = pub[v]
        out["published"][v] = {"sharpe": p.get("sharpe"), "cagr_pct": p.get("cagr"),
                               "hodl_sharpe": p.get("hodl_sharpe"), "hodl_cagr_pct": p.get("hodl_cagr"),
                               "n_obs": p.get("n_obs")}
        rep = out["reproduced_lag1"][v]
        ds, dc = abs(rep["sharpe"] - p["sharpe"]), abs(rep["cagr_pct"] - p["cagr"])
        rep["abs_diff_sharpe"], rep["abs_diff_cagr_pp"] = round(ds, 4), round(dc, 2)
        ok &= ds <= 0.05 and dc <= 3.0
    out["tolerance"] = {"sharpe": 0.05, "cagr_pp": 3.0}
    out["reproduced_within_tolerance"] = bool(ok)
    out["published_multiple_testing"] = {k: cal["multiple_testing"].get(k) for k in
                                         ("dsr", "n_trials", "selected_variant", "verdict", "t_eff", "dsr_effN")}
    out["published_allocation_bootstrap"] = cal.get("allocation_bootstrap", {}).get("sharpe_ci")
    return out


def stage_simulate(ledger: list[dict]) -> dict:
    from engine import challenger_spa_comparison as q
    k = SIM["k"]
    scen = {
        "N1_null_rho0.9": (0.9, [0.0] * k),
        "N2_null_rho0.5": (0.5, [0.0] * k),
        "N3_null_poor_alts_rho0.9": (0.9, [0.0] * 5 + [-0.1] * 15),
        "P1_true_signal_rho0.9": (0.9, [0.1] + [0.0] * (k - 1)),
    }
    res = {}
    for i, (name, (rho, means)) in enumerate(scen.items()):
        res[name] = q.simulate_rejection_rates(SIM["n"], k, rho, SIM["phi"], means, SIM["reps"],
                                               SIM["B"], SIM["mean_block"], SIM["seed"] * 1000 + i)
    base = q.original_trial_budget(ledger, FAMILY)
    mono = {"original": base, "rows": {}, "never_below_original": True, "non_decreasing": True}
    for rho in (0.5, 0.9, 0.99):
        seq = [q.trial_budget_after_adding(base["budget"], base["literal_n"], m, rho) for m in range(0, 51)]
        mono["rows"][str(rho)] = {"m0": seq[0], "m10": seq[10], "m50": seq[50]}
        mono["never_below_original"] &= min(seq) >= base["budget"]
        mono["non_decreasing"] &= all(b >= a for a, b in zip(seq, seq[1:]))
    gates = {
        "N1_size_le_0.075": res["N1_null_rho0.9"]["rates"]["p_c"] <= 0.075,
        "N2_size_le_0.075": res["N2_null_rho0.5"]["rates"]["p_c"] <= 0.075,
        "N2_naive_oversizes_ge_0.10": res["N2_null_rho0.5"]["rates"]["naive"] >= 0.10,
        "N3_size_le_0.075": res["N3_null_poor_alts_rho0.9"]["rates"]["p_c"] <= 0.075,
        "P1_power_ge_0.80": res["P1_true_signal_rho0.9"]["rates"]["p_c"] >= 0.80,
        "budget_monotone": bool(mono["never_below_original"] and mono["non_decreasing"]),
    }
    return {"settings": SIM, "scenarios": res, "budget_monotonicity": mono, "gates": gates,
            "all_gates_pass": all(gates.values())}


def stage_empirical(data_root: Path, cfg: dict, ledger: list[dict]) -> dict:
    import pandas as pd
    from engine import challenger_spa_comparison as q
    sim_path = RESULTS / "simulation_controls.json"
    if not sim_path.exists():
        raise SystemExit("REFUSED: run the simulate stage first (method gates feed the verdict)")
    sim = json.loads(sim_path.read_text(encoding="utf-8"))
    mapped = q.map_candidates_to_trials({v: {"variant": v} for v in VARIANTS}, ledger, FAMILY, SOURCE)
    budget = q.original_trial_budget(ledger, FAMILY)
    gen_ts = max(pd.Timestamp(m["ledger_ts"]) for m in mapped).tz_convert(None)
    df, r, support, np = load_panel(data_root, cfg)
    idx = df.index
    cost = float(cfg["cost_bps"]) / 1e4
    nets = np.column_stack([q.strategy_net_returns(r, df[f"alloc_{v}"].to_numpy(), cost, lag=1)
                            for v in VARIANTS])
    valid = np.isfinite(nets).all(axis=1) & np.isfinite(r)
    support["rows_lost_to_lags"] = int((~valid).sum())
    split = pd.Timestamp(cfg["split_date"])
    train, test = q.chronological_split(idx.values, np.datetime64(split))
    tr, te = train & valid, test & valid
    betas = [q.risk_match_beta(nets[tr, j], r[tr]) for j in range(len(VARIANTS))]
    d = nets[te] - np.array(betas)[None, :] * r[te][:, None]
    t_idx = idx.values[te]
    n = d.shape[0]
    primary = q.spa_test(d, B=B_EMP, mean_block=PRIMARY_BLOCK, seed=SEED_EMP, time_index=t_idx)
    sens = q.block_length_sensitivity(d, SENS_BLOCKS, B=B_EMP, seed=SEED_EMP, time_index=t_idx)
    best = primary["best_index"]
    ann = [ANN * float(x) for x in primary["dbar"]]
    best_ann = max(ann)
    naive = q.naive_best_pvalue(d)
    cash = q.spa_test(nets[te], B=B_EMP, mean_block=PRIMARY_BLOCK, seed=SEED_EMP, time_index=t_idx)
    loggrowth = [ANN * float(np.mean(np.log1p(nets[te][:, j]) - np.log1p(r[te]))) for j in range(len(VARIANTS))]
    pbo = q.cscv_pbo(nets[te], S=16)
    cal = json.loads((data_root / "vector/calibration.json").read_text(encoding="utf-8"))
    calib_asof = pd.Timestamp(cal.get("trial_log", {}).get("asof") or gen_ts)
    eval_start, eval_end = pd.Timestamp(t_idx[0]), pd.Timestamp(t_idx[-1])
    prior = [(split, max(gen_ts, calib_asof))]
    win_eval = q.window_reuse_disclosure(eval_start, eval_end, gen_ts, prior, q.honest_n_blocks(n))
    post = te & (idx.values > np.datetime64(gen_ts))
    n_post = int(post.sum())
    d_post = nets[post] - np.array(betas)[None, :] * r[post][:, None]
    win_post = q.window_reuse_disclosure(pd.Timestamp(idx.values[post][0]) if n_post else eval_end,
                                         eval_end, gen_ts, prior, q.honest_n_blocks(n_post))
    win_post_no_display = q.window_reuse_disclosure(pd.Timestamp(idx.values[post][0]) if n_post else eval_end,
                                                    eval_end, gen_ts, [], q.honest_n_blocks(n_post))
    report = q.assemble_report(primary, sens, best_ann, win_eval, pbo=pbo, naive=naive)
    verdict = q.study_verdict(sim["gates"], data_eligible=True)
    return {
        "family": FAMILY, "source": SOURCE, "mapped_trials": mapped,
        "trial_budget": budget,
        "attrition": {"compared_candidates": len(mapped),
                      "budget_trials_without_retained_loss_panel": budget["budget"] - len(mapped),
                      "status_of_those": "UNAVAILABLE_LOSS_PANEL (counted in the budget, not dropped)"},
        "generation_ts_utc": str(gen_ts), "split_date": str(split.date()),
        "support": support | {"train_n": int(tr.sum()), "eval_n": n,
                              "eval_start": str(eval_start.date()), "eval_end": str(eval_end.date()),
                              "honest_n_blocks_21": q.honest_n_blocks(n),
                              "t_eff_best_newey_west": round(q.effective_sample_size(d[:, best]), 1)},
        "risk_match_beta_train": dict(zip(VARIANTS, [round(b, 4) for b in betas])),
        "spa_primary": primary | {"candidates": list(VARIANTS)},
        "block_sensitivity": sens,
        "annualised_mean_differential": dict(zip(VARIANTS, [round(a, 5) for a in ann])),
        "best_candidate": VARIANTS[best], "best_annualised_mean_differential": round(best_ann, 5),
        "secondary_non_decisional": {
            "naive_best": naive | {"candidate": VARIANTS[naive["best_index"]]},
            "budget_bonferroni_bound": q.budget_bonferroni(naive["p_naive"], budget["budget"]),
            "spa_vs_cash": {k: cash[k] for k in ("p_l", "p_c", "p_u", "stat")},
            "annualised_log_growth_vs_unscaled_hodl": dict(zip(VARIANTS, [round(x, 5) for x in loggrowth])),
            "cscv_pbo": pbo,
        },
        "windows": {"evaluation": win_eval,
                    "post_generation": win_post | {
                        "n": n_post,
                        "mean_differential_ann": (dict(zip(VARIANTS, [round(ANN * float(x), 5) for x in d_post.mean(axis=0)]))
                                                  if n_post else None),
                        "tested": False,
                        "label_if_nightly_display_reruns_ignored": win_post_no_display["label"]}},
        "report": report,
        "study_verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["baseline", "simulate", "empirical",
                             "replay-baseline", "replay-simulate", "replay-empirical"])
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cmd = " ".join(shlex.quote(x) for x in [sys.executable] + sys.argv)
    inputs = {str(PREREG): sha256(PREREG), str(Path(__file__).resolve()): sha256(Path(__file__).resolve()),
              str(REPO / "engine/challenger_spa_comparison.py"): sha256(REPO / "engine/challenger_spa_comparison.py")}
    outputs: dict = {}
    try:
        freeze_guard()
        data_root, config_path = Path(a.data_root), Path(a.config)
        h, cfg = load_inputs(data_root, config_path)
        inputs.update(h)
        compute = {
            "baseline": ("baseline_repro.json", lambda: stage_baseline(data_root, cfg)),
            "simulate": ("simulation_controls.json", lambda: stage_simulate(load_ledger(data_root))),
            "empirical": ("empirical_comparison.json",
                          lambda: stage_empirical(data_root, cfg, load_ledger(data_root))),
        }
        if a.stage.startswith("replay-"):
            # Deterministic replay of the SAME frozen computation (no new choice, preregistered
            # seeds); proves the stored result is reproduced byte-for-byte by the current
            # module and evaluator bytes. Nothing under results/ is written.
            name, fn = compute[a.stage.split("-", 1)[1]]
            stored = RESULTS / name
            if not stored.exists():
                raise SystemExit("REFUSED: nothing to replay")
            fh = hashlib.sha256(dumps(fn()).encode("utf-8")).hexdigest()
            k, v = f"results/{name}", sha256(stored)
            if fh != v:
                raise SystemExit(f"REPLAY MISMATCH: recomputed {fh} != stored {v}")
        else:
            name, fn = compute[a.stage]
            if (RESULTS / name).exists() or (a.stage == "empirical" and logged_success("empirical")):
                if a.stage == "empirical":
                    raise SystemExit("REFUSED: the single empirical comparison already ran — "
                                     "no repeated holdout search")
                raise SystemExit(f"REFUSED: results/{name} already exists — use --stage replay-{a.stage}")
            k, v = write_json(name, fn())
        outputs[k] = v
    except BaseException as exc:  # record every run, including refusals
        code = exc.code if isinstance(exc, SystemExit) and isinstance(exc.code, int) else 1
        append_run(cmd, code, inputs, outputs, f"stage={a.stage} FAILED: {exc}")
        raise
    append_run(cmd, 0, inputs, outputs, f"stage={a.stage} ok")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    sys.exit(main())
