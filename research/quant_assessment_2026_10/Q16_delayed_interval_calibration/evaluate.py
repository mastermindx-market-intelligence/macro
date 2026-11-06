"""Q16 single frozen evaluation: synthetic controls plus ONE empirical holdout comparison.

Refuses to run unless sha256(PREREG.md) equals the hash recorded in FREEZE.log and every
data input matches the pre-registered sha256. Refuses a second holdout run once
decision.json exists (stop rule). Every invocation, including refusals, appends one
record to RUNS.log with command, exit code, input and output sha256s.

Research-only; reads licensed local prices read-only; writes only inside this directory.
"""
from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q16_common as C  # noqa: E402
from engine import interval_delayed_calibration as M  # noqa: E402

PREREG = C.HERE / "PREREG.md"
FREEZE = C.HERE / "FREEZE.log"
AMENDMENT = C.HERE / "PREREG_AMENDMENT.md"
AMENDMENT_LOG = C.HERE / "AMENDMENT.log"
MODULE_PATH = C.STAGING / "engine" / "interval_delayed_calibration.py"
# Amendment 1 (audit MAJOR): the harness module that produces the evidence is itself a
# hashed input, so the shipped module and the module that ran cannot differ silently.
EXPECTED_MODULE_SHA256 = "59db81bd854a1b5a18722a25fa3e3397680661ca068f65519b754825661b6725"
OUT_CONTROLS = C.HERE / "controls.json"
OUT_EMPIRICAL = C.HERE / "empirical.json"
OUT_DECISION = C.HERE / "decision.json"

EXPECTED_INPUTS = {
    "SPY": "6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152",
    "QQQ": "5e851c16c54a1bfe190cdc454cf88b17b2a23601d6e15897f74be2ad19bebf0c",
    "IWM": "fbb51d631c7bae1d9c76152e24b291ea2847c76a424a8db8385c267109f962ea",
    "TLT": "609a3eddb55dcbe33c66c98ddf0a635d0a49a685edee6d2651e17c18dc472a93",
    "GLD": "07170179f8c72d63b5c5144481bde2c81df2c8dbf7fde2dfe2a4499771a1527b",
    "engine/vol_forecast.py": "bcd6ec2cc8c116b469173ab475dc495be7e024b4ea452b9d1cf6de58301e06c0",
}

H = C.HORIZON
ALPHA = C.ALPHA
Z80 = 1.2815515655446004
GAMMAS = (0.001, 0.005, 0.01, 0.02, 0.05)
WINDOW = 504
MIN_CALIB = 252
TUNE_START = 504
BLOCK = 44
N_BOOT = 2000
BOOT_SEED = 16
R_CONTROLS = 200
SCENARIO_SEED = {"stationary": 10000, "shift_up": 20000, "shift_down": 30000}
MIN_HONEST_BLOCKS = 60
REL_BAR = -0.02
COV_TOL = 0.03
WIDTH_CAP = 1.25
MIN_REGIME_BLOCKS = 20


def clean(o):
    """JSON-safe: NaN/inf -> None, numpy scalars -> python."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if not math.isfinite(f) else round(f, 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def frozen_hash() -> str:
    for line in FREEZE.read_text(encoding="utf-8").splitlines():
        if line.startswith("PREREG_SHA256="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("FREEZE.log has no PREREG_SHA256 line")


def amendment_ok() -> bool:
    """If an amendment exists, its sha256 must equal the one witnessed in AMENDMENT.log."""
    if not AMENDMENT.exists():
        return True
    if not AMENDMENT_LOG.exists():
        return False
    want = None
    for line in AMENDMENT_LOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("AMENDMENT_SHA256="):
            want = line.split("=", 1)[1].strip()
    return want is not None and C.sha256_file(AMENDMENT) == want


# ─────────────────────────────────────────────────────────────────────────────
# Controls
# ─────────────────────────────────────────────────────────────────────────────

def run_controls() -> dict:
    reps = []
    viol = 0
    gam: dict[str, list[float]] = {}
    for sc, base in SCENARIO_SEED.items():
        for r in range(R_CONTROLS):
            out = M.control_experiment(scenario=sc, horizon=H, alpha=ALPHA, window=WINDOW,
                                       gammas=GAMMAS, seed=base + r)
            viol += int(out["maturity_violations_aci"])
            gam.setdefault(sc, []).append(out["gamma"])
            reps.append(out)
    dv = M.discrimination_verdict(reps, alpha=ALPHA)
    means: dict = {}
    for sc in SCENARIO_SEED:
        rs = [x for x in reps if x["scenario"] == sc]
        means[sc] = {}
        for meth in ("fixed", "rolling", "aci", "aci_leaky"):
            means[sc][meth] = {}
            for seg in ("test", "post"):
                means[sc][meth][seg] = {
                    k: float(np.mean([x[meth][seg][k] for x in rs]))
                    for k in ("coverage", "mean_width", "mean_interval_score")}
        g = np.asarray(gam[sc])
        means[sc]["gamma_counts"] = {str(v): int(np.sum(g == v)) for v in GAMMAS}
    return {"R_per_scenario": R_CONTROLS, "seeds": SCENARIO_SEED, "discrimination": dv,
            "means": means, "maturity_violations_aci_total": viol}


# ─────────────────────────────────────────────────────────────────────────────
# Empirical holdout (single run)
# ─────────────────────────────────────────────────────────────────────────────

def run_empirical() -> dict:
    panel = C.load_panel()
    axis = next(iter(panel.values())).index
    n = len(axis)
    te = int(np.searchsorted(axis.values, np.datetime64(C.TRAIN_END_DATE), side="right") - 1)
    idx = np.arange(n)
    methods = ("m0", "fixed", "rolling", "aci", "aci_leaky", "aci_lag1")
    nis = {m: np.full((len(C.ASSETS), n), np.nan) for m in methods}
    cov = {m: np.full((len(C.ASSETS), n), np.nan) for m in methods}
    wid = {m: np.full((len(C.ASSETS), n), np.nan) for m in methods}
    ris = {m: np.full((len(C.ASSETS), n), np.nan) for m in methods}
    regimes = np.empty((len(C.ASSETS), n), dtype=object)
    per_asset: dict = {}
    violations: dict = {}
    for ai, a in enumerate(C.ASSETS):
        fr = C.asset_frame(panel[a], H)
        y = fr["y"].to_numpy(dtype=float)
        sig = fr["sigma_h"].to_numpy(dtype=float)
        regimes[ai] = fr["regime"].to_numpy(dtype=object)
        s = M.normalized_scores(y, sig)
        abs_s = np.abs(s)
        qf = M.fixed_split_quantile(abs_s, ALPHA, te, H)
        tg = M.tune_gamma(abs_s, horizon=H, alpha=ALPHA, gammas=GAMMAS, train_end=te,
                          tune_start=TUNE_START, window=WINDOW, min_calib=MIN_CALIB)
        tg1 = M.tune_gamma(abs_s, horizon=H, alpha=ALPHA, gammas=GAMMAS, train_end=te,
                           tune_start=TUNE_START, window=WINDOW, min_calib=MIN_CALIB,
                           avail_lag=1)
        runs = {
            "m0": M.run_delayed_calibration(abs_s, horizon=H, alpha=ALPHA, method="fixed",
                                            q_fixed=Z80, window=WINDOW),
            "fixed": M.run_delayed_calibration(abs_s, horizon=H, alpha=ALPHA, method="fixed",
                                               q_fixed=qf, window=WINDOW),
            "rolling": M.run_delayed_calibration(abs_s, horizon=H, alpha=ALPHA,
                                                 method="rolling", window=WINDOW,
                                                 min_calib=MIN_CALIB),
            "aci": M.run_delayed_calibration(abs_s, horizon=H, alpha=ALPHA, method="aci",
                                             gamma=tg["gamma"], window=WINDOW,
                                             min_calib=MIN_CALIB),
            "aci_leaky": M.run_leaky_aci_diagnostic(abs_s, alpha=ALPHA, gamma=tg["gamma"],
                                                    window=WINDOW, min_calib=MIN_CALIB),
            "aci_lag1": M.run_delayed_calibration(abs_s, horizon=H, alpha=ALPHA, method="aci",
                                                  gamma=tg1["gamma"], window=WINDOW,
                                                  min_calib=MIN_CALIB, avail_lag=1),
        }
        for m, r in runs.items():
            mm = M.interval_metrics(r["q"], s, ALPHA)
            rr = M.interval_metrics(r["q"], s, ALPHA, scale=sig)
            nis[m][ai] = mm["interval_score"]
            cov[m][ai] = mm["covered"]
            wid[m][ai] = mm["width"]
            ris[m][ai] = rr["interval_score"]
        violations[a] = {
            "rolling": M.maturity_violations(runs["rolling"]["consumed_max"], H),
            "aci": M.maturity_violations(runs["aci"]["consumed_max"], H),
            "aci_lag1": M.maturity_violations(runs["aci_lag1"]["consumed_max"], H, 1),
            "aci_leaky_vs_true_horizon": M.maturity_violations(
                runs["aci_leaky"]["consumed_max"], H),
        }
        test_pos = idx > te
        q_ok = np.ones(n, dtype=bool)
        for m in ("fixed", "rolling", "aci"):
            q_ok &= np.isfinite(runs[m]["q"])
        per_asset[a] = {
            "q_fixed": qf, "gamma_aci": tg["gamma"], "gamma_aci_lag1": tg1["gamma"],
            "gamma_table": tg["table"], "gamma_table_lag1": tg1["table"],
            "attrition": {
                "test_positions": int(test_pos.sum()),
                "missing_sigma": int((test_pos & ~np.isfinite(sig)).sum()),
                "missing_label_immature_at_data_end": int((test_pos & ~np.isfinite(y)).sum()),
                "missing_issued_q": int((test_pos & ~q_ok).sum()),
                "in_asset_support": int((test_pos & np.isfinite(s) & q_ok).sum()),
            },
        }

    test_pos = idx > te
    support = np.ones((len(C.ASSETS), n), dtype=bool)
    for m in ("fixed", "rolling", "aci"):
        support &= np.isfinite(nis[m])
    common = test_pos & support.all(axis=0)
    dates = np.where(common)[0]
    honest = M.honest_block_count(dates, H)

    def pooled(m: str) -> dict:
        return {"coverage": float(np.mean(cov[m][:, common])),
                "mean_width": float(np.mean(wid[m][:, common])),
                "mean_interval_score": float(np.mean(nis[m][:, common])),
                "mean_raw_interval_score": float(np.mean(ris[m][:, common])),
                "n_rows": int(common.sum() * len(C.ASSETS))}

    pooled_all = {m: pooled(m) for m in methods
                  if np.all(np.isfinite(nis[m][:, common]))}
    fix_t = nis["fixed"][:, common].mean(axis=0)
    aci_t = nis["aci"][:, common].mean(axis=0)
    rol_t = nis["rolling"][:, common].mean(axis=0)
    d = aci_t - fix_t
    boot = M.circular_block_bootstrap(d, fix_t, block_len=BLOCK, n_boot=N_BOOT,
                                      seed=BOOT_SEED)
    nw = M.newey_west_se(d, BLOCK)
    d_roll = aci_t - rol_t
    boot_roll = M.circular_block_bootstrap(d_roll, rol_t, block_len=BLOCK, n_boot=N_BOOT,
                                           seed=BOOT_SEED)

    per_asset_test = {}
    for ai, a in enumerate(C.ASSETS):
        per_asset_test[a] = {}
        for m in methods:
            v = nis[m][ai, common]
            if not np.all(np.isfinite(v)):
                continue
            per_asset_test[a][m] = {"coverage": float(np.mean(cov[m][ai, common])),
                                    "mean_width": float(np.mean(wid[m][ai, common])),
                                    "mean_interval_score": float(np.mean(v))}

    reg_lab = regimes[:, common].ravel()
    reg_org = np.tile(dates, (len(C.ASSETS), 1)).ravel()
    regime = {}
    for m in ("m0", "fixed", "rolling", "aci"):
        rs = M.regime_support(reg_lab, cov[m][:, common].ravel(), reg_org, H,
                              min_blocks=MIN_REGIME_BLOCKS)
        flat_nis = nis[m][:, common].ravel()
        for k in rs:
            sel = np.array([str(v) == k for v in reg_lab])
            rs[k]["mean_interval_score"] = float(np.mean(flat_nis[sel])) if sel.any() else None
        regime[m] = rs

    leaky_gap = None
    if "aci_leaky" in pooled_all:
        leaky_gap = pooled_all["aci_leaky"]["mean_interval_score"] - \
            pooled_all["aci"]["mean_interval_score"]

    return {
        "axis_first": str(axis[0].date()), "axis_last": str(axis[-1].date()), "n_axis": n,
        "train_end_pos": te, "train_end_date": str(axis[te].date()),
        "test_first_date": str(axis[dates[0]].date()) if dates.size else None,
        "test_last_date": str(axis[dates[-1]].date()) if dates.size else None,
        "n_common_test_dates": int(dates.size), "honest_test_blocks": int(honest),
        "pooled": pooled_all, "per_asset_test": per_asset_test, "per_asset": per_asset,
        "primary": {"relative_effect_R": boot["point"], "R_ci95": [boot["lo"], boot["hi"]],
                    "mean_d": float(np.mean(d)), "nw_se_mean_d": nw,
                    "nw_t": float(np.mean(d) / nw) if nw and nw > 0 else None,
                    "bootstrap": boot},
        "aci_vs_rolling": {"mean_d": float(np.mean(d_roll)), "relative": boot_roll["point"],
                           "ci95": [boot_roll["lo"], boot_roll["hi"]]},
        "regime_support": regime, "leaky_minus_aci_nis": leaky_gap,
        "maturity_violations": violations,
    }


def decide(emp: dict, ctl: dict) -> dict:
    p = emp["pooled"]
    gap = {m: abs(p[m]["coverage"] - (1 - ALPHA)) for m in ("fixed", "aci", "rolling")}
    viol_emp = sum(v["aci"] + v["aci_lag1"] + v["rolling"]
                   for v in emp["maturity_violations"].values())
    viol_total = viol_emp + ctl["maturity_violations_aci_total"]
    crit = {
        "c1_relative_effect": bool(emp["primary"]["relative_effect_R"] <= REL_BAR and
                                   emp["primary"]["R_ci95"][1] < 0),
        "c2_coverage_gap": bool(gap["aci"] <= max(gap["fixed"], COV_TOL)),
        "c3_width_cap": bool(p["aci"]["mean_width"] <= WIDTH_CAP * p["fixed"]["mean_width"]),
        "c4_beats_rolling": bool(emp["aci_vs_rolling"]["mean_d"] <= 0),
        "c5_controls_and_maturity": bool(ctl["discrimination"]["controls_discriminate"] and
                                         viol_total == 0),
    }
    if emp["honest_test_blocks"] < MIN_HONEST_BLOCKS:
        verdict = "INSUFFICIENT_DATA"
    elif all(crit.values()):
        verdict = "KEEP"
    else:
        verdict = "REJECT"
    return {"verdict": verdict, "criteria": crit, "coverage_gap": gap,
            "maturity_violations_total": viol_total,
            "honest_test_blocks": emp["honest_test_blocks"]}


def main() -> int:
    got = C.sha256_file(PREREG)
    want = frozen_hash()
    if got != want:
        print(f"REFUSED: sha256(PREREG.md)={got} != FREEZE.log {want}", file=sys.stderr)
        return 2
    ins = C.input_hashes()
    bad = {k: v for k, v in ins.items() if EXPECTED_INPUTS.get(k) != v}
    if bad:
        print(f"REFUSED: input hash mismatch {sorted(bad)}", file=sys.stderr)
        return 3
    mod = C.sha256_file(MODULE_PATH)
    if mod != EXPECTED_MODULE_SHA256:
        print(f"REFUSED: harness module sha256 {mod} != {EXPECTED_MODULE_SHA256}",
              file=sys.stderr)
        return 3
    if not amendment_ok():
        print("REFUSED: PREREG_AMENDMENT.md sha256 does not match AMENDMENT.log",
              file=sys.stderr)
        return 2
    if OUT_DECISION.exists():
        print("REFUSED: decision.json exists; single-holdout stop rule", file=sys.stderr)
        return 4
    ctl = run_controls()
    emp = run_empirical()
    dec = decide(emp, ctl)
    # All result files are written together only after every computation succeeded, so a
    # crash leaves no partial result (stop rule: a crash rerun is allowed, logged).
    OUT_CONTROLS.write_text(json.dumps(clean(ctl), indent=1, sort_keys=True) + "\n")
    OUT_EMPIRICAL.write_text(json.dumps(clean(emp), indent=1, sort_keys=True) + "\n")
    OUT_DECISION.write_text(json.dumps(clean(dec), indent=1, sort_keys=True) + "\n")
    print(json.dumps(clean(dec), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    except Exception:
        traceback.print_exc()
        rc = 1
    inputs = {}
    try:
        inputs = C.input_hashes()
    except Exception:
        pass
    for p in (PREREG, FREEZE, AMENDMENT, AMENDMENT_LOG, Path(__file__).resolve(),
              C.HERE / "q16_common.py", MODULE_PATH):
        if p.exists():
            inputs[str(p.relative_to(C.STAGING))] = C.sha256_file(p)
    outputs = {p.name: C.sha256_file(p) for p in (OUT_CONTROLS, OUT_EMPIRICAL, OUT_DECISION)
               if p.exists()} if rc == 0 else {}
    C.append_run([sys.executable] + sys.argv, rc, inputs, outputs,
                 note="Q16 frozen evaluation (controls + single empirical holdout)"
                 if rc == 0 else "Q16 evaluate.py non-zero exit (refusal or crash)")
    sys.exit(rc)
